"""test_relocate_paths 测试计划: P3-P6 的分支/退化路径补齐(计划 26-10-18-1604)

主链路在 test_relocate_exec(正常/停滞/watching/链接失败/断连)与 test_grouping_relocate(P4 六守阵);
本文件只收「一次只走一条支路」的边角: 目录别名形态、穿透校验失败、撤销拒绝、对账三条处置、
guardian 的退化路径、journal 落盘与 pid 锁、CLI 入口。目的有二: 分支不留裸奔, 覆盖率不破 98% 门槛。

## 测试计划(每个测试函数一条)
- test_journal_roundtrip_and_heartbeat: spec/journal 往返 + 心跳年龄(无 journal = inf) + 坏文件读 None
- test_journal_pid_lock: 同进程重复抢占 -> False; 释放后可再抢
- test_exec_dir_alias_flow: F>=阈值 + 专属子目录 -> 目录别名(需确认)整条建链并武装
- test_exec_dir_alias_non_empty_root_rolls_back: 内容根非空 -> 别名建不出 -> 转收尾
- test_exec_penetration_failure_keeps_scene: 穿透校验失败 -> failed(alias_unreadable) 且链接保留
- test_exec_reject_and_pause_failure: 形态拒绝(空文件表)/ 暂停失败 -> blocked
- test_precheck_empty_file_table_skips_representative_probe: 空文件表不把 save_path(目录)当代表文件探测(POSIX 目录 nlink>=2 的 CI 红)
- test_guardian_process_names_parsing: tasklist/ps//proc 三条进程表解析 + 平台分派 + 读不到 ⇒ 空
- test_exec_spawn_argv: 真实拉起入口的 argv(detached 单点)
- test_cancel_rejects_unknown_and_failure: 未知 job -> blocked; 搬回被拒 -> blocked + failed 账
- test_reconcile_revert_redelist_done_external: 对账三条处置分支(撤销意图/重删/外部完成)
- test_task_line_exception_isolated: 单 job 抛异常 -> failed(internal_error), 不拖垮任务线
- test_qb_up_probe: 客户端可读 -> True; 无 api -> False
- test_guardian_degenerate_paths: no_spec / already_running / verify 不齐 / 超时退出
- test_guardian_cli_main: main() 返回码与打印(job 不存在 = 1)
- test_guardian_helpers: _port_refused / _verify_dst / _delete_links / _proc_absent 退化
"""
import os
import time

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.infra import alias_fs, relocate_journal
from auto_qb.tools import finalize_watch as fw

from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

FREE = 1 << 40


def _pin_disk_usage(monkeypatch, free=FREE):
    from auto_qb.infra import file_access as fa_mod

    monkeypatch.setattr(
        fa_mod.LocalFileAccess,
        "disk_usage",
        lambda self, path: fa_mod.DiskUsage(total=free * 10, used=0, free=free),
    )


def _env(td, file_count=2, subdir="Show", state="pausedUP"):
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
        rel = f"{subdir}/e{i:02d}.mkv"
        with open(os.path.join(src, *rel.split("/")), "wb") as f:
            f.write(b"x" * 64)
        files.append(_fake_file(rel, 64))
    client.files_map["HA"] = list(files)
    client.files_map["HB"] = list(files)
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=src, progress=1.0, state=state),
        FakeTorrent(hash="HB", name="Show", save_path=src, progress=1.0, state=state),
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
    for f in files:
        p = os.path.join(dst, *f.name.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(b"x" * int(f.size))
        try:
            os.remove(os.path.join(content, os.path.basename(f.name)))
        except OSError:
            pass
    rec = mgr.store.by_hash[mover]
    rec.save_path = dst
    rec.state = "pausedUP"


def _spy_spawn(mod, calls):
    mod._spawn = lambda data_dir, job_id: calls.append(job_id)


def test_journal_roundtrip_and_heartbeat(tmp_path):
    """spec/journal 往返; 心跳年龄(无 journal = inf); 坏 JSON 读 None"""
    d = str(tmp_path / "data")
    relocate_journal.write_spec(d, "j1", {"job_id": "j1", "files": [["a", 1]]})
    assert relocate_journal.read_spec(d, "j1")["job_id"] == "j1"
    relocate_journal.write_journal(d, "j1", {"phase": "armed"})
    j = relocate_journal.read_journal(d, "j1")
    assert j["phase"] == "armed" and j["ts"] > 0
    assert relocate_journal.heartbeat_age(d, "j1") < 5
    assert relocate_journal.heartbeat_age(d, "missing") == float("inf")
    assert relocate_journal.heartbeat_age(d, "j1", now=time.time() + 100) > 90
    with open(relocate_journal.journal_path(d, "j1"), "w", encoding="utf-8") as f:
        f.write("{broken")
    assert relocate_journal.read_journal(d, "j1") is None


def test_journal_pid_lock(tmp_path):
    """pid 锁: 同进程重复抢占失败(已有活进程); 释放后可再抢"""
    d = str(tmp_path / "data")
    assert relocate_journal.acquire_pid(d, "j1") is True
    assert relocate_journal.acquire_pid(d, "j1") is False
    relocate_journal.release_pid(d, "j1")
    assert relocate_journal.acquire_pid(d, "j1") is True
    relocate_journal.release_pid(d, "missing")  # 幂等


def test_exec_dir_alias_flow(tmp_path, monkeypatch):
    """目录别名形态: F>=阈值 + 专属子目录 -> confirm; 确认后整条别名建链并武装"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path, file_count=9)
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    first = mod.relocate_execute(["HA"], dst, confirm=False)
    assert first[0]["cls"] == "confirm" and first[0]["form"] == "dir_alias", first
    items = mod.relocate_execute(["HA"], dst, confirm=True)
    assert items[0]["cls"] == "started", items
    _simulate_moved(mgr, dst, files, content)
    for _ in range(6):
        mod.on_task_line()
    job = mod.get_job(items[0]["job_id"])
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason, job.last_error)
    assert len(job.alias_paths) == 1
    assert os.path.isdir(job.alias_paths[0]) and os.listdir(job.alias_paths[0])


def test_exec_dir_alias_non_empty_root_rolls_back(tmp_path, monkeypatch):
    """目录别名建不出(内容根还非空) -> 删已建/转收尾, 不搬回"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path, file_count=9)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    items = mod.relocate_execute(["HA"], dst, confirm=True)
    _simulate_moved(mgr, dst, files, content)
    with open(os.path.join(content, "leftover.nfo"), "wb") as f:
        f.write(b"junk")  # 内容根非空 -> 目录别名不可建
    for _ in range(4):
        mod.on_task_line()
    job = mod.get_job(items[0]["job_id"])
    assert job.phase == ru.PHASE_REMOVED and job.reason == "alias_partial", (job.phase, job.reason)
    assert list(job.alias_paths) == []


def test_exec_penetration_failure_keeps_scene(tmp_path, monkeypatch):
    """穿透校验失败(链接建了但读不到) -> failed(alias_unreadable), 链接现场保留"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    for _ in range(3):
        mod.on_task_line()  # moved -> verify -> link
    # 本机同卷走硬链接: 删目标路径不产生悬空(数据仍经链接可达), 故直接注入「穿透读不到」
    monkeypatch.setattr(mod, "_penetration_ok", lambda job: False)
    mod.on_task_line()  # penetrate -> fail
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FAILED and job.reason == "alias_unreadable", (job.phase, job.reason)
    assert list(job.alias_paths), "失败要保留现场(便于排查), 不得删链接"


def test_exec_reject_and_pause_failure(tmp_path, monkeypatch):
    """形态拒绝(文件表为空) -> blocked(form); 暂停失败 -> blocked(pause_failed)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    orig = type(client).torrents_files
    monkeypatch.setattr(type(client), "torrents_files", lambda self, h: [])
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "blocked", items
    monkeypatch.setattr(type(client), "torrents_files", orig)
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None
    # 暂停失败(成员运行中)
    mgr.store.by_hash["HA"].state = "uploading"
    mgr.store.by_hash["HB"].state = "uploading"

    def _boom(**kw):
        raise RuntimeError("qB 拒绝暂停")

    monkeypatch.setattr(client, "torrents_pause", _boom)
    items2 = mod.relocate_execute(["HA"], dst)
    assert items2[0]["cls"] == "blocked" and items2[0]["reasons"][0]["gate"] == "pause_failed", items2


def test_precheck_empty_file_table_skips_representative_probe(tmp_path, monkeypatch):
    """空文件表(读不到文件列表): 没有代表文件, 不得拿 save_path 这个目录当代表文件去 lstat

    !POSIX 目录 st_nlink 恒 >= 2(Linux CI 实测): 旧写法落到 `names[0]` 直接 IndexError;
    Windows 目录 nlink=1 根本走不到那条分支 —— 本地全绿、CI 全红。
    """
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    monkeypatch.setattr(type(client), "torrents_files", lambda self, h: [])
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None

    def _norm(p):
        s = str(p)
        if s.startswith("\\\\?\\"):
            s = s[4:]
        return os.path.normcase(os.path.normpath(s))

    probed = []
    real_lstat = os.lstat

    def _lstat(path):
        probed.append(_norm(path))
        return real_lstat(path)

    monkeypatch.setattr(os, "lstat", _lstat)
    item = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and any("文件列表为空" in r["text"] for r in item["reasons"]), item
    assert _norm(src) not in probed, probed


def test_exec_spawn_argv(tmp_path, monkeypatch):
    """真实拉起入口: detached + 无窗口, argv 走 -m auto_qb.tools.finalize_watch"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    seen = {}

    class _P:
        def __init__(self, args, **kw):
            seen["args"] = args
            seen["kw"] = kw

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", _P)
    mod._spawn(str(tmp_path / "data"), "jr-x")
    assert seen["args"][1:4] == ["-m", "auto_qb.tools.finalize_watch", "--data-dir"]
    assert "jr-x" in seen["args"]
    assert seen["kw"]["stdin"] is subprocess.DEVNULL


def test_cancel_rejects_unknown_and_failure(tmp_path, monkeypatch):
    """撤销: 未知 job -> blocked; qB 拒绝搬回 -> blocked + 账落 failed(cancel_failed)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    r = mod.relocate_cancel("nope", cost_confirmed=True)
    assert r["cls"] == "blocked" and r["reasons"][0]["gate"] == "gone"

    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mod._set_job(ru.RelocateJob(**{**mod.get_job(job_id).__dict__, "phase": ru.PHASE_ARMED}))

    def _boom(**kw):
        raise RuntimeError("搬回被拒")

    monkeypatch.setattr(client, "torrents_set_location", _boom)
    r2 = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert r2["cls"] == "blocked" and mod.get_job(job_id).reason == "cancel_failed"


def test_reconcile_revert_redelist_done_external(tmp_path, monkeypatch):
    """对账三条处置: 撤销删除意图 / guardian 重删 / 已被外部完成"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    for _ in range(6):
        mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED

    # 撤销删除意图: journal=removing + 链接在 + qB 在
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REMOVING, "ts": time.time()})
    spawned.clear()
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED
    assert relocate_journal.read_journal(str(tmp_path / "data"), job_id)["phase"] == ru.PHASE_ARMED

    # guardian 重删: journal=removing + 链接在 + qB 不在
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REMOVING, "ts": time.time()})
    mod._qb_up = lambda: False
    spawned.clear()
    mod.on_task_line()
    assert spawned == [job_id], spawned

    # 已被外部完成: 全组都在 dst
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_ARMED, "ts": time.time()})
    mod._qb_up = lambda: True
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_DONE


def test_task_line_exception_isolated(tmp_path, monkeypatch):
    """单 job 抛异常 -> 该 job failed(internal_error), 不影响其它 job/任务线"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    monkeypatch.setattr(mod, "_advance", lambda job: (_ for _ in ()).throw(RuntimeError("boom")))
    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FAILED and job.reason == "internal_error"


def test_qb_up_probe(tmp_path):
    """qB 在? 探测: 客户端可读 -> True(缓存复用); 无 api -> False"""
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    assert mod._qb_up() is True
    assert mod._qb_up() is True  # 缓存命中分支
    mod._ctx.api = None
    mod._qb_up_cache = None
    assert mod._qb_up() is False


def test_guardian_degenerate_paths(tmp_path, monkeypatch):
    """guardian 退化: 无 spec / pid 已占 / 数据不齐 / 超时退出"""
    d = str(tmp_path / "data")
    assert fw.run(d, "nope") == "no_spec"

    relocate_journal.write_spec(d, "j1", {"job_id": "j1", "dst": str(tmp_path), "files": [], "alias_paths": []})
    assert relocate_journal.acquire_pid(d, "j1") is True
    assert fw.run(d, "j1") == "already_running"
    relocate_journal.release_pid(d, "j1")

    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("explorer.exe", ))
    monkeypatch.setattr(fw, "_port_refused", lambda *a, **k: True)
    ticks = {"n": 0}

    def _clock():
        ticks["n"] += 1
        return 1000.0 + ticks["n"] * 10

    # 数据不齐(files 空) -> verify_mismatch, 不删链接
    assert fw.run(d, "j1", stable=30.0, poll=0.0, clock=_clock, sleep=lambda s: None) == "verify_mismatch"

    # qB 一直在 -> 超时退出
    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("qbittorrent.exe", ))
    assert fw.run(d, "j1", stable=30.0, poll=0.0, max_wait=5.0, clock=_clock, sleep=lambda s: None) == "timeout"


def test_guardian_cli_main(tmp_path, capsys):
    """CLI 入口: job 不存在 -> 返回 1 并打印结论"""
    rc = fw.main(["--data-dir", str(tmp_path / "data"), "--job", "nope"])
    assert rc == 1
    assert "no_spec" in capsys.readouterr().out


def test_guardian_helpers(tmp_path, monkeypatch):
    """guardian 辅助: 端口拒连 / 目标校验 / 删链接幂等 / 进程表读不到不算退出"""
    assert fw._port_refused("127.0.0.1", 0) is True
    assert fw._port_refused("127.0.0.1", 1, timeout=0.2) is True
    assert fw._proc_absent(()) is False  # 判不出 -> 未证明
    # P7: 实例级判定 —— 同机还有别的 qB 进程时, 端点拒连仍证明「该实例已退出」
    # (旧实现按全机名册判, 日常实例在跑 => 恒「在」=> 收尾永不触发)
    assert fw._proc_absent(("qbittorrent.exe", "python.exe"), "127.0.0.1", 1) is True
    # P7: _alive 零副作用 —— Windows 上 os.kill(pid,0) 会 TerminateProcess 掉被探测进程
    # (guardian 重拉自噬循环的真因); 探测自身进程必须返回 True 且不得终止它
    from auto_qb.infra import relocate_journal as rj
    assert rj._alive(os.getpid()) is True
    assert rj._alive(999999) is False
    assert fw._proc_absent(("qbittorrent.exe", ), "", 0) is False  # 无端口证据 -> 退回名册
    assert fw._proc_absent(("explorer.exe", )) is True
    assert fw._verify_dst({"dst": str(tmp_path), "files": []}) is False
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x" * 4)
    assert fw._verify_dst({"dst": str(tmp_path), "files": [["a.mkv", 4]]}) is True
    assert fw._verify_dst({"dst": str(tmp_path), "files": [["a.mkv", 5]]}) is False
    assert fw._delete_links({"alias_paths": [str(tmp_path / "ghost")]}) == 0


def test_guardian_process_names_parsing(monkeypatch):
    """进程表解析: tasklist CSV 取首列 / POSIX 两支解析 / 平台分派 / 读不到 ⇒ 空(未证明)

    !分派不能按 Windows 写死: CI 跑在 ubuntu-latest, `_qb_process_names` 走 /proc(或 ps),
    只调 tasklist 的写法在 POSIX 上拿到的是**真机进程名**, 断言恒红(Linux CI 实测)。
    """
    import io
    import subprocess

    class _R:
        stdout = ('"qbittorrent.exe","1234","Console","1","10,000 K"\n'
                  '"explorer.exe","9","Console","1","1 K"\n')

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())
    has_proc = os.path.isdir("/proc")  # POSIX 分派判据(下面会把 isdir 替掉, 先取真值)
    # tasklist 解析本体与平台无关: 只取引号内首列(不真起子进程)
    names = fw._names_from_tasklist()
    assert "qbittorrent.exe" in names and "explorer.exe" in names
    assert fw._proc_absent(names) is False

    # POSIX 两支解析(真函数 + 替身输出): ps 逐行取名字; /proc 逐 pid 读 comm
    assert any("qbittorrent" in n for n in fw._names_from_ps())
    monkeypatch.setattr(fw.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(fw.os, "listdir", lambda p: ["1", "self", "12"])
    monkeypatch.setattr(fw, "open", lambda p, *a, **k: io.StringIO("qbittorrent-nox\n"), raising=False)  # 每次新句柄
    assert fw._names_from_proc() == ("qbittorrent-nox", "qbittorrent-nox")

    # 分派: 按平台选一支(三条来源全换替身, 不读真机进程表)
    picks = []

    def _pick(tag):
        picks.append(tag)
        return names

    monkeypatch.setattr(fw, "_names_from_tasklist", lambda: _pick("tasklist"))
    monkeypatch.setattr(fw, "_names_from_proc", lambda: _pick("proc"))
    monkeypatch.setattr(fw, "_names_from_ps", lambda: _pick("ps"))
    assert fw._qb_process_names() == names
    expect = "tasklist" if os.name == "nt" else ("proc" if has_proc else "ps")
    assert picks == [expect], picks

    # 进程表读不到 -> 空(未证明): 三条来源的异常都要被吞掉(按平台只会走到选中那支)
    def _boom(*a, **k):
        raise OSError("no process table")

    for _slot in ("_names_from_tasklist", "_names_from_proc", "_names_from_ps"):
        monkeypatch.setattr(fw, _slot, _boom)
    assert fw._qb_process_names() == ()


def test_finalize_polling_and_timeout(tmp_path, monkeypatch):
    """收尾轮询: 成员未到位/进度未回 1 继续等; 超 finalize_timeout ⇒ failed"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    for _ in range(6):
        mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED

    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REMOVED, "ts": time.time()})
    mod._remove_links(mod.get_job(job_id).alias_paths)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].state = "missingFiles"
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_FINALIZING

    # 成员未到目标 -> 继续等(不 done)
    mgr.store.by_hash["HB"].save_path = src
    mgr.store.by_hash["HB"].progress = 0.4
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_FINALIZING

    # 超时 -> failed(finalize_timeout)
    mgr.config.relocate.finalize_timeout = 0.001
    mod._rt[job_id]["finalize_ts"] = time.time() - 10
    mod.on_task_line()
    assert mod.get_job(job_id).reason == "finalize_timeout"


def test_execute_early_returns(tmp_path, monkeypatch):
    """执行入口退化入参: 未启用 / 空 hashes / 空目标 / qB 不可用 各回 blocked 且零副作用"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    mgr.config.relocate.enabled = False
    assert mod.relocate_execute(["HA"], dst)[0]["reasons"][0]["gate"] == "disabled"
    mgr.config.relocate.enabled = True
    assert mod.relocate_execute([], dst)[0]["reasons"][0]["gate"] == "param"
    assert mod.relocate_execute(["HA"], "")[0]["reasons"][0]["gate"] == "param"
    mgr.ctx.api = None
    assert mod.relocate_execute(["HA"], dst)[0]["reasons"][0]["gate"] == "unavailable"
    assert mod.jobs_view() == []


def test_guardian_spawn_and_link_failure_paths(tmp_path, monkeypatch):
    """守护进程拉起失败/规格落盘失败/删链接异常 三条退化: 只告警不中断(下轮对账重试)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    job = mod.get_job(job_id)

    monkeypatch.setattr(relocate_journal, "write_spec", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    assert mod._spawn_guardian(job) is False
    monkeypatch.undo()

    def _boom(*a, **k):
        raise OSError("cannot spawn")

    monkeypatch.setattr(mod, "_spawn", _boom)
    assert mod._spawn_guardian(job) is False
    monkeypatch.undo()

    # 删链接异常: 计 0 且不抛(幂等靠下次对账)
    monkeypatch.setattr(alias_fs, "remove_alias", lambda p: (_ for _ in ()).throw(OSError("busy")))
    link = os.path.join(content, "busy.mkv")
    with open(link, "wb") as f:
        f.write(b"x")
    os.link(link, os.path.join(str(tmp_path), "peer.mkv"))
    assert mod._remove_links([link, ""]) == 0
    monkeypatch.undo()

    # 端口配置非法 -> 0(不炸)
    mgr.config.qbittorrent = type("Q", (), {"host": "", "port": "abc"})()
    assert mod._qb_port() == 0 and mod._qb_host() == "127.0.0.1"
    # dry_run 走上下文回退
    mod._dry = False
    mgr.ctx.dry_run = True
    assert mod._dry_run() is True


def test_module_guard_branches(tmp_path, monkeypatch):
    """模块壳的退化守卫: 上下文缺失 / 坏账条目 / stop 落账异常 / 任务线未启用 都不炸"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")

    # stop: 落账抛错只 debug(退出路径不抛)
    monkeypatch.setattr(mod, "_persist", lambda: (_ for _ in ()).throw(OSError("state busy")))
    mod.stop()
    monkeypatch.undo()

    # 无上下文: state 容器为空 dict; relocating 同步/任务线直接返回
    bare = type(mod)()
    assert bare._state_jobs() == {}
    bare._sync_relocating()
    bare.on_task_line()
    assert bare.resolve_physical("") == ""

    # 坏账条目(形状不符)跳过, 好条目照常恢复
    mgr.state["relocate"] = {"jobs": {"bad": {"hashes": []}}}
    assert type(mod)(mgr.ctx)._load_jobs() == 0
    mgr.state["relocate"]["jobs"]["ok"] = ru.job_to_dict(
        ru.RelocateJob(job_id="ok", hashes=("HA", ), mover="HA", src=src, dst=dst, scope=content)
    )
    assert type(mod)(mgr.ctx)._load_jobs() == 1


def test_guardian_cli_rc_zero_on_running(tmp_path, capsys):
    """CLI: 已有 guardian 在跑 -> 返回 0(不重复拉起)"""
    d = str(tmp_path / "data")
    relocate_journal.write_spec(d, "j1", {"job_id": "j1"})
    assert relocate_journal.acquire_pid(d, "j1") is True
    rc = fw.main(["--data-dir", d, "--job", "j1"])
    assert rc == 0 and "already_running" in capsys.readouterr().out


def test_guardian_retires_when_job_closed(tmp_path, monkeypatch):
    """已收口(撤销/完成)的 job: guardian 读到 journal 的 done/cancelled 即退出, 不删链接"""
    d = str(tmp_path / "data")
    link = tmp_path / "a.mkv"
    link.write_bytes(b"x")
    relocate_journal.write_spec(d, "j1", {"job_id": "j1", "files": [["a.mkv", 1]], "alias_paths": [str(link)]})
    relocate_journal.write_journal(d, "j1", {"phase": "cancelled"})
    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("explorer.exe", ))
    monkeypatch.setattr(fw, "_port_refused", lambda *a, **k: True)
    assert fw.run(d, "j1", poll=0.0, sleep=lambda s: None) == "stopped"
    assert os.path.exists(link), "已撤销的 job 不得再动链接(撤销侧已删过)"


def test_cancel_and_finalize_close_journal(tmp_path, monkeypatch):
    """撤销/收尾完成都会把 journal 写成终态, 供 guardian 退休"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = _env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    for _ in range(6):
        mod.on_task_line()
    mod.relocate_cancel(job_id, cost_confirmed=True)
    assert relocate_journal.read_journal(str(tmp_path / "data"), job_id)["phase"] == ru.PHASE_CANCELLED
