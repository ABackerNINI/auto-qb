"""test_traffic_grid_f2_battery 测试计划(26-11-18-0037 T1c-2 退役转世): 26-11-15-1104 F2
点位归属归桶面(及 R2 双口径对照/A8 零迁移/T2 封口定影)已随挂钟桶面退役 —— 本电池改判为
样本分组装配新契约的对应守阵(判读单点承袭: 端点归属/差分/摊配/totals 三层口径, 面形态
栅格桶点 -> 样本分组点列):

## 测试计划(每个测试函数一条)
- test_steady_flow_per_sample_and_group_mean: (承袭 R2 稳态面)稳态流逐样本值恒 100/50
  (k=1)且 k>1 组均值同值(含窗首种子: 种子样本作差分基线, 窗首组含种子差分; 分组只是
  重新划界, 值不变)
- test_rate_step_boundary_attribution: (承袭 R2 台阶面)速率台阶流 —— 端点归属: 台阶后的
  样本对(其差分)记台阶后样本, 幅度 = 单对差分速率(400 B/s); 台阶前样本逐点 100 不受扰
- test_drift_and_dt_jump_honest_no_backfill: (承袭 R2 漂移/dt 跳变面 + 旧 T3 回填改判)
  漂移流 + 一次 4s dt 跳变(恰跨栅格桶的写侧形态)—— 跳变无空值点(dt 链吸收, 未采样非
  断连), 字节含在后继样本快照差分里(totals 面计数器真值), 速率 = delta/实测对跨; 逐样本
  速率受局部单对差分界约束(旧 ceil 桶宽膨胀随桶面退役); Sigma(totals) = 遥差字节守恒
- test_a8_legacy_day_file_zero_migration: (A8)存量 v4 天文件回归 —— format_v4_day_text ->
  parse_v4_day_text 真实格式天文件(混排 1.5s interval 分块/显式漂移 dt/z 游程/n 游程/
  停机重启跨块)在样本分组契约下直接可读、逐样本值正确, 存储格式一行不动(零迁移)

(test_dual_caliber_* 的旧口径参照实现随 cell 覆盖桶几何退役删除; 封口定影面随 T2/T3 退役
—— 前缀和不可回写性由 test_traffic_group_cache 主阵逐位对账承接。)

线程/时钟纪律: 纯函数层无时钟无文件 —— 窗口由用例给定固定 epoch, 流经 V4Block 直构或
format/parse roundtrip(A8 打通解析接缝)。
"""

from auto_qb.core.traffic_group_assembly import assemble_group_points

from auto_qb.core.traffic_store import (
    V4Block,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
)


def _real(res):
    """真值点 (t, dl, up) 序列(空值点 = totals None 剔除)"""
    return [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None]


def _totals_sum(res, key):
    """Sigma(totals[key])(空值点跳过; 逐向 None 项不计)"""
    return sum(t[key] for t in res.totals if t is not None and t[key] is not None)


def test_steady_flow_per_sample_and_group_mean():
    """(承袭 R2 稳态面)稳态流(k=1, si=2): 逐样本值恒 100/50(差分 200/100 每 2s, 瞬时
    字段垃圾值零参与); k>1 组均值同值(窗首种子样本作差分基线, 窗首组含种子差分 —— 分组
    只是重新划界, 值与粒度无关)"""
    t0 = 1_000_000
    recs = [V4Sample(9999, 8888, 1000 + 200 * k, 500 + 100 * k) for k in range(0, 70)]
    blk = V4Block(t0 - 2, 2, 1000, 500, tuple(recs))  # 首槽 @t0-2(种子), 此后逐 2s
    res = assemble_group_points(v4_block_slots(blk), t0, t0 + 120, 2)
    assert res.stride == 1
    real = _real(res)
    assert len(real) == 60  # 窗内样本 @t0..t0+118(种子窗外, 只作基线)
    assert all(dl == 100 and up == 50 for _, dl, up in real)  # 稳态逐样本恒值
    assert _totals_sum(res, "dl") == 200 * 60 == (1000 + 200 * 60) - 1000  # 遥差(含种子基线)
    # k>1 组均值: 预期 1500 样本 -> k=3; 窗内 69 样本(k=1..69, 种子窗外)-> 23 组(末组 1 样本)
    res3 = assemble_group_points(v4_block_slots(blk), t0, t0 + 3000, 2)
    assert res3.stride == 3
    real3 = _real(res3)
    assert len(real3) == 23
    assert real3[0][0] == t0 + 4  # 首组组末样本 ts(组 = 样本 k=1..3)
    assert all(dl == 100 and up == 50 for _, dl, up in real3)
    # 字节守恒: Sigma(totals) = 末窗内样本快照 - 种子快照(两窗各自遥差; 同窗跨 k 恒等由
    # test_traffic_group_assembly::test_byte_conservation_totals_sum_invariant_across_k 钉)
    assert _totals_sum(res3, "dl") == (1000 + 200 * 69) - 1000
    assert _totals_sum(res, "dl") == (1000 + 200 * 60) - 1000


def test_rate_step_boundary_attribution():
    """(承袭 R2 台阶面)速率台阶流(k=1): 端点归属 —— 台阶差分对记台阶后样本(其 ts 的点
    落 400 B/s), 台阶前样本逐点 100 不受扰(幅度 = 1 样本份额 400, 旧口径台阶对落台阶前
    桶的差异随桶面退役 —— 端点归属承袭为样本锚)"""
    t0 = 1_000_000
    step_t = t0 + 60  # 台阶恰落样本序界
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
    res = assemble_group_points(v4_block_slots(blk), t0, t0 + 120, 2)
    real = _real(res)
    assert len(real) == 60
    assert all(dl == 100 for _, dl, _ in real[:31])  # 样本 @t0..t0+60: 台阶前速率 100
    assert all(dl == 400 for _, dl, _ in real[31:])  # 样本 @t0+62 起: 台阶后差分对整对归属
    assert real[31][0] == t0 + 62  # 端点归属: 台阶差分落在台阶后样本


def test_drift_and_dt_jump_honest_no_backfill():
    """(承袭 R2 漂移/dt 跳变面)漂移流(DRIFT_TOL_MS 量级显式 dt 1.75~2.25s)+ 一次 4s 跳变
    (恰跨栅格桶的写侧形态): 跳变无空值点(dt 链吸收 —— 未采样非断连), 跳变字节含在后继
    样本快照差分里(totals 面真值), 速率 = delta/实测对跨 4s(不摊不回填); 逐样本速率受
    局部单对差分界约束(旧 ceil 桶宽膨胀随桶面退役); Sigma(totals) = 遥差字节守恒"""
    t0 = 1_000_000
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
    res = assemble_group_points(v4_block_slots(blk), t0, t0 + 120, 2)
    real = _real(res)
    # 跳变对: dts.index(4000) 的后继样本 —— 差分 = 500 x 4s = 2000 字节, 覆盖 4s -> rate 500
    jump_idx = dts.index(4000)
    jump_ts = t0 - 2 + sum(dts[:jump_idx + 1]) / 1000.0
    jump_pt = next((tt, dl, up) for tt, dl, up in real if abs(tt - jump_ts) < 1e-9)
    assert (jump_pt[1], jump_pt[2]) == (500, 250)  # delta(2000,1000)/4s(局部单对差分速率)
    # 无空值点(dt 链吸收): 跳变不产缺口标记(旧 T3 有界回填面退役, 缺口语义收窄到 n/真空)
    assert not [p["t"] for p, t in zip(res.points, res.totals) if t is None]
    # 逐样本速率界: 局部 1 样本份额(该样本所属对的差分速率上界)—— 变速段份额不放松前段;
    # 覆盖 = min(对跨, 声称 dt) -> 含缝对只计声称覆盖(漂移流无缝, 界即逐对差分速率)
    pair_rates = {}  # ts -> (dl 速率, up 速率)
    prev_ts, prev_dl, prev_up = None, None, None
    for s in v4_block_slots(blk):
        if prev_ts is not None:
            pair_rates[s.ts] = (
                (s.obs[2] - prev_dl) / (s.ts - prev_ts),
                (s.obs[3] - prev_up) / (s.ts - prev_ts),
            )
        prev_ts, prev_dl, prev_up = s.ts, s.obs[2], s.obs[3]
    for tt, dl, up in real:
        local = [r for ts_r, r in pair_rates.items() if tt - 4.0 < ts_r <= tt + 0.001]
        bound = max(r for pair in local for r in pair if r > 0) + 1
        for x in (dl, up):
            if x is not None:
                assert x <= bound, (tt, x, bound)
    # 字节守恒: Sigma(totals) = 末窗内样本快照 - 窗内首个样本的差分基线(= 最后一个
    # ts < t0 的样本快照 —— 窗外前缀作基线, 窗首样本的差分按其对基线入账)
    snaps = [(s.ts, s.obs[2]) for s in v4_block_slots(blk)]
    in_win = [x for x in snaps if t0 <= x[0] < t0 + 120]
    baseline = max(x[1] for x in snaps if x[0] < t0)
    assert _totals_sum(res, "dl") == in_win[-1][1] - baseline


def test_a8_legacy_day_file_zero_migration():
    """(A8)存量 v4 天文件回归: 真实格式天文件(format_v4_day_text -> parse_v4_day_text,
    混排 1.5s interval 分块 / 显式漂移 dt / z 游程 / n 游程 / 停机重启跨块)在样本分组契约
    下直接可读、逐样本值正确 —— 存储格式一行不动(零迁移), 只动读侧"""
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
                    V4NullRun(2, dt_ms=9000),  # n 槽 @2104.5/2109(断连)
                    V4Sample(10, 5, 600, 300, dt_ms=3000),  # @2112
                ),
            ),
        ),
    )
    blocks = parse_v4_day_text(day_text).blocks  # 真实解析路径(零迁移: 格式未变)
    res = assemble_group_points(v4_block_slots(blocks[0]) + v4_block_slots(blocks[1]), 1990, 2200, 1.5)
    assert res.stride == 1
    assert _real(res) == [
        (2000.0, 0, 0),  # 链首 0 线
        (2001.5, 100, 50),  # delta(150,75)/1.5s
        (2003.0, 0, 0),  # z 快照冻结 -> 0 线链不断
        (2004.5, 0, 0),
        (2006.0, 0, 0),
        (2007.5, 0, 0),  # 末枚 z 槽
        (2009.0, 167, 83),  # 游程后恢复: delta(250,125)/1.5s(span == cov 不摊)
        (2100.0, None, None),  # 未观测 89.5s > 60s 停机洞 -> 断链 None(totals 真值)
        (2112.0, 8, 4),  # 标记后短缝(未观测 9s)摊配回收: step x 覆盖(3s) // span(12s) = 25 -> rate 8/4
    ]
    # 空值点两处: 块间真空(t = int(2009))+ n 游程折叠(floor 2104.5); 与同刻观测样本共存
    # (2009 空值在前、真值点在后 —— 旧 emit 同判)
    assert [p["t"] for p, t in zip(res.points, res.totals) if t is None] == [2009, 2104]
    same_t = [p for p, t in zip(res.points, res.totals) if p["t"] == 2009]
    assert same_t[0]["dl"] is None and same_t[1]["dl"] == 167  # 同刻空值在前
    assert res.totals[-1] == {"t": 2112.0, "dl": 100, "up": 50}  # 洞后摊配样本 totals 真值
