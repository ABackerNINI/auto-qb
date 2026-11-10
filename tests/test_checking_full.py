"""test_checking_full 测试计划: checking 动作详细自测(不连接真实 qB, 用模拟对象)

## 测试计划(每个测试函数一条)
- test_checking_no_reference_full_checking: 无参考 -> 全量校验流程
- test_checking_recheck_fail_cooldown: 校验连续失败达上限 -> 当日不再重试(防 recheck 死循环)
- test_checking_full_checking_pending: 全检任务 pending 保留
- test_checking_full_checking_dup_ignore: 全检重复提交忽略
- test_checking_full_checking_auto_start_false: auto_start=false 不自动开始
- test_checking_full_checking_send_error: 发送失败处理
- test_checking_full_checking_pending_resume: 任务队列驱动: 提交后 pending(断点, 不重入队) -> 校验成功 -> 子任务重新入队 origin 续跑(记录执行历史)
- test_checking_full_checking_resume_continues_actions: 断点续跑: 校验成功后执行断点后的剩余动作
- test_checking_full_checking_fail_retry: 任务队列驱动: 见过 checking 后落回未完成才判败 -> 子任务 reset+重新入队 origin 重试
- test_checking_full_checking_first_sample_race_not_failed: 首样本竞态回归(2026-09-25 故障): 快照未见 checking 不计败, 走到成功零失败记录
- test_checking_full_checking_giveup_condemns: 启动宽限耗尽(CHECK_START_GIVEUP)仍未见 checking -> 判败走冷却(防活锁保险丝)
- test_checking_group_full_checking_serialized: 组内校验串行(决策链 1.5): B 让位等待, A 成功晋升参考后 B 重走决策链走跳检
- test_recheck_fail_flushed_immediately: recheck 失败冷却计数即时落盘(防死循环闸门不因崩溃失效)
- test_bump_recheck_fail_resets_count_across_day: C28 守阵 —— 跨自然日重置写 count 键(键名漂移
  -> 昨日计数不清零)
- test_self_recheck_failed_today_predicate: G9 谓词单点(26-10-05-0402) self_recheck_failed_today:
  当日计数 0/无记录/跨日 -> False, >=1 -> True; hash-keyed 只读自身(他人记录不放大)
- test_checking_fail_cooldown_gate_skips_within_window: 校验失败冷却窗口(26-11-08-1717, 决策链
  0.5): 窗口内直接 skip 不再提交 recheck, 且不消耗 recheck_fails 额度(两机制分工)
- test_checking_fail_cooldown_expired_allows_recheck: 冷却记录过期后决策链放行(时间戳自愈,
  种子删除后的残留记录同样自愈)
- test_checking_fail_cooldown_recorded_on_fail_flushed: rule 源 FAILED 判定写入冷却记录并即时
  落盘(窗口闸门不因崩溃失效)
- test_checking_fail_cooldown_key_absent_uses_default: spec 未配 recheck_fail_cooldown -> 运行时
  取 1h 缺省档(缺省档唯一来源 checking_meta)
- test_checking_fail_cooldown_window_from_spec: 闸门窗口按动作 spec 取值(fail_cooldown="30M"):
  窗口内(20min)拦截 / 过窗(40min)放行(40min 在缺省 1h 档仍会拦, 恰好区分窗口来源)
"""

import json

import os

import tempfile

import time

import uuid

from datetime import date

from types import SimpleNamespace

from unittest.mock import patch

from auto_qb.config import Config

from auto_qb.rules.actions import RECHECK_FAIL_LIMIT, CheckAction

from auto_qb.rules.actions.full_checking import bump_recheck_fail, recheck_fail_count

from auto_qb.rules.base import VERDICT_EXECUTED, VERDICT_PENDING

from auto_qb.rules.checking_meta import RECHECK_COOLDOWN_DEFAULT, PieceCheckingStates, PollVerdict, is_piece_checking, poll_verdict, self_recheck_failed_today

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, TaskQueue

from helpers import drive_skip, FakeClient, FakeConfig, FakeTorrent, make_ctx, make_manager, seed_store

from checking_support import (
    CheckingFakeClient,
    _TMP_STATE_DIR,
    inject_group,
    make_check_cfg,
    make_mgr,
    make_target,
    process_rule,
    run_queue,
)


def test_checking_no_reference_full_checking():
    """测试: 无参考 -> without_reference full-checking 完整流程(提交即发送->轮询续延->完成->start+记录+晋升) """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "应提交校验"
    assert ("recheck", None) in client.calls, f"提交时即应同步发送 recheck: {client.calls}"

    # 重复提交同一种子: 忽略(不再发送)
    client.calls.clear()
    process_rule(mgr, client, t, dry_run=False)
    assert ("recheck", None) not in client.calls, f"重复校验应被忽略: {client.calls}"

    # 模拟客户端进入校验状态 -> 续延(任务保留)
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    assert ("start", None) not in client.calls, "校验中不应完成"
    assert len(mgr.task_queue._fast) == 1, "校验中任务应续延保留"

    # 模拟校验完成(退出 checking 状态) -> 自动开始 + 记录 + 晋升
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert ("start", None) in client.calls, f"校验完成应自动开始: {client.calls}"
    assert mgr.state.get("exec_history"), "校验完成应记录执行历史"
    assert mgr.store.verified_references == {"HASH123"}, "校验通过应晋升为参考"
    assert mgr.task_queue._fast == [], "完成后任务应消亡"


def test_checking_recheck_fail_cooldown():
    """任务队列驱动: 校验连续失败达上限 -> 冷却当日不再重试(防损坏文件的 recheck 死循环), 次日重置

    用 CHECK_START_GIVEUP=0 跳过「已见 checking」判定前提: 本测试钉的是冷却闸门算术,
    不是判定前提本身(前提语义见 test_checking_full_checking_fail_retry / giveup 用例)。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    # progress 恒 0.5(<1): 每轮轮询都判失败(概括损坏文件); stoppedDL 满足闸门 0
    t = make_target(state="stoppedDL", progress=0.5)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # P1 提交点实时复核读客户端: 三次提交的 live 放行都靠它(非 checking 态)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)

    # 本用例钉 recheck_fails 当日预算闸门(ops 提交点), 与失败冷却窗口(决策链 0.5)正交:
    # 队列时间(+61s/+121.5s)是模拟推进而冷却记录走挂钟, 窗口闸门会误拦模拟时间线上的重试
    # —— 打桩掉窗口记录写点, 隔离出预算语义本身(窗口语义见 test_checking_fail_cooldown_*)
    with patch("auto_qb.core.modules.ops_mod.CHECK_START_GIVEUP", 0.0), \
            patch("auto_qb.core.modules.ops_mod.record_recheck_cooldown"):
        # 第 1 次执行: 提交 recheck -> 让位; 轮询(+0.5)判失败(count=1) -> origin 重入队
        run_queue(mgr, t0)
        run_queue(mgr, t0 + 0.5)
        assert client.calls.count(("recheck", None)) == 1
        assert mgr.state["recheck_fails"]["HASH123"]["count"] == 1

        # 第 2 次: gate(1<3) -> 再提交; 轮询失败 count=2
        run_queue(mgr, t0 + 61.0)
        run_queue(mgr, t0 + 61.5)
        assert client.calls.count(("recheck", None)) == 2
        assert mgr.state["recheck_fails"]["HASH123"]["count"] == 2

        # 第 3 次: gate(2<3) -> 再提交; 轮询失败 count=3
        run_queue(mgr, t0 + 121.5)
        run_queue(mgr, t0 + 122.0)
        assert client.calls.count(("recheck", None)) == 3
        assert mgr.state["recheck_fails"]["HASH123"]["count"] == 3

        # 第 4 次执行: 冷却生效 -> skip, 不再提交(失败计数保留, 次日重置)
        run_queue(mgr, t0 + 182.0)
    assert client.calls.count(("recheck", None)) == 3, "冷却期内不应再提交"
    assert recheck_fail_count(mgr.ctx.state, "HASH123") == 3


def test_checking_full_checking_pending():
    """测试: 校验未完成 -> 轮询任务续延保留(不丢失) """
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    process_rule(mgr, client, t, dry_run=False)
    assert ("recheck", None) in client.calls, f"提交时即应发送 recheck: {client.calls}"
    # 模拟校验中 -> 任务续延保留
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    assert len(mgr.task_queue._fast) == 1, "任务应保留(续延)"


def test_checking_full_checking_dup_ignore():
    """测试: 同一种子重复提交校验 -> 忽略(仅一次 recheck) """
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    process_rule(mgr, client, t, dry_run=False)
    process_rule(mgr, client, t, dry_run=False)  # 重复 -> 忽略
    n_recheck = sum(1 for c in client.calls if c[0] == "recheck")
    assert n_recheck == 1, f"recheck 应只发送一次: {client.calls}"


def test_checking_full_checking_auto_start_false():
    """测试: auto_start=false -> 校验完成不自动开始, 仍记录执行 + 晋升参考 """
    cfg = make_check_cfg(without_mode="full-checking", without_start=False)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    process_rule(mgr, client, t, dry_run=False)  # 提交即发送
    seed_store(mgr, [make_target(state="checkingDL")])  # 校验中
    run_queue(mgr, t0 + 0.5)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])  # 完成
    run_queue(mgr, t0 + 2.5)
    assert ("start", None) not in client.calls, f"auto_start=false 不应自动开始: {client.calls}"
    assert mgr.state.get("exec_history"), "仍应记录执行历史"
    assert mgr.store.verified_references == {"HASH123"}, "仍应晋升参考"


def test_checking_full_checking_send_error():
    """测试: 校验请求发送失败 -> 动作失败(不晋升/不开始), 轮询任务自然消亡 """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.recheck_error = RuntimeError("simulated recheck failure")
    t = make_target()
    client.torrents["HASH123"] = t  # P1 提交点实时复核读客户端: 复核须放行才能测到发送失败
    t0 = time.time()
    with patch("auto_qb.rules.base.logger.error") as mw:
        handled = process_rule(mgr, client, t, dry_run=False)
        assert handled, "发送失败应返回失败结果(动作已执行)"
        assert any("发送 recheck 失败" in str(c) for c in mw.call_args_list), \
            f"应有失败警告: {mw.call_args_list}"
        run_queue(mgr, t0 + 0.5)  # 轮询任务: 种子无快照 -> 消亡
    assert ("start", None) not in client.calls, "发送失败不应自动开始"
    assert ("recheck", None) not in client.calls, f"发送失败不应产生 recheck 调用: {client.calls}"
    assert mgr.store.verified_references == set(), "发送失败不应晋升参考"
    assert mgr.task_queue._fast == [], "发送失败任务应消亡"
    assert mgr.task_queue.active_check_hashes() == set(), "消亡应释放校验标记"


def test_checking_full_checking_pending_resume():
    """任务队列驱动: 提交后 pending(断点, 不重入队) -> 校验成功 -> 子任务重新入队 origin 续跑(记录执行历史) """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    # 首次执行: checking 提交 -> pending 中断 + 记录断点 + 不重入队(由轮询子任务负责恢复)
    run_queue(mgr, t0)
    assert origin.resume_index == 1, "应记录断点(下一个动作索引)"
    assert origin not in mgr.task_queue._fast, "pending 后规则任务不重入队"
    assert ("recheck", None) in client.calls, "提交时即应同步发送 recheck"
    # 校验中 -> 轮询续延, 规则任务保持不在队列, 断点保留
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    assert origin.resume_index == 1, "校验中断点保留"
    assert client.calls.count(("recheck", None)) == 1, "校验中不重复提交"
    # 校验完成(progress=1.0) -> 子任务 on_success + 重新入队 origin(断点保留)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING, "成功后应由子任务重新入队"
    assert mgr.store.verified_references == {"HASH123"}, "成功应晋升参考"
    assert origin.resume_index == 1, "重新入队应保留断点(续跑语义)"
    assert not mgr.state.get("exec_history"), "执行历史应由续跑完成时记录"
    # 续跑: origin 到期 -> 跳过条件/去重 -> 从断点继续(单动作规则: 空循环) -> 记录执行
    run_queue(mgr, t0 + 60.5)
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"
    assert origin.resume_index is None, "断点应已消费清零"


def test_checking_full_checking_resume_continues_actions():
    """断点续跑: 规则 [checking, start] 校验成功 -> resume 后续跑执行剩余动作 start """
    cfg = make_check_cfg(without_mode="full-checking", without_start=False, extra_actions=[{"start": True}])
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.resume_index == 1 and origin not in mgr.task_queue._fast, "checking pending 应中断并记录断点(不重入队)"
    assert ("recheck", None) in client.calls, "应发送 recheck"
    assert ("start", None) not in client.calls, "pending 中断, 后续动作未执行"
    # 校验完成 -> resume
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING and origin.resume_index == 1
    assert mgr.store.verified_references == {"HASH123"}
    assert not mgr.state.get("exec_history"), "续跑完成前不记录执行历史"
    # 续跑: 执行断点后的 start(最新快照 pausedUP -> 暂停 -> 执行 start)
    run_queue(mgr, t0 + 60.5)
    assert ("start", None) in client.calls, f"续跑应执行后续动作 start: {client.calls}"
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"
    assert origin.resume_index is None, "断点应已消费清零"


def test_checking_full_checking_fail_retry():
    """任务队列驱动: 见过 checking 后落回未完成 -> 判败 -> 子任务 origin.reset() + 重新入队(重走决策链)

    失败判定前提(首样本竞态修复): 未曾观察到 checking 态不算失败(宽限窗口内继续轮询),
    快照见 checking 后再落回未完成才定罪 —— 真实校验失败必然经过 checking 态。

    失败冷却窗口(决策链 0.5)与本用例的重试时间线正交(队列时间模拟推进而冷却记录走挂钟),
    打桩掉窗口记录写点隔离出「判败 -> 重入队 -> 重试」语义本身(见 recheck_fail_cooldown 系用例)。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # P1 提交点实时复核读客户端: 两次提交(初提交 + 重走决策链)的 live 放行都靠它
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    with patch("auto_qb.core.modules.ops_mod.record_recheck_cooldown"):
        run_queue(mgr, t0)
        assert origin.resume_index == 1 and origin not in mgr.task_queue._fast, "首次执行应记录断点且不重入队"
        # 首样本: 快照仍是提交前状态(非 checking, progress=0.0) -> 宽限窗口内继续轮询, 不计败
        seed_store(mgr, [make_target()])
        run_queue(mgr, t0 + 2.5)
        assert mgr.state.get("recheck_fails", {}).get("HASH123") is None, "未见 checking 不得计败"
        assert any(p.kind == "check" for p in mgr.task_queue._fast), "轮询任务应 REQUEUE 存活"
        # 快照见 checking(校验已启动) -> 继续轮询
        seed_store(mgr, [make_target(state="checkingDL")])
        run_queue(mgr, t0 + 5.0)
        # 校验跑完仍未完成(真实失败) -> 定罪: 计败 + origin reset 重入队
        seed_store(mgr, [make_target(state="pausedDL", progress=0.5)])
        run_queue(mgr, t0 + 7.5)
        assert mgr.state["recheck_fails"]["HASH123"]["count"] == 1, "见过 checking 后的未完成才计败"
        assert origin.state == PENDING, "失败后应由子任务重新入队重试"
        assert origin.resume_index is None, "失败应重置断点(重走完整决策链)"
        assert mgr.store.verified_references == set(), "失败不应晋升参考"
        assert not mgr.state.get("exec_history"), "失败不应记录执行历史"
        # 重走决策链: origin 到期 -> 重新 full-checking(再次 pending + 再发 recheck)
        run_queue(mgr, t0 + 60.5)
        assert origin.resume_index == 1 and origin not in mgr.task_queue._fast, "重走决策链应再次校验(再次记录断点)"


def test_checking_full_checking_first_sample_race_not_failed():
    """首样本竞态回归(2026-09-25 故障): recheck 已提交但快照未见 checking(progress=0.0)

    旧行为: WARNING「校验未通过(第1次, progress=0.0)」+ recheck_fails 当日落盘, 经决策链
    1.6 毒化同组(文件映射一致的成员全部被拒检)。新行为: 宽限窗口内继续轮询, 快照见
    checking 后正常走完 -> 校验成功, 全程零失败记录。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)  # 提交 recheck + 登记轮询
    # 故障时序还原: 提交后 ~2s 首样本, 快照仍是提交前状态(非 checking, progress=0.0)
    seed_store(mgr, [make_target()])
    run_queue(mgr, t0 + 2.5)
    assert mgr.state.get("recheck_fails", {}).get("HASH123") is None, "首样本竞态不得计败"
    assert any(p.kind == "check" for p in mgr.task_queue._fast), "轮询应继续而不是消亡"
    # qB 应用 recheck: 快照见 checking -> 校验完成 -> 成功路径
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 5.0)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 7.5)
    assert "HASH123" in mgr.store.verified_references, "校验成功应晋升参考"
    assert mgr.state.get("recheck_fails", {}).get("HASH123") is None, "成功路径无失败记录"
    assert origin.state == PENDING and origin.resume_index == 1, "成功应保留断点等续跑"
    run_queue(mgr, t0 + 60.5)
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"


def test_checking_full_checking_giveup_condemns():
    """启动宽限保险丝: CHECK_START_GIVEUP 耗尽仍未见 checking -> 判败走冷却(防轮询活锁)

    qB 重启丢请求等极端情形下 recheck 永不生效, 无保险丝则轮询无限等待。判败后 origin
    重走决策链重新提交, 请求恢复生效后自然续上。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    with patch("auto_qb.core.modules.ops_mod.CHECK_START_GIVEUP", 0.0):
        seed_store(mgr, [make_target()])  # 快照恒为提交前状态: 永未见 checking
        run_queue(mgr, t0 + 2.5)
    assert mgr.state["recheck_fails"]["HASH123"]["count"] == 1, "宽限耗尽应判败"
    assert origin.state == PENDING and origin.resume_index is None, "判败应重置 origin 重走决策链"
    assert not any(p.kind == "check" for p in mgr.task_queue._fast), "轮询任务应消亡"


# ============================================================
# G. 组内校验串行化(决策链 1.5/1.6)
# ============================================================
def test_checking_group_full_checking_serialized():
    """同组 full-checking 串行: A 提交后 B 让位等待(不提交 recheck); A 成功晋升参考 -> B 恢复走 with_reference 跳检"""
    # state_file 必须给真实路径: 留空会让 atomic_write 往 CWD 的父目录写临时文件
    with tempfile.TemporaryDirectory() as td:
        cfg = make_check_cfg(without_mode="full-checking", without_start=True)
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_mgr(cfg, with_tq=True)
        client = CheckingFakeClient()
        mgr.client = client
        a = make_target(hash="HA")
        b = make_target(hash="HB")
        seed_store(mgr, [a, b])
        client.torrents["HA"] = a  # P1 提交点实时复核读客户端: A 的 full-checking 提交也须 live 放行(非 checking 态)
        client.torrents["HB"] = b  # R2 实时复核读客户端(非快照): 跳检前种子必须在客户端
        inject_group(mgr, "HA", "HB")
        rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
        t0 = time.time()
        ta = mgr.host.get("rules")._create_rule_task(rule, "HA")
        tb = mgr.host.get("rules")._create_rule_task(rule, "HB")
        ta.interval = 60.0
        tb.interval = 60.0
        # A 先执行: 提交 recheck(在途登记) + 让位; HA 进入校验态后 B 再执行
        mgr.task_queue.add_task(ta, t0)
        run_queue(mgr, t0)
        seed_store(mgr, [make_target(hash="HA", state="checkingDL"), b])
        mgr.task_queue.add_task(tb, t0 + 0.1)
        run_queue(mgr, t0 + 0.1)
        assert ("recheck", None) in client.calls, "A 应提交 recheck"
        assert client.calls.count(("recheck", None)) == 1, f"B 不应提交 recheck: {client.calls}"
        assert mgr.task_queue.active_check_hashes() == {"HA"}, "A 应登记在途(等待任务不占用登记)"
        assert ta.resume_index == 1 and tb.resume_index == 1, "A/B 均应记录断点"
        assert ta not in mgr.task_queue._fast and tb not in mgr.task_queue._fast, "A/B 均不重入队(等待恢复)"
        # HA 校验中: A 轮询续延, B 等待任务续等(间距放大避开真实时钟重排的边界)
        run_queue(mgr, t0 + 10.0)
        assert tb.resume_index == 1, "HA 校验中 B 保持推迟"
        # HA 校验成功 -> 晋升参考; B 等待任务发现组内已清 -> resume B 重走决策链
        seed_store(mgr, [make_target(hash="HA", state="pausedUP", progress=1.0), b])
        run_queue(mgr, t0 + 20.0)
        assert mgr.store.verified_references == {"HA"}, "成功应晋升参考"
        assert mgr.task_queue.active_check_hashes() == set(), "轮询消亡应释放在途登记"
        # !S2(26-10-13-0540): HA 成功后的 auto_start 走 QbApi.torrents_start -> 登记 own_writes[HA]
        #   (自有写 deferral 判据)。生产里 HA 的新 state 于下一轮同步回流即逐出该登记; 本用例直写
        #   store.by_hash(seed_store)绕过了 _apply 的「应用+逐出」, 故在此显式模拟同步副作用 ——
        #   否则同组 B 的校验决策会被 deferral 让位(D-3 组级判据: 目标或其组任一成员 ∈ own_writes)。
        seed_store(mgr, [make_target(hash="HA", state="stalledUP", progress=1.0), b])
        mgr.store.own_writes.pop("HA", None)
        # B 的恢复重走发生在等待任务 resume 之后(下一批到期): 命中 verified 参考 -> with_reference 跳检
        run_queue(mgr, t0 + 90.0)
        assert mgr.task_queue.active_check_hashes() == set(), "等待任务不登记在途"
        run_queue(mgr, t0 + 150.0)
        names = [c[0] for c in client.calls]
        assert names.count("recheck") == 1, f"B 恢复后不应再提交 recheck: {client.calls}"
        assert "export" in names and "delete" in names, f"B 应走跳检流程: {client.calls}"
        add_call = [c for c in client.calls if c[0] == "add"][0]
        assert add_call[1]["is_skip_checking"] is True, "B 应以跳检方式重加"


def test_recheck_fail_flushed_immediately():
    """recheck 失败冷却计数即时落盘: bump 后磁盘上已有 recheck_fails

    计数只活在内存的话, 崩溃后对同一损坏文件会多试 recheck(当日上限的防死循环闸门失效
    一次)。直接驱动生产写点 bump_recheck_fail 断言盘上内容。
    """
    mgr = make_mgr(make_check_cfg())
    assert bump_recheck_fail(mgr.ctx.state, "HASH123") == 1
    with open(mgr.state_file, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk.get("recheck_fails", {}).get("HASH123", {}).get("count") == 1, "冷却计数必须已写上盘"


def test_bump_recheck_fail_resets_count_across_day():
    """C28 守阵: 跨自然日重置写的是 count 键(键名漂移 -> 昨日计数不清零, 当日首次即触上限)"""
    cfg = make_check_cfg()
    mgr = make_mgr(cfg)
    state = mgr.ctx.state
    state.data.setdefault("recheck_fails", {})["HX"] = {"date": "2000-01-01", "count": 3}
    assert bump_recheck_fail(state, "HX") == 1, "跨日必须从 1 重新计数"
    assert state.data["recheck_fails"]["HX"] == {"date": date.today().isoformat(), "count": 1}
    assert bump_recheck_fail(state, "HX") == 2, "同日继续累加"


def test_self_recheck_failed_today_predicate():
    """G9 谓词单点(26-10-05-0402): self_recheck_failed_today —— 当日计数 0/无记录/跨日 -> False,
    >=1 -> True; hash-keyed 只读自身(他人当日记录不放大到自身)

    接受面沿用 recheck_fails 现有口径(不发明更锐利谓词); 跨站不殃及的行为面在 ops 侧
    test_skip_gates_rejects_self_check_failed 钉死。
    """
    mgr = make_mgr(make_check_cfg())
    state = mgr.ctx.state
    assert self_recheck_failed_today(state, "HX") is False, "无记录 -> False"
    state.data.setdefault("recheck_fails", {})["HX"] = {"date": date.today().isoformat(), "count": 1}
    assert self_recheck_failed_today(state, "HX") is True, "当日计数 1 -> True"
    state.data["recheck_fails"]["HX"]["count"] = 3
    assert self_recheck_failed_today(state, "HX") is True, "当日计数 3 -> True"
    state.data["recheck_fails"]["HX"]["date"] = "2000-01-01"
    assert self_recheck_failed_today(state, "HX") is False, "跨日重置 -> False"
    state.data["recheck_fails"]["HY"] = {"date": date.today().isoformat(), "count": 2}
    assert self_recheck_failed_today(state, "HX") is False, "他人的当日记录不改变自身判定"
    assert self_recheck_failed_today(state, "HZ") is False, "无记录 hash 不受他人影响(hash-keyed)"


# ============================================================
# H. 校验失败冷却窗口(26-11-08-1717, 决策链 0.5)
# ============================================================
def test_checking_fail_cooldown_gate_skips_within_window():
    """校验失败冷却窗口: 窗口内决策链 0.5 直接 skip, 不再提交 recheck 且不消耗 recheck_fails 额度

    记录点在 ops 层轮询 FAILED 判定(rule 源); 本用例直接预置新鲜记录(挂钟 -30s, 窗口缺省
    1h)钉闸门 skip 语义与「两机制分工」(记录写入本身见 test_checking_fail_cooldown_recorded_on_fail_flushed
    与 test_ops_recheck)。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="stoppedDL", progress=0.5)  # 满足闸门 0(暂停中未完成)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    mgr.ctx.state.data.setdefault("recheck_cooldowns", {})["HASH123"] = time.time() - 30.0
    mgr.ctx.state.save()
    ctx = make_ctx(mgr, t, client, dry_run=False)
    ctx.rule_name = "example_rules.check_rule"
    action = CheckAction({"basic_check": "filelist", "without_reference": {"enabled": True, "mode": "full-checking"}})
    r = action.execute(ctx)
    assert r.is_skipped and "校验失败冷却" in r.message, f"窗口内应被冷却闸门拦截: {r}"
    assert ("recheck", None) not in client.calls, f"窗口内不得再提交 recheck: {client.calls}"
    assert mgr.state.get("recheck_fails", {}).get("HASH123") is None, "冷却闸门在前, 不消耗失败额度"


def test_checking_fail_cooldown_expired_allows_recheck():
    """窗口过期(时间戳自愈): 过期记录不再拦截, 决策链放行正常提交 recheck

    种子删除后的残留记录走同一条过期自愈路径(无主动清扫), 本用例一并钉住该语义。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="stoppedDL", progress=0.5)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    mgr.ctx.state.data.setdefault("recheck_cooldowns", {})["HASH123"] = time.time() - 7200.0  # 窗口(缺省 1h)已过期
    mgr.ctx.state.save()
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, f"窗口过期应放行: {client.calls}"
    assert ("recheck", None) in client.calls, f"窗口过期后应正常提交 recheck: {client.calls}"


def test_checking_fail_cooldown_recorded_on_fail_flushed():
    """rule 源 FAILED 判定写入冷却记录并即时落盘: 窗口闸门不因崩溃失效(对齐 recheck_fails 落盘纪律)"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="stoppedDL", progress=0.5)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    t0 = time.time()
    process_rule(mgr, client, t, dry_run=False)  # 提交 recheck + 登记轮询
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 2.5)  # 生效证据 -> REQUEUE
    seed_store(mgr, [make_target(state="pausedDL", progress=0.5)])
    run_queue(mgr, t0 + 5.0)  # 生效后未完成 -> FAILED
    rec = mgr.state.get("recheck_cooldowns", {}).get("HASH123")
    assert rec is not None, f"FAILED 判定应写入冷却记录: {mgr.state.get('recheck_cooldowns')}"
    assert t0 - 1.0 <= rec <= time.time() + 1.0, f"记录应为挂钟失败时刻: {rec}"
    assert mgr.state["recheck_fails"]["HASH123"]["count"] == 1, "失败冷却计数照常累加(两机制并存)"
    with open(mgr.state_file, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk.get("recheck_cooldowns", {}).get("HASH123") is not None, "冷却记录必须已写上盘"


def test_checking_fail_cooldown_key_absent_uses_default():
    """spec 未配 recheck_fail_cooldown -> 运行时取 1h 缺省档(缺省档唯一来源 checking_meta.RECHECK_COOLDOWN_DEFAULT)"""
    action = CheckAction({"basic_check": "filelist"})
    assert action.recheck_fail_cooldown == RECHECK_COOLDOWN_DEFAULT, "键缺省应取 1h 缺省档"
    action2 = CheckAction({"basic_check": "filelist", "recheck_fail_cooldown": "30M"})
    assert action2.recheck_fail_cooldown == 1800.0, "时间串应解析为秒"


def test_checking_fail_cooldown_window_from_spec():
    """闸门窗口按动作 spec 取值(fail_cooldown="30M"): 窗口内(20min)拦截 / 过窗(40min)放行

    make_check_cfg 的 fail_cooldown 参数消费面: 40min 记录在缺省 1h 档下仍会被拦截,
    过窗放行恰好区分窗口来源是 spec 配置值(1800s)而非缺省档 —— 钉 spec 键面到决策链
    0.5 的取值链路(时间串解析本身见 test_checking_fail_cooldown_key_absent_uses_default)。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True, fail_cooldown="30M")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="stoppedDL", progress=0.5)  # 满足闸门 0(暂停中未完成)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    # 窗口内(20 分钟前 < 30M): 决策链 0.5 拦截, 不提交 recheck
    mgr.ctx.state.data.setdefault("recheck_cooldowns", {})["HASH123"] = time.time() - 20 * 60.0
    mgr.ctx.state.save()
    process_rule(mgr, client, t, dry_run=False)
    assert ("recheck", None) not in client.calls, f"窗口内(20min < 30M)应被拦截: {client.calls}"
    # 过窗(40 分钟前 > 30M): 放行并提交 recheck(缺省 1h 档会仍拦截, 恰好区分窗口来源)
    mgr.ctx.state.data["recheck_cooldowns"]["HASH123"] = time.time() - 40 * 60.0
    mgr.ctx.state.save()
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, f"过窗应放行: {client.calls}"
    assert ("recheck", None) in client.calls, f"过窗(40min > 30M)应提交 recheck: {client.calls}"
