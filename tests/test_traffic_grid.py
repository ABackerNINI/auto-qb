"""test_traffic_grid 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v3 翻转 plan 26-10-04-1957 S3a/S3b)

## 测试计划(每个测试函数一条)
- test_build_grid_24h_and_30d: 24h 窗 30s 栅格 = 2880 桶(floor 对齐); 30d 窗恒 3600s = 720 桶; 未知窗口 ValueError
- test_build_grid_extended_windows: 1m/5m/30m/3h/6h/12h raw 段窗(桶宽 = 采样间隔, 桶数 = 跨度/间隔) + 3d/7d hour 段窗(恒 3600s = 72/168 桶)
- test_build_grid_unaligned_t0_extra_bucket: t0 未对齐栅格时窗首桶提前(floor), 桶数 ceil = 2881(「≈2880」口径)
- test_build_grid_fractional_interval_ceils_bucket_width: 小数采样间隔桶宽向上取整(1.5s -> 2s 桶宽; floor 会隔桶空 = 伪断线)
- test_build_grid_day_windows_d4: 6mo/1y(D4 新档) day 段窗 —— 滚动窗涉及本地日期逐日铺格(桶键 = 本地日界 00:00, 6mo = 182d + 首尾日 / 1y 比 6mo 多 183 桶), interval 86400; 90d 不存在; all 拒绝 build_grid(数据面定栅格)
- test_build_month_grid_all_view: all 视图数据面铺格 —— 首末月行间逐月铺桶(缺失月也在 = null 桶), 乱序/重复 epoch 取最小最大; 空集合 = 空 buckets 兜底栅格
- test_rate_points_null_shape: points 形状 {"t","dl","up"} | null(空桶断线)
- test_group_null_mask_rules: (v3 重写, D6)组桶 null = 无任何成员观测(任一成员 r/z 观测即程序存活真值); 无行成员按 0 计; 借 global 判 null 退役
- test_group_rate_sums_members_missing_zero: 组速率 = 桶内 Σ 成员均值, 无行成员按 0 计; null 桶整桶 None
- test_group_totals_per_member_diff_then_sum: 逐成员先差分再求和 —— 单成员重置贡献 0 不拖垮全组; 成员基线缺失(窗首/无行)贡献 0; null 桶断链
- test_group_50_members_correct_and_time_bound: (v3 口径)50 成员 x 满窗 2880 桶聚合正确性(抽样桶 Σ 校验, 每成员一块 -> v3_grid_obs) + 耗时上界(CPU 时间口径 << 采样间隔 30s, 断言 < 8s)
- test_group_zrun_idle_zero_line_and_outage_null: (v3 重写)组图回归 v3 观测面 —— 全员空闲(z 覆盖)0 线 / 全员无观测(停机)断线 / 成员只剩 z 块也有观测; 组三函数消费 v3_grid_obs 产物
- test_v3_points_known_sequence_end_to_end: 已知序列逐桶核对 —— 天文件文本 -> 解析 -> 桶点: 显式 dt / 缺省 / z 均摊 / n 后链式自洽; 断连/停机 null; totals 差分
- test_v3_d1_cross_bucket_coverage: 跨桶覆盖(D1) —— z 游程展开多桶同值非 null; r 暂停宽桶整段承载不伪断
- test_v3_mixed_interval_blocks_per_record_width: 桶宽有效 dt —— 混排 interval 分块各归各桶; 天然 gap 吸收
- test_v3_totals_diff_reset_baseline_and_zchain: 累计段 —— 差分/重置/基线缺失/断链/z 快照链
- test_v3_same_second_merge_and_mixed_key_raw_priority: 同桶合并(均值+最新快照)/混桶 raw 优先
- test_v3_vacuum_and_disconnect_distinct: 真空/断连两语义分离
- test_v3_window_filter_and_empty: 窗口切片/空元组
- test_v3_series_slots_seam: S3b 接缝 —— v3_series_slots 稳定排序展平
- test_v3_grid_obs_expansion: (S3b)栅格展开 —— 对齐记录 1:1 落桶 / D1 宽桶中间栅格桶同值非 null(totals 首桶落增量) / 跨界记录按重叠秒加权 / null 点不参与(空桶承载) / 窗外桶不消费
- test_v3_agg_obs_direct_mapping: (S3b)agg 行直映栅格桶(hour/day/month 同构) —— 行外窗不消费, avg/totals -> 桶值
- test_v3_earliest_row_ts_blocks_and_agg: (S3b)earliest 计入 day/month 行 —— 块首槽(B.start 含块首 z 游程)+ agg 三层全算; 双空 = None

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V3Block
(天文件文本路径经 format_v3_day_text -> parse_v3_day_text 打通解析接缝)。
"""
import time

import pytest

from auto_qb.core.traffic_grid import (
    BucketObs,
    WINDOW_SPECS,
    build_grid,
    build_month_grid,
    group_null_mask,
    group_rate_points,
    group_totals_points,
    rate_points,
    series_totals_points,
    v3_agg_obs,
    v3_earliest_row_ts,
    v3_grid_obs,
    v3_series_points,
    v3_series_slots,
    v3_totals_points,
)
from auto_qb.core.traffic_store import (
    AggRow,
    V3Block,
    V3NullRun,
    V3ParsedAgg,
    V3Sample,
    V3ZeroRun,
    format_v3_day_text,
    parse_v3_day_text,
    v3_date_str_epoch,
    v3_month_epoch,
    v3_next_month_epoch,
    v3_window_dates,
)

#: 固定"现在"(2027-01-15, 纯测试时刻; 恰为 30 与 3600 的公倍数, 对齐断言干净)
NOW = 1_800_000_000

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


def test_build_grid_day_windows_d4():
    """6mo/1y(D4 新档, plan 26-10-04-1957 §05.3) day 段窗: 滚动窗(now-182d/365d..now)
    涉及的本地日期逐日铺格, 桶键 = 本地日界 00:00(与 agg day 行 epoch 同源), 窗首桶允许
    早于 t0(首日不满宽); 90d 拍板延后不在窗口集; all 拒绝 build_grid(数据面定栅格)"""
    g = build_grid("6mo", NOW)
    assert g.interval == 86400 and g.segment == "day" and g.t0 == NOW - 182 * 86400 and g.t1 == NOW
    dates = sorted(v3_window_dates(g.t0, g.t1 - 1))
    assert list(g.buckets) == [v3_date_str_epoch(d) for d in dates]  # 与窗口日期游走同源(跨夏令时时区一致)
    assert g.buckets[0] <= g.t0 < g.buckets[0] + 86400  # 窗首桶 = t0 所在日界(允许不满宽)
    assert g.buckets[-1] < g.t1  # 末桶在窗内(当日, 无 day 行 = null 桶)
    g1 = build_grid("1y", NOW)
    assert g1.interval == 86400 and g1.segment == "day" and g1.t0 == NOW - 365 * 86400
    assert len(g1.buckets) - len(g.buckets) == 183  # 365d - 182d = 183 个日界桶(时区无关)
    with pytest.raises(ValueError):
        build_grid("90d", NOW)  # D4 拍板延后(90d 视图不存在)
    with pytest.raises(ValueError):
        build_grid("all", NOW)  # all 栅格由 agg month 行数据面定 -> build_month_grid


def test_build_month_grid_all_view():
    """all 视图数据面铺格(S3b §05.3): 首末 month 行 epoch 之间逐月铺桶(缺失月也在 =
    null 桶, 折线断开); 乱序/重复 epoch 只取最小最大; 标称月长 meta; 空集合 = 空 buckets
    兜底栅格(端点空态面)"""
    m0 = v3_month_epoch(NOW)
    m1 = v3_next_month_epoch(m0)
    m2 = v3_next_month_epoch(m1)
    m3 = v3_next_month_epoch(m2)
    mg = build_month_grid((m3, m0, m2, m0), NOW)  # 乱序 + 重复: 缺失月 m1 也在栅格
    assert mg.name == "all" and mg.segment == "month" and mg.interval == 30 * 86400
    assert mg.buckets == (m0, m1, m2, m3)
    assert mg.t0 == m0 and mg.t1 == m3 + 1
    assert build_month_grid((), NOW).buckets == ()  # 无月行: 空 buckets(全 null -> 空态)
    assert build_month_grid((), NOW).interval == 30 * 86400


# ---------------- 单系列离散(§05.1) ----------------
# (v2 raw 归桶/差分/z 覆盖展开用例已随 S3a 读侧翻转重写为 v3 口径, 见文件尾 v3 区)


def test_rate_points_null_shape():
    """points 形状(§08): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)"""
    g = build_grid("24h", NOW, 30.0)
    base = g.first + 60
    obs = {base: BucketObs(1, 2, 3, 4)}
    assert rate_points(obs, g)[g.buckets.index(base)] == {"t": base, "dl": 1, "up": 2}
    assert rate_points(obs, g)[g.buckets.index(base) + 1] is None


# ---------------- 组读侧聚合(§04.1) ----------------


def test_group_null_mask_rules():
    """组桶 null 判定(v3 重写, D6: 借 global 判 null 退役, §05.1): 桶内任一成员有观测
    (r/z)即非 null —— v3 采样器全局同拍, 单成员观测 = 程序存活真值; 无行成员按 0 计;
    全员无观测(停机/断连/组尚无任何观测)-> null"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2 = g.buckets[10], g.buckets[11], g.buckets[12]
    m1 = {b0: BucketObs(1, 1, 1, 1), b2: BucketObs(1, 1, 1, 1)}  # m1 在 b1 无行
    m2 = {b1: BucketObs(5, 5, 1, 1)}  # b1 只有 m2 有行
    mask = group_null_mask([m1, m2], g)
    assert mask[10] is False and mask[11] is False and mask[12] is False
    # b1 全员无观测 -> null; 早于全部成员最早观测的桶必然无观测, 一并 null(v2 earliest 门被吞并)
    mask2 = group_null_mask([m1], g)
    assert mask2[10] is False and mask2[11] is True and mask2[12] is False
    assert all(m for m in mask2[:10])  # 组尚无观测的桶全 null


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

    上界依据: 组图弹层按采样间隔(30s)低频续拉(§07), 单次聚合须远小于一个间隔 ——
    上界 8s ≈ 间隔的 1/4, 是拦「数量级劣化」的粗闸(紧阈值回归基线见
    tests/test_modules_p5.py::test_rebuild_benchmark_5000_seeds + perf_baseline.json)。
    计时口径: CPU 时间(process_time)而非挂钟 —— 断言环境是 `-n 4` 并行 worker + 覆盖率
    插桩, 挂钟上界会被合法负载拉长(同一负载 dev 插桩中位 ~1.26s, windows-latest 实测
    4.01s 假红; 见 pitfalls/testing/timing-tolerance.md「不要为对称加挂钟上界」),
    CPU 时间只计本进程真烧的核时, 不受 worker 抢占 / 调度放大。余量按被守回归量级定:
    8s ≈ 6.3x dev 插桩中位, 2x 于 CI 实测最坏值, 仍 << 30s 间隔。
    v3 口径: 每成员一个 2880 记录块(标称 30s), 组三函数消费 v3_series_points -> v3_grid_obs 产物。
    """
    g = build_grid("24h", NOW, 30.0)
    n = 50
    blocks = []
    for m in range(n):
        recs = tuple(V3Sample(100 + m, 200 + m, i * 10 + m, 0) for i in range(2880))  # 每桶恰一记录, totals 每桶 +10
        blocks.append(V3Block(g.first + 30, 30, recs))  # 槽位 = g.first+30+30i -> 桶键 = g.buckets[i]

    t_start = time.process_time()
    member_obs = [v3_grid_obs(v3_series_points((blk, ), g.t0, g.t1 + 1), g) for blk in blocks]
    mask = group_null_mask(member_obs, g)
    points = group_rate_points(member_obs, g, mask)
    totals = group_totals_points(member_obs, g, mask)
    elapsed = time.process_time() - t_start

    assert len(points) == len(g.buckets)
    assert all(p is not None for p in points)  # 每桶每成员都有观测: 无 null
    idx = 100
    b = g.buckets[idx]
    assert points[idx] == {"t": b, "dl": 100 * n + n * (n - 1) // 2, "up": 200 * n + n * (n - 1) // 2}
    assert totals[idx] == {"t": b, "dl": 10 * n, "up": 0}  # 逐成员每桶 +10; 上行恒 0
    assert totals[g.buckets.index(g.first)] == {"t": g.first, "dl": 0, "up": 0}  # 窗首基线缺失 -> 0
    assert elapsed < 8.0, f"50 成员聚合 CPU 耗时 {elapsed:.3f}s 超上界"


# ---------------- 组图回归(v3 观测面, S3b D6 重写) ----------------


def test_group_zrun_idle_zero_line_and_outage_null():
    """组图回归(v3 观测面): 全员空闲(z 覆盖)出 0 线 / 全员无观测(停机)整桶断线 /
    成员只剩 z 块也有观测(z 游程按均摊槽展开) —— 组三函数消费 v3_grid_obs 产物,
    「借 global 判 null」退役后停机/空闲由成员自身观测面区分"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2, b3 = g.buckets[100], g.buckets[101], g.buckets[102], g.buckets[103]
    # 成员块: r @ b0+30(桶 b0, w=30 对齐) + z 游程 2 槽(桶 b1/b2, 速率 (0,0), 快照恒定)
    blk = V3Block(b0 + 30, 30, (V3Sample(1, 1, 100, 50), V3ZeroRun(2, 100, 50)))
    member_obs = [v3_grid_obs(v3_series_points((blk, ), g.t0, g.t1), g)]
    mask = group_null_mask(member_obs, g)
    assert mask[100] is False and mask[101] is False and mask[102] is False
    assert mask[103] is True  # z 游程之后无新块 = 停机: 全员无观测 -> null(成员观测面裁决)
    pts = group_rate_points(member_obs, g, mask)
    assert pts[100] == {"t": b0, "dl": 1, "up": 1}
    assert pts[101] == {"t": b1, "dl": 0, "up": 0}  # z 槽 = 空闲 0 线(非 null)
    assert pts[102] == {"t": b2, "dl": 0, "up": 0}
    assert pts[103] is None  # 停机桶整桶 None
    totals = group_totals_points(member_obs, g, mask)
    assert totals[100] == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失贡献 0(不出洞)
    assert totals[101] == {"t": b1, "dl": 0, "up": 0}  # z 快照(100,50)同值: 空闲段 delta=0
    assert totals[102] == {"t": b2, "dl": 0, "up": 0}
    assert totals[103] is None


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


# ---------------- v3 视图映射(S3b, §05.3): 桶点流/agg 行 -> 响应栅格 ----------------


def test_v3_grid_obs_expansion():
    """栅格展开(v3_grid_obs, D1 覆盖的栅格形态): 对齐记录 1:1 落桶 / D1 宽桶中间栅格桶
    同值非 null(totals 首个覆盖桶落增量, 其余 delta=0 链不断) / 跨界记录按重叠秒加权 /
    null 点不参与(空桶承载断线) / 窗外栅格桶不消费"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.first + 3000  # 任意栅格桶(3000 为 30 的整倍)
    # 1:1 对齐: 块首槽恰在 b0+30(w=30) -> 桶 [b0, b0+30) = 栅格桶 b0
    blk = V3Block(b0 + 30, 30, (V3Sample(10, 20, 1000, 500), V3Sample(20, 40, 2000, 900)))
    obs = v3_grid_obs(v3_series_points((blk, ), g.t0, g.t1), g)
    assert obs[b0] == BucketObs(10, 20, 1000, 500)
    assert obs[b0 + 30] == BucketObs(20, 40, 2000, 900)
    assert b0 - 30 not in obs and b0 + 60 not in obs  # 窗外/无观测桶不出现在观测表
    # D1 宽桶: 显式 dt=150s(w=150)的记录覆盖 [b1, b1+150) —— 5 个栅格桶同值非 null 同快照
    b1 = g.first + 30
    blk2 = V3Block(g.first + 30, 30, (V3Sample(1, 1, 100, 50), V3Sample(2, 2, 200, 100, dt_ms=150000)))
    pts2 = v3_series_points((blk2, ), g.t0, g.t1)
    obs2 = v3_grid_obs(pts2, g)
    f = g.first
    assert obs2[f] == BucketObs(1, 1, 100, 50)  # 首记录对齐桶
    for t in (f + 30, f + 60, f + 90, f + 120, f + 150):
        assert obs2[t] == BucketObs(2, 2, 200, 100), t  # 宽桶覆盖的中间栅格桶同值(防伪洞)
    assert f + 180 not in obs2
    tot = series_totals_points(obs2, g)
    assert tot[g.buckets.index(f + 30)] == {"t": f + 30, "dl": 100, "up": 50}  # 增量落首个覆盖桶
    assert tot[g.buckets.index(f + 60)] == {"t": f + 60, "dl": 0, "up": 0}  # 同快照 delta=0 链不断
    assert tot[g.buckets.index(f + 150)] == {"t": f + 150, "dl": 0, "up": 0}
    # 跨界加权: r2 显式 dt=45s(w=45)覆盖 [T, T+45) -> 桶 T 分 30s / 桶 T+30 分 15s;
    # 后继 r3(标称 30s)覆盖 [T+45, T+75) 与 r2 共享桶 T+30(15s+15s)—— 加权均值
    T = b0 + 30
    blk3 = V3Block(T, 30, (V3Sample(200, 0, 100, 0), V3Sample(100, 0, 200, 0, dt_ms=45000), V3Sample(50, 0, 300, 0)))
    pts3 = v3_series_points((blk3, ), g.t0, g.t1)
    obs3 = v3_grid_obs(pts3, g)
    assert obs3[T - 30] == BucketObs(200, 0, 100, 0)  # r1 @T: 桶 [T-30, T) 恰对齐
    assert obs3[T] == BucketObs(100, 0, 200, 0)  # r2 @T+45 w=45: 桶 [T, T+30) 只有它覆盖(30s)
    assert obs3[T + 30] == BucketObs(75, 0, 300, 0)  # (100*15 + 50*15)/30 = 75; 快照取覆盖末端最晚的 r3
    assert obs3[T + 60] == BucketObs(50, 0, 300, 0)  # r3 @T+75: 桶 [T+60, T+75) 15s(独占)
    # null 点(n 游程折叠)不参与归桶: 桶无观测 = null, 断线语义由空桶承载
    blk4 = V3Block(
        T + 300, 30, (V3Sample(9, 9, 900, 0), V3NullRun(2, dt_ms=60000), V3Sample(9, 9, 999, 0, dt_ms=30000))
    )
    obs4 = v3_grid_obs(v3_series_points((blk4, ), g.t0, g.t1), g)
    assert obs4[T + 270] == BucketObs(9, 9, 900, 0)
    assert T + 300 not in obs4 and T + 330 not in obs4  # n 游程段无观测 -> 空(null)
    assert obs4[T + 360] == BucketObs(9, 9, 999, 0)


def test_v3_agg_obs_direct_mapping():
    """agg 行直映栅格桶(S3b §05.3): hour/day/month 行 epoch 即桶键, avg/totals -> 桶值
    (max/cov_s 不上图); 窗外行(不在栅格桶集)不消费; 缺行桶不在返回表 = null"""
    g30 = build_grid("30d", NOW)  # hour 栅格(3600 floor 对齐)
    h_in = g30.first + 7200
    h_out = g30.first - 3600  # 窗前
    rows = (
        AggRow("hour", h_in, 111, 222, 33, 44, 1000, 500, 3600),
        AggRow("hour", h_out, 1, 1, 1, 1, 1, 1, 3600),
    )
    obs = v3_agg_obs(rows, g30)
    assert obs == {h_in: BucketObs(111, 33, 1000, 500)}
    # day 行(6mo 栅格 = 本地日界桶)与 month 行(all 栅格)同构直映
    m0 = v3_month_epoch(NOW)
    gm = build_month_grid((m0, v3_next_month_epoch(m0)), NOW)
    mrows = (
        AggRow("month", m0, 7, 9, 8, 10, 700, 800, 2 * 86400), AggRow("month", m0 - 86400, 1, 1, 1, 1, 1, 1, 86400)
    )
    assert v3_agg_obs(mrows, gm) == {m0: BucketObs(7, 8, 700, 800)}


def test_v3_earliest_row_ts_blocks_and_agg():
    """v3 earliest 计入 day/month 行(S3b, §05.4): 块首槽实测时刻(B.start 即首槽, 含块首
    z 游程)+ agg hour/day/month 三层行 epoch 全算 —— 观测面全层的最早证据;
    双空(无块无 agg 行)= None(组端点空态判据「组从未产过流量」的 v3 口径)"""
    agg = V3ParsedAgg(
        key="k",
        hours=(AggRow("hour", 5000, 1, 1, 1, 1, 1, 1, 3600), ),
        days=(AggRow("day", 1000, 1, 1, 1, 1, 1, 1, 86400), ),
        months=(),
        bad_lines=0,
        data_lines=2,
    )
    blocks = (V3Block(3000, 30, (V3Sample(1, 1, 1, 1), )), )
    assert v3_earliest_row_ts(blocks, agg) == 1000  # day 行最早
    assert v3_earliest_row_ts((), agg) == 1000
    assert v3_earliest_row_ts(blocks, None) == 3000  # 只看块
    assert v3_earliest_row_ts((V3Block(
        2000,
        30,
        (V3ZeroRun(2, 1, 1)),
    ), ), None) == 2000  # 块首 z 游程 = B.start
    assert v3_earliest_row_ts((), None) is None  # 双空 = 组从未产过流量
