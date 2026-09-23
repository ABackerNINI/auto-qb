"""文档形态守卫 (2026-09-24 随 plans/reports 入库 W4 落地; 协议见 memory-bank/conventions/doc-forms.md)。

守什么: 四形态协议里最贵的失败模式是「制品的登记与实体脱钩」—— 索引不是生成物、meta 缺失、
状态词漂移、dark 口径靠人眼、认领链只活在散文里。这些都是纯静态判定, 用测试守住成本极低。

范围: `memory-bank/plans/` 与 `memory-bank/reports/` 的 HTML 制品 + 两份生成物索引 + 跨形态专题视图
`_doc-map.md` + 四形态主键 (`doc-topic` / `**Topics:**`) 的覆盖与认领链。

## 测试计划

- test_plans_reports_have_no_md: `plans/` 与 `reports/` 里除 `_index.md` 外没有 `.md` (制品一律单文件 HTML)
- test_artifacts_meta_complete: 每份计划/报告的 `doc-*` meta 齐且 `doc-type` 与所在目录一致
- test_status_vocabulary: `doc-status` ∈ 5 词表 (`Open` / `In Progress` / `Done` / `Dropped` / `Superseded`)
- test_new_artifact_naming: `doc-added ≥ 26-09-24` 的新件必须带 type token (`YY-MM-DD-HHMM-<type>-<topic>.html`)
- test_artifacts_are_dark: 每份计划/报告都含 `color-scheme: dark` (dark 口径从人眼变机检)
- test_docs_index_is_regenerated: `plans|reports/_index.md` == `gen_docs_index.build()`
- test_doc_map_is_regenerated_and_capped: `_doc-map.md` == `gen_doc_map.build()` 且 ≤ `index-auto` cap
- test_doc_map_covers_every_topic: 四形态 topic 集合 ⊆ 专题视图里出现的 topic (覆盖 100%, 孤儿 0)
- test_issue_topics_present: 每条 issue 都有 `doc-topic` (否则会从专题视图里静默漏掉)
- test_claim_chain_is_bidirectional: 声明了 `doc-refs` / `**Refs:**` 的件, 目标必须存在且反向声明
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "memory-bank"
PLANS = MB / "plans"
REPORTS = MB / "reports"
ISSUES = MB / "issues"
TASKS = MB / "tasks"
SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"

STATUSES = ("Open", "In Progress", "Done", "Dropped", "Superseded")
META_RE = re.compile(r'<meta name="(doc-[a-z]+)" content="([^"]*)">')
TASK_TOPICS_RE = re.compile(r"^\*\*Topics:\*\*\s*(.+)$", re.MULTILINE)
TASK_REFS_RE = re.compile(r"^\*\*Refs:\*\*\s*(.+)$", re.MULTILINE)
HTML_REFS_RE = re.compile(r'<meta name="doc-refs" content="([^"]*)">')
# 命名协议从 2026-09-24 起对新件生效; 存量 51 份豁免 (改名引用面远超收益 —— 见计划 §03)
NAMING_FROM = "26-09-24"
NEW_NAME_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-(?:plan|report)-[a-z0-9]+(?:-[a-z0-9]+)*\.html$")

KIND_DIRS = {"plan": PLANS, "report": REPORTS}


def _artifacts() -> list[Path]:
    out: list[Path] = []
    for directory in (PLANS, REPORTS):
        out.extend(sorted(p for p in directory.glob("*.html")))
    return out


def _meta(path: Path) -> dict[str, str]:
    return dict(META_RE.findall(path.read_text(encoding="utf-8")))


def _topics_of_all_forms() -> dict[str, set[str]]:
    """四形态各自声明的 topic 集合 (键 = 形态)。"""
    topics: dict[str, set[str]] = {"plan": set(), "report": set(), "issue": set(), "task": set()}
    for path in _artifacts():
        meta = _meta(path)
        if meta.get("doc-topic"):
            topics[meta["doc-type"]].add(meta["doc-topic"])
    for path in sorted(ISSUES.glob("*.html")):
        meta = _meta(path)
        if meta.get("doc-topic"):
            topics["issue"].add(meta["doc-topic"])
    for path in sorted(TASKS.glob("*.md")):
        if path.name.startswith("_"):
            continue
        match = TASK_TOPICS_RE.search(path.read_text(encoding="utf-8"))
        if match:
            topics["task"].add(match.group(1).strip())
    return topics


def _refs_of(path: Path) -> list[str]:
    """声明引用 (仓库根相对路径列表): HTML 读 `doc-refs` meta, MD 读 `**Refs:**` 行。"""
    text = path.read_text(encoding="utf-8")
    raw = ""
    if path.suffix == ".html":
        match = HTML_REFS_RE.search(text)
        raw = match.group(1) if match else ""
    else:
        match = TASK_REFS_RE.search(text)
        raw = match.group(1) if match else ""
    return [p.strip() for p in raw.split(",") if p.strip()]


def test_plans_reports_have_no_md() -> None:
    """`plans/` 与 `reports/` 是 HTML 制品目录 —— 出现 `.md` 即违规 (2026-09-15 存量违规已随 W1 清掉)。"""
    strays = [
        p.relative_to(ROOT).as_posix() for directory in (PLANS, REPORTS)
        for p in sorted(directory.glob("*.md")) if p.name != "_index.md"
    ]
    assert not strays, "制品目录里出现 .md (计划/报告一律单文件 HTML):\n  " + "\n  ".join(strays)


def test_artifacts_meta_complete() -> None:
    """`doc-*` meta 齐 (type / topic / status / added / updated) 且 `doc-type` 与目录一致。"""
    problems = []
    for path in _artifacts():
        meta = _meta(path)
        expected = "plan" if path.parent == PLANS else "report"
        for key in ("doc-type", "doc-topic", "doc-status", "doc-added", "doc-updated"):
            if not meta.get(key):
                problems.append(f"{path.name}: 缺 {key}")
        if meta.get("doc-type") and meta["doc-type"] != expected:
            problems.append(f"{path.name}: doc-type={meta['doc-type']} 与目录不符 (应为 {expected})")
    assert not problems, "制品 meta 不完整:\n  " + "\n  ".join(problems)


def test_status_vocabulary() -> None:
    """状态词只允许 5 词表 —— 双轨词 (Pending / Completed / Fixed / WontFix / Duplicate) 一律非法。"""
    bad = []
    for path in _artifacts():
        status = _meta(path).get("doc-status", "")
        if status not in STATUSES:
            bad.append(f"{path.name}: doc-status={status!r}")
    assert not bad, f"状态词不在 5 词表 {STATUSES} 内:\n  " + "\n  ".join(bad)


def test_new_artifact_naming() -> None:
    """2026-09-24 起的新件必须 `YY-MM-DD-HHMM-<type>-<topic>.html`; 存量按 `doc-added` 豁免。"""
    bad = []
    for path in _artifacts():
        added = _meta(path).get("doc-added", "")
        if added >= NAMING_FROM and not NEW_NAME_RE.match(path.name):
            bad.append(f"{path.name}: doc-added={added} 属新件, 命名须带 type token")
    assert not bad, "新件命名不合协议:\n  " + "\n  ".join(bad)


def test_artifacts_are_dark() -> None:
    """dark 口径 (`conventions/webui.md`) 从「靠人眼」变机检 —— 每份制品都要有 `color-scheme: dark`。"""
    bad = [path.name for path in _artifacts() if "color-scheme: dark" not in path.read_text(encoding="utf-8")]
    assert not bad, "下列制品缺 `color-scheme: dark`(dark 主题违规):\n  " + "\n  ".join(bad)


def _load_generator(name: str):
    """在进程内加载 skill 生成器 —— 本项目测试禁止起子进程 (`tests/sidefx.py` 会记账)。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    return __import__(name)


def test_docs_index_is_regenerated() -> None:
    """两份目录索引都是生成物: 冲突的解法是重跑, 不是人工合并两版文本。"""
    gen = _load_generator("gen_docs_index")
    rendered = gen.build(ROOT, MB)
    for kind, text in rendered.items():
        index = MB / kind / "_index.md"
        assert index.is_file(), f"缺少 {kind}/_index.md (跑 gen_docs_index.py 生成)"
        assert index.read_text(encoding="utf-8") == text, \
            f"{kind}/_index.md 与生成结果不一致, 请运行 gen_docs_index.py"


def test_doc_map_is_regenerated_and_capped() -> None:
    """专题视图是生成物, 且有上限 (`index-auto` 档) —— 它会随专题数增长, 不能无界。"""
    gen = _load_generator("gen_doc_map")
    target = MB / "_doc-map.md"
    assert target.is_file(), "缺少 _doc-map.md (跑 gen_doc_map.py 生成)"
    current = target.read_text(encoding="utf-8")
    assert current == gen.build(ROOT, MB), "_doc-map.md 与生成结果不一致, 请运行 gen_doc_map.py"

    common = _load_generator("_common")
    cap = common.CAP_POLICY["index-auto"]
    assert len(current) <= cap, f"_doc-map.md 超 cap: {len(current)} > {cap} (专题数增长时需要收口)"


def test_doc_map_covers_every_topic() -> None:
    """覆盖 100% / 孤儿 0: 四形态声明过的每个 topic 都必须出现在专题视图里。"""
    text = (MB / "_doc-map.md").read_text(encoding="utf-8")
    declared = {t for names in _topics_of_all_forms().values() for t in names}
    missing = sorted(t for t in declared if t not in text)
    assert not missing, "下列 topic 未出现在 _doc-map.md 里 (漏登记即静默孤儿):\n  " + "\n  ".join(missing)


def test_issue_topics_present() -> None:
    """issue 缺 `doc-topic` 会从专题视图里静默漏掉 —— 与 plans/reports/tasks 同一条主键纪律。"""
    missing = [p.name for p in sorted(ISSUES.glob("*.html")) if not _meta(p).get("doc-topic")]
    assert not missing, "下列 issue 缺 doc-topic:\n  " + "\n  ".join(missing)


def test_claim_chain_is_bidirectional() -> None:
    """认领链 (issue ↔ 档案 ↔ 计划) 双向可查: 声明了引用就必须被反向声明, 缺链即红。

    只校验**声明过引用**的件 —— 存量绝大多数不声明 `doc-refs` / `**Refs:**`, 天然豁免;
    新件按协议声明后自动进入校验。
    """
    problems = []
    checked = 0
    for path in list(_artifacts()) + [p for p in sorted(TASKS.glob("*.md")) if not p.name.startswith("_")]:
        refs = _refs_of(path)
        if not refs:
            continue
        checked += 1
        rel_self = path.relative_to(ROOT).as_posix()
        for ref in refs:
            target = ROOT / ref
            if not target.exists():
                problems.append(f"{rel_self}: 引用的目标不存在 → {ref}")
                continue
            if rel_self not in _refs_of(target):
                problems.append(f"{rel_self} → {ref}: 目标未反向声明本件 (认领链单向)")
    assert checked, "没有任何件声明引用 —— 认领链守阵失去校验对象"
    assert not problems, "认领链不闭环:\n  " + "\n  ".join(problems)
