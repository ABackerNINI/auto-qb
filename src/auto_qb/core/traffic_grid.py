"""traffic_grid: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1)

S4 API 读侧的取数口径, 全部纯函数(输入 traffic_store.ParsedSeries / 桶表, 输出响应段),
不触文件不触时钟 —— Web 线程直接调用, 单测可独立构造输入:

栅格离散(§05.1):
- [t0, t1) 按「栅格 = 采样间隔」离散: bucket = floor(t / interval) * interval; 桶内多行
  取速率均值; 空桶 = null。raw 段窗口(1m/5m/30m/3h/6h/12h/24h)消费 raw 段(桶宽 =
  sample_interval, 24h 窗 ≈2880 桶), hour 段窗口(3d/7d/30d)消费 hour 段(hour_epoch 即
  桶键, 桶宽恒 3600s, 30d 窗 720 点, 桶内不再聚合)。
- z 零值行程行(plan 26-10-04-0721 §04.1)覆盖展开: 行程闭区间 [start, end] 相交的每个桶
  (start < b+w 且 end >= b)获得速率 (0,0) 观测, totals = 行程快照 —— 空闲段 0 平线;
  混桶 raw 优先(桶内同时有 raw 行与 z 覆盖时取 raw 聚合结果, z 让位)。
- raw 行时间戳不对齐栅格(qB 重连退避/主循环抖动都会让采样时刻漂移, §05.1), 抖动行按
  floor 归桶; 窗首桶允许不满宽(t0 未对齐时首桶只覆盖 [first, t0) 之后的部分 —— 行照收)。

totals 段(§05.1, 单系列):
- 相邻桶累计快照差分: delta = cur - last(cur >= last 时天然非负, 即 max(0,·));
  cur < last 判计数器重置 -> 该桶增量 null(§03.4 同款, dl/up 两向独立判定, 对齐采样器
  _delta 逐向口径); 前桶无快照(窗首/空桶断链)= 基线缺失 -> null。桶内快照取最新非 null
  行的累计对(raw)或 hour 行累计对(hour, 本小时末快照口径与封口一致); z 派生桶携带行程
  快照参与差分 —— 空闲段每桶 delta = 0 链不断, 其后首个活跃桶恢复有基线(plan §04.1)。

组读侧聚合(§04.1, API 层现算不做聚合缓存):
- 速率 = 各成员序列栅格离散到桶 -> 桶内 Σ 成员均值; 桶内无行成员按 0 计;
- 累计增量 = 逐成员先差分(max(0,·) + 回落判重置贡献 0 + 基线缺失贡献 0)再求和 ——
  先逐成员差分再相加, 避免单成员计数器重置把全组差分打成大负数; 组口径宁可少计一桶
  不出洞(§04.1-③);
- 桶 null 判定借全局系列当真值源(§04.1-④): 桶在全局系列为 null(程序停机/qB 断连) ->
  null; 桶早于组内全部成员文件的最早行(组尚无任何观测)-> null; 其余桶即使全员空闲也出
  0 —— 组图空闲段 0 线、停机段断线, 二者靠全局系列区分。

v3 读侧核心(plan 26-10-04-1957 S3a, §05.1/§05.2 —— 文件尾 v3 区):
- 分层纯化: 天文件(V3ParsedDay, 经 traffic_store.V3DayCache 按天加载 + 解析缓存) ->
  块序列 ->(S1 游标 dt 链 v3_block_slots)-> 记录时间轴 ->(逐记录有效 dt 桶宽 + D1 跨桶
  覆盖 + 块间真空)-> 有序桶点列。S3b 的 agg 段(hour/day/month)合流在「桶点」层面并流,
  天文件读取不经本模块任何单一入口硬编码。
- 桶点模型(D1 实施期定稿, 逐记录覆盖桶): 每个观测槽生成一个覆盖桶, 桶宽 = 桶宽(有效dt),
  桶 = [t, ceil(ts)), t = ceil(ts) - w —— 单记录的桶天然覆盖其有效 dt 全程, 标称栅格视角
  下「单记录跨多桶、中间桶同值非 null」由宽桶等价承载; z 游程按均摊槽展开为多桶(rate 同值
  (0,0)、totals 同快照)是覆盖语义的字面形态。v2 组读侧聚合(借 global 判 null)与视图映射
  (WINDOW_SPECS/agg 段)属 S3b, 本阶段不动。
"""
import math
import time
from dataclasses import dataclass
from typing import Optional

from .traffic_store import (
    HOUR_SECONDS,
    ParsedSeries,
    V3Block,
    v3_block_slots,
    v3_bucket_width_s,
)

#: 窗口名 -> (跨度秒, 消费段): 1m-24h 消费 raw 段(桶宽 = 采样间隔), 3d/7d/30d 消费 hour 段
#: (桶宽恒 3600s)(§05.1/§08)。1m/5m/30m/3h/6h/12h/24h 与 qB 速度图窗口对齐, 3d/7d 为外延。
WINDOW_SPECS = {
    "1m": (60, "raw"),
    "5m": (300, "raw"),
    "30m": (1800, "raw"),
    "3h": (10800, "raw"),
    "6h": (21600, "raw"),
    "12h": (43200, "raw"),
    "24h": (86400, "raw"),
    "3d": (259200, "hour"),
    "7d": (604800, "hour"),
    "30d": (2592000, "hour"),
}

#: 24h 窗栅格宽的兜底值(qb_traffic 缺省 = 未启用时的空态 meta; 与配置缺省 30S 同值)
DEFAULT_SAMPLE_INTERVAL_S = 30.0


@dataclass(frozen=True)
class WindowGrid:
    """一次取数的时间栅格(§05.1): [t0, t1) 按 interval 离散出的固定桶序

    buckets 长度 = ceil((t1 - first) / interval)(窗首桶对齐 floor(t0/interval), t0 未对齐
    时比「跨度/interval」恰多一桶 —— §05.1 的「≈2880 桶」口径); 桶值 t = 桶起点 epoch 秒。
    """

    name: str  # WINDOW_SPECS 键(1m-30d)
    t0: int  # 窗口起点(含), epoch 秒
    t1: int  # 窗口终点(不含), epoch 秒
    interval: int  # 桶宽秒(24h = 采样间隔, 30d = 3600)
    segment: str  # 消费段: "raw" | "hour"
    buckets: tuple  # Tuple[int, ...] 桶起点序列(升序)

    @property
    def first(self) -> int:
        return self.buckets[0]

    @property
    def last(self) -> int:
        return self.buckets[-1]


def build_grid(window: str, now: float, sample_interval: float = DEFAULT_SAMPLE_INTERVAL_S) -> WindowGrid:
    """窗口名 + 当前时刻 -> 时间栅格(纯函数; sample_interval 只在 raw 段生效)"""
    try:
        span, segment = WINDOW_SPECS[window]
    except KeyError:
        raise ValueError(f"未知窗口: {window!r}(须为 {'|'.join(WINDOW_SPECS)})") from None
    # 桶宽对采样间隔向上取整(floor 在小数间隔如 1.5s 下取 1s 桶宽, 采样行 1.5s 一条 -> 隔桶为空 = 伪断线;
    # ceil 后桶宽 >= 采样间隔, 等间隔采样行每桶至少一条)
    interval = max(1, math.ceil(sample_interval)) if segment == "raw" else HOUR_SECONDS
    t1 = int(now)
    t0 = t1 - span
    first = t0 - (t0 % interval)  # floor 对齐(epoch 恒正)
    n = (t1 - first + interval - 1) // interval  # ceil
    return WindowGrid(window, t0, t1, interval, segment, tuple(first + i * interval for i in range(n)))


def grid_for_now(window: str, sample_interval: float = DEFAULT_SAMPLE_INTERVAL_S) -> WindowGrid:
    """以当前时刻建栅格(API 层入口; 纯函数版 build_grid 的现在时包装)"""
    return build_grid(window, time.time(), sample_interval)


@dataclass(frozen=True)
class BucketObs:
    """单桶观测(§05.1 归桶结果): 速率均值 + 桶末累计快照"""

    dl_rate: int  # 桶内下载速率均值(bytes/s, round 取整, 口径对齐封口 _aggregate_bucket)
    up_rate: int
    dl_total: Optional[int]  # 桶末 all-time 下载累计快照(bytes; raw 取最新行, hour 取封口行)
    up_total: Optional[int]


def series_bucket_obs(parsed: ParsedSeries, grid: WindowGrid) -> dict:
    """单系列 -> 桶键 -> BucketObs(按窗口消费段分派: raw 归桶聚合(含 z 行程覆盖展开) / hour 直接对位)"""
    if grid.segment == "raw":
        return _obs_from_raw(parsed.raw, parsed.zruns, grid)
    return _obs_from_hours(parsed.hours, grid)


def _obs_from_raw(rows: tuple, zruns: tuple, grid: WindowGrid) -> dict:
    """raw 行归桶(§05.1): 桶内多行速率取均值; 快照取桶内最新非 null 行的累计对

    z 行程覆盖展开(plan 26-10-04-0721 §04.1): 行程闭区间 [start, end] 相交的桶(桶
    [b, b+w), 条件 start < b+w 且 end >= b)获得速率 (0,0) 观测, totals = 行程快照 ——
    单点行程 [ts, ts] 闭区间语义天然覆盖所在桶。混桶 raw 优先: 已有 raw 聚合结果的桶
    z 覆盖让位(确定性规则, 一个桶的粒度图上不可见); 多行程覆盖同桶取文件序首个。
    """
    first, last, interval, t1 = grid.first, grid.last, grid.interval, grid.t1
    acc = {}  # 桶键 -> [dl_sum, up_sum, n, last_ts, dl_total, up_total]
    for r in rows:
        if r.dl_rate is None or r.ts >= t1:  # null 点不参与归桶(空值行只表达断连, §03.5)
            continue
        b = r.ts - (r.ts % interval)
        if b < first or b > last:
            continue  # 窗外行不消费(24h 窗只看 raw 窗内的桶)
        a = acc.get(b)
        if a is None:
            acc[b] = [r.dl_rate, r.up_rate, 1, r.ts, r.dl_total, r.up_total]
            continue
        a[0] += r.dl_rate
        a[1] += r.up_rate
        a[2] += 1
        if r.ts >= a[3]:  # 桶末快照 = 最新行(同刻行取后到者, 快照单调不减口径一致)
            a[3] = r.ts
            a[4] = r.dl_total
            a[5] = r.up_total
    out = {}
    for b, a in acc.items():
        n = a[2]
        out[b] = BucketObs(int(round(a[0] / n)), int(round(a[1] / n)), a[4], a[5])
    for z in zruns:
        b = z.start - (z.start % interval)
        top = z.end - (z.end % interval)
        while b <= top:
            if first <= b <= last and b not in out:  # 窗外桶不消费; 混桶 raw 优先
                out[b] = BucketObs(0, 0, z.dl_total, z.up_total)
            b += interval
    return out


def _obs_from_hours(rows: tuple, grid: WindowGrid) -> dict:
    """hour 行对位(§05.1): hour_epoch 即桶键, 桶内不再聚合(封口已按小时归并)"""
    first, last, t1 = grid.first, grid.last, grid.t1
    out = {}
    for h in rows:
        b = h.hour_epoch
        if b < first or b > last or b >= t1:
            continue
        out[b] = BucketObs(h.dl_avg, h.up_avg, h.dl_total, h.up_total)
    return out


def rate_points(obs: dict, grid: WindowGrid) -> list:
    """速率段(§08 points): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)"""
    out = []
    for b in grid.buckets:
        o = obs.get(b)
        out.append(None if o is None else {"t": b, "dl": o.dl_rate, "up": o.up_rate})
    return out


def _bucket_delta(cur: Optional[int], last: Optional[int]) -> Optional[int]:
    """累计快照差分(§05.1): max(0,·) 的等价形 + 回落判重置 -> null; 基线缺失 -> None"""
    if cur is None or last is None:
        return None
    if cur < last:
        return None  # 计数器重置(qB 非优雅重启/删种重加): 该桶增量 null, 绝不产负增量
    return cur - last


def series_totals_points(obs: dict, grid: WindowGrid) -> list:
    """累计增量段(§08 totals, 单系列): 相邻桶快照差分

    前桶无快照(窗首基线缺失/空桶断链)-> 该桶 null; 空桶本身 null 且断链后继(下一有观测
    桶同样基线缺失)。dl/up 两向独立判定(对齐采样器 _delta 逐向口径)。
    """
    out = []
    prev = None  # 相邻前桶快照(dl_total, up_total)
    for b in grid.buckets:
        o = obs.get(b)
        if o is None:
            out.append(None)
            prev = None
            continue
        dl = _bucket_delta(o.dl_total, prev[0]) if prev is not None else None
        up = _bucket_delta(o.up_total, prev[1]) if prev is not None else None
        out.append({"t": b, "dl": dl, "up": up})
        prev = (o.dl_total, o.up_total)
    return out


def earliest_row_ts(parsed: ParsedSeries) -> Optional[int]:
    """单种文件最早观测行时刻(raw 采样行 + hour 封口行 + z 行程行全算 —— null 行也是
    一次观测, z 行的 start 是一次真实观测(plan 26-10-04-0721 §04.3));
    无任何行(无文件/零行)= None(组尚无任何观测, §04.1-④)"""
    cands = [r.ts for r in parsed.raw]
    cands.extend(h.hour_epoch for h in parsed.hours)
    cands.extend(z.start for z in parsed.zruns)
    return min(cands) if cands else None


def group_null_mask(global_obs: dict, grid: WindowGrid, earliest_member_ts: Optional[int]) -> list:
    """组桶 null 判定(§04.1-④, 借全局系列当真值源) -> bool 列表(True = 该桶 null)

    - 桶不在全局观测表(全局无行 = 程序停机; 全 null 行 = qB 断连 —— 空值行不进观测表)
      -> null: 组图停机段断线;
    - 桶早于组内全部成员文件的最早行(桶末 <= 最早行时刻, 组尚无任何观测)-> null;
    - 其余桶即使全员空闲也非 null(组图空闲段出 0 线, 由聚合层填 0)。
    """
    mask = []
    interval = grid.interval
    for b in grid.buckets:
        if b not in global_obs:
            mask.append(True)
        elif earliest_member_ts is not None and b + interval <= earliest_member_ts:
            mask.append(True)
        else:
            mask.append(False)
    return mask


def group_rate_points(member_obs: list, grid: WindowGrid, null_mask: list) -> list:
    """组速率段(§04.1-②): 桶内 Σ 成员均值; 桶内无行成员按 0 计; null 桶 -> None"""
    out = []
    for i, b in enumerate(grid.buckets):
        if null_mask[i]:
            out.append(None)
            continue
        dl = 0
        up = 0
        for obs in member_obs:
            o = obs.get(b)
            if o is not None:
                dl += o.dl_rate
                up += o.up_rate
        out.append({"t": b, "dl": dl, "up": up})
    return out


def group_totals_points(member_obs: list, grid: WindowGrid, null_mask: list) -> list:
    """组累计增量段(§04.1-③): 逐成员先差分(max(0,·) + 重置/基线缺失贡献 0)再求和

    成员某桶增量缺失(无行/重置/基线缺失)按 0 计 —— 宁可少计一桶不出洞; null 桶整桶
    None 且桶链断开(null 桶之后成员基线同样缺失, 与单系列相邻桶口径一致)。
    """
    prevs = [None] * len(member_obs)  # 逐成员的相邻前桶快照
    out = []
    for i, b in enumerate(grid.buckets):
        if null_mask[i]:
            out.append(None)
            prevs = [None] * len(member_obs)
            continue
        dl = 0
        up = 0
        for j, obs in enumerate(member_obs):
            o = obs.get(b)
            if o is None:
                prevs[j] = None  # 成员本桶无快照: 自身链断, 下桶基线缺失贡献 0
                continue
            p = prevs[j]
            if p is not None:
                if o.dl_total >= p[0]:  # cur < last 重置: 贡献 0(不把全组差分打成大负数)
                    dl += o.dl_total - p[0]
                if o.up_total >= p[1]:
                    up += o.up_total - p[1]
            prevs[j] = (o.dl_total, o.up_total)
        out.append({"t": b, "dl": dl, "up": up})
    return out


# ======================================================================
# v3 读侧核心(plan 26-10-04-1957 S3a, §05.1/§05.2)
#
# 分层纯化(为 S3b 留接缝): 天文件解析产物(V3ParsedDay.blocks) -> 本层 v3_series_slots
# (记录时间轴, S3b agg 段合流的并流点) -> v3_series_points(桶点) -> v3_totals_points
# (累计增量)。天文件读取在 traffic_store.V3DayCache(按天加载 + mtime/size 解析缓存);
# 本模块不触文件不触时钟, 视图映射(WINDOW_SPECS/agg 段/组端点)属 S3b。
#
# 归桶模型(D1 实施期定稿: 逐记录覆盖桶):
# - 每个观测槽(r/z)生成一个覆盖桶: 桶宽 w = v3_bucket_width_s(有效dt)(S1 槽层的 dt_s =
#   显式 dt 或游程均摊 span/run_len), 桶 = [t, ceil(ts)), t = ceil(ts) - w。
#   替代 v2 全局 ceil(sample_interval) 一刀切(traffic_grid.py:91) —— 混排 interval 分块
#   各归各桶, 抖动/漂移不再制造空桶(A2 伪断线根因的读侧残留一并消除)。
# - 桶起点锚定实测时刻(ceil(ts) - w), 无累积漂移 —— 「按桶宽向前铺格」的替代方案会被
#   每行 ceil(dt)-dt ∈ [0,1) 的单调累积拖偏(稳态小漂移退化逐行显式 dt 时块尾可达数十秒),
#   已否决; 锚定式桶起点与实测时刻的偏差恒 < 1 个桶宽。
# - D1 跨桶覆盖: 记录的覆盖区间 [ts-w, ts] 整段由该记录的桶承载 —— 桶宽 = ceil(有效dt)
#   使单记录天然覆盖其有效 dt 全程; 标称栅格视角下「单记录跨多桶、中间桶同值非 null」的
#   语义由宽桶等价实现(观测非 null、rate 同值、totals 同快照都由这一个桶给出), 折线在
#   暂停段不伪断; z 游程按 S1 均摊槽展开为多桶(每桶 rate (0,0) + 同一游程快照)是覆盖
#   语义的字面形态。混桶 raw 优先口径沿用 v2(同 key 合并规则)。
# - 同桶合并(混桶): 同 key 两观测槽 —— raw 优先于 z; raw+raw 速率取均值、快照取最新行
#   (同刻取后到者); z+z 取先到者(v2 多行程同桶口径)。
# - 真空 vs 断连两语义分离(§05.1): 块间 gap 中未被下一块首记录覆盖桶吸收的差值段为真空,
#   出一个 null 点(t = 上一块游标终值取整)断线; gap <= 首槽桶宽(00:00 硬切的 <=1 间隔
#   天然 gap)被首记录覆盖桶吸收不出 null。程序停机 = 无块 = 天然真空(无任何点);
#   断连(程序活着)= n 槽 -> 连续 null 槽折叠为一个 null 点(首槽位置取整)。两者都是
#   null 点, 但来源不同: 真空无任何观测, n 槽是显式 null 观测。
# - 窗口 [t0, t1): 槽 ts >= t1 不消费; 覆盖桶触及窗口左界(ceil(ts) >= t0)才保留 ——
#   桶首允许略早于 t0(上界一个桶宽, 行照收, 对齐 v2 窗首口径); null 点按 t 过滤。
# ======================================================================

#: 真空判定浮点容差(秒): 块间 gap 与首记录覆盖桶的比较 ε
_V3_VACUUM_EPS_S = 1e-6


@dataclass(frozen=True)
class V3PointEntry:
    """v3 读侧单桶点(S3a 桶点层输出, S3b 视图映射的输入形态)

    t = 桶起点 epoch 秒(覆盖桶 [t, t+w), w = 该记录桶宽 —— 响应层如需宽度可由
    v3_bucket_width_s 对有效 dt 复原); rate/totals 全 None = null 点(n 游程/块间真空
    标记, 断线语义 —— v3 r/z 行无 null 形态, null 只来自这两种标记)。
    """

    t: int  # 桶起点 epoch 秒
    dl_rate: Optional[int] = None  # 桶内下载速率均值(bytes/s, round 取整)
    up_rate: Optional[int] = None
    dl_total: Optional[int] = None  # 桶末 all-time 下载累计快照(bytes)
    up_total: Optional[int] = None


@dataclass(frozen=True)
class V3TotalsEntry:
    """v3 单桶点累计增量(v3_totals_points 输出): dl/up = 相邻桶快照差分, None = null"""

    t: int
    dl: Optional[int]
    up: Optional[int]


def v3_series_slots(blocks: tuple) -> tuple:
    """块序列 -> 扁平槽序(记录时间轴层; S3b agg 段合流的接缝): 块按 start_epoch 升序
    (稳定排序, 同刻保文件序), 逐块 v3_block_slots 展开(复用 S1 游标 dt 链, 不另写推算)。"""
    out = []
    for blk in sorted(blocks, key=lambda b: b.start_epoch):
        out.extend(v3_block_slots(blk))
    return tuple(out)


def v3_series_points(blocks: tuple, t0: float, t1: float) -> tuple:
    """v3 读侧核心(§05.1/§05.2): 块序列 -> 窗口 [t0, t1) 内按 t 升序的桶点列

    blocks = V3Block 序列(单系列的若干天文件解析产物合并传入; 天文件按日期升序读出,
    块不跨天故按 start_epoch 排序即恢复时间序)。归桶/覆盖/真空/合并规则见本区头注释。
    无块(停机/无数据)返回空元组(天然真空, 调用方按空态处理)。
    """
    cells = {}  # 桶键 -> [is_raw, dl_sum, up_sum, n, last_ts, dl_total, up_total]
    marks: list = []  # null 点 (t, ...) —— n 游程折叠 + 块间真空
    prev_chain_end: Optional[float] = None
    last_was_null = False
    for block in sorted(blocks, key=lambda blk: blk.start_epoch):
        slots = v3_block_slots(block)
        if not slots:
            continue
        if prev_chain_end is not None:
            first_w = v3_bucket_width_s(slots[0].dt_s)
            # 真空: 下一块首记录覆盖桶起点晚于上一块游标终值 -> 差值段出 null 点
            if math.ceil(slots[0].ts) - first_w > prev_chain_end + _V3_VACUUM_EPS_S:
                marks.append(int(prev_chain_end))
        for s in slots:
            if s.obs is None:
                # n 槽: 连续 null 槽折叠为一个 null 点(首槽位置取整; 断连语义)
                t = int(math.floor(s.ts))
                if t0 <= t < t1 and not last_was_null:
                    marks.append(t)
                last_was_null = True
                continue
            last_was_null = False
            if s.ts >= t1:
                continue  # 窗尾之后的槽不消费(v2 ts >= t1 口径)
            w = v3_bucket_width_s(s.dt_s)
            key = math.ceil(s.ts) - w
            if key + w < t0:  # 覆盖桶不触及窗口左界(桶 [key, key+w) 与 [t0, t1) 无交集)
                continue
            o = s.obs
            e = cells.get(key)
            if e is None:
                cells[key] = [not s.is_zero, o[0], o[1], 1, s.ts, o[2], o[3]]
            elif not s.is_zero:
                if e[0]:  # raw+raw: 速率均值 + 最新行快照(同刻取后到者, v2 口径)
                    e[1] += o[0]
                    e[2] += o[1]
                    e[3] += 1
                    if s.ts >= e[4]:
                        e[4] = s.ts
                        e[5] = o[2]
                        e[6] = o[3]
                else:  # raw 到 z 桶: 混桶 raw 优先(v2 口径沿用)
                    e[0] = True
                    e[1], e[2], e[3], e[4], e[5], e[6] = o[0], o[1], 1, s.ts, o[2], o[3]
            # z 到 raw 桶: raw 优先, z 让位; z 到 z 桶: 先到者保留(v2 多行程同桶口径)
        prev_chain_end = slots[-1].ts  # 游标终值 = 末槽实测时刻(真空判定基准)
    entries = []
    for key in sorted(cells):
        e = cells[key]
        n = e[3]
        entries.append((key, 1, V3PointEntry(key, int(round(e[1] / n)), int(round(e[2] / n)), e[5], e[6])))
    for t in marks:
        if t0 <= t < t1:
            entries.append((t, 0, V3PointEntry(t)))
    # null 点排同刻观测点之前(null 在先 = 该时刻断线、其后才是观测覆盖; 稳定保插入序)
    entries.sort(key=lambda x: (x[0], x[1]))
    return tuple(e for _, _, e in entries)


def v3_totals_points(points: tuple) -> tuple:
    """v3 累计增量段(§05.1): 相邻桶点快照差分 —— v2 规则平移(series_totals_points):
    max(0,·) 等价形 + cur < last 判计数器重置 -> null + 基线缺失(窗首/null 点断链)->
    null; dl/up 两向独立判定。游程快照(z 槽桶 totals 恒定)进差分链 —— 空闲段每桶
    delta = 0 链不断, 其后首个活跃桶恢复有基线; 宽桶(跨桶覆盖)的 delta 覆盖其整段
    有效 dt(暂停期真实增量落在恢复记录的一桶里)。"""
    out = []
    prev = None  # 相邻前桶点快照(dl_total, up_total)
    for p in points:
        if p.dl_rate is None:  # null 点: 断线且断链
            out.append(V3TotalsEntry(t=p.t, dl=None, up=None))
            prev = None
            continue
        dl = _bucket_delta(p.dl_total, prev[0]) if prev is not None else None
        up = _bucket_delta(p.up_total, prev[1]) if prev is not None else None
        out.append(V3TotalsEntry(t=p.t, dl=dl, up=up))
        prev = (p.dl_total, p.up_total)
    return tuple(out)
