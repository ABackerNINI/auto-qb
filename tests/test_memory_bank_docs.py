"""test_memory_bank_docs 测试计划: Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

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


知识库目录化守卫 (检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 进程内 import):

- test_kb_files_respect_caps: 原「## 测试计划」条目见 test_memory_bank_naming.py(跨分文件共用同一用例条目, 文案未改)
- test_kb_pitfall_entries_have_required_fields: pitfalls 条目含 触发 / 判别 / 处置
- test_kb_active_context_within_cap: `activeContext.md` 是 ≤2 KB 合法存根 (2026-09-23 起滚动状态已迁 `activeContext/`)
- test_kb_cap_debt_is_discoverable_not_blocking: 造超限文件 → 必须报成 warn(债务) 而不是 problem
- test_agents_md_cap_is_hard_not_debt: AGENTS.md 超 8,000 仍是 problem(硬规定), 且不出现在债务清单里
- test_kb_slice_cap_and_count_are_debt_not_blocking: 切片尺寸 / 条数 → warns(债务); 命名 / 三行头仍判红
- test_kb_slice_count_limit_warns_at_120_and_targets_80: 到 120 只告警(--check rc 0)、119 静默; 文案含上限 120 与处置目标「蒸馏到 80」
- test_context_caps_hard_and_debt_split: `check_context_caps.py` 的 AGENTS.md 只在 `HARD_CAPS`、不进债务组
- test_context_caps_files_mode_wiring: `check_context_caps.py` 认 `--files`(闸门收窄方案 D) —— 非帽点传入时空组不打印、rc 0
- test_check_caps_only_scopes_kb_walk: `check_caps(only=)` 只算传入文件(方案 D) —— 集内报债务、集外不读不报, None=全量不变
- test_doc_links_are_not_broken: 全库相对链接存在性 (检查器 memory-bank skill 的 `scripts/check_doc_links.py`, 2026-10-06 从根 `scripts/` 迁入)
- test_doc_links_rejects_windows_normalized_targets: 存在性按 Linux 口径判 —— 结尾点(`kb/...`) / 大小写不符 判坏链, 本机 Windows 的路径归一化不得让它恒绿 (2026-10-11 CI 单条红的根因)

文档族注册表与 kb.new / kb.wrap (2026-10-17 P1, 计划 26-10-17-0527; 实现与检查器在
memory-bank skill 的 `scripts/new_doc.py` / `wrap_session.py` / `check_doc_templates.py`,
**进程内 import** —— 本项目测试禁止起子进程):

- test_commit_gate_covers_kb_check: 原「## 测试计划」条目见 test_memory_bank_cli.py(跨分文件共用同一用例条目, 文案未改)

kb.status / kb.bump 与 D4 反向补链 (2026-10-17 P2, 计划 26-10-17-0527; 实现与检查器在
memory-bank skill 的 `scripts/flip_status.py` / `bump_doc.py`, **进程内 import**):


二期四族 pitfall/report/baseline/progress 与守卫扩面 (2026-10-17 P3, 计划 26-10-17-0527;
实现 = `_common.FAMILIES` 扩行 + `templates/` 四件 + new_doc 分派 + check_doc_templates
扩扫描面, 进程内 import; 验收: 计划 §07 P3 行):


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

常驻锚防流水守卫 (检查器 memory-bank skill 的 `scripts/check_mutation_anchor.py`, 2026-10-31 加):

- test_mutation_anchor_guard_is_green_on_current_kb: 蒸馏改版后的常驻锚零违规 (§07 一张记录表 + 一行式状态日志)
- test_mutation_anchor_guard_flags_ledger_log_and_round_numbers: 台账字样 / 白名单外节 / 逐轮流水数字 / 状态日志超限逐类判红; 清白件零误报
- test_mutation_anchor_guard_is_wired_into_kb_check_and_gate: 守卫已挂进 kb.check 与提交闸门两侧

kb.tier 分级清理四动作 (2026-10-31 R0, 计划 26-10-31-0534; 实现在 memory-bank skill 的
`scripts/kb_tier.py`, **进程内 import**, tmp 夹具不碰真实 memory-bank/):


CLOSED_KEEP=60 索引出口 (计划 26-10-31-0534 R3/D5/D14, 2026-10-31 加; tasks 主索引的已完结区只留
最近 60 条, 全量清单另落 `tasks/attachments/_archive.md`, 形态与 issues 侧同款; plans 侧守阵在 test_docs_forms.py):


状态漂移守卫 (检查器 memory-bank skill 的 `scripts/check_status_drift.py`, 2026-10-31 加, **进程内
import**, tmp 夹具不碰真实 memory-bank/; 四档: A 反链x Open / B issue badge vs meta / 异常
status-unreadable 三档硬拦 rc=1, C 反链x In Progress / D 完成断言两档清单只提示):

- test_status_drift_sections_are_whitelisted: 判据词前缀开节(标题后缀/emoji 容忍), H1 文件题不是节, 同级/更高级标题关节, 深层子节留在节内; known-bugs.md 只认「已修复」节
- test_status_drift_link_targets_resolved: 四族(tasks/issues/plans/reports)目标解析; 外链/纯锚点/四族外(pitfalls)/错后缀忽略; 链接带标题不破解析
- test_status_drift_gate_a_flags_open_backlinks: 已实现节反链→Open 目标 → rc=1 + 漂移行 + 「kb.status 翻 In Progress」提示; roadmap/suggestions/evolution 与 H1 题下的同款反链不触发; 四族外目标不触发
- test_status_drift_gate_b_badge_vs_meta: badge≠meta 红; badge==meta / 缺失(文档化边界) / 括注后缀「Open(常驻)」过; ASCII 字母后缀「Opened」红
- test_status_drift_gate_c_never_fails: C+D 清单非空 rc=0 且原文打印 —— C/D 永不拦退出码
- test_status_drift_gate_d_exemptions: 否定前缀(未/尚未/没有)/日期行/围栏代码/行内代码豁免; Open/In Progress 正文裸完成词列出; Done 正文完成词不列
- test_status_drift_anomaly_on_unreadable_status: 缺 `**Status:**` / 词表外值 / 反链目标缺失 / issue-status meta 缺失 → status-unreadable 异常, rc=1 (doc-status-meta.md: ring, 不静默丢)
- test_status_drift_guard_is_wired_into_kb_check_and_gate: 守卫已挂进 kb.check 与提交闸门两侧(与 test_mutation_anchor_guard_is_wired_into_kb_check_and_gate 同旨)

HTML 结构守卫 (检查器 memory-bank skill 的 `scripts/check_html.py`, 2026-11-01 加, **进程内
import**; L1 行级正则 + L2 stdlib 解析器残缺标签名校验双网, script/style 区遮蔽防 JS 字面量
误报; 全库存量基线 = 零命中, 命中即新增 —— 无存量豁免清单; 更广的规范级伤害归 `--vnu` 巡检):

- test_html_guard_flags_broken_endtag_and_passes_clean: `</code)` 缺 `>` 双网命中(L1 行级 + L2 残缺名), 补 `>` 后零命中 —— 26-11-01 两起事故(issues/26-11-01-0334 s2-s7 掉左栏 / reports/26-10-14-1110:320)的最小复现形态钉住
- test_html_guard_ignores_script_literal_regex: `<script>` 内 JS 字面量 `replace(/</g, …)` 不判红(存量实况 plans/26-09-25-2043:502; 分词器 script data 态不认标签, L1 遮蔽 + L2 CDATA 态双保险, 首跑实测无遮蔽时全库误报)
- test_html_guard_corpus_zero_hits: 全库 645 件 HTML 存量零命中(冻结线起点)
- test_html_guard_wired_into_kb_check_and_gate: 守卫挂进 kb.check 与提交闸门两侧(同 test_mutation_anchor 钉法), v.Nu 增量闸门行与 kb.html-audit 巡检任务同鍗住
- test_html_vnu_skips_vue_template_fragments: `shared/tpl/` 下的 Vue 模板分片不送 v.Nu(`v-if`/`@click`/`:prop` 是指令, 必然被判 Attribute not allowed; 26-11-02 首次提交改分片实测 22 条); 判据只认路径, 全被摘掉时不碰 java/vnu.jar
"""

from __future__ import annotations

import re

import sys

from pathlib import Path

from kb_test_support import (
    MB,
    ROOT,
    SKILL,
    SKILL_SCRIPTS,
    _check_html,
    _doc_links_module,
    _drift_doc,
    _drift_fixture,
    _drift_issue,
    _drift_run,
    _drift_task,
    _gen_all,
    _kb_checker,
    _mutation_anchor,
    _status_drift,
    _timekit,
    _wording,
)


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


def test_kb_slice_count_limit_warns_at_120_and_targets_80(tmp_path: Path, monkeypatch, capsys) -> None:
    """120 上限 / 80 处置目标: 到 120 只告警不失败, 低于 120 静默, 文案带可执行落点。

    真实造 120 个合规切片(而非 monkeypatch 压小阈值), 把「达到即告警」与 `--check` 的退出码
    一起钉住 —— 这两点正是 2026-11-03 改为「只通知、不拦」的验收判据。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_active_recent
    import _common

    assert (_common.SLICE_COUNT_LIMIT, _common.SLICE_COUNT_TARGET
           ) == (120, 80), (f"单点常量漂移: {_common.SLICE_COUNT_LIMIT} / {_common.SLICE_COUNT_TARGET}")

    slice_dir = tmp_path / "memory-bank" / "activeContext"
    slice_dir.mkdir(parents=True)

    def write_slices(n: int) -> None:
        for i in range(n):
            day, hour = 1 + i // 24, i % 24
            (slice_dir / f"26-01-{day:02d}-{hour:02d}00-s{i}.md"
            ).write_text(f"# s{i}\n> 摘要: x\n> 最后活动: 2026-01-{day:02d} {hour:02d}:00\n", encoding="utf-8")

    write_slices(119)
    _rows, problems, warns = gen_active_recent.collect(slice_dir, tmp_path)
    assert not problems and not warns, f"119 < 120 不该告警: {warns}"

    write_slices(120)  # 补第 120 片
    _rows, problems, warns = gen_active_recent.collect(slice_dir, tmp_path)
    assert not problems, f"合规切片不该报结构问题: {problems}"
    assert len(warns) == 1, f"到 120 条必须正好一条债务告警: {warns}"
    text = warns[0]
    assert "120" in text and "上限" in text and "80" in text, f"告警文案缺可执行落点: {text}"
    assert "不拦" in text, f"告警必须明示不拦: {text}"

    # 达到上限时 `--check` 仍返回 0 —— 不阻断 kb.check / kb.wrap / 提交
    monkeypatch.setattr(
        sys,
        "argv",
        ["gen_active_recent.py", "--check", "--root",
         str(tmp_path), "--mb-dir",
         str(slice_dir.parent)],
    )
    assert gen_active_recent.main() == 0, "到上限只告警, --check 退出码必须为 0"
    assert "[债务]" in capsys.readouterr().err, "债务行应出现在 stderr"


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


def test_context_caps_files_mode_wiring(monkeypatch) -> None:
    """`check_context_caps.py --files`(方案 D): 传入非帽点文件 → 各组落空仍能打印, rc 0。

    空组必须被剪掉而不是 `max()` 崩 —— 收窄后「传入文件没有任何帽点」是常态
    (改的是普通 KB 文档时, 三条 caps run 里命中的那条就属此形)。
    硬规定语义不变断言: AGENTS.md 不在改动集 → 硬规定组整组不出现。
    """
    import importlib.util
    from contextlib import redirect_stdout

    import io

    spec = importlib.util.spec_from_file_location(
        "check_context_caps_files", ROOT / "scripts" / "check_context_caps.py"
    )
    assert spec and spec.loader, "缺少 scripts/check_context_caps.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["check_context_caps.py", "--files", "memory-bank/not-a-cap-point.md"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = module.main()
    out = buf.getvalue()
    assert rc == 0, out
    assert "硬规定" not in out, "AGENTS.md 不在改动集时硬规定组必须整组跳过"
    assert "无阻塞项" in out


def test_check_caps_only_scopes_kb_walk(tmp_path: Path) -> None:
    """`check_caps(only=)` 收窄读取面(方案 D): 集内超限报债务, 集外超限不读不报; 缺省 None 行为不变。

    收窄必须**只动面、不动严重度**: 分级单点(`HARD_CAP_ROLES`)与此参数正交 —— 集内文件照旧
    按角色分级, 集外文件连 `char_count` 都不跑(这正是收窄的收益所在)。
    """
    checker = _kb_checker()
    root, mb = tmp_path, tmp_path / "memory-bank"
    (mb / "evergreen").mkdir(parents=True)
    (mb / "evergreen" / "_about.md").write_text("# t\n> 摘要: x\n> 触发: y\n", encoding="utf-8")
    for name in ("big-a.md", "big-b.md"):
        (mb / "evergreen" / name).write_text("# 大\n> 摘要: x\n> 触发: y\n" + "x" * 30_000, encoding="utf-8")

    problems_full, warns_full = checker.check_caps(root, mb)
    debts_full, _ = checker.split_warns(warns_full)
    assert len(debts_full) == 2, debts_full

    problems, warns = checker.check_caps(root, mb, only={"memory-bank/evergreen/big-a.md"})
    debts, _ = checker.split_warns(warns)
    assert not problems
    assert len(debts) == 1 and "big-a.md" in debts[0], debts


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


def test_status_drift_sections_are_whitelisted() -> None:
    """判据词前缀开节 (标题后缀/emoji 容忍), H1 文件题不是节, 同级/更高级标题关节,
    深层子节留在节内; known-bugs.md 只认「已修复」节 (判据: 只收白名单节内的反链)。"""
    drift = _status_drift()
    lines = [
        "# 已实现 总览",  # H1 文件题不是节 (它描述文件主题, 不是完成断言)
        "link [a](../tasks/h1.md) under H1",
        "## 已实现 alpha",
        "in section [t](../tasks/a.md)",
        "### 已实现 sub",  # 更深层级: 自身也是白名单节, 但不关外层节
        "inside sub",
        "## 待实现 beta",  # 非判据词 + 同级: 关节且不开新节
        "outside [u](../tasks/b.md)",
        "## 已修复（gamma）✅",  # 后缀/emoji 容忍 (按前缀匹配, 真实文件会装饰标题)
        "inside gamma",
    ]

    assert [n for n, _ in drift.iter_whitelisted_lines(lines, known_bugs_only=False)] == [4, 6, 10]
    # known-bugs.md 口径: 只认「已修复」节 —— 已实现节不收
    assert [n for n, _ in drift.iter_whitelisted_lines(lines, known_bugs_only=True)] == [10]


def test_status_drift_link_targets_resolved(tmp_path: Path) -> None:
    """四族目标解析; 外链/纯锚点/四族外(pitfalls)/错后缀忽略; 链接带标题不破解析
    (判据: 只有落进 tasks/issues/plans/reports 的目标才算完成断言的反链)。"""
    drift = _status_drift()
    mb = _drift_fixture(tmp_path)
    src = mb / "progress" / "implemented-x.md"

    resolve = drift.resolve_family_target
    assert resolve("../tasks/a.md", src, mb)[1] == "task"
    assert resolve("../issues/a.html", src, mb)[1] == "issue"
    assert resolve("../plans/a.html", src, mb)[1] == "plan"
    assert resolve("../reports/a.html", src, mb)[1] == "report"
    assert resolve("../tasks/a.md#sec", src, mb)[1] == "task", "锚点剥掉后照常解析"
    for raw in ("https://example.com/a.md", "#sec", "../pitfalls/git/x.md", "../tasks/a.html", "../../outside.md"):
        assert resolve(raw, src, mb) is None, raw

    (mb / "tasks" / "a.md").write_text("**Status:** Open\n", encoding="utf-8")
    (mb / "tasks" / "b.md").write_text("**Status:** Open\n", encoding="utf-8")
    (mb / "issues" / "a.html").write_text("<html></html>\n", encoding="utf-8")
    (mb / "progress" / "implemented-x.md").write_text(
        "# link targets fixture\n"
        "\n"
        "## 已实现\n"
        "\n"
        "- plain [t](../tasks/a.md)\n"
        '- title [t](../tasks/a.md "标题")\n'
        "- anchor [t](../tasks/b.md#sec)\n"
        "- external [t](https://example.com/a.md)\n"
        "- pure anchor [t](#sec)\n"
        "- other family [t](../pitfalls/git/x.md)\n"
        "- wrong suffix [t](../tasks/a.html)\n"
        "- issue [t](../issues/a.html)\n",
        encoding="utf-8",
    )

    backlinks, missing = drift.collect_backlinks(mb)

    assert [b.target.name for b in backlinks] == ["a.md", "a.md", "b.md", "a.html"], "带标题的链接目标照常解析"
    assert all(b.kind == "task" for b in backlinks[:3]) and backlinks[3].kind == "issue"
    assert missing == [], "库内存在的目标不进异常"


def test_status_drift_gate_a_flags_open_backlinks(tmp_path: Path) -> None:
    """A 档硬拦: 已实现节反链→Open 目标 → rc=1 + `src:line -> target (status: Open)` 漂移行
    + 「kb.status 翻 In Progress」提示; roadmap/suggestions/evolution 与 H1 题下的同款反链
    不触发; 四族外 (pitfalls) 目标不触发。"""
    mb = _drift_fixture(tmp_path)
    _drift_task(mb, "open.md", "Open")
    _drift_doc(mb, "plans", "open-plan.html", "Open")
    (mb / "pitfalls" / "git").mkdir(parents=True)
    (mb / "pitfalls" / "git" / "x.md").write_text("x\n", encoding="utf-8")
    same_link = "# other progress file\n\n## 已实现\n\n- task [t](../tasks/open.md)\n"
    for name in ("roadmap.md", "suggestions.md", "evolution.md"):
        (mb / "progress" / name).write_text(same_link, encoding="utf-8")
    (mb / "progress" / "implemented-a.md").write_text(
        "# gate A fixture\n"
        "\n"
        "## 已实现 alpha\n"
        "\n"
        "- task [t](../tasks/open.md)\n"
        "- plan [t](../plans/open-plan.html)\n"
        "- pitfall [p](../pitfalls/git/x.md)\n",
        encoding="utf-8",
    )
    (mb / "progress" / "implemented-h1.md").write_text(
        "# 已实现 but H1 is a file title\n"
        "\n"
        "- [t](../tasks/open.md)\n",
        encoding="utf-8",
    )

    rc, out, err = _drift_run(tmp_path, mb)

    assert rc == 1
    rows = [line for line in out.split("\n") if "[backlink-x-Open]" in line]
    assert len(rows) == 2, f"只有 implemented-a.md 白名单节里的 2 条反链该触发: {rows}"
    assert "memory-bank/progress/implemented-a.md:5: [backlink-x-Open] -> memory-bank/tasks/open.md (status: Open)" in rows[
        0]
    assert "[backlink-x-Open] -> memory-bank/plans/open-plan.html (status: Open)" in rows[1]
    assert "hint:" in out and "commands run kb.status" in out, "A 档必须带 kb.status 翻状态提示"
    for excluded in ("roadmap", "suggestions", "evolution", "implemented-h1", "pitfalls"):
        assert excluded not in out, f"{excluded} 不得进 A 档"
    assert "2 hard finding(s)" in err


def test_status_drift_gate_b_badge_vs_meta(tmp_path: Path) -> None:
    """B 档硬拦: badge 文本 vs `<meta name="issue-status">` —— 不一致判红 (rc=1);
    badge 缺失不判违规 (文档化边界); 括注后缀「Open(常驻)」与 meta Open 一致;
    后缀是 ASCII 字母「Opened」= 另一个词, 不一致。"""
    mb = _drift_fixture(tmp_path)
    _drift_issue(mb, "b1-contradict.html", "Open", badge="Done")
    _drift_issue(mb, "b2-equal.html", "Open", badge="Open")
    _drift_issue(mb, "b3-no-badge.html", "Open", badge=None)
    _drift_issue(mb, "b4-paren.html", "Open", badge="Open(常驻)")
    _drift_issue(mb, "b5-ascii-suffix.html", "Open", badge="Opened")

    rc, out, _err = _drift_run(tmp_path, mb)

    assert rc == 1
    rows = [line for line in out.split("\n") if "[badge-vs-meta]" in line]
    assert len(rows) == 2, f"只有 b1/b5 该判红: {rows}"
    assert "b1-contradict.html" in rows[0] and "badge='Done'" in rows[0] and "meta='Open'" in rows[0]
    assert "b5-ascii-suffix.html" in rows[1] and "badge='Opened'" in rows[1]
    for tolerated in ("b2-equal", "b3-no-badge", "b4-paren"):
        assert tolerated not in out, f"{tolerated} 不得进 B 档 (缺失/一致/括注后缀都放行)"


def test_status_drift_gate_c_never_fails(tmp_path: Path) -> None:
    """C/D 清单永不拦退出码: 反链x In Progress 与完成断言都进清单, rc=0
    (清单是人工复核面, 不是闸门; 退出码只听 A/B/异常三档)。
    默认模式: 只打 summary 行, 不展开条目正文; --verbose 才逐条。"""
    mb = _drift_fixture(tmp_path)
    _drift_task(mb, "inflight.md", "In Progress")
    _drift_task(mb, "open-word.md", "Open", body="- 已完成 首版\n")
    (mb / "progress" / "implemented-c.md"
    ).write_text("# gate C fixture\n\n## 已实现\n\n- task [t](../tasks/inflight.md)\n", encoding="utf-8")

    # --- 默认模式: summary only, 条目名不出现在 C/D 段
    rc, out, _err = _drift_run(tmp_path, mb)
    assert rc == 0, "C/D 非空不红"
    assert "no hard drift (tiers A/B/anomalies empty)" in out
    assert "== C list: backlink x In Progress (manual review): 1 (--verbose to unfold per-row detail) ==" in out
    assert "== D list: done-style words in Open/In Progress bodies (low confidence): 1 (--verbose to unfold per-row detail) ==" in out
    # 具体条目正文不应在默认输出里
    assert "[backlink-x-InProgress]" not in out, "默认模式 C 档不应展开条目"
    assert "inflight.md" not in out, "默认模式 C 档不应出现文件名"
    assert "[done-assert]" not in out, "默认模式 D 档不应展开条目"
    assert "open-word.md" not in out, "默认模式 D 档不应出现文件名"

    # --- --verbose 模式: 逐条展开
    rc2, out2, _ = _drift_run(tmp_path, mb, extra_args=["--verbose"])
    assert rc2 == 0
    assert "[backlink-x-InProgress] -> memory-bank/tasks/inflight.md (status: In Progress)" in out2
    assert "[done-assert]" in out2 and "open-word.md" in out2, "--verbose 应展开 D 档条目"


def test_status_drift_gate_d_exemptions(tmp_path: Path) -> None:
    """D 档豁免面: 否定前缀 (未/尚未/没有 + 「还没有已实现」的实义形态) / 日期行 /
    围栏代码 / 行内代码都不列; Open/In Progress 正文裸完成词列出 (带状态注记);
    Done 正文完成词不列 (完结件正文说「已完成」天经地义)。
    默认模式只打 summary 行; --verbose 逐条展开, 豁免判定本身在两种模式下一致。"""
    drift = _status_drift()
    mb = _drift_fixture(tmp_path)
    open_done = _drift_task(
        mb,
        "open-done.md",
        "Open",
        body=(
            "- 已完成 首版\n"
            "- 未完成 收尾\n"
            "- 尚未完成 验收\n"
            "- 没有完成 联调\n"
            "- 还没有已实现的同类功能\n"
            "- 2026-10-31 已完成 历史流水\n"
            "- 口径 `已完成` 引述\n"
            "```\n"
            "- 已完成 围栏内\n"
            "```\n"
        ),
    )
    _drift_task(mb, "inflight-word.md", "In Progress", body="- 已修复 一个bug\n")
    _drift_task(mb, "done-quiet.md", "Done", body="- 已完成 全部\n")
    _drift_issue(mb, "open-h.html", "Open", body="<p>已完成</p>\n<p>引述 <code>已完成</code></p>\n<pre>已完成 围栏内</pre>\n")
    _drift_issue(mb, "done-h.html", "Done", body="<p>已完成</p>\n")

    # --- 默认模式: summary only
    rc, out, _err = _drift_run(tmp_path, mb)
    assert rc == 0, "D 清单不红"
    assert "== D list: done-style words in Open/In Progress bodies (low confidence): 3 (--verbose to unfold per-row detail) ==" in out
    assert "[done-assert]" not in out, "默认模式 D 档不应展开条目"
    assert "open-done.md" not in out, "默认模式 D 档不应出现文件名"

    # --- --verbose 模式: 逐条展开 + 豁免验证
    rc2, out2, _ = _drift_run(tmp_path, mb, extra_args=["--verbose"])
    assert rc2 == 0
    flagged = [line for line in out2.split("\n") if "[done-assert]" in line]
    assert len(flagged) == 3, f"每个在办载体恰 1 条裸完成词: {flagged}"
    expect_line = open_done.read_text(encoding="utf-8").split("\n").index("- 已完成 首版") + 1
    assert f"memory-bank/tasks/open-done.md:{expect_line}: [done-assert] word='已完成' (status: Open)" in flagged
    assert any("inflight-word.md" in row and "word='已修复'" in row and "(status: In Progress)" in row for row in flagged)
    assert any("open-h.html" in row and "(status: Open)" in row for row in flagged)
    for exempt in ("done-quiet", "done-h", "未完成", "尚未", "没有", "还没有", "历史流水", "引述", "围栏内"):
        assert exempt not in "\n".join(flagged), f"豁免形态不得入列: {exempt}"

    # 否定前缀的实义命中形态 (单词直接跟在否定词后): 单测钉住豁免判定本身。
    assert drift.scan_md_done_words("- 还没有已实现的功能") == []
    assert drift.scan_md_done_words("- 已实现的功能") == [(1, "已实现")]


def test_status_drift_anomaly_on_unreadable_status(tmp_path: Path) -> None:
    """异常档硬拦 (rc=1): 缺 `**Status:**` / 词表外值 / 反链目标缺失 / issue-status meta
    缺失 → status-unreadable 行 (doc-status-meta.md: 状态层坏了必须响铃, 不许静默丢)。"""
    mb = _drift_fixture(tmp_path)
    _drift_task(mb, "missing-status.md", None)
    (mb / "tasks" / "bad-vocab.md").write_text("# bad vocab\n\n**Status:** Doing\n", encoding="utf-8")
    _drift_issue(mb, "nostatus.html", None)
    (mb / "progress" / "implemented-anom.md").write_text(
        "# anomaly fixture\n"
        "\n"
        "## 已实现\n"
        "\n"
        "- missing status [t](../tasks/missing-status.md)\n"
        "- bad vocab [t](../tasks/bad-vocab.md)\n"
        "- ghost [t](../tasks/ghost.md)\n",
        encoding="utf-8",
    )

    rc, out, _err = _drift_run(tmp_path, mb)

    assert rc == 1
    rows = [line for line in out.split("\n") if "[status-unreadable]" in line]
    assert len(rows) == 4, f"四类异常各一条: {rows}"
    assert any("target missing: memory-bank/tasks/ghost.md" in row for row in rows), "悬空反链是异常, 不是崩溃"
    assert any("-> memory-bank/tasks/missing-status.md (missing)" in row for row in rows)
    assert any("-> memory-bank/tasks/bad-vocab.md (out-of-vocab: 'Doing')" in row for row in rows)
    assert any("nostatus.html" in row and "issue-status meta missing" in row for row in rows)


def test_status_drift_guard_is_wired_into_kb_check_and_gate() -> None:
    """守卫必须挂在 kb.check 与提交闸门两侧 —— 不接线 = 没人跑, 漏闸门 = 静默红
    (与 test_mutation_anchor_guard_is_wired_into_kb_check_and_gate 同旨;
    覆盖面一致性由 test_commit_gate_covers_kb_check 按 run 列表推导)。"""
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    gate_cfg = (ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml").read_text(encoding="utf-8")

    assert "check_status_drift.py --check" in kb_cfg, "check_status_drift.py 未挂进 kb.check"
    assert "check_status_drift.py --check" in gate_cfg, "check_status_drift.py 未挂进提交闸门 (静默红)"


def test_html_guard_flags_broken_endtag_and_passes_clean() -> None:
    """`</code)` 缺 `>` 双网命中 (L1 行级 + L2 残缺名), 补 `>` 后零命中。

    26-11-01 两起事故的最小复现形态: 分词器把 `</code): 目标 …。</p` 整段吃进非法尾标签,
    `<code>` 永不闭合, 其后内容全部嵌进它 (issues/26-11-01-0334 s2-s7 掉左栏 /
    reports/26-10-14-1110:320 同型)。⚠ 正则不许写成单 lookahead: 引擎会把 `</title>`
    回溯成 `</titl`+`e` 穿过否定前瞻而全库误报 (首跑实测, 见脚本内注释)。
    """
    m = _check_html()
    broken = "<p>记录 <code>x.md</code): 目标 qB。</p><section><h2>02</h2></section>"
    problems = m.check_text(broken)
    assert any("闭合标签缺" in p for p in problems), f"L1 应命中: {problems}"
    assert any("残缺标签名" in p for p in problems), f"L2 应命中: {problems}"
    assert not m.check_text(broken.replace("</code):", "</code>):")), "补 `>` 后应零命中"


def test_html_guard_ignores_script_literal_regex() -> None:
    """`<script>` 内 JS 字面量 `replace(/</g, …)` 不判红 (存量实况 plans/26-09-25-2043:502)。

    分词器在 script data 态不把 `</g,` 当标签 —— L1 遮蔽 script/style 区, L2 走解析器自身
    CDATA 态, 双保险同判; 没有遮蔽时 L1 会全库误报 (2026-11-01 首跑实测)。
    """
    m = _check_html()
    text = "<html><body><script>var x = a.replace(/</g, '&lt;').replace(/>/g, '&gt;');</script></body></html>"
    assert not m.check_text(text), "script 内字面量不得判红"


def test_html_guard_corpus_zero_hits() -> None:
    """全库存量基线 = 零命中 (2026-11-01 起冻结: 命中即新增, 无存量豁免清单)。"""
    m = _check_html()
    files = m.collect_files(MB, None)
    assert files, "memory-bank 下没有 HTML?"
    bad = [str(f) for f in files if m.check_text(f.read_bytes().decode("utf-8"))]
    assert not bad, f"存量 HTML 结构命中 (修好后有人又写坏了?): {bad[:5]}"


def test_html_guard_wired_into_kb_check_and_gate() -> None:
    """守卫挂进 kb.check 与提交闸门两侧 (同 test_mutation_anchor 钉法, 防静默红);
    v.Nu 增量闸门行 (`<changed:>` 只查本次改动, 2026-11-01 扩面: 全仓改动 HTML 不限 memory-bank)
    与 kb.html-audit 全库巡检任务同在。"""
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    gate_cfg = (ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml").read_text(encoding="utf-8")
    assert "check_html.py --check" in kb_cfg, "check_html.py 未挂进 kb.check"
    assert "check_html.py --check" in gate_cfg, "check_html.py 未挂进提交闸门 (静默红)"
    assert 'match = [".html"]' in gate_cfg, "v.Nu 闸门触发面未放开到全仓改动 HTML (静默漏)"
    assert "--vnu --strict <changed:**/*.html>" in gate_cfg, "v.Nu 增量闸门行缺失"
    assert "kb.html-audit" in kb_cfg, "kb.html-audit 巡检任务缺失"


def test_html_vnu_skips_vue_template_fragments(tmp_path) -> None:
    """v.Nu 校验的是 HTML 文档语义; `shared/tpl/` 下的 Vue 模板**分片**先摘掉 (摘掉要可见)。

    2026-11-02 首次提交改分片实测: `static/shared/tpl/overlays.html` 的 `v-if` / `@click` /
    `:class` 被 v.Nu 逐条判 `Attribute "…" not allowed` (22 条), 全批只有这一类 —— 范畴错误,
    不是缺陷; 同批 `fx/showcase.html` 零 error, 说明网本身是好的。判据只认路径 (tpl-manifest
    的家), 不用"内容含 v- 就跳过" —— 那会把真正写坏属性名的页面一起放过。皮肤壳
    `static/<皮肤>/index.html` 的内联 `<div id="app">` 是 Vue 根模板, 同一类范畴错误由
    `is_webui_skin_shell` 按路径摘除。
    全被摘掉时不得触碰 java / vnu.jar (不下载、不装 JDK 也能提交纯模板改动) —— 用不存在的
    可执行名证明根本没走到子进程。
    """
    m = _check_html()
    root = tmp_path / "repo"
    tpl = root / "src" / "auto_qb" / "webui" / "static" / "shared" / "tpl" / "overlays.html"
    tpl.parent.mkdir(parents=True)
    tpl.write_text('<div :class="x" v-if="y">a</div>', encoding="utf-8")
    page = root / "src" / "auto_qb" / "webui" / "static" / "fx" / "showcase.html"
    page.parent.mkdir(parents=True)
    page.write_text("<html><body><p>ok</p></body></html>", encoding="utf-8")

    shell = root / "src" / "auto_qb" / "webui" / "static" / "prism" / "index.html"
    shell.parent.mkdir(parents=True)
    shell.write_text('<div id="app"><form v-else>a</form></div>', encoding="utf-8")

    assert m.is_vue_template_fragment(tpl, root), "tpl 分片未被认出 —— v.Nu 会整批误报"
    assert not m.is_vue_template_fragment(page, root), "普通页面被误判成分片 —— 真错误会被放行"
    assert m.is_webui_skin_shell(shell, root), "皮肤壳内联根模板未被认出 —— v.Nu 会整批误报"
    assert not m.is_webui_skin_shell(page, root), "普通页面被误判成皮肤壳 —— 真错误会被放行"
    assert not m.is_webui_skin_shell(tpl, root), "tpl 分片被误判成皮肤壳 —— 该走 tpl 判据"
    assert m.run_vnu([tpl, shell], root, True,
                     "java-does-not-exist") == 0, ("全是 Vue 承载面时仍应 rc=0, 且不得调用 java (调用即抛/下载 jar)")
