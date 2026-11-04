"""`relocate_exec_support` 支撑: 从 `test_relocate_exec.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

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


def _armed_env(tmp_path, monkeypatch, clock=None):
    """跑到 armed 的环境(供对账/撤销用例)

    clock: 透传 relocate_env -> make_manager 的构造期时钟(「开机窗口」用例传
    FakeClock(start=开机后秒数), S3 收敛后不再进程级 patch stdlib time.monotonic)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading", clock=clock)
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED
    mgr.config.data_dir = str(tmp_path / "data")
    return mgr, client, mod, job_id, spawned, src, dst, content


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
