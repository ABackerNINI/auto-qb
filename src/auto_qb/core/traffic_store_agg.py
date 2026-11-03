"""traffic_store 拆分件: agg 行聚合计算(R5 move-only, 计划 26-11-02-2342 §07)。"""
from .traffic_store_codec import AggRow
from .traffic_store_common import DRIFT_TOL_MS, HOUR_SECONDS, V4_ROLLUP_KINDS
from .traffic_store_paths import v4_month_epoch


def v4_hour_agg(hour_epoch: int, samples: tuple) -> AggRow:
    """hour 聚合行(dt 加权, §04.1): avg = round(Σ(rate_i x dt_i) / cov_s),
    cov_s = min(Σdt_i, HOUR_SECONDS) 且下限 1; max 取逐记录最大; totals 取级末快照(末记录);
    cov_s = 0(无有效覆盖)或空 samples -> ValueError(hour 行只在有覆盖时产出, 调用方
    义务)。dt_i 恒等于 interval_s 时严格退化为现行 _aggregate_bucket 纯活跃桶公式
    (avg = round(Σrate/n)) —— 测试对照钉住。
    !与 v4_rollup_agg 同构双实现(加权量不同: 本函数 dt 加权 vs 逐级 cov 加权),
    issue 26-10-11-0207 R07/R10 登记不急合 —— 合并需先统一加权量语义。

    cov_s 下限 1(§04.1 不变量「行存在即有覆盖」): 小时已封口后迟到的补记会重建该桶并
    重封, 此时桶内只有跨小时界的亚秒残余覆盖(2026-10-13 真机实测 0.263s), round 把它
    折成 0 —— 该 hour 行 cov_s = 0 让 day 封口的 v4_rollup_agg 失掉 Σcov_s > 0 前置
    条件, 抛「逐级聚合无有效覆盖」; 该异常在落盘前抛出, 于是每轮 flush 复现且整批 agg
    行丢弃。avg 仍按 float cov 加权, 只对落盘/上卷的度量取下限, 亚秒桶偏差 <= 1s(与
    round 自身 ±0.5s 同阶)。"""
    if not samples:
        raise ValueError("hour 聚合无样本")
    cov = min(sum(s.dt_s for s in samples), float(HOUR_SECONDS))
    if cov <= 0:
        raise ValueError("hour 聚合无有效覆盖")
    last = samples[-1]
    return AggRow(
        kind="hour",
        epoch=hour_epoch,
        dl_avg=int(round(sum(s.dl_rate * s.dt_s for s in samples) / cov)),
        dl_max=max(s.dl_rate for s in samples),
        up_avg=int(round(sum(s.up_rate * s.dt_s for s in samples) / cov)),
        up_max=max(s.up_rate for s in samples),
        dl_total=int(last.dl_total),
        up_total=int(last.up_total),
        cov_s=max(1, int(round(cov))),  # 下限 1: 行存在即有覆盖(亚秒残余桶不得折 0, 见 docstring)
    )


def v4_rollup_agg(kind: str, epoch: int, children: tuple) -> AggRow:
    """逐级派生聚合行(§04.1, 严格逐级 —— day 只从 hour 行聚, month 只从 day 行聚,
    day 不从 raw 直聚: raw_window 裁剪边缘的 cov_s 链只在逐级传递才完整):
    avg = round(Σ(下级.avg x 下级.cov) / Σcov), max = max(下级.max), totals = 级末快照
    (epoch 最大的下级行), cov = Σ下级.cov。kind 限 {"day","month"}(hour 由 v4_hour_agg
    从记录直聚); children 空或 Σcov <= 0 -> ValueError。
    Σcov > 0 由生产者保证(hour 下级 cov_s 下限 1 见 v4_hour_agg; 本级 cov_s = int(Σcov)
    且每个下级 >= 1), 此处只做断言式 fail-fast —— 给 hour 行放宽 cov_s 下限前先想清楚
    day/month 两侧。
    !与 v4_hour_agg 同构双实现(加权量不同: 逐级 cov 加权 vs dt 加权), 两处互指;
    issue 26-10-11-0207 R07/R10 登记不急合。"""
    if kind not in V4_ROLLUP_KINDS:
        raise ValueError(f"非法逐级聚合行型(须 day/month): {kind!r}")
    if not children:
        raise ValueError("逐级聚合无下级行")
    cov = sum(c.cov_s for c in children)
    if cov <= 0:
        raise ValueError("逐级聚合无有效覆盖")
    last = max(children, key=lambda c: c.epoch)
    return AggRow(
        kind=kind,
        epoch=epoch,
        dl_avg=int(round(sum(c.dl_avg * c.cov_s for c in children) / cov)),
        dl_max=max(c.dl_max for c in children),
        up_avg=int(round(sum(c.up_avg * c.cov_s for c in children) / cov)),
        up_max=max(c.up_max for c in children),
        dl_total=int(last.dl_total),
        up_total=int(last.up_total),
        cov_s=int(cov),
    )


def v4_merge_agg(prev: AggRow, row: AggRow) -> AggRow:
    """同 epoch 重封合流(§04.1/§04.2): 已封桶被**迟到的补记**重建后再次封口时, 把新行
    并入原行 —— avg 按各自 cov 加权 / max 取大 / totals 取后封行(时刻更晚的快照) /
    cov = 两者之和(截到行型桶宽)。

    为什么是「合流」而不是「替换」(2026-10-13 真机取证): 在线侧桶被封口时 `pending.pop(h)`
    就弹走了, 之后到达的信用只能重建一个**只含残余**的桶 —— 原行记的是「先到的那部分覆盖」,
    新行记的是「后到的残余」, 二者信用区间互斥(游标区间每次只消费一次)故 cov 相加才是该桶
    的真覆盖。长空闲 z 游程可延迟到 ZRUN_FLUSH_S(24h)才封口, 于是残余可以很大(真机每个小时
    两行、日行 cov_s 只留残余: 44712 vs 全量 86400 —— 约一半覆盖被「替换」吃掉)。
    「替换」只对**完整重算**成立: 重启 catch-up 从天文件重算出整小时, 走的是
    `_catch_up_level`(按 epoch 取最后一行), 不经本函数 —— 那条路不需要也不该合流(会重复计)。
    桶宽上限: hour 3600 / day 86400 / month 当月秒数(合流只补齐缺口, 上限防重复计)。"""
    if prev.kind != row.kind or prev.epoch != row.epoch:
        raise ValueError(f"合流要求同 kind 同 epoch: {prev.kind}/{prev.epoch} vs {row.kind}/{row.epoch}")
    cov = prev.cov_s + row.cov_s
    if cov <= 0:
        # fail-closed 同 v4_rollup_agg: 双行 cov 全零时下面的加权除法是除零(Web 线程炸)。
        # 解析侧 cov_s >= 1(issue 26-10-30-0622)后正常输入到不了这里 —— 断言式守卫,
        # 语义非法行在解析处就按坏行拦下
        raise ValueError("合流无有效覆盖")
    merged = min(cov, _agg_width_s(prev))
    return AggRow(
        kind=prev.kind,
        epoch=prev.epoch,
        dl_avg=int(round((prev.dl_avg * prev.cov_s + row.dl_avg * row.cov_s) / cov)),
        dl_max=max(prev.dl_max, row.dl_max),
        up_avg=int(round((prev.up_avg * prev.cov_s + row.up_avg * row.cov_s) / cov)),
        up_max=max(prev.up_max, row.up_max),
        dl_total=int(row.dl_total),  # 后封行 = 时刻更晚的累计快照
        up_total=int(row.up_total),
        cov_s=int(merged),
    )


def _agg_width_s(row: AggRow) -> int:
    """行型桶宽秒(同 epoch 合流的 cov 上限): hour 3600 / day 86400 / month 当月秒数。
    day 用固定 86400(不拿 epoch 差实算 —— 夏令时下「下一本地午夜」可能落在同日而算出 0 宽,
    反把覆盖裁光); month 按「32 天后的月界」实算(跨度 32 天必然落进下一月), 并保底 28 天。"""
    if row.kind == "hour":
        return HOUR_SECONDS
    if row.kind == "day":
        return 86400
    return max(v4_month_epoch(row.epoch + 32 * 86400) - row.epoch, 28 * 86400)


def v4_block_gap_continuous(prev_end_ts: float, next_block_start: float, interval_s: float) -> bool:
    """跨块覆盖结算判定单点(v4 计划 §01「覆盖结算」定约; 纯函数)

    gap = 新块首槽(B.start, 即新块 B 行起点) - 上一块末槽; gap <= interval_s + DRIFT_TOL
    (250ms) -> 连续 —— 调用方按上一记录速率把 [上一块末槽, 新块首槽) 结算进覆盖信用;
    否则真空(崩溃保护内核不动 —— 崩溃窗口/停机间隙不虚记覆盖)。interval_s 取新块的
    B 行采样间隔(间隙由新块节拍产出; 改间隔场景按新档判定)。gap <= 0(病态重叠)按
    连续判定, 结算区间为空调用方自然无操作。在线 _agg_feed 与离线 _agg_credit_day_file
    两路必须复用本函数(镜像保证靠同源保持) —— 顺带消除现行块首清零信用在 00:00 边界
    每天约 2s 的既有覆盖损失。
    """
    return (next_block_start - prev_end_ts) <= interval_s + DRIFT_TOL_MS / 1000.0
