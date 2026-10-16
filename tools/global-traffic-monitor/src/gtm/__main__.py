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
import time

from gtm import __version__
from gtm.sampler import DEFAULT_SAMPLE_INTERVAL, Sampler
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
        help=f"工具数据目录 (dat/state/lock 落点); 默认 {default_data_dir()!r} 或环境变量 GTM_DATA_DIR",
    )
    return parser


def cmd_run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    data_dir = args.data_dir or default_data_dir()
    storage = Storage(data_dir)
    try:
        storage.acquire_lock()  # fail-fast: 二次启动即报错 (单实例)
    except SingleInstanceLockError as e:
        print(f"gtm: {e}", file=sys.stderr)
        return 1
    sampler = Sampler()  # sample_interval 配置化随 S3 config 落地, 现取模块默认
    try:
        for w in storage.recover(sampler):
            logger.warning("恢复告警 | %s", w)
        logger.info(
            "gtm 启动 | data_dir=%s dat=%s sample_interval=%ss", data_dir, storage.dat_path, DEFAULT_SAMPLE_INTERVAL
        )
        while True:
            try:
                result = sampler.sample_once()
                storage.record(result, sampler.snapshot())
            except Exception:
                # 单轮采样/落盘失败 (Windows replace 竞态耗尽重试/磁盘满等) 不杀守护
                # 进程: ERROR 可见, 下一轮重试自愈 (与「通知失败不阻断落盘」对称)
                logger.exception("采样/落盘本轮失败, 下一轮重试")
            time.sleep(DEFAULT_SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("收到中断, 优雅退出 (最终落盘 + 释放锁)")
    finally:
        try:
            storage.close()
        except Exception:
            logger.exception("最终落盘失败 (下次启动从 state/dat 恢复)")
        storage.release_lock()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    # 无子命令: 打印帮助 (run 等子命令随 S2-S5 逐步落地)
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
