"""S1 采样器守阵: delta / 重置归零 / 跨天硬切 / 适配器过滤 / state 恢复降级 / dat 兜底.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S1).
全部用例 hermetic: clock/counters/stats 一律注入替身, 不碰真实网卡与文件.

## 测试计划

- 正常 delta: 两样本差值进入当日累计; day_total_bytes = up+down
- 重置归零: 上行/下行/双侧重置三种, delta 记 0 + 告警, 不产生负流量, 另一侧正常计
- 跨天硬切: day_rolled=True, 旧日累计清零, 跨日流量计入新日
- 基线: 首样本 delta 恒 0 + baseline=True; 全过滤空场景告警
- 适配器过滤: loopback 三名形态 (lo/lo0/Loopback Pseudo-Interface 1) / down / include 白名单 /
  exclude 黑名单 / stats 缺失不收编 / 顺序优先级 (include 不翻案 loopback 开关)
- state 恢复: 今天载荷累计+基线接续; 昨天载荷累计清零基线接续; 未来/损坏/非映射/版本不符 ->
  降级 (告警 + 无基线); 降级后首样本 baseline=True
- dat 兜底: 今天行恢复 (KB->字节, TM 倒序与正序两态); 无今天行返回 False; 基线仍取当前值
- snapshot/restore round-trip: 快照载荷恢复后与原状态一致
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Mapping, Optional

from gtm.sampler import AdapterFilter, Sampler, SampleResult, is_loopback

DAY = date(2026, 10, 16)
T0 = datetime(2026, 10, 16, 10, 0, 0)


class FakeClock:
    """可拖动的时钟: sample_once / restore / restore_from_dat 各取一次当前值."""
    def __init__(self, now: datetime = T0) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakeCounters:
    """可换页的 net_io_counters 替身."""
    def __init__(self, page: Optional[Mapping[str, SimpleNamespace]] = None) -> None:
        self.page: Mapping[str, SimpleNamespace] = page or {}

    def __call__(self) -> Mapping[str, SimpleNamespace]:
        return self.page


def nic(sent: int, recv: int) -> SimpleNamespace:
    return SimpleNamespace(bytes_sent=sent, bytes_recv=recv)


def stats_page(down: tuple[str, ...] = ()) -> dict[str, SimpleNamespace]:
    """eth0/lo/wlan0/vet 全部 up, 除显式列入 down 的网卡."""
    return {name: SimpleNamespace(isup=name not in down) for name in ("eth0", "lo", "wlan0", "vet")}


def make_sampler(
    clock: Optional[FakeClock] = None,
    counters: Optional[FakeCounters] = None,
    stats: Optional[Mapping[str, SimpleNamespace]] = None,
    adapter_filter: Optional[AdapterFilter] = None,
) -> tuple[Sampler, FakeClock, FakeCounters]:
    clock = clock or FakeClock()
    counters = counters or FakeCounters()
    stats = stats if stats is not None else stats_page()
    sampler = Sampler(
        adapter_filter=adapter_filter,
        clock=clock,
        counters_provider=counters,
        stats_provider=lambda: stats,
    )
    return sampler, clock, counters


# ---- 正常 delta ----


def test_normal_delta_accumulates_into_day():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1000, 2000)}
    r1 = sampler.sample_once()
    assert r1.baseline is True and r1.delta_up_bytes == 0 and r1.delta_down_bytes == 0
    assert (r1.day_up_bytes, r1.day_down_bytes) == (0, 0)

    counters.page = {"eth0": nic(1500, 2300)}
    r2 = sampler.sample_once()
    assert r2.baseline is False
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (500, 300)
    assert (r2.day_up_bytes, r2.day_down_bytes) == (500, 300)
    assert r2.day_total_bytes == 800
    assert r2.counter_reset is False and r2.day_rolled is False and r2.warnings == ()


def test_multi_adapter_totals_sum_after_filter():
    # wlan0 down 被默认排除; lo 回环被默认排除; eth0/vet 计入
    sampler, _, counters = make_sampler(stats=stats_page(down=("wlan0", )))
    counters.page = {"eth0": nic(10, 20), "wlan0": nic(100, 200), "lo": nic(1000, 1000), "vet": nic(5, 7)}
    r1 = sampler.sample_once()
    assert r1.baseline is True
    counters.page = {"eth0": nic(60, 70), "wlan0": nic(160, 260), "lo": nic(1200, 1200), "vet": nic(15, 17)}
    r2 = sampler.sample_once()
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (50 + 10, 50 + 10)


# ---- 计数器重置 ----


def test_counter_reset_up_only_zeroes_up_keeps_down():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1000, 2000)}
    sampler.sample_once()
    counters.page = {"eth0": nic(300, 2400)}  # up 回落 (网卡重连), down 正常
    r = sampler.sample_once()
    assert r.counter_reset is True
    assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 400)
    assert (r.day_up_bytes, r.day_down_bytes) == (0, 400)
    assert len(r.warnings) == 1 and "上行计数器重置" in r.warnings[0]


def test_counter_reset_both_zeroes_both():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1000, 2000)}
    sampler.sample_once()
    counters.page = {"eth0": nic(10, 20)}
    r = sampler.sample_once()
    assert r.counter_reset is True
    assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 0)
    assert (r.day_up_bytes, r.day_down_bytes) == (0, 0)
    assert len(r.warnings) == 2


def test_counter_reset_never_negative_across_many_samples():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(100, 100)}
    sampler.sample_once()
    for sent in (90, 80, 70):
        counters.page = {"eth0": nic(sent, 100)}
        r = sampler.sample_once()
        assert r.day_up_bytes == 0 and r.day_down_bytes == 0
        assert r.delta_up_bytes == 0 and r.delta_down_bytes == 0


def test_all_adapters_filtered_warns_and_counts_zero():
    sampler, _, counters = make_sampler()
    counters.page = {"lo": nic(500, 500)}  # 只有回环 -> 全被默认过滤
    r1 = sampler.sample_once()
    assert r1.baseline is True
    assert any("无适配器通过过滤" in w for w in r1.warnings)
    counters.page = {"eth0": nic(100, 100)}
    r2 = sampler.sample_once()
    # 基线(0) -> 100: 缺失窗流量打进恢复后首包 (文档声明的抖动语义)
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (100, 100)


# ---- 跨天硬切 ----


def test_day_rollover_resets_accumulation():
    sampler, clock, counters = make_sampler()
    counters.page = {"eth0": nic(100, 200)}
    sampler.sample_once()
    counters.page = {"eth0": nic(300, 500)}  # +200/+300
    r = sampler.sample_once()
    assert (r.day_up_bytes, r.day_down_bytes) == (200, 300)

    clock.now = datetime(2026, 10, 17, 0, 0, 1)
    counters.page = {"eth0": nic(400, 560)}  # 跨天后 +100/+60
    r2 = sampler.sample_once()
    assert r2.day_rolled is True
    assert r2.day == date(2026, 10, 17)
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (100, 60)
    assert (r2.day_up_bytes, r2.day_down_bytes) == (100, 60)  # 旧日累计已清零
    assert r2.counter_reset is False


# ---- 适配器过滤 ----


def test_loopback_names_all_platforms():
    assert is_loopback("lo") and is_loopback("lo0") and is_loopback("LOOPBACK")
    assert is_loopback("Loopback Pseudo-Interface 1")
    assert not is_loopback("eth0") and not is_loopback("localnet")


def test_exclude_down_adapter():
    stats = stats_page(down="wlan0")
    sampler, _, counters = make_sampler(stats=stats)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(999, 999)}
    sampler.sample_once()
    counters.page = {"eth0": nic(10, 10), "wlan0": nic(1999, 1999)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (10, 10)


def test_down_adapter_recovering_counts_from_zero():
    stats = stats_page(down="wlan0")
    sampler, _, counters = make_sampler(stats=stats)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(999, 999)}
    sampler.sample_once()
    # wlan0 恢复 up: 过滤条件变化后其缺失窗流量打进首包 (与重置同理的抖动语义)
    stats["wlan0"] = SimpleNamespace(isup=True)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(1999, 1999)}
    r = sampler.sample_once()
    # 基线时合计 0 (wlan0 被过滤), 恢复后合计 = 0+1999: 缺失窗流量全额打进首包
    assert (r.delta_up_bytes, r.delta_down_bytes) == (1999, 1999)


def test_include_whitelist_and_exclude_blacklist():
    filt = AdapterFilter(include=r"^(eth0|wlan0)$", exclude="wlan0")
    sampler, _, counters = make_sampler(adapter_filter=filt)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(500, 500), "vet": nic(700, 700)}
    sampler.sample_once()
    counters.page = {"eth0": nic(100, 100), "wlan0": nic(900, 900), "vet": nic(1400, 1400)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (100, 100)  # 只剩 eth0


def test_include_does_not_override_loopback_switch():
    # include 白名单显式含 lo, 但 exclude_loopback 默认 True 仍剔除 (固定顺序, 文档明示)
    filt = AdapterFilter(include=r"^(eth0|lo)$")
    sampler, _, counters = make_sampler(adapter_filter=filt)
    counters.page = {"eth0": nic(0, 0), "lo": nic(400, 400)}
    sampler.sample_once()
    counters.page = {"eth0": nic(100, 100), "lo": nic(900, 900)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (100, 100)


def test_explicitly_including_loopback_works_when_switch_off():
    filt = AdapterFilter(include=r"^lo$", exclude_loopback=False, exclude_down=False)
    sampler, _, counters = make_sampler(adapter_filter=filt)
    counters.page = {"eth0": nic(0, 0), "lo": nic(400, 400)}
    sampler.sample_once()
    counters.page = {"eth0": nic(1000, 1000), "lo": nic(900, 900)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (500, 500)


def test_stats_missing_for_adapter_included():
    # psutil 给了计数器却没给状态的网卡: 默认不收编为 down (保守口径的反面是丢量, 取计入)
    sampler, _, counters = make_sampler(stats={})
    counters.page = {"eth0": nic(0, 0)}
    sampler.sample_once()
    counters.page = {"eth0": nic(50, 50)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (50, 50)


# ---- state 恢复 ----


def test_restore_same_day_resumes_accumulation_and_baseline():
    sampler, _, counters = make_sampler()
    snap = {
        "version": 1,
        "day": "2026-10-16",
        "day_up_bytes": 4096,
        "day_down_bytes": 8192,
        "last_up_bytes": 5000,
        "last_down_bytes": 9000
    }
    warns = sampler.restore(snap)
    assert warns == ()
    assert sampler.day == DAY and sampler.day_up_bytes == 4096 and sampler.day_down_bytes == 8192
    counters.page = {"eth0": nic(5600, 9300)}  # 相对恢复的基线 +600/+300
    r = sampler.sample_once()
    assert r.baseline is False
    assert (r.day_up_bytes, r.day_down_bytes) == (4096 + 600, 8192 + 300)


def test_restore_yesterday_clears_accumulation_keeps_baseline():
    sampler, _, counters = make_sampler()
    snap = {
        "version": 1,
        "day": "2026-10-15",
        "day_up_bytes": 4096,
        "day_down_bytes": 8192,
        "last_up_bytes": 5000,
        "last_down_bytes": 9000
    }
    warns = sampler.restore(snap)
    assert len(warns) == 1 and "早于今天" in warns[0]
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (0, 0)
    counters.page = {"eth0": nic(5100, 9100)}
    r = sampler.sample_once()
    assert (r.day_up_bytes, r.day_down_bytes) == (100, 100)  # 跨天停机窗流量归今天


def test_restore_future_day_is_degraded():
    sampler, _, _ = make_sampler()
    snap = {
        "version": 1,
        "day": "2026-10-17",
        "day_up_bytes": 1,
        "day_down_bytes": 1,
        "last_up_bytes": 1,
        "last_down_bytes": 1
    }
    warns = sampler.restore(snap)
    assert len(warns) == 1 and "时钟偏差" in warns[0]
    assert not sampler.has_baseline


def test_restore_none_is_degraded_first_sample_is_baseline():
    sampler, _, counters = make_sampler()
    warns = sampler.restore(None)
    assert len(warns) == 1 and "缺失" in warns[0]
    assert not sampler.has_baseline
    counters.page = {"eth0": nic(100, 200)}
    r = sampler.sample_once()
    assert r.baseline is True
    assert (r.day_up_bytes, r.day_down_bytes) == (0, 0)


def test_restore_corrupt_variants_all_degraded():
    base = {
        "version": 1,
        "day": "2026-10-16",
        "day_up_bytes": 1,
        "day_down_bytes": 1,
        "last_up_bytes": 1,
        "last_down_bytes": 1
    }
    bad_cases = [
        "not-a-mapping",
        {
            "day": "2026-10-16",
            "day_up_bytes": 1,
            "day_down_bytes": 1,
            "last_up_bytes": 1,
            "last_down_bytes": 1
        },  # 缺 version
        dict(base, version=2),
        dict(base, day="not-a-date"),
        dict(base, day_up_bytes="abc"),
        dict(base, last_down_bytes=-5),
        dict(base, day="2026/10/16"),  # 非 ISO
    ]
    for bad in bad_cases:
        sampler, _, _ = make_sampler()
        warns = sampler.restore(bad)
        assert len(warns) == 1, bad
        assert not sampler.has_baseline, bad
        assert sampler.day is None, bad


def test_restore_valid_state_without_baseline_allows_baseline_sample():
    # 合法载荷但 last_* 为 None (首次采样前宕机): 不算损坏, 首样本走 baseline
    sampler, _, counters = make_sampler()
    snap = {
        "version": 1,
        "day": "2026-10-16",
        "day_up_bytes": 10,
        "day_down_bytes": 20,
        "last_up_bytes": None,
        "last_down_bytes": None
    }
    warns = sampler.restore(snap)
    assert warns == ()
    counters.page = {"eth0": nic(100, 200)}
    r = sampler.sample_once()
    assert r.baseline is True
    assert (r.day_up_bytes, r.day_down_bytes) == (10, 20)  # 累计保留, 无 delta


# ---- dat 兜底 ----


def test_restore_from_dat_today_row_tm_reverse_order():
    sampler, _, _ = make_sampler()
    text = 'lines: "2"\n2026/10/16 100/200\n2026/10/15 90/190\n'
    assert sampler.restore_from_dat(text) is True
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (100 * 1024, 200 * 1024)
    assert sampler.day == DAY
    assert not sampler.has_baseline  # 基线仍取当前值


def test_restore_from_dat_today_row_chronological_order():
    sampler, _, _ = make_sampler()
    text = "2026/10/14 5/6\n2026/10/15 90/190\n2026/10/16 100/200\n"
    assert sampler.restore_from_dat(text) is True
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (100 * 1024, 200 * 1024)


def test_restore_from_dat_takes_last_matching_today_row():
    sampler, _, _ = make_sampler()
    text = "2026/10/16 100/200\n2026/10/16 111/222\n"
    assert sampler.restore_from_dat(text) is True
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (111 * 1024, 222 * 1024)


def test_restore_from_dat_no_today_row_returns_false():
    sampler, _, _ = make_sampler()
    assert sampler.restore_from_dat('lines: "1"\n2026/10/15 90/190\n') is False
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (0, 0)
    assert sampler.day is None


def test_restore_from_dat_ignores_bad_lines_and_empty():
    sampler, _, _ = make_sampler()
    assert sampler.restore_from_dat("") is False
    assert sampler.restore_from_dat("garbage\n2026/13/40 1/2\n") is False
    assert sampler.day is None


def test_restore_from_dat_then_sample_baseline_from_current():
    # 计划口径: 降级路径只恢复累计, 基线取当前值
    sampler, _, counters = make_sampler()
    sampler.restore_from_dat("2026/10/16 50/60\n")
    counters.page = {"eth0": nic(7000, 8000)}
    r1 = sampler.sample_once()
    assert r1.baseline is True
    assert (r1.day_up_bytes, r1.day_down_bytes) == (50 * 1024, 60 * 1024)
    counters.page = {"eth0": nic(7100, 8200)}
    r2 = sampler.sample_once()
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (100, 200)
    assert (r2.day_up_bytes, r2.day_down_bytes) == (50 * 1024 + 100, 60 * 1024 + 200)


# ---- snapshot round-trip ----


def test_snapshot_restore_round_trip():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1000, 2000)}
    sampler.sample_once()
    counters.page = {"eth0": nic(1500, 2400)}
    sampler.sample_once()
    snap = sampler.snapshot()
    assert snap == {
        "version": 1,
        "day": "2026-10-16",
        "day_up_bytes": 500,
        "day_down_bytes": 400,
        "last_up_bytes": 1500,
        "last_down_bytes": 2400
    }

    revived, _, counters2 = make_sampler()
    assert revived.restore(snap) == ()
    counters2.page = {"eth0": nic(1600, 2500)}
    r = revived.sample_once()
    assert (r.day_up_bytes, r.day_down_bytes) == (600, 500)
    assert r.baseline is False


def test_snapshot_before_any_sample():
    sampler, _, _ = make_sampler()
    assert sampler.snapshot() == {
        "version": 1,
        "day": None,
        "day_up_bytes": 0,
        "day_down_bytes": 0,
        "last_up_bytes": None,
        "last_down_bytes": None
    }
    revived, _, _ = make_sampler()
    assert revived.restore(sampler.snapshot()) == ()
    assert not revived.has_baseline


def test_sample_result_is_frozen_dataclass():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1, 1)}
    r = sampler.sample_once()
    assert isinstance(r, SampleResult)
    try:
        r.day_up_bytes = 5  # type: ignore[misc]
    except Exception as exc:  # frozen dataclass 拒绝赋值
        assert type(exc).__name__ == "FrozenInstanceError"
    else:
        raise AssertionError("SampleResult 应为 frozen dataclass")


# ---- 生产读数与边角出口 (26-10-21 覆盖率门禁 P1-T1.3) ----


def test_select_without_stats_mapping():
    """stats 整段缺失 (psutil 未给状态): 按空映射处理, 不因 None 崩 (等价于全 up)."""
    adapter_filter = AdapterFilter()
    counters = {"eth0": nic(100, 200), "lo": nic(1, 2)}
    selected = adapter_filter.select(counters)  # 不传 stats
    assert list(selected) == ["eth0"]  # loopback 仍被默认开关排除


def test_production_readers_delegate_to_psutil(monkeypatch):
    """生产读数单点 (默认注入点): read_counters/read_stats 直接转发 psutil 的同名调用."""
    import gtm.sampler as sampler_mod

    seen: list[str] = []

    def fake_counters(pernic: bool = False):
        seen.append(f"net_io_counters(pernic={pernic})")
        return {"eth0": nic(1, 2)}

    def fake_stats():
        seen.append("net_if_stats")
        return {"eth0": SimpleNamespace(isup=True)}

    monkeypatch.setattr(sampler_mod.psutil, "net_io_counters", fake_counters)
    monkeypatch.setattr(sampler_mod.psutil, "net_if_stats", fake_stats)
    assert list(sampler_mod.read_counters()) == ["eth0"]
    assert list(sampler_mod.read_stats()) == ["eth0"]
    assert seen == ["net_io_counters(pernic=True)", "net_if_stats"]


def test_restore_day_none_but_baseline_present_is_corrupt():
    """day 为 None 却留着基线字段: 自相矛盾的快照按损坏处理 (不猜哪一半是真的)."""
    sampler, _, _ = make_sampler()
    warns = sampler.restore(
        {
            "version": 1,
            "day": None,
            "day_up_bytes": 0,
            "day_down_bytes": 0,
            "last_up_bytes": 5,
            "last_down_bytes": 5,
        }
    )
    assert len(warns) == 1 and "day 为 None 但基线字段有值" in warns[0]
    assert sampler.day is None and not sampler.has_baseline


def test_restore_negative_day_bytes_is_corrupt():
    """当日累计为负: 按损坏降级 (负数只可能来自坏盘/坏移植, 不许进累计)."""
    sampler, _, _ = make_sampler()
    warns = sampler.restore(
        {
            "version": 1,
            "day": DAY.isoformat(),
            "day_up_bytes": -1,
            "day_down_bytes": 10,
            "last_up_bytes": 1,
            "last_down_bytes": 1,
        }
    )
    assert len(warns) == 1 and "当日累计为负" in warns[0]
    assert sampler.day is None
