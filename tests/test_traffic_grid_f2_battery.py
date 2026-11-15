"""test_traffic_grid_f2_battery 测试计划: 26-11-15-1104 F2 点位归属归桶的专项电池
(R2 双口径差分对照 + A8 存量天文件零迁移回归)

## 测试计划(每个测试函数一条)
- test_dual_caliber_steady_flow_identical: (R2)同一仿真流双口径对照 —— 稳态流(k=1 桶宽 =
  采样间隔)旧覆盖加权 vs 新点位归属逐桶恒等(含窗首桶: 种子样本作差分基线, 两口径同值)
- test_dual_caliber_rate_step_boundary_share: (R2)速率台阶流 —— 差异仅在台阶相邻桶(边界
  样本的份额归属差: 旧口径台阶对落台阶前桶, 新口径端点归属落台阶后桶), 幅度 = |R2-R1|
  <= 1 样本份额; 其余桶逐桶恒等
- test_dual_caliber_drift_and_dt_jump_share: (R2)漂移 + dt 修正跳变流(DRIFT_TOL_MS 量级)
  —— 逐桶 |new - old| <= 1 样本份额(桶内最大单对差分速率; 旧口径 ceil 桶宽膨胀被
  ±1 份额界吸收), 且新口径字节守恒(Σ rate x 桶宽 ≈ 真实增量, round 容差)
- test_dual_caliber_wide_bucket_steady_identical: (R2)k=2 桶宽(采样整倍加宽)稳态流逐桶恒等
  —— 稳态下旧覆盖加权与新点位归属同值(非边界桶恒等的稳态面; 变流场景由上一条钉)
- test_sealed_bucket_immunity_to_late_step: (评审轮1 #2 回归守阵)封口桶不可变 —— 桶值定影当且仅当不在开放等值游程覆盖内: 台阶到达不回写定影桶/摊配回写只及游程桶/闭合后追加样本不再变化(三态对账)
- test_a8_legacy_day_file_zero_migration: (A8)存量 v4 天文件回归 —— format_v4_day_text ->
  parse_v4_day_text 真实格式天文件(混排 1.5s interval 分块 / 显式漂移 dt / z 游程 / n 游程 /
  停机重启跨块)在新归桶语义下直接可读、逐桶值正确, 存储格式一行不动(零迁移)

双口径参照实现口径: 旧管线(F2 退役前)的电池局部逐字平移 —— cell 覆盖桶(ceil(ts)-w,
w = max(1, ceil(有效dt))) -> 相邻 cell 快照差分 delta/w 速率重写(基线缺失/重置 -> None)
-> 覆盖秒加权栅格展开(快照取覆盖末端最晚者)。仅覆盖纯 r 槽流(无 n 游程/真空/长 z 游程
—— 接缝摊配不在触发面, 其语义由 test_traffic_grid_seam 承袭电池钉住)。

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 流经 V4Block 直构或
format/parse roundtrip(A8 打通解析接缝)。
"""

import math

from auto_qb.core.traffic_grid import (
    BucketObs,
    V4PointEntry,
    WindowGrid,
    _floor_buckets,
    v4_grid_obs,
    v4_series_points,
)
from auto_qb.core.traffic_store import (
    V4Block,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
)

# ---------- 旧口径参照实现(F2 退役前管线, 电池局部平移) ----------


def _old_caliber_obs(slots, grid):
    """旧覆盖加权口径(纯 r 槽流): cell 覆盖桶 -> delta/w 重写 -> 覆盖秒加权栅格展开"""
    cells = {}
    for s in slots:
        if s.obs is None:
            continue
        w = max(1, math.ceil(s.dt_s))
        key = math.ceil(s.ts) - w
        o = s.obs
        e = cells.get(key)
        if e is None:
            cells[key] = [o[0], o[1], 1, s.ts, o[2], o[3], w]
        else:
            e[0] += o[0]
            e[1] += o[1]
            e[2] += 1
            if s.ts >= e[3]:
                e[3] = s.ts
                e[4] = o[2]
                e[5] = o[3]
            e[6] = max(e[6], w)
    keys = sorted(cells)
    # 速率重写(26-10-07-2127 方案 B): 相邻 cell 快照差分 / w; 基线缺失/重置 -> None
    rewritten = {}
    prev = None
    for k in keys:
        e = cells[k]
        if prev is None:
            dl = up = None  # 窗首(链首)基线缺失
        else:
            dl = e[4] - prev[0] if e[4] >= prev[0] else None  # cur < last 重置 -> None
            up = e[5] - prev[1] if e[5] >= prev[1] else None
        # 速率 = delta/w(w = cell 覆盖宽)—— 26-10-07-2127 方案 B 的除法面
        rewritten[k] = (None if dl is None else dl / e[6], None if up is None else up / e[6])
        prev = (e[4], e[5])
    # 覆盖秒加权栅格展开(v4_grid_obs 旧摊配面)
    obs: dict = {}
    prev_cov_end = None
    for k in keys:
        e = cells[k]
        t, w = k, e[6]
        cov_end = k + w
        rate_dl, rate_up = rewritten[k]
        broke = prev_cov_end is not None and t > prev_cov_end + 1e-6
        if prev_cov_end is None or cov_end > prev_cov_end:
            prev_cov_end = float(cov_end)
        if cov_end <= grid.first or t > grid.last:
            continue
        i = int(math.floor((t - grid.first) / grid.interval))
        while grid.first + i * grid.interval > t:
            i -= 1
        while grid.first + (i + 1) * grid.interval <= t:
            i += 1
        while True:
            b = grid.first + i * grid.interval
            if b >= cov_end or b > grid.last:
                break
            ov = min(cov_end, grid.first + (i + 1) * grid.interval) - max(t, b)
            if ov > 0 and b >= grid.first:
                a = obs.setdefault(b, [0, 0, 0, 0, cov_end, e[4], e[5], False])
                a[7] = a[7] or broke
                if rate_dl is not None:
                    a[0] += ov
                    a[1] += rate_dl * ov
                if rate_up is not None:
                    a[2] += ov
                    a[3] += rate_up * ov
                if cov_end >= a[4]:
                    a[4] = cov_end
                    a[5] = e[4]
                    a[6] = e[5]
            i += 1
    return {
        b:
            BucketObs(
                int(round(a[1] / a[0])) if a[0] else (None if a[7] else 0),
                int(round(a[3] / a[2])) if a[2] else (None if a[7] else 0),
                a[5],
                a[6],
            )
        for b, a in obs.items()
    }


def _new_caliber_obs(blocks, grid):
    """新口径(F2 点位归属): 生产同一条 v4_series_points -> v4_grid_obs 管线"""
    return v4_grid_obs(v4_series_points(blocks, grid), grid)


# ---------- R2 双口径差分对照 ----------


def test_dual_caliber_steady_flow_identical():
    """(R2)稳态流(k=1, B = si = 2)双口径逐桶恒等 —— 含窗首桶: 窗前种子样本作差分基线,
    两口径同值(非边界桶恒等的稳态面; 100 B/s 恒速, 瞬时字段垃圾值零参与)"""
    t0 = 1_000_000
    grid = WindowGrid("1m", t0, t0 + 120, 2, "raw", _floor_buckets(t0, t0 + 120, 2))
    base = (1000, 500)
    recs = [V4Sample(9999, 8888, base[0] + 200 * k, base[1] + 100 * k) for k in range(0, 70)]
    blk = V4Block(t0 - 2, 2, base[0], base[1], tuple(recs))  # 首槽 @t0-2(种子), 此后逐 2s
    slots = v4_block_slots(blk)
    old_obs = _old_caliber_obs(slots, grid)
    new_obs = _new_caliber_obs((blk, ), grid)
    covered = [b for b in grid.buckets if b in old_obs and b in new_obs]
    assert len(covered) >= 55  # 满窗覆盖(种子样本补齐窗首桶基线)
    for b in covered:
        assert (old_obs[b].dl_rate, old_obs[b].up_rate) == (100, 50), (b, "旧口径")
        assert (new_obs[b].dl_rate, new_obs[b].up_rate) == (100, 50), (b, "新口径")


def test_dual_caliber_rate_step_boundary_share():
    """(R2)速率台阶流(k=1): 差异仅在台阶相邻桶 —— 旧口径把台阶对(其覆盖恰为台阶前桶)
    记台阶前桶, 新口径端点归属记台阶后桶, 幅度 = |R2 - R1| <= 1 样本份额; 其余桶逐桶恒等"""
    t0 = 1_000_000
    grid = WindowGrid("1m", t0, t0 + 120, 2, "raw", _floor_buckets(t0, t0 + 120, 2))
    step_t = t0 + 60  # 台阶恰落桶边界
    recs = []
    total = 1000
    ts = float(t0 - 2)
    recs.append(V4Sample(9999, 8888, total, 500))  # 种子
    for k in range(1, 66):
        ts += 2
        rate = 100 if ts <= step_t else 400
        total += rate * 2
        recs.append(V4Sample(9999, 8888, total, total // 2))
    blk = V4Block(t0 - 2, 2, 1000, 500, tuple(recs))
    slots = v4_block_slots(blk)
    old_obs = _old_caliber_obs(slots, grid)
    new_obs = _new_caliber_obs((blk, ), grid)
    diff_buckets = []
    for b in grid.buckets:
        if b >= grid.t1 - 2 * 2:
            continue  # 数据末边界桶不属对照面(两口径对数据末梢的截断位置差一格)
        o, n = old_obs.get(b), new_obs.get(b)
        ov = (o.dl_rate, o.up_rate) if o else None
        nv = (n.dl_rate, n.up_rate) if n else None
        if ov != nv:
            diff_buckets.append(b)
            share = 400  # 1 样本份额 = 单对差分速率上限(400 B/s 为流内最大)
            if ov is not None and nv is not None:
                for x, y in zip(ov, nv):
                    if x is not None and y is not None:
                        assert abs(x - y) <= share, (b, x, y)
    # 台阶差只在台阶桶一格(旧口径记台阶前桶, 新口径端点归属记台阶后桶): 其余桶逐桶恒等
    assert diff_buckets == [step_t], diff_buckets


def test_dual_caliber_drift_and_dt_jump_share():
    """(R2)漂移 + dt 修正跳变流(真构造): dt 在 1.75~2.25s(DRIFT_TOL_MS=250ms 量级)显式
    漂移并含一次 4s 跳变(恰等桶宽跳过一桶的写侧形态, 记录带显式 dt_ms 4000, 置于窗内)——
    逐桶 |new - old| <= 局部最大单对差分速率(逐桶界, 旧 ceil 桶宽膨胀被 ±1 份额界吸收);
    跳变跨过的空桶 = 有界持有回填(26-11-15-1104 T3/F2-R8 实装: gap 4s <= max(B, si) x 2,
    is_hold 点回填前桶速率/totals 同值/w=0 —— 原 T2 钉「跳变跨过的空桶 = null」随新语义
    重钉为 held); 新口径字节守恒"""
    t0 = 1_000_000
    grid = WindowGrid("1m", t0, t0 + 120, 2, "raw", _floor_buckets(t0, t0 + 120, 2))
    # 漂移 + 一次 dt 修正跳变(跳变置于窗内中部: 前段 56 拍漂移 -> 跳变 -> 后段漂移)
    dts = [1750, 2250, 2000, 1800, 2200, 1950, 2050] * 8 + [4000] + [1750, 2250, 2000, 1800, 2200, 1950, 2050] * 1
    recs = [V4Sample(9999, 8888, 1000, 500)]
    total_dl, total_up = 1000, 500
    ts = float(t0 - 2)
    rate = 150
    for k, dt in enumerate(dts):
        if k == 30:
            rate = 500  # 中途变速
        ts += dt / 1000.0
        delta = int(rate * dt / 1000.0)
        total_dl += delta
        total_up += delta // 2
        recs.append(V4Sample(9999, 8888, total_dl, total_up, dt_ms=dt))  # 显式漂移/跳变 dt
    blk = V4Block(t0 - 2, 2, 1000, 500, tuple(recs))
    slots = v4_block_slots(blk)
    # 跳变(显式 dt 4s)恰跨一个 2s 桶: 有界持有回填(F2/R8)—— 空桶 is_hold 点持有前桶
    # 速率与 totals(原 T2 钉 null, 随新语义重钉; 判据界 gap <= max(B, si) x 2 = 4s)
    jump_idx = dts.index(
        4000
    )  # 跳变对 = (slots[jump_idx], slots[jump_idx + 1])(slots[0] = 种子; dt 4000 的样本在 slots[jump_idx + 1])
    jump_lo = slots[jump_idx].ts
    jump_mid_bucket = grid.first + (int((jump_lo + 2.0 - grid.first) // 2)) * 2  # 跳变跨过的桶
    pts_probe = v4_series_points((blk, ), grid)
    prev_bucket = grid.first + (int((jump_lo - grid.first) // 2)) * 2
    bf = next(p for p in pts_probe if p.t == jump_mid_bucket)
    prev_pt = next(p for p in pts_probe if p.t == prev_bucket)
    assert bf.is_hold and bf.w == 0.0, (bf, "跳变跨过的空桶应按持有语义回填(F2/R8)")
    assert (bf.dl_rate, bf.up_rate) == (prev_pt.dl_rate, prev_pt.up_rate), (bf, prev_pt, "held = 前桶速率")
    assert (bf.dl_total, bf.up_total) == (prev_pt.dl_total, prev_pt.up_total), (bf, prev_pt, "totals = 前桶快照")
    new_obs_probe = _new_caliber_obs((blk, ), grid)
    assert jump_mid_bucket in new_obs_probe, (jump_mid_bucket, "有界回填后跳变桶非 null(无伪断线)")
    # 逐对差分速率表(份额界用): 1 样本份额 = 单对差分速率
    pair_rates = []  # (cur.ts, delta/dur)
    prev_ts = None
    prev_total = 1000
    for s in slots:
        if prev_ts is not None:
            pair_rates.append((s.ts, (s.obs[2] - prev_total) / (s.ts - prev_ts)))
            prev_total = s.obs[2]
        prev_ts = s.ts
    old_obs = _old_caliber_obs(slots, grid)
    new_obs = _new_caliber_obs((blk, ), grid)
    checked = 0
    for b in grid.buckets:
        o, n = old_obs.get(b), new_obs.get(b)
        if o is None and n is None:
            continue
        # 逐桶界: 该桶 ±2 桶宽内落格的对差分速率最大值(局部 1 样本份额, 非全流最大
        # —— 变速后 500 B/s 段的份额不放松前段 150 B/s 桶的界); 单侧存在(出现/缺失
        # 本身是边界效应)同样受界约束
        local = [r for tt, r in pair_rates if b - 2 * grid.interval <= tt <= b + 2 * grid.interval]
        bound = max(local) + 1
        checked += 1
        for side in ((o.dl_rate, o.up_rate) if o else None, (n.dl_rate, n.up_rate) if n else None):
            if side is None:
                continue
            for x in side:
                if x is not None:
                    assert x <= bound, (b, x, bound)
        if o is not None and n is not None:
            for x, y in ((o.dl_rate, n.dl_rate), (o.up_rate, n.up_rate)):
                if x is not None and y is not None:
                    assert abs(x - y) <= bound, (b, x, y, bound)
    assert checked >= 55
    # 新口径字节守恒(逐桶恒等式 rate x 覆盖 = delta): 每个非空桶点的 rate x w ≈ 该桶
    # 被归属字节(端点落在该桶的对差分之和); 容差 = 非空桶数 x 0.5 x 最大覆盖
    # (round 逐桶 <= 0.5 B/s x 覆盖)—— < 最小单对差分(>= 150 x 1.75 = 262 字节),
    # 能卡住 ~1 对差分跨桶越界; 漂移跳桶(无样本桶 = null)的字节不入对账面(其速率面
    # 缺失由 null 诚实承载, T3 回填面)
    attributed = {}
    pts_prev_ts, pts_prev_total = None, None
    for s in slots:
        if pts_prev_ts is not None and t0 <= s.ts < grid.t1:
            key = grid.first + (int((s.ts - grid.first) // grid.interval)) * grid.interval
            attributed[key] = attributed.get(key, 0) + (s.obs[2] - pts_prev_total)
        pts_prev_ts, pts_prev_total = s.ts, s.obs[2]
    pts = v4_series_points((blk, ), grid)
    in_grid = [p for p in pts if grid.first <= p.t <= grid.last and p.dl_rate is not None]
    approx = sum(p.dl_rate * p.w for p in in_grid)
    attributed_sum = sum(v for k, v in attributed.items() if k in {p.t for p in in_grid})
    n_nonnull = len(in_grid)
    assert abs(approx - attributed_sum) <= n_nonnull * 0.5 * 2.25
    assert n_nonnull * 0.5 * 2.25 < min(r for _, r in pair_rates if r > 0) * 1.75  # 界 < 1 对差分


def test_dual_caliber_wide_bucket_steady_identical():
    """(R2)k=2 桶宽(B = 2 x si, 采样整倍加宽)稳态流逐桶恒等 —— 稳态下旧覆盖加权的
    重叠摊配与新点位归属同值(变流场景的差异界由 rate_step/drift 两条钉)"""
    t0 = 1_000_000
    grid = WindowGrid("5m", t0, t0 + 240, 4, "raw", _floor_buckets(t0, t0 + 240, 4))
    recs = [V4Sample(9999, 8888, 1000 + 200 * k, 500 + 100 * k) for k in range(0, 126)]
    blk = V4Block(t0 - 2, 2, 1000, 500, tuple(recs))  # 2s 采样, 4s 桶
    from auto_qb.core.traffic_store import v4_block_slots

    slots = v4_block_slots(blk)
    old_obs = _old_caliber_obs(slots, grid)
    new_obs = _new_caliber_obs((blk, ), grid)
    covered = [b for b in grid.buckets if b in old_obs and b in new_obs]
    assert len(covered) >= 55
    for b in covered:
        assert (old_obs[b].dl_rate, old_obs[b].up_rate) == (100, 50), (b, "旧口径")
        assert (new_obs[b].dl_rate, new_obs[b].up_rate) == (100, 50), (b, "新口径")


# ---------- A8 存量天文件零迁移回归 ----------


def test_a8_legacy_day_file_zero_migration():
    """(A8)存量 v4 天文件回归: 真实格式天文件(format_v4_day_text -> parse_v4_day_text,
    混排 1.5s interval 分块 / 显式漂移 dt / z 游程 / n 游程 / 停机重启跨块)在新归桶语义下
    直接可读、逐桶值正确 —— 存储格式一行不动(零迁移), 只动读侧"""
    day_text = format_v4_day_text(
        "global",
        (
            V4Block(
                2000,
                1.5,
                0,
                0,
                (
                    V4Sample(100, 50, 0, 0),  # @2000 链首
                    V4Sample(100, 50, 150, 75),  # @2001.5(标称 1.5s)
                    V4ZeroRun(4, 150, 75, dt_ms=6000),  # 均摊槽 @2003..2007.5(快照冻结)
                    V4Sample(250, 125, 400, 200, dt_ms=1500),  # @2009(游程终点 + 1.5)
                ),
            ),
            V4Block(  # 停机重启: 新块立基线
                2100,
                1.5,
                500,
                250,
                (
                    V4Sample(0, 0, 500, 250),  # @2100(块基线立点)
                    V4NullRun(2, dt_ms=9000),  # n 槽 @2109/2113.5(断连)
                    V4Sample(10, 5, 600, 300, dt_ms=3000),  # @2116.5
                ),
            ),
        ),
    )
    blocks = parse_v4_day_text(day_text).blocks  # 真实解析路径(零迁移: 格式未变)
    grid = WindowGrid("1m", 1990, 2200, 1.5, "raw", _floor_buckets(1990, 2200, 1.5))
    points = v4_series_points(blocks, grid)
    assert [(p.t, p.dl_rate, p.up_rate, p.dl_total, p.up_total, p.w) for p in points] == [
        (1999.5, 0, 0, 0, 0, 0.0),  # 链首 0 线(@2000 落格 1999.5)
        (2001.0, 100, 50, 150, 75, 1.5),  # delta(150,75)/1.5s
        (2002.5, 0, 0, 150, 75, 1.5),  # z 快照冻结 -> 0 线链不断
        (2004.0, 0, 0, 150, 75, 1.5),
        (2005.5, 0, 0, 150, 75, 1.5),
        (2007.0, 0, 0, 150, 75, 1.5),  # 末枚 z 槽(@2007.5 落格 2007.0)
        (2008.5, 167, 83, 400, 200, 1.5),  # 游程后恢复: delta(250,125)/1.5s(span == cov 不摊)
        (2009, None, None, None, None, 0.0),  # 块间真空标记(t = 前块游标终值 2009)
        (2100.0, None, None, 500, 250, 0.0),  # 未观测 89.5s > 60s 停机洞 -> 断链 None(快照照记)
        (2104, None, None, None, None, 0.0),  # n 游程折叠断连标记(首槽 2104.5 取整)
        (2112.0, 8, 4, 600, 300, 3.0),  # 标记后短缝(未观测 9s)摊配回收: step x 覆盖(3s) // span(12s) = 25 -> rate 8/4
    ]
    obs = v4_grid_obs(points, grid)
    assert obs[2001.0] == BucketObs(100, 50, 150, 75)
    assert 2002.5 in obs and obs[2002.5] == BucketObs(0, 0, 150, 75)  # 空闲段 0 线非 null
    assert obs[2100.0] == BucketObs(None, None, 500, 250)  # 停机洞断链未知 != 0
    assert set(obs) <= set(grid.buckets)  # 观测桶集 = 与栅格桶集的交集(窗外过滤)


def test_sealed_bucket_immunity_to_late_step():
    """(评审轮1 #2 回归守阵)封口桶不可变 —— 桶值定影当且仅当该桶不在**开放等值游程**的
    覆盖内(不变量表述见 traffic_grid 区头「封口桶不可变」):
    - 台阶未到达(游程开放): 游程覆盖桶值可被后续摊配回写改写 —— 非定影集;
    - 台阶到达(游程闭合, 摊配完成): 定影桶(游程覆盖之前的全部桶)与台阶前计算逐桶全等
      —— 定影桶值只依赖已落定样本;
    - 游程闭合后继续追加样本(第三块): 定影桶(含游程桶)不再变化 —— 后续样本不得改写。
    T4 增量解析的桶值缓存封口判定必须纳入「开放等值游程覆盖的桶不定影」。"""
    t0 = 1_000_000
    grid = WindowGrid("1m", t0, t0 + 120, 2, "raw", _floor_buckets(t0, t0 + 120, 2))
    pre = V4Block(999940, 2, 800, 400, (V4Sample(5, 5, 800, 400), V4Sample(5, 5, 900, 450)))  # 游程前活动(窗前链上下文)
    run = V4Block(1000000, 2, 1000, 500, (V4Sample(1, 1, 1000, 500), V4ZeroRun(10, 1000, 500, dt_ms=20000)))
    step = V4Block(1000040, 2, 1262, 631, (V4Sample(9, 9, 1262, 631), ))  # 台阶(缝 18s, 块首 dt 标称 2s)
    later = V4Block(1000090, 2, 1500, 750, (V4Sample(5, 5, 1500, 750), ))  # 游程闭合后的追加样本(缝 48s)

    def _points_obs(blocks):
        # 点流 -> 桶点表(不经 v4_grid_obs 栅格过滤: 窗前链上下文桶也在对账面)
        return {p.t: p for p in v4_series_points(blocks, grid)}

    pts_open = _points_obs((pre, run))  # 台阶未到达: 游程开放
    pts_step = _points_obs((pre, run, step))  # 台阶到达: 游程闭合, 摊配完成
    pts_later = _points_obs((pre, run, step, later))  # 闭合后追加样本

    # 定影桶(游程覆盖之前: t < 1000002, 含窗外链上下文桶)三态逐桶全等 —— 台阶到达不
    # 回写; 追加样本不回写
    for k in (999940, 999942, 1000000):
        assert pts_open[k] == pts_step[k] == pts_later[k], (k, pts_open[k], pts_step[k], pts_later[k])
    # 非定影集 = 开放游程覆盖的桶(1000002..1000020): 台阶到达后经摊配回写改写(与开放态不同)
    run_buckets = [k for k in pts_open if 1000002 <= k <= 1000020]
    assert run_buckets and any(pts_open[k] != pts_step[k] for k in run_buckets)
    # 闭合后追加样本: 游程桶与接收桶定影(pts_step 已有键在 pts_later 逐桶全等, 含摊配
    # 结果; pts_later 新增的追加样本自身桶不算改写)
    for k in pts_step:
        assert pts_step[k] == pts_later.get(k), (k, pts_step[k], pts_later.get(k))
    # 确定性: 同一输入重算逐桶恒等(纯函数面)
    assert _points_obs((pre, run, step)) == pts_step
