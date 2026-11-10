"""test_relocate_exec_reconcile 测试计划: 整组迁移执行体对账面 / S3 接线(S4 相位模型重定义 26-11-05-0808)

S4 重写说明: 旧链对账表 8 行(FINALIZE/RESPAWN/REDELETE/REVERT_INTENT/FAILED_TIMEOUT/
DONE_EXTERNAL/FAILED_GONE)与 guardian 三证删链用例随整链退役 —— 新对账表(wait/rebuild/
verify 三动作, 判据面 ru.reconcile 纯函数层在 test_relocate_units)与 ACT_ENSURE_DAEMON
接线在本文件; journal rewritten 镜像合并(armed -> rewritten 只前进)是新链对账的第一拍。

## 测试计划(每个测试函数一条)
### 对账处置(relocate_exec._apply_reconcile)
- test_apply_reconcile_unknown_action_is_debug_only: 未知对账动作只落 DEBUG, 不改 job
- test_rebuild_backoff_blocks_within_window: 退避窗口内不重建(旧实现每 1-2 tick 一轮建删)
- test_rebuild_capped_then_failed_keeps_scene: 重建达上限 ⇒ failed 留现场(不再永不终态)
- test_apply_reconcile_rebuild_faces: 重建退避账/stage 值/journal 回滚 armed/rebuild_exhausted 文案
- test_rebuild_first_attempt_not_backoff_on_fresh_boot: 开机窗口 —— monotonic < REBUILD_BACKOFF 时首次重建不得被 0.0 哨兵退避吞掉(issue 26-10-31-0932)
- test_apply_reconcile_verify_hangs_benign: ACT_VERIFY 接线 —— 核验不过 = 良性悬挂, rewritten 不推进不判 failed(S4a 退役 FAILED_TIMEOUT), 账留 verify_failed 供反馈面
### journal 镜像合并(_step_reconcile)
- test_step_reconcile_merges_rewritten_forward: armed + journal rewritten -> 跟进 rewritten; rewritten + 旧 journal 相位 -> 不回退
- test_step_reconcile_same_journal_phase_no_remerge: 相位一致 -> 不重复落账, 对账照常走完
### journal failed 相位消费(issue 26-11-07-0527 #3: 对账表消费 failed 相位)
- test_step_reconcile_consumes_failed_journal_to_failed_terminal: 对账读到 journal failed
  (证据可信) => job 转 failed 终态 + 证据原文保留 reason/last_error + journal 终相位不被
  重写 + 本拍不再判 daemon 重拉(消费先于重拉)
- test_failed_journal_consume_idempotent_on_reentry: 幂等 —— 消费后再入(含拿旧非终端对象
  直接再入)不重复写 state/不重复记因
- test_suspect_failed_journal_parks_without_terminal: 保守支 —— 证据形态可疑不转终态,
  WARNING 一次(rt 门), 不推进不重拉
- test_stale_failed_journal_cleared_and_daemon_reclaimed: 陈旧支(评审 finding 1)—— ts
  早于本生命周期锚点(上一世残留)主循环清账(删前证据留痕行 + 删后结果行)+ 本拍恢复
  常规对账与 daemon 重拉判据(残留不清则再迁移死锁在 armed)
- test_stale_failed_journal_clear_failure_parks_tick_and_gates_warning: 清账失败
  (r2-finding 2)—— WARNING 限频一次 + 失败拍直接收口(不重评常规表不重拉), 下拍原样重试
- test_reinitiation_after_consumed_failure_reclaims_daemon: 消费支再发起路径 —— 消费转
  终态后重发起同 id 迁移, 新生命周期把上一世失败账判陈旧清掉, daemon 重拉恢复
### S3 接线(计划 26-11-05-0808 §3.2/S3: spec 双字段 + ACT_ENSURE_DAEMON, 全替身不起真进程)
- test_write_arm_spec_bt_backup_and_members: 实例命中 bt_backup 表 -> spec 写 bt_backup +
  members 双 hash(<hash>.torrent 现算 v2); 未命中 -> 不写 bt_backup(警告降级);
  v2-only/缺 torrent 回落不猜命名
- test_ensure_daemon_spawn_matrix: 死/缺位 -> 重拉 + rt 记账; DAEMON_RESPAWN_BACKOFF 内
  不重复拉; daemon 健康在位 -> 不拉; 无 bt_backup spec / 终态 job -> 不拉
- test_step_reconcile_wires_ensure_daemon: 对账 tick 每拍顺带判新动作
- test_ensure_daemon_logs_and_throttle_ledger: 重拉审计日志 + 退避账键
- test_qb_host_port_and_arm_spec_pinned: qB host/port 读配置 + arm spec 关键键值
### 武装接线(_arm)
- test_arm_writes_spec_and_ensures_daemon: arm -> spec 落盘 + ensure_daemon 重拉 + 恢复运行态
### arm 侧上一世终态账重置(issue 26-11-08-0827)
- test_arm_resets_stale_terminal_journal_of_previous_life: done/cancelled 残留(ts 早于新
  created_at)在 _arm 入口清掉(删前证据留痕 + 删后结果行), 武装照常推进(armed + spec + 重拉)
- test_arm_stale_terminal_clear_failure_parks_and_retries: 清账失败 WARNING 限频一次 +
  本拍不武装不写 spec 不重拉, 解除后下拍原样重试成
- test_arm_terminal_journal_not_provable_stale_parks_conservatively: 锚定不上(终态账 ts
  不早于本世锚点)保守不清账不武装留人工, 绝不把存疑账当残留误删
- test_arm_keeps_live_nonterminal_journal: 在途非终态账(本世 rebuild 再武装)不属本口,
  不删不动, 武装照常
- test_arm_unreadable_journal_parks_and_retries: 文件在位但读不出(读失败被吞成 None,
  评审 finding 1)与账不存在不可混淆 —— 存疑搁置不武装 WARNING 限频一次, 恢复后下拍重试成

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_tag_name_without_config_is_empty: relocate 配置段缺席 -> 待收尾标签名空串
- test_ensure_daemon_spawn_failure_warns_and_still_throttles: 拉起失败只告警 + 退避账键照记
- test_penetrate_stage_without_aliases_goes_straight_to_arm: penetrate 无别名直进武装
"""

import os

import time

import types

from dataclasses import replace

import pytest

from auto_qb.core.modules import relocate_units as ru

from clock import FakeClock

from auto_qb.infra import relocate_journal

from helpers import pin_disk_usage, relocate_env

from helpers import capture_logs

from relocate_exec_support import (
    _armed_env,
    _bare_mod,
    _job,
    _run_ticks,
    _simulate_moved,
    _spy_spawn,
)

# ---------------------------------------------------------------- 对账处置


def test_apply_reconcile_unknown_action_is_debug_only(tmp_path):
    """未知对账动作只落一条 DEBUG(不推进相位, 不炸)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._apply_reconcile(_job(phase=ru.PHASE_ARMED), {}, "some-new-action")
    assert mod._jobs.get("j1") is None, "未知动作不得改 job"


def test_rebuild_backoff_blocks_within_window(tmp_path, monkeypatch):
    """重建退避: 距上次重建不足 REBUILD_BACKOFF ⇒ 本轮跳过(旧实现每 1-2 tick 一轮建删)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    calls = []
    monkeypatch.setattr(mod, "_build_links", lambda j, rt: calls.append(j.job_id) or True)
    rt = {"rebuild_ts": time.monotonic()}  # 刚重建过
    mod._apply_reconcile(_job("j1", phase=ru.PHASE_ARMED), rt, ru.ACT_REBUILD)
    assert calls == [], f"退避窗口内不得重建: {calls}"
    rt["rebuild_ts"] = time.monotonic() - ru.REBUILD_BACKOFF - 1.0
    mod._apply_reconcile(_job("j2", phase=ru.PHASE_ARMED), rt, ru.ACT_REBUILD)
    assert calls == ["j2"], f"退避窗口外应放行重建: {calls}"


def test_rebuild_capped_then_failed_keeps_scene(tmp_path):
    """重建达 attempts 上限 ⇒ failed(rebuild_exhausted) 留现场, 不再无限 create-fail-delete

    建链必失败的环境(权限不足 / 未开开发者模式且 allow_uac 关)里旧实现永不终态。
    """
    mod = _bare_mod(data_dir=str(tmp_path))
    job = _job(phase=ru.PHASE_ARMED, attempts=ru.REBUILD_MAX_ATTEMPTS)
    mod._apply_reconcile(job, {}, ru.ACT_REBUILD)
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "rebuild_exhausted", (saved.phase, saved.reason)
    assert saved.attempts == ru.REBUILD_MAX_ATTEMPTS, "保留重试次数供排查(不抹掉现场)"


def test_apply_reconcile_rebuild_faces(tmp_path, monkeypatch):
    """重建面: 退避账落正确键(ar_57~59)/stage 值(ar_64/65/101/102)/journal 回滚 armed/
    rebuild_exhausted 文案(ar_38/41/45/46)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    calls = []
    monkeypatch.setattr(mod, "_build_links", lambda job, rt: calls.append(job.job_id) or len(calls) == 2)
    dd = str(tmp_path)
    relocate_journal.write_journal(dd, "j1", {"phase": ru.PHASE_ARMED, "ts": time.time()})
    rt = {}
    mod._apply_reconcile(_job("j1", phase=ru.PHASE_ARMED), rt, ru.ACT_REBUILD)
    assert calls == ["j1"], calls
    assert rt["stage"] == "link", rt  # 重建入口 stage(坏值 = 相位机滞留 MOVED)
    assert rt["rebuild_ts"] > 0, rt  # 退避账(丢失 = 瞬态故障连击)
    assert relocate_journal.read_journal(dd, "j1")["phase"] == ru.PHASE_ARMED, "重建必须把 journal 退回 armed"

    mod._apply_reconcile(_job("j2", phase=ru.PHASE_ARMED), rt, ru.ACT_REBUILD)
    assert calls == ["j1"], f"退避窗口内不得重建: {calls}"

    rt2 = {}
    mod._apply_reconcile(_job("j3", phase=ru.PHASE_ARMED), rt2, ru.ACT_REBUILD)
    assert calls == ["j1", "j3"], calls
    assert rt2["stage"] == "penetrate", rt2

    # 达上限: failed 文案逐字(attempts 计数不得 or 1 化)
    mod2 = _bare_mod(data_dir=str(tmp_path))
    mod2._apply_reconcile(_job("j9", phase=ru.PHASE_ARMED, attempts=ru.REBUILD_MAX_ATTEMPTS), {}, ru.ACT_REBUILD)
    saved = mod2._jobs["j9"]
    assert (saved.phase, saved.reason) == (ru.PHASE_FAILED, "rebuild_exhausted"), (saved.phase, saved.reason)
    assert saved.last_error == "重建别名已失败 3 次(上限 3) —— 保留现场交人处理: 通常是权限不足, 修好后重新发起即可", \
        saved.last_error

    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._apply_reconcile(_job("j4", phase=ru.PHASE_ARMED), {}, ru.ACT_REBUILD)
    assert any("重建别名" in m for m in cap.messages), cap.messages


def test_rebuild_first_attempt_not_backoff_on_fresh_boot(tmp_path, monkeypatch):
    """开机窗口: monotonic < REBUILD_BACKOFF 时首次重建不得被退避吞掉(issue 26-10-31-0932)

    rt 里没有 rebuild_ts = 「从未重建」, 不是「开机那一刻重建过」; 旧实现拿 0.0 兜底,
    而 monotonic() 0 点是开机时刻, 开机不满 300s 的机器上退避判据恒真, 重建被静默跳过。
    """
    pin_disk_usage(monkeypatch)
    # 构造期注入(S3 收敛: 不再进程级 patch stdlib time.monotonic): 模拟开机 2 分钟
    boot_clock = FakeClock(start=120.0)
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch, clock=boot_clock)
    mod._qb_up = lambda: True
    mod._remove_links(mod.get_job(job_id).alias_paths)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = src
        mgr.store.by_hash[h].state = "pausedUP"

    _run_ticks(mod, 4)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason)
    for p in job.alias_paths:
        assert os.path.exists(p), p


def test_apply_reconcile_verify_hangs_benign(tmp_path):
    """ACT_VERIFY 接线(_step_verify 单点): 核验不过 = 良性悬挂 —— rewritten 不推进不判
    failed(S4a 退役 FAILED_TIMEOUT), 账上留 verify_failed 供反馈面(全量核验/删链面在
    test_relocate_exec_verify)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    job = _job(phase=ru.PHASE_REWRITTEN, alias_paths=("R:/src/l", ))
    mod.register_job(job)
    mod._apply_reconcile(job, {}, ru.ACT_VERIFY)
    saved = mod._jobs.get("j1")
    assert saved is not None and not saved.is_terminal, saved
    assert saved.reason == ru.REASON_VERIFY_FAILED, saved.reason


# ---------------------------------------------------------------- journal 镜像合并(_step_reconcile)


def test_step_reconcile_merges_rewritten_forward(tmp_path):
    """journal rewritten 镜像合并(D13): armed -> rewritten 只前进; 旧 journal 相位不回退

    daemon 翻 journal 相位 => 主循环把 job 镜像跟进 rewritten(唯一合并方向); job 已在
    rewritten 而 journal 还是旧 armed 心跳账 => 不得降级(前向合并单向)。
    """
    rec = types.SimpleNamespace(hash="HA", save_path="R:/src", state="pausedUP")

    def _mk(store_rec=None):
        store = types.SimpleNamespace(by_hash={"HA": store_rec or rec}, relocating_hashes=set())
        return _bare_mod(store=store, api=types.SimpleNamespace(client=None), data_dir=str(tmp_path))

    mod = _mk()
    relocate_journal.write_journal(str(tmp_path), "j1", {"phase": ru.PHASE_REWRITTEN, "ts": 1.0})
    mod._step_reconcile(_job("j1", phase=ru.PHASE_ARMED), {})
    assert mod.get_job("j1").phase == ru.PHASE_REWRITTEN, "rewritten 必须合并进 job 镜像"

    mod2 = _mk()
    mod2.register_job(_job("j2", phase=ru.PHASE_REWRITTEN))
    relocate_journal.write_journal(str(tmp_path), "j2", {"phase": ru.PHASE_ARMED, "ts": 2.0})
    mod2._step_reconcile(mod2.get_job("j2"), {})
    assert mod2.get_job("j2").phase == ru.PHASE_REWRITTEN, "旧 journal 相位不得把 rewritten 拉回去"


def test_step_reconcile_same_journal_phase_no_remerge(tmp_path):
    """(T2b)job 已在 rewritten(与 journal 同相) -> 不重复落账(_set_job 不被调), 对账照常
    走完; armed + 旧 journal 相位 -> 不合并(旧相位不在新表合并集)"""
    rec = types.SimpleNamespace(hash="HA", save_path="R:/src", state="pausedUP")
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._ctx.store = types.SimpleNamespace(by_hash={"HA": rec}, relocating_hashes=set())
    relocate_journal.write_journal(str(tmp_path), "j1", {"phase": ru.PHASE_REWRITTEN, "ts": 1.0})
    job = _job("j1", phase=ru.PHASE_REWRITTEN)
    mod._step_reconcile(job, {})
    assert mod._jobs == {}, "同相位不得重复落账"


# ---------------------------------------------------------------- journal failed 相位消费(issue 26-11-07-0527 #3)
# 收尾校验失败写下的 journal 相位 failed 必须被对账收敛: 消费转 failed 终态(证据保留)/
# 可疑保守搁置/陈旧残留落回常规表; 三态都不再判 daemon 重拉(STOP_PHASES 扩展后 failed
# 相位对 daemon 退休, 重拉只会空转 —— 证据消费必须先于任何重拉动作)。


def _failed_journal_env(tmp_path, journal_body, **job_kw):
    """failed 相位消费用环境: spec 带 bt_backup(pending 非空, 若无闸门 _ensure_daemon 会
    真重拉)+ journal 落盘 + armed job 登记 + _spawn_daemon 替身。返回 (mod, job, spawned)。"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    _write_new_chain_spec(data_dir, "j1", host, port, backup, v1)
    base = {
        "phase": ru.PHASE_ARMED,
        "hashes": (v1, ),
        "armed_at": 100.0,
        "created_at": 50.0,
    }
    base.update(job_kw)
    job = _job("j1", **base)
    mod.register_job(job)
    relocate_journal.write_journal(data_dir, "j1", dict(journal_body))
    spawned = []
    mod._spawn_daemon = lambda d, h, p: spawned.append((d, h, p))
    return mod, job, spawned


def test_step_reconcile_consumes_failed_journal_to_failed_terminal(tmp_path):
    """消费支(拍板方向): 对账读到 journal failed(证据可信: reason + ts 不早于 armed_at)
    => job 转 failed 终态(_fail 单点), 证据原文保留进 reason/last_error; journal 本身就是
    终相位(STOP_PHASES 已纳 failed), 不被重写; 本拍不再判 daemon 重拉(消费先于重拉)"""
    mod, job, spawned = _failed_journal_env(tmp_path, {
        "phase": "failed",
        "reason": "verify_mismatch",
        "ts": 150.0,
    })
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_reconcile(job, {})
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_FAILED and saved.is_terminal, (saved.phase, saved.reason)
    assert saved.reason == "verify_mismatch", "失败原因原文必须保留(不丢证据)"
    assert "journal 相位 failed" in saved.last_error and "verify_mismatch" in saved.last_error, saved.last_error
    j = relocate_journal.read_journal(str(tmp_path / "data"), "j1")
    assert j["phase"] == "failed" and j["reason"] == "verify_mismatch", "终相位 journal 不被重写(证据留存)"
    assert spawned == [], f"failed 相位不再判重拉: {spawned}"
    assert any("收尾校验失败" in m for m in cap.messages), cap.messages


def test_failed_journal_consume_idempotent_on_reentry(tmp_path):
    """幂等(黄金法则 1): 消费后对账再入(含拿着旧非终端 job 对象的直接再入)不重复写
    state/不重复记因 —— 终态闸以账上现值为准"""
    mod, job, spawned = _failed_journal_env(tmp_path, {
        "phase": "failed",
        "reason": "verify_mismatch",
        "ts": 150.0,
    })
    mod._step_reconcile(job, {})
    first = ru.job_to_dict(mod.get_job("j1"))
    assert first["phase"] == ru.PHASE_FAILED
    # 直接再入: 主动画传旧的非终端 armed 对象(active_jobs 已滤终态, 生产不会; 防御面钉死)
    mod._step_reconcile(job, {})
    mod._apply_reconcile(job, {}, ru.ACT_FAIL_TERMINAL)
    assert ru.job_to_dict(mod.get_job("j1")) == first, "重复消费不得改账(无重复副作用)"
    assert spawned == [], spawned


def test_suspect_failed_journal_parks_without_terminal(tmp_path):
    """保守支: failed 相位但证据形态可疑(reason/ts 缺失) => 不转终态、不推进、不重拉,
    WARNING 一次(rt 门, 对账每拍都来不设门会刷屏); 换 job 重开 rt 后再警一次"""
    mod, job, spawned = _failed_journal_env(tmp_path, {"phase": "failed"})
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_reconcile(job, rt)
        mod._step_reconcile(mod.get_job("j1"), rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_ARMED and not saved.is_terminal, (saved.phase, saved.reason)
    assert saved.reason == "" and saved.last_error == "", "可疑证据不得写进账(留人工, 不误判终态)"
    assert rt.get("journal_failed_suspect_warned") is True, rt
    warns = [m for m in cap.messages if "证据形态可疑" in m]
    assert len(warns) == 1, f"同 job 只警一次: {warns}"
    assert spawned == [], f"可疑支同样不重拉: {spawned}"


def test_stale_failed_journal_cleared_and_daemon_reclaimed(tmp_path):
    """陈旧支(评审 finding 1 修正): failed 但 ts 早于本生命周期锚点(同 job_id 上一世残留)
    => 主循环清账(删前证据留痕行 + 删后结果行), 本拍起恢复常规对账与 daemon 重拉判据
    —— 残留账不清, failed 入 STOP_PHASES 后 daemon 对该 id 永久退休, 再迁移死锁在 armed"""
    mod, job, spawned = _failed_journal_env(
        tmp_path,
        {
            "phase": "failed",
            "reason": "verify_mismatch",
            "ts": 10.0,
        },
        created_at=1000.0,
        armed_at=0.0,
    )
    data_dir = str(tmp_path / "data")
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_reconcile(job, rt)
    assert relocate_journal.read_journal(data_dir, "j1") is None, "陈旧失败账必须被清掉(解除 daemon 退休)"
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_ARMED and not saved.is_terminal, (saved.phase, saved.reason)
    assert spawned == [(data_dir, mod._qb_host(), mod._qb_port())], f"清账后重拉判据恢复: {spawned}"
    # 证据契约(r2-finding 1): reason/ts 证据行删除前落盘, 结果行删后另记
    evidence = [m for m in cap.messages if "证据留痕" in m]
    assert any("j1" in m and "verify_mismatch" in m and "ts=10.0" in m for m in evidence), cap.messages
    assert any("已清理陈旧失败账" in m for m in cap.messages), cap.messages
    assert not any("收尾校验失败" in m or "证据形态可疑" in m for m in cap.messages), cap.messages
    # 下一拍: 账已不在, 常规对账照走; 重拉退避生效不重复拉
    mod._step_reconcile(mod.get_job("j1"), rt)
    assert len(spawned) == 1, spawned


def test_stale_failed_journal_clear_failure_parks_tick_and_gates_warning(tmp_path, monkeypatch):
    """清账失败(r2-finding 2): WARNING 限频一次, 且失败拍直接收口 —— 不重评常规表不重拉
    (journal 仍 failed, daemon 尚未解除退休, 空拉与「下拍对账重试」文案矛盾); 账不消失,
    下拍对账原样重试"""
    mod, job, spawned = _failed_journal_env(
        tmp_path,
        {
            "phase": "failed",
            "reason": "verify_mismatch",
            "ts": 10.0,
        },
        created_at=1000.0,
        armed_at=0.0,
    )
    monkeypatch.setattr(relocate_journal, "clear_journal", lambda d, jid: False)
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_reconcile(job, rt)
        mod._step_reconcile(mod.get_job("j1"), rt)
    assert relocate_journal.read_journal(str(tmp_path / "data"), "j1") is not None, "清账失败账不消失"
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_ARMED and not saved.is_terminal, (saved.phase, saved.reason)
    assert spawned == [], f"清账失败拍不得重拉(journal 仍 failed): {spawned}"
    warns = [m for m in cap.messages if "清理失败" in m]
    assert len(warns) == 1, f"清理失败 WARNING 限频一次: {warns}"
    evidence = [m for m in cap.messages if "证据留痕" in m]
    assert len(evidence) == 1, f"证据留痕行同样限频: {evidence}"


def test_reinitiation_after_consumed_failure_reclaims_daemon(tmp_path):
    """消费支再发起路径(评审 finding 1 第二半): 消费转 failed 终态后用户重发起同 id 迁移
    => 新生命周期对账把上一世失败账判陈旧清掉, daemon 重拉恢复 —— 「排除故障后可重新
    发起迁移」的承诺成立, 不死锁在 armed"""
    mod, job, spawned = _failed_journal_env(
        tmp_path,
        {
            "phase": "failed",
            "reason": "verify_mismatch",
            "ts": 150.0,
        },
    )
    mod._step_reconcile(job, {})
    assert mod.get_job("j1").is_terminal, "本世失败账先消费为前置"
    data_dir = str(tmp_path / "data")
    # 重发起: 同 job_id 新生命周期(登记覆盖旧条目是既有语义), 上一世账 ts 早于新 created_at
    fresh = _job("j1", phase=ru.PHASE_ARMED, hashes=job.hashes, armed_at=500.0, created_at=400.0)
    mod.register_job(fresh)
    mod._step_reconcile(fresh, {})
    assert relocate_journal.read_journal(data_dir, "j1") is None, "上一世失败账按陈旧清掉"
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_ARMED and not saved.is_terminal, (saved.phase, saved.reason)
    assert len(spawned) == 1, f"新生命周期 daemon 重拉恢复: {spawned}"


# ---------------------------------------------------------------- S3 接线(计划 26-11-05-0808 §3.2/S3)
# spec 双字段(bt_backup/members)与 ACT_ENSURE_DAEMON 处置; 全替身, 不起真进程。


def _torrent_fixture(backup, tag: bytes, old_root: str):
    """BT_backup 造一个真实 torrent(同 test_recycle_daemon 造法): 返回 (v1, v2)"""
    from auto_qb.core import fastresume as frmod
    from auto_qb.hr.bencode import compute_infohashes

    info = {b"name": tag, b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    torrent = frmod.bencode({b"announce": b"http://t/ann", b"info": info})
    v1, v2, _ = compute_infohashes(torrent)
    backup.mkdir(parents=True, exist_ok=True)
    (backup / f"{v1}.torrent").write_bytes(torrent)
    return v1, v2


def _s3_mod(tmp_path, host="h1", port=1234, backup=None):
    """S3 接线用裸模块: config 带 qbittorrent 身份 + relocate.bt_backup 标量(替身属性全数据侧)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.config.qbittorrent = types.SimpleNamespace(host=host, port=port)
    if backup is not None:
        mod._ctx.config.relocate.bt_backup = str(backup)
    return mod


def test_write_arm_spec_bt_backup_and_members(tmp_path):
    """arm 侧 spec 双字段接线(单点 _write_arm_spec): 实例命中 bt_backup 表 -> 写字段 +
    members 双 hash(<hash>.torrent 现算 v2); 未命中 -> 不写 bt_backup(S1 五闸外形态,
    警告降级不静默); v2-only/缺 torrent 各回落不猜"""
    backup = tmp_path / "BT_backup"
    v1, v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    assert mod._write_arm_spec(job) is True
    spec = relocate_journal.read_spec(str(tmp_path / "data"), "j1")
    assert spec["bt_backup"] == str(backup), spec
    assert spec["members"] == [{"hash_v1": v1, "hash_v2": v2}], spec["members"]

    # 未命中表: 不写 bt_backup 字段 + 警告(job 停 armed 等人工, 不静默丢收尾)
    mod2 = _s3_mod(tmp_path)
    job2 = _job("j2", phase=ru.PHASE_ARMED, hashes=(v1, "f" * 40))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        assert mod2._write_arm_spec(job2) is True
    spec2 = relocate_journal.read_spec(str(tmp_path / "data"), "j2")
    assert "bt_backup" not in spec2, spec2
    assert spec2["members"] == [
        {
            "hash_v1": v1,
            "hash_v2": ""
        },
        {
            "hash_v1": "f" * 40,
            "hash_v2": ""
        },
    ], spec2["members"]
    assert any("bt_backup 未配置" in m for m in cap.messages), cap.messages

    # v2-only(qB hash 即 v2 infohash): torrent 文件名按 v2 命名, 成员 hash_v1 位携带该 v2
    backup3 = tmp_path / "BT3"
    info = {b"name": b"v2only", b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    from auto_qb.core import fastresume as frmod
    from auto_qb.hr.bencode import compute_infohashes

    torrent = frmod.bencode({b"announce": b"http://t/ann", b"info": info})
    tv1, tv2, _ = compute_infohashes(torrent)
    backup3.mkdir(parents=True, exist_ok=True)
    (backup3 / f"{tv2}.torrent").write_bytes(torrent)
    mod3 = _s3_mod(tmp_path, backup=backup3)
    mod3._ctx.config.relocate.bt_backup = str(backup3)
    job3 = _job("j3", phase=ru.PHASE_ARMED, hashes=(tv2, ))
    assert mod3._write_arm_spec(job3) is True
    spec3 = relocate_journal.read_spec(str(tmp_path / "data"), "j3")
    assert spec3["members"] == [{"hash_v1": tv2, "hash_v2": ""}], spec3["members"]

    # 缺 .torrent: hash_v2 留空不猜(消费侧 locate 兜底扫描仍可命中)
    mod4 = _s3_mod(tmp_path, backup=backup)
    job4 = _job("j4", phase=ru.PHASE_ARMED, hashes=("e" * 40, ))
    assert mod4._write_arm_spec(job4) is True
    spec4 = relocate_journal.read_spec(str(tmp_path / "data"), "j4")
    assert spec4["members"] == [{"hash_v1": "e" * 40, "hash_v2": ""}], spec4["members"]


def _write_new_chain_spec(data_dir, job_id, host, port, backup, v1):
    relocate_journal.write_spec(
        data_dir, job_id, {
            "job_id": job_id,
            "src": "R:/src",
            "dst": "R:/dst",
            "hashes": [v1],
            "host": host,
            "port": port,
            "bt_backup": str(backup),
            "members": [{
                "hash_v1": v1,
                "hash_v2": ""
            }],
        }
    )


def test_ensure_daemon_spawn_matrix(tmp_path):
    """ACT_ENSURE_DAEMON 处置矩阵: spec 带 bt_backup + pending 非空 + 无 daemon 责 -> 重拉 +
    rt 记账; DAEMON_RESPAWN_BACKOFF 内不重复拉(独立 rt 键); daemon 健康在位 -> 不拉
    (至多一个 watcher); 无 bt_backup spec / 终态 job -> 不拉"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    _write_new_chain_spec(data_dir, "j1", host, port, backup, v1)
    spawned = []
    mod._spawn_daemon = lambda d, h, p: spawned.append((d, h, p))

    # 死/缺位(daemon.json 无记录 => daemon_stale) -> 重拉 + rt 记账
    rt = {}
    mod._ensure_daemon(job, rt)
    assert spawned == [(data_dir, host, port)], spawned
    assert "ensure_daemon_ts" in rt, rt

    # 退避窗口内不重复拉(每 tick 对账, 无节流就是每 tick 一个进程)
    mod._ensure_daemon(job, rt)
    assert len(spawned) == 1, spawned

    # 健康在位(pid 活 + 心跳新鲜) -> 不拉(不重复拉起, D12)
    spawned.clear()
    key = relocate_journal.instance_key(host, port)
    relocate_journal.write_daemon_state(data_dir, key, os.getpid(), host=host, port=port)
    mod._ensure_daemon(job, {})
    assert spawned == [], spawned

    # 无 bt_backup spec(五闸外形态): 不白造进程
    spawned.clear()
    relocate_journal.release_daemon_state(data_dir, key, os.getpid())
    relocate_journal.write_spec(
        data_dir, "j1", {
            "job_id": "j1",
            "src": "R:/src",
            "dst": "R:/dst",
            "hashes": [v1],
            "host": host,
            "port": port,
            "members": [{
                "hash_v1": v1,
                "hash_v2": ""
            }],
        }
    )
    mod._ensure_daemon(job, {})
    assert spawned == [], spawned

    # 终态 job: 无动作
    _write_new_chain_spec(data_dir, "j1", host, port, backup, v1)
    mod._ensure_daemon(replace(job, phase=ru.PHASE_DONE), {})
    assert spawned == [], spawned


def test_step_reconcile_wires_ensure_daemon(tmp_path):
    """对账 tick 接线: _step_reconcile 每拍顺带判 ACT_ENSURE_DAEMON(本现场对账判 WAIT,
    新判据独立触发重拉)"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    rec = types.SimpleNamespace(hash=v1, save_path="R:/src", state="pausedUP")
    mod._ctx.store = types.SimpleNamespace(by_hash={v1: rec}, relocating_hashes=set())
    _write_new_chain_spec(data_dir, "j1", host, port, backup, v1)
    spawned = []
    mod._spawn_daemon = lambda d, h, p: spawned.append((d, h, p))
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    rt = {}
    mod._step_reconcile(job, rt)
    assert spawned == [(data_dir, host, port)], spawned
    # 退避生效: 下一拍不再拉
    mod._step_reconcile(job, rt)
    assert len(spawned) == 1, spawned


def test_ensure_daemon_logs_and_throttle_ledger(tmp_path):
    """重拉审计 + 退避账键(ensure_daemon_ts 独立账, 丢失 = 每 tick 空拉一次进程)"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    _write_new_chain_spec(data_dir, "j1", host, port, backup, v1)
    mod._spawn_daemon = lambda d, h, p: None
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._ensure_daemon(job, rt)
    assert any("回收 daemon" in m and "重拉" in m for m in cap.messages), cap.messages
    assert rt["ensure_daemon_ts"] > 0, rt


# ---------------------------------------------------------------- 武装接线(_arm)


def test_arm_writes_spec_and_ensures_daemon(tmp_path, monkeypatch):
    """arm -> spec 落盘 + ensure_daemon 重拉(回收 daemon 接管收尾, 旧 guardian spawn 退役)"""
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    mod._ctx.api = types.SimpleNamespace(torrents_resume=lambda **kw: None)
    spawned = []
    mod._spawn_daemon = lambda d, h, p: spawned.append((d, h, p))
    job = _job("j1", phase=ru.PHASE_MOVED, hashes=(v1, ), resume_hashes=(v1, ))
    rt = {}
    mod._arm(job, rt)
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_ARMED, saved.phase
    spec = relocate_journal.read_spec(str(tmp_path / "data"), "j1")
    assert spec is not None and spec["bt_backup"] == str(backup), spec
    assert "ensure_daemon_ts" in rt, "arm 必须立即 ensure daemon(pending 非空 + 无 daemon 账)"
    assert spawned, spawned


# ---------------------------------------------------------------- arm 侧上一世终态账重置(issue 26-11-08-0827)
# job_id=sha1(mover|src|dst) 同组同目标再发起复用同 id: 上一世 done/cancelled 终态账不清,
# daemon 因 STOP_PHASES 退休 + write_journal 前向合并拒新世记账, 新迁移收不到 fastresume
# 改写。重置挂 _arm 入口(对账陈旧支只覆盖 failed 相位, done/cancelled 无裁决面), 守卫
# 复用 clear_journal 既有协议(确证属上一世才删: 相位终态 + ts 早于本世 created_at)。


def _arm_reset_env(tmp_path, journal_body, created_at=1000.0):
    """arm 重置用环境: bt_backup 命中 + 替身 spawn/resume + 可选 journal 落盘。
    返回 (mod, job, spawned, data_dir, (host, port))。"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    mod._ctx.api = types.SimpleNamespace(torrents_resume=lambda **kw: None)
    spawned = []
    mod._spawn_daemon = lambda d, h, p: spawned.append((d, h, p))
    job = _job("j1", phase=ru.PHASE_MOVED, hashes=(v1, ), resume_hashes=(v1, ), created_at=created_at)
    if journal_body is not None:
        relocate_journal.write_journal(data_dir, "j1", dict(journal_body))
    return mod, job, spawned, data_dir, (host, port)


@pytest.mark.parametrize("phase", ["done", "cancelled"])
def test_arm_resets_stale_terminal_journal_of_previous_life(tmp_path, phase):
    """done/cancelled 残留(ts 早于新 created_at)在 _arm 入口清掉(删前证据留痕 + 删后结果行),
    武装照常推进 —— 残留不清则 daemon 因 STOP_PHASES 退休, 新迁移收不到 fastresume 改写
    (数据不在目标位则悬挂, issue 26-11-08-0827)"""
    mod, job, spawned, data_dir, (host,
                                  port) = _arm_reset_env(tmp_path, {
                                      "phase": phase,
                                      "reason": "old-life",
                                      "ts": 10.0
                                  })
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._arm(job, {})
    assert relocate_journal.read_journal(data_dir, "j1") is None, "上一世终态账必须在武装前清掉"
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_ARMED, saved.phase
    assert spawned == [(data_dir, host, port)], spawned
    evidence = [m for m in cap.messages if "证据留痕" in m]
    assert any("j1" in m and phase in m and "old-life" in m and "ts=10.0" in m for m in evidence), cap.messages
    assert any("已重置上一世终态账" in m for m in cap.messages), cap.messages


def test_arm_stale_terminal_clear_failure_parks_and_retries(tmp_path, monkeypatch):
    """清账失败(盘/权限): WARNING 限频一次 + 本拍不武装(不落账不写 spec 不重拉,
    journal 仍终态 daemon 未解除退休); 解除后下拍原样重试成(rt["stage"] 保持 arm,
    stage 机下拍再进 _arm)"""
    mod, job, spawned, data_dir, _hp = _arm_reset_env(tmp_path, {"phase": "done", "ts": 10.0})
    real_clear = relocate_journal.clear_journal
    monkeypatch.setattr(relocate_journal, "clear_journal", lambda d, jid: False)
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._arm(job, rt)
        mod._arm(job, rt)
    assert relocate_journal.read_journal(data_dir, "j1") is not None, "清账失败账不消失"
    assert "j1" not in mod._jobs, "未清成不得武装"
    assert relocate_journal.read_spec(data_dir, "j1") is None, "未清成不得写 spec"
    assert spawned == [], f"未清成不得重拉(journal 仍终态): {spawned}"
    warns = [m for m in cap.messages if "重置失败" in m]
    assert len(warns) == 1, f"重置失败 WARNING 限频一次: {warns}"
    evidence = [m for m in cap.messages if "证据留痕" in m]
    assert len(evidence) == 1, f"证据留痕行同样限频: {evidence}"
    # 解除后下拍重试成
    monkeypatch.setattr(relocate_journal, "clear_journal", real_clear)
    mod._arm(job, rt)
    assert relocate_journal.read_journal(data_dir, "j1") is None
    assert mod._jobs["j1"].phase == ru.PHASE_ARMED
    assert len(spawned) == 1, spawned


def test_arm_terminal_journal_not_provable_stale_parks_conservatively(tmp_path):
    """锚定不上(终态账 ts 不早于本世 created_at): 保守不清账不武装, WARNING 一次留人工
    —— 绝不把存疑账当残留误删(黄金法则 2; 机制上不可达, 真发生 = 现场存疑)"""
    mod, job, spawned, data_dir, _hp = _arm_reset_env(tmp_path, {"phase": "done", "ts": 2000.0})
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._arm(job, rt)
        mod._arm(job, rt)
    j = relocate_journal.read_journal(data_dir, "j1")
    assert j is not None and j["phase"] == "done", "存疑账不得误删"
    assert "j1" not in mod._jobs and spawned == [], "锚定不上不武装不重拉"
    warns = [m for m in cap.messages if "无法确证属上一世" in m]
    assert len(warns) == 1, f"WARNING 限频一次: {warns}"


def test_arm_keeps_live_nonterminal_journal(tmp_path):
    """在途非终态账(本世 rebuild 再武装的 journal rewritten)不属本口: 不删不动, 武装照常"""
    mod, job, spawned, data_dir, _hp = _arm_reset_env(tmp_path, {"phase": ru.PHASE_REWRITTEN, "ts": 1500.0})
    mod._arm(job, {})
    j = relocate_journal.read_journal(data_dir, "j1")
    assert j is not None and j["phase"] == ru.PHASE_REWRITTEN, "在途账不得清"
    assert mod._jobs["j1"].phase == ru.PHASE_ARMED
    assert len(spawned) == 1, spawned


def test_arm_unreadable_journal_parks_and_retries(tmp_path, monkeypatch):
    """文件在位但读不出(评审 finding 1): 读失败被读单点吞成 None, 与「账不存在」不可混淆
    —— 存疑搁置不武装(WARNING 限频一次), 读恢复后下拍原样重试成; 账本体不动"""
    mod, job, spawned, data_dir, _hp = _arm_reset_env(tmp_path, journal_body=None)
    real_read = relocate_journal.read_journal
    relocate_journal.write_journal(data_dir, "j1", {"phase": "done", "ts": 10.0})
    monkeypatch.setattr(relocate_journal, "read_journal", lambda d, jid: None)
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._arm(job, rt)
        mod._arm(job, rt)
    assert "j1" not in mod._jobs and spawned == [], "读不出不武装"
    assert os.path.exists(relocate_journal.journal_path(data_dir, "j1")), "存疑账本体不动"
    warns = [m for m in cap.messages if "读不出" in m]
    assert len(warns) == 1, f"WARNING 限频一次: {warns}"
    # 读恢复后下拍重试成
    monkeypatch.setattr(relocate_journal, "read_journal", real_read)
    mod._arm(job, rt)
    assert relocate_journal.read_journal(data_dir, "j1") is None, "上一世终态账清掉"
    assert mod._jobs["j1"].phase == ru.PHASE_ARMED
    assert len(spawned) == 1, spawned


def test_qb_host_port_and_arm_spec_pinned(tmp_path, monkeypatch):
    """qB host/port 必须来自配置(qh_*/qp_* 全族) + arm spec 关键键值(sg_7/8/18/19/21/22/25~28/37)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._ctx.config.qbittorrent = types.SimpleNamespace(host="10.1.2.3", port=8123)
    assert mod._qb_host() == "10.1.2.3", mod._qb_host()
    assert mod._qb_port() == 8123, mod._qb_port()

    job = _job("j1", plan={"form": ru.FORM_FILE_LINKS, "files": [["a.mkv", 10]]}, alias_paths=("R:/src/a.mkv", ))
    assert mod._write_arm_spec(job) is True
    spec = relocate_journal.read_spec(str(tmp_path), "j1")
    assert spec is not None, "规格必须落盘(daemon 以此为 pending 账底)"
    assert spec["host"] == "10.1.2.3" and spec["port"] == 8123, spec
    assert spec["dst"] == job.dst, spec
    assert spec["alias_paths"] == ["R:/src/a.mkv"], spec
    assert spec["files"] == [["a.mkv", 10]], spec


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): daemon 拉起失败 / penetrate 无别名直进武装
# ---------------------------------------------------------------------------


def test_ensure_daemon_spawn_failure_warns_and_still_throttles(tmp_path):
    """拉起失败(Popen 炸)只告警不炸对账; 退避账键照记(防失败形态每 tick 空拉)"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    _write_new_chain_spec(data_dir, "j1", host, port, backup, v1)

    def _boom(d, h, p):
        raise OSError("spawn denied")

    mod._spawn_daemon = _boom
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._ensure_daemon(job, rt)
    assert any("回收 daemon 拉起失败" in m for m in cap.messages), cap.messages
    assert "ensure_daemon_ts" in rt, "失败也吃退避账(Popen 不留痕迹时没有节流就是每 tick 空拉)"


def test_penetrate_stage_without_aliases_goes_straight_to_arm(tmp_path):
    """penetrate stage 而别名集为空(链上无链接可穿透的形态): 直进武装(233->248 支)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    job = _job(
        "j1",
        phase=ru.PHASE_MOVED,
        plan={
            "form": ru.FORM_FILE_LINKS,
            "link_kind": "hardlink",
            "files": []
        },
        alias_paths=(),
    )
    rt = {"stage": "penetrate"}
    mod._step_moved(job, rt)
    assert rt["stage"] == "arm", rt
    mod._step_moved(job, rt)  # 下一拍: arm 收口(每 tick 一 stage)
    assert mod.get_job("j1") is not None and mod.get_job("j1").phase == ru.PHASE_ARMED


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 标签名配置缺省 / 路径证据客户端缺位 / 祖先上溯深度耗尽
# ---------------------------------------------------------------------------


def test_tag_name_without_config_is_empty(tmp_path):
    """relocate 配置整段缺省(conf None) -> 待收尾标签名空串(标签镜像静默关闭)"""
    import types as _types

    from relocate_exec_support import _bare_mod

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.config = _types.SimpleNamespace(relocate=None)  # relocate 段缺席
    assert mod._tag_name() == ""
