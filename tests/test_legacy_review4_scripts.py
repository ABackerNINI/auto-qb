"""test_legacy_review4_scripts: R4 存量评审 scripts 主题各修复批次的守卫用例(共用落点)。

P3 批(表#4): scripts/check_context_caps.py 的 porcelain 改动集解析 --
`git status --porcelain` 的 rename 行(`R  old -> new`)必须按状态位分流、以 " -> " 拆开,
新旧两侧路径都进改动集: 旧实现整行 line[3:] 塞进集合, 两个真实路径都不在,
`git mv AGENTS.md docs/AGENTS.md` 这类操作会让硬规定的「改动命中」判定(rel in changed)
静默漏检(与 git() 里「整段 strip 吃掉首行行首空格」的自述漏检同类)。普通行(M/A/D/??)不回归。

本文件是 legacy-review4 scripts 各批次共用的测试落点, 后续批次往里追加用例,
头部 docstring 的「## 测试计划」清单随用例同步登记。用例纯内存构造, 不真跑 git
写操作、不连 qB、不写仓库外文件。

## 测试计划(每个测试函数一条, 后续批次往里追加)
- test_porcelain_rename_paths_both_sides_in_changed_set: `R  old -> new` 按两侧拆开入集; `RM`(暂存改名+工作区又改)同款; 集合里不得残留整串形态
- test_porcelain_scored_rename_still_parsed: 带评分形态 `R90 old -> new`(常规 porcelain v1 不出评分, 防御性兼容)同样两侧入集
- test_porcelain_plain_rows_unchanged: M / MM / A / D / ?? / !! 行为不回归; 首行行首空格不被吃(整段 strip 漏检 "GENTS.md" 的旧坑钉住)
- test_porcelain_modified_path_with_arrow_not_split: 非 rename 行(状态位无 R/C)路径里含 " -> " 不被误拆 -- 分流必须看状态位, 不能只看 " -> "
- test_porcelain_blank_and_short_lines_ignored: 空文本 / 空行 / 纯空白行返回空集, 不产伪路径
- test_porcelain_paths_red_on_whole_string_regression: **红验** -- 旧实现(整串塞入)下 rename 两侧路径都不在集合里, 证明绿判据能区分新旧实现, 不是恒绿
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("check_context_caps", ROOT / "scripts" / "check_context_caps.py")
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def test_porcelain_rename_paths_both_sides_in_changed_set():
    """rename 行(`R  old -> new`)拆开、两侧路径都入改动集; `RM`(暂存改名+工作区又改)同款。"""
    text = (
        "R  AGENTS.md -> docs/AGENTS.md\n"
        "RM README.md -> memory-bank/README.md\n"
        " M scripts/check_context_caps.py\n"
    )
    paths = mod.porcelain_paths(text)
    assert "AGENTS.md" in paths, f"rename 旧路径必须在改动集: {sorted(paths)}"
    assert "docs/AGENTS.md" in paths, f"rename 新路径必须在改动集: {sorted(paths)}"
    assert "README.md" in paths and "memory-bank/README.md" in paths, f"RM 行同样两侧入集: {sorted(paths)}"
    assert "scripts/check_context_caps.py" in paths, "普通 M 行不受影响"
    assert not any(" -> " in p for p in paths), f"改动集里不得残留整串 rename 行: {sorted(paths)}"


def test_porcelain_scored_rename_still_parsed():
    """带评分形态 `R90 old -> new`(常规 porcelain v1 不出评分, 防御性兼容)同样两侧入集。"""
    for line in ("R90 AGENTS.md -> docs/AGENTS.md\n", "R100 AGENTS.md -> docs/AGENTS.md\n"):
        paths = mod.porcelain_paths(line)
        assert paths == {"AGENTS.md", "docs/AGENTS.md"}, f"{line!r} 两侧路径都必须入集: {sorted(paths)}"


def test_porcelain_plain_rows_unchanged():
    """普通 M / MM / A / D / ?? / !! 行为不回归; 首行行首空格不被吃(整段 strip 的旧漏检钉住)。"""
    text = (
        " M AGENTS.md\n"
        "M  src/auto_qb/cli.py\n"
        "MM src/auto_qb/config.py\n"
        "A  docs/new.md\n"
        "D  docs/old.md\n"
        "?? scripts/scratch.py\n"
        "!! ignored.log\n"
    )
    assert mod.porcelain_paths(text) == {
        "AGENTS.md",  # 行首空格必须保住路径起点: 整段 strip 的错位解析会得到 "GENTS.md"
        "src/auto_qb/cli.py",
        "src/auto_qb/config.py",
        "docs/new.md",
        "docs/old.md",
        "scripts/scratch.py",
        "ignored.log",
    }


def test_porcelain_modified_path_with_arrow_not_split():
    """非 rename 行(状态位无 R/C)即使路径里含 " -> " 也整串保留 -- 分流按状态位, 不按 " -> "。"""
    text = " M a -> b.md\n?? weird -> name.md\nA  x -> y.md\n"
    assert mod.porcelain_paths(text) == {"a -> b.md", "weird -> name.md", "x -> y.md"}


def test_porcelain_blank_and_short_lines_ignored():
    """空文本 / 空行 / 纯空白行返回空集, 不产伪路径。"""
    assert mod.porcelain_paths("") == set()
    assert mod.porcelain_paths("\n\n") == set()
    assert mod.porcelain_paths("   \n\t\n") == set()


def test_porcelain_paths_red_on_whole_string_regression():
    """**红验**: 旧实现(整行 line[3:] 整串塞入)下 rename 两侧路径都不在集合里。

    把旧实现逐字内联重放, 断言它确实骗过「两侧路径入集」这一判据 -- 证明上面的
    rename 用例不是恒绿: 生产实现一旦回潮成整串塞入, 本文件的 rename 用例立刻全红。
    """
    text = "R  AGENTS.md -> docs/AGENTS.md\n"
    old_impl = {line[3:].strip() for line in text.splitlines() if line.strip()}  # 旧实现逐字重放
    new_impl = mod.porcelain_paths(text)
    # 新实现: 两侧都入集
    assert "AGENTS.md" in new_impl and "docs/AGENTS.md" in new_impl
    # 旧实现: 两侧都不在, 只塞进整串 -- 这就是回潮时的红面
    assert old_impl == {"AGENTS.md -> docs/AGENTS.md"}
    assert "AGENTS.md" not in old_impl and "docs/AGENTS.md" not in old_impl
