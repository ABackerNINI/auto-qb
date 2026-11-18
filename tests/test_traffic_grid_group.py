"""test_traffic_grid_group 测试计划: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v4 换代 plan 26-10-05-2200 N1; 26-11-15-1104 F2 点位归属归桶 —— 消费 v4_series_points -> v4_grid_obs 的两条用例改判重锚, 其余组聚合断言零变化)

## 测试计划(每个测试函数一条)
- test_group_null_mask_rules: (D6 沿用)组桶 null = 无任何成员观测(任一成员 r/z 观测即程序存活真值); 无行成员按 0 计; 借 global 判 null 退役
- test_group_rate_sums_members_missing_zero: 组速率 = 桶内 Σ 成员均值, 无行成员按 0 计; null 桶整桶 None
- test_group_totals_per_member_diff_then_sum: 逐成员先差分再求和 —— 单成员重置贡献 0 不拖垮全组; 成员基线缺失(窗首/无行)贡献 0; null 桶断链
- test_group_50_members_correct_and_time_bound: 50 成员 x 满窗完整桶(24h@30s 直构栅格 480 完整桶) + 1 进行中桶(26-11-14-1313 F3 floor+1, 尾桶窗内无观测 = null)聚合正确性(抽样桶 Σ 校验, 每成员 obs 直构) + 耗时上界(CPU 时间口径 << 采样间隔 30s, 断言 < 8s)
- test_group_zrun_idle_zero_line_and_outage_null: (D6 沿用)组图回归观测面 —— 全员空闲(z 覆盖)0 线 / 全员无观测(停机)断线 / 成员只剩 z 块也有观测; 组三函数消费 BucketObs 观测表(26-11-18-0037 T1c-2 后 obs 由直构/agg 直映面供给, 旧 v4_grid_obs 随挂钟桶面退役)
- test_group_rate_points_over_transformed_obs_unchanged: 组求和口径不变(S1 钉住)—— group_null_mask/group_rate_points 消费变换后 obs
- test_group_totals_up_direction_reset_independent
- test_group_totals_up_sums_across_members: (gtp_28)组累计上行 = 逐成员差分再求和(多成员非零 up 增量, 此前池内 up 恒 0 撞不出)
- test_group_totals_member_gap_does_not_truncate: (gtp_17)前位成员缺行是 continue 不是截断 —— 后位成员贡献照常计入

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 组员观测 BucketObs
直构(26-11-18-0037 T1c-2: 旧 v4_series_points -> v4_grid_obs 数据面随挂钟桶面退役,
raw 面组聚合走 traffic_qb._group_merge_points, 本电池钉 agg 段窗组三函数语义)。
"""

import time

import pytest

from auto_qb.core.traffic_grid import (
    BucketObs,
    WindowGrid,
    group_null_mask,
    group_rate_points,
    group_totals_points,
    _floor_buckets,
)

from traffic_grid_support import NOW


def _grid_24h_30s():
    """(T1c-2 解耦)组三函数语义电池的固定 24h/30s 栅格: 直构 WindowGrid(raw 桶面退役后
    build_grid 对 raw 段不再产桶; 组聚合语义钉的是既定栅格上的行为而非桶宽规则)"""
    t1 = NOW
    t0 = t1 - 86400
    return WindowGrid("24h", t0, t1, 30, "raw", _floor_buckets(t0, t1, 30))


def test_group_null_mask_rules():
    """组桶 null 判定(D6 沿用: 借 global 判 null 退役, §05.1): 桶内任一成员有观测
    (r/z)即非 null —— 采样器全局同拍, 单成员观测 = 程序存活真值; 无行成员按 0 计;
    全员无观测(停机/断连/组尚无任何观测)-> null"""
    g = _grid_24h_30s()
    b0, b1, b2 = g.buckets[10], g.buckets[11], g.buckets[12]
    m1 = {b0: BucketObs(1, 1, 1, 1), b2: BucketObs(1, 1, 1, 1)}  # m1 在 b1 无行
    m2 = {b1: BucketObs(5, 5, 1, 1)}  # b1 只有 m2 有行
    mask = group_null_mask([m1, m2], g)
    assert mask[10] is False and mask[11] is False and mask[12] is False
    # b1 全员无观测 -> null; 早于全部成员最早观测的桶必然无观测, 一并 null(v2 earliest 门被吞并)
    mask2 = group_null_mask([m1], g)
    assert mask2[10] is False and mask2[11] is True and mask2[12] is False
    assert all(m for m in mask2[:10])  # 组尚无观测的桶全 null


def test_group_rate_sums_members_missing_zero():
    """组速率 = 桶内 Σ 成员均值, 无行成员按 0 计(全员空闲出 0 线); null 桶整桶 None"""
    g = _grid_24h_30s()
    b0, b1 = g.buckets[10], g.buckets[11]
    m1 = {b0: BucketObs(100, 10, 0, 0)}
    m2 = {b0: BucketObs(50, 5, 0, 0), b1: BucketObs(70, 7, 0, 0)}  # m1 在 b1 空闲 -> 按 0 计
    mask = [False] * len(g.buckets)
    mask[11] = False
    mask[12] = True  # 停机桶
    pts = group_rate_points([m1, m2], g, mask)
    assert pts[10] == {"t": b0, "dl": 150, "up": 15}
    assert pts[11] == {"t": b1, "dl": 70, "up": 7}  # 全员空闲的桶出 0 线由 mask=False 保证
    assert pts[12] is None
    empty_bucket = group_rate_points([{}, {}], g, [False] * len(g.buckets))[10]
    assert empty_bucket == {"t": g.buckets[10], "dl": 0, "up": 0}  # 全员无行 -> 0(非 null)


def test_group_totals_per_member_diff_then_sum():
    """逐成员先差分再求和: 单成员重置贡献 0 不拖垮全组; 基线缺失贡献 0; null 桶断链"""
    g = _grid_24h_30s()
    b0, b1, b2, b3 = g.buckets[10], g.buckets[11], g.buckets[12], g.buckets[13]
    # m1: b0 基线缺失(贡献 0) -> b1 +1000 -> b2 重置(cur<last, 贡献 0) -> b3 +100
    m1 = {
        b0: BucketObs(0, 0, 1000, 0),
        b1: BucketObs(0, 0, 2000, 0),
        b2: BucketObs(0, 0, 100, 0),
        b3: BucketObs(0, 0, 200, 0)
    }
    # m2: b1 才有行(基线缺失贡献 0) -> b2 +500 -> b3 +500
    m2 = {b1: BucketObs(0, 0, 500, 0), b2: BucketObs(0, 0, 1000, 0), b3: BucketObs(0, 0, 1500, 0)}
    mask = [False] * len(g.buckets)
    mask[14] = True  # b4 停机桶(null 桶断链)
    totals = group_totals_points([m1, m2], g, mask)
    assert totals[10] == {"t": b0, "dl": 0, "up": 0}  # 双成员基线缺失 -> 0(不出洞)
    assert totals[11] == {"t": b1, "dl": 1000, "up": 0}  # m1 +1000, m2 基线缺失 0
    assert totals[12] == {"t": b2, "dl": 500, "up": 0}  # m1 重置贡献 0(不是 -1900), m2 +500
    assert totals[13] == {"t": b3, "dl": 600, "up": 0}  # m1 +100, m2 +500
    assert totals[14] is None
    # null 桶断链: b4 之后 m1/m2 的快照链断, 下一桶基线缺失贡献 0
    # (R1 改判: 桶键取自 g.buckets —— F1 后 24h@30s 桶宽 180, 不再假设 30s 步进)
    b5 = g.buckets[g.buckets.index(b3) + 2]
    m1[b5] = BucketObs(0, 0, 9999, 0)
    totals2 = group_totals_points([m1, m2], g, mask)
    assert totals2[g.buckets.index(b5)] == {"t": b5, "dl": 0, "up": 0}


def test_group_50_members_correct_and_time_bound():
    """50 成员 x 满窗完整桶 + 1 进行中桶(26-11-14-1313 F3 floor+1, NOW 对齐时尾桶 =
    t1 起的进行中桶; 24h@30s 直构栅格 -> 480 完整桶): 抽样桶 Σ 成员均值/逐成员差分校验
    + 耗时上界(成员 obs 直构 —— 旧 v4_series_points -> v4_grid_obs 面随挂钟桶面退役,
    组聚合语义不变)

    上界依据: 组图弹层按采样间隔(30s)低频续拉(§07), 单次聚合须远小于一个间隔 ——
    上界 8s ≈ 间隔的 1/4, 是拦「数量级劣化」的粗闸(紧阈值回归基线见
    tests/test_modules_p5.py::test_rebuild_benchmark_5000_seeds + perf_baseline.json)。
    计时口径: CPU 时间(process_time)而非挂钟 —— 断言环境是 `-n 4` 并行 worker + 覆盖率
    插桩, 挂钟上界会被合法负载拉长(同一负载 dev 插桩中位 ~1.26s, windows-latest 实测
    4.01s 假红; 见 pitfalls/testing/timing-tolerance.md「不要为对称加挂钟上界」),
    CPU 时间只计本进程真烧的核时, 不受 worker 抢占 / 调度放大。余量按被守回归量级定:
    8s ≈ 6.3x dev 插桩中位, 2x 于 CI 实测最坏值, 仍 << 30s 间隔。
    """
    g = _grid_24h_30s()
    n = 50
    n_full = len(g.buckets) - 1  # 完整桶数(480, 尾桶 = 进行中桶)
    member_obs = []
    for m in range(n):
        # 每桶恰一观测: totals 每桶增长 (100 + m) x 桶宽 -> 桶速率 = (100 + m)
        # (瞬时速率字段垃圾值零参与 —— BucketObs 直构时速率列填真实差分均值)
        obs = {g.buckets[i]: BucketObs(100 + m, 0, (100 + m) * g.interval * i, 0) for i in range(n_full)}
        member_obs.append(obs)

    t_start = time.process_time()
    mask = group_null_mask(member_obs, g)
    points = group_rate_points(member_obs, g, mask)
    totals = group_totals_points(member_obs, g, mask)
    elapsed = time.process_time() - t_start

    assert len(points) == len(g.buckets)
    # 尾桶 = 进行中桶(26-11-14-1313 F3 floor+1, 起点 = t1): 消费窗 ts < t1 内无观测归不进
    # -> 组停机语义 null; 全部完整桶每桶每成员都有观测: 无 null
    assert all(p is not None for p in points[:-1])
    assert points[-1] is None
    idx = 100
    b = g.buckets[idx]
    assert points[idx] == {"t": b, "dl": 100 * n + n * (n - 1) // 2, "up": 0}  # up totals 恒 0 -> 桶速率 0
    assert totals[idx] == {"t": b, "dl": g.interval * (100 * n + n * (n - 1) // 2), "up": 0}  # 逐成员每桶 +rate x 桶宽
    assert totals[g.buckets.index(g.first)] == {"t": g.first, "dl": 0, "up": 0}  # 窗首基线缺失 -> 0
    assert elapsed < 8.0, f"50 成员聚合 CPU 耗时 {elapsed:.3f}s 超上界"


def test_group_zrun_idle_zero_line_and_outage_null():
    """组图回归(观测面, D6 沿用): 全员空闲(z 覆盖)出 0 线 / 全员无观测(停机)整桶断线 /
    成员只剩 z 块也有观测 —— 组三函数消费 BucketObs 观测表(直构; 26-11-18-0037 T1c-2 后
    raw 面组图走样本分组装配 + _group_merge_points, 本面 = agg 段窗组图的同判据底座)"""
    g = _grid_24h_30s()
    b0, b1, b2, b3 = g.buckets[100], g.buckets[101], g.buckets[102], g.buckets[103]
    # 成员观测: r @ b0(桶 b0 链首 0 线) + z 游程 2 槽(桶 b1/b2, 快照恒定 -> 0 线)
    member_obs = [{
        b0: BucketObs(0, 0, 100, 50),
        b1: BucketObs(0, 0, 100, 50),
        b2: BucketObs(0, 0, 100, 50),
    }]
    mask = group_null_mask(member_obs, g)
    assert mask[100] is False and mask[101] is False and mask[102] is False
    assert mask[103] is True  # z 游程之后无新块 = 停机: 全员无观测 -> null(成员观测面裁决)
    pts = group_rate_points(member_obs, g, mask)
    assert pts[100] == {"t": b0, "dl": 0, "up": 0}  # 链首 0 线(差分面; 旧瞬时直采 1/1 退役)
    assert pts[101] == {"t": b1, "dl": 0, "up": 0}  # z 槽 = 空闲 0 线(非 null)
    assert pts[102] == {"t": b2, "dl": 0, "up": 0}
    assert pts[103] is None  # 停机桶整桶 None
    totals = group_totals_points(member_obs, g, mask)
    assert totals[100] == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失贡献 0(不出洞)
    assert totals[101] == {"t": b1, "dl": 0, "up": 0}  # z 快照(100,50)同值: 空闲段 delta=0
    assert totals[102] == {"t": b2, "dl": 0, "up": 0}
    assert totals[103] is None


def test_group_rate_points_over_transformed_obs_unchanged():
    """组求和口径不变(S1 钉住): group_null_mask/group_rate_points 消费 BucketObs 观测表
    (26-11-18-0037 T1c-2 后 obs 由直构/agg 直映面供给)—— 豁免桶(0 线)有快照观测即非
    null, 组和按 0 计入。成员速率逐向未知(BucketObs None)同款按 0 计入和, 但全成员该向
    皆未知时出 None(issue 26-10-16-0954 修复语义; 承接面 = 本用例 None 速率成员分支 ——
    旧承接名 test_v4_grid_obs_break_bucket_rate_null_snapshot_kept 已随挂钟桶面退役)"""
    g = _grid_24h_30s()
    b0, b1 = g.buckets[100], g.buckets[101]
    m1 = {b0: BucketObs(100, 50, 1000, 500), b1: BucketObs(0, 0, 1000, 500)}  # b1 = 豁免桶 0 线
    m2 = {b0: BucketObs(30, 30, 300, 300), b1: BucketObs(20, 10, 1600, 800)}
    mask = group_null_mask([m1, m2], g)
    assert mask[100] is False and mask[101] is False  # 豁免桶有快照观测即非 null
    pts = group_rate_points([m1, m2], g, mask)
    assert pts[100] == {"t": b0, "dl": 130, "up": 80}
    assert pts[101] == {"t": b1, "dl": 20, "up": 10}  # m1 豁免桶按 0 计(无行同款)
    # None 速率成员分支(全成员该向未知 -> 该向 None 出口, 断链未知不冒充 0 值点):
    unknown = [{b0: BucketObs(None, None, 1000, 500)}, {b0: BucketObs(None, None, 1600, 800)}]
    assert group_rate_points(unknown, g, [False] * len(g.buckets))[100] == {"t": b0, "dl": None, "up": None}
    # 混合: 任一成员该向已知 -> 已知向求和、未知向按 0 计(逐向独立)
    mixed = [{b0: BucketObs(None, 5, 1000, 500)}, {b0: BucketObs(30, None, 1600, 800)}]
    assert group_rate_points(mixed, g, [False] * len(g.buckets))[100] == {"t": b0, "dl": 30, "up": 5}


def test_group_totals_up_direction_reset_independent():
    """组累计差分逐向独立: 某成员上行快照回落只让上行贡献 0, 下行照常累加(不整桶丢弃)"""
    g = _grid_24h_30s()
    b0, b1 = g.buckets[10], g.buckets[11]
    member = {b0: BucketObs(0, 0, 1000, 1000), b1: BucketObs(0, 0, 1500, 400)}
    totals = group_totals_points([member], g, [False] * len(g.buckets))
    assert totals[11] == {"t": b1, "dl": 500, "up": 0}


def test_group_totals_up_sums_across_members():
    """(gtp_28)组累计上行 = 逐成员先差分再**求和** —— 多成员非零 up 增量累加(赋值/反号
    变异在第二成员上显形; 此前池内 up 增量恒 0 撞不出)"""
    g = _grid_24h_30s()
    b0, b1 = g.buckets[10], g.buckets[11]
    m1 = {b0: BucketObs(0, 0, 1000, 500), b1: BucketObs(0, 0, 1100, 700)}  # dl +100 / up +200
    m2 = {b0: BucketObs(0, 0, 2000, 1000), b1: BucketObs(0, 0, 2100, 1400)}  # dl +100 / up +400
    totals = group_totals_points([m1, m2], g, [False] * len(g.buckets))
    assert totals[11] == {"t": b1, "dl": 200, "up": 600}


def test_group_totals_member_gap_does_not_truncate():
    """(gtp_17)成员本桶无行是 continue(自身链断)不是截断 —— **前位**成员缺行时后位成员的
    贡献必须照常计入(此前池内用例缺行成员恰排末位, 撞不出)"""
    g = _grid_24h_30s()
    b0, b1 = g.buckets[10], g.buckets[11]
    m1 = {b0: BucketObs(0, 0, 1000, 500)}  # b1 无行(前位成员)
    m2 = {b0: BucketObs(0, 0, 2000, 1000), b1: BucketObs(0, 0, 2100, 1400)}  # b1 +100/+400
    mask = group_null_mask([m1, m2], g)
    assert mask[11] is False  # m2 在 b1 有观测
    totals = group_totals_points([m1, m2], g, mask)
    assert totals[11] == {"t": b1, "dl": 100, "up": 400}
