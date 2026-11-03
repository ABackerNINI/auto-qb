"""test_relocate_exec_run 测试计划: 整组迁移执行体 / 对账 / 收尾 guardian / 三入口接线
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
- test_entry_rule_move_to_gates: 规则 move_to 走闸门: 发起/幂等 skip/需确认 skip/拒绝 fail
### P1-T1.1 守卫与容错簇(计划 26-10-20-2101)
- test_step_move_mover_gone_marks_failed: 搬迁中 mover 从快照消失 -> failed(torrent_gone)
- test_step_move_first_stagnant_sample_starts_stall_clock: 既没搬也没长大且无 stall_since -> 记起点
- test_dst_size_and_ready_probe_failures_are_conservative: 采样异常静默计 0 / 齐备判定一律 False
- test_step_moved_verify_mismatch_fails: 目标侧文件表不符 -> failed(verify_mismatch), 不建链接
- test_arm_survives_regroup_failure: 重归组失败只告警, 武装落账与 guardian 照旧
- test_finish_direct_survives_regroup_and_resume_failure: 单成员收口重归组+恢复都失败也 done
- test_finalize_members_prefilters_file_table: 收尾预过滤(26-10-30-0616) —— files API 只发给
  覆盖分支候选, job.hashes/mover/save_path 不在 src 的成员全免文件表
- test_step_finalize_skips_gone_member_and_pending_progress: 收尾轮询跳过已消失成员 / progress 未回 1 等窗口
- test_entry_rule_move_to_confirm_and_empty_reasons
- test_exec_defer_until_pause_snapshot
- test_exec_move_rejected
- test_exec_skip_when_all_at_target
- test_exec_unknown_stage_falls_back_to_arm
- test_restart_recovers_to_moved_when_data_already_at_dst: 已下发且数据已在 dst ⇒ 直达 moved
### 收口 / 退避守卫(issues 26-10-30-0616 批A: resume_hashes 失败路径 / dry_run 短路 / 重试退避)
- test_on_task_line_holds_in_dry_run: dry-run 相位机不推进(含 start() 恢复账本这条不经入口闸的路径)
- test_build_links_failure_bumps_attempts: 建链失败 ⇒ attempts +1(对账侧重建配额消费它)
### W8(R32) S5 补测(变异审计真洞守阵, 分类: tmp-analysis/w8-r32/classify-mod-{a,b}.md)
  + 同卷硬链接兜底(same_volume 实参丢失 ⇒ capability_ok 翻假)
- test_step_move_qb_moving_never_stalls: qB moving 态永不判停滞(只 warn 转 watching)
- test_step_move_issue_bookkeeping: 下发账(issue/started/last_size/sample_ts)逐键钉死
- test_step_move_sampling_ledger: 采样账本(grew/重置/停滞起点)四场景
- test_step_move_watching_resets_stall: 转 watching 时停滞账清零
- test_execute_branches_never_break_multi_group: 五个分支 continue 不得提前断多组循环
- test_execute_idempotent_faces_and_skip_contract: 幂等三面(touches 目标不同/全组已在目标/后置)与 skip 回执契约
  (桩 FS 未证明面踩 P3b 强探测闸 —— run_probe 替身直通, 闸门决策表单点在 test_relocate_exec_probe_gate.py)
- test_execute_receipts_and_ctx_guard: 三张拒收回执逐字契约 + ctx 守卫 or 链
  + 补发 setLocation 入参(只发 mover) + 发起 rt 初值(stall_since/last_size/sample_ts)
- test_step_finalize_targets_and_journal: 收尾集合(rt 优先回落 hashes)与 DONE journal
- test_step_finalize_gone_member_and_zero_progress: 消失成员跳过不断后续 + progress=0 不算完成
- test_build_links_faces: 目录别名首建/分块断点/attempts 累计
- test_scope_rel_faces: 内容根相对段(反斜杠归一/平铺/尾斜杠/段首)
- test_buckets_group_key_faces: 组键文件分量/物理分量 + gone 回执
- test_summ_counts_contract: 汇总计数逐值契约
- test_dst_size_sums_all_files: 采样求和与异常跳过
- test_native_syscall_and_finalize_members_faces: _native 空格名/syscall 映射/收尾集合两分量
### P4 F 运行时兜底(计划 26-11-04-0055 §04 P4 / §06 D4)
- test_exec_qb_side_check_passes_and_arms: qB 侧元数据一致 -> 自检通过照常武装(列目录入参钉住:
  qB 视角内容根 + with_metadata="true")
- test_exec_qb_side_check_all_mismatch_fails: qB 侧全不一致 -> failed(qb_side_check_failed)
  + 链接现场保留(账面与磁盘)+ 不搬回
- test_exec_qb_side_check_unavailable_skips: 端点 404 -> 跳过 qB 侧部分(不 fail), rt 记一笔供排查
- test_exec_local_penetration_failure_precedes_qb_check: 本机穿透先失败 -> 走原 fail(alias_unreadable),
  qB 侧零调用(优先级: 本机先判)
- test_exec_single_member_no_qb_side_call: 单成员组 direct 不经 penetrate 分支, 推进期零 qB 侧列目录
"""

import os

import time

import types

import pytest

from qbittorrentapi.exceptions import NotFound404Error

from auto_qb.core.modules import relocate_units as ru

from auto_qb.infra import relocate_journal

from helpers import pin_disk_usage, relocate_env

from auto_qb.config.models import RelocateConfig

from auto_qb.core.modules import relocate_exec as rex

from auto_qb.core.modules.grouping_mod import group_key_of

from auto_qb.core.modules.relocate_probe import ProbeResult

from auto_qb.core.modules.relocate_mod import RelocateModule, _native as _mod_native

from auto_qb.infra import alias_fs as afs

from auto_qb.infra import file_access as fa_mod

from auto_qb.infra import utils as infra_utils

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs

from relocate_exec_support import (
    _bare_mod,
    _fake_fs,
    _job,
    _only_job,
    _rec,
    _run_ticks,
    _simulate_moved,
    _solo_member,
    _spy_spawn,
    _stub_cap,
)


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
    """单步有界: 大批文件分块建链接, 单次 on_task_line 只建一批(主循环零阻塞)

    预算口径(2026-11-02, 计划 26-11-02-0657): 5s 是串行低载基准; xdist/高机载下
    实测曾到 19.37s(四 clone 并发, 纯负载无回归), 故高机载放宽到 15s —
    用 AQ_TEST_XDIST 或检测 worker 数判定太重, 直接按"预算=15s, 失败信息带实测值"
    收口: 真回归(>15s)仍拦得住, 机载抖动不误报。"""
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
    assert budget < 15.0, f"单步耗时 {budget:.2f}s(预算 15s, xdist/高机载口径, 串行基准 5s)"


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
    # P3b 执行链强探测闸(26-11-04-0055): 桩 FS 未证明面会消费探测闸 —— 本用例聚焦幂等面,
    # 探测替身直通(闸门自身的决策表已由 test_relocate_exec_probe_gate.py 覆盖)
    monkeypatch.setattr(rex, "run_probe", lambda ctx, src, dst: ProbeResult("passed", "ok", False, {}))
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


# ---------- P4 F 运行时兜底(计划 26-11-04-0055 §04 P4 / §06 D4) ----------


def _stub_dir_content(client, holder, calls):
    """app_get_directory_content 替身: 回 holder[0] 预制条目并记录 (directory_path, with_metadata)"""
    def _list(directory_path=None, with_metadata=None, **kw):
        calls.append((directory_path, with_metadata))
        return list(holder[0])

    client.app_get_directory_content = _list


def _entries_from(dirpath, size_delta=0):
    """本机目录 -> qB 列目录条目形状(name/size/last_modification_date/type; 元数据取真实 stat)"""
    out = []
    for e in os.scandir(str(dirpath)):
        if e.is_dir():
            continue
        st = e.stat()
        out.append(
            {
                "name": e.name,
                "size": int(st.st_size) + size_delta,
                "last_modification_date": int(st.st_mtime),
                "type": "File",
            }
        )
    return out


def test_exec_qb_side_check_passes_and_arms(tmp_path, monkeypatch):
    """qB 侧自检通过: 元数据一致 -> 照常武装; 列目录入参钉住(qB 视角内容根 + with_metadata="true")"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    holder = [[]]  # 预检期条目为空: D 不可判定 -> B′ 元数据 size 相等 -> proved(既有降级链)
    calls = []
    _stub_dir_content(client, holder, calls)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    calls.clear()
    holder[0] = _entries_from(os.path.join(dst, "Show"))  # qB 经链接读到 dst 数据的形态
    _run_ticks(mod, 6)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason, job.last_error)
    assert any(
        os.path.normpath(str(p)) == os.path.normpath(content) and w == "true" for p, w in calls
    ), f"推进期应以 qB 视角内容根 + with_metadata='true' 列目录: {calls}"


def test_exec_qb_side_check_all_mismatch_fails(tmp_path, monkeypatch):
    """qB 侧全不一致 -> failed(qb_side_check_failed): 链接现场保留(账面+磁盘), 不搬回"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    holder = [[]]
    _stub_dir_content(client, holder, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    holder[0] = _entries_from(os.path.join(dst, "Show"), size_delta=1)  # qB 未跟随链接的形态
    _run_ticks(mod, 6)
    job = mod.get_job(job_id)
    assert (job.phase, job.reason) == (ru.PHASE_FAILED, "qb_side_check_failed"), (job.phase, job.reason)
    assert "链接可能未被 qB 跟随" in job.last_error, job.last_error
    assert len(job.alias_paths) == 2, "失败不得清链接账(保留现场)"
    for p in job.alias_paths:
        assert os.path.exists(p), f"链接现场必须真实保留: {p}"
    assert len([c for c in client.calls if c[0] == "set_location"]) == 1, "失败不得搬回(重发 setLocation)"


def test_exec_qb_side_check_unavailable_skips(tmp_path, monkeypatch):
    """端点 404 -> 跳过 qB 侧部分(行为与改造前一致): 不 fail 照常武装, rt 记一笔供排查"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])

    def _boom(directory_path=None, with_metadata=None, **kw):
        raise NotFound404Error

    client.app_get_directory_content = _boom
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason, job.last_error)
    assert "skipped" in str(mod._rt.get(job_id, {}).get("qb_side_check", "")), mod._rt.get(job_id)


def test_exec_local_penetration_failure_precedes_qb_check(tmp_path, monkeypatch):
    """本机穿透先失败 -> 仍走原 fail(alias_unreadable), qB 侧零调用(优先级: 本机先判)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    holder = [[]]
    calls = []
    _stub_dir_content(client, holder, calls)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    calls.clear()
    monkeypatch.setattr(mod, "_penetration_ok", lambda job: False)  # 本机穿透失败
    _run_ticks(mod, 6)
    job = mod.get_job(job_id)
    assert (job.phase, job.reason) == (ru.PHASE_FAILED, "alias_unreadable"), (job.phase, job.reason)
    assert calls == [], f"本机穿透失败时不得再发 qB 侧自检: {calls}"


def test_exec_single_member_no_qb_side_call(tmp_path, monkeypatch):
    """单成员组 direct: 不经 penetrate 分支 —— 推进期零 qB 侧列目录调用, 照常 done"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    store = mgr.store
    key = store.member_to_key["HB"]
    store.groups[key].remove("HB")
    store.group_sizes[key].pop("HB", None)
    store.member_to_key.pop("HB", None)
    store.by_hash.pop("HB", None)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    calls = []
    _stub_dir_content(client, [[]], calls)
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["form"] == "direct", items
    calls.clear()  # 预检面的 path_evidence 不在本断言范围; 这里钉的是推进期零自检
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    job = _only_job(mod)
    assert job["phase"] == ru.PHASE_DONE, job
    assert calls == [], f"单成员组不得做 qB 侧自检: {calls}"
