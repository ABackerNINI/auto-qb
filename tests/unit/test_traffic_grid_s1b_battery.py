"""test_traffic_grid_s1b_battery 测试计划(26-11-18-0037 T1c-2 退役转世): 26-11-15-1104
S1b 收口电池(T3 有界空桶持有回填 + F3 尾桶 holding)已随挂钟桶面退役 —— A1/A5 验收语义
承袭到样本分组装配新契约面, _SamplerSim 写侧仿真器保留复用:

## 测试计划(每个测试函数一条)
- test_a1_steady_beat_diff_tail_appends_only: (A1)稳态恒速仿真逐拍差分(3 seed: 11/23/37)
  —— 新契约下逐样本点一旦落定恒不变(k=1 每样本一点, 值 = 该样本差分/覆盖, 一次算定):
  重叠 t 逐拍恒等(无振荡面), 新点只出现在尾部(追加), 掉点只出现在窗沿(前缀收缩),
  变化集 = 新增 + 前缀掉出; 仿真流含写侧累积漂移(DRIFT_TOL_MS 量级)与 dt 修正跳变
- test_a5_active_endpoint_true_value_no_false_break: (A5 活跃态)采样器活跃时曲线终点 =
  最新样本真值(t = 末样本 ts, 值 = 真实差分/覆盖, 无持有克隆); 覆盖段无空值点(dt 修正
  跳变/偶发 4s 大步进都被 dt 链吸收 —— 未采样非断连, 旧「跳变空桶有界持有回填」面随
  桶面退役); 镜像不变量逐拍核验(读侧块首槽 == 写侧块首)
- test_a5_stall_freezes_at_last_sample: (A5 停滞态)停止进样后窗口推进 —— 点集只在窗沿
  收缩, 无新点无空值点, 末点 t/值恒定(诚实滞后; 旧「有界 held 落线/过界 null」二态随
  持有面退役 —— 停流可见性由前端徽标按末样本 ts 承载, §03/D3)
- test_a5_disconnect_explicit_null_and_reconnect: (A5 断连态)断连 = 显式空值点(n 游程
  折叠一点, 端点 = 空值点, 无真值点尾随); 重连样本 = 诚实缩放(断连面 marked -> 摊配
  回收 step x 覆盖 // span, 速率 < 真实速率不冒充), totals = 跨缺口全量快照差分(字节
  真值); 长断连(观测缝 > 60s 停机洞)-> 重连样本速率 None 不造值(totals 真值), 空值点
  序列如实; 重连后首拍起终点恢复落线

仿真形态(生产同构): 采样间隔 si = 1.5s(生产现况), 1m 窗(窗内样本 ~40 -> k=1); 写侧
游标仿真 traffic_sample_mod 形态 —— 块首 B.start = int(首记录实测), 每拍标称推进 si, 累积
漂移 |actual - (游标 + si)| > DRIFT_TOL_MS(250ms)时本拍写实测 dt_ms 并自然复位; 字节按
真实耗时累积(恒速 1000/500 B/s, 计数器单调; qB 不可达拍计数器冻结)。活尾 = 整块
head_pending 形态(start_epoch = block_start —— 读侧链锚 == 写侧游标, 镜像不变量由 _beat
的首槽锚断言逐拍核验); 活尾复原 = v4_live_tail_slots 无 now 形态(持有延伸分支已退役)。

线程/时钟纪律: 纯函数层无时钟无文件 —— now 由仿真显式推进, 窗口/活尾逐拍直构。
"""

import random

from auto_qb.core.traffic_group_assembly import assemble_group_points

from auto_qb.core.traffic_store import LiveTail, V4NullRun, V4Sample, v4_block_slots, v4_live_tail_slots
from auto_qb.core.traffic_store_common import DRIFT_TOL_MS

_SI = 1.5  # 采样间隔(生产现况)
_DRIFT_TOL = DRIFT_TOL_MS / 1000.0  # 写侧漂移容差(dt 修正触发的累积界, 单点引用)
_START = 1_800_000_000  # 时钟基点(纯测试时刻; 块首 = int(首记录实测), 非本值)


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

    def slots(self):
        """当前全部记录的槽序(磁盘 + 活尾复原的并集: head_pending 整块形态下活尾槽 ==
        整块重算槽, 无需去重; 生产形态去重在缓存锁内, 本仿真直喂装配面)"""
        return v4_live_tail_slots(self.tail())

    def beat_payload(self):
        """单拍装配(生产同构: 活尾槽序 -> 样本分组装配, 窗 = [req_now-60, req_now));
        镜像不变量逐拍核验: 读侧块首槽 == 写侧块首(链锚对齐, 评审轮1 #1 回归面)。"""
        slots = self.slots()
        assert slots[0].ts == float(self.block_start), (
            slots[0].ts,
            self.block_start,
            "读侧链锚 != 写侧块首(镜像不变量破坏)",
        )
        res = assemble_group_points(slots, self.req_now - 60, self.req_now, _SI)
        return res


def _real(res):
    """真值点 (t, dl, up) 序列(空值点 = totals None 剔除)"""
    return [(p["t"], p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None]


def _null_ts(res):
    """显式空值点 t 序列(判据 = totals None)"""
    return [p["t"] for p, t in zip(res.points, res.totals) if t is None]


def test_a1_steady_beat_diff_tail_appends_only():
    """(A1)稳态恒速 + 漂移/dt 修正跳变流逐拍差分(3 seed): 逐样本点落定恒不变(k=1 一次
    算定)—— 重叠 t 逐拍恒等、新点只追加在尾、掉点只收缩在窗沿(变化集 = 新增 + 前缀
    掉出), 无振荡面(旧「封口桶不可变」的振荡不可能性由逐样本一次算定自然承载);
    dt 修正跳变(显式 dt > 标称 + 100ms)真实出现在仿真流中(漂移累积超容差)"""
    for seed in (11, 23, 37):
        sim = _SamplerSim(seed=seed)
        prev = None
        jump_count = 0
        for i in range(80):
            rec = sim.beat()
            res = sim.beat_payload()
            if rec.dt_ms is not None and rec.dt_ms > _SI * 1000 + 100:
                jump_count += 1  # dt 修正跳变(正向漂移修正的写侧形态)
            if i < 10:  # 预热: 链尚短
                prev = res
                continue
            cur = {p["t"]: (p["dl"], p["up"]) for p, t in zip(res.points, res.totals) if t is not None}
            prv = {p["t"]: (p["dl"], p["up"]) for p, t in zip(prev.points, prev.totals) if t is not None}
            overlap = set(cur) & set(prv)
            # 重叠 t 逐拍恒等(样本值一次算定不再改写 —— 振荡在语义上不可能)
            for t in overlap:
                assert cur[t] == prv[t], (seed, i, t, cur[t], prv[t], "重叠样本点值漂移")
            # 新点只在尾部追加(新样本), 掉点只在窗沿(前缀)
            added = set(cur) - set(prv)
            dropped = set(prv) - set(cur)
            assert all(t > max(prv) for t in added), (seed, i, sorted(added), "非尾部新增点")
            assert all(t < min(cur) for t in dropped), (seed, i, sorted(dropped), "非窗沿掉点")
            assert not _null_ts(res), (seed, i, _null_ts(res), "稳态流无空值点")
            prev = res
        assert jump_count > 0, (seed, "仿真流应含 dt 修正跳变(漂移累积超容差)")


def test_a5_active_endpoint_true_value_no_false_break():
    """(A5 活跃态)终点 = 最新样本真值: 每拍末点 t = 末样本槽 ts(链端, 无持有克隆 ——
    旧面 now 延伸 holding 槽面退役), 值 = 真实差分/覆盖(恒速 1000/500, 抖动容差带);
    覆盖段无空值点(偶发 4s 大步进被 dt 链吸收 —— 未采样非断连, 旧跳变回填面退役);
    镜像不变量逐拍核验(见 _SamplerSim.beat_payload)"""
    sim = _SamplerSim(seed=23)
    for i in range(80):
        # i % 17 == 5 注入 4s 大步进(恰跨数个采样间隔的写侧形态 —— dt 链吸收, 无空值点)
        sim.beat(gap=4.0) if i % 17 == 5 and i > 0 else sim.beat()
        if i < 3:
            continue  # 预热: 链首样本无基线 0 线, 末点真值断言需 >= 1 个差分对
        res = sim.beat_payload()
        real = _real(res)
        assert real, (i, "活跃流应有点")
        last = real[-1]
        # 终点 = 窗内最新样本(槽 ts < t1; 写侧游标可在漂移容差内超前实测时刻, 末槽
        # 偶发落在 t1 之后被窗尾过滤 —— 新契约无持有豁免, 端点如实取窗内最新样本)
        expected = max(s.ts for s in sim.slots() if s.ts < sim.req_now)
        assert last[0] == expected, (i, last, expected, "末点 t != 窗内最新样本 ts")
        # 真实速率带: 标称 1000/500; 漂移修正拍的对跨被压缩(< elapsed)令样本速率上浮
        # (上限 = 1000 x si/(si - DRIFT_TOL) x 抖动余量), 下浮由抖动/取整给出
        assert 850 <= last[1] <= 1300 and 425 <= last[2] <= 650, (i, last, "末点值偏出真实速率带")
        assert not _null_ts(res), (i, _null_ts(res), "活跃流无空值点(大步进被 dt 链吸收)")


def test_a5_stall_freezes_at_last_sample():
    """(A5 停滞态)停止进样后窗口半拍步进推进(12 拍): 点集只在窗沿收缩(前缀掉样本),
    无新点无空值点, 末点 t/值恒定 —— 旧「判据界内有界 held 落线/过界 null」二态随持有面
    退役: 数据面停滞期不动, 滞后可见性 = 前端徽标按末样本 ts vs 墙钟承载(§03/D3)"""
    sim = _SamplerSim(seed=37)
    for _ in range(50):
        sim.beat()
    res0 = sim.beat_payload()
    last0 = _real(res0)[-1]
    assert _real(res0)[-1][1] is not None, "进样期终点应落线"
    frozen = 0
    for b in range(1, 13):
        sim.req_now += _SI / 2  # 写侧无新记录, 只推请求时刻
        res = sim.beat_payload()
        assert _real(res)[-1] == last0, (b, _real(res)[-1], last0, "停滞期末点被改写")
        assert not _null_ts(res), (b, "停滞期无空值点(不造断连)")
        assert set(p["t"] for p, t in zip(res.points, res.totals) if t is not None) <= set(
            p["t"] for p, t in zip(res0.points, res0.totals) if t is not None
        )
        frozen += 1
    assert frozen == 12  # 判据面被真实观测(12 拍全部冻结)


def test_a5_disconnect_explicit_null_and_reconnect():
    """(A5 断连态)断连 = 显式空值点(n 游程折叠一点, 端点 = 空值点无真值尾随); 重连样本
    = 诚实缩放(marked -> step x 覆盖 // span, 速率 < 真实速率不冒充), totals = 跨缺口
    全量快照差分(字节真值); 长断连(观测缝 > 60s 停机洞)-> 重连样本速率 None(totals
    真值), 重连后首拍起终点恢复落线"""
    # --- 有界断连缝(显式空值点 + 诚实缩放) ---
    sim = _SamplerSim(seed=41)
    for _ in range(40):
        sim.beat()
    c0 = sim.cursor  # 末真实样本槽(重连前最后观测; 读侧链端镜像)
    sim.beat(gap=1.2, disconnect=True)  # 短缝断连: null 槽
    res_d = sim.beat_payload()
    nulls = _null_ts(res_d)
    assert nulls, (nulls, "断连拍应产显式空值点")
    assert nulls[-1] == float(int(sim.cursor))  # n 首槽 floor 取整(链端镜像)
    assert _real(res_d)[-1][0] == c0  # 空值点之前的末真值点 = 末真实样本(无真值点尾随)
    sim.beat()  # 重连(qB 恢复)
    res_r = sim.beat_payload()
    real_r = _real(res_r)
    recv = real_r[-1]
    assert recv[0] == sim.cursor  # 重连样本 = 新末点
    # 诚实缩放: 断连面 marked -> step_w = step x 覆盖 // span(缝 1.2s 不归因), 速率
    # < 真实速率 1000(不冒充连续); totals = 跨缺口全量快照差分(字节真值)
    assert recv[1] < 1000 and recv[1] > 0, (recv, "重连样本应诚实缩放(非真实速率非 None)")
    tot_r = [t for p, t in zip(res_r.points, res_r.totals) if t is not None]
    # 跨缺口字节含在后继样本差分里(计数器真值 —— 断连拍计数器冻结, 仅缝前累计 + 重连拍)
    assert int(1000 * 1.2) <= tot_r[-1]["dl"] <= int(1000 * 3.0), (tot_r[-1], "跨缺口 totals 应计数器真值")
    # --- 长断连(观测缝 80s > 60s 停机洞) ---
    sim2 = _SamplerSim(seed=41)
    for _ in range(40):
        sim2.beat()
    for _ in range(2):
        sim2.beat(gap=40.0, disconnect=True)  # 观测缝 80s > _V4_SEAM_NULL_S(停机洞)
    res_d2 = sim2.beat_payload()
    # 连续 n 游程折叠一点: 单个空值点 @断连起点(c0 + 40, 在窗内 —— 缝 80s < 窗 60s + 延迟)
    assert _null_ts(res_d2) == [float(int(c0 + 40.0))], (_null_ts(res_d2), "长断连应产单空值点@断连起点")
    sim2.beat()  # 重连(qB 恢复)
    res_r2 = sim2.beat_payload()
    real_r2 = _real(res_r2)
    recv2 = real_r2[-1]
    assert recv2[0] == sim2.cursor
    assert recv2[1] is None and recv2[2] is None, (recv2, "重连样本速率应 None(洞后断链不造值)")
    tot_r2 = [t for p, t in zip(res_r2.points, res_r2.totals) if t is not None]
    # 跨洞 totals = 计数器真值(qB 不可达拍计数器冻结 —— 缝内零字节, 仅重连拍字节入账)
    assert 0 < tot_r2[-1]["dl"] <= int(1000 * 2.0), (tot_r2[-1], "跨洞 totals 应计数器真值(冻结缝不造字节)")
    # 重连后再进两拍: 链恢复, 终点持续落线(恢复落线钉在此, 非重连拍)
    for _ in range(2):
        sim2.beat()
        res = sim2.beat_payload()
        last = _real(res)[-1]
        assert last[0] == sim2.cursor and 900 <= last[1] <= 1100, (last, "恢复期终点应落线")
