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
"""
import os
import time
import types

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.infra import relocate_journal

from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

FREE = 1 << 40


def _pin_disk_usage(monkeypatch, free=FREE):
    from auto_qb.infra import file_access as fa_mod

    monkeypatch.setattr(
        fa_mod.LocalFileAccess,
        "disk_usage",
        lambda self, path: fa_mod.DiskUsage(total=free * 10, used=0, free=free),
    )


def _make_env(td, file_count=2, subdir="Show", state="uploading", progress=1.0):
    """真临时目录 + 双成员组; 返回 (mgr, client, src, dst, content, files)

    组内两个成员共享同一份物理文件(HA/HB), 初始做种态(会被暂停), 目标卷已存在。
    """
    mgr = make_manager(os.path.join(str(td), "state.json"))
    client = FakeClient()
    mgr.client = client
    src = os.path.join(str(td), "src")
    dst = os.path.join(str(td), "dst")
    content = os.path.join(src, subdir)
    os.makedirs(content)
    os.makedirs(dst)
    files = []
    for i in range(file_count):
        name = f"{subdir}/e{i:02d}.mkv"
        with open(os.path.join(content, f"e{i:02d}.mkv"), "wb") as f:
            f.write(b"x" * 64)
        files.append(_fake_file(name, 64))
    client.files_map["HA"] = list(files)
    client.files_map["HB"] = list(files)
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=src, progress=progress, state=state),
        FakeTorrent(hash="HB", name="Show", save_path=src, progress=progress, state=state),
    ]
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    mgr.store.server_state = {"free_space_on_disk": FREE}
    mgr.config.data_dir = os.path.join(str(td), "data")
    mgr.config.relocate.enabled = True
    return mgr, client, src, dst, content, files


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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path, file_count=2, state="uploading")
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path, file_count=5)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
    mod = mgr.host.get("relocate")
    mod._dry = True
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "ok" and any("dry-run" in n for n in items[0]["notes"])
    assert client.calls == [], client.calls
    assert mod.active_jobs() and mod.active_jobs()[0].phase == ru.PHASE_MOVING


def test_exec_step_budget(tmp_path, monkeypatch):
    """单步有界: 大批文件分块建链接, 单次 on_task_line 只建一批(主循环零阻塞)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path, file_count=450)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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


def test_reconcile_respawn_guardian_on_stale_heartbeat(tmp_path, monkeypatch):
    """armed + 链接在 + 心跳过期 ⇒ 重拉 guardian"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_ARMED, "ts": time.time() - 999})
    spawned.clear()
    mod.on_task_line()
    assert spawned == [job_id]


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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    mgr, client, src, dst, content, files = _make_env(tmp_path)
    mgr.config.relocate.enabled = False
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": dst, "cmd_id": "c1"}))
    mgr.web.consume_commands()
    assert client.calls == [("set_location", dst)], client.calls
    assert mgr.host.get("relocate").jobs_view() == [], "关时不得产生 job"


def test_entry_single_and_bulk_create_jobs(tmp_path, monkeypatch):
    """开关开: 单件与批量都产生 job, 回执 truth 计数可读"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path, file_count=2)
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

    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path, file_count=2)
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
    mgr2, client2, src2, dst2, content2, files2 = _make_env(tmp_path / "b", file_count=2)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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


def test_skip_check_skips_during_relocation(tmp_path, monkeypatch):
    """搬迁窗口: relocating 登记内的种子跳检直接 skip(不删除/不重加)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path, state="uploading")
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _make_env(tmp_path)
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
