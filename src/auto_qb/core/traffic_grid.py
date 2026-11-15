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
import math
from dataclasses import dataclass
from typing import Any, Optional

from ..infra import clock
from .traffic_store import (
    HOUR_SECONDS,
    V4ParsedAgg,
    v4_block_slots,
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
    t0: int  # 窗口起点(含), epoch 秒
    t1: int  # 窗口终点(不含), epoch 秒
    interval: float  # 桶宽秒(raw = 采样间隔整倍, 可为 1.5/4.5/22.5/43.5/87/174 等半秒值(26-11-15-1104 F1), 30d = 3600, 6mo/1y = 86400, all = 标称月长; 整值宽归一 int)
    segment: str  # 消费段: "raw" | "hour" | "day" | "month"
    buckets: tuple  # Tuple[int, ...] 桶起点序列(升序)

    @property
    def first(self) -> int:
        return self.buckets[0]

    @property
    def last(self) -> int:
        return self.buckets[-1]


def _floor_buckets(t0: int, t1: int, interval: float) -> tuple:
    """等宽桶序列单点(issue 26-10-11-0207 R07 立, 计划 26-11-14-1313 F3 反转桶数口径):
    起点向下取整对齐(epoch 恒正) + floor+1 桶数 + 生成。build_grid 的 raw 与 hour 两分支
    共用(除桶宽计算外逐字同构); day 分支桶键是本地日界, 不走此处。

    桶数 n = (t1 - first) // interval + 1(恒含进行中桶)—— 反转 26-10-11-0207 R07 的 ceil
    拍板(计划 26-11-14-1313 F3/D3 方波实证): t1 = int(now) 整秒截断 + 首桶 floor 对齐 ->
    t1 - first 一半时间恰落桶边界(整秒 mod 整桶宽), ceil 下 n 在 k/k+1 方波随轮询相位翻转
    (跨度 58s<->60s 实证) -> 前端 rewin(n 变判跨窗换档)瞬时跳窗 + uPlot split 集每拍重推。
    W 恰为 interval 整倍时 n 恒 k+1 与相位无关(生产默认采样面各 raw 窗恒整倍); span 非整倍
    时 n 仍随相位在 k+1/k+2 波动(幅度 1, si=7/3h 窗实测: r=5 时 n=1543 其余 1544)。
    尾桶恒为「进行中桶」(floor(t1/interval) 对齐); 代价: t1 恰落桶边界时尾桶是刚开启的
    空桶(单桶 null, 视觉无感)。"""
    first = t0 - (t0 % interval)  # floor 对齐(epoch 恒正; 半秒宽下 first 为 x.0/x.5 浮点)
    n = int((t1 - first) // interval) + 1  # floor+1: 恒含进行中桶(26-11-14-1313 F3, 反转 R07 ceil; float 宽整值化)
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
        t1 = int(now)
        t0 = t1 - span
        buckets = _floor_buckets(t0, t1, interval)
    elif segment == "day":
        interval = DAY_SECONDS
        t1 = int(now)
        t0 = t1 - span
        buckets = tuple(v4_date_str_epoch(d) for d in sorted(v4_window_dates(t0, t1 - 1)))
    else:  # hour
        interval = HOUR_SECONDS
        t1 = int(now)
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
    """
    first, last, interval = grid.first, grid.last, grid.interval
    t1 = grid.t1
    if gap_bound_s is not None and (
        not isinstance(gap_bound_s, (int, float)) or isinstance(gap_bound_s, bool) or not math.isfinite(gap_bound_s) or
        gap_bound_s <= 0
    ):
        raise ValueError(f"非法 gap_bound_s(须正有限数值): {gap_bound_s!r}")
    gap_bound = float(gap_bound_s) if gap_bound_s is not None else float(interval) * 2.0
    # 消费下界(null 点/差分链同界): 调用面读文件已按 seed_t0 = t0 - interval 外扩一天,
    # 此处再退一个回看界 —— 接缝摊配的变化点跨度锚可远在窗外(P2, 详常量注释)
    null_lo = grid.t0 - interval - _V4_SEAM_LOOKBACK_S
    cells: dict[Any, list] = {}
    # 桶键 -> [dl_delta, dl_cov_ms, up_delta, up_cov_ms, last_ts, snap_dl, snap_up,
    #          broke, is_hold](差分/覆盖逐向独立: 豁免对(delta None)不占速率权重)
    marks: list = []  # null 点 t —— n 游程折叠 + 块间真空(入列时已按 [null_lo, t1) 过滤)
    backfills: list = []  # (空桶键, 源观测桶键) —— 有界空桶持有回填(F2/R8), 发射期装配
    prev_chain_end: Optional[float] = None
    prev_slot: Optional[tuple] = None  # 上一观测槽 (ts, dl_total, up_total) —— 差分链
    last_was_null = False
    marked = False  # 自上一观测槽以来出过 null 点(标记后基线缺失; 摊配判据或支之一)
    # 自上一观测槽以来出现过 null 槽/组界缝(不限窗界 —— 标记入列有 [null_lo, t1) 界,
    # 界外 null/真空不产标记点但仍属断连面): 有界空桶持有回填判据的「活跃链」支之一
    null_since_obs = False
    # 逐向游程状态: [游程值, 锚点 ts, [(桶键, 覆盖毫秒, 是否 z 槽)]]
    dl_run: list = [None, 0.0, []]
    up_run: list = [None, 0.0, []]

    def held_backfill(i_prev: int, i_cur: int, gap: float) -> None:
        """有界空桶持有回填判据单点(F2 后半/R8): 活跃链内空桶(开区间 (i_prev, i_cur))
        且前后观测间隙 <= gap_bound 时按持有语义回填(与 F3 尾桶 holding 同一条规则:
        「最新已知状态仍有效」, 界值同 _tail_gap_bound 单点); 间隙过界(真停滞)与
        marked/null_since_obs(n 游程/块间真空 —— 断连语义, 含窗界外不产标记点的 null/
        真空)不回填保持 null。源桶 = i_prev 桶(发射期
        经 held 面持有其速率, totals 取其末次快照 —— 链 0 增量, 字节守恒由后继样本
        快照差分承载)。判据界下每区间至多 1 枚空桶(前后观测都在各自桶内 -> gap >
        (i_cur - i_prev - 1) x interval, gap <= 2 x interval 推出 i_cur <= i_prev + 2)。"""
        if marked or null_since_obs or gap > gap_bound:
            return
        for j in range(i_prev + 1, i_cur):
            backfills.append((first + j * interval, first + i_prev * interval))

    def bucket_add(key: Any, d: int, share: int) -> None:
        """摊配份额入桶(游程桶在差分链上先于接收槽出现, 桶累加器必已存在)"""
        e = cells[key]
        if d == 0:
            e[0] += share
        else:
            e[2] += share

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
            # 块间真空: 本组首槽声称覆盖(dt_s)接不住上组游标终值 -> 差值段出 null 点
            # (磁盘块与活尾同判 —— 活尾首槽抵达不了链末槽 = 中间有未观测段(重启缝),
            #  同块续链的槽 dt 链天然接住链末槽, 不出标记; issue 26-10-16-0954 修复轮)
            if slots[0].ts - slots[0].dt_s > prev_chain_end + _V4_VACUUM_EPS_S:
                null_since_obs = True  # 组界缝(窗界外不产标记点但仍属断连面, 回填判据用)
                t = int(prev_chain_end)
                if null_lo <= t < t1:
                    marks.append(t)
                    marked = True
        for s in slots:
            if s.obs is None:
                # n 槽: 连续 null 槽折叠为一个 null 点(首槽位置取整; 断连语义)
                null_since_obs = True  # 窗界外 null 不产标记点但仍属断连面(回填判据用)
                t = int(math.floor(s.ts))
                if null_lo <= t < t1 and not last_was_null:
                    marks.append(t)
                    marked = True
                last_was_null = True
                continue
            last_was_null = False
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
                else:
                    e[8] = e[8] and s.is_hold  # 任一非持有槽在桶 -> 非 holding 桶
                    if s.ts >= e[4]:
                        e[4] = s.ts
                        e[5] = o[2]
                        e[6] = o[3]
                prev_chain_end = s.ts
                marked = False
                null_since_obs = False
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
            else:
                e[7] = e[7] or broke  # 断链旗跨同桶后继槽存活(不清成 0 线)
                e[8] = e[8] and s.is_hold
            if s.ts >= e[4]:  # 快照取 ts 最晚者(同刻后到者优先)
                e[4] = s.ts
                e[5] = o[2]
                e[6] = o[3]
            is_z = s.is_zero
            for d, cur, run in ((0, o[2], dl_run), (1, o[3], up_run)):
                # 差分对逐向处理(端点归属: delta 记 cur 所在格); 等值游程入列需 z 形签名
                value, _, run_list = run
                if value is None or hole or cur < value:
                    run[0], run[1], run[2] = cur, s.ts, []
                    delta = None
                elif cur == value:
                    run_list.append((key, cov_ms_pair, is_z))
                    delta = 0
                else:
                    step = cur - value
                    span_ms = int(round((s.ts - run[1]) * 1000))
                    cov_ms = sum(dd for _, dd, _ in run_list) + cov_ms_pair
                    if (
                        cov_ms > 0 and dur_ms > 0 and (
                            marked or span_ms > cov_ms or
                            span_ms > max(2 * int(round(s.dt_s * 1000)), _V4_SEAM_SPREAD_MIN_S * 1000)
                        ) and all(z for _, _, z in run_list)
                    ):
                        # 接缝摊配(P2 承袭): 未覆盖秒不归因 -> 基准先按覆盖份额缩放
                        # (span <= cov 时逐字 == step); 份额按累计比例取整, 余额归接收桶
                        step_w = step if span_ms <= cov_ms else step * cov_ms // span_ms
                        acc = 0
                        cum = 0
                        for k, dd, _ in run_list:
                            cum += dd
                            target = step_w * cum // cov_ms
                            share = target - acc
                            acc = target
                            if share:
                                bucket_add(k, d, share)
                        delta = step_w - acc
                    else:
                        delta = None if marked else step
                    run[0], run[1], run[2] = cur, s.ts, []
                if delta is not None and cov_ms_pair > 0:
                    # 速率面入账(端点归属): 覆盖时长为 0(同刻病理槽序)不归因不造分母
                    if d == 0:
                        e[0] += delta
                        e[1] += cov_ms_pair
                    else:
                        e[2] += delta
                        e[3] += cov_ms_pair
            prev_slot = (s.ts, o[2], o[3])
            marked = False
            null_since_obs = False
        prev_chain_end = slots[-1].ts  # 游标终值 = 末槽实测时刻(真空判定基准)
    entries = []
    for key in sorted(cells):
        e = cells[key]
        dl_cov, up_cov = e[1], e[3]
        if e[8]:  # holding 桶(F4/F3): 速率面在下方合并序里持有上一观测桶
            dl = up = None  # 占位, 发射期回填
        else:
            dl = int(round(e[0] * 1000 / dl_cov)) if dl_cov > 0 else (None if e[7] else 0)
            up = int(round(e[2] * 1000 / up_cov)) if up_cov > 0 else (None if e[7] else 0)
        entries.append((key, 1, V4PointEntry(key, dl, up, e[5], e[6], w=max(dl_cov, up_cov) / 1000, is_hold=e[8])))
    for bf_key, src_key in backfills:
        # 有界空桶持有回填装配(F2/R8): is_hold 旗入下方合并序的 held 面 —— 速率 = 源桶
        # 速率(走槽期已终值, 封口桶不可变不受影响), totals = 源桶末次快照(链 0 增量,
        # 字节守恒: 漏采区间字节含在后继样本快照差分里); w = 0(无观测覆盖, 持有面)
        src = cells[src_key]
        entries.append((bf_key, 1, V4PointEntry(bf_key, None, None, src[5], src[6], w=0.0, is_hold=True)))
    for t in marks:
        entries.append((t, 0, V4PointEntry(t)))
    # null 点排同刻观测点之前(null 在先 = 该时刻断线、其后才是观测覆盖; 稳定保插入序)
    entries.sort(key=lambda x: (x[0], x[1]))
    out = []
    held: Optional[tuple] = None  # 上一非持有观测桶的速率(holding 持有面; null 点清空)
    for _, _, p in entries:
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
    return tuple(out)


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
