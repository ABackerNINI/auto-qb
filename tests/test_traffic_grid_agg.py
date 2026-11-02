"""test_traffic_grid_agg 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v4 换代 plan 26-10-05-2200 N1 —— 仅标识符与 fixture 适配, 断言逻辑零变化)

## 测试计划(每个测试函数一条)
- test_build_month_grid_all_view: all 视图数据面铺格 —— 首末月行间逐月铺桶(缺失月也在 = null 桶), 乱序/重复 epoch 取最小最大; 空集合 = 空 buckets 兜底栅格
- test_v4_d1_cross_bucket_coverage: 跨桶覆盖(D1) —— z 游程展开多桶同值非 null; r 暂停宽桶整段承载不伪断
- test_v4_mixed_interval_blocks_per_record_width: 桶宽有效 dt —— 混排 interval 分块各归各桶; 天然 gap 吸收
- test_v4_totals_diff_reset_baseline_and_zchain: 累计段 —— 差分/重置/基线缺失/断链/z 快照链
- test_v4_same_second_merge_and_mixed_key_raw_priority: 同桶合并(均值+最新快照)/混桶 raw 优先
- test_v4_vacuum_and_disconnect_distinct: 真空/断连两语义分离
- test_v4_agg_obs_direct_mapping: (S3b)agg 行直映栅格桶(hour/day/month 同构) —— 行外窗不消费, avg/totals -> 桶值
- test_v4_earliest_row_ts_blocks_and_agg: (S3b)earliest 计入 day/month 行 —— 块首槽(B.start 含块首 z 游程)+ agg 三层全算; 双空 = None
- test_v4_rate_from_totals_window_seed_and_baseline: (26-10-07-2127 S1)速率口径变换 —— 窗首有种子(前驱桶点作差分基线)后继首桶 rate = delta/w;
  无种子 = 窗首基线缺失 rate=None; totals 与 w 原样保留(totals 通道不受影响)
- test_v4_rate_from_totals_reset_per_direction_chain_unbroken: 重置桶(cur<last)rate 派不出 -> None(dl/up 逐向独立); 链推进独立于 rate 可派
  —— 重置桶的后继对其快照差分仍有基线(链永不被 rate 缺失打断)
- test_v4_rate_from_totals_zchain_vacuum_null_passthrough: z 桶(快照恒定)delta=0 -> 0 线续链; 真空/断连 null 点原样透传且断链;
  断链后基线缺失 rate=None 而 totals 保留(观测面缺口不吞快照); (26-10-16-0954 修复轮)短缝跨标记按真实跨度覆盖份额摊配回收
- test_v4_rate_from_totals_wide_bucket_byte_conservation: 宽桶 rate = delta/w —— 逐桶 rate×w = delta 且 Σ(rate×w) = Σ delta 字节守恒(整除构造)
- test_bucket_delta_null_and_reset
- test_grid_for_now_wraps_build_grid
- test_v4_agg_obs_live_merge_partial_and_residual
- test_v4_rate_from_totals_w1_bucket_rates: (vrft_16/vrft_26)w=1 桶速率照常派出(delta/w)不丢 None
- test_v4_same_bucket_raw_mean_with_zero_dl_first: (vsp_82)raw+raw 同桶判定看 is_raw 旗不看速率列 —— 首记录 dl 速率 0 仍走均值支
- test_build_month_grid_empty_meta_complete: (bmg_3, 顺手 bmg_6/_7/_8/_10/_18..)空月集兜底栅格 meta 仍齐全(name/segment/t0/t1/interval/buckets)
- test_floor_buckets_remainder_one_keeps_tail_bucket: (fb_9)t1-first ≡ 1 (mod interval) 时 ceil 尾桶保留, interval-1 变异成 -2 会少一个尾桶
- test_v4_totals_points_spread_threshold_exact_boundary: (vtp_62)摊配门槛 span 恰等 max(2w,60) 不摊配, 变异成 >= 会多摊一批
- test_v4_rate_from_totals_zero_width_point_defensive: (vrft_15/vrft_25)w=0 直构点防御契约 —— 速率派不出(None)而非除零, 变异成 `w < 0` 会 ZeroDivisionError
- test_grid_for_now_forwards_sample_interval: (mut-core W2 gfn_6)grid_for_now 转发 sample_interval —— 传 1.0 小窗桶宽 1(删实参落默认 30 时桶宽退化 30)

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


def test_v4_d1_cross_bucket_coverage():
    """跨桶覆盖(D1 定稿): z 游程单记录按均摊槽展开多桶 —— 每桶 rate 同值 (0,0) + totals
    同快照 + 非 null(覆盖语义的字面形态); r 记录暂停(显式大 dt)由宽桶整段承载 —— 暂停区间
    无 null 点不伪断(v2 一刀切栅格会出成片空桶伪洞)。totals 增量原单桶落在恢复记录
    (P2 接缝摊配后, 长 z 游程冻结期的台阶按真实发生跨度摊配到游程桶+恢复桶, 见断言)"""
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
        (1000, 40, 40),  # (P2 接缝摊配)160s z 游程冻结期 +200/+200 按覆盖秒摊配(份额 40/桶)
        (1040, 40, 40),
        (1080, 40, 40),
        (1120, 40, 40),
        (1160, 40, 40),  # 接收桶 = 余额; Σ = 200/200 守恒(修复前恢复桶单桶 200/200)
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
        (5000, 50, 15),  # (P2 接缝摊配)z 游程冻结期 +200/+60 按覆盖秒摊配(份额 50/15)
        (5030, 50, 15),
        (5060, 50, 15),
        (5090, 50, 15),  # 接收桶 = 余额; Σ = 200/60 守恒(修复前恢复桶单桶 200/60)
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


def test_v4_agg_obs_live_merge_partial_and_residual():
    """agg 行 + 活尾未封口部分行合流(S7, 2026-10-14; 3d+ 视图图尾真空修复): 磁盘无行的
    桶(开放小时/当日/当月 —— 图尾桶)活尾部分行直映 —— 图尾不再停在最后一个封口桶;
    磁盘已有行的同 epoch(已封桶迟到补记残余)走 v4_merge_agg 合流(cov 加权 avg / max
    取大 / totals 取后封行 / cov 相加截到桶宽)—— 残余不双计不丢, 与写侧 _agg_merge_prev
    同判据; 窗外 epoch(活尾行落在栅格外)不消费; 活尾空 = 退化为纯磁盘直映"""
    g30 = build_grid("30d", NOW)
    h_live = g30.last  # 活尾行 epoch 在栅格桶集内(磁盘无行 -> 直映)
    h_disk = g30.last - 3600  # 磁盘封口行所在桶
    disk = (AggRow("hour", h_disk, 100, 100, 50, 50, 1000, 2000, 1838), )
    live = (AggRow("hour", h_live, 300, 300, 100, 100, 5000, 2500, 1800), )
    obs = v4_agg_obs_live(disk, live, g30)
    assert obs[h_live] == BucketObs(300, 100, 5000, 2500)  # 开放桶直映: 尾真空补齐
    assert obs[h_disk] == BucketObs(100, 50, 1000, 2000)  # 无活尾冲突: 磁盘行原样
    # 同 epoch 残余合流: 首封 1838s@100 + 残余 1762s@200 -> cov 加权 149(非任一侧, 也非 2x)
    residual = (AggRow("hour", h_disk, 200, 200, 60, 60, 2000, 3000, 1762), )
    obs2 = v4_agg_obs_live(disk, residual, g30)
    assert obs2[h_disk] == BucketObs(149, 55, 2000, 3000)  # avg cov 加权 / totals 取后封行
    # 活尾空元组: 与 v4_agg_obs 逐点一致(纯磁盘路径零变化)
    assert v4_agg_obs_live(disk, (), g30) == v4_agg_obs(disk, g30)
    # 活尾行 epoch 落在栅格窗外: 不消费(与磁盘窗外行同口径)
    out = (AggRow("hour", g30.first - 3600, 9, 9, 9, 9, 9, 9, 3600), )
    assert v4_agg_obs_live(disk, out, g30) == v4_agg_obs(disk, g30)


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
    """z 桶(快照恒定)delta=0 -> 0 线续链; 真空/断连 null 点(rate/totals 全 None)原样透传;
    观测面缺口不吞快照(totals 保留)。P2 接缝摊配 + issue 26-10-16-0954 修复轮改口径:
    30s 真空缝 <= 60s = 重启缝, 台阶跨标记按真实跨度摊配回收(修复前断链 None; 覆盖份额
    口径: span=90 > cov=60 -> step_w = 100 x 60 // 90 = 66, 份额 33/33 -> rate 1);
    长缝(>60s)仍断链, 见 test_v4_seam_hole_over_threshold_drops_delta"""
    pts = (
        V4PointEntry(1000, 0, 0, 1000, 500, w=30),  # z 形态
        V4PointEntry(1030, 0, 0, 1000, 500, w=30),  # delta 0 续链
        V4PointEntry(1060, None, None, None, None, w=0),  # 真空/断连 null 点
        V4PointEntry(1090, 5, 5, 1100, 600, w=30),  # 短缝后继: 台阶跨标记摊配
        V4PointEntry(1120, 5, 5, 1700, 900, w=30),  # 对 1090 快照差分恢复: +600/+300 -> 20/10
    )
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (1000, None, None),  # 窗首无种子: 基线缺失(z 形态桶也无基线可差)
        (1030, 1, 1),  # (接缝摊配)台阶 100/100 跨标记摊到 1030/1090(覆盖份额 33, rate=round(33/30))
        (1060, None, None),  # null 点透传(标记桶仍 null, 摊配不凭空造数据)
        (1090, 1, 1),  # 接收桶 = 余额(修复前断链 None)
        (1120, 20, 10),  # 摊配后游程重锚于 1090: 本桶差分照旧
    ]
    assert out[2] == pts[2]  # null 点原样透传(恒等)
    assert (out[3].dl_total, out[3].up_total) == (1100, 600)  # 摊配不吞快照(totals 保留)


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


def test_grid_for_now_wraps_build_grid():
    """grid_for_now = build_grid 的现在时包装(API 层入口): 同一窗口/间隔/段, t1 取调用时刻
    (两次调用秒级差 <= 2s)"""
    g = grid_for_now("24h", 30)
    ref = build_grid("24h", time.time(), 30)
    assert g.name == ref.name == "24h" and g.interval == ref.interval == 30 and g.segment == ref.segment
    assert abs(g.t1 - ref.t1) <= 2


def test_grid_for_now_forwards_sample_interval():
    """(mut-core W2 gfn_6)grid_for_now 必须把 sample_interval 转发给 build_grid:
    传 1.0 时 1m 桶宽 1(删实参落默认 30 会退化成 30s 桶)"""
    g = grid_for_now("1m", 1.0)
    assert g.interval == 1 and g.segment == "raw"


def test_bucket_delta_null_and_reset():
    """累计差分两条 None 出口: 任一侧基线缺失 -> None(未知 != 0, 不冒充分线 0 值点);
    计数器回落(cur < last)-> None(非优雅重启/删种重加, 绝不产负增量)"""
    assert _bucket_delta(None, 5) is None and _bucket_delta(5, None) is None
    assert _bucket_delta(3, 5) is None
    assert _bucket_delta(5, 3) == 2 and _bucket_delta(5, 5) == 0


def test_v4_rate_from_totals_w1_bucket_rates():
    """(vrft_16/vrft_26)w=1 桶(1s 采样/亚秒 dt)速率照常派出(delta/w), 不丢 None ——
    门槛错成 w <= 1 会把 1 秒桶的图面打成缺口(池内 rate 变换用例最小 w=29)"""
    pts = (
        V4PointEntry(970, 1, 1, 1000, 500, w=30),
        V4PointEntry(1000, 5, 5, 1100, 600, w=1),  # delta 100/100 -> rate 100/100
    )
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [(970, None, None), (1000, 100, 100)]
    assert [(p.dl_total, p.up_total, p.w) for p in out] == [(1000, 500, 30), (1100, 600, 1)]  # totals/w 原样


def test_v4_same_bucket_raw_mean_with_zero_dl_first():
    """(vsp_82)raw+raw 同桶判定看 is_raw 旗(e[0])不看速率列 —— 首记录 dl 速率为 0 的
    raw+raw 同桶仍走均值支(变异成 e[1] 会误走覆盖支, 第二条覆盖第一条)"""
    b = V4Block(
        1000,
        1,
        10,
        20,
        (
            V4Sample(9, 9, 10, 20),  # @1000.0, w=1, key 999
            V4Sample(9, 9, 20, 30, dt_ms=1200),  # @1001.2, w=2, key 1000
            V4Sample(0, 100, 30, 40, dt_ms=400),  # @1001.6, w=1, key 1001(首条 dl 速率 0)
            V4Sample(50, 200, 50, 60, dt_ms=400),  # @1002.0, w=1, key 1001(同桶第二条)
        ),
    )
    points = v4_series_points((b, ), 900, 2000)
    assert [(p.t, p.dl_rate, p.up_rate, p.dl_total, p.up_total) for p in points] == [
        (999, 9, 9, 10, 20),
        (1000, 9, 9, 20, 30),
        (1001, 25, 150, 50, 60),  # raw+raw 均值 (0+50)/2, (100+200)/2; 首条 dl=0 不破坏判定
    ]


def test_build_month_grid_empty_meta_complete():
    """(bmg_3, 顺手 bmg_6/_7/_8/_10/_18/_19/_20/_21)空月集兜底栅格 meta 仍齐全(name/
    segment/interval/t0/t1/buckets) —— 下游 traffic_qb 直消费 grid 字段, 任一失守即空态面破"""
    g = build_month_grid((), NOW)
    assert g.name == "all" and g.segment == "month" and g.interval == MONTH_NOMINAL_S
    assert g.t0 == NOW and g.t1 == NOW and g.buckets == ()


def test_floor_buckets_remainder_one_keeps_tail_bucket():
    """(fb_9)ceil 公式 —— t1-first ≡ 1 (mod interval) 时尾桶必须保留; `interval-1` 变异成
    `interval-2` 会少一个尾桶, 窗尾留 1 秒缺口"""
    assert _floor_buckets(100, 111, 10) == (100, 110)


def test_v4_totals_points_spread_threshold_exact_boundary():
    """(vtp_62)接缝摊配门槛 span > max(2w, 60) —— span 恰等门槛时不摊配, 恢复桶整段取
    delta; 变异成 `>=` 会把该 delta 摊回前位等值游程桶"""
    pts = (
        V4PointEntry(1000, 0, 0, 1000, 500, w=30),  # 锚点: 游程值建立
        V4PointEntry(1030, 0, 0, 1000, 500, w=30),  # 等值 z 形游程, span 60 == max(60, 60)
        V4PointEntry(1060, 1, 1, 1100, 500, w=30),  # 恢复桶: step 100 落本桶
    )
    out = v4_totals_points(pts)
    assert [(p.t, p.dl, p.up) for p in out] == [
        (1000, None, None),  # 窗首基线缺失
        (1030, 0, 0),  # 等值游程 delta=0
        (1060, 100, 0),  # 未触发摊配 -> 整段 delta 归恢复桶
    ]


def test_v4_rate_from_totals_zero_width_point_defensive():
    """(vrft_15/vrft_25)w=0 直构点的防御契约 —— `w <= 0` 速率派不出(None)而非除零;
    变异成 `w < 0` 会在 delta/w 处 ZeroDivisionError"""
    pts = (
        V4PointEntry(1000, 0, 0, 1000, 500, w=30),
        V4PointEntry(1030, 0, 0, 1050, 550, w=0),  # 零宽防御点
        V4PointEntry(1060, 1, 1, 1150, 650, w=30),
    )
    out = v4_rate_from_totals(pts)
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (1000, None, None),  # 窗首基线缺失
        (1030, None, None),  # w=0 -> 派不出(不除零)
        (1060, 2, 2),  # 摊配后 delta 50 / w 30 -> 2
    ]
    assert [(p.dl_total, p.up_total, p.w) for p in out] == [(1000, 500, 30), (1050, 550, 0), (1150, 650, 30)]
