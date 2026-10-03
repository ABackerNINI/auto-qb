"""traffic_grid: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1)

S4 API 读侧的取数口径, 全部纯函数(输入 traffic_store.ParsedSeries / 桶表, 输出响应段),
不触文件不触时钟 —— Web 线程直接调用, 单测可独立构造输入:

栅格离散(§05.1):
- [t0, t1) 按「栅格 = 采样间隔」离散: bucket = floor(t / interval) * interval; 桶内多行
  取速率均值; 空桶 = null。24h 窗消费 raw 段(桶宽 = sample_interval, ≈2880 桶), 30d 窗
  消费 hour 段(hour_epoch 即桶键, 桶宽恒 3600s, 720 点, 桶内不再聚合)。
- raw 行时间戳不对齐栅格(qB 重连退避/主循环抖动都会让采样时刻漂移, §05.1), 抖动行按
  floor 归桶; 窗首桶允许不满宽(t0 未对齐时首桶只覆盖 [first, t0) 之后的部分 —— 行照收)。

totals 段(§05.1, 单系列):
- 相邻桶累计快照差分: delta = cur - last(cur >= last 时天然非负, 即 max(0,·));
  cur < last 判计数器重置 -> 该桶增量 null(§03.4 同款, dl/up 两向独立判定, 对齐采样器
  _delta 逐向口径); 前桶无快照(窗首/空桶断链)= 基线缺失 -> null。桶内快照取最新非 null
  行的累计对(raw)或 hour 行累计对(hour, 本小时末快照口径与封口一致)。

组读侧聚合(§04.1, API 层现算不做聚合缓存):
- 速率 = 各成员序列栅格离散到桶 -> 桶内 Σ 成员均值; 桶内无行成员按 0 计;
- 累计增量 = 逐成员先差分(max(0,·) + 回落判重置贡献 0 + 基线缺失贡献 0)再求和 ——
  先逐成员差分再相加, 避免单成员计数器重置把全组差分打成大负数; 组口径宁可少计一桶
  不出洞(§04.1-③);
- 桶 null 判定借全局系列当真值源(§04.1-④): 桶在全局系列为 null(程序停机/qB 断连) ->
  null; 桶早于组内全部成员文件的最早行(组尚无任何观测)-> null; 其余桶即使全员空闲也出
  0 —— 组图空闲段 0 线、停机段断线, 二者靠全局系列区分。
"""
import math
import time
from dataclasses import dataclass
from typing import Optional

from .traffic_store import HOUR_SECONDS, ParsedSeries

#: 窗口名 -> (跨度秒, 消费段): 24h 只消费 raw 段, 30d 只消费 hour 段(§05.1/§08)
WINDOW_SPECS = {"24h": (86400, "raw"), "30d": (2592000, "hour")}

#: 24h 窗栅格宽的兜底值(qb_traffic 缺省 = 未启用时的空态 meta; 与配置缺省 30S 同值)
DEFAULT_SAMPLE_INTERVAL_S = 30.0


@dataclass(frozen=True)
class WindowGrid:
    """一次取数的时间栅格(§05.1): [t0, t1) 按 interval 离散出的固定桶序

    buckets 长度 = ceil((t1 - first) / interval)(窗首桶对齐 floor(t0/interval), t0 未对齐
    时比「跨度/interval」恰多一桶 —— §05.1 的「≈2880 桶」口径); 桶值 t = 桶起点 epoch 秒。
    """

    name: str  # "24h" | "30d"
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
        raise ValueError(f"未知窗口: {window!r}(须为 24h|30d)") from None
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
    """单系列 -> 桶键 -> BucketObs(按窗口消费段分派: raw 归桶聚合 / hour 直接对位)"""
    if grid.segment == "raw":
        return _obs_from_raw(parsed.raw, grid)
    return _obs_from_hours(parsed.hours, grid)


def _obs_from_raw(rows: tuple, grid: WindowGrid) -> dict:
    """raw 行归桶(§05.1): 桶内多行速率取均值; 快照取桶内最新非 null 行的累计对"""
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
    """单种文件最早观测行时刻(raw 采样行 + hour 封口行全算 —— null 行也是一次观测);
    无任何行(无文件/零行)= None(组尚无任何观测, §04.1-④)"""
    cands = [r.ts for r in parsed.raw]
    cands.extend(h.hour_epoch for h in parsed.hours)
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
