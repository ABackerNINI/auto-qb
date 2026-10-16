"""S4 通知守阵: 阈值触发 / 事件号 / 启动补发 / 去重 / 假死端点不阻塞采样循环.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S4).
全部用例 hermetic: tmp_path 数据目录 + 注入推送替身 (不真发 HTTP) + 注入计数器/时钟。

## 测试计划

- 阈值判定: 低于阈值不推; 达阈值推一次 (事件体六字段: event_id/day/up_bytes/
  down_bytes/total_bytes/ts); 累计基数 = 距**上次事件**的当日合计变化 (逐样本累加,
  不是单样本 delta); 阈值经 ConfigHolder 现读 (PUT /config 热重载生效)
- 去重: 同一累计窗口不重复发事件 (派发后基数推进); 事件号单调递增 (订阅方据此去重)
- 跨天: day_rolled 只重置基数不产事件; 累计回退 (不该发生) 同样只重置
- 启动补发: catch_up=True 不看阈值发一次 (事件号接续, 重启后 +1); 派发抛错时基数
  不推进 -> 阈值窗口保留, 下一轮重试 (不静默丢事件)
- 事件号持久化: bump_event_id 落 state.json, 重启 (新 Storage + recover) 接续
- 推送: 向全部存活订阅者推 (各自 token 作 Bearer); 推送前先落盘 (dat 已含新值);
  推送前租约懒剔除 (过期订阅者不收); 无订阅者仍发事件 (事件号仍 +1)
- 失败面: 假死端点 (超时/连接失败) 只记 WARNING 不抛; 一个订阅者失败不拖慢另一个
  (每订阅者一线程); 在途线程达上限则跳过派发并 WARNING
- 生产推送单点 (真 HTTP): http_push POST JSON + `Authorization: Bearer <token>`,
  非 2xx 抛错 (urlopen HTTPError); 通知器默认 pusher 端到端 (真 HTTP 接收端)
- 不阻塞采样循环 (计划 S4 出口, >10s 压测): 真 _run_loop + 两订阅者 (一假死) ——
  采样帧数持续增长、停止信号可即时收尾 (同步推送会让循环卡死在假死端点上)
- 生命周期: close 后不再派发; wait_idle 有界等待在途推送
"""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Mapping, Optional

import pytest

from gtm.__main__ import _run_loop
from gtm.config import Config, ConfigHolder
from gtm.notifier import Notifier, http_push
from gtm.sampler import DAT_ROW_RE, SampleResult, Sampler
from gtm.storage import KB, Storage

# ---- 替身与夹具 ----

TODAY = datetime.date(2026, 10, 16)
TOMORROW = datetime.date(2026, 10, 17)
FIXED_NOW = datetime.datetime(2026, 10, 16, 12, 0, 0)
FAKE_EPOCH = 10_000.0  # 通知器注入时钟 (远小于真实 wall clock, 便于拨钟验租约)

MIB = 1024 * 1024


class FakeNic(SimpleNamespace):
    pass


def make_counters(start: int = 1_000_000):
    """单调递增计数器替身 (每次读 +1024 字节 up, +512 down)."""
    state = {"v": start}
    calls = {"n": 0}

    def counters() -> dict:
        calls["n"] += 1
        state["v"] += 1024
        return {"eth0": FakeNic(bytes_sent=state["v"], bytes_recv=state["v"] // 2)}

    return counters, calls


def make_stats() -> dict:
    return {"eth0": SimpleNamespace(isup=True)}


def make_result(
    *,
    day: datetime.date = TODAY,
    up: int = 0,
    down: int = 0,
    day_rolled: bool = False,
) -> SampleResult:
    """直接构造 SampleResult (阈值逻辑单测; 采样本身的守阵在 test_sampler.py)."""
    return SampleResult(
        day=day,
        day_up_bytes=up,
        day_down_bytes=down,
        delta_up_bytes=0,
        delta_down_bytes=0,
        counter_reset=False,
        day_rolled=day_rolled,
        baseline=False,
    )


class RecordingPusher:
    """推送替身: 记录 (endpoint, token, event, timeout) 调用 (线程安全)。

    可选 behaviors: endpoint -> 回调 (用来模拟假死/报错端点)。
    """
    def __init__(self, behaviors: Optional[Mapping[str, Callable[[], None]]] = None) -> None:
        self.calls: list[tuple[str, str, dict, float]] = []
        self.behaviors = dict(behaviors or {})
        self._lock = threading.Lock()

    def __call__(self, endpoint: str, token: str, event: Mapping[str, object], timeout_s: float) -> None:
        with self._lock:
            self.calls.append((endpoint, token, dict(event), timeout_s))
        behavior = self.behaviors.get(endpoint)
        if behavior is not None:
            behavior()

    @property
    def endpoints(self) -> list[str]:
        with self._lock:
            return [c[0] for c in self.calls]


class FakeClock:
    """通知器挂钟替身 (拨钟验租约剔除)。"""
    def __init__(self, t: float = FAKE_EPOCH) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def make_env(
    tmp_path: Path,
    *,
    config: Optional[Config] = None,
    pusher: Optional[Callable] = None,
    clock: Optional[Callable[[], float]] = None,
    max_inflight: int = 32,
) -> tuple[Storage, ConfigHolder, Notifier]:
    """装配 (storage, holder, notifier); 锁已持有, 数据目录 = tmp_path。"""
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))  # S12: 锁锚点注入 tmp
    storage.acquire_lock()
    holder = ConfigHolder(config or Config())
    notifier = Notifier(
        storage,
        holder,
        pusher=pusher or RecordingPusher(),
        clock=clock or FakeClock(),
        max_inflight=max_inflight,
    )
    return storage, holder, notifier


def subscribe(storage: Storage, sub_id: str, endpoint: str, token: str = "tok") -> None:
    storage.upsert_subscriber(sub_id, endpoint, token)


@contextlib.contextmanager
def capture_notifier_logs(level: int = logging.WARNING):
    """挂 handler 到 gtm.notifier 自建 logger (不碰 caplog —— 见 pitfalls/testing/log-capture)."""
    target = logging.getLogger("gtm.notifier")
    records: list[logging.LogRecord] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Handler(level=level)
    old_level = target.level
    target.addHandler(handler)
    target.setLevel(level)
    try:
        yield records
    finally:
        target.removeHandler(handler)
        target.setLevel(old_level)


# ---- 阈值判定 (计划 S4 出口: 阈值触发单测) ----


def test_below_threshold_no_event(tmp_path) -> None:
    storage, _, notifier = make_env(tmp_path)  # 默认阈值 100 MiB
    subscribe(storage, "s1", "http://h/1")
    try:
        assert notifier.notify(make_result(up=50 * MIB, down=10 * MIB)) is None
        assert storage.last_event_id == 0
        assert notifier.pending_pushes == 0
    finally:
        storage.release_lock()


def test_threshold_triggers_event_with_plan_body(tmp_path) -> None:
    """达阈值 -> 事件体为计划 §04 S4 的六字段 (不多不少)."""
    pusher = RecordingPusher()
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000), pusher=pusher)
    subscribe(storage, "s1", "http://h/1", "tok-1")
    try:
        assert notifier.notify(make_result(up=500)) is None  # 首样本只立基数
        event = notifier.notify(make_result(up=1600))  # 累计 1600 >= 1000
        assert event is not None
        assert set(event) == {"event_id", "day", "up_bytes", "down_bytes", "total_bytes", "ts"}
        assert event["event_id"] == 1
        assert event["day"] == "2026-10-16"
        assert event["up_bytes"] == 1600 and event["down_bytes"] == 0
        assert event["total_bytes"] == 1600
        assert event["ts"] == FAKE_EPOCH
        assert storage.last_event_id == 1
        assert notifier.wait_idle(5.0)
        assert pusher.endpoints == ["http://h/1"]
        assert pusher.calls[0][1] == "tok-1"  # 订阅时登记的 token 作 Bearer
        assert pusher.calls[0][2] == event  # 推送的就是事件体本身
        assert pusher.calls[0][3] == 3.0  # notify_timeout_s 默认
    finally:
        storage.release_lock()


def test_accumulation_is_relative_to_last_event(tmp_path) -> None:
    """累计基数 = 距上次事件的当日合计变化 (逐样本累加, 不是单样本 delta)."""
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000))
    try:
        assert notifier.notify(make_result(up=400)) is None  # 立基数
        assert notifier.notify(make_result(up=700)) is None  # +300
        assert notifier.notify(make_result(up=1000)) is None  # +300, 累计 600 < 1000
        assert notifier.notify(make_result(up=1300)) is None  # +300, 累计 900 < 1000
        event = notifier.notify(make_result(up=1600))  # +300, 累计 1200 >= 1000
        assert event is not None and event["event_id"] == 1
    finally:
        storage.release_lock()


def test_threshold_hot_reload(tmp_path) -> None:
    """阈值经 ConfigHolder 现读: PUT /config 抬阈值后同一增量不再触发."""
    storage, holder, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000))
    try:
        assert notifier.notify(make_result(up=0)) is None
        holder.replace(Config(notify_threshold_bytes=10_000))
        assert notifier.notify(make_result(up=5000)) is None  # 5000 < 10000
        assert notifier.notify(make_result(up=12_000)) is not None  # 累计 12000 >= 10000
    finally:
        storage.release_lock()


# ---- 去重与事件号 ----


def test_same_window_not_reemitted_and_ids_monotonic(tmp_path) -> None:
    """同一累计窗口只发一次 (派发后基数推进) + 事件号单调递增 (订阅方据此去重)."""
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000))
    try:
        assert notifier.notify(make_result(up=0)) is None
        first = notifier.notify(make_result(up=1200))
        assert first is not None and first["event_id"] == 1
        # 同一读数重复投喂: 累计为 0 -> 不重复发事件 (重复投递去重的发送侧)
        assert notifier.notify(make_result(up=1200)) is None
        assert notifier.notify(make_result(up=1200)) is None
        second = notifier.notify(make_result(up=2400))  # 又攒够一个阈值
        assert second is not None and second["event_id"] == 2
        assert storage.last_event_id == 2
    finally:
        storage.release_lock()


def test_day_rollover_resets_baseline_without_event(tmp_path) -> None:
    """跨天: 合计清零只重置基数, 不产生伪事件 (否则会被当负 delta/巨量变化).

    判据必须落在「前一日合计**小于**新日首样本合计」的形态上 —— 若前一日合计更大,
    `total < _last_total` 的回退检查会替 day_rolled 兜底, 守阵就测不到这条分支
    (红验实测: 首版用例正是被回退检查掩盖, 突变未判红)。
    """
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000))
    try:
        assert notifier.notify(make_result(up=100)) is None  # 立基数 100 (前日小流量)
        # 跨天: 新日首样本 1536 > 前日 100 —— 缺 day_rolled 判据就会被当 1436 的变化推事件
        assert notifier.notify(make_result(day=TOMORROW, up=1536, day_rolled=True)) is None
        assert storage.last_event_id == 0
        # 新日重新攒够阈值才发
        event = notifier.notify(make_result(day=TOMORROW, up=2600))
        assert event is not None and event["day"] == "2026-10-17"
    finally:
        storage.release_lock()


def test_total_regression_only_resets_baseline(tmp_path) -> None:
    """累计回退 (不该发生, 防御): 只重置基数, 不发事件."""
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000))
    try:
        assert notifier.notify(make_result(up=10_000)) is None
        assert notifier.notify(make_result(up=100)) is None
        assert notifier.notify(make_result(up=900)) is None  # 从 100 起算, 800 < 1000
        assert notifier.notify(make_result(up=1200)) is not None
    finally:
        storage.release_lock()


# ---- 启动补发 ----


def test_catch_up_emits_once_regardless_of_threshold(tmp_path) -> None:
    """启动/崩溃恢复后首帧补发一次: 不看阈值, 只发一次 (后续回归阈值判定)."""
    pusher = RecordingPusher()
    storage, _, notifier = make_env(tmp_path, pusher=pusher)  # 默认阈值 100 MiB
    subscribe(storage, "s1", "http://h/1")
    try:
        event = notifier.notify(make_result(up=1), catch_up=True)
        assert event is not None and event["event_id"] == 1
        assert notifier.wait_idle(5.0)
        assert pusher.endpoints == ["http://h/1"]
        # 补发后回到阈值判定: 同一读数不再发
        assert notifier.notify(make_result(up=1)) is None
        assert storage.last_event_id == 1
    finally:
        storage.release_lock()


def test_catch_up_event_id_continues_after_restart(tmp_path) -> None:
    """重启 (新 Storage + recover) 后首帧补发的事件号接续, 不回到 1."""
    storage, _, notifier = make_env(tmp_path)
    try:
        assert notifier.notify(make_result(up=0), catch_up=True)["event_id"] == 1
    finally:
        storage.release_lock()
    storage2, _, notifier2 = make_env(tmp_path)
    try:
        storage2.recover(Sampler())
        assert storage2.last_event_id == 1
        assert notifier2.notify(make_result(up=5), catch_up=True)["event_id"] == 2
    finally:
        storage2.release_lock()


def test_baseline_not_advanced_when_dispatch_raises(tmp_path) -> None:
    """派发路径抛错时基数不推进 -> 阈值窗口保留, 下一轮重试 (不静默丢事件)."""
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1000))
    original = storage.bump_event_id

    def boom() -> int:
        raise OSError("state 落盘失败")

    try:
        assert notifier.notify(make_result(up=0)) is None  # 立基数 0
        storage.bump_event_id = boom  # type: ignore[method-assign]
        with pytest.raises(OSError):
            notifier.notify(make_result(up=5000))  # 5000 >= 1000 但派发失败
        storage.bump_event_id = original  # type: ignore[method-assign]
        event = notifier.notify(make_result(up=5000))  # 基数仍是 0 -> 仍触发
        assert event is not None and event["event_id"] == 1
    finally:
        storage.bump_event_id = original  # type: ignore[method-assign]
        storage.release_lock()


def test_event_id_persisted_across_restart(tmp_path) -> None:
    """bump_event_id 落 state.json: 重启接续 (订阅方按事件号单调去重的前提)."""
    storage, _, notifier = make_env(tmp_path)
    try:
        notifier.notify(make_result(up=0), catch_up=True)
        notifier.notify(make_result(up=1), catch_up=True)
        assert storage.last_event_id == 2
        state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
        assert state["last_event_id"] == 2
    finally:
        storage.release_lock()
    storage2, _, notifier2 = make_env(tmp_path)
    try:
        storage2.recover(Sampler())
        assert storage2.last_event_id == 2
        assert notifier2.notify(make_result(up=2), catch_up=True)["event_id"] == 3
    finally:
        storage2.release_lock()


# ---- 推送面 ----


def test_push_reaches_all_subscribers(tmp_path) -> None:
    pusher = RecordingPusher()
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1), pusher=pusher)
    subscribe(storage, "s1", "http://h/1", "tok-1")
    subscribe(storage, "s2", "http://h/2", "tok-2")
    try:
        assert notifier.notify(make_result(up=10), catch_up=True) is not None
        assert notifier.wait_idle(5.0)
        assert sorted(pusher.endpoints) == ["http://h/1", "http://h/2"]
        tokens = {c[0]: c[1] for c in pusher.calls}
        assert tokens == {"http://h/1": "tok-1", "http://h/2": "tok-2"}
    finally:
        storage.release_lock()


def test_no_subscribers_still_emits_event(tmp_path) -> None:
    """无订阅者仍推进事件号 (事件号是全局单调序号, 不因当前无人订阅而回退)."""
    storage, _, notifier = make_env(tmp_path)
    try:
        event = notifier.notify(make_result(up=0), catch_up=True)
        assert event is not None and storage.last_event_id == 1
        assert notifier.pending_pushes == 0
    finally:
        storage.release_lock()


def test_expired_subscriber_pruned_before_push(tmp_path) -> None:
    """通知前租约懒剔除 (与控制面请求入口同纪律): 过期订阅者不收推送."""
    pusher = RecordingPusher()
    storage, _, notifier = make_env(tmp_path, pusher=pusher)
    subscribe(storage, "old", "http://h/old")
    subscribe(storage, "fresh", "http://h/fresh")
    storage._subscribers["old"]["last_heartbeat"] = 0.0  # noqa: SLF001 - 测试拨钟
    try:
        assert notifier.notify(make_result(up=0), catch_up=True) is not None
        assert notifier.wait_idle(5.0)
        assert pusher.endpoints == ["http://h/fresh"]
        assert set(storage.subscribers) == {"fresh"}
    finally:
        storage.release_lock()


def test_push_flushes_dat_first(tmp_path) -> None:
    """推送前先落盘: 订阅者收到事件时 dat 已含当前值 (不落在节流窗口里)."""
    seen: list[str] = []
    box: dict[str, str] = {}

    def pusher(endpoint: str, token: str, event: Mapping[str, object], timeout_s: float) -> None:
        seen.append(Path(box["dat"]).read_text(encoding="utf-8"))

    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1), pusher=pusher)
    box["dat"] = storage.dat_path
    subscribe(storage, "s1", "http://h/1")
    try:
        # 首帧落盘 (节流首帧必落) 后, 再记一笔小增量: 落在节流窗口内 -> dat 未更新
        storage.record(make_result(up=5 * KB, down=3 * KB), {"version": 1})
        second = make_result(up=9 * KB, down=4 * KB)
        storage.record(second, {"version": 1})
        assert " 5/3" in Path(storage.dat_path).read_text(encoding="utf-8")  # 盘上仍是旧值
        assert notifier.notify(second, catch_up=True) is not None
        assert notifier.wait_idle(5.0)
        assert len(seen) == 1
        rows = [m.groups() for m in (DAT_ROW_RE.match(ln.strip()) for ln in seen[0].splitlines()) if m]
        assert rows == [("2026", "10", "16", str(9), str(4))]  # 推送时盘上已是当前值 (KB)
    finally:
        storage.release_lock()


# ---- 失败面 ----


def test_dead_endpoint_warns_and_does_not_raise(tmp_path) -> None:
    """假死端点 (超时/连接失败) 只记 WARNING, 不抛不重试 (订阅者慢轮询兜底)."""
    def dead() -> None:
        raise TimeoutError("timed out")

    pusher = RecordingPusher({"http://dead": dead})
    storage, _, notifier = make_env(tmp_path, config=Config(notify_timeout_s=0.5), pusher=pusher)
    subscribe(storage, "s1", "http://dead")
    try:
        with capture_notifier_logs(logging.WARNING) as records:
            assert notifier.notify(make_result(up=0), catch_up=True) is not None
            assert notifier.wait_idle(5.0)
            assert any("通知推送失败" in r.getMessage() for r in records)
    finally:
        storage.release_lock()


def test_one_slow_subscriber_does_not_delay_others(tmp_path) -> None:
    """每订阅者一线程: 假死端点占满自己的超时窗口, 不拖慢其它订阅者 (互不干扰)."""
    release = threading.Event()

    def slow() -> None:
        release.wait(5.0)  # 模拟假死: 一直占着, 直到测试放行

    pusher = RecordingPusher({"http://slow": slow})
    storage, _, notifier = make_env(tmp_path, config=Config(notify_timeout_s=3.0), pusher=pusher)
    subscribe(storage, "slow", "http://slow")
    subscribe(storage, "fast", "http://fast")
    try:
        started = time.monotonic()
        assert notifier.notify(make_result(up=0), catch_up=True) is not None
        # 健康订阅者应在远小于 slow 端点超时窗口内收到
        deadline = started + 1.0
        while "http://fast" not in pusher.endpoints and time.monotonic() < deadline:
            time.sleep(0.01)
        assert pusher.endpoints.count("http://fast") == 1
        assert time.monotonic() - started < 1.0
        # slow 仍在途 (快线程已摘除自己)
        deadline = time.monotonic() + 1.0
        while notifier.pending_pushes != 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert notifier.pending_pushes == 1
    finally:
        release.set()
        assert notifier.wait_idle(5.0)
        storage.release_lock()


def test_inflight_cap_skips_dispatch(tmp_path) -> None:
    """在途线程达上限: 跳过本轮派发并 WARNING (不静默堆积线程)."""
    release = threading.Event()
    pusher = RecordingPusher({"http://slow": lambda: release.wait(5.0)})
    storage, _, notifier = make_env(tmp_path, config=Config(notify_threshold_bytes=1), pusher=pusher, max_inflight=1)
    subscribe(storage, "s1", "http://slow")
    try:
        assert notifier.notify(make_result(up=10), catch_up=True) is not None
        assert notifier.pending_pushes == 1
        with capture_notifier_logs(logging.WARNING) as records:
            event = notifier.notify(make_result(up=20), catch_up=True)
            assert event is not None and event["event_id"] == 2  # 事件号照常推进
            assert any("上限" in r.getMessage() for r in records)
        assert len(pusher.calls) == 1  # 第二条被跳过
    finally:
        release.set()
        assert notifier.wait_idle(5.0)
        storage.release_lock()


# ---- 不阻塞采样循环 (计划 S4 出口: 两订阅者含假死端点, >10s 压测) ----

PRESSURE_SECONDS = 10.0


def test_push_does_not_block_sampling_loop(tmp_path) -> None:
    """真 _run_loop + 两订阅者 (一假死): 10s 内采样帧数持续增长, 停止信号即时收尾.

    假死端点的推送线程占满 notify_timeout_s (3s) 才抛 —— 若推送在采样线程里同步做,
    循环会卡在第一个假死端点上, 帧数停在个位数且停止后线程 join 不回来。
    """
    release = threading.Event()
    delivered: list[int] = []
    lock = threading.Lock()

    def pusher(endpoint: str, token: str, event: Mapping[str, object], timeout_s: float) -> None:
        if endpoint == "http://dead":
            release.wait(timeout_s)
            raise TimeoutError("simulated dead endpoint")
        with lock:
            delivered.append(int(event["event_id"]))  # type: ignore[arg-type]

    config = Config(sample_interval=0.05, notify_threshold_bytes=100_000, notify_timeout_s=3.0)
    storage, holder, notifier = make_env(tmp_path, config=config, pusher=pusher, clock=time.time)
    subscribe(storage, "dead", "http://dead")
    subscribe(storage, "live", "http://live")
    counters, calls = make_counters()
    sampler = Sampler(clock=lambda: FIXED_NOW, counters_provider=counters, stats_provider=make_stats)
    stop = threading.Event()
    loop = threading.Thread(target=_run_loop, args=(storage, sampler, holder, stop, notifier), daemon=True)
    loop.start()
    try:
        time.sleep(PRESSURE_SECONDS)
        frames = calls["n"]
        assert frames >= 60, f"采样循环被推送阻塞? 10s 只采了 {frames} 帧"
        assert loop.is_alive()
    finally:
        stop.set()
        loop.join(timeout=5.0)
        release.set()
        assert notifier.wait_idle(5.0)
        storage.release_lock()
    assert not loop.is_alive(), "停止信号未能即时收尾 (循环可能卡在同步推送上)"
    with lock:
        assert delivered, "健康订阅者未收到任何事件"
    assert storage.last_event_id >= 1  # 阈值事件确实发生过


# ---- 生产推送单点 (真 HTTP; 默认 pusher 的唯一覆盖) ----


class Receiver:
    """本地 HTTP 接收端替身 (真 socket): 记录 (path, headers, body), 可指定状态码。"""
    def __init__(self, status: int = 200) -> None:
        self.received: list[tuple[str, dict, dict]] = []
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib 命名
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                outer.received.append((self.path, dict(self.headers), json.loads(raw.decode("utf-8"))))
                self.send_response(status)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{self._httpd.server_address[1]}/api/traffic/monitor/notify"

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5.0)


def test_http_push_posts_json_with_bearer_token() -> None:
    """生产推送单点: POST JSON + `Authorization: Bearer <token>` 到订阅端点."""
    receiver = Receiver()
    try:
        http_push(receiver.url, "tok-abc", {"event_id": 7, "day": "2026-10-16", "total_bytes": 42}, 3.0)
        assert len(receiver.received) == 1
        path, headers, body = receiver.received[0]
        assert path == "/api/traffic/monitor/notify"
        assert headers["Authorization"] == "Bearer tok-abc"
        assert headers["Content-Type"].startswith("application/json")
        assert body == {"event_id": 7, "day": "2026-10-16", "total_bytes": 42}
    finally:
        receiver.stop()


def test_http_push_raises_on_error_status() -> None:
    """非 2xx 由 urlopen 抛 HTTPError -> 由调用方兜成 WARNING (不静默当成功)."""
    receiver = Receiver(status=500)
    try:
        with pytest.raises(Exception):
            http_push(receiver.url, "tok", {"event_id": 1}, 3.0)
    finally:
        receiver.stop()


def test_notifier_default_pusher_reaches_real_subscriber(tmp_path) -> None:
    """通知器默认 pusher (= http_push) 端到端: 真 HTTP 接收端收到事件体 + Bearer token."""
    receiver = Receiver()
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))  # S12: 锁锚点注入 tmp
    storage.acquire_lock()
    holder = ConfigHolder(Config(notify_threshold_bytes=1))
    notifier = Notifier(storage, holder)  # 不注入 pusher -> 走生产 http_push
    storage.upsert_subscriber("s1", receiver.url, "tok-e2e")
    try:
        assert notifier.notify(make_result(up=10), catch_up=True) is not None
        assert notifier.wait_idle(5.0)
        assert len(receiver.received) == 1
        _, headers, body = receiver.received[0]
        assert headers["Authorization"] == "Bearer tok-e2e"
        assert body["event_id"] == 1 and body["total_bytes"] == 10
    finally:
        receiver.stop()
        storage.release_lock()


# ---- 生命周期 ----


def test_close_stops_dispatch(tmp_path) -> None:
    pusher = RecordingPusher()
    storage, _, notifier = make_env(tmp_path, pusher=pusher)
    subscribe(storage, "s1", "http://h/1")
    try:
        notifier.close()
        event = notifier.notify(make_result(up=0), catch_up=True)
        assert event is not None  # 事件号照常推进 (仅不再派发)
        assert pusher.calls == []
        assert notifier.pending_pushes == 0
    finally:
        storage.release_lock()


def test_wait_idle_returns_after_inflight_done(tmp_path) -> None:
    release = threading.Event()
    pusher = RecordingPusher({"http://h/1": lambda: release.wait(5.0)})
    storage, _, notifier = make_env(tmp_path, pusher=pusher)
    subscribe(storage, "s1", "http://h/1")
    try:
        notifier.notify(make_result(up=0), catch_up=True)
        assert notifier.wait_idle(0.05) is False  # 在途未结束 -> 超时返回 False
        release.set()
        assert notifier.wait_idle(5.0) is True
    finally:
        storage.release_lock()
