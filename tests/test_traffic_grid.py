"""test_traffic_grid 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1)

## 测试计划(每个测试函数一条)
- test_build_grid_24h_and_30d: 24h 窗 30s 栅格 = 2880 桶(floor 对齐); 30d 窗恒 3600s = 720 桶; 未知窗口 ValueError
- test_build_grid_unaligned_t0_extra_bucket: t0 未对齐栅格时窗首桶提前(floor), 桶数 ceil = 2881(「≈2880」口径)
- test_build_grid_fractional_interval_ceils_bucket_width: 小数采样间隔桶宽向上取整(1.5s -> 2s 桶宽; floor 会隔桶空 = 伪断线)
- test_raw_rows_jitter_bucket_mean_and_empty_null: 抖动采样行按 floor 归桶, 桶内多行取均值(round 取整); 空桶 = null; null 点行不参与; 窗外行不消费
- test_hour_rows_align_by_hour_epoch: 30d 窗 hour 行按 hour_epoch 对位(桶内不再聚合); 窗外/超过 t1 的行不消费
- test_series_totals_diff_max0_reset_baseline: 相邻桶快照差分; cur < last 判重置该桶增量 null(dl/up 逐向独立); 窗首基线缺失 null; 空桶断链后下一有观测桶同样 null
- test_rate_points_and_earliest_row_ts: points 形状 {"t","dl","up"} | null; earliest_row_ts 取 raw+hour 全部行(含 null 行)最早时刻, 零行 = None
- test_group_null_mask_rules: 全局桶无观测 -> null(停机/断连); 桶末 <= 成员最早行 -> null(组尚无观测); 其余桶非 null(全员空闲出 0 线)
- test_group_rate_sums_members_missing_zero: 组速率 = 桶内 Σ 成员均值, 无行成员按 0 计; null 桶整桶 None
- test_group_totals_per_member_diff_then_sum: 逐成员先差分再求和 —— 单成员重置贡献 0 不拖垮全组; 成员基线缺失(窗首/无行)贡献 0; null 桶断链
- test_group_50_members_correct_and_time_bound: 50 成员 x 满窗 2880 桶聚合正确性(抽样桶 Σ 校验) + 耗时上界(<< 采样间隔 30s, 实测断言 < 3s)

线程/时钟纪律: 纯函数层无时钟无文件 —— now 由用例给定固定 epoch, 输入直接构造 ParsedSeries。
"""
import time

import pytest

from auto_qb.core.traffic_grid import (
    BucketObs,
    build_grid,
    earliest_row_ts,
    group_null_mask,
    group_rate_points,
    group_totals_points,
    rate_points,
    series_bucket_obs,
    series_totals_points,
)
from auto_qb.core.traffic_store import HourRow, ParsedSeries, RawRow

#: 固定"现在"(2027-01-15, 纯测试时刻; 恰为 30 与 3600 的公倍数, 对齐断言干净)
NOW = 1_800_000_000


def _series(raw=(), hours=()) -> ParsedSeries:
    return ParsedSeries(key="test", raw=tuple(raw), hours=tuple(hours), bad_lines=0, data_lines=len(raw) + len(hours))


def _row(ts, dl, up, dt=None, ut=None) -> RawRow:
    return RawRow(ts=ts, dl_rate=dl, up_rate=up, dl_total=dt, up_total=ut)


# ---------------- 栅格构建(§05.1) ----------------


def test_build_grid_24h_and_30d():
    """24h 窗 30s 栅格 = 2880 桶(floor 对齐); 30d 窗恒 3600s = 720 桶; 未知窗口 ValueError"""
    g = build_grid("24h", NOW, 30.0)
    assert g.interval == 30 and g.segment == "raw" and g.t1 == NOW and g.t0 == NOW - 86400
    assert len(g.buckets) == 2880
    assert g.first == ((NOW - 86400) // 30) * 30
    assert g.buckets[1] - g.buckets[0] == 30 and g.last == g.first + 2879 * 30
    h = build_grid("30d", NOW, 999.0)  # sample_interval 只在 raw 段生效
    assert h.interval == 3600 and h.segment == "hour" and len(h.buckets) == 720
    assert h.first == ((NOW - 2592000) // 3600) * 3600
    with pytest.raises(ValueError):
        build_grid("7d", NOW)


def test_build_grid_unaligned_t0_extra_bucket():
    """t0 未对齐栅格时窗首桶提前到 floor(t0/interval), 桶数 ceil = 2881(§05.1「≈2880 桶」口径)"""
    now = NOW + 13  # t0 = now-86400 落在桶中间
    g = build_grid("24h", now, 30.0)
    assert len(g.buckets) == 2881
    assert g.first == ((now - 86400) // 30) * 30
    assert g.last < now <= g.last + 30  # 全部桶覆盖 [t0, t1)


def test_build_grid_fractional_interval_ceils_bucket_width():
    """小数采样间隔桶宽向上取整: 1.5s -> 2s 桶宽(floor 取 1s 会让 1.5s 一条的采样行隔桶为空 = 伪断线)"""
    g = build_grid("24h", NOW, 1.5)
    assert g.interval == 2
    assert len(g.buckets) == 43200  # NOW 与 t0 均为偶数, 恰好对齐
    assert g.last < NOW <= g.last + 2  # 覆盖 [t0, t1) 不变


# ---------------- 单系列离散(§05.1) ----------------


def test_raw_rows_jitter_bucket_mean_and_empty_null():
    """抖动行 floor 归桶 + 桶内多行取均值; 空桶 = null; null 点行不参与; 窗外行不消费"""
    g = build_grid("24h", NOW, 30.0)
    base = g.first + 3600  # 窗内 1 小时处的一个对齐桶起点
    rows = [
        _row(base + 5, 100, 50, 1000, 500),  # 桶 base(抖动 +5s)
        _row(base + 25, 200, 70, 2000, 800),  # 同桶第二行(快照取最新行)
        _row(base + 35, 300, 90, 3000, 1200),  # 桶 base+30
        RawRow(ts=base + 15, dl_rate=None, up_rate=None, dl_total=None, up_total=None),  # null 点行不参与
        _row(g.first - 5, 1, 1, 1, 1),  # 窗前一行(桶 < first)不消费
        _row(g.t1 + 5, 1, 1, 1, 1),  # t1 之后不消费
    ]
    obs = series_bucket_obs(_series(rows), g)
    assert obs[base] == BucketObs(dl_rate=150, up_rate=60, dl_total=2000, up_total=800)
    assert obs[base + 30] == BucketObs(dl_rate=300, up_rate=90, dl_total=3000, up_total=1200)
    assert base + 60 not in obs  # 空桶
    pts = rate_points(obs, g)
    i = g.buckets.index(base)
    assert pts[i] == {"t": base, "dl": 150, "up": 60}
    assert pts[i + 2] is None  # 空桶 = null(断线)


def test_hour_rows_align_by_hour_epoch():
    """30d 窗 hour 行按 hour_epoch 对位(桶内不再聚合); 窗外/未进窗的行不消费"""
    g = build_grid("30d", NOW)
    h0 = g.first + 3600 * 10
    hours = [
        HourRow(hour_epoch=h0, dl_avg=111, dl_max=222, up_avg=33, up_max=44, dl_total=1000, up_total=500),
        HourRow(hour_epoch=h0 + 3600, dl_avg=7, dl_max=7, up_avg=8, up_max=8, dl_total=1500, up_total=900),
        HourRow(hour_epoch=g.first - 3600, dl_avg=1, dl_max=1, up_avg=1, up_max=1, dl_total=1, up_total=1),  # 窗前
    ]
    obs = series_bucket_obs(_series(hours=hours), g)
    assert obs[h0] == BucketObs(111, 33, 1000, 500)
    assert obs[h0 + 3600] == BucketObs(7, 8, 1500, 900)
    assert h0 - 3600 not in obs
    pts = rate_points(obs, g)
    assert pts[g.buckets.index(h0)] == {"t": h0, "dl": 111, "up": 33}


def test_series_totals_diff_max0_reset_baseline():
    """相邻桶快照差分: 重置桶 null(逐向独立); 窗首基线缺失 null; 空桶断链后继"""
    g = build_grid("24h", NOW, 30.0)
    base = g.first + 3600  # 窗内 1 小时处的一个对齐桶起点
    rows = [
        _row(base + 5, 10, 10, 1000, 500),  # 桶 base: 窗首(前桶无快照) -> totals null/null
        _row(base + 35, 10, 10, 1800, 400),  # 桶 base+30: dl +800; up 400 < 500 重置 -> null
        _row(base + 65, 10, 10, 2000, 600),  # 桶 base+60: dl +200; up +200
        _row(base + 155, 10, 10, 2100, 700),  # 桶 base+150: 与前桶(base+60)之间隔两个空桶 -> 断链 null
    ]
    totals = series_totals_points(series_bucket_obs(_series(rows), g), g)
    assert totals[g.buckets.index(base)] == {"t": base, "dl": None, "up": None}
    assert totals[g.buckets.index(base) + 1] == {"t": base + 30, "dl": 800, "up": None}  # 逐向独立: up 重置 null
    assert totals[g.buckets.index(base) + 2] == {"t": base + 60, "dl": 200, "up": 200}
    assert totals[g.buckets.index(base) + 5] == {"t": base + 150, "dl": None, "up": None}  # 空桶断链 -> 基线缺失
    assert totals[g.buckets.index(base) + 3] is None  # 空桶本身 null


def test_rate_points_and_earliest_row_ts():
    """points 形状 {"t","dl","up"} | null; earliest_row_ts 收 raw+hour 全部行(含 null 行), 零行 = None"""
    g = build_grid("24h", NOW, 30.0)
    base = g.first + 60
    obs = {base: BucketObs(1, 2, 3, 4)}
    assert rate_points(obs, g)[g.buckets.index(base)] == {"t": base, "dl": 1, "up": 2}
    assert rate_points(obs, g)[g.buckets.index(base) + 1] is None
    assert earliest_row_ts(_series()) is None
    assert earliest_row_ts(_series(raw=[_row(NOW - 100, 1, 1, 1, 1)])) == NOW - 100
    null_row = RawRow(ts=NOW - 200, dl_rate=None, up_rate=None, dl_total=None, up_total=None)
    assert earliest_row_ts(_series(raw=[null_row, _row(NOW - 100, 1, 1, 1, 1)])) == NOW - 200  # null 行也算观测
    assert earliest_row_ts(_series(hours=[HourRow(NOW - 5000, 1, 1, 1, 1, 1, 1)])) == NOW - 5000


# ---------------- 组读侧聚合(§04.1) ----------------


def test_group_null_mask_rules():
    """借全局系列当真值源: 全局无观测桶 null; 桶末 <= 成员最早行 null; 其余桶非 null"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2 = g.buckets[10], g.buckets[11], g.buckets[12]
    g_obs = {b0: BucketObs(1, 1, 1, 1), b2: BucketObs(1, 1, 1, 1)}  # b1 全局无行 = 停机
    mask = group_null_mask(g_obs, g, earliest_member_ts=None)
    assert mask[10] is False and mask[11] is True and mask[12] is False
    # 成员最早行在 b2 桶中间: b2 桶未"早于"最早行(非 null), b1 及以前全 null
    mask2 = group_null_mask(g_obs, g, earliest_member_ts=b2 + 10)
    assert mask2[10] is True and mask2[11] is True and mask2[12] is False
    assert all(mask2[:10])


def test_group_rate_sums_members_missing_zero():
    """组速率 = 桶内 Σ 成员均值, 无行成员按 0 计(全员空闲出 0 线); null 桶整桶 None"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1 = g.buckets[10], g.buckets[11]
    m1 = {b0: BucketObs(100, 10, 0, 0)}
    m2 = {b0: BucketObs(50, 5, 0, 0), b1: BucketObs(70, 7, 0, 0)}  # m1 在 b1 空闲 -> 按 0 计
    mask = [False] * len(g.buckets)
    mask[11] = False
    mask[12] = True  # 停机桶
    pts = group_rate_points([m1, m2], g, mask)
    assert pts[10] == {"t": b0, "dl": 150, "up": 15}
    assert pts[11] == {"t": b1, "dl": 70, "up": 7}  # 全员空闲的桶出 0 线由 mask=False 保证
    assert pts[12] is None
    empty_bucket = group_rate_points([{}, {}], g, [False] * len(g.buckets))[10]
    assert empty_bucket == {"t": g.buckets[10], "dl": 0, "up": 0}  # 全员无行 -> 0(非 null)


def test_group_totals_per_member_diff_then_sum():
    """逐成员先差分再求和: 单成员重置贡献 0 不拖垮全组; 基线缺失贡献 0; null 桶断链"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2, b3 = g.buckets[10], g.buckets[11], g.buckets[12], g.buckets[13]
    # m1: b0 基线缺失(贡献 0) -> b1 +1000 -> b2 重置(cur<last, 贡献 0) -> b3 +100
    m1 = {
        b0: BucketObs(0, 0, 1000, 0),
        b1: BucketObs(0, 0, 2000, 0),
        b2: BucketObs(0, 0, 100, 0),
        b3: BucketObs(0, 0, 200, 0)
    }
    # m2: b1 才有行(基线缺失贡献 0) -> b2 +500 -> b3 +500
    m2 = {b1: BucketObs(0, 0, 500, 0), b2: BucketObs(0, 0, 1000, 0), b3: BucketObs(0, 0, 1500, 0)}
    mask = [False] * len(g.buckets)
    mask[14] = True  # b4 停机桶(null 桶断链)
    totals = group_totals_points([m1, m2], g, mask)
    assert totals[10] == {"t": b0, "dl": 0, "up": 0}  # 双成员基线缺失 -> 0(不出洞)
    assert totals[11] == {"t": b1, "dl": 1000, "up": 0}  # m1 +1000, m2 基线缺失 0
    assert totals[12] == {"t": b2, "dl": 500, "up": 0}  # m1 重置贡献 0(不是 -1900), m2 +500
    assert totals[13] == {"t": b3, "dl": 600, "up": 0}  # m1 +100, m2 +500
    assert totals[14] is None
    # null 桶断链: b4 之后 m1/m2 的快照链断, 下一桶基线缺失贡献 0
    m1[b3 + 2 * 30] = BucketObs(0, 0, 9999, 0)
    totals2 = group_totals_points([m1, m2], g, mask)
    assert totals2[g.buckets.index(b3) + 2] == {"t": b3 + 60, "dl": 0, "up": 0}


# ---------------- 50 成员聚合(P4 验收: 正确性 + 耗时上界, §04.3) ----------------


def test_group_50_members_correct_and_time_bound():
    """50 成员 x 满窗 2880 桶: 抽样桶 Σ 成员均值/逐成员差分校验 + 耗时上界

    上界依据: 组图弹层按采样间隔(30s)低频续拉(§07), 单次聚合须远小于一个间隔;
    实测量级为数十 ms(纯聚合, 不含文件读), 断言 3s 为含 CI 慢机的宽裕上界。
    """
    g = build_grid("24h", NOW, 30.0)
    n = 50
    members = []
    for m in range(n):
        rows = [
            _row(g.first + i * 30 + 5, 100 + m, 200 + m, i * 10 + m, 0)  # 每桶恰一行(抖动 +5s)
            for i in range(2880) if g.first + i * 30 + 5 < g.t1
        ]
        members.append(_series(rows))
    global_rows = [_row(g.first + i * 30 + 1, 1, 1, i, 0) for i in range(2880) if g.first + i * 30 + 1 < g.t1]
    g_obs = series_bucket_obs(_series(global_rows), g)

    t_start = time.perf_counter()
    member_obs = [series_bucket_obs(p, g) for p in members]
    mask = group_null_mask(g_obs, g, min(earliest_row_ts(p) for p in members))
    points = group_rate_points(member_obs, g, mask)
    totals = group_totals_points(member_obs, g, mask)
    elapsed = time.perf_counter() - t_start

    assert len(points) == len(g.buckets)
    assert all(p is not None for p in points)  # 每桶每成员都有行: 无 null
    idx = 100
    b = g.buckets[idx]
    assert points[idx] == {"t": b, "dl": 100 * n + n * (n - 1) // 2, "up": 200 * n + n * (n - 1) // 2}
    assert totals[idx] == {"t": b, "dl": 10 * n, "up": 0}  # 逐成员每桶 +10; 上行恒 0
    assert totals[g.buckets.index(g.first)] == {"t": g.first, "dl": 0, "up": 0}  # 窗首基线缺失 -> 0
    assert elapsed < 3.0, f"50 成员聚合耗时 {elapsed:.3f}s 超上界"
