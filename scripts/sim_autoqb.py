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

用法(与 `python -m auto_qb <config>` 等价, 只是多了信号处理 + 可选的 FS mock):
    python scripts/sim_autoqb.py <config.yml> [--dry-run]

FS mock 注入(语料回放, 计划 §07):
    通过**环境变量**开关, 不占 argv —— auto_qb 自己的参数解析不能被动到:
      AUTOQB_FSMOCK_ROOT    语料 FS 根; 设了才装 mock(未设 = 完全原样, 合成档不受影响)
      AUTOQB_FSMOCK_STATE   播放器导出的磁盘状态表 JSON(可选)
      AUTOQB_FSMOCK_PLAYER  `GET /_fsmock/state` 地址(可选; 给了就按秒拉取, 让磁盘状态随时间变)
    安装必须在 `from auto_qb.cli import main` **之前** —— auto-qb 内部按属性访问
    `os.path.exists`, 替换模块属性即可生效, 不需要改 src/ 一行。
"""
from __future__ import annotations

import os
import signal
import sys


def _on_break(signum, frame):  # pragma: no cover - 仅在 Windows 信号路径触发
    raise KeyboardInterrupt


if hasattr(signal, "SIGBREAK"):  # 仅 Windows 有; Linux 走 SIGTERM -> 默认即终止
    signal.signal(signal.SIGBREAK, _on_break)

# ---- FS mock: 必须在导入 auto_qb 之前装(否则 auto_qb 可能已持有 os.path.exists 的引用) ----
_fs_root = os.environ.get("AUTOQB_FSMOCK_ROOT")
if _fs_root:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sim_fsmock import install  # noqa: E402

    _mock = install(
        root=_fs_root,
        state_file=os.environ.get("AUTOQB_FSMOCK_STATE", ""),
        player_url=os.environ.get("AUTOQB_FSMOCK_PLAYER", ""),
    )
    print(f"[fsmock] installed: root={_fs_root} table={len(_mock.table)} 条", file=sys.stderr)

from auto_qb.cli import main  # noqa: E402  必须在装完信号处理器与 FS mock 后导入

if __name__ == "__main__":
    sys.exit(main())
