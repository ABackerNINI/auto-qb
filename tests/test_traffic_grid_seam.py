"""test_traffic_grid_seam 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; 26-11-15-1104 F2 点位归属归桶重锚 —— 接缝判读承袭, 摊配面平移到槽层一次算定, 逐条改判理由随用例 docstring)

## 测试计划(每个测试函数一条)
- test_v4_series_slots_seam: S3b 接缝 —— v4_series_slots 稳定排序展平
- test_v4_seam_spread_live_tail_restart_no_spike: (P2; F2 桶层改判)活尾缝摊配 —— 磁盘长 z 形等值游程 + 活尾新鲜快照: 接缝差按真实跨度摊配(span == cov 全额), 接收桶无单桶尖峰, 游程桶+接收桶均匀平线, Σ(rate x cov) = step_w 守恒; 缝内栅格桶仍无观测(G2/E2E3)
- test_v4_seam_spread_disk_vacuum_recovers_delta: (P2; F2)磁盘缝摊配 —— 真空标记 present 但缝 <= 60s 时台阶跨标记按真实跨度摊配回收, 标记桶仍 null
- test_v4_seam_hole_over_threshold_drops_delta: (P2 诚实兜底)观测缝 > 60s = 停机洞: delta=None 断链不摊配(活尾长缝与块间真空两形态同判; w=0 断链 None 观测桶有 totals 不混入标记列)
- test_v4_seam_below_threshold_unchanged: (P2 边界; F2)块内短游程仍单桶归因; 块界重启缝摊配回收 —— F2 端点归属下 span == cov 恒成立(差分对跨即覆盖), 旧 ceil 缩口的「未覆盖秒丢弃」消失(缝内字节仍在 totals 链, 全额回收更诚实)
- test_v4_seam_flat_r_run_not_spread: (P2 反例守阵, F2 槽层改判)真 flat-r 游程不摊配 —— z 形签名(速率双零)是摊配必要条件
- test_v4_seam_constants_frozen: (P2 守阵)阈值常量冻结(摊配下限/洞阈值各 60s)
- test_v4_seam_short_gap_two_paths_agree_no_spike: (issue 26-10-16-0954 守阵; F2)短缝接收桶 rate = step/实测对跨; 磁盘与活尾两路径同几何同值; 近洞 60s 缝仍不放大; 缝内栅格桶仍 null
- test_v4_seam_spread_midrun_seam_then_step_uniform: (评审轮1 #1 回归守阵)缝在等值游程中段 + 后接台阶 —— cov = 逐对「对跨 - 未观测秒」合计使 span > cov 恒有效(不依赖 marked 存活), 台阶均摊平线不出单桶尖峰(误接 131 B/s 可判红)
- test_v4_seam_covered_span_mark_two_paths_agree: (残余边界修复轮; F2)覆盖连续且带块界真空标记的缝 —— 两路径同判同值; F2 下锚点 r 槽与首枚 z 槽同桶(份额与锚点差分合并, ±1 样本份额级, R2 口径); 守恒按 round 取整容差
- test_v4_seam_marked_r_run_drops_delta: (P2 提取件半分支守阵, 26-11-18-0037 评审 #10)r 形等值游程(非 z 签名)+ n 断连标记 + 台阶 —— all(z) 不成立且 marked 存活 -> 差分 None 断链, 接收桶速率 None 非 0 线(诚实丢字节)

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
    v4_series_points,
    v4_series_slots,
    _V4_SEAM_LOOKBACK_S,
    _V4_SEAM_NULL_S,
    _V4_SEAM_SPREAD_MIN_S,
    _bucket_delta,
    _floor_buckets,
)

from traffic_grid_support import _p

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


def test_v4_seam_spread_live_tail_restart_no_spike():
    """(P2 主形态, F2 桶层改判)活尾缝摊配: 磁盘链长 z 形等值游程(快照冻结)+ 活尾开放
    z 游程(新鲜快照 F0)—— 接缝差按**真实发生跨度**摊配(span == cov: F2 端点归属下差分
    对跨即覆盖, 不再按 ceil 桶宽缩放), 接收桶无单桶尖峰, 游程桶+接收桶均匀 step_w/cov
    平线, 逐桶 Σ(rate x cov) = step_w 覆盖份额守恒(整除构造); 无观测缝栅格桶仍无观测
    (摊配不凭空造非 null 桶, G2/E2E3)"""
    interval = 2
    disk = V4Block(
        1000,
        interval,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)),
    )  # z 游程 60 槽 x 2s = 120s, 快照冻结 (1000,500); 末槽 @1120 -> 桶 1120
    # 活尾 = 重启后开放 z 游程(head_pending 无落盘记录): F0 = 冻结期真实增长 +262/+131
    run = LiveTailRun(kind="z", start=1129.0, last_seen=1141.0, dl_total=1262, up_total=631, samples=6)
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1129,
        interval_s=interval,
        projected_ts=1129.0,
        records=(),
        open_run=run,
    )
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    points = v4_series_points((disk, ), g, tail_slots=v4_live_tail_slots(tail))
    # 1 r 点 + 60 游程桶 + 1 活尾缝真空标记 + 6 活尾桶(残余边界修复轮: 活尾同判块间真空,
    # 磁盘链末槽 @1120 与活尾首槽 1131 之间有未观测段 -> 出与磁盘路径同位的 null 标记)
    assert len(points) == 68
    assert [p.t for p in points if p.dl_rate is None and p.w == 0] == [1120]
    spread = [p for p in points if p.w > 0]  # 链首桶(1000, w=0)不入 spread
    # 摊配(评审轮1 #1 修复后口径): cov = 逐对「对跨 - 未观测秒」= 60 x 2s + 接收对声称
    # 覆盖 2s = 122s < span 131s(活尾缝 9s 不归因)-> step_w = 262 x 122 // 131 = 244;
    # 份额 (4,2) 均匀, 余额归接收桶 —— 均摊平线无尖峰
    assert all(p.dl_rate == 2 and p.up_rate == 1 for p in spread[0:60])  # 游程 60 桶
    assert (spread[60].t, spread[60].dl_rate, spread[60].up_rate) == (1130, 2, 1)  # 接收桶平线
    assert all(p.dl_rate == 0 and p.up_rate == 0 for p in spread[61:])  # 接收桶之后等值延续 delta=0
    head = next(p for p in points if p.t == 1000)
    assert (head.dl_rate, head.up_rate, head.w) == (0, 0, 0.0)  # 链首 0 线(D4)
    assert sum(p.dl_rate * p.w for p in spread[0:61]) == 244  # 覆盖份额守恒(step x cov // span)
    assert sum(p.up_rate * p.w for p in spread[0:61]) == 122
    # 栅格诚实性: 无观测缝(1122..1128)栅格桶无观测; 接收覆盖 [1129,1131) -> 桶 1130
    obs = v4_grid_obs(points, g)
    assert all(b not in obs for b in (1122, 1124, 1126, 1128))  # 缝内桶仍 null(不凭空造数据)
    assert obs[1130].dl_rate == 2 and obs[1130].dl_total == 1262


def test_v4_seam_spread_disk_vacuum_recovers_delta():
    """(P2, F2 桶层改判)磁盘缝摊配: 块间真空 null 标记 present(渲染断线)但缝 <= 60s 时
    台阶跨标记按真实跨度摊配回收 —— span == cov(F2 差分对跨即覆盖)下全额回收, 标记桶
    自身仍 null(摊配不凭空造数据)"""
    b1 = V4Block(
        1000,
        2,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)),
    )
    b2 = V4Block(1129, 2, 1258, 629, (V4Sample(9, 9, 1258, 629), ))  # 重启后新块(封口形态)
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    points = v4_series_points((b1, b2), g)
    assert any(p.t == 1120 and p.dl_rate is None for p in points)  # 真空标记 present @1120
    marks = [p for p in points if p.dl_rate is None and p.up_rate is None and p.w == 0]
    assert [p.t for p in marks] == [1120]  # 恰一个 null 点(标记)
    spread = [p for p in points if p.w > 0]  # 链首桶(1000, w=0)不入 spread
    assert all(p.dl_rate == 2 and p.up_rate == 1 for p in spread)  # 游程+接收桶均匀平线
    # 跨缝回收: cov = 122s < span 129s(缝 7s 不归因)-> Σ = step x cov // span = 244
    assert sum(p.dl_rate * p.w for p in spread) == 244
    assert sum(p.up_rate * p.w for p in spread) == 122


def test_v4_seam_hole_over_threshold_drops_delta():
    """(P2 诚实兜底)观测缝 > _V4_SEAM_NULL_S(60s)= 停机洞: delta=None 断链, 不摊配
    不回收(E2E3: 停机洞不被摊配填成伪值); 活尾长缝与块间真空两形态同判(残余边界修复轮后
    活尾首槽同样出真空标记 —— 不因路径不同而摇摆)"""
    disk = V4Block(
        1000,
        2,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)),
    )
    # 活尾长缝: 进程停机 300s 后重启采样(B.start=1429), 开放游程 150 样本 x 2s;
    # 首活尾槽 @1431 -> 未观测 309s > 60s(洞; 游程均摊不吸收停机段)
    run = LiveTailRun(kind="z", start=1429.0, last_seen=1729.0, dl_total=1244, up_total=622, samples=150)
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1429,
        interval_s=2,
        projected_ts=1429.0,
        records=(),
        open_run=run,
    )
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    points = v4_series_points((disk, ), g, tail_slots=v4_live_tail_slots(tail))
    assert [p.t for p in points if p.dl_rate is None and p.w == 0 and p.dl_total is None] == [
        1120
    ]  # 活尾缝同判真空(磁盘链末槽; 断链 None 观测桶有 totals 不入列)
    z_part = [p for p in points if p.w > 0 and 1002 <= p.t <= 1120]
    assert all(p.dl_rate == 0 and p.up_rate == 0 for p in z_part)  # 游程桶不摊配(0 线照旧)
    recv = next(p for p in points if p.t == 1430)
    assert recv.dl_rate is None and recv.up_rate is None  # 洞后接收桶断链 None(快照照记)
    assert (recv.dl_total, recv.up_total) == (1244, 622)
    # 块间真空长缝: 新块首槽 @1183 -> 未观测 61s > 60s
    b2 = V4Block(1183, 2, 1244, 622, (V4Sample(9, 9, 1244, 622), ))
    points2 = v4_series_points((disk, b2), g)
    assert any(p.t == 1120 and p.dl_rate is None and p.dl_total is None for p in points2)  # 真空标记 present
    recv2 = next(p for p in points2 if p.t == 1182)
    assert recv2.dl_rate is None and recv2.up_rate is None  # 洞后断链, 不摊配


def test_v4_seam_below_threshold_unchanged():
    """(P2 边界, F2 桶层改判)块内短游程(无标记、全覆盖)行为承袭 —— span == cov 且
    span <= max(2 x 接收槽 dt, 60s) 时恢复桶仍单桶归因; 块界重启缝(有 null 标记)按真实
    跨度摊配回收(F2 端点归属下 span == cov 恒成立: 差分对跨即覆盖, 旧「未覆盖秒丢弃」
    的 ceil 缩口随之消失 —— 缝内字节仍在 totals 链, 全额回收更诚实)"""
    # 块内短游程(2 槽 4s)+ 邻接恢复: span == cov -> 恢复桶单桶归因(承袭)
    b = V4Block(
        2000,
        2,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=4000), V4Sample(2, 2, 1020, 510, dt_ms=5000)),
    )
    g = WindowGrid("5m", 1990, 3000, 2, "raw", _floor_buckets(1990, 3000, 2))
    points = v4_series_points((b, ), g)
    assert [_p(p) for p in points] == [
        (2000, 0, 0, 1000, 500, 0.0),  # 链首 0 线
        (2002, 0, 0, 1000, 500, 2.0),  # z 槽(delta 0)
        (2004, 0, 0, 1000, 500, 2.0),
        (2008, 4, 2, 1020, 510, 5.0),  # 恢复桶 delta(20,10)/5s 单桶归因(端点归属 @2009 所在格)
    ]
    # 有标记短缝(块间 gap 1s, span == cov 7s): 全额摊回游程桶 + 接收桶
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=4000)))
    b2 = V4Block(1007, 2, 1020, 510, (V4Sample(9, 9, 1020, 510), ))
    g2 = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    points2 = v4_series_points((b1, b2), g2)
    assert [_p(p) for p in points2] == [
        (1000, 0, 0, 1000, 500, 0.0),
        (1002, 2, 1, 1000, 500, 2.0),  # 摊配份额 5/2(cum=2s -> target=5)
        (1004, None, None, None, None, 0.0),  # 真空标记仍 null(同刻排观测前)
        (1004, 3, 2, 1000, 500, 2.0),  # 摊配份额 6/3(cum=4s -> target=11)
        (1006, 3, 2, 1020, 510, 2.0),  # 接收桶 = 余额 6/2s(覆盖 = 声称 dt; 修复前: 断链 None)
    ]
    dl_deltas = [p.dl_rate * p.w for p in points2 if p.w > 0]
    up_deltas = [p.up_rate * p.w for p in points2 if p.w > 0]
    # 覆盖份额守恒: cov = 6s < span 7s(缝 1s 不归因)-> Σ = step x cov // span = 17/8
    # (round 取整损失逐桶 <= w/2, 界取 Σw/2 = 3)
    assert abs(sum(dl_deltas) - 17) <= 3 and abs(sum(up_deltas) - 8) <= 3


def test_v4_seam_flat_r_run_not_spread():
    """(P2 反例守阵, F2 槽层改判)非 z 形等值游程(r 记录、上行速率非零、dl totals 真 flat)
    不摊配: 游程 delta 恒 0, 台阶按接收桶单桶归因 —— z 形签名(速率双零)是摊配必要条件,
    防「真 flat + 一次真实增长」被错误摊平稀释"""
    blk = V4Block(
        1000,
        30,
        1000,
        500,
        (
            V4Sample(0, 5, 1000, 500),  # 锚点
            V4Sample(0, 5, 1000, 560, dt_ms=31000),  # 等值 r 游程(rate 非零 -> 非 z 形)
            V4Sample(0, 5, 1000, 620, dt_ms=31000),
            V4Sample(3, 5, 1100, 680, dt_ms=31000),  # dl 台阶 +100(span 124s > max(2dt, 60s) 达门槛)
        ),
    )
    g = WindowGrid("5m", 900, 2000, 30, "raw", _floor_buckets(900, 2000, 30))
    points = v4_series_points((blk, ), g)
    assert [_p(p) for p in points] == [
        (990, 0, 0, 1000, 500, 0.0),  # 链首 0 线
        (1020, 0, 2, 1000, 560, 31.0),  # dl 游程 0 线 / up 60/31s = 2(区间平均)
        (1050, 0, 2, 1000, 620, 31.0),
        (1080, 3, 2, 1100, 680, 31.0),  # 接收桶 dl delta(100)/31s 单桶归因(未摊配)
    ]


def test_v4_seam_constants_frozen():
    """(P2 守阵)阈值常量冻结(计划默认: 摊配下限 60s / 洞阈值 60s, 模块常量非配置键)
    —— 无意漂移即红; 调整阈值须同步本用例与计划 §07 拍板项"""
    assert _V4_SEAM_SPREAD_MIN_S == 60
    assert _V4_SEAM_NULL_S == 60


def test_v4_seam_short_gap_two_paths_agree_no_spike():
    """(issue 26-10-16-0954-bug-traffic-seam-short-gap-spike 守阵, F2 桶层改判)重启缝 <= 60s:
    接缝差不再整块落进接收桶按自身桶宽放大 —— 接收桶 rate = step / 实测对跨, 且**磁盘路径
    (真空标记)与活尾路径(无标记)同几何取值逐位一致**。几何取自运行实例 08:16 重启证据行
    (旧块末样 @1792109749 -> 新块首样 @1792109766, 接缝差 up 2,496,825, 修复前
    1,248,412 B/s = 8.5 倍放大)"""
    old_base = (3782833206353, 1897547120090)
    old_last = (3782833389364, 1897550615935)  # 旧块末样(增量 +183011/+3495845)
    new_base = (3782833517685, 1897553112760)
    old = V4Block(1792109749, 1.5, old_base[0], old_base[1], (V4Sample(0, 67307, old_last[0], old_last[1]), ))
    new = V4Block(
        1792109766,
        1.5,
        new_base[0],
        new_base[1],
        (
            V4Sample(0, 270269, new_base[0], new_base[1]),  # 首采 delta 全 0(块基线立点)
            V4ZeroRun(1, new_base[0] + 341664, new_base[1] + 6754972, dt_ms=54356),  # 单槽长游程
            V4Sample(0, 185691, new_base[0] + 354684, new_base[1] + 7047279),
        ),
    )
    g = WindowGrid("5m", 1792109700, 1792109900, 1.5, "raw", _floor_buckets(1792109700, 1792109900, 1.5))
    out_disk = v4_series_points((old, new), g)
    assert [p.t for p in out_disk if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1792109749]
    recv = next(p for p in out_disk if p.t == 1792109766)  # 缝后首桶(端点归属 @9766 所在格)
    # 覆盖 = 接收槽声称 dt 1.5s: step_w = step x 1.5 // 17 -> rate = step/17(误接 320 可判红)
    assert (recv.dl_rate, recv.up_rate) == (7548, 146872)
    assert abs(recv.dl_rate * recv.w - 128321 * 1.5 / 17) <= recv.w / 2  # 覆盖份额 = step x cov // span
    # 活尾路径同几何(旧块 + 新块整块未落盘): 块间真空同判 -> 同一标记、同一取值
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1792109766,
        interval_s=1.5,
        projected_ts=1792109766.0,
        records=new.records,
        open_run=None,
    )
    out_tail = v4_series_points((old, ), g, tail_slots=v4_live_tail_slots(tail))
    assert [p.t for p in out_tail if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1792109749]
    recv_tail = next(p for p in out_tail if p.t == 1792109766)
    assert (recv_tail.dl_rate, recv_tail.up_rate) == (recv.dl_rate, recv.up_rate)  # 两路径同值
    # 近洞长缝(未观测恰 60s, 未超阈值): 修复前是反直觉的最强放大形态(越接近洞越放大)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), ))
    b2 = V4Block(1062, 2, 7200, 5100, (V4Sample(9, 9, 7200, 5100), ))  # 首样 @1062 -> 未观测 60s
    g2 = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    out3 = v4_series_points((b1, b2), g2)
    recv3 = next(p for p in out3 if p.t == 1062)
    assert (recv3.dl_rate, recv3.up_rate, recv3.w) == (
        100, 74, 2.0
    )  # 覆盖 = 声称 dt 2s: step_w = 6200 x 2 // 62 = 200 -> rate 100(修复前 3100, 31 倍)
    # 缝内栅格桶仍无观测(摊配不凭空造非 null 桶, G2/E2E3)
    obs3 = v4_grid_obs(out3, g2)
    assert all(b not in obs3 for b in (1002, 1020, 1058))


def test_v4_seam_covered_span_mark_two_paths_agree():
    """(issue 26-10-16-0954 残余边界修复轮, F2 桶层改判)覆盖连续且带块界真空标记的缝:
    唯一缝信号是块界真空标记 —— 活尾与磁盘块同判块间真空, 两路径同一标记同一取值。
    F2 端点归属下锚点 r 槽与首枚 z 槽同桶(1000): 摊配份额入锚桶(与锚点自身差分合并
    —— ±1 样本份额级差异, R2 口径), 接收桶 rate = 余额/实测对跨 2.1s。"""
    # 覆盖连续: 种子块末槽 @1003.9, 恢复块首槽 @1006 -> 未观测 0.1s(缝信号 = 真空标记)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=3900)))
    b2 = V4Block(1006, 2, 1200, 600, (V4Sample(9, 9, 1200, 600), ))
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    out_disk = v4_series_points((b1, b2), g)
    assert [p.t for p in out_disk if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1003]
    recv = next(p for p in out_disk if p.t == 1006)
    # 覆盖 = 接收槽声称 dt 2s: step_w = 200 x 5.9 // 6 = 196 -> 余额 67/2s = 34(未覆盖 0.1s 不归因)
    assert (recv.dl_rate, recv.up_rate, recv.w) == (34, 17, 2.0)
    # 活尾路径同几何(新块整块未落盘): 同标记同值
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1006,
        interval_s=2,
        projected_ts=1006.0,
        records=b2.records,
        open_run=None,
    )
    out_tail = v4_series_points((b1, ), g, tail_slots=v4_live_tail_slots(tail))
    assert [p.t for p in out_tail if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1003]
    recv_tail = next(p for p in out_tail if p.t == 1006)
    assert (recv_tail.dl_rate, recv_tail.up_rate) == (recv.dl_rate, recv.up_rate)
    # 覆盖份额守恒(cov 5.9s < span 6s -> 基准 = step x cov // span): Σ = 196/98(未覆盖 0.1s 不归因)
    dl_sum = sum(p.dl_rate * p.w for p in out_disk if p.w > 0 and p.t >= 1000)
    up_sum = sum(p.up_rate * p.w for p in out_disk if p.w > 0 and p.t >= 1000)
    assert abs(dl_sum - 196) <= 2 and abs(up_sum - 98) <= 2  # 守恒(round 取整损失 <= Σw/2)


def test_v4_seam_spread_midrun_seam_then_step_uniform():
    """(评审轮1 #1 回归守阵)缝在等值游程中段 + 后接台阶 —— 摊配判据 span > cov 必须命中:
    cov = 逐对「对跨 - 未观测秒」合计(缝秒不进分母), 不依赖 marked 存活(等值续槽会清零
    marked)—— 台阶均摊到游程桶 + 接收桶出平线, 不出单桶尖峰(修复前覆盖按对跨累计使
    span == cov 恒真、marked 已清零, 三支判据全不命中, 262 台阶整段落接收桶出 131 B/s
    尖峰, 复现 issue 26-10-16-0954 已修复形态)"""
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(10, 1000, 500, dt_ms=20000)))
    # 块间真空(缝 22s)后等值 z 游程续段(快照仍冻结 1000)+ 恢复台阶 262
    b2 = V4Block(1040, 2, 1000, 500, (V4ZeroRun(10, 1000, 500, dt_ms=20000), V4Sample(9, 9, 1262, 631, dt_ms=20000)))
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    points = v4_series_points((b1, b2), g)
    # 真空标记 @1020(缝起点); 缝内栅格桶(1022..1040)无观测 = null
    assert [p.t for p in points if p.dl_rate is None and p.w == 0 and p.dl_total is None] == [1020]
    obs = v4_grid_obs(points, g)
    assert all(b not in obs for b in (1022, 1024, 1026, 1028, 1030, 1032, 1034, 1036, 1038))
    assert 1040 in obs  # 缝后等值续段首槽(@1040 块首)落格 1040: 空闲 0 份额带内
    # 均摊线: 游程桶(1002..1020)+ 接收桶(1080)速率全部落在份额带 [3, 4]
    # (尖峰形态 = 接收桶 131 B/s, 判别力充分)
    spread = [p for p in points if p.w > 0 and p.t >= 1002]
    assert spread and all(3 <= p.dl_rate <= 4 and 1 <= p.up_rate <= 2
                          for p in spread), [(p.t, p.dl_rate) for p in spread]
    recv = next(p for p in points if p.t == 1080)
    run_rates = [p.dl_rate for p in spread if p.t <= 1020]
    assert abs(recv.dl_rate - sum(run_rates) / len(run_rates)) <= 1  # 接收桶与游程桶同处均摊带
    # 覆盖份额守恒: cov = 62.2s(游程对覆盖 + 接收槽声称 dt 20s)< span 80s(缝 17.8s 不归因)
    # -> Σ = step x cov // span = 262 x 62220 // 80000 = 203(round 取整损失 <= Σw/2)
    dl_sum = sum(p.dl_rate * p.w for p in spread)
    up_sum = sum(p.up_rate * p.w for p in spread)
    assert abs(dl_sum - 203) <= sum(p.w for p in spread) / 2 and abs(up_sum - 101) <= sum(p.w for p in spread) / 2


def test_v4_seam_marked_r_run_drops_delta():
    """(P2 提取件半分支守阵, 26-11-18-0037 评审 #10)r 形等值游程(非 z 签名)+ n 断连标记
    + 台阶: 摊配判定 all(z) 不成立且 marked 存活 -> 差分 None 断链(诚实丢字节), 接收桶
    速率 None 非 0 线, totals 快照仍真值 —— 提取件 marked 半分支(返回 None 支)钉面"""
    blk = V4Block(
        1000, 2, 100, 50, (V4Sample(0, 0, 100, 50), V4Sample(0, 0, 100, 50), V4NullRun(2), V4Sample(0, 0, 200, 100))
    )
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    points = v4_series_points((blk, ), g)
    assert any(
        p.t == 1008 and p.dl_rate is None and p.up_rate is None and p.dl_total == 200 and p.up_total == 100
        for p in points
    )
    assert any(p.t == 1004 and p.dl_rate is None and p.dl_total is None for p in points)  # n 标记 present
