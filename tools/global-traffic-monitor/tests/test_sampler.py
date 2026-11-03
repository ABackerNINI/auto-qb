"""S1 采样器守阵: delta / 重置归零 / 跨天硬切 / 适配器过滤 / state 恢复降级 / dat 兜底.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S1);
逐网卡基线重构: memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html (S0).
全部用例 hermetic: clock/counters/stats 一律注入替身, 不碰真实网卡与文件.

## 测试计划

- 正常 delta: 两样本差值进入当日累计; day_total_bytes = up+down; 同一读数重放 3 次
  第 2/3 轮 (0,0) (T7 幂等 I3)
- 重置归零: 上行/下行/双侧重置三种, 该卡该侧 delta 记 0 + 告警, 不产生负流量, 另一侧正常计
- 跨天硬切: day_rolled=True, 旧日累计清零, 跨日流量计入新日, 逐卡记忆保留 (T10)
- 挂钟回跳跨日界: 不硬切 (累计保持 + 采样日钉原日界 + 告警), 日界再前进恢复正常硬切
- 基线: 首样本 delta 恒 0 + baseline=True; 全过滤空场景告警且不改任何逐卡记忆
- 适配器过滤: loopback 三名形态 (lo/lo0/Loopback Pseudo-Interface 1) / down / include 白名单 /
  exclude 黑名单 / stats 缺失不收编 / 顺序优先级 (include 不翻案 loopback 开关)
- 断连-恢复: 无真实增长记 (0,0) (T1); 有真实增长只记增量 (T2); 全过滤后恢复仍记 (0,0) 且
  记忆保留 (T4); 首次出现的网卡只立基线不入账
- 多卡断连 (T3): 一张 down 期间另一张正常增长只记该卡增量, 无重置告警; down 卡回来后仍 (0,0)
- 单卡真回绕 (T5): 该卡该方向 delta 归零 + 只点名该卡的告警, 其他卡正常入账
- 新卡插入 (T6): 带大历史累计的新卡只立基线 (delta 0), 基线记为该卡当前读数
- state 恢复 (v2 载荷): 今天累计 + 逐卡基线接续; 昨天累计清零、逐卡记忆接续;
  未来/损坏/非映射/版本不符 -> 降级 (告警 + 无基线); 降级后首样本 baseline=True
- state 恢复 (v2 局部损坏, T9): 单条非法条目丢弃 + 告警, 其他条生效, day 保留;
  nic_baseline 缺失/非映射/条目非映射/缺字段同样是局部降级而非整体降级
- state 恢复 (v1 兼容): 保留 day 累计、忽略合计基线 (逐卡记忆置空), 首轮 (0,0) +
  一条「state v1 升级」告警, state_restored=True (T8)
- 逐卡记忆 TTL (T13): 超过 7 天未见的卡被清理, 再出现按新卡只立基线 (0,0)
- dat 兜底: 今天行恢复 (KB->字节, TM 倒序与正序两态); 无今天行返回 False; 基线仍取当前值
- snapshot/restore round-trip: v2 载荷 (version=2 + nic_baseline, last_* 为各卡求和) 恢复后与原状态一致
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
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


def test_replay_same_reading_is_idempotent():
    """T7 (I3 幂等): 同一组读数连续采样 3 次, 第 2/3 轮 delta 恒 (0,0)."""
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1234, 5678), "wlan0": nic(11, 22)}
    r1 = sampler.sample_once()
    assert r1.baseline is True and (r1.delta_up_bytes, r1.delta_down_bytes) == (0, 0)
    for _ in range(2):
        r = sampler.sample_once()
        assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 0)
        assert (r.day_up_bytes, r.day_down_bytes) == (0, 0)
        assert r.counter_reset is False


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


def test_genuine_wrap_on_one_nic_keeps_other_nic_counting():
    """T5: 单卡真回绕 (1000 -> 20) 只影响该卡: delta 归零 + 只点名该卡的告警;
    其他卡 (wlan0 0 -> 30) 照常入账, 合计不含回绕前的历史值."""
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(1000, 1000), "wlan0": nic(0, 0)}
    r1 = sampler.sample_once()
    assert r1.baseline is True

    counters.page = {"eth0": nic(20, 20), "wlan0": nic(30, 30)}  # eth0 双侧回绕; wlan0 正常
    r2 = sampler.sample_once()
    assert r2.counter_reset is True
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (30, 30)
    assert (r2.day_up_bytes, r2.day_down_bytes) == (30, 30)
    assert len(r2.warnings) == 2
    assert all("eth0" in w and "wlan0" not in w for w in r2.warnings), r2.warnings
    # 回绕后的新读数成为下轮基线, 下一轮只记真实增量
    counters.page = {"eth0": nic(40, 40), "wlan0": nic(30, 30)}
    r3 = sampler.sample_once()
    assert (r3.delta_up_bytes, r3.delta_down_bytes) == (20, 20)
    assert (r3.day_up_bytes, r3.day_down_bytes) == (50, 50)


def test_counter_reset_never_negative_across_many_samples():
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(100, 100)}
    sampler.sample_once()
    for sent in (90, 80, 70):
        counters.page = {"eth0": nic(sent, 100)}
        r = sampler.sample_once()
        assert r.day_up_bytes == 0 and r.day_down_bytes == 0
        assert r.delta_up_bytes == 0 and r.delta_down_bytes == 0


def test_all_adapters_filtered_keeps_baselines_and_new_adapter_only_establishes():
    sampler, _, counters = make_sampler()
    counters.page = {"lo": nic(500, 500)}  # 只有回环 -> 全被默认过滤
    r1 = sampler.sample_once()
    assert r1.baseline is True
    assert any("无适配器通过过滤" in w for w in r1.warnings)
    counters.page = {"eth0": nic(100, 100)}
    r2 = sampler.sample_once()
    # eth0 从未被观测过 (只在全空后出现): 按新卡只立基线, 历史累计(100)不入账;
    # 全过滤轮没有建立任何记忆 -> 本轮开始时逐卡记忆仍为空, baseline 仍为 True
    assert r2.baseline is True
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (0, 0)
    assert (r2.day_up_bytes, r2.day_down_bytes) == (0, 0)


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


def test_day_rollover_keeps_nic_baseline():
    """T10: 23:59 采样后 00:00 采样 -> day 累计清零, 逐卡记忆保留, 该轮 delta 正常."""
    sampler, clock, counters = make_sampler(clock=FakeClock(datetime(2026, 10, 16, 23, 59, 0)))
    counters.page = {"eth0": nic(100, 200)}
    sampler.sample_once()
    counters.page = {"eth0": nic(300, 500)}  # +200/+300
    r1 = sampler.sample_once()
    assert (r1.day_up_bytes, r1.day_down_bytes) == (200, 300)
    assert sampler.snapshot()["nic_baseline"] == {"eth0": {"up": 300, "down": 500}}

    clock.now = datetime(2026, 10, 17, 0, 0, 1)
    counters.page = {"eth0": nic(400, 560)}  # +100/+60
    r2 = sampler.sample_once()
    assert r2.day_rolled is True
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (100, 60)
    assert (r2.day_up_bytes, r2.day_down_bytes) == (100, 60)  # 旧日累计已清零
    assert sampler.snapshot()["nic_baseline"] == {"eth0": {"up": 400, "down": 560}}


def test_clock_rollback_across_day_boundary_keeps_accumulation():
    """挂钟回跳跨日界 (day < self._day): 不硬切 —— 累计保持, 采样日钉在原日界,
    day_rolled=False。清零会让 dat 今日行被低值 upsert 覆盖且当日不可自愈 (T-03);
    钉日界同时保证 dat upsert 目标不落到历史行。
    """
    sampler, clock, counters = make_sampler()
    counters.page = {"eth0": nic(100, 200)}
    sampler.sample_once()
    counters.page = {"eth0": nic(300, 500)}  # +200/+300
    sampler.sample_once()
    clock.now = datetime(2026, 10, 17, 0, 0, 1)
    counters.page = {"eth0": nic(400, 560)}  # 前进到 10-17: 正常硬切, 新日累计 100/60
    r2 = sampler.sample_once()
    assert r2.day_rolled is True

    clock.now = datetime(2026, 10, 16, 23, 59, 0)  # 挂钟回跳回 10-16 (NTP 校正/手动改钟)
    counters.page = {"eth0": nic(500, 620)}  # +100/+60
    r3 = sampler.sample_once()
    assert r3.day_rolled is False
    assert r3.day == date(2026, 10, 17)  # 采样日钉在原日界 (累计与 upsert 目标一致)
    assert (r3.day_up_bytes, r3.day_down_bytes) == (200, 120)  # 10-17 累计未清零, 继续累加
    assert any("挂钟回跳" in w for w in r3.warnings)
    # 快照日界与累计一致: 重启后 restore 见"快照日期晚于今天" -> 判损坏降级, 与恢复路径同防线
    assert sampler.snapshot()["day"] == "2026-10-17"


def test_clock_rollback_then_forward_resumes_rollover():
    """回跳期间持续按原日累计; 日界再次前进时恢复正常硬切 (当日可自愈)."""
    sampler, clock, counters = make_sampler()
    counters.page = {"eth0": nic(100, 200)}
    sampler.sample_once()
    clock.now = datetime(2026, 10, 17, 0, 0, 1)
    counters.page = {"eth0": nic(300, 500)}
    assert sampler.sample_once().day_rolled is True
    clock.now = datetime(2026, 10, 16, 23, 0, 0)  # 回跳
    counters.page = {"eth0": nic(400, 560)}
    r3 = sampler.sample_once()
    assert r3.day_rolled is False and r3.day == date(2026, 10, 17)
    clock.now = datetime(2026, 10, 18, 0, 0, 1)  # 日界再次前进
    counters.page = {"eth0": nic(500, 620)}
    r4 = sampler.sample_once()
    assert r4.day_rolled is True
    assert r4.day == date(2026, 10, 18)
    assert (r4.day_up_bytes, r4.day_down_bytes) == (100, 60)  # 新日从 0 起计


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


def test_down_adapter_recovering_does_not_backfill_lifetime_counter():
    stats = stats_page(down="wlan0")
    sampler, _, counters = make_sampler(stats=stats)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(999, 999)}
    sampler.sample_once()
    # wlan0 恢复 up: 它在 down 前从未被选中 (无逐卡记忆) -> 恢复首轮只立基线
    stats["wlan0"] = SimpleNamespace(isup=True)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(1999, 1999)}
    r = sampler.sample_once()
    # 1999 里含 999 的历史累计: 无法判定增量, 按 I6 只立基线, 不入账
    assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 0)
    assert (r.day_up_bytes, r.day_down_bytes) == (0, 0)


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


# ---- 断连-恢复 (逐网卡基线) ----


def test_disconnect_recover_without_growth_counts_zero():
    """T1 主回归: 断连被过滤期间计数不涨, 恢复后不得把整份生命周期累计入账."""
    stats = stats_page()
    sampler, _, counters = make_sampler(stats=stats)
    counters.page = {"eth0": nic(999, 999)}
    sampler.sample_once()  # 首轮只立基线
    stats["eth0"] = SimpleNamespace(isup=False)  # down -> 被默认 exclude_down 过滤
    counters.page = {"eth0": nic(999, 999)}
    r_down = sampler.sample_once()
    assert (r_down.delta_up_bytes, r_down.delta_down_bytes) == (0, 0)
    stats["eth0"] = SimpleNamespace(isup=True)  # 恢复, 计数未涨
    counters.page = {"eth0": nic(999, 999)}
    r_up = sampler.sample_once()
    assert (r_up.delta_up_bytes, r_up.delta_down_bytes) == (0, 0)
    assert (r_up.day_up_bytes, r_up.day_down_bytes) == (0, 0)


def test_disconnect_recover_with_real_growth_counts_only_increment():
    """T2: 断连-恢复且计数有真实增长 -> 只记增量(100), 不是整份累计(1099)."""
    stats = stats_page()
    sampler, _, counters = make_sampler(stats=stats)
    counters.page = {"eth0": nic(999, 999)}
    sampler.sample_once()
    stats["eth0"] = SimpleNamespace(isup=False)
    counters.page = {"eth0": nic(999, 999)}
    r_down = sampler.sample_once()
    assert (r_down.delta_up_bytes, r_down.delta_down_bytes) == (0, 0)
    stats["eth0"] = SimpleNamespace(isup=True)
    counters.page = {"eth0": nic(1099, 1099)}
    r_up = sampler.sample_once()
    assert (r_up.delta_up_bytes, r_up.delta_down_bytes) == (100, 100)
    assert (r_up.day_up_bytes, r_up.day_down_bytes) == (100, 100)


def test_multi_nic_one_down_other_counts_normally():
    """T3: 多卡中一张 down (被过滤) 期间另一张正常增长 -> 只记正常卡的增量, 无重置告警;
    down 卡恢复后读数未涨, 仍记 (0,0) (记忆未被 down 轮改写)."""
    stats = stats_page()
    sampler, _, counters = make_sampler(stats=stats)
    counters.page = {"eth0": nic(0, 0), "wlan0": nic(999, 999)}
    r1 = sampler.sample_once()
    assert r1.baseline is True

    stats["wlan0"] = SimpleNamespace(isup=False)  # wlan0 down -> 被默认 exclude_down 过滤
    counters.page = {"eth0": nic(100, 100), "wlan0": nic(999, 999)}
    r_down = sampler.sample_once()
    assert (r_down.delta_up_bytes, r_down.delta_down_bytes) == (100, 100)
    assert r_down.counter_reset is False and r_down.warnings == ()

    stats["wlan0"] = SimpleNamespace(isup=True)  # 恢复, 读数未涨
    counters.page = {"eth0": nic(100, 100), "wlan0": nic(999, 999)}
    r_up = sampler.sample_once()
    assert (r_up.delta_up_bytes, r_up.delta_down_bytes) == (0, 0)
    assert r_up.counter_reset is False and r_up.warnings == ()
    assert (r_up.day_up_bytes, r_up.day_down_bytes) == (100, 100)  # 只含 eth0 的真实增量


def test_new_nic_with_large_lifetime_counters_only_establishes_baseline():
    """T6: 已有 eth0 记忆时新插入 vet (带 700 历史累计) -> 本轮 (0,0), vet 基线写 700."""
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(100, 100)}
    sampler.sample_once()
    counters.page = {"eth0": nic(100, 100), "vet": nic(700, 700)}  # vet 首次出现
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 0)
    assert (r.day_up_bytes, r.day_down_bytes) == (0, 0)
    assert sampler.snapshot()["nic_baseline"] == {
        "eth0": {
            "up": 100,
            "down": 100
        },
        "vet": {
            "up": 700,
            "down": 700
        },
    }
    # 基线已写入: 之后再涨只记增量
    counters.page = {"eth0": nic(100, 100), "vet": nic(750, 760)}
    r2 = sampler.sample_once()
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (50, 60)


def test_nic_memory_expires_after_seven_days_and_reappears_as_new():
    """T13: 某卡超过 7 天未被选中 -> 条目被清理; 再出现按新卡只立基线 (0,0)."""
    sampler, clock, counters = make_sampler()
    counters.page = {"eth0": nic(100, 200)}
    sampler.sample_once()
    assert sampler.snapshot()["nic_baseline"] == {"eth0": {"up": 100, "down": 200}}

    clock.now = T0 + timedelta(days=8)  # eth0 已 8 天未被选中
    counters.page = {"wlan0": nic(500, 600)}  # 只有 wlan0 -> eth0 不进 next_base
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 0)
    assert sampler.snapshot()["nic_baseline"] == {"wlan0": {"up": 500, "down": 600}}  # eth0 已清

    counters.page = {"eth0": nic(9000, 9000), "wlan0": nic(500, 600)}  # eth0 回来 (带大累计)
    r2 = sampler.sample_once()
    assert (r2.delta_up_bytes, r2.delta_down_bytes) == (0, 0)  # 按新卡只立基线
    assert sampler.snapshot()["nic_baseline"]["eth0"] == {"up": 9000, "down": 9000}


def test_all_filtered_preserves_nic_memory_and_counts_later_growth():
    """T4: 全部被过滤时记忆完全不动; 恢复后仍 (0,0), 再涨 50 才记 50."""
    sampler, _, counters = make_sampler()
    counters.page = {"eth0": nic(100, 100)}
    sampler.sample_once()
    counters.page = {"lo": nic(500, 500)}  # selected 全空
    r_empty = sampler.sample_once()
    assert any("无适配器通过过滤" in w for w in r_empty.warnings)
    assert (r_empty.delta_up_bytes, r_empty.delta_down_bytes) == (0, 0)
    counters.page = {"eth0": nic(100, 100)}
    r_back = sampler.sample_once()
    assert (r_back.delta_up_bytes, r_back.delta_down_bytes) == (0, 0)
    counters.page = {"eth0": nic(150, 150)}
    r_grow = sampler.sample_once()
    assert (r_grow.delta_up_bytes, r_grow.delta_down_bytes) == (50, 50)
    assert (r_grow.day_up_bytes, r_grow.day_down_bytes) == (50, 50)


# ---- state 恢复 ----


def test_restore_same_day_resumes_accumulation_and_baseline():
    """v2 载荷: 今天 -> 累计接续 + 逐卡基线恢复, 首次采样按真实增量入账."""
    sampler, _, counters = make_sampler()
    snap = {
        "version": 2,
        "day": "2026-10-16",
        "day_up_bytes": 4096,
        "day_down_bytes": 8192,
        "last_up_bytes": 5000,
        "last_down_bytes": 9000,
        "nic_baseline": {"eth0": {"up": 5000, "down": 9000}}
    }
    warns = sampler.restore(snap)
    assert warns == ()
    assert sampler.state_restored is True
    assert sampler.has_baseline
    assert sampler.day == DAY and sampler.day_up_bytes == 4096 and sampler.day_down_bytes == 8192
    counters.page = {"eth0": nic(5600, 9300)}  # 相对恢复的逐卡基线 +600/+300
    r = sampler.sample_once()
    assert r.baseline is False
    assert (r.delta_up_bytes, r.delta_down_bytes) == (600, 300)
    assert (r.day_up_bytes, r.day_down_bytes) == (4096 + 600, 8192 + 300)


def test_restore_v1_payload_upgrade_keeps_day_and_zeroes_first_delta():
    """T8: v1 载荷升级 -> 保留当日累计, 忽略 v1 合计基线 (逐卡记忆置空), 首轮 (0,0) + 升级告警."""
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
    assert any("state v1 升级" in w for w in warns), f"warns={warns!r}"
    assert getattr(sampler, "state_restored", None) is True
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (4096, 8192)
    assert not sampler.has_baseline  # 逐卡记忆置空, 首轮按新卡立基线
    counters.page = {"eth0": nic(5600, 9300)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (0, 0)
    assert (r.day_up_bytes, r.day_down_bytes) == (4096, 8192)


def test_restore_yesterday_clears_accumulation_keeps_baseline():
    """v2 载荷: 昨天 -> 当日累计清零, 逐卡记忆保留 (跨天停机窗增量归今天)."""
    sampler, _, counters = make_sampler()
    snap = {
        "version": 2,
        "day": "2026-10-15",
        "day_up_bytes": 4096,
        "day_down_bytes": 8192,
        "last_up_bytes": 5000,
        "last_down_bytes": 9000,
        "nic_baseline": {"eth0": {"up": 5000, "down": 9000}}
    }
    warns = sampler.restore(snap)
    assert len(warns) == 1 and "早于今天" in warns[0]
    assert sampler.state_restored is True and sampler.has_baseline
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (0, 0)
    counters.page = {"eth0": nic(5100, 9100)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (100, 100)
    assert (r.day_up_bytes, r.day_down_bytes) == (100, 100)  # 跨天停机窗流量归今天


def test_restore_v2_single_illegal_nic_entry_is_dropped():
    """T9: v2 单条非法 ({"up": "x"}) -> 该条丢弃 + 告警, 其他条生效, day 保留."""
    sampler, _, counters = make_sampler()
    snap = {
        "version": 2,
        "day": "2026-10-16",
        "day_up_bytes": 100,
        "day_down_bytes": 200,
        "last_up_bytes": 10,
        "last_down_bytes": 20,
        "nic_baseline": {
            "eth0": {
                "up": "x",
                "down": 0
            },
            "wlan0": {
                "up": 10,
                "down": 20
            }
        },
    }
    warns = sampler.restore(snap)
    assert len(warns) == 1 and "nic_baseline 条目非法" in warns[0] and "'eth0'" in warns[0]
    assert sampler.state_restored is True
    assert sampler.has_baseline
    assert sampler.snapshot()["nic_baseline"] == {"wlan0": {"up": 10, "down": 20}}  # 只有 wlan0 生效
    assert (sampler.day_up_bytes, sampler.day_down_bytes) == (100, 200)  # day 保留

    counters.page = {"eth0": nic(500, 500), "wlan0": nic(110, 120)}
    r = sampler.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (100, 100)  # 仅 wlan0 的增量
    assert (r.day_up_bytes, r.day_down_bytes) == (200, 300)


def test_restore_v2_nic_baseline_local_corruption_variants():
    """nic_baseline 局部损坏逐形态: 缺失/非映射/键非字符串/条目非映射/缺字段 ->
    丢弃并告警, 但 day 与恢复本身仍生效 (局部损坏不拖垮整体恢复)."""
    base = {
        "version": 2,
        "day": "2026-10-16",
        "day_up_bytes": 10,
        "day_down_bytes": 20,
    }
    cases = [
        (None, "缺失", "无告警"),
        ([], "非映射", "nic_baseline 不是映射"),
        ({5: {"up": 1, "down": 2}}, "键非字符串", "网卡名非字符串"),
        ({"eth0": 7}, "条目非映射", "不是映射"),
        ({"eth0": {"up": 1}}, "缺字段", "up/down 缺失"),
    ]
    for raw, label, expect in cases:
        sampler, _, _ = make_sampler()
        warns = sampler.restore(dict(base, nic_baseline=raw))
        if expect == "无告警":
            assert warns == (), label
        else:
            assert any(expect in w for w in warns), f"{label}: {warns!r}"
            assert not sampler.has_baseline, label
        assert sampler.state_restored is True, label
        assert (sampler.day_up_bytes, sampler.day_down_bytes) == (10, 20), label


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
    base_v1 = {
        "version": 1,
        "day": "2026-10-16",
        "day_up_bytes": 1,
        "day_down_bytes": 1,
        "last_up_bytes": 1,
        "last_down_bytes": 1
    }
    base_v2 = {
        "version": 2,
        "day": "2026-10-16",
        "day_up_bytes": 1,
        "day_down_bytes": 1,
        "last_up_bytes": 1,
        "last_down_bytes": 1,
        "nic_baseline": {"eth0": {"up": 1, "down": 1}}
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
        dict(base_v1, version=3),  # 不支持的版本
        dict(base_v1, day="not-a-date"),
        dict(base_v1, day_up_bytes="abc"),
        dict(base_v1, last_down_bytes=-5),  # v1 合计基线仍按字段合法性校验
        dict(base_v1, day="2026/10/16"),  # 非 ISO
        dict(base_v2, day="not-a-date"),
        dict(base_v2, day=None),  # day 为 None 但逐卡基线有值
    ]
    for bad in bad_cases:
        sampler, _, _ = make_sampler()
        warns = sampler.restore(bad)
        assert len(warns) == 1, bad
        assert not sampler.has_baseline, bad
        assert not sampler.state_restored, bad
        assert sampler.day is None, bad


def test_restore_valid_state_without_baseline_allows_baseline_sample():
    # v1 载荷 (首次采样前宕机): 不算损坏 -> 保留当日累计, 逐卡记忆置空, 首样本走 baseline
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
    assert len(warns) == 1 and "state v1 升级" in warns[0]
    assert sampler.state_restored is True and not sampler.has_baseline
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
        "version": 2,
        "day": "2026-10-16",
        "day_up_bytes": 500,
        "day_down_bytes": 400,
        "last_up_bytes": 1500,  # 兼容/观测口径: 各卡基线求和
        "last_down_bytes": 2400,
        "nic_baseline": {"eth0": {"up": 1500, "down": 2400}}
    }

    revived, _, counters2 = make_sampler()
    assert revived.restore(snap) == ()
    assert revived.state_restored is True and revived.has_baseline
    counters2.page = {"eth0": nic(1600, 2500)}
    r = revived.sample_once()
    assert (r.delta_up_bytes, r.delta_down_bytes) == (100, 100)
    assert (r.day_up_bytes, r.day_down_bytes) == (600, 500)
    assert r.baseline is False


def test_snapshot_before_any_sample():
    sampler, _, _ = make_sampler()
    assert sampler.snapshot() == {
        "version": 2,
        "day": None,
        "day_up_bytes": 0,
        "day_down_bytes": 0,
        "last_up_bytes": None,
        "last_down_bytes": None,
        "nic_baseline": {}
    }
    revived, _, _ = make_sampler()
    assert revived.restore(sampler.snapshot()) == ()
    assert revived.state_restored is True
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
    """psutil 回退读数单点: read_counters/read_stats 直接转发 psutil 的同名调用
    (生产默认经 nic.default_providers 平台决议, 本对是回退与非 Windows 路径)."""
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
