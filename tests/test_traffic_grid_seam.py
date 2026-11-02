"""test_traffic_grid_seam 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v4 换代 plan 26-10-05-2200 N1 —— 仅标识符与 fixture 适配, 断言逻辑零变化)

## 测试计划(每个测试函数一条)
- test_v4_series_slots_seam: S3b 接缝 —— v4_series_slots 稳定排序展平
- test_v4_seam_spread_live_tail_restart_no_spike: (plan 26-10-15-0829 P2; 26-10-16-0954 修复轮改口径)活尾缝摊配 —— 磁盘长 z 形等值游程(快照冻结)+ 活尾新鲜快照:
  接缝差按真实跨度摊配(span > cov 时只回收覆盖份额 step x cov // span), 接收桶无单桶尖峰, 游程桶+接收桶均匀平线; 缝内栅格桶仍无观测(G2/E2E3)
- test_v4_seam_spread_disk_vacuum_recovers_delta: (P2)磁盘缝摊配 —— 真空标记 present 但缝 <= 60s 时台阶跨标记按真实跨度摊配回收(修复前静默丢弃), 标记桶仍 null
- test_v4_seam_hole_over_threshold_drops_delta: (P2 诚实兜底)观测缝 > 60s = 停机洞: delta=None 断链不摊配(活尾长缝与块间真空两形态同判)
- test_v4_seam_below_threshold_unchanged: (P2 边界; 26-10-16-0954 修复轮改口径)块内短游程(无标记、span == cov)仍单桶 delta/w 逐字不变;
  块界重启缝(有标记/未覆盖段)不再按跨度门槛落空, 按真实跨度覆盖份额回收
- test_v4_seam_flat_r_run_not_spread: (P2 反例守阵)真 flat-r 游程(上行非零)不摊配 —— z 形签名(速率双零)是摊配必要条件
- test_v4_seam_constants_frozen: (P2 守阵)阈值常量冻结(摊配下限/洞阈值各 60s, 模块常量非配置键)
- test_v4_seam_short_gap_two_paths_agree_no_spike: (issue 26-10-16-0954-bug-traffic-seam-short-gap-spike)短缝接收桶 rate = step/真实跨度;
  磁盘与活尾两路径同几何同值(含同一位块界真空标记 —— 残余边界修复轮: 活尾同判块间真空); 近洞 60s 缝仍不放大; 缝内栅格桶仍 null
- test_v4_seam_covered_span_mark_two_paths_agree: (残余边界修复轮)覆盖连续(span == cov)且带块界真空标记的缝 —— 磁盘摊配回收(不再 elif marked 丢弃)/活尾同判同值;
  覆盖份额守恒(span == cov 时基准 = step 全额)

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
    """(P2 主形态, P0 实施记录; issue 26-10-16-0954 修复轮改口径)活尾缝摊配: 磁盘链长
    z 形等值游程(快照冻结)+ 活尾开放 z 游程(新鲜快照 F0)—— 接缝差按**真实发生跨度**摊配
    (覆盖份额口径: span=131 > cov=122 时基准 step_w = step x cov // span, 未覆盖的 9s
    停机秒不归因): 接收桶无单桶尖峰(修复前 delta/w, 本事故 2s 桶 ~12,000 倍), 游程桶+
    接收桶均匀 step_w/cov 平线, 逐点 Σ(rate x w) = step_w = 244/122 覆盖份额守恒
    (整除构造); 无观测缝栅格桶仍无观测(摊配不凭空造非 null 桶, G2/E2E3)"""
    interval = 2
    disk = V4Block(
        1000,
        interval,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)),
    )  # z 游程 60 槽 x 2s = 120s, 快照冻结 (1000,500); 末槽 @1120 -> 桶 1118
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
    points = v4_series_points((disk, ), 900, 2000, tail_slots=v4_live_tail_slots(tail))
    # 1 r 点 + 60 游程桶 + 1 活尾缝真空标记 + 6 活尾桶(残余边界修复轮: 活尾同判块间真空,
    # 磁盘链末槽 @1120 与活尾首槽 1131 之间有未观测段 -> 出与磁盘路径同位的 null 标记)
    assert len(points) == 68
    assert [p.t for p in points if p.dl_rate is None and p.w == 0] == [1120]
    out = [p for p in v4_rate_from_totals(points) if not (p.dl_rate is None and p.up_rate is None and p.w == 0)]
    # 摊配: step=262/131, span=131 > cov=122 -> step_w=244/122; 接收者 = 60 游程桶(w=2)
    # + 接收桶(w=2), 按累计比例取整 -> 份额 (4,2) 均匀, 余额归接收桶
    assert all(p.dl_rate == 2 and p.up_rate == 1 for p in out[1:62])  # 游程 60 桶+接收桶 = 均匀平线
    assert all(p.dl_rate == 0 and p.up_rate == 0 for p in out[62:])  # 接收桶之后等值延续 delta=0
    assert out[0].dl_rate is None and out[0].up_rate is None  # 窗首基线缺失
    assert sum(p.dl_rate * p.w for p in out[1:62]) == 244  # 覆盖份额守恒(点级, 整除构造)
    assert sum(p.up_rate * p.w for p in out[1:62]) == 122
    totals = v4_totals_points(points)
    assert [(e.dl, e.up) for e in totals[1:61]] == [(4, 2)] * 60  # 60 游程桶(标记前)
    assert (totals[61].t, totals[61].dl, totals[61].up) == (1120, None, None)  # 缝真空标记
    assert (totals[62].dl, totals[62].up) == (4, 2)  # 接收桶 = 余额
    assert [(e.dl, e.up) for e in totals[63:]] == [(0, 0)] * 5
    # 栅格诚实性: 无观测缝(1120..1126)栅格桶无观测; 接收覆盖 [1129,1131) 奇键跨界:
    # 1128 桶得 1s(rate 2); 1130 桶 = 接收桶 1s(rate 2) + 后继等值点 1s(rate 0) 加权 = 1
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    obs = v4_grid_obs(out, g)
    assert all(b not in obs for b in (1120, 1122, 1124, 1126))  # 缝内桶仍 null(不凭空造数据)
    assert obs[1128].dl_rate == 2 and obs[1130].dl_rate == 1  # 接收覆盖跨界分摊(与后继 0 线加权)


def test_v4_seam_spread_disk_vacuum_recovers_delta():
    """(P2)磁盘缝摊配(P0 实施记录 ② 反事实形态; issue 26-10-16-0954 修复轮改口径):
    块间真空 null 标记 present(渲染断线)但缝 <= _V4_SEAM_NULL_S 时台阶跨标记按真实跨度
    摊配回收 —— 修复前陈旧差被静默丢出 totals 通道; 覆盖份额口径: span=129 > cov=122 ->
    Σ(rate x w) = step x cov // span = 244/122(未覆盖的 7s 停机秒不归因, 整除构造);
    标记桶自身仍 null(摊配不凭空造数据)"""
    b1 = V4Block(
        1000,
        2,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)),
    )
    b2 = V4Block(1129, 2, 1258, 629, (V4Sample(9, 9, 1258, 629), ))  # 重启后新块(封口形态)
    points = v4_series_points((b1, b2), 900, 2000)
    assert any(p.t == 1120 and p.dl_rate is None for p in points)  # 真空标记 present @1120
    out = v4_rate_from_totals(points)
    marks = [p for p in out if p.dl_rate is None and p.up_rate is None and p.w == 0]
    assert [p.t for p in marks] == [1120]  # 恰一个 null 点(标记)
    spread = [p for p in out if not (p.dl_rate is None and p.up_rate is None and p.w == 0)]
    assert all(p.dl_rate == 2 and p.up_rate == 1 for p in spread[1:])  # 游程+接收桶均匀平线
    assert sum(p.dl_rate * p.w for p in spread[1:]) == 244  # 跨缝回收: Σ = 覆盖份额 step x cov // span
    assert sum(p.up_rate * p.w for p in spread[1:]) == 122


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
    # 首活尾槽 @1431 -> 覆盖缝 = 1429-1120 = 309s > 60s(洞; 游程均摊不吸收停机段)
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
    out = v4_rate_from_totals(v4_series_points((disk, ), 900, 2000, tail_slots=v4_live_tail_slots(tail)))
    assert [p.t for p in out if p.dl_rate is None and p.w == 0] == [1120]  # 活尾缝同判真空(磁盘链末槽)
    z_part = [p for p in out if p.w > 0][1:61]
    assert all(p.dl_rate == 0 and p.up_rate == 0 for p in z_part)  # 游程桶不摊配(0 线照旧)
    recv = [p for p in out if p.w > 0][61]
    assert recv.t == 1429 and recv.dl_rate is None and recv.up_rate is None  # 洞后接收桶断链 None
    # 块间真空长缝: 新块首槽 @1183 -> 覆盖缝 61s > 60s
    b2 = V4Block(1183, 2, 1244, 622, (V4Sample(9, 9, 1244, 622), ))
    out2 = v4_rate_from_totals(v4_series_points((disk, b2), 900, 2000))
    assert any(p.t == 1120 and p.dl_rate is None for p in out2)  # 真空标记 present
    assert out2[-1].t == 1181 and out2[-1].dl_rate is None and out2[-1].up_rate is None  # 洞后断链, 不摊配


def test_v4_seam_below_threshold_unchanged():
    """(P2 边界; issue 26-10-16-0954 修复轮改口径)块内短游程(无标记、全覆盖)行为逐字
    不变 —— span == cov 且 span <= max(2 x 桶宽, 60s) 时恢复桶仍单桶 delta/w; 块界重启缝
    (有 null 标记或未覆盖段)不再按跨度门槛落空, 一并按真实跨度摊配回收
    (与 _V4_SEAM_NULL_S 常量注释「<= 本值 = 重启缝 -> 摊配回收」对齐)"""
    # 块内短游程(2 槽 4s)+ 邻接恢复: span=9s == cov -> 恢复桶单桶归因(旧口径)
    b = V4Block(
        2000,
        2,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=4000), V4Sample(2, 2, 1020, 510, dt_ms=5000)),
    )
    out = v4_rate_from_totals(v4_series_points((b, ), 1990, 3000))
    assert [(p.t, p.dl_rate, p.up_rate) for p in out] == [
        (1998, None, None),
        (2000, 0, 0),
        (2002, 0, 0),
        (2004, 4, 2),  # 恢复桶 delta(20,10)/w5(显式 dt 5s -> 桶宽 ceil(5)=5, 桶 [2004,2009)) 单桶归因
    ]
    # 有标记短缝(块间 gap 1s, span=7 > cov=6): 覆盖份额 step_w = 20 x 6 // 7 = 17 摊回游程桶
    # + 接收桶(修复前按跨度门槛落空 -> 断链 None, 字节静默丢出)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=4000)))
    b2 = V4Block(1007, 2, 1020, 510, (V4Sample(9, 9, 1020, 510), ))
    out2 = v4_rate_from_totals(v4_series_points((b1, b2), 900, 2000))
    assert [(p.t, p.dl_rate, p.up_rate) for p in out2] == [
        (998, None, None),
        (1000, 2, 1),  # 摊配份额 5/2(cum=2 -> target=5)
        (1002, 3, 2),  # 摊配份额 6/3(cum=4 -> target=11/5)
        (1004, None, None),  # 真空标记仍 null
        (1005, 3, 2),  # 接收桶 = 余额 6/3(修复前: 断链 None)
    ]
    assert sum(e.dl for e in v4_totals_points(v4_series_points((b1, b2), 900, 2000)) if e.dl is not None) == 17
    assert sum(
        e.up for e in v4_totals_points(v4_series_points((b1, b2), 900, 2000)) if e.up is not None
    ) == 8  # 覆盖份额守恒(未覆盖 1s 不归因)


def test_v4_seam_flat_r_run_not_spread():
    """(P2 反例守阵)非 z 形等值游程(r 记录、上行速率非零、dl totals 真 flat)不摊配:
    游程 delta 恒 0, 台阶按接收桶 delta/w 单桶归因 —— z 形签名(速率双零)是摊配必要
    条件, 防「真 flat + 一次真实增长」被错误摊平稀释"""
    pts = tuple(V4PointEntry(1000 + 30 * k, 0, 5, 1000, 500 + 30 * k, w=30) for k in range(5))
    pts += (V4PointEntry(1150, 3, 5, 1100, 650, w=30), )  # dl 台阶 +100(真单间隔增长)
    out = v4_rate_from_totals(pts)
    assert [(p.dl_rate, p.up_rate) for p in out] == [
        (None, None),
        (0, 1),
        (0, 1),
        (0, 1),
        (0, 1),  # dl 游程 0 线 / up 正常区间平均
        (3, 1),  # 接收桶 dl delta(100)/30 单桶归因(未摊配)
    ]


def test_v4_seam_constants_frozen():
    """(P2 守阵)阈值常量冻结(计划默认: 摊配下限 60s / 洞阈值 60s, 模块常量非配置键)
    —— 无意漂移即红; 调整阈值须同步本用例与计划 §07 拍板项"""
    assert _V4_SEAM_SPREAD_MIN_S == 60
    assert _V4_SEAM_NULL_S == 60


def test_v4_seam_short_gap_two_paths_agree_no_spike():
    """(issue 26-10-16-0954-bug-traffic-seam-short-gap-spike 守阵)重启缝 <= 60s: 接缝差
    不再整块落进接收桶按自身桶宽放大 —— 接收桶 rate = step / 真实跨度(只回收覆盖份额),
    且**磁盘路径(真空标记)与活尾路径(无标记)同几何取值逐位一致**(修复前: 活尾 =
    delta/w 尖峰, 磁盘 = 断链 None —— 同一桶刷盘前后取值不同, 用户无法判断哪个是真的)。
    几何取自运行实例 08:16 重启证据行(旧块末样 @1792109749 -> 新块首样 @1792109766,
    接缝差 up 2,496,825, 修复前 1,248,412 B/s = 8.5 倍放大)"""
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
    out_disk = v4_rate_from_totals(v4_series_points((old, new), 1792109700, 1792109900))
    assert [p.t for p in out_disk if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1792109749]
    recv = [p for p in out_disk if p.t == 1792109764][0]  # 缝后首桶
    assert (recv.dl_rate, recv.up_rate, recv.w) == (7548, 146872, 2)
    assert recv.up_rate * recv.w == 293744  # 覆盖份额 = step x w // span(未覆盖 15s 不归因)
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
    out_tail = v4_rate_from_totals(
        v4_series_points((old, ), 1792109700, 1792109900, tail_slots=v4_live_tail_slots(tail))
    )
    # 活尾首槽(块首记录 B.start)抵达不了磁盘链末槽 -> 与磁盘块同判出真空标记(残余边界修复轮)
    assert [p.t for p in out_tail if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1792109749]
    recv_tail = [p for p in out_tail if p.t == 1792109764][0]
    assert (recv_tail.dl_rate, recv_tail.up_rate) == (recv.dl_rate, recv.up_rate)  # 两路径同值(修复前 尖峰 vs None)
    # 近洞长缝(观测覆盖缝恰 60s, 未超阈值): 修复前是反直觉的最强放大形态(越接近洞越放大)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), ))
    b2 = V4Block(1062, 2, 7200, 5100, (V4Sample(9, 9, 7200, 5100), ))  # 首样 @1062 -> 桶 1060, 缝 = 60s
    out3 = v4_rate_from_totals(v4_series_points((b1, b2), 900, 2000))
    recv3 = out3[-1]
    assert (recv3.t, recv3.w) == (1060, 2)
    assert recv3.dl_rate == 100  # step 6200, span 62 -> 覆盖份额 200 -> rate 100(修复前 6200/2 = 3100, 31 倍)
    assert recv3.up_rate == 74  # step 4600, span 62 -> 份额 148 -> rate 74
    # 缝内栅格桶仍无观测(摊配不凭空造非 null 桶, G2/E2E3)
    g = WindowGrid("5m", 900, 2000, 2, "raw", tuple(range(900, 2000, 2)))
    obs = v4_grid_obs(out3, g)
    assert all(b not in obs for b in (1002, 1020, 1058))


def test_v4_seam_covered_span_mark_two_paths_agree():
    """(issue 26-10-16-0954 残余边界修复轮)覆盖连续且带块界真空标记的缝: 接收点覆盖起点恰接住
    上一观测点覆盖末端(span == cov, 「未覆盖段存在」判据不达), 唯一缝信号是块界真空标记 ——
    修复前活尾组不判真空, 同一几何两条路径取值不同(span <= 60s 时磁盘走 `elif marked` 断链丢弃,
    活尾则把整块台阶打入接收桶)。修复后**活尾与磁盘块同判块间真空**, 两路径同一标记同一取值。
    几何取自 issue 26-10-08-0141 的 1 秒边界带形态(种子覆盖末梢 ceil 取整压过链末槽, 使覆盖
    连续而标记仍在) —— 即本修复轮的残余边界。"""
    # 覆盖连续: 种子块末槽 @1003.9(覆盖末端 ceil = 1004), 恢复块首槽 @1006 -> 桶 1004(恰接住)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=3900)))
    b2 = V4Block(1006, 2, 1200, 600, (V4Sample(9, 9, 1200, 600), ))
    out_disk = v4_rate_from_totals(v4_series_points((b1, b2), 900, 2000))
    assert [p.t for p in out_disk if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1003]
    recv = [p for p in out_disk if p.t == 1004][0]
    assert (recv.dl_rate, recv.up_rate, recv.w) == (34, 17, 2)  # step 200/100 全额按覆盖秒摊(未丢弃)
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
    out_tail = v4_rate_from_totals(v4_series_points((b1, ), 900, 2000, tail_slots=v4_live_tail_slots(tail)))
    assert [p.t for p in out_tail if p.dl_rate is None and p.up_rate is None and p.w == 0] == [1003]
    recv_tail = [p for p in out_tail if p.t == 1004][0]
    assert (recv_tail.dl_rate, recv_tail.up_rate) == (recv.dl_rate, recv.up_rate)
    # 覆盖份额守恒(span == cov -> 基准 step_w = step): 游程桶 + 接收桶逐点 delta 之和 = step
    tot = v4_totals_points(v4_series_points((b1, b2), 900, 2000))
    assert [e.dl for e in tot if e.t >= 1000] == [66, 67, None, 67]
    assert [e.up for e in tot if e.t >= 1000] == [33, 33, None, 34]
