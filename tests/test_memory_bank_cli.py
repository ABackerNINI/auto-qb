"""test_memory_bank_cli 测试计划: Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
一旦索引与档案脱钩 (登记了没文件 / 有文件没登记)、状态分区与档案 `Status` 不一致、
必备章节缺失, 下次会话就无法从 `tasks/` 续作; 同专题重复建档会让续作难以接续 (2026-11-08 重构: tasks 索引与顶层易变件已删, 相关守卫随宿主收缩)。这些判定都是纯静态的, 用测试守住成本极低。

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
  抬 doc-updated / Updated; issue 翻转 (2026-11-07 W4 收编, 计划 26-11-07-0549 D5)
  徽标+meta+日志行一次改; 同状态翻转幂等 (不抬戳不追加); 词表外值/切片/未知载体/缺状态行
  全 fail-fast; 终态带条件提醒 (切片迁出 / Summary 收口); 输出含「机械 0」
  (2026-11-08 重构 W3: 翻转后重建索引的断言随索引生态退役删除 —— kb.status 不再重建任何索引)
- test_flip_status_issue_branch_badge_meta_and_log: issue 分支专项 (W4) —— 徽标+meta 双改
  (类型徽标零触碰) / 状态变更日志追加一行 (缩进对齐已有行, 已有行零触碰) / 幂等同状态零变化 /
  词表外值与缺徽标·缺日志节 fail-fast 不落半文件 / 终态提醒三态 (Done 修法 / Dropped 理由 /
  Superseded 指向) / 红绿双验 (R4): 单改徽标或单改 meta 的病态夹具被
  check_status_drift tier B 判红 —— 证明实现两处都动、漏一不可
- test_bump_doc_appends_changelog_and_fails_fast: 计划 R 行追加 (编号 = 段内最大+1, 已有行
  零触碰, note 自动 HTML 转义) + doc-updated 抬; 档案抬 Updated / 切片抬最后活动; 无变更
  记录段 fail-fast 指路; issue 改版仍拒绝 (文案指路 kb.status, W4 起翻状态走那边); 输出含「机械 0」
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

- test_new_doc_creates_phase2_families: 三族真建冒烟 (tmp 夹具) —— 坑档 `--class` 7 类 +
  `--triggers`(A7 参数分支, 头部零 SLOT)/ 报告出厂 Done / 基线 `--total` 誊写 + 基线时间
  排序键; 建后残留 SLOT 判红、填完判绿; 扫描面恰 2 件 (report+baseline);
  stdout 含「机械 0」收录断言 (2026-11-08 重构 W3: progress 族退役, 冒烟随之收缩)
- test_new_doc_phase2_family_params_fail_fast: 族参数校验 —— 坑档缺/坏 `--class`、缺
  `--triggers`; 基线缺 `--total` 全 fail-fast (之后假定输入合法)
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

issue 族建件收编 (2026-11-07 W3, 计划 26-11-07-0549 D4 —— 翻案 26-10-17-0527 D2;
实现 = `_common.FAMILIES["issue"]` 扩行 (template_by_tier / type_enum 两机制) + new_doc 分派 +
new_issue.py 退役, 进程内 import):

- test_new_doc_creates_issue_family_end_to_end: `kb.new issue` 端到端 (tmp 夹具) ——
  light (docs→light 默认档) / standard (--tier 覆盖与 bug→standard 推导) 各建一件: 命名
  (ISSUE_FILE_RE 完整文件名) / meta (slug/type/tier/status=Open/topic 默认 slug 与显式覆盖) /
  badge 机读形态 (2026-11-08 重构 W3: issues 索引已退役, 建后不再重建); 幂等拒绝 (冻结
  timekit.now); --refs 双向补链;
  末尾 kb.new → kb.status 全链一步 (评审 RB2 1a): 对真建出的 issue 翻 In Progress, 断言
  badge / meta / 状态变更日志行 三处
- test_new_doc_issue_params_fail_fast: issue 族参数校验 —— 枚举外 --type / 缺 --type /
  缺 --summary / 缺 slug / 坏 slug / 坏 --topic / 位置 + --topic 异值全 fail-fast;
  不提供 --status (出厂恒 Open, 翻状态走 kb.status) 由 argparse 拒未知参数钉住
- test_new_doc_key_arg_unified_positional: 传参统一 (issue 26-11-08-1131) —— 主键位置参数
  与 --topic 两形态全族等价: 非 issue 族位置单传可建 (plan/baseline, 原「不接受位置参数」
  拒收面翻正) / 同给同值幂等放行 / 异值拒 (fail-fast); issue 缺位置 --topic 兼作 slug,
  位置给足时 --topic 仍是 doc-topic 覆盖 (W3 行为不变)
- test_checker_scan_face_excludes_issues (D6 拍板钉): issue 入 FAMILIES 不得扩大
  check_doc_templates 的冻结线扫描面 —— 线后遍体缺陷的 issue 件零触碰 (不计数不报红),
  同目录缺陷 plan 件照常判红 (证明扫描面本身没坏)
- test_family_registry_matches_templates (扩展): issue 族同源钉 —— template_by_tier 键 =
  TIERS 且两档模板文件在; type_enum / naming_re / statuses 皆 `_common` 单点本身 (is 身份);
  set(TYPES) <= set(TIER_BY_TYPE) (扩类型漏同步档位映射时 kb.new 当场 _fail, 评审 RB2 守阵);
  ISSUE_FILE_RE 中段从 TYPES 拼 (枚举内全中 / 枚举外拒); badge+issue-status meta 双占位在模板
  (check_status_drift tier B 机读形态); 双模板机读锚命中 (评审 RB2 1b): BADGE_RE「状态」包裹层 +
  「状态变更日志」h2 + 节内裸 ul, 用实现侧同一份正则钉模板 —— 防措辞漂移让 kb.status 对所有
  新建件 rc=1 而测试仍绿

时间守卫 (检查器 memory-bank skill 的 `scripts/timekit.py`, 2026-10-06 加):


回写措辞守卫 (检查器 memory-bank skill 的 `scripts/check_wording.py`, 2026-10-07 加):


常驻锚防流水守卫 (检查器 memory-bank skill 的 `scripts/check_mutation_anchor.py`, 2026-10-31 加):


2026-11-08 重构 W3 机器退役 (计划 26-11-08-1625 D5/D12) 的删测注记 —— 以下守阵随宿主退役,
无行为可守, 整组删除 (非移入他处):
- 分级清理四动作 6 条 (脚本本体与 .commands/kb 的对应条目已删; pitfalls 头部 `> 等级:` 行的数据清理归 T8)
- CLOSED_KEEP 索引出口 5 条 (tasks/plans/reports/issues 的 `_index.md` 与 `_archive.md` 已随
  低价值层移除, 生成器/rebuild_index 分支/相关常量同批退役)

状态漂移守卫 (检查器 memory-bank skill 的 `scripts/check_status_drift.py`, 2026-10-31 加, **进程内
import**, tmp 夹具不碰真实 memory-bank/; B issue badge vs meta / 异常 status-unreadable 两档
硬拦 rc=1, D 完成断言清单只提示; 2026-11-08 重构 W5: 原 A/C 反链两档随 progress/ 退役删除):

- test_wrap_reports_status_drift_lists: kb.wrap 尾部打印 D 清单(空打「无」), 硬拦非空附「状态漂移硬拦非空…」提示行, wrap 退出码与结果不因此改变

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
    _doc_templates,
    _drift_fixture,
    _drift_issue,
    _drift_task,
    _fill_slots,
    _flip_status,
    _gen_doc_map,
    _kb_clock,
    _new_doc,
    _p2_fixture,
    _p3_family_paths,
    _status_drift,
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
    三类: 1. 连字符领域可建 2. 前缀撞名 (`memory-` 开头的非领域) 不得被误收
    3. 真坏领域仍 fail-fast; 裸领域 topic (topic == 枚举项) 沿用 P1 行为照收。
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
    created = list((mb / "active-context").glob("*-wrap-slug.md"))
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
    slice_file = next((mb / "active-context").glob("*-derived-slice.md"))
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
    import check_status_drift
    import flip_status

    fams = _common.FAMILIES
    templates = SKILL_SCRIPTS.parent / "templates"
    for name, spec in fams.items():
        if spec.template_by_tier:
            # 分级族 (issue, W3): 单值 template 让位为空串, 模板按档位从 template_by_tier 选
            assert spec.template == "", f"{name} 族分级选模板时单值 template 必须让位为空串"
            assert set(spec.template_by_tier) == set(_common.TIERS), \
                f"{name} 族 template_by_tier 键必须 == TIERS 单点: {sorted(spec.template_by_tier)}"
            for tier, tpl in spec.template_by_tier.items():
                assert (templates / tpl).is_file(), f"{name} 族 {tier} 档模板缺失: {tpl}"
        else:
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
    # (2026-11-08 重构 W3: progress 族退役, 三行头 --triggers 族只剩 pitfall)
    tpl = (templates / fams["pitfall"].template).read_text(encoding="utf-8")
    assert "> 触发: @@TRIGGERS@@" in tpl, "pitfall 模板必须留触发词占位 (由 --triggers 填, 头部区不留 SLOT)"

    # P3: baseline 模板 H1 含 --total 占位 + 基线时间占位 (排序键, 回退用文件名前缀)
    baseline_tpl = (templates / fams["baseline"].template).read_text(encoding="utf-8")
    assert "# @@TOTAL@@ —— @@TITLE@@" in baseline_tpl, "baseline 模板 H1 必须含 --total 占位 (裁定 A4)"
    assert "> 基线时间: @@" in baseline_tpl, "baseline 模板必须留基线时间占位 (排序键)"

    # 词表单点: 族的 statuses 就是那两个单点**本身** (is, 不是副本)
    assert fams["plan"].statuses is _common.DOC_STATUSES
    assert fams["task"].statuses is _common.TASK_STATUSES
    assert fams["report"].statuses is _common.DOC_STATUSES, "report 与 plan 共用 5 词表单点"
    assert fams["slice"].statuses == (), "切片族无状态词 (三行头不带状态)"
    for fam in ("pitfall", "baseline"):
        assert fams[fam].statuses == (), f"{fam} 族无状态词"

    # 坑档族的子目录选择器 = 7 类枚举单点 (is 身份断言, 同 statuses 纪律)
    assert fams["pitfall"].subdir_values is _common.PITFALL_CLASSES, "坑档类枚举必须 import 单点, 不造副本"
    assert fams["pitfall"].subdir_flag == "class", "坑档子目录选择器 = --class"

    # W3 issue 族 (计划 26-11-07-0549 D4): 全部机制字段皆 `_common` 单点本身 (is 身份断言同上)
    issue = fams["issue"]
    assert issue.type_enum is _common.TYPES, "issue 族的 --type 枚举必须 import 单点, 不造副本"
    assert issue.naming_re is _common.ISSUE_FILE_RE, "issue 命名正则必须与索引校验同一份 (单点)"
    # TIER_BY_TYPE 必须覆盖 TYPES 全集 (评审 RB2): kb.new issue 的档位推导按 type 查表,
    # 缺项 = 扩 TYPES 时漏同步, 建件当场 _fail (new_doc 已改 .get + fail-fast, 这里钉住映射不缺)
    assert set(_common.TYPES) <= set(_common.TIER_BY_TYPE), \
        f"TYPES 每个类型必须有 TIER_BY_TYPE 默认档位: 缺 {sorted(set(_common.TYPES) - set(_common.TIER_BY_TYPE))}"
    assert issue.statuses is _common.DOC_STATUSES, "issue-status 与 doc-* 制品同一 5 词表单点"
    assert issue.default_status == "Open", "issue 出厂恒 Open (翻状态走 kb.status, CLI 不设 --status)"
    assert issue.index_script == "", "issue 索引已随 2026-11-08 重构退役 (D4/D5), 建后不再重建"
    assert issue.ext == ".html" and issue.dir == "issues"
    # ISSUE_FILE_RE 中段从 TYPES 单点拼出 (W3 机制二): 枚举内全部命中, 枚举外拒
    for type_ in _common.TYPES:
        assert _common.ISSUE_FILE_RE.match(f"26-11-07-0549-{type_}-some-slug.html"), \
            f"枚举内类型 {type_} 必须命中命名正则"
    assert _common.ISSUE_FILE_RE.match("26-11-07-0549-nope-slug.html") is None, \
        "枚举外类型必须被命名正则拒 (中段从 TYPES 拼, 不手抄第二份)"
    assert _common.ISSUE_FILE_RE.match("26-11-07-0549-bugfix-slug.html") is None, \
        "枚举项前缀加长 (bugfix) 不得误命中"
    # 模板机读形态: badge (check_status_drift tier B) 与 issue-status meta 双占位 + 默认状态 Open
    for tpl in issue.template_by_tier.values():
        issue_tpl = (templates / tpl).read_text(encoding="utf-8")
        assert '<span class="badge">@@STATUS@@</span>' in issue_tpl, f"{tpl} 必须保留状态 badge 机读形态"
        assert '<meta name="issue-status" content="@@STATUS@@">' in issue_tpl, f"{tpl} 必须保留 issue-status meta"
        assert f'content="{issue.default_status}"' not in issue_tpl, f"{tpl} 的状态由 @@STATUS@@ 占位 (命令填), 不得烤死"
        # 双模板机读锚命中 (评审 RB2 1b): kb.status 对新建件的三个锚 (badge 包裹层 / 日志 h2 / 节内
        # 裸 ul) 必须逐字命中 —— 措辞漂移会让 kb.status 对**所有**新建件 rc=1 而这里仍绿, 故用
        # 实现侧同一份正则 (BADGE_RE / ISSUE_LOG_H2_RE) 钉模板, 不手抄第二份
        badge = check_status_drift.BADGE_RE.search(issue_tpl)
        assert badge and badge.group(1) == "@@STATUS@@", \
            f"{tpl} 必须命中 check_status_drift.BADGE_RE (「状态」包裹层 + badge 机读锚)"
        log_h2 = flip_status.ISSUE_LOG_H2_RE.search(issue_tpl)
        assert log_h2, f"{tpl} 必须命中 flip_status.ISSUE_LOG_H2_RE (「状态变更日志」h2 锚)"
        nxt = flip_status.NEXT_H2_RE.search(issue_tpl, log_h2.end())
        log_section = issue_tpl[log_h2.end():nxt.start() if nxt else len(issue_tpl)]
        assert re.search(r"<ul>.*?</ul>", log_section, re.DOTALL), \
            f"{tpl} 状态变更日志节内必须有裸 <ul> (flip 的日志节锚)"
    assert '@@TOPIC@@' in (templates / issue.template_by_tier["light"]).read_text(encoding="utf-8"), \
        "issue 模板必须留 doc-topic 占位 (主键不可省, 缺它从专题视图静默漏掉)"

    # 头部区零 SLOT (计划 §05 渲染正确性契约): 机器字段由命令填, SLOT 只允许出现在正文区
    checker = _doc_templates()

    def _family_templates(spec) -> list[str]:
        """单值模板或分级全档模板 (issue 族按档位逐个查)。"""
        return list(spec.template_by_tier.values()) if spec.template_by_tier else [spec.template]

    for name, spec in fams.items():
        for tpl in _family_templates(spec):
            head = checker._head_region((templates / tpl).read_text(encoding="utf-8"))
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
    for fam in ("plan", "task", "report", "pitfall"):
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
    """kb.status: 计划/档案/issue 翻转 + 抬时间戳 (issue 走日志行留痕); 幂等不抬戳;
    切片/未知载体/词表外值拒绝全 fail-fast; 终态带条件提醒; 输出含「机械 0」收录断言 (§5.3 / §5.4)。
    issue 分支的专项 battery (两处改/日志行/幂等/红绿双验) 在 test_flip_status_issue_branch_badge_meta_and_log。
    (2026-11-08 重构 W3: 重建索引断言已删 —— 改面四族 _index 退役, kb.status 不再重建任何索引。)"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    flip = _flip_status()
    mb = _p2_fixture(tmp_path)
    plan = _write_plan(mb)
    task = _write_task(mb)
    _write_slice(mb)
    issue = _write_issue(mb)

    def run(path: str, to: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = flip.main(["--root", str(tmp_path), "--mb-dir", str(mb), path, to])
        return rc, out.getvalue(), err.getvalue()

    # --- 计划翻转: 状态 + doc-updated 都抬, 契约输出 (不再重建索引 —— 2026-11-08 W3)
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "In Progress")
    assert rc == 0, err
    assert "doc-status Open → In Progress" in out and "已重建索引" not in out and "机械 0" in out, out
    assert out.count("剩余人工") == 1, "契约行只打一次"
    ptext = plan.read_text(encoding="utf-8")
    assert '<meta name="doc-status" content="In Progress">' in ptext
    assert '<meta name="doc-updated" content="26-10-17-0900">' not in ptext, "doc-updated 应被抬"
    assert "· <b>doc-status</b> In Progress ·" in ptext, "正文 .meta 镜像行的状态词应同改"
    assert "<b>doc-updated</b> 26-10-17-0900" not in ptext, "正文 .meta 镜像行的 doc-updated 应同抬"

    # --- 终态: 条件提醒 (同专题切片迁出), 计数行 条件 1
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "Done")
    assert rc == 0 and "条件 1" in out and "切片" in out and "p2-topic" in out, out

    # --- 同状态幂等: 不抬时间戳 (黄金法则: 幂等无副作用)
    before = plan.read_text(encoding="utf-8")
    rc, out, err = run("plans/26-10-17-0900-plan-p2.html", "Done")
    assert rc == 0 and "幂等" in out and "已重建索引" not in out, out
    assert plan.read_text(encoding="utf-8") == before, "幂等翻转不得改文件"

    # --- 拒绝面全 fail-fast (原因打在输出里); issue 不再拒收 (W4), 翻转见下方专项断言
    rc, _, err = run("plans/26-10-17-0900-plan-p2.html", "Draft")
    assert rc == 1 and "词表" in err, f"词表外值必须拒绝: {err}"
    rc, _, err = run("active-context/26-10-17-0900-p2-topic.md", "Done")
    assert rc == 1 and "kb.wrap" in err, f"切片无状态, 必须拒绝并指路 kb.wrap: {err}"
    rc, _, err = run("memory-bank/nope.md", "Done")
    assert rc == 1 and "文件不存在" in err, f"不存在的路径必须拒绝: {err}"

    # --- issue 翻转 (W4 收编): 徽标 + meta 两处一致 + 日志行 (不再重建索引 —— 2026-11-08 W3)
    rc, out, err = run("issues/26-10-17-0900-bug-p2.html", "Done")
    assert rc == 0, err
    assert "issue-status Open → Done" in out and "已重建索引" not in out and "机械 0" in out, out
    assert "实际修法" in out, "issue 终态 (Done) 应带修法提醒"
    itext = issue.read_text(encoding="utf-8")
    assert '<meta name="issue-status" content="Done">' in itext, "issue-status meta 应改"
    assert '<span class="badge">Done</span>' in itext, "状态徽标应改"
    assert '<span class="badge type">bug</span>' in itext, "类型徽标不得误伤"
    assert "状态 Open → Done（kb.status）" in itext, "状态变更日志应追加一行"

    # --- 档案翻转: **Status:** + **Updated:** + 终态 Summary 收口提醒
    rc, out, err = run("tasks/26-10-17-backend-p2.md", "Done")
    assert rc == 0 and "Status In Progress → Done" in out and "Summary 收口" in out, out
    ttext = task.read_text(encoding="utf-8")
    today = _kb_clock().strftime("%Y-%m-%d")  # 与实现同源取时(见 _kb_clock)
    assert "**Status:** Done" in ttext and f"**Updated:** {today}" in ttext
    rc, _, err = run("tasks/26-10-17-backend-p2.md", "Archived")
    assert rc == 1 and "词表" in err, f"档案 4 词表外值必须拒绝: {err}"


def test_flip_status_issue_branch_badge_meta_and_log(tmp_path: Path) -> None:
    """kb.status issue 分支专项 (W4, 计划 26-11-07-0549 D5): 徽标+meta 两处一次改 + 状态变更日志
    追加一行; 幂等同状态零变化; 词表外值 / 缺徽标 / 缺日志节 fail-fast
    不落半文件; 终态提醒三态各自出现; 红绿双验 (计划 R4): 徽标/meta 单改其一的病态夹具被
    check_status_drift tier B 判红 —— 证明实现两处都动、漏一不可。
    (2026-11-08 重构 W3: 重建索引断言已删 —— issues/_index.md 退役, kb.status 不再重建任何索引。)"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    flip = _flip_status()
    drift = _status_drift()
    mb = _p2_fixture(tmp_path)
    issue = _write_issue(mb)

    def run(path: str, to: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = flip.main(["--root", str(tmp_path), "--mb-dir", str(mb), path, to])
        return rc, out.getvalue(), err.getvalue()

    def drift_check() -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = drift.main(["--root", str(tmp_path), "--mb-dir", str(mb)])
        return rc, out.getvalue() + err.getvalue()

    # --- Open → In Progress: badge 与 meta 双改 (类型徽标零触碰) + 日志行 (不再重建索引)
    rc, out, err = run("issues/26-10-17-0900-bug-p2.html", "In Progress")
    assert rc == 0, err
    assert "issue-status Open → In Progress" in out and "已重建索引" not in out and "机械 0" in out, out
    text = issue.read_text(encoding="utf-8")
    assert '<meta name="issue-status" content="In Progress">' in text, "meta 必须同改"
    assert '<span class="badge">In Progress</span>' in text, "状态徽标必须同改"
    assert '<span class="badge type">bug</span>' in text, "类型徽标不得误伤"
    today = _kb_clock().strftime("%Y-%m-%d")
    assert f"<li>{today} — 状态 Open → In Progress（kb.status）</li>" in text, "日志行应追加"
    assert text.count("状态变更日志") == 1 and text.count("<li>2026-10-17 — 入池") == 1, "已有日志行零触碰"
    # (2026-11-08 重构 W3: 原索引分区断言已删 —— issues/_index.md 退役, 翻转不再重建。)
    # 翻转后 badge vs meta 一致: check_status_drift tier B 对本夹具判绿
    drc, dout = drift_check()
    assert drc == 0 and "badge-vs-meta" not in dout, dout

    # --- 红绿双验 (R4): 单改徽标 / 单改 meta 的病态夹具 (模拟实现漏改其一的产物), tier B 必判红
    badge_only = mb / "issues" / "26-10-17-0901-doc-badge-stale.html"
    badge_only.write_text(
        '<html><head><meta name="issue-status" content="Open"></head><body>\n'
        '<div class="item"><div class="k">状态</div><div class="v"><span class="badge">Done</span></div></div>\n'
        "</body></html>\n",
        encoding="utf-8",
        newline="\n",
    )
    meta_only = mb / "issues" / "26-10-17-0902-doc-meta-stale.html"
    meta_only.write_text(
        '<html><head><meta name="issue-status" content="Done"></head><body>\n'
        '<div class="item"><div class="k">状态</div><div class="v"><span class="badge">Open</span></div></div>\n'
        "</body></html>\n",
        encoding="utf-8",
        newline="\n",
    )
    drc, dout = drift_check()
    assert drc == 1, "病态夹具 (单改其一) 必须被 tier B 判红"
    assert "badge='Done' meta='Open'" in dout, "只改 meta 漏改徽标 → badge=Done meta=Open 应判红"
    assert "badge='Open' meta='Done'" in dout, "只改徽标漏改 meta → badge=Open meta=Done 应判红"
    badge_only.unlink()
    meta_only.unlink()

    # --- 幂等: 同状态再翻零变化 (不追加日志行 / 不改文件)
    before = issue.read_text(encoding="utf-8")
    rc, out, err = run("issues/26-10-17-0900-bug-p2.html", "In Progress")
    assert rc == 0 and "幂等" in out and "已重建索引" not in out, out
    assert issue.read_text(encoding="utf-8") == before, "幂等翻转不得改文件"

    # --- 词表外值: 拒绝且不改文件 (词表纪律的活体校验在 gen_doc_map --check, 见 doc-status-meta 坑档)
    rc, _, err = run("issues/26-10-17-0900-bug-p2.html", "Fixed")
    assert rc == 1 and "词表" in err, f"issue 5 词表外值必须拒绝: {err}"
    assert issue.read_text(encoding="utf-8") == before, "词表拒绝不得改文件"

    # --- 终态提醒三态: Done → 修法 / Dropped → 理由 / Superseded → 指向 (日志行逐次追加)
    rc, out, err = run("issues/26-10-17-0900-bug-p2.html", "Done")
    assert rc == 0 and "条件 1" in out and "实际修法" in out, out
    rc, out, err = run("issues/26-10-17-0900-bug-p2.html", "Dropped")
    assert rc == 0 and "写明放弃理由" in out, out
    assert f"<li>{today} — 状态 Done → Dropped（kb.status）</li>" in issue.read_text(encoding="utf-8")
    rc, out, err = run("issues/26-10-17-0900-bug-p2.html", "Superseded")
    assert rc == 0 and "写明指向" in out, out
    text = issue.read_text(encoding="utf-8")
    assert f"<li>{today} — 状态 Dropped → Superseded（kb.status）</li>" in text
    assert '<span class="badge">Superseded</span>' in text
    assert '<meta name="issue-status" content="Superseded">' in text

    # --- 缺徽标 / 缺日志节: fail-fast 不落半文件 (存量老件缺徽标由 tier B 豁免, 但 kb.status 不做半改)
    nobadge = mb / "issues" / "26-10-17-0903-bug-nobadge.html"
    nobadge.write_text(
        '<html><head><meta name="issue-status" content="Open"></head><body>x</body></html>\n',
        encoding="utf-8",
        newline="\n",
    )
    rc, _, err = run("issues/26-10-17-0903-bug-nobadge.html", "Done")
    assert rc == 1 and "徽标" in err, f"缺状态徽标必须拒绝: {err}"
    assert '<meta name="issue-status" content="Open">' in nobadge.read_text(encoding="utf-8"), "fail-fast 不得改文件"
    nolog = mb / "issues" / "26-10-17-0904-bug-nolog.html"
    nolog.write_text(
        '<html><head><meta name="issue-status" content="Open"></head><body>\n'
        '<div class="item"><div class="k">状态</div><div class="v"><span class="badge">Open</span></div></div>\n'
        "</body></html>\n",
        encoding="utf-8",
        newline="\n",
    )
    rc, _, err = run("issues/26-10-17-0904-bug-nolog.html", "Done")
    assert rc == 1 and "状态变更日志" in err, f"缺日志节必须拒绝不硬塞: {err}"
    assert '<meta name="issue-status" content="Open">' in nolog.read_text(encoding="utf-8"), "fail-fast 不得改文件"


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
    assert rc == 0 and "R1" in out and "机械 0" in out and "已重建索引" not in out, out
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
    rc, out, err = run("active-context/26-10-17-0900-p2-topic.md", "进展一句")
    assert rc == 0 and "最后活动" in out, out
    assert f"> 最后活动: {_kb_clock().strftime('%Y-%m-%d %H:%M')}" in slice_.read_text(encoding="utf-8")

    # 无变更记录段的件 → fail-fast 指路 (多数报告无段, 不猜位置硬塞)
    report = mb / "reports"
    report.mkdir()
    bad = report / "26-10-17-0900-report-nosec.html"
    bad.write_text(
        '<html><head><meta name="doc-updated" content="26-10-17-0900"></head><body>x</body></html>', encoding="utf-8"
    )
    rc, _, err = run("reports/26-10-17-0900-report-nosec.html", "x")
    assert rc == 1 and "变更记录" in err, f"无变更记录段必须拒绝并指路: {err}"
    assert '<meta name="doc-updated" content="26-10-17-0900">' in bad.read_text(encoding="utf-8"), "fail-fast 不得改文件"

    # issue 改版仍拒绝, 文案指路 kb.status (W4: 翻状态已收编 kb.status, 改版不在 bump 范围)
    rc, _, err = run("issues/26-10-17-0900-bug-p2.html", "x")
    assert rc == 1 and "kb.status" in err, err


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
        "memory-bank/active-context/26-10-17-0900-p2-topic.md"
    )
    assert rc == 0, err
    plan = list((mb / "plans").glob("*-plan-refs-plan.html"))
    assert len(plan) == 1
    ptext = plan[0].read_text(encoding="utf-8")
    assert '<meta name="doc-refs" content="memory-bank/tasks/26-10-17-backend-p2.md, ' \
           'memory-bank/pitfalls/git/sync-pull.md, memory-bank/issues/26-10-17-0900-bug-p2.html, ' \
           'memory-bank/active-context/26-10-17-0900-p2-topic.md">' in ptext, ptext[:600]
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
    (mb / "plans" / "_index.md").write_text("# idx\n", encoding="utf-8")
    for bad_refs, why in (("tasks/nope.md", "目标不存在"), ("AGENTS.md", "不在 memory-bank 下"), ("plans/_index.md", "生成物")):
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

    # 1. 先建档案, 再建计划并 --refs 档案 (D4 双向补链)
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

    # 2. 填空 (agent 的一次编辑)
    _fill_slots(plan[0])
    _fill_slots(task[0])
    assert checker.validate_file(plan[0], "plan") == [], "填空后计划必须过新增面守卫"
    assert checker.validate_file(task[0], "task") == [], "填空后档案必须过新增面守卫"

    # 3. kb.status 翻转 (终态)
    rc, out, err = run(flip, [str(plan[0].relative_to(tmp_path)), "In Progress"])
    assert rc == 0 and "已翻转" in out, out
    rc, out, err = run(flip, [f"memory-bank/plans/{plan[0].name}", "Done"])
    assert rc == 0 and "条件 1" in out, out
    rc, out, err = run(flip, [task_rel, "Done"])
    assert rc == 0 and "Summary 收口" in out, out

    # 4. kb.bump 改版记录 (计划有变更记录段)
    rc, out, err = run(bump, [f"memory-bank/plans/{plan[0].name}", "--note", "R1: 演练改版"])
    assert rc == 0 and "R1" in out, out

    # 5. 认领链双向机检绿 (计划 §07 P2 验收判据; gen_doc_map.main() 只读 sys.argv,
    #    进程内直调它的 check 函数 —— 与既有守卫直调 validate_file 同做法)
    docmap = _gen_doc_map()
    items = docmap.collect(mb)
    problems = docmap.check_claim_chain(items, tmp_path, mb)
    assert problems == [], f"认领链双向机检必须绿: {problems}"
    assert docmap.check_topics(items) == 0, "演练件的跨形态主键必须齐"
    assert docmap.check_status_vocabulary(items) == 0, "演练件状态词必须在 5 词表内"

    # 6. 红绿双验 (§06): 删掉目标件的反向声明 = 人工造单向链 → 机检必须红 (证明绿不是恒绿);
    #    还原 → 复绿
    ttext = task[0].read_text(encoding="utf-8")
    plan_rel = f"memory-bank/plans/{plan[0].name}"
    task[0].write_text(ttext.replace(f"**Refs:** {plan_rel}", ""), encoding="utf-8")
    broken = docmap.check_claim_chain(docmap.collect(mb), tmp_path, mb)
    assert any("反向声明" in p for p in broken), f"单向链必须判红 (判据恒绿 = 没守): {broken}"
    task[0].write_text(ttext, encoding="utf-8")
    assert docmap.check_claim_chain(docmap.collect(mb), tmp_path, mb) == [], "还原后必须复绿"

    # 7. 改过的件再过新增面守卫仍绿 (翻转/bump 没破坏形态)
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

    # 建后: 残留 SLOT 判红 (坑档不在扫描面 —— 直接 validate_file)
    assert checker.validate_file(paths["pitfall"], "pitfall"), "坑档建后应残留 SLOT (待填)"
    problems, checked = checker.check_new_faces(tmp_path, mb)
    assert checked == 2, f"扫描面应恰好 2 件 (线后 report + baseline): {checked}"
    assert len(problems) == 2, f"report 与 baseline 建后残留 SLOT 应判红: {problems}"

    # 填完: 三族 validate_file 全绿 + 扫描面全绿
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
    rc, err = run("baseline", title="x", topic="y")
    assert rc == 1 and "--total" in err, f"基线缺 --total 必须拒 (裁定 A4): {err}"


def test_new_doc_creates_issue_family_end_to_end(tmp_path: Path, monkeypatch) -> None:
    """W3 建件收编 (计划 26-11-07-0549 D4): `kb.new issue` 端到端 —— 建件 → 命名/meta/badge →
    幂等拒绝 → --topic 默认 slug 与显式覆盖 → --refs 双向补链。
    (2026-11-08 重构 W3: issues/_index.md 退役, 原「索引+归档同批重建」断言删除。)

    幂等拒绝断言冻结 timekit.now (同 test_new_doc_refuses_slice_and_duplicates 的判据:
    issue 文件名带分钟级戳, 真墙钟跨分钟 = 文件名不同永不撞名的时刻竞态)。
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common
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

    # 1. light (默认档: docs → light 经 TIER_BY_TYPE 推导, 不传 --tier)
    rc, out, err = run("issue", "smoke-issue", "--type", "docs", "--title", "冒烟问题标题", "--summary", "一句话简述")
    assert rc == 0, f"kb.new issue 必须建件成功: {err}"
    assert "机械 0" in out, f"输出缺「机械 0」收录断言: {out}"
    assert "剩余人工 1 项(判断 1 · 条件 0 · 机械 0)" in out, f"输出契约 (模板零 SLOT → 判断 1 项): {out}"
    assert "现象一句话" in out, f"light 档 NEXT_STEP 文案口径 (沿用 new_issue.py): {out}"
    issue = next((mb / "issues").glob("*-docs-smoke-issue.html"))
    assert _common.ISSUE_FILE_RE.match(issue.name), f"文件名必须合 ISSUE_FILE_RE (完整文件名): {issue.name}"
    text = issue.read_text(encoding="utf-8")
    assert f'<meta name="issue-stamp" content="{frozen.strftime(timekit.STAMP_FMT)}">' in text, \
        "时间必须来自 timekit 单点 (与冻结时钟同源)"
    assert '<meta name="issue-slug" content="smoke-issue">' in text
    assert '<meta name="issue-type" content="docs">' in text
    assert '<meta name="issue-tier" content="light">' in text, "docs 默认档 = light (TIER_BY_TYPE 推导)"
    assert '<meta name="issue-status" content="Open">' in text, "出厂恒 Open (spec.default_status)"
    assert '<meta name="doc-topic" content="smoke-issue">' in text, "--topic 缺省 = slug (doc-topic 主键不可缺)"
    assert '<meta name="doc-refs" content="">' in text, "模板自带空 doc-refs meta (--refs 可并值)"
    assert '<span class="badge">Open</span>' in text, "状态 badge 机读形态 (check_status_drift tier B)"
    assert "计划外问题（便签）" in text and "现象与发现场景" not in text, "light 档模板 (三段结构, 非 standard 七段)"
    assert "TODO" in text, "正文留 TODO 待按档位填写"
    # (2026-11-08 重构 W3: 原「索引 + 归档同批重建」断言已删 —— issues/_index.md 退役, 建后不再重建。)

    # 2. standard (--tier 显式覆盖 docs 的 light 默认)
    rc, out, err = run("issue", "smoke-std", "--type", "docs", "--tier", "standard", "--title", "标准档", "--summary", "简")
    assert rc == 0, f"--tier standard 覆盖必须成功: {err}"
    assert "现象 / 证据 / 影响面" in out, f"standard 档 NEXT_STEP 文案口径: {out}"
    std = next((mb / "issues").glob("*-docs-smoke-std.html")).read_text(encoding="utf-8")
    assert '<meta name="issue-tier" content="standard">' in std
    assert "现象与发现场景" in std and "计划外问题（未修）" in std, "standard 档模板 (七段结构)"

    # 3. bug → standard 默认推导 + --topic 显式覆盖 doc-topic (文件名仍用 slug)
    rc, _, err = run(
        "issue", "topic-override", "--type", "bug", "--title", "t", "--summary", "s", "--topic", "custom-topic"
    )
    assert rc == 0, f"bug 建件必须成功: {err}"
    bug = next((mb / "issues").glob("*-bug-topic-override.html")).read_text(encoding="utf-8")
    assert '<meta name="issue-tier" content="standard">' in bug, "bug 默认档 = standard (TIER_BY_TYPE 推导)"
    assert '<meta name="doc-topic" content="custom-topic">' in bug, "--topic 显式覆盖默认 slug"

    # 4. --refs D4 双向补链对 issue 件照常生效 (issue 为声明方)
    assert run("task", "--title", "链目标档案", "--topic", "backend-issue-ref")[0] == 0
    task = next((mb / "tasks").glob("*-backend-issue-ref.md"))
    rc, out, err = run(
        "issue", "chained-issue", "--type", "feat", "--title", "带链问题", "--summary", "链", "--refs",
        f"memory-bank/tasks/{task.name}"
    )
    assert rc == 0, f"--refs 建件必须成功: {err}"
    assert "已双向补链" in out, f"D4 反向补链输出: {out}"
    chained_path = next((mb / "issues").glob("*-feat-chained-issue.html"))
    chained = chained_path.read_text(encoding="utf-8")
    assert f'<meta name="doc-refs" content="memory-bank/tasks/{task.name}">' in chained, "issue 正向 doc-refs"
    assert f"memory-bank/issues/{chained_path.name}" in task.read_text(encoding="utf-8"), "目标档案反向声明本 issue"

    # 5. 幂等拒绝 (冻结时钟下撞同名 —— 同分钟同 slug 同 type)
    rc, _, err = run("issue", "smoke-issue", "--type", "docs", "--title", "t", "--summary", "s")
    assert rc == 1 and "已存在" in err, f"同名重复建必须幂等拒绝: {err}"

    # 6. kb.new issue → kb.status 全链 (评审 RB2 1a): 对真建出的 issue 翻 In Progress,
    #    badge / meta / 状态变更日志行 / 索引分区四处断言 —— 防「建件成功但 kb.status 对
    #    新建件 rc=1」的机读锚漂移只靠注册表模板断言兜底
    flip = _flip_status()
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = flip.main(
            ["--root", str(tmp_path), "--mb-dir",
             str(mb), f"memory-bank/issues/{issue.name}", "In Progress"]
        )
    assert rc == 0, f"kb.status 必须能翻 kb.new issue 建出的件: {err.getvalue()}"
    text = issue.read_text(encoding="utf-8")
    assert '<span class="badge">In Progress</span>' in text, "状态徽标应改"
    assert '<meta name="issue-status" content="In Progress">' in text, "issue-status meta 应改"
    assert f"<li>{frozen.strftime('%Y-%m-%d')} — 状态 Open → In Progress（kb.status）</li>" in text, \
        "状态变更日志应追加一行"
    # (2026-11-08 重构 W3: 原索引分区断言已删 —— issues/_index.md 退役, 翻转不再重建。)


def test_new_doc_issue_params_fail_fast(tmp_path: Path) -> None:
    """issue 族参数 fail-fast (黄金法则: 之后假定输入合法): 枚举外 --type / 缺 --type /
    缺 --summary / 缺 slug / 坏 slug / 坏 --topic / 位置 + --topic 异值全拒。
    (传参统一 issue 26-11-08-1131: 非 issue 族位置参数已放行, 原「不接受位置参数」拒收改为
    异值歧义拒 —— 见 test_new_doc_key_arg_unified_positional。)
    另钉 W3 行为差: 不提供 --status (出厂恒 Open, 翻状态 W4 起走 kb.status) —— argparse 拒未知参数。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def run(*extra: str) -> tuple[int, str]:
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = new_doc.main(["--root", str(tmp_path), "--mb-dir", str(mb), *extra])
        return rc, err.getvalue()

    rc, err = run("issue", "some-slug", "--type", "nope", "--title", "t", "--summary", "s")
    assert rc == 1 and "8 类" in err, f"枚举外 --type 必须 fail-fast: {err}"
    rc, err = run("issue", "some-slug", "--title", "t", "--summary", "s")
    assert rc == 1 and "--type" in err, f"缺 --type 必须拒: {err}"
    rc, err = run("issue", "some-slug", "--type", "docs", "--title", "t")
    assert rc == 1 and "--summary" in err, f"缺 --summary 必须拒 (进索引行): {err}"
    rc, err = run("issue", "--type", "docs", "--title", "t", "--summary", "s")
    assert rc == 1 and "slug" in err, f"缺 slug 位置参数必须拒: {err}"
    rc, err = run("issue", "Bad_Slug", "--type", "docs", "--title", "t", "--summary", "s")
    assert rc == 1 and "不合规" in err, f"坏 slug 必须拒: {err}"
    rc, err = run("issue", "some-slug", "--type", "docs", "--title", "t", "--summary", "s", "--topic", "Bad_Topic")
    assert rc == 1 and "kebab" in err, f"坏 --topic 必须拒: {err}"
    rc, err = run("plan", "positional-slug", "--title", "t", "--topic", "ok-topic")
    assert rc == 1 and "歧义" in err, f"非 issue 族位置 + --topic 异值必须拒 (主键不可歧义): {err}"

    import pytest

    # --status 不是 kb.new issue 的参数 (W3 行为差: 出厂恒 Open, 翻状态 W4 起走 kb.status) ——
    # argparse 对未知参数 SystemExit
    with pytest.raises(SystemExit):
        new_doc.main(
            [
                "--root",
                str(tmp_path), "--mb-dir",
                str(mb), "issue", "some-slug", "--type", "docs", "--title", "t", "--summary", "s", "--status", "Done"
            ]
        )


def test_new_doc_key_arg_unified_positional(tmp_path: Path, monkeypatch) -> None:
    """传参统一 (issue 26-11-08-1131): 主键**位置参数与 --topic 两形态全族等价**, 跨族套形态
    不再 rc=1 —— 非 issue 族位置单传可建 (实踩面: kb.new baseline <slug>); 同给同值幂等放行;
    异值拒 (fail-fast: 主键不可歧义); issue 缺位置 --topic 兼作 slug, 位置给足时 --topic 仍是
    doc-topic 覆盖 (W3 既有行为不变)。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    new_doc = _new_doc()
    import timekit  # 必须在 helper 之后 —— helper 负责把 SKILL_SCRIPTS 插进 sys.path
    frozen = timekit.now()
    monkeypatch.setattr(timekit, "now", lambda: frozen)
    mb = tmp_path / "memory-bank"
    mb.mkdir()

    def run(*extra: str) -> tuple[int, str]:
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = new_doc.main(["--root", str(tmp_path), "--mb-dir", str(mb), *extra])
        return rc, err.getvalue()

    # 非 issue 族位置单传 (原「不接受位置参数」拒收面翻正; baseline 是 2026-11-08 实踩形态)
    rc, err = run("plan", "uni-pos-plan", "--title", "t")
    assert rc == 0, f"plan 位置单传必须可建: {err}"
    plan_html = next((mb / "plans").glob("*plan-uni-pos-plan.html"))
    assert '<meta name="doc-topic" content="uni-pos-plan">' in plan_html.read_text(encoding="utf-8")

    rc, err = run("baseline", "uni-pos-base", "--title", "t", "--total", "1 passed")
    assert rc == 0, f"baseline 位置单传必须可建 (issue 实踩形态): {err}"
    assert list((mb / "testing" / "baselines").glob("*uni-pos-base.md"))

    # 同给同值: 两形态等价, 幂等放行
    rc, err = run("report", "uni-same-key", "--title", "t", "--topic", "uni-same-key")
    assert rc == 0, f"同值位置 + --topic 必须幂等放行: {err}"

    # 同给异值: 主键不可歧义, fail-fast
    rc, err = run("plan", "uni-a", "--title", "t", "--topic", "uni-b")
    assert rc == 1 and "歧义" in err, f"异值位置 + --topic 必须拒: {err}"

    # issue 缺位置: --topic 兼作 slug (文件名第三段 = doc-topic = 同值, 与默认主键口径一致)
    rc, err = run("issue", "--topic", "uni-topic-slug", "--type", "docs", "--title", "t", "--summary", "s")
    assert rc == 0, f"issue 仅 --topic (兼作 slug) 必须可建: {err}"
    issue_html = next((mb / "issues").glob("*docs-uni-topic-slug.html"))
    assert '<meta name="doc-topic" content="uni-topic-slug">' in issue_html.read_text(encoding="utf-8")

    # issue 位置给足: --topic 仍是 doc-topic 覆盖 (W3 既有行为, 不被统一改写)
    rc, err = run(
        "issue", "uni-pos-slug", "--topic", "uni-override", "--type", "docs", "--title", "t", "--summary", "s"
    )
    assert rc == 0, f"issue 位置 slug + --topic 覆盖 (既有形态) 必须保留: {err}"
    text = next((mb / "issues").glob("*docs-uni-pos-slug.html")).read_text(encoding="utf-8")
    assert '<meta name="doc-topic" content="uni-override">' in text


def test_checker_scan_face_excludes_issues(tmp_path: Path) -> None:
    """D6 拍板 (计划 26-11-07-0549): issue 入 FAMILIES **不得扩大** check_doc_templates 的
    冻结线扫描面 —— 它按族目录枚举扫描, issues/ 不在面内 (issue 自己的护栏是
    建件端 FAMILIES 的命名/词表单点已 fail-fast, 不重复建一套)。

    钉法: 线后 (stamp > FREEZE_LINE) 且遍体缺陷的 issue 件必须被零触碰 (不计数不报红);
    同目录放一件缺陷 plan 证明扫描面本身没坏 (计 1 件、判红)。"""
    checker = _doc_templates()
    mb = tmp_path / "memory-bank"
    (mb / "issues").mkdir(parents=True)
    (mb / "plans").mkdir()

    broken_issue = mb / "issues" / "26-11-07-0549-bug-pin.html"
    broken_issue.write_text("<html><body>遍体缺陷: 无任何 meta</body></html>\n", encoding="utf-8")
    broken_plan = mb / "plans" / "26-11-07-0549-plan-pin.html"
    broken_plan.write_text(
        '<html><head><meta name="doc-type" content="plan"></head><body>x</body></html>\n', encoding="utf-8"
    )

    problems, checked = checker.check_new_faces(tmp_path, mb)
    assert checked == 1, f"扫描面只应计 plan 一件 (issues/ 不进冻结线扫描面, D6): {checked}"
    assert any("plan-pin" in p for p in problems), f"缺陷 plan 必须判红 (扫描面本身没坏): {problems}"
    assert not any("issue" in p for p in problems), f"issue 件不得入扫描面 (零触碰): {problems}"


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


def test_wrap_reports_status_drift_lists(tmp_path: Path) -> None:
    """kb.wrap 尾部状态漂移扫描: D 清单默认只打计数 (--verbose 展开详情,
    wrap 自身不带 verbose flag), 空打「无」, 硬拦档 (B/异常) 非空附
    「状态漂移硬拦非空…」提示行 —— 清单只提示, wrap 退出码与结果不因此改变。
    (2026-11-08 重构 W5: 原 C 反链档随 progress/ 退役删除, 夹具不再造 progress/。)"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    wrap = _wrap()
    _status_drift()  # 确保 wrap 同进程 import 的模块可加载 (与 test_kb_scripts_import_cleanly 同面)

    def wrap_run(base: Path, mb: Path, topic: str, did: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = wrap.main(["--root", str(base), "--mb-dir", str(mb), "--topic", topic, "--did", did])
        return rc, out.getvalue()

    # --- 无漂移: D 档打一行「无」, 无硬拦提示, wrap 照常成功
    mb0 = _drift_fixture(tmp_path / "clean")
    rc, out = wrap_run(tmp_path / "clean", mb0, "drift-clean", "无漂移收尾")
    assert rc == 0
    assert "状态漂移扫描 (check_status_drift; 只提示, 不拦截):" in out
    assert "[D 清单: 完成断言] 无" in out
    assert "C 清单" not in out, "C 反链档已随 progress/ 退役, 不应再出现"
    assert "状态漂移硬拦非空" not in out

    # --- D 漂移: wrap 输出 summary 行 (不展开条目正文), wrap 仍成功且无硬拦提示
    mb1 = _drift_fixture(tmp_path / "soft")
    _drift_task(mb1, "inflight.md", "In Progress")
    _drift_task(mb1, "open-word.md", "Open", body="- 已完成 首版\n")
    rc, out = wrap_run(tmp_path / "soft", mb1, "drift-soft", "软漂移收尾")
    assert rc == 0
    assert "[D 清单: 完成断言] 1 条" in out
    # wrap 输出不应展开具体条目正文
    assert "open-word.md" not in out, "wrap D 档段不应出现文件名"
    assert "[done-assert]" not in out, "wrap 不应展开 D 档条目"
    assert "状态漂移硬拦非空" not in out

    # --- 硬拦漂移 (B 档: badge vs meta 矛盾): 附提示行, 但 wrap 退出码与机械面 (建切片) 不受影响
    mb2 = _drift_fixture(tmp_path / "hard")
    _drift_issue(mb2, "contradict.html", "Open", badge="Done")
    rc, out = wrap_run(tmp_path / "hard", mb2, "drift-hard", "硬漂移收尾")
    assert rc == 0, "清单与提示只提示不失败"
    assert "状态漂移硬拦非空, 先 commands run kb.status 处理(部分完成翻 In Progress)再收尾" in out
    assert "[D 清单: 完成断言] 无" in out
    assert len(list((mb2 / "active-context").glob("*-drift-hard.md"))) == 1, "机械面照常完成"
