"""traffic_grid: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v3 读侧 plan 26-10-04-1957 S3a/S3b)

S4 API 读侧的取数口径, 全部纯函数(输入 v4 天文件块序列 / agg 行 / 栅格桶表, 输出响应段),
不触文件不触时钟 —— Web 线程直接调用, 单测可独立构造输入。v2 逐行格式的读侧(系列解析 /
raw 归桶 / z 行程覆盖展开 / 最早观测行)已随 S5 退役删除, 本模块即现行唯一读侧:

窗口与栅格(§05.1/§05.3, WINDOW_SPECS 13 档):
- raw 段窗(1m-24h): 桶宽 = 采样间隔(向上取整防伪断线), 桶 = floor 对齐; 数据经
  traffic_store.V4DayCache 按天加载 -> 块序列 -> v4_series_points 桶点 -> v4_grid_obs
  按重叠秒加权展开到栅格(D1 跨桶覆盖: 宽桶中间栅格桶同值非 null); 另合流采样模块
  活尾快照(S6: 未落盘记录 + 开放游程续链, 图面尾部随采样节拍实时, 不等 flush)。
- hour 段窗(3d/7d/30d): 桶宽恒 3600s, 消费 agg hour 行; day 段窗(6mo/1y): 滚动窗涉及
  本地日期逐日铺格(桶键 = 本地日界 00:00), 消费 agg day 行; month 段窗(all): 数据面定栅格
  (build_month_grid, 首末月行之间逐月铺格), 消费 agg month 行。agg 行 epoch 即栅格桶键
  (v4_agg_obs 直映, 桶内不再聚合)。

桶点模型(D1 实施期定稿, §05.1): 每个观测槽生成一个覆盖桶, 桶宽 = max(1, ceil(有效dt)),
桶 = [ceil(ts)-w, ceil(ts)) —— 单记录的桶天然覆盖其有效 dt 全程; z 游程按均摊槽展开为
多桶(rate 同值 (0,0)、totals 同快照)是覆盖语义的字面形态。块间真空与 n 游程断连都出
null 点, 来源不同(真空无观测 / 断连显式 null)。

totals 段(§05.1, 单系列与组共用差分层):
- 相邻桶累计快照差分: delta = cur - last; cur < last 判计数器重置 -> 该桶增量 null
  (dl/up 两向独立判定, 对齐采样器 _delta 逐向口径); 前桶无快照(窗首/空桶断链)= 基线
  缺失 -> null。z 槽桶快照恒定参与差分 —— 空闲段每桶 delta = 0 链不断。

组读侧聚合(§04.1 -> §05.4, API 层现算不做聚合缓存):
- 速率 = 各成员栅格桶观测 Σ 成员均值, 无行成员按 0 计;
- 累计增量 = 逐成员先差分(重置/基线缺失贡献 0)再求和 —— 宁可少计一桶不出洞;
- 桶 null 判定(v4): 桶内无任何成员观测 -> null —— 单成员的 r/z 观测即「程序存活且 qB
  在线」真值, 不借全局系列(组图 3d+ 窗 M 个成员各只读 1 个 agg 文件)。
"""
import math
import time
from dataclasses import dataclass
from typing import Optional

from .traffic_store import (
    HOUR_SECONDS,
    V4ParsedAgg,
    v4_block_slots,
    v4_bucket_width_s,
    v4_date_str_epoch,
    v4_next_month_epoch,
    v4_window_dates,
)

#: 窗口名 -> (跨度秒, 消费段): 1m-24h 消费 raw 天文件(桶宽 = 采样间隔), 3d/7d/30d 消费
#: agg hour 行(桶宽恒 3600s), 6mo/1y 消费 agg day 行(桶宽 = 本地日界 86400s, 滚动窗),
#: all 消费 agg month 行(数据面定栅格, build_month_grid)(§05.3, D4 档位: 10 -> 13 档,
#: 90d 延后 —— day 行照常产出, 视图可后补)。1m/5m/30m/3h/6h/12h/24h 与 qB 速度图窗口
#: 对齐; 6mo = now-182d..now, 1y = now-365d..now(滚动窗语义, 自然月边界只用于 month 行
#: 聚合粒度)。
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
    "6mo": (15724800, "day"),
    "1y": (31536000, "day"),
    "all": (0, "month"),
}

#: 本地日界桶宽(秒, 6mo/1y 的 day 段窗; day 行 epoch = 本地当日 00:00, 桶键与行键同源)
DAY_SECONDS = 86400

#: all 视图的标称月长(秒, meta.interval_s 供轮询夹取; 真实月长按行间隔 28-31 天不等,
#: 点位真值在 points[].t —— 前端按真值落点, 等距重建只兜底空槽位置, §05.3「月长(按行间隔)」)
MONTH_NOMINAL_S = 30 * DAY_SECONDS

#: 24h 窗栅格宽的兜底值(qb_traffic 缺省 = 未启用时的空态 meta; 与配置缺省 30S 同值)
DEFAULT_SAMPLE_INTERVAL_S = 30.0


@dataclass(frozen=True)
class WindowGrid:
    """一次取数的时间栅格(§05.1): [t0, t1) 按 interval 离散出的固定桶序

    buckets 长度 = ceil((t1 - first) / interval)(窗首桶对齐 floor(t0/interval), t0 未对齐
    时比「跨度/interval」恰多一桶 —— §05.1 的「≈2880 桶」口径); 桶值 t = 桶起点 epoch 秒。
    day 段窗(6mo/1y)例外: 桶键 = 本地日界 00:00(滚动窗 [t0, t1) 涉及的本地日期逐日铺格,
    窗首桶允许早于 t0 —— 首日不满宽); month 段窗(all)由 build_month_grid 数据面铺格。
    """

    name: str  # WINDOW_SPECS 键(1m-all)
    t0: int  # 窗口起点(含), epoch 秒
    t1: int  # 窗口终点(不含), epoch 秒
    interval: int  # 桶宽秒(24h = 采样间隔, 30d = 3600, 6mo/1y = 86400, all = 标称月长)
    segment: str  # 消费段: "raw" | "hour" | "day" | "month"
    buckets: tuple  # Tuple[int, ...] 桶起点序列(升序)

    @property
    def first(self) -> int:
        return self.buckets[0]

    @property
    def last(self) -> int:
        return self.buckets[-1]


def build_grid(window: str, now: float, sample_interval: float = DEFAULT_SAMPLE_INTERVAL_S) -> WindowGrid:
    """窗口名 + 当前时刻 -> 时间栅格(纯函数; sample_interval 只在 raw 段生效)

    day 段窗(6mo/1y): 滚动窗 [now-span, now) 涉及的本地日期逐日铺格(桶键 = 本地日界
    00:00, 与 agg day 行 epoch 同源); 跨夏令时时区本地日界间隔可非严格 86400(部署时区
    UTC+8 无夏令时, 恒等宽)。month 段窗(all)栅格由数据面定, 不在此构建(防御性拒绝)。
    """
    try:
        span, segment = WINDOW_SPECS[window]
    except KeyError:
        raise ValueError(f"未知窗口: {window!r}(须为 {'|'.join(WINDOW_SPECS)})") from None
    if segment == "month":
        raise ValueError("all 窗栅格由 agg month 行数据面定: 用 build_month_grid(...)")
    # 桶宽对采样间隔向上取整(floor 在小数间隔如 1.5s 下取 1s 桶宽, 采样行 1.5s 一条 -> 隔桶为空 = 伪断线;
    # ceil 后桶宽 >= 采样间隔, 等间隔采样行每桶至少一条)
    if segment == "raw":
        interval = max(1, math.ceil(sample_interval))
        t1 = int(now)
        t0 = t1 - span
        first = t0 - (t0 % interval)  # floor 对齐(epoch 恒正)
        n = (t1 - first + interval - 1) // interval  # ceil
        buckets = tuple(first + i * interval for i in range(n))
    elif segment == "day":
        interval = DAY_SECONDS
        t1 = int(now)
        t0 = t1 - span
        buckets = tuple(v4_date_str_epoch(d) for d in sorted(v4_window_dates(t0, t1 - 1)))
    else:  # hour
        interval = HOUR_SECONDS
        t1 = int(now)
        t0 = t1 - span
        first = t0 - (t0 % interval)  # floor 对齐(epoch 恒正)
        n = (t1 - first + interval - 1) // interval  # ceil
        buckets = tuple(first + i * interval for i in range(n))
    return WindowGrid(window, t0, t1, interval, segment, buckets)


def build_month_grid(month_epochs: tuple, now: float) -> WindowGrid:
    """all 视图栅格(数据面定, §05.3): month 行 epoch 集合最小..最大自然月之间逐月铺格
    (缺失月 = null 桶, 折线断开); 空集合 = 空 buckets 兜底栅格(端点空态面, meta 仍齐全)。

    month_epochs = agg month 行 epoch 序列(任意序/可重复, 只取最小最大)。真实月长按行
    间隔 28-31 天不等, meta.interval_s 取标称月长 MONTH_NOMINAL_S 供轮询夹取; 点位真值
    在 points[].t(前端按真值落点)。
    """
    month_epochs = tuple(month_epochs)  # 迭代器入参防御(下面 min/max 两次消费)
    t1 = int(now)
    if not month_epochs:
        return WindowGrid("all", t1, t1, MONTH_NOMINAL_S, "month", ())
    lo, hi = min(month_epochs), max(month_epochs)
    buckets = []
    cur = int(lo)
    while cur <= hi:
        buckets.append(cur)
        cur = v4_next_month_epoch(cur)  # 严格递增, 必终止
    return WindowGrid("all", int(lo), int(hi) + 1, MONTH_NOMINAL_S, "month", tuple(buckets))


def grid_for_now(window: str, sample_interval: float = DEFAULT_SAMPLE_INTERVAL_S) -> WindowGrid:
    """以当前时刻建栅格(API 层入口; 纯函数版 build_grid 的现在时包装)"""
    return build_grid(window, time.time(), sample_interval)


@dataclass(frozen=True)
class BucketObs:
    """单桶观测(§05.1 归桶结果): 速率均值 + 桶末累计快照"""

    dl_rate: int  # 桶内下载速率均值(bytes/s, round 取整)
    up_rate: int
    dl_total: Optional[int]  # 桶末 all-time 下载累计快照(bytes; raw 取最新行, hour 取封口行)
    up_total: Optional[int]


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


def group_null_mask(member_obs: list, grid: WindowGrid) -> list:
    """组桶 null 判定(v4 观测面, §05.1「借 global 判 null」退役) -> bool 列表(True = 该桶 null)

    采样器全局同拍 —— 单成员的 r/z 观测即「程序存活且 qB 在线」的真值:
    - 桶内任一成员有观测(r/z) -> 非 null(无行成员按 0 计, 全员空闲出 0 线);
    - 全员无观测 = 程序停机(块间真空)/ qB 断连(n 游程)/ 组尚无任何观测 -> null;
    组图停机段断线、空闲段 0 线, 二者由成员自身观测面区分, 不再借全局系列
    (每请求省一次全局文件读取; v2 的 earliest_member_ts 门被本规则自然吞并 ——
    早于全部成员最早观测的桶必然无任何成员观测)。
    """
    return [not any(o.get(b) is not None for o in member_obs) for b in grid.buckets]


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
# v4 读侧核心(plan 26-10-04-1957 S3a 立, §05.1/§05.2)
#
# 分层纯化(为 S3b 留接缝): 天文件解析产物(V4ParsedDay.blocks) -> 本层 v4_series_slots
# (记录时间轴, S3b agg 段合流的并流点) -> v4_series_points(桶点) -> v4_totals_points
# (累计增量)。天文件读取在 traffic_store.V4DayCache(按天加载 + mtime/size 解析缓存);
# 本模块不触文件不触时钟, 视图映射(WINDOW_SPECS/agg 段/组端点)属 S3b。
#
# 归桶模型(D1 实施期定稿: 逐记录覆盖桶):
# - 每个观测槽(r/z)生成一个覆盖桶: 桶宽 w = v4_bucket_width_s(有效dt)(S1 槽层的 dt_s =
#   显式 dt 或游程均摊 span/run_len), 桶 = [t, ceil(ts)), t = ceil(ts) - w。
#   替代 v2 全局 ceil(sample_interval) 一刀切 —— 混排 interval 分块
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
# - 活尾合流(S6 验收追加, 2026-10-05): tail_slots(采样模块活尾快照续链产物)追加在磁盘
#   链之后 —— 同链延续不做块间真空判定(磁盘链末槽与活尾首槽之间是一次标称采样间隔,
#   非块界), 且按槽 ts 与磁盘链精确去重(镜像保证: 同一记录写侧游标推进与落盘重算的
#   槽 ts 恒等, 保留严格更晚的后缀即不重不漏)。
# ======================================================================

#: 真空判定浮点容差(秒): 块间 gap 与首记录覆盖桶的比较 ε
_V4_VACUUM_EPS_S = 1e-6


@dataclass(frozen=True)
class V4PointEntry:
    """v4 读侧单桶点(S3a 桶点层输出, S3b 视图映射的输入形态)

    t = 桶起点 epoch 秒(覆盖桶 [t, t+w)); rate/totals 全 None = null 点(n 游程/块间真空
    标记, 断线语义 —— v4 r/z 行无 null 形态, null 只来自这两种标记)。w = 覆盖桶宽秒
    (同 key 多记录合并取最大; 栅格展开 v4_grid_obs 据此铺盖 D1 跨桶覆盖; null 点恒 0)。
    """

    t: int  # 桶起点 epoch 秒
    dl_rate: Optional[int] = None  # 桶内下载速率均值(bytes/s, round 取整)
    up_rate: Optional[int] = None
    dl_total: Optional[int] = None  # 桶末 all-time 下载累计快照(bytes)
    up_total: Optional[int] = None
    w: int = 0  # 覆盖桶宽秒(= ceil(有效dt); 同桶多记录取最大)


@dataclass(frozen=True)
class V4TotalsEntry:
    """单桶点累计增量(v4_totals_points 输出): dl/up = 相邻桶快照差分, None = null"""

    t: int
    dl: Optional[int]
    up: Optional[int]


def v4_series_slots(blocks: tuple) -> tuple:
    """块序列 -> 扁平槽序(记录时间轴层; S3b agg 段合流的接缝): 块按 start_epoch 升序
    (稳定排序, 同刻保文件序), 逐块 v4_block_slots 展开(复用 S1 游标 dt 链, 不另写推算)。"""
    out = []
    for blk in sorted(blocks, key=lambda b: b.start_epoch):
        out.extend(v4_block_slots(blk))
    return tuple(out)


def v4_series_points(blocks: tuple, t0: float, t1: float, tail_slots: tuple = ()) -> tuple:
    """v4 读侧核心(§05.1/§05.2): 块序列 -> 窗口 [t0, t1) 内按 t 升序的桶点列

    blocks = V4Block 序列(单系列的若干天文件解析产物合并传入; 天文件按日期升序读出,
    块不跨天故按 start_epoch 排序即恢复时间序)。归桶/覆盖/真空/合并规则见本区头注释。
    tail_slots = 活尾快照槽序(S6 验收追加, v4_live_tail_slots 产物; 缺省空 = 纯磁盘读):
    追加在磁盘链之后 —— 同链延续不做块间真空判定, 且按槽 ts 与磁盘链精确去重(同一记录
    「写侧游标推进」与「落盘后重算」的槽 ts 恒等, 保留严格更晚的后缀即不重不漏, 快照与
    flush 的先后竞态无害)。
    无块且无活尾(停机/无数据)返回空元组(天然真空, 调用方按空态处理)。
    """
    cells = {}  # 桶键 -> [is_raw, dl_sum, up_sum, n, last_ts, dl_total, up_total, w_max]
    marks: list = []  # null 点 (t, ...) —— n 游程折叠 + 块间真空
    prev_chain_end: Optional[float] = None
    last_was_null = False
    groups = [(v4_block_slots(blk), False) for blk in sorted(blocks, key=lambda blk: blk.start_epoch)]
    if tail_slots:
        groups.append((tuple(tail_slots), True))
    for slots, is_tail in groups:
        if not slots:
            continue
        if prev_chain_end is not None:
            if is_tail:
                slots = tuple(s for s in slots if s.ts > prev_chain_end + _V4_VACUUM_EPS_S)
                if not slots:
                    continue
            else:
                first_w = v4_bucket_width_s(slots[0].dt_s)
                # 真空: 下一块首记录覆盖桶起点晚于上一块游标终值 -> 差值段出 null 点
                if math.ceil(slots[0].ts) - first_w > prev_chain_end + _V4_VACUUM_EPS_S:
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
            w = v4_bucket_width_s(s.dt_s)
            key = math.ceil(s.ts) - w
            if key + w < t0:  # 覆盖桶不触及窗口左界(桶 [key, key+w) 与 [t0, t1) 无交集)
                continue
            o = s.obs
            e = cells.get(key)
            if e is None:
                cells[key] = [not s.is_zero, o[0], o[1], 1, s.ts, o[2], o[3], w]
            elif not s.is_zero:
                e[7] = max(e[7], w)  # 同桶多记录: 覆盖桶宽取最大(并集覆盖)
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
                    e[7] = w  # 覆盖面以 raw 记录的覆盖桶为准(z 让位)
            # z 到 raw 桶: raw 优先, z 让位; z 到 z 桶: 先到者保留(v2 多行程同桶口径)
        prev_chain_end = slots[-1].ts  # 游标终值 = 末槽实测时刻(真空判定基准)
    entries = []
    for key in sorted(cells):
        e = cells[key]
        n = e[3]
        entries.append((key, 1, V4PointEntry(key, int(round(e[1] / n)), int(round(e[2] / n)), e[5], e[6], w=e[7])))
    for t in marks:
        if t0 <= t < t1:
            entries.append((t, 0, V4PointEntry(t)))
    # null 点排同刻观测点之前(null 在先 = 该时刻断线、其后才是观测覆盖; 稳定保插入序)
    entries.sort(key=lambda x: (x[0], x[1]))
    return tuple(e for _, _, e in entries)


def v4_totals_points(points: tuple) -> tuple:
    """累计增量段(§05.1): 相邻桶点快照差分 —— v2 规则平移(series_totals_points):
    max(0,·) 等价形 + cur < last 判计数器重置 -> null + 基线缺失(窗首/null 点断链)->
    null; dl/up 两向独立判定。游程快照(z 槽桶 totals 恒定)进差分链 —— 空闲段每桶
    delta = 0 链不断, 其后首个活跃桶恢复有基线; 宽桶(跨桶覆盖)的 delta 覆盖其整段
    有效 dt(暂停期真实增量落在恢复记录的一桶里)。"""
    out = []
    prev = None  # 相邻前桶点快照(dl_total, up_total)
    for p in points:
        if p.dl_rate is None:  # null 点: 断线且断链
            out.append(V4TotalsEntry(t=p.t, dl=None, up=None))
            prev = None
            continue
        dl = _bucket_delta(p.dl_total, prev[0]) if prev is not None else None
        up = _bucket_delta(p.up_total, prev[1]) if prev is not None else None
        out.append(V4TotalsEntry(t=p.t, dl=dl, up=up))
        prev = (p.dl_total, p.up_total)
    return tuple(out)


# ======================================================================
# v4 视图映射(S3b, §05.3): 桶点流/agg 行 -> 响应栅格桶观测
#
# 响应数组 = 窗口栅格上的「桶值 | null」定长数组(§08 形状不变); 两类入流在栅格桶
# 观测(BucketObs 表)层面合流, 之后的 rate_points / series_totals_points / group_*
# 与 v2 共用同一差分层:
# - raw 段窗(1m-24h): v4_series_points 桶点流 --v4_grid_obs--> 栅格桶(覆盖加权展开);
# - agg 段窗(3d/7d/30d hour / 6mo/1y day / all month): agg 行 --v4_agg_obs--> 栅格桶
#   (行 epoch 即桶键, 直映; 3d+ 窗只读成员 agg 文件, 组图 30d 由 M×31 -> M×1 次读取)。
# ======================================================================


def v4_grid_obs(points: tuple, grid: WindowGrid) -> dict:
    """v4 桶点流 -> 栅格桶观测(S3b §05.1/§05.3, D1 覆盖的栅格展开)

    桶点覆盖区间 [t, t+w) 与栅格桶 [b, b+interval) 按重叠秒数加权:
    - 速率 = Σ(rate x 重叠秒) / Σ重叠秒(口径对齐 v4_hour_agg 的 dt 加权) —— 对齐记录
      恰好 1:1 落桶, 抖动/漂移记录跨界时相邻桶按真实覆盖占比分摊(无伪洞无伪值);
    - 快照取覆盖末端(t+w)最晚的桶点(同末端后到者优先)—— 宽桶(跨多栅格桶)的中间桶
      同值非 null 且同快照(D1 跨桶覆盖的栅格形态: totals 差分在首个覆盖桶落增量,
      其余桶 delta = 0 链不断);
    - null 点(断连/真空标记)不参与 —— 栅格桶无观测 = null, 断线语义由空桶承载;
    - 窗外栅格桶(b < first 或 b > last)不消费(对齐 v2 窗外行口径)。
    """
    first, last, interval = grid.first, grid.last, grid.interval
    acc = {}  # 桶键 -> [重叠秒和, dl 加权和, up 加权和, 覆盖末端, dl_total, up_total]
    for p in points:
        if p.dl_rate is None or p.w <= 0:
            continue  # null 点 / 无覆盖宽度的防御形不参与归桶
        cov_end = p.t + p.w
        if cov_end <= first or p.t > last:
            continue  # 与窗口栅格无交集
        b = p.t - (p.t % interval)
        while b < cov_end:
            if b > last:
                break
            ov = min(cov_end, b + interval) - max(p.t, b)
            if ov > 0 and b >= first:
                a = acc.get(b)
                if a is None:
                    acc[b] = [ov, p.dl_rate * ov, p.up_rate * ov, cov_end, p.dl_total, p.up_total]
                else:
                    a[0] += ov
                    a[1] += p.dl_rate * ov
                    a[2] += p.up_rate * ov
                    if cov_end >= a[3]:  # 覆盖末端最晚者胜(同末端后到者优先)
                        a[3] = cov_end
                        a[4] = p.dl_total
                        a[5] = p.up_total
            b += interval
    return {b: BucketObs(int(round(a[1] / a[0])), int(round(a[2] / a[0])), a[4], a[5]) for b, a in acc.items()}


def v4_agg_obs(rows: tuple, grid: WindowGrid) -> dict:
    """agg 行(hour/day/month) -> 栅格桶观测(S3b §05.3 视图映射): 行 epoch 即栅格桶键

    hour 行 epoch 恰为 3600 整倍(与 hour 栅格 floor 对齐同源), day 行 = 本地日界 00:00
    (= build_grid day 段窗桶键), month 行 = 自然月 1 日 00:00(= build_month_grid 桶键)
    —— 直映不聚合(写侧封口已按桶归并); avg/max/totals/cov_s -> 桶值(max/cov_s 不上图,
    保留供对照); 窗外行(不在栅格桶集)不消费; 缺行栅格桶不出现在返回表 = null。
    """
    buckets = set(grid.buckets)
    return {r.epoch: BucketObs(r.dl_avg, r.up_avg, r.dl_total, r.up_total) for r in rows if r.epoch in buckets}


def v4_earliest_row_ts(blocks: tuple, agg: Optional[V4ParsedAgg]) -> Optional[int]:
    """v4 单系列最早观测时刻(S3b, §05.4): 块首槽实测时刻(B.start 即首槽, 含 z 游程开块
    —— 块首游程首槽 = B.start) + agg 行 epoch(hour/day/month 三层全算 —— 观测面全层的
    最早证据, day/month 行计入 —— 观测面全层的覆盖(v3 新增)); 双空(无块无 agg 行)
    = None(组端点空态判据「组从未产过流量」的观测面口径)。"""
    cands = [b.start_epoch for b in blocks]
    if agg is not None:
        for section in (agg.hours, agg.days, agg.months):
            cands.extend(r.epoch for r in section)
    return min(cands) if cands else None
