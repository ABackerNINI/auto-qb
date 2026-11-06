"""test_relocate_paths 测试计划: P3-P6 的分支/退化路径补齐(计划 26-10-18-1604; S4 相位模型重定义 26-11-05-0808)

主链路在 test_relocate_exec(正常/停滞/watching/链接失败/断连)与 test_grouping_relocate(P4 六守阵);
本文件只收「一次只走一条支路」的边角: 目录别名形态、穿透校验失败、撤销拒绝、对账处置、
arm spec 落盘退化、journal 落盘、daemon 拉起 argv、三证判据(随 finalize_watch.py 退役随迁
recycle_daemon)。目的有二: 分支不留裸奔, 覆盖率不破 98% 门槛。

S4(26-11-05-0808)退役面: 旧 guardian(finalize_watch)退化路径/CLI/pid 锁/per-job 心跳/
对账 revert-redelist-done_external 三支与 finalize 轮询超时全部随整链退役 —— 三证判据函数
随迁 recycle_daemon, 其单测在本文件保留(换 import 目标)。

## 测试计划(每个测试函数一条)
- test_journal_roundtrip: spec/journal 往返 + 坏文件读 None
- test_exec_dir_alias_flow: F>=阈值 + 专属子目录 -> 目录别名(需确认)整条建链并武装
- test_exec_dir_alias_non_empty_root_rolls_back: 内容根非空 -> 别名建不出 -> 回 armed 交对账重建
- test_exec_penetration_failure_keeps_scene: 穿透校验失败 -> failed(alias_unreadable) 且链接保留
- test_exec_reject_and_pause_failure: 形态拒绝(空文件表)/ 暂停失败 -> blocked
- test_precheck_empty_file_table_skips_representative_probe: 空文件表不把 save_path(目录)当代表文件探测(POSIX 目录 nlink>=2 的 CI 红)
- test_daemon_spawn_argv: 真实拉起入口的 argv(detached 单点, -m auto_qb.tools.recycle_daemon)
- test_cancel_rejects_unknown_and_failure: 未知 job -> blocked; 搬回被拒 -> blocked + failed 账
- test_reconcile_new_chain_faces: 对账新链三分支(journal rewritten 镜像合并 / 别名丢失重建 / 全员到 dst 核验过+零依赖收尾完成)
- test_task_line_exception_isolated: 单 job 抛异常 -> failed(internal_error), 不拖垮任务线
- test_qb_up_probe: 客户端可读 -> True; 无 api -> False
- test_daemon_three_proofs_helpers: _port_refused / _proc_absent 双判合取(评审 #6: 名册见
  qB + 端口拒连不判缺席)+ _alive 零副作用
- test_daemon_process_names_parsing: tasklist/ps//proc 三条进程表解析 + 平台分派 + 读不到 ⇒ 空
- test_execute_early_returns
- test_arm_spec_and_daemon_failure_paths: spec 落盘失败只告警 / daemon 拉起异常被对账吞掉 / 删链接异常计 0
- test_cancel_close_journal: 撤销把 journal 写成终态
- test_module_guard_branches
"""
import os

from auto_qb.core.modules import relocate_units as ru
from auto_qb.infra import alias_fs, relocate_journal
from auto_qb.tools import recycle_daemon as rd

from helpers import pin_disk_usage, relocate_env


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
    # S4: 拉起面只剩实例级 _spawn_daemon(见 relocate_exec_support._spy_spawn); 本文件大多
    # 不关心记录, 只需不弹真进程
    mod._spawn_daemon = lambda *a, **k: calls.append(("daemon", ) + tuple(a))


def test_journal_roundtrip(tmp_path):
    """spec/journal 往返; 坏 JSON 读 None"""
    d = str(tmp_path / "data")
    relocate_journal.write_spec(d, "j1", {"job_id": "j1", "files": [["a", 1]]})
    assert relocate_journal.read_spec(d, "j1")["job_id"] == "j1"
    relocate_journal.write_journal(d, "j1", {"phase": "armed"})
    j = relocate_journal.read_journal(d, "j1")
    assert j["phase"] == "armed" and j["ts"] > 0
    with open(relocate_journal.journal_path(d, "j1"), "w", encoding="utf-8") as f:
        f.write("{broken")
    assert relocate_journal.read_journal(d, "j1") is None


def test_exec_dir_alias_flow(tmp_path, monkeypatch):
    """目录别名形态: F>=阈值 + 专属子目录 -> confirm; 确认后整条别名建链并武装"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=9)
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
    assert spawned, "武装后应确保回收 daemon 在位(S4 新链)"


def test_exec_dir_alias_non_empty_root_rolls_back(tmp_path, monkeypatch):
    """目录别名建不出(内容根还非空) -> 删已建/回 armed 交对账重建, 不搬回

    S4: 建链失败不再落 removed(旧链收尾相位已退役) —— 落 armed(alias_partial), 由对账
    REBUILD 带退避重建; 首建(attempts 1)与一次重建(attempts 2)后落退避窗口, 相位停在 armed。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=9)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    items = mod.relocate_execute(["HA"], dst, confirm=True)
    _simulate_moved(mgr, dst, files, content)
    with open(os.path.join(content, "leftover.nfo"), "wb") as f:
        f.write(b"junk")  # 内容根非空 -> 目录别名不可建
    for _ in range(4):
        mod.on_task_line()
    job = mod.get_job(items[0]["job_id"])
    assert job.phase == ru.PHASE_ARMED and job.reason == "alias_partial", (job.phase, job.reason)
    assert list(job.alias_paths) == []
    assert job.attempts == 2, job.attempts  # 首建 1 + 重建 1(其后落 REBUILD_BACKOFF 退避)
    leftovers = [p for p in job.alias_paths if os.path.exists(p)]
    assert leftovers == [], "已建链接必须删净"


def test_exec_penetration_failure_keeps_scene(tmp_path, monkeypatch):
    """穿透校验失败(链接建了但读不到) -> failed(alias_unreadable), 链接现场保留"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2)
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
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2)
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

    !平台差异(2026-10-30 修): 本用例按「os.lstat 有没有被叫到 save_path」取证, 而
    `os.path.realpath` 在 **POSIX 上是 Python 实现**(逐段 `os.lstat` 走), Windows 上走
    `nt._getfinalpathname` 不碰 `os.lstat`。于是同一条生产路径(内容根真实存在时做别名解析比较)
    在 Linux 上会额外 lstat 到 save_path, 把「代表文件探测」的取证污染成假红。这里把 realpath
    换成恒等 —— 取证对象是**代表文件探测**, 不是别名解析; 若 `if names:` 闸门被删, `names[0]`
    会立刻 IndexError, 本用例照样红。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    monkeypatch.setattr(type(client), "torrents_files", lambda self, h: [])
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None
    monkeypatch.setattr(os.path, "realpath", lambda p, **kw: p)  # 见 docstring「平台差异」

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


def test_daemon_spawn_argv(tmp_path, monkeypatch):
    """真实拉起入口: detached + 无窗口, argv 走 -m auto_qb.tools.recycle_daemon(S4 新链单点)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    seen = {}

    class _P:
        def __init__(self, args, **kw):
            seen["args"] = args
            seen["kw"] = kw

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", _P)
    mod._spawn_daemon(str(tmp_path / "data"), mgr.config.qbittorrent.host, int(mgr.config.qbittorrent.port))
    assert seen["args"][1:4] == ["-m", "auto_qb.tools.recycle_daemon", "--data-dir"], seen
    assert "--host" in seen["args"] and "--port" in seen["args"], seen
    assert seen["kw"]["stdin"] is subprocess.DEVNULL


def test_cancel_rejects_unknown_and_failure(tmp_path, monkeypatch):
    """撤销: 未知 job -> blocked; qB 拒绝搬回 -> blocked + 账落 failed(cancel_failed)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
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


def test_reconcile_new_chain_faces(tmp_path, monkeypatch):
    """对账新链三分支(S4): journal rewritten 镜像合并 / 别名丢失重建 / 全员到 dst 核验过+零依赖收尾完成

    - rewritten 镜像合并: daemon 翻 journal 相位 -> 主循环把 armed job 跟进 rewritten(只前进);
    - 别名丢失 + qB 在 -> REBUILD 重建回 armed(本轮建完 penetrate);
    - 全员已到 dst(journal rewritten) -> ACT_VERIFY 挂起: S4 前半不推进, 相位保持 rewritten。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    for _ in range(6):
        mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED

    # (1) rewritten 镜像合并: daemon 翻账 -> 对账拍把 armed 跟进 rewritten
    mod._qb_up = lambda: True
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REWRITTEN, "ts": 1.0})
    mod.on_task_line()
    assert mod.get_job(job_id).phase == ru.PHASE_REWRITTEN, "journal rewritten 必须合并进 job 镜像"

    # (2) 别名丢失 + qB 在 -> REBUILD: 重建回执行段(建链 -> 穿透 -> arm)
    mod._remove_links(mod.get_job(job_id).alias_paths)
    for _ in range(4):
        mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED, (job.phase, job.reason)
    for p in job.alias_paths:
        assert os.path.exists(p), p

    # (3) 全员已在 dst + journal rewritten -> ACT_VERIFY(S4b 落地): 核验过 + 删链门零依赖
    # -> 在线删别名 + 终态 done(journal 同步落终态, daemon 据此退休)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst
    relocate_journal.write_journal(str(tmp_path / "data"), job_id, {"phase": ru.PHASE_REWRITTEN, "ts": 2.0})
    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_DONE and job.reason == ru.REASON_FINALIZED, (job.phase, job.reason)
    assert job.alias_paths == (), "收尾完成后别名账清空"
    assert relocate_journal.read_journal(str(tmp_path / "data"), job_id)["phase"] == "done"


def test_task_line_exception_isolated(tmp_path, monkeypatch):
    """单 job 抛异常 -> 该 job failed(internal_error), 不影响其它 job/任务线"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    monkeypatch.setattr(mod, "_advance", lambda job: (_ for _ in ()).throw(RuntimeError("boom")))
    mod.on_task_line()
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_FAILED and job.reason == "internal_error"


def test_qb_up_probe(tmp_path):
    """qB 在? 探测: 客户端可读 -> True(缓存复用); 无 api -> False"""
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    assert mod._qb_up() is True
    assert mod._qb_up() is True  # 缓存命中分支
    mod._ctx.api = None
    mod._qb_up_cache = None
    assert mod._qb_up() is False


def test_daemon_three_proofs_helpers(tmp_path, monkeypatch):
    """三证判据(随 finalize_watch.py 退役随迁 recycle_daemon): 端口拒连 / 进程判定退化
    + _alive 零副作用(P7: Windows os.kill(pid,0) 自噬循环的守阵)"""
    assert rd._port_refused("127.0.0.1", 0) is True
    assert rd._port_refused("127.0.0.1", 1, timeout=0.2) is True
    assert rd._proc_absent(()) is False  # 判不出 -> 未证明(port=0 无端口证, 保守)
    # 评审 #6: 双判合取 —— 名册见 qB(任一实例)时即使端点拒连也不判缺席: WebUI 不可达
    # (被关/挂死/链路断)!= 进程不在, 假阳性进窗会在 qB 运行期改写 fastresume(N1 铁律);
    # 旧「端点拒连即实例级缺席」短路判据随本修退役
    assert rd._proc_absent(("qbittorrent.exe", "python.exe"), "127.0.0.1", 1) is False
    # P7: _alive 零副作用 —— Windows 上 os.kill(pid,0) 会 TerminateProcess 掉被探测进程;
    # 探测自身进程必须返回 True 且不得终止它
    assert relocate_journal._alive(os.getpid()) is True
    assert relocate_journal._alive(999999) is False
    assert rd._proc_absent(("qbittorrent.exe", ), "", 0) is False  # 无端口证据 -> 退回名册
    assert rd._proc_absent(("explorer.exe", )) is True


def test_daemon_process_names_parsing(monkeypatch):
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
    names = rd._names_from_tasklist()
    assert "qbittorrent.exe" in names and "explorer.exe" in names
    assert rd._proc_absent(names) is False

    # POSIX 两支解析(真函数 + 替身输出): ps 逐行取名字; /proc 逐 pid 读 comm
    assert any("qbittorrent" in n for n in rd._names_from_ps())
    monkeypatch.setattr(rd.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(rd.os, "listdir", lambda p: ["1", "self", "12"])
    monkeypatch.setattr(rd, "open", lambda p, *a, **k: io.StringIO("qbittorrent-nox\n"), raising=False)  # 每次新句柄
    assert rd._names_from_proc() == ("qbittorrent-nox", "qbittorrent-nox")

    # 分派: 按平台选一支(三条来源全换替身, 不读真机进程表)
    picks = []

    def _pick(tag):
        picks.append(tag)
        return names

    monkeypatch.setattr(rd, "_names_from_tasklist", lambda: _pick("tasklist"))
    monkeypatch.setattr(rd, "_names_from_proc", lambda: _pick("proc"))
    monkeypatch.setattr(rd, "_names_from_ps", lambda: _pick("ps"))
    assert rd._qb_process_names() == names
    expect = "tasklist" if os.name == "nt" else ("proc" if has_proc else "ps")
    assert picks == [expect], picks

    # 进程表读不到 -> 空(未证明): 三条来源的异常都要被吞掉(按平台只会走到选中那支)
    def _boom(*a, **k):
        raise OSError("no process table")

    for _slot in ("_names_from_tasklist", "_names_from_proc", "_names_from_ps"):
        monkeypatch.setattr(rd, _slot, _boom)
    assert rd._qb_process_names() == ()


def test_execute_early_returns(tmp_path, monkeypatch):
    """执行入口退化入参: 未启用 / 空 hashes / 空目标 / qB 不可用 各回 blocked 且零副作用"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
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


def test_arm_spec_and_daemon_failure_paths(tmp_path, monkeypatch):
    """arm spec 落盘失败只告警不中断 / daemon 拉起异常被对账吞掉 / 删链接异常计 0(幂等靠下次对账)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    job = mod.get_job(job_id)

    monkeypatch.setattr(relocate_journal, "write_spec", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    assert mod._write_arm_spec(job) is False
    monkeypatch.undo()

    def _boom(*a, **k):
        raise OSError("cannot spawn")

    monkeypatch.setattr(mod, "_spawn_daemon", _boom)
    mod._ensure_daemon(job, {})  # 拉起失败只告警: 下轮 daemon_stale 仍会再判
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


def test_cancel_close_journal(tmp_path, monkeypatch):
    """撤销把 journal 写成终态(回收 daemon 的 STOP_PHASES 退出判据, D12 取消即时生效)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    for _ in range(6):
        mod.on_task_line()
    mod.relocate_cancel(job_id, cost_confirmed=True)
    assert relocate_journal.read_journal(str(tmp_path / "data"), job_id)["phase"] == ru.PHASE_CANCELLED


def test_module_guard_branches(tmp_path, monkeypatch):
    """模块壳的退化守卫: 上下文缺失 / 坏账条目 / stop 落账异常 / 任务线未启用 都不炸"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path)
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
