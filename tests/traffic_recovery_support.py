"""traffic_recovery_support: B1+B2 恢复对拍 harness(计划 26-11-21-1546 S1)

对拍口径(D2/§07 R1): 「旧路径参照(逐槽展开 + 逐槽入账, reference_slot_credit 按 B2 改造
前生产实现逐字镜像冻结 —— v4_hour_agg 保留作对拍基准的同款先例)」vs「新生产路径(B1
read_day_open_segment 开放段限定解析 + skip_through_hour 记账入口过滤 + B2 游程级闭合式
入账)。断言面(分两级):
- 聚合输出层(D2 字面口径, 全语料断言): 完结小时 seal 行 bitwise(AggRow 等值 +
  format_agg_row 9 列文本逐位)+ 开放 pending 桶的 seal 行 bitwise(pending 经聚合后
  相等)+ 跨文件 tail 上下文逐位 + hour 桶集相等。样本列表粒度不比(D2 明示允许不同)。
- fold 内部字段分级(B2 FP 纪律, 见 assert_folds_field_equivalent): wsum/max/totals
  末笔必须逐位; cov ULP 免责(容差 COV_ULP_TOL, FP 论证见其注)—— 精确栅格语料
  (exact_grid=True)两路全程精确, cov 升级为逐位断言; credits 结构豁免(仅 ==0 判空
  消费, 不进聚合输出)。

语料纪律(writer 形态不变式, open_segment 决策的前提): 单条连续采样流时刻严格递增,
逐日一个文件(00:00 硬切块不跨天), 后块 B.start > 前块末槽, totals 单调递增, 块内
r/z/n 混排, dt 链显式/标称混合(|实际 - (锚点+标称)| <= 250ms 不写 dt, 否则写实测
dt_ms —— 与写侧漂移判据同口径)。两族语料(B2 对拍要求, 随机 dt 与精确栅格都要过):
- 默认族: r 行抖动显式 dt; run_dt_jitter=True 时 z/n 游程显式 dt_ms 加超出容差的
  实测抖动(真实写侧形态: 漂移 > 250ms 才写实测) —— 游程 spacing 非精确可表示,
  闭合式 vs 逐槽的 cov ULP 免责路径被真实触发;
- 精确栅格族(exact_grid=True, 配 interval=1.5): 全部记录标称推进(生产 1.5s 档零漂移
  形态), 槽位链全程 FP 精确(整数 + 1.5k 在 [2^30, 2^31) binade 均可精确表示)——
  cov 无 ULP 差, 断言升级为逐位。
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
    v4_block_agg_totals,
    v4_block_gap_continuous,
    v4_block_slots,
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


def _emit_run(
    rng: random.Random, chain: float, interval: float, run_len: int, first: bool, run_dt_jitter: bool = False
) -> tuple:
    """游程编码(链式自洽): 返回 (dt_ms, chain_end)。块首游程端点含(首槽 = B.start,
    末槽 = B.start + spacing x (run_len-1)); 非块首 span/run_len 均摊(链终点 = 末槽)。
    显式 dt 概率 0.3(实测跨度), 其余标称(None)。run_dt_jitter=True 时显式 dt 加超出
    容差的实测抖动(|抖动| > 250ms —— 写侧漂移判据: 超容差才写实测), spacing 非精确
    可表示(B2 闭合式 cov ULP 免责路径的真实触发形态)。"""
    if first:
        span = interval * (run_len - 1)
        if run_len > 1 and rng.random() < 0.3:
            dt = _run_dt_ms(rng, span, run_dt_jitter)
            return dt, chain + dt / 1000.0
        return None, chain + span
    span = interval * run_len
    if rng.random() < 0.3:
        dt = _run_dt_ms(rng, span, run_dt_jitter)
        return dt, chain + dt / 1000.0
    return None, chain + span


def _run_dt_ms(rng: random.Random, span: float, run_dt_jitter: bool) -> int:
    """游程显式 dt_ms(毫秒): 默认 = 标称跨度整毫秒(精确可表示 spacing); run_dt_jitter
    时加实测抖动 —— |抖动| > DRIFT_TOL_S(写侧超容差才写实测的判据同口径), 取
    (0.26..0.6) 随机符号, 保证 spacing = dt/1000/n 非精确栅格点。"""
    if not run_dt_jitter:
        return max(1, int(round(span * 1000)))
    jitter = rng.uniform(0.26, 0.6) * (1 if rng.random() < 0.5 else -1)
    return max(1, int(round((span + jitter) * 1000)))


def _build_block(
    rng: random.Random,
    tot: _Totals,
    t: float,
    interval: float,
    z_p: float,
    n_p: float,
    day_end: float,
    max_records: int,
    exact_grid: bool = False,
    run_dt_jitter: bool = False
) -> tuple:
    """构建一个块(纯生成面): 返回 (start_epoch, records, block_base, chain_end, n_slots)。

    - start_epoch = int(块首样本实测时刻)(B.start; 块首记录槽位恰在 B.start);
    - records 按 dt 链推进(r 样本标称/漂移显式混合, z/n 游程均摊), 全部槽位 < day_end
      (块不跨天 —— 越界即收块);
    - block_base = (dl, up)(块首 r/z 立基线, 块首记录 delta = 0)或 None(块首 n 游程
      前缀 -> 全 n 块, 3 列 B);
    - chain_end = 末槽槽位锚点(= 写侧游标推进结果, 下一块时刻必须严格晚于它);
    - exact_grid=True: r 行恒标称推进(生产 1.5s 档零漂移形态, 槽位链全程 FP 精确)。"""
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
            dt, chain = _emit_run(rng, chain, si, run_len, first=not recs, run_dt_jitter=run_dt_jitter)
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
            dt, chain = _emit_run(rng, chain, si, run_len, first=not recs, run_dt_jitter=run_dt_jitter)
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
            dt, chain = _emit_run(rng, chain, si, run_len, first=not recs, run_dt_jitter=run_dt_jitter)
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
                if exact_grid:
                    adv, dt = si, None  # 精确栅格族: 恒标称(零漂移形态)
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
    totals: tuple = (1_000_000_000, 2_000_000_000),
    exact_grid: bool = False,
    run_dt_jitter: bool = False
) -> dict:
    """随机合成 writer 形态天文件语料(B1/B2 对拍基准; P1c 复用): 逐日一文件写入 store,
    返回 {date: (块数, 槽位数)} 信息面。

    形态纪律(见模块 docstring); 额外编排:
    - 偶数序日以「日界尾块」收尾(两笔 r, 末槽压到 00:00 前约半 interval 的整秒位),
      次日首块自 00:00 起紧随其后 —— 跨 00:00 连续结算形态必现(gap <= interval +
      容差; 极小 interval 时该边界可能翻成真空, 两形态本就都需覆盖); 奇数序日自然
      收尾(跨日真空形态, 结算断链);
    - 块间 gap 混合: 连续(约 1s 量级, 结算信用形态)与真空(超容差, 崩溃/停机形态);
    - n-only 前缀块(3 列 B)偶发, 与基线块任意顺序并存;
    - exact_grid=True(配 interval=1.5 = 生产 1.5s 精确栅格族): r 行恒标称, 槽位链
      全程 FP 精确; run_dt_jitter=True(随机 dt 族): 游程显式 dt_ms 带超容差实测
      抖动, spacing 非精确可表示 —— B2 闭合式 cov ULP 免责路径的真实触发形态。"""
    z_p, n_p = _STYLE_PROBS[style]
    tot = _Totals(*totals)
    si = interval
    info: dict = {}
    t = v4_date_str_epoch(day_dates[0]) + rng.uniform(0.0, 3 * 3600.0)
    for di, date in enumerate(day_dates):
        d_end = v4_date_str_epoch(day_dates[di + 1]) if di + 1 < len(day_dates) else v4_date_str_epoch(date) + 86400.0
        n_blocks, n_slots = 0, 0
        while t < d_end - 2 * si:
            start, recs, base, chain, slots = _build_block(
                rng, tot, t, si, z_p, n_p, d_end, rng.randint(2, 6), exact_grid=exact_grid, run_dt_jitter=run_dt_jitter
            )
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


def reference_slot_credit(hour_samples: dict, parsed_day, prev_tail=None, slot_counter=None, skip_through_hour=None):
    """旧全量路径参照件(B2 改造前生产 _agg_credit_day_file 的逐字镜像, 冻结在测试侧 ——
    v4_hour_agg 保留作对拍基准的同款先例): 逐块 v4_block_slots 展开 + v4_block_agg_totals
    摊配 + 逐槽前向记账。生产路径(B2 游程级闭合式)与它的等价性 = 本文件全部对拍的
    参照基准; 断言层级见 assert_folds_field_equivalent / assert_b1_bitwise_equivalent。"""
    tail = prev_tail
    for block in parsed_day.blocks:
        slots = v4_block_slots(block)
        agg_totals = v4_block_agg_totals(block)  # 形态 D: z 槽摊配值(与 slots 等长同序)
        if slot_counter is not None:
            slot_counter.append(len(slots))
        if not slots:
            continue
        first = slots[0]
        if tail is not None and tail[1] is not None:
            if v4_block_gap_continuous(tail[0], first.ts, block.interval_s):
                dl, up, dlt, upt = tail[1]
                TrafficSampleModule._agg_credit_hours(
                    hour_samples, tail[0], first.ts, dl, up, dlt, upt, skip_through_hour
                )
        for k in range(len(slots) - 1):
            cur, nxt = slots[k], slots[k + 1]
            obs = TrafficSampleModule._slot_agg_obs(cur, agg_totals[k])
            if obs is None:
                continue  # n 槽: null 期不贡献
            TrafficSampleModule._agg_credit_hours(hour_samples, cur.ts, nxt.ts, *obs, skip_through_hour)
        tail = (slots[-1].ts, TrafficSampleModule._slot_agg_obs(slots[-1], agg_totals[-1]))
    return tail


def reference_full_credit(store: TrafficV4Store, key: str, day_dates: tuple, wm_hour) -> tuple:
    """旧全量路径参照(B2 改造前 _recover_series 恢复循环, 循环体与生产逐字对齐): 全量
    解析(store.read_day)+ 无过滤逐文件前向记账(reference_slot_credit = 逐槽参照件)+
    尾部判据丢弃 h <= wm_hour。返回 (hour_samples, tail, slots)。"""
    samples: dict = {}
    tail = None
    slot_counts: list = []
    for d in day_dates:
        pd = store.read_day(key, d)
        if pd is not None:
            tail = reference_slot_credit(samples, pd, tail, slot_counts)
        else:
            tail = None  # 缺失/空文件: 结算上下文断链(与生产循环逐字对齐, 评审 P1b-1)
    if wm_hour is not None:
        samples = {h: f for h, f in samples.items() if h > wm_hour}
    return samples, tail, sum(slot_counts)


def b1_production_credit(store: TrafficV4Store, key: str, day_dates: tuple, wm_hour) -> tuple:
    """生产路径镜像(_recover_series 恢复循环逐字): 水位路径 read_day_open_segment(B1
    开放段限定解析)+ B2 游程级闭合式 _agg_credit_day_file + skip_through_hour 前移过滤;
    fallback(wm None)走 read_day 零过滤(D4 语义不变)。返回 (hour_samples, tail, slots)。"""
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


#: fold.cov 的 ULP 免责容差(秒)。FP 论证(plan 26-11-21-1546 S1-B2 第 4 点):
#: - 理论上界: 闭合式桶内 Σdt = 桶内正长度区间并集端点差一次 Sterbenz 精确减法(=
#:   真实 telescoping 和); 逐槽参照 = 精确分段差的 FP 累加(累加含舍入)—— 两路差 =
#:   参照累加舍入, 上界 ≈ 段数 x ULP(3600) <= ~1.6e-9(段数 <= 3600, ULP(3600) = 2^-41);
#:   容差 1e-6 = 上界 ~600 倍余量。该差只经 round() 进 cov_s(整型吸收)与 avg 分母
#:   (z 桶 rate=0 分子恒 0)。
#: - 实施期实测发现(强于上界): 生产 epoch(ts ~ 1.78e9, binade [2^30, 2^31))下全部
#:   ts 共享 2^-22 栅格, 而桶内 cov < 2^12 => ULP(cov) >= 2^-41 是 2^-22 的整分格 ——
#:   归纳可证 fold.cov 恒为 2^-41 的倍数且 z 分段差(2^-22 的倍数)逐步相加恒精确,
#:   闭合式与逐槽的 cov **恒逐位相等**(随机 dt 语料与 4000 例混排块压力实测 0 差;
#:   2026 语料两族对拍 cov 全逐位)。容差仅作契约面保留: 该论证依赖 epoch binade 与
#:   桶宽的数量关系(极小人工 epoch 且桶 cov 跨 2^10 binade 时理论上可出现真 ULP 差),
#:   不改断言层级。
COV_ULP_TOL = 1e-6


def assert_folds_field_equivalent(ref_fold, b2_fold, ctx: str = "", cov_bitwise: bool = False) -> None:
    """HourFold 内部字段分级断言(B2 FP 纪律, plan 26-11-21-1546 S1 第 4 点; 每类豁免
    论证一句):

    - 必须逐位: dl_wsum/up_wsum —— z 信用每笔 merge 加的是 rate(0) x dt = +0.0,
      x + 0.0 = x 精确(非负 float 无 -0 反例), r 信用之间的求和序两路不变;
      dl_max/up_max —— z rate 恒 0 与 max 比较无观测(速率非负), 桶首笔基线信用两路
      是同一笔(区间序列同位); dl_total/up_total —— 末笔快照 = 桶内最后一个正长度
      区间的 ramp 元素/r 冻结值(整数), 逐槽路径的零长度塌缩区间本就不产 merge。
    - ULP 免责: cov —— 论证见 COV_ULP_TOL 注(闭合式端点差一次精确减法 vs 逐槽精确
      分段差 FP 累加, 差 <= ~1.6e-9)。cov_bitwise=True(精确栅格语料, 槽位链全程 FP
      精确: 整数 + 1.5k 在 [2^30, 2^31) binade 均可精确表示)时断言逐位。
    - 结构豁免: credits(merge 笔数, 桶级合并后变少)—— 仅 ==0 判空消费(HourFold
      消费面单点), 不进任何聚合输出; D2「样本列表粒度允许不同」的同款口径。
    """
    tag = f"[{ctx}] " if ctx else ""
    assert b2_fold.dl_wsum == ref_fold.dl_wsum, (f"{tag}dl_wsum 不等(必须逐位): {ref_fold.dl_wsum!r} vs {b2_fold.dl_wsum!r}")
    assert b2_fold.up_wsum == ref_fold.up_wsum, (f"{tag}up_wsum 不等(必须逐位): {ref_fold.up_wsum!r} vs {b2_fold.up_wsum!r}")
    assert (b2_fold.dl_max, b2_fold.up_max) == (ref_fold.dl_max, ref_fold.up_max), (
        f"{tag}max 不等(必须逐位): ({ref_fold.dl_max}, {ref_fold.up_max}) vs "
        f"({b2_fold.dl_max}, {b2_fold.up_max})"
    )
    assert (b2_fold.dl_total, b2_fold.up_total) == (ref_fold.dl_total, ref_fold.up_total), (
        f"{tag}totals 末笔不等(必须逐位): ({ref_fold.dl_total}, {ref_fold.up_total}) vs "
        f"({b2_fold.dl_total}, {b2_fold.up_total})"
    )
    if cov_bitwise:
        assert b2_fold.cov == ref_fold.cov, f"{tag}cov 不等(精确栅格应逐位): {ref_fold.cov!r} vs {b2_fold.cov!r}"
    else:
        assert abs(b2_fold.cov -
                   ref_fold.cov) <= COV_ULP_TOL, (f"{tag}cov 超 ULP 免责容差: {ref_fold.cov!r} vs {b2_fold.cov!r}")


def assert_b1_bitwise_equivalent(
    ref_samples: dict,
    ref_tail,
    b1_samples: dict,
    b1_tail,
    now: float,
    ctx: str = "",
    cov_bitwise: bool = False
) -> tuple:
    """对拍断言(D2 口径 + B2 FP 分级, 随机语料 harness 的核心): hour 桶集相等 / fold
    内部字段分级(assert_folds_field_equivalent)/ seal 行 bitwise(AggRow 等值 +
    format_agg_row 文本逐位)/ 开放 pending 桶集 + 字段分级 + pending seal 行 bitwise
    (D2「pending 经聚合后相等」)/ 跨文件 tail 上下文逐位。返回 (rows, pending) 供
    调用方追加断言。"""
    tag = f"[{ctx}] " if ctx else ""
    assert set(b1_samples) == set(ref_samples), f"{tag}开放小时键集不等: {set(ref_samples) ^ set(b1_samples)}"
    for h in sorted(ref_samples):
        assert_folds_field_equivalent(
            ref_samples[h], b1_samples[h], ctx=f"{ctx} h={h}" if ctx else f"h={h}", cov_bitwise=cov_bitwise
        )
    assert b1_tail == ref_tail, f"{tag}跨文件 tail 上下文不等: {ref_tail!r} vs {b1_tail!r}"
    ref_rows, ref_pending = split_rows_pending(ref_samples, now)
    b1_rows, b1_pending = split_rows_pending(b1_samples, now)
    assert b1_rows == ref_rows, f"{tag}seal 行序列不等"
    assert [format_agg_row(r) for r in b1_rows] == [format_agg_row(r) for r in ref_rows], f"{tag}agg 行文本不等"
    assert set(b1_pending) == set(ref_pending), f"{tag}pending 桶集不等: {set(ref_pending) ^ set(b1_pending)}"
    for h in sorted(ref_pending):
        assert_folds_field_equivalent(
            ref_pending[h],
            b1_pending[h],
            ctx=f"{ctx} pending h={h}" if ctx else f"pending h={h}",
            cov_bitwise=cov_bitwise
        )
        assert b1_pending[h].seal(h) == ref_pending[h].seal(h), f"{tag}pending seal 行不等: {h}"
    return ref_rows, ref_pending
