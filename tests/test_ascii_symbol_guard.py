"""非 ASCII 图形符号闸门: 全库扫描 + 冻结清单递减不红 (2026-11-08 grilling 拍板 D1-D6)。

判据规范单点: memory-bank/conventions/code-style.md「非 ASCII 图形符号禁令」表 A/B/C。
D1 把「图形符号」收窄为装饰性 / 状态性象形字符 (表 A), 中文行文里的语义标点 (表 B:
箭头 U+2190-21FF / 章节符与数学符) 明确豁免 —— 此前只给示例 + 「等」兜底, 评审按宽口径
判红与规范相左, issue 26-11-08-0044 长期 Open。D2/D3 定闸门形态与载体。

设计不变量: 存量 309 单元 / 2178 处(基线 4cff729d, 2543a603 复验未变)一次清不完 (用户 2026-11-06 拍板「先入池等排期」),
故闸门**带病上岗**: 冻结清单全登记, 只拦新增。key = (文件, 字符类) -> 命中处数:
- 实测 > 冻结 -> 红 (新引入 / 超量); 部分递减 (0 < 实测 < 冻结) 不红;
- 某类清光后**必须同步撤下冻结条目**, 否则回加会被放过 —— 撤下后回加当场红, 递减不可逆;
- 冻结条目目标文件消失即红 (死条目); 排除面三张表每条带理由且目标须真实存在。
与 tests/test_mypy_allowlist_guard.py 同一口径: 摩擦是有意的, 逼每条新豁免留下理由。

排除面: 整目录 (第三方设计骨架 / 参考资源)、整文件 (功能性数据: gitmoji 映射表与断言数据;
逐字镜像与历史快照)、局部 (文件, 字符类) (WebUI 可见文案的关闭图标 U+2715, 延续 0229
先例; 描述 GBK 乱码的 U+FFFD 逐字引文)。文档 .md 与 memory-bank/**.html 按规范放行,
整目录不在扫描面。

检出能力由合成源红验内建: 字符类归属、新增 / 部分递减 / 撤条目后回加 / 归零未撤 /
死条目各有断言, 扫描或对账逻辑退化即红。本守阵与数据模块自身不得含表 A 字面字符
(合成样本一律 chr() 构造), 由 test_guard_sources_have_no_literal_ban_symbols 钉住。

## 测试计划(每个测试函数一条)

- test_count_text_detects_ban_classes_and_spares_semantic_symbols: 合成文本里带圈 / 杂项 / Dingbats / 几何块各计 1, 箭头 / 章节符 / 数学符零命中
- test_findings_reject_new_or_increased_symbol: 干净文件新增符号与冻结单元超量都判红
- test_findings_allow_partial_reduction: 实测少于冻结但未归零 -> 零 finding (递减不红)
- test_findings_reject_re_add_after_entry_removed: 清光并撤下冻结条目后回加同一符号 -> 判红 (递减不可逆)
- test_findings_require_removal_of_zeroed_entry: 冻结条目已归零却未撤下 -> 判红并提示撤下
- test_findings_reject_dead_frozen_target: 冻结条目目标文件不存在 -> 判红
- test_exclusions_have_reasons_and_live_targets: 三张排除表每条理由非空、类名合法、目标真实存在
- test_scan_excludes_exempt_paths: 真仓扫描结果不含任何被排除的目录 / 文件 / 局部单元
- test_scan_surface_covers_declared_scope: 规范覆盖文件后缀全在扫描面, 根级与 .github/.vscode 候选不漏扫, 红线配置显式排除
- test_code_style_table_is_single_source: code-style.md 表 A 的码位 token 集合与闸门常量双向相等
- test_guard_sources_have_no_literal_ban_symbols: 守阵与冻结数据模块自身零表 A 字面字符 (防自指)
- test_repo_matches_frozen: 真仓实测对冻结清单零 finding (带病上岗基线)
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from _ascii_symbol_frozen import (  # noqa: E402
    BAN_CLASSES,
    EXCLUDE_DIRS,
    EXCLUDE_FILES,
    EXEMPT_CELLS,
    FROZEN,
    SCAN_ROOTS,
    collect_files,
    SCAN_SUFFIXES,
    SKIP_PARTS,
)

CODE_STYLE = REPO_ROOT / "memory-bank" / "conventions" / "code-style.md"
GUARD_SOURCES = (Path(__file__).name, "_ascii_symbol_frozen.py")
Cell = tuple[str, str]

# ---- 扫描 -------------------------------------------------------------------------------------------


def _count_text(rel: str, text: str) -> Counter[Cell]:
    """按表 A 逐字符归类计数; 局部豁免单元 (文件, 类) 整类跳过。"""
    out: Counter[Cell] = Counter()
    for ch in text:
        cp = ord(ch)
        for name, ranges in BAN_CLASSES.items():
            if any(a <= cp <= b for a, b in ranges):
                if (rel, name) not in EXEMPT_CELLS:
                    out[(rel, name)] += 1
                break
    return out


def _scan() -> Counter[Cell]:
    """全库只读扫描, 候选文件与冻结清单共用 collect_files 同一份口径。"""
    out: Counter[Cell] = Counter()
    for path in collect_files(REPO_ROOT):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(rel.startswith(d) for d in EXCLUDE_DIRS) or rel in EXCLUDE_FILES:
            continue
        out.update(_count_text(rel, path.read_text(encoding="utf-8", errors="ignore")))
    return out


def _findings(actual: dict[Cell, int], frozen: dict[Cell, int], exists: Callable[[str], bool]) -> list[str]:
    """三类 finding: 新增/超量、目标失效、已归零未撤下。递减 (仍非零) 不产生 finding。"""
    findings: list[str] = []
    for (path, name), count in sorted(actual.items()):
        allowed = frozen.get((path, name), 0)
        if count > allowed:
            findings.append(f"新增/超量 {path} [{name}]: 实测 {count} > 冻结 {allowed}")
    for (path, name), allowed in sorted(frozen.items()):
        if not exists(path):
            findings.append(f"冻结条目目标已失效: {path} [{name}]")
        elif actual.get((path, name), 0) == 0:
            findings.append(f"冻结条目已归零须撤下(否则回加会被放过): {path} [{name}] 冻结 {allowed}")
    return findings


@lru_cache(maxsize=1)
def _repo_actual() -> tuple[tuple[Cell, int], ...]:
    return tuple(sorted(_scan().items()))


def _exists(rel: str) -> bool:
    return (REPO_ROOT / rel).exists()


def _synthetic_exists(_rel: str) -> bool:
    """合成样本路径不落盘, 一律视为存在 —— 让每条红验只聚焦被测的那一条判据。"""
    return True


# ---- 合成源红验 -------------------------------------------------------------------------------------


def test_count_text_detects_ban_classes_and_spares_semantic_symbols() -> None:
    text = (
        "注释 " + chr(0x2460) + " 警告 " + chr(0x26A0) + " 关闭 " + chr(0x2715) + " 流程 " + chr(0x2192) + " 推导 " +
        chr(0x21D2) + " 章节 " + chr(0x00A7) + " 不等 " + chr(0x2260) + " 几何 " + chr(0x25A0)
    )
    got = _count_text("synthetic.py", text)
    assert got == Counter(
        {
            ("synthetic.py", "circled"): 1,
            ("synthetic.py", "misc_symbol"): 1,
            ("synthetic.py", "dingbats"): 1,
            ("synthetic.py", "geometric"): 1,
        }
    )


def test_findings_reject_new_or_increased_symbol() -> None:
    new = _findings({("clean.py", "circled"): 1}, {}, _synthetic_exists)
    assert len(new) == 1 and "新增/超量" in new[0] and "clean.py" in new[0]
    grown = _findings({("a.py", "circled"): 4}, {("a.py", "circled"): 3}, _synthetic_exists)
    assert len(grown) == 1 and "新增/超量" in grown[0]


def test_findings_allow_partial_reduction() -> None:
    assert _findings({("a.py", "circled"): 2}, {("a.py", "circled"): 5}, _synthetic_exists) == []


def test_findings_reject_re_add_after_entry_removed() -> None:
    frozen = {("a.py", "circled"): 3, ("b.py", "circled"): 2}
    withdrawn = {key: value for key, value in frozen.items() if key[0] != "a.py"}
    actual = {("b.py", "circled"): 2}
    assert _findings(actual, withdrawn, _synthetic_exists) == []
    back = dict(actual)
    back[("a.py", "circled")] = 1
    findings = _findings(back, withdrawn, _synthetic_exists)
    assert any("新增/超量" in line and "a.py" in line for line in findings)


def test_findings_require_removal_of_zeroed_entry() -> None:
    findings = _findings({}, {("a.py", "circled"): 3}, _synthetic_exists)
    assert len(findings) == 1 and "须撤下" in findings[0]


def test_findings_reject_dead_frozen_target() -> None:
    findings = _findings({}, {("gone.py", "circled"): 3}, lambda _rel: False)
    assert len(findings) == 1 and "失效" in findings[0]


# ---- 真仓对账 ---------------------------------------------------------------------------------------


def test_exclusions_have_reasons_and_live_targets() -> None:
    for directory, reason in EXCLUDE_DIRS.items():
        assert reason.strip(), f"整目录豁免缺理由: {directory}"
        assert (REPO_ROOT / directory).is_dir(), f"整目录豁免目标已失效: {directory}"
    for path, reason in EXCLUDE_FILES.items():
        assert reason.strip(), f"整文件豁免缺理由: {path}"
        assert (REPO_ROOT / path).is_file(), f"整文件豁免目标已失效: {path}"
    for (path, name), reason in EXEMPT_CELLS.items():
        assert reason.strip(), f"局部豁免缺理由: {path} [{name}]"
        assert name in BAN_CLASSES, f"局部豁免类名越界: {name}"
        assert (REPO_ROOT / path).is_file(), f"局部豁免目标已失效: {path}"


def test_scan_excludes_exempt_paths() -> None:
    actual = dict(_repo_actual())
    for path, _ in actual:
        assert not any(path.startswith(d) for d in EXCLUDE_DIRS), f"排除目录漏过: {path}"
        assert path not in EXCLUDE_FILES, f"排除文件漏过: {path}"
    for key in EXEMPT_CELLS:
        assert key not in actual, f"局部豁免单元漏过: {key}"


def test_scan_surface_covers_declared_scope() -> None:
    """规范「覆盖文件」声明与闸门扫描面一致: 防根级 / 配置目录白名单漂移。"""
    text = CODE_STYLE.read_text(encoding="utf-8")
    match = re.search(r"\*\*覆盖文件\*\*[：:]([^\n]+)", text)
    assert match, "code-style.md 缺覆盖文件声明"
    declared = set(re.findall(r"`\.([\w]+)`", match.group(1)))
    assert len(declared) >= 10, f"覆盖文件声明解析异常: {sorted(declared)}"
    suffixes = {suffix.lstrip(".") for suffix in SCAN_SUFFIXES}
    assert declared <= suffixes, f"规范声明的后缀未纳入闸门: {sorted(declared - suffixes)}"
    candidates = {path.relative_to(REPO_ROOT).as_posix() for path in collect_files(REPO_ROOT)}
    for path in REPO_ROOT.iterdir():
        if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES and path.name not in EXCLUDE_FILES:
            assert path.name in candidates, f"根级文件漏扫: {path.name}"
    for directory in (".github", ".vscode"):
        if (REPO_ROOT / directory).is_dir():
            assert directory in SCAN_ROOTS, f"配置目录 {directory} 不在 SCAN_ROOTS"
            assert any(c.startswith(directory + "/") for c in candidates), f"配置目录 {directory} 未进入扫描面"
    assert "config.yml" in EXCLUDE_FILES, "红线产品配置未显式排除"
    assert all(path != "config.yml" for path, _ in _repo_actual()), "红线产品配置被闸门纳管"


def test_code_style_table_is_single_source() -> None:
    def token(low: int, high: int) -> str:
        return f"U+{low:04X}" if low == high else f"U+{low:04X}-{high:04X}"

    from_guard = {token(low, high) for ranges in BAN_CLASSES.values() for low, high in ranges}
    text = CODE_STYLE.read_text(encoding="utf-8")
    section = text.split("**表 A")[1].split("**表 B")[0]
    from_doc = set(re.findall(r"U\+[0-9A-F]{4,6}(?:-[0-9A-F]{4,6})?", section))
    assert from_guard == from_doc, (
        f"规范表 A 与闸门常量漂移: 规范独有 {sorted(from_doc - from_guard)}, "
        f"闸门独有 {sorted(from_guard - from_doc)}"
    )


def test_guard_sources_have_no_literal_ban_symbols() -> None:
    for name in GUARD_SOURCES:
        text = (TESTS_DIR / name).read_text(encoding="utf-8")
        assert not _count_text("tests/" + name, text), f"守阵源码自含表 A 字面字符: {name}"


def test_repo_matches_frozen() -> None:
    findings = _findings(dict(_repo_actual()), FROZEN, _exists)
    assert not findings, "非 ASCII 图形符号闸门判红:\n  " + "\n  ".join(findings)
