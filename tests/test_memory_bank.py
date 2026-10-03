"""Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
一旦索引与档案脱钩 (登记了没文件 / 有文件没登记)、状态分区与档案 `Status` 不一致、
必备章节缺失, 下次会话就无法从 `tasks/` 续作; 一旦会话纪要回流进 `activeContext.md`,
该文件会重新膨胀成流水账 (2026-09-17 复盘的真实故障)。这些判定都是纯静态的, 用测试守住成本极低。

2026-09-18 起档案命名由 `TASKnnn-<slug>.md` 改为 `YY-MM-DD-<slug>.md`(全局序号在 9 个并行
worktree 下必然撞号)。本文件在兼容期内同时接受两种命名, 主键一律取"去掉编号 / 日期前缀后的 slug"。

2026-09-30 **cap 债务制**改造 (计划 `memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html`):
尺寸类 cap 从"提交前置条件"降级为**债务**(超限只是读起来更贵, 事实源完好) —— 除 `AGENTS.md`
(越过它发生的是 IDE 注入**截断**, 尾部对模型真不可见, 是硬规定, 超了仍拦)。所以本文件删掉了
对 KB 角色**现行文档尺寸**的断言, 换成「债务可发现性」断言: 造一个超限文件, 它必须被报成
warn 而不是 problem —— 守住"降级后的严重度仍然正确", 而不是"今天的文件恰好不超"。

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
- test_kb_topic_files_have_metadata / test_kb_files_respect_caps / test_kb_class_names_and_topic_filenames: 三行头元数据 / **硬规定** cap / 类名与文件名
- test_kb_no_orphan_index_dirs / test_kb_stubs_are_valid: 顶层索引都被 README 引用; 被拆文档留合法存根
- test_kb_pitfall_entries_have_required_fields: pitfalls 条目含 触发 / 判别 / 处置
- test_kb_active_context_within_cap: `activeContext.md` 是 ≤2 KB 合法存根 (2026-09-23 起滚动状态已迁 `activeContext/`)
- test_kb_active_context_slices_are_valid: 切片命名定宽 / 三行头齐 (结构); 尺寸与条数是**债务**, 不判红
- test_kb_cap_debt_is_discoverable_not_blocking: 造超限文件 → 必须报成 warn(债务) 而不是 problem
- test_agents_md_cap_is_hard_not_debt: AGENTS.md 超 8,000 仍是 problem(硬规定), 且不出现在债务清单里
- test_kb_slice_cap_and_count_are_debt_not_blocking: 切片尺寸 / 条数 → warns(债务); 命名 / 三行头仍判红
- test_kb_active_render_respects_byte_budget: kb.active 默认字节预算截取(30KB 内联上限), 页脚留总数, --all / -n N 逃生
- test_context_caps_hard_and_debt_split: `check_context_caps.py` 的 AGENTS.md 只在 `HARD_CAPS`、不进债务组
- test_doc_links_are_not_broken: 全库相对链接存在性 (检查器 `scripts/check_doc_links.py`)
- test_memory_bank_instructions_match_current_structure: `memory-bank.instructions.md` 与当前结构一致 (2026-09-23 瘦身后针列表同步换过)
- test_skill_cap_table_matches_cap_policy: SKILL.md 的 cap 表数值集合 == `_common.CAP_POLICY` (防手抄表漂移)
- test_kb_scripts_import_cleanly: skill 的脚本都能 import
- test_gen_all_declares_exactly_all_indexes: gen_all.py 的产出集合 == 库内全部 `_index.md`(生成物全集单点)
- test_gen_all_check_is_green: gen_all.py `--check` 在当前库上绿 (磁盘 == 生成结果)
- test_gen_all_list_matches_outputs: `--list` 声明的路径集合 == collect() 实际产出 (白名单不得多/少)
- test_gen_cmd_hints_name_real_tasks: 生成物的"怎么重建"提示必须指向真能重建它的命令(`gen_cmd` 按脚本查表 + `kb.index` 覆盖面 ⊇ 闸门判红的生成物集合, 经 gen_all.py 单点收编后按声明核对; 2026-09-24 `_doc-map.md` 报错文案指错命令的机检)
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
            # !必须锚到**行首标题**: `section in text` 会被正文里的字面量骗过 ——
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
    """**硬规定** cap 必须绿 —— 2026-09-30 债务制后, `check_caps` 的 problems 只剩这一类。

    尺寸类 cap 降级前后, 本用例的名字没变、语义变了: 它现在只拦 `HARD_CAP_ROLES`
    (唯一成员 `agents` = AGENTS.md —— 越过 8,000 是 IDE 注入**截断**, 尾部对模型真不可见)。
    其余角色的尺寸超限进了 warns(债务): 不拦提交, 由 `doc.caps` 在提交时现算并转告用户,
    清理另开会话 —— 判红的代价是在会话最贵的时刻逼出文档手术返工(计划 §01 根因)。
    """
    problems, _warns = _kb_checker().check_caps(ROOT, MB)
    assert not problems, "\n".join(problems)

    # 硬规定单点: AGENTS.md 的 8,000 不由本文件定义, 但"它必须仍在硬规定里"要钉住 ——
    # 万一有人把它搬进债务组, 上面那条 assert 会变成恒绿(AGENTS.md 超限也不再有人拦)。
    checker = _kb_checker()
    assert checker.HARD_CAP_ROLES == ("agents",
                                     ), (f"硬规定角色集变了: {checker.HARD_CAP_ROLES} —— AGENTS.md 的截断语义必须留在 problems 侧")
    agents_size = checker.char_count(ROOT / "AGENTS.md")
    assert agents_size <= checker.CAP_POLICY["agents"], (
        f"AGENTS.md {agents_size:,} 字符 > 硬上限 {checker.CAP_POLICY['agents']:,} —— "
        "超出部分注入时被 slice 掉, 必须就地削薄(不套 50% 收缩, 也没有挂账通道)"
    )


def test_kb_class_names_and_topic_filenames() -> None:
    """类名 ∈ 固定枚举; 主题文件名匹配 `^[a-z0-9]+(-[a-z0-9]+)*\\.md$`。"""
    problems = _kb_checker().check_names(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_no_orphan_index_dirs() -> None:
    """每个顶层 `_index.md` 都被 memory-bank/README.md 引用 (新增目录忘了登记就红)。"""
    problems = _kb_checker().check_orphan_indexes(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_stubs_are_valid() -> None:
    """被拆文档的原路径必须是 ≤2 KB 存根 (含「已迁至」、不含正文) —— 护住 400+ 处历史引用。"""
    problems = _kb_checker().check_stubs(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_pitfall_entries_have_required_fields() -> None:
    """pitfalls 条目含 触发 / 判别 / 处置 三必填字段 (`- **触发**: …`)。"""
    problems = _kb_checker().check_pitfall_entries(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_active_context_within_cap() -> None:
    """`activeContext.md` 必须是**合法存根**(≤2 KB + 含「已迁至」+ 无正文), 不是一份被硬顶卡住的正文。

    2026-09-23 目录化后语义变了: 旧的 12 KB「易变层硬顶」已失去对象 —— 滚动状态搬进
    `activeContext/` 切片, 原路径只留指针。所以改判存根合法性(与 `check_stubs` 同源);
    那个 12 KB 数字不再是这一层的问题, 切片各自的 cap 见下一条。
    """
    ok, why = _kb_checker().is_stub(MB / "activeContext.md")
    assert ok, f"activeContext.md 不是合法存根: {why}"


def test_kb_active_context_slices_are_valid() -> None:
    """切片命名定宽 / 三行头齐 —— 这两个是**结构**, 坏了就解析不了, 判红。

    尺寸与条数不再在本用例里判红(2026-09-30, D2 拍板归债务通道): 切片是「每会话重写文件头
    同一段」的替代物, 冲突在结构上消掉了, 代价是文件数不再有界 —— 但"该蒸馏了"与"切片的
    命名坏了"性质不同: 前者只是读起来更贵, 后者是事实源残缺。旧口径把它俩都判红, 实测后果是
    阈值(按 ~5 片/日校准的估计值)打满时, 逼出"为了过守卫而违规归档"(切片 26-09-30-2112 记的实例)。
    """
    checker = _kb_checker()
    import gen_active_recent

    slice_dir = MB / "activeContext"
    assert slice_dir.is_dir(), "缺少 memory-bank/activeContext/ 切片目录"
    rows, problems, _warns = gen_active_recent.collect(slice_dir, ROOT)
    assert not problems, "\n".join(problems)
    assert checker.role_of("memory-bank/activeContext/x.md") == "slice", "切片路径未被 _common.role_of 认成 slice 角色"
    assert rows, "切片目录是空的 —— 滚动状态没有归宿"


def test_kb_active_render_respects_byte_budget() -> None:
    """kb.active 默认按字节预算截取 —— AI 工具壳内联上限 30,000 字节 (pitfalls/ops/console-encoding.md)。

    切片 90+ 条后全量输出 ~51KB → 落盘 + 截断点切进多字节字符时预览整段乱码, 「全量」反而不可读。
    守四点: 预算内必停(按编码后字节计) / 收紧到只够一行也不许输出空表 / 页脚保留总数与省略数
    (截的是展示不是事实) / 不传预算(--all)仍全量。行内容是合成行, 不与现行切片数耦合。
    """
    from datetime import datetime, timedelta

    import gen_active_recent

    now = datetime(2026, 10, 2, 12, 0)

    def row(i: int) -> dict:
        when = datetime(2026, 1, 1) + timedelta(days=i)
        return {
            "rel": f"memory-bank/activeContext/s{i}.md",
            "slug": f"topic-{i:02d}",
            "created": when,
            "last": when,
            "summary": "摘要" * 150
        }

    rows = [row(i) for i in range(60)]
    out = gen_active_recent.render(rows, 14, now, byte_budget=gen_active_recent.DEFAULT_BYTE_BUDGET)
    assert len(out.encode("utf-8")) < 30_000, "默认预算输出仍可能超 AI 工具壳内联上限"
    assert "共 60 个切片" in out and "省略" in out, "页脚必须保留总数与省略数"

    tiny = gen_active_recent.render(rows, 14, now, byte_budget=100)
    assert "省略 59 条" in tiny, "预算只够一行时至少显示 1 行, 不得输出空表"

    full = gen_active_recent.render(rows, 14, now)
    assert "省略" not in full and "topic-59" in full, "不传预算(--all)必须仍是全量"

    five = gen_active_recent.render(rows, 14, now, limit=5)
    assert "省略 55 条" in five and "topic-59" not in five, "-n N 按条数截取"


def test_kb_cap_debt_is_discoverable_not_blocking(tmp_path: Path) -> None:
    """尺寸债务**必须可发现**: 造一个超限文件, 它得报成 warn(债务) 而不是 problem(判红)。

    为什么改成这样断言: 降级之后, "断言现行文档都不超"会退化成恒绿 —— 债务制**允许**文件超限,
    那时守卫不响, 但 `doc.caps` 必须响。所以这里守的是"严重度仍然正确", 而不是"今天恰好不超"。
    """
    checker = _kb_checker()
    root, mb = tmp_path, tmp_path / "memory-bank"
    (mb / "evergreen").mkdir(parents=True)
    (mb / "evergreen" / "_about.md").write_text("# t\n> 摘要: x\n> 触发: y\n", encoding="utf-8")
    big = mb / "evergreen" / "big.md"
    big.write_text("# 大\n> 摘要: x\n> 触发: y\n" + "x" * 30_000, encoding="utf-8")

    problems, warns = checker.check_caps(root, mb)

    assert not problems, f"尺寸超限不该再进 problems(它已是债务): {problems}"
    assert any("big.md" in w and "超 cap" in w for w in warns), f"超限文件没被报成债务: {warns}"
    assert any("债务" in w for w in warns), f"债务行必须自带处置口径(转告用户另开会话清理): {warns}"


def test_agents_md_cap_is_hard_not_debt(tmp_path: Path) -> None:
    """AGENTS.md 超 8,000 仍是 problem(硬规定), 且**不出现在债务清单里**。

    它越过的不是预算而是**截断点**: IDE 注入 `slice(0, 8000)`, 尾部对模型真不可见 ——
    所以 2026-09-30 用户拍板: 不能超、不套 50% 收缩、不进债务体系(它不常改, 一旦改了就该顺手合规)。
    """
    checker = _kb_checker()
    root, mb = tmp_path, tmp_path / "memory-bank"
    mb.mkdir()
    (root / "AGENTS.md").write_text("x" * 8_001, encoding="utf-8")

    problems, warns = checker.check_caps(root, mb)
    assert any("AGENTS.md" in p and "超 cap" in p for p in problems), f"AGENTS.md 超限必须仍是 problem: {problems}"
    assert not any("AGENTS.md" in w for w in warns), f"AGENTS.md 不该进债务清单: {warns}"

    # 剔除硬规定角色后(这正是 `doc.caps` 的调用形态), 它既不进债务、也不该留下 problems
    debt_roles = tuple(r for r in checker.DEFAULT_ROLES if r not in checker.HARD_CAP_ROLES)
    debt_problems, debt_warns = checker.check_caps(root, mb, debt_roles)
    assert not debt_problems and not debt_warns, (
        f"剔除 {checker.HARD_CAP_ROLES} 后不该再有任何输出: {debt_problems} / {debt_warns}"
    )


def test_kb_slice_cap_and_count_are_debt_not_blocking(tmp_path: Path, monkeypatch) -> None:
    """切片尺寸 / 条数 → warns(债务); 命名 / 三行头 → problems(判红)。

    `collect()` 返回三元组 (行, 问题, 债务): 债务侧的判据是"该蒸馏了", 问题侧的判据是"结构坏了"。
    条数阈值用 monkeypatch 压到 2 —— 真造 71 个文件既慢又与校准数字耦合。
    """
    import gen_active_recent
    import gen_baseline_recent

    monkeypatch.setattr(gen_active_recent, "SLICE_COUNT_LIMIT", 2)

    slice_dir = tmp_path / "activeContext"
    slice_dir.mkdir()
    for i in range(3):
        (slice_dir / f"26-01-0{i + 1}-0000-s{i}.md"
        ).write_text(f"# s{i}\n> 摘要: x\n> 最后活动: 2026-01-0{i + 1} 00:00\n", encoding="utf-8")
    rows, problems, warns = gen_active_recent.collect(slice_dir, tmp_path)
    assert not problems, f"合规切片不该报问题: {problems}"
    assert len(rows) == 3
    assert len(warns) == 1 and "债务" in warns[0], f"条数超限必须报成一条债务: {warns}"

    # 命名坏了 = 结构问题, 仍判红(不因债务制放松)
    (slice_dir / "bad-name.md").write_text("# bad\n", encoding="utf-8")
    _rows, problems, _warns = gen_active_recent.collect(slice_dir, tmp_path)
    assert any("文件名不合" in p for p in problems), f"不合规命名必须仍是 problem: {problems}"

    # 基线切片同口径: 尺寸超限是债务
    base_dir = tmp_path / "memory-bank" / "testing" / "baselines"
    base_dir.mkdir(parents=True)
    # root 传 tmp_path, rel 才会是 `memory-bank/testing/baselines/...` → 命中 baseline-slice 档 (8,000)
    (base_dir / "26-01-01-0000-b0.md").write_text("# b\n> 摘要: x\n" + "x" * 9_000, encoding="utf-8")
    _rows2, problems2, warns2 = gen_baseline_recent.collect(base_dir, tmp_path)
    assert not problems2, f"基线切片尺寸不该判红: {problems2}"
    assert any("债务" in w for w in warns2), f"基线切片超限必须报成债务: {warns2}"


def test_context_caps_hard_and_debt_split() -> None:
    """`scripts/check_context_caps.py` 的分档: AGENTS.md 只在 `HARD_CAPS`, **不进**任何债务组。

    钉住它的理由: 债务制的牙齿全在"债务必然可见", 而 AGENTS.md 是**唯一**不许挂账的文件 ——
    一旦有人把它挪进 `SKILL_CAPS` / `READ_BUDGET_CAPS`, 它超限就只剩一行提示, 尾部静默截断
    会重新变成"写了但没人看见"。
    """
    import importlib.util

    path = ROOT / "scripts" / "check_context_caps.py"
    spec = importlib.util.spec_from_file_location("check_context_caps", path)
    assert spec and spec.loader, "缺少 scripts/check_context_caps.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert set(module.HARD_CAPS) == {"AGENTS.md"}, f"硬规定组应是 AGENTS.md 一份: {set(module.HARD_CAPS)}"
    assert module.HARD_CAPS["AGENTS.md"] == 8000, "AGENTS.md 的 8000 是 IDE 注入常量, 不是可调预算"
    assert "AGENTS.md" not in module.SKILL_CAPS and "AGENTS.md" not in module.READ_BUDGET_CAPS, (
        "AGENTS.md 不得出现在债务组 —— 它没有挂账通道"
    )


def test_memory_bank_instructions_match_current_structure() -> None:
    """`applyTo: memory-bank/**` 的规则载体必须与**当前结构**一致。

    为什么值得单独钉: 它只在**编辑 `memory-bank/` 时**注入 —— 不重写的话, 目录化重构后的新结构
    在改库那一刻**根本不在上下文里**, 于是又会按旧的 8 文件结构去写。2026-09-22 重写前的旧版
    还在教「read ALL memory bank files at the start of every task」—— 那正是本库膨胀到 50 万字符的原因。

    2026-09-23 瘦身: 4,213 → 2,486 字符(106 → 55 行)。删掉的四节(cap 分级表 / 三行头模板 / pitfalls 字段 /
    任务档案格式)**都在 skill 与 `_common.py` 有单点**, 而其中 cap 表是**数值型重复** —— 守卫只钉
    token 不钉数值, 改了源不会红。所以针列表同步换掉了 `## 原始请求` / `## 进度日志`(那是 skill
    里「任务档案规范」的内容), 换成 `CAP_POLICY`(证明它指向机器单点而不是自己抄一张表)。
    WARN: **不要退回成"纯指针"**: 本文件是**自动注入**, 而 skill 是**按需触发**加载 —— 纯指针会让
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

    WARN: 只比**数值多集合 + 行数**: 能判红「改了源没改表」与「少写一行」, **判不出**「两行数值互换角色」
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
    """skill 的脚本都能被 import —— 模块级错误在这里当场红, 不必等闸门跑 `--help`。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    for name in (
        "_common", "gen_tasks_index", "gen_kb_index", "gen_docs_index", "gen_all", "check_kb_structure",
        "gen_active_recent", "gen_baseline_recent"
    ):
        path = SKILL_SCRIPTS / f"{name}.py"
        assert path.is_file(), f"缺少 {path.relative_to(ROOT)}"
        __import__(name)


def _gen_all():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_all

    return gen_all


def test_gen_all_declares_exactly_all_indexes() -> None:
    """生成物集合单点: gen_all 的产出 == 库内**全部** `_index.md` —— 一个不多, 一个不少。

    这是 sync 自动化解白名单的安全底线: 白名单里多一个其实不是生成物的路径, sync 就会
    在冲突时静默丢弃手写内容(第 3 步自证也救不回来); 少一个则冲突化解不了。
    """
    gen_all = _gen_all()
    outputs = gen_all.collect(ROOT, MB)
    on_disk = set(MB.rglob("_index.md"))
    assert set(outputs) == on_disk, (
        f"gen_all 产出与库内 _index.md 不一致: 多 {sorted(set(outputs) - on_disk)} / "
        f"少 {sorted(on_disk - set(outputs))}"
    )


def test_gen_all_check_is_green() -> None:
    """`--check` 在当前库上必须绿 —— 磁盘内容 == 生成结果(等价于 kb.check 的生成物部分)。"""
    gen_all = _gen_all()
    outputs = gen_all.collect(ROOT, MB)
    drifted = [p for p, want in outputs.items() if (p.read_text(encoding="utf-8") if p.exists() else "") != want]
    assert not drifted, "请运行 `commands run kb.index` 重建:\n" + "\n".join(
        f"  {p.relative_to(ROOT)}" for p in sorted(drifted)
    )


def test_gen_all_list_matches_outputs(capsys) -> None:
    """`--list` 声明的集合必须与 collect() 实际写出的集合**恒等** —— 白名单不得多/少。"""
    gen_all = _gen_all()
    assert gen_all.main(["--list"]) == 0
    listed = {ROOT / line for line in capsys.readouterr().out.splitlines() if line.strip()}
    assert listed == set(gen_all.collect(ROOT, MB))


def test_gen_cmd_hints_name_real_tasks() -> None:
    """生成物的"怎么重建"提示必须指向**真的能重建它**的命令(2026-09-24 实测缺陷)

    原先 `_common.gen_cmd()` 忽略传入的脚本名, 一律返回 `commands run kb.index`, 而 `kb.index`
    当时只跑 gen_tasks_index + gen_kb_index。于是 `_doc-map.md` / `plans|reports/_index.md` 的报错
    文案("请运行 commands run kb.index")**照做一遍仍然是红的** —— 而提交闸门早就把这两条的
    `--check` 挂上了, 形成"闸门能红、却没有一条能修的命令"。

    三条断言(前两条都拦不住这个缺陷, 只有 3. 判的是"跑那条命令真的会重建/校验它"):
      1. 每个 `gen_cmd(root, "<脚本>")` 调用点的脚本名都在表里(新生成脚本忘了登记 ⇒ 退回默认值);
      2. 表里每个 task id 在 `.commands/` 里真实存在(任务改名/删除后提示不能变成死指针);
      3. **提示说跑 `kb.index` 的脚本必须真的出现在 `kb.index` 的 run 列表里**(`kb.check` 同理)
         —— 这同时钉住了"`kb.index` 的覆盖面 ⊇ 提交闸门判红的生成物集合"这条设计口径。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    table = _common.GEN_CMD_BY_SCRIPT

    # 1. 调用点全覆盖
    call_sites: set[str] = set()
    for path in sorted(SKILL_SCRIPTS.glob("*.py")):
        call_sites |= set(re.findall(r'gen_cmd\(\s*root\s*,\s*"([^"]+)"\s*\)', path.read_text(encoding="utf-8")))
    assert call_sites, "一个 gen_cmd 调用点都没扫到(写法变了? 同步本守阵)"
    missing = sorted(call_sites - set(table))
    assert not missing, (f"这些脚本调了 gen_cmd 却不在 GEN_CMD_BY_SCRIPT 表里: {missing} —— "
                         "会退回默认值 `kb.index`, 而它未必能重建该脚本的产出")

    def task_body(task_id: str) -> str:
        pack, _, name = task_id.partition(".")
        cfg = ROOT / ".commands" / pack / "config.toml"
        assert cfg.is_file(), f"提示里的包不存在: {cfg.relative_to(ROOT)}"
        text = cfg.read_text(encoding="utf-8")
        m = re.search(rf'^\[tasks\."{re.escape(task_id)}"\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M)
        assert m, f"{cfg.relative_to(ROOT)} 里找不到任务 `{task_id}` —— 表里的提示是死指针"
        return m.group(1)

    gen_scripts = {s for _skill, s in _gen_all().GENERATORS}

    for script, hint in sorted(table.items()):
        parts = hint.split()
        assert parts[:2] == ["commands", "run"] and len(parts) >= 3, f"{script} 的提示不是 `commands run <task>`: {hint!r}"
        task_id = parts[2]
        body = task_body(task_id)  # 2. 任务真实存在
        if task_id == "kb.index":  # 3. 核心: 真的会重建它
            # 2026-10-03 起 kb.index 收成一条 `gen_all.py`: 提示说跑 kb.index 的脚本, 要么直接出现在
            # run 列表里, 要么由 gen_all 的 GENERATORS 声明覆盖(集合单点收编, 不再是手抄副本)。
            covered = script in body or ("gen_all.py" in body and script in gen_scripts)
            assert covered, (
                f"{script} 的提示说跑 `{task_id}`, 但它的 run 列表与 gen_all.GENERATORS 都没覆盖 {script} —— "
                f"用户照做一遍仍然是红的(2026-09-24 实测的缺陷形态)"
            )
        elif task_id == "kb.check":
            assert f"{script} --check" in body, (f"{script} 的提示说跑 `{task_id}`, 但它的 run 列表里没有 `{script} --check`")
