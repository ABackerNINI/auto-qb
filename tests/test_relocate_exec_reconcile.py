"""test_relocate_exec_reconcile 测试计划: 整组迁移执行体 / 对账 / 收尾 guardian / 三入口接线
(计划 26-10-18-1604 §04 P3/P5/P6)

验收判据(plan §04):
- P3: Fake qB 集成覆盖五场景 —— 正常、停滞判失败(不搬回)、长耗时转 watching(不判失败)、
  第 3 条链接失败 ⇒ 删已建链接 + 转收尾、qB 中途断连(不重复下发); 主循环零阻塞(单步 < 50ms)。
- P5: 关闭时调用序列与今日一致(守阵); 开启时三入口(单件/批量/规则)都产生 job。
- P6: 对账表 8 行逐行(纯函数层在 test_relocate_units)、撤销回滚、guardian 三证后删链接。
- 真机 qB 验证留待他人在有 qB 的环境执行(本轮 Fake qB 全替身)。

## 测试计划(每个测试函数一条)
- test_reconcile_finalize_after_qb_restart: journal=removed + qB 在 + missingFiles ⇒ setLocation 收尾
- test_reconcile_rebuild_when_link_lost_but_qb_alive: 链接不在 + qB 在 + 种子正常 ⇒ 重建回 armed
- test_reconcile_respawn_guardian_on_stale_heartbeat: 心跳过期 ⇒ 重拉 guardian
- test_reconcile_failed_gone_and_timeout: 种子消失 ⇒ failed(gone); 超时未收尾 ⇒ failed(timeout)
- test_guardian_removes_links_after_three_proofs: guardian 三证齐全 ⇒ 先写 removing 再删链接写 removed
### P1-T1.1 守卫与容错簇(计划 26-10-20-2101)
- test_apply_reconcile_finalize_done_and_rejected: 收尾动作两档(成员全散 done / setLocation 被拒 failed)
- test_apply_reconcile_unknown_action_is_debug_only: 未知对账动作只落 DEBUG, 不改 job
### 收口 / 退避守卫(issues 26-10-30-0616 批A: resume_hashes 失败路径 / dry_run 短路 / 重试退避)
- test_rebuild_backoff_blocks_within_window: 退避窗口内不重建(旧实现每 1-2 tick 一轮建删)
- test_rebuild_capped_then_failed_keeps_scene: 重建达上限 ⇒ failed 留现场(不再永不终态)
- test_reconcile_respawn_backoff_not_every_tick: guardian 重拉退避(旧实现每 tick 拉一次进程)
- test_rebuild_first_attempt_not_backoff_on_fresh_boot: 开机窗口 —— monotonic < REBUILD_BACKOFF 时首次重建不得被 0.0 哨兵退避吞掉(issue 26-10-31-0932)
- test_respawn_first_spawn_not_backoff_on_fresh_boot: 开机窗口 —— monotonic < RESPAWN_BACKOFF 时 guardian 首拉不受退避(issue 26-10-31-0932)
### W8(R32) S5 补测(变异审计真洞守阵, 分类: tmp-analysis/w8-r32/classify-mod-{a,b}.md)
  + 同卷硬链接兜底(same_volume 实参丢失 ⇒ capability_ok 翻假)
  + 补发 setLocation 入参(只发 mover) + 发起 rt 初值(stall_since/last_size/sample_ts)
- test_apply_reconcile_rebuild_faces: 重建退避账/stage 值/journal 意图回滚/rebuild_exhausted 文案
- test_apply_reconcile_finalize_and_done_faces: 收尾下发实参/rt 账/DONE journal 相位
- test_qb_host_port_and_guardian_spec_pinned: qB host/port 读配置 + guardian spec 关键键值
- test_reconcile_merge_and_elapsed: journal 前向合并 + elapsed 不得过早判死
- test_respawn_and_reconcile_logs: 重拉退避账 + 审计日志

覆盖率第三轮 T2b 补测(26-11-05):
- test_step_reconcile_same_journal_phase_no_remerge: journal 相位与 job 相位一致 -> 不重复落账, 对账照常走完(340->342)
"""

import os

import time

import types

import pytest

from auto_qb.core.modules import relocate_units as ru

from auto_qb.infra import relocate_journal

from helpers import pin_disk_usage, relocate_env

from auto_qb.config.models import RelocateConfig

from auto_qb.core.modules.grouping_mod import group_key_of

from auto_qb.core.modules.relocate_mod import RelocateModule, _native as _mod_native

from auto_qb.infra import alias_fs as afs

from auto_qb.infra import file_access as fa_mod

from auto_qb.infra import utils as infra_utils

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs

from relocate_exec_support import (
    _armed_env,
    _bare_mod,
    _job,
    _run_ticks,
    _simulate_moved,
    _spy_spawn,
)


def test_reconcile_finalize_after_qb_restart(tmp_path, monkeypatch):
    """journal=removed + qB 在 + 成员 missingFiles ⇒ 对成员 setLocation 收尾, 归位后 done"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    mod._remove_links(mod.get_job(job_id).alias_paths)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = src
        mgr.store.by_hash[h].state = "missingFiles"

    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FINALIZING, (job.phase, job.reason)
    fin = [c for c in client.calls if c[0] == "set_location"][-1]
    assert fin[1] == dst, "收尾把仍指向原路径的成员 setLocation 到目标"

    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst
        mgr.store.by_hash[h].progress = 1.0
        mgr.store.by_hash[h].state = "pausedUP"
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_DONE


def test_reconcile_rebuild_when_link_lost_but_qb_alive(tmp_path, monkeypatch):
    """链接不在 + qB 在 + 种子正常(删的时候 qB 其实在跑) ⇒ 重建链接回 armed"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    mod._remove_links(mod.get_job(job_id).alias_paths)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = src
        mgr.store.by_hash[h].state = "pausedUP"

    _run_ticks(mod, 4)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason)
    for p in job.alias_paths:
        assert os.path.exists(p), p


def test_rebuild_first_attempt_not_backoff_on_fresh_boot(tmp_path, monkeypatch):
    """开机窗口: monotonic < REBUILD_BACKOFF 时首次重建不得被退避吞掉(issue 26-10-31-0932)

    rt 里没有 rebuild_ts = 「从未重建」, 不是「开机那一刻重建过」; 旧实现拿 0.0 兜底,
    而 monotonic() 0 点是开机时刻, 开机不满 300s 的机器上退避判据恒真, 重建被静默跳过
    (同树 09:05 全量绿、重启后 09:15 起单跑稳定红的翻转点)。
    """
    pin_disk_usage(monkeypatch)
    monkeypatch.setattr(time, "monotonic", lambda: 120.0)  # 模拟开机 2 分钟
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    mod._remove_links(mod.get_job(job_id).alias_paths)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = src
        mgr.store.by_hash[h].state = "pausedUP"

    _run_ticks(mod, 4)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason)
    for p in job.alias_paths:
        assert os.path.exists(p), p


def test_reconcile_respawn_guardian_on_stale_heartbeat(tmp_path, monkeypatch):
    """armed + 链接在 + 心跳过期(且退避窗口已过) ⇒ 重拉 guardian"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_ARMED, "ts": time.time() - 999})
    spawned.clear()
    mod._rt[job_id]["respawn_ts"] = time.monotonic() - ru.RESPAWN_BACKOFF - 1.0  # 退避窗口外
    mod.on_task_line()
    assert spawned == [job_id]


def test_reconcile_respawn_backoff_not_every_tick(tmp_path, monkeypatch):
    """重拉退避: 距上次拉起不足 RESPAWN_BACKOFF ⇒ 本轮跳过(旧实现每 tick 拉一次进程)

    心跳判据没变, 下一轮还会判到同一个动作 —— 退避掉的只是「同一秒内反复 fork」。
    """
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_ARMED, "ts": time.time() - 999})
    spawned.clear()
    mod._rt[job_id]["respawn_ts"] = time.monotonic()  # 刚拉过
    for _ in range(5):
        mod.on_task_line()
    assert spawned == [], f"退避窗口内不得每 tick 重拉: {spawned}"


def test_respawn_first_spawn_not_backoff_on_fresh_boot(tmp_path, monkeypatch):
    """开机窗口: monotonic < RESPAWN_BACKOFF 时 guardian 首拉不受退避(issue 26-10-31-0932)

    _respawn_guardian 的 docstring 口径是「首次拉起(rt 无记录)不受退避影响」; 旧实现 0.0 兜底
    在开机不满 60s 的机器上连首拉也静默吞掉 —— 与重建退避同一处缺陷的孪生实例。
    """
    pin_disk_usage(monkeypatch)
    monkeypatch.setattr(time, "monotonic", lambda: 30.0)  # 模拟开机 30 秒
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_ARMED, "ts": time.time() - 999})
    spawned.clear()
    # rt 不落盘(重启由 qB 现场恢复) —— 守护进程重启后重拉记录清零, 这正是「首拉」的真实形态;
    # _armed_env 的对账 tick 已写过 respawn_ts, 弹掉还原首拉现场
    mod._rt[job_id].pop("respawn_ts", None)
    assert "respawn_ts" not in mod._rt[job_id], "前提: rt 无重拉记录(首拉)"
    mod.on_task_line()
    assert spawned == [job_id], f"开机窗口内首拉不得被退避吞掉: {spawned}"


def test_reconcile_failed_gone_and_timeout(tmp_path, monkeypatch):
    """种子消失 ⇒ failed(gone); journal 已删链接但 qB 长期不在且超时 ⇒ failed(timeout)"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    mgr.store.by_hash.pop("HA", None)
    mgr.store.by_hash.pop("HB", None)
    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FAILED and job.reason == "torrent_gone", (job.phase, job.reason)

    # 另一条: qB 不在 + 链接已删 + 超过 finalize_timeout
    os.makedirs(tmp_path / "b", exist_ok=True)
    mgr2, client2, mod2, job2, _sp, _s, _d, _c = _armed_env(tmp_path / "b", monkeypatch)
    mod2._qb_up = lambda: False
    mgr2.config.relocate.finalize_timeout = 1.0
    relocate_journal.write_journal(str(tmp_path / "b" / "data"), job2, {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    mod2._remove_links(mod2.get_job(job2).alias_paths)
    job_rec = mod2.get_job(job2)
    mod2._set_job(ru.RelocateJob(**{**job_rec.__dict__, "armed_at": time.time() - 100}))
    mod2.on_task_line()
    assert mod2.get_job(job2).reason == "finalize_timeout"


def test_guardian_removes_links_after_three_proofs(tmp_path, monkeypatch):
    """guardian: 三证齐全 ⇒ 落 removing -> 逐条删链接 -> 落 removed"""
    from auto_qb.tools import finalize_watch as fw

    data_dir = str(tmp_path / "data")
    dst = tmp_path / "dst"
    src = tmp_path / "src"
    dst.mkdir()
    src.mkdir()
    (dst / "a.mkv").write_bytes(b"x" * 8)
    link = src / "a.mkv"
    os.link(dst / "a.mkv", link)  # 硬链接: 无需特权, 且 alias_kind_of 认得出
    spec = {
        "job_id": "jr-x",
        "src": str(src),
        "dst": str(dst),
        "scope": str(dst),
        "files": [["a.mkv", 8]],
        "alias_paths": [str(link)],
        "host": "127.0.0.1",
        "port": 1,
    }
    relocate_journal.write_spec(data_dir, "jr-x", spec)
    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("explorer.exe", ))
    monkeypatch.setattr(fw, "_port_refused", lambda *a, **k: True)
    ticks = {"n": 0}

    def _clock():
        ticks["n"] += 1
        return 1000.0 + ticks["n"] * 10

    result = fw.run(data_dir, "jr-x", heartbeat=10.0, stable=30.0, poll=0.0, clock=_clock, sleep=lambda s: None)
    assert result == "removed", result
    assert not os.path.exists(link), "链接必须被删掉"
    assert os.path.exists(dst / "a.mkv"), "目标数据不得被碰"
    journal = relocate_journal.read_journal(data_dir, "jr-x")
    assert journal["phase"] == "removed" and journal["checks"]["links_removed"] == 1


def test_apply_reconcile_finalize_done_and_rejected(tmp_path, monkeypatch):
    """收尾动作两档: 成员全散 -> done(finalized); setLocation 被拒 -> failed(finalize_rejected)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    job = _job(phase=ru.PHASE_REMOVED)
    monkeypatch.setattr(mod, "_finalize_members", lambda j: ())
    mod._apply_reconcile(job, {}, ru.ACT_FINALIZE)
    assert mod._jobs["j1"].phase == ru.PHASE_DONE and mod._jobs["j1"].reason == "finalized"

    mod2 = _bare_mod(
        api=types.SimpleNamespace(torrents_set_location=lambda **kw: (_ for _ in ()).throw(RuntimeError("409"))),
        data_dir=str(tmp_path)
    )
    monkeypatch.setattr(mod2, "_finalize_members", lambda j: ("HA", ))
    mod2._apply_reconcile(_job(phase=ru.PHASE_REMOVED), {}, ru.ACT_FINALIZE)
    assert mod2._jobs["j1"].phase == ru.PHASE_FAILED and mod2._jobs["j1"].reason == "finalize_rejected"


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
    mod._apply_reconcile(_job("j1", phase=ru.PHASE_REMOVED), rt, ru.ACT_REBUILD)
    assert calls == [], f"退避窗口内不得重建: {calls}"
    rt["rebuild_ts"] = time.monotonic() - ru.REBUILD_BACKOFF - 1.0
    mod._apply_reconcile(_job("j2", phase=ru.PHASE_REMOVED), rt, ru.ACT_REBUILD)
    assert calls == ["j2"], f"退避窗口外应放行重建: {calls}"


def test_rebuild_capped_then_failed_keeps_scene(tmp_path):
    """重建达 attempts 上限 ⇒ failed(rebuild_exhausted) 留现场, 不再无限 create-fail-delete

    建链必失败的环境(权限不足 / 未开开发者模式且 allow_uac 关)里旧实现永不终态。
    """
    mod = _bare_mod(data_dir=str(tmp_path))
    job = _job(phase=ru.PHASE_REMOVED, attempts=ru.REBUILD_MAX_ATTEMPTS)
    mod._apply_reconcile(job, {}, ru.ACT_REBUILD)
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "rebuild_exhausted", (saved.phase, saved.reason)
    assert saved.attempts == ru.REBUILD_MAX_ATTEMPTS, "保留重试次数供排查(不抹掉现场)"


def test_apply_reconcile_rebuild_faces(tmp_path, monkeypatch):
    """重建面: 退避账落正确键(ar_57~59)/stage 值(ar_64/65/101/102)/journal 意图回滚(ar_90/91)/
    rebuild_exhausted 文案(ar_38/41/45/46)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    calls = []
    monkeypatch.setattr(mod, "_build_links", lambda job, rt: calls.append(job.job_id) or len(calls) == 2)
    dd = str(tmp_path)
    relocate_journal.write_journal(dd, "j1", {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    rt = {}
    mod._apply_reconcile(_job("j1", phase=ru.PHASE_REMOVED), rt, ru.ACT_REBUILD)
    assert calls == ["j1"], calls
    assert rt["stage"] == "link", rt  # 重建入口 stage(坏值 = 相位机滞留 MOVED)
    assert rt["rebuild_ts"] > 0, rt  # 退避账(丢失 = 瞬态故障连击)
    assert relocate_journal.read_journal(dd, "j1")["phase"] == ru.PHASE_ARMED, "重建必须回滚 journal 意图"

    mod._apply_reconcile(_job("j2", phase=ru.PHASE_REMOVED), rt, ru.ACT_REBUILD)
    assert calls == ["j1"], f"退避窗口内不得重建: {calls}"

    rt2 = {}
    mod._apply_reconcile(_job("j3", phase=ru.PHASE_REMOVED), rt2, ru.ACT_REBUILD)
    assert calls == ["j1", "j3"], calls
    assert rt2["stage"] == "penetrate", rt2

    # 达上限: failed 文案逐字(attempts 计数不得 or 1 化)
    mod2 = _bare_mod(data_dir=str(tmp_path))
    mod2._apply_reconcile(_job("j9", phase=ru.PHASE_REMOVED, attempts=ru.REBUILD_MAX_ATTEMPTS), {}, ru.ACT_REBUILD)
    saved = mod2._jobs["j9"]
    assert (saved.phase, saved.reason) == (ru.PHASE_FAILED, "rebuild_exhausted"), (saved.phase, saved.reason)
    assert saved.last_error == "重建链接已失败 3 次(上限 3) —— 保留现场交人处理: 通常是权限不足, 修好后重新发起即可", \
        saved.last_error

    # 意图撤销: 删别名期间 qB 回来 —— journal 退回 armed + 审计(ar_11)
    mod3 = _bare_mod(data_dir=str(tmp_path))
    respawned = []
    monkeypatch.setattr(mod3, "_respawn_guardian", lambda job, rt: respawned.append(job.job_id))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap3:
        mod3._apply_reconcile(_job("j7", phase=ru.PHASE_ARMED), {}, ru.ACT_REVERT_INTENT)
    assert respawned == ["j7"], respawned
    assert relocate_journal.read_journal(dd, "j7")["phase"] == ru.PHASE_ARMED
    assert any("撤销删除意图" in m for m in cap3.messages), cap3.messages


def test_apply_reconcile_finalize_and_done_faces(tmp_path, monkeypatch):
    """收尾下发实参(ar_116/118)/rt 收尾账(ar_130~136)/DONE journal 相位与 external 标记(ar_168~181)"""
    locs = []
    mod = _bare_mod(
        api=types.SimpleNamespace(torrents_set_location=lambda **kw: locs.append(dict(kw)), client=None),
        data_dir=str(tmp_path),
    )
    monkeypatch.setattr(mod, "_finalize_members", lambda job: ("HC", "HD"))
    rt = {}
    mod._apply_reconcile(_job("j1", phase=ru.PHASE_REMOVED), rt, ru.ACT_FINALIZE)
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FINALIZING, saved
    assert locs and locs[0]["torrent_hashes"] == ["HC", "HD"] and locs[0]["location"] == saved.dst, locs
    assert rt["finalize"] == ["HC", "HD"], rt  # 动态收尾集合(丢失 = 新成员搁浅)
    assert rt["finalize_ts"] > 0, rt  # 超时保护起点

    mod._apply_reconcile(_job("j2", phase=ru.PHASE_ARMED), {}, ru.ACT_DONE_EXTERNAL)
    saved = mod._jobs["j2"]
    assert saved.phase == ru.PHASE_DONE and saved.reason == "external", (saved.phase, saved.reason)
    j = relocate_journal.read_journal(str(tmp_path), "j2")
    assert j is not None and j["phase"] == ru.PHASE_DONE, j  # guardian 退休通知(丢 = 僵尸)


def test_qb_host_port_and_guardian_spec_pinned(tmp_path, monkeypatch):
    """qB host/port 必须来自配置(qh_*/qp_* 全族) + guardian spec 关键键值(sg_7/8/18/19/21/22/25~28/37)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._ctx.config.qbittorrent = types.SimpleNamespace(host="10.1.2.3", port=8123)
    assert mod._qb_host() == "10.1.2.3", mod._qb_host()
    assert mod._qb_port() == 8123, mod._qb_port()

    job = _job("j1", plan={"form": ru.FORM_FILE_LINKS, "files": [["a.mkv", 10]]}, alias_paths=("R:/src/a.mkv", ))
    seen = []
    monkeypatch.setattr(mod, "_spawn", lambda data_dir, job_id: seen.append((data_dir, job_id)))
    assert mod._spawn_guardian(job) is True
    assert seen == [(str(tmp_path), "j1")], seen
    spec = relocate_journal.read_spec(str(tmp_path), "j1")
    assert spec is not None, "规格必须落盘(写失败 = guardian 永不拉起)"
    assert spec["host"] == "10.1.2.3" and spec["port"] == 8123, spec
    assert spec["dst"] == job.dst, spec
    assert spec["alias_paths"] == ["R:/src/a.mkv"], spec
    assert spec["files"] == [["a.mkv", 10]], spec


def test_reconcile_merge_and_elapsed(tmp_path):
    """journal 前向合并(sr_16/17/23) + elapsed 不得过早判死(sr_52)"""
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store, api=types.SimpleNamespace(client=None), data_dir=str(tmp_path))
    job = _job("j1", phase=ru.PHASE_ARMED)
    mod.register_job(job)
    relocate_journal.write_journal(str(tmp_path), "j1", {"phase": ru.PHASE_REMOVING, "ts": time.time()})
    mod._step_reconcile(job, {})
    assert mod.get_job("j1").phase == ru.PHASE_REMOVING, mod.get_job("j1")  # 收尾意图必须把 armed 拉向前

    mod2 = _bare_mod(
        store=store,
        api=types.SimpleNamespace(client=None),
        data_dir=str(tmp_path),
        relocate=RelocateConfig(enabled=True, finalize_timeout=1.0),
    )
    job2 = _job("j2", phase=ru.PHASE_ARMED, armed_at=time.time())
    mod2.register_job(job2)
    relocate_journal.write_journal(str(tmp_path), "j2", {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    mod2._step_reconcile(job2, {})
    assert mod2.get_job("j2").phase == ru.PHASE_REMOVED, mod2.get_job("j2")  # 意图向前合并; 未超时不得过早 failed


def test_respawn_and_reconcile_logs(tmp_path, monkeypatch):
    """重拉: 退避账写正确键(rg_12/13/14) + 心跳过期审计(ar_5)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    spawned = []
    monkeypatch.setattr(mod, "_spawn_guardian", lambda job: spawned.append(job.job_id) or True)
    rt = {}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._apply_reconcile(_job("j1", phase=ru.PHASE_ARMED), rt, ru.ACT_RESPAWN)
    assert spawned == ["j1"], spawned
    assert rt["respawn_ts"] > 0, rt  # 退避账(丢失 = 每 tick 重拉进程)
    assert any("重拉" in m for m in cap.messages), cap.messages


# ---------- 覆盖率第三轮 T2b 补测(26-11-05): journal 同相位不重复落账 ----------


def test_step_reconcile_same_journal_phase_no_remerge(tmp_path):
    """(T2b)journal 相位与 job 相位一致(340->342) -> 不重复落账(_set_job 不被调), 对账
    照常走完(本环境判 WAIT 零动作); 相位不同则照旧向前合并"""
    rec = types.SimpleNamespace(hash="HA", save_path="R:/src", state="pausedUP")
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._ctx.store = types.SimpleNamespace(by_hash={"HA": rec}, relocating_hashes=set())
    relocate_journal.write_journal(str(tmp_path), "j1", {"phase": ru.PHASE_REMOVING, "ts": time.time()})
    job = _job("j1", phase=ru.PHASE_REMOVING)
    mod._step_reconcile(job, {})
    assert mod._jobs == {}, "同相位不得重复落账"

    mod2 = _bare_mod(data_dir=str(tmp_path))
    mod2._ctx.store = types.SimpleNamespace(by_hash={"HA": rec}, relocating_hashes=set())
    job2 = _job("j1", phase=ru.PHASE_ARMED)
    mod2._step_reconcile(job2, {})
    assert "j1" in mod2._jobs and mod2._jobs["j1"].phase == ru.PHASE_REMOVING, "异相位照旧向前合并"
