"""test_traffic_grid_s1b_battery 测试计划: 26-11-15-1104 S1b 收口电池(T3 = F3 holding 新定义
+ F2 后半有界空桶持有回填)—— A1/A5 验收仿真流

## 测试计划(每个测试函数一条)
- test_a1_steady_beat_diff_tail_within_two_buckets: (A1)稳态恒速仿真逐拍差分(3 seed:
  11/23/37)—— 相邻两拍 payload(rate + totals 两面)变化桶数 <= 2 且变化桶只在尾部 1-2 段
  (新样本合理收敛); 值不振荡(同一桶值不出现 A->B->A 翻转); 仿真流含写侧累积漂移
  (DRIFT_TOL_MS 量级)与 dt 修正跳变(恰等桶宽跳桶的写侧形态)
- test_a5_active_endpoint_on_line_and_no_false_break: (A5 活跃态)采样器活跃时曲线终点恒落
  判定线(每拍尾桶非 null); 覆盖段无伪断线(首个非 null 桶到尾桶之间无 None 洞); dt 修正
  跳变跨过的空桶 = 有界持有回填(is_hold 点, held = 前桶速率, totals = 前桶快照, w = 0)
  —— i=40 注入相位钉定的保证跳桶拍(_force_skip_beat), held 回填断言体实际执行
  (skip_asserted 计数), 非死代码
- test_a5_stall_over_bound_honest_null: (A5 停滞态, R8「间隙过界仍 null」)停止进样后间隙
  有界(<= max(B, si) x 2)的拍尾桶仍 held 落线; 间隙过界后尾桶 null 诚实断线且不再恢复;
  停滞期已定影桶逐拍不变(不回写); 判据界两侧(有界 held / 过界 null)都被真实观测到
- test_a5_disconnect_n_run_stays_null: (A5 断连态, R8「真断连仍 null」)两态: 有界断连缝
  (单拍 disconnect, 对末真实样本对跨 <= 判据界且跨过 1 枚空桶 —— 几何满足回填面, 仅
  断连守卫 marked/null_since_obs 拦住回填, 空桶保持 null = 守卫判别力钉)与长断连(观测缝
  > 60s 停机洞, 重连桶速率 None 不造值, 快照照记); 重连拍尾桶 = 诚实缺口(held 被标记
  清空 -> 速率面 (None, None)), 重连后首个真实差分拍恢复落线

仿真形态(生产同构): 采样间隔 si = 1.5s(生产现况), 1m 窗桶宽 B = 1.5(F1: k=1, 桶宽 = 采样
整倍); 写侧游标仿真 traffic_sample_mod 形态 —— 块首 B.start = int(首记录实测), 每拍标称推进
si, 累积漂移 |actual - (游标 + si)| > DRIFT_TOL_MS(250ms)时本拍写实测 dt_ms 并自然复位;
字节按真实耗时累积(恒速 1000/500 B/s, 计数器单调; qB 不可达拍计数器冻结)。活尾 = 整块
head_pending 形态(start_epoch = block_start —— 读侧链锚 == 写侧游标, 镜像不变量由
_beat_payload 的首槽锚断言逐拍核验); 判据界 gap_bound = max(B, si) x 2 与
v4_series_points gap_bound_s 同一单点值。

线程/时钟纪律: 纯函数层无时钟无文件 —— now 由仿真显式推进, 窗口/活尾逐拍直构。
"""

import math
import random

from auto_qb.core.traffic_grid import (
    WindowGrid,
    _floor_buckets,
    rate_points,
    series_totals_points,
    v4_grid_obs,
    v4_series_points,
)
from auto_qb.core.traffic_store import LiveTail, V4NullRun, V4Sample, v4_live_tail_slots
from auto_qb.core.traffic_store_common import DRIFT_TOL_MS

_SI = 1.5  # 采样间隔(生产现况)
_B = 1.5  # 1m 窗桶宽(F1: k=1, 桶宽 = 采样整倍)
_GAP_BOUND = max(_B, _SI) * 2.0  # 判据界单点(与 v4_live_tail_slots max_gap_s / gap_bound_s 同值)
_DRIFT_TOL = DRIFT_TOL_MS / 1000.0  # 写侧漂移容差(延伸判据的链端超前界, 单点引用)
_START = 1_800_000_000  # 时钟基点(纯测试时刻; 块首 = int(首记录实测), 非本值)


def _grid_1m(now):
    """1m 窗栅格(F1 桶宽 = si 整倍 k=1 -> B = si; floor 对齐 + floor+1 进行中桶)"""
    t0 = int(now) - 60
    t1 = int(now)
    return WindowGrid("1m", t0, t1, _B, "raw", _floor_buckets(t0, t1, _B))


class _SamplerSim:
    """写侧游标仿真(traffic_sample_mod 形态): 标称推进 + DRIFT_TOL_MS 累积漂移修正

    块首 B.start = int(首记录实测)(亚秒余量成为初始累积漂移, 由后续显式 dt 自然吸收);
    每拍实测时刻 actual += si + 抖动(或显式 gap); 漂移 = actual - (游标 + 标称推进),
    |漂移| > 0.25 时本拍写实测 dt_ms(游标推到实测点, 自然复位), 否则游标推进标称值。
    字节按真实耗时累积(恒速), 计数器单调不减(块内无重置; qB 不可达拍冻结)。"""
    def __init__(self, dl_rate=1000.0, up_rate=500.0, seed=11):
        self.now = float(_START)  # 实测时刻
        self.cursor = float(_START)  # 写侧游标(首拍置为块首 = int(首记录实测))
        self.block_start = None  # 块首(读侧链锚; tail() 传同一值 -> 镜像不变量)
        self.req_now = float(_START)  # 请求时刻 = 采样实测 + 请求延迟(生产: Web 请求晚于末次采样)
        self.dl = 10_000_000
        self.up = 5_000_000
        self.records: list = []
        self.rng = random.Random(seed)
        self.dl_rate = dl_rate
        self.up_rate = up_rate
        self.first = True

    def beat(self, gap=None, disconnect=False):
        """推进一拍并产出一条记录(gap = 显式实测间隔, 缺省 si + 抖动; disconnect = 本拍
        qB 不可达, 产 V4NullRun)"""
        step = gap if gap is not None else _SI + self.rng.uniform(-0.08, 0.08)
        elapsed = step
        self.now += step
        self.req_now = self.now + self.rng.uniform(0.02, 0.12)  # 请求延迟(生产: 请求晚于末次采样)
        if not disconnect:
            # qB 不可达时计数器冻结(n 记录无 totals 面 —— 生产写侧同形)
            self.dl += int(self.dl_rate * elapsed)
            self.up += int(self.up_rate * elapsed)
        if self.first:
            # 块首记录: dt 列无语义不写; B.start = int(首记录实测) —— tail() 传同一值,
            # 读侧链锚 == 写侧游标(镜像不变量)
            self.first = False
            self.block_start = int(self.now)
            self.cursor = float(self.block_start)
            rec = V4NullRun(1) if disconnect else V4Sample(0, 0, self.dl, self.up)
            self.records.append(rec)
            return rec
        nominal = _SI  # 单槽记录标称推进
        drift = self.now - (self.cursor + nominal)
        if abs(drift) > _DRIFT_TOL:
            dt_ms = max(1, int(round((self.now - self.cursor) * 1000)))
            rec = V4NullRun(1, dt_ms=dt_ms) if disconnect else V4Sample(0, 0, self.dl, self.up, dt_ms=dt_ms)
            self.cursor += dt_ms / 1000.0  # 游标推到实测点(自然复位)
        else:
            rec = V4NullRun(1) if disconnect else V4Sample(0, 0, self.dl, self.up)
            self.cursor += nominal
        self.records.append(rec)
        return rec

    def tail(self):
        """活尾快照(整块 head_pending 形态: 槽位复用块内推算, 与落盘重算恒一)"""
        return LiveTail(
            block_open=True,
            head_pending=True,
            start_epoch=self.block_start,
            interval_s=_SI,
            projected_ts=self.cursor,
            records=tuple(self.records),
            open_run=None,
        )


def _force_skip_beat(sim):
    """构造保证跳桶的一拍(评审轮1 #3): 落点钉到「游标所在桶 + 2」内 —— 跨过恰好 1 枚
    空桶, 且显式对跨 <= 2B = 判据界(有界回填必触发, 不会滑成停滞 null)。

    相位钉定: target = (b+2)B + min(0.05, mod/2)(mod = 游标桶内相位):
    - mod >= 0.1: dt = 2B + 0.05 - mod <= 2B - 0.05, 落点距桶界 0.05(ms 舍入界外);
    - mod < 0.1: dt = 2B - mod/2 <= 2B, 落点 = (b+2)B + mod/2(>= 桶界; mod 极小时
      dt_ms 舍入恒 = 3000 -> 落点 = (b+2)B + mod >= 桶界, floor 仍入 b+2)。"""
    b = math.floor(sim.cursor / _B)
    mod = sim.cursor - b * _B
    target = (b + 2) * _B + min(0.05, mod / 2)
    return sim.beat(gap=target - sim.now)


def _beat_payload(sim, now):
    """单拍 payload(生产同构: 活尾合流 -> 点位归属归桶 -> 响应两面); rate/totals 字典
    保留 null 桶(值 None —— 空桶断线语义, 与响应数组的 null 槽位同形)。
    镜像不变量逐拍核验: 读侧块首槽 == 写侧块首(链锚对齐, 评审轮1 #1 回归面)。"""
    grid = _grid_1m(now)
    tail_slots = v4_live_tail_slots(sim.tail(), now=now, max_gap_s=_GAP_BOUND)
    assert tail_slots[0].ts == float(sim.block_start), (
        tail_slots[0].ts,
        sim.block_start,
        "读侧链锚 != 写侧块首(镜像不变量破坏)",
    )
    points = v4_series_points((), grid, tail_slots=tail_slots, gap_bound_s=_GAP_BOUND)
    obs = v4_grid_obs(points, grid)
    rate = {b: ((d["dl"], d["up"]) if d is not None else None) for b, d in zip(grid.buckets, rate_points(obs, grid))}
    totals = {
        b: ((d["dl"], d["up"]) if d is not None else None)
        for b, d in zip(grid.buckets, series_totals_points(obs, grid))
    }
    return grid, rate, totals, points


def test_a1_steady_beat_diff_tail_within_two_buckets():
    """(A1)稳态恒速 + 漂移/dt 修正跳变流逐拍差分(3 seed): 变化桶数 <= 2, 变化桶只在
    尾 1-2 段, 值不振荡(A->B->A 翻转不存在)—— 封口桶不可变使振荡在语义上不可能,
    此断言为其回归面"""
    for seed in (11, 23, 37):
        sim = _SamplerSim(seed=seed)
        history: dict = {}  # 桶键 -> rate 值历史(振荡检测)
        jump_count = 0
        prev = None
        for i in range(80):
            rec = sim.beat()
            grid, rate, totals, points = _beat_payload(sim, sim.req_now)
            if prev is not None and i >= 30:  # 预热 30 拍后断言(窗口被链上下文填满)
                changed = [t for t in rate.keys() & prev[0].keys() if rate[t] != prev[0][t]]
                changed_t = [t for t in totals.keys() & prev[1].keys() if totals[t] != prev[1][t]]
                assert len(changed) <= 2, (seed, i, sorted(changed), "rate 面变化桶数超界")
                assert len(changed_t) <= 2, (seed, i, sorted(changed_t), "totals 面变化桶数超界")
                for t in changed:
                    # 变化桶只在尾部 1-2 段(尾桶与次尾桶; 桶宽 B 步进)
                    assert t >= grid.last - 2 * _B, (seed, i, t, grid.last, "变化桶越出尾部两段")
                for t in changed:
                    h = history.setdefault(t, [])
                    h.append(rate[t])
                    # 振荡 = 值回到两个拍之前的值且与上一拍不同(A->B->A)
                    assert not (len(h) >= 3 and h[-1] == h[-3] and h[-1] != h[-2]), (seed, t, h, "值振荡")
            prev = (rate, totals)
            # dt 修正跳变(显式 dt > 标称 + 100ms —— 正向漂移修正的写侧形态)计数
            if rec.dt_ms is not None and rec.dt_ms > _SI * 1000 + 100:
                jump_count += 1
        # 仿真流确含 dt 修正跳变(DRIFT_TOL_MS 量级漂移的自然结果)
        assert jump_count > 0, (seed, "仿真流应含 dt 修正跳变(漂移累积超容差)")


def test_a5_active_endpoint_on_line_and_no_false_break():
    """(A5 活跃态)终点恒落判定线 + 覆盖段无伪断线 + 跳变空桶有界回填(held 面):
    i=40 注入保证跳桶拍(_force_skip_beat), held 回填断言体实际执行(skip_asserted 计数
    —— 评审轮1 #3: 原唯一自然跳桶事件落 warmup 被跳过, 断言零执行)"""
    sim = _SamplerSim(seed=23)
    skip_detected = 0
    skip_asserted = 0  # held 回填断言体实际执行次数(非死代码证明)
    for i in range(80):
        rec = _force_skip_beat(sim) if i == 40 else sim.beat()
        # dt 修正跳变检测: 本拍显式 dt 使样本跨过 >= 1 个栅格桶 -> 记录空桶与源桶键
        skip_pair = None
        if rec.dt_ms is not None:
            first = _grid_1m(sim.req_now).first
            prev_ts = sim.cursor - rec.dt_ms / 1000.0
            i_prev = int((prev_ts - first) // _B)
            i_cur = int((sim.cursor - first) // _B)
            if i_cur > i_prev + 1:
                skip_pair = (i_prev + 1, i_prev)
                skip_detected += 1
        grid, rate, totals, points = _beat_payload(sim, sim.req_now)
        # 跳变跨过的空桶(窗内) = held 回填点: held = 前桶速率, totals = 前桶快照, w = 0
        # (置于预热 continue 之前 —— 保证跳桶拍在 i=40, 此块必实际执行)
        if skip_pair is not None:
            bf_key = grid.first + skip_pair[0] * _B
            src_key = grid.first + skip_pair[1] * _B
            if bf_key >= grid.t0:
                skip_asserted += 1
                bf = next(p for p in points if p.t == bf_key)
                assert bf.is_hold and bf.w == 0.0, (i, bf, "跳变空桶应为 held 回填点")
                src = next(p for p in points if p.t == src_key)
                assert (bf.dl_rate, bf.up_rate) == (src.dl_rate, src.up_rate), (i, bf, src, "held = 前桶速率")
                assert (bf.dl_total, bf.up_total) == (src.dl_total, src.up_total), (i, bf, src, "totals = 前桶快照")
                assert rate.get(bf_key) is not None, (i, bf_key, "回填桶不落线 = 伪断线")
        if i < 5:
            continue  # 预热: 块首几拍链尚短(终点/覆盖段断言需链上下文)
        # 终点恒落判定线: 尾桶非 null(尾桶 = 进行中桶, holding/held 或真实观测)
        assert rate.get(grid.last) is not None, (i, grid.last, "尾桶 null = 终点脱线")
        # 覆盖段无伪断线: 首个非 null 桶到尾桶之间无 None 洞
        covered = [t for t in sorted(rate) if t >= grid.t0 and rate[t] is not None]
        first = covered[0]
        hole = [t for t in rate if first <= t <= grid.last and rate[t] is None]
        assert not hole, (i, hole, "覆盖段出现伪断线")
    # 保证跳桶拍被检测且回填断言体实际执行(评审轮1 #3: 非死代码)
    assert skip_detected > 0 and skip_asserted >= 1, (skip_detected, skip_asserted, "跳桶事件/断言体未执行")


def test_a5_stall_over_bound_honest_null():
    """(A5 停滞态, R8 间隙过界仍 null): 有界间隙拍尾桶仍 held(相邻有界拍值恒定 —— 无
    闪烁); 过界后 null 诚实断线不恢复; 停滞期已定影桶逐拍不变; 判据界两侧都被真实观测到
    (saw_held/saw_null 旗)"""
    sim = _SamplerSim(seed=37)
    prev_rate = None
    real_pts = []
    for i in range(50):
        sim.beat()
        grid, rate, totals, points = _beat_payload(sim, sim.req_now)
        prev_rate = (grid, rate)
        # 非持有观测桶集合 = 停滞期不得改写的定影面(持有/回填面在过界后随判据消失,
        # 不属定影; 进样期末桶若为 hold 面, 停滞首拍可因窗口推进收敛出被窗尾过滤的
        # 末样本真实值 —— 开放面收敛, 非定影改写)
        real_pts = [p for p in points if not p.is_hold and p.dl_rate is not None]
    assert prev_rate[1].get(prev_rate[0].last) is not None, "进样期终点应落线"
    # 停滞: 停止进样, now 以半拍步进推进(写侧无新记录)—— 间隙逐拍增长; 期望值按活尾
    # 延伸判据(间隙 = now - 读侧链端 <= max(B, si) x 2 时 held, 过界 null)逐拍推导
    # (链端 = 写侧游标: 镜像不变量由 _beat_payload 逐拍核验, 手工推导与 src 同源;
    #  半拍步进使判据界两侧各有 >= 2 拍被真实观测, 不整拍跨过过界点 —— 评审轮1 #2)
    sealed = {p.t: (p.dl_rate, p.up_rate) for p in real_pts if p.t >= prev_rate[0].t0}
    stall_endpoint = []
    saw_held_after_stall = False
    saw_null_after_stall = False
    prev_bounded_endpoint = None
    for b in range(1, 13):
        now = sim.req_now + b * _SI / 2
        grid, rate, totals, _ = _beat_payload(sim, now)
        stall_endpoint.append(rate.get(grid.last))
        # 真实观测桶(定影面)逐拍不变(不回写不翻转; 持有/回填面随判据消失属诚实行为)
        for t, v in sealed.items():
            if t in rate:
                assert rate[t] == v, (b, t, "停滞期定影桶被改写")
        gap = now - sim.cursor  # 读侧链端 = 写侧游标(镜像)
        if -_DRIFT_TOL < gap <= _GAP_BOUND:  # 延伸判据(与 v4_live_tail_slots 同一单点): 有界 + 链端超前不超写侧漂移容差
            # 有界间隙(判据界内侧): 尾桶仍持有落线, 且相邻有界拍值恒定(无闪烁)
            saw_held_after_stall = True
            endpoint = rate.get(grid.last)
            assert endpoint is not None, (b, grid.last, "有界间隙尾桶不应断线")
            if prev_bounded_endpoint is not None:
                assert endpoint == prev_bounded_endpoint, (b, endpoint, prev_bounded_endpoint, "有界拍 held 值应恒定")
            prev_bounded_endpoint = endpoint
        else:
            # 间隙过界(判据界外侧): 尾桶 null 诚实断线, 且此后不再恢复
            saw_null_after_stall = True
            assert rate.get(grid.last) is None, (b, grid.last, "间隙过界尾桶应 null")
    # 判据界两侧都被真实观测到(评审轮1 #2: 不得整拍跨过过界点)
    assert saw_held_after_stall and saw_null_after_stall, (stall_endpoint, "停滞流应含有界与过界两态")
    assert stall_endpoint[-1] is None and stall_endpoint[-2] is None, "过界后应持续断线"


def test_a5_disconnect_n_run_stays_null():
    """(A5 断连态, R8 真断连仍 null)两态:
    - 有界断连缝: 单拍 disconnect(对末真实样本对跨 <= 判据界且跨过 1 枚空桶 —— 几何
      与判据界都满足回填面, 仅断连守卫 marked/null_since_obs 拦住回填), 缝内空桶保持
      null(守卫判别力钉 —— 评审轮1 #4: 移除守卫此例必红);
    - 长断连(观测缝 > 60s 停机洞): 重连桶速率 None 不造值(快照照记);
    - 重连拍尾桶 = 诚实缺口(held 被标记清空 -> 速率面 (None, None) —— 评审轮1 #5:
      原断言对元组 is not None 恒真), 重连后首个真实差分拍恢复落线"""
    # --- 有界断连缝(守卫判别力) ---
    sim = _SamplerSim(seed=41)
    for _ in range(40):
        sim.beat()
    c0 = sim.cursor  # 末真实样本槽(重连前最后观测; 读侧链端镜像)
    sim.beat(gap=1.2, disconnect=True)  # 短缝断连: null 槽(实测 dt 修正 ~1.2s, 判据界量级)
    grid_d, rate_d, _, _ = _beat_payload(sim, sim.req_now)
    assert rate_d.get(grid_d.last) is None, (grid_d.last, "断连中尾桶应 null(末槽 obs None 不延伸)")
    sim.beat()  # 重连(qB 恢复)
    grid_r, rate_r, totals_r, points_r = _beat_payload(sim, sim.req_now)
    # 判别力前置: 重连对末真实样本的对跨 <= 判据界 且 跨过 >= 1 枚空桶 —— 几何与界都
    # 满足 held_backfill 的非守卫条件, 缝内空桶仍 null 只能来自断连守卫
    i_prev = int((c0 - grid_r.first) // _B)
    i_cur = int((sim.cursor - grid_r.first) // _B)
    gap_total = sim.cursor - c0
    assert i_cur >= i_prev + 2 and gap_total <= _GAP_BOUND, (i_prev, i_cur, gap_total, "判别力前置不成立")
    bf_key = grid_r.first + (i_prev + 1) * _B
    assert rate_r.get(bf_key) is None, (bf_key, "有界断连缝空桶被回填(断连守卫失守)")
    # 重连拍尾桶 = 诚实缺口: held 被断连标记清空 -> 速率面 (None, None)(不造值不落线)
    assert rate_r.get(grid_r.last) == (None, None), (grid_r.last, rate_r.get(grid_r.last), "重连拍尾桶应诚实缺口")
    # --- 长断连(观测缝 > 60s 停机洞) ---
    sim2 = _SamplerSim(seed=41)
    for _ in range(40):
        sim2.beat()
    for _ in range(4):
        sim2.beat(gap=20.0, disconnect=True)  # 观测缝 80s > _V4_SEAM_NULL_S
    grid_d2, rate_d2, _, _ = _beat_payload(sim2, sim2.req_now)
    assert rate_d2.get(grid_d2.last) is None, (grid_d2.last, "长断连中尾桶应 null")
    sim2.beat()  # 重连(qB 恢复)
    grid_r2, rate_r2, totals_r2, points_r2 = _beat_payload(sim2, sim2.req_now)
    # 断连段桶(重连后回看)保持 null —— 标记(n 游程)不回填, 洞后不摊配(诚实断线)
    null_span = [t for t in rate_r2 if grid_r2.t0 <= t < grid_r2.last and rate_r2[t] is None]
    assert null_span, "断连段应有 null 桶(诚实断线)"
    # 重连桶: 停机洞断链 -> 速率 None 不造值(快照照记, totals 非 None)
    recv_key = grid_r2.first + int((sim2.cursor - grid_r2.first) // _B) * _B  # 重连样本点位归属桶
    recv = next(p for p in points_r2 if p.t == recv_key)
    assert recv.dl_rate is None and recv.up_rate is None, (recv, "重连桶速率应 None(洞后断链不造值)")
    assert recv.dl_total is not None and recv.up_total is not None, (recv, "重连桶快照应照记")
    # 重连拍尾桶诚实缺口(held 被标记清空)
    assert rate_r2.get(grid_r2.last) == (None, None), (grid_r2.last, rate_r2.get(grid_r2.last), "重连拍尾桶应诚实缺口")
    # 重连后再进两拍: 首个真实差分拍起链恢复, 终点持续落线(恢复落线钉在此, 非重连拍)
    for _ in range(2):
        sim2.beat()
        grid, rate, _, _ = _beat_payload(sim2, sim2.req_now)
        assert rate.get(grid.last) is not None, (grid.last, "恢复期尾桶应持续落线")
