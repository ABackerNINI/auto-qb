"""traffic_sample_mod 拆分件: 聚合域 mixin(R5 move-only, 计划 26-11-02-2342 §07)。

方法体里对类级静态方法的引用写成 `_SampleAggMixin.`(搬出根模块后 `TrafficSampleModule`
不再可见; 同一函数对象, 语义不变)。根模块以同名 logger 记录, 日志名仍为
`auto_qb.core.modules.traffic_sample_mod`。

P2b 追加(plan 26-11-21-1546 S2 第二步): acc 快照账本接线面在本文件 —— 启动快路
(`_try_ledger_fastpath`, 指纹探针 + R3 两向判定 `raw_tail_beyond_cursor` 尾块轻量读)、
AccSeriesState<->SeriesAgg 逐字段转换(静态守阵钉对齐)、flush 随批变化行(`_flush_acc_rows`)
与 stop 终态行(`_acc_stop_rows`)。账本格式/追加/压实本体在 core/traffic_store_acc_ledger.py。
"""
import logging
import math
import os
import time
from typing import Any, Callable, List, Optional, Tuple

from ..traffic_store import (
    HOUR_SECONDS,
    TrafficV4Store,
    V4DayResume,
    V4HourSample,
    V4NullRun,
    V4ParsedDay,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    parse_v4_day_text,
    v4_block_gap_continuous,
    v4_day_block_offsets,
    v4_day_block_starts,
    v4_day_epoch,
    v4_merge_agg,
    v4_month_epoch,
    v4_rollup_agg,
    v4_run_geometry,
    v4_z_ramp_element,
    v4_z_totals_ramp,
)
from ..traffic_store_acc_ledger import (
    AccHourFoldState,
    AccSeriesState,
    AccSnapshot,
    append_acc_snapshots,
    compact_acc_ledger,
    probe_agg_fingerprint,
    stat_agg_fingerprint,
)

from .traffic_sample_common import EVICT_CHECK_INTERVAL_S, HourFold, OpenRun, SeriesAgg, _hour_spans, _record_slots

logger = logging.getLogger("auto_qb.core.modules.traffic_sample_mod")

# ---------- acc 快照账本接线(P2b, plan 26-11-21-1546 S2 第二步; 组件单点在
# ---------- core/traffic_store_acc_ledger.py, 本节只做 modules 层消费) ----------

#: R3 两向判定的表达式噪声容差(秒): 账本游标 = 写侧游标(buf.projected_ts), 尾槽游标 =
#: 读侧 dt 链推进结果 —— 两者镜像同源但表达式不同(非块首游程可差 1 ULP; 生产 epoch
#: ~2^31 下 ULP ~5e-7s)。容差 0.5ms 吸收表达式噪声(几个 ULP ~1e-6s, 三数量级余量), 又
#: 严格低于 dt_ms=1 钳制边界(时钟回拨/亚毫秒到达写 dt_ms=1 合法行, 读侧 advance=1ms)下
#: 真实超前记录的最小槽距(1ms)—— crash 窗口内恰一条 1ms 记录的超前(尾-游标 ≈ 1e-3)
#: 大于容差必判回放, 「误判只向多回放(亏性能不丢数据)单向倾斜」的声明在该边界成立。
ACC_RAW_TAIL_TOL_S = 5e-4

#: 尾块判定窗口(字节, R3 轻量读纪律 —— 不为判定做全量读): 只读最新候选天文件的尾部
#: 窗口扫 \nB 定位最后一个有效块头。块宽上界 = Q3 保险闸 V4_BUFFER_SLOT_CAP(3600 槽)
#: x ~36B/r 行 ≈ 130KB, 256KB 常态一发命中; 无块头时翻倍重读至上限, 仍无 = 保守 fallback。
_ACC_TAIL_WINDOW_BYTES = 256 * 1024
_ACC_TAIL_WINDOW_MAX_BYTES = 1024 * 1024


def agg_state_from_acc(state: AccSeriesState) -> SeriesAgg:
    """AccSeriesState -> SeriesAgg 逐字段拷贝(快路直采的恢复面)。字段对齐(名字+顺序)
    由 tests/test_traffic_acc_ledger.py 静态守阵钉死, 增删字段即红。pending 桶值
    AccHourFoldState -> HourFold 逐字段重建(不与解析产物共享可变容器); 行表浅拷贝
    (AggRow 冻结不可变, 换容器即可)。"""
    agg = SeriesAgg()
    agg.pending = {
        h:
            HourFold(
                dl_wsum=f.dl_wsum,
                up_wsum=f.up_wsum,
                cov=f.cov,
                dl_max=f.dl_max,
                up_max=f.up_max,
                dl_total=f.dl_total,
                up_total=f.up_total,
                credits=f.credits,
            )
        for h, f in state.pending.items()
    }
    agg.open_credit = tuple(state.open_credit) if state.open_credit is not None else None
    agg.day_epoch = state.day_epoch
    agg.day_hours = list(state.day_hours)
    agg.month_epoch = state.month_epoch
    agg.month_days = list(state.month_days)
    if state.closed_day is not None:
        agg.closed_day = (state.closed_day[0], list(state.closed_day[1]))
    if state.closed_month is not None:
        agg.closed_month = (state.closed_month[0], list(state.closed_month[1]))
    agg.earliest_hour = state.earliest_hour
    return agg


def acc_state_from_agg(agg: SeriesAgg) -> AccSeriesState:
    """SeriesAgg -> AccSeriesState 逐字段拷贝(写侧面: flush 随批变化行 / stop 终态行的
    快照构建)。同一镜像纪律; fold 逐字段拷贝(在线折叠态是活对象, 快照必须持副本)。
    AccSnapshot(cursor/fingerprint 列)由调用方随构建点取值(游标 = _series_cursor,
    指纹 = 封口后的 agg.dat stat)。"""
    st = AccSeriesState()
    st.pending = {
        h:
            AccHourFoldState(
                dl_wsum=f.dl_wsum,
                up_wsum=f.up_wsum,
                cov=f.cov,
                dl_max=f.dl_max,
                up_max=f.up_max,
                dl_total=f.dl_total,
                up_total=f.up_total,
                credits=f.credits,
            )
        for h, f in agg.pending.items()
    }
    st.open_credit = tuple(agg.open_credit) if agg.open_credit is not None else None
    st.day_epoch = agg.day_epoch
    st.day_hours = list(agg.day_hours)
    st.month_epoch = agg.month_epoch
    st.month_days = list(agg.month_days)
    if agg.closed_day is not None:
        st.closed_day = (agg.closed_day[0], list(agg.closed_day[1]))
    if agg.closed_month is not None:
        st.closed_month = (agg.closed_month[0], list(agg.closed_month[1]))
    st.earliest_hour = agg.earliest_hour
    return st


def _tail_block_cursor(block) -> float:
    """尾块 dt 链推进 -> 读侧游标(R3 判定的尾槽值): 公式与 _agg_credit_day_file 逐位
    同式 —— r = 显式 dt 或标称(块首 advance 0), 游程 = t + (base + spacing x (n-1))
    (v4_run_geometry 推导单点)。返回末记录的槽位锚点(与写侧 projected_ts 镜像同源;
    与「末槽 ts」表达式可差 1 ULP, 由 ACC_RAW_TAIL_TOL_S 吸收)。"""
    interval = float(block.interval_s)
    t = float(block.start_epoch)
    first = True
    for rec in block.records:
        if isinstance(rec, V4Sample):
            advance = 0.0 if first else ((rec.dt_ms / 1000.0) if rec.dt_ms is not None else interval)
            ts = t + advance
            t = ts
        elif isinstance(rec, (V4ZeroRun, V4NullRun)):
            spacing, base = v4_run_geometry(rec, interval, first)
            t = t + (base + spacing * (rec.run_len - 1))
        else:
            raise TypeError(f"未知块记录型: {type(rec).__name__}")
        first = False
    return t


def raw_tail_beyond_cursor(store: TrafficV4Store, key: str, cursor: Optional[float]) -> bool:
    """R3 两向判定(§03.3/§07 R3, 快路直采的前置闸): raw 尾是否超前于账本游标。
    True = 存在游标之后的槽位**或无法轻量判定**(该系列 fallback 回放, 保守口径:
    判定失真只准亏性能不准丢数据 —— 误判单向倾斜见 ACC_RAW_TAIL_TOL_S 注);
    False = raw 尾 <= 游标(快路直采, 折叠态已含全部 raw 信用)。

    轻量读纪律(§03.3「不得为判定把快路做成全量读」): 候选文件 = 日期 >= 游标所在日的
    天文件(块不跨天 -> 更早文件的槽位全部 < 游标日 00:00 <= 游标, 时序不变式下不可能
    超前; 最新文件的尾槽 = 全候选集最大槽位), 只读其尾部窗口字节扫 \\nB 定位最后一个
    有效块头, 自该偏移 resume 解析到 EOF(与 read_day_open_segment 同款续解机制),
    dt 链推进取尾游标(_tail_block_cursor)。单系列成本 = 1 listdir + 1 尾窗口读 +
    1 尾块解析, 零 agg 读、零全文件解析。

    保守分支(一律 True -> fallback): 游标 None 且存在天文件(账本从未入账而有 raw,
    语义上必有未回放槽位, 不读文件直判)/ 文件尺寸异常(0 字节)/ 窗口翻倍至上限仍无
    有效块头(损坏/只有头行)/ 尾块为空块(B 行后无合法记录 —— 尾槽不可判)/ 日界换算、
    解析或 IO 异常(全函数保守闸 —— 判定不得让恢复入口抛错)。候选文件集为空 =
    False(游标之后无 raw 槽位)。"""
    try:
        if cursor is None:
            return bool(store.series_day_dates(key, 0.0))  # 账本从未入账: 有 raw 即有未回放槽位
        dates = store.series_day_dates(key, float(v4_day_epoch(cursor)))
        if not dates:
            return False  # 游标日之后无天文件: raw 尾 <= 游标
        path = store.series_day_path(key, dates[-1])
        size = os.path.getsize(path)
        if size <= 0:
            return True  # 空文件(创建中断形态): 无法判定, 保守回放
        window = min(size, _ACC_TAIL_WINDOW_BYTES)
        while True:
            with open(path, "rb") as f:
                f.seek(size - window)
                raw = f.read(window)
            starts = v4_day_block_starts(raw, v4_day_block_offsets(raw))
            if starts or window >= size or window >= _ACC_TAIL_WINDOW_MAX_BYTES:
                break
            window = min(size, window * 2)  # 尾窗口未及任何块头(尾块超窗): 翻倍重读
        if not starts:
            return True  # 全文件无有效块头(损坏/只有头行): 保守回放
        resume = V4DayResume(
            key=key,
            bad_lines=0,
            data_lines=0,
            blocks=(),
            open_start=None,
            open_interval=None,
            open_dl_base=None,
            open_up_base=None,
            open_records=(),
        )
        parsed = parse_v4_day_text(raw[starts[-1][0]:].decode("utf-8", errors="replace"), resume=resume)
        blocks = parsed.blocks
        if not blocks or not blocks[-1].records:
            return True  # 尾块为空块(B 行后无合法记录): 尾槽不可判, 保守回放
        return _tail_block_cursor(blocks[-1]) > cursor + ACC_RAW_TAIL_TOL_S
    except (OSError, ValueError, TypeError):
        return True  # 文件/日界换算/解析异常: 保守回放(该系列走 fallback 重建)


def _open_run_hour_samples(agg: "SeriesAgg", run: Optional[OpenRun], out: Optional[dict] = None) -> dict:
    """开放游程 + 未结算信用 -> hour 桶折叠态(活尾合成, plan 26-10-29-0231 §03; 模块级
    纯函数)。out 缺省 = 新建 dict 返回(测试探针面); 传入 out(活尾 pending 副本,
    dict-of-fold)= 信用直接并入 —— R2 浮点序: 与旧列表路径「settled 样本列表 + 合成
    样本按时间序 extend」的求和序同序(逐笔 merge), 两个 fold 的累计值直接相加不满足
    结合律, 禁止(D12, 计划 26-11-21-1546)。

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

    每段恰 1 笔信用 merge(O(小时数), 不是 O(槽数)): 段内速率与 totals 恒定, seal 的
    dt 加权与「级末快照 = 末笔」在等值信用下与逐槽展开等价。
    返回 {hour_epoch: HourFold, ...}(传 out 时即该对象; 不与累计器共享容器)。
    """
    if out is None:
        out = {}
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
    影响)。合成段与已结算信用同桶时按时间序排在后 merge(D12 折叠态逐笔 merge, R2 同
    序), seal 的「级末快照 = 末笔」因此拿到更晚的 totals。

    口径与写侧封口同源(三层各自当前桶):
    - hour: pending 各桶逐桶 seal(D12 折叠态, 数学与 v4_hour_agg 同); 含「已完成未 flush」的桶(flush
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
    # 副本: 合成段只进副本, 累计器本体不动(封口路径零影响); 合成信用经 _open_run_hour_samples
    # 按到达顺序逐笔 merge 进副本 fold(R2 浮点序: 旧列表路径「同桶样本按时间序追加在后」
    # 的求和序 = 逐笔 merge 序, bitwise 等价 —— 折叠值直接相加禁止, 加法不满足结合律)
    pending = {h: fold.copy() for h, fold in agg.pending.items()}
    _open_run_hour_samples(agg, run, pending)
    for h in sorted(pending):
        fold = pending[h]
        if fold.credits == 0:
            continue  # 空桶不留(全 null 覆盖的小时不产行, 与 _agg_flush_series 同)
        try:
            hour_partials.append(fold.seal(h))
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


def _agg_credit_z_run(
    hour_samples: dict, first_ts: float, spacing: float, rec: V4ZeroRun, skip_through_hour: Optional[int]
) -> None:
    """z 游程内部槽区间的桶级闭合式入账(B2, plan 26-11-21-1546 S1; 模块级纯函数)。

    取代逐槽展开(B1 前的 _agg_credit_day_file 主循环): 游程 n 槽槽位 ts_k =
    (t + base) + spacing*k(k = 0..n-1, 与 v4_block_slots 同式逐位 —— first_ts 即
    ts_0 = fl(t + base), spacing/base 由 v4_run_geometry 推导), 槽区间 [ts_k, ts_{k+1})
    的信用 = (0, 0, ramp[k], spacing)(ramp = v4_z_totals_ramp 摊配)。n-1 个内部区间
    按小时桶分组: 每桶一笔 merge(0, 0, ramp[ki], Σdt)—— ki = 桶内最后一个**正长度**
    区间的起点槽, Σdt = 桶内正长度区间并集的端点差一次减法 —— O(桶数)(<= 游程跨的
    小时数, 天文件块不跨天 => <= 25), 不随槽数放大。

    FP 等价层级(D2 口径, 对拍守阵 tests/traffic_recovery_support.py 随机语料钉死):
    - 必须逐位: wsum(z 信用每笔 +0.0: x + 0.0 = x 精确, 非负 float 无 -0 反例, r 信用
      求和序不变)/ max(z rate 恒 0 不动 max, 桶首笔基线信用两路同一笔)/ totals 末笔
      (ramp[ki] 为整数, 与逐槽路径「桶内最后一笔 merge」同值 —— 零长度塌缩区间在逐槽
      路径本就不产 merge, 末笔同取正长度区间)/ 信用区间边界(槽 ts 同式)。
    - ULP 免责: fold.cov(桶内 Σdt)—— 闭合式 = 端点差一次 Sterbenz 精确减法(= 真实
      telescoping 和); 逐槽参照 = 精确分段差的 FP 累加(每段 ts 差精确, 累加含舍入)。
      两路差 = 参照累加舍入, 上界 ≈ 段数 x ULP(3600) <= ~1.6e-9(段数 <= 3600,
      ULP(3600) = 2^-41)—— 只经 round() 进 cov_s(整型吸收)与 avg 分母(z 桶 rate = 0
      分子恒 0)。实施期实测(强于上界): 生产 epoch(ts ∈ [2^30, 2^31))下全部 ts 共享
      2^-22 栅格且桶内 cov < 2^12 => 逐槽累加每步精确(Sterbenz 型归纳, 论证全量见
      tests/traffic_recovery_support.py COV_ULP_TOL 注), 闭合式与逐槽 cov **恒逐位
      相等**(随机 dt 语料 + 4000 例混排块压力实测 0 差); 容差仅作契约面保留(论证
      依赖 epoch binade 与桶宽数量关系, 不改断言层级)。
    - 结构豁免: fold.credits(merge 笔数, 桶级合并后变少)—— 仅 ==0 判空消费, 不进任何
      聚合输出(D2「样本列表粒度允许不同」的同款口径)。

    零长度塌缩区间(spacing < ULP(ts) 时相邻槽舍入同点; 语料/生产 spacing >> ULP 不出现)
    在逐槽路径 end <= start 跳过不 merge —— 闭合式桶内并集不含零宽区间(区间连续铺贴无
    洞), ki 回退跳过塌缩链, Σdt 与末笔均与逐槽路径一致。

    每桶经 _agg_credit_hours 单区间入账(区间恒落单桶: s_start >= b、s_end <= 桶界,
    恰一笔 merge; skip_through_hour 过滤与首桶定位 int(cur)//HOUR_SECONDS*HOUR_SECONDS
    与逐槽路径同式同判)。"""
    n = rec.run_len
    span_end = first_ts + spacing * (n - 1)  # 末槽 ts_{n-1}(与 v4_block_slots 槽位表达式同式)
    if n < 2 or span_end <= first_ts:
        return  # 单槽游程无内部区间(尾部信用由调用方 pending 结算); span_end 防御支
    b = int(first_ts) // HOUR_SECONDS * HOUR_SECONDS  # 首桶(与 _agg_credit_hours 的 h 计算同式)
    while b < span_end:
        be = b + HOUR_SECONDS
        # ki_naive = 「桶界 be 之前最后一个槽」为起点的区间: 先 O(1) 反推首个 >= be 的
        # 槽下标(候选按实数除法, FP 修正 <= 2 步; 塌缩链回退步数有界且不超过逐槽路径
        # 本要走的槽数 —— 语料/生产 spacing >> ULP(ts) 恒为 0 步)
        i = max(1, min(n, math.ceil((be - first_ts) / spacing)))
        while i > 1 and first_ts + spacing * (i - 1) >= be:
            i -= 1
        while i < n and first_ts + spacing * i < be:
            i += 1
        ki = (n - 2) if i >= n else i - 1  # ts_{i-1} < be <= ts_i: 候选桶末区间起点
        while ki >= 0 and first_ts + spacing * ki >= first_ts + spacing * (ki + 1):
            ki -= 1  # 塌缩区间(零长度)无 merge: 回退到正长度区间
        if ki < 0:
            b += HOUR_SECONDS
            continue  # 桶内无正长度区间: 不入账(与逐槽路径一致)
        s_start = first_ts if first_ts > b else b  # max(b, ts_0): 桶内并集起点
        last_end = first_ts + spacing * (ki + 1)
        s_end = be if last_end > be else last_end  # min(be, ts_{ki+1}): 桶内并集终点
        ramp_dl, ramp_up = v4_z_ramp_element(rec.dl_total, rec.up_total, rec.dl_total_end, rec.up_total_end, n, ki)
        _SampleAggMixin._agg_credit_hours(hour_samples, s_start, s_end, 0, 0, ramp_dl, ramp_up, skip_through_hour)
        b += HOUR_SECONDS


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
        pending: dict,
        start: float,
        end: float,
        dl: int,
        up: int,
        dl_total: int,
        up_total: int,
        skip_through_hour: Optional[int] = None
    ) -> None:
        """区间 [start, end) 按小时界拆分入账(HourFold 逐笔 merge, dt = 桶内覆盖秒;
        D12 折叠态单点 —— 在线记账与恢复离线记账共用, 离线传局部 dict)。末槽的信用
        区间跨小时界时自然拆分, hour 桶 cov 上界 3600 由 seal 收口(= v4_hour_agg 同款
        min 截断)。信用按到达顺序并入(R2: 与旧列表路径逐条 append 的浮点求和序同序,
        聚合输出 bitwise 等价)。

        skip_through_hour 非 None(恢复离线侧 B1 水位前移, plan 26-11-21-1546 S1)时
        hour <= 该值的桶即时跳过不入账(封口小时信用在记账入口丢弃, 不建桶不 merge;
        在线路不传 = 无水位概念零过滤)。跳过支只跳过 merge, 桶界推进照常 —— 保留桶的
        dt 值与合并序与旧「全量入账 + 尾部丢弃」逐位一致(对拍守阵钉住)。"""
        if end <= start:
            return
        cur = start
        while cur < end:
            h = int(cur) // HOUR_SECONDS * HOUR_SECONDS
            seg = min(end, h + HOUR_SECONDS) - cur
            if skip_through_hour is None or h > skip_through_hour:
                fold = pending.get(h)
                if fold is None:
                    fold = pending[h] = HourFold()
                fold.merge(dl, up, dl_total, up_total, seg)
            cur += seg

    def _agg_flush_all(self, now: float) -> set:
        """全系列聚合封口(§4.2 flush 时点; stop() 复用 —— 未完结层级留累计器, 重启经
        catch-up 重建, 零丢失)。返回本轮 agg 封口 append 成功的系列键集(S2 acc 随批行
        的「变化」判据之一; 空集 = 本轮无任何 agg 落盘)。

        逐系列隔离(2026-10-13 真机取证): 单系列封口抛错只该影响该系列。此前异常一路上抛到
        handler, 于是 1. 其余系列本轮也不封口 2. `_agg_append` 永不执行 = 全系列 agg 静默停写
        3. 抛点在状态复位之前, 同一错每轮 flush 复现 —— 真机上一个系列抛「逐级聚合无有效
        覆盖」, 全系列小时行一个多小时没落盘。现在逐系列 catch + 善后(见
        _agg_reset_after_error), 单系列的问题不再放大成全局停写。"""
        sealed_ok: set = set()
        for key in list(self._agg_states):
            try:
                if self._agg_flush_series(key, now):
                    sealed_ok.add(key)
            except Exception as e:  # noqa: BLE001 —— 逐系列隔离即本函数职责(见 docstring)
                self._agg_reset_after_error(key, e)
            else:
                self._agg_warned.discard(key)  # 恢复健康: 下次再错重新告警一次
        return sealed_ok

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
        时点 piggyback 裁剪检查(§4.5)。返回是否实际写了 agg 文件(测试用)。
        开头清 _acc_append_failed(S2 硬序旗标, 单点见 _agg_append): 旗标语义 =
        「本系列最近一次 agg append 尝试失败」, 每轮封口开头复位 —— 本轮再失败由
        _agg_append 置位(acc 行本轮跳过), 本轮无 agg 行时保持清位(下轮 acc 行自愈)。"""
        self._acc_append_failed.discard(key)
        agg = self._agg_states.get(key)
        if agg is None:
            return False
        rows: List[Any] = []  # AggRow 行; 写成 Any 规避 _agg_ingest_* 形参 List[V4HourSample] 的既有型差(递减面)
        for h in sorted(agg.pending):
            if h + HOUR_SECONDS > now:
                break  # 首个未完结小时即止(pending 按序, 之后只会更晚)
            fold = agg.pending.pop(h)
            if fold.credits == 0:
                continue  # 空桶不留(全 null 覆盖的小时不产行, 空桶 = null)
            self._agg_ingest_hour(agg, fold.seal(h), rows)
        if agg.day_epoch is not None and agg.day_hours and v4_day_epoch(now) > agg.day_epoch:
            self._agg_ingest_day(agg, v4_rollup_agg("day", agg.day_epoch, tuple(agg.day_hours)), rows)
            # 已关日存根(issue R1#63): 关层复位后该日 hour 仍会被迟到信用重封, 存根是
            # 那时的合流源(_agg_reseal_closed_day); 行表对象随存根移交, 复位行表换新列表
            agg.closed_day = (agg.day_epoch, agg.day_hours)
            agg.day_epoch, agg.day_hours = None, []
        if agg.month_epoch is not None and agg.month_days and v4_month_epoch(now) > agg.month_epoch:
            rows.append(v4_rollup_agg("month", agg.month_epoch, tuple(agg.month_days)))
            agg.closed_month = (agg.month_epoch, agg.month_days)  # 已关月存根(同上, 月界同构面)
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
        (2026-10-13 真机: 日行 cov_s 只留残余 44712 vs 全量 86400)。开放累计器不含该桶
        (层已关闭/已翻走)时此处不合流 —— 那条路在 _agg_reseal_closed_day(已关层存根,
        issue R1#63), 由 _agg_ingest_hour 先行分流。"""
        if cur_epoch is None or bucket_epoch_of(row.epoch) != cur_epoch:
            return row
        for h in cur_rows:
            if h.epoch == row.epoch:
                return v4_merge_agg(h, row)
        return row

    @staticmethod
    def _acc_upsert_row(rows: List[V4HourSample], row: V4HourSample) -> None:
        """累计器/存根行表的「同 epoch 替换, 否则追加」单点(_ingest_acc 同款语义)"""
        for i, h in enumerate(rows):
            if h.epoch == row.epoch:
                rows[i] = row
                return
        rows.append(row)

    @staticmethod
    def _agg_reseal_closed_day(agg: SeriesAgg, row: V4HourSample, rows_out: List[V4HourSample]) -> None:
        """已关日的 hour 迟到重封(issue 26-11-07-0527 R1#63): 日/月关层复位累计器后, 该日
        hour 再被迟到信用重封时开放累计器里已无合流源 —— 修复前残余行未经 v4_merge_agg
        直接落盘, 解析按「同 epoch 取最后一行」让残余行替换已写全量行(cov/avg/max 静默
        腐蚀; 月界同构面连 day/month 行一起腐蚀), 且重启恢复以最后一行为水位不会再重算
        修复。真机形态: 午夜跨天空闲 z 游程在 00:00 后首个样本封口, 而 flush 恰落在
        00:00 与封口记录之间。

        口径: 合流源取**已关日存根**(关层时保留的已写行, 与 agg 文件有效行同值) ——
        合流后经存根**重建日行**并随本批落盘: 重建是**完整重算**(子行集 = 该日全部有效
        hour 行), 走替换语义不经 v4_merge_agg(与重启 catch-up 同口径, 合流会重复计);
        月层按同口径消化重建日行 —— 开放月只替换 month_days 条目(月行尚未写, 随月末
        封口自然带上), 已关月替换存根条目并重建月行。开放累计器(day_epoch/day_hours)
        全程不动: 背日行不得级联翻日(否则把开放日提前误关成缺日行)。"""
        day_epoch, day_rows = agg.closed_day
        stored = row
        for i, h in enumerate(day_rows):
            if h.epoch == row.epoch:
                stored = v4_merge_agg(h, row)
                day_rows[i] = stored
                break
        else:
            day_rows.append(row)  # 存根无此小时(此前整点无行/整点为 null): 首写
        rows_out.append(stored)
        day_row = v4_rollup_agg("day", day_epoch, tuple(day_rows))
        rows_out.append(day_row)
        month_bucket = v4_month_epoch(day_epoch)
        if agg.month_epoch == month_bucket:
            _SampleAggMixin._acc_upsert_row(agg.month_days, day_row)
        elif agg.closed_month is not None and agg.closed_month[0] == month_bucket:
            month_epoch, month_rows = agg.closed_month
            _SampleAggMixin._acc_upsert_row(month_rows, day_row)
            rows_out.append(v4_rollup_agg("month", month_epoch, tuple(month_rows)))
        # 月层都不匹配(背日超过一个月, 正常信用回溯 <= 24h 到不了): 日行已落盘, 月层不动

    @staticmethod
    def _agg_ingest_hour(agg: SeriesAgg, row: V4HourSample, rows_out: List[V4HourSample]) -> None:
        """完结 hour 行落批 + 并入 day 累计器(严格逐级): 入库行(首封或与已封行合流的重封行)
        随本批落盘(§4.2 完结整小时 append hour 行; 同 epoch 重封 = 追加**合流行**, 解析取
        最后一行 —— 落批必须是合流行, 否则读侧末行仍是残余); 同日追加; 同 epoch 重封与
        累计器旧行合流(v4_merge_agg); 翻日(暂停恢复跨多小时滞留)先级联封前一日再开新累计器。
        本行属于**已关日**(开放日累计器不是它)时改走已关日存根合流(_agg_reseal_closed_day,
        issue R1#63), 开放累计器不动。顺带维护 earliest_hour 裁剪判据(§4.5): 运行期才开始
        产数据的系列(全新安装 global / 新种子 / 热重载启用)不经 _recover_series, 判据只能在
        此初始化 + min 更新, 否则 _agg_trim 恒早退、agg.dat 无界增长(26-10-06-0028 C-01)。"""
        day_bucket = v4_day_epoch(row.epoch)
        if agg.day_epoch != day_bucket and agg.closed_day is not None and agg.closed_day[0] == day_bucket:
            _SampleAggMixin._agg_reseal_closed_day(agg, row, rows_out)
        else:
            stored = _SampleAggMixin._agg_merge_prev(row, agg.day_epoch, agg.day_hours, v4_day_epoch)
            rows_out.append(stored)

            def cascade(close_epoch: int, close_rows: List[V4HourSample]) -> None:
                # 前一日随本行翻日封口(其末 hour 已过, 前一日必已完结)
                _SampleAggMixin._agg_ingest_day(agg, v4_rollup_agg("day", close_epoch, tuple(close_rows)), rows_out)

            agg.day_epoch, agg.day_hours = _SampleAggMixin._ingest_acc(
                stored, agg.day_epoch, agg.day_hours, v4_day_epoch, cascade
            )
        if agg.earliest_hour is None or row.epoch < agg.earliest_hour:
            agg.earliest_hour = row.epoch

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
        catch-up 从天文件/agg 尾重建补算(幂等)。
        S2 硬序旗标(_acc_append_failed): append 失败置位 / 成功清位 —— acc 随批行
        (_flush_acc_rows/_acc_stop_rows)对置位系列跳过(账本行不得领先于 agg 现状:
        行内指纹/游标语义对齐 agg, 领先会让恢复快路采到「累计器含未落盘封口行」的
        状态); 复位点在 _agg_flush_series 开头(下一轮无 agg 行时 acc 行自愈补写)。"""
        if not rows:
            return False
        if not self._persistence_on or not self._ctx.config.data_dir:
            return False  # dry_run: 封口内存照常推进, 写静默跳过
        try:
            self._get_v4_store().append_agg_rows(key, rows)
            self._persist_warned = False
            self._acc_append_failed.discard(key)
            return True
        except OSError as e:
            self._acc_append_failed.add(key)
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
            self._acc_cursors.pop(key, None)  # S2: 账本接线缓存同步清理(防陈旧游标复活已删系列)
            self._acc_dirty.discard(key)
            self._acc_append_failed.discard(key)
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

    def _recover_series(
        self,
        key: str,
        store: TrafficV4Store,
        now: float,
        window: float,
        acc_snapshot: Optional["AccSnapshot"] = None
    ) -> dict:
        """单系列恢复(§4.3/§4.4): 扫 agg 文尾 -> 水位(= 文件尾行, 不落内存不重 append)
        + 文件内行重建当日/当月累计器 -> catch-up 逐级补算 append(hour <- 读集内天文件
        raw 游程级闭合式前向记账(B2, plan 26-11-21-1546) / day <- agg 内 hour 行 /
        month <- day 行) -> 末尾才裁剪(硬序)。S2 起入口先试 acc 快照快路(见下方
        P2b 段; acc_snapshot = 账本该系列末行或 None)。

        读集按需(plan 26-10-12-2010 D1): 读集下界 = agg 水位所在日
        [v4_day_epoch(wm_hour), 今日] —— 水位封口小时不读不重算, 读集常态 1 个天文件、
        跨日界至多 2 个, 与 24h 流量图读侧契约同阶; rollup_window 只决定保留(D2:
        1000000D 永久保留不动), 不决定启动读集。为什么是「所在日」而非时刻:
        series_day_dates 按文件名日期过滤, 传 day(wm_hour) 恰好纳入水位当天天文件
        (水位之后的 raw 必落在该日或更晚文件 —— 天文件 00:00 硬切、块不跨天)。
        agg 无可用水位(wm_hour is None: 缺失/损坏/无 hour 行)时退回 now - window 全量
        兜底(D5: 无可信水位则不可判哪些小时已聚合, 全量重算 + INFO 留痕, 诚实兜底不猜)。
        停机超窗的天文件已删 -> 对应 hour/day 行缺失跳过不标注(图上真空, 与块间 gap 同)。

        B1 水位前移(plan 26-11-21-1546 S1): 文件内处理范围从「全文件解析 + 全槽入账 +
        尾部丢弃」改为「字节级块定位 + 开放段限定解析 + 记账入口过滤」—— 水位路径逐
        文件只解析开放段(store.read_day_open_segment: 首个整块落保留小时的块自其前一块
        起解析, 前一块供跨块结算上下文; 全封口文件只解析末块供跨文件 tail 接力), 封口
        块零解析零入账; hour 信用经 _agg_credit_day_file(skip_through_hour=wm_hour)在
        记账入口即时跳过(hour_samples 不再出现封口桶)。边界上下文忠实(R1): 上下文块
        的封口信用被过滤但 tail 照常接力, 00:00 跨文件连续结算的信用落保留小时不丢;
        等价性由对拍守阵钉死(D2 口径, tests/traffic_recovery_support.py)。末尾
        h <= wm_hour 判据保留为防御二门(开放段决策的兜底)。fallback 路径(wm None)
        零过滤全量入账, 语义零变化(D4/D5)。

        acc 快照快路(P2b/S2 入口分支, §03.3): acc_snapshot 非 None(账本有效且该系列
        有末行)时先走 _try_ledger_fastpath —— 指纹探针 + R3 两向判定全过 = 从折叠态
        逐字段直采 SeriesAgg(累计器/pending/open_credit/earliest_hour 全部就位, 零
        agg 读零 raw 读, 判定本身只有 1 次 agg.dat stat + 尾块轻量读); 失配/缺失/
        损坏/raw 超前 = 该系列 fallback(B1+B2, 单系列隔离, INFO 留痕 per D9)。
        fallback 重建后标记 _acc_dirty(首轮 flush 补写账本行, 快路自愈)并记忆重建
        游标 = 读集尾槽(day_tail[0], 与在线游标同语义 —— 后续封口-only 变化的 acc 行
        仍有正确游标)。

        返回读集埋点 {"day_dates", "bound", "new_hours", "slots", "source"}(供
        _recover_aggregates 汇总与测试机检读集有界; slots = B1 开放段口径: 实际解析/
        记账走过的块槽位数, 封口块不再计; source = "ledger" 快路直采 / "rebuild"
        fallback 重建 —— S2 新增字段, 快路下 bound = "ledger"、day_dates 空)。"""
        if acc_snapshot is not None and self._try_ledger_fastpath(key, store, acc_snapshot):
            return {"day_dates": (), "bound": "ledger", "new_hours": 0, "slots": 0, "source": "ledger"}
        parsed = store.read_agg(key)
        agg = self._agg_state(key)
        agg.earliest_hour = parsed.hours[0].epoch if parsed.hours else None
        wm_hour = parsed.hours[-1].epoch if parsed.hours else None
        wm_day = parsed.days[-1].epoch if parsed.days else None
        wm_month = parsed.months[-1].epoch if parsed.months else None
        today = v4_day_epoch(now)
        cur_month = v4_month_epoch(now)
        # --- hour catch-up: 读集内天文件 raw 前向记账(B2 起游程级闭合式, 成本 ∝ 行数;
        # --- 与在线记账同一口径); 跨天文件末槽上下文接力(00:00 边界连续时条件结算, 缺文件断链) ---
        hour_samples: dict = {}  # hour_epoch -> HourFold(D12 折叠态, 与在线 pending 同表示)
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
            if wm_hour is None:
                parsed_day = store.read_day(key, date)  # fallback(D4): 全量解析, 语义不变
            else:
                # B1(plan 26-11-21-1546 S1): 只解析开放段 —— 封口块零解析零入账; 上下文
                # 块(开放段首块的前一块/全封口文件的末块)整块解析供 tail 接力, 其封口
                # 信用由 skip_through_hour 在记账入口过滤(R1: 跨块/跨文件边界上下文忠实)
                parsed_day = store.read_day_open_segment(key, date, wm_hour)
            if parsed_day is not None:
                day_tail = self._agg_credit_day_file(
                    hour_samples, parsed_day, day_tail, slot_counts, skip_through_hour=wm_hour
                )
            else:
                day_tail = None  # 缺失文件: 结算上下文断链(其后间隙由 gap 判定兜底真空)
        if len(day_dates) > 2:
            src = f"水位日 {day_dates[0]} 陈旧(聚合持续未落盘?)" if bound == "watermark" else "fallback 保留窗全量"
            logger.info(f"流量采样 | {key} 读集 {len(day_dates)} 天(>2): 下界来源 = {src}(不影响正确性, 正确性由逐小时重算判据保证)")
        new_hours = []
        for h in sorted(hour_samples):
            if wm_hour is not None and h <= wm_hour:
                continue  # 水位之前已有行: 不重算(前向水位, §4.4; B1 起记账入口已过滤,
                # 此处为防御二门 —— 开放段决策的兜底)
            fold = hour_samples[h]
            if fold.credits == 0:
                continue  # 空桶(全 null 覆盖的小时不产行, 空桶 = null; 防御支)
            if h + HOUR_SECONDS <= now:
                new_hours.append(fold.seal(h))  # 完结缺失小时 -> 补算行
            else:
                agg.pending[h] = fold  # 开放小时 -> 重建累计器(D12 折叠态; 信用序列与在线同序)
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
        # S2 自愈面: 重建系列标记 dirty(首轮 flush 补写账本行, 恢复快路) + 记忆重建
        # 游标 = 读集尾槽(day_tail[0] 与在线游标同语义: 末记录槽位锚点; None = 读集无 tail)
        self._acc_dirty.add(key)
        if day_tail is not None:
            self._acc_cursors[key] = day_tail[0]
        return {
            "day_dates": day_dates,
            "bound": bound,
            "new_hours": len(new_hours),
            "slots": sum(slot_counts),
            "source": "rebuild",
        }

    def _try_ledger_fastpath(self, key: str, store: TrafficV4Store, snap: AccSnapshot) -> bool:
        """acc 快照快路(D9/§03.3, _recover_series 入口分支): 两道闸全过 = 从账本折叠态
        逐字段直采 SeriesAgg 并返回 True(零 agg 读零 raw 读 —— 判定本身只有 1 次
        agg.dat stat 探针 + 1 次尾块轻量读); 任一不过 = False(该系列 fallback B1+B2,
        单系列隔离, INFO 留痕 per D9 —— 快照是加速器不承载正确性):
        1. 指纹探针: 现 agg.dat stat == 账本行内指纹(失配/缺失 = agg 已变化, 采账本态
           会与 agg 现状发散);
        2. R3 两向判定: raw 尾槽 <= 账本游标(超前 = 崩溃落在 raw 追加与账本追加之间,
           账本落后, 须回放尾段)。
        直采时同步记忆游标(_acc_cursors —— 后续封口-only 变化的 acc 行仍要正确游标)。"""
        if not probe_agg_fingerprint(self._ctx.config.data_dir, key, snap.agg_fingerprint):
            logger.info(f"流量采样 | {key} acc 快照指纹失配(agg.dat 与账本行不符), 该系列走 fallback 重建(D9 单系列隔离)")
            return False
        if raw_tail_beyond_cursor(store, key, snap.cursor):
            logger.info(f"流量采样 | {key} raw 尾超前于账本游标(崩溃窗口 R3 两向), 该系列走 fallback 重建回放尾段")
            return False
        self._agg_states[key] = agg_state_from_acc(snap.state)
        if snap.cursor is not None:
            self._acc_cursors[key] = snap.cursor
        return True

    def _series_cursor(self, key: str) -> Optional[float]:
        """系列游标(acc 行 cursor 列; = 累计器已入账到的最后槽位 = 最后一条记录的槽位
        锚点): 优先写侧游标 buf.projected_ts(与 _agg_feed 的 cursor 实参同源 —— 每记录
        到达时两者同点推进, 缓冲对象存活期内恒有效, 关块复位不清它); 缓冲不在(壳清理)
        回落游标记忆(_acc_cursors, 上次 acc 行构建时记下); 再回落 open_credit[0]
        (r/z 尾与写侧游标同值)。n 尾 + 缓冲不在的窄角游标不可恢复 -> None(读侧两向
        判定对 None 保守 fallback, 语义不损只亏一次重建)。"""
        buf = self._buffers.get(key)
        if buf is not None:
            return buf.projected_ts if buf.projected_ts else None
        cur = self._acc_cursors.get(key)
        if cur is not None:
            return cur
        agg = self._agg_states.get(key)
        credit = agg.open_credit if agg is not None else None
        return float(credit[0]) if credit is not None else None

    def _flush_acc_rows(self, sealed_ok: set) -> None:
        """acc 账本随批追加(§03.4 flush 时点第3/4步, S2/D7/D8): 本 flush 有状态变化的
        系列行 append(变化判定 = agg 封口发生了 append[sealed_ok] 或累计器有推进
        [_acc_dirty, _flush_series 落盘记录时标记]; 空闲系列零追加 —— 黄金法则 1)。
        硬序: agg 封口 append 失败的系列本轮跳过(_acc_append_failed 置位 —— 账本行不得
        领先于 agg 现状; 系列保持 dirty, 下轮无 agg 行时自愈补写)。acc 行指纹 = 封口后
        (append+trim)的 agg.dat stat —— 读侧探针的比对基准; 游标 = _series_cursor。
        变化系列合一批 append(单次 open("a") piggyback), 随后压实检查(>16MB 单次重写,
        阈值内零写)。append 与压实两处 OSError 均告警不上抛(append 失败保持 dirty 下轮
        补写; 压实失败无数据后果 —— 行已落账, tmp+os.replace 纪律下原文件完好下轮自愈)。"""
        if not self._persistence_on or not self._ctx.config.data_dir:
            return
        changed = [
            key for key in sorted(self._agg_states)
            if key not in self._acc_append_failed and (key in self._acc_dirty or key in sealed_ok)
        ]
        if not changed:
            return  # 空闲 flush: 零追加零 stat(压实检查随写走 —— 无追加即无增长)
        data_dir = self._ctx.config.data_dir
        snaps = []
        for key in changed:
            cursor = self._series_cursor(key)
            snaps.append(
                AccSnapshot(
                    key=key,
                    cursor=cursor,
                    agg_fingerprint=stat_agg_fingerprint(data_dir, key),
                    state=acc_state_from_agg(self._agg_states[key]),
                )
            )
            if cursor is not None:
                self._acc_cursors[key] = cursor
        try:
            append_acc_snapshots(data_dir, snaps)
        except OSError as e:
            if self._persist_warned:
                logger.debug(f"流量采样 | acc 账本追加失败(持续): {e}")
            else:
                logger.warning(f"流量采样 | acc 账本追加失败(本批快照行丢失, 系列保持 dirty 下轮补写): {e}")
                self._persist_warned = True
            return
        self._acc_dirty.difference_update(changed)
        try:
            compact_acc_ledger(data_dir)  # (4) 压实检查(阈值内零写; 重写失败原文件完好留待下轮)
        except OSError as e:
            # 压实读侧/重写失败无数据后果(行已追加成功, tmp+os.replace 纪律下原文件完好,
            # 下轮随批自愈), 与本函数 append 失败口径拉平: 告警不上抛(否则穿透采样轮)。
            logger.warning(f"流量采样 | acc 账本压实检查失败(快照行已落账, 原文件完好下轮自愈): {e}")

    def _acc_stop_rows(self) -> None:
        """stop 终态行(§03.4/D8: 「acc 全系列终态行 append」): 优雅退出把全部系列的
        折叠态落账本, 下次启动全量快路(零重算)。幂等: _acc_stop_done 单次闸 —— 终态行
        内容与首发批一致, 重复 stop 零追加(黄金法则 1)。硬序同 flush: agg 封口 append
        失败的系列跳过(重启该系列按 fallback 重建)。dry_run 零写。append 与压实两处
        OSError 均告警不上抛 —— stop 在 host.stop_all() 内, 上抛会跳过 state.save(黄金
        法则 3)与 _lock.release(压实失败无数据后果, 同 flush 侧口径)。"""
        if not self._persistence_on or not self._ctx.config.data_dir or self._acc_stop_done:
            return
        self._acc_stop_done = True  # 单次闸: 置位在构建前 —— 失败也不重试(重启 fallback 兜底)
        data_dir = self._ctx.config.data_dir
        snaps = []
        for key in sorted(self._agg_states):
            if key in self._acc_append_failed:
                continue  # agg 封口 append 失败: 行不领先于 agg 现状(硬序)
            cursor = self._series_cursor(key)
            snaps.append(
                AccSnapshot(
                    key=key,
                    cursor=cursor,
                    agg_fingerprint=stat_agg_fingerprint(data_dir, key),
                    state=acc_state_from_agg(self._agg_states[key]),
                )
            )
            if cursor is not None:
                self._acc_cursors[key] = cursor
            self._acc_dirty.discard(key)
        if not snaps:
            return
        try:
            append_acc_snapshots(data_dir, snaps)
        except OSError as e:
            logger.warning(f"流量采样 | acc 账本 stop 终态行追加失败(重启按系列 fallback 重建): {e}")
            return
        try:
            compact_acc_ledger(data_dir)
        except OSError as e:
            # 同 flush 侧口径: 压实失败无数据后果(终态行已追加成功, 原文件完好), 告警
            # 不上抛 —— stop 在 host.stop_all() 内, 上抛会跳过 state.save 与锁释放。
            logger.warning(f"流量采样 | acc 账本 stop 压实检查失败(终态行已落账, 原文件完好): {e}")

    @staticmethod
    def _slot_agg_obs(slot: V4Slot, agg_totals: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int, int, int]]:
        """单槽的 agg 入账观测(形态 D 单点): z 槽 = (0, 0, 摊配 dl, 摊配 up)
        (v4_block_agg_totals 的逐槽值 —— 无末端列/单槽游程时 = 开启快照, 与旧语义逐位一致);
        r 槽 = 原 obs(速率 + 冻结 totals); n 槽 = None(null 期不贡献)。

        B2(plan 26-11-21-1546 S1)起生产恢复路径不再逐槽展开, 本函数仅剩测试侧逐槽
        参照件(tests/traffic_recovery_support.reference_slot_credit, 改造前实现逐字镜像)
        消费 —— 保留作对拍基准, 与 v4_hour_agg 同款先例; 生产语义由 _agg_credit_day_file
        的游程级闭合式承载(观测形态逐位同源)。"""
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
        slot_counter: Optional[List[int]] = None,
        skip_through_hour: Optional[int] = None
    ) -> Optional[tuple]:
        """单天文件游程级闭合式记账(恢复离线侧; B2, plan 26-11-21-1546 S1 —— 取代逐槽
        展开: 成本 ∝ 记录行数 + 小时桶数, 不随槽数放大; 空闲系列 3 千行文本展开 2 万槽
        的纯浪费根除)。与在线 _agg_feed 结算区间信用同一口径(信用区间边界/tail 逐位
        同源, z 的 agg 摊配两路共用 v4_z_totals_ramp/v4_z_ramp_element 同式)。

        逐块逐记录推进 dt 链游标(公式与 v4_block_slots 逐位同式, 推导单点
        v4_run_geometry):
        - r 记录(1 槽): ts = fl(t + advance)(advance = 显式 dt 或标称 interval; 块首
          advance = 0, 首槽恰在 B.start), 信用逐行不变(单区间 O(桶));
        - z 游程: 内部槽区间按小时桶闭合式入账(_agg_credit_z_run, O(桶数));
        - n 游程: O(1) 跳过(槽 obs 全 None 不贡献, 只推进游标);
        - 前向记账「末槽信用归下一记录」边界忠实: 每记录先在其首槽结算上一记录末槽的
          待结算信用 pending(单区间 O(桶)), 再入账自身内部区间 —— 信用区间序列与逐槽
          路径逐一同位(obs/边界全同)。游程末槽 pending = (末槽 ts, 摊配末端值
          ramp[n-1], 与在线 z 记录的尾部信用同值) / n 游程 = (末槽 ts, None)。
        游标推进逐位同源: 游程游标 = fl(t + fl(base + fl(spacing*(n-1))))(v4_block_slots
        游标行同式 —— 与末槽 ts 是两个表达式, 非块首可差 1 ULP, 逐槽路径本就如此,
        闭合式照抄两式)。

        跨块覆盖结算(v4 计划 §01「覆盖结算」, 与在线路复用判定单点 v4_block_gap_continuous):
        块间(含跨天文件 —— prev_tail 由 _recover_series 传入上一文件末槽上下文)gap =
        下一块首槽(float(B.start) = 块首记录首槽, 恒等) - 上一块末槽, 连续(<= interval +
        DRIFT_TOL)则按上一槽速率把 [末槽, 首槽) 结算进覆盖, 崩溃/停机间隙超容差为真空
        —— 00:00 边界既有每天约 2s 覆盖损失就此消除。prev_tail = (末槽 ts, obs) 或
        None(无上下文/上文件缺链); 返回本文件末槽上下文(末槽为 null 观测时 obs = None,
        调用方结算侧自然跳过; B1 全封口文件只解析末块时本函数照常产出末块 tail, 跨文件
        接力不受开放段限定影响)。

        FP 等价层级(D2 口径, 对拍守阵 tests/traffic_recovery_support.py 随机语料钉死):
        - 必须逐位: wsum(z 信用每笔 +0.0: x + 0.0 = x 精确; r 信用求和序不变)/ max
          (z rate 0 不动 max, 桶首笔基线信用两路同一笔)/ totals 末笔(桶末正长度区间
          ramp 元素与逐槽「桶内最后一笔」同值, 整数)/ 信用区间边界与 tail(槽 ts 同式)/
          块槽计数(Σ(1 / run_len) 与展开槽数同值);
        - ULP 免责: fold.cov(桶内 Σdt —— 闭合式 = 端点差一次精确减法 vs 逐槽精确分段
          差的 FP 累加, 差 = 参照累加舍入 <= ~1.6e-9, 见 _agg_credit_z_run)—— 只经
          round() 进 cov_s(整型吸收)与 avg 分母(z 桶 rate = 0 分子恒 0; 精确栅格语料
          两路全程精确, cov 逐位相等由守阵单钉);
        - 结构豁免: fold.credits(merge 笔数, 桶级合并后变少)—— 仅 ==0 判空消费, 不进
          任何聚合输出(D2「样本列表粒度允许不同」同款口径)。

        slot_counter 非 None(恢复埋点 §4.3, plan 26-10-12-2010)时按块追加各块槽数;
        B1(plan 26-11-21-1546 S1)起口径 = **实际解析/记账走过的块**(开放段 + 上下文
        块; 封口块在 read_day_open_segment 已不进 blocks, 不再计), B2 起按记录元数据
        O(行数) 直算 Σ(1 for r / run_len for 游程), 数值与展开槽数逐块同值, 不再物化
        槽序(v4_block_slots 本体保留: 在线活尾/读侧分组仍在用, 仅恢复路径摘除调用)。
        skip_through_hour 非 None = B1 水位前移过滤(hour <= 该值的桶在 _agg_credit_hours
        记账入口即时跳过, hour_samples 不再出现封口桶; 上下文块的封口信用由此过滤,
        骑水位块的保留信用照常入账); 不传 = 零过滤(在线/兜底路径不变)。"""
        tail = prev_tail
        for block in parsed_day.blocks:
            records = block.records
            if slot_counter is not None:
                slot_counter.append(sum(1 if isinstance(r, V4Sample) else r.run_len for r in records))
            if not records:
                continue  # 空块(解析层不产出, 防御支): 零槽零 tail 推进
            interval = float(block.interval_s)
            first_ts = float(block.start_epoch)  # 块首记录首槽恒在 B.start(块首 advance/base = 0)
            if tail is not None and tail[1] is not None:
                if v4_block_gap_continuous(tail[0], first_ts, block.interval_s):
                    dl, up, dlt, upt = tail[1]
                    _SampleAggMixin._agg_credit_hours(
                        hour_samples, tail[0], first_ts, dl, up, dlt, upt, skip_through_hour
                    )
            t = first_ts  # 游标 = 上一已消费记录的槽位锚点(v4_block_slots 同名变量同值)
            pending = None  # (末槽 ts, obs): 上一已消费槽的待结算信用(「末槽信用归下一记录」)
            for idx, rec in enumerate(records):
                first = idx == 0
                if isinstance(rec, V4Sample):
                    advance = 0.0 if first else ((rec.dt_ms / 1000.0) if rec.dt_ms is not None else interval)
                    ts = t + advance  # 槽位(v4_block_slots 同式); 其后 t += advance 同值
                    if pending is not None and pending[1] is not None:
                        _SampleAggMixin._agg_credit_hours(hour_samples, pending[0], ts, *pending[1], skip_through_hour)
                    pending = (ts, (rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total))
                    t = ts
                    continue
                if isinstance(rec, (V4ZeroRun, V4NullRun)):
                    spacing, base = v4_run_geometry(rec, interval, first)  # 推导单点(与展开同源)
                    slot_first = t + base  # 首槽 ts_0 = fl((t + base) + fl(spacing*0)) = fl(t + base)
                    if pending is not None and pending[1] is not None:
                        _SampleAggMixin._agg_credit_hours(
                            hour_samples, pending[0], slot_first, *pending[1], skip_through_hour
                        )
                    if isinstance(rec, V4ZeroRun):
                        _agg_credit_z_run(hour_samples, slot_first, spacing, rec, skip_through_hour)
                        end_dl, end_up = v4_z_ramp_element(
                            rec.dl_total, rec.up_total, rec.dl_total_end, rec.up_total_end, rec.run_len, rec.run_len - 1
                        )
                        pending = (slot_first + spacing * (rec.run_len - 1), (0, 0, end_dl, end_up))
                    else:
                        # n 游程: null 期不贡献, 末槽 obs = None(其后区间结算侧自然跳过)
                        pending = (slot_first + spacing * (rec.run_len - 1), None)
                    t = t + (base + spacing * (rec.run_len - 1))  # 游标(v4_block_slots 游标行同式)
                    continue
                raise TypeError(f"未知块记录型: {type(rec).__name__}")
            tail = pending  # 末槽上下文 = (末槽 ts, 末槽 obs) —— 与逐槽路径 slots[-1] 同值
        return tail
