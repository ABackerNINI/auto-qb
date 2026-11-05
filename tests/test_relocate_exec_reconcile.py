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

### S3 接线(计划 26-11-05-0808 §3.2/S3: spec 双字段 + ACT_ENSURE_DAEMON, 全替身不起真进程)
- test_spawn_guardian_spec_bt_backup_and_members: 实例命中 bt_backup 表 -> spec 写 bt_backup +
  members 双 hash(<hash>.torrent 现算 v2); 未命中 -> 不写 bt_backup(旧链 opt-in);
  v2-only/缺 torrent 回落不猜命名
- test_ensure_daemon_spawn_matrix: 死/缺位 -> 重拉 + rt 记账; RESPAWN_BACKOFF 内不重复拉;
  daemon 健康在位 -> 不拉; 旧链 spec / 终态 job -> 不拉
- test_step_reconcile_wires_ensure_daemon: 对账 tick 每拍顺带判新动作(旧表产出不变)
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
    # 构造期注入(S3 收敛: 不再进程级 patch stdlib time.monotonic): 模拟开机 2 分钟 ——
    # rt 无 rebuild_ts 的首建不得被旧 0.0 兜底吞进退避窗口(monotonic 0 点是开机时刻)
    boot_clock = FakeClock(start=120.0)
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch, clock=boot_clock)
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
    # 构造期注入(S3 收敛: 不再进程级 patch stdlib time.monotonic): 模拟开机 30 秒 ——
    # rt 无 respawn_ts 的 guardian 首拉不得被旧 0.0 兜底吞进退避窗口
    boot_clock = FakeClock(start=30.0)
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch, clock=boot_clock)
    mod._qb_up = lambda: True
    # journal 心跳时间戳落注入钟时间线(心跳年龄 = clock.now() - ts, S3 注入后两侧同源取时;
    # 旧写 time.time() - 999 依赖「monotonic 被钉 30s 而墙钟仍走真钟」的进程级改写)
    relocate_journal.write_journal(
        str(tmp_path / "data"), job_id, {
            "phase": ru.PHASE_ARMED,
            "ts": boot_clock.now() - 999
        }
    )
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


def test_spawn_guardian_spec_bt_backup_and_members(tmp_path):
    """arm 侧 spec 双字段接线(单点 _spawn_guardian): 实例命中 bt_backup 表 -> 写字段 +
    members 双 hash(<hash>.torrent 现算 v2); 未命中 -> 不写 bt_backup(旧链 opt-in 语义),
    members 仍落(v1 派生, hash_v2 空); v2-only/缺 torrent 各回落不猜"""
    backup = tmp_path / "BT_backup"
    v1, v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    seen = []
    mod._spawn = lambda data_dir, job_id: seen.append(job_id)
    assert mod._spawn_guardian(job) is True
    spec = relocate_journal.read_spec(str(tmp_path / "data"), "j1")
    assert spec["bt_backup"] == str(backup), spec
    assert spec["members"] == [{"hash_v1": v1, "hash_v2": v2}], spec["members"]

    # 未命中表: 不写 bt_backup 字段(daemon 不认领, 行为同旧链); members 仍派生
    mod2 = _s3_mod(tmp_path)
    job2 = _job("j2", phase=ru.PHASE_ARMED, hashes=(v1, "f" * 40))
    mod2._spawn = lambda data_dir, job_id: seen.append(job_id)
    assert mod2._spawn_guardian(job2) is True
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
    mod3._spawn = lambda data_dir, job_id: seen.append(job_id)
    assert mod3._spawn_guardian(job3) is True
    spec3 = relocate_journal.read_spec(str(tmp_path / "data"), "j3")
    assert spec3["members"] == [{"hash_v1": tv2, "hash_v2": ""}], spec3["members"]

    # 缺 .torrent: hash_v2 留空不猜(消费侧 locate 兜底扫描仍可命中)
    mod4 = _s3_mod(tmp_path, backup=backup)
    job4 = _job("j4", phase=ru.PHASE_ARMED, hashes=("e" * 40, ))
    mod4._spawn = lambda data_dir, job_id: seen.append(job_id)
    assert mod4._spawn_guardian(job4) is True
    spec4 = relocate_journal.read_spec(str(tmp_path / "data"), "j4")
    assert spec4["members"] == [{"hash_v1": "e" * 40, "hash_v2": ""}], spec4["members"]


def test_ensure_daemon_spawn_matrix(tmp_path):
    """ACT_ENSURE_DAEMON 处置矩阵(判据独立于 reconcile 旧表): spec 带 bt_backup + pending
    非空 + 无 daemon 账 -> 重拉; 健康在位 -> 不拉(至多一个 watcher); 旧链 spec / 终态
    -> 不拉; 首拉后 RESPAWN_BACKOFF 内不重复拉(独立 rt 键)"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    relocate_journal.write_spec(
        data_dir, "j1", {
            "job_id": "j1",
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

    # 旧链 spec(无 bt_backup): daemon 不认领, 不白造进程
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
    relocate_journal.write_spec(
        data_dir, "j1", {
            "job_id": "j1",
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
    mod._ensure_daemon(replace(job, phase=ru.PHASE_DONE), {})
    assert spawned == [], spawned


def test_step_reconcile_wires_ensure_daemon(tmp_path):
    """对账 tick 接线: _step_reconcile 每拍顺带判 ACT_ENSURE_DAEMON(新增动作不改旧表
    产出 —— 本现场旧表判 WAIT, 新判据独立触发重拉)"""
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    v1, _v2 = _torrent_fixture(backup, b"m-ok", "R:/src")
    mod = _s3_mod(tmp_path, backup=backup)
    host, port = mod._qb_host(), mod._qb_port()
    rec = types.SimpleNamespace(hash=v1, save_path="R:/src", state="pausedUP")
    mod._ctx.store = types.SimpleNamespace(by_hash={v1: rec}, relocating_hashes=set())
    relocate_journal.write_spec(
        data_dir, "j1", {
            "job_id": "j1",
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
    spawned = []
    mod._spawn_daemon = lambda d, h, p: spawned.append((d, h, p))
    job = _job("j1", phase=ru.PHASE_ARMED, hashes=(v1, ))
    rt = {}
    mod._step_reconcile(job, rt)
    assert spawned == [(data_dir, host, port)], spawned
    # 退避生效: 下一拍不再拉
    mod._step_reconcile(job, rt)
    assert len(spawned) == 1, spawned
