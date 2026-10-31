"""test_relocate_exec 测试计划: 整组迁移执行体 / 对账 / 收尾 guardian / 三入口接线
(计划 26-10-18-1604 §04 P3/P5/P6)

验收判据(plan §04):
- P3: Fake qB 集成覆盖五场景 —— 正常、停滞判失败(不搬回)、长耗时转 watching(不判失败)、
  第 3 条链接失败 ⇒ 删已建链接 + 转收尾、qB 中途断连(不重复下发); 主循环零阻塞(单步 < 50ms)。
- P5: 关闭时调用序列与今日一致(守阵); 开启时三入口(单件/批量/规则)都产生 job。
- P6: 对账表 8 行逐行(纯函数层在 test_relocate_units)、撤销回滚、guardian 三证后删链接。
- 真机 qB 验证留待他人在有 qB 的环境执行(本轮 Fake qB 全替身)。

## 测试计划(每个测试函数一条)
- test_exec_normal_flow_links_and_arm: 正常链路 —— 暂停/下发/轮询/建逐文件链接/穿透校验/
  重归组/武装/恢复运行态; 链接真实存在且指向目标数据
- test_exec_stalled_fails_without_moving_back: 停滞判失败, 零搬回(qB setLocation 只下发过一次)
- test_exec_long_running_turns_watching: moving 超 warn_after 转 watching 且不判失败
- test_exec_link_failure_rolls_back_and_finalizes: 第 3 条链接失败 ⇒ 删已建 2 条 + 转收尾
- test_exec_qb_disconnect_does_not_reissue: qB 断连(moving 态消失前)不重复下发 setLocation
- test_exec_direct_single_member_skips_alias: 单成员组 direct: 无别名、直接 done
- test_exec_dry_run_no_side_effects: dry-run 不落盘不建链(回执标 dry-run)
- test_exec_step_budget: 单步耗时预算 —— 建链接分块, 单次 on_task_line 只建一批(<50ms)
- test_reconcile_finalize_after_qb_restart: journal=removed + qB 在 + missingFiles ⇒ setLocation 收尾
- test_reconcile_rebuild_when_link_lost_but_qb_alive: 链接不在 + qB 在 + 种子正常 ⇒ 重建回 armed
- test_reconcile_respawn_guardian_on_stale_heartbeat: 心跳过期 ⇒ 重拉 guardian
- test_reconcile_failed_gone_and_timeout: 种子消失 ⇒ failed(gone); 超时未收尾 ⇒ failed(timeout)
- test_cancel_requires_cost_confirmation_then_rolls_back: 撤销先给成本, 确认后删链接 + 搬回
- test_guardian_removes_links_after_three_proofs: guardian 三证齐全 ⇒ 先写 removing 再删链接写 removed
- test_jobs_persist_and_reload: job 账落 state 并能重启恢复(非终态重挂 relocating 登记)
- test_entry_single_location_disabled_unchanged: 开关关: 单件移动调用序列与今日逐字节一致
- test_entry_single_and_bulk_create_jobs: 开关开: 单件/批量都产生 job(回执 truth 计数)
- test_entry_rule_move_to_gates: 规则 move_to 走闸门: 发起/幂等 skip/需确认 skip/拒绝 fail
### P1-T1.1 守卫与容错簇(计划 26-10-20-2101)
- test_resolve_physical_falls_back_on_resolver_error: 物理位置解析异常退回原路径(组判定绝不因迁移崩)
- test_persist_noop_when_state_box_unavailable: state 账不可用时 _persist 静默返回
- test_sync_relocating_builds_registry_on_legacy_store: 老 store 替身无 relocating_hashes -> 自建并登记非终态成员
- test_on_task_line_noop_without_ctx: ctx/store 缺失(停机路径)零动作
- test_advance_ignores_terminal_phase: 终态相位不再推进(相位机兜底)
- test_step_move_mover_gone_marks_failed: 搬迁中 mover 从快照消失 -> failed(torrent_gone)
- test_step_move_first_stagnant_sample_starts_stall_clock: 既没搬也没长大且无 stall_since -> 记起点
- test_dst_size_and_ready_probe_failures_are_conservative: 采样异常静默计 0 / 齐备判定一律 False
- test_step_moved_verify_mismatch_fails: 目标侧文件表不符 -> failed(verify_mismatch), 不建链接
- test_penetration_ok_rejects_missing_or_unstatable: 穿透校验三态(不存在/stat 抛/齐备)
- test_arm_survives_regroup_failure: 重归组失败只告警, 武装落账与 guardian 照旧
- test_finish_direct_survives_regroup_and_resume_failure: 单成员收口重归组+恢复都失败也 done
- test_qb_up_caches_negative_probe: 「qB 在?」探测异常判不在并缓存 10s
- test_apply_reconcile_finalize_done_and_rejected: 收尾动作两档(成员全散 done / setLocation 被拒 failed)
- test_finalize_members_prefilters_file_table: 收尾预过滤(26-10-30-0616) —— files API 只发给
  覆盖分支候选, job.hashes/mover/save_path 不在 src 的成员全免文件表
- test_apply_reconcile_unknown_action_is_debug_only: 未知对账动作只落 DEBUG, 不改 job
- test_step_finalize_skips_gone_member_and_pending_progress: 收尾轮询跳过已消失成员 / progress 未回 1 等窗口
- test_entry_rule_move_to_confirm_and_empty_reasons
- test_exec_defer_until_pause_snapshot
- test_exec_move_rejected
- test_exec_skip_when_all_at_target
- test_exec_unknown_stage_falls_back_to_arm
- test_restart_does_not_reissue_setlocation
- test_restart_reissues_setlocation_when_never_issued: 崩溃窗口(账已落/未下发) ⇒ 重启补发一次
  setLocation(issue 26-10-30-0616; 旧实现一律 issue=False, 600s 后按 move_stalled 误判)
- test_restart_recovers_to_moved_when_data_already_at_dst: 已下发且数据已在 dst ⇒ 直达 moved
- test_restart_issued_without_evidence_keeps_polling: 已下发但无现场 ⇒ 不重发不立刻判失败
- test_skip_check_skips_during_relocation
### 收口 / 退避守卫(issues 26-10-30-0616 批A: resume_hashes 失败路径 / dry_run 短路 / 重试退避)
- test_fail_path_resumes_paused_members: 失败出口消费 resume_hashes(旧实现只在成功路径恢复)
- test_fail_path_resume_rejected_still_fails_and_names_paused: 恢复被拒: 失败照落 + 告警点名仍被暂停
- test_cancel_failed_resumes_members: 撤销搬回被拒 ⇒ failed(cancel_failed) 且恢复成员
- test_on_task_line_holds_in_dry_run: dry-run 相位机不推进(含 start() 恢复账本这条不经入口闸的路径)
- test_cancel_dry_run_is_blocked: dry-run 撤销零动作(不删链接不搬回)
- test_build_links_failure_bumps_attempts: 建链失败 ⇒ attempts +1(对账侧重建配额消费它)
- test_rebuild_backoff_blocks_within_window: 退避窗口内不重建(旧实现每 1-2 tick 一轮建删)
- test_rebuild_capped_then_failed_keeps_scene: 重建达上限 ⇒ failed 留现场(不再永不终态)
- test_reconcile_respawn_backoff_not_every_tick: guardian 重拉退避(旧实现每 tick 拉一次进程)
- test_rebuild_first_attempt_not_backoff_on_fresh_boot: 开机窗口 —— monotonic < REBUILD_BACKOFF 时首次重建不得被 0.0 哨兵退避吞掉(issue 26-10-31-0932)
- test_respawn_first_spawn_not_backoff_on_fresh_boot: 开机窗口 —— monotonic < RESPAWN_BACKOFF 时 guardian 首拉不受退避(issue 26-10-31-0932)
"""
import os
import time
import types

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.infra import relocate_journal

from helpers import pin_disk_usage, relocate_env


def _simulate_moved(mgr, dst, files, content, mover="HA"):
    """模拟 qB 搬完: 目标侧齐备、源侧文件被搬走、mover 已指向目标"""
    for rel, size in [(f.name, f.size) for f in files]:
        p = os.path.join(dst, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x" * int(size))
        try:
            os.remove(os.path.join(content, os.path.basename(rel)))
        except OSError:
            pass
    mover_rec = mgr.store.by_hash[mover]
    mover_rec.save_path = dst
    mover_rec.state = "pausedUP"


def _spy_spawn(mod, calls):
    mod._spawn = lambda data_dir, job_id: calls.append(job_id)


def _run_ticks(mod, n=6):
    for _ in range(n):
        mod.on_task_line()


def _only_job(mod):
    jobs = mod.jobs_view()
    assert len(jobs) == 1, jobs
    return jobs[0]


def test_exec_normal_flow_links_and_arm(tmp_path, monkeypatch):
    """正常链路: 暂停 -> 下发 -> 轮询 -> 逐文件链接 -> 穿透 -> 重归组 -> armed -> 恢复"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)

    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "started", items
    job_id = items[0]["job_id"]
    assert ("set_location", dst) in client.calls
    assert any(c[0] == "pause" for c in client.calls), client.calls

    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)

    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason, job.last_error)
    assert len(job.alias_paths) == 2
    for p in job.alias_paths:
        assert os.path.exists(p), p  # 经链接读得到目标数据
    assert job_id in spawned, f"武装后应拉起 guardian: {spawned}"
    assert any(c[0] == "resume" for c in client.calls), "武装后应恢复运行态"
    # 重归组: 两个成员仍在同一组(组键首元 = 目标目录, 不裂组)
    key = mgr.store.member_to_key.get("HA")
    assert key is not None and key[0] == dst.replace("\\", "/")
    assert set(mgr.store.groups[key]) == {"HA", "HB"}


def test_exec_stalled_fails_without_moving_back(tmp_path, monkeypatch):
    """停滞判失败: dst 不增长且 qB 不在 moving 超时 ⇒ failed, 零搬回(只下发过一次 setLocation)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mgr.config.relocate.move_stall_timeout = 600.0
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    items = mod.relocate_execute(["HA"], dst)
    job_id = items[0]["job_id"]
    rt = mod._rt[job_id]
    now = time.monotonic()
    rt.update({"started": now - 900, "sample_ts": now + 1000, "last_size": 0, "stall_since": now - 700})

    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FAILED and job.reason == "move_stalled", (job.phase, job.reason)
    locs = [c for c in client.calls if c[0] == "set_location"]
    assert len(locs) == 1, f"失败后不得搬回(重发 setLocation): {locs}"
    assert os.path.isdir(content) and os.listdir(content), "失败不得删/动源数据"


def test_exec_long_running_turns_watching(tmp_path, monkeypatch):
    """长耗时: qB 仍在 moving 且超过 warn_after ⇒ 转 watching(只提示), 不判失败"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mgr.config.relocate.move_warn_after = 7200.0
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mgr.store.by_hash["HA"].state = "moving"
    rt = mod._rt[job_id]
    rt["started"] = time.monotonic() - 8000.0
    rt["sample_ts"] = time.monotonic() + 1000.0

    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_WATCHING, (job.phase, job.reason)


def test_exec_link_failure_rolls_back_and_finalizes(tmp_path, monkeypatch):
    """第 3 条链接失败 ⇒ 已建的 2 条被删 + 转 removed(收尾路径), 不搬回"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=5, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)

    from auto_qb.infra import alias_fs

    real = alias_fs.create_file_alias
    state = {"n": 0}

    def _fail_third(link, target, kind):
        state["n"] += 1
        if state["n"] == 3:
            raise OSError("模拟第 3 条链接失败(权限不足)")
        return real(link, target, kind)

    monkeypatch.setattr(alias_fs, "create_file_alias", _fail_third)
    _run_ticks(mod, 3)  # 1: moved / 2: verify->link / 3: 建链失败 -> 回滚转收尾

    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_REMOVED and job.reason == "alias_partial", (job.phase, job.reason)
    assert list(job.alias_paths) == [], "失败回滚必须清空已建链接账"
    leftovers = [
        os.path.join(content, f"e0{i}.mkv") for i in range(5) if os.path.exists(os.path.join(content, f"e0{i}.mkv"))
    ]
    assert leftovers == [], f"已建链接必须删净: {leftovers}"
    assert len([c for c in client.calls if c[0] == "set_location"]) == 1, "链接失败不得搬回"


def test_exec_qb_disconnect_does_not_reissue(tmp_path, monkeypatch):
    """qB 中途断连(快照停在 moving): 不重复下发 setLocation(会排队/覆盖)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mgr.store.by_hash["HA"].state = "moving"
    for _ in range(5):
        mod.on_task_line()
    assert len([c for c in client.calls if c[0] == "set_location"]) == 1, client.calls
    assert mod.get_job(job_id).phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING)


def test_exec_direct_single_member_skips_alias(tmp_path, monkeypatch):
    """单成员组: direct —— 无别名、无收尾, 搬完直接 done"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    # 只留一个成员: 直接改 store 组结构(单成员组 = 独占内容)
    store = mgr.store
    key = store.member_to_key["HB"]
    store.groups[key].remove("HB")
    store.group_sizes[key].pop("HB", None)
    store.member_to_key.pop("HB", None)
    store.by_hash.pop("HB", None)
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["form"] == "direct", items
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    job = _only_job(mod)
    assert job["phase"] == ru.PHASE_DONE, job
    assert job["alias_paths"] == []
    assert spawned == [], "direct 无别名 ⇒ 不需要 guardian"


def test_exec_dry_run_no_side_effects(tmp_path, monkeypatch):
    """dry-run: 不落盘不建链, 回执标 dry-run(数据面零动作)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    mod._dry = True
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "ok" and any("dry-run" in n for n in items[0]["notes"])
    assert client.calls == [], client.calls
    assert mod.active_jobs() and mod.active_jobs()[0].phase == ru.PHASE_MOVING


def test_exec_step_budget(tmp_path, monkeypatch):
    """单步有界: 大批文件分块建链接, 单次 on_task_line 只建一批(主循环零阻塞)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=450, state="uploading")
    mgr.config.relocate.alias_file_threshold = 1000  # 强制逐文件链接(不做目录别名)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    mod.relocate_execute(["HA"], dst)
    _simulate_moved(mgr, dst, files, content)
    mod.on_task_line()  # moving -> moved
    mod.on_task_line()  # verify -> link
    t0 = time.monotonic()
    mod.on_task_line()  # 第一批链接(上限 200)
    budget = time.monotonic() - t0
    job = _only_job(mod)
    assert job["phase"] == ru.PHASE_MOVED, job["phase"]
    assert len(job["alias_paths"]) == 200, len(job["alias_paths"])
    assert budget < 5.0, f"单步耗时 {budget:.2f}s"


def _armed_env(tmp_path, monkeypatch):
    """跑到 armed 的环境(供对账/撤销用例)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED
    mgr.config.data_dir = str(tmp_path / "data")
    return mgr, client, mod, job_id, spawned, src, dst, content


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


def test_cancel_requires_cost_confirmation_then_rolls_back(tmp_path, monkeypatch):
    """撤销: 未确认只回成本; 确认后删链接 + 搬回 + cancelled + 恢复运行态"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    first = mod.relocate_cancel(job_id)
    assert first["cls"] == "confirm" and first["cost"]["bytes"] > 0
    assert os.path.exists(mod.get_job(job_id).alias_paths[0]), "未确认时不得动链接"

    client.calls.clear()
    r = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert r["cls"] == "ok" and mod.get_job(job_id).phase == ru.PHASE_CANCELLED
    assert mod.get_job(job_id).alias_paths == ()
    assert ("set_location", src) in client.calls, client.calls
    assert any(c[0] == "resume" for c in client.calls), client.calls


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


def test_jobs_persist_and_reload(tmp_path, monkeypatch):
    """job 账落 state; 重启恢复非终态 job 并重挂 relocating 登记"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "started", items
    job_id = items[0]["job_id"]
    assert job_id in (mgr.state.get("relocate") or {}).get("jobs", {})

    mod2 = type(mod)(mgr.ctx)
    n = mod2._load_jobs()
    assert n == 1 and mod2.get_job(job_id).phase == ru.PHASE_MOVING
    assert {"HA", "HB"} <= mgr.store.relocating_hashes


def test_entry_single_location_disabled_unchanged(tmp_path, monkeypatch):
    """开关关: 单件移动仍是「一次 setLocation」—— 调用序列与今日逐字节一致"""
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mgr.config.relocate.enabled = False
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": dst, "cmd_id": "c1"}))
    mgr.web.consume_commands()
    assert client.calls == [("set_location", dst)], client.calls
    assert mgr.host.get("relocate").jobs_view() == [], "关时不得产生 job"


def test_entry_single_and_bulk_create_jobs(tmp_path, monkeypatch):
    """开关开: 单件与批量都产生 job, 回执 truth 计数可读"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": dst, "cmd_id": "c1"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["c1"]
    assert rec["status"] == "ok" and rec["truth"]["summary"]["started"] == 1, rec
    assert len(mod.jobs_view()) == 1

    # 批量: 同一组再选一个成员 -> 幂等 skip(同组同目标的 job 在途, 不新建第二条账)
    mgr.web.commands.put(("bulk_torrents", {"hashes": ["HB"], "action": "location", "location": dst, "cmd_id": "c2"}))
    mgr.web.consume_commands()
    rec2 = mgr.web.results["c2"]
    assert rec2["status"] == "ok" and rec2["truth"]["summary"]["skip"] == 1, rec2
    assert len(mod.jobs_view()) == 1


def test_entry_rule_move_to_gates(tmp_path, monkeypatch):
    """规则 move_to: 发起/幂等 skip/需确认 skip/拒绝 fail 四态"""
    from auto_qb.rules.actions.transfer import MoveToAction

    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])

    class _Ctx:
        def __init__(self, hash="HA", dry_run=False):
            self.hash = hash
            self.dry_run = dry_run
            self.manager = mgr
            self.config = mgr.config
            self.api = mgr.api

    act = MoveToAction({"path": dst})
    r = act.execute(_Ctx())
    assert r.is_ok and "整组迁移已发起" in r.message, r
    # 幂等: 已在该目标
    r2 = act.execute(_Ctx())
    assert r2.is_skipped and "幂等" in r2.message, r2
    # 目标冲突 -> fail 且带自解释原因
    os.makedirs(tmp_path / "b", exist_ok=True)
    mgr2, client2, src2, dst2, content2, files2 = relocate_env(tmp_path / "b", file_count=2, state="uploading")
    os.makedirs(os.path.join(dst2, "Show"), exist_ok=True)
    (tmp_path / "b" / "dst" / "Show" / "e00.mkv").write_bytes(b"occupied")

    class _Ctx2(_Ctx):
        def __init__(self):
            super().__init__()
            self.manager = mgr2
            self.config = mgr2.config
            self.api = mgr2.api

    r3 = MoveToAction({"path": dst2}).execute(_Ctx2())
    assert r3.is_failed and "闸门拒绝" in r3.message, r3


def test_restart_does_not_reissue_setlocation(tmp_path, monkeypatch):
    """重启恢复: 账里 phase=moving 的 job 继续轮询, **不重复下发** setLocation"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mgr.store.by_hash["HA"].state = "moving"
    client.calls.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    assert mod2._load_jobs() == 1
    mod2.on_task_line()
    assert [c for c in client.calls if c[0] == "set_location"] == [], "重启不得重发 setLocation"
    assert mod2.get_job(job_id).phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING)


def test_restart_reissues_setlocation_when_never_issued(tmp_path, monkeypatch):
    """崩溃窗口(账已落、setLocation 未发出): 重启据 move_issued=False 补发一次, 不再静默等停滞超时

    旧实现 _load_jobs 对 MOVING job 一律 issue=False ⇒ 补发永不发生, dst 恒空且 qB 不在
    moving, 只会在 move_stall_timeout(600s)后按 move_stalled 误判失败(issue 26-10-30-0616)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mod._state_jobs()[job_id]["move_issued"] = False  # 模拟「落账与下发之间」中断
    client.calls.clear()
    mgr.store.own_writes.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    assert mod2._load_jobs() == 1
    mod2.on_task_line()  # 第一个 tick 只定夺现场
    assert [c for c in client.calls if c[0] == "set_location"] == [], "定夺现场这一 tick 不下发"
    mod2.on_task_line()  # 第二个 tick 才真的补发
    assert [c for c in client.calls if c[0] == "set_location"] == [("set_location", dst)], "必须补发一次"
    job = mod2.get_job(job_id)
    assert job.move_issued is True, "补发成功必须落账「已下发」"
    assert job.phase == ru.PHASE_MOVING, job


def test_restart_recovers_to_moved_when_data_already_at_dst(tmp_path, monkeypatch):
    """重启恢复: 已下发且 dst 已有数据 ⇒ 按判据直接进 moved 校验(不重发、不等停滞超时)

    只落一个文件 == 「搬了一半就中断」的现场: 常规轮询会一直等在 moving/stall_since 上,
    恢复判据则立刻进 moved, 由 _dst_ready 给出 verify_mismatch(现场保留, 交人处理)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    first = files[0]
    p = os.path.join(dst, *first.name.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b"x" * int(first.size))
    mgr.store.by_hash["HA"].state = "pausedUP"
    client.calls.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    mod2._load_jobs()
    mod2.on_task_line()
    assert mod2.get_job(job_id).phase == ru.PHASE_MOVED, mod2.get_job(job_id)
    mod2.on_task_line()
    job = mod2.get_job(job_id)
    assert (job.phase, job.reason) == (ru.PHASE_FAILED, "verify_mismatch"), job
    assert [c for c in client.calls if c[0] == "set_location"] == [], "数据已在 dst 不得重发"


def test_restart_issued_without_evidence_keeps_polling(tmp_path, monkeypatch):
    """重启恢复: 已下发但 qB 不在 moving 且 dst 无数据 ⇒ 不重发、也不立刻判失败(交停滞判据)

    快照滞后会让「刚下发还没动」与真停滞同形, 立刻判失败会误杀正常迁移 —— 保守默认。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mgr.store.by_hash["HA"].state = "pausedUP"
    client.calls.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    mod2._load_jobs()
    mod2.on_task_line()
    job = mod2.get_job(job_id)
    assert [c for c in client.calls if c[0] == "set_location"] == [], "已下发过不得重发"
    assert job.phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING) and job.reason == "", job
    assert mod2._rt[job_id].get("recover") is None, "现场判据只判一次, 之后交常规轮询"


def test_skip_check_skips_during_relocation(tmp_path, monkeypatch):
    """搬迁窗口: relocating 登记内的种子跳检直接 skip(不删除/不重加)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    mod.relocate_execute(["HA"], dst)
    assert "HA" in mgr.store.relocating_hashes
    mgr.store.own_writes.clear()  # 自有暂停登记先清掉, 单独验证搬迁窗口闸门
    client.calls.clear()
    r = mgr.ctx.ops.skip_check("HA", source="web")
    assert r.is_skipped and "整组迁移" in r.message, r
    assert client.calls == [], client.calls


def test_exec_defer_until_pause_snapshot(tmp_path, monkeypatch):
    """下发前等自有暂停快照回流(own_write_pending): 未回流不下发, 回流后下发一次"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mod._rt[job_id]["issue"] = True  # 回到「尚未下发」形态
    mgr.store.own_writes.clear()
    mgr.store.note_own_write("HA")
    client.calls.clear()
    mod.on_task_line()
    assert [c for c in client.calls if c[0] == "set_location"] == [], "快照未回流不得下发"
    mgr.store.own_writes.clear()
    mod.on_task_line()
    assert [c for c in client.calls if c[0] == "set_location"] == [("set_location", dst)]


def test_exec_move_rejected(tmp_path, monkeypatch):
    """qB 拒绝 setLocation -> failed(move_rejected), 不自动搬回、不动数据"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mod._rt[job_id]["issue"] = True
    mgr.store.own_writes.clear()

    def _boom(**kw):
        raise RuntimeError("qB 拒绝")

    monkeypatch.setattr(client, "torrents_set_location", _boom)
    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FAILED and job.reason == "move_rejected", (job.phase, job.reason)
    assert os.path.isdir(content) and os.listdir(content)


def test_exec_skip_when_all_at_target(tmp_path, monkeypatch):
    """全组已在目标位置 -> skip(幂等), 不建账不下发"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst
    client.calls.clear()
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "skip" and "幂等" in items[0]["notes"][0], items
    assert client.calls == [] and mod.jobs_view() == []


def test_exec_unknown_stage_falls_back_to_arm(tmp_path, monkeypatch):
    """未知 stage 按 arm 收口(防御: 运行期字段损坏不至于挂死)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    mod.on_task_line()
    mod.on_task_line()
    mod._rt[job_id]["stage"] = "weird"
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED


# ---------------- P1-T1.1 守卫与容错簇(计划 26-10-20-2101) ----------------
#
# relocate_mod 的守卫与容错分支是「迁移功能绝不拖垮主链路」的落点: 解析/采样/齐备判定
# 一律保守(异常即退回/记 0/判不齐备), 相位机对终态与缺 ctx 一律零动作。这些分支正常
# 路径不可达(配置合法 + 磁盘在), 只能直接喂坏输入。


def _bare_mod(store=None, api=None, relocate=None, data_dir=""):
    """不落盘的裸模块: ctx 用 SimpleNamespace 拼(state.data 供 _persist 落账)

    data_dir 必须给临时目录: journal 写入点会真建目录, 留空会落到 CWD(副作用台账会拦)。
    """
    from auto_qb.config.models import RelocateConfig
    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(
        store=store if store is not None else types.SimpleNamespace(by_hash={}, relocating_hashes=set()),
        api=api if api is not None else types.SimpleNamespace(),
        config=types.SimpleNamespace(relocate=relocate or RelocateConfig(enabled=True), data_dir=data_dir),
        state=types.SimpleNamespace(data={}),
    )
    return mod


def _job(
    job_id="j1",
    phase=ru.PHASE_MOVING,
    plan=None,
    hashes=("HA", ),
    resume_hashes=(),
    src="R:/src",
    dst="R:/dst",
    scope=None,
    **kw,
):
    return ru.RelocateJob(
        job_id=job_id,
        hashes=hashes,
        mover="HA",
        src=src,
        dst=dst,
        scope=scope or src,
        phase=phase,
        resume_hashes=resume_hashes,
        plan=plan or {},
        **kw,
    )


def test_resolve_physical_falls_back_on_resolver_error(monkeypatch):
    """物理位置解析异常退回原路径(§3.4 第 1 层: 组判定绝不因迁移功能崩)"""
    from auto_qb.core.modules import relocate_units as ru_mod

    mod = _bare_mod()
    assert mod.resolve_physical("") == "", "空路径原样返回"
    monkeypatch.setattr(ru_mod, "resolve_physical", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("解析炸了")))
    assert mod.resolve_physical("R:/x") == "R:/x", "解析失败必须退回原路径"


def test_persist_noop_when_state_box_unavailable(monkeypatch):
    """state 账不可用(容器非 dict)时 _persist 静默返回, 不炸主循环"""
    mod = _bare_mod()
    monkeypatch.setattr(mod, "_state_jobs", lambda: None)
    mod._persist()  # 不抛


def test_sync_relocating_builds_registry_on_legacy_store():
    """老 store 替身没有 relocating_hashes: 自建一份并登记非终态 job 的成员并集"""
    mod = _bare_mod()
    store = types.SimpleNamespace(by_hash={})  # 无 relocating_hashes 字段
    mod._ctx = types.SimpleNamespace(
        store=store, config=types.SimpleNamespace(relocate=None), state=types.SimpleNamespace(data={})
    )
    mod.register_job(_job())
    mod._sync_relocating()
    assert store.relocating_hashes == {"HA"}, "登记必须落在自建集合上"


def test_on_task_line_noop_without_ctx():
    """ctx/store 缺失(停机路径)时 on_task_line 零动作, 不碰任何 job"""
    from auto_qb.config.models import RelocateConfig
    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod = RelocateModule()  # ctx=None
    mod._conf = RelocateConfig(enabled=True)  # 开关开: 不走 enabled 早退, 必须走 ctx 守卫
    mod.on_task_line()  # 不抛
    assert mod.jobs_view() == []


def test_advance_ignores_terminal_phase():
    """终态相位不再推进(相位机兜底: done/failed/cancelled 落到 elif 链之外)"""
    mod = _bare_mod()
    mod._advance(_job(phase=ru.PHASE_DONE))
    mod._advance(_job("j2", phase=ru.PHASE_CANCELLED))
    assert mod._rt == {"j1": {}, "j2": {}}, "只建运行态槽, 不改 job"


def test_step_move_mover_gone_marks_failed():
    """搬迁中 mover 从快照消失 -> failed(torrent_gone), 不再下发 setLocation"""
    calls = []
    api = types.SimpleNamespace(torrents_set_location=lambda **kw: calls.append(kw))
    mod = _bare_mod(api=api)
    mod._step_move(_job(), {})
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "torrent_gone"
    assert calls == [], "mover 已消失不得下发搬迁"


def test_step_move_first_stagnant_sample_starts_stall_clock():
    """既没在搬也没长大且 stall_since 为空 -> 记当前时刻(停滞判定的起点)"""
    from auto_qb.config.models import RelocateConfig

    mod = _bare_mod(store=types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP")}))
    mod._conf = RelocateConfig(enabled=True, move_stall_timeout=600.0, move_warn_after=7200.0)
    job = _job(plan={"files": [["a.mkv", 10]]})
    rt = {"issue": False, "sample_ts": 0.0, "last_size": 999, "started": time.monotonic()}
    mod._step_move(job, rt)
    assert rt["stall_since"] > 0, "首次停滞采样必须记起点(否则永远判不出停滞)"
    assert mod._jobs.get("j1") is None, "首采样不推进相位"


def test_dst_size_and_ready_probe_failures_are_conservative(monkeypatch):
    """采样异常: _dst_size 静默计 0(每 5s 一次不刷屏); _dst_ready 一律 False(宁可等)"""
    from auto_qb.infra import file_access as fa_mod

    mod = _bare_mod()
    job = _job(plan={"files": [["a.mkv", 10]]})

    class _DeadFA:
        def exists(self, path):
            raise OSError("盘掉线")

        def getsize(self, path):
            return 10

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _DeadFA())
    assert mod._dst_size(job) == 0, "采样异常按 0 计"
    assert mod._dst_ready(job) is False, "判定不出齐备一律 False"
    # 空计划: 无可校验内容 -> False(不把「没计划」当齐备)
    assert mod._dst_ready(_job("j2", plan={})) is False


def test_step_moved_verify_mismatch_fails(tmp_path):
    """目标侧文件数/大小不符 -> failed(verify_mismatch), 一个链接都不建"""
    mod = _bare_mod()
    job = ru.RelocateJob(
        job_id="j1",
        hashes=("HA", ),
        mover="HA",
        src=str(tmp_path),
        dst=str(tmp_path / "dst"),
        scope=str(tmp_path),
        phase=ru.PHASE_MOVED,
        plan={"files": [["e00.mkv", 64]]}
    )
    mod._step_moved(job, {})
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "verify_mismatch"
    assert saved.alias_paths == (), "校验不符不得建链接"


def test_penetration_ok_rejects_missing_or_unstatable(monkeypatch):
    """穿透校验: 原路径不存在/大小不符 -> False; stat 抛异常 -> False(一律保守)"""
    from auto_qb.infra import file_access as fa_mod

    mod = _bare_mod()
    job = _job(plan={"files": [["a.mkv", 10]]})

    class _FA:
        def __init__(self, exists, size, boom=False):
            self._exists, self._size, self._boom = exists, size, boom

        def exists(self, p):
            if self._boom:
                raise OSError("盘掉线")
            return self._exists

        def getsize(self, p):
            return self._size

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA(False, 0))
    assert mod._penetration_ok(job) is False, "原路径不存在 = 穿透失败"
    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA(True, 10, boom=True))
    assert mod._penetration_ok(job) is False, "stat 抛异常 = 穿透失败"
    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA(True, 10))
    assert mod._penetration_ok(job) is True


def test_arm_survives_regroup_failure(monkeypatch):
    """重归组失败只告警: 落账照旧 armed + guardian 照拉(下轮 save_path 变化还会再归)"""
    spawned = []
    mod = _bare_mod()
    mod._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: (_ for _ in ()).throw(RuntimeError("归组炸了")))
    monkeypatch.setattr(mod, "_spawn_guardian", lambda job: spawned.append(job.job_id) or True)
    mod._arm(_job(), {})
    assert mod._jobs["j1"].phase == ru.PHASE_ARMED, "重归组失败不得阻断武装落账"
    assert spawned == ["j1"], "guardian 照拉"


def test_finish_direct_survives_regroup_and_resume_failure():
    """单成员收口: 重归组与恢复运行态都失败也照样 done(数据面已就位, 用户可手动起)"""
    mod = _bare_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: (_ for _ in ()).throw(RuntimeError("qB 拒了")))
    )
    mod._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: (_ for _ in ()).throw(RuntimeError("归组炸了")))
    job = ru.RelocateJob(
        job_id="j1", hashes=("HA", ), mover="HA", src="R:/s", dst="R:/d", scope="R:/s", resume_hashes=("HA", )
    )
    mod._finish_direct(job)
    assert mod._jobs["j1"].phase == ru.PHASE_DONE and mod._jobs["j1"].reason == "direct"


def test_qb_up_caches_negative_probe():
    """「qB 在?」三证之一: 探测异常判「不在」并缓存 10s(免得每 tick 一次请求)"""
    calls = []

    class _Client:
        def app_preferences(self):
            calls.append(1)
            raise RuntimeError("连不上")

    mod = _bare_mod(api=types.SimpleNamespace(client=_Client()))
    assert mod._qb_up() is False
    assert mod._qb_up() is False
    assert len(calls) == 1, "10s 内必须命中缓存(负结论同样缓存)"


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


def test_finalize_members_prefilters_file_table(tmp_path):
    """收尾集合预过滤(26-10-30-0616): files API 只发给覆盖分支候选

    旧实现全库逐条先 rec.files(一次 HTTP)再按 save_path 过滤, qB 重启后走标准收尾
    路径时单 tick 串行 N 次 HTTP, 大库主循环停摆分钟级; 判定实际只有目录别名的
    覆盖分支(save_path==src)读内容根, job.hashes/mover 全短路免文件表。
    """
    calls = []

    def _rec(h, save_path):
        return types.SimpleNamespace(
            save_path=save_path,
            hash=h,
            files=lambda client, _h=h: calls.append(_h) or [types.SimpleNamespace(name="a.mkv", size=1)],
        )

    store = types.SimpleNamespace(
        by_hash={
            "HA": _rec("HA", "R:/dst"),  # mover: 判定短路, 免文件表
            "HB": _rec("HB", "R:/src"),  # 创建时成员: 判定短路, 免文件表
            "HC": _rec("HC", "R:/src"),  # 覆盖分支候选: 唯一该取文件表的
            "HX": _rec("HX", "R:/else"),  # save_path 不在 src: 免文件表
        }
    )
    mod = _bare_mod(store=store, api=types.SimpleNamespace(client=object()))
    job = _job(phase=ru.PHASE_ARMED, plan={"form": ru.FORM_DIR_ALIAS}, hashes=("HA", "HB"))
    assert mod._finalize_members(job) == ("HB", "HC")
    assert calls == ["HC"], f"只有覆盖分支候选才发 files API, 实际 {calls}"

    calls.clear()
    flat = _job(phase=ru.PHASE_ARMED, plan={"form": ru.FORM_FILE_LINKS}, hashes=("HA", "HB"))
    assert mod._finalize_members(flat) == ("HB", )
    assert calls == [], "逐文件链接 job 覆盖语义不成立, 全程零 files API"


def test_apply_reconcile_unknown_action_is_debug_only(tmp_path):
    """未知对账动作只落一条 DEBUG(不推进相位, 不炸)"""
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._apply_reconcile(_job(phase=ru.PHASE_ARMED), {}, "some-new-action")
    assert mod._jobs.get("j1") is None, "未知动作不得改 job"


def test_step_finalize_skips_gone_member_and_pending_progress(tmp_path):
    """收尾轮询: 成员已消失 -> 跳过(不判未完成); progress<1 且非校验中 -> 未完成(等窗口)"""
    store = types.SimpleNamespace(
        by_hash={
            "HA": types.SimpleNamespace(save_path="R:/dst", progress=1.0, state="pausedUP"),
            "HB": types.SimpleNamespace(save_path="R:/dst", progress=0.4, state="pausedUP"),
        }
    )
    mod = _bare_mod(store=store, data_dir=str(tmp_path))
    job = _job(phase=ru.PHASE_FINALIZING, hashes=("HA", "GONE"))
    mod._step_finalize(job, {"finalize": ["HA", "GONE"]})
    assert mod._jobs["j1"].phase == ru.PHASE_DONE, "消失成员跳过, 其余到齐即完成"

    # progress 未回 1: 不完成, 且窗口未到不判失败
    job2 = _job("j2", phase=ru.PHASE_FINALIZING, hashes=("HB", ))
    mod._step_finalize(job2, {"finalize": ["HB"], "finalize_ts": time.time()})
    assert mod._jobs.get("j2") is None, "窗口内未完成不得判失败"


def test_entry_rule_move_to_confirm_and_empty_reasons(tmp_path, monkeypatch):
    """规则 move_to 两条边缘回执: ① 预检判 confirm(目录别名需显式确认) -> skip 并指路 WebUI;
    ② 闸门拒绝但 reasons 为空 -> fail 文案回落「未通过预检」(绝不留空原因)

    直接替换模块的 relocate_execute 返回固定 items —— 这两条是**回执文案**面, 预检细节
    已由 relocate_paths 覆盖, 这里只钉「四种 cls 各自怎么说」。
    """
    from auto_qb.rules.actions.transfer import MoveToAction

    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")

    class _Ctx:
        hash = "HA"
        dry_run = False
        manager = mgr
        config = mgr.config
        api = mgr.api

    act = MoveToAction({"path": dst})
    monkeypatch.setattr(mod, "relocate_execute", lambda hashes, path, confirm=False: [{"cls": "confirm"}])
    r = act.execute(_Ctx())
    assert r.is_skipped and "显式确认" in r.message, r

    monkeypatch.setattr(
        mod, "relocate_execute", lambda hashes, path, confirm=False: [{
            "cls": "blocked",
            "reasons": []
        }]
    )
    r2 = act.execute(_Ctx())
    assert r2.is_failed and "未通过预检" in r2.message, r2


# ---------------------------------------------------------------- 收口/退避守卫(issues 26-10-30-0616 批A)


def test_fail_path_resumes_paused_members():
    """失败出口消费 resume_hashes: 迁移没成 ⇒ 把发起时暂停的成员放回运行态

    旧实现只在成功路径(武装 / 单成员收口 / 撤销成功)恢复, 失败出口一律漏掉 —— 整组
    成员永久停在暂停态且日志一字不提, 用户只能观察到「莫名暂停」。
    """
    resumed = []
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP")}, relocating_hashes=set())
    mod = _bare_mod(
        store=store,
        api=types.SimpleNamespace(
            torrents_set_location=lambda **kw: (_ for _ in ()).throw(RuntimeError("qB 拒绝 setLocation")),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
    )
    mod._step_move(_job(resume_hashes=("HA", "HB")), {"issue": True})
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "move_rejected", (saved.phase, saved.reason)
    assert resumed == [["HA", "HB"]], f"失败必须把被暂停的成员放回运行态: {resumed}"


def test_fail_path_resume_rejected_still_fails_and_names_paused():
    """恢复被拒: 失败照落(数据面保留现场), 只告警并点名「仍被暂停」(用户可照单手动恢复)"""
    from helpers import capture_logs

    mod = _bare_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: (_ for _ in ()).throw(RuntimeError("拒了"))))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._fail(_job(resume_hashes=("HA", )), "move_stalled", "停滞")
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "move_stalled"
    assert any("仍被暂停" in m and "HA" in m for m in cap.messages), cap.messages


def test_cancel_failed_resumes_members(tmp_path):
    """撤销搬回被拒 ⇒ failed(cancel_failed) 且恢复成员(搬回没成, 组不该继续被按住)"""
    resumed = []
    mod = _bare_mod(
        api=types.SimpleNamespace(
            torrents_set_location=lambda **kw: (_ for _ in ()).throw(RuntimeError("409")),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
        data_dir=str(tmp_path),
    )
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=("HA", ))
    out = mod.relocate_cancel("j1", cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "cancel_failed", out
    assert mod._jobs["j1"].phase == ru.PHASE_FAILED and mod._jobs["j1"].reason == "cancel_failed"
    assert resumed == [["HA"]], f"撤销失败必须恢复成员: {resumed}"


def test_on_task_line_holds_in_dry_run(tmp_path, monkeypatch):
    """dry-run: 相位机不推进 —— 含「恢复账本」这条不经入口闸的路径

    相位机每一步都是真写(setLocation / 建删链接 / 拉 guardian / 恢复运行态), 而
    relocate_execute 那道闸只挡新建 job; 上一轮非终态 job 由 start() 从 state 恢复,
    携它以 --dry-run 启动必须同样零动作。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    before = len([c for c in client.calls if c[0] == "set_location"])
    mod._dry = True  # 等价于以 --dry-run 启动
    _run_ticks(mod, 3)
    assert len([c for c in client.calls if c[0] == "set_location"]) == before, "dry-run 不得下发 setLocation"
    assert mod.get_job(job_id).phase == ru.PHASE_MOVING, "相位机不得推进"

    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod2 = RelocateModule()  # 新进程: 从 state 恢复同一批 job(启动期 _load_jobs)
    mod2._ctx = mod._ctx
    mod2._dry = True
    assert mod2._load_jobs() >= 1, "state 里应有上一轮留下的非终态 job"
    mod2.on_task_line()
    assert len([c for c in client.calls if c[0] == "set_location"]) == before, "恢复账本路径同样不得真写"


def test_cancel_dry_run_is_blocked(tmp_path, monkeypatch):
    """dry-run 撤销零动作: 回执 blocked(dry_run), 不删链接不搬回(搬回要再复制全量数据)"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    links = list(mod.get_job(job_id).alias_paths)
    assert links, "armed 现场应有链接(撤销要删的对象)"
    mod._dry = True
    out = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "dry_run", out
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED, "撤销不得改相位"
    assert [c for c in client.calls if c[0] == "set_location"][-1][1] == dst, "不得搬回源路径"
    assert any(os.path.exists(p) for p in links), "链接必须还在"


def test_build_links_failure_bumps_attempts(tmp_path, monkeypatch):
    """建链失败 ⇒ attempts +1(对账侧的重建配额消费它; 旧实现该字段全程零消费)"""
    from auto_qb.infra import alias_fs

    monkeypatch.setattr(alias_fs, "create_file_alias", lambda *a, **k: (_ for _ in ()).throw(OSError("权限不足")))
    mod = _bare_mod(data_dir=str(tmp_path))
    job = _job(
        phase=ru.PHASE_MOVED, plan={"files": [["a.mkv", 10]]}, src=str(tmp_path / "src"), dst=str(tmp_path / "dst")
    )
    assert mod._build_links(job, {"links": [], "link_pos": 0}) is False
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_REMOVED and saved.reason == "alias_partial", (saved.phase, saved.reason)
    assert saved.attempts == 1, saved.attempts


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
