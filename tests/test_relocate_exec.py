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
### W8(R32) S5 补测(变异审计真洞守阵, 分类: tmp-analysis/w8-r32/classify-mod-{a,b}.md)
- test_group_facts_gate_inputs_block_gates: 事实包字段丢失/损坏仍拦闸(incomplete/moving/third_party_link/hardlink 四闸) + reparse 非零 tag/缺省 tag 判别
- test_group_facts_same_volume_proof_both_sides: 同卷证明任一侧吻合即过(源侧/目标侧两场景)
- test_group_facts_fact_sources_faces: 文件表/目标卷剩余/listing 失败三事实源的单点行为
- test_group_facts_platform_and_unc_faces: remote 拦 platform 闸 / cap 崩溃面 / UNC dir 形态 / file_alias_kind 实参
  + 同卷硬链接兜底(same_volume 实参丢失 ⇒ capability_ok 翻假)
- test_group_facts_long_path_and_start_plan_faces: 长路径校正(260) + 执行入口 plan 同参 + file_link_error 文案 + hard_max 配置
- test_group_facts_multi_root_and_hard_max_faces: 多首段内容根回落 + 硬上限拒绝
- test_group_facts_dir_link_note_faces: 目录级链接 note(OSError 与 realpath 两段拼接)
- test_step_move_qb_moving_never_stalls: qB moving 态永不判停滞(只 warn 转 watching)
- test_step_move_issue_bookkeeping: 下发账(issue/started/last_size/sample_ts)逐键钉死
- test_step_move_sampling_ledger: 采样账本(grew/重置/停滞起点)四场景
- test_step_move_watching_resets_stall: 转 watching 时停滞账清零
- test_execute_branches_never_break_multi_group: 五个分支 continue 不得提前断多组循环
- test_execute_idempotent_faces_and_skip_contract: 幂等三面(touches 目标不同/全组已在目标/后置)与 skip 回执契约
- test_execute_receipts_and_ctx_guard: 三张拒收回执逐字契约 + ctx 守卫 or 链
- test_start_job_ids_and_receipt_contract: job_id 三分量进键 + started 回执契约
- test_start_job_inflight_guard: 在途拦截(非终态拦/终态放)与拦截回执契约
- test_start_job_pause_issue_args_and_crash_window: 暂停/下发实参钉死 + 崩溃窗补发
  + 补发 setLocation 入参(只发 mover) + 发起 rt 初值(stall_since/last_size/sample_ts)
- test_start_job_plan_faces: plan 消费 file_link_error 与 hard_max 配置
- test_apply_reconcile_rebuild_faces: 重建退避账/stage 值/journal 意图回滚/rebuild_exhausted 文案
- test_apply_reconcile_finalize_and_done_faces: 收尾下发实参/rt 账/DONE journal 相位
- test_step_finalize_targets_and_journal: 收尾集合(rt 优先回落 hashes)与 DONE journal
- test_step_finalize_gone_member_and_zero_progress: 消失成员跳过不断后续 + progress=0 不算完成
- test_qb_host_port_and_guardian_spec_pinned: qB host/port 读配置 + guardian spec 关键键值
- test_spawn_args_pinned: guardian 进程拉起参数(--job/平台支/stdio)
- test_recover_dispatch_faces: 恢复四分派(moving/补发/不补发/RESUME)
- test_start_wiring_and_load_jobs: start 接线(ctx/dry/enabled)与 _load_jobs rt 账
- test_reconcile_merge_and_elapsed: journal 前向合并 + elapsed 不得过早判死
- test_cancel_write_intent_faces: 撤销写意图(删链接/搬回实参/reason/回执)
- test_build_links_faces: 目录别名首建/分块断点/attempts 累计
- test_scope_rel_faces: 内容根相对段(反斜杠归一/平铺/尾斜杠/段首)
- test_buckets_group_key_faces: 组键文件分量/物理分量 + gone 回执
- test_summ_counts_contract: 汇总计数逐值契约
- test_dst_size_sums_all_files: 采样求和与异常跳过
- test_native_syscall_and_finalize_members_faces: _native 空格名/syscall 映射/收尾集合两分量
- test_respawn_and_reconcile_logs: 重拉退避账 + 审计日志
- test_misc_low_contract_faces: on_task_line 守卫/异常账面/_fail 文案/武装与收口实参/纵深单层
- test_precheck_receipt_contract_and_add_param: 预检拒收回执契约 + 添加预检空参
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
    mover="HA",
    **kw,
):
    return ru.RelocateJob(
        job_id=job_id,
        hashes=hashes,
        mover=mover,
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


# ---------------- W8(R32) S5 补测(变异审计真洞守阵) ----------------
# 分类与位点: tmp-analysis/w8-r32/classify-mod-a.md / classify-mod-b.md(R32 S3 终态:
# relocate_mod 真洞 844 = 中 258 / 低 555 / 极低 28 / 等价 276)。守阵按簇整族杀:
# 一组断言覆盖同构变异(键名/大小写/None 化/falsy 同值族), 红验逐条落 tmp-analysis/w8-r32/。
from auto_qb.config.models import RelocateConfig
from auto_qb.core.modules.grouping_mod import group_key_of
from auto_qb.core.modules.relocate_mod import RelocateModule, _native as _mod_native
from auto_qb.infra import alias_fs as afs
from auto_qb.infra import file_access as fa_mod
from auto_qb.infra import utils as infra_utils
from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs


def _facts_mod(conf=None, server_free=None):
    """纯事实收集环境: 不落盘, store/config 全替身(_group_facts 只读面)"""
    store = types.SimpleNamespace(by_hash={}, relocating_hashes=set())
    if server_free is not None:
        store.server_state = {"free_space_on_disk": server_free}
    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(
        store=store,
        api=types.SimpleNamespace(client=object()),
        config=types.SimpleNamespace(relocate=conf or RelocateConfig(enabled=True), data_dir=""),
        state=types.SimpleNamespace(data={}),
    )
    return mod


def _rec(h="HA", name="Show", save_path="R:/src", state="pausedUP", progress=1.0):
    return FakeTorrent(hash=h, name=name, save_path=save_path, state=state, progress=progress)


def _fake_fs(
    monkeypatch,
    *,
    exists=False,
    scandir=None,
    scandir_boom=False,
    free=1 << 40,
    free_by_path=None,
    realpath=None,
    sizes=None,
    boom_sizes=()
):
    """可控文件系统替身: 只覆盖 relocate_mod 消费的五个面(exists/scandir/disk_usage/realpath/getsize)"""
    class _FA:
        def exists(self, path):
            return False if path is None else exists

        def scandir(self, path):
            if scandir_boom:
                raise OSError("listing 炸了")
            return list(scandir or [])

        def disk_usage(self, path):
            if path is None:
                raise RuntimeError("disk_usage(None) 必炸")
            f = free_by_path(path) if free_by_path else free
            return fa_mod.DiskUsage(total=f * 10, used=0, free=f)

        def realpath_lexical(self, path):
            if path is None:
                return None
            return realpath or path

        def getsize(self, path):
            base = os.path.basename(path)
            if base in boom_sizes:
                raise OSError("采样炸了")
            return (sizes or {}).get(base, 0)

        def map_to_container(self, path):
            return None

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA())
    return _FA()


def _stub_cap(
    monkeypatch,
    *,
    link_visible=True,
    dir_kind=None,
    file_kind=None,
    dir_symlink_ok=False,
    dir_symlink_error="",
    file_symlink_error="",
    hardlink_ok=False,
    hardlink_error=""
):
    """替身能力包: 平台判定面不依赖真机探测(WSL/Windows 双侧确定性)

    ``file_kind`` 显式给定 = 该形态可用(同时决定 file_symlink 探针 ok); 给 None 时按
    ``hardlink_ok`` + 同卷实参走真实阶梯的硬链接兜底分支(Windows 同卷唯一可建组合)。
    """
    seen = {}

    def _fak(same_volume):
        seen["arg"] = same_volume
        if file_kind is not None:
            return file_kind
        if not link_visible:
            return None
        if same_volume and hardlink_ok:
            return afs.KIND_HARDLINK
        return None

    cap = types.SimpleNamespace(
        process_os="windows",
        host_os="windows",
        container=False,
        wsl=False,
        path_style="windows",
        foreign_fs=None,
        link_visible_to_host=link_visible,
        junction=afs.LinkProbe(False, error="junction 不可用"),
        dir_symlink=afs.LinkProbe(dir_symlink_ok, error=dir_symlink_error),
        file_symlink=afs.LinkProbe(file_kind is not None, error=file_symlink_error),
        hardlink=afs.LinkProbe(hardlink_ok, error=hardlink_error),
        dir_alias_kind=dir_kind,
        file_alias_kind=_fak,
    )
    monkeypatch.setattr(afs, "get_capability", lambda refresh=False: cap)
    return cap, seen


def _stub_lstat(monkeypatch, *, islnk=False, nlink=1, tag=0, omit_tag=False, boom=False):
    """代表文件 lstat 替身(第三方链接/硬链接识别面的输入)

    ``omit_tag`` = 不提供 ``st_reparse_tag``(POSIX stat 形态): 判别默认值必须落在假值上。
    """
    import stat as stat_mod

    def _lstat(path):
        if boom:
            raise OSError("不可读")
        attrs = {
            "st_mode": stat_mod.S_IFLNK if islnk else stat_mod.S_IFREG,
            "st_nlink": nlink,
        }
        if not omit_tag:
            attrs["st_reparse_tag"] = tag
        return types.SimpleNamespace(**attrs)

    monkeypatch.setattr(os, "lstat", _lstat)


def _solo_member(mgr, client, td, h="HC", subdir="Solo", fname="s01.mkv"):
    """再造一个单成员组(多组循环用例的组B)"""
    src2 = os.path.join(str(td), "solo")
    content2 = os.path.join(src2, subdir)
    os.makedirs(content2, exist_ok=True)
    with open(os.path.join(content2, fname), "wb") as f:
        f.write(b"x" * 64)
    client.files_map[h] = [_fake_file(f"{subdir}/{fname}", 64)]
    tor = FakeTorrent(hash=h, name="Solo", save_path=src2, progress=1.0, state="pausedUP")
    client.torrents[h] = tor
    mgr.store.by_hash[h] = tor
    mgr.host.get("grouping")._assign_new_torrent(h)
    return src2


def test_group_facts_gate_inputs_block_gates(monkeypatch):
    """事实包字段丢失/损坏必须仍能拦闸(incomplete/moving/third_party_link/hardlink 四闸)

    盖 classify-mod-a 中危簇①(gf_293/294/329/331~340: progresses/states 丢失 → 闸门漏判)
    与 gf_284/314/230/232/233/237(第三方链接/硬链接代表文件失真): 任一字段被 None 化/
    键漂移/切片错位, 这里全部当场红。
    """
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    def _facts(progress=1.0, state="pausedUP"):
        mod = _facts_mod()
        _fake_fs(monkeypatch, exists=False, scandir_boom=True)
        _stub_cap(monkeypatch, file_kind="hardlink")
        return mod, mod._group_facts([_rec("HA", progress=progress, state=state), _rec("HB")], "R:/dst", client)

    for p in (0.0, 0.5):  # progress=0.0 是常态入口(刚加种子), or 1.0 变异专门打它
        mod, facts = _facts(progress=p)
        assert facts.progresses[0] == p, facts.progresses
        v = ru.evaluate_group(facts)
        assert v["cls"] == "blocked" and any(r["gate"] == "incomplete" for r in v["reasons"]), (p, v)

    mod, facts = _facts(state="moving")
    assert facts.states[0] == "moving", facts.states
    v = ru.evaluate_group(facts)
    assert v["cls"] == "blocked" and any(r["gate"] == "moving" for r in v["reasons"]), v

    _stub_lstat(monkeypatch, islnk=True)
    mod, facts = _facts()
    assert facts.third_party_link_files == (facts.files[0][0], ), facts.third_party_link_files
    v = ru.evaluate_group(facts)
    tp = next(r for r in v["reasons"] if r["gate"] == "third_party_link")
    assert facts.files[0][0] in tp["text"], tp  # 文案必须点名首文件(names[1] 错位当场红)

    _stub_lstat(monkeypatch, islnk=False, nlink=2)
    mod, facts = _facts()
    assert facts.hardlink_files == (facts.files[0][0], ), facts.hardlink_files
    v = ru.evaluate_group(facts)
    hl = next(r for r in v["reasons"] if r["gate"] == "hardlink")
    assert facts.files[0][0] in hl["text"], hl

    # reparse 点非零 tag(Windows junction/目录链接, 非 S_ISLNK)也必须判第三方链接:
    # `or tag` 被 and 化/反化会漏判(gf_220/221/227/228 簇)。
    _stub_lstat(monkeypatch, islnk=False, tag=0xA0000003)  # IO_REPARSE_TAG_MOUNT_POINT
    mod, facts = _facts()
    assert facts.third_party_link_files == (facts.files[0][0], ), facts.third_party_link_files
    v = ru.evaluate_group(facts)
    assert any(r["gate"] == "third_party_link" for r in v["reasons"]), v

    # tag 缺省(POSIX stat 形态): getattr 默认值必须为假值, 否则每个普通文件都会被误判链接。
    _stub_lstat(monkeypatch, islnk=False, nlink=1, omit_tag=True)
    mod, facts = _facts()
    assert facts.third_party_link_files == () and facts.hardlink_files == (), (
        facts.third_party_link_files,
        facts.hardlink_files,
    )

    assert facts.name == "Show" and facts.target == "R:/dst"  # 事实包身份面不得 None 化


def test_group_facts_same_volume_proof_both_sides(monkeypatch):
    """同卷证明: qB 上报与**任一侧**吻合即过(源侧/目标侧两场景, gf_126~132/103/104)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    qb_free = 1 << 40

    def _facts(free_by_path):
        mod = _facts_mod(server_free=qb_free)
        _fake_fs(monkeypatch, free_by_path=free_by_path)
        _stub_cap(monkeypatch, file_kind="hardlink")
        return mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)

    # 源侧吻合(正向迁移: qB 报的就是源卷)—— and 化/任一侧 None 化都会误拒
    facts = _facts(lambda p: qb_free if p == "R:/src" else (1 << 39))
    assert facts.target_free == 1 << 39 and facts.same_fs_proved is True, (facts.target_free, facts.same_fs_proved)
    v = ru.evaluate_group(facts)
    assert all(r["gate"] != "same_fs" for r in v["reasons"]), v

    # 目标侧吻合(反向迁移/复位场景: 源是 T, qB 报 S)
    facts = _facts(lambda p: qb_free if p == "R:/dst" else (1 << 39))
    assert facts.same_fs_proved is True, facts.same_fs_proved
    v = ru.evaluate_group(facts)
    assert all(r["gate"] != "same_fs" for r in v["reasons"]), v


def test_group_facts_fact_sources_faces(monkeypatch):
    """三事实源单点: 文件表来自 client(gf_9)/目标卷剩余可读(gf_101)/listing 失败=不可判定(gf_53)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod = _facts_mod()
    _fake_fs(monkeypatch, exists=False, scandir_boom=True)
    _stub_cap(monkeypatch, file_kind="hardlink")
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts.files == (("Show/e00.mkv", 64), ), facts.files  # 丢 client = 全组误拒面
    assert facts.target_free == 1 << 40, facts.target_free  # disk_usage(None) 化 = space 误拒面
    assert facts.content_root_exclusive is None, facts.content_root_exclusive  # listing 失败只许「不可判定」


def test_group_facts_platform_and_unc_faces(monkeypatch, tmp_path):
    """平台判定面: remote 拦 platform 闸(gf_139)/cap None 崩溃面(gf_142)/UNC dir 形态(gf_186~188)/
    file_alias_kind 实参 = bool(same_volume)(gf_151/152)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    # remote(两侧 free 都对不上 => proved False): 多成员组必须拦 platform 闸
    mod = _facts_mod(server_free=12345)
    _fake_fs(monkeypatch, free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink")
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts.same_fs_proved is False, facts.same_fs_proved
    v = ru.evaluate_group(facts)
    assert any(r["gate"] == "platform" for r in v["reasons"]), v

    # 健康能力包: platform_verdict 必须拿到 cap(None 化 = AttributeError 崩溃面)
    mod2 = _facts_mod(server_free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink")
    facts2 = mod2._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts2.capability_ok is True, facts2.capability_reason

    # UNC 目标: dir 形态严格随 dir_symlink.ok 走
    mod3 = _facts_mod(server_free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink", dir_symlink_ok=True)
    facts3 = mod3._group_facts([_rec("HA"), _rec("HB")], r"\\server\share", client)
    assert facts3.dir_link_kind == afs.KIND_SYMLINK, facts3.dir_link_kind
    _stub_cap(monkeypatch, file_kind="hardlink", dir_symlink_ok=False, dir_symlink_error="不可建")
    facts4 = mod3._group_facts([_rec("HA"), _rec("HB")], r"\\server\share", client)
    assert facts4.dir_link_kind is None, facts4.dir_link_kind

    # file_alias_kind 的实参必须是真 bool(same_volume): 真实同卷目录上应传 True
    mgr, client2, src, dst, content, files = relocate_env(tmp_path / "sv", state="pausedUP")
    cap, seen = _stub_cap(monkeypatch, file_kind="hardlink")
    facts5 = mgr.host.get("relocate")._group_facts([mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]], dst, client2)
    assert seen["arg"] is True, seen
    assert facts5.file_link_kind == "hardlink", facts5.file_link_kind

    # 同卷 + 文件符号链接不可用、硬链接可用(Windows 同卷唯一可建文件别名的组合):
    # `same_volume=bool(same_vol)` 被 None 化 / 实参删除 / 内层 bool(None) 都会让
    # platform_verdict 走不到硬链接兜底 => capability_ok 翻假(gf_140/144/147)。
    mgr2, client3, src3, dst3, content3, files3 = relocate_env(tmp_path / "hl", state="pausedUP")
    _stub_cap(monkeypatch, hardlink_ok=True)
    facts6 = mgr2.host.get("relocate")._group_facts([mgr2.store.by_hash["HA"], mgr2.store.by_hash["HB"]], dst3, client3)
    assert facts6.same_volume is True, facts6.same_volume
    assert facts6.capability_ok is True, facts6.capability_reason
    assert facts6.file_link_kind == afs.KIND_HARDLINK, facts6.file_link_kind


def test_group_facts_long_path_and_start_plan_faces(tmp_path, monkeypatch):
    """长路径校正(gf_281/311/347/348) + 执行入口 plan 同参(sj_39/50) + file_link_error 文案(sj_36/47/49)
    + hard_max 配置进 plan(sj_32/43)"""
    client = FakeClient()

    def _facts(conf=None, cap_kw=None, save_path="R:/src", target="R:/dst"):
        _fake_fs(monkeypatch, free=1 << 40)
        _stub_cap(monkeypatch, **(cap_kw or {"file_kind": "symlink"}))
        mod = _facts_mod(server_free=1 << 40, conf=conf)
        recs = [_rec("HA", save_path=save_path), _rec("HB", save_path=save_path)]
        return mod, recs, mod._group_facts(recs, target, client)

    # Windows 长路径: symlink 形态 + >= 260 => 拒绝且文案带实测数字
    monkeypatch.setattr(infra_utils, "is_windows", lambda: True)
    long_name = "n" * 250 + ".mkv"
    client.files_map["HA"] = [_fake_file("Show/" + long_name, 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod, recs, facts = _facts()
    assert facts.link_path_limit == afs.WIN_MAX_PATH, facts.link_path_limit
    v = ru.evaluate_group(facts)
    assert v["cls"] == "blocked" and any(r["gate"] == "form" and "路径过长" in r["text"] for r in v["reasons"]), v
    item = mod._start_job(recs, "R:/dst", facts, v, client)
    assert item["cls"] == "blocked" and any("路径过长" in r["text"] for r in item["reasons"]), item

    # POSIX 面: 无上限(恒 260 = 误拒长路径组)
    monkeypatch.setattr(infra_utils, "is_windows", lambda: False)
    _, _, facts2 = _facts()
    assert facts2.link_path_limit is None, facts2.link_path_limit

    # file_link_error 进拒绝文案(能力不可用 + 多成员)
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod, recs, facts3 = _facts(cap_kw={"file_kind": None, "file_symlink_error": "需提权"})
    assert "文件级链接不可建" in facts3.file_link_error, facts3.file_link_error
    v3 = ru.evaluate_group(facts3)
    assert v3["cls"] == "blocked" and any("文件级链接不可建" in r["text"] for r in v3["reasons"]), v3

    # hard_max 从配置进 plan(2 > 1 => 硬上限拒绝; None 化/落缺省 2000 当场红)
    mod, recs, facts4 = _facts(
        conf=RelocateConfig(enabled=True, alias_file_threshold=1, hard_max_links=1), cap_kw={"file_kind": "hardlink"}
    )
    v4 = ru.evaluate_group(facts4)
    item4 = mod._start_job(recs, "R:/dst", facts4, v4, client)
    assert item4["cls"] == "blocked" and any("硬上限" in r["text"] for r in item4["reasons"]), item4


def test_group_facts_multi_root_and_hard_max_faces(tmp_path, monkeypatch):
    """多首段 -> 内容根回落 save_path 且 listing 必须有结论(gf_27); 硬上限拒绝可达(gf_283)"""
    client = FakeClient()
    content = tmp_path / "src"
    (content / "Show").mkdir(parents=True)
    (content / "Movie").mkdir()
    (content / "Show" / "e00.mkv").write_bytes(b"x" * 64)
    (content / "Movie" / "e01.mkv").write_bytes(b"x" * 64)
    dst = tmp_path / "dst"
    dst.mkdir()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Movie/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    _stub_cap(monkeypatch, file_kind="hardlink")
    mod = _facts_mod(server_free=1 << 40)
    facts = mod._group_facts([_rec("HA", save_path=str(content)), _rec("HB", save_path=str(content))], str(dst), client)
    assert facts.content_root_exclusive is False, facts.content_root_exclusive
    v = ru.evaluate_group(facts)
    assert all(r["gate"] != "target_unknown" for r in v["reasons"]), v  # content_root None 化 => 误判不可判定

    # 单文件平铺: 内容根 = save_path 本身, listing 同样必须有结论(gf_27: None 化 = 事实全丢)
    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "e00.mkv").write_bytes(b"x" * 64)
    (flat / "misc").mkdir()
    client.files_map["HD"] = [_fake_file("e00.mkv", 64)]
    hd = FakeTorrent(hash="HD", name="Flat", save_path=str(flat), progress=1.0, state="pausedUP")
    facts3 = mod._group_facts([hd], str(dst), client)
    assert facts3.content_root_exclusive is False, facts3.content_root_exclusive


def test_group_facts_dir_link_note_faces(monkeypatch):
    """目录级链接 note: 两段拼接(gf_240~256) —— 前缀/分隔/丢失全当场红"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod = _facts_mod(server_free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink")
    _fake_fs(monkeypatch, exists=True, realpath="Z:/elsewhere/Show")
    _stub_lstat(monkeypatch, islnk=False, nlink=1)  # 代表文件可读且非链接: note 只剩 realpath 一段
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    cr = os.path.join("R:/src", "Show")  # 内容根经 os.path.join, 分隔符随平台
    assert facts.third_party_dir_note.startswith("检测到目录级链接("), facts.third_party_dir_note
    assert f"({cr} -> Z:/elsewhere/Show)" in facts.third_party_dir_note, facts.third_party_dir_note

    _stub_lstat(monkeypatch, boom=True)  # 代表文件不可读 + realpath 差异: 两段必须都在且单空格连接
    facts2 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts2.third_party_dir_note.startswith("代表文件不可读(远程/容器未映射?): 第三方链接与硬链接未识别"), \
        facts2.third_party_dir_note
    assert "未识别 检测到目录级链接" in facts2.third_party_dir_note, facts2.third_party_dir_note


def test_step_move_qb_moving_never_stalls(monkeypatch):
    """qB 在 moving: 永不判停滞 —— 超时也只转 watching(sm_77~84/90/91/142 整族)"""
    issues = []
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="moving", save_path="R:/src")})
    mod = _bare_mod(
        store=store,
        api=types.SimpleNamespace(torrents_set_location=lambda **kw: issues.append(kw)),
    )
    job = _job(plan={"files": [["a.mkv", 10]]})
    now = time.monotonic()
    # 已超 warn_after(本该转 watching); 若 moving 判定失真则 stalled_for=700 >= 600 会误判 FAILED
    rt = {"issue": False, "started": now - 8000, "sample_ts": 0.0, "last_size": 10, "stall_since": now - 700}
    mod._step_move(job, rt)
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_WATCHING, (saved.phase, saved.reason)
    assert issues == [], "moving 态不得再下发"


def test_step_move_issue_bookkeeping(monkeypatch):
    """下发账逐键钉死: issue 翻转/started/sample_ts/last_size 初值(sm_54~56/57~59/64/121~126/124)"""
    issues = []
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store, api=types.SimpleNamespace(torrents_set_location=lambda **kw: issues.append(kw)))
    job = _job(plan={"files": [["a.mkv", 10]]})
    rt = {"issue": True}
    mod._step_move(job, rt)
    assert len(issues) == 1 and issues[0]["location"] == job.dst, issues
    assert rt["issue"] is False, rt  # 键漂移/值反转 = 每 tick 重发 setLocation
    assert rt["started"] > 0, rt
    assert rt["sample_ts"] == 0.0 and rt["last_size"] == -1 and rt["stall_since"] == 0.0, rt

    mod._step_move(job, rt)  # 第二 tick: 采样 -> last_size/sample_ts 落正确键
    assert rt["last_size"] == 0, rt  # dst 无数据: 0; None 化/键漂移当场红
    assert rt["sample_ts"] > 0, rt
    rt["sample_ts"] = 0.0
    mod._step_move(job, rt)  # 第三 tick: last_size 已是 int, int(None) 变异在此炸
    assert rt["last_size"] == 0, rt


def test_step_move_sampling_ledger(tmp_path, monkeypatch):
    """采样账本四场景: grew 重置/等体积不重置/moving 重置/停滞起点不被误改(sm_110/111/127/129/130/133~135)"""
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store)
    dstdir = tmp_path / "dst"
    dstdir.mkdir()
    (dstdir / "a.mkv").write_bytes(b"x" * 10)
    job = _job(src=str(tmp_path / "src"), dst=str(dstdir), plan={"files": [["a.mkv", 10]]})

    # 体积增长 -> 停滞账清零(即便 qB 不在 moving)
    rt = {"issue": False, "started": time.monotonic(), "sample_ts": 0.0, "last_size": 5, "stall_since": 0.0}
    mod._step_move(job, rt)
    assert rt["stall_since"] == 0.0, rt

    # 等体积不算增长 -> 记停滞起点(>= 变异 = 永不计时)
    rt = {"issue": False, "started": time.monotonic(), "sample_ts": 0.0, "last_size": 10, "stall_since": 0.0}
    mod._step_move(job, rt)
    assert rt["stall_since"] > 0, rt

    # qB 在 moving(体积不增) -> 同样清零; 且必须落在正确键上
    mod._ctx.store.by_hash["HA"].state = "moving"
    now = time.monotonic()
    rt = {"issue": False, "started": now, "sample_ts": 0.0, "last_size": 0, "stall_since": now - 100}
    mod._step_move(job, rt)
    assert rt["stall_since"] == 0.0, rt

    # 停滞起点已记且无新证据 -> 原值保留(读键漂移 = 每采样被 now 覆盖)
    mod._ctx.store.by_hash["HA"].state = "pausedUP"
    preset = time.monotonic() - 100.0
    rt = {"issue": False, "started": time.monotonic(), "sample_ts": 0.0, "last_size": 10, "stall_since": preset}
    mod._step_move(job, rt)
    assert rt["stall_since"] == preset, rt


def test_step_move_watching_resets_stall(monkeypatch):
    """转 watching 必须清停滞账(sm_223/224/225): 旧时间戳带进 watching = 首采样即误判 FAILED"""
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="moving", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job(plan={"files": [["a.mkv", 10]]})
    now = time.monotonic()
    rt = {"issue": False, "started": now - 8000, "sample_ts": now + 1000, "stall_since": now - 700}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_move(job, rt)
    assert mod._jobs["j1"].phase == ru.PHASE_WATCHING, mod._jobs["j1"]
    assert rt["stall_since"] == 0.0, rt
    assert any("转 watching" in m and "7200.0s" in m for m in cap.messages), cap.messages


def test_execute_branches_never_break_multi_group(tmp_path, monkeypatch):
    """多组循环: 任一组落入 skip/blocked/confirm 分支后, 后续组必须照常出回执(re_139/167/185/196/213)"""
    pin_disk_usage(monkeypatch)

    def _env(name, **kw):
        mgr, client, src, dst, content, files = relocate_env(tmp_path / name, state="pausedUP", **kw)
        mod = mgr.host.get("relocate")
        _spy_spawn(mod, [])
        _solo_member(mgr, client, tmp_path / name)
        return mgr, client, mod, src, dst

    # 已在目标 skip(组A)之后组B 照常
    mgr, client, mod, src, dst = _env("brk1")
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst
    client.calls.clear()
    items = mod.relocate_execute(["HA", "HB", "HC"], dst)
    assert [i["cls"] for i in items] == ["skip", "started"], items

    # 闸门拒绝(组A 目标冲突)之后组B 照常
    mgr, client, mod, src, dst = _env("brk2")
    os.makedirs(os.path.join(dst, "Show"), exist_ok=True)
    with open(os.path.join(dst, "Show", "e00.mkv"), "wb") as f:
        f.write(b"occupied")
    items = mod.relocate_execute(["HA", "HB", "HC"], dst)
    assert [i["cls"] for i in items] == ["blocked", "started"], items

    # 需确认(组A 目录别名提议)之后组B 照常
    mgr, client, mod, src, dst = _env("brk3")
    mgr.config.relocate.alias_file_threshold = 1
    _stub_cap(monkeypatch, dir_kind="junction", file_kind=None)
    items = mod.relocate_execute(["HA", "HB", "HC"], dst)
    assert [i["cls"] for i in items] == ["confirm", "started"], items

    # 在途幂等 skip(组A)之后组B 照常(恢复普通能力替身, 免受 ③ 的目录别名提议影响)
    _stub_cap(monkeypatch, file_kind="hardlink")
    mgr, client, mod, src, dst = _env("brk4")
    assert mod.relocate_execute(["HA", "HB"], dst)[0]["cls"] == "started"
    client.calls.clear()
    items = mod.relocate_execute(["HA", "HB", "HC"], dst)
    assert [i["cls"] for i in items] == ["skip", "started"], items

    # 后置幂等 skip(mover 已在目标、组未齐)之后组B 照常
    mgr, client, mod, src, dst = _env("brk5")
    mgr.store.by_hash["HA"].save_path = dst
    fmap = mod._file_map(mgr.store.by_hash["HA"], client)
    key = group_key_of(dst, fmap)
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    items = mod.relocate_execute(["HA", "HC"], dst)
    assert [i["cls"] for i in items] == ["skip", "started"], items
    assert items[0]["notes"][-1] == "已在目标位置(幂等): 未发起迁移", items[0]["notes"]


def test_execute_idempotent_faces_and_skip_contract(tmp_path, monkeypatch):
    """幂等三面与 skip 回执契约(re_99/108/115~138/141/143/145~166/197/199/201/208~211)"""
    pin_disk_usage(monkeypatch)
    # client 丢失 = 「文件列表为空」全组误拒面: 正常路径必须 started(rec.files 不得吃缓存, re_99/171)
    _fake_fs(monkeypatch, free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink")
    recs9 = {}
    for h in ("HA", "HB"):
        recs9[h] = types.SimpleNamespace(
            hash=h,
            save_path="R:/src",
            name="Show",
            log_repr=h,
            progress=1.0,
            state="pausedUP",
            state_enum=None,
            files=lambda c: [_fake_file("Show/e00.mkv", 64),
                             _fake_file("Show/e01.mkv", 64)]
            if c is not None else (_ for _ in ()).throw(RuntimeError("no client"))
        )
    store9 = types.SimpleNamespace(
        get=lambda h: recs9.get(h),
        groups={},
        by_hash=recs9,
        relocating_hashes=set(),
        server_state={"free_space_on_disk": 1 << 40}
    )
    mod9 = RelocateModule()
    mod9._ctx = types.SimpleNamespace(
        store=store9,
        api=types.SimpleNamespace(client=object(), torrents_set_location=lambda **kw: None),
        config=types.SimpleNamespace(relocate=RelocateConfig(enabled=True)),
        state=types.SimpleNamespace(data={}),
    )
    assert mod9.relocate_execute(["HA", "HB"], "R:/dst")[0]["cls"] == "started"

    mgr, client, src, dst, content, files = relocate_env(tmp_path / "idm", state="pausedUP")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    items = mod.relocate_execute(["HA", "HB"], dst)
    assert items[0]["cls"] == "started", items
    job_id = items[0]["job_id"]

    # 幂等键面: touches 但目标不同 -> 不得误 skip(误 skip = 无关组迁同一目标被吞)
    os.makedirs(str(tmp_path / "idm" / "dst2"), exist_ok=True)
    client.calls.clear()
    items = mod.relocate_execute(["HA"], str(tmp_path / "idm" / "dst2"))
    assert items[0]["cls"] == "blocked", items
    assert items[0]["reasons"][0]["gate"] == "unfinished", items[0]

    # 在途 skip 回执契约(逐键)
    client.calls.clear()
    items = mod.relocate_execute(["HA", "HB"], dst)
    it = items[0]
    assert it["cls"] == "skip" and it["job_id"] == job_id, it
    assert set(it) >= {"hashes", "mover", "name", "save_path", "target", "cls", "job_id", "phase", "reasons",
                       "notes"}, set(it)
    assert it["hashes"] == ["HA", "HB"] and it["mover"] == "HA" and it["name"] == "Show", it
    assert it["save_path"] == src and it["target"] == dst and it["phase"] == ru.PHASE_MOVING, it

    # 全组已在目标: skip 无 job_id + 精确 notes + 零下发
    mgr2, client2, src2, dst2, content2, files2 = relocate_env(tmp_path / "atd", state="pausedUP")
    mod2 = mgr2.host.get("relocate")
    _spy_spawn(mod2, [])
    for h in ("HA", "HB"):
        mgr2.store.by_hash[h].save_path = dst2
    client2.calls.clear()
    items = mod2.relocate_execute(["HA"], dst2)
    it = items[0]
    assert it["cls"] == "skip" and "job_id" not in it, it
    assert it["notes"] == ["全组已在目标位置(幂等): 未发起迁移"], it["notes"]
    assert set(it) >= {"hashes", "mover", "name", "save_path", "target", "cls", "reasons", "notes"}, set(it)
    assert it["hashes"] == ["HA"] and it["mover"] == "HA" and it["name"] == "Show", it
    assert it["save_path"] == dst2 and it["target"] == dst2, it
    assert [c for c in client2.calls if c[0] == "set_location"] == [], client2.calls

    # 后置幂等 skip: item 形态完整, 不重复发起建账(setLocation)
    mgr3, client3, src3, dst3, content3, files3 = relocate_env(tmp_path / "post", state="pausedUP")
    mod3 = mgr3.host.get("relocate")
    _spy_spawn(mod3, [])
    mgr3.store.by_hash["HA"].save_path = dst3
    fmap = mod3._file_map(mgr3.store.by_hash["HA"], client3)
    key = group_key_of(dst3, fmap)
    mgr3.store.groups[key] = ["HA", "HB"]
    mgr3.store.member_to_key["HA"] = key
    mgr3.store.member_to_key["HB"] = key
    client3.calls.clear()
    items = mod3.relocate_execute(["HA"], dst3)
    it = items[0]
    assert it["cls"] == "skip" and "job_id" not in it, it
    assert it["hashes"] == ["HA", "HB"] and it["mover"] == "HA" and it["name"] == "Show", it
    assert it["save_path"] == dst3 and it["target"] == dst3, it
    assert it["notes"][-1] == "已在目标位置(幂等): 未发起迁移", it["notes"]
    assert all(isinstance(x, str) for x in it["notes"]), it["notes"]
    assert [c for c in client3.calls if c[0] == "set_location"] == [], "后置幂等不得重复发起"


def test_execute_receipts_and_ctx_guard(tmp_path):
    """三张拒收回执逐字契约(re_25~98) + ctx 守卫 or 链不得漏放(re_77)"""
    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(
        store=types.SimpleNamespace(by_hash={}),
        api=types.SimpleNamespace(client=object()),
        config=types.SimpleNamespace(relocate=RelocateConfig(enabled=False), data_dir=""),
        state=types.SimpleNamespace(data={}),
    )
    it = mod.relocate_execute(["HA"], "R:/dst")[0]
    assert set(it) == {"hashes", "target", "cls", "reasons"}, set(it)
    assert it["cls"] == "blocked" and it["target"] == "R:/dst" and it["hashes"] == ["HA"], it
    assert it["reasons"][0]["gate"] == "disabled", it
    assert it["reasons"][0]["text"] == "整组迁移未启用(配置键 relocate.enabled)", it["reasons"][0]

    mod._ctx.config.relocate = RelocateConfig(enabled=True)
    it = mod.relocate_execute([], "R:/dst")[0]
    assert it["cls"] == "blocked" and it["target"] == "R:/dst" and it["hashes"] == [], it
    assert it["reasons"][0]["gate"] == "param" and it["reasons"][0]["text"] == "未提供任何 hash", it
    it = mod.relocate_execute(["HA"], "  ")[0]
    assert it["cls"] == "blocked" and it["target"] == "" and it["hashes"] == ["HA"], it
    assert it["reasons"][0]["gate"] == "param" and it["reasons"][0]["text"] == "未提供目标位置(location 不能为空)", it

    # store 缺失: 守卫链必须仍挡(首个 or and 化 = AttributeError 崩溃面) + unavailable 回执逐字
    mod._ctx.store = None
    it = mod.relocate_execute(["HA"], "R:/dst")[0]
    assert it["cls"] == "blocked" and it["target"] == "R:/dst", it
    assert it["reasons"][0]["gate"] == "unavailable", it
    assert it["reasons"][0]["text"] == "模块上下文或 qB 客户端不可用", it["reasons"][0]


def test_start_job_ids_and_receipt_contract(tmp_path, monkeypatch):
    """job_id 三分量(mover/target/src)各自进键(sj_5/6/8/9/10) + started 回执契约(sj_179~193)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP")
    src2 = _solo_member(mgr, client, tmp_path)
    mod = mgr.host.get("relocate")
    verdict = {"cls": "ok", "notes": [], "reasons": []}

    recs_a = [mgr.store.by_hash["HA"]]
    item_a = mod._start_job(recs_a, dst, mod._group_facts(recs_a, dst, client), verdict, client)
    recs_c = [mgr.store.by_hash["HC"]]
    item_c = mod._start_job(recs_c, dst, mod._group_facts(recs_c, dst, client), verdict, client)

    assert item_a["job_id"] == ru.job_id_for("HA", dst, src), item_a["job_id"]
    assert item_c["job_id"] == ru.job_id_for("HC", dst, src2), item_c["job_id"]
    assert item_a["job_id"] != item_c["job_id"], (item_a["job_id"], item_c["job_id"])

    assert item_a["cls"] == "started" and item_a["phase"] == ru.PHASE_MOVING, item_a
    assert set(item_a) >= {"job_id", "phase", "alias_kind", "link_count", "notes", "cls"}, set(item_a)
    assert item_a["notes"][-1] == "qB 正在搬迁, 完成后自动建别名并武装收尾", item_a["notes"]


def test_start_job_inflight_guard(tmp_path, monkeypatch):
    """在途拦截: 非终态拦(sj_11/12)、终态放(sj_15)、拦截回执契约(sj_16~27)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP")
    mod = mgr.host.get("relocate")
    recs = [mgr.store.by_hash["HA"]]
    facts = mod._group_facts(recs, dst, client)
    verdict = {"cls": "ok", "notes": [], "reasons": []}
    jid = ru.job_id_for("HA", dst, src)

    mod._jobs[jid] = ru.RelocateJob(job_id=jid, hashes=("HA", "HB"), mover="HA", src=src, dst=dst, scope=content)
    item = mod._start_job(recs, dst, facts, verdict, client)
    assert item["cls"] == "blocked" and item["job_id"] == jid, item
    assert set(item) >= {"cls", "job_id", "reasons"}, set(item)
    assert item["reasons"][0]["gate"] == "unfinished", item
    assert "已有在途迁移" in item["reasons"][0]["text"], item

    mod._jobs[jid] = ru.RelocateJob(
        job_id=jid, hashes=("HA", "HB"), mover="HA", src=src, dst=dst, scope=content, phase=ru.PHASE_FAILED
    )
    client.calls.clear()
    item2 = mod._start_job(recs, dst, facts, verdict, client)
    assert item2["cls"] == "started", item2
    assert ("set_location", dst) in client.calls, client.calls


def test_start_job_pause_issue_args_and_crash_window(tmp_path, monkeypatch):
    """暂停/下发实参钉死(sj_82/162/164) + 发起审计(sj_171/172) + 崩溃窗补发(sj_133)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    pauses, issues = [], []
    real_set = client.torrents_set_location
    monkeypatch.setattr(client, "torrents_pause", lambda **kw: pauses.append(list(kw["torrent_hashes"])))
    client.torrents_set_location = lambda **kw: issues.append((list(kw["torrent_hashes"]), kw["location"])
                                                             ) or real_set(**kw)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "started", items
    assert pauses == [["HA", "HB"]], pauses  # 暂停必须按住全组
    assert issues == [(["HA"], dst)], issues  # 下发只发 mover、目标不得空
    assert any("迁移发起" in m and "mover HA)" in m for m in cap.messages), cap.messages

    # 发起审计的哈希截断必须 [:8](两字符 mover 区分不了 [:9], 用长 hash 钉)
    mgr3, client3, src3, dst3, content3, files3 = relocate_env(tmp_path / "lg", state="pausedUP")
    _solo_member(mgr3, client3, tmp_path / "lg", h="HASHABCDEFGHI")
    mod3 = mgr3.host.get("relocate")
    _spy_spawn(mod3, [])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap3:
        mod3.relocate_execute(["HASHABCDEFGHI"], dst3)
    assert any("迁移发起" in m and "mover HASHABCD)" in m for m in cap3.messages), cap3.messages

    # 崩溃窗: 账已落、setLocation 未发出 -> 相位机必须补发一次
    mgr2, client2, src2, dst2, content2, files2 = relocate_env(tmp_path / "cw", state="uploading")
    mod2 = mgr2.host.get("relocate")
    _spy_spawn(mod2, [])
    real2 = client2.torrents_set_location

    def _boom(**kw):
        raise RuntimeError("qB 拒了")

    client2.torrents_set_location = _boom
    with pytest.raises(RuntimeError):
        mod2.relocate_execute(["HA"], dst2)
    jid = next(iter(mod2._jobs))
    assert mod2._rt[jid]["issue"] is True, mod2._rt[jid]
    # 发起时的 rt 初值必须干净: 键名大小写漂移 / stall_since 非零 = 停滞时钟先手开跑
    # (sj_140/144/145; 先手开跑会让 `elif not rt.get("stall_since")` 分支永远轮不到)
    assert mod2._rt[jid]["last_size"] == -1 and mod2._rt[jid]["sample_ts"] == 0.0, mod2._rt[jid]
    assert mod2._rt[jid]["stall_since"] == 0.0, mod2._rt[jid]
    client2.torrents_set_location = real2
    mgr2.store.own_writes.clear()  # 暂停快照已回流(崩溃窗现场: 暂停早已生效)
    mod2.on_task_line()
    assert [c for c in client2.calls if c[0] == "set_location"] == [("set_location", dst2)], client2.calls
    # 补发路径的入参同样必须是 mover(且实参键在场): 缺省 None = qB 全局改路径(sm_41/43)
    assert client2.limit_location_hashes_calls == [("set_location", ["HA"])], client2.limit_location_hashes_calls


def test_start_job_plan_faces(tmp_path, monkeypatch):
    """plan 消费面: file_link_error 进拒绝文案(sj_36/47/49) + hard_max 从配置进 plan(sj_32/43)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    def _facts(cap_kw, conf=None, fs_kw=None):
        _fake_fs(monkeypatch, free=1 << 40, **(fs_kw or {}))
        _stub_cap(monkeypatch, **cap_kw)
        mod = _facts_mod(server_free=1 << 40, conf=conf)
        recs = [_rec("HA"), _rec("HB")]
        return mod, recs, mod._group_facts(recs, "R:/dst", client)

    mod, recs, facts = _facts({"file_kind": None, "file_symlink_error": "需提权"})
    assert "文件级链接不可建" in facts.file_link_error, facts.file_link_error
    v = ru.evaluate_group(facts)
    item = mod._start_job(recs, "R:/dst", facts, v, client)
    assert item["cls"] == "blocked" and any("文件级链接不可建" in r["text"] for r in item["reasons"]), item

    mod, recs, facts2 = _facts(
        {"file_kind": "hardlink"}, conf=RelocateConfig(enabled=True, alias_file_threshold=1, hard_max_links=1)
    )
    v2 = ru.evaluate_group(facts2)
    item2 = mod._start_job(recs, "R:/dst", facts2, v2, client)
    assert item2["cls"] == "blocked" and any("硬上限" in r["text"] for r in item2["reasons"]), item2

    # dir_link_error 进拒绝文案(文件级与目录级都不可建 + 内容根专属, sj_49)
    mod, recs, facts5 = _facts(
        {
            "file_kind": None,
            "file_symlink_error": "需提权",
            "hardlink_error": "x"
        },
        fs_kw={"scandir": [types.SimpleNamespace(name="e00.mkv"),
                           types.SimpleNamespace(name="e01.mkv")]}
    )
    assert "目录别名不可建" in facts5.dir_link_error, facts5.dir_link_error
    v5 = ru.evaluate_group(facts5)
    assert any("目录别名不可建" in r["text"] for r in v5["reasons"]), v5
    item5 = mod._start_job(recs, "R:/dst", facts5, v5, client)
    assert item5["cls"] == "blocked" and any("目录别名不可建" in r["text"] for r in item5["reasons"]), item5


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


def test_step_finalize_targets_and_journal(tmp_path):
    """收尾集合: rt 优先于 job.hashes(sf_2~6), DONE 落 journal(sf_82~95)"""
    store = types.SimpleNamespace(
        by_hash={
            "HA": types.SimpleNamespace(save_path="R:/src", progress=1.0, state="pausedUP"),
            "HB": types.SimpleNamespace(save_path="R:/dst", progress=1.0, state="pausedUP"),
            "HC": types.SimpleNamespace(save_path="R:/dst", progress=1.0, state="pausedUP"),
        }
    )
    mod = _bare_mod(store=store, data_dir=str(tmp_path))
    mod._step_finalize(
        _job("j1", phase=ru.PHASE_FINALIZING, hashes=("HA", "HB")), {
            "finalize": ["HC"],
            "finalize_ts": time.time()
        }
    )
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_DONE and saved.reason == "finalized", (saved.phase, saved.reason)
    j = relocate_journal.read_journal(str(tmp_path), "j1")
    assert j is not None and j["phase"] == ru.PHASE_DONE, j

    # rt 集合缺席(重启窗): 回落 job.hashes 也算齐(list(None) = 崩溃面)
    mod._step_finalize(_job("j2", phase=ru.PHASE_FINALIZING, hashes=("HC", )), {"finalize_ts": time.time()})
    assert mod._jobs["j2"].phase == ru.PHASE_DONE, mod._jobs["j2"]


def test_step_finalize_gone_member_and_zero_progress(tmp_path):
    """消失成员跳过但不得断后续检查(sf_13); progress=0.0 不算完成(sf_31)"""
    store = types.SimpleNamespace(
        by_hash={"HB": types.SimpleNamespace(save_path="R:/src", progress=1.0, state="pausedUP")}
    )
    mod = _bare_mod(store=store, data_dir=str(tmp_path))
    mod._step_finalize(
        _job("j1", phase=ru.PHASE_FINALIZING, hashes=("HA", )), {
            "finalize": ["GONE", "HB"],
            "finalize_ts": time.time()
        }
    )
    assert mod._jobs.get("j1") is None, "消失成员之后的未到成员必须继续拦收尾(不得过早 DONE)"

    store2 = types.SimpleNamespace(
        by_hash={"HB": types.SimpleNamespace(save_path="R:/dst", progress=0.0, state="pausedUP")}
    )
    mod2 = _bare_mod(store=store2, data_dir=str(tmp_path))
    mod2._step_finalize(
        _job("j2", phase=ru.PHASE_FINALIZING, hashes=("HB", )), {
            "finalize": ["HB"],
            "finalize_ts": time.time()
        }
    )
    assert mod2._jobs.get("j2") is None, "progress=0.0 不得被判完成"


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


def test_spawn_args_pinned(monkeypatch):
    """guardian 进程拉起参数: --job 逐字(sp_8/9)/平台支(sp_20/24/26/32~35)/stdio 与 close_fds(sp_13~19)"""
    import subprocess

    seen = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: seen.append((a, k)))
    mod = RelocateModule()
    monkeypatch.setattr(infra_utils, "is_windows", lambda: True)
    mod._spawn("D:/dd", "jr-x")
    argv, kwargs = seen[-1][0][0], seen[-1][1]
    assert "--job" in argv and argv[-1] == "jr-x", argv
    assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW, kwargs
    assert kwargs["stdout"] == subprocess.DEVNULL and kwargs["stderr"] == subprocess.DEVNULL, kwargs
    assert kwargs["close_fds"] is True, kwargs

    monkeypatch.setattr(infra_utils, "is_windows", lambda: False)
    mod._spawn("D:/dd", "jr-y")
    argv, kwargs = seen[-1][0][0], seen[-1][1]
    assert "--job" in argv and argv[-1] == "jr-y", argv
    assert kwargs["start_new_session"] is True, kwargs  # guardian 不随 auto-qb 进程组消亡


def test_recover_dispatch_faces(tmp_path):
    """恢复四分派: moving=POLL(rv_6~20/39)/未下发补发(rv_55/56)/已下发不补发(rv_48)/数据在 dst=RESUME(rv_23~40)"""
    # qB 在搬: 继续轮询, 不补发
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="moving", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job()
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HA"])
    assert rt.get("recover") is None and rt.get("issue") is False, rt
    assert any("继续轮询" in m for m in cap.messages), cap.messages

    # 未下发 + 无现场: 补发一次(issue=True)+ warning 点名 mover(哈希截断必须 [:8], rv_56)
    store = types.SimpleNamespace(by_hash={"HS": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job(mover="HASHABCDEFGHI", move_issued=False)
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HS"])
    assert rt["issue"] is True, rt
    assert any("补发" in m and "(mover HASHABCD ->" in m for m in cap.messages), cap.messages

    # 已下发 + 无现场: 不重发(保守默认, 交停滞判据)
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job(move_issued=True)
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HA"])
    assert rt.get("issue") is False, rt
    assert any("未见搬迁现场" in m for m in cap.messages), cap.messages

    # 数据已在 dst: RESUME 直进 moved 校验
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/dst")})
    mod = _bare_mod(store=store)
    job = _job()
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HA"])
    assert mod._jobs["j1"].phase == ru.PHASE_MOVED, mod._jobs["j1"]
    assert rt["stage"] == "verify", rt
    assert any("补做" in m for m in cap.messages), cap.messages

    # 分派入口: _step_move 的 recover 分支必须把**真 mover**递给判据(sm_19: 传 None = 误补发)
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="moving", save_path="R:/src")})
    mod = _bare_mod(store=store)
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    mod._step_move(_job(), rt)
    assert rt.get("issue") is False, rt


def test_start_wiring_and_load_jobs(tmp_path, monkeypatch):
    """start 接线(ctx/dry/enabled: st_2/4/5/6/8/14/15) + _load_jobs rt 账逐键(lj_11~25)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]

    fresh = RelocateModule()
    fresh.start(mgr.ctx, dry_run=False)
    assert fresh._ctx is mgr.ctx, "ctx 必须接线(丢失 = 相位机全停)"

    fresh2 = RelocateModule()
    fresh2.start(mgr.ctx, dry_run=True)
    assert fresh2._dry is True, "干跑标志必须透传(丢失 = --dry-run 真写)"
    assert fresh2.get_job(job_id) is not None, "enabled 时必须恢复 job 账"

    rt = fresh2._rt[job_id]
    assert rt["issue"] is False, rt  # 键漂移/值反转 = 恢复后必重发 setLocation
    assert rt["started"] > 0 and rt["sample_ts"] == 0.0, rt
    assert rt["last_size"] == -1 and rt["stall_since"] == 0.0, rt  # 停滞起点真值 = 首采样误判 FAILED


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


def test_cancel_write_intent_faces(tmp_path):
    """撤销写意图: 删链接(rc_65)/搬回实参(rc_67/69)/reason 与回执契约(rc_99/121~126/gone)"""
    dd = str(tmp_path)
    target = tmp_path / "data.mkv"
    target.write_bytes(b"x" * 64)
    link = str(tmp_path / "link.mkv")
    os.link(str(target), link)
    resumed, locs = [], []
    mod = _bare_mod(
        api=types.SimpleNamespace(
            client=None,
            torrents_set_location=lambda **kw: locs.append(dict(kw)),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
        data_dir=dd,
    )
    job = _job(
        "j1",
        phase=ru.PHASE_ARMED,
        alias_paths=(link, ),
        resume_hashes=("HA", ),
        plan={
            "form": ru.FORM_FILE_LINKS,
            "files": [["data.mkv", 64]]
        }
    )
    mod._jobs["j1"] = job

    first = mod.relocate_cancel("j1")
    assert first["cls"] == "confirm" and first["cost"]["job_id"] == "j1" and first["cost"]["bytes"] == 64, first
    assert os.path.exists(link), "未确认不得动链接"

    out = mod.relocate_cancel("j1", cost_confirmed=True)
    assert out["cls"] == "ok", out
    assert set(out) >= {"cls", "cost", "job_id", "phase"}, set(out)
    assert not os.path.exists(link), "撤销必须删链接(链接不删即搬回 = 残链孤现场)"
    assert locs and locs[0]["torrent_hashes"] == ["HA"] and locs[0]["location"] == job.src, locs
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_CANCELLED and saved.reason == "cancelled", (saved.phase, saved.reason)
    assert resumed == [["HA"]], resumed
    assert relocate_journal.read_journal(dd, "j1")["phase"] == ru.PHASE_CANCELLED

    gone = mod.relocate_cancel("nope")
    assert gone["cls"] == "blocked" and gone["reasons"][0]["gate"] == "gone", gone
    assert "未找到迁移任务" in gone["reasons"][0]["text"], gone


def test_build_links_faces(tmp_path, monkeypatch):
    """建链面: 目录别名首建(bl_32)/分块断点(bl_93 + bl_50~53)/attempts 累计(bl_114)"""
    dir_calls = []
    monkeypatch.setattr(afs, "create_dir_alias", lambda link, target, kind: dir_calls.append((link, target, kind)))
    mod = _bare_mod()
    job = _job("j1", phase=ru.PHASE_MOVED, plan={"form": ru.FORM_DIR_ALIAS, "link_kind": "junction", "files": []})
    rt = {"links": [], "link_pos": 0}
    assert mod._build_links(job, rt) is True, "目录别名首建: 链接不存在是常态, 不得当异常回滚"
    assert dir_calls == [(job.src, job.dst, "junction")], dir_calls
    assert rt["links"] == [job.src], rt

    # 逐文件分块: >200 首批必须 False 落账断点; 续建从 link_pos 起
    file_calls = []
    monkeypatch.setattr(afs, "create_file_alias", lambda link, target, kind: file_calls.append(link))
    src = str(tmp_path / "src")
    dst = str(tmp_path / "dst")
    os.makedirs(src, exist_ok=True)
    os.makedirs(dst, exist_ok=True)
    files = [["f%03d.mkv" % i, 10] for i in range(250)]
    job2 = _job(
        "j2",
        phase=ru.PHASE_MOVED,
        src=src,
        dst=dst,
        plan={
            "form": ru.FORM_FILE_LINKS,
            "link_kind": "hardlink",
            "files": files
        }
    )
    rt2 = {"links": [], "link_pos": 0}
    assert mod._build_links(job2, rt2) is False, "首批 200 条即转 penetrate = 分块迁移误杀"
    assert len(file_calls) == 200 and rt2["link_pos"] == 200, (len(file_calls), rt2)
    assert mod._build_links(job2, rt2) is True
    assert len(file_calls) == 250 and rt2["link_pos"] == 250, (len(file_calls), rt2)

    # 建链失败: attempts 在非零基础上累计(归零化 = 重建配额永不耗尽)
    def _boom(link, target, kind):
        raise OSError("权限不足")

    monkeypatch.setattr(afs, "create_file_alias", _boom)
    job3 = _job(
        "j3",
        phase=ru.PHASE_MOVED,
        src=src,
        dst=dst,
        attempts=2,
        plan={
            "form": ru.FORM_FILE_LINKS,
            "link_kind": "hardlink",
            "files": [["a.mkv", 10]]
        }
    )
    assert mod._build_links(job3, {"links": [], "link_pos": 0}) is False
    saved = mod._jobs["j3"]
    assert saved.attempts == 3 and saved.reason == "alias_partial", (saved.attempts, saved.reason)


def test_scope_rel_faces():
    """内容根相对段: 反斜杠归一(sc_8/9/18/19)/平铺(sc_29)/尾斜杠(sc_2/10/12/20)/段首不误剥(sc_25)"""
    mod = RelocateModule()
    assert mod._scope_rel(_job(src="R:/auto/src", scope="R:/auto/src/Show")) == "Show"
    assert mod._scope_rel(_job(src="R:\\auto\\src", scope="R:\\auto\\src\\Show")) == "Show"
    assert mod._scope_rel(_job(src="R:/s", scope="R:/s")) == ""
    assert mod._scope_rel(_job(src="R:/s/", scope="R:/s/sub")) == "sub"
    assert mod._scope_rel(_job(src="R:/s", scope="R:/s/xDir")) == "xDir"
    assert mod._scope_rel(_job(src="R:/s", scope="R:/s/sub/")) == "sub"  # 尾斜杠: rstrip(None) 只剥空白(sc_12)
    assert mod._scope_rel(_job(src="R:/s", scope="R:/s/ShowX")) == "ShowX"  # X 结尾不得被字符集误剥(sc_20)
    assert mod._scope_rel(_job(src="R:/s/ShowX", scope="R:/s/ShowX/sub")) == "sub"  # sc_10
    assert mod._scope_rel(_job(src="R:/s", scope="R:/s/Xdir")) == "Xdir"  # 段首 X 不误剥(sc_25)


def test_buckets_group_key_faces(tmp_path, monkeypatch):
    """组键两分量: 文件表(bk_3/4/6/30)与物理位置(bk_33/45/47) + gone 回执(bk_23~25)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP")
    mod = mgr.host.get("relocate")

    # 文件表分量: 同 save_path 不同文件表 -> 不同组(client 丢失 = 全塌成一组;
    # rec.files 必须对 None client 真抛 —— FakeTorrent 惰性缓存会让 client=None 变异不可区分, bk_3/4/6/30)
    recs1 = {}
    for h, rel in (("HA", "ShowA/a.mkv"), ("HC", "ShowB/b.mkv")):
        recs1[h] = types.SimpleNamespace(
            hash=h,
            save_path=src,
            log_repr=h,
            files=lambda c, _r=rel: [_fake_file(_r, 64)]
            if c is not None else (_ for _ in ()).throw(RuntimeError("no client"))
        )
    store1 = types.SimpleNamespace(get=lambda h: recs1.get(h), groups={}, by_hash=recs1)
    mod1 = _bare_mod(store=store1, api=types.SimpleNamespace(client=object()))
    gone, groups = mod1._buckets(["HA", "HC"])
    assert not gone and len(groups) == 2, (gone, groups)

    # 物理分量: 已迁 mover(save_path=dst)与仍在源的同组并成一组(登记表解析)
    job = ru.RelocateJob(
        job_id="jr-t",
        hashes=("HA", ),
        mover="HA",
        src=src,
        dst=dst,
        scope=content,
        alias_kind="dir",
        plan={"form": ru.FORM_DIR_ALIAS}
    )
    mod.register_job(job)
    mgr.store.by_hash["HA"].save_path = dst
    gone, groups = mod._buckets(["HA", "HB"])
    assert len(groups) == 1 and {r.hash for r in groups[0]} == {"HA", "HB"}, groups

    gone, _g = mod._buckets(["NOPE"])
    assert gone and gone[0]["cls"] == "blocked" and gone[0]["reasons"][0]["gate"] == "gone", gone
    assert gone[0]["reasons"][0]["text"] == "种子已不在客户端", gone[0]


def test_summ_counts_contract():
    """汇总计数逐值契约(su_4/7/10/11/20/33/34 + 键名/缺省族)"""
    assert RelocateModule._summ([{"cls": "ok"}, {"cls": "ok"}, {"cls": "confirm"}, {"cls": "blocked"}, {}]) == \
        "ok 2 / confirm 1 / blocked 2"
    assert RelocateModule._summ([{"cls": "ok"}]) == "ok 1 / confirm 0 / blocked 0"
    assert RelocateModule._summ([{}]) == "ok 0 / confirm 0 / blocked 1"


def test_dst_size_sums_all_files(monkeypatch):
    """采样: 多文件求和(ds_12) + 单件异常只跳过不断后续(ds_20)"""
    mod = _bare_mod()
    job = _job(plan={"files": [["a.mkv", 10], ["b.mkv", 20]]})
    _fake_fs(monkeypatch, exists=True, sizes={"a.mkv": 10, "b.mkv": 20})
    assert mod._dst_size(job) == 30, mod._dst_size(job)
    _fake_fs(monkeypatch, exists=True, sizes={"a.mkv": 10, "b.mkv": 20}, boom_sizes=("a.mkv", ))
    assert mod._dst_size(job) == 20, "采样异常只跳过当件"


def test_native_syscall_and_finalize_members_faces(monkeypatch):
    """_native 空格名(nt_2)/syscall 容器映射(sl_1/2/3)/收尾集合两分量(fm_14/19)/文件表失败告警(flm_3)"""
    assert _mod_native("R:/src", "Show/a b/c.mkv") == os.path.join("R:/src", "Show", "a b", "c.mkv")

    class _FA:
        def map_to_container(self, path):
            return "/mnt/qb" + path if "R:/x" in path else None

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA())
    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(config=types.SimpleNamespace(data_dir=""))
    assert mod._syscall("R:/x/a.mkv") == "/mnt/qbR:/x/a.mkv", mod._syscall("R:/x/a.mkv")

    def _srec(h, sp, flist):
        def _files(client, _f=flist):  # 对 None client 真抛: 否则 api.client=None 化不可区分(fm_19)
            if client is None:
                raise RuntimeError("no client")
            return list(_f)

        return types.SimpleNamespace(save_path=sp, hash=h, log_repr=h, files=_files)

    store = types.SimpleNamespace(
        by_hash={
            "HX": _srec("HX", "R:/else", []),
            "HA": _srec("HA", "R:/dst", []),
            "HB": _srec("HB", "R:/src", []),
            "HC": _srec("HC", "R:/src", [_fake_file("ShowA/a.mkv", 1)]),
        }
    )
    mod2 = _bare_mod(store=store, api=types.SimpleNamespace(client=object()))
    job = _job("j9", phase=ru.PHASE_ARMED, hashes=("HA", "HB"), scope="R:/src/ShowA", plan={"form": ru.FORM_DIR_ALIAS})
    assert mod2._finalize_members(job) == ("HB", "HC"), mod2._finalize_members(job)

    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        assert RelocateModule._file_map(_srec("HZ", "x", None), object()) == {}
    assert any("读取文件列表失败" in m for m in cap.messages), cap.messages


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


def test_misc_low_contract_faces(monkeypatch):
    """低危代表: 未启用零动作(ot_3)/异常账面(ot_22/25/28/31)/_fail 文案(fl_*, sm_7/200)/
    verify_mismatch 文案(mv_16)/武装与收口实参(am_*, fd_*)/纵深单层(pn_8/dr_11)/删链告警(rl_13)"""
    # 未启用: 相位机零动作(即便 _jobs 非空 —— 热重载关闭场景)
    mod = _bare_mod(relocate=RelocateConfig(enabled=False))
    advanced = []
    monkeypatch.setattr(mod, "_advance", lambda job: advanced.append(job.job_id))
    mod.register_job(_job("j1"))
    mod.on_task_line()
    assert advanced == [], advanced

    # 推进异常: internal_error 账面带异常文本
    mod2 = _bare_mod()
    mod2.register_job(_job("j2"))

    def _boom(job):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod2, "_advance", _boom)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod2.on_task_line()
    saved = mod2._jobs["j2"]
    assert (saved.phase, saved.reason, saved.last_error) == (ru.PHASE_FAILED, "internal_error", "boom"), saved
    assert any("推进异常" in m and "boom" in m for m in cap.messages), cap.messages

    # _fail: 缺省空串 + 显式文本
    mod3 = _bare_mod()
    assert mod3._fail(_job("j3"), "r1").last_error == ""
    assert mod3._fail(_job("j4"), "r1", "boom").last_error == "boom"

    # 停滞失败与 mover 消失的失败文案
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod4 = _bare_mod(store=store)
    now = time.monotonic()
    rt = {"issue": False, "started": now - 100, "sample_ts": 0.0, "last_size": 10, "stall_since": now - 700}
    mod4._step_move(_job(plan={"files": [["a.mkv", 10]]}), rt)
    saved = mod4._jobs["j1"]
    assert (saved.phase, saved.reason) == (ru.PHASE_FAILED, "move_stalled"), (saved.phase, saved.reason)
    assert saved.last_error == "搬迁停滞(dst 不再增长且 qB 已不在 moving)", saved.last_error

    mod5 = _bare_mod(store=types.SimpleNamespace(by_hash={}))
    mod5._step_move(_job("j5"), {})
    saved = mod5._jobs["j5"]
    assert (saved.phase, saved.reason, saved.last_error) == (ru.PHASE_FAILED, "torrent_gone", "搬迁中种子已不存在"), \
        saved

    # verify_mismatch 文案
    mod6 = _bare_mod()
    mod6._step_moved(_job("j6", phase=ru.PHASE_MOVED, plan={"files": [["a.mkv", 10]]}), {})
    saved = mod6._jobs["j6"]
    assert (saved.phase, saved.reason, saved.last_error) == (ru.PHASE_FAILED, "verify_mismatch", "目标侧文件数/大小不符"), \
        saved

    # 武装: 相位/reason 清账/重归组实参/审计日志
    rg_args = []
    mod7 = _bare_mod()
    mod7._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: rg_args.append(a))
    monkeypatch.setattr(mod7, "_spawn_guardian", lambda job: True)
    job7 = _job("j7", phase=ru.PHASE_MOVED, alias_kind="")  # direct 形态: or 分支才可达(am_34/35/36)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod7._arm(job7, {})
    saved = mod7._jobs["j7"]
    assert saved.phase == ru.PHASE_ARMED and saved.reason == "" and saved.attempts == 0, saved
    assert rg_args == [(job7.scope, job7.src, job7.hashes)], rg_args
    assert any("已武装收尾" in m and "形态 direct" in m for m in cap.messages), cap.messages

    # 单成员收口: 重归组实参 + 恢复成员 + done
    resumed = []
    mod8 = _bare_mod(
        api=types.SimpleNamespace(client=None, torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])))
    )
    mod8._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: rg_args.append(a))
    job8 = _job("j8", src="R:/src8", resume_hashes=("HA", ))  # src 独立: 重归组实参断言才区分得了缺参变异
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap8:
        mod8._finish_direct(job8)
    saved = mod8._jobs["j8"]
    assert saved.phase == ru.PHASE_DONE and saved.reason == "direct", saved
    assert rg_args[-1] == (job8.scope, job8.src, job8.hashes), rg_args
    assert resumed == [["HA"]], resumed
    assert any("单成员组迁移完成" in m for m in cap8.messages), cap8.messages

    # 重归组失败: 只告警不阻断收口落账(am_16/fd_16)
    def _rg_boom(*a):
        raise RuntimeError("归组炸了")

    mod7b = _bare_mod()
    mod7b._ctx.grouping = types.SimpleNamespace(regroup_scope=_rg_boom)
    monkeypatch.setattr(mod7b, "_spawn_guardian", lambda job: True)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap7b:
        mod7b._arm(_job("j7b", phase=ru.PHASE_MOVED), {})
    assert mod7b._jobs["j7b"].phase == ru.PHASE_ARMED, mod7b._jobs["j7b"]
    assert any("重归组失败" in m for m in cap7b.messages), cap7b.messages

    # 单成员收口的重归组失败同样只告警不阻断(fd_16)
    mod8b = _bare_mod(api=types.SimpleNamespace(client=None, torrents_resume=lambda **kw: None))
    mod8b._ctx.grouping = types.SimpleNamespace(regroup_scope=_rg_boom)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap8b:
        mod8b._finish_direct(_job("j8b", src="R:/src8b"))
    assert mod8b._jobs["j8b"].phase == ru.PHASE_DONE and mod8b._jobs["j8b"].reason == "direct"
    assert any("重归组失败" in m for m in cap8b.messages), cap8b.messages

    # 纵深单层: exists 不可判时不得因 getsize 报对就放行
    class _FA2:
        def exists(self, p):
            return False

        def getsize(self, p):
            return 10

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA2())
    mod9 = _bare_mod()
    job9 = _job("j9", plan={"files": [["a.mkv", 10]]})
    assert mod9._penetration_ok(job9) is False
    assert mod9._dst_ready(job9) is False

    # 删链失败必须留告警(残链排障线索)
    monkeypatch.setattr(afs, "alias_kind_of", lambda p: (_ for _ in ()).throw(RuntimeError("炸")))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._remove_links(["R:/x"])
    assert any("删链接失败" in m for m in cap.messages), cap.messages


def test_precheck_receipt_contract_and_add_param(tmp_path, monkeypatch):
    """预检拒收回执契约(rp_23~101) + 正常预检事实面(rp_108/114) + 添加预检空参(pa_4/12~18)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP", data_dir=False)
    mod = mgr.host.get("relocate")
    mgr.config.relocate.enabled = False
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert set(it) == {"hashes", "cls", "reasons"}, set(it)
    assert it["cls"] == "blocked" and it["hashes"] == ["HA"], it
    assert it["reasons"][0]["gate"] == "disabled", it
    assert it["reasons"][0]["text"] == "整组迁移未启用(配置键 relocate.enabled) —— 路由层已 fail-closed, 此处为纵深防御", it

    mgr.config.relocate.enabled = True
    it = mod.relocate_precheck([], dst)[0]
    assert it["hashes"] == [] and it["reasons"][0]["gate"] == "param", it
    assert it["reasons"][0]["text"] == "未提供任何 hash(预检目标不能为空)", it
    it = mod.relocate_precheck(["HA"], "")[0]
    assert it["hashes"] == ["HA"] and it["reasons"][0]["gate"] == "param", it
    assert it["reasons"][0]["text"] == "未提供目标位置(location 不能为空)", it

    from auto_qb.core.modules.relocate_mod import RelocateModule as _RM
    m2 = _RM()
    m2._ctx = types.SimpleNamespace(config=types.SimpleNamespace(relocate=RelocateConfig(enabled=True)), store=None)
    it = m2.relocate_precheck(["HA"], dst)[0]
    assert it["hashes"] == ["HA"] and it["reasons"][0]["text"] == "模块上下文或种子存储不可用, 无法预检", it
    m2._ctx = types.SimpleNamespace(
        config=types.SimpleNamespace(relocate=RelocateConfig(enabled=True)),
        store=types.SimpleNamespace(by_hash={}),
        api=None,
    )
    it = m2.relocate_precheck(["HA"], dst)[0]
    assert it["hashes"] == ["HA"] and it["reasons"][0]["text"] == "qB 客户端未连接, 无法只读预检", it

    # 正常预检: 文件表必须进事实(读空 = 形态判定失真) + 汇总审计;
    # 换对 None client 真抛的记录 —— FakeTorrent 惰性缓存会让 client=None 变异不可区分(rp_108)
    _stub_cap(monkeypatch, file_kind="hardlink")
    for h in ("HA", "HB"):
        mgr.store.by_hash[h] = types.SimpleNamespace(
            hash=h,
            save_path=src,
            name="Show",
            log_repr=h,
            progress=1.0,
            state="pausedUP",
            state_enum=None,
            files=lambda c: [_fake_file("Show/e00.mkv", 64),
                             _fake_file("Show/e01.mkv", 64)]
            if c is not None else (_ for _ in ()).throw(RuntimeError("no client"))
        )
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        items = mod.relocate_precheck(["HA"], dst)
    assert items[0]["cls"] == "ok" and items[0]["file_count"] == 2, items
    assert any("迁移预检" in m for m in cap.messages), cap.messages

    # 添加预检: 空参拒收回执契约
    out = mod.precheck_add("", "n")
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "param", out
    assert set(out) >= {"save_path", "name", "requested_path", "reasons"}, set(out)
    assert out["save_path"] == "" and out["name"] == "n" and out["requested_path"] == "", out
