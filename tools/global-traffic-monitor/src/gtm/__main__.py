"""gtm 命令行入口 (S0 骨架: 仅 --version).

后续步骤逐步补充子命令:
  S1-S4: run            采样-落盘-通知主循环 (控制面随 run 启动, 127.0.0.1:8099)
  S5:    install-autostart / uninstall-autostart   三平台自启幂等注册/卸载
"""

from __future__ import annotations

import argparse
import sys

from gtm import __version__


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
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    # S0 骨架: 无子命令时打印版本与骨架提示 (run 等子命令随 S1-S5 落地)
    print(f"gtm {__version__} (S0 骨架; run / install-autostart 子命令随 S1-S5 逐步落地)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
