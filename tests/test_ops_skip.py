"""test_ops_skip 测试计划: test_ops: 危险操作独立操作层(OpsMixin)自测(plan 26-09-30-0109 §5.1, 不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_ops_skip_check_day_shared_across_sources: 跳检同日去重跨来源共享(web 先跳, 规则同日再跳被拒)
- test_ops_web_skip_check_no_highrisk_warning: web 源不产生「无参考跳检(高风险)」告警(规则侧语义不泄漏进 WEB)
- test_ops_skip_check_export_error_mentions_gone: 提交前不直查; 种子不在时失败在导出步, 文案点明「可能已不在客户端」, 零删除/重加 (S3 改口径)
- test_ops_skip_gates_prune_stale_skip_day: 跳检同日去重表跨日残留清理 (P2-a)

跳检闸门扩展(plan 26-10-05-0314 S1b-1: 三分流 detail 单点 + force + 预检):
- test_skip_gates_rejects_completed: T1 已完成(做种态 p=1)拒, 文案含「已完成」, 零副作用
- test_skip_gates_rejects_active: T2 活跃中拒, 文案含「活跃」与「暂停」出路, 零副作用
- test_skip_gates_predicate_edge_states: T2b 边缘态逐态钉死 = state_enum.is_stopped 现有语义(同 checking.py:88 谓词)
- test_skip_gates_allows_paused_incomplete: T3 暂停未完成放行(辅种主场景, 防过严回归)
- test_skip_gates_rejects_group_downloading: T4 组内有活跃下载成员拒, 文案含「组内/下载」
- test_skip_gates_allows_group_all_paused: T5 组内全暂停/未归组放行(放行面锁)
- test_skip_check_filelist_precondition_blocks: T7 文件缺失/路径不可判定拒(带 check_filelist 描述与 fs.path_map 出路), 未导出未删除
- test_skip_gates_rejects_group_checking_inflight: T16 组内其它成员校验在途(G7, case 2)两半各一例: 队列登记 / 快照 is_checking(用户手动 recheck, G5 队列视野外); 在途清空后放行; 零副作用 (S1b-2)
- test_skip_gates_rejects_group_check_failed: T17 组内成员校验失败推断(G8, case 1): 正样本文案带成员+出路; 负样本三例(映射不一致 / 记录指向已完成成员自愈不参与 / 非当日); 只读自愈不 pop; 零副作用 (S1b-2)
- test_skip_gates_g7_evidence_and_blocker_identity: S1(26-10-21-1857) —— G7 证据口径: checkingResumeData 不算在验 / 映射不一致成员不参与 / 命中时文案点名 blocker(hash8+名字+state)
- test_skip_gates_inflight_ttl_expires_leaked_registration: S1(26-10-21-1857) —— 在途登记超 TTL 视为泄漏: G5 放行并记 WARNING(登记只在轮询任务 FINISHED 时释放)
- test_skip_check_no_sleep_polling_and_keeps_record: S2(26-10-21-1857) —— 相位机成功路径零 sleep(原 500ms × 10 轮询) + 删除不摘记录 + 运行状态零写入(调用序 export→delete→add→add_tags)
- test_skip_submit_async_scheduler_and_failure_isolation: S3(26-10-21-1857) —— 异步入口只受理(pending) + 调度器 advance_due 并行推进 + 逐 hash 失败隔离 + 窗口抑制随终态撤销
- test_skip_window_suppression_ignores_sync_removal: S3(26-10-21-1857) —— 删除→重加窗口内 torrents_removed 不算删除(增量轮与全量轮都豁免), 窗口结束后恢复常态
- test_skip_recovery_reconciles_backup_ledger: S4(26-10-21-1857) —— 崩溃恢复对账: 备份账本三分流(已回→清账 / 不在且备份在→seed_mode 重加 / 备份丢失→ERROR), 每进程只跑一次
- test_skip_gates_detail_classification: T18 detail 三态归类 + 执行路径与 detail 首个未过闸门同源断言 + G7/G8 归类(G8 blocked 短路 filelist / G7 force 不短路)
- test_skip_check_force_semantics: T19 force 仅豁越 cls=force(G5/G7)并留 WARNING+INFO 审计; blocked(G3/G6/G8/filelist)一律硬拒; 签名缺省 False
- test_skip_check_deferred_on_own_write: 跳检让位(A 系 26-10-13-0540 S2 D-2) —— 目标或其组刚被自有停/起(快照未回流) -> 让位不决策, 零副作用
- test_skip_readd_carries_share_limits_mode: (qb-5-3, issue 26-10-31-0711-bug-skip-readd-share-limits-mode) 重加回传分享限制模式: 5.3 快照带 share_limits_mode -> camelCase kwarg 原样透传(防 MatchAny/MatchAll 被静默重置为 Default); 5.2 快照恒 None -> 传 None 库不发键(wire 不变)
- test_guard_skip_delete_scope_keep_record: 删除作用域单 hash + keep_record 防线 + web 无参考告警不泄漏(fn3, 含 has_reference=False 面)
- test_guard_skip_finish_start_scope: 自动开始作用域单 hash(fn18 高危 None=全库开始)
- test_guard_skip_readd_args_pin: 重加参数直传 pin(torrent_files/save_path/category/tags/contentLayout/stopped/seq/f_l/limits, ac 簇 + pr14)
- test_guard_skip_submit_defaults_conservative: 缺省参数保守默认(ss3 WEB 不自动开始/ss5 rule 不自动豁越 + origin 保存 ss14/ss22/sb42/sb49/jn11/jn20)
- test_guard_skip_begin_idempotent: 同 hash 在途幂等闸(sb8 失效=旧 job 被覆盖)

覆盖率第三轮 T1a(ops_skip 相位机推进/守卫余量, 26-11-04 快照缺口 18 单位):
- test_skip_gone_retry_delete_raise_and_attempts_exhausted: gone 相位确认种子仍在 -> 幂等重试删除抛错被吞(402-403), 退避次数耗尽终态失败 + 残留记录撤账
- test_skip_drive_settle_during_backoff_sleep_race: 退避 sleep 期间主循环微步并发推进把 job 推到终态 -> 驱动循环经 while 条件出口收束(189->200 分支弧, 非 break 出口)
- test_skip_step_after_settle_is_noop: 终态 job 再被步进(并发双驱动形态)为 no-op: 不重复结算/广播/回调(213->217 分支)
- test_skip_result_cache_trims_oldest: 终态结果缓存超 _SKIP_RESULT_KEEP 淘汰最旧条目(234-235); 兼验 web=None 时 settle 跳过进度广播(237->249 分支)
- test_skip_settle_notify_failure_isolated: 进度事件广播失败只记 WARNING, 不影响已落定终态(247-248)
- test_skip_settle_on_done_failure_isolated: 终态回调异常只记 ERROR, 终态结果照常落账可查(254-255)
- test_advance_due_budget_calls_truncates: advance_due 步数预算先到先止, 超预算 job 留待下轮(296-297)
- test_skip_appeared_confirm_error_retries: 确认重加直查异常走退避重试不终态(418-420, 直驱拨相位)
- test_skip_appeared_retry_add_raise_swallowed: 重加确认不到时的幂等重加抛错被吞(433-434), 次数耗尽终态失败并撤掉快照残留记录
"""

import copy

import inspect

import logging

import os

import tempfile

import time

import uuid

from contextlib import contextmanager

from datetime import date

from types import SimpleNamespace

from auto_qb.core.modules.ops_common import SKIP_PHASE_APPEARED
from auto_qb.core.modules.ops_mod import OpsModule

from auto_qb.core.taskqueue import REQUEUE, Task, TaskQueue

from auto_qb.rules.actions import RECHECK_FAIL_LIMIT

from auto_qb.rules.checking_meta import INFLIGHT_TTL, is_piece_checking

from auto_qb.rules.actions.full_checking import bump_recheck_fail

from helpers import FakeClient, FakeConfig, FakeTorrent, capture_logs, drive_skip, make_manager, seed_store

from ops_support import (
    _TMP_STATE_DIR,
    _wrap_client,
    capture_ops_logs,
    make_mgr,
    seed_inflight,
    seed_paused,
    wire_group,
)


# ============================================================
# B. ops_skip_check: 跨来源共享去重 + 告警按来源
# ============================================================
def test_ops_skip_check_day_shared_across_sources():
    """测试: 跳检同日去重跨来源共享 —— web 跳检成功后, 规则源同日再跳被拒(「今日已跳检过」自解释)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client, hash="HASH123")  # FakeClient 重加固定回 HASH123
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"web 跳检应完成: {r}"
    assert mgr.state["skip_check_day"]["HASH123"] == date.today().isoformat(), "web 跳检应记录同日去重"
    # 保真链(26-10-11-2045 修复验收): 跳检成功 ⇒ 种子已完成 ⇒ 同日重跳曾被 G3 遮蔽返 fail;
    # dedup 前移后应直接命中 dedup 闸门返 skip —— 全程不手动改 progress, 正是修复前的必红形态
    r2 = mgr.ctx.ops.skip_check("HASH123", source="rule")
    assert r2.is_skipped and "今日已跳检过" in r2.message, f"跨来源同日应去重: {r2}"


def test_ops_web_skip_check_no_highrisk_warning():
    """测试: web 源跳检不产生「无参考跳检(高风险)」告警 —— 规则侧语义不泄漏进 WEB(前端危险确认框已告知)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client, hash="HASH123")
    r = mgr.ctx.ops.skip_check("HASH123", source="web", has_reference=False)
    assert r.is_ok, f"web 跳检应完成: {r}"
    assert mgr.state["skip_check_day"].get("HASH123"), "跳检应完成并记录"


def test_ops_skip_check_export_error_mentions_gone():
    """测试(S3): 提交前不直查; 种子真不在时失败在导出步, 文案点明"可能已不在客户端", 零删除/重加"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")

    def boom(**kw):
        raise RuntimeError("api down")

    client.torrents_export = boom
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "可能已不在客户端" in r.message, f"导出失败应带定位提示: {r}"
    assert not any(c[0] in ("delete", "add") for c in client.calls), "导出失败后不得删除/重加"


def test_ops_skip_gates_prune_stale_skip_day():
    """测试: 跳检同日去重表的跨日残留在过闸时清掉(防表无限增长)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    mgr.state.setdefault("skip_check_day", {})["STALE"] = "2000-01-01"  # 跨日残留
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"跳检应完成: {r}"
    assert "STALE" not in mgr.state["skip_check_day"], "跨日残留应被清理"
    assert mgr.state["skip_check_day"]["HASH123"] == date.today().isoformat()


def test_skip_gates_rejects_completed():
    """测试(T1): 已完成种子(做种态 p=1)跳检被拒, 文案含「已完成」; 零副作用(无去重记录/无备份/无写 API)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="pausedUP", progress=1.0)  # 做种态 p=1 -> 落 G3
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "已完成" in r.message, f"已完成应被拒: {r}"
    assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"


def test_skip_gates_rejects_active():
    """测试(T2): 活跃中(下载中, 非 stopped 且 p<1)跳检被拒, 文案含「活跃」与「暂停」出路; 零副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stalledDL", progress=0.5)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "活跃" in r.message and "暂停" in r.message, f"活跃中应被拒且给出路: {r}"
    assert client.calls == [], f"拒绝零副作用: {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"


def test_skip_gates_predicate_edge_states():
    """测试(T2b, 口径锁): 边缘态逐态钉死 —— G3/G4 判定就是 state_enum.is_stopped and progress < 1.0
    (逐字同 checking.py:88), 不发明 WEB 特有口径: p=1 无论状态落 G3; p<1 非 stopped 落 G4;
    p<1 stopped 放行"""
    from qbittorrentapi import TorrentState

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ops = mgr.ctx.ops
    stopped_states = ["pausedDL", "stoppedDL", "pausedUP", "stoppedUP"]
    non_stopped_states = [
        "downloading",
        "metaDL",
        "forcedDL",
        "forcedMetaDL",
        "stalledDL",
        "queuedDL",
        "checkingDL",
        "checkingResumeData",
        "uploading",
        "forcedUP",
        "stalledUP",
        "queuedUP",
        "allocating",
        "moving",
        "error",
        "missingFiles",
        "unknown",
    ]
    # 钉死测试自己的状态清单与枚举语义一致(清单漂移即红, 防用例口径失真)
    for s in stopped_states:
        assert TorrentState(s).is_stopped, f"{s} 应 is_stopped"
    for s in non_stopped_states:
        assert not TorrentState(s).is_stopped, f"{s} 应非 is_stopped"

    def g6_may_cofire(state):  # store.group_has_downloading 对未归组种子判自身(S1a 语义, 下载中谓词)
        ts = TorrentState(state)
        return ts.is_downloading and not ts.is_stopped and not ts.is_checking

    for state in non_stopped_states:
        t = FakeTorrent(hash="HA", state=state, progress=0.0)
        seed_store(mgr, [t])
        vs = ops._skip_gates_detail("HA", t)
        expected = ["G4"] + (["G6"] if g6_may_cofire(state) else [])
        assert [v.gate for v in vs] == expected, f"{state} p=0 应落 G4(非 stopped): {vs}"
        assert all(v.cls == "blocked" for v in vs), f"G4/G6 是 case 1 硬闸: {vs}"
    for state in stopped_states:
        t = FakeTorrent(hash="HA", state=state, progress=0.0)
        seed_store(mgr, [t])
        assert ops._skip_gates_detail("HA", t) == [], f"{state} p=0 应放行(stopped 且 p<1): 同规则侧口径"
    for state in non_stopped_states + stopped_states:
        t = FakeTorrent(hash="HA", state=state, progress=1.0)
        seed_store(mgr, [t])
        vs = ops._skip_gates_detail("HA", t)
        # 已完成但仍在验(checkingDL/checkingUP)落 G5(force): 「已完成, 跳检无意义」在这时是错话,
        # 且 G3 是 blocked 无逃生, 会把「误发起的 recheck」堵死
        head = ["G5"] if is_piece_checking(state) else ["G3"]
        expected = head + (["G6"] if g6_may_cofire(state) else [])
        assert [v.gate for v in vs] == expected, f"{state} p=1 应落 {head[0]}: {vs}"


def test_skip_gates_allows_paused_incomplete():
    """测试(T3, 放行面锁): 暂停未完成(stoppedDL p=0)闸门全过且整条跳检成功 —— 辅种主场景防过严回归"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    assert mgr.ctx.ops._skip_gates_detail("HASH123", t) == [], "暂停未完成应过全部闸门(辅种主场景)"
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"暂停未完成应放行完成跳检: {r}"


def test_skip_check_no_sleep_polling_and_keeps_record():
    """测试(S2): 相位机成功路径不 sleep(原实现 500ms × 10 轮询, 单条 ~6s);
    且全程不动记录 —— 删除不摘记录(keep_record), 也不做 live 回写(运行状态等 qB 上报)"""
    from unittest.mock import patch

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t

    slept = []
    with patch("auto_qb.core.modules.ops_mod.time.sleep", side_effect=lambda s: slept.append(s)):
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"暂停未完成应完成跳检: {r}"
    assert slept == [], f"成功路径不应有任何 sleep(相位机每步一次调用): {slept}"
    # 记录对象原样保留(既没被 remove_torrent 摘除, 也没被 restore_torrent 重建)
    assert mgr.store.get("HASH123") is t, "跳检不得摘除/重建记录(keep_record)"
    assert t.progress == 0.0 and t.state == "stoppedDL", "运行状态不得被跳检路径写入(只等 qB 上报)"
    names = [c[0] for c in client.calls]
    assert names == ["export", "delete", "add", "add_tags"], f"相位序应为一轮一调用: {names}"


def test_skip_readd_carries_share_limits_mode():
    """测试(qb-5-3): 跳检重加回传分享限制模式 —— qB 5.3 给 torrent 新增 share_limits_mode
    (Default/MatchAny/MatchAll), 重加只回传白名单字段时新模式被静默重置为 Default。
    5.3 快照带该字段 -> camelCase kwarg 原样透传; 5.2 快照无该字段(恒 None) -> 传 None,
    库对 None 值键不发键(5.2 wire 不变)。issue 26-10-31-0711-bug-skip-readd-share-limits-mode。
    """
    # 5.3 形态: 快照捕获到非默认模式 -> 重加原样带回
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t53 = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0, share_limits_mode="MatchAny")
    seed_store(mgr, [t53])
    client.torrents["HASH123"] = t53
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"跳检应完成: {r}"
    add_call = next(c for c in client.calls if c[0] == "add")
    assert add_call[1]["shareLimitsMode"] == "MatchAny", \
        f"重加须回传原模式(防静默重置为 Default): {add_call[1]}"

    # 5.2 形态: 快照无该字段(缺省 None) -> 透传 None(库不发键, wire 不变)
    mgr2 = make_mgr(FakeConfig())
    client2 = FakeClient()
    mgr2.client = client2
    t52 = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr2, [t52])
    client2.torrents["HASH123"] = t52
    r2 = mgr2.ctx.ops.skip_check("HASH123", source="web")
    assert r2.is_ok, f"跳检应完成: {r2}"
    add_call2 = next(c for c in client2.calls if c[0] == "add")
    assert add_call2[1]["shareLimitsMode"] is None, \
        f"5.2 快照缺省应透传 None(库不发键): {add_call2[1]}"


def test_skip_submit_async_scheduler_and_failure_isolation():
    """测试(S3): 异步入口 —— skip_submit 只建 job 返回 pending; 调度器 advance_due 并行推进,
    单条失败不影响另一条(逐 hash 独立终态); 窗口抑制登记随终态撤销"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    a = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    # fake add 固定把 HASH123 登记回客户端 -> 这条重加确认不到, 用来验失败隔离
    b = FakeTorrent(hash="HBADD", state="stoppedDL", progress=0.0)
    seed_store(mgr, [a, b])
    client.torrents["HASH123"] = a
    client.torrents["HBADD"] = b
    ops = mgr.ctx.ops
    results = {}

    def on_done(job):
        results[job.hash] = job.result

    ra = ops.skip_submit("HASH123", source="web", on_done=on_done)
    rb = ops.skip_submit("HBADD", source="web", on_done=on_done)
    assert ra.is_pending and rb.is_pending, f"异步入口只受理不等待: {ra} / {rb}"
    assert ops.next_run_at() is not None, "在途 job 应暴露下一步到期时间(第三条时间线)"
    assert {"HASH123", "HBADD"} <= mgr.store.skipping_hashes, "建 job 时应登记窗口抑制"

    assert drive_skip(mgr), "调度推进应把在途 job 全部推到终态"
    assert ops.next_run_at() is None, "终态后不应再有在途 job"
    assert mgr.store.skipping_hashes == set(), "终态应撤销窗口抑制登记"
    assert results["HASH123"].is_ok, results.get("HASH123")
    assert results["HBADD"].is_failed, results.get("HBADD")
    assert mgr.state["skip_check_day"].get("HASH123"), "成功的那条应记同日去重"
    assert not mgr.state["skip_check_day"].get("HBADD"), "失败的那条不得记去重"


def test_skip_window_suppression_ignores_sync_removal():
    """测试(S3): 删除→重加窗口内 qB 上报 torrents_removed 不算删除 —— 记录保留、不进 last_removed
    (否则 grouping 会走「种子已删除」链路: 取消归组 / 缺文件扫描 / 删除事件); 窗口结束后恢复常态"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    assert mgr.ctx.ops.skip_submit("HASH123", source="web").is_pending

    _, removed = mgr.store._apply({}, ["HASH123"], full=False)
    assert "HASH123" not in removed and mgr.store.get("HASH123") is t, "增量轮: 窗口内不得摘记录/报删除"
    _, removed_full = mgr.store._apply({}, [], full=True)
    assert "HASH123" not in removed_full and mgr.store.get("HASH123") is t, "全量轮: 窗口内同样豁免"

    assert drive_skip(mgr), "调度推进应把 job 推到终态"
    _, removed_after = mgr.store._apply({}, ["HASH123"], full=False)
    assert "HASH123" in removed_after and mgr.store.get("HASH123") is None, "窗口结束后 removal 应照常生效"


def test_skip_recovery_reconciles_backup_ledger():
    """测试(S4): 崩溃恢复对账 —— 备份账本(删除前落盘)是唯一凭据: 种子不在客户端则用备份重加
    (seed_mode), 种子已回来则清掉残留备份; 每进程只跑一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_mgr(FakeConfig())
        client = FakeClient()
        mgr.client = client
        keep = FakeTorrent(hash="HKEEP", state="pausedUP", progress=1.0)
        seed_store(mgr, [keep])
        client.torrents["HKEEP"] = keep
        path = os.path.join(td, "HMISSING.torrent")
        with open(path, "wb") as f:
            f.write(b"dummy-torrent")
        backups = mgr.state.setdefault("skip_check_backup", {})
        backups["HPRESENT"] = {"path": os.path.join(td, "nope.torrent"), "save_path": "R:\\", "ts": 0}
        backups["HMISSING"] = {"path": path, "save_path": r"R:\Downloads", "category": "", "tags": "", "ts": 0}
        mgr.store.by_hash["HPRESENT"] = FakeTorrent(hash="HPRESENT", state="pausedUP", progress=1.0)

        mgr.ctx.ops.on_sync_line(True)

        assert "HPRESENT" not in mgr.state["skip_check_backup"], "已回客户端的种子应清账"
        assert "HMISSING" not in mgr.state["skip_check_backup"], "重加成功应清账"
        adds = [c for c in client.calls if c[0] == "add"]
        assert adds and adds[0][1]["is_skip_checking"] is True, f"应用备份重加(seed_mode): {client.calls}"

        mgr.ctx.ops.on_sync_line(True)  # 一次性: 再调不再动作
        assert len([c for c in client.calls if c[0] == "add"]) == 1, "对账每进程只跑一次"


def test_skip_gates_rejects_group_downloading():
    """测试(T4): 组内有活跃下载成员跳检被拒(共享物理文件被写, 跳检标全部块有效 = 脏数据), 文案含「组内/下载」"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="downloading", progress=0.3)
    seed_store(mgr, [ha, hb])
    client.torrents["HASH123"] = ha
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HASH123", "HB")
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "组内" in r.message and "下载" in r.message, f"组内有下载应被拒: {r}"
    assert client.calls == [], f"拒绝零副作用: {client.calls}"


def test_skip_gates_allows_group_all_paused():
    """测试(T5, 放行面锁): 组内全暂停/已完成放行; 未归组(单种子)放行"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="stoppedUP", progress=1.0)  # 组内做种态不是「下载中」
    hc = FakeTorrent(hash="HC", state="pausedDL", progress=0.0)  # 未归组
    seed_store(mgr, [ha, hb, hc])
    wire_group(mgr, "K", "HA", "HB")
    ops = mgr.ctx.ops
    assert ops._skip_gates_detail("HA", ha) == [], "组内全暂停/已完成应放行"
    assert ops._skip_gates_detail("HC", hc) == [], "未归组应放行"
    assert ops._skip_gates("HC", hc) is None, "执行路径全过应返回 None"


def test_skip_check_deferred_on_own_write():
    """守阵(A 系 S2 D-2): 目标或其组刚被自有停/起(快照未回流) -> 跳检让位, 不按陈旧快照出决策

    WEB 命令路径不经 task 线(D-1 覆盖不到), 靠此闸拦下; 零副作用(未导出未删除)。
    红验: 去掉 skip_check 入口的 own_write_pending 闸门 -> 走完四阶段, `client.calls == []` 断言红。
    """
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = seed_paused(mgr, client, "HA")
    hb = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr, [ha, hb])
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HA", "HB")

    # ① 目标自身刚被自有停/起
    mgr.store.note_own_write("HA")
    r = mgr.ctx.ops.skip_check("HA", source="web")
    assert r.is_skipped and "稍后" in r.message, f"自身命中应让位: {r}"
    assert client.calls == [], f"让位零副作用: {client.calls}"

    # ② 仅同组成员刚被自有停/起(组维度)
    mgr.store.own_writes.clear()
    mgr.store.note_own_write("HB")
    r2 = mgr.ctx.ops.skip_check("HA", source="web")
    assert r2.is_skipped and "稍后" in r2.message, f"同组成员命中应让位: {r2}"
    assert client.calls == [], f"让位零副作用: {client.calls}"

    # ③ 登记清除后不再让位(证明是 deferral 而非永久拒绝)
    mgr.store.own_writes.clear()
    r3 = mgr.ctx.ops.skip_check("HA", source="web")
    assert not (r3.is_skipped and "稍后" in r3.message), f"登记清除后不应再让位: {r3}"


def test_skip_check_filelist_precondition_blocks():
    """测试(T7): 前置文件检查并入执行链(R2 之后、导出之前) —— 文件缺失 is_failed 带 check_filelist
    描述且未导出未删除; 路径不可判定(映射 miss)保守 blocked 且文案自带「修 fs.path_map 配置」出路"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    client.files = [SimpleNamespace(name="missing.bin", size=123)]  # 磁盘上不存在 -> check_filelist 报缺失
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "前置文件检查未通过" in r.message and "文件缺失: missing.bin" in r.message, \
        f"文件缺失应带 check_filelist 描述拒绝: {r}"
    assert not any(c[0] in ("export", "delete", "add") for c in client.calls), \
        f"文件缺失零副作用(未导出未删除, R2 与文件检查都在不可逆步骤前): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"

    # 映射 miss(存在性不可判定): 保守 blocked, 出路文案指向 fs.path_map 配置
    from auto_qb.infra import file_access as fa_mod

    class _UndeterminedFA:
        def exists(self, path):
            return fa_mod.UNDETERMINED

    real_get = fa_mod.get_file_access
    fa_mod.get_file_access = lambda: _UndeterminedFA()  # ops_mod.file_access 是同一模块对象, 单点替换即生效
    try:
        r2 = mgr.ctx.ops.skip_check("HASH123", source="web")
    finally:
        fa_mod.get_file_access = real_get
    assert r2.is_failed and "路径不可判定" in r2.message and "修正 fs.path_map 配置" in r2.message, \
        f"映射 miss 应保守 blocked 且给出路: {r2}"


# ============================================================
# E2. 组内镜像闸门(plan 26-10-05-0314 S1b-2): G7 镜像决策链 1.5 others_checking /
#     G8 镜像决策链 1.6 四要件(假失败自愈只读变体) —— 谓词逐字同规则侧, 规则源零变化
# ============================================================
def test_skip_gates_rejects_group_checking_inflight():
    """测试(T16): 组内其它成员 full-checking 在途(G7, case 2)拒 —— 两半视野各一例:
    队列登记(active_check_hashes, 规则发起)与 store 快照 is_checking(用户手动 recheck,
    G5 的队列视野看不见它); 文案含「校验中」; 在途清空后放行; 零副作用"""
    # 半 1: 队列登记半(规则发起的校验经 recheck 在途登记可见)
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr, [ha, hb])
    client.torrents["HASH123"] = ha
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HASH123", "HB")
    seed_inflight(mgr, "HB")
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "正在全量校验" in r.message, f"组员在途(队列登记)应拒: {r}"
    assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"
    # 在途清空后放行(detail 空表 + 整条跳检成功)
    mgr.task_queue = TaskQueue()
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "在途清空后应过全部闸门"
    r2 = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r2.is_ok, f"在途清空后跳检应放行完成: {r2}"

    # 半 2: store 快照 is_checking 半(用户手动 recheck: 队列无登记, 只在快照可见)
    mgr_b = make_mgr(FakeConfig())
    client_b = FakeClient()
    mgr_b.client = client_b
    ha_b = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb_b = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr_b, [ha_b, hb_b])
    client_b.torrents["HASH123"] = ha_b
    client_b.torrents["HB"] = hb_b
    wire_group(mgr_b, "K", "HASH123", "HB")
    hb_b.state = "checkingDL"
    assert "HB" not in mgr_b.task_queue.active_check_hashes(), "半 2 前提: 队列无登记(G5 视野外)"
    vs = mgr_b.ctx.ops._skip_gates_detail("HASH123", ha_b)
    assert [v.gate for v in vs] == ["G7"], f"快照 is_checking 半应只落 G7: {vs}"
    r3 = mgr_b.ctx.ops.skip_check("HASH123", source="web")
    assert r3.is_failed and "正在全量校验" in r3.message, f"组员在途(快照)应拒: {r3}"
    hb_b.state = "pausedDL"
    assert mgr_b.ctx.ops._skip_gates_detail("HASH123", ha_b) == [], "快照退出校验态后应放行"


def test_skip_gates_rejects_group_check_failed():
    """测试(T17): 组内成员校验失败推断(G8, case 1) —— 其它成员当日 recheck_fails>0 且文件映射一致
    -> 拒, 文案含「校验失败」与 full-checking 出路; 负样本三例: 文件映射不一致放行 / 记录指向
    已完成成员放行(假失败自愈不参与) / 非当日放行; G8 路径不 pop 记录(只读自愈, 清理归规则侧);
    零副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr, [ha, hb])
    client.torrents["HASH123"] = ha
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HASH123", "HB")
    key = mgr.store.member_to_key["HASH123"]
    mgr.store.group_sizes.setdefault(key, {})["HASH123"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 100}
    mgr.state.setdefault("recheck_fails", {})["HB"] = {"date": date.today().isoformat(), "count": 1}
    fails_before = copy.deepcopy(mgr.state["recheck_fails"])

    # 正样本: G8 blocked, 文案带成员 hash8 与出路
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "校验失败" in r.message and "文件映射一致" in r.message, f"组员当日失败应拒: {r}"
    assert "HB" in r.message and "full-checking" in r.message, f"文案应带成员与出路: {r}"
    assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"
    assert mgr.state["recheck_fails"] == fails_before, "G8 路径不得改写 recheck_fails(零副作用)"

    # 负样本 1: 文件映射不一致(组内大小有差异, 校验的是不同数据) -> 不推断, 放行
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 200}
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "映射不一致应放行"
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 100}

    # 负样本 2: 记录指向已完成成员(假失败自愈: 与数据无关) -> 不参与推断, 且不 pop(只读变体)
    hb.state, hb.progress = "pausedUP", 1.0
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "已完成成员的失败记录应自愈放行"
    assert "HB" in mgr.state["recheck_fails"], \
        "G8 只读自愈不得 pop 记录(规则侧 full_checking.py:146 会 pop, 清理归规则侧与次日重置)"

    # 负样本 3: 非当日(次日重置口径) -> 放行
    hb.state, hb.progress = "pausedDL", 0.0
    mgr.state["recheck_fails"]["HB"] = {"date": "2000-01-01", "count": 1}
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "非当日记录应放行"


def test_skip_gates_g7_evidence_and_blocker_identity():
    """测试(S1): G7 证据口径与点名 —— checkingResumeData 不算在验(qB 简历校验不产生数据判决);
    映射不一致的成员不参与(对齐 G8); 命中时文案点名 blocker(hash8 + 名字 + state)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    a = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    b = FakeTorrent(hash="HBCHECK", name="Blocker.Movie", state="pausedDL", progress=0.0)
    seed_store(mgr, [a, b])
    client.torrents["HASH123"] = a
    client.torrents["HBCHECK"] = b
    wire_group(mgr, "K", "HASH123", "HBCHECK")
    key = mgr.store.member_to_key["HASH123"]
    mgr.store.group_sizes.setdefault(key, {})["HASH123"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HBCHECK"] = {"movie.mkv": 100}

    # 1) checkingResumeData: qB 启动/加种时的 resume data 比对, 不产生数据完整性判决 -> 不挡
    b.state = "checkingResumeData"
    assert mgr.ctx.ops._skip_gates_detail("HASH123", a) == [], "checkingResumeData 不应算作在验"

    # 2) 映射不一致: 校验的是另一份数据, 判决与本次跳检无关 -> 不参与(对齐 G8)
    b.state = "checkingUP"
    mgr.store.group_sizes[key]["HBCHECK"] = {"movie.mkv": 200}
    assert mgr.ctx.ops._skip_gates_detail("HASH123", a) == [], "映射不一致的成员不应参与 G7"

    # 3) 映射一致 + 真在验 -> G7(force), 文案点名 blocker(含 state 已持续时长)
    mgr.store.group_sizes[key]["HBCHECK"] = {"movie.mkv": 100}
    mgr.store.state_since["HBCHECK"] = time.time() - 125  # 本地观测到的状态起点(纯展示用)
    vs = mgr.ctx.ops._skip_gates_detail("HASH123", a)
    assert [v.gate for v in vs] == ["G7"], vs
    assert vs[0].cls == "force", vs
    text = vs[0].text
    assert "HBCHECK" in text and "Blocker.Movie" in text and "checkingUP" in text, \
        f"文案必须点名 blocker(hash8/名字/state): {text}"
    assert "已 2 分钟" in text, f"文案应带状态持续时长: {text}"


def test_skip_gates_inflight_ttl_expires_leaked_registration():
    """测试(S1): 在途登记超 TTL 视为泄漏(轮询任务已被丢弃) —— G5/G7 放行并记 WARNING

    登记只在轮询任务 FINISHED 时释放; 任务被异常丢弃时登记会永久残留, 让闸门一直亮着。"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])
    seed_inflight(mgr, "HASH123")

    # 新鲜登记 -> G5(在途)
    assert [v.gate for v in mgr.ctx.ops._skip_gates_detail("HASH123", t)] == ["G5"], "新鲜登记应挡"

    # 超过 TTL -> 忽略登记并记 WARNING
    mgr.task_queue.active_check_age = lambda h: INFLIGHT_TTL + 1
    with capture_logs("auto_qb.core.modules.ops_mod") as cap:
        assert mgr.ctx.ops._skip_gates_detail("HASH123", t) == [], "泄漏登记超 TTL 后应放行"
    assert any("登记泄漏" in m for m in cap.messages), cap.messages


def test_skip_gates_detail_classification():
    """测试(T18): _skip_gates_detail 三态归类 —— G5/G7->force; G3/G4/G6/G8/filelist/partial/dedup
    -> blocked; 全过->空; 执行路径 _skip_gates 与 detail 首个未过闸门一致(同源断言, 防两套谓词漂移;
    dedup 沿用 skip 形态、其余 fail 形态)。G7/G8(S1b-2)归入: G8 blocked 短路 filelist / G7 force 不短路"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ops = mgr.ctx.ops
    today = date.today().isoformat()

    def fresh(state, progress, hash_):
        t = FakeTorrent(hash=hash_, state=state, progress=progress)
        seed_store(mgr, [t])
        return t

    def gates(hash_, t):
        return [(v.gate, v.cls) for v in ops._skip_gates_detail(hash_, t)]

    # G3 已完成(做种态) -> blocked
    t = fresh("pausedUP", 1.0, "G3HA")
    assert gates("G3HA", t) == [("G3", "blocked")]
    # G4 活跃中 -> blocked(p=0 不触发 partial; 未归组下载态并发命中 G6, 自身即下载方, S1a 语义)
    t = fresh("downloading", 0.0, "G4HB")
    assert gates("G4HB", t) == [("G4", "blocked"), ("G6", "blocked")]
    # G5 同 hash 校验在途 -> force(case 2; G7 组内在途同归 force)
    t = fresh("pausedDL", 0.0, "G5HC")
    seed_inflight(mgr, "G5HC")
    assert gates("G5HC", t) == [("G5", "force")]
    r = ops._skip_gates("G5HC", t)
    assert r.is_failed and "正在全量校验" in r.message, f"force 类闸门缺省仍硬拒: {r}"
    # G6 组内活跃下载 -> blocked
    t = fresh("pausedDL", 0.0, "G6HD")
    hb = FakeTorrent(hash="G6HE", state="downloading", progress=0.3)
    seed_store(mgr, [t, hb])
    wire_group(mgr, "K6", "G6HD", "G6HE")
    assert gates("G6HD", t) == [("G6", "blocked")]
    # G7 组内其它成员校验在途 -> force(队列登记半); force 类不短路 filelist(缺失文件先设:
    # 文件列表是记录级惰性缓存, 首次 filelist 即定型, 之后改 client.files 不影响已缓存记录)
    t = fresh("pausedDL", 0.0, "G7HJ")
    hb7 = FakeTorrent(hash="G7HK", state="pausedDL", progress=0.0)
    seed_store(mgr, [t, hb7])
    wire_group(mgr, "K7", "G7HJ", "G7HK")
    seed_inflight(mgr, "G7HK")
    client.files = [SimpleNamespace(name="x.bin", size=1)]  # filelist 若真跑必 fail
    assert gates("G7HJ", t) == [("G7", "force"), ("filelist", "blocked")], \
        "G7 是 force 类, filelist 不得被短路(force 豁越后 case 1 硬闸仍须真跑)"
    client.files = []
    t2 = fresh("pausedDL", 0.0, "G7HN")  # 新记录: 旧记录已把缺失文件缓存进惰性列表, 换记录钉纯 G7 归类
    seed_store(mgr, [t2, hb7])
    wire_group(mgr, "K7", "G7HN", "G7HK")
    assert gates("G7HN", t2) == [("G7", "force")]
    mgr.task_queue = TaskQueue()  # 清在途登记, 换快照半: 用户手动 recheck(队列无登记)
    hb7.state = "checkingDL"
    assert gates("G7HN", t2) == [("G7", "force")]
    hb7.state = "pausedDL"
    # G8 组内成员校验失败推断 -> blocked(同映射 + 当日失败计数); blocked 短路 filelist
    t = fresh("pausedDL", 0.0, "G8HL")
    hb8 = FakeTorrent(hash="G8HM", state="pausedDL", progress=0.0)
    seed_store(mgr, [t, hb8])
    wire_group(mgr, "K8", "G8HL", "G8HM")
    key8 = mgr.store.member_to_key["G8HL"]
    mgr.store.group_sizes.setdefault(key8, {})["G8HL"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key8]["G8HM"] = {"movie.mkv": 100}
    mgr.state.setdefault("recheck_fails", {})["G8HM"] = {"date": today, "count": 1}
    client.files = [SimpleNamespace(name="x.bin", size=1)]  # filelist 若真跑必 fail
    fc8 = client.files_calls
    assert gates("G8HL", t) == [("G8", "blocked")], "G8 blocked 应短路 filelist(结论已注定)"
    assert client.files_calls == fc8, "G8 未过时 filelist 不得真跑(短路省 files API)"
    client.files = []
    # partial 部分下载 -> blocked(既有闸门并入 detail, 语义文案零变化)
    t = fresh("pausedDL", 0.5, "PRTF")
    assert gates("PRTF", t) == [("partial", "blocked")]
    # dedup 同日去重 -> blocked(既有闸门并入 detail; 执行路径沿用 skip 形态)
    t = fresh("pausedDL", 0.0, "DDPHG")
    mgr.state.setdefault("skip_check_day", {})["DDPHG"] = today
    assert gates("DDPHG", t) == [("dedup", "blocked")]
    r = ops._skip_gates("DDPHG", t)
    assert r.is_skipped and r.message == ops._skip_gates_detail("DDPHG", t)[0].text, \
        f"执行路径 dedup 应沿用 skip 形态且文案同源: {r}"
    # filelist 前置文件检查 -> blocked(排最后)
    t = fresh("pausedDL", 0.0, "FLHH")
    client.files = [SimpleNamespace(name="x.bin", size=1)]
    assert gates("FLHH", t) == [("filelist", "blocked")]
    client.files = []
    # 全过 -> 空列表; 执行路径 None
    t = fresh("pausedDL", 0.0, "OKHI")
    assert gates("OKHI", t) == []
    assert ops._skip_gates("OKHI", t) is None
    # 同源断言(混合场景): 活跃部分下载 -> detail 按固定顺序(G4 -> G6 -> partial), 执行路径取首个
    t = fresh("downloading", 0.5, "MXHJ")
    vs = ops._skip_gates_detail("MXHJ", t)
    assert [(v.gate, v.cls) for v in vs] == [("G4", "blocked"), ("G6", "blocked"), ("partial", "blocked")], \
        f"固定顺序: {vs}"
    r = ops._skip_gates("MXHJ", t)
    assert r.is_failed and r.message == vs[0].text, f"执行路径应取首个未过闸门(同源): {r} vs {vs[0]}"


def test_skip_check_force_semantics():
    """测试(T19): force 语义 —— force=True 仅豁越 cls=force 的未过闸门(G5/G7: WARNING 降级 +
    INFO 审计后放行成功); cls=blocked(G3/G6/G8/filelist)即使 force=True 仍硬拒带原文案;
    缺省 force=False 全拒(T6 已覆盖); 规则侧调用点不传 force 由签名缺省证明(零变化不变式)"""
    # G5 场景 force=True: 豁越放行成功, 留 WARNING(闸门降级) + INFO(审计: hash + 闸门)
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    seed_inflight(mgr, "HASH123")
    with capture_logs("auto_qb.core.modules.ops_mod", logging.DEBUG) as cap:
        r = mgr.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r.is_ok, f"force=True 应豁越 G5 放行: {r}"
    warns = [x.getMessage() for x in cap.records if x.levelname == "WARNING"]
    audits = [x.getMessage() for x in cap.records if x.levelname == "INFO"]
    assert any("force 豁越跳检闸门 G5" in m for m in warns), f"豁越闸门应留 WARNING: {warns}"
    assert any("force 审计" in m and "G5" in m and "HASH123" in m for m in audits), \
        f"豁越应留 INFO 审计(hash+闸门): {audits}"
    assert mgr.state["skip_check_day"]["HASH123"] == date.today().isoformat(), "豁越后跳检应真实完成"

    # G3 已完成 + force=True: case 1 硬拒带原文案
    mgr2 = make_mgr(FakeConfig())
    client2 = FakeClient()
    mgr2.client = client2
    t2 = FakeTorrent(hash="HASH123", state="pausedUP", progress=1.0)
    seed_store(mgr2, [t2])
    client2.torrents["HASH123"] = t2
    r2 = mgr2.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r2.is_failed and "已完成" in r2.message, f"blocked 闸门对 force 硬拒: {r2}"

    # G6 组内下载 + force=True: 仍硬拒
    mgr3 = make_mgr(FakeConfig())
    client3 = FakeClient()
    mgr3.client = client3
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="downloading", progress=0.3)
    seed_store(mgr3, [ha, hb])
    client3.torrents["HASH123"] = ha
    client3.torrents["HB"] = hb
    wire_group(mgr3, "K", "HASH123", "HB")
    r3 = mgr3.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r3.is_failed and "组内" in r3.message, f"G6 对 force 硬拒: {r3}"

    # filelist + force=True: 仍硬拒(证据缺失不给 force)
    mgr4 = make_mgr(FakeConfig())
    client4 = FakeClient()
    mgr4.client = client4
    seed_paused(mgr4, client4, hash="HASH123")
    client4.files = [SimpleNamespace(name="missing.bin", size=1)]
    r4 = mgr4.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r4.is_failed and "前置文件检查未通过" in r4.message, f"filelist 对 force 硬拒: {r4}"

    # 缺省 force=False: G5 场景硬拒(与上面 force=True 成对照)
    mgr5 = make_mgr(FakeConfig())
    client5 = FakeClient()
    mgr5.client = client5
    seed_paused(mgr5, client5, hash="HASH123")
    seed_inflight(mgr5, "HASH123")
    r5 = mgr5.ctx.ops.skip_check("HASH123", source="web")
    assert r5.is_failed and "正在全量校验" in r5.message, f"缺省 force=False 应硬拒: {r5}"

    # G7 组内校验在途 + force=True: 豁越放行(与 G5 同款, WARNING 降级 + INFO 审计)
    mgr6 = make_mgr(FakeConfig())
    client6 = FakeClient()
    mgr6.client = client6
    ha6 = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb6 = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr6, [ha6, hb6])
    client6.torrents["HASH123"] = ha6
    client6.torrents["HB"] = hb6
    wire_group(mgr6, "K", "HASH123", "HB")
    seed_inflight(mgr6, "HB")
    with capture_logs("auto_qb.core.modules.ops_mod", logging.DEBUG) as cap6:
        r6 = mgr6.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r6.is_ok, f"force=True 应豁越 G7 放行: {r6}"
    warns6 = [x.getMessage() for x in cap6.records if x.levelname == "WARNING"]
    audits6 = [x.getMessage() for x in cap6.records if x.levelname == "INFO"]
    assert any("force 豁越跳检闸门 G7" in m for m in warns6), f"G7 豁越应留 WARNING: {warns6}"
    assert any("force 审计" in m and "G7" in m and "HASH123" in m for m in audits6), \
        f"G7 豁越应留 INFO 审计(hash+闸门): {audits6}"

    # G8 组内校验失败推断 + force=True: case 1 仍硬拒带原文案
    mgr7 = make_mgr(FakeConfig())
    client7 = FakeClient()
    mgr7.client = client7
    ha7 = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb7 = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr7, [ha7, hb7])
    client7.torrents["HASH123"] = ha7
    client7.torrents["HB"] = hb7
    wire_group(mgr7, "K", "HASH123", "HB")
    key7 = mgr7.store.member_to_key["HASH123"]
    mgr7.store.group_sizes.setdefault(key7, {})["HASH123"] = {"movie.mkv": 100}
    mgr7.store.group_sizes[key7]["HB"] = {"movie.mkv": 100}
    mgr7.state.setdefault("recheck_fails", {})["HB"] = {"date": date.today().isoformat(), "count": 1}
    r7 = mgr7.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r7.is_failed and "校验失败" in r7.message and "full-checking" in r7.message, \
        f"G8 对 force 硬拒带原文案: {r7}"
    assert client7.calls == [], f"G8 硬拒零副作用: {client7.calls}"

    # 规则侧零变化证明: 签名缺省 False, 规则调用点(skip_checking.py)不传即零变化
    assert inspect.signature(OpsModule.skip_check).parameters["force"].default is False


def test_guard_skip_delete_scope_keep_record():
    """守阵(W9a gn18/gn20 高危 + gn19/gn21/gn22 + fn3): 跳检删除作用域必须是单 hash 且
    keep_record=True(delete+add 同上报间隔防线); web 源无「无参考跳检」告警泄漏"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    dels = _wrap_client(client, "torrents_delete", [])
    with capture_ops_logs() as logs:
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"暂停未完成应完成跳检: {r}"
    assert len(dels) == 1, f"删除恰一次: {dels}"
    assert dels[0]["torrent_hashes"] == "HASH123", f"删除作用域必须单 hash(不得 None=全库摘登记): {dels}"
    assert mgr.store.get("HASH123") is t, "keep_record 语义: 删除不得摘快照记录(残缺 patch 防线)"
    assert not any("无参考跳检" in m for m in logs), "web 源不得泄漏规则侧无参考告警(fn3)"
    # fn3 反面: web + 无参考 也不得告警(and→or 放宽即红)
    mgr2 = make_mgr(FakeConfig())
    client2 = FakeClient()
    mgr2.client = client2
    t2 = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr2, [t2])
    client2.torrents["HASH123"] = t2
    with capture_ops_logs() as logs2:
        r2 = mgr2.ctx.ops.skip_check("HASH123", source="web", has_reference=False)
    assert r2.is_ok
    assert not any("无参考跳检" in m for m in logs2), "web 源即使无参考也不得泄漏规则侧告警(fn3)"


def test_guard_skip_finish_start_scope():
    """守阵(W9a fn18 高危): auto_start 收尾的开始作用域必须是单 hash —— torrents_start(None)
    = 全库种子自动开始"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    starts = []

    def rec_start(torrent_hashes=None, **kw):
        starts.append(torrent_hashes)
        return client.torrents_start.__wrapped__(torrent_hashes=torrent_hashes, **
                                                 kw) if hasattr(client.torrents_start, "__wrapped__") else None

    orig_start = FakeClient.torrents_start
    client.torrents_start = lambda torrent_hashes=None, **kw: (
        starts.append(torrent_hashes), orig_start(client, torrent_hashes=torrent_hashes, **kw)
    ) and None
    r = mgr.ctx.ops.skip_check("HASH123", source="web", auto_start=True)
    assert r.is_ok, f"跳检应完成: {r}"
    assert starts == ["HASH123"], f"自动开始作用域必须单 hash(不得 None=全库开始): {starts}"


def test_guard_skip_readd_args_pin():
    """守阵(W9a ac 簇 + pr14/pr16): 重加参数直传 pin —— torrent_files/保存路径/分类/标签/
    内容布局/停种/顺序下载/首末块/上下列限速/比率与做种时限/分享限制全部原样回传,
    布局丢失=重加即 missingFiles"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(
        hash="HASH123",
        state="stoppedDL",
        progress=0.0,
        save_path="R:/Downloads",
        content_path="R:/Downloads/Test",
        category="cat",
        tags="tag1,tag2",
        seq_dl=True,
        f_l_piece_prio=True,
        up_limit=1234,
        dl_limit=5678,
        ratio_limit=2.5,
        seeding_time_limit=3600,
        inactive_seeding_time_limit=42,
        share_limit_action="ModeX",
    )
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    adds = _wrap_client(client, "torrents_add", [])
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"跳检应完成: {r}"
    assert len(adds) == 1, f"重加恰一次: {adds}"
    a = adds[0]
    assert a["torrent_files"] == [b"TORRENT-DATA"], f"必须带导出的 .torrent 数据: {a.get('torrent_files')}"
    assert a["save_path"] == "R:/Downloads", "save_path 丢失=数据位置错(缺文件态)"
    assert a["category"] == "cat" and a["tags"] == "tag1,tag2", "分类/标签不得丢失"
    assert a["contentLayout"] == "Original", "内容布局必须推断回传(丢失=重加即 missingFiles)"
    assert a["is_stopped"] is True, "重加必须显式停种"
    assert a["is_skip_checking"] is True
    assert a["is_sequential_download"] is True and a["is_first_last_piece_priority"] is True, "顺序下载偏好不得重置"
    assert a["upload_limit"] == 1234 and a["download_limit"] == 5678, "上传/下载限速属性不得丢失"
    assert a["ratio_limit"] == 2.5 and a["seeding_time_limit"] == 3600, "做种比率/做种时间限制不得重置"
    assert a["share_limit_action"] == "ModeX" and a["inactive_seeding_time_limit"] == 42, "分享限制属性不得重置"


def test_guard_skip_submit_defaults_conservative():
    """守阵(W9a ss3/ss5 + ss14/ss22/sb42/sb49/jn11/jn20): 缺省参数保守默认 —— WEB 批量不传
    auto_start 终态不得自动开始; 规则源不传 force 不得自动豁越 cls=force 闸; rule origin 必须随 job 保存"""
    # ss3: WEB 批量缺省不自动开始
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client)
    r = mgr.ctx.ops.skip_submit("HA", source="web")
    assert r.is_pending, f"异步入口应受理: {r}"
    assert mgr.ctx.ops._skip_jobs["HA"].auto_start is False, "WEB 缺省不得自动开始(保守默认)"
    # ss5: 规则源缺省 force=False -> G5(同 hash 校验在途, cls=force)必须真拦
    mgr2 = make_mgr(FakeConfig())
    client2 = FakeClient()
    mgr2.client = client2
    seed_paused(mgr2, client2)
    seed_inflight(mgr2, "HA")
    r2 = mgr2.ctx.ops.skip_submit("HA", source="rule")
    assert r2.is_failed and "校验" in r2.message, f"规则源缺省不得豁越 G5 force 闸: {r2}"
    # origin: 规则断点随 job 保存(终态重入队的数据源)
    mgr3 = make_mgr(FakeConfig())
    client3 = FakeClient()
    mgr3.client = client3
    seed_paused(mgr3, client3)
    origin = Task("rule", "rule-test", hash="HA", store=mgr3.store, handler=lambda task, d: REQUEUE)
    r3 = mgr3.ctx.ops.skip_submit("HA", source="rule", origin=origin)
    assert r3.is_pending
    assert mgr3.ctx.ops._skip_jobs["HA"].origin is origin, "rule origin 必须随 job 保存(丢=规则任务悬空)"


def test_guard_skip_begin_idempotent():
    """守阵(W9a sb8): 同 hash 在途幂等闸 —— 第二次提交必须被拒且旧 job 原样
    (闸失效=旧 job 的 on_done/origin 成孤儿)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)
    ops = mgr.ctx.ops
    job1 = ops._skip_job_new("HA", t, "web", False, True)
    r = ops.skip_submit("HA", source="web")
    assert "已在执行中" in r.message, f"幂等闸必须拒绝二次提交: {r}"
    assert ops._skip_jobs["HA"] is job1, "旧 job 不得被覆盖"


# ============================================================
# 覆盖率第三轮 T1a: 相位机推进/守卫余量(26-11-04 快照缺口 18 单位)
# ============================================================
def test_skip_gone_retry_delete_raise_and_attempts_exhausted():
    """测试: gone 相位确认种子仍在(qB 删除异步未落地形态) -> 幂等重试删除抛错被吞(兜底分支),
    退避次数(10/20/50/50/50ms)耗尽终态失败; 删除不摘记录, 失败不清同日去重"""
    from unittest.mock import patch

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    dels = {"n": 0}

    def flaky_delete(torrent_hashes=None, **kw):
        dels["n"] += 1
        if dels["n"] > 1:
            raise RuntimeError("delete in flight")  # 重试删除抛错: 兜底分支只吞不炸
        # 首删"成功"但不摘种子(模拟 qB 删除异步未落地): gone 相位确认仍在 -> 进退避重试

    client.torrents_delete = flaky_delete
    slept = []
    with patch("auto_qb.core.modules.ops_mod.time.sleep", side_effect=lambda s: slept.append(s)):
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "删除后种子仍在客户端" in r.message, f"重试耗尽应终态失败: {r}"
    assert dels["n"] == 5, f"首删 + 4 次幂等重试(第 5 次退避名额耗尽不再重试): {dels['n']}"
    assert len(slept) >= 1, "退避窗口真实存在(相位机每步一次调用, 步间退避)"
    assert mgr.store.get("HASH123") is t, "失败路径不摘快照记录(种子明明还在)"
    assert mgr.ctx.ops._skip_jobs == {}, "终态后 job 出账"


def test_skip_drive_settle_during_backoff_sleep_race():
    """测试: 退避 sleep 期间主循环微步并发推进(竞态形态, 同线程直驱模拟)把 job 推到终态 ->
    驱动循环经 while 条件出口收束(而非 break) —— 覆盖 189->200 分支弧"""
    from unittest.mock import patch

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    ops = mgr.ctx.ops

    def sticky_delete(torrent_hashes=None, **kw):
        pass  # 删除恒"成功"但种子仍在(gone 相位每轮进退避重试)

    client.torrents_delete = sticky_delete

    def race_sleep(_seconds):
        for j in list(ops._skip_jobs.values()):  # 主循环微步线并发布进(竞态)
            for _ in range(10):  # 一口气把余下退避走完: 终态确定在 sleep 窗口内落定
                ops._skip_step(j)

    with patch("auto_qb.core.modules.ops_mod.time.sleep", side_effect=race_sleep):
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "删除后种子仍在客户端" in r.message, f"并发推进应把 job 推到终态: {r}"
    assert ops.skip_result("HASH123") is r, "终态在 sleep 中落定, 同对象返回"
    assert ops.next_run_at() is None and ops._skip_jobs == {}, "终态后在途清空"


def test_skip_step_after_settle_is_noop():
    """测试: 终态 job 再被步进(并发双驱动形态)为 no-op —— 不重复结算/不重复广播/不重复回调
    (覆盖 213->217 分支弧: handler None 落到终态短路)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    ops = mgr.ctx.ops
    done_calls = {"n": 0}
    seen = {}

    def on_done(job):
        done_calls["n"] += 1
        seen["job"] = job

    assert ops.skip_submit("HASH123", source="web", on_done=on_done).is_pending
    assert drive_skip(mgr), "在途 job 应推到终态"
    job = seen["job"]
    assert job.settled and job.result.is_ok
    calls_before = list(client.calls)
    notify_calls = []
    mgr.ctx.web = SimpleNamespace(notify=lambda name, payload: notify_calls.append(name))
    ops._skip_step(job)  # 终态后再次步进: 必须整段 no-op
    assert notify_calls == [], "终态 job 不得重复广播进度事件"
    assert done_calls["n"] == 1, "终态回调不得重放"
    assert list(client.calls) == calls_before, "终态 job 再步进不得有新客户端调用"
    assert job.result.is_ok and job.settled, "结果与终态标志原样"


def test_skip_result_cache_trims_oldest():
    """测试: 终态结果缓存超 _SKIP_RESULT_KEEP(64)淘汰最旧条目(234-235);
    兼验 ctx.web=None(web 未启用形态)时 settle 跳过进度广播(237->249 分支弧)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    ops = mgr.ctx.ops
    for i in range(64):
        ops._skip_results[f"OLD{i:02d}"] = object()
    mgr.ctx.web = None  # web 未启用: settle 的进度广播段整体跳过
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"跳检应完成: {r}"
    assert "OLD00" not in ops._skip_results, "第 65 条入账后最旧条目应被淘汰"
    assert len(ops._skip_results) == 64, f"缓存上限钉死 64: {len(ops._skip_results)}"
    assert ops.skip_result("HASH123") is r, "新终态可查且与返回同对象"


def test_skip_settle_notify_failure_isolated():
    """测试: 进度事件广播失败只记 WARNING(事件广播失败不得影响已落定的终态)(247-248)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    mgr.ctx.web = SimpleNamespace(notify=lambda name, payload: (_ for _ in ()).throw(RuntimeError("bus down")))
    with capture_ops_logs() as logs:
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"广播失败不得影响跳检终态: {r}"
    assert any("跳检进度事件广播失败" in m for m in logs), logs
    res = mgr.ctx.ops.skip_result("HASH123")
    assert res is not None and res.is_ok, "终态结果照常落账"


def test_skip_settle_on_done_failure_isolated():
    """测试: 终态回调异常只记 ERROR(回调异常不得影响已落定的终态), 终态结果照常落账可查(254-255)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    ops = mgr.ctx.ops

    def bad_on_done(job):
        raise RuntimeError("collector crashed")

    assert ops.skip_submit("HASH123", source="web", on_done=bad_on_done).is_pending
    with capture_ops_logs() as logs:
        assert drive_skip(mgr), "回调抛错不得挡住其它 job 的推进"
    r = ops.skip_result("HASH123")
    assert r is not None and r.is_ok, f"终态结果照常落账: {r}"
    assert any("跳检终态回调异常" in m and "collector crashed" in m for m in logs), logs
    assert ops.next_run_at() is None and ops._skip_jobs == {}, "job 已出账"


def test_advance_due_budget_calls_truncates():
    """测试: advance_due 步数预算先到先止 —— budget_calls=1 时本轮只推进一条,
    超预算的 job 留待下轮(296-297), 后续推进仍能全部到终态"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    a = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    b = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr, [a, b])  # 一次性灌入(seed_store 是整表替换, 两次各灌会互相覆盖)
    client.torrents["HASH123"] = a
    client.torrents["HB"] = b
    ops = mgr.ctx.ops
    assert ops.skip_submit("HASH123", source="web").is_pending
    assert ops.skip_submit("HB", source="web").is_pending
    stepped = ops.advance_due(budget_ms=50.0, budget_calls=1)
    assert stepped == 1, f"预算先到先止: 本轮只推一步, 实推 {stepped}"
    assert len(ops._skip_jobs) == 2, "两条 job 均未到终态(单步不足以结算)"
    assert drive_skip(mgr), "余下预算内应能把全部在途 job 推到终态"
    assert ops.next_run_at() is None and ops._skip_jobs == {}, "终态后在途清空"


def test_skip_appeared_confirm_error_retries():
    """测试: 确认重加(qB 侧尚未处理完/直查异常)走退避重试, 不终态(418-420; 直驱拨相位)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    ops = mgr.ctx.ops
    assert ops.skip_submit("HASH123", source="web").is_pending
    job = ops._skip_jobs["HASH123"]
    job.phase = SKIP_PHASE_APPEARED  # 直驱: 相位拨到「确认重加」
    client.torrents_info = lambda **kw: (_ for _ in ()).throw(RuntimeError("api down"))
    ops._skip_step(job)
    assert job.attempts == 1, "确认异常应记一次退避重试"
    assert job.phase == SKIP_PHASE_APPEARED and not job.settled, "确认异常不终态, 留待退避后再试"
    assert ops.skip_result("HASH123") is None, "未到终态不应有结果缓存"


def test_skip_appeared_retry_add_raise_swallowed():
    """测试: 重加后确认不到时的幂等重加抛错被吞(433-434), 退避次数耗尽终态失败;
    失败路径把快照里的残留记录撤掉(它是假账, 下轮上报按真删除处理)"""
    from unittest.mock import patch

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    adds = {"n": 0}

    def flaky_add(**kw):
        adds["n"] += 1
        if adds["n"] > 1:
            raise RuntimeError("duplicate in flight")  # 幂等重加抛错: 兜底分支只吞不炸
        FakeClient.torrents_add(client, **kw)  # 首次重加正常受理
        client.torrents.pop("HASH123", None)  # qB 尚未处理完: 确认相位看不到 -> 进退避

    client.torrents_add = flaky_add
    with patch("auto_qb.core.modules.ops_mod.time.sleep", side_effect=lambda s: None):
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "重加后未确认到种子" in r.message, f"确认不到应终态失败: {r}"
    assert adds["n"] == 5, f"首次重加 + 4 次幂等重加(第 5 次重试名额耗尽不再重加): {adds['n']}"
    assert mgr.store.get("HASH123") is None, "失败路径应撤掉快照残留记录(假账)"
    assert mgr.ctx.ops._skip_jobs == {}, "终态后 job 出账"
