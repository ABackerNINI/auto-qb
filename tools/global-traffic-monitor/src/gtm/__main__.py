"""gtm 命令行入口.

子命令:
  run                             采样-落盘-通知主循环 (单写线程; 控制面随 run 启动)
  install-autostart               三平台自启幂等注册 (S5)
  uninstall-autostart             三平台自启幂等卸载 (S5)
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading

from gtm import __version__
from gtm.config import Config, ConfigHolder, load_config
from gtm.installer import AutostartError, UnsupportedPlatformError, build_installer
from gtm.notifier import Notifier
from gtm.sampler import AdapterFilter, Sampler
from gtm.server import ControlServer, TokenManager
from gtm.storage import SingleInstanceLockError, Storage, default_data_dir

logger = logging.getLogger("gtm")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gtm",
        description="全局流量监视小工具 (TrafficMonitor 替代)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"gtm {__version__}",
        help="打印版本号并退出",
    )
    sub = parser.add_subparsers(dest="command", metavar="<命令>")
    run = sub.add_parser("run", help="前台运行采样-落盘主循环 (自启机制拉起的前台服务)")
    run.add_argument(
        "--data-dir",
        default=None,
        metavar="DIR",
        help=f"工具数据目录 (dat/state/lock/config 落点); 默认 {default_data_dir()!r} 或环境变量 GTM_DATA_DIR",
    )
    install = sub.add_parser("install-autostart", help="注册开机自启 (三平台, 幂等)")
    install.add_argument(
        "--data-dir",
        default=None,
        metavar="DIR",
        help="写进注册项的数据目录 (解析成绝对路径写死; 自启拉起不依赖环境变量)",
    )
    uninstall = sub.add_parser("uninstall-autostart", help="卸载开机自启 (三平台, 幂等)")
    return parser


def _build_adapter_filter(config: Config) -> AdapterFilter:
    """配置 -> 适配器过滤 (采样循环每轮重建: PUT /config 改 include/exclude 热生效).

    模式列表以 `|` 并入单个正则 (AdapterFilter 收单正则串; 空列表 -> None)。
    过滤集变更会让采样器的合计口径与既有基线错位一次: 下次 delta 判定为计数器
    重置 (记 0 + WARNING) 后自愈, 属预期降级而非数据损坏。
    非法正则已在 config 校验层拒掉 (聚合报错), 到不了这里。
    """
    include = "|".join(config.adapter_include) or None
    exclude = "|".join(config.adapter_exclude) or None
    return AdapterFilter(include=include, exclude=exclude)


def _run_loop(
    storage: Storage,
    sampler: Sampler,
    holder: ConfigHolder,
    stop_event: threading.Event,
    notifier: Notifier | None = None,
) -> None:
    """采样-落盘-通知主循环 (每轮读 holder.current: PUT /config 热重载即时生效)。

    stop_event.wait 替代 time.sleep: 停止信号即时响应 (不空等一个采样间隔)。
    单轮异常只记 ERROR 不杀循环 (与「通知失败不阻断落盘」对称)。

    通知 (S4): 阈值参数每轮现读 (热重载生效); **首个成功帧**走 catch_up 补发一次
    —— 启动/崩溃恢复后订阅者的视图可能已陈旧 (计划 §04 S4)。catch_up 只在派发
    成功后才算完成 (notify 抛错时保持待补发, 下一轮重试)。
    """
    first_frame = True
    while not stop_event.is_set():
        cfg = holder.current
        try:
            # 过滤器重建也进 try: 配置侧万一漏过非法正则, 只丢一轮不杀循环
            sampler.filter = _build_adapter_filter(cfg)
            storage.set_flush_params(cfg.flush_delta_bytes, cfg.flush_interval_s)
            result = sampler.sample_once()
            storage.record(result, sampler.snapshot())
            if notifier is not None:
                notifier.notify(result, catch_up=first_frame)
                first_frame = False
        except Exception:
            # 单轮采样/落盘/通知失败 (Windows replace 竞态耗尽重试/磁盘满/state 写失败
            # 等) 不杀守护进程: ERROR 可见, 下一轮重试自愈 (与「通知失败不阻断落盘」
            # 对称)
            logger.exception("采样/落盘/通知本轮失败, 下一轮重试")
        stop_event.wait(cfg.sample_interval)


def cmd_run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    data_dir = args.data_dir or default_data_dir()
    # 配置加载: 校验失败 fail-fast 并聚合报错 (黄金法则 4; 不静默用默认值继续)
    config, _ = _load_config_or_fail(data_dir)
    if config is None:
        return 1
    holder = ConfigHolder(config)
    storage = Storage(
        data_dir,
        flush_delta_bytes=config.flush_delta_bytes,
        flush_interval_s=config.flush_interval_s,
    )
    try:
        storage.acquire_lock()  # fail-fast: 二次启动即报错 (单实例)
    except SingleInstanceLockError as e:
        print(f"gtm: {e}", file=sys.stderr)
        return 1
    sampler = Sampler(adapter_filter=_build_adapter_filter(config))
    server = ControlServer(
        storage,
        sampler,
        holder,
        TokenManager(f"{data_dir}/monitor.token"),
        host=config.http_host,
        port=config.http_port,
    )
    try:
        server.start()  # fail-fast: 控制面端口占用即报错 (计划 §03 S3)
    except OSError as e:
        print(f"gtm: 控制面启动失败 (端口 {config.http_port} 被占用?): {e}", file=sys.stderr)
        storage.release_lock()
        return 1
    stop_event = threading.Event()
    notifier = Notifier(storage, holder)
    try:
        for w in storage.recover(sampler):
            logger.warning("恢复告警 | %s", w)
        logger.info(
            "gtm 启动 | data_dir=%s dat=%s sample_interval=%ss 通知阈值=%dMiB 控制面=%s",
            data_dir,
            storage.dat_path,
            config.sample_interval,
            config.notify_threshold_bytes // (1024 * 1024),
            server.url(),
        )
        _run_loop(storage, sampler, holder, stop_event, notifier)
    except KeyboardInterrupt:
        logger.info("收到中断, 优雅退出 (最终落盘 + 释放锁 + 停控制面)")
    finally:
        stop_event.set()
        try:
            notifier.close()  # 有界等待在途推送 (守护线程, 超时即弃)
        except Exception:
            logger.exception("通知器收尾失败")
        try:
            server.stop()
        except Exception:
            logger.exception("控制面停止失败")
        try:
            storage.close()
        except Exception:
            logger.exception("最终落盘失败 (下次启动从 state/dat 恢复)")
        storage.release_lock()
    return 0


def _load_config_or_fail(data_dir: str) -> tuple[Config | None, tuple[str, ...]]:
    """加载 config.yml; 校验失败 -> 聚合错误逐条打到 stderr 并返回 (None, errors)."""
    config, errors = load_config(f"{data_dir}/config.yml")
    if config is None:
        for e in errors:
            print(f"gtm: config 校验失败: {e}", file=sys.stderr)
    return config, errors


def cmd_autostart(args: argparse.Namespace, *, install: bool) -> int:
    """自启注册/卸载 (S5): 幂等, 结果打到 stdout, 退出码供 S6 设置页判成败.

    退出码: 0 = 达成期望态 (含 skipped/absent 两种 no-op) · 1 = 平台命令失败/前置
    条件缺失 · 2 = 平台不支持 (非 Windows/Linux/macOS)。
    卸载不需要数据目录 (注册项按固定名称定位), 故 uninstall-autostart 无 --data-dir。
    """
    data_dir = getattr(args, "data_dir", None) or default_data_dir()
    try:
        backend = build_installer(data_dir)
    except UnsupportedPlatformError as e:
        print(f"gtm: {e}", file=sys.stderr)
        return 2
    except AutostartError as e:
        print(f"gtm: 自启{'注册' if install else '卸载'}失败: {e}", file=sys.stderr)
        return 1
    try:
        result = backend.register() if install else backend.unregister()
    except AutostartError as e:
        print(f"gtm: 自启{'注册' if install else '卸载'}失败: {e}", file=sys.stderr)
        return 1
    print(f"gtm: {result.message}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "install-autostart":
        return cmd_autostart(args, install=True)
    if args.command == "uninstall-autostart":
        return cmd_autostart(args, install=False)
    # 无子命令: 打印帮助
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
