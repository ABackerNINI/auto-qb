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
- 目录定位 (S11): resolve_tool_root 源码态由 __file__ 上溯到工具根 (含 pyproject.toml) /
  冻结态 (sys.frozen) 取 sys.executable 所在目录; default_data_dir 默认 = <工具根>/data
  且 GLOBAL_TRAFFIC_MONITOR_DATA_DIR 优先; 旧用户目录一次性搬迁 (旧有
  history_traffic.dat 且目标空才搬, 幂等可重入, 显式 --data-dir 不触发)
- 发现指针与锁锚点 (S12): 指针目录按平台用户目录 (Windows LOCALAPPDATA / macOS
  Application Support / Linux XDG) 解析, 与 data_dir 解耦; endpoint.json / instance.lock
  落在指针目录; Storage 默认锁锚在指针目录 (非 data_dir, 测试经 lock_path 注入);
  write_endpoint 原子落盘 + remove_endpoint 幂等; 旧数据目录叶名 gtm 不受重构影响
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
    endpoint_path,
    instance_lock_path,
    legacy_data_dir,
    migrate_legacy_data_dir,
    pointer_dir,
    remove_endpoint,
    resolve_tool_root,
    write_endpoint,
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
    # S12: 锁锚在用户级指针目录 —— 单测注入 tmp 锁路径, 保持 hermetic 且不碰真实用户目录
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"), clock=mono or FakeMono())
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


# ---- S3: 注册表并入 state 载荷 (HTTP 线程与采样线程同锁写盘) ----


def test_record_merges_subscribers_into_state_payload(tmp_path):
    """record 写盘 = 快照 + 注册表 + 事件号 完整镜像 (注册表不被采样快照覆盖)."""
    storage = make_storage(tmp_path)
    sampler = make_sampler()
    storage.recover(sampler)
    storage.upsert_subscriber("s1", "http://h/1", "t")
    counters = FakeCounters()
    sample_record(storage, sampler, counters, 2 * MIB, 1 * MIB)
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["subscribers"]["s1"]["endpoint"] == "http://h/1"  # 采样写盘保留注册表
    assert state["day_up_bytes"] == 0  # 首帧 baseline
    assert state["last_event_id"] == 0


def test_subscriber_mutation_before_first_sample_persists(tmp_path):
    """首帧采样前的订阅变更: state.json 落控制字段 (无采样字段, 与全新安装等价,
    recover 自然降级, 不污染采样恢复)."""
    storage = make_storage(tmp_path)
    storage.upsert_subscriber("s1", "http://h/1", "t")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["subscribers"]["s1"]["endpoint"] == "http://h/1"
    assert "day_up_bytes" not in state  # 尚未采样


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
    lock = str(tmp_path / "instance.lock")
    st1 = make_storage(tmp_path)
    st2 = Storage(str(tmp_path), lock_path=lock)
    with pytest.raises(SingleInstanceLockError) as excinfo:
        st2.acquire_lock()
    msg = str(excinfo.value)
    assert "另一 global-traffic-monitor 实例已持有锁" in msg
    assert "PID" in msg and str(os.getpid()) in msg
    st1.release_lock()
    st3 = Storage(str(tmp_path), lock_path=lock)
    st3.acquire_lock()  # 释放后可再获取
    st3.release_lock()


def test_single_instance_lock_blocks_second_process(tmp_path):
    held = make_storage(tmp_path)  # 持锁实例必须存活 (GC 会关 fd 释放 msvcrt 锁)
    lock_path = str(tmp_path / "instance.lock")
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
    assert "另一 global-traffic-monitor 实例已持有锁" in proc.stdout and str(os.getpid()) in proc.stdout


def test_lock_release_idempotent_and_meta_removed(tmp_path):
    storage = make_storage(tmp_path)
    meta = tmp_path / "instance.lock.meta.json"
    assert meta.exists()
    storage.release_lock()
    assert not meta.exists()
    storage.release_lock()  # 幂等: 未持锁再释放不炸
    # 锁文件残留按平台语义 (Windows 删 / POSIX flock 残留), 不断言其存在性


# ---- 目录定位 / 数据默认落点 / 旧数据搬迁 (S11) ----


def test_resolve_tool_root_source_mode_is_tool_dir():
    """源码态 (D11): 由 __file__ 上溯到仓库内工具根 (即含 pyproject.toml 的目录)."""
    root = resolve_tool_root()
    assert root.name == "global-traffic-monitor"
    assert (root / "pyproject.toml").is_file()


def test_resolve_tool_root_frozen_mode_uses_executable_dir(tmp_path, monkeypatch):
    """冻结态 (D11): onefile 的 __file__ 指向 _MEIPASS 临时解包目录, 故取 sys.executable 所在目录."""
    fake_exe = tmp_path / "dist" / "global-traffic-monitor.exe"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    assert resolve_tool_root() == fake_exe.parent
    monkeypatch.delenv("GLOBAL_TRAFFIC_MONITOR_DATA_DIR", raising=False)
    assert default_data_dir() == str(fake_exe.parent / "data")  # 冻结态数据落 <exe 目录>/data


def test_default_data_dir_is_install_dir_data(monkeypatch):
    """默认数据目录 = <工具安装目录>/data (D12), 不再是平台用户目录."""
    monkeypatch.delenv("GLOBAL_TRAFFIC_MONITOR_DATA_DIR", raising=False)
    assert default_data_dir() == str(resolve_tool_root() / "data")


def test_default_data_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("GLOBAL_TRAFFIC_MONITOR_DATA_DIR", str(tmp_path / "custom"))
    assert default_data_dir() == str(tmp_path / "custom")
    monkeypatch.delenv("GLOBAL_TRAFFIC_MONITOR_DATA_DIR", raising=False)
    assert Path(default_data_dir()) == resolve_tool_root() / "data"


def _write_legacy(legacy: Path) -> None:
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "history_traffic.dat").write_text('lines: "1"\n2026/10/16 1/1\n', encoding="utf-8")
    (legacy / "state.json").write_text("{}\n", encoding="utf-8")


def test_migrate_legacy_data_dir_moves_when_target_empty(tmp_path, monkeypatch):
    """旧目录有 dat 且目标空: 数据文件搬进目标 (搬走, 非复制)."""
    legacy = tmp_path / "legacy"
    _write_legacy(legacy)
    target = tmp_path / "new" / "data"
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(legacy))
    msg = migrate_legacy_data_dir(str(target))
    assert msg and "搬迁完成" in msg
    assert (target / "history_traffic.dat").is_file() and (target / "state.json").is_file()
    assert not (legacy / "history_traffic.dat").exists()


def test_migrate_legacy_data_dir_skips_when_target_nonempty(tmp_path, monkeypatch):
    """目标已有数据 -> 不搬 (幂等; 不覆盖新数据)."""
    legacy = tmp_path / "legacy"
    _write_legacy(legacy)
    target = tmp_path / "data"
    target.mkdir()
    (target / "state.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(legacy))
    assert migrate_legacy_data_dir(str(target)) is None
    assert (legacy / "history_traffic.dat").is_file()  # 旧文件未动


def test_migrate_legacy_data_dir_skips_without_legacy_dat(tmp_path, monkeypatch):
    """旧目录无 history_traffic.dat -> 不搬 (无旧数据可言)."""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "state.json").write_text("{}\n", encoding="utf-8")
    target = tmp_path / "data"
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(legacy))
    assert migrate_legacy_data_dir(str(target)) is None
    assert not target.exists()


def test_migrate_legacy_data_dir_idempotent(tmp_path, monkeypatch):
    """幂等: 第一次搬迁后目标非空, 再跑即 no-op."""
    legacy = tmp_path / "legacy"
    _write_legacy(legacy)
    target = tmp_path / "data"
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(legacy))
    assert migrate_legacy_data_dir(str(target)) is not None
    assert migrate_legacy_data_dir(str(target)) is None


def test_resolve_data_dir_explicit_override_skips_migration(tmp_path, monkeypatch):
    """显式 --data-dir: 按用户所指目录, 不擅自从旧位置搬数据 (只默认路径才搬迁)."""
    from gtm import __main__ as cli

    legacy = tmp_path / "legacy"
    _write_legacy(legacy)
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(legacy))
    explicit = tmp_path / "explicit"
    assert cli._resolve_data_dir(str(explicit)) == str(explicit)
    assert (legacy / "history_traffic.dat").is_file()  # 未触发搬迁


# ---- 发现指针 / 锁锚点 (S12) ----


def test_legacy_data_dir_still_platform_user_leaf_gtm(monkeypatch):
    """重构 (_platform_data_home) 不改 D12 契约: 旧数据目录仍 = 平台用户目录/gtm."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\LA")
    assert legacy_data_dir() == os.path.join(r"C:\LA", "gtm")


def test_pointer_dir_platform_windows(monkeypatch):
    """D6: Windows 指 %LOCALAPPDATA%\\global-traffic-monitor (无 LOCALAPPDATA 时回退 ~\\AppData\\Local)."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\LA")
    assert pointer_dir() == os.path.join(r"C:\LA", "global-traffic-monitor")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(os.path, "expanduser", lambda p: r"C:\Users\x")
    assert pointer_dir() == os.path.join(r"C:\Users\x", "AppData", "Local", "global-traffic-monitor")


def test_pointer_dir_platform_macos(monkeypatch):
    """D6: macOS 指 ~/Library/Application Support/global-traffic-monitor."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(os.path, "expanduser", lambda p: "/Users/x")
    assert pointer_dir() == os.path.join("/Users/x", "Library", "Application Support", "global-traffic-monitor")


def test_pointer_dir_platform_linux_xdg(monkeypatch):
    """D6: Linux 指 $XDG_DATA_HOME/global-traffic-monitor (无则 ~/.local/share)."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/home/x/.xdg")
    assert pointer_dir() == os.path.join("/home/x/.xdg", "global-traffic-monitor")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(os.path, "expanduser", lambda p: "/home/x")
    assert pointer_dir() == os.path.join("/home/x", ".local", "share", "global-traffic-monitor")


def test_endpoint_and_lock_live_under_pointer_dir(tmp_path, monkeypatch):
    """D6/D8: endpoint.json 与 instance.lock 都落在指针目录 (与 data_dir 无关)."""
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(tmp_path / "ptr"))
    assert endpoint_path() == str(tmp_path / "ptr" / "endpoint.json")
    assert instance_lock_path() == str(tmp_path / "ptr" / "instance.lock")


def test_storage_default_lock_anchored_at_pointer_not_data_dir(tmp_path, monkeypatch):
    """D8: 默认锁锚在指针目录 —— 数据目录可自定义, 「整机一个工具」不随之漂移."""
    ptr = tmp_path / "ptr"
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    storage = Storage(str(tmp_path / "data"))
    assert Path(storage.lock_path) == ptr / "instance.lock"
    assert not Path(storage.lock_path).is_relative_to(tmp_path / "data")
    storage.acquire_lock()
    assert (ptr / "instance.lock").exists()  # 锁目录被自动创建
    assert not (tmp_path / "data" / "instance.lock").exists()
    storage.release_lock()


def test_write_endpoint_atomic_and_remove_idempotent(tmp_path, monkeypatch):
    """D6/S12: write_endpoint 原子落盘 (JSON 可读); remove_endpoint 幂等 (缺失即 no-op)."""
    ptr = tmp_path / "ptr"
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    written = write_endpoint({"schema": 1, "port": 8099, "port_again": 8099})
    assert Path(written) == ptr / "endpoint.json"
    assert json.loads(Path(written).read_text(encoding="utf-8"))["port"] == 8099
    remove_endpoint()
    assert not Path(written).exists()
    remove_endpoint()  # 幂等: 已删再删不抛
