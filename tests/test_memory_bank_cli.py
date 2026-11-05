"""test_memory_bank_cli 测试计划: Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

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
- test_wrap_archive_flag_anchors_umbrella_archive: `--archive` 显式锚档案 —— 异键 (伞形档案
  `test-umbrella-audit` vs 切片 `derived-slice`) 时命中并抬 Updated + 进度日志; 不传时
  提示落空且档案零触碰 (默认行为不变); 坏 kebab 拒
- test_checker_three_mutations_judged_red: 红绿双验 —— 填完 = 基准绿; 三类突变 (删状态行 /
  词表外值 / 留 SLOT) 逐类判红, 每类还原后复绿 (证明绿不是恒绿)
- test_checker_freeze_line_exempts_stock: 冻结线之前 (档案日期 26-10-16 / plan·report 文件名
  stamp 0735) 的缺陷件豁免; 之后 (26-10-17 / 0740) 入检查面判红 (D3 存量冻结只拦新增)
- test_checker_catches_new_plan_missing_doc_added: 手写新计划缺 doc-added 必判红 (26-10-31 修
  RM02-RM10 九件无状态计划事故的回归阵: 原按文件自身 doc-added 圈面, 缺头部新件整件逃逸;
  修复后圈面 = 文件名 stamp 前缀, 与文件招供无关)
- test_family_registry_matches_templates: 模板烤进去的出厂值与 `_common.FAMILIES` 同源
  (设计底线: 不造第二套词表/命名规则)
- test_new_doc_templates_lead_with_only_answer_slot: 五个文档族模板的第一个 SLOT 必须是
  「本篇只回答」+ 预算/触顶固定动作 (2026-11-05 计划 §07 P1/P2 的写前判定)
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


回写措辞守卫 (检查器 memory-bank skill 的 `scripts/check_wording.py`, 2026-10-07 加):


常驻锚防流水守卫 (检查器 memory-bank skill 的 `scripts/check_mutation_anchor.py`, 2026-10-31 加):


kb.tier 分级清理四动作 (2026-10-31 R0, 计划 26-10-31-0534; 实现在 memory-bank skill 的
`scripts/kb_tier.py`, **进程内 import**, tmp 夹具不碰真实 memory-bank/):

- test_kb_tier_set_marks_and_fails_fast: set 插入为头部区第 4 行 (前三行零触碰) / 已有等
  级行原地改值 / 同值幂等不写盘 / 非法等级与不存在文件与生成物·附件·库外路径 fail-fast /
  头部区不足 4 行插在头部区末尾 / CRLF 文件插入行保持 \r\n
- test_kb_tier_list_separates_unmarked: list 列出该等级全部文件 (行数/字符数); 未打标件
  (无 `> 等级:` 行) 区分呈现 —— L0 视图全列待定件, 其它级只给一行汇总; 非法等级拒绝
- test_kb_tier_migrate_dry_run_default_and_apply: migrate 默认 dry-run 零写盘; --apply 后
  正文段逐字节搬 attachments/ (行数与 
 计数与原文一致, 字节差只允许来自相对链接的
  `../` 前缀; scheme/根相对/锚点链接不动), 主档留 `> 已外迁:` 指针且摘要判据单点仍在;
  CRLF 文件整段搬后行尾形态不变; 迁后重跑按指针幂等跳过
- test_kb_tier_migrate_skips_already_migrated: migrate 幂等闸 —— 主档已带 `> 已外迁:` 指针
  的文件一律跳过, 即使残留 `## ` 段也不二次外迁、不产生第二份附件、dry-run/--apply 都零写盘
  (R1 实测: git/ 已迁档会被旧逻辑重复处理)
- test_kb_tier_purge_gates_all_or_nothing: purge 默认 dry-run 不删; 非 L3 拒绝; 三闸门逐
  条触发 —— ①无守阵且头部无「无需守阵」②全仓反向引用未清零 ③头部缺 `> 观察通过:` 标
  记 —— 任一不过全体拒绝 (全或无, 删零个) 且 rc=1; 三闸门全过 + --apply 才真删
- test_kb_tier_is_registered: kb.tier 已收录进 .commands/kb (收录协议 when/note 必填;
  与 test_kb_status_and_bump_are_registered 同旨)

CLOSED_KEEP=60 索引出口 (计划 26-10-31-0534 R3/D5/D14, 2026-10-31 加; tasks 主索引的已完结区只留
最近 60 条, 全量清单另落 `tasks/attachments/_archive.md`, 形态与 issues 侧同款; plans 侧守阵在 test_docs_forms.py):

- test_closed_keep_trims_done_to_60_and_archives_full: Done 62 件 -> 主索引只留最近 60 条 + 隐藏提示; 归档全量(只列 slug 与标题, 不带摘要防链接位移)、链接带 ../ 指回原文; 在办分区不受影响
- test_closed_keep_boundary_at_60: 第 60/61 条边界 —— 恰 60 条不裁无提示, 第 61 条起裁 1 条出提示
- test_closed_keep_never_trims_inflight_and_dropped_also_trims: 在办条数再多不裁(只治完结堆积); Dropped 同属完结区一并裁
- test_closed_keep_archive_same_batch_wiring: rebuild_index(kb.status/kb.bump 落点)主索引与归档同批落盘; 归档落 `tasks/attachments/_archive.md` 且故意不叫 `_index.md`(不套 index-auto cap)
- test_closed_keep_constants_match_issues: 跨 skill 常量等值钉住 —— memory-bank 侧 CLOSED_KEEP/ARCHIVE_REL/完结状态集与 create-issue 的 gen_issues_index 同值同语义(跨 skill 不 import, 防两套实现漂移)
- test_issues_closed_keep_behavior_unchanged: issues/ 零行为变化回归 —— 61 件 Done issue 主索引留 60 + 提示、归档全量(把改造前行为钉下来)

状态漂移守卫 (检查器 memory-bank skill 的 `scripts/check_status_drift.py`, 2026-10-31 加, **进程内
import**, tmp 夹具不碰真实 memory-bank/; 四档: A 反链x Open / B issue badge vs meta / 异常
status-unreadable 三档硬拦 rc=1, C 反链x In Progress / D 完成断言两档清单只提示):

- test_wrap_reports_status_drift_lists: kb.wrap 尾部打印 C/D 清单(空打「无」), 硬拦非空附「状态漂移硬拦非空…」提示行, wrap 退出码与结果不因此改变

HTML 结构守卫 (检查器 memory-bank skill 的 `scripts/check_html.py`, 2026-11-01 加, **进程内
import**; L1 行级正则 + L2 stdlib 解析器残缺标签名校验双网, script/style 区遮蔽防 JS 字面量
误报; 全库存量基线 = 零命中, 命中即新增 —— 无存量豁免清单; 更广的规范级伤害归 `--vnu` 巡检):

"""

from __future__ import annotations

import re

import sys

from pathlib import Path

from kb_test_support import (
    ROOT,
    SKILL_SCRIPTS,
    _bump_doc,
    _closed_keep_fixture,
    _closed_keep_module,
    _doc_templates,
    _drift_fixture,
    _drift_task,
    _entry_lines,
    _fill_slots,
    _flip_status,
    _gen_all,
    _gen_doc_map,
    _index_section,
    _kb_clock,
    _kb_tier,
    _new_doc,
    _p2_fixture,
    _p3_family_paths,
    _status_drift,
    _tier_fixture,
    _tier_pitfall,
    _wrap,
    _write_issue,
    _write_plan,
    _write_slice,
    _write_task,
)


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


def test_wrap_archive_flag_anchors_umbrella_archive(tmp_path: Path) -> None:
    """`--archive` 显式锚档案: 伞形档案与派生计划各持不同 key 时一次同时命中两侧。

    不传 `--archive` 时行为不变 (用 `--topic` 匹配档案), 落空提示保留原文案且档案零触碰;
    传了则档案按 `--archive` 的 `**Topics:**` 键精确匹配, 切片文件名仍由 `--topic` 决定。
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    wrap = _wrap()
    new_doc = _new_doc()
    import timekit  # 必须在 helper 之后 —— helper 负责把 SKILL_SCRIPTS 插进 sys.path

    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def wrap_run(topic: str, did: str, archive: str | None = None) -> tuple[int, str]:
        argv = ["--root", str(tmp_path), "--mb-dir", str(mb), "--topic", topic, "--did", did]
        if archive is not None:
            argv += ["--archive", archive]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = wrap.main(argv)
        return rc, out.getvalue()

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        assert (
            new_doc.main(
                [
                    "--root",
                    str(tmp_path),
                    "--mb-dir",
                    str(mb),
                    "task",
                    "--title",
                    "伞形档案",
                    "--topic",
                    "test-umbrella-audit",
                ]
            ) == 0
        )
    archive = next((mb / "tasks").glob("*-test-umbrella-audit.md"))
    before = archive.read_text(encoding="utf-8")

    # 不传 --archive: 沿用 --topic 匹配 → 落空 (默认行为不变), 档案零触碰
    rc, out = wrap_run("derived-slice", "不传锚点")
    assert rc == 0
    assert "未找到同专题档案" in out, f"未传 --archive 应保留原文案: {out}"
    assert archive.read_text(encoding="utf-8") == before, "落空时档案不得被改"

    # 传 --archive: 异键伞形档案被命中并更新
    rc, out = wrap_run("derived-slice", "传锚点", archive="test-umbrella-audit")
    assert rc == 0
    assert "未找到" not in out, f"--archive 命中时不该有落空提示: {out}"
    assert "已更新档案" in out, f"应按 --archive 键命中档案: {out}"
    text = archive.read_text(encoding="utf-8")
    today = timekit.now().strftime("%Y-%m-%d")
    assert f"**Updated:** {today}" in text, "命中的档案应抬 Updated 到今天"
    assert "传锚点" in text, "命中的档案进度日志应追加本轮 did"
    slice_file = next((mb / "activeContext").glob("*-derived-slice.md"))
    assert "**R1(" in slice_file.read_text(encoding="utf-8"), "切片仍按 --topic 抬活动 + 追加 R 行"

    # 坏 kebab: 与 --topic 同一 SLUG_RE 校验
    rc, out = wrap_run("derived-slice", "坏锚点", archive="Bad_Key")
    assert rc == 1, f"非 kebab 的 --archive 必须拒: {out}"


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


def test_new_doc_templates_lead_with_only_answer_slot() -> None:
    """模板的第一个 SLOT 必须是「本篇只回答」, 并带上预算 + 触顶固定动作。

    写前判定靠模板落地 (2026-11-05 计划 26-11-05-1049 §07 P1/P2): 第一格先问「这篇只回答什么」,
    跨问题就拆件; 预算与「禁止压文案」写进同一句, 免得建件后才发现该拆。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    fams = _common.FAMILIES
    templates = SKILL_SCRIPTS.parent / "templates"
    for fam in ("plan", "task", "report", "pitfall", "progress"):
        text = (templates / fams[fam].template).read_text(encoding="utf-8")
        slots = re.findall(r"<!--\s*SLOT:.*?-->", text, re.S)
        assert slots, f"{fam} 模板不得零 SLOT"
        assert "本篇只回答" in text, f"{fam} 模板缺「本篇只回答」"
        assert "只回答" in slots[0], f"{fam} 模板的第一个 SLOT 必须问「只回答什么」: {slots[0][:80]}"
        if fam == "report":
            assert "快照冻结, 不设 cap" in text, "report 冻结件不设 cap"
        else:
            assert "预算" in text and "禁止压文案" in text, f"{fam} 模板须写明预算与触顶固定动作"


def test_doc_templates_checker_is_wired() -> None:
    """检查器必须挂在 kb.check 与提交闸门两侧 —— 不接线 = 没人跑 (与
    test_wording_guard_is_wired_into_kb_check / test_commit_gate_covers_kb_check 同旨)。"""
    kb_cfg = (ROOT / ".commands" / "kb" / "config.toml").read_text(encoding="utf-8")
    body = re.search(r'^\[tasks\."kb\.check"\]\n(.*?)(?=^\[|\Z)', kb_cfg, re.S | re.M)
    assert body, "kb/config.toml 里找不到 kb.check"
    assert "check_doc_templates.py --check" in body.group(1), "check_doc_templates.py --check 未挂进 kb.check"

    gate_cfg = (ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml").read_text(encoding="utf-8")
    assert "check_doc_templates.py --check" in gate_cfg, "check_doc_templates.py --check 未挂进提交闸门"


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

    # 无 --refs → 与 P1 行为一致 (无反向补链行); doc-refs meta 模板自带**空值占位** (2026-10-31 起,
    # issue 26-10-31-2226-feat-kb-docrefs-bidirectional-automation: 建件即带占位, 回填走原位改值)
    rc, out, err = run("plan", "--title", "无引用", "--topic", "no-refs")
    assert rc == 0, err
    noref = list((mb / "plans").glob("*-plan-no-refs.html"))
    assert '<meta name="doc-refs" content="">' in noref[0].read_text(encoding="utf-8")
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
    assert "> 已外迁:" in main_text and f"](attachments/{att.name})" in main_text, "指针指向附件相对路径"
    assert "判据单点一句话" in main_text, "摘要判据单点必须留在主档可读位置"
    assert "事故时间线" not in main_text, "叙事段应已迁出"

    # --- 迁后重跑: 主档已带指针, 按幂等闸跳过 (不进外迁清单、零写盘)
    rc, out, err = run("migrate", "--level", "L2")
    assert rc == 0 and "幂等跳过" in out, out


def test_kb_tier_migrate_skips_already_migrated(tmp_path: Path) -> None:
    """kb.tier migrate 幂等闸: 主档已带 `> 已外迁:` 指针的文件一律跳过 —— 即使残留
    `## ` 正文段也不二次外迁、不产生第二份附件 (R1 实测: git/ 已迁档会被旧逻辑重复处理)。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    tier = _kb_tier()
    mb = _tier_fixture(tmp_path)
    # 已迁档形态: 头部 + 指针行 + 残留 `## ` 段 (迁后又手工补写过的极端形态)
    pit = mb / "pitfalls" / "git" / "migrated-already.md"
    pit.write_text(
        "# migrated-already\n"
        "\n"
        "> 摘要: 判据单点一句话。\n"
        "> 等级: L2\n"
        "> 触发: git, sync\n"
        "\n"
        "> 已外迁: 叙事整段迁至 [migrated-already-migrated-26-10-31-0952.md]"
        "(attachments/migrated-already-migrated-26-10-31-0952.md) (kb.tier migrate 26-10-31-0952)\n"
        "\n"
        "## 迁后残留段\n"
        "\n"
        "- 迁后又手工补写的内容。\n",
        encoding="utf-8",
        newline="\n",
    )
    before = pit.read_bytes()

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = tier.main(["--root", str(tmp_path), "--mb-dir", str(mb), *argv])
        return rc, out.getvalue(), err.getvalue()

    # --- dry-run: 按指针幂等跳过, 不进外迁清单、不建附件目录、主档零改动
    rc, out, err = run("migrate", "--level", "L2")
    assert rc == 0, err
    assert "幂等跳过" in out and "migrated-already" in out, out
    assert "将外迁" not in out, "已迁档不得进外迁清单"
    assert not (mb / "pitfalls" / "git" / "attachments").exists()
    assert pit.read_bytes() == before

    # --- --apply 也不写盘: 零新附件、主档零改动
    rc, out, err = run("migrate", "--level", "L2", "--apply")
    assert rc == 0, err
    assert "幂等跳过" in out, out
    assert not (mb / "pitfalls" / "git" / "attachments").exists(), "不得产生第二份附件"
    assert pit.read_bytes() == before, "主档零改动"


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


def test_closed_keep_trims_done_to_60_and_archives_full(tmp_path: Path) -> None:
    """阈值语义: Done 62 件 -> 主索引只留**最近 60** 条 + 一行隐藏提示; 归档是全量(只列 slug 与标题)。

    档案原地不动(出口只治索引视图) —— 夹具文件一个不搬, 由"归档里每件都能反查"间接守住。
    """
    gen = _closed_keep_module()
    root, mb = _closed_keep_fixture(tmp_path, done=62, inflight=2)

    rendered = gen.build(root, mb)
    done_section = _index_section(rendered, "Done")
    assert len(_entry_lines(done_section)) == 60, "Done 区只保留最近 60 条"
    assert "closed-keep-062" in done_section and "closed-keep-061" in done_section, "最近两件必须在"
    assert "closed-keep-001" not in done_section and "closed-keep-002" not in done_section, "最老两件出索引"
    assert "> 更早的 **2** 条已出本索引" in done_section, "隐藏提示行(形态同 issues 侧)"
    assert "x" * 80 not in rendered, "主索引摘要按 SUMMARY_MAX 截断"

    inflight_section = _index_section(rendered, "In Progress")
    assert "closed-keep-063" in inflight_section and "closed-keep-064" in inflight_section, "在办不受影响"

    archive = gen.build_archive(root, mb)
    assert "closed-keep-001" in archive and "closed-keep-062" in archive, "归档是全量(被主索引隐藏的件也在)"
    assert "x" * 80 not in archive, "归档行不带摘要 —— Summary 里可能带相对 tasks/ 的链接, 搬进 attachments 会位移成坏链"
    assert "](../26-01-01-test-closed-keep-001.md)" in archive, "归档链接带 ../ 指回档案原文"


def test_closed_keep_boundary_at_60(tmp_path: Path) -> None:
    """第 60/61 条边界: 恰 60 条不裁、无提示; 第 61 条起裁 1 条并出提示 —— 跟 issues 侧同一口径。"""
    gen = _closed_keep_module()

    root, mb = _closed_keep_fixture(tmp_path, done=60)
    rendered = gen.build(root, mb)
    assert len(_entry_lines(_index_section(rendered, "Done"))) == 60
    assert "更早的" not in rendered, "恰在阈值内不得出现隐藏提示"

    root, mb = _closed_keep_fixture(tmp_path / "second", done=61)
    rendered = gen.build(root, mb)
    assert len(_entry_lines(_index_section(rendered, "Done"))) == 60
    assert "> 更早的 **1** 条已出本索引" in _index_section(rendered, "Done")


def test_closed_keep_never_trims_inflight_and_dropped_also_trims(tmp_path: Path) -> None:
    """状态过滤: 在办(In Progress / Open)条数再多也不裁 —— 出口只治完结堆积; Dropped 同属完结区一并裁。"""
    gen = _closed_keep_module()
    root, mb = _closed_keep_fixture(tmp_path, done=61, dropped=61, inflight=65)

    rendered = gen.build(root, mb)
    inflight = _index_section(rendered, "In Progress")
    assert len(_entry_lines(inflight)) == 65, "在办条目不受 CLOSED_KEEP 影响"
    assert "更早的" not in inflight, "在办区不得出现隐藏提示"
    for status in ("Done", "Dropped"):
        section = _index_section(rendered, status)
        assert len(_entry_lines(section)) == 60, f"{status} 区裁到 60"
        assert "> 更早的 **1** 条已出本索引" in section


def test_closed_keep_archive_same_batch_wiring(tmp_path: Path) -> None:
    """归档清单与主索引**同批**落盘: `rebuild_index`(kb.status / kb.bump 的落点)两份都写 ——
    缺了归档, `gen_all --check` / 生成器自身 `--check` 恒红(同 gen_issues_index 的同批纪律)。"""
    gen = _closed_keep_module()
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    root, mb = _closed_keep_fixture(tmp_path, done=61)
    written = _common.rebuild_index(root, mb, "gen_tasks_index")
    assert {p.relative_to(mb).as_posix() for p in written} == {"tasks/_index.md", "tasks/attachments/_archive.md"}
    archive = mb / "tasks" / "attachments" / "_archive.md"
    assert archive.is_file(), "归档清单落 `tasks/attachments/`"
    assert archive.read_text(encoding="utf-8") == gen.build_archive(root, mb)
    # 命名与落点(计划 §07): 故意不叫 `_index.md` —— 那会被 role_of 套 index-auto 的 25,200 cap
    assert _common.ARCHIVE_NAME == "_archive.md" and not _common.ARCHIVE_NAME.endswith("_index.md")
    assert _common.ARCHIVE_REL == "attachments/_archive.md"
    assert gen.ARCHIVE_REL is _common.ARCHIVE_REL, "生成器用 `_common` 单点, 不另抄一份"


def test_closed_keep_constants_match_issues() -> None:
    """跨 skill 常量等值钉住: memory-bank 侧与 create-issue 的 gen_issues_index 同值同语义。

    跨 skill 不 import(单点纪律, 见 gen_all._load_isolated) —— 两边各有一份常量,
    漂移由本守阵拦住: 60 与归档落点任一侧改动, 这里立刻红。
    """
    gen_all = _gen_all()
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    ci_scripts = gen_all.find_skill_dir("create-issue", ROOT) / "scripts"
    assert ci_scripts.is_dir(), "定位不到 create-issue skill"
    issues_gen = gen_all._load_isolated(ci_scripts / "gen_issues_index.py", "_gen_issues_index_pin")
    assert _common.CLOSED_KEEP == issues_gen.CLOSED_KEEP == 60, "两侧 CLOSED_KEEP 必须同值(D14: 同一套常量语义)"
    assert _common.ARCHIVE_REL == issues_gen.ARCHIVE_REL == "attachments/_archive.md"
    # 完结状态同一语义: issues 的 CLOSED_STATUSES == 制品 5 词表的完结子集
    assert tuple(sorted(_common.TERMINAL_DOC_STATUSES)) == issues_gen.CLOSED_STATUSES


def test_issues_closed_keep_behavior_unchanged(tmp_path: Path) -> None:
    """issues/ 零行为变化回归: 61 件 Done issue -> 主索引只留最近 60 条 + 提示, 归档全量。

    本轮没改 gen_issues_index.py 一行 —— 这条守阵把"改造前"的行为钉下来, 防将来重构漂移。
    """
    gen_all = _gen_all()
    ci_scripts = gen_all.find_skill_dir("create-issue", ROOT) / "scripts"
    issues_gen = gen_all._load_isolated(ci_scripts / "gen_issues_index.py", "_gen_issues_index_reg")
    issues = tmp_path / "issues"
    issues.mkdir()
    for n in range(1, 62):
        stamp = f"26-01-{n:02d}-0001"
        (issues / f"{stamp}-bug-closed-keep-{n:03d}.html").write_text(
            '<html><head>\n'
            f'<meta name="issue-status" content="Done">\n'
            f'<meta name="issue-stamp" content="{stamp}">\n'
            f'<meta name="issue-title" content="CLOSED_KEEP issue {n:03d}">\n'
            f'<meta name="issue-summary" content="issue {n:03d} 摘要">\n'
            '</head><body>x</body></html>\n',
            encoding="utf-8",
            newline="\n",
        )
    items = issues_gen.collect(issues)
    rendered = issues_gen.render(items, issues, tmp_path)
    done_section = _index_section(rendered, "Done")
    assert len(_entry_lines(done_section)) == 60, "issues 主索引 Done 区留最近 60 条"
    assert "> 更早的 **1** 条已出本索引" in done_section
    assert "closed-keep-001" not in done_section and "closed-keep-061" in done_section
    archive = issues_gen.render_archive(items, issues, tmp_path)
    assert "closed-keep-001" in archive and "closed-keep-061" in archive, "issues 归档仍是全量"


def test_wrap_reports_status_drift_lists(tmp_path: Path) -> None:
    """kb.wrap 尾部状态漂移扫描: C/D 清单默认只打计数 (--verbose 展开详情,
    wrap 自身不带 verbose flag), 空打「无」, 硬拦档 (A/B/异常) 非空附
    「状态漂移硬拦非空…」提示行 —— 清单只提示, wrap 退出码与结果不因此改变。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    wrap = _wrap()
    _status_drift()  # 确保 wrap 同进程 import 的模块可加载 (与 test_kb_scripts_import_cleanly 同面)

    def wrap_run(base: Path, mb: Path, topic: str, did: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = wrap.main(["--root", str(base), "--mb-dir", str(mb), "--topic", topic, "--did", did])
        return rc, out.getvalue()

    # --- 无漂移: 两档各打一行「无」, 无硬拦提示, wrap 照常成功
    mb0 = _drift_fixture(tmp_path / "clean")
    rc, out = wrap_run(tmp_path / "clean", mb0, "drift-clean", "无漂移收尾")
    assert rc == 0
    assert "状态漂移扫描 (check_status_drift; 只提示, 不拦截):" in out
    assert "[C 清单: 反链 x In Progress] 无" in out and "[D 清单: 完成断言] 无" in out
    assert "状态漂移硬拦非空" not in out

    # --- C/D 漂移: wrap 输出 summary 行 (不展开条目正文), wrap 仍成功且无硬拦提示
    mb1 = _drift_fixture(tmp_path / "soft")
    _drift_task(mb1, "inflight.md", "In Progress")
    _drift_task(mb1, "open-word.md", "Open", body="- 已完成 首版\n")
    (mb1 / "progress" /
     "implemented-w.md").write_text("# wrap fixture\n\n## 已实现\n\n- task [t](../tasks/inflight.md)\n", encoding="utf-8")
    rc, out = wrap_run(tmp_path / "soft", mb1, "drift-soft", "软漂移收尾")
    assert rc == 0
    assert "[C 清单: 反链 x In Progress] 1 条" in out
    assert "[D 清单: 完成断言] 1 条" in out
    # wrap 输出不应展开具体条目正文
    assert "[backlink-x-InProgress]" not in out, "wrap 不应展开 C 档条目"
    assert "inflight.md" not in out.split("状态漂移扫描")[1] if "状态漂移扫描" in out else False, "wrap C 档段不应出现文件名"
    assert "[done-assert]" not in out, "wrap 不应展开 D 档条目"
    assert "状态漂移硬拦非空" not in out

    # --- 硬拦漂移: 附提示行, 但 wrap 退出码与机械面 (建切片) 不受影响
    mb2 = _drift_fixture(tmp_path / "hard")
    _drift_task(mb2, "open.md", "Open")
    (mb2 / "progress" / "implemented-h.md"
    ).write_text("# wrap hard fixture\n\n## 已实现\n\n- task [t](../tasks/open.md)\n", encoding="utf-8")
    rc, out = wrap_run(tmp_path / "hard", mb2, "drift-hard", "硬漂移收尾")
    assert rc == 0, "清单与提示只提示不失败"
    assert "状态漂移硬拦非空, 先 commands run kb.status 处理(部分完成翻 In Progress)再收尾" in out
    assert "[C 清单: 反链 x In Progress] 无" in out and "[D 清单: 完成断言] 无" in out
    assert len(list((mb2 / "activeContext").glob("*-drift-hard.md"))) == 1, "机械面照常完成"
