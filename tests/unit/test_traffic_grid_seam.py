"""test_traffic_grid_seam 测试计划: qB 口径流量图接缝摊配电池(26-11-18-0037 T1c-2 挂钟
桶面退役后, 判读面 = assemble_group_points 样本分组装配; 摊配单点 = traffic_grid.
_seam_spread_delta 提取件 —— 旧 v4_series_points 桶点级断言逐条改判到样本点层, 桶键 ->
样本 ts, 期望值同源重推)

## 测试计划(每个测试函数一条)
- test_v4_series_slots_seam: S3b 接缝 —— v4_series_slots 稳定排序展平
- test_v4_seam_spread_live_tail_restart_no_spike: (P2 主形态)活尾缝摊配 —— 磁盘长 z 形
  等值游程 + 活尾开放游程: 接缝差按真实发生跨度摊配(span > cov 部分不归因), 接收样本
  无单点尖峰, 游程样本 + 接收样本均匀平线, Sigma(rate x 覆盖) = step_w 守恒; 缝内无
  任何样本点(摊配不凭空造数据, G2/E2E3); 真空显式空值点 @链末槽
- test_v4_seam_spread_disk_vacuum_recovers_delta: (P2)磁盘缝摊配 —— 真空标记 present
  (显式空值点)但缝 <= 60s 时台阶跨标记按真实跨度摊配回收, 标记自身仍空值点
- test_v4_seam_hole_over_threshold_drops_delta: (P2 诚实兜底)观测缝 > 60s = 停机洞:
  delta=None 断链不摊配(活尾长缝与块间真空两形态同判; 接收样本速率 None, totals 真值)
- test_v4_seam_below_threshold_unchanged: (P2 边界)块内短游程仍单样本归因; 块界重启缝
  (有标记)按真实跨度摊配回收(span == cov 差分对跨即覆盖, 全额回收)
- test_v4_seam_flat_r_run_not_spread: (P2 反例守阵)真 flat-r 游程不摊配 —— z 形签名
  (速率双零)是摊配必要条件, 台阶按接收样本单点归因
- test_v4_seam_constants_frozen: (P2 守阵)阈值常量冻结(摊配下限/洞阈值/回看界)
- test_v4_seam_short_gap_two_paths_agree_no_spike: (issue 26-10-16-0954 守阵)重启缝 <= 60s:
  接收样本 rate = step x 覆盖 // span(误接 step/对跨全量可判红), 磁盘与活尾两路径同几何
  同值; 近洞 60s 缝仍不放大; 缝内无样本点
- test_v4_seam_covered_span_mark_two_paths_agree: (issue 26-10-16-0954 残余边界修复轮)
  覆盖连续且带块界真空标记的缝 —— 两路径同一标记同一取值; 摊配份额入游程样本(与锚点
  差分合并), 接收样本 = 余额/声称覆盖; 守恒按 round 取整容差
- test_v4_seam_spread_midrun_seam_then_step_uniform: (评审轮1 #1 回归守阵)缝在等值游程
  中段 + 后接台阶 —— cov = 逐对「对跨 - 未观测秒」合计使 span > cov 恒命中(不依赖
  marked 存活), 台阶均摊平线无单点尖峰(尖峰形态 = 接收样本 131 B/s 级可判红)
(test_v4_seam_marked_r_run_drops_delta 已退役承接: r 形游程 + marked 断链面由
test_traffic_group_assembly::test_marked_r_run_equal_chain_drops_delta 承接)

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V4Block
/活尾快照; 装配面 k=1 逐样本点(t = 样本 ts), 显式空值点 = totals None 的点。
"""

import pytest

from auto_qb.core.traffic_grid import (
    _V4_SEAM_LOOKBACK_S,
    _V4_SEAM_NULL_S,
    _V4_SEAM_SPREAD_MIN_S,
    v4_series_slots,
)

from auto_qb.core.traffic_group_assembly import assemble_group_points

from auto_qb.core.traffic_store import (
    LiveTail,
    LiveTailRun,
    V4Block,
    V4Sample,
    V4ZeroRun,
    v4_block_slots,
    v4_live_tail_slots,
)


def _null_ts(res):
    """装配结果中的显式空值点 t 序列(判据 = totals None)"""
    return [p["t"] for p, t in zip(res.points, res.totals) if t is None]


def _real(res):
    """真值点 (t, dl, up) 序列(空值点剔除)"""
    return [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None]


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


def _disk():
    """主形态共用磁盘块: r@1000 + 60 槽 z 游程(dt 120s, 快照冻结 1000/500, 末槽 @1120)"""
    return V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)))


def test_v4_seam_spread_live_tail_restart_no_spike():
    """(P2 主形态)活尾缝摊配: 磁盘长 z 游程(快照冻结 1000)+ 活尾开放游程(新鲜快照 1262)
    —— 台阶 262 按真实跨度摊配: cov = 60 x 2s + 接收对声称 2s = 122s < span 131s(活尾缝
    9s 不归因) -> step_w = 262 x 122 // 131 = 244, 份额 (4,2) 均匀入游程样本 + 接收样本
    余额 —— 平线无尖峰; Sigma(rate x 覆盖) = 244/122 守恒; 缝内(1122..1128)无任何样本点;
    真空显式空值点 @1120(磁盘链末槽, 活尾同判块间真空)"""
    run = LiveTailRun(kind="z", start=1129.0, last_seen=1141.0, dl_total=1262, up_total=631, samples=6)
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1129,
        interval_s=2,
        projected_ts=1129.0,
        records=(),
        open_run=run
    )
    disk_slots = v4_block_slots(_disk())
    tail_slots = tuple(s for s in v4_live_tail_slots(tail) if s.ts > disk_slots[-1].ts)  # 按 ts 去重(缓存面同款)
    res = assemble_group_points(disk_slots + tail_slots, 1000, 1142, 2)
    assert res.stride == 1
    assert _null_ts(res) == [1120]  # 真空显式空值点(t = 磁盘链末槽)
    real = _real(res)
    assert len(real) == 67  # 1 链首 + 60 游程 + 1 接收 + 5 等值延续
    assert real[0] == (1000.0, 0, 0)  # 链首 0 线(D4)
    assert all(dl == 2 and up == 1 for _, dl, up in real[1:61])  # 游程 60 样本均摊平线
    assert real[61] == (1131.0, 2, 1)  # 接收样本 = 余额(份额 4), 平线无尖峰
    assert all(dl == 0 and up == 0 for _, dl, up in real[62:])  # 接收后等值延续 delta 0
    # Sigma(rate x 覆盖) = step_w = 244/122(游程 60 x 2s x 2 + 接收 2s x 2)
    assert sum(dl * 2 for _, dl, _ in real[1:62]) == 244
    assert sum(up * 2 for _, _, up in real[1:62]) == 122
    # totals 面计数器真值(摊配不污染): 接收样本 = 跨缝全量快照差分 262/131
    recv_tot = next(t for p, t in zip(res.points, res.totals) if p["t"] == 1131.0)
    assert recv_tot == {"t": 1131.0, "dl": 262, "up": 131}
    # 缝内(1122..1128)无任何样本点(不凭空造数据)
    assert not any(1122 <= p["t"] <= 1128 for p in res.points)


def test_v4_seam_spread_disk_vacuum_recovers_delta():
    """(P2)磁盘缝摊配: 真空显式空值点 present @1120 但缝 7s <= 60s —— 台阶 258 跨标记按
    真实跨度摊配回收(cov 122s < span 129s -> step_w = 244), 游程 + 接收样本均匀平线,
    标记自身仍空值点(摊配不凭空造数据)"""
    b2 = V4Block(1129, 2, 1258, 629, (V4Sample(9, 9, 1258, 629), ))  # 重启后新块
    res = assemble_group_points(v4_series_slots((_disk(), b2)), 1000, 1142, 2)
    assert res.stride == 1
    assert _null_ts(res) == [1120]  # 恰一个空值点(真空标记)
    real = _real(res)
    assert len(real) == 62  # 1 链首 + 60 游程 + 1 接收
    assert all(dl == 2 and up == 1 for _, dl, up in real[1:])  # 游程 + 接收均匀平线
    assert sum(dl * 2 for _, dl, _ in real[1:]) == 244  # 覆盖份额守恒(step x cov // span)
    assert sum(up * 2 for _, _, up in real[1:]) == 122


def test_v4_seam_hole_over_threshold_drops_delta():
    """(P2 诚实兜底)观测缝 > 60s = 停机洞: 接收样本 delta=None 断链(速率 None 不造值,
    totals 真值照记), 不摊配; 活尾长缝与块间真空两形态同判(标记同为 @链末槽 1120)"""
    run = LiveTailRun(kind="z", start=1429.0, last_seen=1729.0, dl_total=1244, up_total=622, samples=150)
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1429,
        interval_s=2,
        projected_ts=1429.0,
        records=(),
        open_run=run
    )
    disk_slots = v4_block_slots(_disk())
    tail_slots = tuple(s for s in v4_live_tail_slots(tail) if s.ts > disk_slots[-1].ts)
    res = assemble_group_points(disk_slots + tail_slots, 1000, 1730, 2)
    assert _null_ts(res) == [1120]  # 活尾缝同判真空(断链 None 观测样本有 totals 不入列)
    recv = next((p, t) for p, t in zip(res.points, res.totals) if p["t"] == 1431.0)
    assert recv[0]["dl"] is None and recv[0]["up"] is None  # 洞后接收样本断链 None(不摊配)
    assert recv[1] == {"t": 1431.0, "dl": 244, "up": 122}  # totals 跨洞快照差分真值
    # 洞后等值延续样本: 0 线链(新游程立点后等值差分 0, 覆盖照常)
    after = [(p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if 1433 <= p["t"] <= 1729]
    assert after and all(dl == 0 and up == 0 for dl, up in after)
    # 块间真空长缝: 新块首槽 @1183 -> 未观测 61s > 60s
    b2 = V4Block(1183, 2, 1244, 622, (V4Sample(9, 9, 1244, 622), ))
    res2 = assemble_group_points(v4_series_slots((_disk(), b2)), 1000, 1200, 2)
    assert _null_ts(res2) == [1120]
    recv2 = next((p, t) for p, t in zip(res2.points, res2.totals) if p["t"] == 1183.0)
    assert recv2[0]["dl"] is None and recv2[0]["up"] is None  # 洞后断链, 不摊配
    assert recv2[1] == {"t": 1183.0, "dl": 244, "up": 122}


def test_v4_seam_below_threshold_unchanged():
    """(P2 边界)块内短游程(无标记、全覆盖)行为承袭 —— span == cov 且 span <= max(2 x
    接收槽 dt, 60s) 时恢复样本单点归因; 块界重启缝(有标记)按真实跨度摊配回收(span ==
    cov 恒成立: 差分对跨即覆盖, 全额回收更诚实)"""
    b = V4Block(
        2000,
        2,
        1000,
        500,
        (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=4000), V4Sample(2, 2, 1020, 510, dt_ms=5000)),
    )
    res = assemble_group_points(v4_block_slots(b), 2000, 2012, 2)
    assert _real(res) == [
        (2000.0, 0, 0),  # 链首 0 线
        (2002.0, 0, 0),  # z 槽(delta 0)
        (2004.0, 0, 0),
        (2009.0, 4, 2),  # 恢复样本 delta(20,10)/5s 单点归因(span 5s <= max(2 x 5s, 60s) 不摊)
    ]
    # 有标记短缝(块间 gap 1s, span 7s > cov 6s): 全额摊回游程样本 + 接收样本(余额)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=4000)))
    b2 = V4Block(1007, 2, 1020, 510, (V4Sample(9, 9, 1020, 510), ))
    res2 = assemble_group_points(v4_series_slots((b1, b2)), 1000, 1020, 2)
    assert _null_ts(res2) == [1004]  # 真空标记仍空值点(同刻排观测样本前)
    assert _real(res2) == [
        (1000.0, 0, 0),
        (1002.0, 2, 1),  # 摊配份额 5/2(cum 2s -> target 5)
        (1004.0, 3, 2),  # 摊配份额 6/2(cum 4s -> target 11)
        (1007.0, 3, 2),  # 接收样本 = 余额 6/2s(覆盖 = 声称 dt; 修复前断链 None)
    ]
    # 覆盖份额守恒: cov = 6s < span 7s(缝 1s 不归因)-> Sigma = step x cov // span = 17/8
    # (round 取整损失逐样本 <= w/2, 界取 Sigma w / 2 = 3)
    dl_sum = sum(dl * 2 for _, dl, _ in _real(res2)[1:])
    up_sum = sum(up * 2 for _, _, up in _real(res2)[1:])
    assert abs(dl_sum - 17) <= 3 and abs(up_sum - 8) <= 3
    assert res2.totals[-1] == {"t": 1007.0, "dl": 20, "up": 10}  # totals 面计数器真值


def test_v4_seam_flat_r_run_not_spread():
    """(P2 反例守阵)非 z 形等值游程(r 记录、上行速率非零、dl totals 真 flat)不摊配:
    游程样本 delta 恒 0, 台阶按接收样本单点归因 —— z 形签名(速率双零)是摊配必要条件,
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
            V4Sample(3, 5, 1100, 680, dt_ms=31000),  # dl 台阶 +100(span 93s > max(2dt, 60s) 达门槛)
        ),
    )
    res = assemble_group_points(v4_block_slots(blk), 1000, 1100, 30)
    assert _real(res) == [
        (1000.0, 0, 0),  # 链首 0 线
        (1031.0, 0, 2),  # dl 游程 0 线 / up 60/31s = 2(区间平均)
        (1062.0, 0, 2),
        (1093.0, 3, 2),  # 接收样本 dl delta(100)/31s 单点归因(未摊配)
    ]


def test_v4_seam_constants_frozen():
    """(P2 守阵)阈值常量冻结(计划默认: 摊配下限 60s / 洞阈值 60s / 回看界 1 天, 模块
    常量非配置键)—— 无意漂移即红; 调整阈值须同步本用例与计划 §07 拍板项"""
    assert _V4_SEAM_SPREAD_MIN_S == 60
    assert _V4_SEAM_NULL_S == 60
    assert _V4_SEAM_LOOKBACK_S == 86_400


def test_v4_seam_short_gap_two_paths_agree_no_spike():
    """(issue 26-10-16-0954 守阵)重启缝 <= 60s: 接缝差不再整块落进接收样本按自身覆盖放大
    —— 接收样本 rate = step x 覆盖 // span, 且磁盘路径(真空标记)与活尾路径同几何取值
    逐位一致。几何取自运行实例 08:16 重启证据行(旧块末样 @...749 -> 新块首样 @...766,
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
    out_disk = assemble_group_points(v4_series_slots((old, new)), 1792109700, 1792109900, 1.5)
    assert _null_ts(out_disk) == [1792109749]  # 真空标记(t = 前块链终值)
    recv = next((p, t) for p, t in zip(out_disk.points, out_disk.totals) if p["t"] == 1792109766.0)
    # 覆盖 = 接收槽声称 dt 1.5s: step_w = step x 1.5 // 17 -> rate = step/17(误接 320 可判红)
    assert (recv[0]["dl"], recv[0]["up"]) == (7548, 146872)
    assert abs(recv[0]["dl"] * 1.5 - 128321 * 1.5 / 17) <= 1.5 / 2  # 覆盖份额 = step x cov // span
    # 活尾路径同几何(新块整块未落盘): 块间真空同判 -> 同一标记、同一取值
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=1792109766,
        interval_s=1.5,
        projected_ts=1792109766.0,
        records=new.records,
        open_run=None,
    )
    old_slots = v4_block_slots(old)
    tail_slots = tuple(s for s in v4_live_tail_slots(tail) if s.ts > old_slots[-1].ts)
    out_tail = assemble_group_points(old_slots + tail_slots, 1792109700, 1792109900, 1.5)
    assert _null_ts(out_tail) == [1792109749]
    recv_tail = next((p, t) for p, t in zip(out_tail.points, out_tail.totals) if p["t"] == 1792109766.0)
    assert (recv_tail[0]["dl"], recv_tail[0]["up"]) == (recv[0]["dl"], recv[0]["up"])  # 两路径同值
    # 近洞长缝(未观测恰 60s, 未超阈值): 修复前是反直觉的最强放大形态(越接近洞越放大)
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), ))
    b2 = V4Block(1062, 2, 7200, 5100, (V4Sample(9, 9, 7200, 5100), ))  # 首样 @1062 -> 未观测 60s
    out3 = assemble_group_points(v4_series_slots((b1, b2)), 1000, 1200, 2)
    recv3 = next((p, t) for p, t in zip(out3.points, out3.totals) if p["t"] == 1062.0)
    assert (recv3[0]["dl"], recv3[0]["up"]) == (
        100, 74
    )  # 覆盖 = 声称 dt 2s: step_w = 6200 x 2 // 62 = 200 -> rate 100(修复前 3100, 31 倍)
    assert not any(1002 <= p["t"] <= 1058 for p in out3.points)  # 缝内无样本点(不凭空造数据)


def test_v4_seam_covered_span_mark_two_paths_agree():
    """(issue 26-10-16-0954 残余边界修复轮)覆盖连续且带块界真空标记的缝: 唯一缝信号是
    块界真空标记 —— 活尾与磁盘块同判, 两路径同一标记同一取值; 摊配份额入游程样本
    (与锚点差分同累计), 接收样本 rate = 余额/声称覆盖 2s(未覆盖 0.1s 不归因)"""
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(2, 1000, 500, dt_ms=3900)))
    b2 = V4Block(1006, 2, 1200, 600, (V4Sample(9, 9, 1200, 600), ))
    out_disk = assemble_group_points(v4_series_slots((b1, b2)), 1000, 1100, 2)
    assert _null_ts(out_disk) == [1003]  # 真空标记(t = int(前块游标终值 1003.9))
    recv = next((p, t) for p, t in zip(out_disk.points, out_disk.totals) if p["t"] == 1006.0)
    # 覆盖 = 接收槽声称 dt 2s: step_w = 200 x 5.9 // 6 = 196 -> 余额 67/2s = 34(未覆盖 0.1s 不归因)
    assert (recv[0]["dl"], recv[0]["up"]) == (34, 17)
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
    old_slots = v4_block_slots(b1)
    tail_slots = tuple(s for s in v4_live_tail_slots(tail) if s.ts > old_slots[-1].ts)
    out_tail = assemble_group_points(old_slots + tail_slots, 1000, 1100, 2)
    assert _null_ts(out_tail) == [1003]
    recv_tail = next((p, t) for p, t in zip(out_tail.points, out_tail.totals) if p["t"] == 1006.0)
    assert (recv_tail[0]["dl"], recv_tail[0]["up"]) == (recv[0]["dl"], recv[0]["up"])
    # 覆盖份额守恒(cov 5.9s < span 6s -> 基准 = step x cov // span): Sigma = 196/98
    # (round 取整损失 <= Sigma w / 2 = 2.95; 逐样本覆盖 = z 对声称 1.95s x 2 + 接收 2s)
    real = _real(out_disk)
    dl_sum = sum(dl * (1.95 if tt < 1006 else 2.0) for tt, dl, _ in real[1:])
    up_sum = sum(up * (1.95 if tt < 1006 else 2.0) for tt, _, up in real[1:])
    assert abs(dl_sum - 196) <= 3 and abs(up_sum - 98) <= 3


def test_v4_seam_spread_midrun_seam_then_step_uniform():
    """(评审轮1 #1 回归守阵)缝在等值游程中段 + 后接台阶 —— 摊配判据 span > cov 必须命中:
    cov = 逐对「对跨 - 未观测秒」合计(缝秒不进分母), 不依赖 marked 存活(等值续槽会清零
    marked)—— 台阶均摊到游程样本 + 接收样本出平线, 不出单点尖峰(修复前覆盖按对跨累计使
    span == cov 恒真、marked 已清零, 三支判据全不命中, 262 台阶整段落接收样本出 131 B/s
    尖峰, 复现 issue 26-10-16-0954 已修复形态)"""
    b1 = V4Block(1000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(10, 1000, 500, dt_ms=20000)))
    # 块间真空(缝 22s)后等值 z 游程续段(快照仍冻结 1000; 块首游程端点含均摊 10 槽
    # @1040..1060, 槽距 20/9)+ 恢复台阶 262 @1080
    b2 = V4Block(1040, 2, 1000, 500, (V4ZeroRun(10, 1000, 500, dt_ms=20000), V4Sample(9, 9, 1262, 631, dt_ms=20000)))
    res = assemble_group_points(v4_series_slots((b1, b2)), 1000, 1200, 2)
    assert _null_ts(res) == [1020]  # 真空标记 @缝起点
    assert not any(1022 <= p["t"] <= 1038 for p in res.points)  # 缝内无样本点
    # 均摊线: 游程样本(1002..1060)+ 接收样本(1080)速率全部落在份额带 [3, 4]
    # (尖峰形态 = 接收样本 131 B/s, 判别力充分); 逐样本覆盖 = 各对声称 dt(2s 或 20/9s 或 20s)
    spread = [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None and p["t"] >= 1002]
    assert spread and all(3 <= dl <= 4 and 1 <= up <= 2 for _, dl, up in spread), spread

    def _cov(tt):
        if tt < 1020:
            return 2.0  # b1 z 对(声称 dt 2s)
        if tt < 1080:
            return 20.0 / 9  # b2 块首游程槽(端点含均摊槽距 20/9s)
        return 20.0  # 接收对(声称 dt 20s)

    recv = next(dl for tt, dl, _ in spread if tt == 1080.0)
    run_rates = [dl for tt, dl, _ in spread if tt <= 1020]
    assert abs(recv - sum(run_rates) / len(run_rates)) <= 1  # 接收样本与游程样本同处均摊带
    # 覆盖份额守恒: cov = 62.2s(游程对覆盖 + 接收槽声称 dt 20s)< span 80s(缝 17.8s 不归因)
    # -> Sigma = step x cov // span = 262 x 62222 // 80000 = 203(round 取整损失 <= Sigma w / 2)
    dl_sum = sum(dl * _cov(tt) for tt, dl, _ in spread)
    up_sum = sum(up * _cov(tt) for tt, _, up in spread)
    assert abs(dl_sum - 203) <= sum(_cov(tt) for tt, _, _ in spread) / 2
    assert abs(up_sum - 101) <= sum(_cov(tt) for tt, _, _ in spread) / 2
