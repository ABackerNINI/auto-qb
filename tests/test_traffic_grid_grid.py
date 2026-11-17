"""test_traffic_grid_grid 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v4 换代 plan 26-10-05-2200 N1; 26-11-15-1104 F2 点位归属归桶重锚 —— v4 面逐条改判, 改判理由随用例 docstring)

## 测试计划(每个测试函数一条)
- test_build_grid_24h_and_30d: 24h 窗 30s 采样桶宽 = 180(采样整倍加宽, F1)恒 481 桶(floor+1 恒含进行中桶); 30d 窗恒 3600s = 721 桶; 未知窗口 ValueError
- test_build_grid_extended_windows: 1m/5m/30m/3h/6h/12h raw 段窗(桶宽 = 采样整倍: 30/30/30/30/60/90, 桶数 = 跨度/间隔 + 1, F1) + 3d/7d hour 段窗(恒 3600s = 73/169 桶)
- test_build_grid_unaligned_t0_extra_bucket: t0 未对齐栅格时窗首桶提前(floor), 桶数仍 481(floor+1 与相位无关, 180 | 86400 整倍)
- test_build_grid_fractional_interval_kept_not_ceiled: 小数采样间隔桶宽保持采样整倍不取整(1.5s -> 1.5s 桶宽 41 桶; 旧 ceil 口径反转, F1 双几何实证)
- test_build_grid_raw_bucket_cap_high_frequency_sampling: (26-11-15-1104 F1)raw 桶数上限 500 —— 1.5s 采样: 1m -> 1.5s 桶 41 / 5m -> 1.5s 桶 201 / 30m -> 4.5s 桶 401 / 3h -> 22.5s 桶 481 / 6h -> 43.5s 桶与 12h -> 87s 桶与 24h -> 174s 桶各 497-498 随相位(span/B 非整倍, floor+1), 上限恒 <= 500
- test_build_grid_raw_anchor_float_phase_invariant: (issue 26-11-17-0936 治本守阵)raw 窗 t1 保留浮点挂钟 + first 按 interval 网格双向校正对齐 —— 1m/5m 任意 (A mod3, frac) 每拍恰 +interval, 30m 每 3 拍恰 +4.5 且不再出现 0/+4.5 二拍聚簇
- test_build_grid_bucket_cap_exact_500_divisor: (D7/A6 边角)span 恰 500 x si 整数倍的采样(旧分母 501)分母 -1 预留进行中桶位后逐相位 <= 500
- test_build_grid_bucket_cap_exact_500_divisor 相位扫扩满一整桶宽(评审 #4), n 两形态集合 {494,495}/{496,497}/{376} 逐值钉
- test_build_grid_nonpositive_interval_fails_fast: (黄金法则 4)非正 si fail-fast raise(来源链纯 config 派生, 校验单点在 validate_config)
- test_build_grid_raw_bucket_cap_default_sampling_widens: (F1 改判)30s 默认采样整倍加宽表 —— 1m/5m/30m/3h 桶宽仍 30(k=1), 6h -> 60 / 12h -> 90 / 24h -> 180, 桶数 = 跨度/间隔 + 1
- test_build_grid_raw_cap_seed_extension_covers_sample_bucket: (S3 x S2/D3 联动)桶宽恒 >= 采样间隔(F1: 桶宽 = si x k, k >= 1) -> 窗首种子外扩(grid.t0 - grid.interval)恒覆盖 >= 1 个采样桶; 各窗桶数(含进行中桶)<= 500(D7 判据, 分母预留)
- test_floor_buckets_boundary_and_mid_t1_equal_n: (26-11-14-1313 S1a/F3)t1 恰落桶边界 vs 落桶中 n 恒等(反转 R07 ceil 的方波实证)
- test_build_grid_n_phase_invariant_span_multiple_of_interval: (26-11-14-1313 S1a/F3)W mod interval == 0 时 n 不随相位漂移(now 相位扫过一整桶宽 n 恒定, raw 与 hour 两段)
- test_build_grid_day_windows_d4: 6mo/1y(D4 新档) day 段窗 —— 滚动窗涉及本地日期逐日铺格(桶键 = 本地日界 00:00, 6mo = 182d + 首尾日 / 1y 比 6mo 多 183 桶), interval 86400; 90d 不存在; all 拒绝 build_grid(数据面定栅格)
- test_rate_points_null_shape: points 形状 {"t","dl","up"} | null(空桶断线)
- test_v4_points_known_sequence_end_to_end: (F2 改判重锚)已知序列逐桶核对 —— 天文件文本 -> 解析 -> 点位归属桶点: 显式 dt / 缺省 / z 均摊 / n 后链式自洽; 断连/停机 null; 响应 totals 通道(相邻桶快照差分)断链诚实
- test_v4_window_filter_and_empty: (F2 改判重锚)窗口切片/空元组; 窗前槽桶入流(链上下文)且响应被 v4_grid_obs 窗外过滤
- test_v4_series_points_float_interval_keys_single_derivation: (评审 blocker 回归, F2 改判重锚)si=2.4 非 0.5 步进桶宽, 槽点位归属桶键与 buckets 同式派生(first + i x interval 单一表达式), 逐相位全链(rate/totals)无 null 洞; 速率 100/50 = delta/实测对跨(旧 ceil 膨胀消除)
- test_v4_series_points_point_assignment_and_vacuum: (F2 核心)样本按 floor(ts/B)xB 落格 / 跨界样本端点归属 / n 游程折叠 null / 空样本桶 null(旧 D1 宽桶覆盖随桥接退役, T3 有界回填)
- test_v4_series_points_live_tail_merge_dedup: (S6 验收追加)活尾合流 —— 磁盘部分块+活尾 == 整块桶点(无真空 null 点); 滞后快照重列已落盘记录被按 ts 精确去重; 无块纯活尾(z 游程 0 线)照常出点
- test_v4_series_points_exempt_pairs_zero_line_snapshot_kept: (D4 豁免, F2 桶层改判)差分派不出(重置形态)的对不占权重不占覆盖, 桶无差分覆盖且无缝 -> 0 线 + 快照照记; 混合桶豁免不稀释有效差分; 真 null 点不参与
- test_v4_series_points_break_bucket_rate_null_snapshot_kept: (issue 26-10-16-0954 守阵, F2 桶层改判)停机洞断链桶该向出 None(不再是 0/0 伪点), 快照照记 -> 次桶基线不断; 链首桶仍 0 线; 组面全成员未知 -> None
- test_v4_grid_obs_direct_mapping_edges: (F2 改判)v4_grid_obs 直映边界 —— 窗外桶点(链上下文)不消费 / null 点不参与 / 窗内逐键直映(旧权重面退役)
- test_v4_series_points_same_bucket_merge_downstream: (mut-core W2 vsp_75/vsp_120 守阵, F2 改判)同桶多槽(混桶 z+raw / raw+raw)差分一次算定 + 快照竞争 + 覆盖时长活着进下游
- test_v4_series_points_initial_nrun_mark: (vsp_5)序列首槽即 n 槽的断连标记必须发出
- test_v4_series_points_up_channel_independent_differential: (vgo_73/vgo_76 改判)up 通道差分独立累加(逐向独立判定与豁免)
- test_v4_series_points_lookback_boundary_slots_kept: (vsp_59/vsp_60)消费下界边界槽保留 —— 槽 ts 恰达 grid.t0 - interval - 86400 照收(判据含等号)
- test_v4_series_points_same_t_marks_and_obs_sort_stable: (vsp_163; vsp_160 复裁等价)同刻双 null 标记 + 同刻观测点 —— (t, rank) 排序键保序(null 在先)
- test_v4_series_points_break_flag_survives_bucket_second_point: (vgo_60/vgo_62 改判)断链旗跨同桶后继槽(逐向豁免)存活, 不被清成 0 线
- test_v4_series_points_null_mark_at_lookback_boundary_kept: (vsp_43/vsp_155)null 标记恰在链界 —— 下界含等号
- test_v4_series_points_marks_at_window_end_not_emitted: (vsp_44/vsp_156)窗尾整秒标记不发出
- test_v4_series_points_observed_slot_at_window_end_not_consumed: (vsp_52)恰在 t1 的观测槽不消费(ts >= t1)
- test_build_grid_day_window_midnight_anchors: (bg_52/bg_53)day 窗日期集 t1-1 口径
- test_v4_series_points_snapshot_competition_latest_ts_wins: (vgo_80 + vsp_95 合钉, F2 改判)同桶快照竞争 = ts 最晚者胜, 同刻后到者优先(>= 判据)
  (退役)coverage_end_advance 守阵 -> snapshot_competition 的 ts 竞争判据承接;
- test_v4_series_points_broken_bucket_zero_rate_kept_zero: (vgo_105/vgo_117 改判)断链桶有差分覆盖且速率为 0 仍是 0 线(看覆盖毫秒不看差分和)
- test_build_grid_integral_interval_floor_not_raised: (mut-core W2 bg_21)桶宽下限恒 1s
- test_v4_series_points_same_bucket_later_snapshot_wins: (mut-core W2 vsp_96, F2 改判)同桶 raw+raw 差分一次算定 + 快照取 ts 最晚
- test_v4_series_points_three_raw_same_bucket_no_typeerror: (mut-core W2 vsp_97, F2 改判)同桶三条 raw 差分累加/快照末条, 累加器槽位写坏显形
- test_v4_series_points_same_timestamp_later_snapshot_wins: (mut-core W2 vsp_95, F2 改判)同刻双 raw 快照 >= 判据; 同刻对跨 0 不进速率面
- test_v4_series_points_mixed_bucket_raw_priority_keeps_mean: (mut-core W2 vsp_105/vsp_107/vsp_115, F2 改判)z+raw+raw 同桶差分累加, 通道取错值失真
- test_v4_series_points_stale_slot_below_lookback_not_consumed: (T2b)消费下界外槽不消费
- test_v4_series_points_same_bucket_zero_slots_differential_snapshot: (T2b 改判)同桶 z+z: 差分对照 totals 链真值; 快照统一 ts 最晚(旧 z 先到者保留口径退役)
- test_v4_series_points_same_bucket_out_of_order_ts_keeps_latest_snapshot: (T2b)同桶乱序 ts: 快照按实测更晚者; 负对跨不进速率面
- test_v4_series_points_marked_run_not_zero_shape_drops_delta: (T2b 改判槽层)标记后台阶但游程非 z 形 -> 断链 None 不摊配
- test_v4_series_points_pre_window_chain_context_filtered_from_obs: (T2b 改判)窗前链上下文桶入流且响应被窗外过滤(D3 种子差分基线)
- test_v4_seed_vacuum_null_t0_edge_band_chain_break: (issue 26-10-08-0141, F2 改判重锚)窗首种子边界带 —— 标记同界保留, 重启缝接收桶 = step/实测对跨(带内 295 / 带外 286 可区分)

折叠态机与缓存防线单元(S4 缺口收口 26-11-17, 直构钉防御面契约; 集成面等价性归 bucket_cache 主阵):
- test_bucket_index_correction_loops_float_interval: 点位归属双向校正环在非精确二进制
  桶宽(配置 si 任意 float)下的触发实证与键语义不变式(两方向各一对实测触发点)
- test_check_gap_bound_fail_fast_and_default: gap_bound_s 非正/非有限/非数值/bool
  fail-fast + None 缺省 interval x 2 + 显式正值原样
- test_fold_sanitize_window_realignment_defensive: 窗界再对齐防御契约(prev_slot/
  marked_ts 复位 + 游程锚点滑出返回 True + 未立游程哨兵不误判)
- test_fold_emit_window_filters_and_sealed_backfill_source: 发射窗外回填桶过滤(lo/hi
  两向)+ 源桶封口后快照经 sealed 表解析(字节守恒)+ 封口表与累加器均无 KeyError
- test_fold_emit_mark_window_filter: 窗外 null 标记不入发射列(与回填判据面互斥分 fold)
- test_fold_held_at_scan_paths: held 初值降序首扫(越过 holding 桶/越过回填桶/标记清空
  /fallback)
- test_fold_sealed_floor_null_lo_fallback: 链首无观测 + 累加器非空 -> null_lo 兜底定影
- test_fold_seam_allocation_zero_share_and_balance: 接缝摊配份额取整 0 与余额归接收桶
  + 字节守恒(份额和 + delta == step_w)
- test_day_cursor_valid_structural_invalid_paths: 天游标结构校验逐失效面(收缩/改写/
  停驻块消失/记录数缩/末记录替换/非游程停驻/超游程长)+ 合法两形态对照
- test_guard_group_order_fail_fast: 槽组时序倒挂 fail-fast + 正常时序放行

活尾链端延伸 holding 槽响应面(F4, 计划 26-11-14-1313; F2 最小搬运改判):
- test_v4_hold_slot_fills_tail_grid_bucket: 活跃链延伸前尾桶(进行中桶)null(G5 复现),
  传 now 后尾桶恒有观测且值接续末观测桶值(持有面平接 1000/500 —— 旧 750/375 含
  ceil(1.5)=2 膨胀, F2 精确对跨消除); now=None 缺省响应面与现状一致
- test_v4_hold_slot_rate_face_holds_last_bucket_rate: 尾桶值 = 上一非持有观测桶的桶速率
  (carry-forward)—— 非 0 假跌零亦非 qB 瞬时直采值(假跳升)
- test_v4_hold_slot_totals_chain_untouched: 两相位 totals 面不变式 —— 与末样本同桶合并
  时逐桶全等(持有面不进差分不稀释); 末样本被窗尾过滤时 holding 桶如数回收真实增量
  (1500/750); 旧 v4_totals_points 桶点级断言随中间层退役(响应 totals 通道承接)
- test_v4_hold_slot_z_run_tail_zero_line: z 游程链端延伸尾桶 0 线非 null(空闲观测持有)
- test_v4_hold_slot_stall_over_bound_tail_stays_null: 间隙过界(停滞)尾桶保持 null
- test_v4_hold_slot_merge_with_real_sample_deholds: holding 槽与真实观测槽同桶合并 ->
  合并桶 is_hold=False, 桶值由差分一次算定

几何解耦助手(R1 改判, plan webui-traffic-root-revamp F1): _grid_30s / _grid_1m_2s 直构
WindowGrid 钉语义电池的固定栅格 —— F1 后 24h@30s 桶宽 = 180、1m@1.5s 桶宽 = 1.5, 旧
30s/2s 栅格不再是 build_grid 的可达形; 归桶/差分/摊配/holding 语义电池钉的是既定栅格上的
行为而非桶宽规则, 直构解耦

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
    _V4BucketDayCursor,
    _V4SeriesFold,
    _bucket_delta,
    _bucket_index,
    _check_gap_bound,
    _floor_buckets,
    _guard_group_order,
    _v4_bucket_day_cursor_valid,
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


def _grid_30s(now):
    """(R1 改判, plan webui-traffic-root-revamp F1)语义电池固定 30s 桶的 24h 形栅格:
    F1 后 build_grid 的 24h 桶宽 = 采样整倍(30s 采样 -> 180s), 旧 30s/24h 栅格不再是任何
    采样的可达形 —— 归桶/差分/摊配语义电池钉的是既定栅格上的行为而非桶宽规则, 直构
    WindowGrid 解耦几何(S1b 归桶重锚时再随新几何重钉)"""
    t1 = int(now)
    t0 = t1 - 86400
    return WindowGrid("24h", t0, t1, 30, "raw", _floor_buckets(t0, t1, 30))


def _grid_1m_2s(now):
    """(R1 改判, 同 _grid_30s)holding 电池固定 2s 桶的 1m 形栅格: F1 后 1m@1.5s 桶宽 = 1.5,
    旧「1.5s 采样 ceil 到 2s 桶」栅格不可达 —— 直构解耦(holding/差分语义不变)"""
    t1 = int(now)
    t0 = t1 - 60
    return WindowGrid("1m", t0, t1, 2, "raw", _floor_buckets(t0, t1, 2))


def test_build_grid_24h_and_30d():
    """24h 窗 30s 采样桶宽 = 180(采样整倍加宽 k=6, 26-11-15-1104 F1 替换旧 max(ceil(si),
    ceil(span/2880)) 取整口径 —— 反转理由: 桶边须与采样节拍同律, 双几何实证见该计划 §02)
    恒 481 桶(floor+1 恒含进行中桶, 26-11-14-1313 F3 反转 R07 ceil 口径);
    30d 窗恒 3600s = 721 桶; 未知窗口 ValueError"""
    g = build_grid("24h", NOW, 30.0)
    assert g.interval == 180 and g.segment == "raw" and g.t1 == NOW and g.t0 == NOW - 86400
    assert len(g.buckets) == 481
    assert g.first == ((NOW - 86400) // 180) * 180
    assert g.buckets[1] - g.buckets[0] == 180 and g.last == g.first + 480 * 180  # 尾桶 = 进行中桶(t1 起)
    h = build_grid("30d", NOW, 999.0)  # sample_interval 只在 raw 段生效
    assert h.interval == 3600 and h.segment == "hour" and len(h.buckets) == 721
    assert h.first == ((NOW - 2592000) // 3600) * 3600
    with pytest.raises(ValueError):
        build_grid("90d", NOW)  # 窗口集外(7d 已随 2026-10-04 十档窗口入库, 合法)


def test_build_grid_extended_windows():
    """扩展十档窗口(2026-10-04, 与 qB 速度图对齐 + 3d/7d 外延): raw 段窗桶宽 = 采样整倍
    (26-11-15-1104 F1: 1m/5m/30m/3h span<=500x30 恰 k=1 桶宽 30, 6h k=2 -> 60, 12h k=3 -> 90),
    hour 段窗(3d/7d)恒 3600s; 采样间隔只在 raw 段生效; 桶数 = 跨度/间隔 + 1(26-11-14-1313
    F3 floor+1 恒含进行中桶; 各窗 span 恰为桶宽整倍 -> 桶数与相位无关)"""
    for name, span, iv in (
        ("1m", 60, 30), ("5m", 300, 30), ("30m", 1800, 30), ("3h", 10800, 30), ("6h", 21600, 60), ("12h", 43200, 90)
    ):
        g = build_grid(name, NOW, 30.0)
        assert g.interval == iv and g.segment == "raw" and g.t0 == NOW - span, name
        assert len(g.buckets) == span // iv + 1, name  # NOW 与 t0 均为 iv 的公倍数: +1 进行中桶
    for name, span in (("3d", 259200), ("7d", 604800)):
        h = build_grid(name, NOW, 999.0)  # sample_interval 只在 raw 段生效
        assert h.interval == 3600 and h.segment == "hour" and len(h.buckets) == span // 3600 + 1, name
        assert h.first == ((NOW - span) // 3600) * 3600, name


def test_build_grid_unaligned_t0_extra_bucket():
    """t0 未对齐栅格时窗首桶提前到 floor(t0/interval), 桶数仍 481(26-11-14-1313 F3:
    floor+1 桶数与相位无关; 26-11-15-1104 F1 后 24h@30s 桶宽 180, 180 | 86400 整倍 ->
    对齐/未对齐恒等)"""
    now = NOW + 13  # t0 = now-86400 落在桶中间
    g = build_grid("24h", now, 30.0)
    assert len(g.buckets) == 481
    assert g.first == ((now - 86400) // 180) * 180
    assert g.last < now <= g.last + 180  # 尾桶 = 进行中桶(含 t1)


def test_build_grid_fractional_interval_kept_not_ceiled():
    """(26-11-15-1104 F1 改判)小数采样间隔桶宽保持采样整倍不取整: 1.5s -> 1.5s 桶宽
    (旧口径 ceil 到 2s —— 反转理由: 桶边与采样行错位正是双几何根缺陷的展示面, 桶宽 =
    采样整倍后点位归属与桶边同律)。桶数 = 41(60/1.5 = 40 整倍 + 1 进行中桶, F3);
    24h 窗同采样间隔被桶数上限加宽到 174s 桶(见下方上限用例)"""
    g = build_grid("1m", NOW, 1.5)
    assert g.interval == 1.5
    assert len(g.buckets) == 41
    assert g.last == NOW <= g.last + 1.5  # 尾桶恒为进行中桶(floor(t1/interval) 对齐)
    assert g.buckets[1] - g.buckets[0] == 1.5  # 半秒宽: 桶键为 x.0/x.5 浮点


def test_build_grid_integral_interval_floor_not_raised():
    """(mut-core W2 bg_21)桶宽下限恒 1s: 采样间隔 1.0 时 1m/5m 桶宽恰 1(k = ceil(span/500)
    = 1, F1 采样整倍口径); 30m span/500 = 3.6 -> k=4 桶宽 4(旧口径无上限约束 1801 桶,
    F1 桶数上限 500 收敛到 451 —— 反转理由见 plan webui-traffic-root-revamp F1/D7);
    桶数 +1(26-11-14-1313 F3 floor+1 恒含进行中桶)"""
    for name, n in (("1m", 61), ("5m", 301)):
        g = build_grid(name, NOW, 1.0)
        assert g.interval == 1 and len(g.buckets) == n, name
    g = build_grid("30m", NOW, 1.0)
    assert g.interval == 4 and len(g.buckets) == 451


def test_build_grid_raw_bucket_cap_high_frequency_sampling():
    """(计划 26-11-15-1104 F1/D7 桶数上限 500)raw 桶宽 = 采样间隔 x k, k = ceil(span/(500 x si)):
    1.5s 采样下 1m -> 1.5s 桶恒 41 / 5m -> 1.5s 桶恒 201 / 30m -> 4.5s 桶恒 401 /
    3h -> 22.5s 桶恒 481(以上 span 恰为桶宽整倍, 桶数单值); 6h -> 43.5s 桶 / 12h -> 87s 桶 /
    24h -> 174s 桶 —— span/B = 496.55 非整倍, floor+1 下桶数 497-498 随轮询相位波动
    (上限恒 <= 500; 整倍窗桶数恒定)"""
    for name, iv, n in (("1m", 1.5, 41), ("5m", 1.5, 201), ("30m", 4.5, 401), ("3h", 22.5, 481)):
        g = build_grid(name, NOW, 1.5)
        assert g.interval == iv and len(g.buckets) == n, name
    for name, iv in (("6h", 43.5), ("12h", 87), ("24h", 174)):
        g = build_grid(name, NOW, 1.5)
        assert g.interval == iv and len(g.buckets) in (497, 498), name  # 非整倍窗: 相位波动幅度 1
        assert len(g.buckets) <= MAX_RAW_BUCKETS  # 上限恒 <= 500


def test_build_grid_raw_anchor_float_phase_invariant():
    """(issue 26-11-17-0936 治本守阵)旧 t1=int(now) 整秒截断与 si=1.5s 轮询混叠: 1m/5m
    窗起点按 (int(now₀) mod3, frac) 出 +3.0/0.0 二拍, 30m 出 0/+4.5 的 2~3 拍聚簇。
    治本后 t1 直接取浮点挂钟、_floor_anchor 按 interval 网格双向校正 —— 逐拍真算:
    1m/5m 任意相位 first 每拍恰 +interval; 30m 每 3 拍恰 +4.5(0/0/4.5 均匀轮转),
    且不再出现旧机制的 +4.5/0/+4.5 二拍交替。整点输入语义不变(t1 == now 数值)。"""
    si = 1.5
    for window, span in (("1m", 60), ("5m", 300)):
        interval = build_grid(window, 1_000_000.0, si).interval
        for base in range(1_000_000, 1_000_006):  # mod3 全覆盖(含旧别名正反相位)
            for frac in (0.0, 0.4, 0.5, 0.7, 0.9):
                grids = [build_grid(window, base + frac + si * k, si) for k in range(7)]
                for k, g in enumerate(grids):
                    assert g.t1 == base + frac + si * k  # 不再整秒截断
                    assert len(g.buckets) == span // interval + 1
                    assert g.first <= g.t0 < g.first + g.interval
                    assert g.last <= g.t1 < g.last + g.interval
                deltas = [round(grids[k].first - grids[k - 1].first, 6) for k in range(1, 7)]
                assert deltas == [interval] * 6, (window, base, frac, deltas)

    window = "30m"
    interval = build_grid(window, 1_000_000.0, si).interval
    assert interval == 4.5
    for base in range(1_000_000, 1_000_009):  # mod9 全覆盖(含旧 2~3 拍聚簇相位)
        for frac in (0.0, 0.7):
            grids = [build_grid(window, base + frac + si * k, si) for k in range(10)]
            for g in grids:
                assert len(g.buckets) == 401
                assert g.last <= g.t1 < g.last + g.interval
            deltas = [round(grids[k].first - grids[k - 1].first, 6) for k in range(1, 10)]
            assert all(d in (0.0, interval) for d in deltas), (base, frac, deltas)
            for start in range(0, 7):  # 任意连续 3 拍 = 1 格, 均匀无聚簇
                assert round(sum(deltas[start:start + 3]), 6) == interval, (base, frac, start, deltas)
            assert not any(  # 旧二拍交替的判别式: +格 / 0 / +格
                deltas[i] == interval and deltas[i + 1] == 0.0 and deltas[i + 2] == interval
                for i in range(len(deltas) - 2)
            ), (base, frac, deltas)


def test_build_grid_raw_bucket_cap_default_sampling_widens():
    """(26-11-15-1104 F1 改判)30s 默认采样整倍加宽表: 旧口径 max(30, ceil(span/2880)) 数学
    恒等桶宽恒 30 —— 反转: 桶宽 = 30 x k, k = ceil(span/15000), 6h/12h/24h 依次 k=2/3/6 ->
    桶宽 60/90/180, 桶数收敛到 <= 481(上限 500 治理所有部署, 不只高频采样)"""
    assert MAX_RAW_BUCKETS == 500
    for name, span, iv in (
        ("1m", 60, 30),
        ("5m", 300, 30),
        ("30m", 1800, 30),
        ("3h", 10800, 30),
        ("6h", 21600, 60),
        ("12h", 43200, 90),
        ("24h", 86400, 180),
    ):
        g = build_grid(name, NOW, 30.0)
        assert g.interval == iv, name
        assert len(g.buckets) == span // iv + 1, name


def test_build_grid_bucket_cap_exact_500_divisor():
    """(26-11-15-1104 D7/A6 边角电池)span 恰为 500 x si 整数倍的采样(旧分母下 k 使 span/桶宽
    = 500 -> 含进行中桶 501, 越判据)—— 分母取 上限-1 预留进行中桶位后恒 <= 500:
    si=2.4 24h 旧 B=172.8 n=501 -> 新 B=175.2; si=1.728 24h 旧 B=172.8 n=501 -> 新 B=174.528;
    si=7.2 3h 旧 B=21.6 n=501 -> 新 B=28.8。相位扫满一整桶宽(评审 #4: 短扫跨不过 n 翻形
    边界, docstring 声明的两形态实际只钉到低形态)—— 上界恒 <= 500 + n 两形态集合逐一钉
    (非整倍窗 n 在 floor(span/B)+1/+2 两值随相位翻转, 整倍窗恒单值)"""
    for si, window, n_forms in ((2.4, "24h", {494, 495}), (1.728, "24h", {496, 497}), (7.2, "3h", {376})):
        iv = build_grid(window, NOW, si).interval
        seen = set()
        for phase in range(0, math.ceil(iv) + 1):  # 扫满一整桶宽: 翻形边界两侧都入钉
            g = build_grid(window, NOW + phase, si)
            assert len(g.buckets) <= MAX_RAW_BUCKETS, (si, window, phase)  # D7: 最大 500 桶(含进行中桶)
            seen.add(len(g.buckets))
        assert seen == n_forms, (si, window, seen)  # 两形态(或整倍窗单值)逐值钉
    g = build_grid("24h", NOW, 2.4)
    assert g.interval == 175.2 and len(g.buckets) <= 500  # 2.4 x ceil(86400/1197.6) = 175.2
    assert g.last < NOW + 1 <= g.last + g.interval  # 尾桶恒为进行中桶


def test_v4_series_points_float_interval_keys_single_derivation():
    """(评审 blocker 回归, 26-11-15-1104 F2 改判重锚)非 0.5 步进桶宽(si=2.4)下样本槽的点位
    归属桶键与 grid.buckets 必须同式派生(first + i x interval 单一表达式, _bucket_index 校正
    后取键)—— 修复前两条浮点舍入路径键差 1 ulp, obs.get 失配把有观测的桶经
    rate_points/series_totals_points 全链渲染成 null 洞(si=2.4 @1m 实测最多 11/26 桶 null)。
    F2 后槽键即桶键(单几何), 逐相位扫(0.1s 步进跨 2.4s 主周期)全链无 null 洞:
    有观测桶 rate/totals 非 null 且速率恒 100/50(delta 240/120 ÷ 实测对跨 2.4s —— 旧口径
    delta/w(ceil(2.4)=3) = 80/40 的 ceil 膨胀随覆盖桶宽退役一并消除)"""
    for phase in range(0, 48):
        now = NOW + phase / 10.0
        g = build_grid("1m", now, 2.4)
        assert g.interval == 2.4
        start = float(g.first) + g.interval  # 采样行与桶边同律: 首槽 = 第 1 桶起点, 每桶恰一条
        recs = tuple(V4Sample(100, 50, 240 * (k + 1), 120 * (k + 1)) for k in range(20))
        blk = V4Block(start, 2.4, 0, 0, recs)
        pts = v4_series_points((blk, ), g)
        obs = v4_grid_obs(pts, g)
        assert g.buckets[1] in obs and obs[g.buckets[1]] == BucketObs(0, 0, 240, 120)  # 链首桶 0 线(D4)
        covered = g.buckets[2:20]  # 桶 2..19: 差分对端点归属(每桶恰一对 delta 240/2.4s)
        for j, b in enumerate(covered):
            assert b in obs, (phase, j, "键失配: 有观测桶不在观测表(修复前 1 ulp 双舍入路径)")
            assert (obs[b].dl_rate, obs[b].up_rate) == (100, 50), (phase, j)
        assert rate_points(obs, g)[2:20] == [{
            "t": b,
            "dl": 100,
            "up": 50
        } for b in covered], (
            phase,
            "rate_points 全链 null 洞",
        )
        tots = series_totals_points(obs, g)
        assert all(tots[g.buckets.index(b)] is not None for b in covered[1:]), (phase, "totals 断链洞")


def test_build_grid_nonpositive_interval_fails_fast():
    """(黄金法则 4)si 来源链 = 纯 config 派生(validate_config 保证 multiplier >= 1 x
    main_tick >= 0.5), build_grid 对非正值 fail-fast raise 而非静默兜底 —— 0 间隔若静默
    落 DEFAULT 会把装配缺陷藏进「看起来正常」的 30s 栅格"""
    for bad in (0, 0.0, -1.5):
        with pytest.raises(ValueError):
            build_grid("1m", NOW, bad)


def test_build_grid_raw_cap_seed_extension_covers_sample_bucket():
    """(S3 x S2/D3 联动)桶宽恒 >= 采样间隔(F1: 桶宽 = si x k, k >= 1) —— S2 的窗首
    种子外扩量(grid.t0 - grid.interval)因此恒覆盖 >= 1 个采样桶, 种子点总能取到前驱桶点
    作差分基线; 各窗桶数(含进行中桶)被 500 兜住 —— 分母 = 上限 - 1 预留进行中桶位(D7/A6
    「最大 500 桶」判据, 见 MAX_RAW_BUCKETS 注)"""
    for name in ("1m", "5m", "30m", "3h", "6h", "12h", "24h"):
        for si in (1.5, 2.0, 30.0):
            g = build_grid(name, NOW, si)
            assert g.interval >= si, (name, si)  # 桶宽 = si x k, k >= 1 -> 种子外扩覆盖采样桶
            assert len(g.buckets) <= MAX_RAW_BUCKETS, (name, si)  # 含进行中桶恒 <= 上限(D7 判据)
    g = build_grid("24h", NOW, 1.5)
    assert g.interval == 174  # 1.5 x ceil(86400/750) = 174: 种子外扩 174s 覆盖 >= 1 个 1.5s 采样桶


def test_floor_buckets_boundary_and_mid_t1_equal_n():
    """(26-11-14-1313 S1a/F3)t1 恰落桶边界 vs 落桶中: n 恒等(floor+1 恒含进行中桶)。
    反转 26-10-11-0207 R07 的 ceil 拍板: t1 = int(now) 整秒截断 + 首桶 floor 对齐 ->
    t1 - first 一半时间恰落桶边界, ceil 下 n 在 k/k+1 方波随轮询相位翻转(生产同构桩实测
    跨度 58s<->60s) -> 前端 rewin 误判跳窗 + split 集每拍重推; floor+1 后任意相位恒 k+1。
    构造: 跨度 W=200 为 interval=100 整倍, t1 = t0 + W + 相位(相位扫过 [0, I))"""
    assert _floor_buckets(100, 300, 100) == (100, 200, 300)  # t1 恰落边界: 尾桶 = 进行中桶(t1 起)
    assert _floor_buckets(100, 350, 100) == (100, 200, 300)  # t1 落桶中: 同 n
    assert _floor_buckets(100, 399, 100) == (100, 200, 300)  # t1 落桶中(差 1s 到边界): 仍同 n


def test_build_grid_n_phase_invariant_span_multiple_of_interval():
    """(26-11-14-1313 S1a/F3)W mod interval == 0 时 n 不随相位漂移: now 相位扫过一整个桶宽,
    n 恒定且尾桶恒为进行中桶(floor(t1/interval) 对齐) —— ceil 旧口径下 n 在 k/k+1 方波翻转
    (G4 实证: split 数 11<->12 翻转 39 次/20 拍)。raw 与 hour 两分支共用 _floor_buckets,
    两段各钉一次"""
    for window, span in (("1m", 60), ("5m", 300), ("24h", 86400)):
        for phase in range(0, 180):  # 相位扫过最大桶宽 180(24h@30s, F1): 恒整倍 -> n 恒定
            g = build_grid(window, NOW + phase, 30.0)
            assert len(g.buckets) == span // g.interval + 1, (window, phase)
            assert g.last == ((NOW + phase) // g.interval) * g.interval, (window, phase)  # 尾桶恒为进行中桶
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


def test_rate_points_null_shape():
    """points 形状(§08): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)"""
    g = build_grid("24h", NOW, 30.0)
    base = g.buckets[10]  # 任意栅格桶键(F1 后桶宽 180, 不再假设 30s 步进)
    obs = {base: BucketObs(1, 2, 3, 4)}
    assert rate_points(obs, g)[g.buckets.index(base)] == {"t": base, "dl": 1, "up": 2}
    assert rate_points(obs, g)[g.buckets.index(base) + 1] is None


def test_v4_points_known_sequence_end_to_end():
    """已知序列逐桶核对(验收: 三端点数据对照; 26-11-15-1104 F2 改判重锚) —— 天文件文本 ->
    解析 -> 点位归属桶点, 每桶 rate/totals/时间正确; 游标 dt 链四形态在桶点层复钉:
    显式 dt(r1)/缺省(r0,r3)/均摊定位(z 槽)/链式自洽(n 游程后首 r 以游程终点为基准);
    断连与停机两语义分离(null 标记); 速率 = 桶内样本差分和 / 覆盖时长一次算定
    (旧 cell ceil(ts)-w 键与 v4_totals_points 中间层随双几何退役)"""
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
    g = WindowGrid("5m", 1000, 5001, 30, "raw", _floor_buckets(1000, 5001, 30))
    points = v4_series_points(blocks, g)
    # 桶键 = floor(ts/B)xB 点位归属(栅格单几何); 速率 = 差分和 / 覆盖时长
    assert [_p(p) for p in points] == [
        (990, 0, 0, 1000, 2000, 0.0),  # r0 @1000 落格 990(点位归属): 链首 0 线(D4), 快照照记
        (1020, 3, 3, 1100, 2100, 30.4),  # r1: delta(100,100)/30.4s(显式漂移对跨)
        (1050, 0, 0, 1100, 2100, 30.0),  # z 槽1 @1060.4: 快照冻结 -> 0 线链不断
        (1080, 0, 0, 1100, 2100, 30.0),  # z 槽2 @1090.4
        (1110, 0, 0, 1100, 2100, 30.0),  # z 槽3 @1120.4(游程实测终点)
        (1150, None, None, None, None, 0.0),  # n 游程折叠为单个 null 点(首槽 1150.9 取整)
        (1200, None, None, 1200, 2200, 0.0),  # r2 @1211.4: 未观测 61s > 60s 停机洞 -> 断链 None
        (1211, None, None, None, None, 0.0),  # 块间真空 null 点(t = 前块游标终值 1211.4 取整)
        (4980, None, None, 1300, 2300, 0.0),  # r3 @5000: 真空断链后基线缺失(停机洞)
    ]
    # 响应 totals 通道(相邻桶快照差分): 断连/真空段空桶断链, 诚实不造数
    obs = v4_grid_obs(points, g)
    tots = series_totals_points(obs, g)
    by_t = {e["t"]: e for e in tots if e is not None}
    assert by_t[990] == {"t": 990, "dl": None, "up": None}  # 窗首基线缺失
    assert by_t[1020] == {"t": 1020, "dl": 100, "up": 100}  # 1100-1000 / 2100-2000
    assert by_t[1050] == {"t": 1050, "dl": 0, "up": 0}  # z 快照同值 -> 空闲段 delta=0 链不断
    assert by_t[1080] == {"t": 1080, "dl": 0, "up": 0}
    assert by_t[1110] == {"t": 1110, "dl": 0, "up": 0}
    assert all(tots[g.buckets.index(b)] is None for b in (1140, 1170, 1230))  # n 游程/真空段无观测 = 桶缺位
    assert tots[g.buckets.index(1200)] == {"t": 1200, "dl": None, "up": None}  # r2 桶有观测但断链后基线缺失
    assert tots[g.buckets.index(4980)] == {"t": 4980, "dl": None, "up": None}  # 真空断链后基线缺失
    # 块乱序传入: 按 start_epoch 稳定排序还原时间序, 结果一致
    assert v4_series_points((block2, block1), g) == points


def test_v4_series_points_same_bucket_later_snapshot_wins():
    """(mut-core W2 vsp_96)同桶 raw+raw: 差分一次算定、快照取 ts 最晚者。totals 数值大于
    ts 时, 比较对象错成 totals(e[5])恒假 -> 快照永不更新"""
    slots = (
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.9, 1.0, (15, 21, 4000, 5000), False),
    )
    grid = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((), grid, tail_slots=slots)
    assert [_p(p) for p in points] == [(998, 2500, 2500, 4000, 5000, 0.4)]  # delta 1000/0.4s


def test_v4_series_points_three_raw_same_bucket_no_typeerror():
    """(mut-core W2 vsp_97)同桶三条 raw: 差分累加三条、快照取末条 —— 累加器槽位被写成
    None 时后继对的比较/累加会 TypeError 或值失真"""
    slots = (
        V4Slot(998.2, 1.0, (4, 8, 2000, 3000), False),
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.9, 1.0, (6, 10, 4000, 5000), False),
    )
    grid = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((), grid, tail_slots=slots)
    assert [_p(p) for p in points] == [(998, 2857, 2857, 4000, 5000, 0.7)]  # delta 2000/0.7s


def test_v4_series_points_same_timestamp_later_snapshot_wins():
    """(mut-core W2 vsp_95)同刻双 raw 记录: 快照取后到者(>= 变异成 > 会保留先到者);
    同刻对跨 0 不进速率面(覆盖时长 > 0 判据, 旧瞬时均值语义随 cell 几何退役)"""
    slots = (
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.5, 1.0, (15, 21, 4000, 5000), False),
    )
    grid = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((), grid, tail_slots=slots)
    assert [_p(p) for p in points] == [(998, 0, 0, 4000, 5000, 0.0)]


def test_v4_series_points_mixed_bucket_raw_priority_keeps_mean():
    """(mut-core W2 vsp_105/vsp_107/vsp_115 改判)z+raw+raw 三连同桶: 差分面全槽入账
    (z 对 delta 0 / z->raw 台阶真值; 旧「raw 优先覆盖 z」的 cell 合并旗随 cell 几何退役
    —— F2 点位归属下同桶各差分对逐条累加), 快照取 ts 最晚者; 通道取错(up 当 dl)值失真"""
    slots = (
        V4Slot(998.2, 1.0, (0, 0, 1000, 2000), True),
        V4Slot(998.5, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.9, 1.0, (15, 21, 4000, 5000), False),
    )
    grid = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((), grid, tail_slots=slots)
    assert [_p(p) for p in points] == [(998, 4286, 4286, 4000, 5000, 0.7)]  # delta 3000/0.7s


def test_v4_window_filter_and_empty():
    """窗口切片(F2 改判重锚): ts >= t1 槽不消费 / 窗口左界侧保留全部块内槽桶(链上下文,
    P2 回看: 差分链需完整陈旧跨度, 响应由 v4_grid_obs 栅格过滤承载) / null 点按同界过滤 /
    无块 = 空元组(停机天然真空)"""
    b1 = V4Block(500, 30, 1, 1, (V4Sample(1, 1, 1, 1), V4Sample(1, 1, 1, 1)))  # @500/@530(窗前, 回看保留)
    b2 = V4Block(1000, 30, 2, 2, (V4Sample(2, 2, 2, 2), V4Sample(3, 3, 3, 3), V4NullRun(2)))  # @1000/@1030/n
    b3 = V4Block(2000, 30, 4, 4, (V4Sample(4, 4, 4, 4), ))  # @2000(t1 之后)
    g = WindowGrid("5m", 1000, 1100, 30, "raw", _floor_buckets(1000, 1100, 30))
    points = v4_series_points((b1, b2, b3), g)
    assert [_p(p) for p in points] == [
        (480, 0, 0, 1, 1, 0.0),  # (P2 回看)b1 链首槽(@500 落格 480): 0 线(链上下文, 不进响应)
        (510, 0, 0, 1, 1, 30.0),  # b1 第二槽(@530 落格 510): delta 0 / 30s(窗前桶, 链上下文)
        (530, None, None, None, None, 0.0),  # b1->b2 块间真空标记(t = int(530))
        (990, None, None, 2, 2, 0.0),  # @1000 落格 990: 停机洞(未观测 440s > 60s)断链 None, 快照照记
        (1020, 0, 0, 3, 3, 30.0),  # @1030 落格 1020: delta 1/30s -> 0(基线恢复)
        (1060, None, None, None, None, 0.0),  # n 槽 null 点(首槽 1060.0)
        (1090, None, None, None, None, 0.0),  # b2->b3 真空标记(t=1090 < t1)
    ]
    assert v4_series_points((), g) == ()  # 无块 = 天然真空
    assert v4_series_points((V4Block(1000, 30, None, None, ()), ), g) == ()  # 空块(解析器不产, 防御直构)跳过
    assert v4_series_points((b3, ), g) == ()  # 全部槽在窗尾之后(ts >= t1 不消费)


def test_v4_series_points_point_assignment_and_vacuum():
    """点位归属归桶(F2 核心语义) + 真空/断连分离(承袭): 样本按 floor(ts/B)xB 落格
    (落哪格算哪格) / 跨界样本按端点归属记后继槽所在格(R2 ±1 样本份额差, 不再摊配) /
    n 游程折叠 null 标记(桶无观测 = null)。旧 D1 宽桶跨桶覆盖(中间栅格桶同值非 null)
    与覆盖秒加权随桥接层退役: 空样本桶 = null 承袭(有界持有回填属 T3)。"""
    g = _grid_30s(NOW)
    b0 = g.first + 3000  # 任意栅格桶(3000 为 30 的整倍)
    # 1:1 对齐: 块首槽恰在 b0 -> 桶 b0; 差分端点归属: (b0 -> b0+30) 对记 b0+30 桶
    blk = V4Block(b0, 30, 1000, 500, (V4Sample(10, 20, 1000, 500), V4Sample(20, 40, 2000, 900)))
    pts = v4_series_points((blk, ), g)
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(0, 0, 1000, 500)  # 链首 0 线
    assert obs[b0 + 30] == BucketObs(33, 13, 2000, 900)  # delta(1000,400)/30s = 33/13
    assert b0 - 30 not in obs and b0 + 60 not in obs  # 无观测桶不出现在观测表
    # 跨界样本: r2 显式 dt=45s @T+45 -> 端点归属整对记 T+30 桶(对跨 45s), 不再按重叠秒摊配
    T = b0 + 30
    blk3 = V4Block(
        T, 30, 100, 0, (V4Sample(200, 0, 100, 0), V4Sample(100, 0, 200, 0, dt_ms=45000), V4Sample(50, 0, 300, 0))
    )
    obs3 = v4_grid_obs(v4_series_points((blk3, ), g), g)
    assert obs3[T] == BucketObs(0, 0, 100, 0)  # 链首 0 线(样本 @T 恰在桶首)
    assert obs3[T + 30] == BucketObs(2, 0, 200, 0)  # delta 100/45s = 2.2 -> 2(端点归属 T+45 所在桶)
    assert obs3[T + 60] == BucketObs(3, 0, 300, 0)  # delta 100/30s = 3
    # n 游程折叠: 断连段桶无观测 = null(空桶承载断线), 前后桶观测照常
    blk4 = V4Block(
        T + 300, 30, 900, 0, (V4Sample(9, 9, 900, 0), V4NullRun(2, dt_ms=60000), V4Sample(9, 9, 999, 0, dt_ms=30000))
    )
    obs4 = v4_grid_obs(v4_series_points((blk4, ), g), g)
    assert obs4[T + 300] == BucketObs(0, 0, 900, 0)
    assert T + 330 not in obs4 and T + 360 not in obs4  # n 游程段无观测 -> 空(null)
    assert obs4[T + 390] == BucketObs(
        1, 0, 999, 0
    )  # 标记后短缝摊配回收: span 90s > cov 30s -> 只回收覆盖份额 99/3 -> rate 1(未观测 60s 不归因)


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
    g = WindowGrid("5m", start - 10, start + 400, 30, "raw", _floor_buckets(start - 10, start + 400, 30))
    full = v4_series_points((V4Block(start, interval, 1000, 500, recs), ), g)
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
    merged = v4_series_points(disk, g, tail_slots=v4_live_tail_slots(tail))
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
    merged_stale = v4_series_points(disk, g, tail_slots=v4_live_tail_slots(stale))
    assert merged_stale == full
    # 无块纯活尾(进程首日全空闲, 天文件未产生): z 游程槽出 0 线桶点
    run = LiveTailRun(kind="z", start=start + 60.0, last_seen=start + 120.0, dl_total=9, up_total=8, samples=4)
    tail_only = LiveTail(False, False, None, interval, 0.0, (), run)
    pts = v4_series_points((), g, tail_slots=v4_live_tail_slots(tail_only))
    assert pts and all(p.dl_rate == 0 and p.up_rate == 0 and p.dl_total == 9 for p in pts)
    assert not any(p.dl_rate is None for p in pts)


def _hold_active_fixture():
    """F4 响应面共用地盘: 生产同构节律(1.5s 采样 / 1m 窗 2s 桶宽 —— 桶宽几何现由 _grid_1m_2s
    直构钉住(R1 改判: F1 后 build_grid 1m@1.5s 桶宽 = 1.5), 采样节律仍 1.5s), 稳态流 + 瞬时垃圾
    速率字段(5000/2500, 区间平均恒 750/375)。活尾持最后 3 条未落盘记录(head_pending=
    False 倒推), 链端 = start + 88.5。返回 (disk, tail, chain_end)。"""
    interval = 1.5
    start = 1_800_000_000  # 偶数, 与 2s 桶宽对齐
    recs = tuple(V4Sample(5000, 2500, 1500 * (k + 1), 750 * (k + 1)) for k in range(60))
    chain_end = v4_block_slots(V4Block(start, interval, 0, 0, recs))[-1].ts  # = start + 88.5
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
    return disk, tail, chain_end


def _hold_obs(disk, tail, grid, now, max_gap_s):
    """延伸参数 -> (栅格桶观测, 桶点流)。now=None = 不延伸(现状形态); 走生产同一条
    v4_series_points -> v4_grid_obs 管线(26-11-15-1104 F2: grid 直传, 点位归属归桶 +
    速率一次算定; grid.t1 = int(now) 为窗)。"""
    tail_slots = v4_live_tail_slots(tail) if now is None else v4_live_tail_slots(tail, now=now, max_gap_s=max_gap_s)
    pts = v4_series_points(disk, grid, tail_slots=tail_slots)
    return v4_grid_obs(pts, grid), pts


def test_v4_hold_slot_fills_tail_grid_bucket():
    """(F4, F2 最小搬运改判)活跃链延伸前尾桶 null(G5 复现: 末样本槽 ts=链端 >= t1=int(now)
    被窗尾过滤), 传 now 后 holding 槽豁免过滤 -> 尾桶恒有观测且值接续末观测桶值(持有面
    平接 1000/500 —— 旧口径 750/375 含 ceil(1.5)=2 的桶宽膨胀, F2 精确对跨后消除);
    其余桶与不延伸形态逐桶一致(向后兼容面)。holding 桶键 = grid.last(进行中桶,
    「现在所在格」), 不进差分面(0 delta / 0 覆盖, 不稀释同桶真实观测)"""
    disk, tail, chain_end = _hold_active_fixture()
    now = chain_end + 0.3
    grid = _grid_1m_2s(now)  # (R1 改判)固定 2s 桶几何: holding 语义电池, 见助手注
    assert grid.last == int(chain_end)  # 尾桶 = 刚开启的进行中桶 [t1, t1+2)
    # G5 现状: 不延伸 -> 尾桶无观测(null), 曲线终点收在判定线左侧一格
    obs_old, _ = _hold_obs(disk, tail, grid, None, None)
    assert grid.last not in obs_old
    # F4: 延伸 -> 尾桶恒有观测(P1 上界: max(2, 1.5) x 2 = 4)
    obs_new, _ = _hold_obs(disk, tail, grid, now, 4.0)
    o = obs_new[grid.last]
    assert (o.dl_rate, o.up_rate) == (1000, 500)  # 接续末观测桶值(非 0 非 null; delta 1500/1.5s)
    assert (o.dl_total, o.up_total) == (90000, 45000)  # totals = 末次快照同值
    # 前桶不受扰: 与延伸前逐桶一致(除尾桶外)
    assert {k: v for k, v in obs_new.items() if k != grid.last} == obs_old


def test_v4_hold_slot_rate_face_holds_last_bucket_rate():
    """(F4 速率面语义, F2 改判)尾桶值 = 上一非持有观测桶的桶速率(carry-forward):
    瞬时字段 5000/2500 垃圾值零上图, 桶层一次算定面 1000/500 —— 持有面取后者
    (非差分 0 的假跌零, 亦非瞬时直采的假跳升)"""
    disk, tail, chain_end = _hold_active_fixture()
    now = chain_end + 0.3
    grid = _grid_1m_2s(now)  # (R1 改判)固定 2s 桶几何: holding 语义电池, 见助手注
    obs, pts = _hold_obs(disk, tail, grid, now, 4.0)
    hold_point = pts[-1]
    assert hold_point.is_hold  # 桶点持有旗贯通到输出
    assert (hold_point.dl_rate, hold_point.up_rate) == (1000, 500)
    assert (obs[grid.last].dl_rate, obs[grid.last].up_rate) == (1000, 500)
    assert all(p.dl_rate is None or p.dl_rate <= 1000 for p in pts)  # 瞬时垃圾 5000 零上图


def test_v4_hold_slot_totals_chain_untouched():
    """(F4 诚实性, F2 改判)两相位钉 totals 面不变式:
    - gap 跨整秒相位(末样本槽在窗内): holding 槽与末样本同桶合并 -> is_hold=False,
      速率/快照由真实观测一次算定, 延伸前后栅格桶逐桶全等(持有面不进差分不稀释);
    - gap 不跨整秒相位(末样本槽被窗尾过滤): holding 桶如数回收末样本真实增量(1500/750
      —— 此前该增量整段丢失), 其余桶 delta 与不延伸形态逐桶一致。
    旧 v4_totals_points 桶点级 0 增量/摊配份额断言随中间层退役(响应 totals 通道承接)。"""
    disk, tail, chain_end = _hold_active_fixture()
    # 相位一: gap 1.2 跨整秒(t1 = 89 > 链端 88.5), holding 槽与末样本(@88.5)同桶(88)
    now_a = chain_end + 1.2
    grid_a = _grid_1m_2s(now_a)  # (R1 改判)固定 2s 桶几何, 见助手注
    obs_old_a, pts_old_a = _hold_obs(disk, tail, grid_a, None, None)
    obs_new_a, pts_new_a = _hold_obs(disk, tail, grid_a, now_a, 4.0)
    assert pts_new_a[-1].is_hold is False  # 真实观测在桶 -> 合并桶非 holding
    assert obs_new_a == obs_old_a  # 逐桶全等(速率与 totals 通道零漂移)
    tots_old_a = series_totals_points(obs_old_a, grid_a)
    tots_new_a = series_totals_points(obs_new_a, grid_a)
    assert tots_new_a == tots_old_a
    assert tots_new_a[-1] == {"t": grid_a.last, "dl": 1500, "up": 750}  # 末样本真实增量照常入账
    # 相位二: gap 0.3 不跨整秒(t1 = 88 = int(链端)), 末样本槽被窗尾过滤
    now_b = chain_end + 0.3
    grid_b = _grid_1m_2s(now_b)  # (R1 改判)固定 2s 桶几何, 见助手注
    obs_old_b, pts_old_b = _hold_obs(disk, tail, grid_b, None, None)
    obs_new_b, pts_new_b = _hold_obs(disk, tail, grid_b, now_b, 4.0)
    assert grid_b.last not in obs_old_b
    assert pts_new_b[-1].is_hold  # 纯 holding 桶
    assert (pts_new_b[-1].dl_total, pts_new_b[-1].up_total) == (90000, 45000)  # 快照接住末样本
    assert pts_new_b[-1].w == 0.0  # 持有面非观测: 0 覆盖(旧 w=ceil(gap) 覆盖桶语义退役)
    tots_old = series_totals_points(obs_old_b, grid_b)
    tots_new = series_totals_points(obs_new_b, grid_b)
    assert tots_new[:-1] == tots_old[:-1]
    # 栅格级: 尾桶快照链接住末样本 totals(90000) -> 末样本真实增量(1500/750)如数回收,
    # 不多不少(旧 P2 摊配覆盖份额 750/375 随中间层退役 —— F2 端点归属整对归尾桶)
    assert tots_new[-1] == {"t": grid_b.last, "dl": 1500, "up": 750}


def test_v4_hold_slot_z_run_tail_zero_line():
    """(F4, F2 改判; 26-11-17 治本改判)z 游程链端延伸: 尾桶 0 线非 null(空闲观测持有 ——
    「最新已知状态仍有效」), totals 快照照记; 不延伸时尾桶保持 null(末槽 @120 早于浮点
    t1=+150.5, 但无 holding 槽落到进行中桶 [150,180))。治本前 t1=int(now) 会把
    now=+120.5 截成 +120 而滤掉末槽, 那是整秒截断的副作用而非 F4 诚实边界。"""
    start = 1_800_000_000
    run = LiveTailRun(kind="z", start=start + 60.0, last_seen=start + 120.0, dl_total=9, up_total=8, samples=4)
    tail = LiveTail(False, False, None, 30, 0.0, (), run)
    now = start + 150.5  # 链端 @120, gap 30.5 <= 缺省上界 60; holding 槽落进行中桶 [150,180)
    grid = build_grid("5m", now, 30.0)
    assert grid.t1 == now and grid.last == start + 150
    pts_old = v4_series_points((), grid, tail_slots=v4_live_tail_slots(tail))
    assert grid.last not in v4_grid_obs(pts_old, grid)  # 不延伸: 进行中桶无槽 -> null
    pts = v4_series_points((), grid, tail_slots=v4_live_tail_slots(tail, now=now))
    o = v4_grid_obs(pts, grid)[grid.last]
    assert (o.dl_rate, o.up_rate) == (0, 0)  # 0 线非 null(持有 z 末速率 0)
    assert (o.dl_total, o.up_total) == (9, 8)


def test_v4_hold_slot_stall_over_bound_tail_stays_null():
    """(F4 诚实边界)间隙过界(停滞)不延伸: now - 链端 > 上界 -> 槽序与响应面同不延伸
    形态逐字节一致, 尾桶保持 null(不造数据)"""
    disk, tail, chain_end = _hold_active_fixture()
    now = chain_end + 4.5  # gap 4.5 > P1 上界 4
    grid = _grid_1m_2s(now)  # (R1 改判)固定 2s 桶几何: holding 语义电池, 见助手注
    slots = v4_live_tail_slots(tail, now=now, max_gap_s=4.0)
    assert slots == v4_live_tail_slots(tail) and not any(s.is_hold for s in slots)
    pts = v4_series_points(disk, grid, tail_slots=slots)
    assert grid.last not in v4_grid_obs(pts, grid)


def test_v4_hold_slot_merge_with_real_sample_deholds():
    """(F4 防御面, F2 改判)holding 槽与真实观测槽同桶合并 -> 合并桶 is_hold=False(桶内有
    真实观测, 速率按差分一次算定)—— 持有旗不泄漏进含真实观测的桶(泄漏面: 速率被改写为
    持有值)。几何: 桶宽 2s, 真实槽 @90.5 与 holding 槽(键恒 = grid.last = 90)同桶"""
    start = 1_800_000_000
    first = V4Slot(ts=start + 88.5, dt_s=1.0, obs=(100, 50, 1000, 500), is_zero=False)
    real = V4Slot(ts=start + 90.5, dt_s=2.0, obs=(100, 50, 1600, 800), is_zero=False)
    hold = V4Slot(ts=start + 91.3, dt_s=0.8, obs=(100, 50, 1600, 800), is_zero=False, is_hold=True)
    grid = build_grid("1m", start + 91.4, 2.0)  # 桶宽 2s, t1 = 浮点 now=start+91.4, 尾桶 = start+90
    assert grid.t1 == start + 91.4 and grid.last == start + 90
    pts = v4_series_points((), grid, tail_slots=(first, real, hold))
    assert [p.t for p in pts] == [start + 88, start + 90]
    merged = pts[-1]
    assert not merged.is_hold  # 真实观测入桶 -> 非 holding 桶点
    assert (merged.dl_rate, merged.up_rate) == (300, 150)  # delta(600,300)/2.0s 一次算定
    assert (merged.dl_total, merged.up_total) == (1600, 800)  # 快照取 ts 最晚者(holding 同值)
    assert merged.w == 2.0  # 覆盖时长 = 实测对跨(holding 槽不进差分面)


def test_v4_seed_vacuum_null_t0_edge_band_chain_break():
    """(issue 26-10-08-0141; F2 改判重锚)窗首种子边界带 —— 停机标记与链同界
    (_V4_SEAM_LOOKBACK_S)后带内带外的停机标记均保留, 差分链均正确断开。
    F2 端点归属下重启缝接收桶速率 = step / 实测对跨(覆盖时长 = 差分对跨, 不再 ceil;
    未覆盖秒不归因只在游程内有真实缝时缩放): 带内 9000/30.5s = 295 与带外
    9000/31.5s = 286 可区分(旧口径 300/290 含 ceil 桶宽)"""
    seed = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=29500)))
    recover = V4Block(1030, 30, 10600, 5300, (V4Sample(9, 9, 10600, 5300), V4Sample(8, 8, 11200, 5600)))
    g = WindowGrid("5m", 1000, 1200, 30, "raw", _floor_buckets(1000, 1200, 30))
    pts = v4_series_points((seed, recover), g)
    assert [_p(p) for p in pts] == [
        (960, 0, 0, 1000, 500, 0.0),  # 种子块首槽(链上下文): 0 线, 快照照记
        (990, 20, 10, 1600, 800, 29.5),  # 种子次槽: delta(600,300)/29.5s(窗首差分基线, D3)
        (999, None, None, None, None, 0.0),  # 真空 null 点: t = int(999.5) = t0-1, 同界保留
        (1020, 295, 148, 10600, 5300, 30.0),  # 恢复首点: 重启缝回收 step x 覆盖 // span(覆盖 = 声称 dt 30s)
        (1050, 20, 10, 11200, 5600, 30.0),  # 次桶基线恢复 delta(600,300)/30s
    ]
    # 带外对照(判别力所在): 停机再早 1 秒(末槽 @998.5)—— 标记 t = 998 同界保留,
    # 接收桶对跨 31.5s -> rate 286(误接旧值 300 与带内 295 均可判红)
    seed2 = V4Block(970, 30, 1000, 500, (V4Sample(1, 1, 1000, 500), V4Sample(2, 2, 1600, 800, dt_ms=28500)))
    pts2 = v4_series_points((seed2, recover), g)
    assert [_p(p) for p in pts2] == [
        (960, 0, 0, 1000, 500, 0.0),
        (990, 21, 11, 1600, 800, 28.5),  # delta 600/28.5s = 21.05 -> 21; 300/28.5 = 10.5 -> 11
        (998, None, None, None, None, 0.0),
        (1020, 286, 143, 10600, 5300, 30.0),  # 覆盖 = 接收槽声称 dt 30s: 9000 x 30 // 31.5 = 8571 -> rate 286; up 142.9 -> 143
        (1050, 20, 10, 11200, 5600, 30.0),
    ]


def test_v4_series_points_exempt_pairs_zero_line_snapshot_kept():
    """D4 豁免(26-11-15-1104 F2 后在桶层一次算定内实现, 逐向独立): 差分派不出(重置形态)
    的对不占速率权重也不占覆盖, 桶无任何差分覆盖且无观测缝 -> 0 线 + 快照照记(后续桶
    差分基线不断); 混合桶(豁免对 + 有效对)有效差分照常派出(不稀释不虚 0); 真 null 点
    (n 游程/真空)不参与(桶 null)。旧 v4_grid_obs 豁免权重面随覆盖加权桥接退役。"""
    g = _grid_30s(NOW)
    b0, b1, b2 = g.buckets[100], g.buckets[101], g.buckets[102]
    blk = V4Block(
        b0,
        30,
        1000,
        500,
        (
            V4Sample(10, 10, 1000, 500),  # 链首(基线)
            V4Sample(10, 10, 900, 800, dt_ms=30000),  # @b1: dl 重置(900<1000)-> 豁免; up +300
            V4Sample(20, 10, 1600, 1400, dt_ms=30000),  # @b2: 对重置快照差分 +700/+600
        ),
    )
    pts = v4_series_points((blk, ), g)
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(0, 0, 1000, 500)  # 链首 0 线
    assert obs[b1] == BucketObs(0, 10, 900, 800)  # dl 豁免 -> 0 线(无缝非 broke); up 300/30s = 10
    assert obs[b2] == BucketObs(23, 20, 1600, 1400)  # dl 700/30s = 23.3 -> 23; up 600/30 = 20
    tot = series_totals_points(obs, g)
    assert tot[g.buckets.index(b1)] == {"t": b1, "dl": None, "up": 300}  # 重置桶增量 None(逐向)
    assert tot[g.buckets.index(b2)] == {"t": b2, "dl": 700, "up": 600}  # 快照照记 -> 基线不断
    # 混合桶: 同桶内重置对 + 有效对 —— 有效差分照常派出
    blk2 = V4Block(
        b2,
        30,
        0,
        0,
        (
            V4Sample(10, 10, 2000, 1000),  # @b2 链首
            V4Sample(10, 10, 1000, 900, dt_ms=10000),  # @b2+10: 重置 -> 豁免
            V4Sample(10, 10, 1100, 1000, dt_ms=10000),  # @b2+20: +100/10s(三槽同桶)
        ),
    )
    pts2 = v4_series_points((blk2, ), g)
    obs2 = v4_grid_obs(pts2, g)
    assert obs2[b2] == BucketObs(10, 10, 1100, 1000)  # 100/10s = 10(重置对豁免不稀释; obs 键 = 桶键)
    # 真 null 点仍不参与: 桶无观测 = null
    assert v4_grid_obs((V4PointEntry(b0, None, None, None, None, w=0.0), ), g) == {}
    # 逐向豁免: dl 派不出(up 可派)—— dl 出 0 线, up 正常(对称面由上方 b1 钉)


def test_v4_series_points_break_bucket_rate_null_snapshot_kept():
    """(issue 26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker 守阵, F2 桶层改判)
    断链桶语义: 桶内存在未观测缝(对跨 > 本槽声称覆盖 dt > 60s = 停机洞)且该向无差分
    覆盖 -> None(断链未知 != 0 线; 修复前 0/0 伪点 -> 全窗孤点 + 值域塌缩); 快照照记
    (差分链基线不断); 无观测缝的链首桶(程序/窗口起点)仍保留 D4 的 0 线; 组面同规则"""
    g = _grid_30s(NOW)
    b0, b2 = g.buckets[100], g.buckets[104]  # b2 = b0+120: 缝 120s, 未观测 90s > 60s 洞
    blk1 = V4Block(b0, 30, 1000, 500, (V4Sample(5, 5, 1000, 500), ))
    blk2 = V4Block(b2, 30, 9000, 4000, (V4Sample(9, 9, 9000, 4000), V4Sample(7, 7, 20000, 9000, dt_ms=30000)))
    pts = v4_series_points((blk1, blk2), g)
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(0, 0, 1000, 500)  # 链首 0 线
    assert obs[b2] == BucketObs(None, None, 9000, 4000)  # 断链未知(停机洞) != 0
    assert rate_points(obs, g)[g.buckets.index(b2)] == {"t": b2, "dl": None, "up": None}
    tot = series_totals_points(obs, g)
    assert tot[g.buckets.index(b2)] == {"t": b2, "dl": None, "up": None}  # 跨洞增长不可归因(不造数)
    assert tot[g.buckets.index(b2 + 30)] == {"t": b2 + 30, "dl": 11000, "up": 5000}  # 次桶基线不断
    # 对照: 同形但无观测缝(链路首点, 程序/窗口起点) -> 保留 D4 的 0 线
    blk3 = V4Block(b0, 30, 1000, 500, (V4Sample(5, 5, 1000, 500), V4Sample(5, 5, 1600, 800, dt_ms=30000)))
    obs2 = v4_grid_obs(v4_series_points((blk3, ), g), g)
    assert obs2[b0] == BucketObs(0, 0, 1000, 500)
    # 组面: 全成员该向未知 -> None(断链未知不冒充 0 值点); 有成员已知 -> 未知按 0 计入和
    mask = [False] * len(g.buckets)
    unknown = [{b0: BucketObs(None, None, 1000, 500)}, {b0: BucketObs(None, None, 1600, 800)}]
    assert group_rate_points(unknown, g, mask)[100] == {"t": b0, "dl": None, "up": None}
    mixed = [{b0: BucketObs(None, 5, 1000, 500)}, {b0: BucketObs(30, None, 1600, 800)}]
    assert group_rate_points(mixed, g, mask)[100] == {"t": b0, "dl": 30, "up": 5}


def test_v4_grid_obs_direct_mapping_edges():
    """v4_grid_obs 直映边界(26-11-15-1104 F2 后无权重面): 窗外桶点(链上下文)不消费 /
    null 点不参与(桶无观测 = null) / 窗内桶点逐键直映(BucketObs 原样装配)。
    快照竞争(ts 最晚者胜)与逐向豁免已上收 v4_series_points 桶层, 由槽层电池钉住。"""
    g = build_grid("24h", NOW, 30.0)
    first, last = g.first, g.last
    pts = (
        V4PointEntry(first - 600, 100, 100, 10, 20, w=30.0),  # 窗外链上下文桶: 不消费
        V4PointEntry(first, 200, 200, 100, 200, w=30.0),
        V4PointEntry(last, 400, 400, 300, 400, w=120.0),
        V4PointEntry(last + 300, 500, 500, 900, 800, w=30.0),  # 窗尾之后(防御直构): 不消费
        V4PointEntry(first + 30, None, None, None, None, w=0.0),  # null 点: 不参与
    )
    obs = v4_grid_obs(pts, g)
    assert first - 600 not in obs and last + 300 not in obs
    assert first + 30 not in obs  # null 点不参与
    assert obs[first] == BucketObs(200, 200, 100, 200)
    assert obs[last] == BucketObs(400, 400, 300, 400)
    assert max(obs) == last


def test_v4_series_points_same_bucket_merge_downstream():
    """(mut-core W2 vsp_75/vsp_120 守阵, F2 改判)同桶多槽(混桶 z+raw / raw+raw)的差分
    一次算定 + 快照竞争 + 覆盖时长活着进下游 —— 累加器槽位写坏(None)在速率面除法/
    round 处 TypeError 或值失真。旧「覆盖桶宽 w 并集」语义随 cell 几何退役,
    w = 覆盖时长(实测对跨合计)。"""
    b = V4Block(
        1000,
        1,
        10,
        20,
        (
            V4Sample(1, 1, 100, 100),  # @1000.0 链首
            V4ZeroRun(1, 100, 100, dt_ms=400),  # z @1000.4: delta 0(快照冻结)
            V4Sample(2, 2, 300, 300, dt_ms=400),  # @1000.8: 与 z 同桶(混桶): delta 200/0.4s+0.4s
            V4Sample(30, 40, 400, 400, dt_ms=400),  # @1001.2 -> 桶 1001
            V4Sample(50, 60, 500, 500, dt_ms=400),  # @1001.6: raw+raw 同桶: delta 200
        ),
    )
    g = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((b, ), g)
    assert [_p(p) for p in points] == [
        (1000, 250, 250, 300, 300, 0.8),  # 混桶: (z 前差分 0 + z->raw 200)/0.8s = 250
        (1001, 250, 250, 500, 500, 0.8),  # raw+raw: (100+100)/0.8s = 250; 快照取 ts 最晚
    ]
    obs = v4_grid_obs(points, g)  # 下游消费(v4_grid_obs 直映)
    assert obs[1001] == BucketObs(250, 250, 500, 500)


def test_v4_series_points_initial_nrun_mark():
    """(vsp_5)块首 n 游程的断连标记必须发出: 序列首槽即 n 槽时 last_was_null 初值 False
    使首标记得以发出(变异成 True 吞掉序列开头的断连标记)。可达性已证: 块首 n 游程 =
    程序开块时 qB 断连的合法形态(traffic_sample_mod._append_record「块首 n 游程不开基线,
    3 列 B 无基线块」+「无基线块仅 n 游程合法」)"""
    b = V4Block(1000, 30, None, None, (V4NullRun(3), V4Sample(1, 1, 1, 1, dt_ms=30000)))
    g = WindowGrid("5m", 900, 2000, 30, "raw", _floor_buckets(900, 2000, 30))
    points = v4_series_points((b, ), g)
    assert [_p(p) for p in points] == [
        (1000, None, None, None, None, 0.0),  # 块首 n 游程折叠的单个断连标记(首槽 1000.0)
        (1080, None, None, 1, 1, 0.0),  # r @1090 落格 1080: 标记后无前观测基线 -> 断链 None(快照照记)
    ]


def test_v4_series_points_up_channel_independent_differential():
    """(vgo_73/vgo_76 改判)up 通道差分独立累加(F2 逐向独立判定与豁免)—— up 有效差分
    照常派出、up 重置只打该向豁免不波及 dl, 赋值变异在均值上显形"""
    g = _grid_30s(NOW)  # 桶宽 30(直构; 24h@30s 的 F1 桶宽 180 会把三槽并入一桶)
    b0 = g.buckets[100]
    blk = V4Block(
        b0,
        30,
        1000,
        500,
        (
            V4Sample(100, 100, 1000, 500),  # 链首
            V4Sample(100, 100, 1100, 400, dt_ms=30000),  # @b0+30: up 重置(400<500) -> 豁免; dl +100
            V4Sample(100, 100, 1200, 900, dt_ms=30000),  # @b0+60: 对重置快照差分 dl +100 / up +500
        ),
    )
    pts = v4_series_points((blk, ), g)
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(0, 0, 1000, 500)  # 链首 0 线
    assert obs[b0 + 30] == BucketObs(3, 0, 1100, 400)  # dl 100/30s -> 3; up 重置 -> 0 线(无缝)
    assert obs[b0 + 60] == BucketObs(3, 17, 1200, 900)  # up 500/30s = 16.7 -> 17(逐向独立恢复)


def test_v4_series_points_lookback_boundary_slots_kept():
    """(vsp_59, 顺手 vsp_60)差分链窗外回看界(_V4_SEAM_LOOKBACK_S)边界槽保留: 槽 ts 恰达
    消费下界(grid.t0 - interval - 86400)照收(「ts >= 下界」判据含等号) —— 判据错成 >
    或退化成 <= 会把边界槽丢出链, 窗首摊配分母失真(池内全用小 epoch 撞不到回看界)"""
    t0 = NOW
    lo = t0 - _V4_SEAM_LOOKBACK_S
    grid = WindowGrid("24h", t0, t0 + 3600, 60, "raw", _floor_buckets(t0, t0 + 3600, 60))
    b = V4Block(lo - 60, 60, 100, 50, (V4ZeroRun(2, 100, 50), V4Sample(2, 2, 300, 150, dt_ms=60000)))
    points = v4_series_points((b, ), grid)
    assert [_p(p) for p in points] == [
        (lo - 60, 0, 0, 100, 50, 0.0),  # 首槽 @lo-60 = 消费下界(含等号)照收: 链首 0 线
        (lo, 0, 0, 100, 50, 60.0),  # 槽 @lo
        (lo + 60, 3, 2, 300, 150, 60.0),  # r @lo+60: delta(200,100)/60s(span==cov, 不触发陈旧跨度摊配)
    ]


def test_v4_series_points_same_t_marks_and_obs_sort_stable():
    """(vsp_160, 顺手 vsp_163)同刻双 null 标记 + 同刻观测点的排序: rank 位 (t, rank) 保序
    —— null 标记先于同刻观测点; 排序键失守(None / (t, entry))会在 V4PointEntry 比较上
    TypeError。几何: 亚秒 n 游程折叠标记与块间真空标记落同一整秒 + 同刻观测桶"""
    b1 = V4Block(1000, 30, 1, 1, (V4NullRun(2, dt_ms=600), V4Sample(1, 1, 1, 1, dt_ms=300)))
    b2 = V4Block(2000, 30, 2, 2, (V4Sample(2, 2, 2, 2), ))
    grid = WindowGrid("5m", 900, 3000, 1, "raw", _floor_buckets(900, 3000, 1))
    points = v4_series_points((b1, b2), grid)
    assert [_p(p) for p in points] == [
        (1000, None, None, None, None, 0.0),  # n 游程折叠标记(首槽 1000.0)
        (1000, None, None, None, None, 0.0),  # 块间真空标记(t = 前块游标终值 1000.9 取整)—— 同刻
        (1000, None, None, 1, 1, 0.0),  # 同刻观测桶(样本 @1000.9): null 标记排在其前; 标记后无基线 -> None
        (2000, None, None, 2, 2, 0.0),  # b2 观测: 未观测 ~969s > 60s 停机洞 -> None
    ]


def test_v4_series_points_break_flag_survives_bucket_second_point():
    """(vgo_60, 顺手 vgo_62; F2 桶层改判)断链旗必须跨同桶后继槽存活(or 累积) —— 断链桶内
    第二槽(逐向豁免: 重置)不得清旗, 否则断链桶冒充 0 线(issue 26-10-16-0954 语义回退)"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    blk1 = V4Block(b0 - 100, 30, 1000, 500, (V4Sample(5, 5, 1000, 500), ))
    blk2 = V4Block(b0, 30, 2000, 900, (V4Sample(9, 9, 2000, 900), V4Sample(9, 9, 1000, 400, dt_ms=10000)))
    points = v4_series_points((blk1, blk2), g)
    assert [_p(p) for p in points if p.t == b0] == [(b0, None, None, 1000, 400, 0.0)]
    obs = v4_grid_obs(points, g)
    assert obs[b0] == BucketObs(None, None, 1000, 400)  # 断链未知 != 0(后继重置槽不清旗)
    tot = series_totals_points(obs, g)
    assert tot[g.buckets.index(b0)] == {"t": b0, "dl": 0, "up": None}  # dl 同值 0; up 回落重置 None


def test_v4_series_points_null_mark_at_lookback_boundary_kept():
    """(vsp_43/vsp_155)null 标记恰在消费下界(_V4_SEAM_LOOKBACK_S 链界)必须发出 —— 下界
    判据含等号(null_lo <= t), 变异成 < 会吞掉窗首断连标记"""
    t0 = NOW
    lo = t0 - _V4_SEAM_LOOKBACK_S
    grid = WindowGrid("24h", t0, t0 + 3600, 30, "raw", _floor_buckets(t0, t0 + 3600, 30))
    b = V4Block(lo, 30, None, None, (V4NullRun(3), V4Sample(1, 1, 100, 50, dt_ms=30000)))
    points = v4_series_points((b, ), grid)
    assert [_p(p) for p in points] == [
        (lo, None, None, None, None, 0.0),  # n 游程首槽恰在链界 -> 断连标记保留
        (lo + 90, None, None, 100, 50, 0.0),  # n 终点 lo+90 处 r 槽: 标记后无前观测基线 -> 断链 None
    ]


def test_v4_series_points_marks_at_window_end_not_emitted():
    """(vsp_44/vsp_156)窗尾整秒标记不发出 —— null 槽末槽恰为 t1 时不追加; 块间真空
    标记恰为 t1 时由界过滤挡下(变异成 <= 会多出窗外 null 点)"""
    t1 = NOW + 3600
    # 前块末槽 @t1: t1-60 首个 n 槽在窗内出标记; 块间真空标记 = prev_chain_end = t1;
    # 后块起点在窗外(只为制造真空标记, 自身观测槽不消费)
    b1 = V4Block(t1 - 60, 30, None, None, (V4NullRun(2, dt_ms=60000), ))
    b2 = V4Block(t1 + 3600, 30, 10, 20, (V4Sample(6, 6, 200, 60), ))
    grid = WindowGrid("5m", NOW, t1, 30, "raw", _floor_buckets(NOW, t1, 30))
    points = v4_series_points((b1, b2), grid)
    assert [_p(p) for p in points] == [
        (t1 - 60, None, None, None, None, 0.0),  # 窗内 n 标记; 末槽 t1 与真空标记 t1 均在窗外不发出
    ]


def test_v4_series_points_observed_slot_at_window_end_not_consumed():
    """(vsp_52)恰在 t1 的观测槽不消费(v2 口径 ts >= t1) —— 变异成 ts > t1 会把窗外
    记录铺成窗尾桶"""
    t1 = NOW + 3600
    b = V4Block(t1, 30, 10, 20, (V4Sample(5, 5, 100, 50), ))
    grid = WindowGrid("5m", NOW, t1, 30, "raw", _floor_buckets(NOW, t1, 30))
    assert v4_series_points((b, ), grid) == ()


def test_build_grid_day_window_midnight_anchors():
    """(bg_52/bg_53)day 窗日期集 t1-1 口径 —— now 恰为 23:59:59 不多铺次日桶, 恰为
    00:00:01 不丢当日桶(变异成 t1+1/t1-2 会各错一天)"""
    midnight = v4_day_epoch(NOW)
    span = WINDOW_SPECS["6mo"][0]
    for now in (midnight + 86399, midnight + 1):
        g = build_grid("6mo", now)
        assert g.segment == "day" and g.t1 == now and g.t0 == now - span
        assert g.last == midnight  # 末桶恒为 now 所在本地日界


def test_v4_series_points_snapshot_competition_latest_ts_wins():
    """(vgo_80 + vsp_95 合钉, F2 桶层改判)同桶快照竞争 = ts 最晚者胜, 同刻后到者优先
    (判据含等号 s.ts >= e[4]; 变异成 > 会保留先到快照, totals 停在 1000/500)。
    旧「覆盖末端最晚者胜」随覆盖桶几何退役 —— 竞争键从 ceil(ts) 收敛为实测 ts。"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    blk = V4Block(
        b0,
        30,
        1000,
        500,
        (
            V4Sample(10, 10, 1000, 500, dt_ms=5000),  # @b0+5
            V4Sample(20, 20, 2000, 900, dt_ms=5000),  # @b0+10: 快照竞争(更晚 ts)
            V4Sample(30, 30, 3000, 950, dt_ms=0),  # @b0+10 同刻后到: >= 判据下抢走快照
        ),
    )
    pts = v4_series_points((blk, ), g)
    # 速率: 同刻对跨 0 不入账(覆盖时长 > 0 判据) -> dl 1000/5s = 200, up 400/5s = 80
    assert [_p(p) for p in pts] == [(b0, 200, 80, 3000, 950, 5.0)]


# test_v4_grid_obs_coverage_end_advance_keeps_latest_snapshot 已随覆盖桶几何退役(F2):
# 「覆盖末端推进」的变异守阵由 test_v4_series_points_snapshot_competition_latest_ts_wins
# 的 ts 竞争判据承接(e[4] = 实测 ts 最晚者)。


def test_v4_series_points_broken_bucket_zero_rate_kept_zero():
    """(vgo_105/vgo_117 改判)断链桶有差分覆盖且速率为 0 时仍是 0 线, 不是 None —— 均值
    判据看覆盖毫秒(dl_cov/up_cov), 变异成看差分和会把 0 误判成无覆盖, 断链桶冒充缺口"""
    g = build_grid("24h", NOW, 30.0)
    b0 = g.buckets[100]
    blk1 = V4Block(b0 - 100, 30, 1000, 500, (V4Sample(9, 9, 1000, 500), ))
    # 恢复槽(停机洞 -> 对豁免)+ 同桶后继空闲槽(delta 0, 有效覆盖)-> 0 线非 None
    blk2 = V4Block(b0, 30, 2000, 900, (V4Sample(0, 0, 2000, 900), V4Sample(0, 0, 2000, 900, dt_ms=10000)))
    pts = v4_series_points((blk1, blk2), g)
    assert [_p(p) for p in pts if p.t == b0] == [(b0, 0, 0, 2000, 900, 10.0)]
    obs = v4_grid_obs(pts, g)
    assert obs[b0] == BucketObs(0, 0, 2000, 900)  # 有覆盖(delta 0) -> 0 线; 快照照记


# ---------- 覆盖率第三轮 T2b 补测(26-11-05): 窗界/快照竞争复合条件 ----------


def test_v4_series_points_stale_slot_below_lookback_not_consumed():
    """(T2b)消费下界外槽不消费(ts < grid.t0 - interval - 86400): 差分链只保留回看界内的
    完整陈旧跨度, 更老的槽不进桶点流; 界内槽照常消费"""
    stale = V4Slot(1000.5, 1.0, (5, 9, 3000, 4000), False)  # ts << 消费下界(t0 - 86401)
    fresh = V4Slot(200000.5, 1.0, (6, 10, 5000, 6000), False)
    grid = WindowGrid("5m", 200000, 200600, 1, "raw", _floor_buckets(200000, 200600, 1))
    points = v4_series_points((), grid, tail_slots=(stale, fresh))
    assert [_p(p) for p in points] == [(200000, 0, 0, 5000, 6000, 0.0)]  # 界内槽链首 0 线


def test_v4_series_points_same_bucket_zero_slots_differential_snapshot():
    """(T2b 改判)同桶 z+z: 差分面对照 totals 链真值(两段独立 z 快照不同值时按差分计 ——
    真实 z 游程同桶槽快照恒同值, 差分恒 0); 快照统一取 ts 最晚者(旧「z 到 z 桶先到者
    保留」的 v2 口径随 cell 几何退役, 改判理由: 同桶合并规则单点化, 快照竞争不再分流)"""
    slots = (
        V4Slot(998.5, 1.0, (0, 0, 1000, 2000), True),
        V4Slot(998.9, 1.0, (0, 0, 9000, 9000), True),  # 病理两段 z( totals 不同值)
    )
    grid = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((), grid, tail_slots=slots)
    assert [_p(p) for p in points] == [(998, 20000, 17500, 9000, 9000, 0.4)]  # 差分 8000/7000 ÷ 0.4s


def test_v4_series_points_same_bucket_out_of_order_ts_keeps_latest_snapshot():
    """(T2b)同桶 raw+raw 且后到槽 ts 更早(乱序): 快照保持实测更晚的先到者(503->478)
    —— 快照竞争判据是 ts 不是到达序; 负对跨(乱序)不进速率面(覆盖时长 > 0 判据)"""
    slots = (
        V4Slot(998.9, 1.0, (5, 9, 3000, 4000), False),
        V4Slot(998.5, 1.0, (15, 21, 4000, 5000), False),  # 后到但 ts 早: 不抢快照
    )
    grid = WindowGrid("5m", 900, 2000, 1, "raw", _floor_buckets(900, 2000, 1))
    points = v4_series_points((), grid, tail_slots=slots)
    assert [_p(p) for p in points] == [(998, 0, 0, 3000, 4000, 0.0)]


def test_v4_series_points_marked_run_not_zero_shape_drops_delta():
    """(T2b 改判槽层)既有断链语义(614->615): null 标记后的台阶但锚点后游程非 z 形
    (真速率记录)-> 不摊配, 基线缺失 None —— 摊配的 z 形签名是必要条件, marked 只是
    或支之一"""
    blk1 = V4Block(1000, 30, 1000, 1000, (V4Sample(10, 10, 1000, 1000), V4Sample(10, 10, 1000, 1000, dt_ms=30000)))
    blk2 = V4Block(1120, 30, 1100, 1100, (V4Sample(20, 20, 1100, 1100), ))  # 块间真空标记 + 台阶
    grid = WindowGrid("5m", 900, 2000, 30, "raw", _floor_buckets(900, 2000, 30))
    points = v4_series_points((blk1, blk2), grid)
    assert [_p(p) for p in points] == [
        (990, 0, 0, 1000, 1000, 0.0),  # 链首 0 线(等值 r 游程锚点, @1000 落格 990)
        (1020, 0, 0, 1000, 1000, 30.0),  # 等值 r 游程: delta 0(速率非零 -> 非 z 形签名)
        (1030, None, None, None, None, 0.0),  # 块间真空标记(t = 1030)
        (1110, None, None, 1100, 1100, 0.0),  # 标记后台阶: 游程非 z 形不摊配 -> 基线缺失 None
    ]


def test_v4_series_points_pre_window_chain_context_filtered_from_obs():
    """(T2b 改判)窗首前的链上下文桶: 点位归属下窗前槽落窗前桶(照常入流, 供差分基线),
    v4_grid_obs 窗外桶不消费 —— 响应桶集恒 == 与栅格桶集的交集, 窗外桶不凭空出现。
    旧「宽桶跨窗首部分重叠展开」随覆盖加权桥接退役: 窗前样本的差分按端点归属记在
    窗前桶, 首个窗内桶的速率由(窗前末槽 -> 窗内首槽)对给出(D3 种子语义)。"""
    g = build_grid("24h", NOW, 30.0)
    first = g.first
    blk = V4Block(first - 30, 30, 1000, 500, (V4Sample(10, 10, 1000, 500), V4Sample(10, 10, 1600, 800, dt_ms=30000)))
    pts = v4_series_points((blk, ), g)
    assert [p.t for p in pts] == [first - 180, first]  # 窗前槽 @first-30 落窗前桶(桶宽 180, F1)入流
    obs = v4_grid_obs(pts, g)
    assert set(obs) == {first}, "窗外链上下文桶不得出观测"
    assert obs[first] == BucketObs(20, 10, 1600, 800)  # 窗前基线 -> 首桶 delta(600,300)/30s


# ======================================================================
# 折叠态机与缓存防线单元(S4 缺口收口, 26-11-17; 主会话拍板「写真测试不降窗」)
# 直构 _V4SeriesFold / 游标 / 槽组 —— 钉防御面契约本体(函数 docstring 承诺的行为),
# 集成面等价性由 test_traffic_grid_bucket_cache 的逐位对账主阵承管, 两层互不替代。
# ======================================================================


def test_bucket_index_correction_loops_float_interval():
    """(缺口收口)点位归属桶序双向校正环(_bucket_index i-=1 / i+=1 两环):
    floor((ts-first)/interval) 的除法舍入与键表达式 first + i x interval 的乘法舍入
    在**非精确二进制桶宽**下可相差一格 —— 配置 si 是任意 float(如 2.4), 桶宽 = si x k
    同样非精确, 除法把 74.39999999999999/2.4 舍入到 30(偏小)而键 31 x 2.4 恰含 ts(偏
    大), 反向 1.7/0.1 舍入到 17 而键 17 x 0.1 = 1.7000000000000002 越过 ts。两环把两个
    方向都拉回键语义: 结果桶恒满足 first + i x B <= ts < first + (i+1) x B(与键查找
    obs.get 恒命中的不变式同源)。生产精确二进制桶宽(1.5/4.5/22.5/43.5/87/174,
    si=1.5 x k)下两环不触发(1e6 随机扫描零命中) —— 触发面收窄到任意 si 配置形态。"""
    # dec 环(除法下标偏大): 键 17 x 0.1 舍入越过 ts -> 回退到桶 16
    i = _bucket_index(1.7, 0.0, 0.1)
    assert i == 16
    assert 0.0 + i * 0.1 <= 1.7 < 0.0 + (i + 1) * 0.1
    # inc 环(除法下标偏小): 键 31 x 2.4 恰含 ts -> 进到桶 31
    ts = 74.39999999999999
    j = _bucket_index(ts, 0.0, 2.4)
    assert j == 31
    assert 0.0 + j * 2.4 <= ts < 0.0 + (j + 1) * 2.4


def test_check_gap_bound_fail_fast_and_default():
    """(缺口收口)gap_bound_s 校验与缺省单点(_check_gap_bound): 非正 / 非有限 / 非数值
    / bool 一律 ValueError fail-fast(v4_series_points 与桶值缓存共用同一判据, 传坏值
    不得静默落进判据面); None 缺省 = interval x 2(F1 raw 桶宽恒采样整倍 B >= si,
    与调用面 max(B, si) x 2 数学恒等); 显式正值原样返回(float 归一)。"""
    for bad in (0, -1.0, float("inf"), float("nan"), "3", True, [], 3 + 4j):
        with pytest.raises(ValueError, match="非法 gap_bound_s"):
            _check_gap_bound(bad, 1.5)
    assert _check_gap_bound(None, 1.5) == 3.0
    assert _check_gap_bound(7.5, 1.5) == 7.5


def test_fold_sanitize_window_realignment_defensive():
    """(缺口收口)增量折叠前的窗界再对齐(_V4SeriesFold.sanitize)防御契约: prev_slot /
    marked_ts 滑出回看界 -> 复位 None(对齐全量现算在当前 null_lo 下不消费界外态);
    游程锚点(run[1])滑出回看界 -> 返回 True(调用方必须整条目冷重建 —— docstring 承诺
    的语义, 单个读集前沿生命周期内常态不可达, 失效面组合可造出, 直构钉住契约本体);
    未立游程(run[0] None 且 run_list 空 —— 锚 0.0 是初值哨兵)不判滑出。"""
    f = _V4SeriesFold()
    f.prev_slot = (999.0, (1, 2))
    f.marked_ts = 998.0
    f.dl_run = [None, 0.0, [], 0]
    f.up_run = [None, 0.0, [], 0]
    assert f.sanitize(1000.0) is False
    assert f.prev_slot is None and f.marked_ts is None
    f.dl_run = [(999.0, (1, 2)), 999.0, [(999.0, 10, True, 999.0)], 0]
    assert f.sanitize(1000.0) is True  # dl 游程锚点滑出 -> 冷重建信号
    f2 = _V4SeriesFold()
    f2.up_run = [(999.0, (1, 2)), 999.0, [(999.0, 10, True, 999.0)], 0]
    assert f2.sanitize(1000.0) is True  # up 向独立同判
    f3 = _V4SeriesFold()
    f3.dl_run = [(1050.0, (1, 2)), 1050.0, [(1050.0, 10, True, 1050.0)], 0]
    assert f3.sanitize(1000.0) is False  # 锚点在界内 = 常态面


def _cell(dl_delta: int, hold: bool = False) -> list:
    """直构桶累加器(布局单点 = fold 主循环 cells[key] 九列): [dl_share, dl_cov_ms,
    up_share, up_cov_ms, 快照 ts, dl_total, up_total, broke, is_hold]"""
    return [dl_delta, 1000, 0, 1000, 1.0, 100, 50, False, hold]


def test_fold_emit_window_filters_and_sealed_backfill_source():
    """(缺口收口)发射窗界过滤与回填源桶解析(_V4SeriesFold.emit): 窗外回填桶
    (bf_key < lo / bf_key 越过 hi 或 hi 排他等值)不发射 —— 响应桶集恒 == 与窗的交集
    (链上下文不入响应); 回填源桶已封口裁剪(cells 无键)时快照经 sealed 封口值表解析
    (字节守恒: 回填点 totals = 源桶末次快照), 封口表与累加器均无 = KeyError fail-fast
    (结构性异常不静默造点)。"""
    g = _V4SeriesFold()
    slots = (
        V4Slot(ts=1.0, dt_s=1.0, obs=(100, 50, 1000, 500), is_zero=False, is_hold=False),
        V4Slot(ts=3.0, dt_s=2.0, obs=(100, 50, 1100, 550), is_zero=False, is_hold=False),
    )
    g.fold([(slots, False)], 0.0, 10.0, 1.0, 10.0, -1.0, 3.0)  # 跨桶 2 的有界空桶 -> 回填 (2.0 -> 1.0)
    assert g.backfills == [(2.0, 1.0)]
    full = g.emit(None, None, None)
    assert [(p.t, p.is_hold, p.dl_total, p.up_total) for p in full] == [
        (1.0, False, 1000, 500),  # 链首桶 0 线(D4, 无缝链首不置旗)
        (2.0, True, 1000, 500),  # 回填持有点: 速率持源桶 0 线, totals = 源桶快照(链 0 增量)
        (3.0, False, 1100, 550),
    ]
    assert [p.t for p in g.emit(2.5, None, None)] == [3.0]  # 回填桶 bf_key < lo 过滤
    assert [p.t for p in g.emit(None, 2.0, None, hi_inclusive=False)] == [1.0]  # bf_key == hi(排他)过滤
    # 源桶封口裁剪(cells+cell_keys 同步移除, 模拟 _publish 地平线裁剪后的折叠态形态):
    # 快照经封口值表解析, 回填点 totals 逐位 = 封口值
    del g.cells[1.0]
    g.cell_keys.remove(1.0)
    sealed = g.emit(None, None, None, sealed={1.0: V4PointEntry(1.0, 100, 50, 1000, 500)})
    assert [(p.t, p.is_hold, p.dl_total, p.up_total) for p in sealed if p.is_hold] == [(2.0, True, 1000, 500)]
    with pytest.raises(KeyError, match="回填源桶缺失"):
        g.emit(None, None, None, sealed=None)


def test_fold_emit_mark_window_filter():
    """(缺口收口)标记点窗界过滤(emit 标记循环 t < lo continue): null 标记在窗界前
    不入发射列(断连标记是链上下文面, 响应窗不消费); 窗内标记照常入列参与 held 合并
    (null 点清空持有面)。与回填过滤分 fold 直构 —— 标记点入发射列会改变全量发射点列
    形态(标记占发射序)与链首 broke 面, 故与回填过滤形态分开直构, 两判据面互不缠绕。"""
    b = _V4SeriesFold()
    slots = (
        V4Slot(ts=0.5, dt_s=1.0, obs=None, is_zero=False, is_hold=False),  # n 槽 -> 标记 t=0
        V4Slot(ts=1.5, dt_s=1.0, obs=(100, 50, 1000, 500), is_zero=False, is_hold=False),
        V4Slot(ts=4.0, dt_s=2.5, obs=(100, 50, 1100, 550), is_zero=False, is_hold=False),
    )
    b.fold([(slots, False)], 0.0, 10.0, 1.0, 10.0, -1.0, 9.0)
    assert b.marks == [0]
    assert [p.t for p in b.emit(None, None, None)] == [0, 1.0, 2.0, 3.0, 4.0]  # 标记占发射序
    assert [p.t for p in b.emit(3.0, None, None)] == [3.0, 4.0]  # 标记 0 < lo 过滤, 观测桶照常


def test_fold_held_at_scan_paths():
    """(缺口收口)held 面合并扫描单点(_V4SeriesFold.held_at): 缓存路径发射的 held 初值
    = 开放面 < position 的降序首扫 —— 首个非持有观测桶给其速率; holding 桶(回填/尾桶)
    不携带不入账, 跳过继续向前扫; null 标记先行即 None(None 点清空持有面); 开放面无项
    -> fallback(封口面末端 held 值)。与全量发射的合并序逐位同判(docstring 承诺)。"""
    h = _V4SeriesFold()
    h.cells = {1.0: _cell(100), 2.0: _cell(0, hold=True), 4.0: _cell(300)}
    h.cell_keys = [1.0, 2.0, 4.0]
    assert h.held_at(3.0, None) == (100, 0)  # position 前最新观测桶是 holding -> 跳过, 取再前观测桶
    assert h.held_at(5.0, None) == (300, 0)  # 最新观测桶非持有 -> 直取
    h2 = _V4SeriesFold()
    h2.cells = {1.0: _cell(100)}
    h2.cell_keys = [1.0]
    h2.backfills = [(2.0, 1.0)]
    assert h2.held_at(2.5, None) == (100, 0)  # 回填桶不携带 held, 越过取观测桶
    h3 = _V4SeriesFold()
    h3.backfills = [(2.0, 1.0)]
    assert h3.held_at(2.5, "FB") == "FB"  # 仅回填可扫 -> fallback
    h4 = _V4SeriesFold()
    h4.cells = {1.0: _cell(100)}
    h4.cell_keys = [1.0]
    h4.marks = [2.0]
    assert h4.held_at(2.5, "FB") is None  # null 标记先行: 持有面清空(优先于观测桶)


def test_fold_sealed_floor_null_lo_fallback():
    """(缺口收口)封口边界的回看界兜底(_V4SeriesFold.sealed_floor): prev_slot 为 None
    (链首无观测)而累加器非空(观测全在回看界外)时以 null_lo 兜底 —— 回看界外桶值不再
    受任何后续槽影响(新槽消费下界同界), 视同定影; 有 prev_slot 时以链末观测桶键为界
    (常态面); 无任何候选返回 None。"""
    s = _V4SeriesFold()
    s.cells = {1.0: _cell(100)}
    assert s.sealed_floor(0.0, 1.0, 1234.0) == 1234.0  # 链首无观测 + 累加器非空 -> null_lo 兜底
    s2 = _V4SeriesFold()
    s2.prev_slot = (500.0, (1, 2))
    assert s2.sealed_floor(0.0, 1.0, 1234.0) == 500.0  # 常态面: 链末观测桶键
    s3 = _V4SeriesFold()
    assert s3.sealed_floor(0.0, 1.0, 1234.0) is None  # 无观测无游程


def test_fold_seam_allocation_zero_share_and_balance():
    """(缺口收口)接缝摊配的按比例取整面(fold 游程闭合分支): span > cov 的含缝 z 游程
    台阶按覆盖份额缩放(step_w = step x cov // span), 逐项份额 = step_w x 累计 // cov_ms
    —— 份额取整可为 0(小份额项不进桶), 余额(delta = step_w - acc)归接收桶; 字节守恒
    不变式: 各游程桶份额 + 接收桶 delta == step_w(缩放后的总量一分不丢)。z 槽桶份额
    恒 0 与「空闲段 0 线」并存(摊配份额只进非零项)。"""
    f = _V4SeriesFold()
    # z 游程 9 槽: 墙钟步 10s / 声称覆盖 5s(含缝对) -> span 100s, cov 50s(8 x 5s + 台阶对 10s, 首槽立游程不进 run_list)
    slots = tuple(
        V4Slot(ts=float(k * 10), dt_s=5.0, obs=(0, 0, 1000, 500), is_zero=True, is_hold=False) for k in range(9)
    )
    slots += (V4Slot(ts=100.0, dt_s=10.0, obs=(50, 25, 1010, 505), is_zero=False, is_hold=False), )
    f.fold([(slots, False)], 0.0, 200.0, 1.0, 200.0, -1.0, 0.0)
    # step = 10 字节, step_w = 10 x 50000 // 100000 = 5; 累计 5k..40k(8 项) -> 份额 0,0,1,0,1,0,1,0,1
    shares = {k: f.cells[k][0] for k in sorted(f.cells) if k < 100.0}
    assert shares == {0.0: 0, 10.0: 0, 20.0: 1, 30.0: 0, 40.0: 1, 50.0: 0, 60.0: 1, 70.0: 0, 80.0: 1}
    assert f.cells[100.0][0] == 1  # 接收桶 delta = 余额 5 - 4
    assert sum(shares.values()) + f.cells[100.0][0] == 5  # 字节守恒 == step_w


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


def test_guard_group_order_fail_fast():
    """(缺口收口)槽组时序守卫(_guard_group_order, 缓存路径防御面): 槽组按 (日期, 块序)
    构造恒时序递增, 首槽倒挂(先于前组末槽 - 真空 epsilon)= 解析产物结构性异常 ->
    ValueError fail-fast 拒折, 不静默产出负对跨的脏速率; 时序正常组不拦截。"""
    def slot(t):
        return V4Slot(ts=t, dt_s=1.0, obs=(0, 0, 1, 1), is_zero=False, is_hold=False)

    with pytest.raises(ValueError, match="槽组时序倒挂"):
        _guard_group_order([((slot(100.0), ), False), ((slot(50.0), ), False)])
    _guard_group_order([((slot(100.0), ), False), ((slot(200.0), ), False)])  # 正常时序
