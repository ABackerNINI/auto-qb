"""traffic_recovery_support: B1 恢复对拍 harness(计划 26-11-21-1546 S1; 供 P1c/B2 复用)

对拍口径(D2/§07 R1): 「旧全量路径(全解析 + 全槽入账 + 尾部丢弃, 用现有公开件重建参照
实现 —— v4_hour_agg 保留作对拍基准的先例)」vs「新 B1 路径(read_day_open_segment 开放段
限定解析 + skip_through_hour 记账入口过滤)」。断言面: 开放小时折叠态逐字段 bitwise
(HourFold dataclass 等值 = 7 数逐字段)+ 完结小时 seal 行 bitwise(AggRow NamedTuple 等值
+ format_agg_row 9 列文本逐位)+ 开放小时 pending 折叠态 bitwise + 跨文件 tail 上下文
逐位。样本列表粒度不比(D2 明示允许不同)。

语料纪律(writer 形态不变式, open_segment 决策的前提): 单条连续采样流时刻严格递增,
逐日一个文件(00:00 硬切块不跨天), 后块 B.start > 前块末槽, totals 单调递增, 块内
r/z/n 混排, dt 链显式/标称混合(|实际 - (锚点+标称)| <= 250ms 不写 dt, 否则写实测
dt_ms —— 与写侧漂移判据同口径)。
"""

import math
import random

from auto_qb.core.modules.traffic_sample_mod import TrafficSampleModule
from auto_qb.core.traffic_store import (
    HOUR_SECONDS,
    TrafficV4Store,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    v4_date_str_epoch,
    v4_day_epoch,
)

#: 写侧累积漂移容差(秒; traffic_store_common.DRIFT_TOL_MS / 1000 同源口径)
DRIFT_TOL_S = 0.25

#: 语料风格 -> (z 游程概率, n 游程概率); 其余概率 = r 样本
_STYLE_PROBS = {
    "z-heavy": (0.86, 0.04),  # 空闲日: 长零速游程主导(行少槽多)
    "r-heavy": (0.06, 0.03),  # 活跃日: r 行主导(行多)
    "mixed": (0.45, 0.08),
}


class _Totals:
    """all-time totals 单调递增(无计数器回落形态 —— 写侧回落会强制关块重立基线, 语料
    不含该形态; 负 delta 是解析免费校验面, 不属本 harness 对拍域)"""
    def __init__(self, dl: int, up: int) -> None:
        self.dl = dl
        self.up = up

    def bump(self, rng: random.Random) -> None:
        self.dl += rng.randrange(0, 50_000)
        self.up += rng.randrange(0, 20_000)


def _emit_run(rng: random.Random, chain: float, interval: float, run_len: int, first: bool) -> tuple:
    """游程编码(链式自洽): 返回 (dt_ms, chain_end)。块首游程端点含(首槽 = B.start,
    末槽 = B.start + spacing x (run_len-1)); 非块首 span/run_len 均摊(链终点 = 末槽)。
    显式 dt 概率 0.3(实测跨度), 其余标称(None)。"""
    if first:
        span = interval * (run_len - 1)
        if run_len > 1 and rng.random() < 0.3:
            dt = max(1, int(round(span * 1000)))
            return dt, chain + dt / 1000.0
        return None, chain + span
    span = interval * run_len
    if rng.random() < 0.3:
        dt = max(1, int(round(span * 1000)))
        return dt, chain + dt / 1000.0
    return None, chain + span


def _build_block(
    rng: random.Random, tot: _Totals, t: float, interval: float, z_p: float, n_p: float, day_end: float,
    max_records: int
) -> tuple:
    """构建一个块(纯生成面): 返回 (start_epoch, records, block_base, chain_end, n_slots)。

    - start_epoch = int(块首样本实测时刻)(B.start; 块首记录槽位恰在 B.start);
    - records 按 dt 链推进(r 样本标称/漂移显式混合, z/n 游程均摊), 全部槽位 < day_end
      (块不跨天 —— 越界即收块);
    - block_base = (dl, up)(块首 r/z 立基线, 块首记录 delta = 0)或 None(块首 n 游程
      前缀 -> 全 n 块, 3 列 B);
    - chain_end = 末槽槽位锚点(= 写侧游标推进结果, 下一块时刻必须严格晚于它)。"""
    si = interval
    start = float(math.floor(t))
    chain = start
    recs: list = []
    n_slots = 0
    base = None
    n_only = rng.random() < n_p * 0.5  # 偶发 n-only 前缀块(3 列 B, 块内仅 n 合法)
    limit = day_end - 0.05
    for _ in range(max_records):
        if chain >= limit:
            break  # 末槽已达日界附近: 收块(跨 00:00 连续由下一日首块衔接)
        if n_only:
            run_len = rng.randint(1, 4)
            if chain + (si * run_len if recs else si * (run_len - 1)) > limit:
                break
            dt, chain = _emit_run(rng, chain, si, run_len, first=not recs)
            recs.append(V4NullRun(run_len, dt))
            n_slots += run_len
            continue
        roll = rng.random()
        if roll < z_p:
            run_len = rng.randint(2, 40)
            fit = int((limit - chain) / si) - (1 if not recs else 0)
            if si * (run_len - 1 if not recs else run_len) > limit - chain:
                run_len = max(2, fit)  # 收块前压缩游程(保底 2 槽)
                if si * (run_len - 1 if not recs else run_len) > limit - chain:
                    break
            open_dl, open_up = tot.dl, tot.up
            dt, chain = _emit_run(rng, chain, si, run_len, first=not recs)
            tot.bump(rng)  # 末端快照(>= 开启快照; 形态 D 末端对)
            if base is None:
                base = (open_dl, open_up)  # 块首 z 立基线: 冻结列 = 开启快照, delta = 0
            recs.append(V4ZeroRun(run_len, open_dl, open_up, dt, tot.dl, tot.up))
            n_slots += run_len
        elif roll < z_p + n_p:
            if not recs:
                n_only = True  # 块首 n 游程 = n-only 前缀块(3 列 B, 写侧拆块口径)
            run_len = rng.randint(1, 6)
            if chain + (si * run_len if recs else si * (run_len - 1)) > limit:
                break
            dt, chain = _emit_run(rng, chain, si, run_len, first=not recs)
            recs.append(V4NullRun(run_len, dt))
            n_slots += run_len
        else:
            tot.bump(rng)
            if not recs:
                # 块首 r: 槽位恰在 B.start, 链不推进; 基线 = 本记录快照(delta = 0)
                if chain > limit:
                    break
                base = (tot.dl, tot.up)
                recs.append(V4Sample(rng.randrange(0, 500_000), rng.randrange(0, 200_000), tot.dl, tot.up))
                n_slots += 1
            else:
                jitter = rng.uniform(-0.3, 0.3)
                if abs(jitter) <= DRIFT_TOL_S or rng.random() < 0.7:
                    adv, dt = si, None  # 漂移 <= 容差: 标称推进(写侧同判)
                else:
                    adv = si + jitter
                    dt = max(1, int(round(adv * 1000)))
                if chain + adv > limit:
                    break
                chain += adv
                recs.append(V4Sample(rng.randrange(0, 500_000), rng.randrange(0, 200_000), tot.dl, tot.up, dt))
                n_slots += 1
    if not recs:
        return start, (), None, chain, 0
    return start, tuple(recs), base, chain, n_slots


def synthesize_series_files(
    store: TrafficV4Store,
    key: str,
    day_dates: tuple,
    rng: random.Random,
    *,
    interval: float = 30.0,
    style: str = "mixed",
    totals: tuple = (1_000_000_000, 2_000_000_000)
) -> dict:
    """随机合成 writer 形态天文件语料(B1 对拍基准; P1c 复用): 逐日一文件写入 store,
    返回 {date: (块数, 槽位数)} 信息面。

    形态纪律(见模块 docstring); 额外编排:
    - 偶数序日以「日界尾块」收尾(两笔 r, 末槽压到 00:00 前约半 interval 的整秒位),
      次日首块自 00:00 起紧随其后 —— 跨 00:00 连续结算形态必现(gap <= interval +
      容差; 极小 interval 时该边界可能翻成真空, 两形态本就都需覆盖); 奇数序日自然
      收尾(跨日真空形态, 结算断链);
    - 块间 gap 混合: 连续(约 1s 量级, 结算信用形态)与真空(超容差, 崩溃/停机形态);
    - n-only 前缀块(3 列 B)偶发, 与基线块任意顺序并存。"""
    z_p, n_p = _STYLE_PROBS[style]
    tot = _Totals(*totals)
    si = interval
    info: dict = {}
    t = v4_date_str_epoch(day_dates[0]) + rng.uniform(0.0, 3 * 3600.0)
    for di, date in enumerate(day_dates):
        d_end = v4_date_str_epoch(day_dates[di + 1]) if di + 1 < len(day_dates) else v4_date_str_epoch(date) + 86400.0
        n_blocks, n_slots = 0, 0
        while t < d_end - 2 * si:
            start, recs, base, chain, slots = _build_block(rng, tot, t, si, z_p, n_p, d_end, rng.randint(2, 6))
            if not recs:
                break
            store.append_records(key, date, (start, si), recs, base)
            n_blocks += 1
            n_slots += slots
            # 下一块时刻: floor(chain)+1 保证 B.start 严格晚于前块末槽(写侧产出不变式);
            # 连续形态(gap < interval, 结算信用)与真空形态(gap 超容差)混合
            if rng.random() < 0.6:
                t = math.floor(chain) + 1.0 + rng.uniform(0.0, si * 0.4)
            else:
                t = math.floor(chain) + 1.0 + rng.uniform(si, 600.0)
        if di % 2 == 0 and di + 1 < len(day_dates):
            # 日界尾块: 两笔 r(块首 delta 0 + 标称推进), 末槽 = floor(日界 - max(1, si/2) - si) + si
            # —— 距 00:00 约 0.5 interval(整秒), 次日首块 B.start >= 日界, gap <= interval + 容差
            tail_last = d_end - max(1.0, si * 0.5)
            tail_start = math.floor(tail_last - si)
            tot.bump(rng)
            tot.bump(rng)
            store.append_records(
                key,
                date,
                (float(tail_start), si),
                (
                    V4Sample(rng.randrange(0, 500_000), rng.randrange(0, 200_000), tot.dl, tot.up),
                    V4Sample(rng.randrange(0, 500_000), rng.randrange(0, 200_000), tot.dl, tot.up),
                ),
                (tot.dl, tot.up),
            )
            n_blocks += 1
            n_slots += 2
            chain = tail_start + si  # 标称推进: 末槽 = B.start + si
            t = max(chain + 1.0, d_end) + rng.uniform(0.0, si * 0.4)  # 次日首块 >= 日界(不跨天)
        else:
            t = max(t, d_end) + rng.uniform(0.0, 2 * si)  # 奇数序日: 跨日真空
        info[date] = (n_blocks, n_slots)
    return info


def read_set_dates(store: TrafficV4Store, key: str, now: float, wm_hour, window: float = 30 * 86400.0) -> tuple:
    """恢复读集(_recover_series 逐字镜像, D3 文件级读集不变): 下界 = 水位所在日 /
    fallback(wm None)保留窗 now - window。"""
    lower = v4_day_epoch(wm_hour) if wm_hour is not None else now - window
    return store.series_day_dates(key, lower)


def reference_full_credit(store: TrafficV4Store, key: str, day_dates: tuple, wm_hour) -> tuple:
    """旧全量路径参照(改造前 _recover_series 恢复循环, 用现有公开件重建, 循环体与生产
    逐字对齐): 全量解析(store.read_day)+ 无过滤逐文件前向记账(_agg_credit_day_file)+
    尾部判据丢弃 h <= wm_hour。返回 (hour_samples, tail, slots)。"""
    samples: dict = {}
    tail = None
    slot_counts: list = []
    for d in day_dates:
        pd = store.read_day(key, d)
        if pd is not None:
            tail = TrafficSampleModule._agg_credit_day_file(samples, pd, tail, slot_counts)
        else:
            tail = None  # 缺失/空文件: 结算上下文断链(与生产循环逐字对齐, 评审 P1b-1)
    if wm_hour is not None:
        samples = {h: f for h, f in samples.items() if h > wm_hour}
    return samples, tail, sum(slot_counts)


def b1_production_credit(store: TrafficV4Store, key: str, day_dates: tuple, wm_hour) -> tuple:
    """B1 生产路径镜像(_recover_series 恢复循环逐字): 水位路径 read_day_open_segment +
    skip_through_hour 前移过滤; fallback(wm None)走 read_day 零过滤(D4 语义不变)。
    返回 (hour_samples, tail, slots)。"""
    samples: dict = {}
    tail = None
    slot_counts: list = []
    for d in day_dates:
        pd = store.read_day(key, d) if wm_hour is None else store.read_day_open_segment(key, d, wm_hour)
        if pd is not None:
            tail = TrafficSampleModule._agg_credit_day_file(samples, pd, tail, slot_counts, skip_through_hour=wm_hour)
        else:
            tail = None
    return samples, tail, sum(slot_counts)


def split_rows_pending(samples: dict, now: float) -> tuple:
    """_recover_series 的下游消费面切片(D12 折叠态): 完结小时 -> seal 行序列;
    开放小时 -> pending 折叠态(重建累计器)。"""
    rows: list = []
    pending: dict = {}
    for h in sorted(samples):
        fold = samples[h]
        if fold.credits == 0:
            continue  # 空桶不产行(防御支, 生产路径同)
        if h + HOUR_SECONDS <= now:
            rows.append(fold.seal(h))
        else:
            pending[h] = fold
    return rows, pending


def assert_b1_bitwise_equivalent(
    ref_samples: dict, ref_tail, b1_samples: dict, b1_tail, now: float, ctx: str = ""
) -> tuple:
    """对拍断言(D2 口径, 随机语料 harness 的核心): 折叠态逐字段 bitwise / seal 行
    bitwise(AggRow 等值 + format_agg_row 文本逐位)/ pending 折叠态 bitwise / 跨文件
    tail 上下文逐位。返回 (rows, pending) 供调用方追加断言。"""
    tag = f"[{ctx}] " if ctx else ""
    assert set(b1_samples) == set(ref_samples), f"{tag}开放小时键集不等: {set(ref_samples) ^ set(b1_samples)}"
    for h in sorted(ref_samples):
        assert b1_samples[h] == ref_samples[h], f"{tag}hour 折叠态不等: {h}"
    assert b1_tail == ref_tail, f"{tag}跨文件 tail 上下文不等: {ref_tail!r} vs {b1_tail!r}"
    ref_rows, ref_pending = split_rows_pending(ref_samples, now)
    b1_rows, b1_pending = split_rows_pending(b1_samples, now)
    assert b1_rows == ref_rows, f"{tag}seal 行序列不等"
    assert [format_agg_row(r) for r in b1_rows] == [format_agg_row(r) for r in ref_rows], f"{tag}agg 行文本不等"
    assert b1_pending == ref_pending, f"{tag}pending 折叠态不等"
    return ref_rows, ref_pending
