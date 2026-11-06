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
    """S3 接线用裸模块: config 带 qbittorrent 身份 + bt_backup 表(替身属性全数据侧)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.config.qbittorrent = types.SimpleNamespace(host=host, port=port)
    if backup is not None:
        mod._ctx.config.bt_backup = {f"{host}:{port}": str(backup)}
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
    mod3._ctx.config.bt_backup = {f"h1:1234": str(backup3)}
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
