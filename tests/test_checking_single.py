"""test_checking_single 测试计划: checking 动作详细自测(不连接真实 qB, 用模拟对象)

## 测试计划(每个测试函数一条)
- test_checking_config_missing_section: with/without 段缺省合法(默认不启用)
- test_checking_config_defaults: 缺省配置项取默认值
- test_checking_config_custom_timeout: custom_basic_check_timeout 时间串解析为秒/缺省 600/非 custom 提供不报错
- test_checking_paused_completed_reference: 暂停已完成亦是参考种子(is_complete 判定)
- test_checking_complete_no_repeat: 完成种子反复触发不重复校验(bug 回归)
- test_checking_piecehashes_same: piecehashes 一致 -> 跳检
- test_checking_piecehashes_diff: piecehashes 不一致 -> 全检
- test_checking_piecehashes_api_error: piecehashes API 错误 -> 降级处理
- test_checking_custom_rc0: custom 校验 rc0 -> 完成
- test_checking_custom_rc1: custom 校验 rc1 -> 失败
- test_checking_verified_reference_used: verified 参考种子被使用
- test_checking_verified_references_not_persisted: verified 参考不持久化(仅内存)
- test_checking_dry_run: dry-run 不发送请求
- test_checking_action_deferred_on_own_write: 决策链入口让位(A 系 S2 D-3): 目标或其组刚被自有停/起(快照未回流) -> 本轮不出决策
- test_run_custom_check_carries_timeout: C27 守阵 —— 自定义校验 subprocess 必须带 timeout(action 解析值, 缺省 600)
- test_run_custom_check_timeout_classified_warning: 自定义校验超时 -> WARNING(含程序路径/候选hash/配置超时值/视为非参考)且视为非参考
- test_run_custom_check_oserror_classified_warning: OSError(含 FileNotFoundError) -> WARNING 且视为非参考
- test_run_custom_check_unexpected_exception_classified_error: 其它异常 -> ERROR 且不崩溃
"""

import json

import logging

import subprocess

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

from helpers import capture_logs, drive_skip, FakeClient, FakeConfig, FakeTorrent, make_ctx, make_manager, seed_store

from checking_support import (
    CheckingFakeClient,
    _TMP_STATE_DIR,
    _seg,
    inject_group,
    make_check_cfg,
    make_mgr,
    make_target,
    process_rule,
    run_queue,
)


# ============================================================
# A. 配置解析(spec 正确性 fail-fast 在 config 校验阶段, 见 test_config.py)
# ============================================================
def test_checking_config_missing_section():
    """测试: with/without 段可缺省(该段默认不启用), 显式段未写 enabled 默认不启用"""
    a = CheckAction({"basic_check": "filelist", "without_reference": _seg("full-checking")})
    assert a.with_reference == {"enabled": False, "mode": "", "auto_start": False}, "缺 with 段应默认不启用"
    b = CheckAction({"basic_check": "filelist", "with_reference": _seg("skip-checking")})
    assert b.without_reference == {"enabled": False, "mode": "", "auto_start": False}, "缺 without 段应默认不启用"
    assert a.without_reference["enabled"] is False, "显式段未写 enabled 默认不启用"
    assert b.with_reference["enabled"] is False, "显式段未写 enabled 默认不启用"


def test_checking_config_defaults():
    """测试: auto_start 缺省 false; 非 custom 时提供 custom_basic_check_program_path 不报错(忽略)"""
    a = CheckAction(
        {
            "basic_check": "filelist",
            "with_reference": {
                "mode": "skip-checking"
            },  # 无 auto_start
            "without_reference": {
                "mode": "full-checking"
            },
            "custom_basic_check_program_path": "/ignored/check.exe",  # 非 custom, 应忽略
        }
    )
    assert a.with_reference["auto_start"] is False
    assert a.without_reference["auto_start"] is False
    assert a.custom_program == "/ignored/check.exe"  # 不报错且保留
    assert a.basic_check == "filelist"


def test_checking_config_custom_timeout():
    """测试: custom_basic_check_timeout 时间串经 parse_time 解析为秒; 缺省 600; 非 custom 提供该键不报错"""
    a = CheckAction(
        {
            "basic_check": "custom",
            "custom_basic_check_program_path": "prog",
            "custom_basic_check_timeout": "90S"
        }
    )
    assert a.custom_timeout == 90.0, "时间串应解析为秒(90S -> 90.0)"
    b = CheckAction({"basic_check": "custom", "custom_basic_check_program_path": "prog"})
    assert b.custom_timeout == 600, "缺省应为 600s(C27 超时保险丝缺省档)"
    c = CheckAction({"basic_check": "filelist", "custom_basic_check_timeout": "90S"})  # 非 custom, 不报错
    assert c.custom_timeout == 90.0


def test_checking_paused_completed_reference():
    """测试: 暂停中的已完成(pausedUP)亦是参考候选(is_complete 判定, 参考用元数据与暂停无关) -> with_reference 段跳检"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    p = FakeTorrent(hash="P1", name="P1", state="pausedUP")  # 暂停已完成: 有效参考
    inject_group(mgr, "HASH123", "P1")
    seed_store(mgr, [t, p])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, f"暂停完成参考应可用: {client.calls}"
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "add_tags", "start"], f"跳检调用顺序: {client.calls}"
    add_call = [c for c in client.calls if c[0] == "add"][0]
    assert add_call[1]["is_skip_checking"] is True, f"重加应跳过校验: {add_call}"


def test_checking_complete_no_repeat():
    """测试(bug 回归): 已完成种子反复触发 -> 不重复 recheck/跳检"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    for _ in range(3):
        process_rule(mgr, client, t, dry_run=False)
    assert client.calls == [], f"已完成种子不应有任何校验调用: {client.calls}"


def test_checking_piecehashes_same():
    """测试: piecehashes 一致 -> 确定参考 -> with_reference 段执行(使用 torrents_piece_hashes API)"""
    cfg = make_check_cfg(basic_check="piecehashes", with_mode="skip-checking", with_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.piece_hashes_map = {"HASH123": ["a", "b"], "R1": ["a", "b"]}  # 一致
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("piece_hashes", "HASH123") in client.calls, f"应获取目标 piece hashes: {client.calls}"
    assert ("piece_hashes", "R1") in client.calls, f"应获取候选 piece hashes: {client.calls}"
    assert [c[0] for c in client.calls] == ["piece_hashes", "piece_hashes", "export", "delete", "add", "add_tags"], \
        f"有参考应走 with_reference 跳检(无 start, 跳检后打标): {client.calls}"


def test_checking_piecehashes_diff():
    """测试: piecehashes 不一致 -> 无参考 -> without_reference 段"""
    cfg = make_check_cfg(basic_check="piecehashes", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.piece_hashes_map = {"HASH123": ["a", "b"], "R1": ["a", "c"]}  # 不一致
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"
    assert ("export", None) not in client.calls, f"不应跳检: {client.calls}"


def test_checking_piecehashes_api_error():
    """测试: piece hashes API 异常 -> 视为无参考(不中断) -> without_reference 段"""
    cfg = make_check_cfg(basic_check="piecehashes", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.piece_hashes_error = True
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "API 错误不应中断"
    assert ("recheck", None) in client.calls, f"应降级为 full-checking: {client.calls}"


def test_checking_custom_rc0():
    """测试: custom 基础检查 rc=0 -> 候选为参考; 程序参数 = <候选hash> <保存路径>"""
    cfg = make_check_cfg(
        basic_check="custom", custom_program=r"C:\check.exe", with_mode="skip-checking", with_start=False
    )
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    with patch("subprocess.run") as mrun:
        mrun.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        handled = process_rule(mgr, client, t, dry_run=False)
        assert handled
        args = mrun.call_args.args[0]
        assert args == [r"C:\check.exe", "R1", r"R:\Downloads"], f"程序参数: {args}"
        assert ("export", "HASH123") in client.calls, f"有参考应走 with_reference 段: {client.calls}"


def test_checking_custom_rc1():
    """测试: custom 基础检查 rc!=0 -> 非参考 -> without_reference 段"""
    cfg = make_check_cfg(
        basic_check="custom", custom_program=r"C:\check.exe", without_mode="full-checking", without_start=True
    )
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    with patch("subprocess.run") as mrun:
        mrun.return_value = SimpleNamespace(returncode=1, stdout="", stderr="bad")
        handled = process_rule(mgr, client, t, dry_run=False)
        assert handled
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"
    assert ("export", None) not in client.calls, f"不应跳检: {client.calls}"


def test_checking_verified_reference_used():
    """测试: 内存 verified_references 与 basic_check 并集作参考(即使成员非上传状态)"""
    cfg = make_check_cfg(with_mode="skip-checking", with_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    mgr.store.verified_references = {"R1"}  # 历史 full-checking 通过
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="pausedUP")  # 非上传候选, 仅靠 verified
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("export", "HASH123") in client.calls, f"verified 参考应走 with_reference 段: {client.calls}"


def test_checking_verified_references_not_persisted():
    """测试: verified_references 仅内存, 重启后重新积累(不写 state_file)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = make_check_cfg(without_mode="full-checking", without_start=True)
        cfg.state_file = state_file
        mgr = make_mgr(cfg, with_tq=True)
        client = CheckingFakeClient()
        mgr.client = client
        t = make_target()
        client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
        t0 = time.time()
        process_rule(mgr, client, t, dry_run=False)  # 提交即发送 recheck
        seed_store(mgr, [make_target(state="checkingDL")])  # 校验中
        run_queue(mgr, t0 + 0.5)
        seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])  # 完成
        run_queue(mgr, t0 + 2.5)
        assert mgr.store.verified_references == {"HASH123"}, "完成后应晋升"
        mgr.ctx.state.save()

        mgr2 = make_manager(cfg=cfg)  # 重新加载同一 state 文件
        assert mgr2.store.verified_references == set(), "verified 参考不应持久化"


def test_checking_dry_run():
    """测试: dry-run -> 不调用任何客户端 API(含校验/跳检)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="full-checking")
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    handled = process_rule(mgr, client, t, dry_run=True)
    assert handled, "dry-run 应正常返回"
    assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"


def test_checking_action_deferred_on_own_write():
    """守阵(A 系 S2 D-3): 决策链入口让位 —— 目标或其组刚被自有停/起(快照未回流)则本轮不出决策

    红验: 去掉 CheckAction.execute 入口的 own_write_pending 闸门 -> 直接提交 recheck, 断言红。
    """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    ha = make_target(hash="HA")
    hb = make_target(hash="HB")
    seed_store(mgr, [ha, hb])
    client.torrents["HA"] = ha
    client.torrents["HB"] = hb
    inject_group(mgr, "HA", "HB")

    # 1. 同组成员 HB 刚被自有停/起 -> HA 的校验决策让位(不提交 recheck)
    mgr.store.note_own_write("HB")
    process_rule(mgr, client, ha)
    assert ("recheck", None) not in client.calls, f"让位不应提交 recheck: {client.calls}"

    # 2. 登记清除后照常提交 recheck(证明是 deferral 而非永久拒绝)
    mgr.store.own_writes.clear()
    process_rule(mgr, client, ha)
    assert ("recheck", None) in client.calls, f"登记清除后应提交 recheck: {client.calls}"


def test_run_custom_check_carries_timeout():
    """C27 守阵: 自定义校验 subprocess 必须带 timeout(action 解析值, 缺省 600) —— 重设计后超时
    保险丝仍须无条件传给 subprocess.run(去掉 -> 挂死的外部程序无限阻塞规则线程)"""
    action = CheckAction({"basic_check": "custom", "custom_basic_check_program_path": "prog"})
    tor = FakeTorrent(hash="C1", name="C", state="stalledUP")
    with patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stderr="")) as run:
        assert action._run_custom_check(None, tor) is True
    assert run.call_args.kwargs["timeout"] == action.custom_timeout == 600, f"缺超时保险丝: {run.call_args}"


def test_run_custom_check_timeout_classified_warning():
    """测试: 自定义校验超时 -> WARNING(含程序路径/候选 hash/实际配置超时值/「视为非参考」)且判非参考"""
    action = CheckAction(
        {
            "basic_check": "custom",
            "custom_basic_check_program_path": "prog",
            "custom_basic_check_timeout": "30S"
        }
    )
    tor = FakeTorrent(hash="C1ABCD", name="C", state="stalledUP")
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="prog", timeout=30)):
        with capture_logs("auto_qb.rules.actions.checking") as cap:
            assert action._run_custom_check(None, tor) is False, "超时候选应视为非参考"
    warns = [r for r in cap.records if r.levelno == logging.WARNING]
    assert len(warns) == 1, cap.text
    assert not any(r.levelno >= logging.ERROR for r in cap.records), cap.text
    msg = warns[0].getMessage()
    for token in ("prog", "C1ABCD", "30", "视为非参考"):
        assert token in msg, msg


def test_run_custom_check_oserror_classified_warning():
    """测试: 自定义校验 OSError(含 FileNotFoundError, 如容器缺程序) -> WARNING 且判非参考(不崩溃)"""
    action = CheckAction({"basic_check": "custom", "custom_basic_check_program_path": "prog"})
    tor = FakeTorrent(hash="C1ABCD", name="C", state="stalledUP")
    with patch("subprocess.run", side_effect=OSError("no prog")):
        with capture_logs("auto_qb.rules.actions.checking") as cap:
            assert action._run_custom_check(None, tor) is False, "执行失败候选应视为非参考"
    warns = [r for r in cap.records if r.levelno == logging.WARNING]
    assert len(warns) == 1, cap.text
    assert not any(r.levelno >= logging.ERROR for r in cap.records), cap.text
    msg = warns[0].getMessage()
    for token in ("prog", "C1ABCD", "视为非参考"):
        assert token in msg, msg


def test_run_custom_check_unexpected_exception_classified_error():
    """测试: 其它异常 -> ERROR(非环境性失败, 要按错误让人看见)且不崩溃、判非参考"""
    action = CheckAction({"basic_check": "custom", "custom_basic_check_program_path": "prog"})
    tor = FakeTorrent(hash="C1ABCD", name="C", state="stalledUP")
    with patch("subprocess.run", side_effect=ValueError("boom")):
        with capture_logs("auto_qb.rules.actions.checking") as cap:
            assert action._run_custom_check(None, tor) is False, "异常候选应视为非参考(不向上抛)"
    errs = [r for r in cap.records if r.levelno >= logging.ERROR]
    assert len(errs) == 1, cap.text
    assert "boom" in errs[0].getMessage(), errs[0].getMessage()
