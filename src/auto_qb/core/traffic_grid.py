"""traffic_grid: qB 口径流量图读侧栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4, §05.1/§04.1; v3 读侧 plan 26-10-04-1957 S3a/S3b)

S4 API 读侧的取数口径, 全部纯函数(输入 v4 天文件块序列 / agg 行 / 栅格桶表, 输出响应段),
不触文件不触时钟 —— Web 线程直接调用, 单测可独立构造输入。v2 逐行格式的读侧(系列解析 /
raw 归桶 / z 行程覆盖展开 / 最早观测行)已随 S5 退役删除, 本模块即现行唯一读侧:

窗口与栅格(§05.1/§05.3, WINDOW_SPECS 13 档):
- raw 段窗(1m-24h): 桶宽 = 采样间隔 x k, k = ceil(span/(MAX_RAW_BUCKETS x 采样间隔)) ——
  桶宽恒为采样整倍 + 桶数 <= 上限(计划 26-11-15-1104 F1/D7, 替换旧 max(ceil(si), ceil(span/2880))
  取整口径: 桶边与采样行错位的双几何实证见该计划 §02), 桶 = floor 对齐; 数据经
  traffic_store.V4DayCache 按天加载 -> 块序列 -> v4_series_points 点位归属归桶(栅格单
  几何, 26-11-15-1104 F2) -> v4_grid_obs 直映栅格桶观测; 另合流采样模块活尾快照
  (S6: 未落盘记录 + 开放游程续链, 图面尾部随采样节拍实时, 不等 flush)。
- hour 段窗(3d/7d/30d): 桶宽恒 3600s, 消费 agg hour 行; day 段窗(6mo/1y): 滚动窗涉及
  本地日期逐日铺格(桶键 = 本地日界 00:00), 消费 agg day 行; month 段窗(all): 数据面定栅格
  (build_month_grid, 首末月行之间逐月铺格), 消费 agg month 行。agg 行 epoch 即栅格桶键
  (v4_agg_obs 直映, 桶内不再聚合)。

桶点模型(26-11-15-1104 F2 点位归属归桶, 替代旧逐记录覆盖桶 ceil(ts)-w 几何):
- 栅格单几何: 样本槽(r/z)按 floor(ts/B)xB 点位归属 —— 落哪格算哪格, 桶键 = 栅格桶键
  (first + i x interval 单一表达式派生, 与 grid.buckets 逐位相等); 样本槽与栅格桶统一
  到同一套键, 旧 cell ceil-锚定几何与覆盖加权摊配桥接层一并退役。
- 桶速率一次算定: 桶速率 = 桶内样本差分和 / 覆盖时长 —— 相邻槽差分(delta = cur - prev
  快照, 逐向独立)按后继槽点位归桶(端点归属), 覆盖时长 = 差分对跨的实测毫秒; 速率一次
  算定不再重写(旧 v4_rate_from_totals 的 delta/w 桶层重写随双几何退役)。
- z 槽桶=0: z 槽快照冻结 -> 对差分恒 0, 空闲段每桶 0 线链不断(z-run 语义承袭); 块间
  真空与 n 游程断连都出 null 点, 来源不同(真空无观测 / 断连显式 null)。

totals 段(§05.1, 单系列与组共用差分层):
- 相邻桶累计快照差分: delta = cur - last; cur < last 判计数器重置 -> 该桶增量 null
  (dl/up 两向独立判定, 对齐采样器 _delta 逐向口径); 前桶无快照(窗首/空桶断链)= 基线
  缺失 -> null。z 槽桶快照恒定参与差分 —— 空闲段每桶 delta = 0 链不断。
- 接缝摊配(plan 26-10-15-0829 P2; 重启缝形态 issue 26-10-16-0954 修复轮补入; F2 后在
  槽层一次算定内承袭, 详 v4_series_points): 长 z 形等值游程(写侧快照冻结)末端的台阶按
  真实发生跨度摊配到游程桶 + 接收桶(消除单桶归因随桶宽反比的放大); 观测缝
  > _V4_SEAM_NULL_S = 停机洞, 仍断链丢弃(诚实性); <= 本值的重启缝按真实跨度回收。

组读侧聚合(§04.1 -> §05.4, API 层现算不做聚合缓存):
- 速率 = 各成员栅格桶观测 Σ 成员均值, 无行成员按 0 计;
- 累计增量 = 逐成员先差分(重置/基线缺失贡献 0)再求和 —— 宁可少计一桶不出洞;
- 桶 null 判定(v4): 桶内无任何成员观测 -> null —— 单成员的 r/z 观测即「程序存活且 qB
  在线」真值, 不借全局系列(组图 3d+ 窗 M 个成员各只读 1 个 agg 文件)。
"""
import bisect
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

from ..infra import clock
from .traffic_store import (
    HOUR_SECONDS,
    V4NullRun,
    V4ParsedAgg,
    V4ZeroRun,
    v4_block_slots,
    v4_block_slots_from,
    v4_date_str_epoch,
    v4_merge_agg,
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

#: 24h 窗栅格宽的兜底值(qb_traffic 缺省 = 未启用时的空态 meta; 沿用旧版配置缺省 30S,
#: 新键默认 1 倍 main_tick 后它只兜空态, 见计划 26-11-10-0252 D11)
DEFAULT_SAMPLE_INTERVAL_S = 30.0


def effective_sample_interval(multiplier: int, main_tick: float) -> float:
    """生效采样间隔单点: multiplier * main_tick(秒)。采样器与 webui 栅格同调(D10)

    配置键 qb_traffic.sample_interval_multiplier 是 main_tick 的整数倍数(plan 26-11-10-0252
    D3/D5), 生效秒值 = 直乘, 无取整无告警(倍数语义下失配数学上不可能, D10)。采样器的块头
    interval 与 webui raw 段窗桶宽都经本函数取同一值, 两处不得各自换算。
    """
    return float(multiplier) * float(main_tick)


#: raw 段窗桶数上限(计划 26-11-15-1104 F1/D7, 语义 = 桶数上限, 2880 -> 500): raw 桶宽 =
#: 采样间隔 x k, k = ceil(span/((上限 - 1) x 采样间隔)) —— 分母预留 1 个进行中桶位(F3
#: floor+1), 使**含进行中桶**的桶数恒 <= 上限(A6/D7 拍板「最大 500 桶」判据优先于公式
#: 字面: 分母取上限本身时 span 恰 500 倍桶宽的采样(如 24h @ si=2.4)会出 501)。桶宽恒为
#: 采样间隔的整倍(点位归属归桶与采样节拍同律; 旧「按 span/上限取整」几何使桶边与采样行
#: 错位, 双几何实证见该计划 §02)。高频采样(生产现况 1.5s)下 24h 窗本可达数万桶(JSON
#: 传输 MB 级 + uPlot 万点级重渲染 + 后端每拍全量重展开), 收敛到 <=500。整倍窗桶数恒定;
#: 非整倍窗(6h/12h/24h @1.5s 采样)随轮询相位在 floor+1 相邻值波动(幅度 1, 桶数 497-498)。
#: 业界同型先例: RRDtool CF=AVERAGE · qB GUI SpeedPlotView Averager(1s->144s 分桶)·
#: Deluge stats 多级桶 · Grafana $__rate_interval。
MAX_RAW_BUCKETS = 500


@dataclass(frozen=True)
class WindowGrid:
    """一次取数的时间栅格(§05.1): [t0, t1) 按 interval 离散出的固定桶序

    buckets 长度 = (t1 - first) // interval + 1(恒含进行中桶; 计划 26-11-14-1313 F3 反转
    26-10-11-0207 R07 的 ceil 口径 —— 反转理由见 _floor_buckets; 窗首桶对齐
    floor(t0/interval)); 桶值 t = 桶起点 epoch 秒。
    day 段窗(6mo/1y)例外: 桶键 = 本地日界 00:00(滚动窗 [t0, t1) 涉及的本地日期逐日铺格,
    窗首桶允许早于 t0 —— 首日不满宽); month 段窗(all)由 build_month_grid 数据面铺格。
    """

    name: str  # WINDOW_SPECS 键(1m-all)
    t0: float  # 窗口起点(含), epoch 秒(与浮点挂钟同源, 不再整秒截断)
    t1: float  # 窗口终点(不含), epoch 秒(同上; 整点输入时数值仍为整数)
    interval: float  # 桶宽秒(raw = 采样间隔整倍, 可为 1.5/4.5/22.5/43.5/87/174 等半秒值(26-11-15-1104 F1), 30d = 3600, 6mo/1y = 86400, all = 标称月长; 整值宽归一 int)
    segment: str  # 消费段: "raw" | "hour" | "day" | "month"
    buckets: tuple  # Tuple[int, ...] 桶起点序列(升序)

    @property
    def first(self) -> int:
        return self.buckets[0]

    @property
    def last(self) -> int:
        return self.buckets[-1]


def _floor_anchor(t: float, interval: float) -> float:
    """浮点时刻向下对齐到 interval 网格(issue 26-11-17-0936 治本单点): math.floor(t/interval)
    起步后双向校正到「first <= t < first+interval」, 桶键恒以 first + i×interval 同式派生
    (与 _bucket_index 同一浮点路径, 非整倍宽下不差 1 ulp)。直接对浮点 now 对齐, 不再经
    int(now) 整秒截断 —— 后者与 1.5s 轮询/桶宽 floor 对齐混叠出 +3.0/0.0 二拍抖动。"""
    i = math.floor(float(t) / float(interval))
    first = i * interval
    while first > t:
        i -= 1
        first = i * interval
    while first + interval <= t:
        i += 1
        first = i * interval
    return first


def _floor_buckets(t0: float, t1: float, interval: float) -> tuple:
    """等宽桶序列单点(issue 26-10-11-0207 R07 立, 计划 26-11-14-1313 F3 反转桶数口径):
    起点向下取整对齐 + floor+1 桶数 + 生成。build_grid 的 raw 与 hour 两分支
    共用(除桶宽计算外逐字同构); day 分支桶键是本地日界, 不走此处。

    桶数 n = floor((t1-first)/interval)+1(恒含进行中桶)—— 反转 R07 ceil 方波的历史判据仍
    成立; 输入 t0/t1 现为浮点挂钟(26-11-17-0936 治本): first 按 _floor_anchor 对同一
    interval 网格对齐并双向校正,n 由浮点跨度现算再双向校正到 last <= t1 < next。
    span 为 interval 整倍时 n 恒 k+1 与相位无关(生产默认采样面 1m/5m/30m/3h 全整倍);
    非整倍窗 n 在 k+1/k+2 两形态随相位波动(幅度 1, 6h/12h/24h @1.5s 实测 497-498)。
    尾桶恒为「进行中桶」(包含浮点 t1); t1 恰落桶边界时尾桶是刚开启的空桶(单桶 null,
    视觉无感)。"""
    first = _floor_anchor(t0, interval)
    n = int(math.floor((float(t1) - first) / float(interval))) + 1
    while n > 1 and first + (n - 1) * interval > t1:
        n -= 1
    while first + n * interval <= t1:
        n += 1
    return tuple(first + i * interval for i in range(n))


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
    if segment == "raw":
        # 桶宽 = 采样间隔 x k, k = ceil(span/((上限-1) x 采样间隔))(计划 26-11-15-1104 F1, 替换旧
        # max(ceil(采样间隔), ceil(span/上限)) 取整口径): 桶宽恒为采样整倍(桶边与采样节拍同律,
        # 归桶与展示的伪失真随双几何消失), 含进行中桶的桶数恒 <= 上限(分母预留 1 个进行中桶位,
        # 详 MAX_RAW_BUCKETS 注)。整值宽归一 int(桶键保持整数, 与 hour/day 段及历史 meta 整值
        # 形态一致)。si 来源链 = 纯 config 派生(multiplier >= 1 x main_tick >= 0.5, 两因子均在
        # validate_config 全量校验面聚合报错) —— 黄金法则 4: 校验后的代码假定配置正确, 非正值
        # 在此 fail-fast(绝不让 0 间隔静默产出除零/忙循环面)。
        si = float(sample_interval)
        if not si > 0:
            raise ValueError(f"sample_interval 须 > 0(生效采样间隔 = multiplier x main_tick, 校验面保证正值): {si!r}")
        interval = si * math.ceil(span / ((MAX_RAW_BUCKETS - 1) * si))
        if interval.is_integer():
            interval = int(interval)
        # 治本(issue 26-11-17-0936): t1 保留浮点挂钟, 不再 int(now) 整秒截断 —— 轮询
        # 周期 = si 时截断令 Δt1 在 +1/+2 间交替, floor 对齐后窗起点出现 2 拍
        # (1m/5m, +3.0/0.0)与 2~3 拍(30m, 0/+4.5)聚簇; 直接对浮点 now 走同一
        # interval 网格, Δfirst 恒为 0 或 1 格且无相位别名。整点输入语义不变。
        t1 = float(now)
        t0 = t1 - span
        buckets = _floor_buckets(t0, t1, interval)
    elif segment == "day":
        interval = DAY_SECONDS
        t1 = int(now)  # 非 raw 段保持原整秒边界(t1-1 日期口径不变)
        t0 = t1 - span
        buckets = tuple(v4_date_str_epoch(d) for d in sorted(v4_window_dates(t0, t1 - 1)))
    else:  # hour
        interval = HOUR_SECONDS
        t1 = int(now)  # 同上(小时桶远大于轮询, 无整秒混叠面)
        t0 = t1 - span
        buckets = _floor_buckets(t0, t1, interval)
    return WindowGrid(window, t0, t1, interval, segment, buckets)


def build_month_grid(month_epochs: tuple, now: float) -> WindowGrid:
    """all 视图栅格(数据面定, §05.3): month 行 epoch 集合最小..最大自然月之间逐月铺格
    (缺失月 = null 桶, 折线断开); 空集合 = 空 buckets 兜底栅格(端点空态面, meta 仍齐全)。

    month_epochs = agg month 行 epoch 序列(任意序/可重复, 只取最小最大)。真实月长按行
    间隔 28-31 天不等, meta.interval_s 取标称月长 MONTH_NOMINAL_S 供轮询夹取; 点位真值
    在 points[].t(前端按真值落点)。
    """
    month_epochs = tuple(month_epochs)  # 迭代器入参防御(下面 min/max 两次消费)
    t1 = int(now)  # 非 raw 段保持原整秒边界
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
    """以当前时刻建栅格(API 层入口; 纯函数版 build_grid 的现在时包装; 叶子取时走 clock 单点)"""
    return build_grid(window, clock.SYSTEM_CLOCK.now(), sample_interval)


@dataclass(frozen=True)
class BucketObs:
    """单桶观测(§05.1 归桶结果): 速率均值 + 桶末累计快照

    dl_rate/up_rate = None 表示「该向无速率覆盖, 且本桶覆盖起点晚于上一观测点覆盖末端」
    (观测缝/停机洞断链而来, 速率未知而非 0; issue 26-10-16-0954 修复语义: 断链后首桶不得
    冒充 0 值点) —— 快照仍照记(差分链基线不断), 无观测缝的起始桶(程序/窗口起点)沿用
    D4 的 0 线(1/N 缺口视觉无感)。
    """

    dl_rate: Optional[int]  # 桶内下载速率均值(bytes/s, round 取整); None = 断链来的未知(见类注)
    up_rate: Optional[int]
    dl_total: Optional[int]  # 桶末 all-time 下载累计快照(bytes; raw 取最新行, hour 取封口行)
    up_total: Optional[int]


def rate_points(obs: dict, grid: WindowGrid) -> list:
    """速率段(§08 points): 桶有观测 -> {"t","dl","up"}; 空桶 = null(断线语义, §05.2)

    桶观测的逐向 None(断链来的未知, 见 BucketObs 类注)原样落成 null —— 前端把它与空桶
    同视为缺口(斜纹), 不会画出 0 值孤点。
    """
    out = []
    for b in grid.buckets:
        o = obs.get(b)
        out.append(None if o is None else {"t": b, "dl": o.dl_rate, "up": o.up_rate})
    return out


def _bucket_delta(cur: Optional[int], last: Optional[int]) -> Optional[int]:
    """累计快照差分(§05.1): max(0,·) 的等价形 + 回落判重置 -> null; 基线缺失 -> None
    !「cur < last 判重置」口径的分层形态之一(采样器 traffic_sample_mod._delta / v4
    解析侧负 delta 校验同判据, 三处互指; issue 26-10-11-0207 R07/R10 登记保持分层)"""
    if cur is None or last is None:
        return None
    if cur < last:
        return None  # 计数器重置(qB 非优雅重启/删种重加): 该桶增量 null, 绝不产负增量
    return cur - last


def series_totals_points(obs: dict, grid: WindowGrid) -> list:
    """累计增量段(§08 totals, 单系列): 相邻桶快照差分

    前桶无快照(窗首基线缺失/空桶断链)-> 该桶 null; 空桶本身 null 且断链后继(下一有观测
    桶同样基线缺失)。dl/up 两向独立判定(对齐采样器 _delta 逐向口径)。
    !同源双实现登记(issue 26-10-11-0207 R07/R10)单点化(26-11-15-1104 F2): 原 v4 侧孪生
    v4_totals_points 已随 cell 几何退役 —— 差分/摊配口径单点在 v4_series_points 槽层
    一次算定, 本函数只承载**响应 totals 通道**(相邻栅格桶快照差分, 输入 obs 桶表);
    改差分口径改 v4_series_points, 改快照差分展示口径改本函数, 两面不再互为平移。
    """
    out: list[dict[str, Any] | None] = []
    prev = None  # 相邻前桶快照(dl_total, up_total)
    for b in grid.buckets:
        o = obs.get(b)
        if o is None:
            out.append(None)
            prev = None
            continue
        dl: int | None = _bucket_delta(o.dl_total, prev[0]) if prev is not None else None
        up: int | None = _bucket_delta(o.up_total, prev[1]) if prev is not None else None
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
    """组速率段(§04.1-2): 桶内 Σ 成员均值; 桶内无行成员按 0 计; null 桶 -> None

    成员速率逐向未知(BucketObs 的 None, 断链桶)按 0 计入和(与无行成员同款); 但**该桶有成员
    观测而全成员该向速率皆未知**时该向出 None —— 组图同样不得把「断链来的未知」画成 0 值孤点
    (issue 26-10-16-0954 修复面; 桶级 null 仍由 null_mask/成员观测面承载, 语义不变)。
    """
    out: list[dict[str, Any] | None] = []
    for i, b in enumerate(grid.buckets):
        if null_mask[i]:
            out.append(None)
            continue
        dl = 0
        up = 0
        has_obs = False  # 该桶有无成员观测行(无 = 全员无行, 按 0 计; 桶级 null 由 mask 兜)
        dl_known = False
        up_known = False
        for obs in member_obs:
            o = obs.get(b)
            if o is None:
                continue
            has_obs = True
            if o.dl_rate is not None:
                dl += o.dl_rate
                dl_known = True
            if o.up_rate is not None:
                up += o.up_rate
                up_known = True
        out.append(
            {
                "t": b,
                "dl": dl if dl_known else (None if has_obs else 0),
                "up": up if up_known else (None if has_obs else 0),
            }
        )
    return out


def group_totals_points(member_obs: list, grid: WindowGrid, null_mask: list) -> list:
    """组累计增量段(§04.1-3): 逐成员先差分(max(0,·) + 重置/基线缺失贡献 0)再求和

    成员某桶增量缺失(无行/重置/基线缺失)按 0 计 —— 宁可少计一桶不出洞; null 桶整桶
    None 且桶链断开(null 桶之后成员基线同样缺失, 与单系列相邻桶口径一致)。
    """
    prevs = [None] * len(member_obs)  # 逐成员的相邻前桶快照
    out: list[dict[str, Any] | None] = []
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
# v4 读侧核心(plan 26-10-04-1957 S3a 立, §05.1/§05.2; 26-11-15-1104 F2 点位归属归桶重锚)
#
# 分层(F2 后): 天文件解析产物(V4ParsedDay.blocks) -> 本层 v4_series_slots(记录时间轴)
# -> v4_series_points(栅格桶点: 点位归属归桶 + 桶速率一次算定) -> v4_grid_obs(直映栅格
# 桶观测) -> rate_points / series_totals_points(与 v2 共用差分层)。天文件读取在
# traffic_store.V4DayCache(按天加载 + mtime/size 解析缓存); 本模块不触文件不触时钟。
#
# 归桶模型(26-11-15-1104 F2 点位归属, 替代旧逐记录覆盖桶 ceil(ts)-w 几何):
# - 栅格单几何: 样本槽(r/z)按 floor(ts/B)xB 点位归属 —— 落哪格算哪格; 桶键 = 栅格桶键
#   (first + i x interval 单一表达式派生, 与 grid.buckets 逐位相等), 样本槽与栅格桶统一
#   到同一套键。旧 cell ceil-锚定几何(每记录一个 ceil(ts)-w 覆盖桶)与 v4_grid_obs 的
#   覆盖加权摊配桥接层一并退役 —— 双几何(槽层覆盖桶 vs 展示栅格)正是速率语义双轨的
#   根(计划 §02 根缺陷二), 单几何后桶层一次算定, 无重写。
# - 桶速率一次算定(F2): 桶速率 = 桶内样本差分和 / 覆盖时长。相邻槽差分(delta = cur -
#   prev 快照, 逐向独立)按**后继槽点位**归桶(端点归属: 差分对 (prev, cur) 记在 cur 所
#   在格); 覆盖时长 = 差分对跨的实测毫秒 **减未观测秒**(对跨 - 本槽声称覆盖 dt_s; 整数
#   ms 化 —— 摊配份额算术保持整除严格守恒), 连续链望远镜和恒 = 对跨、含缝链恒 < 跨度
#   (缝秒不进入分母 —— 「未覆盖秒不归因」的承袭面, 使 span > cov 判据在缝跨游程时保持
#   有效)。速率 = round(delta_sum x 1000 / cov_ms), 一次算定不重写(旧 v4_rate_from_totals
#   的 delta/w 重写层退役)。
# - z 槽桶=0(z-run 语义承袭): z 槽快照冻结 -> 对差分恒 0, 全 z 桶速率 0 线链不断。
# - 同桶多槽: 快照取 ts 最晚者(同刻后到者优先); 桶 is_hold 旗 = 各槽 is_hold 的与。
# - 断链与判读承袭(P2, 在槽层一次算定内实现):
#   * null 标记(n 游程折叠 / 块间真空)断链 —— 标记后基线缺失 delta=None;
#   * 观测缝 = 对跨(gap) - 本槽声称覆盖(dt_s) > _V4_SEAM_NULL_S = 停机洞: delta=None
#     断链不摊配; 缝 > 0(未观测秒存在)置桶 broke 旗 —— 该向无差分覆盖时出 None
#     (未知 != 0, issue 26-10-16-0954), 无缝的链首桶(程序/窗口起点)保留 0 线(D4);
#   * cur < last 计数器重置: 逐向 delta=None;
#   * 接缝摊配: 长 z 形等值游程末端的台阶按真实跨度摊配到游程桶 + 接收桶 —— 判据 =
#     (marked / span > cov / span > max(2 x 接收槽 dt, 60s)) 且游程全 z 形; cov = 逐对
#     「对跨 - 未观测秒」合计(缝秒不进分母 —— 缝跨游程中段时 span > cov 恒有效, 不依
#     赖 marked 存活); 份额按覆盖毫秒比例取整, 余额归接收桶, 严格守恒; 游程内有未观测
#     缝时基准 step_w = step x cov // span(未覆盖秒不归因); flat-r 游程不摊(z 形签名
#     必要条件)。
# - 有界空桶持有回填(计划 §03 F2 后半/R8, 26-11-15-1104 T3 实装): 活跃链内空样本桶
#   (前后两观测槽跨过的栅格桶, dt 修正跳变恰跨桶界/长间隔 z 槽是常态来源)且前后观测间隙
#   <= gap_bound_s(max(B, si) x 2 —— 与 F3 尾桶 holding 同一条判据单点:「最新已知状态仍
#   有效」)时, 按持有语义回填前桶速率(held 面, is_hold 旗透传; totals = 前桶末次快照同值
#   —— 累计面不造字节, 字节守恒由 totals 链保证: 漏采区间字节含在后继样本快照差分里,
#   held 比 null 更诚实)。真停滞/断连不回填: 间隙过界(> 判据界)与 null 标记(n 游程/块间
#   真空 —— 断连语义)保持 null; 「空样本桶 = null」随之收窄为「间隙过界的空桶」。回填点
#   值只依赖源观测桶的已定影面(速率/快照在走槽期已终值), 封口桶不可变不受回填影响
#   (回填发生时空桶本就在开放面, 其值不依赖后继样本)。
# - 封口桶不可变(T4/T5 桶值缓存的正确性根基): 桶值定影 = **样本已齐且不在开放等值游程
#   的覆盖内**(当且仅当二者)—— 等值游程闭合(台阶到达或输入末尾)且摊配完成后, 其覆盖
#   桶连同此前全部桶定影, 定影桶值只依赖已落定样本, 后续追加样本不得改写; 两条例外不
#   定影: 开放等值游程覆盖的桶(游程闭合前可被摊配回写改写, 份额依赖后继台阶)+ 台阶
#   接收桶/进行中桶(样本未齐, 闭合时刻后继等值游程闭合摊配仍可回写)—— **T4 增量解析
#   的桶值缓存封口判定必须纳入这两类不定影, 进行中桶由「每请求现算」规则另行排除**。
#   守阵: test_traffic_grid_f2_battery::test_sealed_bucket_immunity_to_late_step。
# - 窗口与链: ts >= t1 槽不消费(holding 豁免); 消费下界 = grid.t0 - interval -
#   _V4_SEAM_LOOKBACK_S(P2: 摊配的变化点跨度锚可远在窗外, 差分链保留完整陈旧跨度);
#   窗外桶照常入流(链上下文), 响应由 v4_grid_obs 栅格过滤承载; null 点标记与链同界。
# - 活尾合流(S6 验收追加, 2026-10-05): tail_slots(采样模块活尾快照续链产物)追加在磁盘
#   链之后 —— 按槽 ts 与磁盘链精确去重(镜像保证: 同一记录写侧游标推进与落盘重算的
#   槽 ts 恒等, 保留严格更晚的后缀即不重不漏); **块间真空判定与磁盘块同判**(issue
#   26-10-16-0954 修复轮: head_pending 的活尾首槽是块首记录(重启后 B.start), 与磁盘链
#   末槽可隔一整段停机; 不判则活尾缝在磁盘缝有标记/无标记之间摇摆)。
# - holding 槽(F3 新定义, 计划 26-11-15-1104; 承袭 F4 计划 26-11-14-1313): 尾桶 = 进行中
#   桶, 速率 = 持有末次观测速率(held); 停滞/断连不延伸(诚实边界承袭 F4, codec 侧裁决);
#   延伸窗口含链端超前至多一个写侧漂移容差的伪迹面(F3: 超前是负向漂移未及修正的游标
#   伪迹非停滞, 不延伸会让活跃链尾桶间歇 null —— A5; 详 codec v4_live_tail_slots)。
#   is_hold 槽豁免 ts >= t1 窗尾过滤, 归桶走点位归属同一路径(_bucket_index —— ts=now 恒
#   落进行中桶 grid.last; 半秒级桶宽的相位边缘 now 可溢出一格, 钳回 grid.last 以响应栅格
#   形状为准), 与末样本同桶则天然合并(合并歧义随双几何消失 —— T2 的「桶键恒 grid.last」
#   临时规则按此精调), 不进速率面差分(0 delta / 0 覆盖, 不稀释同桶真实观测), 桶 is_hold
#   (全槽持有)时速率 = 持有上一非持有观测桶速率(null 点清空持有面; 前桶速率派不出时持有
#   None —— 诚实未知); totals 面快照同值 0 增量, 累计面不造字节。
# ======================================================================

#: 真空判定浮点容差(秒): 块间 gap 与首记录覆盖桶的比较 ε
_V4_VACUUM_EPS_S = 1e-6

#: 接缝摊配触发下限(秒, plan 26-10-15-0829 P2): 快照台阶的变化点跨度超过
#: max(2 x 接收桶宽, 本值) 才按真实跨度摊配 —— 2x 桶宽即「明显大于单桶宽」, 本值兜底
#: 防高频采样把普通抖动摊平(计划 §06 R2)。模块常量非配置键(P2 拍板默认: 不新增配置键)。
_V4_SEAM_SPREAD_MIN_S = 60

#: 观测缝停机洞阈值(秒, plan 26-10-15-0829 P2 诚实兜底): 相邻两观测桶点的覆盖缝超过
#: 本值 = 停机洞 -> 差分断链(delta=None, 宁可丢弃不摊配 —— G2/E2E3 诚实性); <= 本值 =
#: 重启缝 -> 接缝差按真实跨度摊配回收(P0 实施记录 2, G3/E2E4 受益)。
#: !语义锚定(plan §03 P0 实施记录 REC): 摊配分母 = 变化点跨度(可长达整个 z 游程,
#: 本事故 6.6h), 洞判定分母 = 观测覆盖缝(重启 ~10s)—— 两量分离; 「超 SEAM_NULL_S
#: 标 null」约束的是后者, 若约束前者则长游程陈旧差永不可摊, 与「两缝一并治理」矛盾。
_V4_SEAM_NULL_S = 60

#: 差分链窗外回看界(秒, plan 26-10-15-0829 P2 实施期扩展落点): 块内槽点与 null 点标记的
#: 保留下界从「覆盖桶触及 t0 / t0-1」放宽到「覆盖桶末端 >= t0 - 本值」(P2 史述 —— 该口径
#: 随 cell 覆盖桶几何于 26-11-15-1104 F2 退役)—— 接缝摊配的变化点
#: 跨度锚(冻结值建立点)可能远在窗外(本事故 6.6h), 窗界截断会把摊配分母压回窗内残余跨度,
#: 窄窗重新放大 ~15x(G1「三窗峰值同量级」被破)。界取写侧游程强制封口上限 ZRUN_FLUSH_S
#: 同值(traffic_sample_mod, 86400s): 陈旧跨度物理上不可能超过它; 超界槽点只可能是前缀
#: (块按天切, 过滤单调), 差分链在保留首点重锚, 无中断风险。
#: !F2 现行口径(26-11-15-1104): 保留界 = 槽点 ts >= t0 - interval - 本值(v4_series_points
#: 槽过滤; 比旧「覆盖桶末端」公式宽一个 interval —— 点位归属下无覆盖桶末端可述), null
#: 点标记同界。渲染不受影响: 窗外槽点由
#: v4_grid_obs 桶键窗口过滤承载(26-11-15-1104 F2 直映), D3 窗首种子语义不变(被完整链
#: 自然包含)。
#: !取代 issue 26-10-08-0141 的 _V4_NULL_FLOOR_S=1 秒标记带: 标记与点同界后, 原 1 秒带
#: 整段被包含 —— 标记窄于点界会在窗外重建该 issue 的断链失效假尖峰(带外标记被丢而种子
#: 点因回看保留, 链误接)。null 点恒不外发(v4_grid_obs 跳过), 多留的标记只影响断链位置。
_V4_SEAM_LOOKBACK_S = 86_400


@dataclass(frozen=True)
class V4PointEntry:
    """v4 读侧单桶点(F2 点位归属归桶后 = 栅格桶点, 即响应桶的真值形态)

    t = 栅格桶键(first + i x interval 同式派生; 窗外链上下文桶可为 < grid.first);
    rate = 桶速率(桶内样本差分和 / 覆盖时长, 一次算定; 单向 None = 该向差分派不出
    —— 基线缺失/重置/断链/停机洞; 双 None 且无速率覆盖的 broke 桶 = 断链未知, 链首桶
    出 0 线); rate/totals 全 None = null 点(n 游程/块间真空标记, 断线语义 —— v4 r/z 行
    无 null 形态, null 只来自这两种标记)。w = 桶覆盖时长秒(差分对跨实测毫秒合计, 逐向
    豁免取最大; null 点恒 0)。is_hold = 持有面桶点(活尾 holding F4/F3 或空桶持有回填
    F2/R8): 速率面持有上一观测桶速率, totals = 源观测桶末次快照(链 0 增量不造字节)。
    """

    t: Any  # 栅格桶键(整值宽 int, 半秒宽 float —— 与 grid.buckets 同式派生逐位相等)
    dl_rate: Optional[int] = None  # 桶内下载速率(bytes/s, round 取整)
    up_rate: Optional[int] = None
    dl_total: Optional[int] = None  # 桶末 all-time 下载累计快照(bytes)
    up_total: Optional[int] = None
    w: float = 0.0  # 桶覆盖时长秒(差分对跨实测和; null 点恒 0)
    is_hold: bool = False  # True = 持有面桶点: 活尾 holding(F4/F3)或空桶持有回填(F2/R8)—— 速率面持有上一观测桶速率


def v4_series_slots(blocks: tuple) -> tuple:
    """块序列 -> 扁平槽序(记录时间轴层; S3b agg 段合流的接缝): 块按 start_epoch 升序
    (稳定排序, 同刻保文件序), 逐块 v4_block_slots 展开(复用 S1 游标 dt 链, 不另写推算)。"""
    out: list[Any] = []
    for blk in sorted(blocks, key=lambda b: b.start_epoch):
        out.extend(v4_block_slots(blk))
    return tuple(out)


def _bucket_index(ts: float, first: Any, interval: Any) -> int:
    """槽 ts 的点位归属桶序(F2 点位归属单点): 含 ts 的栅格桶下标

    起步 floor((ts - first)/interval) + 双向校正到「b <= ts < b 的下一桶」, 桶键恒以
    first + i x interval 单一表达式派生 —— 与 grid.buckets 同式, 浮点逐位相等(obs.get
    与 rate_points/group_* 的键查找恒命中; 异式派生在非 0.5 步进宽下差 1 ulp, 有观测桶
    渲染成 null 洞 —— 评审 blocker 实证, 26-11-15-1104 F2 后本函数是唯一的槽 -> 桶路径)。
    """
    i = int(math.floor((ts - first) / interval))
    while first + i * interval > ts:
        i -= 1
    while first + (i + 1) * interval <= ts:
        i += 1
    return i


def _check_gap_bound(gap_bound_s: Optional[float], interval: float) -> float:
    """gap_bound_s 校验与缺省单点(v4_series_points 与桶值缓存共用, fail-fast 同判据):
    须正有限数值, 缺省 None 落 grid.interval x 2(raw 段桶宽恒为采样整倍, F1, B >= si,
    数学上与调用面公式 max(interval_s, 采样间隔) x 2 恒等)。"""
    if gap_bound_s is not None and (
        not isinstance(gap_bound_s, (int, float)) or isinstance(gap_bound_s, bool) or not math.isfinite(gap_bound_s) or
        gap_bound_s <= 0
    ):
        raise ValueError(f"非法 gap_bound_s(须正有限数值): {gap_bound_s!r}")
    return float(gap_bound_s) if gap_bound_s is not None else float(interval) * 2.0


def _v4_null_lo(grid: "WindowGrid") -> float:
    """差分链消费下界单点(null 点/差分链同界): t0 - interval - 回看界 —— 调用面读文件已按
    seed_t0 = t0 - interval 外扩一天, 此处再退一个回看界 —— 接缝摊配的变化点跨度锚可远在
    窗外(P2, 详 _V4_SEAM_LOOKBACK_S 常量注释)。"""
    return grid.t0 - grid.interval - _V4_SEAM_LOOKBACK_S


class _V4SeriesFold:
    """v4_series_points 的折叠状态机(F4-2, 计划 26-11-15-1104 S2-2): 归桶/差分/摊配语义
    的唯一实现, 两种驱动方式共用同一槽循环 —— 全量(一次喂全部块组, v4_series_points 包装)
    与增量(按游标只喂新增槽组, V4SeriesBucketCache 驱动)。状态字段即原闭包局部态的逐字
    平移, 行为零改动(存量电池 test_traffic_grid_* 全量钉住)。

    增量驱动的语义锚(与「每请求全量现算」逐位等价的依据, 详见 V4SeriesBucketCache):
    - 状态仅由「已消费槽」决定; 已消费 = ts < t1 且 ts >= null_lo(两界单调, 消费集恒为
      槽流前缀), 故游标式续喂 + 窗界外槽重展重判 与 全量现算逐请求同构;
    - marked 以 marked_ts(标记点位置)承载: marked 等价于 marked_ts 已设且 >= null_lo
      (全量路径标记入列恒 >= null_lo, 二者恒等; 增量路径据此对「标记已滑出回看界」的
      陈旧态再判定, 对齐全量现算的重建结果);
    - 折叠态不含窗界: cells/游程/标记位置全在绝对桶键格上(F2 桶键 = first + i x interval
      单一表达式, 同一 interval 下跨请求逐位相等), 窗界只在槽过滤与发射过滤处生效。
    """

    __slots__ = (
        "cells",
        "cell_keys",
        "marks",
        "backfills",
        "prev_chain_end",
        "prev_slot",
        "last_was_null",
        "marked_ts",
        "null_since_obs",
        "dl_run",
        "up_run",
    )

    def __init__(self) -> None:
        self.cells: dict[Any, list] = {}
        # 桶键按插入序 = 升序(槽流时序单调 -> 归桶键非降; 发射/封口按此二分, 免整排)
        self.cell_keys: list = []
        self.marks: list = []  # null 点 t —— n 游程折叠 + 块间真空(入列时已按 [null_lo, t1) 过滤)
        self.backfills: list = []  # (空桶键, 源观测桶键) —— 有界空桶持有回填(F2/R8), 发射期装配
        self.prev_chain_end: Optional[float] = None
        self.prev_slot: Optional[tuple] = None  # 上一观测槽 (ts, dl_total, up_total) —— 差分链
        self.last_was_null = False
        self.marked_ts: Optional[float] = None  # 自上一观测槽以来末个 null 点位置(None = 无)
        # 自上一观测槽以来出现过 null 槽/组界缝(不限窗界 —— 标记入列有 [null_lo, t1) 界,
        # 界外 null/真空不产标记点但仍属断连面): 有界空桶持有回填判据的「活跃链」支之一
        self.null_since_obs = False
        # 逐向游程状态: [游程值, 锚点 ts, [(桶键, 覆盖毫秒, 是否 z 槽, 槽 ts)], 前缀覆盖毫秒]
        # (前缀 = 已裁剪游程项的覆盖毫秒合计 —— 缓存逐出裁剪后摊配算术守恒用, 全量路径恒 0)
        self.dl_run: list = [None, 0.0, [], 0]
        self.up_run: list = [None, 0.0, [], 0]

    def copy(self) -> "_V4SeriesFold":
        """活尾折叠专用副本: 磁盘链状态不动, 活尾槽组折在副本上发射 —— 活尾快照
        每请求整体替换(非追加不变式), 绝不入持久状态。桶累加器是可变列表, 逐桶浅拷
        (活尾槽会原位改写快照列 e[4]/e[5]/e[6] —— 共享即污染持久态); 其余元素不可变,
        一层拷贝即足。"""
        f = _V4SeriesFold()
        f.cells = {k: list(v) for k, v in self.cells.items()}
        f.cell_keys = self.cell_keys.copy()
        f.marks = self.marks.copy()
        f.backfills = self.backfills.copy()
        f.prev_chain_end = self.prev_chain_end
        f.prev_slot = self.prev_slot
        f.last_was_null = self.last_was_null
        f.marked_ts = self.marked_ts
        f.null_since_obs = self.null_since_obs
        f.dl_run = [self.dl_run[0], self.dl_run[1], self.dl_run[2].copy(), self.dl_run[3]]
        f.up_run = [self.up_run[0], self.up_run[1], self.up_run[2].copy(), self.up_run[3]]
        return f

    def sanitize(self, null_lo: float) -> bool:
        """增量折叠前的窗界再对齐(F4-2): 把「由已滑出回看界的槽承载」的状态面对齐
        全量现算在当前 null_lo 下的语义(全量现算只消费 ts >= null_lo 的槽):
        - prev_slot: 基线槽已滑出回看界 -> 置 None(全量现算链首同样无基线);
        - marked_ts: 标记点已滑出回看界 -> 置 None(全量现算不入列该标记, marked=False)。
        返回 True = 游程锚点已滑出回看界 —— 调用方必须整条目冷重建(语义单点 = 全量
        现算, 与失效面 b/c 同路径; 此地不做局部重建: 「锚点前缀裁剪 + e0 重锚」会丢
        被裁剪项的覆盖累计且不重推桶累加器, 与全量现算非逐字段等价)。
        可达性: 冷折叠/读集前沿(c2)重建后, 游程锚点恒为读集内记录, 而 null_lo <
        窗首种子 <= 读集任意记录 —— 单个 c2 生命周期内锚点不可能滑出回看界, 本返回值
        常态恒 False, 仅作跨失效面组合的防御路径(触发即冷重建, 不静默续折)。
        """
        if self.prev_slot is not None and self.prev_slot[0] < null_lo:
            self.prev_slot = None
        if self.marked_ts is not None and self.marked_ts < null_lo:
            self.marked_ts = None
        for run in (self.dl_run, self.up_run):
            if run[0] is None and not run[2]:
                continue  # 未立游程(锚点 0.0 是初值哨兵, 非「滑出」)
            if run[1] < null_lo:
                return True
        return False

    def fold(
        self, groups, first: float, last: float, interval: float, t1: float, null_lo: float, gap_bound: float
    ) -> None:
        """槽组折叠(唯一槽循环; groups = (slots, is_tail) 序列): 语义 = v4_series_points
        原实现的逐字平移(判读见该函数 docstring 与区头「归桶模型」)。"""
        cells = self.cells
        cell_keys = self.cell_keys
        marks = self.marks
        backfills = self.backfills
        prev_slot = self.prev_slot
        marked = self.marked_ts is not None and self.marked_ts >= null_lo

        def held_backfill(i_prev: int, i_cur: int, gap: float) -> None:
            """有界空桶持有回填判据单点(F2 后半/R8): 活跃链内空桶(开区间 (i_prev, i_cur))
            且前后观测间隙 <= gap_bound 时按持有语义回填(与 F3 尾桶 holding 同一条规则:
            「最新已知状态仍有效」, 界值同 _tail_gap_bound 单点); 间隙过界(真停滞)与
            marked/null_since_obs(n 游程/块间真空 —— 断连语义, 含窗界外不产标记点的 null/
            真空)不回填保持 null。源桶 = i_prev 桶(发射期
            经 held 面持有其速率, totals 取其末次快照 —— 链 0 增量, 字节守恒由后继样本
            快照差分承载)。判据界下每区间至多 1 枚空桶(前后观测都在各自桶内 -> gap >
            (i_cur - i_prev - 1) x interval, gap <= 2 x interval 推出 i_cur <= i_prev + 2)。"""
            if marked or self.null_since_obs or gap > gap_bound:
                return
            for j in range(i_prev + 1, i_cur):
                backfills.append((first + j * interval, first + i_prev * interval))

        def bucket_add(key: Any, d: int, share: int) -> None:
            """摊配份额入桶(游程桶在差分链上先于接收槽出现, 桶累加器必已存在; 缓存路径
            的游程项可被逐出裁剪 —— 其桶在裁剪地平线之下, 永不进响应栅格, 份额可弃)"""
            e = cells.get(key)
            if e is None:
                return
            if d == 0:
                e[0] += share
            else:
                e[2] += share

        for slots, is_tail in groups:
            if not slots:
                continue
            if self.prev_chain_end is not None:
                if is_tail:
                    slots = tuple(s for s in slots if s.ts > self.prev_chain_end + _V4_VACUUM_EPS_S)
                    if not slots:
                        continue
                # 块间真空: 本组首槽声称覆盖(dt_s)接不住上组游标终值 -> 差值段出 null 点
                # (磁盘块与活尾同判 —— 活尾首槽抵达不了链末槽 = 中间有未观测段(重启缝),
                #  同块续链的槽 dt 链天然接住链末槽, 不出标记; issue 26-10-16-0954 修复轮)
                if slots[0].ts - slots[0].dt_s > self.prev_chain_end + _V4_VACUUM_EPS_S:
                    self.null_since_obs = True  # 组界缝(窗界外不产标记点但仍属断连面, 回填判据用)
                    t = int(self.prev_chain_end)
                    if null_lo <= t < t1:
                        marks.append(t)
                        self.marked_ts = t
                        marked = True
            for s in slots:
                if s.obs is None:
                    # n 槽: 连续 null 槽折叠为一个 null 点(首槽位置取整; 断连语义)
                    self.null_since_obs = True  # 窗界外 null 不产标记点但仍属断连面(回填判据用)
                    t = int(math.floor(s.ts))
                    if null_lo <= t < t1 and not self.last_was_null:
                        marks.append(t)
                        self.marked_ts = t
                        marked = True
                    self.last_was_null = True
                    continue
                self.last_was_null = False
                if s.ts >= t1 and not s.is_hold:
                    continue  # 窗尾之后的槽不消费(v2 ts >= t1 口径); holding 槽豁免(F4)
                o = s.obs
                if s.is_hold:
                    # holding 槽(F3 新定义, 承袭 F4 最小搬运): 合成持有面非采样观测 —— 归桶
                    # 走点位归属同一路径(_bucket_index; ts=now 恒落进行中桶 grid.last, 半秒级
                    # 桶宽的相位边缘 now 可溢出一格 -> 钳回 grid.last, 响应栅格形状以
                    # grid.buckets 为准), 与末样本同桶天然合并(合并歧义随双几何消失), 不进
                    # 差分链不占覆盖(0 delta / 0 覆盖, 不稀释同桶真实观测), 只更新快照与
                    # is_hold 旗; 链上此前的空桶按同一回填判据单点持有
                    key = min(first + _bucket_index(s.ts, first, interval) * interval, last)
                    if prev_slot is not None:
                        i_prev = _bucket_index(prev_slot[0], first, interval)
                        i_hold = _bucket_index(key, first, interval)
                        if i_hold > i_prev + 1:
                            held_backfill(i_prev, i_hold, s.ts - prev_slot[0])
                    e = cells.get(key)
                    if e is None:
                        cells[key] = [0, 0, 0, 0, s.ts, o[2], o[3], False, True]
                        cell_keys.append(key)
                    else:
                        e[8] = e[8] and s.is_hold  # 任一非持有槽在桶 -> 非 holding 桶
                        if s.ts >= e[4]:
                            e[4] = s.ts
                            e[5] = o[2]
                            e[6] = o[3]
                    self.prev_chain_end = s.ts
                    self.marked_ts = None
                    marked = False
                    self.null_since_obs = False
                    continue
                if s.ts < null_lo:
                    continue  # 差分链窗外回看界之外的槽不消费(P2: 保留完整陈旧跨度)
                i_cur = _bucket_index(s.ts, first, interval)
                key = first + i_cur * interval
                # 有界空桶持有回填检测(F2/R8): 本槽与上一观测槽跨过的空桶(活跃链内 —— marked
                # 为假即无 null 标记; 间隙判据在 held_backfill 单点)
                if prev_slot is not None:
                    i_prev = _bucket_index(prev_slot[0], first, interval)
                    if i_cur > i_prev + 1:
                        held_backfill(i_prev, i_cur, s.ts - prev_slot[0])
                dur_ms = 0 if prev_slot is None else int(round((s.ts - prev_slot[0]) * 1000))
                # 未观测秒 = 对跨 - 本槽声称覆盖(dt_s): 块内链式推进恒 0; 组界(重启/断连/
                # 停机)为正值 —— > 0 置 broke(断链桶出 None 非 0 线), > 60s 为停机洞
                unobs_ms = 0 if prev_slot is None else dur_ms - int(round(s.dt_s * 1000))
                # 覆盖时长(本对的分母/摊配份额权重)= min(对跨, 声称覆盖 dt): 连续链恒 =
                # 对跨; 含缝对只计声称覆盖 —— 缝秒不进分母(「未覆盖秒不归因」), 使 span > cov
                # 摊配判据在缝跨游程中段时保持有效(评审轮1 #1: 覆盖按对跨累计会使
                # span > cov 恒假且 marked 在等值续槽时清零, 台阶整段落接收桶出单桶尖峰,
                # 复现 issue 26-10-16-0954); 声称覆盖超声对跨(亚秒病理槽序)取对跨
                cov_ms_pair = dur_ms - max(0, unobs_ms)
                hole = unobs_ms > _V4_SEAM_NULL_S * 1000
                # broke = 本槽与上一观测槽之间存在未观测秒: 组界对跨超声称 dt, 或 null 标记
                # 先于本槽(断连/真空 —— 标记本身即未观测段; 链首无前槽时 gap 无量可测,
                # marked 即缺口)。无缝的链首桶(程序/窗口起点)不置旗 -> 0 线(D4)
                broke = unobs_ms > 0 or marked
                e = cells.get(key)
                if e is None:
                    e = cells[key] = [0, 0, 0, 0, s.ts, o[2], o[3], broke, s.is_hold]
                    cell_keys.append(key)
                else:
                    e[7] = e[7] or broke  # 断链旗跨同桶后继槽存活(不清成 0 线)
                    e[8] = e[8] and s.is_hold
                if s.ts >= e[4]:  # 快照取 ts 最晚者(同刻后到者优先)
                    e[4] = s.ts
                    e[5] = o[2]
                    e[6] = o[3]
                is_z = s.is_zero
                for d, cur, run in ((0, o[2], self.dl_run), (1, o[3], self.up_run)):
                    # 差分对逐向处理(端点归属: delta 记 cur 所在格); 等值游程入列需 z 形签名
                    value, _, run_list, run_prefix = run
                    if value is None or hole or cur < value:
                        run[0], run[1], run[2], run[3] = cur, s.ts, [], 0
                        delta = None
                    elif cur == value:
                        run_list.append((key, cov_ms_pair, is_z, s.ts))
                        delta = 0
                    else:
                        step = cur - value
                        span_ms = int(round((s.ts - run[1]) * 1000))
                        cov_ms = run_prefix + sum(dd for _, dd, _, _ in run_list) + cov_ms_pair
                        if (
                            cov_ms > 0 and dur_ms > 0 and (
                                marked or span_ms > cov_ms or
                                span_ms > max(2 * int(round(s.dt_s * 1000)), _V4_SEAM_SPREAD_MIN_S * 1000)
                            ) and all(z for _, _, z, _ in run_list)
                        ):
                            # 接缝摊配(P2 承袭): 未覆盖秒不归因 -> 基准先按覆盖份额缩放
                            # (span <= cov 时逐字 == step); 份额按累计比例取整, 余额归接收桶
                            # (前缀覆盖毫秒 = 已裁剪游程项的合计, 计入累计但不再入桶 —— 其桶
                            #  在裁剪地平线下, 永不进响应栅格)
                            step_w = step if span_ms <= cov_ms else step * cov_ms // span_ms
                            acc = 0
                            cum = run_prefix
                            for k, dd, _, _ts in run_list:
                                cum += dd
                                target = step_w * cum // cov_ms
                                share = target - acc
                                acc = target
                                if share:
                                    bucket_add(k, d, share)
                            delta = step_w - acc
                        else:
                            delta = None if marked else step
                        run[0], run[1], run[2], run[3] = cur, s.ts, [], 0
                    if delta is not None and cov_ms_pair > 0:
                        # 速率面入账(端点归属): 覆盖时长为 0(同刻病理槽序)不归因不造分母
                        if d == 0:
                            e[0] += delta
                            e[1] += cov_ms_pair
                        else:
                            e[2] += delta
                            e[3] += cov_ms_pair
                prev_slot = (s.ts, o[2], o[3])
                self.marked_ts = None
                marked = False
                self.null_since_obs = False
            self.prev_chain_end = slots[-1].ts  # 游标终值 = 末槽实测时刻(真空判定基准)
        self.prev_slot = prev_slot

    def _cell_point(self, key: Any, e: list) -> V4PointEntry:
        """桶累加器 -> 桶点(发射期单桶装配, 全量/增量发射共用)"""
        dl_cov, up_cov = e[1], e[3]
        if e[8]:  # holding 桶(F4/F3): 速率面在合并序里持有上一观测桶
            dl = up = None  # 占位, 合并期回填
        else:
            dl = int(round(e[0] * 1000 / dl_cov)) if dl_cov > 0 else (None if e[7] else 0)
            up = int(round(e[2] * 1000 / up_cov)) if up_cov > 0 else (None if e[7] else 0)
        return V4PointEntry(key, dl, up, e[5], e[6], w=max(dl_cov, up_cov) / 1000, is_hold=e[8])

    def emit(
        self,
        lo: Optional[float],
        hi: Optional[float],
        held_init: Optional[tuple],
        sealed: Optional[dict] = None,
        hi_inclusive: bool = True,
    ) -> list:
        """发射 [lo, hi] 桶点列(held 面合并序; lo/hi None = 无界 —— 全量发射)。

        hi_inclusive=True(缺省, 响应路径)= 含 hi 桶; False(封口发布路径)= [lo, hi)
        —— 封口边界桶(进行中桶)不定影, 不入发布回放。
        held_init = 合并扫描在 lo 之前应携带的 held 值(全量路径 None; 缓存路径 =
        封口面末端扫描值, 使开放面的持有桶与全量现算同源)。sealed = 封口桶值表
        (桶键 -> V4PointEntry), 供回填源桶已封口时的快照解析(cells 已裁剪时)。
        标记点(null 点)照常入列参与 held 合并 —— 调用方按 v4_grid_obs 口径过滤不外发。
        """
        items = []
        keys = self.cell_keys  # 插入序 = 升序(时序单调归桶), 二分取段免整排
        i0 = 0 if lo is None else bisect.bisect_left(keys, lo)
        if hi is None:
            i1 = len(keys)
        elif hi_inclusive:
            i1 = bisect.bisect_right(keys, hi)
        else:
            i1 = bisect.bisect_left(keys, hi)
        for k in keys[i0:i1]:
            items.append((k, 1, self._cell_point(k, self.cells[k])))
        for bf_key, src_key in self.backfills:
            if lo is not None and bf_key < lo:
                continue
            if hi is not None and (bf_key > hi or (not hi_inclusive and bf_key == hi)):
                continue
            # 有界空桶持有回填装配(F2/R8): is_hold 旗入下方合并序的 held 面 —— 速率 = 源桶
            # 速率(走槽期已终值, 封口桶不可变不受影响), totals = 源桶末次快照(链 0 增量,
            # 字节守恒: 漏采区间字节含在后继样本快照差分里); w = 0(无观测覆盖, 持有面)。
            # 源桶 = cells 表项; 已封口裁剪时经 sealed 封口值表解析(快照列同名)。
            src = self.cells.get(src_key)
            if src is not None:
                snap = (src[5], src[6])
            else:
                se = sealed.get(src_key) if sealed is not None else None
                if se is None:
                    raise KeyError(f"回填源桶缺失(封口表与累加器均无): {src_key!r}")
                snap = (se.dl_total, se.up_total)
            items.append((bf_key, 1, V4PointEntry(bf_key, None, None, snap[0], snap[1], w=0.0, is_hold=True)))
        for t in self.marks:
            if lo is not None and t < lo:
                continue
            if hi is not None and (t > hi or (not hi_inclusive and t == hi)):
                continue
            items.append((t, 0, V4PointEntry(t)))
        # null 点排同刻观测点之前(null 在先 = 该时刻断线、其后才是观测覆盖; 稳定保插入序)
        items.sort(key=lambda x: (x[0], x[1]))
        out = []
        held = held_init  # 上一非持有观测桶的速率(holding 持有面; null 点清空)
        for _, _, p in items:
            if p.dl_rate is None and p.up_rate is None and p.dl_total is None and p.up_total is None:
                held = None  # null 点: 不跨断口持有
                out.append(p)
                continue
            if p.is_hold:
                dl, up = held if held is not None else (None, None)
                out.append(V4PointEntry(p.t, dl, up, p.dl_total, p.up_total, p.w, is_hold=True))
            else:
                held = (p.dl_rate, p.up_rate)
                out.append(p)
        return out

    def held_at(self, position: float, fallback: Optional[tuple]) -> Optional[tuple]:
        """合并扫描在 position 处应携带的 held 值(缓存路径发射 [grid.first, grid.last] 段
        的 held 初值): 开放面中 < position 的项按降序扫 —— 首个非持有观测桶给其速率,
        null 标记先行即 None(None 点清空持有面), 持有桶(回填/尾桶)不携带不入账;
        开放面无项 -> fallback(封口面末端 held 值)。与全量发射的合并序逐位同判。"""
        keys = self.cell_keys
        ci = bisect.bisect_left(keys, position) - 1
        marks = [t for t in self.marks if t < position]
        mi = len(marks) - 1
        bi = len(self.backfills) - 1
        while True:
            cands = []
            if ci >= 0:
                cands.append((keys[ci], 2))
            if mi >= 0:
                cands.append((marks[mi], 0))
            if bi >= 0 and self.backfills[bi][0] < position:
                cands.append((self.backfills[bi][0], 1))
            if not cands:
                return fallback
            pos, kind = max(cands)
            if kind == 0:
                return None  # null 标记先于任何观测桶: 持有面清空
            if kind == 1:
                bi -= 1  # 回填桶 = 持有面, 不携带 held, 继续向前扫
                continue
            e = self.cells[keys[ci]]
            if e[8]:
                ci -= 1  # holding 桶: 速率来自更前的观测桶, 继续向前扫
                continue
            p = self._cell_point(keys[ci], e)
            return (p.dl_rate, p.up_rate)

    def sealed_floor(self, first: float, interval: float, null_lo: float) -> Optional[float]:
        """封口边界(F4-2, 与区头「封口桶不可变」定影定义单点对齐): min(开放等值游程
        覆盖的最低桶键, 进行中桶键) —— 全部 < 本值的桶键定影(样本已齐 = 差分链已走过
        (键 < 上一观测槽所在桶), 且不在开放等值游程覆盖内); 台阶接收桶 = 上一观测槽
        所在桶(未齐), 开放游程覆盖桶 = 游程项键(未定影)。prev_slot 为 None(链首无观测)
        而累加器非空(观测全在回看界外)时以 null_lo 兜底: 回看界外桶值不再受任何后续
        槽影响(新槽消费下界同界), 视同定影。无任何候选(无观测无游程)返回 None。"""
        cands = []
        for run in (self.dl_run, self.up_run):
            if run[2]:
                # 首项即最小键: 游程项按槽时序追加(归桶键非降), 裁剪只删前缀 —— O(1)
                # 取首, 不做全表扫描(空闲长游程表可达窗内槽数量级)
                cands.append(run[2][0][0])
        if self.prev_slot is not None:
            cands.append(first + _bucket_index(self.prev_slot[0], first, interval) * interval)
        elif self.cells:
            cands.append(null_lo)
        return min(cands) if cands else None


def v4_series_points(
    blocks: tuple, grid: "WindowGrid", tail_slots: tuple = (), gap_bound_s: Optional[float] = None
) -> tuple:
    """v4 读侧核心(§05.1/§05.2; 26-11-15-1104 F2 点位归属归桶): 块序列 -> 栅格桶点列

    blocks = V4Block 序列(单系列的若干天文件解析产物合并传入; 天文件按日期升序读出,
    块不跨天故按 start_epoch 排序即恢复时间序)。grid = 目标窗栅格(WindowGrid)——
    点位归属归桶的键源: 样本槽按 floor(ts/B)xB 落格, 桶键 = first + i x interval 同式
    派生(与 grid.buckets 逐位相等); 桶速率 = 桶内样本差分和 / 覆盖时长, 一次算定
    (规则全景见本区头注释「归桶模型」)。
    tail_slots = 活尾快照槽序(S6 验收追加, v4_live_tail_slots 产物; 缺省空 = 纯磁盘读):
    追加在磁盘链之后 —— 按槽 ts 与磁盘链精确去重(同一记录「写侧游标推进」与「落盘后
    重算」的槽 ts 恒等, 保留严格更晚的后缀即不重不漏), 且与磁盘块**同判块间真空**
    (issue 26-10-16-0954 修复轮: 首槽抵达不了磁盘链末槽 = 中间有未观测段(重启缝),
    出 null 标记断链 —— 与磁盘块同一条判据, 两路径同几何取值一致; 同块续链天然不出标记)。
    无块且无活尾(停机/无数据)返回空元组(天然真空, 调用方按空态处理)。
    holding 槽(F3 新定义, 计划 26-11-15-1104; 承袭 F4, tail_slots 末尾的 is_hold 槽):
    豁免 ts >= t1 窗尾过滤, 归桶走点位归属同一路径(_bucket_index —— ts=now 恒落进行中
    桶 grid.last, 相位边缘溢出一格时钳回), 与末样本同桶天然合并, 不进速率面差分
    (0 delta / 0 覆盖), 桶 is_hold 时速率面持有上一非持有观测桶速率。
    有界空桶持有回填(计划 §03 F2 后半/R8, T3 实装): 活跃链内空桶且前后观测间隙
    <= gap_bound_s 时按持有语义回填前桶速率(与尾桶 holding 同一条判据单点); 间隙过界/
    null 标记(断连)不回填保持 null。封口桶不可变不变量见区头注释(回填不与之冲突:
    回填点值只依赖源桶已定影面, 空桶本就在开放面)。
    gap_bound_s = 持有回填/尾桶 holding 的间隙判据界(秒): 调用面传
    max(interval_s 桶宽, 采样间隔) x 2(traffic_qb._tail_gap_bound —— 与活尾延伸
    max_gap_s 同一单点值)。缺省 None 落 grid.interval x 2 —— raw 段桶宽恒为采样整倍
    (F1, B >= si), 数学上与调用面公式恒等; 显式传参仅为判据单点的字面归一。
    传值须正有限(违者 ValueError, fail-fast)。

    实现注(F4-2, 26-11-15-1104 S2-2): 槽循环体已平移进 _V4SeriesFold(全量驱动形态),
    语义零改动 —— 同一实现同时服务桶值单调缓存的增量驱动(V4SeriesBucketCache), 本函数
    即其全量参照面; 存量电池(test_traffic_grid_*)全部钉在本函数上。
    """
    first, last, interval = grid.first, grid.last, grid.interval
    gap_bound = _check_gap_bound(gap_bound_s, interval)
    null_lo = _v4_null_lo(grid)
    fold = _V4SeriesFold()
    groups = [(v4_block_slots(blk), False) for blk in sorted(blocks, key=lambda blk: blk.start_epoch)]
    if tail_slots:
        groups.append((tuple(tail_slots), True))
    fold.fold(groups, first, last, interval, grid.t1, null_lo, gap_bound)
    return tuple(fold.emit(None, None, None))


class _V4BucketDayCursor:
    """桶值缓存的单天消费游标(F4-2): 天文件按「只追加」不变式(R3)增长, 游标 =
    已消费槽流的前缀位置 —— 下轮请求只展开游标之后的槽(增量), 游标之前永不重展。

    - starts: 已整块消费的块 start_epoch 序列(校验面: 与 parsed.blocks 前缀逐一起点核对);
    - cur_start: 停驻块(部分消费)的 start_epoch; None = 停在块边界(下一未消费块 =
      blocks[len(starts)]);
    - rec_idx/slots_done/last_ts/run_base/run_spacing: 停驻块内的块级槽游标
      (v4_block_slots_from 同构 —— last_ts = 游程锚点 t, run_base/run_spacing = 游程形参);
    - last_rec: 最后消费的记录对象(冻结 dataclass, 等值校验用 —— 前缀防伪的廉价形)。
    """
    __slots__ = ("starts", "cur_start", "rec_idx", "slots_done", "last_ts", "run_base", "run_spacing", "last_rec")

    def __init__(self) -> None:
        self.starts: tuple = ()
        self.cur_start: Optional[int] = None
        self.rec_idx = 0
        self.slots_done = 0
        self.last_ts: Optional[float] = None
        self.run_base: Optional[float] = None
        self.run_spacing: Optional[float] = None
        self.last_rec: Any = None


def _v4_bucket_day_cursor_valid(cur: _V4BucketDayCursor, blocks: tuple) -> bool:
    """天游标与当前解析产物的结构一致性校验(F4-2 失效面): 起点前缀逐一对上 + 停驻块
    记录数未缩 + 末消费记录恒等。任一不符 = 结构性变化(裁剪重写/删除/外部改写)——
    调用方整条目冷重建(同输入重算恒等, 一次性代价)。前缀内容编辑(结构不变)不在
    校验面内: 天文件只追加是存储层不变式(R3), 写侧全在 open("a") 批量追加; 非追加写
    由 V4DayCache 增量解析探针在解析层退全量, 本层按结构面兜底。"""
    n = len(cur.starts)
    if n > len(blocks):
        return False
    for i, s in enumerate(cur.starts):
        if blocks[i].start_epoch != s:
            return False
    if cur.cur_start is not None:
        if n >= len(blocks) or blocks[n].start_epoch != cur.cur_start:
            return False
        recs = blocks[n].records
        if cur.slots_done > 0:
            if cur.rec_idx >= len(recs):
                return False
            rec = recs[cur.rec_idx]
            if rec != cur.last_rec or not isinstance(rec, (V4ZeroRun, V4NullRun)) or cur.slots_done > rec.run_len:
                return False
        else:
            if cur.rec_idx > len(recs):
                return False
            if cur.rec_idx > 0 and recs[cur.rec_idx - 1] != cur.last_rec:
                return False
    return True


class V4SeriesBucketCache:
    """raw 段窗桶值单调缓存(F4-2/3, 计划 26-11-15-1104 S2-2; §03 F4-2 / §06 R4 / §07 D5)

    正确性根基 = 区头「封口桶不可变」(T2/T3 定影定义, 单点对齐): 桶值定影 = 样本已齐
    且不在开放等值游程覆盖内 —— 定影桶值只依赖已落定样本, 后续追加样本不得改写, 命中
    恒安全。封口边界由 _V4SeriesFold.sealed_floor 按**同一处定义**计算(开放游程覆盖的
    最低桶键与进行中桶键取 min), 不另造第二套判据; 两类不定影例外(开放游程覆盖桶 +
    台阶接收桶/进行中桶)天然落在边界之上 = 每请求现算。

    - 键结构: (系列键, window) -> 条目; 桶键 = 绝对桶格 epoch(first + i x interval, F2
      单一表达式 —— 同一 interval 下跨请求逐位相等, 栅格随 now 平移不改桶键身份)。
      条目内再分: 封口值表(桶键 -> V4PointEntry, 定影面) + 折叠态(开放面) + 天游标。
    - 每请求只算增量: 天文件解析走 V4DayCache(T4, 只读), 本缓存持折叠态按游标只折新增
      槽(R6 口径 ~10ms -> 亚毫秒); 非封口桶(进行中桶/开放游程覆盖桶/台阶接收桶)在开放
      面每请求重发射, 绝不入封口值表; 活尾快照每请求整体替换(非追加), 折在状态副本上
      发射后即弃, 绝不入持久态。
    - LRU 上限 = 128 条目(系列键 x 窗): 组图一次请求驻留 M(可达 30)条, 用户在 2-3 个
      窗位间切换即 ~90 条 —— 64 会让组图整体反复逐出冷重建, 温态亚毫秒静默消失; 128 =
      30 x 3 窗 + 全局/单种余量。逐出 LRU(命中移队尾, 最久未用先逐出)。内存预算(分型
      如实账): 常规条目(活跃/混合流)= 封口值表(<= ~500 桶 x V4PointEntry)+ 开放面
      累加器(窗口 + 1 桶宽, 地平线裁剪保上界)+ 游程项(裁到 t0 - interval)≈ 0.1-0.5MB,
      128 条 ≈ 15-60MB; **病理形态(全天空闲 z 游程)单条目游程项按槽逐条入列且地平线
      只裁窗外键, 24h 窗内 57600 槽 x 2 向 4 元组 ≈ 15-20MB/条目**(实测 115188 项 x
      ~156B ≈ 18.0MB/条目, 基准 test_a4_bench_idle_* 打印; 128 条全空闲满窗驻留最坏
      ~2.3GB)—— 仅当「多窗位 x 多空闲 24h 系列」同时驻留才线性堆积, LRU 逐出兜底;
      空闲形态纯命中温态单种实测 ~4.5ms(A4 线内), 组图 M=30 空闲 ~200-240ms 超 A4
      组图线(纯空闲流永不封口 -> 全窗 ~498 桶每请求走开放面重发射 + fold.copy 游程表
      整表拷贝, O(窗内槽数)/成员/请求 —— 主会话拍板接受现状, 距 T5 前基线 ~25.6s/
      请求两个数量级, 见基准 test_a4_bench_group_m30_idle_warm 报告)。解析产物内存不
      在此预算(归 V4DayCache 的 V4_DAY_CACHE_BUDGET_BYTES 文本字节预算管 —— 组图活跃
      形态曾因 4MB 预算挤出 LRU 致每拍整天重解析 ~400ms, 26-11-16 拍板抬至 16MB 后
      温态 p95 = 11.15ms, 见基准 test_a4_bench_group_m30_warm 报告)。
    - 失效面(R4): (a) 天文件追加 = 增量(游标推进, 非失效); (b) 天文件结构性变化(裁剪
      重写/删除 —— 游标校验不过)、内容前缀变化的兜底、游程锚点滑出回看界(sanitize
      防御路径, 常态不可达 —— 详 _V4SeriesFold.sanitize)= 整条目冷重建(同输入重算恒等);
      (c) 配置变化(桶宽 interval / 采样间隔变更 -> 桶键格整体改变) = 条目丢弃冷重建;
      (c2) 读集前沿变化(窗首种子滑过本地日界, 最早读取日期更替 —— 差分链起点 = 读集
      最早记录, 旧日文件滑出读集后全量现算的链从新日首记录重锚, 链首桶 0 线语义随
      之改变)= 整条目冷重建(每条目每日至多一次, 一次性代价); (d) 组图成员集变化 =
      成员各按自身系列键查表, 新成员首请求冷算(组图冷态豁免, A4), 无组级缓存面
      (D5: Σ 聚合 M×~1ms 不设二级缓存); (e) 逐出 = LRU 上限。
    - 多实例隔离: 缓存实例随 QbTrafficChartApi 每域 router 一份(构造期预建)—— 实例
      身份即隔离边界, 不同 data_dir(qB 多实例)天然不同实例, 键不需另含实例身份。
    - 线程模型: 单锁串行(V4DayCache 同款)—— 读侧被 Web 线程并发调用, 折叠/发射/发布
      全程持锁(亚毫秒到冷算一次的量级); 只读文件在调用方(锁外), 本类只读传入的解析
      产物 + 自身内存态, 单一写线程假设(黄金法则 5)不涉及。
    - 幂等: 同输入(同解析产物 + 同栅格 + 同活尾)重算恒等(折叠为纯函数式推进)。
    """

    #: 条目数上界(LRU; 见类注内存预算段 —— M=30 组图 x 3 窗位 + 全局/单种余量)
    MAX_ENTRIES = 128

    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._max = max(1, int(max_entries))
        self._lock = threading.Lock()
        # (系列键, window) -> _V4BucketEntry
        self._entries: "OrderedDict" = OrderedDict()

    def series_points(
        self,
        key: str,
        days: tuple,
        grid: "WindowGrid",
        tail_slots: tuple,
        gap_bound_s: Optional[float],
        sample_interval: float,
    ) -> tuple:
        """单系列 raw 段窗 -> 栅格桶点列(封口值表命中 + 开放面重发射 + 活尾副本折叠)。

        days = V4DayCache.read_window 产物 ((date_str, V4ParsedDay | None), 按日期升序);
        grid = 请求栅格; tail_slots = 本请求活尾槽序(v4_live_tail_slots 产物, 不入持久态);
        gap_bound_s / sample_interval = 判据界与配置指纹(traffic_qb 同源传参)。返回点列
        (V4PointEntry, 含标记点 —— 调用方经 v4_grid_obs 过滤装配, 与全量现算同一下游)。
        OSError 不经过本类(调用方读文件在先), 读取竞态走端点 last-good 兜底(§08)。
        """
        if grid.segment != "raw":
            raise ValueError(f"桶值缓存仅服务 raw 段窗: {grid.name!r}({grid.segment!r})")
        gap_bound = _check_gap_bound(gap_bound_s, grid.interval)
        null_lo = _v4_null_lo(grid)
        with self._lock:
            ck = (key, grid.name)
            ent = self._entries.get(ck)
            if ent is not None and (ent.interval != grid.interval or ent.sample_interval != sample_interval):
                ent = None  # 配置面失效: 桶键格整体改变, 冷重建(失效面 c)
            if ent is not None and days and days[0][0] != ent.first_date:
                ent = None  # 读集前沿变化: 差分链起点重锚, 冷重建(失效面 c2)
            if ent is None:
                ent = _V4BucketEntry(grid.interval, sample_interval)
                ent.first_date = days[0][0] if days else None
                self._cold_fold(ent, key, days, grid, null_lo, gap_bound)
            else:
                self._advance(ent, key, days, grid, null_lo, gap_bound)
            self._publish(ent, grid, null_lo)
            # 活尾: 折在状态副本上发射(活尾快照每请求整体替换, 非追加不变式, 不入持久态)
            fold = ent.fold.copy()
            if tail_slots:
                fold.fold(
                    [(tuple(tail_slots), True)], grid.first, grid.last, grid.interval, grid.t1, null_lo, gap_bound
                )
            points = self._response_points(ent, fold, grid)
            self._entries[ck] = ent
            self._entries.move_to_end(ck)
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)
            return points

    # ---------- 内部(锁内调用) ----------

    def _cold_fold(self, ent, key: str, days: tuple, grid: "WindowGrid", null_lo: float, gap_bound: float) -> None:
        """冷折叠(首次/失效重建): 全部天文件块全量展开 + 折叠, 天游标随展开推进。"""
        groups = []
        for date_str, parsed in days:
            cur = _V4BucketDayCursor()
            ent.day_cursors[date_str] = cur
            if parsed is None:
                continue
            for blk in parsed.blocks:
                slots, bcur, exhausted = v4_block_slots_from(blk, (0, 0, None, None, None), grid.t1)
                if slots:
                    groups.append((slots, False))
                _day_cursor_after(cur, blk, bcur, exhausted, blk is parsed.blocks[-1])
        _guard_group_order(groups)
        ent.fold.fold(groups, grid.first, grid.last, grid.interval, grid.t1, null_lo, gap_bound)

    def _advance(self, ent, key: str, days: tuple, grid: "WindowGrid", null_lo: float, gap_bound: float) -> None:
        """增量折叠: 窗界再对齐(sanitize) -> 逐天校验游标 -> 只展开游标之后的槽组 -> 折叠。
        游标校验不过(结构性变化, 失效面 b)或游程锚点滑出回看界(sanitize 防御路径)=
        整条目冷重建(就地替换 fold/封口表/游标, 同输入重算恒等)。"""
        groups = []
        reset = ent.fold.sanitize(null_lo)
        seen = set()
        for date_str, parsed in days if not reset else ():
            seen.add(date_str)
            cur = ent.day_cursors.get(date_str)
            if cur is None:
                cur = ent.day_cursors[date_str] = _V4BucketDayCursor()  # 新日期(该天首读)
            if parsed is None:
                if cur.starts or cur.cur_start is not None:
                    reset = True  # 天文件消失(删除/移动) —— 结构性变化
                    break
                continue
            if not _v4_bucket_day_cursor_valid(cur, parsed.blocks):
                reset = True
                break
            blocks = parsed.blocks
            n_done = len(cur.starts)
            if cur.cur_start is not None:
                blk = blocks[n_done]
                slots, bcur, exhausted = v4_block_slots_from(
                    blk, (cur.rec_idx, cur.slots_done, cur.last_ts, cur.run_base, cur.run_spacing), grid.t1
                )
                if slots:
                    groups.append((slots, False))
                _day_cursor_after(cur, blk, bcur, exhausted, blk is blocks[-1])
                next_i = n_done + 1
            else:
                next_i = n_done
            for blk in blocks[next_i:]:
                slots, bcur, exhausted = v4_block_slots_from(blk, (0, 0, None, None, None), grid.t1)
                if slots:
                    groups.append((slots, False))
                _day_cursor_after(cur, blk, bcur, exhausted, blk is blocks[-1])
        if reset:
            # 冷重建: 清游标与折叠态(封口表随折叠态重建 —— 同输入重算恒等)
            ent.fold = _V4SeriesFold()
            ent.day_cursors = {}
            ent.sealed = {}
            ent.sealed_keys = []
            ent.held_face = None
            ent.floor = None
            self._cold_fold(ent, key, days, grid, null_lo, gap_bound)
            return
        for d in [d for d in ent.day_cursors if d not in seen]:
            del ent.day_cursors[d]  # 已滑出读集的天(数据全消费且天文件已封日)游标退役
        _guard_group_order(groups)
        ent.fold.fold(groups, grid.first, grid.last, grid.interval, grid.t1, null_lo, gap_bound)

    def _publish(self, ent, grid: "WindowGrid", null_lo: float) -> None:
        """封口发布: 计算新封口边界 -> [旧界, 新界) 的发射序回放(定影值入表 + held 面
        推进) -> 从折叠态移除已封口项 -> 地平线裁剪(封口表/游程项)。"""
        fold = ent.fold
        new_floor = fold.sealed_floor(grid.first, grid.interval, null_lo)
        old_floor = ent.floor
        if new_floor is not None and (old_floor is None or new_floor > old_floor):
            for p in fold.emit(old_floor, new_floor, ent.held_face, ent.sealed, hi_inclusive=False):
                if p.dl_rate is None and p.up_rate is None and p.dl_total is None and p.up_total is None:
                    ent.held_face = None  # null 点: 不跨断口持有
                    continue
                if not p.is_hold:
                    ent.held_face = (p.dl_rate, p.up_rate)
                # 定影值入表(持有面桶点同样入表 —— 回填桶值已定影, 其速率 = 源桶定影值;
                #  held 面不被持有桶点推进)
                ent.sealed[p.t] = p
                ent.sealed_keys.append(p.t)
            # 从折叠态移除已封口项(标记/回填/累加器 —— 它们已定影进封口值表或 held 面)
            fold.marks = [t for t in fold.marks if t >= new_floor]
            fold.backfills = [bf for bf in fold.backfills if bf[0] >= new_floor]
            i = bisect.bisect_left(fold.cell_keys, new_floor)
            for k in fold.cell_keys[:i]:
                del fold.cells[k]
            del fold.cell_keys[:i]
            ent.floor = new_floor
        # 地平线裁剪: 封口表中已滑出窗口的桶键(grid.first 单调不减 -> 永不回看)退役;
        # 游程项裁到 t0 - interval(其摊配份额折入前缀覆盖毫秒, 算术守恒, 桶在窗下不可见)
        j = bisect.bisect_left(ent.sealed_keys, grid.first)
        if j:
            for k in ent.sealed_keys[:j]:
                del ent.sealed[k]
            del ent.sealed_keys[:j]
        horizon = grid.t0 - grid.interval
        for run in (fold.dl_run, fold.up_run):
            entries = run[2]
            k = 0
            while k < len(entries) and entries[k][0] < horizon:
                k += 1
            if k:
                run[3] += sum(e[1] for e in entries[:k])
                del entries[:k]

    def _response_points(self, ent, fold, grid: "WindowGrid") -> tuple:
        """响应点列 = 封口值表窗内段 + 开放面 [grid.first, grid.last] 发射(held 初值 =
        开放面向前扫描, 兜底封口面末端 held —— 与全量现算的合并序逐位同判)。"""
        i0 = bisect.bisect_left(ent.sealed_keys, grid.first)
        i1 = bisect.bisect_right(ent.sealed_keys, grid.last)
        out = [ent.sealed[k] for k in ent.sealed_keys[i0:i1]]
        held_init = fold.held_at(grid.first, ent.held_face)
        out.extend(fold.emit(grid.first, grid.last, held_init, ent.sealed))
        return tuple(out)


class _V4BucketEntry:
    """桶值缓存条目(系列键 x 窗): 折叠态 + 封口值表 + 天游标 + 配置指纹"""
    __slots__ = (
        "fold",
        "sealed",
        "sealed_keys",
        "held_face",
        "floor",
        "day_cursors",
        "interval",
        "sample_interval",
        "first_date",
    )

    def __init__(self, interval: float, sample_interval: float) -> None:
        self.fold = _V4SeriesFold()
        self.sealed: dict = {}  # 桶键 -> V4PointEntry(定影值, 合并序后真值)
        self.sealed_keys: list = []  # 封口桶键升序(与 sealed 同步, 二分取窗内段)
        self.held_face: Optional[tuple] = None  # 封口面末端的 held 值(null 点清空; 持有面不改)
        self.floor: Optional[float] = None  # 当前封口边界(sealed_floor 最新值)
        self.day_cursors: dict = {}  # date_str -> _V4BucketDayCursor
        self.interval = interval
        self.sample_interval = sample_interval
        self.first_date: Optional[str] = None  # 读集最早日期(链起点锚; 更替 = 冷重建失效面 c2)


def _day_cursor_after(cur: _V4BucketDayCursor, blk, bcur: tuple, exhausted: bool, is_last: bool) -> None:
    """块展开后的天游标推进: 整块展完且非当天末块 -> 并入 starts(块边界); 未展完(窗尾
    截停)或**当天末块**(开放块, 只追加不变式下仍会增长) -> 停驻块游标(下轮从该处续展,
    窗尾外槽与新追加记录重展重判)。last_rec = 末消费记录(校验面)。"""
    rec_idx, slots_done, last_ts, run_base, run_spacing = bcur
    if exhausted and not is_last:
        cur.starts = cur.starts + (blk.start_epoch, )
        cur.cur_start = None
        cur.rec_idx = 0
        cur.slots_done = 0
        cur.last_ts = None
        cur.run_base = None
        cur.run_spacing = None
        cur.last_rec = blk.records[-1] if blk.records else None
        return
    cur.cur_start = blk.start_epoch
    cur.rec_idx = rec_idx
    cur.slots_done = slots_done
    cur.last_ts = last_ts
    cur.run_base = run_base
    cur.run_spacing = run_spacing
    recs = blk.records
    if slots_done > 0:
        cur.last_rec = recs[rec_idx]
    elif rec_idx > 0:
        cur.last_rec = recs[rec_idx - 1]
    else:
        cur.last_rec = None


def _guard_group_order(groups: list) -> None:
    """槽组时序守卫(缓存路径防御面): 槽组按 (日期, 块序) 构造恒时序递增; 首槽倒挂 =
    解析产物结构性异常(分组键序被破坏), fail-fast 拒折(调用方按异常面处置),
    不静默产出负对跨的脏速率。"""
    prev_end = None
    for slots, _is_tail in groups:
        if prev_end is not None and slots[0].ts < prev_end - _V4_VACUUM_EPS_S:
            raise ValueError(f"槽组时序倒挂: 首槽 {slots[0].ts!r} 先于前组末槽 {prev_end!r}")
        prev_end = slots[-1].ts


# ======================================================================
# v4 视图映射(S3b, §05.3; 26-11-15-1104 F2 后 raw 段为直映): 桶点流/agg 行 -> 响应栅格桶观测
#
# 响应数组 = 窗口栅格上的「桶值 | null」定长数组(§08 形状不变); 两类入流在栅格桶
# 观测(BucketObs 表)层面合流, 之后的 rate_points / series_totals_points / group_*
# 与 v2 共用同一差分层:
# - raw 段窗(1m-24h): v4_series_points 桶点流 --v4_grid_obs--> 栅格桶(直映 —— F2 点位
#   归属下桶点键即栅格桶键, 速率/断链判读已在桶层一次算定; 旧覆盖加权摊配桥接退役);
# - agg 段窗(3d/7d/30d hour / 6mo/1y day / all month): agg 行 --v4_agg_obs--> 栅格桶
#   (行 epoch 即桶键, 直映; 3d+ 窗只读成员 agg 文件, 组图 30d 由 M×31 -> M×1 次读取)。
# - agg 段活尾合流(S7, 2026-10-14): 磁盘封口行 + 活尾未封口部分行(开放小时/当日/
#   当月)--v4_agg_obs_live--> 栅格桶(按 epoch 合流, v4_merge_agg 口径)—— agg.dat
#   只有封口行, 不合流则图尾停在最后一个封口桶(3d+ 视图尾真空)。
# ======================================================================


def v4_grid_obs(points: tuple, grid: WindowGrid) -> dict:
    """v4 桶点流 -> 栅格桶观测(S3b §05.1/§05.3; 26-11-15-1104 F2 后 = 直映)

    F2 点位归属归桶下桶点键即栅格桶键(first + i x interval 同式派生), 速率/断链判读
    (broke -> None / 链首 0 线)已在 v4_series_points 桶层一次算定 —— 本函数只做窗内
    过滤 + null 点剔除 + BucketObs 装配, 不再有权重面:
    - 窗外桶点(链上下文: 消费下界回看界内的前驱桶)不消费(对齐 v2 窗外行口径);
    - null 点(断连/真空标记, 率/totals 全空)不参与 —— 栅格桶无观测 = null, 断线语义由
      空桶承载;
    - 旧覆盖加权摊配面(D1 重叠秒展开 / D4 豁免权重 / 快照覆盖末端竞争)随双几何退役:
      快照竞争(ts 最晚者胜)与逐向豁免已上收桶层。
    """
    lo, hi = grid.first, grid.last
    return {
        p.t: BucketObs(p.dl_rate, p.up_rate, p.dl_total, p.up_total)
        for p in points if lo <= p.t <= hi and
        not (p.dl_rate is None and p.up_rate is None and p.dl_total is None and p.up_total is None)
    }


def v4_agg_obs(rows: tuple, grid: WindowGrid) -> dict:
    """agg 行(hour/day/month) -> 栅格桶观测(S3b §05.3 视图映射): 行 epoch 即栅格桶键

    hour 行 epoch 恰为 3600 整倍(与 hour 栅格 floor 对齐同源), day 行 = 本地日界 00:00
    (= build_grid day 段窗桶键), month 行 = 自然月 1 日 00:00(= build_month_grid 桶键)
    —— 直映不聚合(写侧封口已按桶归并); avg/max/totals/cov_s -> 桶值(max/cov_s 不上图,
    保留供对照); 窗外行(不在栅格桶集)不消费; 缺行栅格桶不出现在返回表 = null。
    """
    buckets = set(grid.buckets)
    return {r.epoch: BucketObs(r.dl_avg, r.up_avg, r.dl_total, r.up_total) for r in rows if r.epoch in buckets}


def v4_agg_obs_live(rows: tuple, live_rows: tuple, grid: WindowGrid) -> dict:
    """agg 行 + 活尾未封口部分行 -> 栅格桶观测(S7, 2026-10-14; §05.3 活尾合流的 agg 段形态)

    rows = 磁盘封口行(agg.dat 解析产物, 调用方已按段 kind 过滤); live_rows = 采样模块
    活尾快照的 pending_agg 部分行(同为该段 kind; AggRow 元组)。按 epoch 合流后直映:
    - 磁盘无该 epoch 行(开放桶: 当前小时/当日/当月常态) -> 活尾部分行直映, 图尾不再
      停在最后一个封口桶(用户报「3 天及以上视图有真空」的修复点);
    - 磁盘已有该 epoch 行(已封桶的迟到补记残余, 或 append 与发布同轮的竞态窗) ->
      v4_merge_agg 合流(cov 加权 avg / max 取大 / totals 取后封行 / cov 相加截到桶宽),
      与写侧 _agg_merge_prev 同判据 —— 残余段不双计、不丢;
    - 窗外 epoch(不在栅格桶集)不消费, 对齐 v4_agg_obs; 缺行桶不进返回表 = null。
    live_rows 与 rows 不同 kind 时 v4_merge_agg fail-fast(调用方按段过滤的义务)。
    """
    merged: dict = {}
    for r in rows:
        merged[r.epoch] = r
    for r in live_rows:
        prev = merged.get(r.epoch)
        merged[r.epoch] = v4_merge_agg(prev, r) if prev is not None else r
    buckets = set(grid.buckets)
    return {
        r.epoch: BucketObs(r.dl_avg, r.up_avg, r.dl_total, r.up_total)
        for r in merged.values() if r.epoch in buckets
    }


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
