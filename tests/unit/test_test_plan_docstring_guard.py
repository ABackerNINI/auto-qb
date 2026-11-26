"""tests 全量守阵:「## 测试计划」docstring 清单与实际 def test_* 逐文件机械对账(issue 26-10-21-0502)

模块 docstring 的「## 测试计划」段与文件内实际 `def test_*` 是同一事实的两份表示, AGENTS.md 硬规则
「新增测试必须同步清单」此前只靠人肉 —— 2026-10-05 清理过一轮(11 文件 21 幽灵), 2026-10-22 认领
复验仍积到 51 文件漂移 / 295 条未列 / 4 文件无清单段 / 6 幽灵(取证基线 cecbe4a9 记 56/约290/7)。
本守阵固化比对: 新增/改名/删除用例不同步清单, 全量测试当场红。

判据(与 2026-10-21 取证脚本同口径):
- 段定位: 模块 docstring 里首个含「测试计划」的 `##` 标题行, 段止于下一个 `##` 标题或 docstring 末尾;
- 列表行: 段内以 `-`/`*`/`+`/`N.` 开头的行才算条目, 散文行提及用例名不算登记(散文引用豁免);
- 缺列: 每个 `def test_*`(含类内方法)的用例名必须出现在至少一个列表行;
- 幽灵: 列表行行首(跳过 `**`/反引号/`[x] ` 装饰)锚定的用例名必须是本文件真实存在的 def;
  行中提及(交叉引用如「归 test_xxx」)不作幽灵判;
- 豁免名单: EXEMPT_FILES(整文件)/EXEMPT_NAMES(单用例), 每条必须写理由, 存量清零后保持空表。

检出能力由合成源单测钉住(红验内建): 缺列/幽灵/段边界/装饰/豁免各有断言, 扫描逻辑退化即红。
本文件自身的「## 测试计划」列出下面全部用例 —— 守阵扫描自己也受自己管辖。

## 测试计划(每个测试函数一条)

- test_scan_flags_missing_entry: 新增 def 未登记清单 -> 缺列 finding(合成源红验)
- test_scan_flags_ghost_entry: 行首锚定的条目名没有对应 def -> 幽灵 finding(合成源红验)
- test_scan_accepts_complete_plan_and_prose_mentions: 完整清单零 finding; 散文行提及不算登记也不判幽灵; 列表行行中提及算登记不算幽灵
- test_scan_section_boundary_and_decorations: 段止于下一个「##」标题(段外条目不认); `**`/反引号/[x] 装饰与 N. 序号条目照常锚定
- test_scan_exemptions: EXEMPT_FILES 整文件跳过 + EXEMPT_NAMES 单用例免列
- test_repo_plan_matches_defs: 全仓 tests/test_*.py 扫描零漂移(存量 2026-10-22 已回填, 新漂移当场红)
"""

import ast
import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

# 豁免名单: 文件名(相对 tests/) -> 理由(一句话)。整文件跳过清单比对, 例如用例名运行期动态生成的文件。
EXEMPT_FILES: dict[str, str] = {}

# 豁免名单: (文件名, 用例名) -> 理由(一句话)。该用例不要求列入清单, 且允许条目指向它而文件内无 def。
EXEMPT_NAMES: dict[tuple[str, str], str] = {}

_LIST_LINE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
_TEST_NAME = re.compile(r"\btest_[a-z0-9_]+\b")
_ANCHOR = re.compile(r"^(?:\*\*|`|\[[ x]\]\s*)*(test_[a-z0-9_]+)")
_HEADING_MARK = "测试计划"


def _plan_section(doc: str) -> list[str]:
    """取模块 docstring 里「## 测试计划」段的行(到下一个 `##` 标题或 docstring 末尾), 无该段返回空表。"""
    lines = doc.splitlines()
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("##") and _HEADING_MARK in stripped:
            start = i
            break
    if start is None:
        return []
    body = lines[start + 1:]
    for j, line in enumerate(body):
        stripped = line.strip()
        # 边界只认同级标题「## 」(带空格): 「### 」小节是段内结构, 不得截断 —— 截断了会把
        # 小节后的条目整段算成缺列(26-10-22 回填首跑即误伤 hr 族 16 文件, 靠此口径修正)
        if stripped.startswith("## ") and _HEADING_MARK not in stripped:
            return body[:j]
    return body


def _listed_and_anchored(section: list[str]) -> tuple[set[str], set[str]]:
    """段内列表行 -> (登记名集合, 行首锚定名集合)。行中提及算登记; 只有行首锚定参与幽灵判定。"""
    listed: set[str] = set()
    anchored: set[str] = set()
    for line in section:
        stripped = line.strip()
        m = _LIST_LINE.match(stripped)
        if not m:
            continue
        body = stripped[m.end():]
        listed.update(_TEST_NAME.findall(body))
        a = _ANCHOR.match(body)
        if a:
            anchored.add(a.group(1))
    return listed, anchored


def scan_file(path: Path) -> list[str]:
    """对单个测试文件做清单对账, 返回人读 finding 列表(空 = 无漂移)。"""
    rel = path.name
    if rel in EXEMPT_FILES:
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    defs = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    }
    if not defs:
        return []
    doc = ast.get_docstring(tree)
    section = _plan_section(doc) if doc else []
    if not section:
        return [f"{rel}: 模块 docstring 缺「## 测试计划」段, {len(defs)} 条用例无对账清单"]
    listed, anchored = _listed_and_anchored(section)
    exempt = {name for file, name in EXEMPT_NAMES if file == rel}
    missing = sorted(defs - listed - exempt)
    ghosts = sorted(anchored - defs - exempt)
    findings = []
    if missing:
        findings.append(f"{rel}: {len(missing)} 条用例未列「## 测试计划」清单: {', '.join(missing)}")
    if ghosts:
        findings.append(f"{rel}: 幽灵条目(行首锚定但文件内无此 def): {', '.join(ghosts)}")
    return findings


def scan_repo() -> list[str]:
    """全仓扫描 tests/test_*.py(与 pytest 默认收集面 test_*.py 同口径)。"""
    findings: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        findings.extend(scan_file(path))
    return findings


# ---- 合成源红验样本(不是本文件用例, 守阵不扫描它们的内容) ----

SRC_MISSING = '''"""demo

## 测试计划

- test_a: 已登记条目
"""

def test_a():
    pass


def test_b():
    pass
'''

SRC_GHOST = '''"""demo

## 测试计划

- test_gone: 改名/删除后未清的条目
- test_a: 在
"""

def test_a():
    pass
'''

SRC_PROSE = '''"""demo

## 测试计划

说明段提及 test_a 不算登记(散文行), 也不因散文提及判幽灵。

- test_b: 真条目
"""

def test_a():
    pass


def test_b():
    pass
'''

SRC_COMPLETE = '''"""demo

## 测试计划(每个测试函数一条)

- **test_a**: 加粗装饰条目
- `test_b`: 反引号装饰条目
- [x] test_c: 勾选装饰条目
- 2. test_d: 序号条目
- test_a, test_e: 一行两名都算登记; 顺带提 test_zzz(文件内不存在, 行中提及不作幽灵判)
"""

def test_a():
    pass


def test_b():
    pass


def test_c():
    pass


def test_d():
    pass


def test_e():
    pass
'''

SRC_BOUNDARY = '''"""demo

## 测试计划

- test_a: 段内条目

## 附注

- test_b: 段外条目, 不认
"""

def test_a():
    pass


def test_b():
    pass
'''


def _write_and_scan(tmp_path: Path, source: str) -> list[str]:
    target = tmp_path / "demo.py"
    target.write_text(source, encoding="utf-8")
    return scan_file(target)


def test_scan_flags_missing_entry(tmp_path):
    findings = _write_and_scan(tmp_path, SRC_MISSING)
    assert len(findings) == 1 and "test_b" in findings[0] and "未列" in findings[0], findings


def test_scan_flags_ghost_entry(tmp_path):
    findings = _write_and_scan(tmp_path, SRC_GHOST)
    assert len(findings) == 1 and "test_gone" in findings[0] and "幽灵" in findings[0], findings


def test_scan_accepts_complete_plan_and_prose_mentions(tmp_path):
    assert _write_and_scan(tmp_path, SRC_COMPLETE) == []
    prose = _write_and_scan(tmp_path, SRC_PROSE)
    assert len(prose) == 1 and "test_a" in prose[0] and "未列" in prose[0], prose


def test_scan_section_boundary_and_decorations(tmp_path):
    boundary = _write_and_scan(tmp_path, SRC_BOUNDARY)
    assert len(boundary) == 1 and "test_b" in boundary[0], boundary
    assert _write_and_scan(tmp_path, SRC_COMPLETE) == []


def test_scan_exemptions(tmp_path, monkeypatch):
    monkeypatch.setitem(EXEMPT_NAMES, ("demo.py", "test_b"), "条目级豁免: 理由")
    assert _write_and_scan(tmp_path, SRC_MISSING) == []
    monkeypatch.setitem(EXEMPT_FILES, "demo.py", "文件级豁免: 理由")
    monkeypatch.delitem(EXEMPT_NAMES, ("demo.py", "test_b"))
    assert _write_and_scan(tmp_path, SRC_MISSING) == []


def test_repo_plan_matches_defs():
    findings = scan_repo()
    assert not findings, (
        "「## 测试计划」清单与实际用例漂移 —— 新增/改名/删除用例后请同步该文件头部清单"
        "(每条用例一行 `- test_用例名: 一句话`; 删除/改名用例时清掉或改名对应条目):\n" + "\n".join(findings)
    )
