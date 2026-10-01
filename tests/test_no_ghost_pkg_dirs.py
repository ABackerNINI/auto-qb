"""test_no_ghost_pkg_dirs 守阵: src 下不存在「只剩 __pycache__ 而无任何 .py 的幽灵包目录」。

背景 (issue 26-10-01-1946): core/mixins/ 源码随 9b3c50f8 退役后, 本机残留一个只含
__pycache__ 的空壳目录 (16 个历史 .pyc, mtime 全 <= 09-30), 删过两次被目击「再生」,
2026-10-01 20:49 复现取证: 删目录后跑 test.full (1914 passed) 未再生 —— 残留属历史
产物, 当前测试面已不再触发导入; 但这种空壳会误导「包还在」的排障判断, 用纯静态判定
守住成本极低 (同 test_docs_forms 思路)。

## 测试计划
- test_src_has_no_ghost_pkg_dirs: src 下任何目录若子树里含 __pycache__ 却没有一个 .py, 即红
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _ghost_pkg_dirs() -> list[str]:
    """src 下含 __pycache__ 子目录但自身子树无任何 .py 的目录 (相对 repo 根的路径)。"""
    ghosts: list[str] = []
    if not SRC.is_dir():
        return ghosts
    for cache in SRC.rglob("__pycache__"):
        parent = cache.parent
        if not any(parent.rglob("*.py")):
            ghosts.append(parent.relative_to(ROOT).as_posix())
    return sorted(set(ghosts))


def test_src_has_no_ghost_pkg_dirs():
    ghosts = _ghost_pkg_dirs()
    assert not ghosts, ("src 下发现幽灵包目录 (只剩 __pycache__ 无任何 .py, 会误导排障; "
                        f"源码已退役请整目录删除): {ghosts}")
