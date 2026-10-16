"""S2 落盘守阵: dat 格式与原子写 / state 每次采样 / 节流 / 崩溃恢复 / 单实例锁 / 并发读.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S2).
全部用例 hermetic: tmp_path 落盘, 时钟注入替身, 不碰真实网卡与工具数据目录.

## 测试计划

- dat 格式: lines 头 + 行降序 (新日在前) + KB 向下取整 (宁可少报); upsert 当日
  原地更新其它日不动; 加载保留既有日并跳过坏行 (curves 容错口径)
- curves 兼容: 产出的 dat 经 auto-qb curves.py parse_history_dat 解析 (bad==0,
  值逐日一致); sampler.restore_from_dat 对产出文本 round-trip (读写两侧同格式单点)
- 原子写: 写失败 (fsync 抛) 留原文件且无临时残留; replace 遇 PermissionError
  (Windows 读者持句柄) 退避重试成功, 重试耗尽抛错且留原文件; 并发读守阵 (线程 +
  子进程) 只见完整文件 (无半行/截断/空文件)
- state: 每次 record 必写 (丢失窗口 <= 采样间隔); 缺失/损坏 read() -> None
- 节流: 低于阈值且未到间隔不落盘; 达 1MiB 落盘; 达 30s 落盘; 首帧必落盘
  (恢复值/初始值即时持久化); render 活尾随时可服务 (文件未落盘时内存即最新)
- 恢复: kill -9 后续跑日累计接续不丢不重 (state 权威); state 缺失/损坏(版本不符)
  -> dat 兜底; 有效载荷 (今天) 不触发兜底 —— state 与 dat 冲突时取 state
- 跨天: day_rolled 封存旧日最终值 (未达阈值也落盘) + 新日行懒写 + 节流基线重置
- 单实例锁: 进程内二次获取 fail-fast (含持有者 PID); 跨进程 (真·二次启动) 同样
  fail-fast; 释放后可再获取; release 幂等; 伴生 meta 随释放删除
- default_data_dir: 环境变量优先, 平台形状末段为 gtm
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

from gtm.sampler import DAT_ROW_RE, Sampler
from gtm.storage import (
    DEFAULT_FLUSH_DELTA_BYTES,
    KB,
    MIB,
    DatStore,
    SingleInstanceLockError,
    StateStore,
    Storage,
    atomic_write_text,
    default_data_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

DAY1 = date(2026, 10, 15)
DAY2 = date(2026, 10, 16)

# ---- 替身 ----


class FakeMono:
    """FlushPolicy 的单调时钟替身 (可拖动)."""
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeWall:
    """Sampler 的挂钟替身 (可拖动到次日, 驱动跨天)."""
    def __init__(self, now: datetime = datetime(2026, 10, 16, 12, 0, 0)) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakeCounters:
    """net_io_counters 替身 (可换页)."""
    def __init__(self) -> None:
        self.page: dict = {}

    def __call__(self) -> dict:
        return self.page


def nic(sent: int, recv: int) -> SimpleNamespace:
    return SimpleNamespace(bytes_sent=sent, bytes_recv=recv)


def make_sampler(clock: Optional[FakeWall] = None, counters: Optional[FakeCounters] = None) -> Sampler:
    return Sampler(
        clock=clock or FakeWall(),
        counters_provider=counters or FakeCounters(),
        stats_provider=lambda: {},
    )


def make_storage(tmp_path: Path, mono: Optional[FakeMono] = None) -> Storage:
    storage = Storage(str(tmp_path), clock=mono or FakeMono())
    storage.acquire_lock()
    return storage


def sample_record(storage: Storage, sampler: Sampler, counters: FakeCounters, sent: int, recv: int):
    """驱动一次真实采样并落盘编排 (result + snapshot 均来自 sampler, 与生产同链路)."""
    counters.page = {"eth0": nic(sent, recv)}
    r = sampler.sample_once()
    storage.record(r, sampler.snapshot())
    return r


def load_auto_qb_curves():
    """加载 auto-qb 真解析器 curves.py 作 oracle (工具独立部署时跳过, 不进假绿)."""
    curves_py = REPO_ROOT / "src" / "auto_qb" / "core" / "curves.py"
    if not curves_py.exists():
        pytest.skip("auto-qb curves.py 不在仓库内 (工具独立部署时跳过本 oracle)")
    spec = importlib.util.spec_from_file_location("auto_qb_curves_oracle", curves_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dat_text(tmp_path: Path) -> str:
    return (tmp_path / "history_traffic.dat").read_text(encoding="utf-8")


def dat_mtime_ns(tmp_path: Path) -> int:
    return (tmp_path / "history_traffic.dat").stat().st_mtime_ns


# ---- dat 格式 ----


def test_dat_render_format_tm_compatible(tmp_path):
    ds = DatStore(str(tmp_path / "history_traffic.dat"))
    ds.upsert(DAY1, 3 * MIB, 5 * MIB)
    ds.upsert(DAY2, 7 * MIB, 2 * MIB)
    # 首行行数说明 + 新日在前 (TM 倒序) + 整数 KB
    assert ds.render() == 'lines: "2"\n2026/10/16 7168/2048\n2026/10/15 3072/5120\n'


def test_dat_kb_flooring(tmp_path):
    ds = DatStore(str(tmp_path / "d.dat"))
    ds.upsert(DAY2, KB - 1, 2 * KB + 1)
    assert ds.render() == f'lines: "1"\n2026/10/16 0/2\n'


def test_dat_upsert_updates_today_in_place(tmp_path):
    ds = DatStore(str(tmp_path / "d.dat"))
    ds.upsert(DAY2, 1 * MIB, 1 * MIB)
    ds.upsert(DAY2, 2 * MIB, 3 * MIB)
    ds.upsert(DAY1, 9 * MIB, 9 * MIB)
    text = ds.render()
    assert text.count("\n") == 3  # 头 + 两行, 当日未分裂
    assert "2026/10/16 2048/3072" in text
    assert "2026/10/15 9216/9216" in text


def test_dat_load_preserves_existing_days_and_skips_bad_lines(tmp_path):
    p = tmp_path / "history_traffic.dat"
    atomic_write_text(str(p), 'lines: "2"\n2026/10/16 10/20\ngarbage line\n2026/10/15 5/6\n')
    ds = DatStore(str(p))
    ds.load()
    ds.upsert(DAY2, 30 * KB, 60 * KB)
    assert ds.render() == 'lines: "2"\n2026/10/16 30/60\n2026/10/15 5/6\n'


def test_generated_dat_parses_with_autoqb_curves(tmp_path):
    ds = DatStore(str(tmp_path / "history_traffic.dat"))
    ds.upsert(DAY1, 3 * MIB, 5 * MIB)
    ds.upsert(DAY2, 7 * MIB, 2 * MIB)
    ds.flush()
    curves = load_auto_qb_curves()
    rows, bad = curves.parse_history_dat(dat_text(tmp_path))
    assert bad == 0
    assert rows == [(DAY1, 3 * MIB, 5 * MIB), (DAY2, 7 * MIB, 2 * MIB)]


def test_sampler_restore_from_dat_roundtrip_on_generated(tmp_path):
    ds = DatStore(str(tmp_path / "history_traffic.dat"))
    ds.upsert(DAY2, 4 * MIB, 2 * MIB)
    ds.flush()
    s = Sampler(clock=FakeWall(datetime(2026, 10, 16, 12, 0, 0)))
    assert s.restore_from_dat(dat_text(tmp_path)) is True
    assert s.day == DAY2 and s.day_up_bytes == 4 * MIB and s.day_down_bytes == 2 * MIB


# ---- 原子写 ----


def test_atomic_write_failure_keeps_original_and_leaves_no_litter(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    atomic_write_text(str(p), "old\n")

    def boom(_fd: int) -> None:
        raise OSError("模拟磁盘错误")

    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        atomic_write_text(str(p), "new\n")
    assert p.read_text(encoding="utf-8") == "old\n"  # 原文件完整保留
    litter = [q.name for q in tmp_path.iterdir() if q.name != "state.json"]
    assert litter == []  # 临时文件已清理


def test_atomic_write_retries_replace_on_permission_error(tmp_path, monkeypatch):
    p = tmp_path / "f.dat"
    atomic_write_text(str(p), "old\n")
    real_replace = os.replace
    calls = [0]

    def flaky(src, dst):
        calls[0] += 1
        if calls[0] <= 2:
            raise PermissionError("模拟读者持句柄 (WinError 5)")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    atomic_write_text(str(p), "new\n")  # 前两次被拒, 第三次成功
    assert calls[0] == 3
    assert p.read_text(encoding="utf-8") == "new\n"


def test_atomic_write_raises_after_retry_exhausted(tmp_path, monkeypatch):
    p = tmp_path / "f.dat"
    atomic_write_text(str(p), "old\n")

    def always_deny(src, dst):
        raise PermissionError("持久冲突 (读家长持/磁盘满)")

    monkeypatch.setattr(os, "replace", always_deny)
    with pytest.raises(PermissionError):
        atomic_write_text(str(p), "new\n")
    assert p.read_text(encoding="utf-8") == "old\n"  # 重试耗尽: 原文件保留
    litter = [q.name for q in tmp_path.iterdir() if q.name != "f.dat"]
    assert litter == []  # 临时文件已清理


def _validate_dat_bytes(data: bytes) -> Optional[str]:
    """返回违规描述; None = 完整一致. (空文件在预写后即违规: 文件应恒存在)."""
    if not data:
        return "读到空文件 (原子写保证文件恒存在)"
    if not data.endswith(b"\n"):
        return f"文件不以换行结束 (截断?): {data[-40:]!r}"
    lines = data.decode("ascii").splitlines()
    if not lines or not lines[0].startswith('lines: "'):
        return f"首行不是 lines 头: {lines[:1]!r}"
    for line in lines[1:]:
        if not DAT_ROW_RE.match(line):
            return f"行不匹配 TM 行格式: {line!r}"
    return None


def test_concurrent_reader_thread_never_sees_partial(tmp_path):
    dat = tmp_path / "history_traffic.dat"
    atomic_write_text(str(dat), 'lines: "1"\n2026/10/16 1/1\n')  # 读者启动前文件已存在
    stop = threading.Event()
    violations: list[str] = []
    reads = [0]

    def reader() -> None:
        while not stop.is_set():
            try:
                data = dat.read_bytes()
            except PermissionError:
                # replace 事务窗口内的瞬时打开拒绝 (读者看不到内容, 非半截内容): 重试
                time.sleep(0.005)
                continue
            reads[0] += 1
            v = _validate_dat_bytes(data)
            if v:
                violations.append(v)
            time.sleep(0.001)  # 真实读者非热循环; 1ms 节流仍覆盖写窗口

    t = threading.Thread(target=reader)
    t.start()
    try:
        for i in range(300):
            atomic_write_text(str(dat), f'lines: "1"\n2026/10/16 {i + 2}/{i + 2}\n')
    finally:
        stop.set()
        t.join()
    assert reads[0] > 50
    assert violations == []


_READER_PROC_SCRIPT = r"""
import os, re, sys, time
path, done, started = sys.argv[1], sys.argv[2], sys.argv[3]
ROW = re.compile(r"^\d{4}/\d{1,2}/\d{1,2} \d+/\d+$")
open(started, "w").close()
bad = 0
reads = 0

def read_retry():
    for _ in range(50):
        try:
            with open(path, "rb") as f:
                return f.read()
        except PermissionError:
            time.sleep(0.005)  # replace 事务窗口内的瞬时打开拒绝: 重试
    raise RuntimeError("open 持续被拒绝")

while not os.path.exists(done):
    data = read_retry()
    reads += 1
    if not data or not data.endswith(b"\n"):
        bad += 1
        continue
    lines = data.decode("ascii", "replace").splitlines()
    if not lines or not lines[0].startswith('lines: "'):
        bad += 1
        continue
    for line in lines[1:]:
        if not ROW.match(line):
            bad += 1
            break
    time.sleep(0.001)  # 真实读者非热循环; 1ms 节流仍覆盖写窗口
print(reads, bad)
"""


def test_concurrent_reader_process_never_sees_partial(tmp_path):
    dat = tmp_path / "history_traffic.dat"
    done = tmp_path / "reader.done"
    started = tmp_path / "reader.started"
    atomic_write_text(str(dat), 'lines: "1"\n2026/10/16 1/1\n')
    proc = subprocess.Popen(
        [sys.executable, "-c", _READER_PROC_SCRIPT,
         str(dat), str(done), str(started)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not started.exists() and time.monotonic() < deadline:  # 握手: 读者就绪后才写
            time.sleep(0.01)
        assert started.exists(), "读者进程未就绪"
        for i in range(400):
            atomic_write_text(str(dat), f'lines: "1"\n2026/10/16 {i + 2}/{i + 2}\n')
        done.write_text("done\n")
        out, err = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode == 0, err
    reads, bad = out.split()
    assert int(bad) == 0 and int(reads) > 100


# ---- state.json ----


def test_state_written_on_every_record(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 0, 0)  # 基线
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["day"] == "2026-10-16" and state["day_up_bytes"] == 0
    sample_record(storage, sampler, counters, 5 * MIB, 0)  # +5MiB
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["day_up_bytes"] == 5 * MIB and state["last_up_bytes"] == 5 * MIB
    # 丢失窗口 <= 采样间隔的证据: 每次采样后 state 已是最新 (无需 close)


def test_state_read_returns_none_on_missing_and_corrupt(tmp_path):
    assert StateStore(str(tmp_path / "state.json")).read() is None
    atomic_write_text(str(tmp_path / "state.json"), "{{{ 不是 JSON")
    assert StateStore(str(tmp_path / "state.json")).read() is None
    atomic_write_text(str(tmp_path / "state.json"), "[1, 2]")
    assert StateStore(str(tmp_path / "state.json")).read() is None


# ---- 落盘节流 ----


def test_no_flush_below_threshold_before_interval(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    mono = FakeMono()
    storage = make_storage(tmp_path, mono)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 0, 0)  # 首帧必落盘
    mtime1 = dat_mtime_ns(tmp_path)
    mono.t += 10  # < 30s
    sample_record(storage, sampler, counters, int(0.5 * MIB), 0)  # +0.5MiB < 1MiB
    assert dat_mtime_ns(tmp_path) == mtime1  # 未落盘


def test_flush_on_delta_threshold(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    mono = FakeMono()
    storage = make_storage(tmp_path, mono)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 0, 0)
    mtime1 = dat_mtime_ns(tmp_path)
    sample_record(storage, sampler, counters, DEFAULT_FLUSH_DELTA_BYTES, 0)  # 恰达 1MiB
    assert dat_mtime_ns(tmp_path) != mtime1
    assert "2026/10/16 1024/0" in dat_text(tmp_path)


def test_flush_on_interval(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    mono = FakeMono()
    storage = make_storage(tmp_path, mono)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 0, 0)
    mtime1 = dat_mtime_ns(tmp_path)
    mono.t += 29.5  # < 30s
    sample_record(storage, sampler, counters, int(0.1 * MIB), 0)
    assert dat_mtime_ns(tmp_path) == mtime1
    mono.t += 1.0  # 累计 30.5s >= 30s
    sample_record(storage, sampler, counters, int(0.2 * MIB), 0)
    assert dat_mtime_ns(tmp_path) != mtime1


def test_first_frame_flush_persists_recovered_value(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 2 * MIB, 1 * MIB)  # 基线
    sample_record(storage, sampler, counters, 7 * MIB, 4 * MIB)  # 当日 5/3 MiB
    storage.release_lock()
    del storage, sampler, counters
    # 重启: 恢复值 5/3 MiB 应随首帧落盘 (不等到阈值/间隔)
    counters2 = FakeCounters()
    sampler2 = make_sampler(counters=counters2)
    storage2 = make_storage(tmp_path)
    storage2.recover(sampler2)
    assert sampler2.day_up_bytes == 5 * MIB and sampler2.day_down_bytes == 3 * MIB
    sample_record(storage2, sampler2, counters2, 9 * MIB, 4 * MIB)  # 首帧即落盘
    assert "2026/10/16 7168/3072" in dat_text(tmp_path)  # 恢复值 + 新 delta 已持久化


def test_render_reflects_memory_before_flush(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 0, 0)  # 首帧落盘
    sample_record(storage, sampler, counters, int(0.2 * MIB), 0)  # 低于阈值, 未落盘
    # 内存活尾随时可服务: dat_text 即最新, 磁盘文件仍旧
    assert "2026/10/16 204/0" in storage.dat_text()
    assert "2026/10/16 0/0" in dat_text(tmp_path)


# ---- 崩溃恢复 ----


def test_restart_continuity_day_cumulative(tmp_path):
    counters = FakeCounters()
    sampler = make_sampler(counters=counters)
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 2 * MIB, 1 * MIB)  # 基线
    sample_record(storage, sampler, counters, 7 * MIB, 4 * MIB)  # 当日 5/3 MiB
    storage.release_lock()
    del storage, sampler, counters  # 模拟 kill -9: 不做 close, state.json 已随采样落盘
    counters2 = FakeCounters()
    sampler2 = make_sampler(counters=counters2)
    storage2 = make_storage(tmp_path)
    storage2.recover(sampler2)
    assert sampler2.day_up_bytes == 5 * MIB and sampler2.day_down_bytes == 3 * MIB
    assert sampler2.has_baseline  # 计数器基线从 state 恢复
    sample_record(storage2, sampler2, counters2, 9 * MIB, 4 * MIB)  # 接着涨: +2/0
    assert sampler2.day_up_bytes == 7 * MIB and sampler2.day_down_bytes == 3 * MIB  # 不丢不重


def test_recover_fallback_to_dat_when_state_missing(tmp_path):
    atomic_write_text(
        str(tmp_path / "history_traffic.dat"),
        f'lines: "1"\n2026/10/16 {4 * MIB // KB}/{2 * MIB // KB}\n',
    )
    sampler = make_sampler()
    storage = make_storage(tmp_path)
    warnings = storage.recover(sampler)
    assert sampler.day == DAY2 and sampler.day_up_bytes == 4 * MIB and sampler.day_down_bytes == 2 * MIB
    assert not sampler.has_baseline  # 降级: 计数器基线取当前值 (首样本 baseline)
    assert any("state" in w for w in warnings)


def test_recover_fallback_when_state_version_unsupported(tmp_path):
    atomic_write_text(
        str(tmp_path / "history_traffic.dat"),
        f'lines: "1"\n2026/10/16 {4 * MIB // KB}/{2 * MIB // KB}\n',
    )
    atomic_write_text(
        str(tmp_path / "state.json"),
        json.dumps(
            {
                "version": 999,
                "day": "2026-10-16",
                "day_up_bytes": 9 * MIB,
                "day_down_bytes": 0,
                "last_up_bytes": 5,
                "last_down_bytes": 5,
            }
        ),
    )
    sampler = make_sampler()
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    assert sampler.day_up_bytes == 4 * MIB  # 损坏 state 不采信, dat 兜底


def test_recover_prefers_state_over_dat_when_valid(tmp_path):
    atomic_write_text(
        str(tmp_path / "history_traffic.dat"),
        f'lines: "1"\n2026/10/16 {1 * MIB // KB}/{1 * MIB // KB}\n',
    )
    atomic_write_text(
        str(tmp_path / "state.json"),
        json.dumps(
            {
                "version": 1,
                "day": "2026-10-16",
                "day_up_bytes": 5 * MIB,
                "day_down_bytes": 1 * MIB,
                "last_up_bytes": 7 * MIB,
                "last_down_bytes": 4 * MIB,
            }
        ),
    )
    sampler = make_sampler()
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    assert sampler.day_up_bytes == 5 * MIB and sampler.day_down_bytes == 1 * MIB  # state 权威
    assert sampler.has_baseline


# ---- 跨天 ----


def test_day_roll_seals_old_day_and_new_day_is_lazy(tmp_path):
    counters = FakeCounters()
    wall = FakeWall()
    sampler = make_sampler(clock=wall, counters=counters)
    storage = make_storage(tmp_path)
    storage.recover(sampler)
    sample_record(storage, sampler, counters, 0, 0)  # 首帧落盘 (day1 0/0)
    sample_record(storage, sampler, counters, 200_000, 0)  # day1 200000B, 未落盘
    # 跨天: day_rolled -> 封存旧日最终值 + 新日行懒写
    wall.now = datetime(2026, 10, 17, 0, 0, 30)
    r = sample_record(storage, sampler, counters, 500_000, 0)  # 新日 +300000B
    assert r.day_rolled is True and r.day_up_bytes == 300_000
    assert "2026/10/16 195/0" in dat_text(tmp_path)  # 旧日最终值已封存 (未达阈值也落盘)
    assert "2026/10/17" not in dat_text(tmp_path)  # 新日行懒写 (节流未触发)
    # 新日累计越过阈值 -> 落盘
    sample_record(storage, sampler, counters, 2_000_000, 0)  # 新日累计 1800000B
    assert "2026/10/17 1757/0" in dat_text(tmp_path)


# ---- 单实例锁 ----


def test_single_instance_lock_blocks_second_in_process(tmp_path):
    st1 = make_storage(tmp_path)
    st2 = Storage(str(tmp_path))
    with pytest.raises(SingleInstanceLockError) as excinfo:
        st2.acquire_lock()
    msg = str(excinfo.value)
    assert "另一 gtm 实例已持有锁" in msg
    assert "PID" in msg and str(os.getpid()) in msg
    st1.release_lock()
    st3 = Storage(str(tmp_path))
    st3.acquire_lock()  # 释放后可再获取
    st3.release_lock()


def test_single_instance_lock_blocks_second_process(tmp_path):
    held = make_storage(tmp_path)  # 持锁实例必须存活 (GC 会关 fd 释放 msvcrt 锁)
    lock_path = str(tmp_path / "gtm.lock")
    code = (
        "from gtm.storage import SingleInstanceLock, SingleInstanceLockError\n"
        f"lk = SingleInstanceLock({lock_path!r})\n"
        "try:\n"
        "    lk.acquire()\n"
        "except SingleInstanceLockError as e:\n"
        "    print('BUSY', e)\n"
        "else:\n"
        "    print('ACQUIRED')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert "BUSY" in proc.stdout
    assert "另一 gtm 实例已持有锁" in proc.stdout and str(os.getpid()) in proc.stdout


def test_lock_release_idempotent_and_meta_removed(tmp_path):
    storage = make_storage(tmp_path)
    meta = tmp_path / "gtm.lock.meta.json"
    assert meta.exists()
    storage.release_lock()
    assert not meta.exists()
    storage.release_lock()  # 幂等: 未持锁再释放不炸
    # 锁文件残留按平台语义 (Windows 删 / POSIX flock 残留), 不断言其存在性


# ---- 数据目录默认值 ----


def test_default_data_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("GTM_DATA_DIR", str(tmp_path / "custom"))
    assert default_data_dir() == str(tmp_path / "custom")
    monkeypatch.delenv("GTM_DATA_DIR", raising=False)
    assert Path(default_data_dir()).name == "gtm"  # 平台形状: 末段为 gtm
