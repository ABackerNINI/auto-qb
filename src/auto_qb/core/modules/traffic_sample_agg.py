"""traffic_sample_mod 拆分件: 聚合域 mixin(R5 move-only, 计划 26-11-02-2342 §07)。

方法体里对类级静态方法的引用写成 `_SampleAggMixin.`(搬出根模块后 `TrafficSampleModule`
不再可见; 同一函数对象, 语义不变)。根模块以同名 logger 记录, 日志名仍为
`auto_qb.core.modules.traffic_sample_mod`。
"""
import logging
import time
from typing import Any, Callable, List, Optional, Tuple

from ..traffic_store import (
    HOUR_SECONDS,
    TrafficV4Store,
    V4HourSample,
    V4NullRun,
    V4ParsedDay,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    v4_block_agg_totals,
    v4_block_gap_continuous,
    v4_block_slots,
    v4_day_epoch,
    v4_hour_agg,
    v4_merge_agg,
    v4_month_epoch,
    v4_rollup_agg,
    v4_z_totals_ramp,
)

from .traffic_sample_common import EVICT_CHECK_INTERVAL_S, OpenRun, SeriesAgg, _hour_spans, _record_slots

logger = logging.getLogger("auto_qb.core.modules.traffic_sample_mod")


def _open_run_hour_samples(agg: "SeriesAgg", run: Optional[OpenRun]) -> dict:
    """开放游程 + 未结算信用 -> hour 桶样本(活尾合成, plan 26-10-29-0231 §03; 模块级纯函数)。

    为什么需要它: agg 记账只在记录落盘时发生(_agg_feed <- _append_record), 而 z 游程
    只在**封口**时成记录(非零样本 / 换型 / 00:00 硬切 / stop / 天级保险闸)—— 空闲期
    agg.pending 恒空、open_credit 悬着未结算, 于是 3d/7d/30d(hour)与 6mo/1y/all(逐级
    继承)的图尾从最后一个封口点起到 now 全是 null, 前端渲染成「无采样」。跨天后尤甚:
    00:00 把前一日整段封口补记成行(昨日 0 线是对的), 同时新游程从 00:00 起再不封口
    —— 用户报的「0 值区显示无采样, 特别是跨天后」正是这一段。

    口径与封口路径逐字同源(复用同一批纯函数, 不写第二份聚合逻辑):
    - (1) credit 段 [open_credit 槽位, 游程首槽): 按上一记录速率 —— 即 _agg_feed 在
      下一记录到达时结算的同一区间。**无开放游程时不出任何样本**(见函数体注释: 把信用
      推到 now 会在「系列已不再被采样」的退化形态下凭空造覆盖)。
    - (2) 游程内(z 型): 速率恒 0, totals 按 v4_z_totals_ramp 逐段摊配到**末端锚点**
      (run.last_dl_total/last_up_total = 封口时 _resolve_run_end 用的同一个值)。不取
      开启快照: 读侧 v4_merge_agg 取「后封行」totals, 合成行带更早快照会让累计链回退
      (计划 §01 不变量 2)。
    - (3) 末端取 run.last_seen, **不推到 now**: 采样停摆时不能凭空造覆盖(裁定 D2)。
    - (4) n 游程(断连)只出 (1), 之后留 null —— 断连不可归因为 0(裁定 D3)。

    每段恰 1 条 V4HourSample(O(小时数), 不是 O(槽数)): 段内速率与 totals 恒定,
    v4_hour_agg 的 dt 加权与「级末快照 = 末记录」在等值样本下与逐槽展开等价。
    返回 {hour_epoch: [V4HourSample, ...]}; 调用方并入 pending 副本(不与累计器共享容器)。
    """
    out: dict = {}
    credit = agg.open_credit
    if credit is None:
        return out  # 无观测信用(null 期后): 不猜
    if run is None:
        # 无开放游程 = 没有「仍在采样」的证据: 不把信用推到 now。健康形态下 credit 槽位
        # 就是本轮刚落的记录(now - 槽位 ~ 毫秒, 补不补都一样); 而**退化形态**(种子已从 qB
        # 消失 / 系列不再被采样, 最后一条是非零 r 记录)若照推, 会按旧速率凭空造出整段
        # 非零覆盖 —— 与「不猜」冲突。信用的前向结算留给下一条记录(封口路径本职)。
        return out
    _SampleAggMixin._agg_credit_hours(out, credit[0], run.start, credit[1], credit[2], credit[3], credit[4])
    if run.kind != "z":
        return out  # n 游程: 断连不可归因, run.start 之后留 null
    spans = _hour_spans(run.start, run.last_seen)
    # 摊配粒度 = 小时段数(不是槽数): n == 1 时 v4_z_totals_ramp 的「单槽跨度退化取开启
    # 快照」规则不适用(一段 = 整条游程, 末端就是末端锚点) —— 传 2 再只取末元。
    ramp = v4_z_totals_ramp(run.dl_total, run.up_total, run.last_dl_total, run.last_up_total, max(len(spans), 2))
    if len(spans) == 1:
        ramp = ramp[-1:]
    for (seg_start, seg_end), (dl_total, up_total) in zip(spans, ramp):
        _SampleAggMixin._agg_credit_hours(out, seg_start, seg_end, 0, 0, dl_total, up_total)
    return out


def _pending_agg_rows(agg: "SeriesAgg", run: Optional[OpenRun], now: float) -> tuple:
    """聚合累计器 -> 活尾未封口部分行(S7, 2026-10-14; 模块级纯函数供单测探针)。

    agg.dat 只有**封口**行(hour 完结整小时 / day 完结本地日 / month 完结自然月才
    append), 未封口的当前桶只活在写侧累计器 —— 不发布则 3d/7d/30d(hour)/6mo/1y(day)/
    all(month)视图图尾停在最后一个封口桶(用户报「3 天及以上视图有真空: 只显示到
    14 日 0 点, 实际已到 1 点」的根因)。本函数把累计器里的当前桶部分聚合成 AggRow
    发布到活尾快照(LiveTail.pending_agg), 读侧按 epoch 与磁盘封口行合流。

    活尾合成段(plan 26-10-29-0231, 用户报「3d 及以上视图 0 值区显示无采样, 特别是跨天
    后」): 累计器只记「已落盘记录」的信用, 空闲游程未封口期间 pending 为空 —— 于是把
    _open_run_hour_samples 的合成段并入 pending 的**副本**(累计器本体不动, 封口路径零
    影响)。合成段与已结算样本同桶时按时间序追加在后, v4_hour_agg 的「级末快照 = 末
    记录」因此拿到更晚的 totals。

    口径与写侧封口同源(三层各自当前桶):
    - hour: pending 各桶逐桶 v4_hour_agg(dt 加权); 含「已完成未 flush」的桶(flush
      时点未到)与开放当前小时; 已封桶的迟到补记残余也在 pending(写侧重封时
      _agg_merge_prev 合流, 读侧同样按 v4_merge_agg 合流, 两端口径一致);
    - day: 开放日累计器(当日已封 hour 行)+ 当日 pending 部分行 -> v4_rollup_agg;
      开放日 = agg.day_epoch(无封口小时时回落今日);
    - month: 开放月累计器(当月已封 day 行)+ 当月 day 部分行 -> v4_rollup_agg;
      开放月 = agg.month_epoch(无封口日时回落本月)。
    跨桶边界(暂停跨日/月恢复)按 epoch 归属过滤, 旧桶残余不并进新桶行。无样本/无
    有效覆盖的层级不出行(v4_hour_agg / v4_rollup_agg 的 ValueError 逐一跳过 ——
    空桶 = null 语义, 与封口路径同)。day/month 两级的本地日界/月界换算对**人工
    时钟**(测试把模块 time 钉在 1970 附近)在 Windows 上换出负 epoch -> OSError,
    按「该级不出行」处理(生产时钟恒为正不受影响; 纯增益面, 缺该级只回到修复前
    的形态)。
    """
    rows: list = []
    hour_partials: list = []
    # 副本: 合成段只进副本, 累计器本体不动(封口路径零影响; 同桶样本按时间序追加在后)
    pending = {h: list(samples) for h, samples in agg.pending.items()}
    for h, samples in _open_run_hour_samples(agg, run).items():
        pending.setdefault(h, []).extend(samples)
    for h in sorted(pending):
        samples = pending[h]
        if not samples:
            continue  # 空桶不留(全 null 覆盖的小时不产行, 与 _agg_flush_series 同)
        try:
            hour_partials.append(v4_hour_agg(h, tuple(samples)))
        except ValueError:
            continue  # 无有效覆盖: 不出行(桶 = null)
    rows.extend(hour_partials)
    try:
        day_epoch = agg.day_epoch if agg.day_epoch is not None else v4_day_epoch(now)
        # 合成段可能把「今日小时」带进 pending, 而 agg.day_epoch 仍停在前一日(00:00 后尚未
        # 有封口小时行入库): 开放日按子行里最晚的那天走, 前一日已封口小时不并进新日行
        for r in hour_partials:
            e = v4_day_epoch(r.epoch)
            if e > day_epoch:
                day_epoch = e
        day_children = list(agg.day_hours) if day_epoch == agg.day_epoch else []
        day_children += [r for r in hour_partials if v4_day_epoch(r.epoch) == day_epoch]
        if day_children:
            rows.append(v4_rollup_agg("day", day_epoch, tuple(day_children)))
    except (ValueError, OSError, OverflowError):
        pass  # 无有效覆盖 / 人工时钟的本地界换算失败: 该级不出行(见 docstring)
    try:
        month_epoch = agg.month_epoch if agg.month_epoch is not None else v4_month_epoch(now)
        month_children = list(agg.month_days
                             ) + [r for r in rows if r.kind == "day" and v4_month_epoch(r.epoch) == month_epoch]
        if month_children:
            rows.append(v4_rollup_agg("month", month_epoch, tuple(month_children)))
    except (ValueError, OSError, OverflowError):
        pass  # 同上
    return tuple(rows)


class _SampleAggMixin:
    # ---------- 聚合分层与恢复(S2b, §04) ----------

    def _agg_state(self, key: str) -> SeriesAgg:
        """单系列聚合累计器(lazily 建; 纯内存结构, dry_run 照常推进)"""
        agg = self._agg_states.get(key)
        if agg is None:
            agg = self._agg_states[key] = SeriesAgg()
        return agg

    def _agg_feed(
        self, key: str, rec: V4Sample | V4ZeroRun | V4NullRun, anchor: float, cursor: float, block_head: bool,
        interval_s: float
    ) -> None:
        """聚合累计器逐记录入账(§4.1): 前向记账 —— 本记录到达时结算上一非 null 槽的
        前向覆盖 [信用槽位, 本记录首槽), 再入账本记录内部的游程槽区间(z 恒 0/n 不记),
        信用移到本记录末槽。槽位序列与落盘 dt 链同一游标推进结果(严格同源)。

        跨块覆盖结算(v4 计划 §01「覆盖结算」, 本棒起取代「块首清零信用」): 块首记录
        到达时不再无条件丢弃信用, 而经判定单点 v4_block_gap_continuous 结算 —— gap =
        本块首槽(B.start) - 上一块末槽(credit[0]), gap <= interval_s + DRIFT_TOL(250ms)
        -> 连续, 按上一记录速率把 [末槽, 首槽) 结算进信用; 否则真空(崩溃保护内核不动,
        不虚记覆盖)。与离线 _agg_credit_day_file 两路复用同一判定函数(镜像保证靠同源
        保持), 顺带消除现行 00:00 边界每天约 2s 的既有覆盖损失。"""
        agg = self._agg_state(key)
        credit = agg.open_credit
        slots = _record_slots(rec, anchor, cursor, block_head)
        if credit is not None and slots:
            if not block_head or v4_block_gap_continuous(credit[0], slots[0], interval_s):
                self._agg_credit_hours(agg.pending, credit[0], slots[0], credit[1], credit[2], credit[3], credit[4])
        if isinstance(rec, V4ZeroRun):
            # 游程内部槽区间: 速率恒 0; totals 按「开启快照 -> 末端快照」逐槽线性摊配
            # (形态 D, plan 26-10-16-1509 §04: 与离线 _agg_credit_day_file 共用同一纯函数;
            # 无末端列/末端低于开启 = 显式退化 -> 恒快照 = 旧语义)
            ramp = v4_z_totals_ramp(rec.dl_total, rec.up_total, rec.dl_total_end, rec.up_total_end, len(slots))
            for k in range(len(slots) - 1):
                self._agg_credit_hours(agg.pending, slots[k], slots[k + 1], 0, 0, ramp[k][0], ramp[k][1])
        if isinstance(rec, V4Sample):
            agg.open_credit = (float(cursor), rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total)
        elif isinstance(rec, V4ZeroRun):
            # 游程尾部信用 = 末端摊配值(ramp[-1] = v_{n-1} = 末端快照; 退化时 = 开启快照)
            agg.open_credit = (float(cursor), 0, 0, ramp[-1][0], ramp[-1][1])
        else:
            agg.open_credit = None  # n 游程: null 期无观测, 信用清空(其后区间不记)

    @staticmethod
    def _agg_credit_hours(
        pending: dict, start: float, end: float, dl: int, up: int, dl_total: int, up_total: int
    ) -> None:
        """区间 [start, end) 按小时界拆分入账(V4HourSample, dt = 桶内覆盖秒); 在线记账
        与恢复离线记账共用(离线传局部 dict)。末槽的信用区间跨小时界时自然拆分,
        hour 桶 cov 上界 3600 由 v4_hour_agg 收口。"""
        if end <= start:
            return
        cur = start
        while cur < end:
            h = int(cur) // HOUR_SECONDS * HOUR_SECONDS
            seg = min(end, h + HOUR_SECONDS) - cur
            pending.setdefault(h, []).append(V4HourSample(dl, up, dl_total, up_total, seg))
            cur += seg

    def _agg_flush_all(self, now: float) -> None:
        """全系列聚合封口(§4.2 flush 时点; stop() 复用 —— 未完结层级留累计器, 重启经
        catch-up 重建, 零丢失)。

        逐系列隔离(2026-10-13 真机取证): 单系列封口抛错只该影响该系列。此前异常一路上抛到
        handler, 于是 ①其余系列本轮也不封口 ②`_agg_append` 永不执行 = 全系列 agg 静默停写
        ③抛点在状态复位之前, 同一错每轮 flush 复现 —— 真机上一个系列抛「逐级聚合无有效
        覆盖」, 全系列小时行一个多小时没落盘。现在逐系列 catch + 善后(见
        _agg_reset_after_error), 单系列的问题不再放大成全局停写。"""
        for key in list(self._agg_states):
            try:
                self._agg_flush_series(key, now)
            except Exception as e:  # noqa: BLE001 —— 逐系列隔离即本函数职责(见 docstring)
                self._agg_reset_after_error(key, e)
            else:
                self._agg_warned.discard(key)  # 恢复健康: 下次再错重新告警一次

    def _agg_reset_after_error(self, key: str, err: Exception) -> None:
        """单系列封口失败善后(见 _agg_flush_all): 告警(同系列恢复前只一次, 免 6 次/分钟刷屏)
        + **重置该系列聚合累计器**。为什么重置: 抛点位于「本批行 append 之前」, 累计器里
        已封未落盘的行再也送不出去, 不重置就会每轮 flush 重抛同一错(真机复现)。重置后
        后续小时照常封口; 缺的那段由下次重启的 catch-up 从天文件重算补回(与「崩溃窗口丢
        缓冲 = 真空」同一诚实口径: 不猜、不静默 —— 告警行写明缺口出处)。"""
        if key not in self._agg_warned:
            self._agg_warned.add(key)
            logger.error(
                f"流量采样 | {key} 聚合封口失败(该系列聚合累计器已重置, 后续小时照常封口; "
                f"本段缺口待下次重启 catch-up 从天文件重算补回): {type(err).__name__}: {err}"
            )
        self._agg_states.pop(key, None)

    def _agg_flush_series(self, key: str, now: float) -> bool:
        """单系列聚合封口(§4.2): 完结整小时 -> hour 行 -> 完结本地日 -> day 行 ->
        完结自然月 -> month 行, 顺序检查; 产出行合并一批 append(每系列每 flush 至多
        +1 次 open)。dry_run / data_dir 空: 封口内存照常推进, 写静默跳过。hour 封口
        时点 piggyback 裁剪检查(§4.5)。返回是否实际写了 agg 文件(测试用)。"""
        agg = self._agg_states.get(key)
        if agg is None:
            return False
        rows: List[Any] = []  # AggRow 行; 写成 Any 规避 _agg_ingest_* 形参 List[V4HourSample] 的既有型差(递减面)
        for h in sorted(agg.pending):
            if h + HOUR_SECONDS > now:
                break  # 首个未完结小时即止(pending 按序, 之后只会更晚)
            samples = agg.pending.pop(h)
            if not samples:
                continue  # 空桶不留(全 null 覆盖的小时不产行, 空桶 = null)
            self._agg_ingest_hour(agg, v4_hour_agg(h, tuple(samples)), rows)
        if agg.day_epoch is not None and agg.day_hours and v4_day_epoch(now) > agg.day_epoch:
            self._agg_ingest_day(agg, v4_rollup_agg("day", agg.day_epoch, tuple(agg.day_hours)), rows)
            agg.day_epoch, agg.day_hours = None, []
        if agg.month_epoch is not None and agg.month_days and v4_month_epoch(now) > agg.month_epoch:
            rows.append(v4_rollup_agg("month", agg.month_epoch, tuple(agg.month_days)))
            agg.month_epoch, agg.month_days = None, []
        wrote = self._agg_append(key, tuple(rows))
        conf = self._ctx.config.qb_traffic
        if conf is not None and any(r.kind == "hour" for r in rows):
            self._agg_trim(key, agg, now, conf.rollup_window)  # piggyback hour 封口时点
        return wrote

    @staticmethod
    def _ingest_acc(
        row: V4HourSample,
        cur_epoch: Optional[int],
        cur_rows: List[V4HourSample],
        bucket_epoch_of: Callable[[int], int],
        cascade: Callable[[int, List[V4HourSample]], None],
    ) -> tuple:
        """聚合累计器并入骨架单点(issue 26-10-11-0207 R10): hour/day 两级同构 —— 首桶开
        累计器 / 同桶追加(同 epoch 重封替换, 传入行已由 _agg_merge_prev 合流过) / 翻桶先
        级联封口(cascade)再开新累计器。返回 (new_epoch, new_rows); 本行落批
        (rows_out.append)与 hour 的 earliest_hour 判据由调用方自理。"""
        e = bucket_epoch_of(row.epoch)
        if cur_epoch is None:
            return e, [row]
        if e == cur_epoch:
            rows = [h if h.epoch != row.epoch else row for h in cur_rows]
            if all(h.epoch != row.epoch for h in rows):
                rows.append(row)
            return cur_epoch, rows
        cascade(cur_epoch, cur_rows)
        return e, [row]

    @staticmethod
    def _agg_merge_prev(
        row: V4HourSample,
        cur_epoch: Optional[int],
        cur_rows: List[V4HourSample],
        bucket_epoch_of: Callable[[int], int],
    ) -> V4HourSample:
        """同桶重封的入库行(§04.2): 该 epoch 已在累计器里(小时封口后被迟到的补记重建又再
        封一次)时, 返回与已封行的**合流行**(v4_merge_agg), 否则原样返回本行。落批的必须是
        这个返回值 —— 解析按「同 epoch 取最后一行」, 落残余行等于读侧也只看到残余
        (2026-10-13 真机: 日行 cov_s 只留残余 44712 vs 全量 86400)。"""
        if cur_epoch is None or bucket_epoch_of(row.epoch) != cur_epoch:
            return row
        for h in cur_rows:
            if h.epoch == row.epoch:
                return v4_merge_agg(h, row)
        return row

    @staticmethod
    def _agg_ingest_hour(agg: SeriesAgg, row: V4HourSample, rows_out: List[V4HourSample]) -> None:
        """完结 hour 行落批 + 并入 day 累计器(严格逐级): 入库行(首封或与已封行合流的重封行)
        随本批落盘(§4.2 完结整小时 append hour 行; 同 epoch 重封 = 追加**合流行**, 解析取
        最后一行 —— 落批必须是合流行, 否则读侧末行仍是残余); 同日追加; 同 epoch 重封与
        累计器旧行合流(v4_merge_agg); 翻日(暂停恢复跨多小时滞留)先级联封前一日再开新累计器。
        顺带维护 earliest_hour 裁剪判据(§4.5): 运行期才开始产数据的系列(全新安装 global /
        新种子 / 热重载启用)不经 _recover_series, 判据只能在此初始化 + min 更新, 否则
        _agg_trim 恒早退、agg.dat 无界增长(26-10-06-0028 C-01)。"""
        stored = _SampleAggMixin._agg_merge_prev(row, agg.day_epoch, agg.day_hours, v4_day_epoch)
        rows_out.append(stored)
        if agg.earliest_hour is None or row.epoch < agg.earliest_hour:
            agg.earliest_hour = row.epoch

        def cascade(close_epoch: int, close_rows: List[V4HourSample]) -> None:
            # 前一日随本行翻日封口(其末 hour 已过, 前一日必已完结)
            _SampleAggMixin._agg_ingest_day(agg, v4_rollup_agg("day", close_epoch, tuple(close_rows)), rows_out)

        agg.day_epoch, agg.day_hours = _SampleAggMixin._ingest_acc(
            stored, agg.day_epoch, agg.day_hours, v4_day_epoch, cascade
        )

    @staticmethod
    def _agg_ingest_day(agg: SeriesAgg, row: V4HourSample, rows_out: List[V4HourSample]) -> None:
        """完结 day 行落批 + 并入 month 累计器(严格逐级): 入库行(首封, 或与已封行合流的
        重封行)随本批落盘(§4.2 完结本地日 append day 行; 同 epoch 重封 = 追加合流行); 同月
        追加 / 同 epoch 合流 / 翻月级联封前一月(语义同 _agg_ingest_hour)。"""
        stored = _SampleAggMixin._agg_merge_prev(row, agg.month_epoch, agg.month_days, v4_month_epoch)
        rows_out.append(stored)

        def cascade(close_epoch: int, close_rows: List[V4HourSample]) -> None:
            rows_out.append(v4_rollup_agg("month", close_epoch, tuple(close_rows)))

        agg.month_epoch, agg.month_days = _SampleAggMixin._ingest_acc(
            stored, agg.month_epoch, agg.month_days, v4_month_epoch, cascade
        )

    def _agg_append(self, key: str, rows: tuple) -> bool:
        """聚合行批量落盘(同款追加纪律, dry_run 静默跳过): OSError 按落盘失败口径
        告警不上抛(连续失败只告警一次, 与天文件共用记忆) —— 行随累计器丢失, 重启经
        catch-up 从天文件/agg 尾重建补算(幂等)。"""
        if not rows:
            return False
        if not self._persistence_on or not self._ctx.config.data_dir:
            return False  # dry_run: 封口内存照常推进, 写静默跳过
        try:
            self._get_v4_store().append_agg_rows(key, rows)
            self._persist_warned = False
            return True
        except OSError as e:
            if self._persist_warned:
                logger.debug(f"流量采样 | {key} agg 行落盘失败(持续): {e}")
            else:
                logger.warning(f"流量采样 | {key} agg 行落盘失败(本批聚合行丢失, 重启后补算): {e}")
                self._persist_warned = True
            return False

    def _agg_trim(self, key: str, agg: SeriesAgg, now: float, window: float) -> None:
        """hour 行按 rollup_window 裁剪(§4.5): 判据用内存最老行(零常规文件读), 存在
        到龄行才重写(无到龄零写 = same_content 语义); dry_run 静默跳过。"""
        if not self._persistence_on or not self._ctx.config.data_dir:
            return
        if agg.earliest_hour is None or now - agg.earliest_hour <= window:
            return  # 无到龄行(边界含): 不读不写
        try:
            agg.earliest_hour = self._get_v4_store().trim_agg_hours(key, now, window)
        except OSError as e:
            logger.warning(f"流量采样 | {key} agg 裁剪失败(原文件完好, 下轮重试): {e}")

    def _maybe_evict(self, conf: Any, now: float) -> None:
        """种子按龄淘汰(§4.5, flush 时点): 扫描节流至多每 EVICT_CHECK_INTERVAL_S 一次
        (判据口径与触发频率解耦); 淘汰 = 删超龄系列目录, 返回键同步清理该系列全部内存
        缓存(数据门/累计器/基线/镜像/缓冲/游程 —— 防陈旧门缓存复活已删系列)。"""
        if not self._persistence_on or not self._ctx.config.data_dir:
            return  # dry_run: 淘汰写操作静默跳过
        if self._last_evict_check is not None and now - self._last_evict_check < EVICT_CHECK_INTERVAL_S:
            return
        self._last_evict_check = now
        try:
            evicted = self._get_v4_store().evict_expired_series(now, conf.rollup_window)
        except OSError as e:
            logger.warning(f"流量采样 | 种子淘汰扫描失败(下轮重试): {e}")
            return
        for key in evicted:
            self._agg_states.pop(key, None)
            self._has_data.discard(key)
            self._no_data.discard(key)
            self._baselines.pop(key, None)
            self.latest.pop(key, None)
            self._buffers.pop(key, None)
            self._open_runs.pop(key, None)
        if evicted:
            logger.info(f"流量采样 | 按龄淘汰超龄系列目录 {len(evicted)} 个(天文件 + agg.dat)")

    @staticmethod
    def _catch_up_level(
        children: List[V4HourSample], bucket_epoch_of: Callable[[int], int], cur_bucket: int, watermark: Optional[int],
        kind: str
    ) -> tuple:
        """catch-up 逐级补算骨架单点(issue 26-10-11-0207 R10): day/month 两级同构 ——
        子行(存量 + 新补)按桶分组成本级行, 未完结的当前桶重建累计器、水位前已有行不重算
        (前向水位 §4.4)、其余完结桶补算 rollup 行(返回作上一级输入)。累计器字段名两级
        不同, 故 (补算行, 当前桶 epoch, 当前桶子行) 三元组返回由调用方落回 agg。"""
        buckets: dict = {}
        for c in children:
            buckets.setdefault(bucket_epoch_of(c.epoch), []).append(c)
        cur_epoch, cur_rows = None, []
        out = []
        for b in sorted(buckets):
            if b >= cur_bucket:
                cur_epoch, cur_rows = b, list(buckets[b])  # 当前桶累计器(未完结)
                continue
            if watermark is not None and b <= watermark:
                continue  # 已有行: 不重算
            out.append(v4_rollup_agg(kind, b, tuple(buckets[b])))
        return out, cur_epoch, cur_rows

    def _recover_series(self, key: str, store: TrafficV4Store, now: float, window: float) -> dict:
        """单系列恢复(§4.3/§4.4): 扫 agg 文尾 -> 水位(= 文件尾行, 不落内存不重 append)
        + 文件内行重建当日/当月累计器 -> catch-up 逐级补算 append(hour <- 读集内天文件
        raw 逐槽前向记账 / day <- agg 内 hour 行 / month <- day 行) -> 末尾才裁剪(硬序)。

        读集按需(plan 26-10-12-2010 D1): 读集下界 = agg 水位所在日
        [v4_day_epoch(wm_hour), 今日] —— 水位封口小时不读不重算(现判据 h <= wm_hour
        已在过滤), 读集常态 1 个天文件、跨日界至多 2 个, 与 24h 流量图读侧契约同阶;
        rollup_window 只决定保留(D2: 1000000D 永久保留不动), 不决定启动读集。为什么是
        「所在日」而非时刻: series_day_dates 按文件名日期过滤, 传 day(wm_hour) 恰好纳入
        水位当天天文件(水位之后的 raw 必落在该日或更晚文件 —— 天文件 00:00 硬切、块不跨天)。
        agg 无可用水位(wm_hour is None: 缺失/损坏/无 hour 行)时退回 now - window 全量
        兜底(D5: 无可信水位则不可判哪些小时已聚合, 全量重算 + INFO 留痕, 诚实兜底不猜)。
        停机超窗的天文件已删 -> 对应 hour/day 行缺失跳过不标注(图上真空, 与块间 gap 同)。

        返回读集埋点 {"day_dates", "bound", "new_hours", "slots"}(供 _recover_aggregates
        汇总与测试机检读集有界)。"""
        parsed = store.read_agg(key)
        agg = self._agg_state(key)
        agg.earliest_hour = parsed.hours[0].epoch if parsed.hours else None
        wm_hour = parsed.hours[-1].epoch if parsed.hours else None
        wm_day = parsed.days[-1].epoch if parsed.days else None
        wm_month = parsed.months[-1].epoch if parsed.months else None
        today = v4_day_epoch(now)
        cur_month = v4_month_epoch(now)
        # --- hour catch-up: 读集内天文件 raw 逐槽前向记账(与在线记账同一口径);
        # --- 跨天文件末槽上下文接力(00:00 边界连续时条件结算, 缺文件断链) ---
        hour_samples: dict = {}
        day_tail: Optional[tuple] = None
        if wm_hour is not None:
            lower = v4_day_epoch(wm_hour)  # 按需口径: 读集下界 = 水位所在日
            bound = "watermark"
        else:
            lower = now - window  # 兜底(D5): 无可信水位, 退回保留窗全量
            bound = "fallback"
            logger.info(f"流量采样 | {key} agg 无可用水位(缺失/损坏/无 hour 行), "
                        f"读集退回保留窗 now - rollup_window 全量兜底(D5)")
        slot_counts: list = []
        day_dates = store.series_day_dates(key, lower)
        for date in day_dates:
            parsed_day = store.read_day(key, date)
            if parsed_day is not None:
                day_tail = self._agg_credit_day_file(hour_samples, parsed_day, day_tail, slot_counts)
            else:
                day_tail = None  # 缺失文件: 结算上下文断链(其后间隙由 gap 判定兜底真空)
        if len(day_dates) > 2:
            src = f"水位日 {day_dates[0]} 陈旧(聚合持续未落盘?)" if bound == "watermark" else "fallback 保留窗全量"
            logger.info(f"流量采样 | {key} 读集 {len(day_dates)} 天(>2): 下界来源 = {src}(不影响正确性, 正确性由逐小时重算判据保证)")
        new_hours = []
        for h in sorted(hour_samples):
            if wm_hour is not None and h <= wm_hour:
                continue  # 水位之前已有行: 不重算(前向水位, §4.4)
            samples = hour_samples[h]
            if not samples:
                continue
            if h + HOUR_SECONDS <= now:
                new_hours.append(v4_hour_agg(h, tuple(samples)))  # 完结缺失小时 -> 补算行
            else:
                agg.pending[h] = list(samples)  # 开放小时 -> 重建累计器
        # --- 当日/当月累计器从文件内行重建 + day/month catch-up(严格逐级) ---
        new_days, agg.day_epoch, agg.day_hours = self._catch_up_level(
            list(parsed.hours) + new_hours, v4_day_epoch, today, wm_day, "day"
        )
        new_months, agg.month_epoch, agg.month_days = self._catch_up_level(
            list(parsed.days) + new_days, v4_month_epoch, cur_month, wm_month, "month"
        )
        rows = tuple(new_hours + new_days + new_months)
        if rows:
            self._agg_append(key, rows)  # catch-up 补算 append(幂等: 同 epoch 取最后一行)
        self._agg_trim(key, agg, now, window)  # 硬序: catch-up 全部落盘后才裁剪
        return {
            "day_dates": day_dates,
            "bound": bound,
            "new_hours": len(new_hours),
            "slots": sum(slot_counts),
        }

    @staticmethod
    def _slot_agg_obs(slot: V4Slot, agg_totals: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """单槽的 agg 入账观测(离线恢复用, 形态 D 单点): z 槽 = (0, 0, 摊配 dl, 摊配 up)
        (v4_block_agg_totals 的逐槽值 —— 无末端列/单槽游程时 = 开启快照, 与旧语义逐位一致);
        r 槽 = 原 obs(速率 + 冻结 totals); n 槽 = None(null 期不贡献)。"""
        if slot.obs is None:
            return None
        if agg_totals is None:
            return slot.obs
        return (0, 0, agg_totals[0], agg_totals[1])

    @staticmethod
    def _agg_credit_day_file(
        hour_samples: dict,
        parsed_day: V4ParsedDay,
        prev_tail: Optional[tuple] = None,
        slot_counter: Optional[List[int]] = None
    ) -> Optional[tuple]:
        """单天文件逐槽前向记账(恢复离线侧): 逐块展开槽位(块内相邻槽区间 [slot_k,
        slot_k+1) 记 slot_k 的观测 —— r = 其速率 / z = 摊配值(v4_block_agg_totals) / n =
        null 不记), 与在线 _agg_feed 结算区间信用同一口径(槽位两路同源, z 的 agg totals
        两路共用 v4_z_totals_ramp)。

        跨块覆盖结算(v4 计划 §01「覆盖结算」, 与在线路复用判定单点 v4_block_gap_continuous):
        块间(含跨天文件 —— prev_tail 由 _recover_series 传入上一文件末槽上下文)gap =
        下一块首槽 - 上一块末槽, 连续(<= interval + DRIFT_TOL)则按上一槽速率把
        [末槽, 首槽) 结算进覆盖, 崩溃/停机间隙超容差为真空 —— 00:00 边界既有每天约 2s
        覆盖损失就此消除。prev_tail = (末槽 ts, obs) 或 None(无上下文/上文件缺链);
        返回本文件末槽上下文(末槽为 null 观测时 obs = None, 调用方结算侧自然跳过;
        z 末槽的 obs 为摊配末端值 —— 与在线 z 记录的尾部信用同值)。

        slot_counter 非 None(恢复埋点 §4.3, plan 26-10-12-2010)时按块追加各块槽数
        (读集成本的量级单点, 供计数属性断言); 不传 = 零影响(既有调用不变)。"""
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
                    _SampleAggMixin._agg_credit_hours(hour_samples, tail[0], first.ts, dl, up, dlt, upt)
            for k in range(len(slots) - 1):
                cur, nxt = slots[k], slots[k + 1]
                obs = _SampleAggMixin._slot_agg_obs(cur, agg_totals[k])
                if obs is None:
                    continue  # n 槽: null 期不贡献
                _SampleAggMixin._agg_credit_hours(hour_samples, cur.ts, nxt.ts, *obs)
            tail = (slots[-1].ts, _SampleAggMixin._slot_agg_obs(slots[-1], agg_totals[-1]))
        return tail
