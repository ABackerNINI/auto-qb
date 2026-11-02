"""test_traffic_grid_grid 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v4 换代 plan 26-10-05-2200 N1 —— 仅标识符与 fixture 适配, 断言逻辑零变化)

## 测试计划(每个测试函数一条)
- test_build_grid_24h_and_30d: 24h 窗 30s 栅格 = 2880 桶(floor 对齐); 30d 窗恒 3600s = 720 桶; 未知窗口 ValueError
- test_build_grid_extended_windows: 1m/5m/30m/3h/6h/12h raw 段窗(桶宽 = 采样间隔, 桶数 = 跨度/间隔) + 3d/7d hour 段窗(恒 3600s = 72/168 桶)
- test_build_grid_unaligned_t0_extra_bucket: t0 未对齐栅格时窗首桶提前(floor), 桶数 ceil = 2881(「≈2880」口径)
- test_build_grid_fractional_interval_ceils_bucket_width: 小数采样间隔桶宽向上取整(1.5s -> 2s 桶宽; floor 会隔桶空 = 伪断线)
- test_build_grid_raw_bucket_cap_high_frequency_sampling: (26-10-07-2127 S3)raw 桶数上限 —— 1.5s 采样 24h 加宽到 30s 桶恰 2880 / 3h -> 4s 桶 2700 / 6h -> 8s 桶 2700 / 12h -> 15s 桶 2880; 小窗(1m/5m/30m)上限不生效仍 2s 桶
- test_build_grid_raw_bucket_cap_default_sampling_unchanged: (S3 零回归面)30s 默认采样下桶数上限数学恒等 —— 各 raw 窗桶宽仍 30, 桶数逐窗与加宽前一致
- test_build_grid_raw_cap_seed_extension_covers_sample_bucket: (S3 x S2/D3 联动)上限只加宽桶宽, grid.interval 恒 >= ceil(采样间隔) -> 窗首种子外扩(grid.t0 - grid.interval)恒覆盖 >= 1 个采样桶; 高频采样各窗桶数 <= 2880
- test_build_grid_day_windows_d4: 6mo/1y(D4 新档) day 段窗 —— 滚动窗涉及本地日期逐日铺格(桶键 = 本地日界 00:00, 6mo = 182d + 首尾日 / 1y 比 6mo 多 183 桶), interval 86400; 90d 不存在; all 拒绝 build_grid(数据面定栅格)
- test_rate_points_null_shape: points 形状 {"t","dl","up"} | null(空桶断线)
- test_v4_points_known_sequence_end_to_end: 已知序列逐桶核对 —— 天文件文本 -> 解析 -> 桶点: 显式 dt / 缺省 / z 均摊 / n 后链式自洽; 断连/停机 null; totals 差分
- test_v4_window_filter_and_empty: 窗口切片/空元组
- test_v4_grid_obs_expansion: (S3b)栅格展开 —— 对齐记录 1:1 落桶 / D1 宽桶中间栅格桶同值非 null(totals 首桶落增量) / 跨界记录按重叠秒加权 / null 点不参与(空桶承载) / 窗外桶不消费
- test_v4_series_points_live_tail_merge_dedup: (S6 验收追加)活尾合流 —— 磁盘部分块+活尾 == 整块桶点(无真空 null 点);
  滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏); 无块纯活尾(z 游程 0 线)照常出点
- test_v4_seed_vacuum_null_t0_edge_band_chain_break: (issue 26-10-08-0141, P2 回看后强化; 26-10-16-0954 修复轮改口径)窗首种子边界带 —— 停机标记与点同界(_V4_SEAM_LOOKBACK_S)后带内带外均保留
  (带外 span > cov -> 覆盖份额回收 290 与误接旧值 300 可区分; 带内 span == cov 回收值与误接同数, 判别力由带外形态承担)
- test_v4_grid_obs_rate_null_totals_valid_exemption: (D4 豁免)rate=None 但 totals 有效的桶点只更新覆盖末端与快照链(rate 权重记 0, 逐向独立)
  —— 桶完全无速率覆盖出 0 线 + 快照照记(后续桶差分基线不断); 混合覆盖按速率覆盖秒加权; 真 null 点仍不参与
- test_v4_grid_obs_break_bucket_rate_null_snapshot_kept: (issue 26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker)断链首桶该向出 None(不再是 0/0 伪点),
  快照照记 -> 次桶基线不断; 无观测缝的起始桶仍 0 线; 组面全成员未知 -> None
- test_v4_grid_obs_window_and_snapshot_edges
  无需改动, 豁免桶 0 线按 0 计入组
- test_v4_series_points_downstream_w_survives_bucket_merge: (mut-core W2 S5 守阵, vsp_75/vsp_120, 高)同桶多记录(混桶 z+raw / raw+raw)的覆盖桶宽 w 活着进下游 —— v4_rate_from_totals / v4_grid_obs 消费不 TypeError
- test_v4_series_points_initial_nrun_mark: (vsp_5, 可达性已证: 块首 n 游程 = 程序开块时 qB 断连的合法形态, 写侧「3 列 B 无基线块」)序列首槽即 n 槽的断连标记必须发出
- test_v4_grid_obs_up_channel_weighted_mean: (vgo_73/vgo_76)up 通道覆盖秒加权均值(对称缺口: dl 侧既有守阵, up 侧补齐)
- test_v4_series_points_lookback_boundary_slots_kept: (vsp_59/vsp_60)回看界边界槽保留 —— 覆盖桶末端恰达 t0-86400 的 z 槽照收(判据错成桶起点/<= 会丢跨界槽)
- test_v4_series_points_same_t_marks_and_obs_sort_stable: (vsp_163; vsp_160 复裁等价——同刻双标记条目恒相等, 元组比较经 == 短路不走 __lt__ 无 TypeError 面)同刻双 null 标记 + 同刻观测点 —— (t, rank) 排序键保序(null 在先), 键失守在 V4PointEntry 比较上 TypeError
- test_v4_grid_obs_break_flag_survives_bucket_second_point: (vgo_60/vgo_62)断链旗跨同桶后继点存活(or 累积), 不被清成 0 线
- test_v4_series_points_null_mark_at_lookback_boundary_kept: (vsp_43/vsp_155)null 标记恰在回看下界 —— 下界含等号, 变异成 `<` 会丢掉该断连标记
- test_v4_series_points_marks_at_window_end_not_emitted: (vsp_44/vsp_156)窗尾整秒标记不发出 —— null 槽末槽恰为 t1 时不追加; 块间真空标记恰为 t1 时由最终过滤挡下
- test_v4_series_points_observed_slot_at_window_end_not_consumed: (vsp_52)恰在 t1 的观测槽不消费(v2 口径 ts >= t1), 变异成 `>` 会多出窗外桶
- test_build_grid_day_window_midnight_anchors: (bg_52/bg_53)day 窗日期集 t1-1 口径 —— 23:59:59 不多铺次日桶, 00:00:01 不丢当日桶
- test_v4_grid_obs_same_end_later_point_wins_snapshot: (vgo_80)同覆盖末端双点快照取后到者, 变异成 `>` 会保留先到快照
- test_v4_grid_obs_coverage_end_advance_keeps_latest_snapshot: (vgo_83)覆盖末端必须推进(`a[4] = cov_end`), 变异成写 a[5] 会让短覆盖点抢走快照
- test_v4_grid_obs_broken_bucket_zero_rate_kept_zero: (vgo_105/vgo_117)断链桶有覆盖且速率为 0 时仍是 0 线, 均值判据错看加权和会把 0 误判成无覆盖出 None
- test_build_grid_integral_interval_floor_not_raised: (mut-core W2 bg_21)桶宽下限恒 1s —— 1.0 采样间隔下小窗桶宽恰 1(下限被抬到 2 让 si∈(0,2) 高频采样桶数腰斩)
- test_v4_series_points_same_bucket_later_snapshot_wins: (mut-core W2 vsp_96)同桶 raw+raw 快照取后到者 —— totals 大于 ts 时比较对象错成 totals 会永不更新
- test_v4_series_points_three_raw_same_bucket_no_typeerror: (mut-core W2 vsp_97)同桶三条 raw 照常均值/末条快照 —— e[4] 被写坏时第三条比较 TypeError
- test_v4_series_points_same_timestamp_later_snapshot_wins: (mut-core W2 vsp_95)同刻双 raw 记录快照取后到者 —— >= 变异成 > 保留先到者(vsp_98/vsp_112 判等价: e[4] 只作单调比较基线, 不参与输出)
- test_v4_series_points_mixed_bucket_raw_priority_keeps_mean: (mut-core W2 vsp_105/vsp_107/vsp_115)z+raw+raw 混桶 raw 优先后两条 raw 仍取均值 —— is_raw 旗写坏退化末条单值, dl 覆盖取错向则均值失真

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
    MONTH_NOMINAL_S,
    V4PointEntry,
    WINDOW_SPECS,
    WindowGrid,
    build_grid,
    build_month_grid,
    grid_for_now,
    group_null_mask,
    group_rate_points,
    group_totals_points,
    rate_points,
    series_totals_points,
    v4_agg_obs,
    v4_agg_obs_live,
    v4_earliest_row_ts,
    v4_grid_obs,
    v4_rate_from_totals,
    v4_series_points,
    v4_series_slots,
    v4_totals_points,
    _V4_SEAM_LOOKBACK_S,
    _V4_SEAM_NULL_S,
    _V4_SEAM_SPREAD_MIN_S,
    _bucket_delta,
    _floor_buckets,
)

from auto_qb.core.traffic_store import (
    AggRow,
    LiveTail,
    LiveTailRun,
    V4Block,
    V4NullRun,
    V4ParsedAgg,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
    v4_live_tail_slots,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_month_epoch,
    v4_next_month_epoch,
    v4_window_dates,
)

from traffic_grid_support import (
    NOW,
    _p,
)


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


def test_build_grid_integral_interval_floor_not_raised():
    """(mut-core W2 bg_21)桶宽下限恒 1s: 采样间隔 1.0 时小窗桶宽恰 1 —— 下限被抬到 2s
    会让 si∈(0,2) 的高频采样在 1m/5m/30m 上凭空把桶数/分辨率腰斩(伪聚合)"""
    for name, n in (("1m", 60), ("5m", 300), ("30m", 1800)):
        g = build_grid(name, NOW, 1.0)
        assert g.interval == 1 and len(g.buckets) == n, name


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


def test_rate_points_null_shape():
    """points 形状(§08): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)"""
    g = build_grid("24h", NOW, 30.0)
    base = g.first + 60
    obs = {base: BucketObs(1, 2, 3, 4)}
    assert rate_points(obs, g)[g.buckets.index(base)] == {"t": base, "dl": 1, "up": 2}
    assert rate_points(obs, g)[g.buckets.index(base) + 1] is None


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


def test_v4_series_points_same_bucket_later_snapshot_wins():
    """(mut-core W2 vsp_96)同桶 raw+raw: 速率取均值、快照取后到者。totals 数值大于 ts 时,
    比较对象错成 totals(e[5])恒假 -> 快照永不更新"""
    slots = (
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.9, 1.0, (15, 21, 4000, 5000), False),
    )
    points = v4_series_points((), 900, 2000, tail_slots=slots)
    assert [(p.t, p.dl_rate, p.up_rate, p.dl_total, p.up_total, p.w) for p in points] == [(998, 10, 15, 4000, 5000, 1)]


def test_v4_series_points_three_raw_same_bucket_no_typeerror():
    """(mut-core W2 vsp_97)同桶三条 raw: 均值三条、快照取末条 —— e[4] 被写成 None 时
    第三条的 `ts >= e[4]` 会 TypeError"""
    slots = (
        V4Slot(998.2, 1.0, (4, 8, 2000, 3000), False),
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.9, 1.0, (6, 10, 4000, 5000), False),
    )
    points = v4_series_points((), 900, 2000, tail_slots=slots)
    assert [(p.t, p.dl_rate, p.up_rate, p.dl_total, p.up_total) for p in points] == [(998, 5, 9, 4000, 5000)]


def test_v4_series_points_same_timestamp_later_snapshot_wins():
    """(mut-core W2 vsp_95)同刻双 raw 记录: 快照取后到者(>= 变异成 > 会保留先到者)。
    vsp_98/vsp_112 判等价 —— e[4] 只作单调比较基线、不参与输出, 生产槽序 ts 非降下陈旧
    e[4] 仍恒 <= 新 ts, 比较结果不变"""
    slots = (
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.5, 1.0, (15, 21, 4000, 5000), False),
    )
    points = v4_series_points((), 900, 2000, tail_slots=slots)
    assert [(p.dl_rate, p.up_rate, p.dl_total, p.up_total) for p in points] == [(10, 15, 4000, 5000)]


def test_v4_series_points_mixed_bucket_raw_priority_keeps_mean():
    """(mut-core W2 vsp_105/vsp_107/vsp_115)z+raw+raw 三连混桶: raw 优先后两条 raw 照常取
    均值 —— is_raw 旗写成假值会退化到「末条 raw 单值」; 覆盖速率取错通道(up 当 dl)均值失真"""
    slots = (
        V4Slot(998.2, 1.0, (0, 0, 1000, 2000), True),
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.9, 1.0, (15, 21, 4000, 5000), False),
    )
    points = v4_series_points((), 900, 2000, tail_slots=slots)
    assert [(p.dl_rate, p.up_rate, p.dl_total, p.up_total) for p in points] == [(10, 15, 4000, 5000)]


def test_v4_window_filter_and_empty():
    """窗口切片: ts >= t1 槽不消费 / 窗口左界侧保留全部块内槽点(P2 回看: 差分链需完整
    陈旧跨度, 渲染由 v4_grid_obs 栅格覆盖过滤承载) / null 点按同界过滤 / 无块 = 空元组
    (停机天然真空)"""
    b1 = V4Block(500, 30, 1, 1, (V4Sample(1, 1, 1, 1), V4Sample(1, 1, 1, 1)))  # @500/@530(窗前, 回看保留)
    b2 = V4Block(1000, 30, 2, 2, (V4Sample(2, 2, 2, 2), V4Sample(3, 3, 3, 3), V4NullRun(2)))  # @1000/@1030/n
    b3 = V4Block(2000, 30, 4, 4, (V4Sample(4, 4, 4, 4), ))  # @2000(t1 之后)
    points = v4_series_points((b1, b2, b3), 1000, 1100)
    assert [_p(p) for p in points] == [
        (470, 1, 1, 1, 1),  # (P2 回看)块首槽保留: 差分链完整(渲染由栅格覆盖过滤, 不进响应)
        (500, 1, 1, 1, 1),
        (530, None, None, None, None),  # b1->b2 块间真空标记(t = int(530)), 同界保留(旧窗界下被丢)
        (970, 2, 2, 2, 2),
        (1000, 3, 3, 3, 3),
        (1060, None, None, None, None),  # n 槽 null 点
        (1090, None, None, None, None),  # b2->b3 真空标记(t=1090 < t1)
    ]
    assert v4_series_points((), 0, 1000) == ()  # 无块 = 天然真空
    assert v4_series_points((V4Block(1000, 30, None, None, ()), ), 0, 1000) == ()  # 空块(解析器不产, 防御直构)跳过
    assert v4_series_points((b3, ), 0, 1000) == ()  # 全部槽在窗尾之后(ts >= t1 不消费)


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


def test_v4_seed_vacuum_null_t0_edge_band_chain_break():
    """(issue 26-10-08-0141)窗首种子 1 秒边界带(P2 回看后语义强化; issue 26-10-16-0954
    修复轮改口径): 停机标记与点同界(_V4_SEAM_LOOKBACK_S)后, (t0-1, t0) 带内与带外的停机
    标记均保留 —— 差分链均正确断开, 离线期字节不被误归成假尖峰。修复轮后重启缝按真实
    跨度摊配回收(两形态均不再断链 None): 带内(种子覆盖末梢恰接到恢复点, span == cov)
    回收值 300/150 与「链误接」同数 —— 判别力由带外形态承担(span=31 > cov=30 ->
    step x cov // span = 8709/4354, rate 290/145, 误接旧值 300/150 必判红); 次桶基线
    恢复 delta/w。原带外对照(标记 998 被丢)在旧窗界下靠「种子点亦被滤」免于误接,
    回看保留种子点后标记同界保留才维持断链 —— 两形态现在同构"""
    # 种子块末槽 @999.5 ∈ (t0-1, t0)(t0 = seed_t0 = 1000); 恢复块首点 @1030 -> 桶 1000
    seed = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=29500)))
    recover = V4Block(1030, 30, 10600, 5300, (V4Sample(9, 9, 10600, 5300), V4Sample(8, 8, 11200, 5600)))
    pts = v4_series_points((seed, recover), 1000, 1200)
    assert [(p.t, p.dl_rate, p.dl_total) for p in pts] == [
        (940, 1, 1000),  # (P2 回看)种子块首槽保留: 差分链完整(渲染由栅格覆盖过滤)
        (970, 2, 1600),  # 种子点: key = ceil(999.5)-30 = 970, 覆盖桶触及 t0 照收(不外发, 供差分基线)
        (999, None, None),  # 真空 null 点: t = int(999.5) = t0-1, 同界保留(修复前被丢)
        (1000, 9, 10600),  # 恢复首点: 重启缝接收桶
        (1030, 8, 11200),
    ]
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (940, None, None),  # 链首基线缺失(不外发)
        (970, 20, 10),  # 种子次槽 delta(600,300)/30(修复前被窗界滤掉, 链首 = 970 基线缺失)
        (999, None, None),
        (1000, 300, 150),  # 重启缝回收: span == cov = 30 -> 9000/4500 全额归接收桶(真实跨度均值 295)
        (1030, 20, 10),  # 次桶基线恢复 delta(600,300)/30
    ]
    # 带外对照(判别力所在): 停机再早 1 秒(末槽 @998.5 -> 取整 998)—— 旧窗界下标记被丢
    # 且种子点亦被滤(免于误接); 回看后两者均保留 —— 接收桶覆盖起点 1000 晚于种子覆盖
    # 末端 999(未覆盖 1s), span=31 > cov=30 -> 只回收覆盖份额(rate 290, 非误差接的 300)
    seed2 = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=28500)))
    pts2 = v4_series_points((seed2, recover), 1000, 1200)
    assert [(p.t, p.dl_rate) for p in pts2] == [
        (940, 1),
        (970, 2),  # key = ceil(998.5) - w29(逐记录桶宽 ceil(28.5)) = 970
        (998, None),  # 带外标记: t = int(998.5) = 998, 同界保留(旧窗界下被丢)
        (1000, 9),
        (1030, 8),
    ]
    assert [(p.t, p.dl_rate) for p in v4_rate_from_totals(pts2)] == [
        (940, None),
        (970, 21),  # delta(600)/w29 = 20.7 -> 21(逐记录桶宽 ceil(28.5) = 29)
        (998, None),
        (1000, 290),  # 覆盖份额 step x cov // span = 8709 -> round(8709/30) = 290(误接旧值 300)
        (1030, 20),
    ]


def test_v4_grid_obs_rate_null_totals_valid_exemption():
    """D4 豁免(v4_grid_obs): rate=None 但 totals 有效的桶点仍参与归桶 —— 只更新覆盖末端
    与快照链(rate 权重记 0, 逐向独立), 桶完全无速率覆盖出 0 线 + 快照照记(后续桶差分基线
    不断); 真 null 点(率/totals 全空)仍不参与(桶 null)。本条钉的是**无观测缝**的起始桶
    0 线(程序/窗口起点); 有观测缝的断链首桶改出 None(issue 26-10-16-0954 修复语义,
    见 test_v4_grid_obs_break_bucket_rate_null_snapshot_kept)"""
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


def test_v4_grid_obs_break_bucket_rate_null_snapshot_kept():
    """(issue 26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker 守阵)断链首桶
    语义: 速率派不出且本桶覆盖起点晚于上一观测点覆盖末端(停机洞/观测缝)时该向出 None
    (前端与空桶同语义: 缺口斜纹; 修复前出 0 线 -> 全窗只剩它一个非 null 值时前端孤点
    标记 + 值域塌到 [0,1], 把一片无采样区一分为二); 快照照记(差分链基线不断);
    无观测缝的起始桶(程序/窗口起点)仍保留 D4 的 0 线; 组面同规则"""
    g = build_grid("24h", NOW, 30.0)
    b0, b1, b2 = g.buckets[100], g.buckets[101], g.buckets[102]
    pts = (
        V4PointEntry(b0, 5, 5, 1000, 500, w=1),  # 洞前最后观测(覆盖 [b0, b0+1))
        V4PointEntry(b2, None, None, 9000, 4000, w=1),  # 洞后首点: 断链 + 覆盖起点晚于 b0+1
        V4PointEntry(b2 + 30, 7, 7, 20000, 9000, w=30),  # 次桶: 对 b2 快照差分
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(5, 5, 1000, 500)
    assert obs[b2] == BucketObs(None, None, 9000, 4000)  # 断链未知 != 0(修复前 0/0 伪点)
    assert rate_points(obs, g)[g.buckets.index(b2)] == {"t": b2, "dl": None, "up": None}
    tot = series_totals_points(obs, g)
    assert tot[g.buckets.index(b2)] == {"t": b2, "dl": None, "up": None}  # 跨洞增长不可归因(不造数)
    assert tot[g.buckets.index(b2 + 30)] == {"t": b2 + 30, "dl": 11000, "up": 5000}  # 快照照记 -> 次桶基线不断
    # 对照: 同形但无观测缝(链路首点, 程序/窗口起点) -> 保留 D4 的 0 线
    pts2 = (
        V4PointEntry(b0, None, None, 1000, 500, w=30),
        V4PointEntry(b1, 5, 5, 1600, 800, w=30),
    )
    assert v4_grid_obs(pts2, g)[b0] == BucketObs(0, 0, 1000, 500)
    # 组面: 全成员该向未知 -> None(断链未知不冒充 0 值点); 有成员已知 -> 未知按 0 计入和
    mask = [False] * len(g.buckets)
    unknown = [{b0: BucketObs(None, None, 1000, 500)}, {b0: BucketObs(None, None, 1600, 800)}]
    assert group_rate_points(unknown, g, mask)[100] == {"t": b0, "dl": None, "up": None}
    mixed = [{b0: BucketObs(None, 5, 1000, 500)}, {b0: BucketObs(30, None, 1600, 800)}]
    assert group_rate_points(mixed, g, mask)[100] == {"t": b0, "dl": 30, "up": 5}


def test_v4_grid_obs_window_and_snapshot_edges():
    """v4_grid_obs 边界: 完全窗外的点不消费(覆盖末端早于窗首)/ 覆盖越过窗尾在最后一个栅格桶
    收口(不越界铺桶)/ 同桶后到的短覆盖点不抢快照(覆盖末端最晚者胜), 速率按覆盖秒加权"""
    g = build_grid("24h", NOW, 30.0)
    first, last = g.first, g.last
    pts = (
        V4PointEntry(first - 600, 100, 100, 10, 20, w=30),  # 窗外: 覆盖末端 < first
        V4PointEntry(first, 200, 200, 100, 200, w=30),  # 窗首桶: 覆盖 30s
        V4PointEntry(first + 10, 300, 300, 111, 222, w=10),  # 同桶后到、覆盖更短
        V4PointEntry(last, 400, 400, 300, 400, w=120),  # 覆盖越过窗尾
    )
    obs = v4_grid_obs(pts, g)
    assert first - 600 not in obs  # 窗外不消费
    assert obs[first].dl_rate == 225  # (200x30 + 300x10) / 40
    assert obs[first].dl_total == 100 and obs[first].up_total == 200  # 覆盖末端最晚者胜(后到短覆盖不抢)
    assert obs[last].dl_rate == 400 and obs[last].dl_total == 300
    assert max(obs) == last  # 窗尾之后不铺桶


def test_v4_series_points_downstream_w_survives_bucket_merge():
    """(vsp_75/vsp_120, 高)同桶多记录的覆盖桶宽 w 必须活着进下游: 混桶(z+raw 与 raw+raw)
    后经 v4_rate_from_totals / v4_grid_obs 消费 —— e[7](w)失守成 None 会在 w <= 0 比较处
    TypeError(端点 500)。此前池内混桶用例未接下游, 撞不出"""
    b = V4Block(
        1000,
        1,
        10,
        20,
        (
            V4Sample(1, 1, 10, 20),  # @1000.0, w=1, key 999
            V4ZeroRun(1, 10, 20, dt_ms=400),  # @1000.4, key 1000
            V4Sample(2, 2, 30, 40, dt_ms=400),  # @1000.8, key 1000: z+raw 混桶(vsp_120 支)
            V4Sample(30, 40, 300, 400, dt_ms=400),  # @1001.2, key 1001
            V4Sample(50, 60, 400, 500, dt_ms=400),  # @1001.6, key 1001: raw+raw 同桶(vsp_75 支)
        ),
    )
    points = v4_series_points((b, ), 900, 2000)
    assert [_p(p) for p in points] == [
        (999, 1, 1, 10, 20),
        (1000, 2, 2, 30, 40),  # 混桶: raw 优先, z 让位
        (1001, 40, 50, 400, 500),  # raw+raw: 速率均值 + 最新行快照
    ]
    assert all(p.w == 1 for p in points)  # 覆盖桶宽取最大, 不失守成 None
    out = v4_rate_from_totals(points)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (999, None, None),  # 窗首基线缺失
        (1000, 20, 20),  # delta 20/20 / w 1
        (1001, 370, 460),  # delta 370/460 / w 1
    ]
    g = WindowGrid("5m", 900, 2000, 1, "raw", tuple(range(900, 2000)))
    obs = v4_grid_obs(out, g)  # 第二下游(v4_grid_obs 的 p.w <= 0 同判面)
    assert obs[1001] == BucketObs(370, 460, 400, 500)


def test_v4_series_points_initial_nrun_mark():
    """(vsp_5)块首 n 游程的断连标记必须发出: 序列首槽即 n 槽时 last_was_null 初值 False
    使首标记得以发出(变异成 True 吞掉序列开头的断连标记)。可达性已证: 块首 n 游程 =
    程序开块时 qB 断连的合法形态(traffic_sample_mod._append_record「块首 n 游程不开基线,
    3 列 B 无基线块」+「无基线块仅 n 游程合法」)"""
    b = V4Block(1000, 30, None, None, (V4NullRun(3), V4Sample(1, 1, 1, 1, dt_ms=30000)))
    points = v4_series_points((b, ), 900, 2000)
    assert [_p(p) for p in points] == [
        (1000, None, None, None, None),  # 块首 n 游程折叠的单个断连标记(首槽 1000.0)
        (1060, 1, 1, 1, 1),  # n 终点 1060 + 30: 桶 [1060, 1090)
    ]


def test_v4_grid_obs_up_channel_weighted_mean():
    """(vgo_73/vgo_76)up 通道覆盖秒加权均值(对称缺口: dl 侧既有断言、up 侧此前无人守)
    —— 同桶两贡献点的 up 覆盖秒与加权和都必须累加(+=), 赋值变异在均值上显形"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    pts = (
        V4PointEntry(b0, 100, 100, 1000, 500, w=30),  # 覆盖 [b0, b0+30): up 30s x 100
        V4PointEntry(b0 + 10, 0, 300, 1100, 900, w=10),  # 覆盖 [b0+10, b0+20): up 10s x 300
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(75, 150, 1000, 500)  # dl (100x30+0x10)/40=75; up (100x30+300x10)/40=150


def test_v4_series_points_lookback_boundary_slots_kept():
    """(vsp_59, 顺手 vsp_60)差分链窗外回看界(_V4_SEAM_LOOKBACK_S)边界槽保留: 覆盖桶末端
    恰达 t0-86400 的 z 槽照收(「桶末端 >= 回看界」判据) —— 判据错成桶起点(key-w)或退化成
    <= 会把跨界槽丢出链, 窗首摊配分母失真(池内全用小 epoch 撞不到回看界)"""
    t0 = NOW
    lo = t0 - _V4_SEAM_LOOKBACK_S
    b = V4Block(lo, 60, 100, 50, (V4ZeroRun(3, 100, 50), V4Sample(2, 2, 300, 150, dt_ms=60000)))
    points = v4_series_points((b, ), t0, t0 + 3600)
    assert [(p.t, p.dl_rate, p.up_rate) for p in points] == [
        (lo - 60, 0, 0),  # 首槽 @lo: key = lo-60, 覆盖末端 = lo 恰达回看界 -> 保留
        (lo, 0, 0),  # 槽 @lo+60
        (lo + 60, 0, 0),  # 槽 @lo+120
        (lo + 120, 2, 2),  # r @lo+180: 桶 [lo+120, lo+180)
    ]


def test_v4_series_points_same_t_marks_and_obs_sort_stable():
    """(vsp_160, 顺手 vsp_163)同刻双 null 标记 + 同刻观测点的排序: rank 位 (t, rank) 保序
    —— null 标记先于同刻观测点; 排序键失守(None / (t, entry))会在 V4PointEntry 比较上
    TypeError。几何: 亚秒 n 游程折叠标记与块间真空标记落同一整秒 + 同刻观测桶"""
    b1 = V4Block(1000, 30, 1, 1, (V4NullRun(2, dt_ms=600), V4Sample(1, 1, 1, 1, dt_ms=300)))
    b2 = V4Block(2000, 30, 2, 2, (V4Sample(2, 2, 2, 2), ))
    points = v4_series_points((b1, b2), 900, 3000)
    assert [(p.t, p.dl_rate, p.w) for p in points] == [
        (1000, None, 0),  # n 游程折叠标记(首槽 1000.0)
        (1000, None, 0),  # 块间真空标记(t = 前块游标终值 1000.9 取整)—— 与上标记同刻
        (1000, 1, 1),  # 同刻观测桶(样本 @1000.9, w=1, key 1000): null 标记排在其前
        (1970, 2, 30),  # b2 观测点
    ]


def test_v4_grid_obs_break_flag_survives_bucket_second_point():
    """(vgo_60, 顺手 vgo_62)断链旗必须跨同桶后继点存活(or 累积) —— 断链桶内第二个无缝点
    不得清旗, 否则断链桶冒充 0 线(issue 26-10-16-0954 语义回退; 池内断链桶皆单点)"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    pts = (
        V4PointEntry(b0 - 60, 5, 5, 1000, 500, w=30),  # 覆盖 [b0-60, b0-30)
        V4PointEntry(b0, None, None, 2000, 900, w=1),  # 覆盖起点 b0 > b0-30: 观测缝 -> 断链
        V4PointEntry(b0 + 1, None, None, 2000, 900, w=1),  # 与前点无缝: broke=False
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(None, None, 2000, 900)  # 断链未知 != 0(后继点不得清旗)


def test_v4_series_points_null_mark_at_lookback_boundary_kept():
    """(vsp_43/vsp_155)null 标记恰在回看下界(_V4_SEAM_LOOKBACK_S)必须发出 —— 下界判据
    含等号(`null_lo <= t`, 附加条件与最终过滤两处); 变异成 `<` 会吞掉窗首断连标记"""
    t0 = NOW
    lo = t0 - _V4_SEAM_LOOKBACK_S
    b = V4Block(lo, 30, None, None, (V4NullRun(3), V4Sample(1, 1, 100, 50, dt_ms=30000)))
    points = v4_series_points((b, ), t0, t0 + 3600)
    assert [(p.t, p.dl_rate) for p in points] == [
        (lo, None),  # n 游程首槽恰在回看下界 -> 断连标记保留
        (lo + 60, 1),  # n 终点 + 30s: 桶 [lo+60, lo+90)
    ]


def test_v4_series_points_marks_at_window_end_not_emitted():
    """(vsp_44/vsp_156)窗尾整秒标记不发出 —— null 槽末槽恰为 t1 时追加条件挡下; 块间真空
    标记恰为 t1 时由最终过滤挡下(变异成 `<=` 会多出窗外 null 点)"""
    t1 = NOW + 3600
    # 前块末槽 @t1: t1-60 首个 n 槽在窗内出标记; 块间真空标记 = prev_chain_end = t1;
    # 后块起点在窗外(只为制造真空标记, 自身观测槽不消费)
    b1 = V4Block(t1 - 60, 30, None, None, (V4NullRun(2, dt_ms=60000), ))
    b2 = V4Block(t1 + 3600, 30, 10, 20, (V4Sample(6, 6, 200, 60), ))
    points = v4_series_points((b1, b2), NOW, t1)
    assert [(p.t, p.dl_rate) for p in points] == [
        (t1 - 60, None),  # 窗内 n 标记; 末槽 t1 与真空标记 t1 均在窗外不发出
    ]


def test_v4_series_points_observed_slot_at_window_end_not_consumed():
    """(vsp_52)恰在 t1 的观测槽不消费(v2 口径 ts >= t1) —— 变异成 `ts > t1` 会把窗外
    记录铺成窗尾桶"""
    t1 = NOW + 3600
    b = V4Block(t1, 30, 10, 20, (V4Sample(5, 5, 100, 50), ))
    assert v4_series_points((b, ), NOW, t1) == ()


def test_build_grid_day_window_midnight_anchors():
    """(bg_52/bg_53)day 窗日期集 t1-1 口径 —— now 恰为 23:59:59 不多铺次日桶, 恰为
    00:00:01 不丢当日桶(变异成 t1+1/t1-2 会各错一天)"""
    midnight = v4_day_epoch(NOW)
    span = WINDOW_SPECS["6mo"][0]
    for now in (midnight + 86399, midnight + 1):
        g = build_grid("6mo", now)
        assert g.segment == "day" and g.t1 == now and g.t0 == now - span
        assert g.last == midnight  # 末桶恒为 now 所在本地日界


def test_v4_grid_obs_same_end_later_point_wins_snapshot():
    """(vgo_80)同覆盖末端双点快照取后到者 —— 判据含等号(`cov_end >= a[4]`); 变异成 `>`
    会保留先到快照(dl/up totals 停在 1000/500)"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    pts = (
        V4PointEntry(b0, 10, 10, 1000, 500, w=30),  # 覆盖 [b0, b0+30)
        V4PointEntry(b0 + 10, 20, 20, 2000, 900, w=20),  # 同末端 [b0+10, b0+30): 后到
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(14, 14, 2000, 900)  # (10x30+20x20)/50=14; 后到快照胜


def test_v4_grid_obs_coverage_end_advance_keeps_latest_snapshot():
    """(vgo_83)覆盖末端必须推进(`a[4] = cov_end`) —— 变异成写 a[5] 时 a[4] 停滞, 更短的
    后续覆盖点会把快照抢为己有"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    pts = (
        V4PointEntry(b0, 1, 1, 100, 50, w=10),  # 覆盖末端 b0+10
        V4PointEntry(b0 + 10, 2, 2, 200, 90, w=20),  # 推进到 b0+30: 快照 200/90
        V4PointEntry(b0 + 20, 3, 3, 300, 120, w=5),  # 末端 b0+25 < b0+30: 不抢快照
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(2, 2, 200, 90)  # (10+40+15)/35=1.857 -> 2; 快照仍是 200/90


def test_v4_grid_obs_broken_bucket_zero_rate_kept_zero():
    """(vgo_105/vgo_117)断链桶有覆盖且速率为 0 仍是 0 线, 不是 None —— 均值判据看覆盖秒
    (`a[0]`/`a[2]`), 变异成看加权和(`a[1]`/`a[3]`)会把 0 误判成无覆盖, 断链桶冒充缺口"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    pts = (
        V4PointEntry(b0 - 60, 9, 9, 1000, 500, w=30),  # 覆盖 [b0-60, b0-30)
        V4PointEntry(b0, 0, 0, 2000, 900, w=30),  # 有观测缝(断链), 但本桶速率覆盖 30s 且为 0
    )
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(0, 0, 2000, 900)  # 有覆盖 -> 0 线; 快照照记
