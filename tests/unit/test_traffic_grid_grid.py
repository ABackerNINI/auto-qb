"""test_traffic_grid_grid 测试计划: qB 口径流量图读侧窗口面 + 样本分组契约守阵
(plan 26-10-03-0946 方案C P4 §05.1; 26-11-18-0037 阶段 1 T1c-2 —— 挂钟桶面(F1 桶宽加宽/
F2 归桶/F3 持有/F4-2 桶值缓存)退役后, 本电池 = build_grid 窗界面守阵 + raw 契约经
assemble_group_points 新面的语义守阵; 旧 v4_series_points 桶点级断言的去向见各用例
docstring 的「承接」注)

## 测试计划(每个测试函数一条)
窗口面(build_grid; 26-11-18-0037 T1c-2 后 raw 段 = 窗界载体):
- test_build_grid_24h_raw_window_bounds_only: 24h raw 窗 = 窗界载体(buckets 恒空,
  interval = 生效采样间隔直传, t0/t1 恒等)—— 旧 F1 桶宽加宽/481 桶面随挂钟桶面退役;
  30d hour 窗不变(3600s = 721 桶); 未知窗口 ValueError
- test_build_grid_extended_windows_bounds_only: raw 档逐窗(1m-24h)窗界载体逐档 + 3d/7d
  hour 档不变(恒 3600s; sample_interval 只在 raw 段生效)
- test_build_grid_raw_t1_float_wall_clock: (issue 26-11-17-0936 承袭)raw 窗 t1 = 浮点
  挂钟原值不整秒截断(窗尾锚末样本语义), t0 = t1 - span 恒等; 整点输入数值不变
- test_build_grid_nonpositive_interval_fails_fast: (黄金法则 4)非正 si fail-fast raise
  (来源链纯 config 派生, 校验单点在 validate_config; 下游 group_null_lo/分组口径 k 全依赖 si)
- test_floor_buckets_boundary_and_mid_t1_equal_n: (26-11-14-1313 S1a/F3)t1 恰落桶边界 vs
  落桶中 n 恒等(floor+1; hour 段窗现消费面 —— raw 桶面退役后本函数只剩 hour/测试直构共用)
- test_build_grid_n_phase_invariant_hour: (26-11-14-1313 S1a/F3)hour 段窗 W mod interval
  == 0 时 n 不随相位漂移(raw 面随桶面退役, 只钉 hour)
- test_build_grid_day_windows_d4: 6mo/1y day 段窗逐日铺格/90d 拒绝/all 拒绝 build_grid
- test_build_grid_day_window_midnight_anchors: (bg_52/bg_53)day 窗日期集 t1-1 口径
- test_rate_points_null_shape: points 形状 {"t","dl","up"} | null(空桶断线; agg 段窗响应通道)

样本分组契约守阵(经 assemble_group_points; 26-11-18-0037 §03):
- test_tail_group_true_value_no_hold_clone: (改写自旧 F4 hold 尾桶填充/速率持有两例)尾组
  恒真值无持有克隆 —— 活跃链装配末点 t = 最新样本 ts, 值 = 组内真实差分/覆盖(瞬时垃圾
  字段零上图), 点数 = 样本数(now 之后无任何合成点); totals 尾组 = 末样本真实增量
- test_tail_group_z_run_zero_line: (改写自旧 F4 z 游程链端延伸例)z 游程尾组 0 线非 null
  (空闲观测真值), t = 末 z 槽 ts, totals 快照同值链不断
- test_stall_no_fabricated_points: (改写自旧 F4 停滞过界例)停滞不造点 —— 停止进样后窗口
  推进, 点集只在窗沿收缩, 无新点无空值点, 末点 t/值恒定(诚实滞后; 停流可见性由前端
  徽标按末样本 ts 承载)
- test_disconnect_n_run_explicit_null_endpoint: (改写自旧 F4 断连不延伸例)断连 = 显式
  空值点收尾(n 游程折叠一点), 无持有克隆、无真值点尾随
- test_window_filter_tail_and_empty_assembly: (承接旧 v4_window_filter_and_empty 的窗尾
  半边)ts >= t1 槽不消费 / 无块空块全窗外 = 空点列(天然真空); 窗前种子/窗外标记面由
  test_traffic_group_assembly::test_window_filter_and_seed_baseline /
  test_marks_outside_window_not_emitted 承接
- test_known_sequence_end_to_end_assembly: (承接旧 v4_points_known_sequence_end_to_end)
  天文件文本 -> 解析 -> k=1 逐样本装配端到端: 显式 dt/缺省/均摊定位/链式自洽四形态;
  断连(n)与真空(块间)显式空值点; 停机洞断链未知(totals 真值); Sigma(totals) = 遥差
- test_live_tail_merge_dedup_assembly: (S6 承袭)磁盘部分块 + 活尾槽 == 整块装配(去重后
  逐位相等); 滞后快照重列已落盘记录被按 ts 去重
- test_seed_vacuum_null_t0_edge_band_assembly: (承接旧 v4_seed_vacuum_null_t0_edge_band)
  窗首种子边界带 —— 真空标记 t < t0 不产空值点(发射面 [t0, t1))但断链面生效(链界
  [null_lo, t1) 含带内标记); 重启缝接收样本速率 = step x 覆盖 // span: 带内 295/148 与
  带外 286/143 可区分(误接旧值可判红)
- test_lookback_boundary_slots_kept_and_mark: (承接旧 v4_series_points_lookback_boundary_
  slots_kept + null_mark_at_lookback_boundary + stale_slot_below_lookback 三例)消费下界
  (t0 - si - 回看界)含等号: 恰在界上的槽消费作差分基线(totals 非 None 可判), 界外槽
  不消费; 恰在界上的 n 标记判得(marked 生效)但不产空值点(发射面 [t0, t1))
- test_break_flag_and_zero_rate_group_faces: (承接旧 vgo_60 断链旗跨同桶后继槽 +
  vgo_105 有覆盖断链桶 0 线两例)组内 broke 旗跨后继样本存活: 洞后样本(delta None 无
  覆盖)+ 同组重置样本(delta None 豁免)—— 组覆盖 0 -> 值 None(断链未知 != 0 线);
  同形但后继为有效 0 差分(有覆盖)-> 组 0 线非 None(判据看覆盖毫秒不看差分和)
- test_seam_allocation_zero_share_and_balance: (承接旧 fold 摊配份额用例, 提取件直钉)
  _seam_spread_delta 按覆盖份额取整 —— 小份额项取整为 0 不入桶, 余额归接收方, 严格守恒
  (份额和 + delta == step_w)

天游标防线单元(分组点列缓存承袭面, 直构钉防御面契约):
- test_day_cursor_valid_structural_invalid_paths: 天游标结构校验逐失效面(收缩/改写/
  停驻块消失/记录数缩/末记录替换/非游程停驻/超游程长)+ 合法两形态对照

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V4Block
(天文件文本路径经 format_v4_day_text -> parse_v4_day_text 打通解析接缝); V4Block 直构时
基线参数取 (0,0) 或首记录 totals —— 槽位数学与基线无关, 仅 format/parse roundtrip 路径
要求 delta 非负。
"""

import pytest

from auto_qb.core.traffic_grid import (
    WINDOW_SPECS,
    build_grid,
    rate_points,
    _V4BucketDayCursor,
    _V4_SEAM_LOOKBACK_S,
    _floor_buckets,
    _seam_spread_delta,
    _v4_bucket_day_cursor_valid,
    v4_series_slots,
)

from auto_qb.core.traffic_group_assembly import assemble_group_points, assemble_group_points_from_blocks

from auto_qb.core.traffic_grid import BucketObs

from auto_qb.core.traffic_store import (
    LiveTail,
    LiveTailRun,
    V4Block,
    V4NullRun,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
    v4_live_tail_slots,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_window_dates,
)

from traffic_grid_support import NOW


def _slots_of(blk):
    """块 -> 槽序(游标 dt 链展开; 装配入参的记录时间轴)"""
    return v4_block_slots(blk)


def _null_ts(res):
    """装配结果中的显式空值点 t 序列(判据 = totals None —— 断链未知真值点的 totals 非
    None, 两者形态分离, 详 assemble_group_points 契约)"""
    return [p["t"] for p, t in zip(res.points, res.totals) if t is None]


# ======================================================================
# 窗口面(build_grid)
# ======================================================================


def test_build_grid_24h_raw_window_bounds_only():
    """(26-11-18-0037 T1c-2)raw 段窗栅格 = 窗界载体: buckets 恒空(挂钟桶面随样本分组契约
    退役 —— 旧 F1 桶宽 = si x k 加宽 + 481 桶面删除), interval = 生效采样间隔直传(仅
    标称组距基元, 无桶面语义), t0/t1 恒等; hour 段窗(30d)不变: 3600s = 721 桶, sample_
    interval 不生效; 未知窗口 ValueError"""
    g = build_grid("24h", NOW, 30.0)
    assert g.segment == "raw" and g.t1 == NOW and g.t0 == NOW - 86400
    assert g.buckets == () and g.interval == 30
    h = build_grid("30d", NOW, 999.0)  # sample_interval 只在 raw 段生效
    assert h.interval == 3600 and h.segment == "hour" and len(h.buckets) == 721
    assert h.first == ((NOW - 2592000) // 3600) * 3600
    with pytest.raises(ValueError):
        build_grid("90d", NOW)  # 窗口集外


def test_build_grid_extended_windows_bounds_only():
    """raw 档逐窗(1m-24h)窗界载体逐档(buckets 恒空, interval = si, t0 = now - span);
    hour 档(3d/7d)不变: 恒 3600s, 桶数 = 跨度/3600 + 1(26-11-14-1313 F3 floor+1)"""
    for name, span in (
        ("1m", 60), ("5m", 300), ("30m", 1800), ("3h", 10800), ("6h", 21600), ("12h", 43200), ("24h", 86400)
    ):
        g = build_grid(name, NOW, 30.0)
        assert g.segment == "raw" and g.buckets == () and g.interval == 30 and g.t0 == NOW - span, name
    for name, span in (("3d", 259200), ("7d", 604800)):
        h = build_grid(name, NOW, 999.0)  # sample_interval 只在 raw 段生效
        assert h.interval == 3600 and h.segment == "hour" and len(h.buckets) == span // 3600 + 1, name
        assert h.first == ((NOW - span) // 3600) * 3600, name


def test_build_grid_raw_t1_float_wall_clock():
    """(issue 26-11-17-0936 承袭)raw 窗 t1 = 浮点挂钟原值(不整秒截断 —— 窗尾锚末样本,
    §03 窗口右沿锚末样本语义的窗界来源), t0 = t1 - span 恒等; 整点输入数值不变"""
    for frac in (0.0, 0.4, 0.5, 0.7, 0.9):
        now = 1_000_000 + frac
        g = build_grid("1m", now, 1.5)
        assert g.t1 == now and g.t0 == now - 60 and g.segment == "raw"
    g = build_grid("1m", 1_000_000, 1.5)  # 整点输入
    assert g.t1 == 1_000_000 and isinstance(g.t1, float)


def test_build_grid_nonpositive_interval_fails_fast():
    """(黄金法则 4)si 来源链 = 纯 config 派生(validate_config 保证 multiplier >= 1 x
    main_tick >= 0.5), build_grid 对非正值 fail-fast raise 而非静默兜底 —— 0 间隔若静默
    落 DEFAULT 会把装配缺陷藏进「看起来正常」的 30s 口径(下游 group_null_lo/分组口径 k
    全依赖 si)"""
    for bad in (0, 0.0, -1.5):
        with pytest.raises(ValueError):
            build_grid("1m", NOW, bad)


def test_floor_buckets_boundary_and_mid_t1_equal_n():
    """(26-11-14-1313 S1a/F3)t1 恰落桶边界 vs 落桶中: n 恒等(floor+1 恒含进行中桶)。
    反转 26-10-11-0207 R07 的 ceil 拍板: t1 整秒截断 + 首桶 floor 对齐 -> t1 - first 一半
    时间恰落桶边界, ceil 下 n 在 k/k+1 方波随轮询相位翻转 -> floor+1 后任意相位恒 k+1。
    hour 段窗现消费面(raw 桶面退役); 构造: 跨度 W=200 为 interval=100 整倍, t1 = t0 + W + 相位"""
    assert _floor_buckets(100, 300, 100) == (100, 200, 300)  # t1 恰落边界: 尾桶 = 进行中桶(t1 起)
    assert _floor_buckets(100, 350, 100) == (100, 200, 300)  # t1 落桶中: 同 n
    assert _floor_buckets(100, 399, 100) == (100, 200, 300)  # t1 落桶中(差 1s 到边界): 仍同 n


def test_build_grid_n_phase_invariant_hour():
    """(26-11-14-1313 S1a/F3)hour 段窗 W mod interval == 0 时 n 不随相位漂移: now 相位扫过
    桶界两侧, n 恒定且尾桶恒为进行中桶(floor(t1/interval) 对齐)—— ceil 旧口径下 n 在
    k/k+1 方波翻转(G4 实证)。raw 面随桶面退役, 只钉 hour 分支"""
    for phase in (0, 1, 1799, 3599):  # hour 段窗(3600s 桶): 相位含边界与桶中
        h = build_grid("3d", NOW + phase, 999.0)
        assert len(h.buckets) == 259200 // 3600 + 1, phase
        assert h.last == ((NOW + phase) // 3600) * 3600, phase


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


def test_build_grid_day_window_midnight_anchors():
    """(bg_52/bg_53)day 窗日期集 t1-1 口径 —— now 恰为 23:59:59 不多铺次日桶, 恰为
    00:00:01 不丢当日桶(变异成 t1+1/t1-2 会各错一天)"""
    midnight = v4_day_epoch(NOW)
    span = WINDOW_SPECS["6mo"][0]
    for now in (midnight + 86399, midnight + 1):
        g = build_grid("6mo", now)
        assert g.segment == "day" and g.t1 == now and g.t0 == now - span
        assert g.last == midnight  # 末桶恒为 now 所在本地日界


def test_rate_points_null_shape():
    """points 形状(§08): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)。
    agg 段窗响应通道(hour 栅格; raw 段响应 = 样本分组点列, 不走本面)"""
    g = build_grid("30d", NOW)
    base = g.buckets[10]
    obs = {base: BucketObs(1, 2, 3, 4)}
    assert rate_points(obs, g)[g.buckets.index(base)] == {"t": base, "dl": 1, "up": 2}
    assert rate_points(obs, g)[g.buckets.index(base) + 1] is None


# ======================================================================
# 样本分组契约守阵(经 assemble_group_points; 26-11-18-0037 §03)
# ======================================================================


def test_tail_group_true_value_no_hold_clone():
    """(改写自旧 F4 hold 尾桶填充/速率持有两例; §03 尾组恒真值)活跃链装配: 末点 t =
    最新样本 ts, 值 = 组内真实差分/覆盖(瞬时垃圾速率字段 5000/2500 零上图, 1000/500)——
    无持有克隆(点数 = 样本数, now 之后无任何合成点, 无 is_hold 面); totals 尾组 =
    末样本真实增量 1500/750(字节守恒, 非持有面 0 增量)。几何: 磁盘 57 条 + 活尾 3 条
    (head_pending=False 倒推复原), 链端 = start + 88.5"""
    interval = 1.5
    start = NOW
    recs = tuple(V4Sample(5000, 2500, 1500 * (k + 1), 750 * (k + 1)) for k in range(60))
    full_slots = _slots_of(V4Block(start, interval, 0, 0, recs))
    chain_end = full_slots[-1].ts  # = start + 88.5
    disk = (V4Block(start, interval, 0, 0, recs[:-3]), )
    tail = LiveTail(
        block_open=True,
        head_pending=False,
        start_epoch=start,
        interval_s=interval,
        projected_ts=chain_end,
        records=recs[-3:],
        open_run=None,
    )
    disk_slots = _slots_of(disk[0])
    tail_slots = tuple(s for s in v4_live_tail_slots(tail) if s.ts > disk_slots[-1].ts)  # 按 ts 去重(缓存面同款)
    res = assemble_group_points(disk_slots + tail_slots, chain_end + 0.3 - 60, chain_end + 0.3, interval)
    assert res.stride == 1 and not res.over_budget
    assert len(res.points) == 40  # 点数 = 窗内样本数(无持有克隆: 旧面传 now 会多一枚 holding 桶点)
    last = res.points[-1]
    assert last["t"] == chain_end  # 最新样本 ts(旧面 = 进行中桶键 grid.last)
    assert (last["dl"], last["up"]) == (1000, 500)  # 组内真实差分/覆盖(非 0 非 null 非瞬时直采)
    assert all(p["dl"] is None or p["dl"] <= 1000 for p in res.points)  # 瞬时垃圾 5000 零上图
    assert res.totals[-1] == {"t": chain_end, "dl": 1500, "up": 750}  # 末样本真实增量如数入账
    assert not _null_ts(res)  # 活跃链无空值点(旧面 holding/回填面不存在)


def test_tail_group_z_run_zero_line():
    """(改写自旧 F4 z 游程链端延伸例)z 游程尾组: 末点 0 线非 null(空闲观测真值 ——
    「最新已知状态」= 0 速率), t = 末 z 槽 ts, totals 快照同值链不断(首样本基线缺失
    None, 其后 0 增量)"""
    start = NOW
    run = LiveTailRun(kind="z", start=start + 60.0, last_seen=start + 120.0, dl_total=9, up_total=8, samples=4)
    tail = LiveTail(False, False, None, 30, 0.0, (), run)
    slots = v4_live_tail_slots(tail)  # 块首封口形态: [60, 120] 端点含均摊 4 槽
    assert [s.ts for s in slots] == [start + 60.0, start + 80.0, start + 100.0, start + 120.0]
    res = assemble_group_points(slots, start + 130.0 - 120, start + 130.0, 30)
    assert res.stride == 1
    assert res.points[0] == {"t": float(start + 60), "dl": 0, "up": 0}  # 链首 0 线(无缝)
    assert res.points[-1] == {"t": float(start + 120), "dl": 0, "up": 0}  # 尾组 0 线非 null
    assert all(p["dl"] == 0 and p["up"] == 0 for p in res.points)  # 全程 0 线(z 快照冻结)
    assert res.totals[0] == {"t": float(start + 60), "dl": None, "up": None}  # 基线缺失
    assert all(t["dl"] == 0 and t["up"] == 0 for t in res.totals[1:])  # 快照同值 -> delta 0 链不断


def test_stall_no_fabricated_points():
    """(改写自旧 F4 停滞过界例)停滞不造点: 停止进样后推进 now 重装配 —— 点集只在窗沿
    收缩(前缀掉样本), 无新点无空值点, 末点 t/值恒定(诚实滞后; 旧面「尾桶 held 落线/
    过界 null」二态随持有面退役 —— 新契约停滞期数据面不动, 可见性由前端徽标承载)"""
    start = NOW
    recs = tuple(V4Sample(0, 0, 1500 * (k + 1), 750 * (k + 1)) for k in range(20))
    slots = _slots_of(V4Block(start, 1.5, 0, 0, recs))
    end = slots[-1].ts  # = start + 28.5(20 槽: start..start+28.5)
    res_active = assemble_group_points(slots, end + 0.3 - 60, end + 0.3, 1.5)
    assert res_active.points[-1]["t"] == end and res_active.points[-1]["dl"] == 1000
    assert not _null_ts(res_active)
    # 停滞 40s(远超任何旧持有判据界): 无新点无空值点, 末点恒等; 窗沿只收缩(前缀掉样本)
    res_stall = assemble_group_points(slots, end + 40.3 - 60, end + 40.3, 1.5)
    assert res_stall.points[-1] == res_active.points[-1]
    assert not _null_ts(res_stall)
    assert len(res_stall.points) == 14  # t0 = start+8.8: 样本 @start+9..28.5 在窗(前缀 6 样本掉出)
    assert set(p["t"] for p in res_stall.points) <= set(p["t"] for p in res_active.points)  # 只收缩


def test_disconnect_n_run_explicit_null_endpoint():
    """(改写自旧 F4 断连不延伸例)断连 = 显式空值点收尾: n 游程折叠一点(t = floor 首槽),
    之后无任何真值点(无持有克隆; 旧面「末槽 obs None 不延伸」的诚实语义由显式空值点
    承载 —— §03/E3 断连徽标依赖)"""
    start = NOW
    blk = V4Block(
        start,
        2,
        100,
        50,
        (V4Sample(0, 0, 100, 50), V4Sample(0, 0, 300, 150), V4NullRun(3, dt_ms=9000)),
    )
    res = assemble_group_points_from_blocks((blk, ), start, start + 40, 2)
    assert res.points[-1] == {"t": start + 5, "dl": None, "up": None}  # n 首槽 @start+5 取整
    assert res.totals[-1] is None
    assert len(res.points) == 3  # 两真值点 + 一空值点(无持有克隆尾随)
    assert res.points[1] == {"t": float(start + 2), "dl": 100, "up": 50}  # 真值差分 200/100 over 2s


def test_window_filter_tail_and_empty_assembly():
    """(承接旧 v4_window_filter_and_empty 的窗尾半边)ts >= t1 槽不消费(窗尾外样本不产
    组点); 无块/空块/全部槽在窗尾后 = 空点列空 totals(天然真空, 空态判据); 窗前种子
    差分基线/窗外标记面由 test_traffic_group_assembly 承接"""
    blk = V4Block(1000, 2, 10, 20, tuple(V4Sample(0, 0, 100 + 50 * k, 50 + 25 * k) for k in range(5)))
    res = assemble_group_points(_slots_of(blk), 1000, 1008, 2)  # 预期 4 样本 -> k=1
    assert [p["t"] for p in res.points] == [1000.0, 1002.0, 1004.0, 1006.0]  # @1008 不消费
    assert assemble_group_points((), 1000, 2000, 2).points == ()  # 无块
    assert assemble_group_points(_slots_of(V4Block(1000, 2, 10, 20, ())), 1000, 2000, 2).points == ()  # 空块
    far = V4Block(5000, 2, 10, 20, (V4Sample(0, 0, 100, 50), ))
    assert assemble_group_points(_slots_of(far), 1000, 2000, 2).points == ()  # 全部槽在窗尾后


def test_known_sequence_end_to_end_assembly():
    """(承接旧 v4_points_known_sequence_end_to_end)天文件文本 -> 解析 -> k=1 逐样本装配
    端到端: 游标 dt 链四形态(显式 dt/缺省/均摊定位/链式自洽)在样本点层复钉; 断连(n)
    与真空(块间)显式空值点分离; 停机洞断链未知(速率 None, totals 真值照记);
    Sigma(totals) = 遥差(字节守恒); 块乱序传入结果一致"""
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
    res = assemble_group_points(v4_series_slots(blocks), 1000, 5001, 30)
    assert res.stride == 1
    assert res.points == (
        {
            "t": 1000.0,
            "dl": 0,
            "up": 0
        },  # r0 链首 0 线(无缝链首, D4)
        {
            "t": 1030.4,
            "dl": 3,
            "up": 3
        },  # r1: delta(100,100)/30.4s(显式漂移对跨)
        {
            "t": 1060.4,
            "dl": 0,
            "up": 0
        },  # z 槽: 快照冻结 -> 0 线链不断
        {
            "t": 1090.4,
            "dl": 0,
            "up": 0
        },
        {
            "t": 1120.4,
            "dl": 0,
            "up": 0
        },
        {
            "t": 1150,
            "dl": None,
            "up": None
        },  # n 游程折叠显式空值点(首槽 1150.9 取整)
        {
            "t": 1211,
            "dl": None,
            "up": None
        },  # 块间真空显式空值点(t = 前块游标终值 1211.4 取整)
        {
            "t": 1211.4,
            "dl": None,
            "up": None
        },  # r2: 未观测 61s > 60s 停机洞 -> 断链未知(totals 真值)
        {
            "t": 5000.0,
            "dl": None,
            "up": None
        },  # r3: 真空断链后基线缺失(停机洞)
    )
    assert res.totals == (
        {
            "t": 1000.0,
            "dl": None,
            "up": None
        },  # 窗首基线缺失
        {
            "t": 1030.4,
            "dl": 100,
            "up": 100
        },  # 1100-1000 / 2100-2000
        {
            "t": 1060.4,
            "dl": 0,
            "up": 0
        },  # z 快照同值 -> 空闲段 delta=0 链不断
        {
            "t": 1090.4,
            "dl": 0,
            "up": 0
        },
        {
            "t": 1120.4,
            "dl": 0,
            "up": 0
        },
        None,  # 空值点
        None,  # 空值点
        {
            "t": 1211.4,
            "dl": 100,
            "up": 100
        },  # 洞后断链未知, totals 真值(1200-1100)
        {
            "t": 5000.0,
            "dl": 100,
            "up": 100
        },  # 1300-1200
    )
    # Sigma(totals) = 遥差(末快照 - 首窗内链基线): 字节守恒
    dl_sum = sum(t["dl"] for t in res.totals if t is not None and t["dl"] is not None)
    assert dl_sum == 300 == 1300 - 1000
    # 块乱序传入: v4_series_slots 按 start_epoch 稳定排序还原时间序, 结果一致
    assert assemble_group_points(v4_series_slots((block2, block1)), 1000, 5001, 30) == res


def test_live_tail_merge_dedup_assembly():
    """(S6 承袭)磁盘部分块 + 活尾槽 == 整块装配(按 ts 去重后逐位相等, 边界无伪真空);
    滞后快照重列已落盘记录被去重(快照与 flush 竞态不重不漏)—— 旧面在 v4_series_points
    活尾合流参数上钉, 新面去重基准 = 磁盘链末槽 ts(traffic_group_cache._tail_slots 同款)"""
    interval = 30
    start = NOW
    recs = (
        V4Sample(100, 50, 1000, 500),
        V4Sample(200, 70, 2000, 800),
        V4ZeroRun(2, 2000, 800),
        V4Sample(150, 60, 2600, 1100),
        V4Sample(90, 40, 3000, 1300),
    )
    full_slots = _slots_of(V4Block(start, interval, 1000, 500, recs))
    res_full = assemble_group_points(full_slots, start - 10, start + 400, interval)
    assert [p["t"] for p in res_full.points] == [float(start + 30 * k) for k in range(6)]  # z 游程 2 槽
    # 中途 flush: 磁盘前 2 条 + 活尾后 3 条(写侧游标 = 整块末槽)
    disk_slots = _slots_of(V4Block(start, interval, 1000, 500, recs[:2]))
    tail = LiveTail(
        block_open=True,
        head_pending=False,
        start_epoch=start,
        interval_s=interval,
        projected_ts=full_slots[-1].ts,
        records=recs[2:],
        open_run=None,
    )
    merged = disk_slots + tuple(s for s in v4_live_tail_slots(tail) if s.ts > disk_slots[-1].ts)
    assert assemble_group_points(merged, start - 10, start + 400, interval) == res_full
    # 滞后快照(重列已落盘的 recs[1]): 去重后仍 == 整块装配
    stale = LiveTail(
        block_open=True,
        head_pending=False,
        start_epoch=start,
        interval_s=interval,
        projected_ts=full_slots[-1].ts,
        records=recs[1:],
        open_run=None,
    )
    merged_stale = disk_slots + tuple(s for s in v4_live_tail_slots(stale) if s.ts > disk_slots[-1].ts)
    assert assemble_group_points(merged_stale, start - 10, start + 400, interval) == res_full


def test_seed_vacuum_null_t0_edge_band_assembly():
    """(承接旧 v4_seed_vacuum_null_t0_edge_band)窗首种子边界带 —— 真空标记 t = int(链终值)
    落 [null_lo, t0) 时: 发射面不产空值点([t0, t1) 界), 断链面仍生效(marked 置位, 链界
    含带内标记); 重启缝接收样本速率 = step x 覆盖 // span(缝秒不进分母): 带内(末槽
    @999.5, 对跨 30.5s)295/148 与带外(末槽 @998.5, 对跨 31.5s)286/143 可区分"""
    recover = V4Block(1030, 30, 10600, 5300, (V4Sample(9, 9, 10600, 5300), V4Sample(8, 8, 11200, 5600)))
    seed = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=29500)))
    res = assemble_group_points(v4_series_slots((seed, recover)), 1000, 1200, 30)
    assert res.stride == 1
    assert not _null_ts(res)  # 真空标记 t = 999 < t0: 不产空值点
    assert res.points == (
        {
            "t": 1030.0,
            "dl": 295,
            "up": 148
        },  # 9000 x 30s // 30.5s = 8852 -> 295(缝 0.5s 不归因)
        {
            "t": 1060.0,
            "dl": 20,
            "up": 10
        },  # 次样本基线恢复 delta(600,300)/30s
    )
    assert res.totals[0] == {"t": 1030.0, "dl": 9000, "up": 4500}  # 窗首组含种子差分(D3)
    # 带外对照(判别力所在): 停机再早 1 秒(末槽 @998.5)—— 对跨 31.5s -> 286/143
    seed2 = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=28500)))
    res2 = assemble_group_points(v4_series_slots((seed2, recover)), 1000, 1200, 30)
    assert not _null_ts(res2)
    assert res2.points[0] == {"t": 1030.0, "dl": 286, "up": 143}
    assert res2.points[1] == {"t": 1060.0, "dl": 20, "up": 10}


def test_lookback_boundary_slots_kept_and_mark():
    """(承接旧 lookback_boundary_slots_kept + null_mark_at_lookback_boundary +
    stale_slot_below_lookback 三例)消费下界(t0 - si - 回看界)判据含等号: 恰在界上的
    观测槽消费(作差分基线 —— 窗内首样本 totals 非 None 可判), 界外槽不消费(基线缺失
    可判); 恰在界上的 n 标记判得(marked 生效 -> 后继样本断链 None)但不产空值点
    (发射面 [t0, t1))"""
    t0 = float(NOW)
    lo = t0 - 60 - _V4_SEAM_LOOKBACK_S  # 消费下界(= group_null_lo 同式)
    base = V4Slot(ts=lo, dt_s=60.0, obs=(0, 0, 100, 50), is_zero=False)  # 恰在界上: 消费
    mark = V4Slot(ts=lo + 60.0, dt_s=60.0, obs=None, is_zero=False)  # n 槽恰在界上带内: 标记判得
    fresh = V4Slot(ts=t0 + 5.0, dt_s=60.0, obs=(0, 0, 300, 150), is_zero=False)  # 窗内样本
    stale = V4Slot(ts=lo - 0.5, dt_s=60.0, obs=(9, 9, 999, 999), is_zero=False)  # 界外: 不消费
    res = assemble_group_points((stale, base, mark, fresh), t0, t0 + 120, 60)
    assert res.stride == 1
    assert res.points == (
        {
            "t": t0 + 5.0,
            "dl": None,
            "up": None
        },  # 跨标记 + 未观测大缝 -> 断链未知(组覆盖 0)
    )
    assert res.totals == ({"t": t0 + 5.0, "dl": 200, "up": 100}, )  # 界上基线槽消费(300-100 / 150-50)
    assert not _null_ts(res)  # 界上标记不产空值点(t < t0)
    # 界外基线对照(判别力): base 挪到界下 0.5s -> 不消费 -> 窗内样本基线缺失(totals 逐向
    # None, 与 res 的 200/100 判别); n 标记判据独立于基线(标记槽自身真空判得)仍生效
    res2 = assemble_group_points(
        (V4Slot(ts=lo - 0.5, dt_s=60.0, obs=(0, 0, 100, 50), is_zero=False), mark, fresh), t0, t0 + 120, 60
    )
    assert res2.points == ({"t": t0 + 5.0, "dl": None, "up": None}, )  # n 标记判得(marked 面) -> 断链未知
    assert res2.totals == ({"t": t0 + 5.0, "dl": None, "up": None}, )


def test_break_flag_and_zero_rate_group_faces():
    """(承接旧 vgo_60 断链旗跨同桶后继槽 + vgo_105 有覆盖断链桶 0 线两例)组内 broke 旗跨
    后继样本存活(e[4] or 累积):
    - 态一: 洞后样本(未观测 > 60s -> delta None, 覆盖不入账)+ 同组重置样本(delta None
      豁免)—— 组覆盖 0 -> 值 None(断链未知 != 0 线; 旗被清成 0 线即红);
    - 态二: 同形但后继为有效 0 差分(有覆盖)-> 组 0 线非 None(判据看覆盖毫秒不看差分和)"""
    t0, t1, si = 1000.0, 1600.0, 1.0  # 预期 600 样本 -> k 初值 2(组 = 两样本; 窗内实落 2 样本)
    seed = V4Slot(ts=999.0, dt_s=1.0, obs=(0, 0, 50, 25), is_zero=False)  # 窗外种子基线
    hole = V4Slot(ts=1062.0, dt_s=1.0, obs=(0, 0, 100, 50), is_zero=False)  # 对跨 63s/声称 1s -> 洞
    reset = V4Slot(ts=1063.0, dt_s=1.0, obs=(0, 0, 50, 25), is_zero=False)  # 重置(delta None 豁免)
    res = assemble_group_points((seed, hole, reset), t0, t1, si)
    assert res.stride == 2
    assert res.points == ({"t": 1063.0, "dl": None, "up": None}, )  # 组覆盖 0 + broke -> None
    assert res.totals == ({"t": 1063.0, "dl": 50, "up": 25}, )  # s1 差分 50/25; s2 重置 None 不出洞
    # 态二: 后继有效 0 差分(有覆盖)-> 0 线非 None(覆盖毫秒判据)
    zero = V4Slot(ts=1063.0, dt_s=1.0, obs=(0, 0, 100, 50), is_zero=False)  # 等值 delta 0, 覆盖 1s
    res2 = assemble_group_points((seed, hole, zero), t0, t1, si)
    assert res2.points == ({"t": 1063.0, "dl": 0, "up": 0}, )  # 有覆盖 -> 0 线(broke 不冒充缺口)
    assert res2.totals == ({"t": 1063.0, "dl": 50, "up": 25}, )


def test_seam_allocation_zero_share_and_balance():
    """(承接旧 fold 摊配份额用例; 提取件直钉)_seam_spread_delta 按覆盖份额取整: span > cov
    的含缝 z 游程台阶按覆盖份额缩放(step_w = step x cov // span), 逐项份额 = step_w x
    累计 // cov_ms —— 小份额项取整为 0 不入桶, 余额(delta = step_w - acc)归接收方;
    字节守恒不变式: 各游程项份额 + 余额 == step_w(缩放后的总量一分不丢)"""
    shares = []

    def add(key, d, share):
        if share:
            shares.append((key, d, share))

    # z 游程 9 槽: 墙钟步 10s / 声称覆盖 5s(含缝对) -> span 100s, cov 50s(8 x 5s + 台阶对 10s,
    # 首槽立游程不进 run_list)
    run_list = [(float(k * 10), 5000, True, float(k * 10)) for k in range(1, 9)]
    delta = _seam_spread_delta(0, 10, 100_000, 50_000, 20_000, 10.0, False, run_list, 0, add)
    assert delta == 1  # 余额 = step_w(5) - acc(4)
    assert shares == [(20.0, 0, 1), (40.0, 0, 1), (60.0, 0, 1), (80.0, 0, 1)]  # 小份额项取整 0 不入桶
    assert sum(s for _, _, s in shares) + delta == 5  # 字节守恒 == step_w


# ======================================================================
# 天游标防线单元(分组点列缓存承袭面, 直构钉防御面契约本体)
# ======================================================================


def test_day_cursor_valid_structural_invalid_paths():
    """(缺口收口)天游标结构一致性校验(_v4_bucket_day_cursor_valid)逐失效面: 天文件
    收缩(starts 超出 blocks)/ 前缀起点被改写 / 停驻块消失或起点不符 / 停驻块记录数缩
    (rec_idx 越界)/ 末消费记录被替换 / 停驻记录非游程型 / slots_done 超游程长 / 块界
    停驻的末消费记录不符 —— 任一不符 = 结构性变化, 调用方整条目冷重建(不得以陈旧游标
    续折)。合法游标两形态(整块边界停驻 / 游程中段停驻)对照 True。"""
    blk1 = V4Block(1000, 2, 100, 50, (V4Sample(10, 5, 100, 50), V4Sample(10, 5, 110, 60), V4ZeroRun(3, 110, 60)))
    blk2 = V4Block(2000, 2, 110, 60, (V4Sample(20, 10, 140, 90), V4ZeroRun(2, 140, 90), V4Sample(5, 5, 150, 95)))

    def mk(**kw):
        cur = _V4BucketDayCursor()
        for k, v in kw.items():
            setattr(cur, k, v)
        return cur

    assert _v4_bucket_day_cursor_valid(mk(starts=(1000, )), (blk1, blk2)) is True  # 块界停驻对照
    assert _v4_bucket_day_cursor_valid(
        mk(
            starts=(1000, ),
            cur_start=2000,
            rec_idx=1,
            slots_done=2,
            last_ts=2001.0,
            run_base=0.0,
            run_spacing=2.0,
            last_rec=blk2.records[1]
        ),
        (blk1, blk2),
    ) is True  # 游程中段停驻对照(slots_done == run_len 上界内)
    assert _v4_bucket_day_cursor_valid(mk(starts=(1000, 2000)), (blk1, )) is False  # 天文件收缩
    assert _v4_bucket_day_cursor_valid(mk(starts=(1000, )), (V4Block(999, 2, 100, 50, blk1.records), )) is False  # 前缀改写
    assert _v4_bucket_day_cursor_valid(mk(starts=(1000, ), cur_start=2000), (blk1, )) is False  # 停驻块消失
    assert _v4_bucket_day_cursor_valid(
        mk(starts=(1000, ), cur_start=2000), (blk1, V4Block(2999, 2, 110, 60, blk2.records))
    ) is False  # 起点不符
    assert _v4_bucket_day_cursor_valid(
        mk(starts=(1000, ), cur_start=2000, rec_idx=9, slots_done=2, last_rec=blk2.records[0]), (blk1, blk2)
    ) is False  # 记录数缩(rec_idx 越界)
    assert _v4_bucket_day_cursor_valid(
        mk(starts=(1000, ), cur_start=2000, rec_idx=0, slots_done=1, last_rec=blk2.records[1]), (blk1, blk2)
    ) is False  # 末消费记录被替换
    assert _v4_bucket_day_cursor_valid(
        mk(starts=(1000, ), cur_start=2000, rec_idx=0, slots_done=1, last_rec=blk2.records[0]), (blk1, blk2)
    ) is False  # 停驻记录非游程型(r 槽无中段续展形态)
    assert _v4_bucket_day_cursor_valid(
        mk(
            starts=(1000, ),
            cur_start=2000,
            rec_idx=1,
            slots_done=9,
            last_ts=2001.0,
            run_base=0.0,
            run_spacing=2.0,
            last_rec=blk2.records[1]
        ),
        (blk1, blk2),
    ) is False  # slots_done 超游程长
    assert _v4_bucket_day_cursor_valid(
        mk(starts=(1000, ), cur_start=2000, rec_idx=2, slots_done=0, last_rec=blk2.records[0]), (blk1, blk2)
    ) is False  # 块界停驻的末消费记录不符
