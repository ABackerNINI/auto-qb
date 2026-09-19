"""auto-qb 子进程启动包装(仅供仿真测试用, 不进 src/)

为什么需要这一层:
    驱动器要在 duration 到点时停掉 auto-qb。直接 terminate()/kill() 在 Windows 上是
    TerminateProcess —— 进程没有机会执行 finally, 于是 `save_state()` 永远不跑,
    state.json 不落盘(实测目录里只剩 state.lock)。这会连带把「跨轮次状态持久化」
    (项目黄金法则 #3)这条判据变成空转。

    CTRL_BREAK_EVENT 也不行: 实测 Python 不会把它转成 KeyboardInterrupt, 进程直接以
    0xC000013A(STATUS_CONTROL_C_EXIT)退出 —— 同样没有 finally。

    所以这里在子进程里显式给 SIGBREAK 装一个抛 KeyboardInterrupt 的处理器, 驱动器的
    graceful_stop() 就能让 auto-qb 走完 `except KeyboardInterrupt -> finally -> save_state()`。

用法(与 `python -m auto_qb <config>` 等价, 只是多了信号处理):
    python scripts/sim_autoqb.py <config.yml> [--dry-run]
"""
from __future__ import annotations

import signal
import sys


def _on_break(signum, frame):  # pragma: no cover - 仅在 Windows 信号路径触发
    raise KeyboardInterrupt


if hasattr(signal, "SIGBREAK"):  # 仅 Windows 有; Linux 走 SIGTERM -> 默认即终止
    signal.signal(signal.SIGBREAK, _on_break)

from auto_qb.cli import main  # noqa: E402  必须在装完信号处理器后导入

if __name__ == "__main__":
    sys.exit(main())
