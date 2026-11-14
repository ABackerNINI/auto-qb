""".commands 包测试的临时目录防呆闸 —— issue 26-11-14-0857 P1b(2026-11-14)。

tests/ 树有 tests/_tmp_bootstrap.py 守着, 包测试此前裸奔: 沙箱把 /tmp 弄成不可写时, tempfile
候选列表末位会**静默回落 CWD**, 而 test.pkg 恰以仓库根起跑 ⇒ gettempdir()=仓库根, 快照副本
(mkdtemp)落进仓库、违背「副本必须在仓库之外」的设计不变量, 删除 / 清扫类操作的爆炸半径也对准了
仓库本身(26-11-13 T4 移植事故同族面)。本闸只拦这一致命面: gettempdir() 解析后落在仓库根之内
⇒ 响亮退出 rc=4(与 tests/ 自举的拒收口径一致); 指向仓库外的外部 TMPDIR 一律放行 —— 包是跨项目
资产, 不复制 tests/ 自举全案, 守卫必须轻到能随包移植。

为什么不 import _snapshot._find_repo_root: 本闸是全体 .commands 包的基建, 不与单个包耦合;
判据(目录须含 HEAD / 文件形态=worktree)按同口径在此落地, 判据漂移时以 _snapshot.py 为准回改。
仅 pytest 层生效: 包自带的 `python <包>/scripts/test_snapshot.py` 直跑形态不经本文件 —— 属纵深
防呆, 不是根治(P0 锚定守卫才是根治, 两者叠加)。
"""
import os
import sys
import tempfile
from pathlib import Path


def _find_repo_root(start: Path) -> Path | None:
    for parent in (start, *start.parents):
        marker = parent / ".git"
        if marker.is_dir():
            if (marker / "HEAD").exists():
                return parent
        elif marker.is_file():
            return parent
    return None


_root = _find_repo_root(Path(__file__).resolve().parent)
if _root is not None:
    _tmp = Path(os.path.realpath(tempfile.gettempdir()))
    _repo = Path(os.path.realpath(_root))
    if _tmp == _repo or _repo in _tmp.parents:
        print(
            f"[FATAL] 临时目录落在仓库内, 拒绝跑包测试(rc=4): gettempdir()={_tmp} 仓库根={_repo}\n"
            "典型根因: 沙箱把 /tmp 弄成不可写 ⇒ tempfile 候选列表末位静默回落 CWD(= 仓库根),\n"
            "快照副本会落进仓库、删除类操作的爆炸半径对准仓库本身(26-11-13 T4 事故同族面)。\n"
            "处置: 放开 /tmp 写权限, 或显式把 TMPDIR 指到仓库之外再跑;\n"
            "背景: memory-bank/pitfalls/testing/tmpdir.md 与 issue 26-11-14-0857-bug-my-commit-flow-snapshot-anchor",
            file=sys.stderr,
        )
        raise SystemExit(4) from None
