"""test_traffic_group_assembly 测试计划: 样本分组装配读侧纯函数(plan 26-11-18-0037 阶段 1,
§03 读侧契约逐条钉面 —— points 形态/分组口径 k/尾组/字节守恒/null 显式空值/fail-fast)

## 测试计划(每个测试函数一条)
- test_k1_short_window_per_sample: 短窗 k=1 逐样本(1m 40 样本形态)—— 每样本一点,
  t = 样本 ts, 值 = 逐样本差分/覆盖; 无缝链首 0 线(D4); totals 基线缺失逐向 None
- test_k_gt1_group_mean_bitwise: 长窗 k>1 均值逐位对账 —— 组值 = Sigma delta x 1000 /
  Sigma 覆盖毫秒(round 取整), 跨组界差分对按端点归属后组(锚换样本索引), t = 组末样本 ts
- test_tail_group_always_true_value: 尾组恒真值 —— 不满 k 的进行中组 t = 最新样本 ts,
  值 = 已落样本真实均值; 追加样本后尾组重算(t/值更新, 无克隆无持有)
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
  时 k 从初值上调至最小达标值, 总点数回落到预算内
- test_over_budget_honest_delivery: 不可达角(缺口标记数 >= 500)—— 按 k 上限(窗内样本数)
  交付, over_budget=True 如实标注, 空值点一个不弃(诚实优先于预算)
- test_stride_capped_at_window_samples: k 上限 = 窗内实际样本数(k 初值超样本数时夹取)
- test_reset_and_hole_semantics: 计数器重置 -> 差分 None 组值 0 线/totals 逐向 None,
  后继样本新链恢复; 缝 > 60s 停机洞 -> 组值 None(totals 仍含跨洞快照差分)
- test_window_filter_and_seed_baseline: 窗尾外槽不消费(ts >= t1), 窗外前缀只作差分基线
  不产组点; 窗内首样本对窗外种子的差分落在窗首组(窗首种子 D3)
- test_marks_outside_window_not_emitted: 窗前 n 游程/真空不产空值点(断连面 marked 语义
  仍生效), 窗尾外标记同样不产
- test_fail_fast_invalid_inputs: 入参非法 fail-fast —— 窗口倒挂/非有限数值/bool/si 非正/
  槽流时序倒挂/is_hold 持有槽/非 V4Slot 项, 一律 raise 不静默修复
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
  只含显式空值点、stride=1、不炸; 槽全在窗外 -> 空点列(天然真空)
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
    MAX_RAW_POINTS,
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
    assert res.totals[0] == {"t": 1000.0, "dl": None, "up": None}  # 基线缺失
    assert all(t["dl"] == 150 and t["up"] == 60 for t in res.totals[1:])
    assert _totals_sum(res, "dl") == 150 * 39  # = 末快照 - 首快照(遥差)


def test_k_gt1_group_mean_bitwise():
    """长窗 k>1 均值逐位对账: 窗 [1000,4000)/2s 预期 1500 样本 -> k=3; 组值 = Sigma delta
    x 1000 / Sigma 覆盖毫秒; 跨组界差分对(s3 对 s2)按端点归属后组 —— 锚换样本索引"""
    totals = [
        (100, 500), (250, 500), (400, 500), (600, 500), (700, 500), (900, 500), (1100, 500), (1200, 500), (1400, 500)
    ]
    blk = _blk(1000, 2, _samples(totals), 100, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 4000, 2)
    assert res.stride == 3 and len(res.points) == 3
    assert [p["t"] for p in res.points] == [1004.0, 1010.0, 1016.0]  # 组末样本 ts
    # g0: 样本0 无基线 + 样本1/2 各 +150/2s -> 300 bytes / 4000ms = 75 B/s
    # g1: 跨界对 s3(+200) + s4(+100) + s5(+200) -> 500 / 6000ms = 83.33 -> round 83
    assert [p["dl"] for p in res.points] == [75, 83, 83]
    assert all(p["up"] == 0 for p in res.points)  # up 快照恒等 -> 每对 delta 0
    assert [t["dl"] for t in res.totals] == [300, 500, 500]  # 组内逐样本差分和
    assert _totals_sum(res, "dl") == 1400 - 100  # 遥差 = 末快照 - 首窗内样本快照


def test_tail_group_always_true_value():
    """尾组恒真值: 10 样本 k=3 -> 末组 1 样本(进行中), t = 最新样本 ts, 值 = 已落样本
    真实均值(差分/覆盖); 追加一个样本重装配 -> 尾组 t/值随真样本更新(无克隆)"""
    totals = [
        (100, 500), (250, 500), (400, 500), (600, 500), (700, 500), (900, 500), (1100, 500), (1200, 500), (1400, 500),
        (1700, 500)
    ]
    blk = _blk(1000, 2, _samples(totals), 100, 500)
    res = assemble_group_points_from_blocks((blk, ), 1000, 4000, 2)
    assert res.stride == 3 and len(res.points) == 4
    tail = res.points[-1]
    assert tail["t"] == 1018.0  # 最新样本 ts
    assert tail["dl"] == 150  # (1700-1400) bytes / 2s
    assert res.totals[-1]["dl"] == 300
    # 追加样本(下一 tick): 尾组重算, 组员变为 2 个, 值/t 更新
    blk2 = _blk(1000, 2, _samples(totals + [(2000, 500)]), 100, 500)
    res2 = assemble_group_points_from_blocks((blk2, ), 1000, 4000, 2)
    tail2 = res2.points[-1]
    assert tail2["t"] == 1020.0 and tail2["dl"] == 150  # (300+300) bytes / 4s
    assert res2.points[:-1] == res.points[:-1]  # 已定影组不受尾组影响


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
    assert s1.points[0]["t"] == 1000.0 and s3.points[0]["t"] == 1004.0  # 窗首组组末样本


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
    g0 = res.points[0]
    assert g0["t"] == 1004.0 and g0["dl"] == 75  # 缺口前组: 与无缺口流同对同值
    assert res.points[2] == {"t": 1020.0, "dl": 0, "up": 0}  # 缺口后组诚实判读: broke 但已落
    # 差分真实(等值链 0) -> 0 线非 None; 断口对不凭空归因(marked 等值入列差分恒 0)
    blk_clean = _blk(1000, 2, _samples([(100, 500), (250, 500), (400, 500)] + [(400, 500)] * 7), 100, 500)
    clean = assemble_group_points_from_blocks((blk_clean, ), 1000, 4000, 2)
    assert clean.points[0] == g0 and not _null_points(clean)
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
    """k 上调路径: 990 样本 + 10 标记, 预期 1000 -> k 初值 2 -> 组点 495 + 10 = 505 > 500,
    上调至 ceil(990/490) = 3 -> 组点 330 + 10 = 340 回到预算内"""
    records = []
    snap = 100
    for _ in range(10):
        for _ in range(99):
            records.append(V4Sample(0, 0, snap, 50))
        records.append(V4NullRun(1))
    blk = _blk(0, 1.5, tuple(records), 100, 50)
    res = assemble_group_points_from_blocks((blk, ), 0, 1500, 1.5)
    assert res.stride == 3 and not res.over_budget
    assert len(res.points) == 330 + 10 <= MAX_RAW_POINTS
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
    assert res.stride == 501  # k 上限 = 窗内样本数
    assert len(_null_points(res)) == 501  # 缺口显式空值语义不弃
    assert len(res.points) == 502  # 1 组点 + 501 空值点(超预算如实)
    groups = _real_points(res)
    assert len(groups) == 1 and groups[0]["t"] == 1500.0  # 全部样本一组, t = 末样本 ts
    assert groups[0]["dl"] == 0  # 平坦 totals -> 等值差分 0
    assert res.totals[-1] is None  # 末位为空值点


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
    """入参非法 fail-fast: 窗口倒挂/非有限数值/bool/si 非正/槽流倒挂/is_hold/非 V4Slot"""
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
    hold = V4Slot(ts=1005.0, dt_s=2.0, obs=(0, 0, 100, 50), is_zero=False, is_hold=True)
    with pytest.raises(ValueError, match="持有槽"):
        assemble_group_points(slots + (hold, ), 1000, 2000, 2)
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
    """eps 带内回退槽(-eps 抖动, 时序守卫放行): 组末 ts/快照不被更早槽回写(快照取 ts
    最晚者, 旧面同判); totals 逐样本差分照常按槽归属入账(计数器真值)"""
    s1 = V4Slot(ts=1000.0, dt_s=2.0, obs=(0, 0, 100, 50), is_zero=False)
    s2 = V4Slot(ts=1000.0 - 1e-7, dt_s=2.0, obs=(0, 0, 200, 100), is_zero=False)  # 抖动 1e-7 < eps 容差带
    res = assemble_group_points((s1, s2), 999, 2000, 2)  # 预期 500.5 样本 -> k=2, 两样本同组
    assert res.stride == 2
    assert res.points[0] == {"t": 1000.0, "dl": 0, "up": 0}  # 组末 ts 恒 1000(不被 999.9999999 回写)
    assert res.totals[0] == {"t": 1000.0, "dl": 100, "up": 50}  # s2 快照差分照常入账


def test_empty_slot_stream():
    """空槽流: 空点列空 totals, stride=1, 不炸(无块且无观测 = 天然真空空态)"""
    res = assemble_group_points((), 1000, 2000, 1.5)
    assert isinstance(res, GroupAssemblyResult)
    assert res.points == () and res.totals == ()
    assert res.stride == 1 and res.over_budget is False
