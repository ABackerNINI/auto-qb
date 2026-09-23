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
- test_active_context_has_no_rolled_up_session_log: 流水账只许住在 `activeContext/` 切片里, `activeContext.md` 本体不得出现 `^- 2026-` 行
- test_session_protocol_is_exposed_in_always_on_entries: skill 载体存在且含阈值/DoD, AGENTS 与 copilot-instructions 均声明阈值并指向 skill

知识库目录化守卫 (检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 进程内 import):

- test_kb_index_is_regenerated / test_kb_index_and_files_are_bijective: 索引 == 生成结果; 索引与目录双向一致
- test_kb_topic_files_have_metadata / test_kb_files_respect_caps / test_kb_class_names_and_topic_filenames: 三行头元数据 / cap 分级 / 类名与文件名
- test_kb_no_orphan_index_dirs / test_kb_stubs_are_valid: 顶层索引都被 README 引用; 被拆文档留合法存根
- test_kb_pitfall_entries_have_required_fields: pitfalls 条目含 触发 / 判别 / 处置
- test_kb_active_context_within_cap: `activeContext.md` 是 ≤1 KB 合法存根 (2026-09-23 起滚动状态已迁 `activeContext/`)
- test_kb_active_context_slices_are_valid: 切片命名定宽 / 三行头齐 / 每个 ≤ 切片 cap / 总数 ≤ 阈值
- test_kb_task_archives_within_cap: `tasks/*.md` ≤24 KB (超了移 `tasks/attachments/`)
- test_doc_links_are_not_broken: 全库相对链接存在性 (检查器 `scripts/check_doc_links.py`)
- test_memory_bank_instructions_match_current_structure: `memory-bank.instructions.md` 与当前结构一致 (2026-09-23 瘦身后针列表同步换过)
- test_skill_cap_table_matches_cap_policy: SKILL.md 的 cap 表数值集合 == `_common.CAP_POLICY` (防手抄表漂移)
- test_kb_scripts_import_cleanly: skill 的 5 个脚本都能 import
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

STATUSES = ("In Progress", "Open", "Done", "Dropped")

# `memory-bank/activeContext/` 切片数上限 —— 切片无界增长是这个方案的已知代价, 给个可判定的收口线
SLICE_COUNT_LIMIT = 40
REQUIRED_SECTIONS = ("## 原始请求", "## 思考过程与决策", "## 实现计划", "## 子任务状态表", "## 进度日志")

DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")
LEGACY_PREFIX_RE = re.compile(r"^TASK\d{3}-")
FILE_RE = re.compile(r"^(?:TASK\d{3}-|\d{2}-\d{2}-\d{2}-)[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
INDEX_ID_RE = re.compile(r"- \[(TASK\d{3}|\d{2}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*)\]")
STATUS_RE = re.compile(r"\*\*Status:\*\* (In Progress|Open|Done|Dropped)")


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
    """滚动状态只许住在 `activeContext/` 切片里 —— `activeContext.md` 本体不得再出现流水账行。

    2026-09-23 语义重定义: 切片**本来就是**流水账(每专题一条时间线), 所以「禁止流水账」这条
    只对 `activeContext.md` 成立 —— 在切片化之后, 原判据(查 `^- 2026-`)会变成**恒绿**
    (存根里不可能有这种行), 恒绿的守卫等于没守。切片侧的膨胀风险改由
    `test_kb_active_context_slices_are_valid` 的 cap 与条数阈值接管。
    """
    text = (MB / "activeContext.md").read_text(encoding="utf-8")
    leaked = [line[:60] for line in text.splitlines() if re.match(r"^- 2026-\d\d-\d\d:", line)]

    assert not leaked, f"activeContext.md 出现流水账纪要行 (应写进 activeContext/ 切片): {leaked}"
    assert (MB / "activeContext").is_dir(), "activeContext/ 切片目录缺失 —— 滚动状态没有归宿"


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
    """`activeContext.md` 必须是**合法存根**(≤1 KB + 含「已迁至」+ 无正文), 不是一份被硬顶卡住的正文。

    2026-09-23 目录化后语义变了: 旧的 12 KB「易变层硬顶」已失去对象 —— 滚动状态搬进
    `activeContext/` 切片, 原路径只留指针。所以改判存根合法性(与 `check_stubs` 同源);
    那个 12 KB 数字不再是这一层的问题, 切片各自的 cap 见下一条。
    """
    ok, why = _kb_checker().is_stub(MB / "activeContext.md")
    assert ok, f"activeContext.md 不是合法存根: {why}"


def test_kb_active_context_slices_are_valid() -> None:
    """切片命名定宽 / 三行头齐 / 每个 ≤ 切片 cap / 总数 ≤ 阈值 —— 防目录无界膨胀。

    切片是「每会话重写文件头同一段」的替代物: 冲突在结构上消掉了, 代价是文件数不再有界
    (初稿按 clone 拆是 4+N 个)。所以把「该归档了」变成可判定的数字, 而不是靠自觉。
    """
    checker = _kb_checker()
    import gen_active_recent

    slice_dir = MB / "activeContext"
    assert slice_dir.is_dir(), "缺少 memory-bank/activeContext/ 切片目录"
    rows, problems = gen_active_recent.collect(slice_dir, ROOT)
    assert not problems, "\n".join(problems)
    assert checker.role_of("memory-bank/activeContext/x.md") == "slice", "切片路径未被 _common.role_of 认成 slice 角色"
    assert rows, "切片目录是空的 —— 滚动状态没有归宿"
    assert len(rows
              ) <= SLICE_COUNT_LIMIT, (f"切片数 {len(rows)} > {SLICE_COUNT_LIMIT} —— 把 14 天未动的切片蒸馏进 progress/ 或任务档案后删除")


def test_kb_task_archives_within_cap() -> None:
    """任务档案 ≤24 KB(其中「历史会话纪要」段 ≤8 KB) —— 超了把纪要段 / 较早日志移 `tasks/attachments/`。

    `attachments/` 是**子目录**而不是平铺: 索引守卫按 `tasks/*.md` 扫描**不递归**, 故附件天然不被当档案。
    """
    problems, _warns = _kb_checker().check_caps(ROOT, MB, ("task", ))
    assert not problems, "\n".join(problems)


def test_memory_bank_instructions_match_current_structure() -> None:
    """`applyTo: memory-bank/**` 的规则载体必须与**当前结构**一致。

    为什么值得单独钉: 它只在**编辑 `memory-bank/` 时**注入 —— 不重写的话, 目录化重构后的新结构
    在改库那一刻**根本不在上下文里**, 于是又会按旧的 8 文件结构去写。2026-09-22 重写前的旧版
    还在教「read ALL memory bank files at the start of every task」—— 那正是本库膨胀到 50 万字符的原因。

    2026-09-23 瘦身: 4,213 → 2,486 字符(106 → 55 行)。删掉的四节(cap 分级表 / 三行头模板 / pitfalls 字段 /
    任务档案格式)**都在 skill 与 `_common.py` 有单点**, 而其中 cap 表是**数值型重复** —— 守卫只钉
    token 不钉数值, 改了源不会红。所以针列表同步换掉了 `## 原始请求` / `## 进度日志`(那是 skill
    里「任务档案规范」的内容), 换成 `CAP_POLICY`(证明它指向机器单点而不是自己抄一张表)。
    ⚠ **不要退回成"纯指针"**: 本文件是**自动注入**, 而 skill 是**按需触发**加载 —— 纯指针会让
    规则从「可见」退化成「可触达」, 而这三条铁律对应的失败模式恰恰是"少做一个动作"。
    """
    path = ROOT / ".github" / "instructions" / "memory-bank.instructions.md"
    assert path.is_file(), "缺少 memory-bank.instructions.md"
    text = path.read_text(encoding="utf-8")

    # 不能直接查 "read ALL memory bank files": 本文件**引用了这句当反例**并标注废弃,
    # 子串必然存在 —— 第一版守卫就是这么自己把自己判红的(与「os.path.normcase 写在
    # docstring 里当反例」是同一类坑)。改查旧版**祈使句的独有尾巴**。
    assert "this is not optional" not in text, ("旧版反模式的祈使句回潮了: 必须改成「先索引、后 grep、禁止整读」")
    assert "已废弃" in text, "引用旧反模式时必须同时标注它已废弃"
    for needle in (
        "applyTo: 'memory-bank/**'",  # 仍是规则载体(机制本身, 不能外迁)
        "先索引、后 grep、禁止整读",  # 检索纪律: 最贵的失败模式, 必须在手边
        "生成物",  # _index.md 不许手改
        ".agents/skills/memory-bank/SKILL.md",  # 指向完整规程
        "CAP_POLICY",  # cap 的机器单点 —— 2026-09-23 瘦身: 不再在这里抄一张会漂移的表
        "activeContext.md",
        "gen_active_recent.py",
    ):
        assert needle in text, f"memory-bank.instructions.md 缺少 `{needle}`"


def test_skill_cap_table_matches_cap_policy() -> None:
    """SKILL.md 的 cap 表必须与 `_common.CAP_POLICY` 的**数值集合**一致 —— 手抄的表会静默漂移。

    2026-09-23 加这条的现场: 给 `CAP_POLICY` 加 `slice = 6,000` 时, SKILL.md 与
    `.github/instructions/memory-bank.instructions.md` 里**两张** cap 表都是手工同步的,
    而当时没有任何守卫盯数值 —— 改了源、忘了表, 全绿。瘦身后那张重复表已删, 剩这一张被钉住。

    ⚠ 只比**数值多集合 + 行数**: 能判红「改了源没改表」与「少写一行」, **判不出**「两行数值互换角色」
    —— 后者只能靠人读表, 这里不假装守得住。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    text = SKILL.read_text(encoding="utf-8")
    nums = [int(n.replace(",", "")) for n in re.findall(r"^\|[^|\n]*\|\s*([\d,]+)\s*\|\s*$", text, re.MULTILINE)]

    assert nums, "SKILL.md 里找不到 cap 表 —— 改结构时把这张表弄丢了?"
    assert len(nums) == len(_common.CAP_POLICY
                           ), (f"SKILL.md cap 表 {len(nums)} 行 != `_common.CAP_POLICY` {len(_common.CAP_POLICY)} 条")
    assert sorted(nums) == sorted(
        _common.CAP_POLICY.values()
    ), (f"SKILL.md cap 表与 `_common.CAP_POLICY` 漂移:\n  表: {sorted(nums)}\n  源: {sorted(_common.CAP_POLICY.values())}")


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
    """skill 的 5 个脚本都能被 import —— 模块级错误在这里当场红, 不必等闸门跑 `--help`。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    for name in ("_common", "gen_tasks_index", "gen_kb_index", "check_kb_structure", "gen_active_recent"):
        path = SKILL_SCRIPTS / f"{name}.py"
        assert path.is_file(), f"缺少 {path.relative_to(ROOT)}"
        __import__(name)
