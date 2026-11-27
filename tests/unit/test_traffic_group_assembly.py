"""test_traffic_group_assembly 测试计划: 样本分组装配读侧纯函数(plan 26-11-18-0037 阶段 1,
§03 读侧契约逐条钉面 —— points 形态/分组口径 k/尾组/字节守恒/null 显式空值/fail-fast)

## 测试计划(每个测试函数一条)
- test_k1_short_window_per_sample: 短窗 k=1 逐样本(1m 40 样本形态)—— 每样本一点,
  t = 样本 ts, 值 = 逐样本差分/覆盖; 无缝链首 0 线(D4); totals 基线缺失逐向 None;
  tail_open = False(直通窗尾点恒定不折叠)
- test_k_gt1_group_mean_bitwise: 长窗 k>1 均值逐位对账 —— 组值 = Sigma delta x 1000 /
  Sigma 覆盖毫秒(round 取整), 时间桶锚 group_bucket(26-11-27 S1a: 1000 落桶 166 单样本
  桶), t = 桶末样本 ts; tail_open = True(末真值点 = 活尾组点)
- test_tail_group_always_true_value: 尾组恒真值 + 组闭合迁移 —— 满桶点 t/值随真样本收敛;
  追加样本落新桶 -> 旧桶点闭合为脊柱(t/值逐位不变), 新桶点为活尾组点
- test_spine_stable_across_sliding_window: 脊柱跨滑动窗逐位不动(INV-3 对账零形状改写,
  S0 症状3 根因修复)—— 同槽流两次 GET 窗沿平移 30s, 内桶点 t/值逐位相等(桶界纯 ts
  函数与窗位置无关); 窗首跨界桶只收窗内成员(窗外同桶样本弃入)单点有界改写, 左缘桶随
  窗滑出即丢不整列改写
- test_byte_conservation_totals_sum_invariant_across_k: 字节守恒 —— 同一槽流在不同窗
  (k=1 vs k=3)下 Sigma(totals) 恒等, 且 = 末样本快照 - 首窗内样本快照(遥差参考);
  带窗外种子时 Sigma = 末快照 - 种子快照(窗首组含种子差分)
- test_gap_bytes_in_successor_sample_diff: 漏采区间字节含在后继样本快照差分里 —— n 游程
  断连后首样本 totals 差分 = 跨缺口全量快照差分(计数器真值, 速率面诚实丢弃不传染 totals)
- test_null_points_fold_and_dedup: n 游程折叠一点(t = floor(首槽 ts)), 相邻两游程出两点
  (观测槽复位去重); 空值点不影响相邻组均值(缺口前组值与无缺口流逐位相等); 缺口后组
  按断连面诚实判读(broke 组已落差分真实 -> 0 线非 None)
- test_vacuum_mark_between_blocks: 块间真空出显式空值点(t = int(链终值), 判定来源承袭),
  标记桶观测点与空值点同 t 共存(空值在前, 旧 emit 同构)
- test_seam_spread_uniform_no_spike: 接缝摊配(提取件复用)—— 长 z 形冻结游程 + 重启缝
  台阶按真实跨度摊配, 游程组 + 接收组均匀平线无单组尖峰, Sigma(值 x 覆盖) = step_w 守恒,
  Sigma(totals) = 遥差(摊配面不得污染 totals 面)
- test_budget_raises_stride_on_marks: k 上调路径 —— 缺口标记顶破预算(组点 + 空值点 > 500)
  时 k 从初值上调至最小达标值, 总点数钉实测 343(333 桶点 + 10 空值, 时间桶锚下纯 ts 确定)
- test_over_budget_honest_delivery: 不可达角(缺口标记数 >= 500)—— 按 k 上限(窗内样本数)
  交付, over_budget=True 如实标注, 空值点一个不弃(诚实优先于预算)
- test_stride_capped_at_window_samples: k 上限 = 窗内实际样本数(k 初值超样本数时夹取)
- test_reset_and_hole_semantics: 计数器重置 -> 差分 None 组值 0 线/totals 逐向 None,
  后继样本新链恢复; 缝 > 60s 停机洞 -> 组值 None(totals 仍含跨洞快照差分)
- test_tail_open_whole_window_reset_form: tail_open 整窗重置形态(26-11-27 评审反例2)
  —— k>1 全组 0 线/totals 逐向 None 时 tail_open 按尾点身份 = True(points[-1] 是活尾
  组点), 旧 any(totals) 推导在该形态误 False; 尾项是断链组点(totals dict)非空值点
- test_window_filter_and_seed_baseline: 窗尾外槽不消费(ts >= t1), 窗外前缀只作差分基线
  不产组点; 窗内首样本对窗外种子的差分落在窗首组(窗首种子 D3)
- test_marks_outside_window_not_emitted: 窗前 n 游程/真空不产空值点(断连面 marked 语义
  仍生效), 窗尾外标记同样不产
- test_fail_fast_invalid_inputs: 入参非法 fail-fast —— 窗口倒挂/非有限数值/bool/si 非正/
  槽流时序倒挂/非 V4Slot 项, 一律 raise 不静默修复(is_hold 持有槽拒收支已随持有面退役删除)
- test_member_points_isomorphic: 组端点同构 —— 同 tick 采样的两个成员(含 z/n 游程与块缝)
  各自装配, 点列 t 逐位相等、stride 相等、空值点位置相等
- test_from_blocks_wrapper_uses_series_slots: 便捷入口复用 v4_series_slots 平展(乱序块
  还原时间序), 与直喂槽流结果逐位相等
- test_seam_spread_helper_contract: 摊配提取件直钉 —— z 形游程 + marked 触发份额分配
  (累计比例取整, 余额归接收方); 非 z 游程(r 形签名)不摊配返回 step; marked 无游程返回
  缩放基准
- test_pre_window_gap_and_stuck_run_faces: 窗外断连面与摊配弃入 —— 真空标记 t 在窗前
  不产空值点但断连面生效(后继组断链); 窗外等值游程槽摊配份额无组可入直接弃
- test_all_null_window_no_samples: 窗内 0 样本全缺口形态 —— 仅 n 游程覆盖全窗 -> points
  只含显式空值点、stride=1、不炸; 槽全在窗外 -> 空点列(天然真空); tail_open = False
  (无组点窗)
- test_zero_coverage_pair_not_attributed: 同刻病理槽序(dt_ms=0 双样本同刻)—— 对跨 0 ->
  覆盖 0, 差分不归因不造分母(防御面), 速率组值 0 线不炸; totals 快照差分照常入账
- test_marked_r_run_equal_chain_drops_delta: r 形等值游程(非 z 签名)+ n 断连标记 + 台阶
  —— 摊配判定 all(z) 不成立且 marked 存活 -> 差分 None 断链, 组值 None(诚实丢字节);
  totals 面快照差分照常真值
- test_eps_band_regression_no_end_ts_rewrite: eps 带内回退槽 —— 组末 ts/快照不被更早槽
  回写(快照取 ts 最晚者, 旧面同判), totals 逐样本差分照常按槽归属入账
- test_empty_slot_stream: 空槽流 -> 空点列空 totals, stride=1, 不炸(天然真空空态)

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 输入直接构造 V4Block
或 V4Slot; 数值构造取整除形态(整除摊配/整除覆盖)避免 round 噪声, 期望值手工逐位推导。
"""

import math

import pytest

from auto_qb.core.traffic_group_assembly import (
    GroupAssemblyResult,
    assemble_group_points,
    assemble_group_points_from_blocks,
)
from auto_qb.core.traffic_grid import _seam_spread_delta, v4_series_slots
from auto_qb.core.traffic_store import (
    V4Block,
    V4NullRun,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    v4_block_slots,
)


def _blk(start, interval, records, dl_base=None, up_base=None):
    """V4Block 直构便捷(基线参数与槽位数学无关, 仅 format/parse roundtrip 要求)"""
    return V4Block(start, interval, dl_base, up_base, tuple(records))


def _samples(totals, si_ms=None):
    """等 dt 采样序列: totals = [(dl_total, up_total), ...]; dt 缺省 = 标称(块 interval)"""
    return tuple(V4Sample(0, 0, dl, up) for dl, up in totals)


def _null_points(res):
    """结果点列中的显式空值点(缺口): totals 项为 None 的点 —— 与「断链组点」(dl/up 双
    None 但 totals 仍为差分和 dict)区分, 后者是断链未知面不是缺口标记"""
    return [p for p, t in zip(res.points, res.totals) if t is None]


def _real_points(res):
    """真值组点(totals 项非 None)"""
    return [p for p, t in zip(res.points, res.totals) if t is not None]


def _totals_sum(res, key):
    """Sigma(totals[key]): None 项(空值点)与逐向 None 计 0 —— 字节守恒对账口径"""
    return sum(t[key] for t in res.totals if t is not None and t[key] is not None)


def test_k1_short_window_per_sample():
    """短窗 k=1 逐样本: 1m/1.5s = 40 样本形态 -> 40 点, t = 样本 ts, 值 = 逐样本差分/覆盖;
    链首无基线且无缝 -> 0 线(D4); totals 首项基线缺失 None, 其后逐样本快照差分"""
    totals = [(1000 + 150 * i, 500 + 60 * i) for i in range(40)]
    blk = _blk(1000, 1.5, _samples(totals), 1000, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 1060, 1.5)
    assert res.stride == 1 and not res.over_budget  # 预期 40 样本 -> k 初值 1
    assert len(res.points) == 40
    assert [p["t"] for p in res.points] == [1000 + 1.5 * i for i in range(40)]
    assert res.points[0] == {"t": 1000.0, "dl": 0, "up": 0}  # 无缝链首 0 线
    assert all(p["dl"] == 100 and p["up"] == 40 for p in res.points[1:])  # 150/1.5s, 60/1.5s
    assert res.tail_open is False  # k=1 直通窗: 尾点恒定不折叠
    assert res.totals[0] == {"t": 1000.0, "dl": None, "up": None}  # 基线缺失
    assert all(t["dl"] == 150 and t["up"] == 60 for t in res.totals[1:])
    assert _totals_sum(res, "dl") == 150 * 39  # = 末快照 - 首快照(遥差)


def test_k_gt1_group_mean_bitwise():
    """长窗 k>1 均值逐位对账: 窗 [1000,4000)/2s 预期 1500 样本 -> k=3, 桶宽 6s(时间桶锚
    group_bucket: 1000 落桶 166 单样本桶, 1002/1004/1006 同桶 167...); 组值 = Sigma delta
    x 1000 / Sigma 覆盖毫秒; t = 桶末样本 ts"""
    totals = [
        (100, 500), (250, 500), (400, 500), (600, 500), (700, 500), (900, 500), (1100, 500), (1200, 500), (1400, 500)
    ]
    blk = _blk(1000, 2, _samples(totals), 100, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 4000, 2)
    assert res.stride == 3 and len(res.points) == 4
    assert [p["t"] for p in res.points] == [1000.0, 1006.0, 1012.0, 1016.0]  # 桶末样本 ts
    # 桶 166 = {1000}: 链首无基线 -> 0 线(D4); 桶 167 = {1002,1004,1006}: +150/+150/+200
    #   -> 500 / 6000ms = 83.33 -> round 83; 桶 168 = {1008,1010,1012}: +100/+200/+200 -> 83;
    # 桶 169 = {1014,1016}: +100/+200 -> 300 / 4000ms = 75
    assert [p["dl"] for p in res.points] == [0, 83, 83, 75]
    assert all(p["up"] == 0 for p in res.points)  # up 快照恒等 -> 每对 delta 0
    assert [t["dl"] for t in res.totals] == [None, 500, 500, 300]  # 桶 166 基线缺失逐向 None
    assert _totals_sum(res, "dl") == 1400 - 100  # 遥差 = 末快照 - 首窗内样本快照
    assert res.tail_open is True  # 末真值点(最高桶 169) = 活尾组点


def test_tail_group_always_true_value():
    """尾组恒真值 + 组闭合迁移: 10 样本 k=3 桶宽 6s -> 桶 169 = {1014,1016,1018} 恰满 3
    样本, t = 桶末样本 ts, 值 = 已落样本真实均值; 追加样本(1020 落新桶 170)重装配 ->
    桶 169 闭合为脊柱(t/值逐位不变), 新桶点 = 活尾组点(tail_open 恒真)"""
    totals = [
        (100, 500), (250, 500), (400, 500), (600, 500), (700, 500), (900, 500), (1100, 500), (1200, 500), (1400, 500),
        (1700, 500)
    ]
    blk = _blk(1000, 2, _samples(totals), 100, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 4000, 2)
    assert res.stride == 3 and len(res.points) == 4
    tail = res.points[-1]
    assert tail["t"] == 1018.0  # 桶末样本 ts(桶 169 三样本)
    assert tail["dl"] == 100  # (100+200+300) bytes / 6s
    assert res.totals[-1]["dl"] == 600
    assert res.tail_open is True  # k>1 末真值点 = 活尾组点
    # 追加样本(下一 tick, 落新桶 170): 桶 169 闭合为脊柱, 新桶 = 活尾组点
    blk2 = _blk(1000, 2, _samples(totals + [(2000, 500)]), 100, 500)
    res2 = assemble_group_points_from_blocks((blk2, ), 1000, 4000, 2)
    tail2 = res2.points[-1]
    assert tail2["t"] == 1020.0 and tail2["dl"] == 150  # (2000-1700) bytes / 2s
    assert res2.points[:-1] == res.points  # 组闭合迁移: 旧桶点逐位不动(INV-3 对账零形状改写)


def test_byte_conservation_totals_sum_invariant_across_k():
    """字节守恒: 同一槽流不同窗(k=1 vs k=3)Sigma(totals) 恒等且 = 遥差参考; 带窗外种子
    时窗首组含种子差分, Sigma = 末快照 - 种子快照(分组只是重新划界)"""
    totals = [(1000 + 130 * i, 500 + 40 * i) for i in range(12)]
    blk = _blk(1000, 2, _samples(totals), 1000, 500)
    r1 = assemble_group_points_from_blocks((blk, ), 1000, 1060, 2)  # 预期 30 样本 -> k=1
    r3 = assemble_group_points_from_blocks((blk, ), 1000, 4000, 2)  # 预期 1500 样本 -> k=3
    assert r1.stride == 1 and r3.stride == 3
    assert _totals_sum(r1, "dl") == _totals_sum(r3, "dl") == 130 * 11
    assert _totals_sum(r1, "up") == _totals_sum(r3, "up") == 40 * 11
    # 带窗外种子(连续 dt 链, 无缝): 窗首组含种子->窗首样本差分
    blk_seed = _blk(990, 2, _samples([(800 + 130 * i, 400) for i in range(13)]), 800, 400)
    s1 = assemble_group_points_from_blocks((blk_seed, ), 1000, 1060, 2)
    s3 = assemble_group_points_from_blocks((blk_seed, ), 1000, 4000, 2)
    seed_snap = 800 + 130 * 4  # 末个窗外样本(ts 998)快照
    assert _totals_sum(s1, "dl") == _totals_sum(s3, "dl") == (800 + 130 * 12) - seed_snap
    # 窗首桶(时间桶锚): 跨界桶只收窗内成员 —— k=1 首样本点与 k=3 首桶点同 t(窗外种子
    # 差分落窗首成员所在桶, 字节守恒不变)
    assert s1.points[0]["t"] == 1000.0 and s3.points[0]["t"] == 1000.0


def test_gap_bytes_in_successor_sample_diff():
    """漏采区间字节含在后继样本快照差分里: n 游程断连 20s, 后继样本 totals 差分 = 跨缺口
    全量快照差分(1262-1000=262); 速率面诚实缩放不传染 totals 面"""
    blk = _blk(1000, 2, (V4Sample(0, 0, 1000, 500), V4NullRun(10), V4Sample(0, 0, 1262, 631)), 1000, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 1100, 2)
    assert [p["t"] for p in _null_points(res)] == [1002.0]  # n 游程折叠一点
    assert res.totals[2] == {"t": 1022.0, "dl": 262, "up": 131}  # 跨缺口全量差分
    assert res.totals[1] is None and res.totals[0]["dl"] is None  # 空值点 None / 基线缺失
    assert _totals_sum(res, "dl") == 262 == 1262 - 1000  # 遥差守恒


def test_null_points_fold_and_dedup():
    """n 游程折叠一点 + 相邻游程两点(观测槽复位); 缺口前组值与无缺口流逐位相等(空值点
    不影响相邻组均值), 缺口后组按断连面诚实判读"""
    gap_totals = [(100, 500), (250, 500), (400, 500)] + [(400, 500)] * 7
    blk_gap = _blk(
        1000, 2, (V4Sample(0, 0, 100, 500), V4Sample(0, 0, 250, 500), V4Sample(0, 0, 400, 500), V4NullRun(5)) +
        (V4Sample(0, 0, 400, 500), ) * 7, 100, 500
    )
    res = assemble_group_points_from_blocks((blk_gap, ), 1000, 4000, 2)
    assert res.stride == 3  # 预期 1500 样本 -> k 初值 3; 1 标记预算内不调
    marks = _null_points(res)
    assert [p["t"] for p in marks] == [1006.0]  # 5 槽 n 游程折叠一点(floor 首槽)
    # 时间桶锚: 桶 166 = {1000}(链首无基线 0 线), 桶 167 = {1002,1004} = 300/4000 = 75
    # (缺口前桶值与无缺口流逐位相等 —— 空值点不影响相邻桶均值)
    assert res.points[0] == {"t": 1000.0, "dl": 0, "up": 0}
    g0 = res.points[1]
    assert g0["t"] == 1004.0 and g0["dl"] == 75
    assert res.points[3] == {"t": 1018.0, "dl": 0, "up": 0}  # 缺口后桶诚实判读: broke 但已落
    # 缺口前桶值不受空值点影响: 同批前 3 样本单独装配(无缺口流)桶 167 = {1002,1004}
    # 逐位相等(空值点不摊入相邻桶; 时间桶锚下缺口使跨界桶成员变少, 对照流取同批样本)
    blk_clean = _blk(1000, 2, _samples([(100, 500), (250, 500), (400, 500)]), 100, 500)
    clean = assemble_group_points_from_blocks((blk_clean, ), 1000, 4000, 2)
    assert clean.points == res.points[:2]
    # 相邻两游程(观测槽复位)出两点
    blk2 = _blk(
        1000, 2,
        (V4Sample(0, 0, 100, 500), V4NullRun(3), V4Sample(0, 0, 100, 500), V4NullRun(3), V4Sample(0, 0, 100, 500)), 100,
        500
    )
    res2 = assemble_group_points_from_blocks((blk2, ), 1000, 1100, 2)
    assert [p["t"] for p in _null_points(res2)] == [1002.0, 1010.0]


def test_vacuum_mark_between_blocks():
    """块间真空出显式空值点(t = int(链终值), 判定来源承袭); 标记与链末槽组点同 t 共存
    (空值在前 —— 旧 emit 同构; 新契约响应面去重属传输阶段任务)"""
    b1 = _blk(1000, 2, (V4Sample(0, 0, 1000, 500), V4ZeroRun(5, 1000, 500)), 1000, 500)  # 链末槽 @1010
    b2 = _blk(1200, 2, (V4Sample(0, 0, 1262, 631), ), 1000, 500)  # 真空 190s
    res = assemble_group_points_from_blocks((b1, b2), 1000, 1300, 2)
    marks = _null_points(res)
    assert [p["t"] for p in marks] == [1010.0]  # t = int(prev_chain_end)
    same_t = [p for p in res.points if p["t"] == 1010.0]
    assert same_t[0]["dl"] is None and same_t[1]["dl"] == 0  # 空值在前, z 槽组点随后


def test_seam_spread_uniform_no_spike():
    """接缝摊配(提取件复用): 长 z 形冻结游程 + 重启缝台阶按真实跨度摊配(span > cov 部分
    不归因), 游程组 + 接收组均匀平线无单组尖峰, Sigma(值 x 组覆盖) = step_w 守恒"""
    b1 = _blk(1000, 2, (V4Sample(1, 1, 1000, 500), V4ZeroRun(60, 1000, 500, dt_ms=120000)), 1000, 500)
    b2 = _blk(1131, 2, (V4Sample(262, 131, 1262, 631), ), 1000, 500)
    res = assemble_group_points_from_blocks((b1, b2), 1000, 1200, 2)
    assert res.stride == 1
    marks = _null_points(res)
    assert [p["t"] for p in marks] == [1120.0]  # 重启缝真空标记
    real = [p for p in res.points if not (p["dl"] is None and p["up"] is None)]
    assert len(real) == 62  # 1 链首 + 60 游程组 + 1 接收组
    assert real[0]["dl"] == 0  # 链首 0 线
    assert all(p["dl"] == 2 and p["up"] == 1 for p in real[1:])  # 均匀平线, 无单组尖峰
    # 每组覆盖 2s(缝 9s 不归因): Sigma(值 x 覆盖) = 61 x 2 x 2 = 244 = step_w
    assert sum(p["dl"] for p in real[1:]) * 2 == 244
    assert sum(p["up"] for p in real[1:]) * 2 == 122
    assert res.totals[-1] == {"t": 1131.0, "dl": 262, "up": 131}  # totals 面计数器真值
    # Sigma(totals) = 遥差 262/131 —— 游程组 totals 恒 0, 摊配份额不得污染 totals 面
    assert _totals_sum(res, "dl") == 262 == 1262 - 1000
    assert _totals_sum(res, "up") == 131


def test_budget_raises_stride_on_marks():
    """k 上调路径: 990 样本 + 10 标记, 预期 1000 -> k 初值 2 -> 组点 + 空值 > 500,
    上调至 ceil(990/490) = 3 -> 桶宽 4.5s 回到预算内(时间桶锚下空值点间隔使桶成员
    跨桶漂移, 桶数不恰等于 990/3 —— 预算判据不变: 总点数 <= MAX_RAW_POINTS)"""
    records = []
    snap = 100
    for _ in range(10):
        for _ in range(99):
            records.append(V4Sample(0, 0, snap, 50))
        records.append(V4NullRun(1))
    blk = _blk(0, 1.5, tuple(records), 100, 50)
    res = assemble_group_points_from_blocks((blk, ), 0, 1500, 1.5)
    assert res.stride == 3 and not res.over_budget
    assert len(res.points) == 343  # 时间桶锚下点数纯 ts 确定: 333 桶点 + 10 空值(修后实测薛写)
    assert len(_null_points(res)) == 10


def test_over_budget_honest_delivery():
    """不可达角: 缺口标记数 >= 500 -> 预算数学不可达, 按 k 上限(窗内样本数)交付并置
    over_budget; 空值点一个不弃(诚实优先于预算), 终止行为有定义"""
    records = []
    for _ in range(501):
        records.append(V4Sample(0, 0, 100, 50))
        records.append(V4NullRun(1))
    blk = _blk(0, 1.5, tuple(records), 100, 50)
    res = assemble_group_points_from_blocks((blk, ), 0, 1504, 1.5)
    assert res.over_budget is True
    assert res.stride == 501  # k 上限 = 窗内样本数; 桶宽 751.5s -> 样本跨两桶
    assert len(_null_points(res)) == 501  # 缺口显式空值语义不弃
    assert len(res.points) == 503  # 2 组点 + 501 空值点(超预算如实)
    groups = _real_points(res)
    assert [p["t"] for p in groups] == [750.0, 1500.0]  # 桶 0 = 样本 0..250 / 桶 1 = 251..500
    assert all(p["dl"] == 0 for p in groups)  # 平坦 totals -> 等值差分 0
    assert res.totals[-1] is None  # 末位为空值点
    assert res.tail_open is False  # 尾随空值点居末: points[-1] 非活尾组点(26-11-27 评审修复语义; 旧 any(totals) 推导误 True)


def test_stride_capped_at_window_samples():
    """k 上限 = 窗内实际样本数: 预期 8000 样本 -> k 初值 16, 实际仅 3 样本 -> 夹取到 3
    (组点 1), 无组点收益的超额 k 不出现"""
    blk = _blk(1000, 1.5, _samples([(100, 50), (160, 50), (220, 50)]), 100, 50)
    res = assemble_group_points_from_blocks((blk, ), 1000, 13000, 1.5)
    assert res.stride == 3 and len(res.points) == 1
    assert res.points[0] == {"t": 1003.0, "dl": 40, "up": 0}  # (60+60) bytes / 3s


def test_reset_and_hole_semantics():
    """计数器重置(cur < last)-> 差分 None: k=1 组值 0 线(D4 同判), totals 逐向 None;
    后继样本立新链恢复真值。缝 > 60s 停机洞 -> 组值 None(断链), totals 仍含跨洞快照差分"""
    blk = _blk(1000, 2, (V4Sample(0, 0, 1000, 500), V4Sample(0, 0, 500, 300), V4Sample(0, 0, 700, 400)), 1000, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 1100, 2)
    assert res.points[1] == {"t": 1002.0, "dl": 0, "up": 0}  # 重置: 差分 None -> 0 线
    assert res.totals[1] == {"t": 1002.0, "dl": None, "up": None}  # 逐向重置 None
    assert res.points[2] == {"t": 1004.0, "dl": 100, "up": 50}  # 新链: 200/2s, 100/2s
    assert res.totals[2] == {"t": 1004.0, "dl": 200, "up": 100}
    # 停机洞: 块间真空 120s(> 60s 阈值)
    b1 = _blk(1000, 2, (V4Sample(0, 0, 1000, 500), ), 1000, 500)
    b2 = _blk(1122, 2, (V4Sample(0, 0, 1262, 631), ), 1000, 500)
    res2 = assemble_group_points_from_blocks((b1, b2), 1000, 1300, 2)
    hole_pt = [p for p in res2.points if p["t"] == 1122.0][0]
    assert hole_pt["dl"] is None and hole_pt["up"] is None  # 洞后断链未知
    assert res2.totals[-1] == {"t": 1122.0, "dl": 262, "up": 131}  # 跨洞快照差分仍真值


def test_tail_open_whole_window_reset_form():
    """tail_open 整窗重置形态(26-11-27 评审反例2): k>1 全组 0 线/totals 逐向 None ——
    计数器逐样本回退(全重置)+ 窗首无种子, 旧 any(totals) 推导在该形态误 False; 修复后
    按发射列尾点身份推导: points[-1] 是活尾组点(最高时间桶) -> True, 与前端二分契约
    (points[:-1] 脊柱 + points[-1] 活尾)一致"""
    totals = [
        (2000, 1000),
        (1800, 900),
        (1600, 800),
        (1400, 700),
        (1200, 600),
        (1000, 500),
        (800, 400),
        (600, 300),
        (400, 200),
        (200, 100),
    ]  # 逐样本回退 = 每对差分重置 None; 1000..1018 每 2s
    blk = _blk(1000, 2, _samples(totals), 2000, 1000)
    res = assemble_group_points_from_blocks((blk, ), 1000, 5000, 2)
    assert res.stride == 4  # 预期 2000 样本 -> k 初值 4, 桶宽 8s
    assert all(p["dl"] == 0 and p["up"] == 0 for p in res.points)  # 全组 0 线(重置差分 None)
    assert all(t is not None and t["dl"] is None and t["up"] is None for t in res.totals)
    assert res.tail_open is True  # points[-1] = 活尾组点(身份判定, 不看 totals)
    assert res.totals[-1] is not None  # 尾项是组点(totals dict)非空值点 —— 与旧判定失配形态互斥
    assert res.points[-1]["t"] == 1018.0  # 最高桶 127 = {1016, 1018}, 桶末样本 ts


def test_window_filter_and_seed_baseline():
    """窗尾外槽不消费(ts >= t1), 窗外前缀只作差分基线不产组点; 窗内首样本对窗外种子的
    差分落在窗首组(窗首种子 D3), 消费下界 = t0 - si - 回看界之外的更早槽不进差分链"""
    totals = [(800 + 100 * i, 400) for i in range(15)]  # 990..1018 每 2s
    blk = _blk(990, 2, _samples(totals), 800, 400)
    res = assemble_group_points_from_blocks((blk, ), 1000, 1010, 2)
    assert res.stride == 1  # 预期 5 样本
    assert [p["t"] for p in res.points] == [1000.0, 1002.0, 1004.0, 1006.0, 1008.0]  # 1010 排除
    assert res.points[0]["dl"] == 50  # 种子(998, 1300) -> (1000, 1400): 100 bytes / 2s
    assert res.totals[0]["dl"] == 100  # totals 首组含种子差分
    # 消费下界之外(> 回看界)的更早槽: 不进差分链 -> 窗首样本无基线 0 线
    far = _blk(5000, 2, _samples([(10, 10), (20, 20)]), 10, 10)
    near = _blk(100000, 2, _samples([(30, 30), (60, 60)]), 30, 30)
    res2 = assemble_group_points(v4_series_slots((far, near)), 100000, 100100, 2)
    assert res2.points[0] == {"t": 100000.0, "dl": 0, "up": 0}  # 链首 0 线(旧槽不接链)
    assert res2.points[1] == {"t": 100002.0, "dl": 15, "up": 15}


def test_marks_outside_window_not_emitted():
    """窗前 n 游程与真空不产空值点(断连面 marked 语义仍生效), 窗尾外标记同样不产;
    窗尾外块引发的真空标记若 t 落窗内仍产出(断口起点在窗内, 承袭判定)"""
    blk = _blk(
        990, 2, (V4Sample(0, 0, 100, 500), V4NullRun(3), V4Sample(0, 0, 100, 500)) +
        tuple(V4Sample(0, 0, 100, 500) for _ in range(10)), 100, 500
    )
    res = assemble_group_points_from_blocks((blk, ), 1000, 1100, 2)
    assert not _null_points(res)  # 窗前 n 游程(994)不产点
    assert res.points[0]["t"] == 1000.0
    # 窗尾外 n 游程: 首槽 ts >= t1 -> 不产点
    blk2 = _blk(1000, 2, tuple(V4Sample(0, 0, 100, 500) for _ in range(5)) + (V4NullRun(5), ), 100, 500)
    res2 = assemble_group_points_from_blocks((blk2, ), 1000, 1010, 2)
    assert not _null_points(res2)
    assert len(res2.points) == 5
    # 窗尾外块的真空标记: 标记 t = 链终值(1008) < t1 -> 产出(断口起点在窗内)
    b1 = _blk(1000, 2, tuple(V4Sample(0, 0, 100, 500) for _ in range(5)), 100, 500)
    b2 = _blk(1200, 2, (V4Sample(0, 0, 200, 500), ), 100, 500)
    res3 = assemble_group_points_from_blocks((b1, b2), 1000, 1010, 2)
    assert [p["t"] for p in _null_points(res3)] == [1008.0]


def test_fail_fast_invalid_inputs():
    """入参非法 fail-fast: 窗口倒挂/非有限数值/bool/si 非正/槽流倒挂/非 V4Slot
    (is_hold 持有槽拒收支已随持有面退役删除: V4Slot.is_hold 字段同批退役)"""
    blk = _blk(1000, 2, _samples([(100, 50), (160, 50)]), 100, 50)
    slots = v4_block_slots(blk)
    with pytest.raises(ValueError, match="窗口非法"):
        assemble_group_points(slots, 1000, 1000, 2)
    with pytest.raises(ValueError, match="窗口非法"):
        assemble_group_points(slots, 1001, 1000, 2)
    with pytest.raises(ValueError, match="非法 t0"):
        assemble_group_points(slots, float("nan"), 2000, 2)
    with pytest.raises(ValueError, match="非法 t1"):
        assemble_group_points(slots, 1000, float("inf"), 2)
    with pytest.raises(ValueError, match="非法 t0"):
        assemble_group_points(slots, True, 2000, 2)
    with pytest.raises(ValueError, match="非法 sample_interval_s"):
        assemble_group_points(slots, 1000, 2000, 0)
    with pytest.raises(ValueError, match="非法 sample_interval_s"):
        assemble_group_points(slots, 1000, 2000, -1.5)
    with pytest.raises(ValueError, match="时序倒挂"):
        assemble_group_points(tuple(reversed(slots)), 1000, 2000, 2)
    with pytest.raises(TypeError, match="非 V4Slot"):
        assemble_group_points((object(), ), 1000, 2000, 2)


def test_member_points_isomorphic():
    """组端点同构: 同 tick 采样的两个成员(同槽 ts 序列, 含 z/n 游程与块缝)各自装配,
    点列 t 逐位相等、stride 相等、空值点位置相等 —— 组端点 Sigma 现算可对齐"""
    recs = (
        V4Sample(0, 0, 100, 50), V4ZeroRun(3, 100, 50), V4Sample(0, 0, 220,
                                                                 110), V4NullRun(2), V4Sample(0, 0, 300, 150)
    )
    ma = _blk(1000, 2, recs, 100, 50)
    mb = _blk(
        1000, 2, (V4Sample(0, 0, 7, 3), V4ZeroRun(3, 7, 3), V4Sample(0, 0, 9, 4), V4NullRun(2), V4Sample(0, 0, 11, 5)),
        7, 3
    )
    ra = assemble_group_points_from_blocks((ma, _blk(1200, 2, (V4Sample(0, 0, 400, 200), ), 300, 150)), 1000, 1300, 2)
    rb = assemble_group_points_from_blocks((mb, _blk(1200, 2, (V4Sample(0, 0, 13, 6), ), 11, 5)), 1000, 1300, 2)
    assert ra.stride == rb.stride
    assert [p["t"] for p in ra.points] == [p["t"] for p in rb.points]
    assert [p["t"] for p in _null_points(ra)] == [p["t"] for p in _null_points(rb)] == [1010.0, 1014.0]
    assert len(ra.points) == len(rb.points)


def test_from_blocks_wrapper_uses_series_slots():
    """便捷入口复用 v4_series_slots 平展: 乱序块还原时间序, 与直喂槽流结果逐位相等"""
    b1 = _blk(1000, 2, (V4Sample(0, 0, 100, 50), ), 100, 50)
    b2 = _blk(1004, 2, (V4Sample(0, 0, 200, 50), ), 100, 50)
    via_blocks = assemble_group_points_from_blocks((b2, b1), 1000, 1100, 2)  # 乱序传入
    direct = assemble_group_points(v4_series_slots((b1, b2)), 1000, 1100, 2)
    assert via_blocks == direct
    # 块界 2s 断口(1000 -> 1004 缺一槽)出真空标记@1000, 与链末组点同 t 共存(空值在前)
    assert [p["t"] for p in via_blocks.points] == [1000.0, 1000.0, 1004.0]
    assert [p["t"] for p in _null_points(via_blocks)] == [1000.0]


def test_seam_spread_helper_contract():
    """摊配提取件直钉(_seam_spread_delta): z 形游程 + marked 触发份额分配(累计比例取整,
    余额归接收方); 非 z 形签名(r 槽)不摊配返回 step; marked 且空游程返回缩放基准"""
    shares = []

    def add(key, d, share):
        shares.append((key, d, share))

    run_list = [(10, 2000, True, 1100.0), (11, 2000, True, 1102.0)]
    # span 6000 == cov 4000 + 对跨 2000: marked 触发 -> step_w = step; 份额按累计比例
    delta = _seam_spread_delta(0, 60, 6000, 6000, 2000, 2.0, True, run_list, 0, add)
    assert delta == 20  # 60 x 2000//6000 = 20 首项, 余额 40... 累计: 20->40, 余额 = 60-40
    assert shares == [(10, 0, 20), (11, 0, 20)]
    # 非 z 形签名: 不摊配, marked 为假 -> 全额 step
    shares.clear()
    flat = [(10, 2000, False, 1100.0)]
    assert _seam_spread_delta(0, 60, 6000, 6000, 2000, 2.0, False, flat, 0, add) == 60
    assert shares == []
    # marked 且空游程: 缩放基准 = step x cov // span(span > cov 未覆盖秒不归因)
    assert _seam_spread_delta(0, 100, 4000, 2000, 2000, 2.0, True, [], 0, add) == 50
    # 无标记且 span 未超界: 不摊配 -> step
    assert _seam_spread_delta(0, 100, 4000, 4000, 2000, 2.0, False, flat, 0, add) == 100


def test_pre_window_gap_and_stuck_run_faces():
    """窗外断连面与摊配弃入: 真空标记 t 在窗前(t < t0)不产空值点但断连面生效(后继组
    断链未知); 窗外长 z 形冻结游程 + 窗内台阶 -> 摊配触发, 窗外游程槽份额无组可入
    (bucket_add 键 None 早退), 响应面不受窗外份额影响"""
    # 真空标记 t = int(990) < t0=1000: 不产点; marked 仍生效 -> 窗内首样本跨 98s 未观测段
    b1 = _blk(990, 2, (V4Sample(0, 0, 100, 50), ), 100, 50)
    b2 = _blk(1090, 2, _samples([(200, 50), (300, 50), (400, 50), (500, 50)]), 100, 50)
    res = assemble_group_points_from_blocks((b1, b2), 1000, 1200, 2)
    assert not _null_points(res)  # 标记在窗前不产点
    assert [p["t"] for p in res.points] == [1090.0, 1092.0, 1094.0, 1096.0]
    assert res.points[0]["dl"] is None  # 98s 未观测 > 60s 洞阈值 -> 断链未知(totals 仍 dict)
    # 窗外 z 游程(4 槽在窗前)+ 窗内 36 槽等值 + 台阶: 摊配触发, 窗前份额弃入
    blk = _blk(990, 2, (V4Sample(0, 0, 100, 50), V4ZeroRun(40, 100, 50), V4Sample(0, 0, 200, 100)), 100, 50)
    res2 = assemble_group_points_from_blocks((blk, ), 1000, 1200, 2)
    assert res2.stride == 1 and not res2.over_budget
    assert res2.points[-1]["t"] == 1072.0 and not _null_points(res2)  # 台阶接收组, 无缺口标记


def test_all_null_window_no_samples():
    """窗内 0 样本全缺口形态: 仅 n 游程覆盖全窗(无基线块, 仅 n 游程合法形态)-> points
    只含显式空值点、stride=1、不炸; 槽全在窗外 -> 空点列(天然真空空态)"""
    blk = _blk(1000, 2, (V4NullRun(10), ))  # n 槽 @1000..1018
    res = assemble_group_points_from_blocks((blk, ), 1000, 1030, 2)
    assert res.stride == 1 and not res.over_budget  # 0 样本 1 标记 -> 预算内
    assert [p["t"] for p in res.points] == [1000.0]  # 游程折叠一点
    assert res.points[0] == {"t": 1000.0, "dl": None, "up": None}
    assert res.totals == (None, )
    res2 = assemble_group_points_from_blocks((blk, ), 2000, 2100, 2)  # 槽全在窗外
    assert res2.points == () and res2.totals == () and res2.stride == 1
    assert res.tail_open is False and res2.tail_open is False  # 无组点窗(纯缺口/空列)


def test_spine_stable_across_sliding_window():
    """脊柱跨滑动窗逐位不动(INV-3 对账零形状改写, S0 症状3 根因修复): 同一槽流两次
    GET(窗沿平移 30s), 内桶点(脊柱)t/值逐位相等 —— 桶界是纯 ts 函数与窗位置无关;
    窗首跨界桶只收窗内成员(窗外同桶样本弃入)单点有界改写, 左缘桶随窗滑出即丢,
    不整列改写(旧窗内序号锚下全列换格)"""
    # 2s 节律 771 样本(1000..2540); 交替差分(偶数样本 300 / 奇数样本 900)让桶均值
    # 对成员集敏感 —— 跨界桶的部分成员改写可见, 内桶逐位不动可断言
    totals = [(100, 50)]
    for i in range(1, 771):
        totals.append((totals[-1][0] + (300 if i % 2 == 0 else 900), 50))
    blk = _blk(1000, 2, _samples(totals), 100, 50)
    r1 = assemble_group_points_from_blocks((blk, ), 1000, 2500, 2)  # 预期 750 样本 -> k=2, 桶宽 4s
    r2 = assemble_group_points_from_blocks((blk, ), 1030, 2530, 2)  # 窗沿平移 30s(一次对账)
    assert r1.stride == 2 and r2.stride == 2
    assert r1.tail_open is True and r2.tail_open is True
    d1 = {p["t"]: p for p in r1.points}
    d2 = {p["t"]: p for p in r2.points}
    # 内桶(脊柱): 两窗共同覆盖的非边缘桶逐位相等(桶 258..623, t = 4g+2; 两窗尾桶
    # 624/632 与跨界桶 250/257 除外)
    for g in range(258, 624):
        t = g * 4 + 2
        assert d1[t] == d2[t], f"桶 {g} 跨窗改写: {d1[t]} != {d2[t]}"
    # 窗首跨界桶单点有界改写: r1 桶 250 = {1000,1002} = 450; r2 同桶已滑出窗(左缘丢弃);
    # r2 跨界桶 257 只收窗内成员 {1030} = 450(1028 弃入 —— r1 同桶全成员均值 300)
    assert d1[1002.0]["dl"] == 450 and d1[1030.0]["dl"] == 300
    assert d2[1030.0]["dl"] == 450 and 1002.0 not in d2
    # 尾桶 = 最高时间桶(活尾组点)随窗尾前移
    assert r1.points[-1]["t"] == 2498.0 and r2.points[-1]["t"] == 2528.0


def test_zero_coverage_pair_not_attributed():
    """同刻病理槽序(dt_ms=0 双样本同刻): 对跨 0 -> 覆盖 0, 差分不归因不造分母(防御面),
    速率组值 0 线不炸; totals 面快照差分照常入账(计数器真值不受速率归因影响)"""
    blk = _blk(1000, 2, (V4Sample(0, 0, 100, 50), V4Sample(0, 0, 200, 100, dt_ms=0)), 100, 50)
    res = assemble_group_points_from_blocks((blk, ), 1000, 1010, 2)
    assert res.stride == 1
    assert len(res.points) == 2  # 两样本同刻但 k=1 各成一组
    assert res.points[0] == {"t": 1000.0, "dl": 0, "up": 0}  # 链首无基线 -> 0 线
    assert res.points[1] == {"t": 1000.0, "dl": 0, "up": 0}  # 覆盖 0 不归因 -> 无差分对 -> 0 线
    assert res.totals[0] == {"t": 1000.0, "dl": None, "up": None}  # 基线缺失
    assert res.totals[1] == {"t": 1000.0, "dl": 100, "up": 50}  # 快照差分照常真值


def test_marked_r_run_equal_chain_drops_delta():
    """r 形等值游程(非 z 签名)+ n 断连标记 + 台阶: 摊配判定 all(z) 不成立且 marked 存活
    -> 差分 None 断链, 组值 None(诚实丢字节非 0 线); totals 面快照差分照常真值"""
    blk = _blk(
        1000, 2, (V4Sample(0, 0, 100, 50), V4Sample(0, 0, 100, 50), V4NullRun(2), V4Sample(0, 0, 200, 100)), 100, 50
    )
    res = assemble_group_points_from_blocks((blk, ), 1000, 1100, 2)
    assert res.stride == 1
    assert [p["t"] for p in _null_points(res)] == [1004.0]  # n 标记一点
    assert res.points[1] == {"t": 1002.0, "dl": 0, "up": 0}  # 等值 r 槽: 差分 0 正常入组
    assert res.points[3] == {"t": 1008.0, "dl": None, "up": None}  # marked + 非 z 游程 -> 断链
    assert res.totals[3] == {"t": 1008.0, "dl": 100, "up": 50}  # totals 真值(断链不传染)


def test_eps_band_regression_no_end_ts_rewrite():
    """eps 带内回退槽(-eps 抖动, 时序守卫放行): 组末 ts/快照不被更晚入列但 ts 更早的槽
    回写(快照取 ts 最晚者, 旧面同判); totals 逐样本差分照常按槽归属入账(计数器真值);
    抖动槽与前一槽同桶(桶界 1000/1004 之间)"""
    s1 = V4Slot(ts=1002.0, dt_s=2.0, obs=(0, 0, 100, 50), is_zero=False)
    s2 = V4Slot(ts=1002.0 - 1e-7, dt_s=2.0, obs=(0, 0, 200, 100), is_zero=False)  # 抖动 1e-7 < eps 容差带
    res = assemble_group_points((s1, s2), 1001, 2002, 2)  # 预期 500.5 样本 -> k=2, 桶宽 4s 两样本同桶
    assert res.stride == 2
    assert res.points[0] == {"t": 1002.0, "dl": 0, "up": 0}  # 组末 ts 恒 1002.0(不被 1001.9999999 回写)
    assert res.totals[0] == {"t": 1002.0, "dl": 100, "up": 50}  # s2 快照差分照常入账
    assert res.tail_open is True


def test_empty_slot_stream():
    """空槽流: 空点列空 totals, stride=1, 不炸(无块且无观测 = 天然真空空态)"""
    res = assemble_group_points((), 1000, 2000, 1.5)
    assert isinstance(res, GroupAssemblyResult)
    assert res.points == () and res.totals == ()
    assert res.stride == 1 and res.over_budget is False
