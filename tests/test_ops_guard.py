"""test_ops_guard 测试计划: test_ops: 危险操作独立操作层(OpsMixin)自测(plan 26-09-30-0109 §5.1, 不连接真实 qB)

## 测试计划(每个测试函数一条)

跳检闸门扩展(plan 26-10-05-0314 S1b-1: 三分流 detail 单点 + force + 预检):
- test_guard_backup_meta_pin: 备份元数据键面 pin(bt38-43) + 备份目录名 pin(bt9/10)
- test_guard_recover_backup_readd_pin: 崩溃恢复重加参数 pin(rb34/37/40/41/42/43/45/46/47/48/49/51/52/53/54/64)
- test_guard_fail_keeps_backup_when_gone: 种子不在时 _skip_fail 必须保留恢复凭据(fl6 中危 info(None) 销毁凭据)
- test_guard_drive_deadline_fail: 驱动超时必须 _skip_fail(job, msg) 收敛且返回原 job(dr8/10/11/13 崩溃卡死簇 + dr9/12 文案)
- test_guard_step_exception_settles: 相位步进异常必须收敛结算(st5/7/8 + na2/4/5 except 逃逸簇)
- test_guard_force_does_not_bypass_blocked: force 只豁越 force 闸, 后置 blocked 必须硬拒(sg10)
- test_guard_sections_pin_ops: ops sections 认领段名 pin(sec1/sec2 双杀)
- test_guard_on_sync_line_once: 启动对账一次性开关(os1/os3/os4)
- test_guard_arbitration_scope_single: 启动超时仲裁直查作用域单 hash(rc112 他人校验态劫持)
- test_guard_drive_backoff_sleeps: GONE 重试退避真睡(dr22/rt11/gn14) + 重试删除作用域/keep_record(gn18/19/20/21/22)
- test_guard_appeared_retry_attempts: APPEARED 重试 attempts 活性(na7 置 None=重加成功反报失败)
- test_guard_gates_ghost_member_inflight: G7 幽灵成员在途必须安全出判(gd103/114/115 崩溃簇)
- test_guard_checking_evidence_none_tor_safe: _checking_evidence tor=None 安全返回(ce3)
- test_guard_settle_keep_progress_requeue: DONE 终态 origin 带 keep_progress 重入队(tl63/65/66) + 有参考 rule 不误告警(sb40/jn7)
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
    run_queue,
    seed_inflight,
    seed_paused,
)


def test_guard_backup_meta_pin():
    """守阵(W9a bt38/bt39/bt40/bt41/bt42/bt43 + bt9/bt10): 备份元数据键面 pin —— 恢复凭据
    的 save_path/category/tags 键名与备份目录名是崩溃恢复的契约面"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_mgr(FakeConfig())
        ops = mgr.ctx.ops
        tor = FakeTorrent(hash="HB1", save_path="R:/X", category="cat", tags="t1,t2")
        path = ops._backup_torrent(tor, b"DATA")
        assert "skip-check-backup" in path, f"备份必须落专用子目录: {path}"
        with open(path, "rb") as f:
            assert f.read() == b"DATA"
        meta = mgr.state["skip_check_backup"]["HB1"]
        assert meta["save_path"] == "R:/X", "恢复元数据必须含 save_path"
        assert meta["category"] == "cat" and meta["tags"] == "t1,t2", "恢复元数据必须含 category/tags"
        assert meta["path"] == path and os.path.exists(path)
        assert os.path.basename(os.path.dirname(path)) == "skip-check-backup", \
            f"备份必须落 state 同级的 skip-check-backup 专用目录: {path}"


def test_guard_recover_backup_readd_pin():
    """守阵(W9a rb34/37/40/41/42/43/45/46/47/48/49/51/52/53/54/64): 崩溃恢复重加必须以
    二进制备份数据 + 原保存路径/分类/标签 + 停种 seed_mode 下发(任一丢失=恢复恒失败/数据位置错)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_mgr(FakeConfig())
        client = FakeClient()
        mgr.client = client
        keep = FakeTorrent(hash="HKEEP", state="pausedUP", progress=1.0)
        seed_store(mgr, [keep])
        client.torrents["HKEEP"] = keep  # by_hash 非空才过 on_sync_line 首闸
        path = os.path.join(td, "HMISSING.torrent")
        with open(path, "wb") as f:
            f.write(b"dummy-torrent")
        mgr.state.setdefault("skip_check_backup", {})["HMISSING"] = {
            "path": path,
            "save_path": r"R:\Downloads",
            "category": "cat",
            "tags": "tg",
            "ts": 0,
        }
        adds = _wrap_client(client, "torrents_add", [])
        mgr.ctx.ops.on_sync_line(True)
        assert len(adds) == 1, f"崩溃于删除后的种子必须用备份重加: {client.calls}"
        a = adds[0]
        assert a["torrent_files"] == [b"dummy-torrent"], f"必须以二进制 .torrent 重加(文本模式读=恒失败): {a.get('torrent_files')}"
        assert a["save_path"] == r"R:\Downloads", "重加必须回原保存路径"
        assert a["category"] == "cat" and a["tags"] == "tg", "分类/标签必须回传"
        assert a["is_skip_checking"] is True, "恢复重加必须 seed_mode(跳过校验)"
        assert a["is_stopped"] is True, "恢复重加必须停种"


def test_guard_fail_keeps_backup_when_gone():
    """守阵(W9a fl6): _skip_fail 时种子确实不在 -> 恢复凭据(备份)必须保留 ——
    torrents_info(None)=全库表会把「不在」误判成「还在」, 备份被销毁"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    other = FakeTorrent(hash="HOTHER", state="pausedUP", progress=1.0)
    client.torrents["HOTHER"] = other  # 干扰种子: info(None) 的全库面会被它劫持
    t = FakeTorrent(hash="HG", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])  # 只进快照不进客户端(种子已不在)
    ops = mgr.ctx.ops
    job = ops._skip_job_new("HG", t, "web", False, True)
    ops._backup_torrent(t, b"cred")
    assert "HG" in mgr.state["skip_check_backup"]
    ops._skip_fail(job, "重加种子失败: boom")
    assert "HG" in mgr.state["skip_check_backup"], "种子不在时备份(唯一恢复凭据)必须保留"
    assert os.path.exists(mgr.state["skip_check_backup"]["HG"]["path"]), "备份文件不得被清"
    assert mgr.store.get("HG") is None, "假账快照记录应被撤掉"


def test_guard_drive_deadline_fail(monkeypatch):
    """守阵(W9a dr8/dr10/dr11/dr13 + dr9/dr12): 驱动超时必须以 _skip_fail(job, msg) 收敛且
    返回原 job —— 参数错位/裸 return 都会崩在调用侧或让 job 不结算卡死(跳检闸恒闭至重启)"""
    from auto_qb.core.modules import ops_mod as ops_m

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HD1", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HD1"] = t
    ops = mgr.ctx.ops
    job = ops._skip_job_new("HD1", t, "web", False, True)
    monkeypatch.setattr(ops_m, "SKIP_DRIVE_TIMEOUT", 0.05)
    ops._skip_step = lambda j: None  # 卡死相位: 永不推进到终态
    ret = ops._skip_drive(job)
    assert ret is job, "必须返回原 job(裸 return None 会在调用侧崩)"
    assert job.phase == ops_m.SKIP_PHASE_FAILED, "超时必须落到失败终态"
    assert job.error == "跳检执行超时(客户端未在期限内响应), 备份保留", f"失败文案必须原样: {job.error!r}"


def test_guard_step_exception_settles(monkeypatch):
    """守阵(W9a st5/st7/st8 + na2/na4/na5): 相位步进异常必须经 _skip_fail(job, msg) 收敛结算
    —— except 块内的参数变异会直接逃逸成上抛崩 + job 不结算卡死"""
    from auto_qb.core.modules import ops_mod as ops_m

    def boom(_):
        raise RuntimeError("boom")

    # st 簇: handler 主链异常 -> 外层 except 收敛
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HS", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HS"] = t
    ops = mgr.ctx.ops
    job = ops._skip_job_new("HS", t, "web", False, True)
    job.phase = ops_m.SKIP_PHASE_GONE
    monkeypatch.setattr(ops, "_skip_step_gone", boom)
    ops._skip_step(job)
    assert job.settled and job.result is not None and job.result.is_failed, "handler 异常必须收敛成失败终态"
    assert "跳检执行异常" in job.result.message, f"失败文案应点明异常: {job.result.message}"
    assert "HS" not in ops._skip_jobs, "job 必须出账(不结算=跳检闸恒闭)"
    # na 簇: 重加失败 -> 内层 except 收敛且文案点明「重加种子失败」
    mgr2 = make_mgr(FakeConfig())
    client2 = FakeClient()
    mgr2.client = client2
    client2.add_error = RuntimeError("boom")
    t2 = FakeTorrent(hash="HN", state="stoppedDL", progress=0.0)
    seed_store(mgr2, [t2])
    client2.torrents["HN"] = t2
    ops2 = mgr2.ctx.ops
    job2 = ops2._skip_job_new("HN", t2, "web", False, True)
    job2.phase = ops_m.SKIP_PHASE_ADDING
    job2.data = b"x"
    job2.backup = "p"
    ops2._skip_step(job2)
    assert job2.settled and "重加种子失败" in job2.result.message, \
        f"重加失败文案必须点明(逃逸进外层 except 即红): {job2.result.message}"


def test_guard_force_does_not_bypass_blocked():
    """守阵(W9a sg10): force 只豁越 cls=force 的闸(G5), 后置 blocked(partial)必须照常硬拒 ——
    豁越后 break 会把 blocked 闸连带豁越(垃圾块标有效)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.5)  # 0<p<1 -> partial blocked 在 G5 之后
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    seed_inflight(mgr, "HA")  # G5 force 在前
    r = mgr.ctx.ops._skip_gates("HA", t, force=True)
    assert r is not None and r.is_failed, f"force 豁越 G5 后 partial(blocked)必须硬拒: {r}"


def test_guard_sections_pin_ops():
    """守阵(W9a ops sec1/sec2, no tests 记账): 配置段认领名 pin —— 认领错位会让
    skip_checking_tag 段成孤儿段"""
    mgr = make_mgr(FakeConfig())
    assert mgr.ctx.ops.sections() == ("skip_checking_tag", )


def test_guard_on_sync_line_once():
    """守阵(W9a os1/os3/os4): 启动对账一次性开关 —— 开关语义破(不置位/条件反转)会让
    残留备份每轮被重复重加"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_mgr(FakeConfig())
        client = FakeClient()
        mgr.client = client
        keep = FakeTorrent(hash="HKEEP", state="pausedUP", progress=1.0)
        seed_store(mgr, [keep])
        client.torrents["HKEEP"] = keep  # by_hash 非空才过首闸
        path1 = os.path.join(td, "H1.torrent")
        with open(path1, "wb") as f:
            f.write(b"d1")
        mgr.state.setdefault("skip_check_backup", {})["H1"] = {
            "path": path1,
            "save_path": "R:/",
            "category": "",
            "tags": ""
        }
        mgr.ctx.ops.on_sync_line(True)
        assert len([c for c in client.calls if c[0] == "add"]) == 1, "首轮应对账重加"
        path2 = os.path.join(td, "H2.torrent")
        with open(path2, "wb") as f:
            f.write(b"d2")
        mgr.state.setdefault("skip_check_backup", {})["H2"] = {
            "path": path2,
            "save_path": "R:/",
            "category": "",
            "tags": ""
        }
        mgr.ctx.ops.on_sync_line(True)  # 进程内不复位: 不得再次对账
        assert len([c for c in client.calls if c[0] == "add"]) == 1, f"对账每进程只跑一次: {client.calls}"


def test_guard_arbitration_scope_single():
    """守阵(W9a rc112): 启动超时仲裁直查必须单 hash —— torrents_info(None)=全库表, 任意
    他种子的校验态会劫持宽限判定(双向失真)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    other = FakeTorrent(hash="HOTHER", state="checkingDL", progress=0.5)
    client.torrents["HOTHER"] = other  # 干扰种子在客户端首位(mutation 下 info(None) 会拉它进仲裁)
    t = seed_paused(mgr, client)  # pausedDL 非真校验态
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_pending, f"rule 源应 pending: {r}"
    now = time.time()
    real_time = time.time
    try:
        time.time = lambda: now + 601.0
        run_queue(mgr, now + 601.0)  # 宽限耗尽: 仲裁直查(单 hash)见 pausedDL -> 判败
    finally:
        time.time = real_time
    assert mgr.state["recheck_fails"]["HA"]["count"] == 1, \
        "仲裁直查必须单 hash: 他人 checking 态不得劫持判定(误延长宽限=不计失败)"


def test_guard_drive_backoff_sleeps(monkeypatch):
    """守阵(W9a dr22 + rt11 + gn14): GONE 相位确认不到消失 -> 重试退避 10~50ms 必须真睡
    (退避被跳过=存在性直查热轮询 API 轰炸; 退避归零=窗口内重试风暴)"""
    from unittest.mock import patch

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    client.torrents_info = lambda **kw: [t]  # 恒报「仍在客户端」-> GONE 相位反复重试
    dels = _wrap_client(client, "torrents_delete", [])
    slept = []
    with patch("auto_qb.core.modules.ops_mod.time.sleep", side_effect=lambda s: slept.append(s)):
        r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "删除后种子仍在客户端" in r.message, f"重试耗尽应失败且文案点明: {r}"
    assert slept and all(s > 0 for s in slept), f"10~50ms 退避必须真睡(跳过/归零即红): {slept}"
    assert len(dels) == 5, f"初删 + 4 次重试删除: {[d.get('torrent_hashes') for d in dels]}"
    assert all(d["torrent_hashes"] == "HASH123" for d in dels), \
        f"删除(含重试)作用域必须单 hash(不得 None=全库摘登记): {dels}"
    # keep_record 在 facade 消费(不透传 client): 重试删除若丢 keep_record, 快照记录会被当场摘除
    assert mgr.store.get("HASH123") is t, "重试删除仍不得摘快照记录(keep_record 防线)"


def test_guard_appeared_retry_attempts():
    """守阵(W9a na7): APPEARED 相位 attempts 必须真置 0 —— 置 None 会让首次重试
    (attempts+1)TypeError, 重加已成功反报失败且 FINISH 不跑(参考标记丢失)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    calls = {"n": 0}
    orig_info = client.torrents_info

    def fake_info(**kw):
        calls["n"] += 1
        if calls["n"] == 2:  # 首次重加确认回空 -> APPEARED 相位走一次重试
            return []
        return orig_info(**kw)

    client.torrents_info = fake_info
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"重试后必须确认到种子并正常完成(APPEARED attempts 死存储置 None 即红): {r}"


def test_guard_gates_ghost_member_inflight():
    """守阵(W9a gd103/gd114/gd115): G7 幽灵成员(组表有登记、快照无记录)带在途校验时,
    闸门判定必须安全出判(不得对 None 记录取属性崩溃)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    mgr.store.member_to_key["HA"] = "K"
    mgr.store.member_to_key["HG"] = "K"  # 幽灵: 组表有、by_hash 无
    mgr.store.groups["K"] = ["HA", "HG"]
    mgr.store.group_sizes["K"] = {"HA": {"a.mkv": 100}, "HG": {"a.mkv": 100}}
    seed_inflight(mgr, "HG")  # 幽灵成员的在途登记(kind=inflight, rec=None)
    verdicts = mgr.ctx.ops._skip_gates_detail("HA", t)
    g7 = [v for v in verdicts if v.gate == "G7"]
    assert g7, f"幽灵成员在途应出 G7 判: {verdicts}"
    assert "校验已提交" in g7[0].text, f"rec=None 时 detail 应走 else 文案(不得取 rec.state/rec.name): {g7[0].text}"


def test_guard_checking_evidence_none_tor_safe():
    """守阵(W9a ce3): _checking_evidence 对 tor=None(幽灵成员)必须安全返回 None ——
    条件恒真化会对 None 取 .state 崩溃"""
    mgr = make_mgr(FakeConfig())
    assert mgr.ctx.ops._checking_evidence("HX", None) is None, "tor=None 必须安全返回 None"


def test_guard_settle_keep_progress_requeue():
    """守阵(W9a tl63/tl65/tl66 + sb40/jn7): DONE 终态 rule origin 必须带 keep_progress=True
    重入队(断点续跑); 有参考的 rule 跳检不得误报无参考告警"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    origin = Task("rule", "rule-test", hash="HASH123", store=mgr.store, handler=lambda task, d: REQUEUE)
    origin.resume_index = 4  # 断点标记: keep_progress 才保留
    rec = []
    orig_at = mgr.task_queue.add_task
    mgr.task_queue.add_task = lambda task, **kw: (rec.append((task, kw)), orig_at(task, **kw))[1]
    with capture_ops_logs() as logs:
        r = mgr.ctx.ops.skip_submit("HASH123", source="rule", has_reference=True, origin=origin)
        job = mgr.ctx.ops._skip_jobs["HASH123"]
        mgr.ctx.ops._skip_drive(job)  # 同步驱动到终态(settle 的 origin 重入队发生在 _skip_settle)
    assert r.is_pending and job.result is not None and job.result.is_ok, f"跳检应完成: {r} / {job.result}"
    assert any(tk is origin and kw.get("keep_progress") is True for tk, kw in rec), \
        f"DONE 终态 origin 必须带 keep_progress=True 重入队: {rec}"
    assert not any("无参考跳检" in m for m in logs), "有参考的 rule 跳检不得误报无参考告警"
