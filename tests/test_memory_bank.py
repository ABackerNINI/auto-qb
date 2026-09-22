"""Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
一旦索引与档案脱钩 (登记了没文件 / 有文件没登记)、状态分区与档案 `Status` 不一致、
必备章节缺失, 下次会话就无法从 `tasks/` 续作; 一旦会话纪要回流进 `activeContext.md`,
该文件会重新膨胀成流水账 (2026-09-17 复盘的真实故障)。这些判定都是纯静态的, 用测试守住成本极低。

2026-09-18 起档案命名由 `TASKnnn-<slug>.md` 改为 `YY-MM-DD-<slug>.md`(全局序号在 9 个并行
worktree 下必然撞号)。本文件在兼容期内同时接受两种命名, 主键一律取"去掉编号 / 日期前缀后的 slug"。

## 测试计划

- test_tasks_index_and_files_are_bijective: `_index.md` 登记的键与 `tasks/*.md` 文件双向一致
- test_slug_is_unique_ignoring_date_prefix: 去掉日期 / 编号前缀后 slug 唯一 + 索引同键只登记一次 (防并行分支同专题两份档案)
- test_task_file_naming_and_sections: 文件名符合 `YY-MM-DD-<slug>.md`(兼容旧 `TASKnnn-<slug>.md`), 且五个必备章节齐全
- test_task_status_matches_index_section: 档案 `**Status:**` 与索引所在分区一致
- test_index_has_all_status_sections: 索引保留四个状态分区标题
- test_index_is_regenerated: `_index.md` == memory-bank skill 的 `gen_tasks_index.py` 生成结果
- test_active_context_has_no_rolled_up_session_log: `activeContext.md` 不出现 `^- 2026-` 流水账纪要行
- test_session_protocol_is_exposed_in_always_on_entries: skill 载体存在且含阈值/DoD, AGENTS 与 copilot-instructions 均声明阈值并指向 skill

知识库目录化守卫 (检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 进程内 import):

- test_kb_index_is_regenerated / test_kb_index_and_files_are_bijective: 索引 == 生成结果; 索引与目录双向一致
- test_kb_topic_files_have_metadata / test_kb_files_respect_caps / test_kb_class_names_and_topic_filenames: 三行头元数据 / cap 分级 / 类名与文件名
- test_kb_no_orphan_index_dirs / test_kb_stubs_are_valid: 顶层索引都被 README 引用; 被拆文档留合法存根
- test_kb_pitfall_entries_have_required_fields: pitfalls 条目含 触发 / 判别 / 处置
- test_kb_active_context_within_cap: `activeContext.md` ≤12 KB (易变层硬顶)
- test_kb_task_archives_within_cap: `tasks/*.md` ≤24 KB (超了移 `tasks/attachments/`)
- test_doc_links_are_not_broken: 全库相对链接存在性 (检查器 `scripts/check_doc_links.py`)
- test_kb_scripts_import_cleanly: skill 的 4 个脚本都能 import
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "memory-bank"
TASKS = MB / "tasks"
INDEX = TASKS / "_index.md"
SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"
GEN = SKILL_SCRIPTS / "gen_tasks_index.py"
SKILL = ROOT / ".agents" / "skills" / "memory-bank" / "SKILL.md"

STATUSES = ("In Progress", "Pending", "Completed", "Abandoned")
REQUIRED_SECTIONS = ("## 原始请求", "## 思考过程与决策", "## 实现计划", "## 子任务状态表", "## 进度日志")

DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")
LEGACY_PREFIX_RE = re.compile(r"^TASK\d{3}-")
FILE_RE = re.compile(r"^(?:TASK\d{3}-|\d{2}-\d{2}-\d{2}-)[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
INDEX_ID_RE = re.compile(r"- \[(TASK\d{3}|\d{2}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*)\]")
STATUS_RE = re.compile(r"\*\*Status:\*\* (In Progress|Pending|Completed|Abandoned)")


def _task_files() -> list[Path]:
    return sorted(p for p in TASKS.glob("*.md") if not p.name.startswith("_"))


def _slug_of(path: Path) -> str:
    """去掉编号前缀 (`TASKnnn-`) 或日期前缀 (`YY-MM-DD-`) 后的专题 slug。"""
    stem = path.stem
    stem = LEGACY_PREFIX_RE.sub("", stem)
    return DATE_PREFIX_RE.sub("", stem)


def _indexed_sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            continue
        for key in INDEX_ID_RE.findall(line):
            sections[key] = current
    return sections


def test_tasks_index_and_files_are_bijective() -> None:
    indexed = set(_indexed_sections())
    on_disk = {path.stem for path in _task_files()}

    assert indexed == on_disk, (f"索引与档案文件不一致: 仅索引登记={sorted(indexed - on_disk)}, "
                                f"仅有文件={sorted(on_disk - indexed)}")


def test_slug_is_unique_ignoring_date_prefix() -> None:
    """并行 worktree 各自立档会产出重复: 同一专题两份档案 (2026-09-18 实测 TASK014/TASK015 逐字节相同)
    + 索引里重复登记。重复条目在 dict 式解析里会静默覆盖, 双向一致与状态分区两个守卫都发现不了,
    所以必须单独守。改名后同一专题在不同日期建档会产生不同文件名, 因此比对必须**忽略日期前缀**。"""
    slugs: dict[str, list[str]] = {}
    for path in _task_files():
        slugs.setdefault(_slug_of(path), []).append(path.name)
    dup_slugs = {slug: names for slug, names in slugs.items() if len(names) > 1}

    assert not dup_slugs, f"存在同 slug 的重复任务档案 (同一专题两份, 需合并): {dup_slugs}"

    indexed = INDEX_ID_RE.findall(INDEX.read_text(encoding="utf-8"))
    dup_ids = sorted({key for key in indexed if indexed.count(key) > 1})

    assert not dup_ids, f"索引中同一档案被重复登记: {dup_ids}"


def test_task_file_naming_and_sections() -> None:
    files = _task_files()
    assert files, "tasks/ 下没有任何任务档案"

    for path in files:
        assert FILE_RE.match(path.name), (f"任务文件名不符合 YY-MM-DD-<slug>.md (slug 为英文小写连字符): {path.name}")
        text = path.read_text(encoding="utf-8")
        assert STATUS_RE.search(text), f"{path.name} 缺少合法的 `**Status:**` 行"
        for section in REQUIRED_SECTIONS:
            # ❗必须锚到**行首标题**: `section in text` 会被正文里的字面量骗过 ——
            # 本档案的日志里正好写了"把 `## 进度日志` 标题丢了"这句, 于是缺章节也判绿(2026-09-22 实测)。
            assert re.search(rf"^{re.escape(section)}\s*$", text,
                             re.M), (f"{path.name} 缺少必备章节 `{section}`(须是行首的 `## ` 标题, 正文里提到不算)")


def test_task_status_matches_index_section() -> None:
    sections = _indexed_sections()
    for path in _task_files():
        match = STATUS_RE.search(path.read_text(encoding="utf-8"))
        assert match, f"{path.name} 缺少 `**Status:**`"
        assert sections[
            path.stem
        ] == match.group(1), (f"{path.name} 档案 Status={match.group(1)} 与索引分区 "
                              f"`## {sections[path.stem]}` 不一致")


def test_index_has_all_status_sections() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for status in STATUSES:
        assert f"## {status}" in text, f"_index.md 缺少状态分区 `## {status}`"


def test_index_is_regenerated() -> None:
    """`_index.md` 是生成物: 冲突不再靠人工合并, 而是"任一方重跑一次脚本"。
    本守卫保证磁盘上的索引确实是脚本产物, 而不是有人手改过。

    **不跑子进程**: 本项目测试禁止启动外部进程 (`tests/sidefx.py` 的 POPEN 记账会判越界),
    所以这里在进程内 import 生成器并比对渲染结果, 语义与 `--check` 一致。
    """
    assert GEN.exists(), "缺少 memory-bank skill 的 scripts/gen_tasks_index.py (索引将无法重建)"
    assert SKILL_SCRIPTS.is_dir(), "缺少 memory-bank skill 的 scripts/ (生成器将无法加载)"
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_tasks_index

    rendered = gen_tasks_index.build(ROOT, MB)
    current = INDEX.read_text(encoding="utf-8")

    assert current == rendered, "请运行 `python .agents/skills/memory-bank/scripts/gen_tasks_index.py` 重建索引"


def test_active_context_has_no_rolled_up_session_log() -> None:
    text = (MB / "activeContext.md").read_text(encoding="utf-8")
    leaked = [line[:60] for line in text.splitlines() if re.match(r"^- 2026-\d\d-\d\d:", line)]

    assert not leaked, f"activeContext.md 出现流水账纪要行 (应迁入 tasks/ 档案对应专题): {leaked}"


def test_session_protocol_is_exposed_in_always_on_entries() -> None:
    assert SKILL.exists(), "缺少 skill 载体 .agents/skills/memory-bank/SKILL.md (会话协议将无法被触发)"
    skill_text = SKILL.read_text(encoding="utf-8")
    for token in ("立档阈值", "收尾 DoD", "会话开始"):
        assert token in skill_text, f"SKILL.md 缺少 {token}"

    for entry in (ROOT / "AGENTS.md", ROOT / ".github" / "copilot-instructions.md"):
        text = entry.read_text(encoding="utf-8")
        assert "立档阈值" in text, f"{entry.name} 未声明立档阈值"
        assert ".agents/skills/memory-bank/SKILL.md" in text, f"{entry.name} 未指向 memory-bank skill"


# ---------------------------------------------------------------------------
# 知识库目录化守卫 (2026-09-22, 任务 26-09-22-memory-bank-dir-refactor)
#
# 检查器实现在 memory-bank skill 的 `scripts/check_kb_structure.py`, 这里**在进程内 import** 它 ——
# 本项目测试禁止起子进程 (`tests/sidefx.py` 的 POPEN 记账会判越界), 与 gen_tasks_index 同做法。
# cap 与类枚举常量单点定义在 skill 的 `_common.py`, 守卫 import 它, 不手抄。
#
# 这些守卫是**结构性**的: 目录还没建时它们空转通过, 一旦某个 `<文档>/` 落地就自动开始生效。
# 两个例外按波次启用 —— `activeContext.md` 的 12 KB 硬顶 (W4) 与 `tasks/*.md` 的 24 KB
# (W7) 都在 `check_caps` 的默认角色集之外, 迁移完成后再纳入。
# ---------------------------------------------------------------------------


def _kb_checker():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_kb_structure

    return check_kb_structure


def test_kb_index_is_regenerated() -> None:
    """每个索引目录的 `_index.md` == 生成结果 (索引是生成物, 冲突靠重跑, 不手改)。"""
    problems = _kb_checker().check_index_regenerated(ROOT, MB)
    assert not problems, ("请运行 `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 重建:\n" + "\n".join(problems))


def test_kb_index_and_files_are_bijective() -> None:
    """索引 ↔ 目录内容双向一致: 有文件没登记、登记了没文件, 都红。"""
    problems = _kb_checker().check_bijection(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_topic_files_have_metadata() -> None:
    """每个主题文件与 `_about.md` 都含三行头元数据 —— 生成器的数据源, 缺了索引行就是空的。"""
    problems = _kb_checker().check_metadata(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_files_respect_caps() -> None:
    """每个文件 ≤ 其角色的 cap (角色策略单点在 skill 的 `_common.CAP_POLICY`)。"""
    problems, _warns = _kb_checker().check_caps(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_class_names_and_topic_filenames() -> None:
    """类名 ∈ 固定枚举; 主题文件名匹配 `^[a-z0-9]+(-[a-z0-9]+)*\\.md$`。"""
    problems = _kb_checker().check_names(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_no_orphan_index_dirs() -> None:
    """每个顶层 `_index.md` 都被 memory-bank/README.md 引用 (新增目录忘了登记就红)。"""
    problems = _kb_checker().check_orphan_indexes(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_stubs_are_valid() -> None:
    """被拆文档的原路径必须是 ≤1 KB 存根 (含「已迁至」、不含正文) —— 护住 400+ 处历史引用。"""
    problems = _kb_checker().check_stubs(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_pitfall_entries_have_required_fields() -> None:
    """pitfalls 条目含 触发 / 判别 / 处置 三必填字段 (`- **触发**: …`)。"""
    problems = _kb_checker().check_pitfall_entries(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_active_context_within_cap() -> None:
    """`activeContext.md` ≤12 KB —— 易变层硬顶: 超了就是内容该外迁的信号, 不是「这次先写着」。

    2026-09-17 那次复盘(纪要回流成流水账, 文件膨胀 10 倍)从教训变成机制, 靠的就是这条。
    """
    problems = _kb_checker().check_active_context_cap(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_task_archives_within_cap() -> None:
    """任务档案 ≤24 KB(其中「历史会话纪要」段 ≤8 KB) —— 超了把纪要段 / 较早日志移 `tasks/attachments/`。

    `attachments/` 是**子目录**而不是平铺: 索引守卫按 `tasks/*.md` 扫描**不递归**, 故附件天然不被当档案。
    """
    problems, _warns = _kb_checker().check_caps(ROOT, MB, ("task", ))
    assert not problems, "\n".join(problems)


def test_doc_links_are_not_broken() -> None:
    """全库**相对链接存在性** —— 改名 / 搬家后的坏链不会让任何测试失败, 只能机检。

    知识库目录化重构一次新增/改写了 400+ 处相对链接; 这条守卫把"改文件名后必须查全仓引用"
    从人工扫变成可自动跑的判据(实测首跑就抓出 73 处坏链, 全是搬家导致的相对深度错位)。
    检查器在 `scripts/check_doc_links.py`, **进程内 import**(本项目测试禁止起子进程)。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_doc_links", ROOT / "scripts" / "check_doc_links.py")
    assert spec and spec.loader, "缺少 scripts/check_doc_links.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    broken = module.scan_all(ROOT)
    assert not broken, "相对链接坏链:\n" + "\n".join(f"  {p}:{n} → {t}" for p, n, t in broken)


def test_kb_scripts_import_cleanly() -> None:
    """skill 的 4 个脚本都能被 import —— 模块级错误在这里当场红, 不必等闸门跑 `--help`。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    for name in ("_common", "gen_tasks_index", "gen_kb_index", "check_kb_structure"):
        path = SKILL_SCRIPTS / f"{name}.py"
        assert path.is_file(), f"缺少 {path.relative_to(ROOT)}"
        __import__(name)
