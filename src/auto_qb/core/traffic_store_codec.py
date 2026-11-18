"""traffic_store 拆分件: v4 行型编解码(R5 move-only, 计划 26-11-02-2342 §07)。

slot/block/天/agg 行 dataclass 与 format/parse 全在此; `_parse_v4_text` 仍是两个
解析器共用的唯一行循环驱动器。读侧调用方(TrafficV4Store/V4DayCache)留在根模块,
根以 `from .traffic_store_codec import parse_v4_*` 重新绑定 —— 按根属性打补丁仍生效。
"""
import math
from dataclasses import dataclass
from typing import Any, Callable, List, NamedTuple, Optional

from .traffic_store_common import (
    AGG_FIELDS,
    AGG_KINDS,
    AGG_LEGACY_FIELDS,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    _fmt_dt_tail,
    _fmt_int,
    _fmt_interval_s,
    _parse_dt_ms,
    _parse_interval_s,
    _parse_nn_int,
    _parse_pos_int,
)

# ======================================================================
# 纯函数区(plan 26-10-04-1957 S1 立, §02.3/§04/§06.2; 行型定约随 v4 换代由 v4 计划
# §01 取代, 单点见模块 docstring「格式 v4 契约」与文件尾 v4 区头注释)
#
# 天文件解析/序列化、路径解析、聚合与活尾槽位推算的纯函数层(读写两侧同源)。解析纪律
# (坏行整行跳过、游标不推进、撕裂尾豁免)沿用 v2/v3 先例; 整数/小数秒 + 毫秒口径:
# start_epoch 整数秒; interval_s >= 1 允许小数秒(规范十进制 —— 整数值不带小数点, 与
# 历史整秒文件形态一致; 非整值最短往返表示如 1.5); dt_ms 正整数且 <= DT_MS_MAX。
#
# dt 链定约(§02.3 读侧规则 + §09.2 授权的实施期细化, S2 写侧必须同约定产出):
# - 游标 t = 上一已消费记录的槽位锚点; t0 = B.start = 块首记录实测 epoch(块首记录
#   槽位恰在 t0, 块首记录自身的 dt 列无语义, 写侧不写)。
# - r 记录: 槽位 = t + advance; advance = 显式 dt_ms 或标称 interval_s。显式 dt_ms =
#   距上一记录链上终点的实测毫秒数 —— 链上终点在上一记录显式时即其实测锚点, 故即
#   「距上一记录实际毫秒数」(§02.1)。
# - z/n 游程: advance = 显式 dt_ms 或标称 run_len x interval_s(§02.1 缺省口径);
#   run_len 个槽在 [t, t+advance] 内均摊(槽 k = t + k x advance/run_len, k=1..len,
#   末槽恰在 t+advance = 游程实测终点 last_seen); 显式 dt_ms = 游程开启时链上锚点
#   到末槽的实测毫秒数(OpenRun.start := 链上锚点 —— §09.2「z/n 相邻游程编码细节」
#   实施期定约: 相邻游程间的一次采样间隔并入后一游程的 dt_ms, 链式无系统误差);
#   其后记录的 dt 以游程终点(实测)为基准(§02.3) —— 链式自洽。
# - 块首记录为游程时特殊: B.start 即其首槽(块首无上一记录, 无引导间隔), 槽 k =
#   t0 + k x dt_ms/(run_len-1)(k=0..len-1, 端点含), 缺省按标称 interval。
# - 有效 dt(桶宽, §02.3): r = 显式 dt 或标称 interval; 游程槽 = 均摊 span/run_len。
# ======================================================================


@dataclass(frozen=True)
class V4Slot:
    """v4 块内单槽展开(v4_block_slots 返回): 游标 dt 链推算出的观测点

    obs 形态: r 槽 = (dl_rate, up_rate, dl_total, up_total); z 槽 = (0, 0, dlt, upt)
    (空闲观测, totals 恒定); n 槽 = None(null)。ts 为浮点秒 —— 显式 dt_ms 带亚秒精度;
    dt_s = 距上一槽有效间隔(秒, §02.3 有效 dt; 块首槽取标称 interval_s)。
    !旧 is_hold 字段(活尾链端延伸合成槽, F4/F3 计划 26-11-14-1313/26-11-15-1104)已随
    持有面退役(26-11-18-0037 D2 样本分组契约: 尾组恒真值无克隆)删除 —— 槽 = 纯采样
    /游程观测, 空值点契约无持有槽(v4_live_tail_slots 复原即纯槽序)。
    """

    ts: float
    dt_s: float
    obs: Optional[tuple]
    is_zero: bool  # True = z 游程槽(速率恒 0); n 槽为 False 且 obs = None


def v4_block_slots(block: "V4Block") -> tuple:
    """块内逐槽时间推算(游标 dt 链 + 均摊定位; §02.3 读侧规则, 纯函数)

    规则见文件头「纯函数区」头注释「dt 链定约」: t0 = B.start; 每消费一记录游标推进
    (显式 dt_ms 或 槽位数 x interval_s x 1000)/1000 秒, r 槽落在新游标处, z/n 游程的
    run_len 个槽在 [t, t+advance] 内均摊(末槽恰在 t+advance = 游程实测终点), 其后
    记录的 dt 以游程终点为基准 —— 链式自洽。缺省按标称 interval; 显式 dt 行严格按
    实测推进。本函数只走 dt 链 —— 全路径不存在「时刻 = start + i x interval」的纯
    等间隔推算(测试钉住 d̄>0 序列无累积误差)。

    块首记录槽位恰在 B.start(其自身 dt 列无语义, 不消费); 块首记录为游程时首槽 =
    B.start、槽距 = dt_ms/(run_len-1)(端点含)或缺省标称 interval。
    本函数只认 V4 记录型(基线列与槽位数学无关)。
    返回 Tuple[V4Slot, ...](槽序 = 槽位升序 = 记录槽序展开)。
    """
    slots: list = []
    interval = float(block.interval_s)
    t = float(block.start_epoch)  # 游标 = 上一已消费记录的槽位锚点; 块首记录锚点 = B.start
    for idx, rec in enumerate(block.records):
        first = idx == 0
        if isinstance(rec, V4Sample):
            if first:
                advance = 0.0  # 块首记录槽位恰在 B.start(其 dt 列无语义, 不消费)
                dt_s = interval
            else:
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else interval
                dt_s = advance
            slots.append(
                V4Slot(
                    ts=t + advance,
                    dt_s=dt_s,
                    obs=(rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total),
                    is_zero=False,
                )
            )
            t += advance
            continue
        if isinstance(rec, (V4ZeroRun, V4NullRun)):
            run_len = rec.run_len
            if first:
                # 块首游程: 首槽 = B.start, 端点含均摊(§09.2 实施期定约, 见区头注释);
                # 游标终点 = 末槽 = B.start + spacing x (run_len-1)
                spacing = (rec.dt_ms / 1000.0) / (run_len - 1) if (rec.dt_ms is not None and run_len > 1) else interval
                base = 0.0
            else:
                # 非块首游程: advance = 显式 dt(链上锚点 -> 末槽)或标称 run_len x interval;
                # 槽 k = t + k x advance/run_len(k=1..len), 均摊 span/run_len(§02.3);
                # 引导一次采样间隔(链上锚点 -> 首槽)并入 dt_ms, 游标终点 = 末槽
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else run_len * interval
                spacing = advance / run_len
                base = spacing
            for k in range(run_len):
                if isinstance(rec, V4ZeroRun):
                    obs = (0, 0, rec.dl_total, rec.up_total)
                    is_zero = True
                else:
                    obs = None
                    is_zero = False
                slots.append(V4Slot(ts=t + base + spacing * k, dt_s=spacing, obs=obs, is_zero=is_zero))
            t += base + spacing * (run_len - 1)  # 游标 = 末槽 = 游程实测终点(链式自洽)
            continue
        raise TypeError(f"未知块记录型: {type(rec).__name__}")
    return tuple(slots)


#: 块级槽游标(F4-2 立, 现消费者 = 分组点列缓存): (rec_idx, slots_done, anchor_t, run_base, run_spacing)
#: - rec_idx = 消费停驻的记录下标; slots_done = 该记录已消费槽数(0 = 记录边界)。
#: - slots_done == 0: anchor_t = dt 链锚点(上一已消费记录的槽位终点; rec_idx == 0 时 =
#:   block.start_epoch), run_base/run_spacing 恒 None。
#: - slots_done > 0: 停驻在游程记录(records[rec_idx], z/n 行)中部 —— anchor_t = 该游程
#:   的槽位推算锚点(t), run_base/run_spacing = 该游程的 base/spacing(r 槽单槽记录不产
#:   部分游标, 消费即整记录)。存锚点而非末槽 ts: 续展槽位表达式与全量展开逐位同式
#:   (t + base + spacing x k), 浮点零漂移。
_V4_BLOCK_CURSOR_START = (0, 0, None, None, None)


def v4_block_slots_from(block: "V4Block", cursor: tuple, t1: Optional[float] = None) -> tuple:
    """v4_block_slots 的游标续展形(F4-2, 计划 26-11-15-1104; dt 链定约同一实现的第二入口):
    从游标 cursor 接续展开 block 的槽序, 返回 (slots, next_cursor, exhausted)。

    - slots = 本段展开的全部槽(V4Slot 升序, 含 ts >= t1 的窗尾外槽 —— 调用方消费面
      (样本分组装配 / 分组点列缓存)按窗尾过滤逐槽裁决, 本函数不代滤; 游标仍停在首个
      ts >= t1 的槽, 窗尾外的槽下轮请求重展重判 —— 与全量现算「每请求按当时窗界消费」
      语义一致)。
    - next_cursor 同构游标; exhausted = True 表示整块槽序展完(next_cursor 停块尾)。
    - t1 = None: 全量展开(next_cursor 停块尾)。同游标起点 _V4_BLOCK_CURSOR_START、
      t1=None 时 slots 与 v4_block_slots(block) 逐位相等(同一 dt 链实现的两形态, 槽位
      表达式逐字同式; 守阵 test_traffic_store_slots::test_block_slots_from_full_
      equivalence 钉住)。
    - 只认 V4 记录型(与 v4_block_slots 同判); 未知型 TypeError fail-fast。
    """
    rec_idx, slots_done, anchor_t, run_base, run_spacing = cursor
    records = block.records
    interval = float(block.interval_s)
    slots: list = []
    if slots_done:
        # 游程中段续展: 余下槽 k = slots_done..run_len-1, ts = t + base + spacing x k
        # (与全量展开同式逐位相等; 游标推进 = 游程实测终点, 同式)
        rec = records[rec_idx]
        if isinstance(rec, V4Sample) or not isinstance(rec, (V4ZeroRun, V4NullRun)):
            raise TypeError(f"游标停驻记录须为游程型(z/n): {type(rec).__name__}")
        run_len = rec.run_len
        is_z = isinstance(rec, V4ZeroRun)
        obs = (0, 0, rec.dl_total, rec.up_total) if is_z else None
        t = anchor_t
        base, spacing = run_base, run_spacing
        for k in range(slots_done, run_len):
            ts = t + base + spacing * k
            if t1 is not None and ts >= t1:
                return tuple(slots), (rec_idx, k, t, base, spacing), False
            slots.append(V4Slot(ts=ts, dt_s=spacing, obs=obs, is_zero=is_z))
        t += base + spacing * (run_len - 1)  # 游标 = 末槽 = 游程实测终点(链式自洽)
        rec_idx += 1
        slots_done = 0
        anchor_t, run_base, run_spacing = t, None, None
    else:
        t = float(block.start_epoch) if anchor_t is None else anchor_t
    for idx in range(rec_idx, len(records)):
        rec = records[idx]
        first = idx == 0
        if isinstance(rec, V4Sample):
            if first:
                advance = 0.0  # 块首记录槽位恰在 B.start(其 dt 列无语义, 不消费)
                dt_s = interval
            else:
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else interval
                dt_s = advance
            ts = t + advance
            if t1 is not None and ts >= t1:
                return tuple(slots), (idx, 0, t, None, None), False
            slots.append(
                V4Slot(
                    ts=ts,
                    dt_s=dt_s,
                    obs=(rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total),
                    is_zero=False,
                )
            )
            t = ts
            continue
        if isinstance(rec, (V4ZeroRun, V4NullRun)):
            run_len = rec.run_len
            if first:
                spacing = (rec.dt_ms / 1000.0) / (run_len - 1) if (rec.dt_ms is not None and run_len > 1) else interval
                base = 0.0
            else:
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else run_len * interval
                spacing = advance / run_len
                base = spacing
            is_z = isinstance(rec, V4ZeroRun)
            obs = (0, 0, rec.dl_total, rec.up_total) if is_z else None
            for k in range(run_len):
                ts = t + base + spacing * k
                if t1 is not None and ts >= t1:
                    # 部分消费: 游标停驻游程中部(存锚点 t + base/spacing, 续展同式零漂移)
                    return tuple(slots), (idx, k, t, base, spacing), False
                slots.append(V4Slot(ts=ts, dt_s=spacing, obs=obs, is_zero=is_z))
            t += base + spacing * (run_len - 1)  # 游标 = 末槽 = 游程实测终点(链式自洽)
            continue
        raise TypeError(f"未知块记录型: {type(rec).__name__}")
    return tuple(slots), (len(records), 0, t, None, None), True


def v4_z_totals_ramp(dl_open: int, up_open: int, dl_end: Optional[int], up_end: Optional[int], n: int) -> tuple:
    """z 游程 agg 累计快照逐槽摊配(形态 D, plan 26-10-16-1509 §04; 在线 _agg_feed 与
    离线 _agg_credit_day_file 共用同一纯函数 —— 镜像靠同源)。

    游程内部第 k 槽(k = 0..n-1)的 agg totals = 开启快照 -> 末端快照按槽序线性插值:
    v_k = S0 + round((S1 - S0) x k / (n-1))(整数四舍五入, 端点精确: v_0 = S0, v_{n-1} = S1;
    取整余量归末端槽, 区间累加严格守恒)。n == 1(单槽, 跨度退化)恒取 S0; dl_end/up_end
    为 None(旧文件无末端列)或低于开启快照(游程内计数器重置的落盘形态 —— 重置落差不是
    增长)时按开启快照退化(恒快照 = 旧语义)。逐向独立(dl/up 各摊各的)。

    返回 Tuple[(dl_total, up_total), ...](长度 = n, 与 v4_block_slots 同段槽序一一对应)。
    raw 面不消费本函数(raw 差分链仍用冻结列)。"""
    dl1 = dl_open if dl_end is None or dl_end < dl_open else dl_end
    up1 = up_open if up_end is None or up_end < up_open else up_end
    if n <= 1:
        return ((dl_open, up_open), ) * max(n, 0)
    gd, gu = dl1 - dl_open, up1 - up_open
    half = (n - 1) // 2
    return tuple((dl_open + (gd * k + half) // (n - 1), up_open + (gu * k + half) // (n - 1)) for k in range(n))


def v4_block_agg_totals(block: "V4Block") -> tuple:
    """块内 z 游程的 agg 摊配逐槽序列(与 v4_block_slots 等长, 槽序一致; 离线侧消费者 =
    _agg_credit_day_file): z 槽 = v4_z_totals_ramp 的 (dl_total, up_total); r 槽 / n 槽 =
    None(agg 侧 r 用自身 obs、n 不贡献)。raw 车道(V4Slot.obs)不受本函数影响 —— 两者对
    「每记录槽数」的口径必须一致(r=1 / 游程=run_len), 改任一处需同步。"""
    out: list = []
    for rec in block.records:
        if isinstance(rec, V4ZeroRun):
            out.extend(v4_z_totals_ramp(rec.dl_total, rec.up_total, rec.dl_total_end, rec.up_total_end, rec.run_len))
        elif isinstance(rec, V4Sample):
            out.append(None)
        elif isinstance(rec, V4NullRun):
            out.extend((None, ) * rec.run_len)
        else:
            raise TypeError(f"未知块记录型: {type(rec).__name__}")
    return tuple(out)


# v4_bucket_width_s(逐记录覆盖桶宽 max(1, ceil(有效dt)))已随 26-11-15-1104 F2 栅格单几何
# 退役; 后续挂钟桶面(F1 桶宽加宽)亦随 26-11-18-0037 样本分组契约退役 —— 槽不再自带覆盖
# 桶宽。dt_s 仍为槽层的有效间隔(§02.3), 供读侧差分对跨的未观测秒判据消费。

# ---------- 活尾快照(S6 验收追加, 2026-10-05): 写侧未落盘状态 -> 读侧续链 ----------


@dataclass(frozen=True)
class LiveTailRun:
    """活尾开放游程冻结副本(S6): OpenRun 的不可变投影(发布时拷贝, Web 线程只读);
    槽位 = 未来封口形态 —— 非块首在 (锚点, last_seen] 均摊, 块首在 [B.start, last_seen]
    端点含(封口前 last_seen 仍会推进, 活尾按当轮快照近似, 偏差亚桶宽级图面无感)。"""

    kind: str  # "z" | "n"
    start: float  # 首个零/null 样本实测时刻(块首封口时 B.start = int(start))
    last_seen: float  # 最后一个样本时刻(活尾区间终点)
    dl_total: int  # all-time 下载累计快照(开启时刻, n 游程恒 0)
    up_total: int
    samples: int  # 游程内样本计数(封口后 = run_len)


@dataclass(frozen=True)
class LiveTail:
    """单系列活尾快照(S6, 采样模块每轮发布, Web 线程只读): 未落盘 buffer 记录 + 开放
    游程, 供流量图 raw 段窗合流(图面尾部实时, 不等 flush_interval)。

    block_open=True 时 records = 当前开放块未落盘的记录序列。镜像保证: 同一记录
    「写侧游标推进」与「落盘后 v4_block_slots 重算」的槽 ts 恒等 ——
    - head_pending=True(块尚无任何落盘, records = 全块记录): 槽位 = v4_block_slots
      整块重算(块首规则), 与 eventual 落盘重算恒等;
    - head_pending=False(块首已随此前 flush 落盘): 记录均为非块首, 槽位从写侧游标
      projected_ts(最后一条记录的槽位锚点)**倒推**复原 —— 倒推与前向推进对非块首
      记录恒等(游程末槽 = 游标, 逐记录回退各自 advance), 且不依赖磁盘链在窗内可见
      (1m 窗看不到上次 flush 的记录时活尾定位照常成立)。读侧据此按 ts 精确去重,
      快照与 flush 的先后竞态不重不漏。
    block_open=False 时 records 恒空(发布侧保证; 此时开放游程按块首封口形态定位
    —— 首槽 = int(run.start))。

    pending_agg(S7 验收追加, 2026-10-14): 聚合累计器里**未封口**的当前桶部分行
    (AggRow 元组, hour/day/month 三型混放, epoch 升序)—— agg.dat 只有封口行,
    开放小时/当日/当月只活在写侧累计器, 不发布则 3d/7d/30d(小时)/6mo/1y(日)/
    all(月)视图图尾停在最后一个封口桶(用户报「真空」)。读侧按 epoch 与磁盘封口行
    合流(v4_merge_agg 口径: 磁盘无行的开放桶直映, 已封桶的迟到补记残余与封口行
    合并 —— 与写侧 _agg_merge_prev 同判据)。与 records 独立: flush 后 records
    清空(磁盘接管 raw 面), 只要小时未封口 pending_agg 照常发布(agg 面)。
    26-10-29 起(plan 26-10-29-0231)部分行还含**开放游程合成段**: 空闲 z 游程未封口
    期间累计器 pending 为空, 图尾从最后一个封口点起到 now 整段 null(跨天后从 00:00
    起尤甚) —— 写侧按 _open_run_hour_samples 合成「未结算信用 + 游程内 0 速率」,
    与 raw 面 v4_live_tail_slots 的开放游程合成同构。合成行 totals 取游程末端锚点
    (不是开启快照), 保证 v4_merge_agg 的「totals 取后封行」不回退。
    """

    block_open: bool  # 写侧是否存在开放块(start_epoch 非 None)
    head_pending: bool  # 开放块尚无任何落盘(B 行未写, records = 全块记录)
    start_epoch: Optional[int]  # 开放块 B.start(block_open 才非 None; head_pending 复用)
    interval_s: float  # 槽位标称推进秒(块 interval; 无块时取当前生效采样间隔)
    projected_ts: float  # 写侧游标 = 最后一条记录的槽位锚点(block_open 才有语义)
    records: tuple  # 未落盘记录(V4Sample/V4ZeroRun/V4NullRun, 按槽序; block_open 才非空)
    open_run: Optional[LiveTailRun]  # 开放游程冻结副本(None = 无)
    pending_agg: tuple = ()  # 未封口聚合部分行(S7; AggRow 元组, 缺省空 = 纯磁盘 agg 读)


def v4_live_tail_slots(tail: LiveTail) -> tuple:
    """活尾快照 -> 槽序(S6 读侧接缝, 纯函数): 绝对槽位复原规则见 LiveTail docstring
    (head_pending 整块复用 v4_block_slots / 否则从 projected_ts 倒推 —— 两者都与这些
    记录落盘后的重算恒等)。开放游程 = 未来封口形态的槽位: 链锚点 = 记录链终点
    (head_pending 时 = 全块重算游标终值; 否则 = projected_ts), 非块首封口在
    (锚点, last_seen] 均摊(末槽 = last_seen); 无开放块按块首封口形态([B.start,
    last_seen] 端点含)。z 槽 obs = (0,0,快照), n 槽 obs = None。返回 Tuple[V4Slot, ...]
    (ts 升序)。

    活尾链端延伸(holding 槽, F4 计划 26-11-14-1313 / F3 26-11-15-1104 的 now/max_gap_s
    形参面)已随持有面退役(26-11-18-0037 D2 样本分组契约: 尾组 = 最新样本恒真值无克隆,
    每 tick 随样本更新; 停滞/断连不造点 —— 滞后/断连可见性由前端徽标按末样本 ts 与
    显式空值点承载): 本函数复原即**纯槽序**, 无任何合成槽; 与磁盘链的按 ts 去重
    (保留严格更晚后缀)在消费面缓存锁内(traffic_group_cache._tail_slots)。
    """
    if not tail.block_open and (tail.records or tail.head_pending):
        raise ValueError("活尾快照 invariant 破坏: block_open=False 不得携带 records/head_pending")
    slots: list = []
    interval = float(tail.interval_s)
    if tail.block_open and tail.head_pending and tail.records:
        # 块全量未落盘: 活尾 = 整块, 槽位复用块内推算(块首规则, 与落盘重算恒一)。
        # 活尾 records 为 V4 记录型(totals 恒绝对值, 槽位数学与基线无关), 构造 V4Block
        # 无基线形态仅作槽位推算载体
        slots.extend(v4_block_slots(V4Block(int(tail.start_epoch), tail.interval_s, None, None, tail.records)))
        chain_end = slots[-1].ts if slots else float(tail.start_epoch)
    else:
        # 非块首记录从写侧游标倒推(游标 = 最后一条记录锚点; 逐记录回退各自 advance)
        cursor = float(tail.projected_ts)
        for rec in reversed(tail.records):
            if isinstance(rec, V4Sample):
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else interval
                slots.append(
                    V4Slot(
                        ts=cursor,
                        dt_s=advance,
                        obs=(rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total),
                        is_zero=False,
                    )
                )
                cursor -= advance
                continue
            if isinstance(rec, (V4ZeroRun, V4NullRun)):
                # 非块首游程: run_len 个槽在 (cursor - advance, cursor] 均摊, 末槽 = cursor
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else rec.run_len * interval
                spacing = advance / rec.run_len
                is_z = isinstance(rec, V4ZeroRun)
                for k in range(rec.run_len):
                    if is_z:
                        obs = (0, 0, rec.dl_total, rec.up_total)
                    else:
                        obs = None
                    slots.append(V4Slot(ts=cursor - spacing * k, dt_s=spacing, obs=obs, is_zero=is_z))
                cursor -= advance
                continue
            raise TypeError(f"未知活尾记录型: {type(rec).__name__}")
        slots.reverse()
        chain_end = float(tail.projected_ts)
    run = tail.open_run
    if run is not None:
        n = run.samples
        is_z = run.kind == "z"
        z_obs = (0, 0, run.dl_total, run.up_total) if is_z else None
        if tail.block_open:
            # 非块首封口形态: 槽在 (chain_end, last_seen] 均摊, 末槽 = last_seen
            span = run.last_seen - chain_end
            spacing = span / n if span > 0 else interval
            for k in range(n):
                slots.append(V4Slot(ts=chain_end + spacing * (k + 1), dt_s=spacing, obs=z_obs, is_zero=is_z))
        else:
            # 块首封口形态(无开放块): B.start = int(run.start), 端点含均摊至 last_seen
            start = float(int(run.start))
            span = max(run.last_seen - start, 0.0)
            spacing = span / (n - 1) if n > 1 else 0.0
            for k in range(n):
                slots.append(V4Slot(ts=start + spacing * k, dt_s=spacing or interval, obs=z_obs, is_zero=is_z))
    return tuple(slots)


# ---------- 聚合行型(agg.dat, §02.2 + §04.1) ----------


@dataclass(frozen=True)
class AggRow:
    """聚合行(§02.2): hour/day/month 同构 9 列, agg.dat 追加混存

    epoch 语义: hour = 桶起点; day = 本地当日 00:00; month = 本地自然月 1 日 00:00。
    cov_s = 有效时长秒(hour 必带 —— 8 列无法还原有效时长, 部分覆盖小时等权平均有偏)。
    """

    kind: str  # "hour" | "day" | "month"
    epoch: int
    dl_avg: int
    dl_max: int
    up_avg: int
    up_max: int
    dl_total: int
    up_total: int
    cov_s: int


class V4HourSample(NamedTuple):
    """hour 累计器的逐记录输入(§04.1): dt_s 由调用方裁剪到桶内(min(dt_i, hour_end-t_i));
    z 游程槽 rate=0/span 均摊(v4_block_slots 的 z 槽即此形态), n 槽不贡献(调用方剔除)"""

    dl_rate: int
    up_rate: int
    dl_total: int
    up_total: int
    dt_s: float


@dataclass(frozen=True)
class V4ParsedAgg:
    """agg.dat 解析结果(parse_v4_agg_text 返回)"""

    key: Optional[str]
    hours: tuple  # Tuple[AggRow, ...](epoch 升序, 同 epoch 取最后一行 —— 重封追加行读侧口径)
    days: tuple
    months: tuple
    bad_lines: int
    data_lines: int
    torn_tail: bool = False


def format_agg_row(row: AggRow) -> str:
    """agg 行文本(§02.2): <kind>,<epoch>,<dl_avg>,<dl_max>,<up_avg>,<up_max>,
    <dl_total>,<up_total>,<cov_s>(9 列); kind 须在 AGG_KINDS"""
    if row.kind not in AGG_KINDS:
        raise ValueError(f"非法聚合行型: {row.kind!r}")
    return (
        f"{row.kind},{_fmt_int(row.epoch)},{_fmt_int(row.dl_avg)},{_fmt_int(row.dl_max)},"
        f"{_fmt_int(row.up_avg)},{_fmt_int(row.up_max)},{_fmt_int(row.dl_total)},{_fmt_int(row.up_total)},"
        f"{_fmt_int(row.cov_s)}"
    )


def _parse_v4_text(text: str, on_line: Callable[[List[str]], bool], *, resumed: Optional[tuple] = None) -> tuple:
    """v4 文本解析公共行循环驱动器(parse_v4_agg_text / parse_v4_day_text 纪律单点;
    issue 26-10-29-1304 R07-T06 收敛 —— 解析纪律骨架唯一实现, 行型判定留在 on_line)

    只管纪律不管行型: splitlines / torn 判定(无尾换行) / 头行门闩 / key 行取首个
    (重复 key 行落入 on_line 按该侧行型判坏) / 空行注释行跳过不计坏 / data 逐行计入
    (头行之后全部行, 含空行注释坏行 —— 坏行占比分母) / on_line(parts) 返回 True =
    已消费, 返回 False 或抛 ValueError/IndexError 同归 bad += 1(同一吞异常路径, 两种
    来源不区分 —— 行型守卫靠抛 ValueError 复用该路径, data 语义不因来源分叉) /
    撕裂尾标记(文件撕裂且坏行恰为末行)。头行缺失或不符 HEADER_LINE_V4 -> 返回
    (None, len(lines), len(lines), torn): 整文件记坏且 bad 含头行本身, 回调一次未跑,
    调用方累积器为空 => 组装即整文件坏形态。返回 (key, bad, data, torn_tail),
    结果对象(V4ParsedAgg / V4ParsedDay)由调用方各自组装。

    resumed = (key, bad, data) 前缀续解状态(F4-1 增量解析, 计划 26-11-15-1104): 跳过
    头行门闩(key 行已在前缀消费), 全部行按 data 行进入同一行循环, 计数自前缀续算 ——
    撕裂尾/坏行/空行注释/key 重复行纪律与整文件解析完全同源(同一循环同一分支), 语义
    等价于对 (前缀 + text) 拼接文本的整文件解析, 只是行型状态由 on_line 侧(块状态机)
    自行复位。前缀侧 key=None(头行门闩失守)不得用于续解(调用方把关, V4DayResume 单点)。
    """
    lines = text.splitlines()
    torn = bool(text) and not text.endswith("\n")
    if resumed is None:
        header = lines[0].strip() if lines else None
        if header != HEADER_LINE_V4:
            # 头行缺失/不符(含旧版头行): 文件级不匹配格式 —— 每一行都算坏行(损坏判定必然命中)
            return None, len(lines), len(lines), torn
        key: Optional[str] = None
        bad = 0
        data = 0
        body = lines[1:]
    else:
        key, bad, data = resumed
        body = lines
    torn_tail = False
    last_idx = len(body) - 1
    for i, line in enumerate(body):
        data += 1
        s = line.strip()
        if not s or s.startswith("#"):
            continue  # 空行/注释行跳过不计坏(对齐 v3 先例)
        parts = s.split(",")
        try:
            if parts[0] == "key" and len(parts) == 2 and parts[1] and key is None:
                key = parts[1]
                continue
            if on_line(parts):
                continue
        except (ValueError, IndexError):
            pass
        bad += 1  # 键名/列数不匹配或字段非法(整行跳过, 游标不推进)
        if torn and i == last_idx:
            torn_tail = True  # 尾部半行 = 正常崩溃残留(阈值豁免, 对齐 v3)
    return key, bad, data, torn_tail


def parse_v4_agg_text(text: str) -> V4ParsedAgg:
    """agg.dat 文本 -> V4ParsedAgg(纯函数; §02.2 + §04.4)

    头行必须恰为 HEADER_LINE_V4(缺失/不符整文件记坏, 同天文件口径); hour/day/month
    行 9 列, 8 列旧行兜底 cov_s = 3600(防御性, v4 全新目录正常不出现); cov_s 下限 1
    (与写侧 v4_hour_agg 契约对齐, 违者按坏行 —— issue 26-10-30-0622); 同 kind 同
    epoch 重复行取最后一行(重封 = 追加行的读侧口径); 坏行纪律与天文件一致。
    返回按 kind 分列、epoch 升序。
    !解析纪律骨架(头行门闩 / data+bad 计数 / 空行注释跳 / split(",") / try-except /
    撕裂尾豁免 / key 首个消费)单点在 _parse_v4_text(issue 26-10-29-1304 R07-T06 收敛),
    本函数只留 agg 行型分支(hour/day/month 9 列 + 8 列旧行兜底)。
    """
    rows_by_kind: dict = {k: {} for k in AGG_KINDS}

    def on_agg_line(parts: list) -> bool:
        if parts[0] in AGG_KINDS and len(parts) in (AGG_LEGACY_FIELDS, AGG_FIELDS):
            # 8 列旧行兜底 cov_s = 3600(§02.2 防御性)
            cov = _parse_nn_int(parts[8]) if len(parts) == AGG_FIELDS else HOUR_SECONDS
            if cov < 1:
                # 下限 1 与写侧契约对齐(§04.1「行存在即有覆盖」, v4_hour_agg cov_s 下限 1):
                # cov_s = 0 的语义非法行若放行, rollup(_catch_up_level 全零 cov 子行)炸
                # ValueError 逃逸恢复循环 / merge(v4_agg_obs_live)除零 —— 按坏行整行跳过
                # (行型守卫复用 _parse_v4_text 的 ValueError 吞异常路径, issue 26-10-30-0622)
                raise ValueError(f"cov_s 下限 1(行存在即有覆盖): {parts[8]}")
            row = AggRow(
                kind=parts[0],
                epoch=int(parts[1]),
                dl_avg=_parse_nn_int(parts[2]),
                dl_max=_parse_nn_int(parts[3]),
                up_avg=_parse_nn_int(parts[4]),
                up_max=_parse_nn_int(parts[5]),
                dl_total=_parse_nn_int(parts[6]),
                up_total=_parse_nn_int(parts[7]),
                cov_s=cov,
            )
            rows_by_kind[row.kind][row.epoch] = row  # 同 epoch 重复取最后一行(重封读侧口径)
            return True
        return False  # 键名/列数不匹配(整行记坏, 游标不推进)

    key, bad, data, torn_tail = _parse_v4_text(text, on_agg_line)
    by_kind = {k: tuple(rows_by_kind[k][e] for e in sorted(rows_by_kind[k])) for k in AGG_KINDS}
    return V4ParsedAgg(
        key=key,
        hours=by_kind["hour"],
        days=by_kind["day"],
        months=by_kind["month"],
        bad_lines=bad,
        data_lines=data,
        torn_tail=torn_tail,
    )


# ======================================================================
# v4 纯函数区(plan 26-10-05-2200 B1 立, 批 2 起接线为生产行为; 契约单点在根模块 docstring;
# z 行末端对语义与回滚约束单点在本区头注释)
#
# v4 行型定约(读写两侧同源单点; 规格出处 = v4 计划 §01, 取代 v3 计划 §02.1「逐列冻结」
# 条款; interval_s 小数秒 + dt_ms 毫秒口径沿用):
#     # auto-qb qb-traffic v4                                文件头, 每文件一次(头行门闩, 不设双读)
#     key,<系列标识>                                    不变(global / torrent:<infohash>)
#     B,<start_epoch>,<interval_s>                      3 列 = 无基线块(仅 n 游程合法)
#     B,<start_epoch>,<interval_s>,<dl_base>,<up_base>  5 列 = 基线 = 块内首个带 totals 观测的快照
#     r,<dl_rate>,<up_rate>,<dl_delta>,<up_delta>[,<dt_ms>]  delta 相对块基线; 负值 = 坏行(免费校验)
#     z,<run_len>,<dl_delta>,<up_delta>,<dl_endd>,<up_endd>[,<dt_ms>]  块首 z 的 delta = 0;
#         末端对(形态 D, plan 26-10-16-1509 §04)= 封口时刻已知的末端快照相对同一块基线的
#         delta(记录无末端值时写冻结列同值 = 显式退化); 旧文件 4/5 列无末端对 -> 解析为
#         None -> agg 摊配按开启快照退化(向后兼容)。raw 差分链只消费 delta 列/冻结列,
#         末端对仅 agg 车道(两路摊配共用 v4_z_totals_ramp)。
#     n,<run_len>[,<dt_ms>]                              不变
#
# 核心不变式: delta 只存在于线格式 —— 内存结构(V4Sample/V4ZeroRun/V4NullRun/V4Block)
# 全部维持绝对 totals; format 序列化时减法(绝对值 - 块基线), parse 以块基线逐行复原
# (绝对值 = 基线 + 本行 delta; delta-vs-基线逐行独立 —— 坏行整行跳过不传播, 无块内链式
# 状态, 与 flush 批次无关)。基线立点: 块首记录带 totals(r 或 z)时基线 = 该快照, 其
# delta = 0; 块首为 n 游程时写侧把 n-only 前缀拆成 3 列 B 无基线块, 恢复传输的记录开新
# 块立基线。解析守卫: 无基线块内出现 r/z 即坏行; 基线块内负 delta 必是损坏(绝对值形态
# 做不到的免费校验 —— 计数器回落由写侧「重置强制关块重立基线」排除, 批 2 状态机)。
# dt 链 / 撕裂尾 / 损坏占比口径原样沿用 v3(dt 列语义与 v3 完全一致, 辅助函数共用;
# dt 链定约见文件头「纯函数区」头注释, 此处不复写)。
# 形态 D 回滚约束(plan 26-10-16-1509 §07): 本版本写出的 z 行为 6/7 列, 不认识末端对的旧
# 解析器(列数不匹配)会把整行判坏 -> 回滚到旧版本前必须先剥离 z 行末端对(6/7 -> 4/5 列)
# 或保留兼容解析; 已落盘的末端对不回补不删除(与「历史坏行不回补」同口径)。
# ======================================================================


@dataclass(frozen=True)
class V4Sample:
    """v4 数据记录(r 行): 速率对 + all-time totals 绝对快照对(内存恒绝对值, delta 只在
    线格式 —— 序列化时减块基线); dt_ms 语义同 v3(距上一记录链上终点的实测毫秒数,
    None = 标称 interval)"""

    dl_rate: int
    up_rate: int
    dl_total: int
    up_total: int
    dt_ms: Optional[int] = None


@dataclass(frozen=True)
class V4ZeroRun:
    """v4 零速游程(z 行): 占 run_len 个采样槽, 速率恒 (0,0); totals 快照为绝对值(delta
    相对块基线只在行文本); dt_ms 语义同 v3。

    dl_total_end/up_total_end = 封口时刻已知的末端快照(形态 D, plan 26-10-16-1509 §04):
    封口时随 z 行末端列一起落盘(拿不到时写与冻结列同值 = 显式退化); None = 记录未携带
    末端对(旧文件解析结果/手工合成记录), agg 摊配按开启快照退化。raw 面差分链只消费
    dl_total/up_total(冻结列), 末端对仅供 agg 车道(见 v4_z_totals_ramp)。"""

    run_len: int
    dl_total: int
    up_total: int
    dt_ms: Optional[int] = None
    dl_total_end: Optional[int] = None
    up_total_end: Optional[int] = None


@dataclass(frozen=True)
class V4NullRun:
    """v4 null 游程(n 行): 占 run_len 个采样槽(断连/缺字段), 无观测; 行型与语义同 v3"""

    run_len: int
    dt_ms: Optional[int] = None


@dataclass(frozen=True)
class V4Block:
    """v4 块: 块头 B + 记录序列(按槽序); 块不跨天(00:00 硬切)。dl_base/up_base = 块基线
    (5 列块头; = 块内首个带 totals 观测的快照, 块首记录的 delta 恒 0), 二者成对: 全 None =
    无基线块(3 列 B, 仅 n 游程合法 —— 块首 n 游程前缀), 全非 None = 基线块。records 内
    totals 恒为绝对值(delta 只在序列化时减法)"""

    start_epoch: int  # 块首记录实测 epoch 秒
    interval_s: float  # 本块采样间隔(秒, >= 1; 允许小数秒如 1.5, 整数值存 float)
    dl_base: Optional[int]  # 块基线: 下载 all-time 快照(None = 无基线块, 与 up_base 成对)
    up_base: Optional[int]
    records: tuple  # Tuple[V4Sample | V4ZeroRun | V4NullRun, ...]


@dataclass(frozen=True)
class V4ParsedDay:
    """单天文件解析结果(parse_v4_day_text 返回; 块为 V4Block, 纯数据)"""

    key: Optional[str]  # 头行 key 行的系列标识(无头行/坏头行/头行非 v4 时 None)
    blocks: tuple  # Tuple[V4Block, ...](文件序; 空块不保留)
    bad_lines: int  # 跳过的坏行数(含尾部半行)
    data_lines: int  # 受检行总数(头行后全部行; 损坏占比分母)
    torn_tail: bool = False  # 末尾未写完的半行(正常崩溃残留; 豁免损坏占比)


def format_v4_b_row(
    start_epoch: int, interval_s: float, dl_base: Optional[int] = None, up_base: Optional[int] = None
) -> str:
    """块头行文本(v4 §01 二态): 无基线 = B,<start_epoch>,<interval_s>(3 列, 仅 n 游程
    合法); 基线块 = B,<start_epoch>,<interval_s>,<dl_base>,<up_base>(5 列, 基线 = 块内
    首个带 totals 观测的快照)。基线二态须成对(缺一 fail-fast); interval_s 校验口径同 v3
    (>= 1 数值, 允许小数秒)。"""
    if (dl_base is None) != (up_base is None):
        raise ValueError(f"块头基线须成对(全 None = 无基线块 / 全非 None = 基线块): {dl_base!r}/{up_base!r}")
    if not isinstance(interval_s, (int, float)) or isinstance(interval_s, bool):
        raise ValueError(f"非法 interval_s(须 >= 1 数值): {interval_s!r}")
    if not math.isfinite(interval_s) or interval_s < 1:
        raise ValueError(f"非法 interval_s(须 >= 1): {interval_s!r}")
    head = f"B,{_fmt_int(start_epoch)},{_fmt_interval_s(float(interval_s))}"
    if dl_base is None:
        return head
    return f"{head},{_fmt_int(dl_base)},{_fmt_int(up_base)}"


def format_v4_r_row(rec: V4Sample, dl_base: Optional[int], up_base: Optional[int]) -> str:
    """数据行文本(v4 §01): r,<dl>,<up>,<dl_delta>,<up_delta>[,<dt_ms>]; delta = 内存绝对
    totals - 块基线(减法单点在此, 读侧复原后逐列语义与 v3 一致)。r 行须基线块(无基线块
    仅 n 游程合法); 负 delta = 写侧违约 fail-fast(计数器回落须先关块重立基线 —— 解析侧
    对应按坏行, 免费校验)。"""
    if dl_base is None or up_base is None:
        raise ValueError("r 行须基线块(无基线块仅 n 游程合法)")
    dlt = int(rec.dl_total) - int(dl_base)
    upt = int(rec.up_total) - int(up_base)
    if dlt < 0 or upt < 0:
        raise ValueError(f"负 delta(计数器回落须先关块重立基线): dl={dlt}, up={upt}")
    return (
        f"r,{_fmt_int(rec.dl_rate)},{_fmt_int(rec.up_rate)},{_fmt_int(dlt)},{_fmt_int(upt)}"
        f"{_fmt_dt_tail(rec.dt_ms)}"
    )


def format_v4_z_row(rec: V4ZeroRun, dl_base: Optional[int], up_base: Optional[int]) -> str:
    """零速游程行文本(v4 §01 + 形态 D): z,<run_len>,<dl_delta>,<up_delta>,<dl_end_delta>,
    <up_end_delta>[,<dt_ms>](delta 相对块基线; 块首 z 的 delta = 0 —— 基线 = 该快照)。
    末端对(形态 D, plan 26-10-16-1509 §04) = 封口时刻已知的末端快照相对同一块基线的
    delta; 记录未携带末端值(None)时写冻结列同值 = 显式退化(解析侧两端等价)。其余纪律同
    format_v4_r_row。"""
    if dl_base is None or up_base is None:
        raise ValueError("z 行须基线块(无基线块仅 n 游程合法)")
    dlt = int(rec.dl_total) - int(dl_base)
    upt = int(rec.up_total) - int(up_base)
    dle = int(rec.dl_total_end if rec.dl_total_end is not None else rec.dl_total) - int(dl_base)
    upe = int(rec.up_total_end if rec.up_total_end is not None else rec.up_total) - int(up_base)
    if min(dlt, upt, dle, upe) < 0:
        raise ValueError(f"负 delta(计数器回落须先关块重立基线): dl={dlt}, up={upt}, dl_end={dle}, up_end={upe}")
    return (
        f"z,{_fmt_int(rec.run_len)},{_fmt_int(dlt)},{_fmt_int(upt)},{_fmt_int(dle)},{_fmt_int(upe)}"
        f"{_fmt_dt_tail(rec.dt_ms)}"
    )


def format_v4_n_row(rec: V4NullRun) -> str:
    """null 游程行文本(v4 §01, 行型与 v3 不变): n,<run_len>[,<dt_ms>]"""
    return f"n,{_fmt_int(rec.run_len)}{_fmt_dt_tail(rec.dt_ms)}"


def format_v4_day_text(key: str, blocks: tuple) -> str:
    """v4 天文件整文件文本(头行 v4 + key 行 + 逐块 B 行[二态携带块基线] 与记录行; \\n
    行尾, 对齐 v3 输出纪律)。批 2 flush 的批量写入口形态; 本函数只做序列化, 不触文件
    系统。r/z 行 delta 由块基线减法序列化 —— 无基线块内 r/z 在此 fail-fast(与解析守卫
    同源)。"""
    lines = [HEADER_LINE_V4, f"key,{key}"]
    for b in blocks:
        lines.append(format_v4_b_row(b.start_epoch, b.interval_s, b.dl_base, b.up_base))
        for rec in b.records:
            if isinstance(rec, V4Sample):
                lines.append(format_v4_r_row(rec, b.dl_base, b.up_base))
            elif isinstance(rec, V4ZeroRun):
                lines.append(format_v4_z_row(rec, b.dl_base, b.up_base))
            else:
                lines.append(format_v4_n_row(rec))
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class V4DayResume:
    """天文件增量解析续点(parse_v4_day_text resume=/with_resume=True; F4-1 计划
    26-11-15-1104): 「整行收尾的前缀解析状态」—— 前缀按整行边界消费完(文本以 \\n 结束)
    时的块状态机快照与计数。只追加不变式下, 对 (前缀 + 新增字节) 以 resume= 续解 ==
    对拼接文本的整文件全量重解析(逐位等价; 块/槽/坏行计数/撕裂尾全同源 —— 行循环与
    块状态机同一实现, 见 _parse_v4_text resumed= 与 _V4DayBlockMachine)。

    key = 头行 key 行标识; 前缀侧 key=None(头行门闩失守/缺 key 行)不可续解(续解会
    丢头行门闩语义) —— parse_v4_day_text 不产出这种续点(守卫在此单点)。
    blocks = 已封口块(开放块之前); open_* = 开放块(末个 B 行的块, records 可为空,
    None = 前缀尚无 B 行); bad_lines/data_lines = 前缀计数(续解自此累加)。
    """

    key: Optional[str]
    bad_lines: int
    data_lines: int
    blocks: tuple  # Tuple[V4Block, ...](已封口, 文件序)
    open_start: Optional[int]
    open_interval: Optional[float]
    open_dl_base: Optional[int]
    open_up_base: Optional[int]
    open_records: tuple  # Tuple[V4Sample | V4ZeroRun | V4NullRun, ...](开放块已收记录)


class _V4DayBlockMachine:
    """天文件块状态机(parse_v4_day_text 行型分支单点; B/r/z/n 全部行型语义唯一实现)

    从 parse_v4_day_text 的闭包形态原样搬移(行为零改动, 守阵回归钉住); 类化只为
    F4-1 增量解析能复位状态: resume= 构造即从前缀续点接续(已封口块 + 开放块状态),
    后续行语义与前缀是同一次解析完全一致 —— 不存在第二套行型判定。
    """
    def __init__(self, resume: Optional[V4DayResume] = None) -> None:
        if resume is None:
            self._blocks: list = []
            self._start: Optional[int] = None
            self._interval: Optional[float] = None
            self._dl_base: Optional[int] = None
            self._up_base: Optional[int] = None
            self._records: list = []
        else:
            self._blocks = list(resume.blocks)
            self._start = resume.open_start
            self._interval = resume.open_interval
            self._dl_base = resume.open_dl_base
            self._up_base = resume.open_up_base
            self._records = list(resume.open_records)

    def _close(self) -> None:
        if self._start is not None and self._records:
            self._blocks.append(
                V4Block(
                    start_epoch=self._start,
                    interval_s=self._interval,
                    dl_base=self._dl_base,
                    up_base=self._up_base,
                    records=tuple(self._records),
                )
            )
        self._start = None
        self._interval = None
        self._dl_base = None
        self._up_base = None
        self._records = []

    def feed(self, parts: list) -> bool:
        # B/r/z/n 行型分支(纪律面全在 _parse_v4_text): True = 已消费;
        # False / ValueError / IndexError = 记坏(驱动器统一口径, data 语义不因来源分叉)
        if parts[0] == "B" and len(parts) in (3, 5):
            # 二态块头: 3 列无基线 / 5 列基线; 先解析校验再切换块状态(非法 B 行整行计坏,
            # 既有块不受影响); 基线列负值按坏行(_parse_nn_int 拒负)
            b_start = int(parts[1])
            b_interval = _parse_interval_s(parts[2])
            b_dl = _parse_nn_int(parts[3]) if len(parts) == 5 else None
            b_up = _parse_nn_int(parts[4]) if len(parts) == 5 else None
            self._close()
            self._start = b_start
            self._interval = b_interval
            self._dl_base = b_dl
            self._up_base = b_up
            return True
        if self._start is None:
            raise ValueError("块头前出现数据行")  # 游标无锚点, 记坏不消费
        if self._dl_base is None and parts[0] in ("r", "z"):
            raise ValueError("无基线块内出现 r/z(仅 n 游程合法)")  # 解析守卫, 整行坏
        if parts[0] == "r" and len(parts) in (5, 6):
            self._records.append(
                V4Sample(
                    dl_rate=_parse_nn_int(parts[1]),
                    up_rate=_parse_nn_int(parts[2]),
                    # delta 以块基线逐行复原绝对值(基线 + 本行 delta, 逐行独立 —— 坏行不传播);
                    # 负 delta 在 _parse_nn_int 即抛(免费校验)
                    dl_total=self._dl_base + _parse_nn_int(parts[3]),
                    up_total=self._up_base + _parse_nn_int(parts[4]),
                    dt_ms=_parse_dt_ms(parts[5]) if len(parts) == 6 else None,
                )
            )
            return True
        if parts[0] == "z" and len(parts) in (4, 5, 6, 7):
            # 形态 D(plan 26-10-16-1509 §04): 6/7 列 = 携带末端快照对(块基线 + 列 delta);
            # 4/5 列 = 旧文件无末端列 -> None(agg 摊配按开启快照退化, 向后兼容)
            if len(parts) >= 6:
                dl_end, up_end = self._dl_base + _parse_nn_int(parts[4]), self._up_base + _parse_nn_int(parts[5])
                dt_ms = _parse_dt_ms(parts[6]) if len(parts) == 7 else None
            else:
                dl_end, up_end = None, None
                dt_ms = _parse_dt_ms(parts[4]) if len(parts) == 5 else None
            self._records.append(
                V4ZeroRun(
                    run_len=_parse_pos_int(parts[1]),
                    dl_total=self._dl_base + _parse_nn_int(parts[2]),
                    up_total=self._up_base + _parse_nn_int(parts[3]),
                    dt_ms=dt_ms,
                    dl_total_end=dl_end,
                    up_total_end=up_end,
                )
            )
            return True
        if parts[0] == "n" and len(parts) in (2, 3):
            self._records.append(
                V4NullRun(
                    run_len=_parse_pos_int(parts[1]),
                    dt_ms=_parse_dt_ms(parts[2]) if len(parts) == 3 else None,
                )
            )
            return True
        return False  # 键名/列数不匹配(整行记坏, 游标不推进)

    def resume_state(self, key: Optional[str], bad: int, data: int) -> V4DayResume:
        """续点快照(必须在 build/_close 之前取: blocks 不含开放块, 开放块单独在 open_*)"""
        return V4DayResume(
            key=key,
            bad_lines=bad,
            data_lines=data,
            blocks=tuple(self._blocks),
            open_start=self._start,
            open_interval=self._interval,
            open_dl_base=self._dl_base,
            open_up_base=self._up_base,
            open_records=tuple(self._records),
        )

    def build(self, key: Optional[str], bad: int, data: int, torn_tail: bool) -> V4ParsedDay:
        self._close()
        return V4ParsedDay(key=key, blocks=tuple(self._blocks), bad_lines=bad, data_lines=data, torn_tail=torn_tail)


def parse_v4_day_text(text: str, *, resume: Optional[V4DayResume] = None, with_resume: bool = False) -> Any:
    """v4 天文件文本 -> V4ParsedDay(纯函数, 无文件访问; v4 计划 §01 行型定约)

    头行必须恰为 HEADER_LINE_V4: 缺失/不符(含 v1/v2/v3 旧头行 —— R2 换代, 不设双读)
    整文件不匹配格式, 全部行记坏。B 行二态: 3 列 = 无基线块(块内仅 n 游程合法, 出现 r/z
    即坏行 —— 解析守卫), 5 列 = 基线块(dl_base/up_base = 块内首个带 totals 观测的快照)。
    r/z 行存相对块基线的 delta, 解析逐行复原绝对值(绝对值 = 基线 + 本行 delta;
    delta-vs-基线逐行独立 —— 坏行整行跳过、游标不推进, 后续行复原不受影响); 负 delta 必
    是损坏(免费校验: 计数器回落在绝对值形态合法, delta 形态非法, _parse_nn_int 即拒)。
    n 行不变。其余纪律 —— key 行取首个(重复记坏)/空行注释行跳过/坏行列数 r ∈ {5,6},
    z ∈ {4,5}, n ∈ {2,3}/dt_ms 须正整数且 <= DT_MS_MAX/撕裂尾半行豁免损坏占比/损坏占比
    分母 —— 原样沿用 v3 口径。
    !解析纪律骨架(头行门闩 / data+bad 计数 / 空行注释跳 / split(",") / try-except /
    撕裂尾豁免 / key 首个消费)单点在 _parse_v4_text(issue 26-10-29-1304 R07-T06 收敛),
    本函数只留 B/r/z/n 行型分支与块状态机(_V4DayBlockMachine); 块头前数据行 / 无基线块
    r/z 两个解析守卫以 ValueError 抛给驱动器, 与字段非法同走吞异常计坏路径(data 不分叉)。

    F4-1 增量解析(计划 26-11-15-1104, V4DayCache 消费):
    - resume=V4DayResume: 前缀续解 —— 行循环与块状态机同一实现复位接续, 语义 = 对
      (前缀 + text) 的整文件解析(逐位等价; 计数自前缀累加)。
    - with_resume=True: 返回 (V4ParsedDay, V4DayResume | None) —— 续点仅在文本整行收尾
      (以 \\n 结束)且 key 非 None(头行门闩已过)时产出; 撕裂尾/头行失守 = None(不可续,
      读侧退全量重解析)。续解段(with_resume+resume=)同规则产出链式续点。
    """
    machine = _V4DayBlockMachine(resume)
    if resume is None:
        key, bad, data, torn_tail = _parse_v4_text(text, machine.feed)
    else:
        key, bad, data, torn_tail = _parse_v4_text(
            text, machine.feed, resumed=(resume.key, resume.bad_lines, resume.data_lines)
        )
    cp: Optional[V4DayResume] = None
    if with_resume and text.endswith("\n") and key is not None:
        cp = machine.resume_state(key, bad, data)
    result = machine.build(key, bad, data, torn_tail)
    if with_resume:
        return result, cp
    return result
