"""test_traffic_grid 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v4 换代 plan 26-10-05-2200 N1 —— 仅标识符与 fixture 适配, 断言逻辑零变化)

## 测试计划(每个测试函数一条)
- test_build_grid_24h_and_30d: 24h 窗 30s 栅格 = 2880 桶(floor 对齐); 30d 窗恒 3600s = 720 桶; 未知窗口 ValueError
- test_build_grid_extended_windows: 1m/5m/30m/3h/6h/12h raw 段窗(桶宽 = 采样间隔, 桶数 = 跨度/间隔) + 3d/7d hour 段窗(恒 3600s = 72/168 桶)
- test_build_grid_unaligned_t0_extra_bucket: t0 未对齐栅格时窗首桶提前(floor), 桶数 ceil = 2881(「≈2880」口径)
- test_build_grid_fractional_interval_ceils_bucket_width: 小数采样间隔桶宽向上取整(1.5s -> 2s 桶宽; floor 会隔桶空 = 伪断线)
- test_build_grid_raw_bucket_cap_high_frequency_sampling: (26-10-07-2127 S3)raw 桶数上限 —— 1.5s 采样 24h 加宽到 30s 桶恰 2880 / 3h -> 4s 桶 2700 / 6h -> 8s 桶 2700 / 12h -> 15s 桶 2880; 小窗(1m/5m/30m)上限不生效仍 2s 桶
- test_build_grid_raw_bucket_cap_default_sampling_unchanged: (S3 零回归面)30s 默认采样下桶数上限数学恒等 —— 各 raw 窗桶宽仍 30, 桶数逐窗与加宽前一致
- test_build_grid_raw_cap_seed_extension_covers_sample_bucket: (S3 x S2/D3 联动)上限只加宽桶宽, grid.interval 恒 >= ceil(采样间隔) -> 窗首种子外扩(grid.t0 - grid.interval)恒覆盖 >= 1 个采样桶; 高频采样各窗桶数 <= 2880
- test_build_grid_day_windows_d4: 6mo/1y(D4 新档) day 段窗 —— 滚动窗涉及本地日期逐日铺格(桶键 = 本地日界 00:00, 6mo = 182d + 首尾日 / 1y 比 6mo 多 183 桶), interval 86400; 90d 不存在; all 拒绝 build_grid(数据面定栅格)
- test_build_month_grid_all_view: all 视图数据面铺格 —— 首末月行间逐月铺桶(缺失月也在 = null 桶), 乱序/重复 epoch 取最小最大; 空集合 = 空 buckets 兜底栅格
- test_rate_points_null_shape: points 形状 {"t","dl","up"} | null(空桶断线)
- test_group_null_mask_rules: (D6 沿用)组桶 null = 无任何成员观测(任一成员 r/z 观测即程序存活真值); 无行成员按 0 计; 借 global 判 null 退役
- test_group_rate_sums_members_missing_zero: 组速率 = 桶内 Σ 成员均值, 无行成员按 0 计; null 桶整桶 None
- test_group_totals_per_member_diff_then_sum: 逐成员先差分再求和 —— 单成员重置贡献 0 不拖垮全组; 成员基线缺失(窗首/无行)贡献 0; null 桶断链
- test_group_50_members_correct_and_time_bound: 50 成员 x 满窗 2880 桶聚合正确性(抽样桶 Σ 校验, 每成员一块 -> v4_grid_obs) + 耗时上界(CPU 时间口径 << 采样间隔 30s, 断言 < 8s)
- test_group_zrun_idle_zero_line_and_outage_null: (D6 沿用)组图回归观测面 —— 全员空闲(z 覆盖)0 线 / 全员无观测(停机)断线 / 成员只剩 z 块也有观测; 组三函数消费 v4_grid_obs 产物
- test_v4_points_known_sequence_end_to_end: 已知序列逐桶核对 —— 天文件文本 -> 解析 -> 桶点: 显式 dt / 缺省 / z 均摊 / n 后链式自洽; 断连/停机 null; totals 差分
- test_v4_d1_cross_bucket_coverage: 跨桶覆盖(D1) —— z 游程展开多桶同值非 null; r 暂停宽桶整段承载不伪断
- test_v4_mixed_interval_blocks_per_record_width: 桶宽有效 dt —— 混排 interval 分块各归各桶; 天然 gap 吸收
- test_v4_totals_diff_reset_baseline_and_zchain: 累计段 —— 差分/重置/基线缺失/断链/z 快照链
- test_v4_same_second_merge_and_mixed_key_raw_priority: 同桶合并(均值+最新快照)/混桶 raw 优先
- test_v4_vacuum_and_disconnect_distinct: 真空/断连两语义分离
- test_v4_window_filter_and_empty: 窗口切片/空元组
- test_v4_series_slots_seam: S3b 接缝 —— v4_series_slots 稳定排序展平
- test_v4_grid_obs_expansion: (S3b)栅格展开 —— 对齐记录 1:1 落桶 / D1 宽桶中间栅格桶同值非 null(totals 首桶落增量) / 跨界记录按重叠秒加权 / null 点不参与(空桶承载) / 窗外桶不消费
- test_v4_agg_obs_direct_mapping: (S3b)agg 行直映栅格桶(hour/day/month 同构) —— 行外窗不消费, avg/totals -> 桶值
- test_v4_earliest_row_ts_blocks_and_agg: (S3b)earliest 计入 day/month 行 —— 块首槽(B.start 含块首 z 游程)+ agg 三层全算; 双空 = None
- test_v4_series_points_live_tail_merge_dedup: (S6 验收追加)活尾合流 —— 磁盘部分块+活尾 == 整块桶点(无真空 null 点);
  滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏); 无块纯活尾(z 游程 0 线)照常出点
- test_v4_rate_from_totals_window_seed_and_baseline: (26-10-07-2127 S1)速率口径变换 —— 窗首有种子(前驱桶点作差分基线)后继首桶 rate = delta/w;
  无种子 = 窗首基线缺失 rate=None; totals 与 w 原样保留(totals 通道不受影响)
- test_v4_rate_from_totals_reset_per_direction_chain_unbroken: 重置桶(cur<last)rate 派不出 -> None(dl/up 逐向独立); 链推进独立于 rate 可派
  —— 重置桶的后继对其快照差分仍有基线(链永不被 rate 缺失打断)
- test_v4_rate_from_totals_zchain_vacuum_null_passthrough: z 桶(快照恒定)delta=0 -> 0 线续链; 真空/断连 null 点原样透传且断链;
  断链后基线缺失 rate=None 而 totals 保留(观测面缺口不吞快照)
- test_v4_seed_vacuum_null_t0_edge_band_chain_break: (issue 26-10-08-0141)窗首种子 1 秒边界带 —— 停机落在 (t0-1, t0) 时真空 null 点取整后 = t0-1 落窗外,
  窗过滤下界放宽 _V4_NULL_FLOOR_S 后保留并正确断链(恢复首桶 rate 派不出, 非跨停机假尖峰); 带外(种子点亦被滤)无假尖峰路径
- test_v4_rate_from_totals_wide_bucket_byte_conservation: 宽桶 rate = delta/w —— 逐桶 rate×w = delta 且 Σ(rate×w) = Σ delta 字节守恒(整除构造)
- test_v4_grid_obs_rate_null_totals_valid_exemption: (D4 豁免)rate=None 但 totals 有效的桶点只更新覆盖末端与快照链(rate 权重记 0, 逐向独立)
  —— 桶完全无速率覆盖出 0 线 + 快照照记(后续桶差分基线不断); 混合覆盖按速率覆盖秒加权; 真 null 点仍不参与
- test_group_rate_points_over_transformed_obs_unchanged: 组求和口径不变(S1 钉住)—— group_null_mask/group_rate_points 消费变换后 obs
  无需改动, 豁免桶 0 线按 0 计入组

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V4Block
(天文件文本路径经 format_v4_day_text -> parse_v4_day_text 打通解析接缝); V4Block 直构时
基线参数取 (0,0) 或首记录 totals —— 槽位数学与基线无关, 仅 format/parse roundtrip 路径
要求 delta 非负。
"""
import math
import time

import pytest

from auto_qb.core.traffic_grid import (
    BucketObs,
    MAX_RAW_BUCKETS,
    V4PointEntry,
    WINDOW_SPECS,
    build_grid,
    build_month_grid,
    group_null_mask,
    group_rate_points,
    group_totals_points,
    rate_points,
    series_totals_points,
    v4_agg_obs,
    v4_earliest_row_ts,
    v4_grid_obs,
    v4_rate_from_totals,
    v4_series_points,
    v4_series_slots,
    v4_totals_points,
)
from auto_qb.core.traffic_store import (
    AggRow,
    LiveTail,
    LiveTailRun,
    V4Block,
    V4NullRun,
    V4ParsedAgg,
    V4Sample,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
    v4_live_tail_slots,
    v4_date_str_epoch,
    v4_month_epoch,
    v4_next_month_epoch,
    v4_window_dates,
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
    """小数采样间隔桶宽向上取整: 1.5s -> 2s 桶宽(floor 取 1s 会让 1.5s 一条的采样行隔桶为空 =
    伪断线)。取小窗(1m)使 S3 桶数上限不生效, 纯粹钉住 ceil 语义; 24h 窗同采样间隔被上限加宽
    到 30s 桶(见下方 S3 上限用例)"""
    g = build_grid("1m", NOW, 1.5)
    assert g.interval == 2
    assert len(g.buckets) == 30  # NOW 与 t0 均为偶数, 恰好对齐
    assert g.last < NOW <= g.last + 2  # 覆盖 [t0, t1) 不变


def test_build_grid_raw_bucket_cap_high_frequency_sampling():
    """(计划 26-10-07-2127 S3 万桶级治理)raw 桶宽 = max(ceil(采样间隔), ceil(span/2880)):
    高频采样(1.5s)下 24h 从 43200 桶(2s 桶)加宽到 30s 桶恰 2880; 3h -> 4s 桶 2700;
    6h -> 8s 桶 2700; 12h -> 15s 桶 2880; 小窗(1m/5m/30m)上限不生效仍 2s 桶"""
    g24 = build_grid("24h", NOW, 1.5)
    assert g24.interval == 30 and len(g24.buckets) == 2880  # ceil(86400/2880)=30
    g3h = build_grid("3h", NOW, 1.5)
    assert g3h.interval == 4 and len(g3h.buckets) == 2700  # ceil(10800/2880)=4
    g6h = build_grid("6h", NOW, 1.5)
    assert g6h.interval == 8 and len(g6h.buckets) == 2700  # ceil(21600/2880)=8
    g12h = build_grid("12h", NOW, 1.5)
    assert g12h.interval == 15 and len(g12h.buckets) == 2880  # ceil(43200/2880)=15
    for name, n in (("1m", 30), ("5m", 150), ("30m", 900)):  # 上限不生效: 仍按采样间隔 ceil(1.5)=2
        g = build_grid(name, NOW, 1.5)
        assert g.interval == 2 and len(g.buckets) == n, name


def test_build_grid_raw_bucket_cap_default_sampling_unchanged():
    """(S3 零回归面)30s 默认采样下桶数上限数学恒等: ceil(span/2880) <= 30 恒被采样间隔一侧
    取到, 各 raw 窗桶宽仍 30、桶数逐窗与加宽前一致 —— 上限只治理高频采样部署"""
    assert MAX_RAW_BUCKETS == 2880
    for name, span in (
        ("1m", 60), ("5m", 300), ("30m", 1800), ("3h", 10800), ("6h", 21600), ("12h", 43200), ("24h", 86400)
    ):
        g = build_grid(name, NOW, 30.0)
        assert g.interval == 30, name
        assert len(g.buckets) == span // 30, name


def test_build_grid_raw_cap_seed_extension_covers_sample_bucket():
    """(S3 x S2/D3 联动)上限只加宽桶宽不缩窄, grid.interval 恒 >= ceil(采样间隔) —— S2 的窗首
    种子外扩量(grid.t0 - grid.interval)因此恒覆盖 >= 1 个原始采样桶, 种子点总能取到前驱桶点
    作差分基线; 高频采样下各窗桶数被 2880 兜住(NOW 与 t0 对齐时恰 <= 2880)"""
    for name in ("1m", "5m", "30m", "3h", "6h", "12h", "24h"):
        for si in (1.5, 2.0, 30.0):
            g = build_grid(name, NOW, si)
            assert g.interval >= math.ceil(si), (name, si)  # 加宽后 >= 采样桶宽 -> 种子外扩覆盖采样桶
            assert len(g.buckets) <= MAX_RAW_BUCKETS, (name, si)  # NOW 对齐: 桶数 <= 上限
    g = build_grid("24h", NOW, 1.5)
    assert g.interval == 30 and math.ceil(1.5) == 2
    assert g.interval >= 2  # 种子外扩 30s 覆盖 >= 1 个 2s 采样桶


def test_build_grid_day_windows_d4():
    """6mo/1y(D4 新档, plan 26-10-04-1957 §05.3) day 段窗: 滚动窗(now-182d/365d..now)
    涉及的本地日期逐日铺格, 桶键 = 本地日界 00:00(与 agg day 行 epoch 同源), 窗首桶允许
    早于 t0(首日不满宽); 90d 拍板延后不在窗口集; all 拒绝 build_grid(数据面定栅格)"""
    g = build_grid("6mo", NOW)
    assert g.interval == 86400 and g.segment == "day" and g.t0 == NOW - 182 * 86400 and g.t1 == NOW
    dates = sorted(v4_window_dates(g.t0, g.t1 - 1))
    assert list(g.buckets) == [v4_date_str_epoch(d) for d in dates]  # 与窗口日期游走同源(跨夏令时时区一致)
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
    m0 = v4_month_epoch(NOW)
    m1 = v4_next_month_epoch(m0)
    m2 = v4_next_month_epoch(m1)
    m3 = v4_next_month_epoch(m2)
    mg = build_month_grid((m3, m0, m2, m0), NOW)  # 乱序 + 重复: 缺失月 m1 也在栅格
    assert mg.name == "all" and mg.segment == "month" and mg.interval == 30 * 86400
    assert mg.buckets == (m0, m1, m2, m3)
    assert mg.t0 == m0 and mg.t1 == m3 + 1
    assert build_month_grid((), NOW).buckets == ()  # 无月行: 空 buckets(全 null -> 空态)
    assert build_month_grid((), NOW).interval == 30 * 86400


# ---------------- 单系列离散(§05.1) ----------------
# (v2 raw 归桶/差分/z 覆盖展开用例已随 S3a 读侧翻转重写, 现为 v4 口径, 见文件尾 v4 区)


def test_rate_points_null_shape():
    """points 形状(§08): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)"""
    g = build_grid("24h", NOW, 30.0)
    base = g.first + 60
    obs = {base: BucketObs(1, 2, 3, 4)}
    assert rate_points(obs, g)[g.buckets.index(base)] == {"t": base, "dl": 1, "up": 2}
    assert rate_points(obs, g)[g.buckets.index(base) + 1] is None


# ---------------- 组读侧聚合(§04.1) ----------------


def test_group_null_mask_rules():
    """组桶 null 判定(D6 沿用: 借 global 判 null 退役, §05.1): 桶内任一成员有观测
    (r/z)即非 null —— 采样器全局同拍, 单成员观测 = 程序存活真值; 无行成员按 0 计;
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
    v4 口径: 每成员一个 2880 记录块(标称 30s), 组三函数消费 v4_series_points -> v4_grid_obs 产物。
    """
    g = build_grid("24h", NOW, 30.0)
    n = 50
    blocks = []
    for m in range(n):
        recs = tuple(V4Sample(100 + m, 200 + m, i * 10 + m, 0) for i in range(2880))  # 每桶恰一记录, totals 每桶 +10
        blocks.append(V4Block(g.first + 30, 30, 0, 0, recs))  # 槽位 = g.first+30+30i -> 桶键 = g.buckets[i]

    t_start = time.process_time()
    member_obs = [v4_grid_obs(v4_series_points((blk, ), g.t0, g.t1 + 1), g) for blk in blocks]
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


# ---------------- 组图回归(观测面, S3b D6 沿用) ----------------


def test_group_zrun_idle_zero_line_and_outage_null():
    """组图回归(观测面): 全员空闲(z 覆盖)出 0 线 / 全员无观测(停机)整桶断线 /
    成员只剩 z 块也有观测(z 游程按均摊槽展开) —— 组三函数消费 v4_grid_obs 产物,
    「借 global 判 null」退役后停机/空闲由成员自身观测面区分"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2, b3 = g.buckets[100], g.buckets[101], g.buckets[102], g.buckets[103]
    # 成员块: r @ b0+30(桶 b0, w=30 对齐) + z 游程 2 槽(桶 b1/b2, 速率 (0,0), 快照恒定)
    blk = V4Block(b0 + 30, 30, 100, 50, (V4Sample(1, 1, 100, 50), V4ZeroRun(2, 100, 50)))
    member_obs = [v4_grid_obs(v4_series_points((blk, ), g.t0, g.t1), g)]
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


# ---------------- v4 读侧核心(plan 26-10-04-1957 S3a 立, v4 计划 N1 改名, §05.1/§05.2) ----------------
# 桶点模型(D1 实施期定稿): 逐记录覆盖桶 —— 桶宽 = max(1, ceil(有效dt)), 桶 = [ceil(ts)-w,
# ceil(ts)), t = 桶起点; 单记录的桶天然覆盖其有效 dt 全程(标称栅格视角「中间桶同值非 null」
# 的等价承载), z 游程按均摊槽展开多桶是覆盖语义的字面形态。全部用例构造 v4 块/天文件喂读侧。


def _p(entry):
    """V4PointEntry -> 可比元组"""
    return (entry.t, entry.dl_rate, entry.up_rate, entry.dl_total, entry.up_total)


def test_v4_points_known_sequence_end_to_end():
    """已知序列逐桶核对(验收: 三端点数据对照) —— 天文件文本 -> 解析 -> 桶点, 每桶
    rate/totals/时间正确; 游标 dt 链四形态在桶点层复钉: 显式 dt(r1)/缺省(r0,r3)/
    均摊定位(z 槽)/链式自洽(n 游程后首 r 以游程终点为基准); 断连与停机两语义分离"""
    block1 = V4Block(
        1000,
        30,
        1000,
        2000,
        (
            V4Sample(10, 20, 1000, 2000),  # r0 @1000.0(缺省 dt)
            V4Sample(11, 21, 1100, 2100, dt_ms=30400),  # r1 @1030.4(显式漂移)
            V4ZeroRun(3, 1100, 2100, dt_ms=90000),  # z 槽 @1060.4/1090.4/1120.4(均摊)
            V4NullRun(2, dt_ms=61000),  # n 槽 @1150.9/1181.4(断连)
            V4Sample(12, 22, 1200, 2200, dt_ms=30000),  # r2 @1211.4(= n 游程终点 1181.4 + 30, 链式自洽)
        ),
    )
    block2 = V4Block(5000, 30, 1300, 2300, (V4Sample(13, 23, 1300, 2300), ))  # 停机重启后新块 @5000
    blocks = parse_v4_day_text(format_v4_day_text("global", (block1, block2))).blocks
    points = v4_series_points(blocks, 1000, 5001)
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
    totals = v4_totals_points(points)
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
    assert v4_series_points((block2, block1), 1000, 5001) == points


def test_v4_d1_cross_bucket_coverage():
    """跨桶覆盖(D1 定稿): z 游程单记录按均摊槽展开多桶 —— 每桶 rate 同值 (0,0) + totals
    同快照 + 非 null(覆盖语义的字面形态); r 记录暂停(显式大 dt)由宽桶整段承载 —— 暂停区间
    无 null 点不伪断(v2 一刀切栅格会出成片空桶伪洞), totals 增量落在恢复记录一桶"""
    b = V4Block(
        1000,
        30,
        100,
        200,
        (
            V4Sample(1, 1, 100, 200),  # @1000 -> key 970
            V4ZeroRun(4, 100, 200, dt_ms=160000),  # 单记录跨 4 桶: 均摊槽 @1040/1080/1120/1160(spacing 40)
            V4Sample(2, 2, 300, 400, dt_ms=40000),  # @1200(游程终点 1160 + 40) -> key 1160
        ),
    )
    points = v4_series_points((b, ), 900, 2000)
    assert [_p(p) for p in points] == [
        (970, 1, 1, 100, 200),
        (1000, 0, 0, 100, 200),  # z 槽1: w=40, ceil(1040)-40 —— rate 同值/快照同/非 null
        (1040, 0, 0, 100, 200),  # z 槽2
        (1080, 0, 0, 100, 200),  # z 槽3
        (1120, 0, 0, 100, 200),  # z 槽4(游程终点)
        (1160, 2, 2, 300, 400),  # 后继 r 以游程终点为基准(链式自洽)
    ]
    assert not any(p.dl_rate is None for p in points)  # 覆盖段全程无 null(防伪洞)
    totals = v4_totals_points(points)
    assert [(e.t, e.dl, e.up) for e in totals] == [
        (970, None, None),
        (1000, 0, 0),  # 空闲段 delta=0 链不断
        (1040, 0, 0),
        (1080, 0, 0),
        (1120, 0, 0),
        (1160, 200, 200),  # 恢复桶有基线(由游程快照续上)
    ]
    # r 记录暂停: 2s 块内一记录显式 dt=20s -> 宽桶 [2000,2020) 整段承载(= 10 个标称 2s 桶)
    b2 = V4Block(
        2000,
        2,
        10,
        20,
        (
            V4Sample(5, 5, 10, 20),  # @2000, w=2, key 1998
            V4Sample(6, 6, 20, 40, dt_ms=20000),  # @2020(暂停 20s 如实入行), w=20, key=2000
            V4Sample(7, 7, 30, 60),  # @2022, w=2, key=2020
        ),
    )
    points2 = v4_series_points((b2, ), 1990, 3000)
    assert [_p(p) for p in points2] == [
        (1998, 5, 5, 10, 20),
        (2000, 6, 6, 20, 40),  # 宽桶: 暂停段由该记录的桶承载, 无 null 不伪断
        (2020, 7, 7, 30, 60),
    ]
    totals2 = v4_totals_points(points2)
    assert [(e.t, e.dl, e.up) for e in totals2] == [(1998, None, None), (2000, 10, 20), (2020, 10, 20)]


def test_v4_mixed_interval_blocks_per_record_width():
    """桶宽有效 dt(验收): 混排 interval 分块(60s/2s/30s)各归各桶 —— 逐记录桶宽 =
    max(1, ceil(有效dt)) 替代全局一刀切; 块间 <=1 间隔的天然 gap(含 00:00 硬切)被首记录
    覆盖桶吸收, 不出伪真空"""
    b1 = V4Block(1000, 60, 10, 20, (V4Sample(1, 1, 10, 20), V4Sample(2, 2, 20, 40)))  # @1000/@1060, 桶宽 60
    b2 = V4Block(1062, 2, 30, 60, (V4Sample(3, 3, 30, 60), V4Sample(4, 4, 40, 80)))  # @1062/@1064, 桶宽 2
    b3 = V4Block(1094, 30, 50, 100, (V4Sample(5, 5, 50, 100), ))  # @1094, 桶宽 30
    points = v4_series_points((b3, b1, b2), 900, 2000)  # 乱序传入
    assert [_p(p) for p in points] == [
        (940, 1, 1, 10, 20),  # 60s 块: ceil(1000)-60
        (1000, 2, 2, 20, 40),  # ceil(1060)-60
        (1060, 3, 3, 30, 60),  # 2s 块: ceil(1062)-2(gap 2s <= 首槽桶宽 2, 无真空)
        (1062, 4, 4, 40, 80),  # ceil(1064)-2
        (1064, 5, 5, 50, 100),  # 30s 块: ceil(1094)-30(gap 30s <= 首槽桶宽 30, 无真空)
    ]
    assert not any(p.dl_rate is None for p in points)  # 全程无伪真空


def test_v4_totals_diff_reset_baseline_and_zchain():
    """累计段(v2 语义平移): 相邻桶快照差分 / cur<last 重置桶 null(dl/up 逐向独立) /
    窗首基线缺失 / n 槽 null 点断链后继基线缺失 / 真空断链 / z 游程快照进差分链 ——
    空闲段 delta=0 链不断, 其后首个活跃桶恢复有基线"""
    b1 = V4Block(
        1000,
        30,
        1000,
        500,
        (
            V4Sample(10, 10, 1000, 500),  # @1000 -> key 970
            V4Sample(10, 10, 1800, 400),  # @1030 -> key 1000: dl +800; up 400<500 重置 -> null
            V4Sample(10, 10, 2000, 600),  # @1060 -> key 1030: +200/+200
            V4NullRun(2, dt_ms=61000),  # n 槽 @1090.5/1121.0 -> null 点 1090(断链)
            V4Sample(10, 10, 2100, 700, dt_ms=30000),  # @1151(n 终点 1121+30) -> key 1121: 基线缺失
            V4Sample(10, 10, 2200, 800),  # @1181 -> key 1151: +100/+100
        ),
    )
    b2 = V4Block(
        5000,
        30,
        1000,
        500,
        (
            V4Sample(10, 10, 1000, 500),  # @5000 -> key 4970(真空断链后)
            V4ZeroRun(3, 1000, 500),  # 槽 @5030/5060/5090 -> keys 5000/5030/5060(快照恒定)
            V4Sample(10, 10, 1200, 560, dt_ms=30000),  # @5120 -> key 5090: dl +200 / up +60
        ),
    )
    totals = v4_totals_points(v4_series_points((b1, b2), 900, 6000))
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


def test_v4_same_second_merge_and_mixed_key_raw_priority():
    """同桶合并: 同秒两 raw 行(dt < 1s)速率取均值、快照取最新行(两行同桶口径);
    raw 槽与 z 槽同 key 撞桶 -> 混桶 raw 优先(v2 口径沿用, 确定性钉住)"""
    b = V4Block(
        1000,
        1,
        10,
        20,
        (
            V4Sample(1, 1, 10, 20),  # @1000.0, w=1, key 999
            V4ZeroRun(1, 10, 20, dt_ms=400),  # @1000.4, key 1000
            V4Sample(2, 2, 30, 40, dt_ms=400),  # @1000.8, key 1000 -> 与 z 桶撞 key: raw 优先
            V4Sample(30, 40, 300, 400, dt_ms=400),  # @1001.2, key 1001
            V4Sample(50, 60, 400, 500, dt_ms=400),  # @1001.6, key 1001 -> 同秒第二行
        ),
    )
    points = v4_series_points((b, ), 900, 2000)
    assert [_p(p) for p in points] == [
        (999, 1, 1, 10, 20),
        (1000, 2, 2, 30, 40),  # 混桶: 取 raw, z 让位
        (1001, 40, 50, 400, 500),  # 均值 (30+50)/2, (40+60)/2; 快照取最新行(@1001.6)
    ]


def test_v4_vacuum_and_disconnect_distinct():
    """真空/断连两语义分离(验收): 块内 n 游程 -> 连续 null 槽折叠单个 null 点(首槽位置);
    块间 gap -> 一个真空 null 点(t = 前块游标终值)且 gap 段无任何桶点; 连续块(gap 被首
    记录覆盖桶吸收)不出 null —— 两者各司其职互不误报"""
    b1 = V4Block(1000, 30, 1, 1, (V4Sample(1, 1, 1, 1), V4NullRun(3)))  # r @1000; n 槽 @1030/1060/1090
    b2 = V4Block(5000, 30, 2, 2, (V4Sample(2, 2, 2, 2), ))  # 停机后新块(真空)
    b3 = V4Block(5030, 30, 3, 3, (V4Sample(3, 3, 3, 3), ))  # 连续采样接续(无真空)
    points = v4_series_points((b1, b2, b3), 900, 6000)
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


def test_v4_window_filter_and_empty():
    """窗口切片: ts >= t1 槽不消费 / 覆盖桶触及 t0 才保留(桶首允许略早于 t0, 上界一个
    桶宽, 行照收对齐 v2 窗首口径) / null 点按窗口过滤 / 无块 = 空元组(停机天然真空)"""
    b1 = V4Block(500, 30, 1, 1, (V4Sample(1, 1, 1, 1), V4Sample(1, 1, 1, 1)))  # @500/@530(窗前)
    b2 = V4Block(1000, 30, 2, 2, (V4Sample(2, 2, 2, 2), V4Sample(3, 3, 3, 3), V4NullRun(2)))  # @1000/@1030/n
    b3 = V4Block(2000, 30, 4, 4, (V4Sample(4, 4, 4, 4), ))  # @2000(t1 之后)
    points = v4_series_points((b1, b2, b3), 1000, 1100)
    assert [_p(p) for p in points] == [
        (970, 2, 2, 2, 2),  # 桶 [970,1000) 触及 t0: 照收(桶首略早于 t0)
        (1000, 3, 3, 3, 3),
        (1060, None, None, None, None),  # n 槽 null 点
        (1090, None, None, None, None),  # b2->b3 真空标记(t=1090 < t1)
    ]
    assert v4_series_points((), 0, 1000) == ()  # 无块 = 天然真空
    assert v4_series_points((V4Block(1000, 30, None, None, ()), ), 0, 1000) == ()  # 空块(解析器不产, 防御直构)跳过
    assert v4_series_points((b3, ), 0, 1000) == ()  # 全部槽在窗外


def test_v4_series_slots_seam():
    """S3b 接缝: v4_series_slots 把块序列按 start_epoch 稳定排序展平为记录时间轴
    (乱序输入还原时间序), 逐槽 ts/dt_s/obs/is_zero 与单块 v4_block_slots 一致"""
    b1 = V4Block(1000, 30, 10, 20, (V4Sample(1, 1, 10, 20), ))
    b2 = V4Block(2000, 60, 30, 40, (V4Sample(2, 2, 30, 40), V4ZeroRun(2, 30, 40)))
    slots = v4_series_slots((b2, b1))  # 乱序传入
    assert [s.ts for s in slots] == [1000.0, 2000.0, 2060.0, 2120.0]  # z 游程缺省 = 标称 60s x2 槽
    assert slots[0].obs == (1, 1, 10, 20) and not slots[0].is_zero and slots[0].dt_s == 30.0
    assert slots[1].obs == (2, 2, 30, 40) and not slots[1].is_zero
    assert all(s.obs == (0, 0, 30, 40) and s.is_zero and s.dt_s == 60.0 for s in slots[2:])


# ---------------- v4 视图映射(S3b, §05.3): 桶点流/agg 行 -> 响应栅格 ----------------


def test_v4_grid_obs_expansion():
    """栅格展开(v4_grid_obs, D1 覆盖的栅格形态): 对齐记录 1:1 落桶 / D1 宽桶中间栅格桶
    同值非 null(totals 首个覆盖桶落增量, 其余 delta=0 链不断) / 跨界记录按重叠秒加权 /
    null 点不参与(空桶承载断线) / 窗外栅格桶不消费"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.first + 3000  # 任意栅格桶(3000 为 30 的整倍)
    # 1:1 对齐: 块首槽恰在 b0+30(w=30) -> 桶 [b0, b0+30) = 栅格桶 b0
    blk = V4Block(b0 + 30, 30, 1000, 500, (V4Sample(10, 20, 1000, 500), V4Sample(20, 40, 2000, 900)))
    obs = v4_grid_obs(v4_series_points((blk, ), g.t0, g.t1), g)
    assert obs[b0] == BucketObs(10, 20, 1000, 500)
    assert obs[b0 + 30] == BucketObs(20, 40, 2000, 900)
    assert b0 - 30 not in obs and b0 + 60 not in obs  # 窗外/无观测桶不出现在观测表
    # D1 宽桶: 显式 dt=150s(w=150)的记录覆盖 [b1, b1+150) —— 5 个栅格桶同值非 null 同快照
    b1 = g.first + 30
    blk2 = V4Block(g.first + 30, 30, 100, 50, (V4Sample(1, 1, 100, 50), V4Sample(2, 2, 200, 100, dt_ms=150000)))
    pts2 = v4_series_points((blk2, ), g.t0, g.t1)
    obs2 = v4_grid_obs(pts2, g)
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
    blk3 = V4Block(
        T, 30, 100, 0, (V4Sample(200, 0, 100, 0), V4Sample(100, 0, 200, 0, dt_ms=45000), V4Sample(50, 0, 300, 0))
    )
    pts3 = v4_series_points((blk3, ), g.t0, g.t1)
    obs3 = v4_grid_obs(pts3, g)
    assert obs3[T - 30] == BucketObs(200, 0, 100, 0)  # r1 @T: 桶 [T-30, T) 恰对齐
    assert obs3[T] == BucketObs(100, 0, 200, 0)  # r2 @T+45 w=45: 桶 [T, T+30) 只有它覆盖(30s)
    assert obs3[T + 30] == BucketObs(75, 0, 300, 0)  # (100*15 + 50*15)/30 = 75; 快照取覆盖末端最晚的 r3
    assert obs3[T + 60] == BucketObs(50, 0, 300, 0)  # r3 @T+75: 桶 [T+60, T+75) 15s(独占)
    # null 点(n 游程折叠)不参与归桶: 桶无观测 = null, 断线语义由空桶承载
    blk4 = V4Block(
        T + 300, 30, 900, 0, (V4Sample(9, 9, 900, 0), V4NullRun(2, dt_ms=60000), V4Sample(9, 9, 999, 0, dt_ms=30000))
    )
    obs4 = v4_grid_obs(v4_series_points((blk4, ), g.t0, g.t1), g)
    assert obs4[T + 270] == BucketObs(9, 9, 900, 0)
    assert T + 300 not in obs4 and T + 330 not in obs4  # n 游程段无观测 -> 空(null)
    assert obs4[T + 360] == BucketObs(9, 9, 999, 0)


def test_v4_agg_obs_direct_mapping():
    """agg 行直映栅格桶(S3b §05.3): hour/day/month 行 epoch 即桶键, avg/totals -> 桶值
    (max/cov_s 不上图); 窗外行(不在栅格桶集)不消费; 缺行桶不在返回表 = null"""
    g30 = build_grid("30d", NOW)  # hour 栅格(3600 floor 对齐)
    h_in = g30.first + 7200
    h_out = g30.first - 3600  # 窗前
    rows = (
        AggRow("hour", h_in, 111, 222, 33, 44, 1000, 500, 3600),
        AggRow("hour", h_out, 1, 1, 1, 1, 1, 1, 3600),
    )
    obs = v4_agg_obs(rows, g30)
    assert obs == {h_in: BucketObs(111, 33, 1000, 500)}
    # day 行(6mo 栅格 = 本地日界桶)与 month 行(all 栅格)同构直映
    m0 = v4_month_epoch(NOW)
    gm = build_month_grid((m0, v4_next_month_epoch(m0)), NOW)
    mrows = (
        AggRow("month", m0, 7, 9, 8, 10, 700, 800, 2 * 86400), AggRow("month", m0 - 86400, 1, 1, 1, 1, 1, 1, 86400)
    )
    assert v4_agg_obs(mrows, gm) == {m0: BucketObs(7, 8, 700, 800)}


def test_v4_earliest_row_ts_blocks_and_agg():
    """v4 earliest 计入 day/month 行(S3b, §05.4): 块首槽实测时刻(B.start 即首槽, 含块首
    z 游程)+ agg hour/day/month 三层行 epoch 全算 —— 观测面全层的最早证据;
    双空(无块无 agg 行)= None(组端点空态判据「组从未产过流量」)"""
    agg = V4ParsedAgg(
        key="k",
        hours=(AggRow("hour", 5000, 1, 1, 1, 1, 1, 1, 3600), ),
        days=(AggRow("day", 1000, 1, 1, 1, 1, 1, 1, 86400), ),
        months=(),
        bad_lines=0,
        data_lines=2,
    )
    blocks = (V4Block(3000, 30, 1, 1, (V4Sample(1, 1, 1, 1), )), )
    assert v4_earliest_row_ts(blocks, agg) == 1000  # day 行最早
    assert v4_earliest_row_ts((), agg) == 1000
    assert v4_earliest_row_ts(blocks, None) == 3000  # 只看块
    assert v4_earliest_row_ts((V4Block(
        2000,
        30,
        1,
        1,
        (V4ZeroRun(2, 1, 1)),
    ), ), None) == 2000  # 块首 z 游程 = B.start
    assert v4_earliest_row_ts((), None) is None  # 双空 = 组从未产过流量


# ---------- v4 活尾合流(S6 验收追加, 2026-10-05) ----------


def test_v4_series_points_live_tail_merge_dedup():
    """(S6)活尾合流: 磁盘部分块 + 活尾槽 == 整块桶点(边界无真空 null 点); 滞后快照重列
    已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏); 无块纯活尾(z 游程)照常出 0 线"""
    interval = 30
    start = 1_800_000_000
    recs = (
        V4Sample(100, 50, 1000, 500),
        V4Sample(200, 70, 2000, 800),
        V4ZeroRun(2, 2000, 800),
        V4Sample(150, 60, 2600, 1100),
        V4Sample(90, 40, 3000, 1300),
    )
    full = v4_series_points((V4Block(start, interval, 1000, 500, recs), ), start - 10, start + 400)
    full_slots = v4_block_slots(V4Block(start, interval, 1000, 500, recs))
    # 中途 flush: 磁盘前 2 条 + 活尾后 3 条(写侧游标 = 整块末槽)
    disk = (V4Block(start, interval, 1000, 500, recs[:2]), )
    tail = LiveTail(
        block_open=True,
        head_pending=False,
        start_epoch=start,
        interval_s=interval,
        projected_ts=full_slots[-1].ts,
        records=recs[2:],
        open_run=None,
    )
    merged = v4_series_points(disk, start - 10, start + 400, tail_slots=v4_live_tail_slots(tail))
    assert merged == full  # 合流 == 整块(边界一次标称间隔不被误判真空, 无 null 点)
    # 滞后快照(重列已落盘的 recs[1]): 去重后仍 == 整块桶点
    stale = LiveTail(
        block_open=True,
        head_pending=False,
        start_epoch=start,
        interval_s=interval,
        projected_ts=full_slots[-1].ts,
        records=recs[1:],
        open_run=None,
    )
    merged_stale = v4_series_points(disk, start - 10, start + 400, tail_slots=v4_live_tail_slots(stale))
    assert merged_stale == full
    # 无块纯活尾(进程首日全空闲, 天文件未产生): z 游程槽出 0 线桶点
    run = LiveTailRun(kind="z", start=start + 60.0, last_seen=start + 120.0, dl_total=9, up_total=8, samples=4)
    tail_only = LiveTail(False, False, None, interval, 0.0, (), run)
    pts = v4_series_points((), start, start + 200, tail_slots=v4_live_tail_slots(tail_only))
    assert pts and all(p.dl_rate == 0 and p.up_rate == 0 and p.dl_total == 9 for p in pts)
    assert not any(p.dl_rate is None for p in pts)


# ---------- v4 速率口径变换(计划 26-10-07-2127 S1: 方案 B 计数器差分区间平均, 纯读侧) ----------


def test_v4_rate_from_totals_window_seed_and_baseline():
    """速率口径变换 —— 窗首有种子(前驱桶点作差分基线): 后继首桶 rate = delta/w, 种子自身
    基线缺失 rate=None(v4_grid_obs 窗外过滤天然不外发, 接线属 S2); 无种子 = 窗首基线缺失
    rate=None; totals 与 w 原样保留(totals 通道不受影响)"""
    pts = (
        V4PointEntry(970, 5, 5, 1000, 2000, w=30),  # 窗外前驱桶点(D3 种子形态)
        V4PointEntry(1000, 99, 99, 1600, 2600, w=30),  # delta 600/600 -> 区间平均 20/20
        V4PointEntry(1030, 0, 0, 1600, 2600, w=30),  # z 形态桶: delta 0 -> 0 线续链
    )
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [(970, None, None), (1000, 20, 20), (1030, 0, 0)]
    assert [(p.dl_total, p.up_total, p.w) for p in out] == [
        (1000, 2000, 30),
        (1600, 2600, 30),
        (1600, 2600, 30),
    ]
    # 无种子: 同列去掉前驱 -> 首桶基线缺失 rate=None, 其余不变
    out2 = v4_rate_from_totals(pts[1:])
    assert [(p.t, p.dl_rate, p.up_rate) for p in out2] == [(1000, None, None), (1030, 0, 0)]


def test_v4_rate_from_totals_reset_per_direction_chain_unbroken():
    """重置桶(cur<last)rate 派不出 -> None(dl/up 逐向独立, 对齐采样器 _delta 口径);
    链推进独立于 rate 可派 —— 重置桶的后继对其快照差分仍有基线(链永不被 rate 缺失打断)"""
    pts = (
        V4PointEntry(1000, 1, 1, 1000, 500, w=30),
        V4PointEntry(1030, 1, 1, 100, 1100, w=30),  # dl 重置(100<1000)-> dl None; up +600 -> 20
        V4PointEntry(1060, 1, 1, 700, 1400, w=30),  # 对重置桶快照差分(链不断): +600/+300 -> 20/10
    )
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (1000, None, None),  # 窗首基线缺失
        (1030, None, 20),  # 逐向独立: dl 重置 null / up 区间平均
        (1060, 20, 10),  # 重置桶之后链仍有基线
    ]
    assert [(p.dl_total, p.up_total) for p in out] == [(1000, 500), (100, 1100), (700, 1400)]  # totals 原样


def test_v4_rate_from_totals_zchain_vacuum_null_passthrough():
    """z 桶(快照恒定)delta=0 -> 0 线续链; 真空/断连 null 点(rate/totals 全 None)原样透传
    且断链 —— 后继基线缺失 rate=None 而 totals 原样保留(观测面缺口不吞快照)"""
    pts = (
        V4PointEntry(1000, 0, 0, 1000, 500, w=30),  # z 形态
        V4PointEntry(1030, 0, 0, 1000, 500, w=30),  # delta 0 续链
        V4PointEntry(1060, None, None, None, None, w=0),  # 真空/断连 null 点
        V4PointEntry(1090, 5, 5, 1100, 600, w=30),  # 断链后基线缺失
        V4PointEntry(1120, 5, 5, 1700, 900, w=30),  # 对 1090 快照差分恢复: +600/+300 -> 20/10
    )
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (1000, None, None),  # 窗首无种子: 基线缺失(z 形态桶也无基线可差)
        (1030, 0, 0),  # z 形态桶对前驱差分 delta=0 -> 0 线续链
        (1060, None, None),  # null 点透传
        (1090, None, None),  # 断链后基线缺失
        (1120, 20, 10),
    ]
    assert out[2] == pts[2]  # null 点原样透传(恒等)
    assert (out[3].dl_total, out[3].up_total) == (1100, 600)  # 断链不吞快照(totals 保留)


def test_v4_seed_vacuum_null_t0_edge_band_chain_break():
    """(issue 26-10-08-0141)窗首种子 1 秒边界带: 停机时刻落在 (t0-1, t0) 时, 真空 null 点
    t = int(prev_chain_end) 取整后 = t0-1 恰落窗外 —— 窗过滤下界放宽 _V4_NULL_FLOOR_S 后
    标记保留(修复前被丢), 种子点(key = t0-w, 覆盖桶触及 t0 照收)与恢复首点之间差分链正确
    断开: 恢复首桶 rate 派不出(None)且离线期字节不被误归(修复前链误接 -> 恢复首桶 delta 跨
    停机 = 假尖峰), 次桶基线恢复 delta/w。带外(停机再早 1 秒)种子点亦不满足覆盖被滤,
    恢复首点本就无基线 —— 无假尖峰路径, 钉住边界带恰为 (t0-1, t0)"""
    # 种子块末槽 @999.5 ∈ (t0-1, t0)(t0 = seed_t0 = 1000); 恢复块首点 @1030 -> 桶 1000
    seed = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=29500)))
    recover = V4Block(1030, 30, 10600, 5300, (V4Sample(9, 9, 10600, 5300), V4Sample(8, 8, 11200, 5600)))
    pts = v4_series_points((seed, recover), 1000, 1200)
    assert [(p.t, p.dl_rate, p.dl_total) for p in pts] == [
        (970, 2, 1600),  # 种子点: key = ceil(999.5)-30 = 970, 覆盖桶触及 t0 照收(不外发, 供差分基线)
        (999, None, None),  # 真空 null 点: t = int(999.5) = t0-1, 下界放宽后保留(修复前被丢)
        (1000, 9, 10600),  # 恢复首点: 断链后基线缺失
        (1030, 8, 11200),
    ]
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (970, None, None),  # 种子自身基线缺失(不外发)
        (999, None, None),
        (1000, None, None),  # 恢复首桶: 断链 -> 派不出(修复前 = (10600-1600)/30 = 300 假尖峰)
        (1030, 20, 10),  # 次桶基线恢复 delta(600,300)/30
    ]
    # 带外对照: 停机再早 1 秒(末槽 @998.5 -> 取整 998 < t0-1)时种子点亦不满足覆盖
    # (ceil(998.5)-30 = 969, 覆盖桶 [969,999) 不触及 t0=1000) -> 被滤, 恢复首点本就无基线
    seed2 = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=28500)))
    pts2 = v4_series_points((seed2, recover), 1000, 1200)
    assert [(p.t, p.dl_rate) for p in pts2] == [(1000, 9), (1030, 8)]  # 种子/null 均在窗外: 无标记无种子点
    assert [(p.t, p.dl_rate) for p in v4_rate_from_totals(pts2)] == [(1000, None), (1030, 20)]  # 无假尖峰


def test_v4_rate_from_totals_wide_bucket_byte_conservation():
    """宽桶分摊字节守恒(方案 B 附带收益的守阵): rate = delta/w, 逐桶 rate×w = delta 且
    Σ(rate×w) = Σ delta 与 totals 通道严格一致(整除构造); 瞬时口径的旧 rate 列被整体重写"""
    pts = (
        V4PointEntry(1000, 1, 1, 1000, 500, w=30),  # 种子
        V4PointEntry(1030, 88, 66, 2500, 1400, w=150),  # 宽桶(暂停恢复形): delta 1500/900 -> 10/6
        V4PointEntry(1180, 99, 99, 3100, 1700, w=30),  # delta 600/300 -> 20/10
    )
    out = v4_rate_from_totals(pts)
    assert [(p.dl_rate, p.up_rate) for p in out] == [(None, None), (10, 6), (20, 10)]
    assert [p.dl_rate * p.w for p in out[1:]] == [1500, 600]  # 逐桶 rate×w = delta
    assert sum(p.dl_rate * p.w for p in out[1:]) == 3100 - 1000  # Σ = Σ delta(种子快照->末快照)
    assert sum(p.up_rate * p.w for p in out[1:]) == 1700 - 500


def test_v4_grid_obs_rate_null_totals_valid_exemption():
    """D4 豁免(v4_grid_obs): rate=None 但 totals 有效的桶点仍参与归桶 —— 只更新覆盖末端
    与快照链(rate 权重记 0, 逐向独立), 桶完全无速率覆盖出 0 线 + 快照照记(后续桶差分基线
    不断); 真 null 点(率/totals 全空)仍不参与(桶 null)"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2 = g.buckets[100], g.buckets[101], g.buckets[102]
    pts = (
        V4PointEntry(b0, 10, 10, 1000, 500, w=30),
        V4PointEntry(b1, None, None, 1000, 500, w=30),  # 派不出(重置/基线缺失形态): 豁免参与
        V4PointEntry(b2, 20, 10, 1600, 800, w=30),  # delta 600/300
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(10, 10, 1000, 500)
    assert obs[b1] == BucketObs(0, 0, 1000, 500)  # 0 线 + 快照照记(非 null 桶)
    assert obs[b2] == BucketObs(20, 10, 1600, 800)
    # 豁免桶的快照续链: 后续桶差分基线不断(若 b1 缺席 b2 将基线缺失)
    tot = series_totals_points(obs, g)
    assert tot[g.buckets.index(b1)] == {"t": b1, "dl": 0, "up": 0}
    assert tot[g.buckets.index(b2)] == {"t": b2, "dl": 600, "up": 300}
    # 真 null 点仍不参与: 桶无观测 = null
    assert v4_grid_obs((V4PointEntry(b0, None, None, None, None, w=0), ), g) == {}
    # 逐向豁免: dl 派不出(up 可派)—— dl 出 0 线, up 正常覆盖
    obs3 = v4_grid_obs((V4PointEntry(b0, None, 6, 1200, 500, w=30), ), g)
    assert obs3[b0] == BucketObs(0, 6, 1200, 500)
    # 混合覆盖: 豁免点与速率点共享桶 —— 速率均值只按速率覆盖秒加权(豁免不稀释不虚 0)
    pts4 = (
        V4PointEntry(b2, None, None, 1000, 500, w=15),  # 覆盖 [b2, b2+15)
        V4PointEntry(b2 + 15, 10, 10, 1300, 800, w=30),  # 覆盖 [b2+15, b2+45): 跨 b2/b2+30
    )
    obs4 = v4_grid_obs(pts4, g)
    assert obs4[b2] == BucketObs(10, 10, 1300, 800)  # 15s 速率覆盖 -> 均值 10(非 (10+0)/2)
    assert obs4[b2 + 30] == BucketObs(10, 10, 1300, 800)


def test_group_rate_points_over_transformed_obs_unchanged():
    """组求和口径不变(S1 钉住): group_null_mask/group_rate_points 消费变换后 v4_grid_obs
    产物无需改动 —— 豁免桶(0 线)有快照观测即非 null, 组和按 0 计入; S2 接线后组图直接受益"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1 = g.buckets[100], g.buckets[101]
    m1 = {b0: BucketObs(100, 50, 1000, 500), b1: BucketObs(0, 0, 1000, 500)}  # b1 = 豁免桶 0 线
    m2 = {b0: BucketObs(30, 30, 300, 300), b1: BucketObs(20, 10, 1600, 800)}
    mask = group_null_mask([m1, m2], g)
    assert mask[100] is False and mask[101] is False  # 豁免桶有快照观测即非 null
    pts = group_rate_points([m1, m2], g, mask)
    assert pts[100] == {"t": b0, "dl": 130, "up": 80}
    assert pts[101] == {"t": b1, "dl": 20, "up": 10}  # m1 豁免桶按 0 计(无行同款)
