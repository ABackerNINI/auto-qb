"""gtm 命令行入口.

后续步骤逐步补充子命令:
  S2:    run            采样-落盘主循环 (单写线程; 控制面与通知随 S3/S4 接入)
  S3-S4: run            控制面随 run 启动 (127.0.0.1:8099), 通知接入主循环
  S5:    install-autostart / uninstall-autostart   三平台自启幂等注册/卸载
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading

from gtm import __version__
from gtm.config import Config, ConfigHolder, load_config
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
) -> None:
    """采样-落盘主循环 (每轮读 holder.current: PUT /config 热重载即时生效).

    stop_event.wait 替代 time.sleep: 停止信号即时响应 (不空等一个采样间隔)。
    单轮异常只记 ERROR 不杀循环 (与「通知失败不阻断落盘」对称)。
    """
    while not stop_event.is_set():
        cfg = holder.current
        try:
            # 过滤器重建也进 try: 配置侧万一漏过非法正则, 只丢一轮不杀循环
            sampler.filter = _build_adapter_filter(cfg)
            storage.set_flush_params(cfg.flush_delta_bytes, cfg.flush_interval_s)
            result = sampler.sample_once()
            storage.record(result, sampler.snapshot())
        except Exception:
            # 单轮采样/落盘失败 (Windows replace 竞态耗尽重试/磁盘满等) 不杀守护
            # 进程: ERROR 可见, 下一轮重试自愈 (与「通知失败不阻断落盘」对称)
            logger.exception("采样/落盘本轮失败, 下一轮重试")
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
    try:
        for w in storage.recover(sampler):
            logger.warning("恢复告警 | %s", w)
        logger.info(
            "gtm 启动 | data_dir=%s dat=%s sample_interval=%ss 控制面=%s",
            data_dir,
            storage.dat_path,
            config.sample_interval,
            server.url(),
        )
        _run_loop(storage, sampler, holder, stop_event)
    except KeyboardInterrupt:
        logger.info("收到中断, 优雅退出 (最终落盘 + 释放锁 + 停控制面)")
    finally:
        stop_event.set()
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    # 无子命令: 打印帮助 (run 等子命令随 S2-S5 逐步落地)
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
