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
  子进程) 只见完整文件 (无半行/截断/空文件) —— 活性判据是「写到读者读够 N 次为止」
  (不靠写次数推断, 单次写耗时跨平台差一个量级)
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
    SingleInstanceLock,
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


# ---- 并发读守阵的活性门槛 ----
#
# 语义: 读者必须在**写者活跃的窗口内**完成至少这么多次完整读, 否则守阵是真空过的
# (读者没跑 / 循环秒退 -> 永远读不到半截内容, 断言恒绿)。
#
# ⚠ 不能靠「写者写满 N 次」间接推断读者读够了多少次: 单次 atomic_write_text 的耗时
# 随机器与文件系统漂移一个量级 (CI ubuntu-latest 上 mkstemp+fsync+replace ~0.1ms,
# 开发机 Windows 上慢得多) —— 原本「写 300 次期间读者必读 >50 次」的期望在 Linux CI
# 上实测只有 29 次, 写者早就收工了读者还没读几轮。这是**机器速度依赖的活性阈值**,
# 不是被测行为的回归。改法: 写者写到**读者读够为止** (上限 + deadline 兜底), 把
# 「期望读够」换成「确保读够」——读者不干活时循环撞 deadline, 断言照红。
LIVE_READS_THREAD = 50
LIVE_READS_PROC = 100
#: 写者写入次数上限 (正常路径几百次即达标; 上限只在读者异常慢/不干活时触及)
LIVE_WRITES_LIMIT = 20000
#: 活性等待总上限: 读者始终不读时到此为止并红 (防测试挂死)
LIVE_DEADLINE_SEC = 15.0


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
        # 写到读者读够为止 (写次数不是活性判据, 见 LIVE_READS_THREAD 注释)
        writes = 0
        deadline = time.monotonic() + LIVE_DEADLINE_SEC
        while reads[0] < LIVE_READS_THREAD and writes < LIVE_WRITES_LIMIT and time.monotonic() < deadline:
            atomic_write_text(str(dat), f'lines: "1"\n2026/10/16 {writes + 2}/{writes + 2}\n')
            writes += 1
            time.sleep(0)  # 让出 GIL: 读者比写者慢时不空耗写入配额
    finally:
        stop.set()
        t.join()
    assert reads[0] >= LIVE_READS_THREAD  # 活性: 读者确实在写窗口内读过 (空转/没跑 -> 红)
    assert violations == []  # 被守行为: 任何时刻打开都是完整文件


_READER_PROC_SCRIPT = r"""
import os, re, sys, time
path, done, started, counts = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
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
    with open(counts, "w") as cf:  # 心跳计数: 父进程据此判断读者已覆盖几轮 (不靠墙钟推断)
        cf.write(str(reads))
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


def _reader_reads(counts: Path) -> int:
    """子进程上报的读次数 (心跳文件); 缺失 / 撞上写半途的空串 -> 0 (不误判达标)."""
    try:
        return int(counts.read_text())
    except (FileNotFoundError, ValueError):
        return 0


def test_concurrent_reader_process_never_sees_partial(tmp_path):
    dat = tmp_path / "history_traffic.dat"
    done = tmp_path / "reader.done"
    started = tmp_path / "reader.started"
    counts = tmp_path / "reader.reads"
    atomic_write_text(str(dat), 'lines: "1"\n2026/10/16 1/1\n')
    proc = subprocess.Popen(
        [sys.executable, "-c", _READER_PROC_SCRIPT,
         str(dat), str(done), str(started),
         str(counts)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not started.exists() and time.monotonic() < deadline:  # 握手: 读者就绪后才写
            time.sleep(0.01)
        assert started.exists(), "读者进程未就绪"
        # 写到读者读够为止 (写次数不是活性判据, 见 LIVE_READS_PROC 注释)
        writes = 0
        deadline = time.monotonic() + LIVE_DEADLINE_SEC
        while (_reader_reads(counts) < LIVE_READS_PROC and writes < LIVE_WRITES_LIMIT and time.monotonic() < deadline):
            atomic_write_text(str(dat), f'lines: "1"\n2026/10/16 {writes + 2}/{writes + 2}\n')
            writes += 1
        done.write_text("done\n")
        out, err = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode == 0, err
    reads, bad = out.split()
    # 活性: 读者确实在写窗口内读过 (空转/没跑 -> 红) + 被守行为: 无半截内容
    assert int(bad) == 0 and int(reads) >= LIVE_READS_PROC


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


# ---- 搬迁/原子写/锁/state 的容错出口 (26-10-21 覆盖率门禁 P2-T2.2) ----


def test_remove_endpoint_swallows_oserror(tmp_path, caplog):
    """删发现指针遇非「已缺失」的 OSError: 只 WARNING, 不抛 (优雅退出不能被它挡住)."""
    target = tmp_path / "endpoint.json"
    target.mkdir()  # 路径是目录 -> os.remove 抛 OSError
    with caplog.at_level("WARNING", logger="gtm.storage"):
        remove_endpoint(path=str(target))  # 不抛
    assert "发现指针删除失败" in caplog.text


def test_migrate_legacy_skips_when_legacy_is_target(tmp_path, monkeypatch):
    """旧目录与目标同址: 直接 no-op (不自己搬给自己)."""
    same = tmp_path / "data"
    _write_legacy(same)
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(same))
    assert migrate_legacy_data_dir(str(same)) is None
    assert (same / "history_traffic.dat").is_file()  # 原地不动


def test_migrate_legacy_reports_interruption(tmp_path, monkeypatch, caplog):
    """搬迁中途 OSError (目标路径被同名文件占住): 记 WARNING 并返回中断结论, 不阻断启动."""
    legacy = tmp_path / "legacy"
    _write_legacy(legacy)
    blocked = tmp_path / "blocked"
    blocked.write_text("我是文件, 不是目录", encoding="utf-8")  # makedirs 会抛 FileExistsError
    monkeypatch.setattr("gtm.storage.legacy_data_dir", lambda: str(legacy))
    with caplog.at_level("WARNING", logger="gtm.storage"):
        msg = migrate_legacy_data_dir(str(blocked))
    assert msg and "搬迁中断" in msg
    assert "旧数据目录搬迁中断" in caplog.text
    assert (legacy / "history_traffic.dat").is_file()  # 未搬成, 旧文件仍在


def test_atomic_write_rejects_empty_path():
    """空路径直接 ValueError (abspath('') 是 CWD, 会把临时文件丢到别处)."""
    with pytest.raises(ValueError) as ei:
        atomic_write_text("", "x")
    assert "path 不能为空" in str(ei.value)


def test_atomic_write_cleanup_failure_is_swallowed(tmp_path, monkeypatch):
    """写失败后清理临时文件也失败: 仍抛原始错误, 不让清理异常盖住根因."""
    import gtm.storage as storage_mod

    def fail_replace(tmp, target):
        raise PermissionError("读者持句柄")

    def fail_remove(path):
        raise PermissionError("临时文件删不掉")

    monkeypatch.setattr(storage_mod, "_replace_retry", fail_replace)
    monkeypatch.setattr(storage_mod.os, "remove", fail_remove)
    target = tmp_path / "out.txt"
    with pytest.raises(PermissionError) as ei:
        atomic_write_text(str(target), "x")
    assert "读者持句柄" in str(ei.value)  # 根因没被清理异常替换


def test_dat_load_skips_invalid_date_row(tmp_path):
    """dat 里日期非法 (2026/13/45): 整行跳过并告警, 其它日照常加载."""
    path = tmp_path / "history_traffic.dat"
    path.write_text('lines: "2"\n2026/13/45 1/2\n2026/10/16 3/4\n', encoding="utf-8")
    store = DatStore(str(path))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("gtm.storage.logger.warning", lambda *a, **k: None)  # 只验行为, 不锁日志文案
        store.load()
    assert list(store._rows) == [date(2026, 10, 16)]
    assert store._rows[date(2026, 10, 16)] == (3 * KB, 4 * KB)


def test_lock_release_swallows_meta_remove_oserror(tmp_path):
    """释放锁时删伴生 meta 失败: 吞掉 (锁已释放, meta 只是排障辅助)."""
    lock = SingleInstanceLock(str(tmp_path / "instance.lock"))
    lock.acquire()
    Path(lock.meta_path).unlink()
    Path(lock.meta_path).mkdir()  # meta 路径变成目录 -> os.remove 抛 OSError
    lock.release()  # 不抛
    assert lock._held is False


def test_lock_context_manager(tmp_path):
    """with 语法: 进入即持锁, 退出即释放 (泄漏锁会卡死下一次启动)."""
    path = str(tmp_path / "instance.lock")
    with SingleInstanceLock(path) as lock:
        assert lock._held is True
        with pytest.raises(SingleInstanceLockError):
            SingleInstanceLock(path).acquire()  # 持锁期间二次获取 fail-fast
    assert lock._held is False
    SingleInstanceLock(path).acquire()  # 释放后可再取


def test_lock_meta_write_failure_only_debug(tmp_path, caplog):
    """伴生 meta 写失败只 DEBUG: 锁才是主防线, meta 仅用于报错时补 PID."""
    def boom(path, text):
        raise OSError("磁盘满")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("gtm.storage.atomic_write_text", boom)
        with caplog.at_level("DEBUG", logger="gtm.storage"):
            lock = SingleInstanceLock(str(tmp_path / "instance.lock"))
            lock.acquire()  # 不抛
    assert lock._held is True
    assert "锁伴生 meta 写入失败" in caplog.text
    lock.release()


def test_storage_context_manager_and_explicit_load(tmp_path):
    """Storage 的 with 语法 (进持锁/出释放) + 显式 load() 幂等."""
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))
    with storage as held:
        assert held is storage
        assert storage._lock._held is True
        held.load()  # 显式加载 (重复调用安全)
        held.load()
        assert held._dat.loaded is True
    assert storage._lock._held is False


def test_recover_skips_corrupt_subscriber_entries(tmp_path, caplog):
    """state.json 订阅条目局部损坏: 坏条跳过并告警, 好条照常入表, 末事件号接续."""
    state = {
        "version": 1,
        "day": "2026-10-16",
        "day_up_bytes": 10,
        "day_down_bytes": 20,
        "last_up_bytes": 10,
        "last_down_bytes": 20,
        "subscribers":
            {
                "good": {
                    "endpoint": "http://h/1",
                    "token": "t",
                    "last_heartbeat": 100.0
                },
                "no-endpoint": {
                    "token": "t",
                    "last_heartbeat": 100.0
                },
                "bool-heartbeat": {
                    "endpoint": "http://h/2",
                    "last_heartbeat": True
                },
                "not-a-dict": "oops",
            },
        "last_event_id": 5,
    }
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    storage = make_storage(tmp_path)
    try:
        with caplog.at_level("WARNING", logger="gtm.storage"):
            storage.recover(make_sampler())
        assert set(storage.subscribers) == {"good"}
        assert storage.last_event_id == 5
        assert "订阅条目损坏已跳过" in caplog.text
    finally:
        storage.release_lock()


def test_storage_close_flushes_final_state(tmp_path):
    """close(): 最终落盘 (dat 封口), 不残留未落盘的活尾."""
    counters = FakeCounters()
    storage = make_storage(tmp_path)
    sampler = make_sampler(counters=counters)
    try:
        sample_record(storage, sampler, counters, 1024, 2048)
        storage.close()
        assert (tmp_path / "history_traffic.dat").is_file()
    finally:
        storage.release_lock()
