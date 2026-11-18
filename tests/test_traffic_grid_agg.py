"""test_traffic_grid_agg 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; 26-11-15-1104 F2 点位归属归桶重锚 —— v4 面逐条改判, 改判理由随用例 docstring 与退役指针注释)

## 测试计划(每个测试函数一条)
- test_build_month_grid_all_view: all 视图数据面铺格 —— 首末月行间逐月铺桶(缺失月也在 = null 桶), 乱序/重复 epoch 取最小最大; 空集合 = 空 buckets 兜底栅格
(26-11-18-0037 T1c-2: 挂钟桶面退役 —— v4_series_points 桶点级用例逐条改判到
assemble_group_points 样本分组装配面, 桶键 -> 样本 ts, 期望值同源重推; agg 段窗用例不动)
- test_v4_point_assignment_zrun_spread_and_pause: (改判样本点层)z 游程均摊槽逐样本出点 + 冻结期台阶按真实跨度摊配(Sigma rate x cov = step 守恒); r 暂停整对端点归属恢复样本 —— 暂停区间无样本即无点(新契约: 缺口只在 n 游程/块间真空, dt 大步进 = 未采样非断连, 旧 R8 有界持有回填面随桶面退役)
- test_v4_mixed_interval_blocks_point_assignment: (改判)混排 interval 分块: 块 interval 只决定槽位 dt 链; 天然 gap 被 dt 链吸收不出伪真空
- test_v4_differential_reset_baseline_and_zchain: (改判)差分一次算定全边界 —— 重置逐向豁免/窗首 0 线/断连后停机洞 None/totals 真值/陈旧跨度摊配(Sigma = step 守恒)
- test_v4_same_bucket_merge_and_mixed_slots: (改判)同组多槽 -> k=1 逐样本点: z 对 delta 0/台阶真值逐样本出点(旧同桶合并面随桶面退役)
- test_v4_vacuum_and_disconnect_distinct: 真空/断连两语义分离(承袭, 显式空值点)
- test_v4_agg_obs_direct_mapping: (S3b)agg 行直映栅格桶(hour/day/month 同构)
- test_v4_earliest_row_ts_blocks_and_agg: (S3b)earliest 计入 day/month 行; 双空 = None
- test_bucket_delta_null_and_reset
- test_grid_for_now_wraps_build_grid: (T1c-2 改判)grid_for_now 窗界包装一致性(raw 桶面退役: 窗界/段/间隔直传)
- test_v4_agg_obs_live_merge_partial_and_residual
- test_v4_series_points_instantaneous_fields_not_used: (vsp_82 改判样本点层)瞬时速率字段不参与一次算定(垃圾值/零值零污染)
- test_build_month_grid_empty_meta_complete: (bmg_3)空月集兜底栅格 meta 仍齐全
- test_floor_buckets_remainder_one_keeps_tail_bucket: (fb_9)floor+1 进行中桶保留
- test_v4_series_points_spread_threshold_exact_boundary: (vtp_62 改判样本点层)摊配门槛 span 恰等 max(2 x 接收槽 dt, 60) 不摊配, 变异成 >= 会多摊一批
- test_grid_for_now_forwards_sample_interval: (mut-core W2 gfn_6)grid_for_now 转发 sample_interval
退役指针(旧中间层用例的去向, 旧名 -> 承接面):
  window_seed_and_baseline -> D3 种子语义由 web 种子用例 + grid 窗前链上下文用例承接;
  reset_per_direction_chain_unbroken -> up_channel 独立差分用例 + differential 用例承接;
  zchain_vacuum_null_passthrough -> differential/vacuum 用例承接;
  wide_bucket_byte_conservation -> seam/zrun 摊配 Σ(rate x cov) = step 断言承接;
  w1_bucket_rates -> 1s 桶差分用例承接;
  zero_width_point_defensive -> 同刻对跨 0 不进速率面(test_traffic_group_assembly::
  test_zero_coverage_pair_not_attributed + test_traffic_group_cache::
  test_fail_fast_guards_whitebox 承接; 26-11-18-0037 T1c-2: 原 grid same_timestamp
  用例已随挂钟桶面退役)。

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V4Block
(天文件文本路径经 format_v4_day_text -> parse_v4_day_text 打通解析接缝); V4Block 直构时
基线参数取 (0,0) 或首记录 totals —— 槽位数学与基线无关, 仅 format/parse roundtrip 路径
要求 delta 非负。
"""

import time

from auto_qb.core.traffic_grid import (
    BucketObs,
    MONTH_NOMINAL_S,
    build_grid,
    build_month_grid,
    grid_for_now,
    v4_agg_obs,
    v4_agg_obs_live,
    v4_earliest_row_ts,
    _bucket_delta,
    _floor_buckets,
    v4_series_slots,
)

from auto_qb.core.traffic_group_assembly import assemble_group_points

from auto_qb.core.traffic_store import (
    AggRow,
    V4Block,
    V4NullRun,
    V4ParsedAgg,
    V4Sample,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
    v4_month_epoch,
    v4_next_month_epoch,
)

from traffic_grid_support import NOW


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


def test_v4_point_assignment_zrun_spread_and_pause():
    """(改判样本点层, 原 D1 跨桶覆盖)z 游程按均摊槽展开逐样本出点 —— 每样本 rate 同值
    (0/摊配份额); 长 z 游程冻结期的台阶按真实发生跨度摊配到游程样本+恢复样本(span ==
    cov 全额, Sigma(rate x cov) = step 守恒); r 记录暂停(显式大 dt)整对端点归属恢复样本
    —— 暂停区间无样本即无点(新契约: 缺口只在 n 游程/块间真空, dt 大步进 = 未采样非断连;
    旧 R8 有界持有回填面随挂钟桶面退役, 26-11-18-0037 D2)"""
    b = V4Block(
        1000,
        30,
        100,
        200,
        (
            V4Sample(1, 1, 100, 200),  # @1000 锚点
            V4ZeroRun(4, 100, 200, dt_ms=160000),  # 均摊槽 @1040/1080/1120/1160(spacing 40)
            V4Sample(2, 2, 300, 400, dt_ms=40000),  # @1200(游程终点 1160 + 40)
        ),
    )
    res = assemble_group_points(v4_block_slots(b), 1000, 1250, 30)
    assert res.stride == 1
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None] == [
        (1000.0, 0, 0),  # 链首 0 线(@1000)
        (1040.0, 1, 1),  # z 槽: 摊配份额 40/40s = 1(冻结期台阶均摊, span == cov 全额)
        (1080.0, 1, 1),
        (1120.0, 1, 1),
        (1160.0, 1, 1),
        (1200.0, 1, 1),  # 接收样本 = 余额份额 40; Sigma(rate x cov) = 5 x 40 = 200 守恒
    ]
    assert not any(t is None for t in res.totals)  # 游程段全程非空值点(防伪洞)
    assert res.totals[-1] == {"t": 1200.0, "dl": 200, "up": 200}  # totals 面计数器真值(100 -> 300)
    # r 记录暂停: 2s 块内显式 dt=20s -> 差分对跨 20s 端点归属恢复样本; 暂停区间无样本 = 无点
    b2 = V4Block(
        2000,
        2,
        10,
        20,
        (
            V4Sample(5, 5, 10, 20),  # @2000 链首
            V4Sample(6, 6, 30, 60, dt_ms=20000),  # @2020(暂停 20s 如实入行)
            V4Sample(7, 7, 40, 80),  # @2022
        ),
    )
    res2 = assemble_group_points(v4_block_slots(b2), 2000, 2050, 2)
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res2.points, res2.totals) if t is not None] == [
        (2000.0, 0, 0),
        (2020.0, 1, 2),  # delta(20,40)/20s = 1/2(端点归属)
        (2022.0, 5, 10),  # delta(10,20)/2s
    ]
    assert not any(2000 < p["t"] < 2020 for p in res2.points)  # 暂停区间无样本即无点(未采样非断连)


def test_v4_mixed_interval_blocks_point_assignment():
    """(改判样本点层)混排 interval 分块(60s/2s/30s): 块 interval 只决定槽位 dt 链 ——
    各块槽位各归各样本点(t = 样本 ts); 块间 <=1 间隔的天然 gap(含 00:00 硬切)被 dt 链
    吸收(首槽声称覆盖接住前块游标终值), 不出伪真空空值点"""
    b1 = V4Block(1000, 60, 600, 1200, (V4Sample(1, 1, 600, 1200), V4Sample(2, 2, 1200, 2400)))  # @1000/@1060
    b2 = V4Block(1062, 2, 1800, 3610, (V4Sample(3, 3, 1800, 3610), V4Sample(4, 4, 1810, 3620)))  # @1062/@1064
    b3 = V4Block(1094, 30, 1870, 3800, (V4Sample(5, 5, 1870, 3800), ))  # @1094
    res = assemble_group_points(v4_series_slots((b3, b1, b2)), 1000, 1100, 2)  # 乱序传入
    assert res.stride == 1
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None] == [
        (1000.0, 0, 0),  # 链首 0 线
        (1060.0, 10, 20),  # delta(600,1200)/60s(60s 块槽位)
        (1062.0, 300, 605),  # 2s 块(gap 2s == 首槽 dt, 无真空); delta(600,1210)/2s
        (1064.0, 5, 5),
        (1094.0, 2, 6),  # 30s 块(gap 30s == 首槽 dt, 无真空)
    ]
    assert not any(t is None for t in res.totals[1:])  # 全程无伪真空空值点(首项基线缺失 None)


def test_v4_differential_reset_baseline_and_zchain():
    """(改判样本点层, 原累计段)差分一次算定全边界: cur<last 重置样本该向豁免(totals 逐向
    None, 速率面无缝 0 线)/ 窗首基线缺失 -> 0 线 / n 槽显式空值点断链后停机洞 None
    (totals 真值照记)/ z 游程快照冻结进差分链 —— 空闲段 delta=0 链不断, 恢复样本按陈旧
    跨度摊配(份额 60/30 覆盖毫秒比例, Sigma = step 守恒)"""
    b1 = V4Block(
        1000,
        30,
        1000,
        500,
        (
            V4Sample(10, 10, 1000, 500),  # @1000 链首
            V4Sample(10, 10, 1800, 400),  # @1030: dl +800; up 400<500 重置 -> 豁免
            V4Sample(10, 10, 2000, 600),  # @1060: +200/+200(对重置快照差分)
            V4NullRun(2, dt_ms=61000),  # n 槽 @1090.5/1121.0 -> 空值点 1090(断连)
            V4Sample(10, 10, 2100, 700, dt_ms=30000),  # @1151(n 终点 1121+30)
            V4Sample(10, 10, 2200, 800),  # @1181: +100/+100
        ),
    )
    b2 = V4Block(
        5000,
        30,
        1000,
        500,
        (
            V4Sample(10, 10, 1000, 500),  # @5000(真空断链后)
            V4ZeroRun(3, 1000, 500),  # 槽 @5030/5060/5090(快照恒定)
            V4Sample(10, 10, 1240, 620, dt_ms=30000),  # @5120: dl +240 / up +120(整除构造)
        ),
    )
    res = assemble_group_points(v4_series_slots((b1, b2)), 1000, 5200, 30)
    assert res.stride == 1
    real = [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None]
    assert real == [
        (1000.0, 0, 0),  # 窗首基线缺失 -> 0 线(D4)
        (1030.0, 27, 0),  # dl 800/30s = 26.7 -> 27; up 重置 -> 0 线(无缝)
        (1060.0, 7, 7),  # 对重置快照差分 +200/+200 -> 6.7 -> 7(链不断)
        (1151.0, None, None),  # 断链后未观测 61s > 60s 停机洞 -> None(totals 真值)
        (1181.0, 3, 3),  # 基线恢复 +100/+100
        (5000.0, None, None),  # 真空断链后基线缺失(重置: 快照 1000/500 < 前快照 -> totals 逐向 None)
        (5030.0, 2, 1),  # 陈旧跨度摊配份额 60/30 -> rate 2/1(游程样本均匀平线)
        (5060.0, 2, 1),
        (5090.0, 2, 1),
        (5120.0, 2, 1),  # 接收样本 = 余额 60/30(span == cov 全额守恒)
    ]
    assert [p["t"] for p, t in zip(res.points, res.totals) if t is None] == [1090, 1181]  # n 断连 + 真空两空值点
    dl_shares = [p["dl"] * 30 for p, t in zip(res.points, res.totals) if t is not None and 5030 <= p["t"] <= 5120]
    up_shares = [p["up"] * 30 for p, t in zip(res.points, res.totals) if t is not None and 5030 <= p["t"] <= 5120]
    assert sum(dl_shares) == 240 and sum(up_shares) == 120  # Sigma = step 守恒(整除构造)
    tot_b1 = [t for p, t in zip(res.points, res.totals) if t is not None and p["t"] < 2000]
    assert tot_b1[1] == {"t": 1030.0, "dl": 800, "up": None}  # up 重置 -> 逐向 None(dl 真值)
    assert tot_b1[3] == {"t": 1151.0, "dl": 100, "up": 100}  # 洞后 totals 真值(跨洞快照差分)


def test_v4_same_bucket_merge_and_mixed_slots():
    """(改判样本点层)同组多槽 -> k=1 逐样本点: 差分面逐对入账(z 对 delta 0 / raw 台阶
    真值 —— 旧「同桶合并 + 快照 ts 最晚者」的桶面随挂钟桶面退役, 快照竞争判据由装配面
    「组末样本 ts/末样本快照」自然承载, 详见 test_traffic_grid_grid 端到端用例)"""
    b = V4Block(
        1000,
        1,
        10,
        20,
        (
            V4Sample(1, 1, 10, 20),  # @1000.0 链首
            V4ZeroRun(1, 10, 20, dt_ms=500),  # z @1000.5: delta 0(快照冻结)
            V4Sample(2, 2, 30, 40, dt_ms=500),  # @1001.0: 台阶
            V4Sample(30, 40, 300, 400, dt_ms=500),  # @1001.5
            V4Sample(50, 60, 400, 500, dt_ms=500),  # @1002.0
        ),
    )
    res = assemble_group_points(v4_block_slots(b), 1000, 1010, 1)
    assert res.stride == 1
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None] == [
        (1000.0, 0, 0),  # 链首 + z 对前无差分: 0 线
        (1000.5, 0, 0),  # z 槽: 快照冻结 -> delta 0
        (1001.0, 40, 40),  # z->raw 台阶 20/0.5s
        (1001.5, 540, 720),  # delta(270,360)/0.5s
        (1002.0, 200, 200),  # delta(100,100)/0.5s
    ]


def test_v4_vacuum_and_disconnect_distinct():
    """真空/断连两语义分离(验收, 承袭; 显式空值点形态): 块内 n 游程 -> 连续 null 槽折叠
    单个空值点(首槽位置取整); 块间 gap -> 一个真空空值点(t = 前块游标终值); 连续块(gap
    被首槽声称覆盖吸收)不出空值点 —— 两者各司其职互不误报"""
    b1 = V4Block(1000, 30, 1, 1, (V4Sample(1, 1, 1, 1), V4NullRun(3)))  # r @1000; n 槽 @1030/1060/1090
    b2 = V4Block(5000, 30, 2, 2, (V4Sample(2, 2, 2, 2), ))  # 停机后新块(真空)
    b3 = V4Block(5030, 30, 3, 3, (V4Sample(3, 3, 3, 3), ))  # 连续采样接续(无真空)
    res = assemble_group_points(v4_series_slots((b1, b2, b3)), 1000, 5100, 30)
    assert res.stride == 1
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None] == [
        (1000.0, 0, 0),  # 链首 0 线(@1000)
        (5000.0, None, None),  # @5000: 停机洞断链 None(totals 真值 1/1)
        (5030.0, 0, 0),  # @5030: b2->b3 gap 30s == 首槽 dt 被吸收, 无空值点
    ]
    assert [p["t"] for p, t in zip(res.points, res.totals) if t is None] == [1030, 1090]  # 恰两个空值点: 断连 + 真空
    assert not any(1090 < p["t"] < 5000 for p in res.points)  # 真空段无任何样本点


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


# test_v4_rate_from_totals_window_seed_and_baseline 已随 v4_rate_from_totals 退役(F2):
# D3 窗首种子语义(窗前样本作差分基线, 窗首样本速率 = 差分/覆盖 非 0 线)由
# test_web_traffic_qb::test_api_traffic_qb_raw_seed_extension_window_start_baseline 与
# test_traffic_group_assembly::test_window_filter_and_seed_baseline +
# test_traffic_grid_grid::test_window_filter_tail_and_empty_assembly 承接
# (26-11-18-0037 T1c-2: 原 grid 承接名 test_v4_series_points_pre_window_chain_context_
# filtered_from_obs 已随挂钟桶面退役)。

# test_v4_rate_from_totals_reset_per_direction_chain_unbroken 已随 v4_rate_from_totals 退役
# (F2): 重置逐向豁免 + 链推进独立于速率可派由 test_traffic_group_assembly::
# test_reset_and_hole_semantics(重置逐向/洞后基线)与
# test_v4_differential_reset_baseline_and_zchain(重置桶后继有基线)承接
# (26-11-18-0037 T1c-2: 原 grid 承接名 test_v4_series_points_up_channel_independent_
# differential 已随挂钟桶面退役)。

# test_v4_rate_from_totals_zchain_vacuum_null_passthrough 已随 v4_rate_from_totals 退役(F2):
# z 链 0 线续链 / 真空断连 null 透传 / 断链后基线缺失由 test_v4_differential_reset_baseline_
# and_zchain 与 test_v4_vacuum_and_disconnect_distinct 承接。

# test_v4_rate_from_totals_wide_bucket_byte_conservation 已随 v4_rate_from_totals 退役(F2):
# 速率 x 覆盖 = delta 的字节守恒在摊配面由 test_v4_seam_spread_live_tail_restart_no_spike
# / test_v4_point_assignment_zrun_spread_and_pause 的 Σ(rate x cov) = step_w 断言承接。

# test_v4_hold_slot_honest_fallbacks 已随持有面退役(26-11-18-0037 D2/T1c-2 —— F4 holding
# 桶点与 is_hold 旗不复存在): 诚实回退三态的语义承接 —— 链首/断口/重置后速率派不出 ->
# 组值 None 不造速率, 由 test_traffic_group_assembly::test_reset_and_hole_semantics
# (重置/停机洞 None)与 test_traffic_grid_grid::test_disconnect_n_run_explicit_null_endpoint
# (null 断口后无克隆)承接。


def test_grid_for_now_wraps_build_grid():
    """grid_for_now = build_grid 的现在时包装(API 层入口): 同一窗口/间隔/段, t1 取调用时刻
    (两次调用秒级差 <= 2s; 26-11-18-0037 T1c-2 后 raw 段 = 窗界载体: interval = si 直传,
    buckets 恒空 —— 旧 F1 桶宽 180 断言随挂钟桶面退役)"""
    g = grid_for_now("24h", 30)
    ref = build_grid("24h", time.time(), 30)
    assert g.name == ref.name == "24h" and g.interval == ref.interval == 30 and g.segment == ref.segment
    assert g.buckets == () and abs(g.t1 - ref.t1) <= 2


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


# test_v4_rate_from_totals_w1_bucket_rates 已随 v4_rate_from_totals 重写层退役(F2 一次算定):
# 「1s 桶速率照常派出」守阵由槽层电池承接(同桶差分对跨 1s -> rate = delta/1s, 见
# test_v4_same_bucket_merge_and_mixed_slots 的 1s 桶; None 不丢由差分豁免电池钉)。


def test_v4_series_points_instantaneous_fields_not_used():
    """(vsp_82 改判样本点层)瞬时速率字段不参与一次算定 —— 逐样本速率 = 差分 / 覆盖时长,
    与 obs 前两列(qB 瞬时直采)无关: 字段垃圾值/零值不污染样本速率(变异成读 obs[0..1]
    会在均值处显形)。旧 is_raw 旗均值支随 cell 几何退役。"""
    b = V4Block(
        1000,
        1,
        10,
        20,
        (
            V4Sample(9999, 9999, 10, 20),  # @1000.0 链首(瞬时字段垃圾)
            V4Sample(9999, 0, 30, 40, dt_ms=1200),  # @1001.2
            V4Sample(0, 9999, 50, 60, dt_ms=400),  # @1001.6(首条 dl 速率 0)
        ),
    )
    res = assemble_group_points(v4_block_slots(b), 1000, 1010, 1)
    assert res.stride == 1
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None] == [
        (1000.0, 0, 0),
        (1001.2, 17, 17),  # delta(20,20)/1.2s = 16.7 -> 17(瞬时字段 9999/0 零参与)
        (1001.6, 50, 50),  # delta(20,20)/0.4s
    ]


def test_build_month_grid_empty_meta_complete():
    """(bmg_3, 顺手 bmg_6/_7/_8/_10/_18/_19/_20/_21)空月集兜底栅格 meta 仍齐全(name/
    segment/interval/t0/t1/buckets) —— 下游 traffic_qb 直消费 grid 字段, 任一失守即空态面破"""
    g = build_month_grid((), NOW)
    assert g.name == "all" and g.segment == "month" and g.interval == MONTH_NOMINAL_S
    assert g.t0 == NOW and g.t1 == NOW and g.buckets == ()


def test_floor_buckets_remainder_one_keeps_tail_bucket():
    """(fb_9)floor+1 公式(26-11-14-1313 F3 反转 R07 ceil 口径, 反转理由见 _floor_buckets
    docstring) —— t1-first ≡ 1 (mod interval) 时进行中桶必须保留; `+ 1` 丢失(退化成 floor)
    会少一个尾桶, 窗尾留 1 秒缺口"""
    assert _floor_buckets(100, 111, 10) == (100, 110)


def test_v4_series_points_spread_threshold_exact_boundary():
    """(vtp_62 改判样本点层)接缝摊配门槛 span > max(2 x 接收槽 dt, 60s) —— span 恰等门槛
    时不摊配, 恢复样本整段取 delta; 变异成 `>=` 会把该 delta 摊回前位等值游程样本"""
    blk = V4Block(
        1000,
        30,
        1000,
        500,
        (
            V4Sample(0, 0, 1000, 500),  # 锚点: 游程值建立
            V4ZeroRun(1, 1000, 500),  # 等值 z 形游程 1 槽, span 60 == max(2 x 30, 60)
            V4Sample(1, 1, 1100, 500, dt_ms=30000),  # 恢复样本: step 100 落本样本
        ),
    )
    res = assemble_group_points(v4_block_slots(blk), 1000, 1200, 30)
    assert res.stride == 1
    assert [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None] == [
        (1000.0, 0, 0),  # 窗首基线缺失 -> 0 线
        (1030.0, 0, 0),  # 等值游程 delta=0
        (1060.0, 3, 0),  # 未触发摊配 -> 整段 delta 归恢复样本(dl 100/30s = 3; up 0)
    ]
