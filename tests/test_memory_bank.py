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
- test_session_protocol_is_exposed_in_always_on_entries: skill 载体存在且含阈值/DoD, `AGENTS.md` 声明阈值并指向 skill (copilot-instructions 2026-10-06 降级为指针后不再受查)

知识库目录化守卫 (检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 进程内 import):

- test_kb_index_is_regenerated / test_kb_index_and_files_are_bijective: 索引 == 生成结果; 索引与目录双向一致
- test_kb_topic_files_have_metadata / test_kb_files_respect_caps / test_kb_class_names_and_topic_filenames: 三行头元数据 / **硬规定** cap / 类名与文件名
- test_kb_no_orphan_index_dirs / test_kb_stubs_are_valid: 顶层索引都被 README 引用; 被拆文档留合法存根
- test_kb_pitfall_entries_have_required_fields: pitfalls 条目含 触发 / 判别 / 处置
- test_kb_active_context_within_cap: `activeContext.md` 是 ≤2 KB 合法存根 (2026-09-23 起滚动状态已迁 `activeContext/`)
- test_kb_active_context_slices_are_valid: 切片命名定宽 / 三行头齐 (结构); 尺寸与条数是**债务**, 不判红
- test_kb_cap_debt_is_discoverable_not_blocking: 造超限文件 → 必须报成 warn(债务) 而不是 problem
- test_kb_debt_count_excludes_min_size_hints: CLI 汇总行的「cap 债务 N 项」只数带 `DEBT_MARK` 的行, 「文件过小」提示不计入
- test_agents_md_cap_is_hard_not_debt: AGENTS.md 超 8,000 仍是 problem(硬规定), 且不出现在债务清单里
- test_kb_slice_cap_and_count_are_debt_not_blocking: 切片尺寸 / 条数 → warns(债务); 命名 / 三行头仍判红
- test_kb_active_render_respects_byte_budget: kb.active 默认字节预算截取(30KB 内联上限), 页脚留总数, --all / -n N 逃生
- test_context_caps_hard_and_debt_split: `check_context_caps.py` 的 AGENTS.md 只在 `HARD_CAPS`、不进债务组
- test_doc_links_are_not_broken: 全库相对链接存在性 (检查器 memory-bank skill 的 `scripts/check_doc_links.py`, 2026-10-06 从根 `scripts/` 迁入)
- test_doc_links_rejects_windows_normalized_targets: 存在性按 Linux 口径判 —— 结尾点(`kb/...`) / 大小写不符 判坏链, 本机 Windows 的路径归一化不得让它恒绿 (2026-10-11 CI 单条红的根因)

文档族注册表与 kb.new / kb.wrap (2026-10-17 P1, 计划 26-10-17-0527; 实现与检查器在
memory-bank skill 的 `scripts/new_doc.py` / `wrap_session.py` / `check_doc_templates.py`,
**进程内 import** —— 本项目测试禁止起子进程):

- test_new_doc_creates_valid_plan_and_task: 真建 plan + task 各一件 (tmp 夹具) —— 命名/头部字段
  / SLOT 清单齐; 建后残留 SLOT 判红 (守卫设计), 填完判绿; stdout 含「机械 0」收录断言 (§5.4)
- test_new_doc_refuses_slice_and_duplicates: slice 族拒绝并指路 kb.wrap; 重复建/坏 topic/坏领域
  全 fail-fast (--refs 已由 P2 的 D4 双向补链接手, 见下; 重复建冻结 timekit.now 钉同分钟 ——
  plan 分钟戳命名 + 真墙钟跨分钟 = 两次文件名不同永不撞名, CI 偶发红 26-10-17 实证)
- test_new_doc_task_domain_is_longest_prefix_match: 领域段最长前缀匹配 (P1 首段切分缺陷,
  P2 补) —— 连字符领域 `memory-bank` 可建 / `memory-` 前缀撞名不误收 / 裸领域沿用 P1 行为
- test_wrap_creates_zero_slot_slice_and_updates: 建切片零 SLOT 即合规 (判断剩余 0, 裁定 A6);
  二次调用抬最后活动 + 追加 R 行; 同专题档案抬 Updated + 进度日志日期行 (A5)
- test_checker_three_mutations_judged_red: 红绿双验 —— 填完 = 基准绿; 三类突变 (删状态行 /
  词表外值 / 留 SLOT) 逐类判红, 每类还原后复绿 (证明绿不是恒绿)
- test_checker_freeze_line_exempts_stock: 冻结线之前 (档案日期 26-10-16 / plan·report 文件名
  stamp 0735) 的缺陷件豁免; 之后 (26-10-17 / 0740) 入检查面判红 (D3 存量冻结只拦新增)
- test_checker_catches_new_plan_missing_doc_added: 手写新计划缺 doc-added 必判红 (26-10-31 修
  RM02-RM10 九件无状态计划事故的回归阵: 原按文件自身 doc-added 圈面, 缺头部新件整件逃逸;
  修复后圈面 = 文件名 stamp 前缀, 与文件招供无关)
- test_family_registry_matches_templates: 模板烤进去的出厂值与 `_common.FAMILIES` 同源
  (设计底线: 不造第二套词表/命名规则)
- test_doc_templates_checker_is_wired: 检查器挂在 kb.check 与提交闸门两侧 (不接线 = 没人跑;
  与 test_commit_gate_covers_kb_check 同旨)

kb.status / kb.bump 与 D4 反向补链 (2026-10-17 P2, 计划 26-10-17-0527; 实现与检查器在
memory-bank skill 的 `scripts/flip_status.py` / `bump_doc.py`, **进程内 import**):

- test_flip_status_flips_bumps_and_fails_fast: 计划/档案翻转 (doc-status / **Status:**) + 自动
  抬 doc-updated / Updated + 重建索引; 同状态翻转幂等 (不抬戳不重建); 词表外值/切片/issue/
  未知载体/缺状态行全 fail-fast; 终态带条件提醒 (切片迁出 / Summary 收口); 输出含「机械 0」
- test_bump_doc_appends_changelog_and_fails_fast: 计划 R 行追加 (编号 = 段内最大+1, 已有行
  零触碰, note 自动 HTML 转义) + doc-updated 抬; 档案抬 Updated / 切片抬最后活动; 无变更
  记录段 fail-fast 指路; 输出含「机械 0」
- test_new_doc_refs_auto_chains_bidirectionally: D4 反向认领 —— 本件写 doc-refs / **Refs:**,
  目标件 (HTML/md 四类载体) 自动反向声明, 幂等合并 (逗号); 坏 refs (不存在/库外/生成物)
  全 fail-fast 且不落半文件; 无 --refs 与 P1 行为一致
- test_p2_full_chain_drill: P2 验收演练 (计划 §07) —— kb.new(--refs) → 填空 → kb.status →
  kb.bump → gen_doc_map --check 双向机检绿; 改过的件再过新增面守卫仍绿
- test_kb_status_and_bump_are_registered: kb.status / kb.bump 已收录进 .commands/kb (收录
  协议; 不接线 = 没人跑)

二期四族 pitfall/report/baseline/progress 与守卫扩面 (2026-10-17 P3, 计划 26-10-17-0527;
实现 = `_common.FAMILIES` 扩行 + `templates/` 四件 + new_doc 分派 + check_doc_templates
扩扫描面, 进程内 import; 验收: 计划 §07 P3 行):

- test_new_doc_creates_phase2_families: 四族真建冒烟 (tmp 夹具) —— 坑档 `--class` 7 类 +
  `--triggers`(A7 参数分支, 头部零 SLOT)/ 报告出厂 Done / 基线 `--total` 誊写 + 基线时间
  排序键 / 进展件三行头; 建后残留 SLOT 判红、填完判绿; 扫描面恰 2 件 (report+baseline);
  stdout 含「机械 0」收录断言
- test_new_doc_phase2_family_params_fail_fast: 四族参数校验 —— 坑档缺/坏 `--class`、缺
  `--triggers`; 进展件缺 `--triggers`; 基线缺 `--total` 全 fail-fast (之后假定输入合法)
- test_pitfall_refs_chain_bidirectionally: D4 反向认领对坑档形态 (md 锚点链的三行头
  分支) —— 坑档正向 `**Refs:**` + 档案目标反向声明, 幂等
- test_checker_report_mutations_judged_red: 报告族红绿双验 —— 删 doc-status / 词表外值
  / 留 SLOT 三类突变逐类判红, 还原复绿 (状态承载族第二例, HTML 面)
- test_family_registry_matches_templates (扩展): 报告出厂 Done + doc-type 同源; 坑档/
  进展件模板触发词占位; 基线模板 TOTAL 与基线时间占位; 坑档族 subdir 单点身份断言;
  **全族模板头部区零 SLOT** (渲染正确性契约, §05 守卫配套)
- test_checker_freeze_line_exempts_stock (扩展): report (doc-added 精确到分) 与
  baseline (stamp 前缀) 两个新扫描面 —— 线前豁免、线后判红; 坑档/进展件不在扫描面
  (命名无时间戳, 不可判定新旧, 由既有守卫兜底)

时间守卫 (检查器 memory-bank skill 的 `scripts/timekit.py`, 2026-10-06 加):

- test_timekit_now_is_utc_plus_8_naive: 取时是 UTC+8 naive 墙钟 (与本地时区无关, 无 tzinfo)
- test_timekit_guards_catch_three_layers: 文件名未来 / 坏「最后活动」/ 斜杠日期三种种子全逮住
- test_timekit_body_ignores_code_and_paths: 正文层跳过代码上下文与路径标识符 (不误报)
- test_timekit_check_is_green_on_current_kb: 存量 KB 零违规 (清洗完成后)

回写措辞守卫 (检查器 memory-bank skill 的 `scripts/check_wording.py`, 2026-10-07 加):

- test_wording_guard_is_green_on_current_kb: 存量 KB 零违规 (清洗完成后)
- test_wording_guard_flags_status_but_exempts_dated_and_tree_state: 无日期状态行判红; 日期流水 / 树态 / 行内代码引述 / 豁免标记 都不报
- test_wording_guard_is_wired_into_kb_check: 守卫已挂进 `kb.check` 的 run 列表 (不接线 = 没人跑)
- test_commit_gate_covers_kb_check: 提交闸门 [[gates]] 覆盖 `kb.check` 的每一条 `--check` (gen_all 展开成 GENERATORS) —— 漏挂 = 静默红 (2026-10-11 实测: 基线切片缺三行头致 kb.check 恒红而闸门不拦)
- test_number_guard_exempts_dated_code_and_reports_only_overflow: 判据族 B 裸数字判红; 日期/代码/豁免标记不报; 存量冻结只报溢出
- test_number_guard_is_green_on_current_kb: 当前 KB 裸数字未超冻结常数 (存量冻结; 超出 = 本轮新增手抄)
- test_number_guard_dated_exemption_does_not_cover_continuation_lines: 已知边界 —— 日期豁免只认首行, 续行照常入判
- test_memory_bank_instructions_match_current_structure: `memory-bank.instructions.md` 与当前结构一致 (2026-09-23 瘦身后针列表同步换过)
- test_skill_cap_table_matches_cap_policy: SKILL.md 的 cap 表数值集合 == `_common.CAP_POLICY` (防手抄表漂移)
- test_kb_scripts_import_cleanly: skill 的脚本都能 import

常驻锚防流水守卫 (检查器 memory-bank skill 的 `scripts/check_mutation_anchor.py`, 2026-10-31 加):

- test_mutation_anchor_guard_is_green_on_current_kb: 蒸馏改版后的常驻锚零违规 (§07 一张记录表 + 一行式状态日志)
- test_mutation_anchor_guard_flags_ledger_log_and_round_numbers: 台账字样 / 白名单外节 / 逐轮流水数字 / 状态日志超限逐类判红; 清白件零误报
- test_mutation_anchor_guard_is_wired_into_kb_check_and_gate: 守卫已挂进 kb.check 与提交闸门两侧

kb.tier 分级清理四动作 (2026-10-31 R0, 计划 26-10-31-0534; 实现在 memory-bank skill 的
`scripts/kb_tier.py`, **进程内 import**, tmp 夹具不碰真实 memory-bank/):

- test_kb_tier_set_marks_and_fails_fast: set 插入为头部区第 4 行 (前三行零触碰) / 已有等
  级行原地改值 / 同值幂等不写盘 / 非法等级与不存在文件与生成物·附件·库外路径 fail-fast /
  头部区不足 4 行插在头部区末尾 / CRLF 文件插入行保持 \\r\\n
- test_kb_tier_list_separates_unmarked: list 列出该等级全部文件 (行数/字符数); 未打标件
  (无 `> 等级:` 行) 区分呈现 —— L0 视图全列待定件, 其它级只给一行汇总; 非法等级拒绝
- test_kb_tier_migrate_dry_run_default_and_apply: migrate 默认 dry-run 零写盘; --apply 后
  正文段逐字节搬 attachments/ (行数与 \\r\\n 计数与原文一致, 字节差只允许来自相对链接的
  `../` 前缀; scheme/根相对/锚点链接不动), 主档留 `> 已外迁:` 指针且摘要判据单点仍在;
  CRLF 文件整段搬后行尾形态不变; 迁后重跑跳过 (无正文段)
- test_kb_tier_purge_gates_all_or_nothing: purge 默认 dry-run 不删; 非 L3 拒绝; 三闸门逐
  条触发 —— ①无守阵且头部无「无需守阵」②全仓反向引用未清零 ③头部缺 `> 观察通过:` 标
  记 —— 任一不过全体拒绝 (全或无, 删零个) 且 rc=1; 三闸门全过 + --apply 才真删
- test_kb_tier_is_registered: kb.tier 已收录进 .commands/kb (收录协议 when/note 必填;
  与 test_kb_status_and_bump_are_registered 同旨)
- test_gen_all_declares_exactly_all_indexes: gen_all.py 的产出集合 == 库内全部 `_index.md`(生成物全集单点)
- test_gen_all_check_is_green: gen_all.py `--check` 在当前库上绿 (磁盘 == 生成结果)
- test_gen_all_list_matches_outputs: `--list` 声明的路径集合 == collect() 实际产出 (白名单不得多/少)
- test_generated_indexes_are_lf_only: 生成物字节里无 CR —— 生成器 `write_text` 显式 `newline="\n"`, 防 Windows 上按 os.linesep 落成 CRLF 的"纯行尾噪音"
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

# 非 `_index.md` 的生成物 —— 新增一个必须显式登记(详见 test_gen_all_declares_exactly_all_indexes)
EXTRA_GENERATED = ("memory-bank/issues/attachments/_archive.md", )

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

    # 2026-10-06 起只查 `AGENTS.md` —— `.github/copilot-instructions.md` 已降级为**纯指针**
    # (内容只有"以 ../AGENTS.md 为准")。原先"两个入口都得含阈值 / skill 路径"的断言实际是在
    # **替过期副本兜底**: 副本一改成不重复口径就判红, 逼得它要么留着旧说法、要么留一行机械 token。
    # 会话协议守单点足够 —— 指针自己不承载口径, 也就不需要被守。
    agents = ROOT / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    assert "立档阈值" in text, f"{agents.name} 未声明立档阈值"
    assert ".agents/skills/memory-bank/SKILL.md" in text, f"{agents.name} 未指向 memory-bank skill"


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

    # 不能依赖别的用例先插过 sys.path —— xdist 分组随测试集变化(2026-10-13 W7 加了
    # 一个 dom_panel 用例就翻出本潜伏依赖), 自带插入才是确定性口径。
    import sys

    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
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


def test_kb_debt_count_excludes_min_size_hints(tmp_path: Path, monkeypatch, capsys) -> None:
    """CLI 汇总行的「cap 债务 N 项」**只数带 `DEBT_MARK` 的行**, 「文件过小」提示不进这个数。

    判据出自 `pitfalls/kb/cap-debt.md` 第 1 条: **债务数必须能清零** —— 一件债务对应一个动作
    (精简 / 外迁), 而「文件过小」没有这样的动作(把它往外迁是错的动作)。旧实现直接 `len(warns)`,
    于是这行恒报常数(2026-10-06 实测 ~40 项)而真实债务 0 ⇒ 清理会话按它收口必然徒劳。
    """
    checker = _kb_checker()
    evergreen = tmp_path / "memory-bank" / "evergreen"
    evergreen.mkdir(parents=True)
    (evergreen / "_about.md").write_text("# t\n> 摘要: x\n> 触发: y\n", encoding="utf-8")
    (evergreen / "small.md").write_text("# 小\n> 摘要: x\n> 触发: y\n", encoding="utf-8")

    def run() -> str:
        monkeypatch.setattr(sys, "argv", ["check_kb_structure.py", "--root", str(tmp_path)])
        checker.main()
        return capsys.readouterr().out

    only_hint = run()
    assert "cap 债务 0 项" in only_hint, f"「文件过小」不得计入债务数: {only_hint}"
    assert "cap 债务 1 项" not in only_hint, f"债务数被「过小」提示撑大了: {only_hint}"
    assert "过小" in only_hint, "提示本身仍要打印(只是不计入债务数)"

    (evergreen / "big.md").write_text("# 大\n> 摘要: x\n> 触发: y\n" + "x" * 30_000, encoding="utf-8")
    with_debt = run()
    assert "cap 债务 1 项" in with_debt, f"真实超限必须计成 1 项债务: {with_debt}"


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


def _doc_links_module():
    """载入 memory-bank skill 的链接检查器 (**进程内 import** —— 本项目测试禁止起子进程)。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_doc_links", SKILL_SCRIPTS / "check_doc_links.py")
    assert spec and spec.loader, "缺少 memory-bank skill 的 scripts/check_doc_links.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doc_links_are_not_broken() -> None:
    """全库**相对链接存在性** —— 改名 / 搬家后的坏链不会让任何测试失败, 只能机检。

    知识库目录化重构一次新增/改写了 400+ 处相对链接; 这条守卫把"改文件名后必须查全仓引用"
    从人工扫变成可自动跑的判据(实测首跑就抓出 73 处坏链, 全是搬家导致的相对深度错位)。
    检查器在 memory-bank skill 的 `scripts/check_doc_links.py`(2026-10-06 从根 `scripts/` 迁入,
    随 skill 移植), **进程内 import**(本项目测试禁止起子进程)。存在性口径见下条。
    """
    broken = _doc_links_module().scan_all(ROOT)
    assert not broken, "相对链接坏链:\n" + "\n".join(f"  {p}:{n} → {t}" for p, n, t in broken)


def test_doc_links_rejects_windows_normalized_targets(tmp_path: Path) -> None:
    """存在性必须按 **Linux / CI 口径**判 —— 不许被 Windows 的路径归一化骗成恒绿。

    2026-10-11 的真实 CI 红(本机三道防线全绿): 目标 `...` 在 Windows 上 `(kb / "...").exists()`
    返回 `True` —— Win32 把结尾的点剥掉, 路径塌成父目录 `kb/`, 而 `os.listdir` 里根本没有该条目;
    同族还有大小写不敏感(`kb/Cap.md` 命中 `kb/cap.md`)。于是坏链连过 doc.links 闸门 /
    test.quick 闸门 / 手工 test.full, 只在 ubuntu job 红。
    红验: 把 `link_exists` 退回 `(base / rel).exists()` ⇒ 本用例在本机立刻红。
    """
    mb = tmp_path / "memory-bank"
    (mb / "kb").mkdir(parents=True)
    (mb / "kb" / "cap.md").write_text("# cap\n", encoding="utf-8")
    (mb / "doc.md").write_text(
        "- 真链接 [a](kb/cap.md)\n"
        "- 父目录导航 [b](..)\n"
        "- 锚点 [c](kb/cap.md#sec)\n"
        "- 省略号占位 [d](kb/...)\n"
        "- 结尾点 [e](kb/x.)\n"
        "- 大小写不符 [f](kb/Cap.md)\n"
        "- 引述 `[g](kb/...)` 不算链接\n",
        encoding="utf-8",
    )

    broken = _doc_links_module().scan_all(tmp_path)
    assert [(n, t) for _, n, t in broken] == [(4, "kb/..."), (5, "kb/x."), (6, "kb/Cap.md")], broken


def test_kb_scripts_import_cleanly() -> None:
    """skill 的脚本都能被 import —— 模块级错误在这里当场红, 不必等闸门跑 `--help`。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    for name in (
        "_common", "gen_tasks_index", "gen_kb_index", "gen_docs_index", "gen_all", "check_kb_structure",
        "gen_active_recent", "gen_baseline_recent", "check_doc_links", "timekit", "check_wording", "new_doc",
        "wrap_session", "check_doc_templates", "flip_status", "bump_doc", "kb_tier"
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
    """生成物集合单点: gen_all 的产出 == 库内**全部** `_index.md` + `EXTRA_GENERATED` —— 一个不多, 一个不少。

    这是 sync 自动化解白名单的安全底线: 白名单里多一个其实不是生成物的路径, sync 就会
    在冲突时静默丢弃手写内容(第 3 步自证也救不回来); 少一个则冲突化解不了。

    `EXTRA_GENERATED`(2026-10-11 加入): 不叫 `_index.md` 的**生成物**。issues 归档索引是第一个 ——
    它落在 `attachments/`(该目录不计 cap)才敢放全量清单, 而名字不叫 `_index.md` 正是为了
    **不**被 `index-auto` 角色套上 25,200 的 cap。新增同类生成物必须**显式登记在这里** ——
    否则本守阵会在它出现的那一刻红, 逼你确认它确实是生成物而不是手写件。
    """
    gen_all = _gen_all()
    outputs = gen_all.collect(ROOT, MB)
    on_disk = set(MB.rglob("_index.md")) | {ROOT / rel for rel in EXTRA_GENERATED}
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


def test_generated_indexes_are_lf_only() -> None:
    """生成物一律 LF 行尾 (2026-10-04) —— `Path.write_text` 的 `newline` 默认 `None` ⇒ 按 `os.linesep`
    翻换行, Windows 上把 `\n` 写成 CRLF, 于是 `kb.index` 顺带产出一批"纯行尾噪音"的 modified
    (坑档 pitfalls/git/editing-traps.md; 根因属该条记的"未决改造")。

    这里逐**字节**断言无 CR —— 用 `read_text` 会把 CRLF 折成 LF, 正好是这条缺陷能逃过既有
    `test_gen_all_check_is_green` / `kb.check` 的原因(它们对行尾不敏感)。文件集合取
    `gen_all.collect()` 的键(生成物单点), 不另抄一份清单。
    """
    gen_all = _gen_all()
    offenders = sorted(
        p.relative_to(ROOT).as_posix() for p in gen_all.collect(ROOT, MB) if p.exists() and b"\r" in p.read_bytes()
    )
    assert not offenders, (
        "这些生成物含 CR 字节(应为纯 LF), 请运行 `commands run kb.index` 重建:\n" + "\n".join(f"  {rel}" for rel in offenders)
    )


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


# ---------------------------------------------------------------------------
# 日期守卫 (2026-10-06, 计划 plans/26-09-30-0931): 时间单点 + 三层守卫
#
# 检查器在 memory-bank skill 的 `scripts/timekit.py`, **进程内 import** (本项目测试禁止起子进程)。
# TZ 无关性**不**用 `TZ=... 子进程` 验 (那要起进程) —— 改为钉住"取值 == UTC 瞬时 + 8h 的 naive
# 墙钟": 该等式在构造上就与本地时区无关 (本地时区一变, 等式立刻不成立)。
# ---------------------------------------------------------------------------


def _timekit():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import timekit

    return timekit


def test_timekit_now_is_utc_plus_8_naive() -> None:
    from datetime import datetime, timedelta, timezone

    timekit = _timekit()
    before = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
    got = timekit.now()
    after = (datetime.now(timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)

    assert got.tzinfo is None, "取时必须是 naive 墙钟 (与全库 naive 解析一致, 不混 aware)"
    assert before <= got <= after, f"取时不是 UTC+8 墙钟: {got} (期望 {before} ~ {after})"


def test_timekit_guards_catch_three_layers(tmp_path: Path) -> None:
    """三种种子经 `--mb-dir` 指向的 tmp 夹具, 三层 (文件名 / 元数据 / 正文) 全部逮住。"""
    timekit = _timekit()
    mb = tmp_path / "memory-bank"
    (mb / "tasks").mkdir(parents=True)
    (mb / "activeContext").mkdir(parents=True)

    (mb / "tasks" / "99-01-01-future-slug.md").write_text("# t\n> 摘要: x\n> 触发: y\n", encoding="utf-8")
    (mb / "activeContext" /
     "26-01-01-0000-bad.md").write_text("# t\n> 摘要: x\n> 最后活动: 2026-01-01 00:0x\n", encoding="utf-8")
    (mb / "tasks" / "26-01-01-slash.md").write_text("# t\n> 摘要: x\n> 触发: y\n正文 2026/01/01\n", encoding="utf-8")

    joined = "\n".join(timekit.collect_violations(tmp_path, mb))

    assert "文件名日期在未来" in joined, joined
    assert "最后活动" in joined, joined
    assert "斜杠日期" in joined, joined


def test_timekit_body_ignores_code_and_paths(tmp_path: Path) -> None:
    """正文层跳过围栏代码 / 行内代码与路径里的紧凑 8 位数字 —— 不误报 (2026-10-06 存量清洗口径)。"""
    timekit = _timekit()
    mb = tmp_path / "memory-bank"
    mb.mkdir()
    (mb / "doc.md").write_text(
        "# t\n> 摘要: x\n> 触发: y\n"
        "行内 `2026/01/01` 与围栏:\n"
        "```\n2026/01/02\n```\n"
        "路径 .cluster/audit-20260921/ 与备份 git-backup-20260922-2343 不是日期 token\n",
        encoding="utf-8",
    )

    problems = timekit.collect_violations(tmp_path, mb)

    assert not problems, f"代码上下文/路径标识符被误报: {problems}"


def test_timekit_check_is_green_on_current_kb() -> None:
    """存量 KB 零违规 (清洗完成后) —— 未来日期 / 坏体例都必须已清干净。"""
    problems = _timekit().collect_violations(ROOT, MB)

    assert not problems, "日期守卫违规 (取时走 `commands run kb.time`):\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# 回写措辞守卫 (2026-10-07, 口径单点在 skill 的「回写措辞」节)
#
# 为什么值得机检: `commit` 的 hash 由 tree + parent + 时间戳决定 —— 一个提交**永远无法包含自己的
# hash**; 而 DoD 要求回写件随主提交一并暂存, 于是「待提交」写在 hash 尚不存在的时点, 提交一落地
# 就变成假话。2026-09-27 审计 (reports/26-09-27-1547) 实证「靠收尾回扫修正」会失败: 切片停在
# 「等待提交」而提交已完成。检查器同样**进程内 import** (本项目测试禁止起子进程)。
# ---------------------------------------------------------------------------


def _wording():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_wording

    return check_wording


def test_wording_guard_is_green_on_current_kb() -> None:
    """存量 KB 零违规 (清洗完成后) —— 两个滚动更新面上不得再有「待提交」类时点相对断言。"""
    problems = _wording().collect_violations(ROOT, MB)

    assert not problems, ("回写措辞违规 (提交后必然过期; 改用时不变措辞「随本专题入库」或直接省去):\n" + "\n".join(problems))


def test_wording_guard_flags_status_but_exempts_dated_and_tree_state(tmp_path: Path) -> None:
    """五条边界各走一次: 无日期的状态行判红; 带日期流水 / 树态描述 / 行内代码 / 豁免标记 都不判红。

    这些豁免不是"放松", 是判据本身: 带日期的条目**自带时点**(改写它是篡改日志);
    `未提交改动` 是**树态描述**而非状态断言 (基线切片里 76 处这类合法用法);
    行内代码要能**引述**被禁措辞 (元讨论 —— 口径文档 / 坑档 / 本档案自己都要写它)。
    """
    wording = _wording()
    mb = tmp_path / "memory-bank"
    (mb / "tasks").mkdir(parents=True)
    (mb / "tasks" / "a.md").write_text(
        "- 修复完成, 待提交。\n"
        "- 2026-10-07 批 3 落地(改动留工作区待提交)。\n"
        "- 工作树含本轮未提交改动。\n"
        "- 口径禁写 `待提交` 这类断言。\n"
        "- 改动待提交 <!-- wording:allow -->\n"
        "- **未 commit**(用户未说「提交」)。\n"
        "- 等用户显式指令。\n",
        encoding="utf-8",
    )

    problems = wording.collect_violations(tmp_path, mb)
    joined = "\n".join(problems)

    assert len(problems) == 3, f"应恰好判红 3 条 (状态行 / 粗体标记 / 等指令): {problems}"
    assert "待提交" in joined and "未 commit" in joined and "等…指令" in joined
    assert "批 3 落地" not in joined, "带日期的历史流水条目必须豁免"
    assert "工作树含本轮未提交改动" not in joined, "树态描述必须豁免"
    assert "口径禁写" not in joined, "行内代码里的引述必须豁免"
    assert "wording:allow" not in joined, "豁免标记行不得被判红"


def test_wording_guard_is_wired_into_kb_check() -> None:
    """守卫必须挂在 `kb.check` 的 run 列表里 —— 不接线 = 没人跑 (与 timekit 同款要求)。"""
    cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    body = re.search(r'^\[tasks\."kb\.check"\]\n(.*?)(?=^\[|\Z)', cfg, re.S | re.M)

    assert body, "kb/config.toml 里找不到 kb.check"
    assert "check_wording.py --check" in body.group(1), "check_wording.py --check 未挂进 kb.check"


# ---------------------------------------------------------------------------
# 常驻锚防流水守卫 (2026-10-31, 口径单点在 mutation-testing skill 的「四段职责」/ 硬约束 12)
#
# 为什么值得机检: 排期锚 §01 明写「它不记流水」, 但 §08「轮次台账」与逐轮状态日志恰恰长成了
# 流水 —— 与任务档案/基线切片大面积重复, 重复必漂移 (实证: §07 hr 行漏记 R22、core 行计划
# 指针落后)。2026-10-31 蒸馏改版后由 check_mutation_anchor.py 钉住; 检查器**进程内 import**。
# ---------------------------------------------------------------------------


def _mutation_anchor():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_mutation_anchor

    return check_mutation_anchor


def test_mutation_anchor_guard_is_green_on_current_kb() -> None:
    """蒸馏改版后的常驻锚零违规 —— §07 覆盖进度总表一张记录表 + 一行式状态日志。"""
    problems = _mutation_anchor().collect_violations(ROOT, MB)

    assert not problems, ("常驻锚流水回归 (台账 / 逐轮日志写回锚里; 轮次明细的事实源是任务档案 + 基线切片):\n" + "\n".join(problems))


def test_mutation_anchor_guard_flags_ledger_log_and_round_numbers(tmp_path: Path) -> None:
    """四类判据逐类判红: 台账字样 / 白名单外节 / 逐轮流水数字 / 状态日志超限; 清白件零误报。"""
    anchor = _mutation_anchor()
    clean = (
        "<html><body>"
        "<h2><span class=\"no\">01</span>这个锚是干什么的</h2>"
        "<section><h2><span class=\"no\">07</span>覆盖进度总表</h2></section>"
        "<section><h2><span class=\"no\">08</span>状态变更日志</h2>"
        "<ul><li>2026-10-08 06:42 — 建立, 状态 Open。</li></ul></section>"
        "</body></html>"
    )

    assert anchor.scan_anchor(clean) == [], "清白件不得误报"

    dirty = (
        "<html><body>"
        "<h2><span class=\"no\">08</span>轮次台账</h2>"
        "<h2><span class=\"no\">09</span>自创节</h2>"
        "<p>存活 604 → 502, 红验 481/540 KILLED, 坑复发 +1</p>"
        "<section><h2>状态变更日志</h2><ul>" + "".join("<li>" + "长" * 400 + "</li>" for _ in range(9)) + "</ul></section>"
        "</body></html>"
    )
    problems = anchor.scan_anchor(dirty)
    joined = "\n".join(problems)

    assert "台账回归" in joined and "轮次台账" in joined
    assert "节白名单" in joined and "自创节" in joined
    assert "存活对差" in joined and "逐轮红验数字" in joined and "坑复发计数" in joined
    assert "日志体量" in joined, "9 条 × 400 字符的日志必须双限全红"


def test_mutation_anchor_guard_is_wired_into_kb_check_and_gate() -> None:
    """守卫必须挂在 kb.check 与提交闸门两侧 —— 不接线 = 没人跑, 漏闸门 = 静默红。

    `test_commit_gate_covers_kb_check` 已按 run 列表推导闸门覆盖面; 本条把名字钉死, 防
    kb.check 清单整行改名后两条测试同时静默失效。
    """
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    gate_cfg = (ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml").read_text(encoding="utf-8")

    assert "check_mutation_anchor.py --check" in kb_cfg, "check_mutation_anchor.py 未挂进 kb.check"
    assert "check_mutation_anchor.py --check" in gate_cfg, "check_mutation_anchor.py 未挂进提交闸门 (静默红)"


def test_commit_gate_covers_kb_check() -> None:
    """提交闸门必须覆盖 `kb.check` 的**每一条** `--check` —— 漏挂的那条就是**静默红**。

    2026-10-11 实测缺陷 (issue `26-10-11-1630-docs-baselines-missing-summary-header`): 三份基线切片
    缺三行头, `kb.check` 第 4 条 (`gen_baseline_recent --check`) 恒红, 而提交闸门里**没有**这条
    (`check_wording --check` 同样漏挂) ⇒ "能判红却不在闸门里": 缺陷静默通过所有提交, 只能靠人
    手动跑 `kb.check` 撞见。根因是闸门的 `[[gates]]` run 清单与 `kb.check` 各自演化 (手抄副本)。

    判据: 取 `kb.check` run 列表里所有 `X.py --check`, 把 `gen_all.py` 展开成它声明的 `GENERATORS`
    (索引生成器的集合单点), 要求每个都出现在 `.my-commit-flow.toml` 的某个 `[[gates]]` run 里。
    与 `test_gen_cmd_hints_name_real_tasks` 的"`kb.index` 覆盖面 ⊇ 闸门判红集"同旨, 这里是反方向
    (闸门 ⊇ `kb.check`), 两条合起来钉住"闸门判红的每一条都有人能修、且该跑的都真的在跑"。
    """
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    body = re.search(r'^\[tasks\."kb\.check"\]\n(.*?)(?=^\[|\Z)', kb_cfg, re.S | re.M)
    assert body, "kb/config.toml 里找不到 kb.check"
    checked = set(re.findall(r"([\w_]+\.py) --check", body.group(1)))
    assert checked, "kb.check 的 run 列表里没有 `--check` (写法变了? 同步本守阵)"

    if "gen_all.py" in checked:  # 索引生成器的集合单点: 展开成 GENERATORS 再核对
        checked.discard("gen_all.py")
        checked |= {script for _skill, script in _gen_all().GENERATORS}

    gate_cfg = (ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml").read_text(encoding="utf-8")
    gated = set(re.findall(r"([\w_]+\.py) --check", gate_cfg))

    missing = sorted(checked - gated)
    assert not missing, (
        f"提交闸门漏挂 kb.check 的 `--check`: {missing} —— 这些检查能判红却不在闸门里 = 静默红; "
        "把对应 `<脚本> --check` 加进 .my-commit-flow.toml 的 [[gates]] run 列表"
    )


def test_number_guard_exempts_dated_code_and_reports_only_overflow(tmp_path: Path) -> None:
    """判据族 B 边界 (2026-10-08 方案 C): 裸数字判红; 日期行 / 行内代码 / 豁免标记不判红; 存量不刷屏。

    存量冻结是**数目制**: 命中数 ≤ FROZEN 放行, 超出只报溢出条数 (不刷全部存量 —— 那会把提交闸门刷屏)。
    """
    wording = _wording()
    mb = tmp_path / "memory-bank"
    (mb / "tasks").mkdir(parents=True)
    (mb / "tasks" / "a.md").write_text(
        "- 本轮 test.full 2772 passed。\n"
        "- 2026-10-08 实测 2772 passed (历史流水)。\n"
        "- 口径里写 `2772 passed` 是引述。\n"
        "- 数字 2772 passed <!-- wording:allow -->\n",
        encoding="utf-8",
    )

    # 只有第 1 行 (无日期 / 无豁免) 命中; 日期行 / 行内代码 / 豁免标记都不命中。
    assert len(wording.list_test_numbers(tmp_path, mb)) == 1
    # 冻结常数设为 0 → 溢出 1 条, collect 只报溢出 (不刷全部存量)。
    original = wording.FROZEN_TEST_NUM_COUNT
    try:
        wording.FROZEN_TEST_NUM_COUNT = 0
        problems = wording.collect_violations(tmp_path, mb)
    finally:
        wording.FROZEN_TEST_NUM_COUNT = original
    assert sum(1 for p in problems if "裸" in p) == 1, f"存量冻结: 只报新增 1 条: {problems}"
    assert any("新增 1 处" in p for p in problems), f"应报新增条数: {problems}"

    # 冻结常数够大 → 全放行 (存量不拦)。
    wording.FROZEN_TEST_NUM_COUNT = 99
    try:
        assert not wording.collect_violations(tmp_path, mb)
    finally:
        wording.FROZEN_TEST_NUM_COUNT = original


def test_number_guard_dated_exemption_does_not_cover_continuation_lines(tmp_path: Path) -> None:
    """❗已知边界 (2026-10-08): 日期豁免只认**首行**, 多行流水条目的**续行**照常入判。

    这不是缺陷而是判据的已知形态 (见 `pitfalls/kb/scripts.md`): 处置 = 续行内容回避禁写形态
    (流水里写数字改「见 kb.baseline」)。本用例钉住它, 免得有人以为"带日期的整条流水都安全"。
    """
    wording = _wording()
    mb = tmp_path / "memory-bank"
    (mb / "tasks").mkdir(parents=True)
    (mb / "tasks" / "a.md").write_text(
        "- 2026-10-08 08:42 — 首行带日期 (豁免), 但下面续行里的数字照常入判:\n"
        "  本轮 test.full 2772 passed (续行, 不豁免)。\n",
        encoding="utf-8",
    )

    hits = wording.list_test_numbers(tmp_path, mb)

    assert len(hits) == 1, f"续行里的裸数字应入判 (首行已豁免): {hits}"


def test_number_guard_is_green_on_current_kb() -> None:
    """当前 KB 的裸数字不得超过冻结常数 (存量冻结; 超出 = 本轮又手抄了)。"""
    wording = _wording()
    actual = wording.count_test_numbers(ROOT, MB)

    assert actual <= wording.FROZEN_TEST_NUM_COUNT, (
        f"手抄测试数字 {actual} 处 > 冻结常数 {wording.FROZEN_TEST_NUM_COUNT} —— 本轮新增了手抄; "
        "数字只写 testing/baselines/ 切片, 正文改「见 kb.baseline」"
    )


# ---------------------------------------------------------------------------
# 文档族注册表与 kb.new / kb.wrap (2026-10-17 P1, 计划 26-10-17-0527)
#
# 实现与检查器在 memory-bank skill 的 `scripts/` (new_doc.py / wrap_session.py /
# check_doc_templates.py), 本文件**在进程内 import** 它们 (本项目测试禁止起子进程,
# `tests/sidefx.py` 的 POPEN 记账会判越界), 与既有守卫同做法。
#
# 红绿双验口径: 每类突变先判红、还原后**复绿** —— 只断言「能红」不够 (判据恒红等于没守),
# 必须证明「绿不是恒绿」。夹具一律 tmp_path, 不碰真实知识库。
# ---------------------------------------------------------------------------


def _doc_templates():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_doc_templates

    return check_doc_templates


def _new_doc():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import new_doc

    return new_doc


def _wrap():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import wrap_session

    return wrap_session


def _fill_slots(path: Path) -> None:
    """模拟 agent 的「一次填空」: 把所有 SLOT 标记替换为内容。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    text = path.read_text(encoding="utf-8")
    path.write_text(_common.SLOT_RE.sub("已填内容", text), encoding="utf-8")


def test_new_doc_creates_valid_plan_and_task(tmp_path: Path) -> None:
    """真建 plan + task 各一件 (tmp 夹具): 命名/头部/SLOT 清单齐, 建后残留 SLOT 判红、填完判绿。

    同时钉住 §5.4 收录断言: 两条命令的 stdout 必须含「机械 0」断言行 —— 这是计划把
    「剩余人工步骤」从散文变成可机检契约的那一行。
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        rc = new_doc.main(
            [
                "--root",
                str(tmp_path),
                "--mb-dir",
                str(mb),
                "plan",
                "--title",
                "冒烟计划标题",
                "--topic",
                "smoke-plan",
            ]
        )
    assert rc == 0
    assert "机械 0" in out.getvalue(), f"kb.new plan 输出缺「机械 0」收录断言: {out.getvalue()}"

    created = list((mb / "plans").glob("*-plan-smoke-plan.html"))
    assert len(created) == 1, f"应建出且只建出一件计划: {created}"
    text = created[0].read_text(encoding="utf-8")
    assert '<meta name="doc-status" content="Open">' in text
    assert '<meta name="doc-topic" content="smoke-plan">' in text
    assert "color-scheme: dark" in text
    assert checker.validate_file(created[0], "plan"), "建后应残留 SLOT (待填) —— 守卫靠它拦「没填完」"
    _fill_slots(created[0])
    assert checker.validate_file(created[0], "plan") == [], f"填完必须绿: {checker.validate_file(created[0], 'plan')}"

    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        rc = new_doc.main(
            [
                "--root",
                str(tmp_path),
                "--mb-dir",
                str(mb),
                "task",
                "--title",
                "冒烟档案标题",
                "--topic",
                "backend-smoke",
            ]
        )
    assert rc == 0
    assert "机械 0" in out.getvalue(), f"kb.new task 输出缺「机械 0」收录断言: {out.getvalue()}"

    task = list((mb / "tasks").glob("*-backend-smoke.md"))
    assert len(task) == 1, f"应建出且只建出一份档案: {task}"
    text = task[0].read_text(encoding="utf-8")
    assert "**Status:** In Progress" in text
    assert "**Summary:** 冒烟档案标题" in text, "Summary 应由 --title 预填 (裁定 A1)"
    assert "**Topics:** backend-smoke" in text
    assert re.match(r"^\d{2}-\d{2}-\d{2}-", task[0].name), "档案文件名应是 YY-MM-DD-<slug>.md (日期到天, 不带时分)"
    _fill_slots(task[0])
    assert checker.validate_file(task[0], "task") == [], f"填完必须绿: {checker.validate_file(task[0], 'task')}"


def test_new_doc_refuses_slice_and_duplicates(tmp_path: Path, monkeypatch) -> None:
    """拒绝路径全 fail-fast: slice 族指路 kb.wrap / 重复建幂等拒绝 / 坏 topic 与坏领域当场拒
    (之后假定输入合法 —— 黄金法则 fail-fast)。--refs 的拒绝路径已随 D4 消失 (P2 起自动
    双向补链), 其 fail-fast 由 test_new_doc_refs_auto_chains_bidirectionally 覆盖。
    重复建断言冻结 timekit.now (CI 偶发红 26-10-17): plan 文件名带分钟级戳 (`%y-%m-%d-%H%M`),
    幂等拒绝靠撞同名 —— 真墙钟两次调用跨分钟 = 文件名不同永不撞名, 与平台无关的时刻竞态;
    生产幂等语义 (同路径拒绝) 没破, 是用例没钉住「同路径」的前提。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    import timekit  # 必须在 helper 之后 —— helper 负责把 SKILL_SCRIPTS 插进 sys.path
    frozen = timekit.now()
    monkeypatch.setattr(timekit, "now", lambda: frozen)
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def run(*extra: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = new_doc.main(["--root", str(tmp_path), "--mb-dir", str(mb), *extra])
        return rc, out.getvalue(), err.getvalue()

    rc, _, err = run("slice", "--title", "x", "--topic", "y")
    assert rc == 1 and "kb.wrap" in err, f"slice 族必须拒绝并指路 kb.wrap: {err}"

    rc, _, err = run("task", "--title", "x", "--topic", "Backend_Smoke")
    assert rc == 1 and "kebab" in err, f"坏 topic (非 kebab) 必须拒绝: {err}"

    rc, _, err = run("task", "--title", "x", "--topic", "unknown-domain-slug")
    assert rc == 1 and "领域枚举" in err, f"坏领域必须拒绝: {err}"

    assert run("plan", "--title", "重复计划", "--topic", "dup-plan")[0] == 0
    rc, _, err = run("plan", "--title", "重复计划", "--topic", "dup-plan")
    assert rc == 1 and "已存在" in err, f"同路径重复建必须幂等拒绝: {err}"


def test_new_doc_task_domain_is_longest_prefix_match(tmp_path: Path) -> None:
    """领域段 = **最长前缀匹配**的枚举项, 不是首段切分 (P1 缺陷, 26-10-17 P2 补)。

    领域枚举自身可含短横线 (`memory-bank`): 首段切分 `topic.split("-", 1)[0]` 会把
    `memory-bank-xxx` 切出 `memory` —— 枚举里的 `memory-bank` 永远不可达。本测试钉住
    三类: ① 连字符领域可建 ② 前缀撞名 (`memory-` 开头的非领域) 不得被误收
    ③ 真坏领域仍 fail-fast; 裸领域 topic (topic == 枚举项) 沿用 P1 行为照收。
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def run(topic: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = new_doc.main(
                [
                    "--root",
                    str(tmp_path),
                    "--mb-dir",
                    str(mb),
                    "task",
                    "--title",
                    "领域回归",
                    "--topic",
                    topic,
                ]
            )
        return rc, out.getvalue(), err.getvalue()

    rc, _, err = run("memory-bank-doc-pipeline")
    assert rc == 0, f"连字符领域 memory-bank 必须可建 (P1 首段切分缺陷): {err}"
    created = list((mb / "tasks").glob("*-memory-bank-doc-pipeline.md"))
    assert len(created) == 1, f"应建出且只建出一份档案: {created}"
    assert "**Topics:** memory-bank-doc-pipeline" in created[0].read_text(encoding="utf-8")

    rc, _, err = run("memory-foo")
    assert rc == 1 and "领域枚举" in err, f"memory- 开头的非领域必须拒 (最长前缀不得误收): {err}"

    rc, _, err = run("memory-bank")
    assert rc == 0, f"裸领域 topic (topic == 枚举项) 沿用 P1 行为照收: {err}"

    rc, _, err = run("webui-bar")
    assert rc == 0, f"单词领域回归不得破: {err}"

    rc, _, err = run("nosuch-slug")
    assert rc == 1 and "领域枚举" in err, f"真坏领域必须拒: {err}"


def test_wrap_creates_zero_slot_slice_and_updates(tmp_path: Path) -> None:
    """建切片零 SLOT 即合规 (§5.3 判断剩余 0, 裁定 A6); 二次调用抬最后活动 + 追加 R 行;
    同专题档案抬 Updated + 进度日志日期行 (A5: 日期属派生面, 轮内不逐行写)。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    wrap = _wrap()
    checker = _doc_templates()
    new_doc = _new_doc()
    import timekit  # 必须在 helper 之后 —— helper 负责把 SKILL_SCRIPTS 插进 sys.path

    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def wrap_run(topic: str, did: str) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = wrap.main(["--root", str(tmp_path), "--mb-dir", str(mb), "--topic", topic, "--did", did])
        return rc

    assert wrap_run("wrap-slug", "本轮做了什么") == 0
    created = list((mb / "activeContext").glob("*-wrap-slug.md"))
    assert len(created) == 1, f"应建出且只建出一张切片: {created}"
    assert checker.validate_file(
        created[0], "slice"
    ) == [], (f"kb.wrap 建的切片必须零 SLOT 即合规 (判断剩余 0): {checker.validate_file(created[0], 'slice')}")
    text = created[0].read_text(encoding="utf-8")
    assert "**R0(" in text and "> 最后活动:" in text

    assert wrap_run("wrap-slug", "第二轮") == 0
    text = created[0].read_text(encoding="utf-8")
    assert "**R1(" in text, "二次调用应追加 R1 行 (编号 = 现有最大 + 1)"

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        assert new_doc.main(
            [
                "--root",
                str(tmp_path),
                "--mb-dir",
                str(mb),
                "task",
                "--title",
                "归档专题",
                "--topic",
                "backend-wrap-slug",
            ]
        ) == 0
    archive = next((mb / "tasks").glob("*-backend-wrap-slug.md"))
    assert wrap_run("backend-wrap-slug", "收尾一轮") == 0
    text = archive.read_text(encoding="utf-8")
    today = timekit.now().strftime("%Y-%m-%d")
    assert f"**Updated:** {today}" in text, "同专题档案应抬 Updated 到今天"
    assert any(line.startswith(f"- {today} ") for line in text.split("\n")), ("档案进度日志应追加带日期的一行 (A5)")


def test_checker_three_mutations_judged_red(tmp_path: Path) -> None:
    """红绿双验 (计划 §06): 填完 = 基准绿; 三类突变逐类判红; 每类还原后复绿。

    三类 = 删状态行 / 留 SLOT / 词表外值 —— 分别对应「头部字段缺失」「填空未完成」
    「状态词漂移」三个失败模式, 守卫少了任何一类, 那个模式就没人拦。
    """
    new_doc = _new_doc()
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    import io
    from contextlib import redirect_stderr, redirect_stdout

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        assert new_doc.main(
            [
                "--root",
                str(tmp_path),
                "--mb-dir",
                str(mb),
                "task",
                "--title",
                "突变档案",
                "--topic",
                "backend-mutant",
            ]
        ) == 0
    task = next((mb / "tasks").glob("*-backend-mutant.md"))
    _fill_slots(task)
    original = task.read_text(encoding="utf-8")
    assert checker.validate_file(task, "task") == [], "填完必须绿 —— 否则红绿双验失去基准"

    mutations = {
        "删状态行": lambda t: "\n".join(line for line in t.split("\n") if not line.startswith("**Status:**")),
        "词表外值": lambda t: t.replace("**Status:** In Progress", "**Status:** Doing"),
        "留 SLOT": lambda t: t.replace("已填内容", "<!-- SLOT: 又留了一个 -->", 1),
    }
    for name, mutate in mutations.items():
        task.write_text(mutate(original), encoding="utf-8")
        problems = checker.validate_file(task, "task")
        assert problems, f"突变「{name}」必须判红: {problems}"
        task.write_text(original, encoding="utf-8")
        assert checker.validate_file(task, "task") == [], f"还原「{name}」后必须复绿"


def test_checker_freeze_line_exempts_stock(tmp_path: Path) -> None:
    """冻结线语义 (D3 存量冻结只拦新增): 线之前的缺陷件豁免, 之后入检查面判红。

    档案族命名只到天 (YY-MM-DD), 文件名分不出当天线前/线后 —— 口径取「日期 ≥ 冻结日」
    入检查面 (既有当天档案均合规); plan/report/baseline 同按**文件名 stamp 前缀**圈面
    (26-10-31 修: 不读文件自身 meta —— 缺头部新件不再逃逸, 见事故回归阵)。
    坑档/进展件命名无时间戳, 不在扫描面 (既有守卫兜底)。
    """
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    (mb / "tasks").mkdir(parents=True)
    (mb / "plans").mkdir(parents=True)
    (mb / "reports").mkdir(parents=True)
    (mb / "testing" / "baselines").mkdir(parents=True)

    defective_md = "# 缺状态行的档案\n\n**Added:** 2026-01-01\n"
    (mb / "tasks" / "26-10-16-backend-old.md").write_text(defective_md, encoding="utf-8")
    (mb / "tasks" / "26-10-17-backend-new.md").write_text(defective_md, encoding="utf-8")

    defective_plan = (
        '<html><head><meta name="doc-type" content="plan">'
        '<meta name="doc-status" content="Draft">'
        '<meta name="doc-added" content="26-10-17-0735">'
        '<meta name="doc-updated" content="26-10-17-0735">'
        "</head><body></body></html>"
    )
    new_plan = defective_plan.replace("0735", "0740")
    (mb / "plans" / "26-10-17-0735-plan-old.html").write_text(defective_plan, encoding="utf-8")
    (mb / "plans" / "26-10-17-0740-plan-new.html").write_text(new_plan, encoding="utf-8")

    # report: doc-type=report + doc-status 表外值 Draft (出厂应为 Done, 但判红的是词表越界)
    defective_report = defective_plan.replace('content="plan"', 'content="report"')
    new_report = defective_report.replace("0735", "0740")
    (mb / "reports" / "26-10-17-0735-report-old.html").write_text(defective_report, encoding="utf-8")
    (mb / "reports" / "26-10-17-0740-report-new.html").write_text(new_report, encoding="utf-8")

    # baseline: 缺 `> 摘要:` 与 `> 基线时间:` (头部字段判红), 命名带时分
    defective_baseline = "# 3498 passed —— 缺字段的基线\n\n## 验收数字\n\nx\n"
    (mb / "testing" / "baselines" / "26-10-17-0735-base-old.md").write_text(defective_baseline, encoding="utf-8")
    (mb / "testing" / "baselines" / "26-10-17-0740-base-new.md").write_text(defective_baseline, encoding="utf-8")

    problems, checked = checker.check_new_faces(tmp_path, mb)

    assert checked == 4, f"检查面应恰好 4 件 (档案/plan/report/baseline 各线后一件): {checked}"
    assert not any("backend-old" in p for p in problems), "冻结线之前的缺陷档案必须豁免 (存量)"
    assert not any("plan-old" in p for p in problems), "doc-added 在线之前的 plan 必须豁免 (存量)"
    assert not any("report-old" in p for p in problems), "doc-added 在线之前的 report 必须豁免 (存量)"
    assert not any("base-old" in p for p in problems), "stamp 在线之前的 baseline 必须豁免 (存量)"
    assert any("backend-new" in p for p in problems), "线后档案的缺陷必须判红"
    assert any("plan-new" in p for p in problems), "线后 plan 的缺陷必须判红"
    assert any("report-new" in p for p in problems), "线后 report 的词表外值必须判红"
    assert any("base-new" in p for p in problems), "线后 baseline 的缺头部字段必须判红"


def test_checker_catches_new_plan_missing_doc_added(tmp_path: Path) -> None:
    """事故回归阵 (26-10-31, RM02-RM10 九件无状态计划): 手写新 plan 缺 doc-added 必判红。

    原圈面按**文件自身 doc-added** 决定扫不扫 —— 缺头部的手写新件整件逃逸 (豁免自噬:
    越缺字段越查不到)。修复后圈面 = 文件名 stamp 前缀, 与文件招供无关; 本阵钉住
    「头部残缺 ≠ 免检」, 防圈面判据回退。
    """
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    (mb / "plans").mkdir(parents=True)

    handmade = (
        '<html><head><meta charset="UTF-8">'
        '<meta name="doc-topic" content="handmade-escape">'
        "</head><body></body></html>"
    )
    (mb / "plans" / "26-10-31-0927-plan-real-rm99.html").write_text(handmade, encoding="utf-8")

    problems, checked = checker.check_new_faces(tmp_path, mb)

    assert checked == 1, f"缺 doc-added 的新件必须入检查面 (不再整件跳过): {checked}"
    assert any("rm99" in p for p in problems), f"手写新件缺头部必须判红: {problems}"
    assert any("doc-status" in p for p in problems), "缺 doc-status 要在问题清单里"
    assert any("doc-added" in p for p in problems), "缺 doc-added 要在问题清单里"


def test_family_registry_matches_templates() -> None:
    """模板烤进去的出厂值必须与 `_common.FAMILIES` 同源 (计划 §01 设计底线)。

    先例: `test_skill_cap_table_matches_cap_policy` 钉 cap 表 —— 模板与注册表各自演化时,
    命令会照模板建件、守卫照注册表判红, 两边都"绿"但建出来的件过不了检。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    fams = _common.FAMILIES
    templates = SKILL_SCRIPTS.parent / "templates"
    for name, spec in fams.items():
        assert (templates / spec.template).is_file(), f"{name} 族模板缺失: {spec.template}"

    plan_tpl = (templates / fams["plan"].template).read_text(encoding="utf-8")
    assert f'content="{fams["plan"].default_status}"' in plan_tpl, "plan 模板的 doc-status 必须 == 注册表出厂状态"
    assert 'content="plan"' in plan_tpl, "plan 模板的 doc-type 必须与族名一致"

    task_tpl = (templates / fams["task"].template).read_text(encoding="utf-8")
    assert f"**Status:** {fams['task'].default_status}" in task_tpl, "task 模板的 Status 行必须 == 注册表出厂状态"

    # P3: report 出厂即终态 (doc-forms 状态词节: report 恒 Done —— 快照完成即冻结)
    report_tpl = (templates / fams["report"].template).read_text(encoding="utf-8")
    assert f'content="{fams["report"].default_status}"' in report_tpl, "report 模板的 doc-status 必须 == 注册表出厂状态 (Done)"
    assert 'content="report"' in report_tpl, "report 模板的 doc-type 必须与族名一致"

    # P3: 三行头族的触发词走 --triggers 参数 (裁定 A7 参数分支; 头部区零 SLOT 契约)
    for fam in ("pitfall", "progress"):
        tpl = (templates / fams[fam].template).read_text(encoding="utf-8")
        assert "> 触发: @@TRIGGERS@@" in tpl, f"{fam} 模板必须留触发词占位 (由 --triggers 填, 头部区不留 SLOT)"

    # P3: baseline 模板 H1 含 --total 占位 + 基线时间占位 (排序键, 回退用文件名前缀)
    baseline_tpl = (templates / fams["baseline"].template).read_text(encoding="utf-8")
    assert "# @@TOTAL@@ —— @@TITLE@@" in baseline_tpl, "baseline 模板 H1 必须含 --total 占位 (裁定 A4)"
    assert "> 基线时间: @@" in baseline_tpl, "baseline 模板必须留基线时间占位 (排序键)"

    # 词表单点: 族的 statuses 就是那两个单点**本身** (is, 不是副本)
    assert fams["plan"].statuses is _common.DOC_STATUSES
    assert fams["task"].statuses is _common.TASK_STATUSES
    assert fams["report"].statuses is _common.DOC_STATUSES, "report 与 plan 共用 5 词表单点"
    assert fams["slice"].statuses == (), "切片族无状态词 (三行头不带状态)"
    for fam in ("pitfall", "baseline", "progress"):
        assert fams[fam].statuses == (), f"{fam} 族无状态词"

    # 坑档族的子目录选择器 = 7 类枚举单点 (is 身份断言, 同 statuses 纪律)
    assert fams["pitfall"].subdir_values is _common.PITFALL_CLASSES, "坑档类枚举必须 import 单点, 不造副本"
    assert fams["pitfall"].subdir_flag == "class", "坑档子目录选择器 = --class"

    # 头部区零 SLOT (计划 §05 渲染正确性契约): 机器字段由命令填, SLOT 只允许出现在正文区
    checker = _doc_templates()
    for name, spec in fams.items():
        head = checker._head_region((templates / spec.template).read_text(encoding="utf-8"))
        head_slots = re.findall(r"<!--\s*SLOT:", head)
        assert not head_slots, f"{name} 模板头部区不得有 SLOT 标记 (机器字段必须由命令填): {len(head_slots)} 处"


def test_doc_templates_checker_is_wired() -> None:
    """检查器必须挂在 kb.check 与提交闸门两侧 —— 不接线 = 没人跑 (与
    test_wording_guard_is_wired_into_kb_check / test_commit_gate_covers_kb_check 同旨)。"""
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    body = re.search(r'^\[tasks\."kb\.check"\]\n(.*?)(?=^\[|\Z)', kb_cfg, re.S | re.M)
    assert body, "kb/config.toml 里找不到 kb.check"
    assert "check_doc_templates.py --check" in body.group(1), "check_doc_templates.py --check 未挂进 kb.check"

    gate_cfg = (ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml").read_text(encoding="utf-8")
    assert "check_doc_templates.py --check" in gate_cfg, "check_doc_templates.py --check 未挂进提交闸门"


# ---------------------------------------------------------------------------
# kb.status / kb.bump / D4 反向补链 (2026-10-17 P2, 计划 26-10-17-0527)
#
# 实现与检查器在 memory-bank skill 的 `scripts/flip_status.py` / `bump_doc.py`
# (new_doc.py 的 --refs 走 D4), 本文件**在进程内 import** 它们 —— 同 P1 口径。
# 验收: 计划 §07 P2 行 ——「对 P1 临时件全链演练; 认领链双向机检绿」。
# ---------------------------------------------------------------------------


def _flip_status():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import flip_status

    return flip_status


def _bump_doc():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import bump_doc

    return bump_doc


def _gen_doc_map():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_doc_map

    return gen_doc_map


def _kb_clock():
    """实现侧的时间单点(`timekit.now()`, UTC+8 墙钟 —— `kb.status`/`kb.bump` 都取自它)。

    断言必须与实现**同源取时**, 不能写死日期: 本文件曾把运行当天 (2026-10-17) 写成字面量,
    过零点必红, 与业务无关 (issue 26-10-18-0608-test-memory-bank-test-hardcoded-today)。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import timekit

    return timekit.now()


def _p2_fixture(tmp_path: Path) -> Path:
    """P2 夹具: 最小可跑的 memory-bank (plans / tasks / activeContext / issues)。"""
    mb = tmp_path / "memory-bank"
    for sub in ("plans", "tasks", "activeContext", "issues"):
        (mb / sub).mkdir(parents=True)
    return mb


def _write_plan(mb: Path, name: str = "26-10-17-0900-plan-p2.html") -> Path:
    path = mb / "plans" / name
    path.write_text(
        """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>P2 冒烟计划</title>
<meta name="doc-type" content="plan">
<meta name="doc-topic" content="p2-topic">
<meta name="doc-status" content="Open">
<meta name="doc-added" content="26-10-17-0900">
<meta name="doc-updated" content="26-10-17-0900">
</head>
<body>
<div class="meta">
  <b>doc-added</b> 26-10-17-0900 · <b>doc-updated</b> 26-10-17-0900 · <b>doc-status</b> Open · <b>载体</b> 单文件 HTML(dark)<br>
</div>
<h2><span class="no">§10</span>变更记录</h2>
<ul>
  <li><span class="tag">R0 · 26-10-17-0900</span> 初版。</li>
</ul>
</body>
</html>
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_task(mb: Path, name: str = "26-10-17-backend-p2.md") -> Path:
    path = mb / "tasks" / name
    path.write_text(
        """# 26-10-17-backend-p2 — P2 冒烟档案

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-17
**Summary:** P2 冒烟档案标题
**Topics:** backend-p2

## 原始请求

x
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_slice(mb: Path, name: str = "26-10-17-0900-p2-topic.md") -> Path:
    path = mb / "activeContext" / name
    path.write_text(
        """# P2 冒烟切片

> 摘要: 冒烟
> 最后活动: 2026-10-17 09:00

## 产出

x
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_issue(mb: Path, name: str = "26-10-17-0900-bug-p2.html") -> Path:
    path = mb / "issues" / name
    path.write_text(
        '<html><head>\n<meta name="issue-status" content="Open">\n<meta name="doc-topic" content="p2-bug">\n</head><body>x</body></html>\n',
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_flip_status_flips_bumps_and_fails_fast(tmp_path: Path) -> None:
    """kb.status: 计划/档案翻转 + 抬时间戳 + 重建索引; 幂等不抬戳; 五类拒绝全 fail-fast;
    终态带条件提醒; 输出含「机械 0」收录断言 (§5.3 / §5.4)。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    flip = _flip_status()
    mb = _p2_fixture(tmp_path)
    plan = _write_plan(mb)
    task = _write_task(mb)
    _write_slice(mb)
    _write_issue(mb)

    def run(path: str, to: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = flip.main(["--root", str(tmp_path), "--mb-dir", str(mb), path, to])
        return rc, out.getvalue(), err.getvalue()

    # --- 计划翻转: 状态 + doc-updated 都抬, 索引重建, 契约输出
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "In Progress")
    assert rc == 0, err
    assert "doc-status Open → In Progress" in out and "已重建索引" in out and "机械 0" in out, out
    assert out.count("剩余人工") == 1, "契约行只打一次"
    ptext = plan.read_text(encoding="utf-8")
    assert '<meta name="doc-status" content="In Progress">' in ptext
    assert '<meta name="doc-updated" content="26-10-17-0900">' not in ptext, "doc-updated 应被抬"
    assert "· <b>doc-status</b> In Progress ·" in ptext, "正文 .meta 镜像行的状态词应同改"
    assert "<b>doc-updated</b> 26-10-17-0900" not in ptext, "正文 .meta 镜像行的 doc-updated 应同抬"

    # --- 终态: 条件提醒 (同专题切片迁出), 计数行 条件 1
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "Done")
    assert rc == 0 and "条件 1" in out and "切片" in out and "p2-topic" in out, out

    # --- 同状态幂等: 不抬时间戳不重建索引 (黄金法则: 幂等无副作用)
    before = plan.read_text(encoding="utf-8")
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "Done")
    assert rc == 0 and "幂等" in out and "已重建索引" not in out, out
    assert plan.read_text(encoding="utf-8") == before, "幂等翻转不得改文件"

    # --- 五类拒绝全 fail-fast (原因打在输出里)
    rc, _, err = run("plans/26-10-17-0900-plan-p2.html", "Draft")
    assert rc == 1 and "词表" in err, f"词表外值必须拒绝: {err}"
    rc, _, err = run("activeContext/26-10-17-0900-p2-topic.md", "Done")
    assert rc == 1 and "kb.wrap" in err, f"切片无状态, 必须拒绝并指路 kb.wrap: {err}"
    rc, _, err = run("issues/26-10-17-0900-bug-p2.html", "Done")
    assert rc == 1 and "create-issue" in err, f"issue 有自己的词表与索引, 必须拒绝并指路: {err}"
    rc, _, err = run("memory-bank/nope.md", "Done")
    assert rc == 1 and "文件不存在" in err, f"不存在的路径必须拒绝: {err}"

    # --- 档案翻转: **Status:** + **Updated:** + 终态 Summary 收口提醒
    rc, out, err = run("tasks/26-10-17-backend-p2.md", "Done")
    assert rc == 0 and "Status In Progress → Done" in out and "Summary 收口" in out, out
    ttext = task.read_text(encoding="utf-8")
    today = _kb_clock().strftime("%Y-%m-%d")  # 与实现同源取时(见 _kb_clock)
    assert "**Status:** Done" in ttext and f"**Updated:** {today}" in ttext
    rc, _, err = run("tasks/26-10-17-backend-p2.md", "Archived")
    assert rc == 1 and "词表" in err, f"档案 4 词表外值必须拒绝: {err}"


def test_bump_doc_appends_changelog_and_fails_fast(tmp_path: Path) -> None:
    """kb.bump: 计划 R 行追加 (编号递推/已有行零触碰/note 转义) + doc-updated 抬;
    档案抬 Updated / 切片抬最后活动; 无变更记录段 fail-fast; 输出含「机械 0」。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    bump = _bump_doc()
    mb = _p2_fixture(tmp_path)
    plan = _write_plan(mb)
    task = _write_task(mb)
    slice_ = _write_slice(mb)
    _write_issue(mb)

    def run(path: str, note: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = bump.main(["--root", str(tmp_path), "--mb-dir", str(mb), path, "--note", note])
        return rc, out.getvalue(), err.getvalue()

    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "R1: 加冒烟")
    assert rc == 0 and "R1" in out and "机械 0" in out and "已重建索引" in out, out
    ptext = plan.read_text(encoding="utf-8")
    assert '<li><span class="tag">R1 · ' in ptext and "R1: 加冒烟" in ptext
    assert ptext.count("R0 · 26-10-17-0900") == 1, "已有 R 行零触碰"
    assert '<meta name="doc-updated" content="26-10-17-0900">' not in ptext, "doc-updated 应被抬"
    assert "<b>doc-updated</b> 26-10-17-0900" not in ptext, "正文 .meta 镜像行应同抬"

    # 二次 bump → R2 (编号递推 = 段内最大 + 1)
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "R2: 再改")
    assert rc == 0 and "R2" in out, out
    ptext = plan.read_text(encoding="utf-8")
    assert ptext.count('<span class="tag">R0 · ') == 1 and ptext.count('<span class="tag">R1 · ') == 1
    assert ptext.count('<span class="tag">R2 · ') == 1

    # note 自动 HTML 转义 (值里出现 < > & 不破坏 meta/结构)
    rc, _, err = run("plans/26-10-17-0900-plan-p2.html", "修 a<b & c>d")
    assert rc == 0, err
    assert "修 a&lt;b &amp; c&gt;d" in plan.read_text(encoding="utf-8")

    # 档案抬 Updated / 切片抬最后活动 (期望值取自实现的时间单点, 不写死日期)
    rc, out, err = run("tasks/26-10-17-backend-p2.md", "进展一句")
    assert rc == 0 and "Updated" in out, out
    assert f"**Updated:** {_kb_clock().strftime('%Y-%m-%d')}" in task.read_text(encoding="utf-8")
    rc, out, err = run("activeContext/26-10-17-0900-p2-topic.md", "进展一句")
    assert rc == 0 and "最后活动" in out, out
    assert f"> 最后活动: {_kb_clock().strftime('%Y-%m-%d %H:%M')}" in slice_.read_text(encoding="utf-8")

    # 无变更记录段的件 → fail-fast 指路 (多数报告无段, 不猜位置硬塞)
    # (reports/ 目录可能已被索引重建创建 —— mkdir(exist_ok=True))
    report = mb / "reports"
    report.mkdir(exist_ok=True)
    bad = report / "26-10-17-0900-report-nosec.html"
    bad.write_text(
        '<html><head><meta name="doc-updated" content="26-10-17-0900"></head><body>x</body></html>', encoding="utf-8"
    )
    rc, _, err = run("reports/26-10-17-0900-report-nosec.html", "x")
    assert rc == 1 and "变更记录" in err, f"无变更记录段必须拒绝并指路: {err}"
    assert '<meta name="doc-updated" content="26-10-17-0900">' in bad.read_text(encoding="utf-8"), "fail-fast 不得改文件"

    # issue → 拒绝指路 create-issue
    rc, _, err = run("issues/26-10-17-0900-bug-p2.html", "x")
    assert rc == 1 and "create-issue" in err, err


def test_new_doc_refs_auto_chains_bidirectionally(tmp_path: Path) -> None:
    """D4 反向认领 (计划 §08): --refs 自动双向补链 —— 本件写 doc-refs / **Refs:**,
    目标件 (HTML/md 各类载体) 自动反向声明, 幂等合并; 坏 refs 全 fail-fast 不落半文件。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    mb = _p2_fixture(tmp_path)
    target_task = _write_task(mb)
    pit_dir = mb / "pitfalls" / "git"
    pit_dir.mkdir(parents=True)
    target_pit = pit_dir / "sync-pull.md"
    target_pit.write_text("# 坑标题\n\n> 摘要: abc\n> 触发: git, push\n\n### entry\n", encoding="utf-8", newline="\n")
    target_issue = _write_issue(mb)
    target_slice = _write_slice(mb)

    def run(*extra: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = new_doc.main(["--root", str(tmp_path), "--mb-dir", str(mb), *extra])
        return rc, out.getvalue(), err.getvalue()

    # 四类目标 (仓库根相对) —— 本件正向声明 + 目标件反向声明
    rc, out, err = run(
        "plan", "--title", "引用计划", "--topic", "refs-plan", "--refs", "memory-bank/tasks/26-10-17-backend-p2.md,"
        "memory-bank/pitfalls/git/sync-pull.md,"
        "memory-bank/issues/26-10-17-0900-bug-p2.html,"
        "memory-bank/activeContext/26-10-17-0900-p2-topic.md"
    )
    assert rc == 0, err
    plan = list((mb / "plans").glob("*-plan-refs-plan.html"))
    assert len(plan) == 1
    ptext = plan[0].read_text(encoding="utf-8")
    assert '<meta name="doc-refs" content="memory-bank/tasks/26-10-17-backend-p2.md, ' \
           'memory-bank/pitfalls/git/sync-pull.md, memory-bank/issues/26-10-17-0900-bug-p2.html, ' \
           'memory-bank/activeContext/26-10-17-0900-p2-topic.md">' in ptext, ptext[:600]
    plan_rel = f"memory-bank/plans/{plan[0].name}"
    assert f"**Refs:** {plan_rel}" in target_task.read_text(encoding="utf-8")
    assert f"**Refs:** {plan_rel}" in target_pit.read_text(encoding="utf-8")
    assert f'<meta name="doc-refs" content="{plan_rel}">' in target_issue.read_text(encoding="utf-8")
    assert f"**Refs:** {plan_rel}" in target_slice.read_text(encoding="utf-8")
    assert out.count("已双向补链") == 4, f"四类目标各一行: {out}"

    # mb 相对形态 + 幂等合并 (同目标再来一件 → 目标已有反向声明, 合并为逗号列表)
    rc, out, err = run(
        "task", "--title", "引用档案", "--topic", "backend-refs-task", "--refs", "tasks/26-10-17-backend-p2.md"
    )
    assert rc == 0, err
    task = list((mb / "tasks").glob("*-backend-refs-task.md"))
    assert len(task) == 1
    assert "**Refs:** memory-bank/tasks/26-10-17-backend-p2.md" in task[0].read_text(encoding="utf-8")
    refline = [ln for ln in target_task.read_text(encoding="utf-8").splitlines() if ln.startswith("**Refs:**")]
    assert len(refline) == 1 and refline[0].count(",") == 1, f"目标反向声明应合并为一行两条: {refline}"

    # 坏 refs → fail-fast 且不落半文件 (库外目标用根级 AGENTS.md 探测: 存在但不在 memory-bank 内)
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    for bad_refs, why in (("tasks/nope.md", "目标不存在"), ("AGENTS.md", "不在 memory-bank 下"), ("tasks/_index.md", "生成物")):
        rc, _, err = run("plan", "--title", "坏", "--topic", "bad-refs", "--refs", bad_refs)
        assert rc == 1 and why in err, f"{bad_refs} 必须拒绝 ({why}): {err}"
        assert not list((mb / "plans").glob("*-plan-bad-refs.html")), "fail-fast 不得落半文件"

    # 无 --refs → 与 P1 行为一致 (无 doc-refs meta, 无反向补链行)
    rc, out, err = run("plan", "--title", "无引用", "--topic", "no-refs")
    assert rc == 0, err
    noref = list((mb / "plans").glob("*-plan-no-refs.html"))
    assert "doc-refs" not in noref[0].read_text(encoding="utf-8")
    assert "已双向补链" not in out


def test_p2_full_chain_drill(tmp_path: Path) -> None:
    """P2 验收 (计划 §07): 对临时件全链演练 —— kb.new(--refs) → 填空 → kb.status → kb.bump
    → 认领链双向机检 (gen_doc_map --check) 绿; 改过的件再过新增面守卫仍绿。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc, flip, bump = _new_doc(), _flip_status(), _bump_doc()
    checker, docmap = _doc_templates(), _gen_doc_map()
    mb = _p2_fixture(tmp_path)

    def run(mod, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = mod.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        return rc, out.getvalue(), err.getvalue()

    # ① 先建档案, 再建计划并 --refs 档案 (D4 双向补链)
    rc, _, err = run(new_doc, ["task", "--title", "演练档案", "--topic", "docs-drill"])
    assert rc == 0, err
    task = list((mb / "tasks").glob("*-docs-drill.md"))
    assert len(task) == 1
    task_rel = f"memory-bank/tasks/{task[0].name}"
    rc, out, err = run(new_doc, ["plan", "--title", "演练计划", "--topic", "drill-topic", "--refs", task_rel])
    assert rc == 0, err
    plan = list((mb / "plans").glob("*-plan-drill-topic.html"))
    assert len(plan) == 1
    assert "已双向补链" in out, f"D4 应打印双向补链行: {out}"

    # ② 填空 (agent 的一次编辑)
    _fill_slots(plan[0])
    _fill_slots(task[0])
    assert checker.validate_file(plan[0], "plan") == [], "填空后计划必须过新增面守卫"
    assert checker.validate_file(task[0], "task") == [], "填空后档案必须过新增面守卫"

    # ③ kb.status 翻转 (终态)
    rc, out, err = run(flip, [str(plan[0].relative_to(tmp_path)), "In Progress"])
    assert rc == 0 and "已翻转" in out, out
    rc, out, err = run(flip, [f"memory-bank/plans/{plan[0].name}", "Done"])
    assert rc == 0 and "条件 1" in out, out
    rc, out, err = run(flip, [task_rel, "Done"])
    assert rc == 0 and "Summary 收口" in out, out

    # ④ kb.bump 改版记录 (计划有变更记录段)
    rc, out, err = run(bump, [f"memory-bank/plans/{plan[0].name}", "--note", "R1: 演练改版"])
    assert rc == 0 and "R1" in out, out

    # ⑤ 认领链双向机检绿 (计划 §07 P2 验收判据; gen_doc_map.main() 只读 sys.argv,
    #    进程内直调它的 check 函数 —— 与既有守卫直调 validate_file 同做法)
    docmap = _gen_doc_map()
    items = docmap.collect(mb)
    problems = docmap.check_claim_chain(items, tmp_path, mb)
    assert problems == [], f"认领链双向机检必须绿: {problems}"
    assert docmap.check_topics(items) == 0, "演练件的跨形态主键必须齐"
    assert docmap.check_status_vocabulary(items) == 0, "演练件状态词必须在 5 词表内"

    # ⑥ 红绿双验 (§06): 删掉目标件的反向声明 = 人工造单向链 → 机检必须红 (证明绿不是恒绿);
    #    还原 → 复绿
    ttext = task[0].read_text(encoding="utf-8")
    plan_rel = f"memory-bank/plans/{plan[0].name}"
    task[0].write_text(ttext.replace(f"**Refs:** {plan_rel}", ""), encoding="utf-8")
    broken = docmap.check_claim_chain(docmap.collect(mb), tmp_path, mb)
    assert any("反向声明" in p for p in broken), f"单向链必须判红 (判据恒绿 = 没守): {broken}"
    task[0].write_text(ttext, encoding="utf-8")
    assert docmap.check_claim_chain(docmap.collect(mb), tmp_path, mb) == [], "还原后必须复绿"

    # ⑦ 改过的件再过新增面守卫仍绿 (翻转/bump 没破坏形态)
    assert checker.validate_file(plan[0], "plan") == [], "翻转+bump 后的计划必须仍过守卫"
    assert checker.validate_file(task[0], "task") == [], "翻转后的档案必须仍过守卫"


def test_kb_status_and_bump_are_registered() -> None:
    """kb.status / kb.bump 已收录进 .commands/kb (收录协议: 不接线 = 没人跑;
    与 test_doc_templates_checker_is_wired 同旨)。when 与 note 是收录协议必填项。"""
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    for task_id, script in (("kb.status", "flip_status.py"), ("kb.bump", "bump_doc.py")):
        body = re.search(r'^\[tasks\."%s"\]\n(.*?)(?=^\[|\Z)' % re.escape(task_id), kb_cfg, re.S | re.M)
        assert body, f"{task_id} 未收录进 .commands/kb (收录协议)"
        assert script in body.group(1), f"{task_id} 的 run 必须指到 {script}"
        assert 'when    = "' in body.group(1), f"{task_id} 缺 when (收录协议必填: 下次能被发现的唯一线索)"
        assert 'note    = "' in body.group(1), f"{task_id} 缺 note (收录协议必填: 环境陷阱的判据)"


# ---------------------------------------------------------------------------
# 二期四族 pitfall/report/baseline/progress 与守卫扩面 (2026-10-17 P3, 计划 26-10-17-0527)
#
# 实现 = `_common.FAMILIES` 扩行 + `templates/` 四件 + new_doc 分派 +
# check_doc_templates 扩扫描面; 进程内 import, 同 P1 口径。
# 验收: 计划 §07 P3 行 —— 四族模板(族注册表扩行) + 文档回写; §06 红绿双验口径。
# ---------------------------------------------------------------------------


def _p3_family_paths(mb: Path) -> dict[str, Path]:
    """P3 冒烟四件的落点 (同 build 顺序)。"""
    return {
        "pitfall": mb / "pitfalls" / "kb" / "smoke-pitfall.md",
        "report": next((mb / "reports").glob("*-report-smoke-report.html")),
        "baseline": next((mb / "testing" / "baselines").glob("*-smoke-baseline.md")),
        "progress": mb / "progress" / "smoke-progress.md",
    }


def test_new_doc_creates_phase2_families(tmp_path: Path) -> None:
    """P3 四族真建冒烟 (计划 §06): 坑档 (`--class` 7 类 + `--triggers`, 头部零 SLOT 契约) /
    报告 (出厂即 Done 终态) / 基线 (`--total` 誊写 + 基线时间排序键) / 进展件 (三行头)。

    每族: rc=0 + 「机械 0」收录断言 + 头部字段由参数/时间戳派生; 建后残留 SLOT 判红、
    填完判绿; 扫描面恰 2 件 (report + baseline —— 坑档/进展件命名无时间戳, 不在冻结线
    扫描面, 直接 validate_file)。
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def build(family: str, **kw) -> str:
        argv = ["--root", str(tmp_path), "--mb-dir", str(mb), family]
        for key, value in kw.items():
            argv += [f"--{key}", value]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = new_doc.main(argv)
        assert rc == 0, f"{family} 建件必须成功: {err.getvalue()}"
        assert "机械 0" in out.getvalue(), f"{family} 输出缺「机械 0」收录断言: {out.getvalue()}"
        return out.getvalue()

    build("pitfall", **{"class": "kb"}, title="冒烟坑标题", topic="smoke-pitfall", triggers="触发词1, 触发词2")
    build("report", title="冒烟报告", topic="smoke-report")
    build("baseline", title="冒烟基线", topic="smoke-baseline", total="3498 passed + 4 skipped(根)")
    build("progress", title="冒烟进展", topic="smoke-progress", triggers="触发词1")

    paths = _p3_family_paths(mb)

    # 坑档: 三行头由参数/标题派生 (摘要 = --title 预填, 裁定 A1 口径); 触发词来自 --triggers
    pitfall_text = paths["pitfall"].read_text(encoding="utf-8")
    assert pitfall_text.startswith("# 冒烟坑标题\n\n> 摘要: 冒烟坑标题\n> 触发: 触发词1, 触发词2\n")

    # 报告: 出厂即 Done 终态 (doc-forms 状态词节: report 恒 Done) + dark CSS
    report_text = paths["report"].read_text(encoding="utf-8")
    assert '<meta name="doc-type" content="report">' in report_text
    assert '<meta name="doc-status" content="Done">' in report_text
    assert "color-scheme: dark" in report_text

    # 基线: H1 = TOTAL —— 标题; 基线时间 = 排序键 (严格 YYYY-MM-DD HH:MM)
    baseline_text = paths["baseline"].read_text(encoding="utf-8")
    assert baseline_text.startswith("# 3498 passed + 4 skipped(根) —— 冒烟基线")
    assert re.search(r"^> 基线时间: \d{4}-\d{2}-\d{2} \d{2}:\d{2}$", baseline_text, re.MULTILINE)

    # 建后: 残留 SLOT 判红 (坑档/进展件不在扫描面 —— 直接 validate_file)
    assert checker.validate_file(paths["pitfall"], "pitfall"), "坑档建后应残留 SLOT (待填)"
    assert checker.validate_file(paths["progress"], "progress"), "进展件建后应残留 SLOT (待填)"
    problems, checked = checker.check_new_faces(tmp_path, mb)
    assert checked == 2, f"扫描面应恰好 2 件 (线后 report + baseline): {checked}"
    assert len(problems) == 2, f"report 与 baseline 建后残留 SLOT 应判红: {problems}"

    # 填完: 四族 validate_file 全绿 + 扫描面全绿
    for family, path in paths.items():
        _fill_slots(path)
        assert checker.validate_file(path, family) == [], f"{family} 填完必须绿: {checker.validate_file(path, family)}"
    problems, checked = checker.check_new_faces(tmp_path, mb)
    assert problems == [] and checked == 2, f"填完扫描面必须全绿: {problems}"


def test_new_doc_phase2_family_params_fail_fast(tmp_path: Path) -> None:
    """四族参数 fail-fast (黄金法则: 之后假定输入合法): 坑档缺/坏 `--class`、缺
    `--triggers`; 进展件缺 `--triggers`; 基线缺 `--total`。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def run(family: str, **kw) -> tuple[int, str]:
        argv = ["--root", str(tmp_path), "--mb-dir", str(mb), family]
        for key, value in kw.items():
            argv += [f"--{key}", value]
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = new_doc.main(argv)
        return rc, err.getvalue()

    rc, err = run("pitfall", title="x", topic="y", triggers="t")
    assert rc == 1 and "--class" in err, f"坑档缺 --class 必须拒: {err}"
    rc, err = run("pitfall", **{"class": "nope"}, title="x", topic="y", triggers="t")
    assert rc == 1 and "7 类" in err, f"坑档坏 --class 必须拒: {err}"
    rc, err = run("pitfall", **{"class": "kb"}, title="x", topic="y")
    assert rc == 1 and "--triggers" in err, f"坑档缺 --triggers 必须拒 (头部零 SLOT 契约): {err}"
    rc, err = run("progress", title="x", topic="y")
    assert rc == 1 and "--triggers" in err, f"进展件缺 --triggers 必须拒: {err}"
    rc, err = run("baseline", title="x", topic="y")
    assert rc == 1 and "--total" in err, f"基线缺 --total 必须拒 (裁定 A4): {err}"


def test_pitfall_refs_chain_bidirectionally(tmp_path: Path) -> None:
    """D4 反向认领对坑档形态 (md 锚点链的三行头分支 —— 三行头最后一个 `>` 行后插
    `**Refs:**`): 坑档正向声明 + 档案目标反向声明本坑档, 幂等。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def run(argv: list[str]) -> int:
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = new_doc.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        assert rc == 0, err.getvalue()
        return rc

    run(["task", "--title", "认领目标档案", "--topic", "backend-refs-tgt"])
    task = next((mb / "tasks").glob("*-backend-refs-tgt.md"))
    run(
        [
            "pitfall", "--class", "git", "--title", "带链坑档", "--topic", "chained-pitfall", "--triggers", "词", "--refs",
            f"memory-bank/tasks/{task.name}"
        ]
    )
    pitfall = mb / "pitfalls" / "git" / "chained-pitfall.md"

    assert f"**Refs:** memory-bank/tasks/{task.name}" in pitfall.read_text(encoding="utf-8"), \
        "坑档必须正向声明 Refs (锚点链: 三行头最后一个 `>` 行后)"
    assert f"memory-bank/pitfalls/git/chained-pitfall.md" in task.read_text(encoding="utf-8"), \
        "档案目标必须反向声明本坑档"


def test_checker_report_mutations_judged_red(tmp_path: Path) -> None:
    """报告族红绿双验 (计划 §06 三类突变, 状态承载族第二例): 填完 = 基准绿;
    删 doc-status / 词表外值 / 留 SLOT 逐类判红, 每类还原后复绿。"""
    new_doc = _new_doc()
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    import io
    from contextlib import redirect_stderr, redirect_stdout

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        assert new_doc.main(
            ["--root",
             str(tmp_path), "--mb-dir",
             str(mb), "report", "--title", "突变报告", "--topic", "mutant-report"]
        ) == 0
    report = next((mb / "reports").glob("*-report-mutant-report.html"))
    _fill_slots(report)
    original = report.read_text(encoding="utf-8")
    assert checker.validate_file(report, "report") == [], "填完必须绿 —— 否则红绿双验失去基准"

    mutations = {
        "删 doc-status":
            lambda t: "\n".join(line for line in t.split("\n") if 'name="doc-status"' not in line),
        "词表外值":
            lambda t: t.replace('<meta name="doc-status" content="Done">', '<meta name="doc-status" content="Draft">'),
        "留 SLOT":
            lambda t: t.replace("已填内容", "<!-- SLOT: 又留了一个 -->", 1),
    }
    for name, mutate in mutations.items():
        report.write_text(mutate(original), encoding="utf-8")
        problems = checker.validate_file(report, "report")
        assert problems, f"突变「{name}」必须判红: {problems}"
        report.write_text(original, encoding="utf-8")
        assert checker.validate_file(report, "report") == [], f"还原「{name}」后必须复绿"


# ---------------------------------------------------------------------------
# kb.tier 分级清理四动作 (2026-10-31 R0, 计划 26-10-31-0534)
#
# 实现在 memory-bank skill 的 `scripts/kb_tier.py`, 本文件**进程内 import** (同 P2 口径);
# 夹具全部在 tmp, 只读面不碰真实 memory-bank/。验收: 计划 §04 R0 表 —— 四动作 +
# 守阵测试; 保守默认 = migrate / purge 高危动作默认 dry-run。
# ---------------------------------------------------------------------------


def _kb_tier():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import kb_tier

    return kb_tier


def _tier_fixture(tmp_path: Path) -> Path:
    """kb.tier 夹具: 最小可跑的 pitfalls/git/ (只建 kb.tier 扫描的那一层)。"""
    mb = tmp_path / "memory-bank"
    (mb / "pitfalls" / "git").mkdir(parents=True)
    return mb


def _tier_pitfall(mb: Path, stem: str, crlf: bool = False) -> Path:
    """标准坑档夹具: 三行头 + `### ` 条目正文 (含各类链接, 供 migrate 断言)。"""
    body = (
        f"# {stem}\n"
        "\n"
        "> 摘要: 判据单点一句话。\n"
        "> 触发: git, sync\n"
        "\n"
        "### 旧叙事\n"
        "\n"
        "- 判别: 见 [运行口径](../../testing/run.md) 与 [同目录](refs.md)。\n"
        "- 外链: [文档](https://example.com/a.md) 与 [锚点](#sec) 原样。\n"
        "- 叙事: 事故时间线。\n"
    )
    if crlf:
        body = body.replace("\n", "\r\n")
    path = mb / "pitfalls" / "git" / f"{stem}.md"
    path.write_bytes(body.encode("utf-8"))
    return path


def test_kb_tier_set_marks_and_fails_fast(tmp_path: Path) -> None:
    """kb.tier set: 插入为头部区第 4 行 / 原地改值 / 幂等 / 非法值与坏路径 fail-fast;
    头部区不足 4 行插在头部区末尾; CRLF 文件插入行保持 CRLF 行尾。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    tier = _kb_tier()
    mb = _tier_fixture(tmp_path)
    pit = _tier_pitfall(mb, "sync-pull")

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = tier.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        return rc, out.getvalue(), err.getvalue()

    # --- 插入为头部区第 4 行, 前三行零触碰 (mb 相对路径形态)
    rc, out, err = run("set", "pitfalls/git/sync-pull.md", "L2")
    assert rc == 0, err
    lines = pit.read_bytes().decode("utf-8").splitlines(keepends=True)
    assert lines[3] == "> 等级: L2\n", lines[:5]
    assert lines[0] == "# sync-pull\n" and lines[2].startswith("> 摘要:"), "前三行零触碰"

    # --- 已有等级行 → 原地改值 (行数不变, 其它行不动)
    rc, out, err = run("set", "pitfalls/git/sync-pull.md", "L0")
    assert rc == 0 and "L2 -> L0" in out.replace("→", "->"), out
    lines2 = pit.read_bytes().decode("utf-8").splitlines(keepends=True)
    assert len(lines2) == len(lines) and lines2[3] == "> 等级: L0\n" and lines2[4] == lines[4]

    # --- 同值幂等: 不写盘
    before = pit.read_bytes()
    rc, out, err = run("set", "pitfalls/git/sync-pull.md", "L0")
    assert rc == 0 and "幂等" in out, out
    assert pit.read_bytes() == before, "幂等打标不得改文件"

    # --- 非法等级 / 不存在文件 / 生成物 全 fail-fast (拒绝时不得改文件)
    rc, _, err = run("set", "pitfalls/git/sync-pull.md", "L9")
    assert rc == 1 and "词表" in err, f"非法等级必须拒绝: {err}"
    assert pit.read_bytes() == before, "拒绝时不得改文件"
    rc, _, err = run("set", "pitfalls/git/nope.md", "L2")
    assert rc == 1 and "文件不存在" in err, err
    (mb / "pitfalls" / "git" / "_index.md").write_text("# idx\n", encoding="utf-8")
    rc, _, err = run("set", "pitfalls/git/_index.md", "L2")
    assert rc == 1 and "生成物" in err, f"生成物必须拒绝: {err}"

    # --- 头部区不足 4 行 → 插在头部区末尾 (首个 ## 之前)
    short = mb / "pitfalls" / "git" / "short-head.md"
    short.write_text("# 短头\n\n## 正文\n", encoding="utf-8", newline="\n")
    rc, _, err = run("set", "pitfalls/git/short-head.md", "L3")
    assert rc == 0, err
    assert short.read_text(encoding="utf-8").splitlines() == ["# 短头", "", "> 等级: L3", "## 正文"]

    # --- CRLF 文件: 插入行保持 \r\n (写盘形态不漂移)
    crlf_pit = _tier_pitfall(mb, "crlf-file", crlf=True)
    rc, _, err = run("set", "pitfalls/git/crlf-file.md", "L1")
    assert rc == 0, err
    assert "> 等级: L1\r\n" in crlf_pit.read_bytes().decode("utf-8")


def test_kb_tier_list_separates_unmarked(tmp_path: Path) -> None:
    """kb.tier list: 列出该等级全部文件 (行数/字符数); 未打标件区分呈现 ——
    L0 视图全列待定件, 其它级只给一行汇总; 非法等级拒绝。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    tier = _kb_tier()
    mb = _tier_fixture(tmp_path)
    _tier_pitfall(mb, "alpha")
    _tier_pitfall(mb, "beta")
    _tier_pitfall(mb, "gamma")

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = tier.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        return rc, out.getvalue(), err.getvalue()

    rc, _, err = run("set", "pitfalls/git/alpha.md", "L3")
    assert rc == 0, err
    rc, _, err = run("set", "pitfalls/git/beta.md", "L2")
    assert rc == 0, err

    # --- L3 视图: 只列 alpha; 未打标件给一行汇总 (不逐件刷屏)
    rc, out, err = run("list", "--level", "L3")
    assert rc == 0, err
    assert "pitfalls/git/alpha.md" in out and "1 件" in out, out
    assert "行" in out and "字符" in out, "条数/字符数必须呈现"
    assert "pitfalls/git/beta.md" not in out and "pitfalls/git/gamma.md" not in out, out
    assert "未打标 1 件" in out, "其它级视图未打标件只给汇总行"

    # --- L0 视图: 未打标件逐件列出 (判据缺失 = 待定, 与已打标 L0 区分)
    rc, out, err = run("list", "--level", "L0")
    assert rc == 0, err
    assert "pitfalls/git/gamma.md" in out and "待定" in out, f"L0 视图必须全列未打标件: {out}"

    # --- 非法等级拒绝
    rc, _, err = run("list", "--level", "L9")
    assert rc == 1 and "词表" in err, err


def test_kb_tier_migrate_dry_run_default_and_apply(tmp_path: Path) -> None:
    """kb.tier migrate: 默认 dry-run 零写盘; --apply 后正文段逐字节搬 attachments/
    (行数与 \r\n 计数与原文一致, 字节差只允许来自相对链接的 ../ 前缀), 主档留指针且
    摘要判据单点仍在; CRLF 文件行尾形态不变; 迁后重跑跳过 (无正文段)。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    tier = _kb_tier()
    mb = _tier_fixture(tmp_path)
    pit = _tier_pitfall(mb, "old-story")
    crlf_pit = _tier_pitfall(mb, "old-crlf", crlf=True)

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = tier.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        return rc, out.getvalue(), err.getvalue()

    for name in ("old-story", "old-crlf"):
        rc, _, err = run("set", f"pitfalls/git/{name}.md", "L2")
        assert rc == 0, err

    original = pit.read_bytes()
    orig_text = original.decode("utf-8")
    orig_body = orig_text[orig_text.index("### "):]
    crlf_original = crlf_pit.read_bytes()
    crlf_body = crlf_original.decode("utf-8")[crlf_original.decode("utf-8").index("### "):]

    # --- 默认 dry-run: 只打印, 零写盘
    rc, out, err = run("migrate", "--level", "L2")
    assert rc == 0 and "dry-run" in out, out
    assert not (mb / "pitfalls" / "git" / "attachments").exists(), "dry-run 不得建附件目录"
    assert pit.read_bytes() == original and crlf_pit.read_bytes() == crlf_original

    # --- --apply: 附件 = 原正文段逐字节 + 相对链接 ../ 前缀 (唯一允许的字节差)
    rc, out, err = run("migrate", "--level", "L2", "--apply")
    assert rc == 0, err
    att_dir = mb / "pitfalls" / "git" / "attachments"
    att = next(att_dir.glob("old-story-migrated-*.md"))
    att_bytes = att.read_bytes()
    att_text = att_bytes.decode("utf-8")
    assert "(../../../testing/run.md)" in att_text, "已带 ../ 的相对链接要再加一层"
    assert "(../refs.md)" in att_text, "同目录相对链接加一层 ../"
    assert "(https://example.com/a.md)" in att_text, "scheme 绝对链接不动"
    assert "(#sec)" in att_text, "纯锚点不动"
    # 行尾形态校验: 行数与 \r\n 计数与原文一致; 字节差恰为两处 ../ 前缀 (各 3 字节)
    assert att_text.count("\r\n") == orig_body.count("\r\n")
    assert att_text.count("\n") - att_text.count("\r\n") == orig_body.count("\n") - orig_body.count("\r\n")
    assert len(att_bytes) == len(orig_body.encode("utf-8")) + 6, "字节差必须恰为两处 ../ 前缀"
    assert "事故时间线" in att_text and "### 旧叙事" in att_text, "叙事段原样在附件"

    # --- CRLF 文件: 整段搬后行尾形态不变
    crlf_att = next(att_dir.glob("old-crlf-migrated-*.md"))
    crlf_att_text = crlf_att.read_bytes().decode("utf-8")
    assert "\r\n" in crlf_att_text and crlf_att_text.count("\r\n") == crlf_body.count("\r\n")

    # --- 主档: 指针行 + 摘要判据单点仍在, 叙事已迁出
    main_text = pit.read_bytes().decode("utf-8")
    assert "> 已外迁:" in main_text and f"]({att.name})" in main_text, "指针指向附件相对路径"
    assert "判据单点一句话" in main_text, "摘要判据单点必须留在主档可读位置"
    assert "事故时间线" not in main_text, "叙事段应已迁出"

    # --- 迁后重跑: 主档已无正文段, 跳过不报错
    rc, out, err = run("migrate", "--level", "L2")
    assert rc == 0 and "无正文段" in out, out


def test_kb_tier_purge_gates_all_or_nothing(tmp_path: Path) -> None:
    """kb.tier purge: 默认 dry-run 不删; 非 L3 拒绝; 三闸门逐条触发 —— ①无守阵且
    头部无「无需守阵」②全仓反向引用未清零 ③头部缺 `> 观察通过:` 标记 —— 任一不过
    全体拒绝 (全或无) 且 rc=1; 三闸门全过 + --apply 才真删。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    tier = _kb_tier()
    mb = _tier_fixture(tmp_path)
    names = ("g1-ok", "g2-backref", "g3-no-observe", "g4-no-guard", "g5-no-guard-ok")
    paths = {n: _tier_pitfall(mb, n) for n in names}

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = tier.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        return rc, out.getvalue(), err.getvalue()

    for n in names:
        rc, _, err = run("set", f"pitfalls/git/{n}.md", "L3")
        assert rc == 0, err

    def _head_add(path: Path, line: str) -> None:
        """头部区等级行后加一行 (夹具的观察通过 / 无需守阵标记)。"""
        text = path.read_bytes().decode("utf-8")
        path.write_bytes(text.replace("> 等级: L3\n", f"> 等级: L3\n{line}\n", 1).encode("utf-8"))

    # g1: 守阵 + 观察通过 (应可删); g2: 守阵 + 观察通过但被引用 (闸门2);
    # g3: 守阵但缺观察通过 (闸门3); g4: 无守阵 (闸门1); g5: 头部「无需守阵」+ 观察通过
    _head_add(paths["g1-ok"], "> 观察通过: 2026-10-30")
    _head_add(paths["g2-backref"], "> 观察通过: 2026-10-30")
    _head_add(paths["g5-no-guard-ok"], "> 无需守阵: 判据进的是文档不是代码")
    _head_add(paths["g5-no-guard-ok"], "> 观察通过: 2026-10-30")
    for n in ("g1-ok", "g2-backref", "g3-no-observe"):
        text = paths[n].read_bytes().decode("utf-8")
        paths[n].write_bytes(
            text.replace("### 旧叙事\n", "### 旧叙事\n\n- 处置: 守阵: `tests/test_x.py::test_y`\n", 1).encode("utf-8")
        )
    (mb / "README.md").write_text("引用: 见 [g2](pitfalls/git/g2-backref.md)。\n", encoding="utf-8")

    def exists(n: str) -> bool:
        return paths[n].is_file()

    # --- 非 L3 拒绝 (L0-L2 是保留/降噪/外迁, 不是删除面)
    rc, _, err = run("purge", "--level", "L2")
    assert rc == 1 and "只接受" in err, err

    # --- 默认 dry-run: 闸门逐条报告, 一个都不删
    rc, out, err = run("purge", "--level", "L3")
    assert all(exists(n) for n in names), "dry-run 不得删文件"
    assert "闸门2" in out and "g2-backref" in out, out
    assert "闸门3" in out and "g3-no-observe" in out, out
    assert "闸门1" in out and "g4-no-guard" in out, out

    # --- --apply 但有闸门未过: 全或无, 连三闸门全过的 g1/g5 也不删, rc=1
    rc, out, err = run("purge", "--level", "L3", "--apply")
    assert rc == 1, f"存在闸门未过必须拒绝: {out}"
    assert all(exists(n) for n in names), "全或无: 一个都不许删"
    assert "闸门1" in out and "闸门2" in out and "闸门3" in out, out

    # --- 处置: 清反向引用 + 补观察通过 + g4 补「无需守阵」→ 三闸门全过, 真删
    (mb / "README.md").unlink()
    _head_add(paths["g3-no-observe"], "> 观察通过: 2026-10-30")
    _head_add(paths["g4-no-guard"], "> 无需守阵: 判据进的是文档不是代码")
    _head_add(paths["g4-no-guard"], "> 观察通过: 2026-10-30")
    rc, out, err = run("purge", "--level", "L3", "--apply")
    assert rc == 0, f"三闸门全过必须真删: {out}\n{err}"
    assert not any(exists(n) for n in names), "全部删除"


def test_kb_tier_is_registered() -> None:
    """kb.tier 已收录进 .commands/kb (收录协议: 不接线 = 没人跑; when 与 note 必填)。"""
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    body = re.search(r'^\[tasks\."kb\.tier"\]\n(.*?)(?=^\[|\Z)', kb_cfg, re.S | re.M)
    assert body, "kb.tier 未收录进 .commands/kb (收录协议)"
    assert "kb_tier.py" in body.group(1), "kb.tier 的 run 必须指到 kb_tier.py"
    assert 'when    = "' in body.group(1), "kb.tier 缺 when (收录协议必填)"
    assert 'note    = "' in body.group(1), "kb.tier 缺 note (收录协议必填)"
