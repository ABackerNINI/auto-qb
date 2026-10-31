"""文档形态守卫 (2026-09-24 随 plans/reports 入库 W4 落地; 协议见 memory-bank/conventions/doc-forms.md)。

守什么: 四形态协议里最贵的失败模式是「制品的登记与实体脱钩」—— 索引不是生成物、meta 缺失、
状态词漂移、dark 口径靠人眼、认领链只活在散文里。这些都是纯静态判定, 用测试守住成本极低。

范围: `memory-bank/plans/` 与 `memory-bank/reports/` 的 HTML 制品 + 两份生成物索引 + 跨形态专题视图
(查询 CLI `kb.docmap`, 2026-09-29 起 `_doc-map.md` 物化退役) + 四形态主键 (`doc-topic` / `**Topics:**`)
的覆盖与认领链。

## 测试计划

- test_plans_reports_have_no_md: `plans/` 与 `reports/` 里除 `_index.md` 外没有 `.md` (制品一律单文件 HTML)
- test_artifacts_meta_complete: 每份计划/报告的 `doc-*` meta 齐且 `doc-type` 与所在目录一致
- test_status_vocabulary: `doc-status` ∈ 5 词表 (`Open` / `In Progress` / `Done` / `Dropped` / `Superseded`)
- test_docs_index_rejects_unknown_status: 表外状态让 `gen_docs_index.build` fail-fast (不再静默漏收, 根因修复)
- test_docs_index_indexes_valid_status: 合法状态正常入索引 (防 fail-fast 过严)
- test_doc_map_flags_unknown_status: `gen_doc_map.check_status_vocabulary` 表外值退码 1 / 合法值与空值放行
- test_status_vocabulary_is_single_point: 生成器与守卫引用同一份 `_common.DOC_STATUSES` (不手抄副本)
- test_new_artifact_naming: `doc-added ≥ 26-09-24` 的新件必须带 type token (`YY-MM-DD-HHMM-<type>-<topic>.html`)
- test_artifacts_are_dark: 每份计划/报告都含 `color-scheme: dark` (dark 口径从人眼变机检)
- test_docs_index_is_regenerated: `plans|reports/_index.md` == `gen_docs_index.build()`
- test_doc_topics_complete: 四形态任一文档缺 `doc-topic` / `**Topics:**` 即红 (旧覆盖测试的补漏版)
- test_doc_map_live_rotation: 全完结专题在默认视图只留名 (轮转), `--all` 仍全量
- test_doc_map_name_list_never_splits_keys: 名录折行以专题名为原子, 含空格的复合键不被撕断 (2026-10-18)
- test_doc_map_flags_composite_topic_key: 逗号复合键 / 非 kebab 主键判红, 单 kebab 与空值放行; 真实语料零违例 (issue 26-10-18-0858 拍板②)
- test_issue_topics_present: 每条 issue 都有 `doc-topic` (否则会从专题视图里静默漏掉)
- test_claim_chain_is_bidirectional: 声明了 `doc-refs` / `**Refs:**` 的件, 目标必须存在且反向声明
- test_claim_chain_missing_target_hints_separator: ref 含视觉分隔符报「目标不存在」时, 报错自带英文逗号分隔提示 (issue 26-10-03-0746)

CLOSED_KEEP=60 索引出口 (计划 26-10-31-0534 R3/D14, 2026-10-31 加; plans 主索引的已完结区只留最近
60 条, 全量清单另落 `plans/attachments/_archive.md`; tasks 侧守阵在 test_memory_bank.py):

- test_docs_closed_keep_trims_plans_and_archives: plans Done 61 件 -> 主索引留最近 60 + 隐藏提示; 归档全量、只 plans 有、链接带 ../ 指回制品原文; 在办分区不受影响
- test_docs_closed_keep_reports_unaffected: reports 不动(D14) —— Done 61 件照旧全量出索引、无提示、无归档
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "memory-bank"
PLANS = MB / "plans"
REPORTS = MB / "reports"
ISSUES = MB / "issues"
SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"

# 5 词表单点在 skill 的 `_common.DOC_STATUSES` (生成器与守卫同源, 不手抄) —— 见 pitfalls/kb/doc-status-meta.md
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))
import _common  # noqa: E402
from _common import DOC_STATUSES as STATUSES  # noqa: E402

META_RE = re.compile(r'<meta name="(doc-[a-z]+)" content="([^"]*)">')
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


def test_doc_topics_complete() -> None:
    """主键纪律 (2026-09-29 随 `_doc-map.md` 物化退役重写): 四形态任一文档缺 doc-topic / **Topics:** 即红。

    旧「覆盖 100%」实现把声明过的 topic 集合对物化文本做 `t not in text` 判断, 空主键因
    `"" in text` 恒真被静默放过; 现在直接列出缺主键的文档。
    """
    gen = _load_generator("gen_doc_map")
    orphans = [f"{i['form']}: {i['link']}" for i in gen.collect(MB) if not i["topic"]]
    assert not orphans, "下列文档缺跨形态主键 (doc-topic / **Topics:**):\n  " + "\n  ".join(orphans)


def test_doc_map_live_rotation() -> None:
    """轮转口径: 活跃**多件**专题默认视图给全行; 全完结专题与单件专题只列名; `--all` 仍全量。"""
    gen = _load_generator("gen_doc_map")
    items = gen.collect(MB)
    live_text, all_text = gen.render_live(items), gen.render_all(items)
    for topic, group in gen.group_by_topic(items).items():
        has_line = f"- **{topic}**" in live_text
        if len(group) > 1 and gen.is_live(group):
            assert has_line, f"{topic} 有未完结件, 默认视图丢了全行"
        else:
            assert not has_line, f"{topic} 是单件或已完结, 默认视图不应有全行 (轮转失效)"
            assert topic in live_text, f"{topic} 连名录里都没有 (覆盖断裂)"
        assert topic in all_text, f"{topic} 未出现在 --all 全量视图"


def test_doc_map_name_list_never_splits_keys() -> None:
    """名录折行以专题名为原子: 含空格的复合键拼到折行边界也不得从中间撕断 (2026-10-18)。

    旧按字节位 rfind 折行会把 "topic-alpha, topic-beta" 撕成两行, 使 `topic in live_text`
    判定与 --topic 跳转失效; 触发条件是名录长度 (任何新增单件专题名都可能推动边界)。
    """
    gen = _load_generator("gen_doc_map")
    filler = "a" * (gen.NAME_WRAP - 5)  # 占位到边界前, 迫使折行落在复合键上
    lines = gen._name_list([filler, "topic-alpha, topic-beta", "tail"])
    text = "\n".join(lines)
    assert "topic-alpha, topic-beta" in text
    assert len(lines) >= 2  # 确实发生了折行, 不是没折


def test_doc_map_flags_composite_topic_key() -> None:
    """主键形态纪律 (2026-10-18, issue 26-10-18-0858 拍板②): 逗号复合键 / 非 kebab 判红, 单 kebab 与空值放行。

    拍板②(维持单主键口径, 生成器不拆键)后, 机检单点下沉到 gen_doc_map.check_topic_key_shape ——
    与认领链 (2026-10-03)、状态词表 (2026-10-16) 同款路径: 校验只活在 pytest 时, 纯文档轮
    (test.quick 闸门 match 只盯 src/tests) 会漏。tasks 的 `**Topics:**` 与四形态 `doc-topic`
    同一正则; 空值 (缺主键) 归 check_topics 管, 本函数只判形态。存量 8 份已于同轮回归单主键,
    真实语料必须零违例。
    """
    gen = _load_generator("gen_doc_map")
    base = {"form": "task", "topic": "t", "status": "Done", "stamp": "26-10-18-1010", "title": "t"}
    bad = {**base, "link": "tasks/x.md", "topic": "webui-detail-panel-redesign, webui-drawer-templates"}
    assert gen.check_topic_key_shape([bad]) == 1, "逗号复合键必须判红"
    ok = {**base, "link": "tasks/y.md", "topic": "webui-detail-table-rebuild"}
    empty = {**base, "link": "tasks/z.md", "topic": ""}
    assert gen.check_topic_key_shape([ok, empty]) == 0, "单 kebab 与空值(归 check_topics)应放行"
    real = [
        f"{i['form']}: {i['link']} → {i['topic']!r}"
        for i in gen.collect(MB) if i["topic"] and not gen.KEBAB_RE.fullmatch(i["topic"])
    ]
    assert not real, "真实语料仍有非 kebab 主键:\n  " + "\n  ".join(real)


def test_issue_topics_present() -> None:
    """issue 缺 `doc-topic` 会从专题视图里静默漏掉 —— 与 plans/reports/tasks 同一条主键纪律。"""
    missing = [p.name for p in sorted(ISSUES.glob("*.html")) if not _meta(p).get("doc-topic")]
    assert not missing, "下列 issue 缺 doc-topic:\n  " + "\n  ".join(missing)


def test_claim_chain_is_bidirectional() -> None:
    """认领链 (issue ↔ 档案 ↔ 计划) 双向可查: 声明了引用就必须被反向声明, 缺链即红。

    2026-10-03 机检单点下沉到 gen_doc_map.check_claim_chain —— 此前校验只活在 pytest, 纯文档轮
    (test.quick 闸门 match 只盯 src/tests) 的单向链一路绿灯入库 (657366c3, 见
    issues/26-10-03-0521); 下沉后提交闸门 (gen_doc_map --check) 全轮次覆盖, 本测试与其同源复验。
    声明方 = 四形态全量 (旧实现漏扫 issue 声明方); 只校验**声明过引用**的件, 未声明天然豁免。
    """
    gen = _load_generator("gen_doc_map")
    problems = gen.check_claim_chain(gen.collect(MB), ROOT, MB)
    assert not problems, "认领链不闭环:\n  " + "\n  ".join(problems)


def test_claim_chain_missing_target_hints_separator() -> None:
    """ref 含视觉分隔符时报错必须自带「英文逗号分隔」提示 —— 解析只认逗号, 但报错要自解释 (issue 26-10-03-0746)。"""
    gen = _load_generator("gen_doc_map")
    base = {"form": "issue", "topic": "t", "status": "Open", "stamp": "26-10-03-0746", "title": "t"}
    sep_item = {**base, "link": "issues/x.html", "refs": ["memory-bank/plans/a.html · memory-bank/plans/b.html"]}
    problems = gen.check_claim_chain([sep_item], ROOT, MB)
    assert len(problems) == 1, f"视觉分隔符 case 应恰好报一条: {problems}"
    assert "视觉分隔符" in problems[0] and "英文逗号" in problems[0], problems[0]
    plain_item = {**base, "link": "issues/x.html", "refs": ["memory-bank/plans/no-such-file.html"]}
    problems = gen.check_claim_chain([plain_item], ROOT, MB)
    assert len(problems) == 1, f"普通断链 case 应恰好报一条: {problems}"
    assert "视觉分隔符" not in problems[0], problems[0]


# --------------------------------------------------------------------------- 状态词表 fail-fast 守阵

_ARTIFACT_TMPL = (
    "<html><head>"
    '<meta name="doc-type" content="{kind}">'
    '<meta name="doc-topic" content="t">'
    '<meta name="doc-status" content="{status}">'
    '<meta name="doc-added" content="26-10-16-0021">'
    '<meta name="doc-updated" content="26-10-16-0021">'
    "<title>t</title></head><body></body></html>"
)


def _fake_artifact(mb: Path, kind: str, status: str) -> Path:
    directory = mb / f"{kind}s"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"26-10-16-0021-{kind}-x.html"
    path.write_text(_ARTIFACT_TMPL.format(kind=kind, status=status), encoding="utf-8")
    return path


def test_docs_index_rejects_unknown_status(tmp_path: Path) -> None:
    """表外状态不再静默漏收: `gen_docs_index.build` fail-fast (根因修复, 见 pitfalls/kb/doc-status-meta.md)。"""
    gen = _load_generator("gen_docs_index")
    mb = tmp_path / "memory-bank"
    _fake_artifact(mb, "plan", "Draft")
    with pytest.raises(gen.StatusVocabularyError):
        gen.build(tmp_path, mb)


def test_docs_index_indexes_valid_status(tmp_path: Path) -> None:
    """合法状态正常入索引 —— 防 fail-fast 过严把好件也拦下。"""
    gen = _load_generator("gen_docs_index")
    mb = tmp_path / "memory-bank"
    _fake_artifact(mb, "plan", "Open")
    rendered = gen.build(tmp_path, mb)
    assert "26-10-16-0021-plan-x.html" in rendered["plans"]


def test_doc_map_flags_unknown_status() -> None:
    """提交闸门侧的词表校验 (B 补强): 表外值退码 1, 合法值与空值放行。"""
    gen = _load_generator("gen_doc_map")
    ok = {"form": "plan", "status": "Open", "link": "plans/a.html", "topic": "t"}
    blank = {"form": "plan", "status": "", "link": "plans/a.html", "topic": "t"}
    draft = {"form": "plan", "status": "Draft", "link": "plans/a.html", "topic": "t"}
    fixed = {"form": "issue", "status": "Fixed", "link": "issues/b.html", "topic": "t"}
    assert gen.check_status_vocabulary([ok]) == 0
    assert gen.check_status_vocabulary([blank]) == 0
    assert gen.check_status_vocabulary([draft]) == 1
    assert gen.check_status_vocabulary([fixed]) == 1


def test_status_vocabulary_is_single_point() -> None:
    """5 词表只有 `_common.DOC_STATUSES` 一处 —— 生成器与守卫 import 同一对象, 不手抄副本。"""
    assert _load_generator("gen_docs_index").DOC_STATUSES is _common.DOC_STATUSES
    assert _load_generator("gen_doc_map").DOC_STATUSES is _common.DOC_STATUSES
    assert STATUSES is _common.DOC_STATUSES


# --------------------------------------------------------------------------- CLOSED_KEEP 出口
# (计划 26-10-31-0534 R3/D14, 2026-10-31 加: plans 主索引的已完结区只留最近 `CLOSED_KEEP` 条,
# 全量清单另落 `plans/attachments/_archive.md`; **reports 不动**。tasks 侧守阵在
# tests/test_memory_bank.py; 阈值/在办不裁等语义的细粒度红验在那边, 这里守制品目录自己的面。)


def _closed_keep_docs_fixture(tmp_path: Path, kind: str, done: int, inflight: int = 0) -> tuple[Path, Path]:
    """`done` 件 Done + `inflight` 件 In Progress 的制品夹具; doc-added 时间戳逐件递增(排序键可辨)。"""
    mb = tmp_path / "memory-bank"
    (mb / "plans").mkdir(parents=True, exist_ok=True)
    (mb / "reports").mkdir(parents=True, exist_ok=True)
    n = 0
    for status, count in (("Done", done), ("In Progress", inflight)):
        for _ in range(count):
            n += 1
            stamp = f"26-01-01-{n:04d}"
            (mb / f"{kind}s" / f"26-01-01-{n:04d}-{kind}-closed-keep-{n:03d}.html").write_text(
                "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
                f"<title>CLOSED_KEEP {kind} {n:03d}</title>\n"
                f'<meta name="doc-type" content="{kind}">\n'
                f'<meta name="doc-topic" content="closed-keep-{n:03d}">\n'
                f'<meta name="doc-status" content="{status}">\n'
                f'<meta name="doc-added" content="{stamp}">\n'
                f'<meta name="doc-updated" content="{stamp}">\n'
                "</head>\n<body>x</body>\n</html>\n",
                encoding="utf-8",
                newline="\n",
            )
    return tmp_path, mb


def _docs_index_section(text: str, status: str) -> str:
    m = re.search(rf"^## {re.escape(status)}\n\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, f"索引缺状态分区 `## {status}`"
    return m.group(1)


def test_docs_closed_keep_trims_plans_and_archives(tmp_path: Path) -> None:
    """plans 的 Done 61 件 -> 主索引只留最近 60 条 + 隐藏提示; 归档全量、落 `plans/attachments/_archive.md`。"""
    gen = _load_generator("gen_docs_index")
    root, mb = _closed_keep_docs_fixture(tmp_path, "plan", done=61, inflight=2)

    rendered = gen.build(root, mb)["plans"]
    done_section = _docs_index_section(rendered, "Done")
    entries = [line for line in done_section.splitlines() if line.startswith("- ")]
    assert len(entries) == 60, "Done 区只保留最近 60 条"
    assert "closed-keep-061" in done_section and "closed-keep-001" not in done_section
    assert "> 更早的 **1** 条已出本索引" in done_section
    inflight_section = _docs_index_section(rendered, "In Progress")
    assert "closed-keep-062" in inflight_section and "closed-keep-063" in inflight_section, "在办不受影响"

    archives = gen.build_archives(root, mb)
    assert set(archives) == {mb / "plans" / "attachments" / "_archive.md"}, "只 plans 有归档(reports 不动, D14)"
    archive = archives[mb / "plans" / "attachments" / "_archive.md"]
    assert "closed-keep-001" in archive and "closed-keep-061" in archive, "归档是全量"
    assert "](../26-01-01-0001-plan-closed-keep-001.html)" in archive, "归档链接带 ../ 指回制品原文"


def test_docs_closed_keep_reports_unaffected(tmp_path: Path) -> None:
    """reports 不动(D14): Done 61 件照旧全量出索引、无隐藏提示、无归档 —— 出口对它零行为变化。"""
    gen = _load_generator("gen_docs_index")
    root, mb = _closed_keep_docs_fixture(tmp_path, "report", done=61)

    rendered = gen.build(root, mb)["reports"]
    done_section = _docs_index_section(rendered, "Done")
    entries = [line for line in done_section.splitlines() if line.startswith("- ")]
    assert len(entries) == 61, "reports 全量出索引"
    assert "更早的" not in rendered, "无隐藏提示"
    assert "> **已完结状态**" not in rendered, "reports 头部不出 CLOSED_KEEP 说明行"
    assert set(gen.build_archives(root, mb)) == {mb / "plans" / "attachments" / "_archive.md"}, \
        "归档集合里只有 plans( reports 不动, D14)"
