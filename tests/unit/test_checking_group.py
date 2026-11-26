"""test_checking_group 测试计划: checking 动作详细自测(不连接真实 qB, 用模拟对象)

## 测试计划(每个测试函数一条)
- test_download_conflict_multi_dl: 多成员下载中 -> 冲突, 不发起校验
- test_download_conflict_mixed: 下载中与暂停混合 -> 冲突
- test_download_conflict_no_repeat: 已发起的校验不重复提交
- test_download_conflict_resolve_recur: 冲突消除后恢复校验(递归决策)
- test_download_conflict_single_dl: 单下载中不冲突
- test_download_conflict_grouping_disabled: 分组未启用不检查冲突
- test_checking_no_group_uses_without_reference: 未归组无参考 -> 直接校验
- test_checking_group_fail_record_healed_when_member_completed: 1.6 假失败自愈: 记录指向已完成成员 -> 记录清除且不推断
- test_checking_group_no_infer_when_sizes_differ: 组内文件映射不一致 -> 不推断, B 照常校验
- test_checking_group_wait_timeout_force_resume: 等待超时强制恢复重判(防在途登记泄漏活锁)
- test_checking_group_wait_own_deleted_revives_origin: 组内等待中自身已删除 -> revive origin + 轮询消亡 (P2-a)
- test_checking_group_wait_poll_error_revives_origin: 组内等待轮询异常 -> revive origin + 消亡 (P2-a)
- test_is_piece_checking_excludes_resume_data: 全量校验态判定 —— 排除 qB 启动期简历校验 checkingResumeData(伪证据别名)
- test_poll_verdict_line_by_line: 轮询单跳判定逐行表测(事故行: 无证据 progress=1.0 不得 SUCCESS)
- test_poll_verdict_success_iff_seen_checking: 判定穷举性质(160 组合): SUCCESS 必有 seen_checking 背书
- test_group_fail_inference_gates_own_hash_and_zero_count: C25 守阵 —— 1.6 闸门: 自身失败不推断
  自己, count==0 的兄弟不推断
- test_group_fail_inference_scans_past_self_and_stale_records: C26 守阵 —— 1.6 遍历遇自身/陈旧
  记录只跳过当前项(continue→break 会截断后续真失败成员)
- test_group_fail_selfheal_flushes_state: 1.6 假失败自愈 pop 后即时落盘(pop 后盘上已无记录)
- test_group_fail_no_selfheal_skips_save: 1.6 未发生自愈 -> 不 pop 不落盘(两路径对照)
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

from auto_qb.rules.checking_meta import PieceCheckingStates, PollVerdict, is_piece_checking, poll_verdict

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


# ============================================================
# B. 分组下载冲突(6)
# ============================================================
def test_download_conflict_multi_dl():
    """测试: 同组两个及以上种子同时下载 -> 警告 + 整组暂停(一次); dry-run 不暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
            FakeTorrent(hash="D2", name="D2", state="downloading", amount_left=1),
        ]
    )
    inject_group(mgr, "D1", "D2")
    mgr.host.get("grouping")._check_download_conflicts(dry_run=True)
    assert ("stop", None) not in client.calls, f"dry-run 不应暂停: {client.calls}"
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"


def test_download_conflict_mixed():
    """测试: 已完成与下载中并存 -> 警告 + 整组暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="U1", name="U1", state="stalledUP", amount_left=0),
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
        ]
    )
    inject_group(mgr, "U1", "D1")
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"混合并存应整组暂停: {client.calls}"


def test_download_conflict_no_repeat():
    """测试: 冲突持续 -> 不重复暂停(幂等去重)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
            FakeTorrent(hash="D2", name="D2", state="downloading", amount_left=1),
        ]
    )
    inject_group(mgr, "D1", "D2")
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"冲突持续不应重复暂停: {client.calls}"


def test_download_conflict_resolve_recur():
    """测试: 冲突消除后清除去重, 重现时再次警告+暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    d1 = FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1)
    d2 = FakeTorrent(hash="D2", name="D2", state="downloading", amount_left=1)
    seed_store(mgr, [d1, d2])
    inject_group(mgr, "D1", "D2")
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1

    # 冲突消除(全组完成, 无下载中): 不再暂停, 去重记录清除
    d1.state = "stalledUP"
    d1.amount_left = 0
    d2.state = "stalledUP"
    d2.amount_left = 0
    seed_store(mgr, [d1, d2])
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"冲突消除后不应暂停: {client.calls}"

    # 冲突重现(D2 重新下载): 再次暂停(记录已清除, 新冲突类型 mixed)
    d2.state = "downloading"
    d2.amount_left = 1
    seed_store(mgr, [d1, d2])
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 2, f"冲突重现应再次暂停: {client.calls}"


def test_download_conflict_single_dl():
    """测试: 单下载中(无已完成)不冲突; 多组互不影响"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
            FakeTorrent(hash="U1", name="U1", state="stalledUP", amount_left=0),
        ]
    )
    inject_group(mgr, "D1", key=("K1", ))
    inject_group(mgr, "U1", key=("K2", ))
    mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
    assert ("stop", None) not in client.calls, f"单下载中不应暂停: {client.calls}"


def test_download_conflict_grouping_disabled():
    """测试: 分组未启用 -> 整轮刷新不触发下载冲突检查(无 stop)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()  # grouping.enabled = False
        mgr = make_mgr(cfg)
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="D1", name="D1", state="downloading", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="D2", name="D2", state="downloading", save_path=r"R:\Downloads")
        client.torrents["D1"] = t1
        client.torrents["D2"] = t2
        mgr._refresh_torrents()
        assert ("stop", None) not in client.calls, f"分组未启用不应检查冲突: {client.calls}"
        assert mgr.store.groups == {}, f"分组未启用不应有分组: {mgr.store.groups}"


def test_checking_no_group_uses_without_reference():
    """测试: 分组未启用/未归组 -> 视为单种子组, 无参考 -> without_reference 段"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    run_queue(mgr)  # 首轮: 发送 recheck
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"


def test_checking_group_fail_record_healed_when_member_completed():
    """决策链 1.6 假失败自愈: 失败记录指向的成员已完成(progress>=1) -> 记录清除且不推断

    2026-09-25 误判故障解毒: A 的「失败」与数据无关(实际校验已通过)时, B 不得被推断拦截,
    记录就地清除(否则毒化持续到次日)。A 已完成 -> B 经决策链 2 以 A 为参考走跳检。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA", state="pausedUP", progress=1.0)  # A 已完成: 记录必为假失败
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    client.torrents["HB"] = b  # R2 实时复核读客户端(非快照): 跳检前种子必须在客户端
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {})["HA"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 100}
    mgr.state.setdefault("recheck_fails", {})["HA"] = {"date": date.today().isoformat(), "count": 1}
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr.host.get("rules")._create_rule_task(rule, "HB")
    mgr.task_queue.add_task(tb, time.time())
    run_queue(mgr)
    assert "HA" not in mgr.state.get("recheck_fails", {}), "假失败记录应被自愈清除"
    assert client.calls.count(("recheck", None)) == 0, "A 已完成可为参考, B 走跳检而非 full-checking"
    add_call = [c for c in client.calls if c[0] == "add"]
    assert add_call and add_call[0][1]["is_skip_checking"] is True, f"B 应以 A 为参考走跳检: {client.calls}"


def test_checking_group_no_infer_when_sizes_differ():
    """决策链 1.6 不推断: 组内文件映射不一致(校验的是不同数据) -> B 照常提交 full-checking"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {})["HA"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 200}  # 大小不一致
    mgr.state.setdefault("recheck_fails", {})["HA"] = {"date": date.today().isoformat(), "count": 1}
    client.torrents["HB"] = b  # P1 提交点实时复核读客户端: B 提交前种子必须在客户端(非 checking 态)
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr.host.get("rules")._create_rule_task(rule, "HB")
    mgr.task_queue.add_task(tb, time.time())
    run_queue(mgr)
    assert ("recheck", None) in client.calls, "映射不一致不应推断, B 照常校验"
    assert mgr.task_queue.active_check_hashes() == {"HB"}, "B 提交后应登记在途"
    assert tb.resume_index == 1 and tb not in mgr.task_queue._fast, "B 提交后推迟, 由轮询子任务恢复"


def test_checking_group_wait_timeout_force_resume():
    """等待超时兜底: 超时强制恢复重走决策链(防在途登记泄漏活锁), 组内仍在校验则再次让位"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA", state="checkingDL")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr.host.get("rules")._create_rule_task(rule, "HB")
    tb.interval = 60.0
    t0 = time.time()
    mgr.task_queue.add_task(tb, t0)
    run_queue(mgr, t0)
    assert tb.resume_index == 1 and tb not in mgr.task_queue._fast, "B 应推迟等待"
    with patch("auto_qb.rules.actions.full_checking.GROUP_CHECK_WAIT_LIMIT", 0.0):
        seed_store(mgr, [a, b])  # HA 持续校验中
        run_queue(mgr, t0 + 60.5)  # 等待任务超时 -> 强制 resume(origin 重新入队; run_due 快照语义下当批不执行)
        run_queue(mgr, t0 + 60.5)  # 下一批到期: B 重走决策链 -> 仍在校验 -> 再次让位
    assert tb.resume_index == 1 and tb not in mgr.task_queue._fast, "超时强制恢复后应重走决策链并再次推迟"
    assert client.calls.count(("recheck", None)) == 0, f"B 全程不应提交 recheck: {client.calls}"


# ============================================================
# P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02): 组内校验等待轮询的异常出口
# ============================================================
def _group_wait_env(td):
    """构造组内等待场景: A 已提交 recheck 在途, B 让位等待(check-wait 任务已注册)

    返回 (mgr, client, ta, tb); 复用 test_checking_group_full_checking_serialized 的摆法。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    cfg.state_file = os.path.join(td, "state.json")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    client.torrents["HA"] = a  # P1 提交点实时复核读客户端: A 的 full-checking 提交须 live 放行(非 checking 态)
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    t0 = time.time()
    ta = mgr.host.get("rules")._create_rule_task(rule, "HA")
    tb = mgr.host.get("rules")._create_rule_task(rule, "HB")
    ta.interval = 60.0
    tb.interval = 60.0
    mgr.task_queue.add_task(ta, t0)
    run_queue(mgr, t0)
    assert mgr.task_queue.active_check_hashes() == {"HA"}, "A 应登记在途"
    mgr.task_queue.add_task(tb, t0 + 0.1)
    run_queue(mgr, t0 + 0.1)
    assert tb.resume_index == 1, "B 应进入等待(断点)"
    return mgr, client, ta, tb


def test_checking_group_wait_own_deleted_revives_origin():
    """组内校验等待: 等待期间自身种子已删除 -> 告警 + revive origin(由删除守卫判死) + 等待任务消亡"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, ta, tb = _group_wait_env(td)
        assert client.calls.count(("recheck", None)) == 1, "只有 A 提交 recheck"
        mgr.store.remove_torrent("HB")  # 等待期间自身被删除
        run_queue(mgr, time.time() + 5.0)
        assert not any(t.kind == "check-wait" for t in mgr.task_queue._fast), "等待任务应消亡"
        assert tb in mgr.task_queue._fast, "origin 应被 revive 重入队(后续由删除守卫判死)"
        assert client.calls.count(("recheck", None)) == 1, "删除后不得再提交 recheck"


def test_checking_group_wait_poll_error_revives_origin():
    """组内校验等待: 轮询异常 -> 告警 + revive origin + 等待任务消亡(防在途泄漏活锁)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, ta, tb = _group_wait_env(td)
        orig_get = mgr.store.get

        def boom(h):
            raise RuntimeError("snapshot boom")

        mgr.store.get = boom  # 让 wait_poll 首步即异常
        try:
            run_queue(mgr, time.time() + 5.0)
        finally:
            mgr.store.get = orig_get
        assert not any(t.kind == "check-wait" for t in mgr.task_queue._fast), "等待任务应消亡"
        assert tb in mgr.task_queue._fast, "origin 应被 revive 重入队"
        assert client.calls.count(("recheck", None)) == 1, "异常路径不得重复提交 recheck"


# ============================================================
# H. checking_meta 判定纯函数(plan 26-10-04-1824 S1): 不连真 qB, 纯函数直接导入测试
# ============================================================
def test_is_piece_checking_excludes_resume_data():
    """测试: 全量校验态判定 —— checkingDL/checkingUP 为真; qB 启动期简历校验 checkingResumeData 与常见态全假"""
    assert PieceCheckingStates == frozenset({"checkingDL", "checkingUP"}), "真全量校验态集合只有 checkingDL/checkingUP"
    assert is_piece_checking("checkingDL") is True
    assert is_piece_checking("checkingUP") is True
    assert is_piece_checking("checkingResumeData") is False, "简历校验是启动期伪证据别名, 必须排除"
    for st in (
        "downloading", "uploading", "stalledDL", "stalledUP", "pausedDL", "pausedUP", "stoppedUP", "error",
        "missingFiles", "queuedDL"
    ):
        assert is_piece_checking(st) is False, f"非校验态 {st} 不应判真"


def test_poll_verdict_line_by_line():
    """测试: 判定顺序语义逐行表测(期望值全显式); 含事故行(issue 26-10-03-1140)

    事故行: 线上现状的成功分支 `if rec.progress >= 1.0: 成功` 对陈旧快照直接下结论 ——
    seen=F, progress=1.0(=baseline) 被误判「校验成功」; 新语义钉为 WAITING/START_TIMEOUT。
    """
    # 事故行: 未见生效证据 + 陈旧快照 progress=1.0(=baseline): 未超宽限 -> WAITING, 超宽限 -> START_TIMEOUT
    assert poll_verdict(seen_checking=False, progress=1.0, baseline_progress=1.0, elapsed=0.0) is PollVerdict.WAITING
    assert poll_verdict(seen_checking=False, progress=1.0, baseline_progress=1.0, elapsed=599.0) is PollVerdict.WAITING
    assert poll_verdict(
        seen_checking=False, progress=1.0, baseline_progress=1.0, elapsed=600.0
    ) is PollVerdict.START_TIMEOUT
    # 生效已确认 -> 结果判定(不再看 baseline): 完成 SUCCESS / 未完成 FAILED
    assert poll_verdict(seen_checking=True, progress=1.0, baseline_progress=1.0, elapsed=0.0) is PollVerdict.SUCCESS
    assert poll_verdict(seen_checking=True, progress=0.97, baseline_progress=0.5, elapsed=0.0) is PollVerdict.FAILED
    # 未见生效证据但 progress 回落(数据缺损签名): 超宽限与否都 FAILED(先于超时判定)
    assert poll_verdict(seen_checking=False, progress=0.9, baseline_progress=1.0, elapsed=0.0) is PollVerdict.FAILED
    assert poll_verdict(seen_checking=False, progress=0.9, baseline_progress=1.0, elapsed=1e6) is PollVerdict.FAILED
    # progress==baseline 未超宽限: 歧义 -> 继续等
    assert poll_verdict(seen_checking=False, progress=0.5, baseline_progress=0.5, elapsed=599.0) is PollVerdict.WAITING


def test_poll_verdict_success_iff_seen_checking():
    """测试: 穷举性质(全叉积 160 组合, 非抽样) —— SUCCESS 必有生效证据背书, 无证据成功不可表达

    seen=True 时判定只由 progress 决定(progress>=1.0 则 SUCCESS, 与 baseline/elapsed 无关);
    seen=False 时 SUCCESS 永不可达。
    """
    for seen in (False, True):
        for progress in (0.0, 0.5, 0.999, 1.0, 1.5):
            for baseline in (0.0, 0.5, 1.0, 1.2):
                for elapsed in (0.0, 599.0, 600.0, 1e6):
                    v = poll_verdict(seen_checking=seen, progress=progress, baseline_progress=baseline, elapsed=elapsed)
                    ctx = f"seen={seen} progress={progress} baseline={baseline} elapsed={elapsed} -> {v}"
                    if seen:
                        assert (v is PollVerdict.SUCCESS) == (progress >= 1.0), f"生效后判定只由 progress 决定: {ctx}"
                    else:
                        assert v is not PollVerdict.SUCCESS, f"无生效证据不得 SUCCESS: {ctx}"


def test_group_fail_inference_gates_own_hash_and_zero_count():
    """C25 守阵: 1.6 闸门 —— 自身失败不得推断自己, 无失败证据的兄弟也不得推断

    变异: `h == hash or count <= 0` 的 `or` 改 `and` -> 自身的失败记录反被当证据;
    `<= 0` 改 `< 0` -> count==0(无证据)的兄弟被当成失败成员。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    me = make_target(hash="HA")
    sib = make_target(hash="HB")
    seed_store(mgr, [me, sib])
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {}).update({"HA": {"movie.mkv": 100}, "HB": {"movie.mkv": 100}})
    mgr.state.setdefault("recheck_fails", {})["HA"] = {"date": date.today().isoformat(), "count": 3}
    ctx = make_ctx(mgr, me, client)
    action = CheckAction({"basic_check": "filelist"})
    assert action._skip_on_group_check_failed(ctx, ["HA", "HB"]) is None, "自身失败/兄弟无证据都不得推断"


def test_group_fail_inference_scans_past_self_and_stale_records():
    """C26 守阵: 1.6 遍历遇自身/陈旧记录只跳过当前项

    变异: 两处 `continue` 改成 `break` -> 首轮(自身)或陈旧记录处即中断, 后面的真失败成员
    不被判定, 失败推断与假失败自愈整段失效。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    me = make_target(hash="HA")
    stale = make_target(hash="HB", state="pausedUP", progress=1.0)  # 已完成 -> 记录是假失败
    failed = make_target(hash="HC")
    seed_store(mgr, [me, stale, failed])
    inject_group(mgr, "HA", "HB", "HC")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {}).update(
        {
            "HA": {
                "movie.mkv": 100
            },
            "HB": {
                "movie.mkv": 100
            },
            "HC": {
                "movie.mkv": 100
            },
        }
    )
    today = date.today().isoformat()
    mgr.state.setdefault("recheck_fails",
                         {}).update({
                             "HB": {
                                 "date": today,
                                 "count": 3
                             },
                             "HC": {
                                 "date": today,
                                 "count": 2
                             },
                         })
    ctx = make_ctx(mgr, me, client)
    action = CheckAction({"basic_check": "filelist"})
    out = action._skip_on_group_check_failed(ctx, ["HA", "HB", "HC"])
    assert out is not None and out.is_skipped, "末位的真失败成员仍应被判定并推断跳过"
    assert "HC" in out.message
    assert "HB" not in mgr.state.get("recheck_fails", {}), "陈旧记录应被自愈清除"


def test_group_fail_selfheal_flushes_state():
    """1.6 假失败自愈清除即时落盘: pop 后状态已在盘上, 不依赖周期落盘窗口

    回归 issue 26-11-03-0104: 自愈只改内存时, 崩溃/断电会丢失本次自愈(残留记录下次 1.6
    再自愈, 代价是一次多余 recheck)。本用例直接驱动生产写点、不经跳检路径 —— 跳检完成
    自身也会 save_state, 走整条规则链会把两种写点混在一起, 掩盖本处漏落盘。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    me = make_target(hash="HA")
    done = make_target(hash="HB", state="pausedUP", progress=1.0)  # 已完成: 记录必为假失败
    seed_store(mgr, [me, done])
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {}).update({"HA": {"movie.mkv": 100}, "HB": {"movie.mkv": 100}})
    mgr.state.setdefault("recheck_fails", {})["HB"] = {"date": date.today().isoformat(), "count": 2}
    ctx = make_ctx(mgr, me, client)
    action = CheckAction({"basic_check": "filelist"})
    with patch.object(mgr.ctx.state, "save", wraps=mgr.ctx.state.save) as m_save:
        assert action._skip_on_group_check_failed(ctx, ["HA", "HB"]) is None, "自愈不参与推断"
    assert m_save.call_count == 1, "自愈清除必须即时落盘一次"
    assert os.path.exists(mgr.state_file), "自愈后状态文件必须已写出"
    with open(mgr.state_file, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert "HB" not in on_disk.get("recheck_fails", {}), "盘上不得残留已自愈的失败记录"


def test_group_fail_no_selfheal_skips_save():
    """1.6 未发生自愈 -> 不 pop 不落盘(落盘只在自愈写点发生, 不等于每次 1.6 都写盘)

    与 test_group_fail_selfheal_flushes_state 配成两路径: 记录仍指向未完成成员时是有效
    失败证据, 映射不一致也不推断 —— 内存记录原样保留, 且不得产生额外磁盘写入。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    me = make_target(hash="HA")
    sib = make_target(hash="HB")  # 未完成: 失败记录有效
    seed_store(mgr, [me, sib])
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {}).update({"HA": {"movie.mkv": 100}, "HB": {"movie.mkv": 200}})
    mgr.state.setdefault("recheck_fails", {})["HB"] = {"date": date.today().isoformat(), "count": 1}
    ctx = make_ctx(mgr, me, client)
    action = CheckAction({"basic_check": "filelist"})
    with patch.object(mgr.ctx.state, "save", wraps=mgr.ctx.state.save) as m_save:
        assert action._skip_on_group_check_failed(ctx, ["HA", "HB"]) is None, "映射不一致不推断"
        assert m_save.call_count == 0, "未发生自愈不得落盘"
    assert "HB" in mgr.state.get("recheck_fails", {}), "有效失败记录不得被清除"
    assert not os.path.exists(mgr.state_file), "未发生自愈时不应凭空写出状态文件"
