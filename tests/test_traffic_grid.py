"""test_traffic_grid 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1)

## 测试计划(每个测试函数一条)
- test_build_grid_24h_and_30d: 24h 窗 30s 栅格 = 2880 桶(floor 对齐); 30d 窗恒 3600s = 720 桶; 未知窗口 ValueError
- test_build_grid_extended_windows: 1m/5m/30m/3h/6h/12h raw 段窗(桶宽 = 采样间隔, 桶数 = 跨度/间隔) + 3d/7d hour 段窗(恒 3600s = 72/168 桶)
- test_build_grid_unaligned_t0_extra_bucket: t0 未对齐栅格时窗首桶提前(floor), 桶数 ceil = 2881(「≈2880」口径)
- test_build_grid_fractional_interval_ceils_bucket_width: 小数采样间隔桶宽向上取整(1.5s -> 2s 桶宽; floor 会隔桶空 = 伪断线)
- test_hour_rows_align_by_hour_epoch: 30d 窗 hour 行按 hour_epoch 对位(桶内不再聚合); 窗外/超过 t1 的行不消费
- test_rate_points_and_earliest_row_ts: points 形状 {"t","dl","up"} | null; earliest_row_ts 取 raw+hour 全部行(含 null 行)最早时刻, 零行 = None
- test_group_null_mask_rules: 全局桶无观测 -> null(停机/断连); 桶末 <= 成员最早行 -> null(组尚无观测); 其余桶非 null(全员空闲出 0 线)
- test_group_rate_sums_members_missing_zero: 组速率 = 桶内 Σ 成员均值, 无行成员按 0 计; null 桶整桶 None
- test_group_totals_per_member_diff_then_sum: 逐成员先差分再求和 —— 单成员重置贡献 0 不拖垮全组; 成员基线缺失(窗首/无行)贡献 0; null 桶断链
- test_group_50_members_correct_and_time_bound: 50 成员 x 满窗 2880 桶聚合正确性(抽样桶 Σ 校验) + 耗时上界(<< 采样间隔 30s, 实测断言 < 3s)
- test_earliest_row_ts_includes_zrun_start: earliest_row_ts 把 z 行 start 计入最早观测(只剩 z 行的文件也有最早观测)
- test_group_zrun_idle_zero_line_and_outage_null: 组图回归(组三函数零改动消费 z 派生观测) —— 全员空闲 0 线 / 停机桶借 global 判 null / 成员只剩 z 行 earliest 含 z start

v2 读侧行为用例随 S3a 读侧翻转重写为 v3 口径(D6; v2 series_bucket_obs/z 覆盖展开的旧断言
退役, 构造 v3 块/天文件喂给读侧; v2 组三函数与 build_grid 仍接线, 其用例保留至 S3b/S5 翻):

v3 读侧核心(plan 26-10-04-1957 S3a, §05.1/§05.2 —— 每个测试函数一条):
- test_v3_points_known_sequence_end_to_end: 已知序列逐桶核对 —— 天文件文本 -> 解析 -> 桶点:
  显式 dt 漂移行 / 缺省行 / z 游程均摊定位 / n 游程后首 r 链式自洽(游标 dt 链四形态在桶点
  层复钉); 断连(n 槽)null 点 / 停机(块间真空)null 点 / 每桶 rate/totals/时间逐一断言
- test_v3_d1_cross_bucket_coverage: 跨桶覆盖(D1) —— z 游程单记录展开多桶 rate 同值(0,0)+
  totals 同快照非 null(覆盖语义字面形态); r 记录暂停(显式大 dt)宽桶整段承载 —— 暂停区间
  无 null 点不伪断, totals 增量落在恢复记录一桶
- test_v3_mixed_interval_blocks_per_record_width: 桶宽有效 dt —— 混排 interval 分块(60s/2s/30s)
  各归各桶(逐记录桶宽 = max(1,ceil(有效dt))), 块间 gap 被首记录覆盖桶吸收不出伪真空
- test_v3_totals_diff_reset_baseline_and_zchain: 累计段 —— 相邻桶快照差分 / 重置桶 null(dl/up
  逐向独立) / 窗首基线缺失 / n 槽 null 点断链后继基线缺失 / 真空断链 / z 游程快照进差分链
  (空闲段 delta=0 链不断, 后继活跃桶恢复有基线) —— v2 语义平移
- test_v3_same_second_merge_and_mixed_key_raw_priority: 同桶合并 —— 同秒两 raw 行速率取均值+
  快照取最新行; raw 槽与 z 槽同 key 撞桶 -> 混桶 raw 优先(确定性钉住)
- test_v3_vacuum_and_disconnect_distinct: 真空/断连两语义分离 —— 块间 gap 出一个 null 点
  (t = 前块游标终值)且 gap 段无任何桶点; 块内 n 游程折叠为单个 null 点(首槽位置); 互不误报
- test_v3_window_filter_and_empty: 窗口切片 —— ts >= t1 槽不消费 / 覆盖桶触及 t0 才保留
  (桶首允许略早于 t0) / null 点按窗口过滤 / 窗外无数据 = 空元组(停机天然真空)
- test_v3_series_slots_seam: S3b 接缝 —— v3_series_slots 块按 start_epoch 稳定排序展平为
  记录时间轴(乱序输入还原时间序), 逐槽 ts/dt_s/obs 与单块 v3_block_slots 一致

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V3Block
(天文件文本路径经 format_v3_day_text -> parse_v3_day_text 打通解析接缝)。
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
    v3_series_points,
    v3_series_slots,
    v3_totals_points,
)
from auto_qb.core.traffic_store import (
    HourRow,
    ParsedSeries,
    RawRow,
    V3Block,
    V3NullRun,
    V3Sample,
    V3ZeroRun,
    ZRow,
    format_v3_day_text,
    parse_v3_day_text,
)

#: 固定"现在"(2027-01-15, 纯测试时刻; 恰为 30 与 3600 的公倍数, 对齐断言干净)
NOW = 1_800_000_000


def _series(raw=(), hours=(), zruns=()) -> ParsedSeries:
    return ParsedSeries(
        key="test",
        raw=tuple(raw),
        hours=tuple(hours),
        zruns=tuple(zruns),
        bad_lines=0,
        data_lines=len(raw) + len(hours),
    )


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
        build_grid("90d", NOW)  # 窗口集外(7d 已随 2026-10-04 十档窗口入库, 合法)


def test_build_grid_extended_windows():
    """扩展十档窗口(2026-10-04, 与 qB 速度图对齐 + 3d/7d 外延): raw 段窗桶宽 = 采样间隔,
    hour 段窗(3d/7d)恒 3600s; 采样间隔只在 raw 段生效"""
    for name, span in (("1m", 60), ("5m", 300), ("30m", 1800), ("3h", 10800), ("6h", 21600), ("12h", 43200)):
        g = build_grid(name, NOW, 30.0)
        assert g.interval == 30 and g.segment == "raw" and g.t0 == NOW - span, name
        assert len(g.buckets) == span // 30, name  # NOW 与 t0 均为 30 的公倍数, 恰好对齐
    for name, span in (("3d", 259200), ("7d", 604800)):
        h = build_grid(name, NOW, 999.0)  # sample_interval 只在 raw 段生效
        assert h.interval == 3600 and h.segment == "hour" and len(h.buckets) == span // 3600, name
        assert h.first == ((NOW - span) // 3600) * 3600, name


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
# (v2 raw 归桶/差分/z 覆盖展开用例已随 S3a 读侧翻转重写为 v3 口径, 见文件尾 v3 区)


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


# ---------------- z 行与 earliest(仍接线面; v2 覆盖展开/续链用例已平移 v3 区) ----------------


def test_earliest_row_ts_includes_zrun_start():
    """earliest_row_ts 把 z 行 start 计入最早观测(§04.3, z 行是一次真实观测):
    只剩 z 行的文件(raw 滑出 24h 窗)也有最早观测, 组图不再据此误判全 null"""
    zruns = (ZRow(start=NOW - 8000, end=NOW - 7000, dl_total=1, up_total=1), )
    assert earliest_row_ts(_series(zruns=zruns)) == NOW - 8000
    raws = [_row(NOW - 100, 1, 1, 1, 1)]
    assert earliest_row_ts(_series(raws, zruns=zruns)) == NOW - 8000  # raw 更晚: 取 z start


# ---------------- 组图回归(P3: 组三函数零改动消费 z 派生观测) ----------------


def test_group_zrun_idle_zero_line_and_outage_null():
    """组图回归: 全员空闲(z 覆盖)出 0 线 / 停机桶借 global 判 null(即使成员有 z 派生观测) /
    成员只剩 z 行时 earliest 含 z start 不再误判「组尚无任何观测」—— 组三函数零改动"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2 = g.buckets[100], g.buckets[101], g.buckets[102]
    zruns = (ZRow(start=b0, end=b2 + 29, dl_total=500, up_total=100), )
    member = _series(zruns=zruns)  # 成员只剩 z 行: b0..b2 全部 z 派生观测
    member_obs = series_bucket_obs(member, g)
    g_obs = {b0: BucketObs(0, 0, 500, 100), b2: BucketObs(0, 0, 500, 100)}  # global: b1 无行 = 停机
    mask = group_null_mask(g_obs, g, earliest_row_ts(member))
    assert mask[100] is False and mask[101] is True and mask[102] is False  # 停机桶借 global 判 null
    pts = group_rate_points([member_obs], g, mask)
    assert pts[100] == {"t": b0, "dl": 0, "up": 0}  # 全员空闲 0 线(非 null)
    assert pts[101] is None  # 停机桶整桶 None
    assert pts[102] == {"t": b2, "dl": 0, "up": 0}
    totals = group_totals_points([member_obs], g, mask)
    assert totals[100] == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失贡献 0(不出洞)
    assert totals[102] == {"t": b2, "dl": 0, "up": 0}  # 空闲段 delta=0


# ---------------- v3 读侧核心(plan 26-10-04-1957 S3a, §05.1/§05.2) ----------------
# 桶点模型(D1 实施期定稿): 逐记录覆盖桶 —— 桶宽 = max(1, ceil(有效dt)), 桶 = [ceil(ts)-w,
# ceil(ts)), t = 桶起点; 单记录的桶天然覆盖其有效 dt 全程(标称栅格视角「中间桶同值非 null」
# 的等价承载), z 游程按均摊槽展开多桶是覆盖语义的字面形态。全部用例构造 v3 块/天文件喂读侧。


def _p(entry):
    """V3PointEntry -> 可比元组"""
    return (entry.t, entry.dl_rate, entry.up_rate, entry.dl_total, entry.up_total)


def test_v3_points_known_sequence_end_to_end():
    """已知序列逐桶核对(验收: 三端点数据对照) —— 天文件文本 -> 解析 -> 桶点, 每桶
    rate/totals/时间正确; 游标 dt 链四形态在桶点层复钉: 显式 dt(r1)/缺省(r0,r3)/
    均摊定位(z 槽)/链式自洽(n 游程后首 r 以游程终点为基准); 断连与停机两语义分离"""
    block1 = V3Block(
        1000,
        30,
        (
            V3Sample(10, 20, 1000, 2000),  # r0 @1000.0(缺省 dt)
            V3Sample(11, 21, 1100, 2100, dt_ms=30400),  # r1 @1030.4(显式漂移)
            V3ZeroRun(3, 1100, 2100, dt_ms=90000),  # z 槽 @1060.4/1090.4/1120.4(均摊)
            V3NullRun(2, dt_ms=61000),  # n 槽 @1150.9/1181.4(断连)
            V3Sample(12, 22, 1200, 2200, dt_ms=30000),  # r2 @1211.4(= n 游程终点 1181.4 + 30, 链式自洽)
        ),
    )
    block2 = V3Block(5000, 30, (V3Sample(13, 23, 1300, 2300), ))  # 停机重启后新块 @5000
    blocks = parse_v3_day_text(format_v3_day_text("global", (block1, block2))).blocks
    points = v3_series_points(blocks, 1000, 5001)
    # 桶键 = ceil(ts) - w(w = 桶宽有效dt): 逐桶时间/rate/totals 断言
    assert [_p(p) for p in points] == [
        (970, 10, 20, 1000, 2000),  # r0: w=30(缺省), 桶 [970,1000) 触及 t0 照收
        (1000, 11, 21, 1100, 2100),  # r1: w=31(显式 30.4s), ceil(1030.4)-31
        (1031, 0, 0, 1100, 2100),  # z 槽1 @1060.4: w=30(均摊 90/3)
        (1061, 0, 0, 1100, 2100),  # z 槽2 @1090.4
        (1091, 0, 0, 1100, 2100),  # z 槽3 @1120.4(游程实测终点)
        (1150, None, None, None, None),  # n 游程折叠为单个 null 点(首槽 1150.9 取整)
        (1182, 12, 22, 1200, 2200),  # r2 @1211.4: ceil-30
        (1211, None, None, None, None),  # 块间真空 null 点(t = 前块游标终值 1211.4 取整)
        (4970, 13, 23, 1300, 2300),  # r3 @5000: 桶起点 5000-30
    ]
    totals = v3_totals_points(points)
    assert [(e.t, e.dl, e.up) for e in totals] == [
        (970, None, None),  # 窗首基线缺失
        (1000, 100, 100),  # 1100-1000 / 2100-2000
        (1031, 0, 0),  # z 快照(1100,2100)与前桶同值 -> 空闲段 delta=0 链不断
        (1061, 0, 0),
        (1091, 0, 0),
        (1150, None, None),  # n 槽 null 点断链
        (1182, None, None),  # 断链后基线缺失
        (1211, None, None),  # 真空
        (4970, None, None),  # 真空断链后基线缺失
    ]
    # 块乱序传入: 按 start_epoch 稳定排序还原时间序, 结果一致
    assert v3_series_points((block2, block1), 1000, 5001) == points


def test_v3_d1_cross_bucket_coverage():
    """跨桶覆盖(D1 定稿): z 游程单记录按均摊槽展开多桶 —— 每桶 rate 同值 (0,0) + totals
    同快照 + 非 null(覆盖语义的字面形态); r 记录暂停(显式大 dt)由宽桶整段承载 —— 暂停区间
    无 null 点不伪断(v2 一刀切栅格会出成片空桶伪洞), totals 增量落在恢复记录一桶"""
    b = V3Block(
        1000,
        30,
        (
            V3Sample(1, 1, 100, 200),  # @1000 -> key 970
            V3ZeroRun(4, 100, 200, dt_ms=160000),  # 单记录跨 4 桶: 均摊槽 @1040/1080/1120/1160(spacing 40)
            V3Sample(2, 2, 300, 400, dt_ms=40000),  # @1200(游程终点 1160 + 40) -> key 1160
        ),
    )
    points = v3_series_points((b, ), 900, 2000)
    assert [_p(p) for p in points] == [
        (970, 1, 1, 100, 200),
        (1000, 0, 0, 100, 200),  # z 槽1: w=40, ceil(1040)-40 —— rate 同值/快照同/非 null
        (1040, 0, 0, 100, 200),  # z 槽2
        (1080, 0, 0, 100, 200),  # z 槽3
        (1120, 0, 0, 100, 200),  # z 槽4(游程终点)
        (1160, 2, 2, 300, 400),  # 后继 r 以游程终点为基准(链式自洽)
    ]
    assert not any(p.dl_rate is None for p in points)  # 覆盖段全程无 null(防伪洞)
    totals = v3_totals_points(points)
    assert [(e.t, e.dl, e.up) for e in totals] == [
        (970, None, None),
        (1000, 0, 0),  # 空闲段 delta=0 链不断
        (1040, 0, 0),
        (1080, 0, 0),
        (1120, 0, 0),
        (1160, 200, 200),  # 恢复桶有基线(由游程快照续上)
    ]
    # r 记录暂停: 2s 块内一记录显式 dt=20s -> 宽桶 [2000,2020) 整段承载(= 10 个标称 2s 桶)
    b2 = V3Block(
        2000,
        2,
        (
            V3Sample(5, 5, 10, 20),  # @2000, w=2, key 1998
            V3Sample(6, 6, 20, 40, dt_ms=20000),  # @2020(暂停 20s 如实入行), w=20, key=2000
            V3Sample(7, 7, 30, 60),  # @2022, w=2, key=2020
        ),
    )
    points2 = v3_series_points((b2, ), 1990, 3000)
    assert [_p(p) for p in points2] == [
        (1998, 5, 5, 10, 20),
        (2000, 6, 6, 20, 40),  # 宽桶: 暂停段由该记录的桶承载, 无 null 不伪断
        (2020, 7, 7, 30, 60),
    ]
    totals2 = v3_totals_points(points2)
    assert [(e.t, e.dl, e.up) for e in totals2] == [(1998, None, None), (2000, 10, 20), (2020, 10, 20)]


def test_v3_mixed_interval_blocks_per_record_width():
    """桶宽有效 dt(验收): 混排 interval 分块(60s/2s/30s)各归各桶 —— 逐记录桶宽 =
    max(1, ceil(有效dt)) 替代全局一刀切; 块间 <=1 间隔的天然 gap(含 00:00 硬切)被首记录
    覆盖桶吸收, 不出伪真空"""
    b1 = V3Block(1000, 60, (V3Sample(1, 1, 10, 20), V3Sample(2, 2, 20, 40)))  # @1000/@1060, 桶宽 60
    b2 = V3Block(1062, 2, (V3Sample(3, 3, 30, 60), V3Sample(4, 4, 40, 80)))  # @1062/@1064, 桶宽 2
    b3 = V3Block(1094, 30, (V3Sample(5, 5, 50, 100), ))  # @1094, 桶宽 30
    points = v3_series_points((b3, b1, b2), 900, 2000)  # 乱序传入
    assert [_p(p) for p in points] == [
        (940, 1, 1, 10, 20),  # 60s 块: ceil(1000)-60
        (1000, 2, 2, 20, 40),  # ceil(1060)-60
        (1060, 3, 3, 30, 60),  # 2s 块: ceil(1062)-2(gap 2s <= 首槽桶宽 2, 无真空)
        (1062, 4, 4, 40, 80),  # ceil(1064)-2
        (1064, 5, 5, 50, 100),  # 30s 块: ceil(1094)-30(gap 30s <= 首槽桶宽 30, 无真空)
    ]
    assert not any(p.dl_rate is None for p in points)  # 全程无伪真空


def test_v3_totals_diff_reset_baseline_and_zchain():
    """累计段(v2 语义平移): 相邻桶快照差分 / cur<last 重置桶 null(dl/up 逐向独立) /
    窗首基线缺失 / n 槽 null 点断链后继基线缺失 / 真空断链 / z 游程快照进差分链 ——
    空闲段 delta=0 链不断, 其后首个活跃桶恢复有基线"""
    b1 = V3Block(
        1000,
        30,
        (
            V3Sample(10, 10, 1000, 500),  # @1000 -> key 970
            V3Sample(10, 10, 1800, 400),  # @1030 -> key 1000: dl +800; up 400<500 重置 -> null
            V3Sample(10, 10, 2000, 600),  # @1060 -> key 1030: +200/+200
            V3NullRun(2, dt_ms=61000),  # n 槽 @1090.5/1121.0 -> null 点 1090(断链)
            V3Sample(10, 10, 2100, 700, dt_ms=30000),  # @1151(n 终点 1121+30) -> key 1121: 基线缺失
            V3Sample(10, 10, 2200, 800),  # @1181 -> key 1151: +100/+100
        ),
    )
    b2 = V3Block(
        5000,
        30,
        (
            V3Sample(10, 10, 1000, 500),  # @5000 -> key 4970(真空断链后)
            V3ZeroRun(3, 1000, 500),  # 槽 @5030/5060/5090 -> keys 5000/5030/5060(快照恒定)
            V3Sample(10, 10, 1200, 560, dt_ms=30000),  # @5120 -> key 5090: dl +200 / up +60
        ),
    )
    totals = v3_totals_points(v3_series_points((b1, b2), 900, 6000))
    assert [(e.t, e.dl, e.up) for e in totals] == [
        (970, None, None),  # 窗首基线缺失
        (1000, 800, None),  # 逐向独立: dl +800 / up 重置 null
        (1030, 200, 200),
        (1090, None, None),  # n 槽 null 点
        (1121, None, None),  # 断链后基线缺失
        (1151, 100, 100),
        (1181, None, None),  # 块间真空
        (4970, None, None),  # 真空断链后基线缺失
        (5000, 0, 0),  # 基线由 4970 桶快照续上
        (5030, 0, 0),  # z 快照(1000,500)恒定 -> 空闲段 delta=0 链不断
        (5060, 0, 0),
        (5090, 200, 60),  # 后继活跃桶恢复有基线(由 z 快照续上)
    ]


def test_v3_same_second_merge_and_mixed_key_raw_priority():
    """同桶合并: 同秒两 raw 行(dt < 1s)速率取均值、快照取最新行(两行同桶口径);
    raw 槽与 z 槽同 key 撞桶 -> 混桶 raw 优先(v2 口径沿用, 确定性钉住)"""
    b = V3Block(
        1000,
        1,
        (
            V3Sample(1, 1, 10, 20),  # @1000.0, w=1, key 999
            V3ZeroRun(1, 10, 20, dt_ms=400),  # @1000.4, key 1000
            V3Sample(2, 2, 30, 40, dt_ms=400),  # @1000.8, key 1000 -> 与 z 桶撞 key: raw 优先
            V3Sample(30, 40, 300, 400, dt_ms=400),  # @1001.2, key 1001
            V3Sample(50, 60, 400, 500, dt_ms=400),  # @1001.6, key 1001 -> 同秒第二行
        ),
    )
    points = v3_series_points((b, ), 900, 2000)
    assert [_p(p) for p in points] == [
        (999, 1, 1, 10, 20),
        (1000, 2, 2, 30, 40),  # 混桶: 取 raw, z 让位
        (1001, 40, 50, 400, 500),  # 均值 (30+50)/2, (40+60)/2; 快照取最新行(@1001.6)
    ]


def test_v3_vacuum_and_disconnect_distinct():
    """真空/断连两语义分离(验收): 块内 n 游程 -> 连续 null 槽折叠单个 null 点(首槽位置);
    块间 gap -> 一个真空 null 点(t = 前块游标终值)且 gap 段无任何桶点; 连续块(gap 被首
    记录覆盖桶吸收)不出 null —— 两者各司其职互不误报"""
    b1 = V3Block(1000, 30, (V3Sample(1, 1, 1, 1), V3NullRun(3)))  # r @1000; n 槽 @1030/1060/1090
    b2 = V3Block(5000, 30, (V3Sample(2, 2, 2, 2), ))  # 停机后新块(真空)
    b3 = V3Block(5030, 30, (V3Sample(3, 3, 3, 3), ))  # 连续采样接续(无真空)
    points = v3_series_points((b1, b2, b3), 900, 6000)
    assert [_p(p) for p in points] == [
        (970, 1, 1, 1, 1),
        (1030, None, None, None, None),  # n 游程: 3 槽折叠为 1 个 null 点(断连, 程序活着)
        (1090, None, None, None, None),  # 块间真空: t = 前块游标终值 1090
        (4970, 2, 2, 2, 2),
        (5000, 3, 3, 3, 3),  # b2->b3 gap 30s <= 首槽桶宽 30: 被覆盖桶吸收, 无 null
    ]
    null_ts = [p.t for p in points if p.dl_rate is None]
    assert null_ts == [1030, 1090]  # 恰两个 null: 断连一个 + 真空一个
    assert not any(1090 < p.t < 4970 for p in points)  # 真空段无任何桶点


def test_v3_window_filter_and_empty():
    """窗口切片: ts >= t1 槽不消费 / 覆盖桶触及 t0 才保留(桶首允许略早于 t0, 上界一个
    桶宽, 行照收对齐 v2 窗首口径) / null 点按窗口过滤 / 无块 = 空元组(停机天然真空)"""
    b1 = V3Block(500, 30, (V3Sample(1, 1, 1, 1), V3Sample(1, 1, 1, 1)))  # @500/@530(窗前)
    b2 = V3Block(1000, 30, (V3Sample(2, 2, 2, 2), V3Sample(3, 3, 3, 3), V3NullRun(2)))  # @1000/@1030/n
    b3 = V3Block(2000, 30, (V3Sample(4, 4, 4, 4), ))  # @2000(t1 之后)
    points = v3_series_points((b1, b2, b3), 1000, 1100)
    assert [_p(p) for p in points] == [
        (970, 2, 2, 2, 2),  # 桶 [970,1000) 触及 t0: 照收(桶首略早于 t0)
        (1000, 3, 3, 3, 3),
        (1060, None, None, None, None),  # n 槽 null 点
        (1090, None, None, None, None),  # b2->b3 真空标记(t=1090 < t1)
    ]
    assert v3_series_points((), 0, 1000) == ()  # 无块 = 天然真空
    assert v3_series_points((V3Block(1000, 30, ()), ), 0, 1000) == ()  # 空块(解析器不产, 防御直构)跳过
    assert v3_series_points((b3, ), 0, 1000) == ()  # 全部槽在窗外


def test_v3_series_slots_seam():
    """S3b 接缝: v3_series_slots 把块序列按 start_epoch 稳定排序展平为记录时间轴
    (乱序输入还原时间序), 逐槽 ts/dt_s/obs/is_zero 与单块 v3_block_slots 一致"""
    b1 = V3Block(1000, 30, (V3Sample(1, 1, 10, 20), ))
    b2 = V3Block(2000, 60, (V3Sample(2, 2, 30, 40), V3ZeroRun(2, 30, 40)))
    slots = v3_series_slots((b2, b1))  # 乱序传入
    assert [s.ts for s in slots] == [1000.0, 2000.0, 2060.0, 2120.0]  # z 游程缺省 = 标称 60s x2 槽
    assert slots[0].obs == (1, 1, 10, 20) and not slots[0].is_zero and slots[0].dt_s == 30.0
    assert slots[1].obs == (2, 2, 30, 40) and not slots[1].is_zero
    assert all(s.obs == (0, 0, 30, 40) and s.is_zero and s.dt_s == 60.0 for s in slots[2:])
