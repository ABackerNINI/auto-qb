"""traffic_grid: qB 口径流量图读侧窗口/栅格离散与组聚合纯函数(plan 26-10-03-0946 方案C P4,
§05.1/§04.1; v3 读侧 plan 26-10-04-1957 S3a/S3b; 26-11-18-0037 阶段 1 raw 段窗换样本分组契约)

S4 API 读侧的取数口径, 全部纯函数(输入 v4 天文件块序列 / agg 行 / 栅格桶表, 输出响应段),
不触文件不触时钟 —— Web 线程直接调用, 单测可独立构造输入。v2 逐行格式读侧 / 26-11-15-1104
挂钟桶面(F1 桶宽加宽 / F2 点位归属归桶 / F3 持有 / F4-2 桶值缓存)已随 26-11-18-0037 D2
样本分组契约退役删除(raw 段窗响应 = core.traffic_group_assembly 样本分组点列 + 
core.traffic_group_cache 分组点列缓存, 两者的判读单点 —— 差分/_seam_spread_delta 摊配/
null 标记/天游标 —— 仍由本模块承载); 本模块现行面:

窗口与栅格(§05.1/§05.3, WINDOW_SPECS 13 档):
- raw 段窗(1m-24h): 挂钟桶面退役后栅格只剩**窗界载体**(t0/t1 浮点挂钟, buckets 恒空)——
  数据经 traffic_store.V4DayCache 按天加载 -> 块序列 -> 样本分组装配(traffic_group_assembly,
  消费下界 group_null_lo = t0 - si - 回看界, 窗首种子 D3 与接缝锚回看给足); 另合流采样
  模块活尾快照(S6: 未落盘记录 + 开放游程续链, 图面尾部随采样节拍实时, 不等 flush)。
- hour 段窗(3d/7d/30d): 桶宽恒 3600s, 消费 agg hour 行; day 段窗(6mo/1y): 滚动窗涉及
  本地日期逐日铺格(桶键 = 本地日界 00:00), 消费 agg day 行; month 段窗(all): 数据面定栅格
  (build_month_grid, 首末月行之间逐月铺格), 消费 agg month 行。agg 行 epoch 即栅格桶键
  (v4_agg_obs 直映, 桶内不再聚合)。桶面仅 agg 段窗继续消费(D4: agg 段窗零改动)。

槽位数学与判读单点(样本分组装配的共用底层, 详 traffic_group_assembly):
- 差分链: 相邻样本累计快照差分 _bucket_delta —— cur < last 判计数器重置 -> null(dl/up
  两向独立判定, 对齐采样器 _delta 逐向口径); 基线缺失 -> None。
- 接缝摊配(plan 26-10-15-0829 P2; 重启缝形态 issue 26-10-16-0954 修复轮补入; 
  _seam_spread_delta 提取件, 桶面时代与分组装配共用同一实现): 长 z 形等值游程(写侧快照
  冻结)末端的台阶按真实发生跨度摊配; 观测缝 > _V4_SEAM_NULL_S = 停机洞, 断链丢弃
  (诚实性); <= 本值的重启缝按真实跨度回收。
- null 标记: n 游程(断连)/ 块间真空(重启缝)出显式空值点(来源语义不同, 承袭分离)。

totals 段(§05.1, agg 段窗响应通道):
- 相邻桶累计快照差分: delta = cur - last; cur < last 判计数器重置 -> 该桶增量 null
  (dl/up 两向独立判定); 前桶无快照(窗首/空桶断链)= 基线缺失 -> null。

组读侧聚合(§04.1 -> §05.4, agg 段窗; raw 段窗组 Σ = traffic_qb._group_merge_points 现算):
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
    V4NullRun,
    V4ParsedAgg,
    V4ZeroRun,
    v4_block_slots,
    v4_date_str_epoch,
    v4_merge_agg,
    v4_next_month_epoch,
    v4_window_dates,
)

#: 窗口名 -> (跨度秒, 消费段): 1m-24h 消费 raw 天文件(样本分组装配), 3d/7d/30d 消费
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


@dataclass(frozen=True)
class WindowGrid:
    """一次取数的时间栅格(§05.1)

    agg 段窗: buckets = [t0, t1) 按 interval 离散出的固定桶序, 长度 = (t1 - first) //
    interval + 1(恒含进行中桶; 计划 26-11-14-1313 F3 反转 26-10-11-0207 R07 的 ceil
    口径 —— 反转理由见 _floor_buckets; 窗首桶对齐 floor(t0/interval)); 桶值 t = 桶起点
    epoch 秒。day 段窗(6mo/1y)例外: 桶键 = 本地日界 00:00(滚动窗 [t0, t1) 涉及的本地
    日期逐日铺格, 窗首桶允许早于 t0 —— 首日不满宽); month 段窗(all)由 build_month_grid
    数据面铺格。
    raw 段窗(1m-24h, 26-11-18-0037 T1c-2): 挂钟桶面已随样本分组契约退役, 栅格只剩
    **窗界载体** —— t0/t1(浮点挂钟)与 segment 供限速事件取数界/装配窗/空态 meta 消费,
    buckets 恒空、interval = 生效采样间隔(标称组距基元, 无桶面语义)。raw 栅格调
    first/last 是编程错误(IndexError 防御面 —— 桶面消费者仅 agg 段窗)。
    """

    name: str  # WINDOW_SPECS 键(1m-all)
    t0: float  # 窗口起点(含), epoch 秒(与浮点挂钟同源, 不再整秒截断)
    t1: float  # 窗口终点(不含), epoch 秒(同上; 整点输入时数值仍为整数)
    interval: float  # 桶宽秒(hour = 3600, day = 86400, all = 标称月长; raw = 生效采样间隔, 仅标称组距基元无桶面 —— 见类注); 整值宽归一 int
    segment: str  # 消费段: "raw" | "hour" | "day" | "month"
    buckets: tuple  # 桶起点序列(升序; raw 段窗恒空 —— 桶面退役, 见类注)

    @property
    def first(self) -> int:
        return self.buckets[0]

    @property
    def last(self) -> int:
        return self.buckets[-1]


def _floor_anchor(t: float, interval: float) -> float:
    """浮点时刻向下对齐到 interval 网格(issue 26-11-17-0936 治本单点): math.floor(t/interval)
    起步后双向校正到「first <= t < first+interval」, 桶键恒以 first + i×interval 同式派生
    (非整倍宽下不差 1 ulp)。直接对浮点 now 对齐, 不再经 int(now) 整秒截断 —— 后者与
    1.5s 轮询/桶宽 floor 对齐混叠出 +3.0/0.0 二拍抖动。"""
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
    起点向下取整对齐 + floor+1 桶数 + 生成。build_grid 的 hour 分支与测试直构栅格共用;
    day 分支桶键是本地日界, raw 分支桶面退役(26-11-18-0037 T1c-2), 均不走此处。

    桶数 n = floor((t1-first)/interval)+1(恒含进行中桶)—— 反转 R07 ceil 方波的历史判据仍
    成立; 输入 t0/t1 现为浮点挂钟(26-11-17-0936 治本): first 按 _floor_anchor 对同一
    interval 网格对齐并双向校正,n 由浮点跨度现算再双向校正到 last <= t1 < next。
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

    raw 段窗(1m-24h, 26-11-18-0037 T1c-2): 挂钟桶面随样本分组契约退役, 本函数对 raw 段
    只产**窗界载体** —— t1 = 浮点挂钟原值(issue 26-11-17-0936: 窗尾锚末样本, 不整秒截断;
    响应窗右沿 = 末样本语义的窗界来源), t0 = t1 - span, buckets 恒空(详 WindowGrid 类注);
    si 保留 fail-fast 校验(黄金法则 4: 来源链 = 纯 config 派生(multiplier >= 1 x
    main_tick >= 0.5, validate_config 全量校验面聚合报错), 非正值绝不静默落 DEFAULT 掩盖
    装配缺陷 —— 下游 group_null_lo/分组口径 k 全依赖 si)。
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
        si = float(sample_interval)
        if not si > 0:
            raise ValueError(f"sample_interval 须 > 0(生效采样间隔 = multiplier x main_tick, 校验面保证正值): {si!r}")
        t1 = float(now)  # 浮点挂钟直传(窗尾锚末样本; 整点输入语义不变)
        t0 = t1 - span
        buckets: tuple = ()  # 桶面退役(raw 响应 = 样本分组点列, 无挂钟桶)
        return WindowGrid(window, t0, t1, si, segment, buckets)
    if segment == "day":
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
    v4_totals_points 已随 cell 几何退役 —— 差分/摊配口径单点在样本分组装配槽层
    (traffic_group_assembly, 26-11-18-0037 起)一次算定, 本函数只承载**agg 段窗响应
    totals 通道**(相邻栅格桶快照差分, 输入 obs 桶表); 改差分口径改装配面, 改快照差分
    展示口径改本函数, 两面不再互为平移。
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
# v4 槽位数学与判读单点(plan 26-10-04-1957 S3a 立; 26-11-18-0037 阶段 1 T1c-2 收编)
#
# 26-11-15-1104 挂钟桶面(F2 点位归属归桶 / F3 持有 / F4-2 桶值缓存 V4SeriesBucketCache /
# T2/T3 封口定影 / R8 有界空桶持有回填)已随 26-11-18-0037 D2 样本分组契约退役: raw 段窗
# 读侧 = traffic_group_assembly.assemble_group_points(样本分组点列)+
# traffic_group_cache.V4SeriesGroupCache(分组点列缓存)。本区只保留**判读单点**(新装配与
# 分组缓存共用的底层, 口径不得分叉):
# - v4_series_slots: 记录时间轴平展(块按 start_epoch 稳定排序逐块 v4_block_slots 展开);
# - _seam_spread_delta: 接缝摊配判定与份额分配(P2 原样提取件, 存量接缝电池钉住);
# - _bucket_delta: 累计快照差分(重置/基线缺失三层口径);
# - _V4_VACUUM_EPS_S / _V4_SEAM_* 常量: 真空容差/摊配下限/停机洞阈值/回看界。
# - 天游标三件(_V4BucketDayCursor / _v4_bucket_day_cursor_valid / _day_cursor_after):
#   F4-2 的「消费集 = 槽流前缀、只展新增槽」游标模式原样承袭进分组点列缓存。
# 摊配/差分/null 标记的判读全景(端点归属/未覆盖秒不归因/z 形签名/停机洞断链/份额守恒)
# 见 _seam_spread_delta 与 traffic_group_assembly 模块 docstring —— 语义承袭旧桶面单点,
# 面形态从栅格桶点换成样本分组点列。
# ======================================================================

#: 真空判定浮点容差(秒): 块间 gap 与链端覆盖的比较 ε(旧桶面/新装配与分组缓存共用)
_V4_VACUUM_EPS_S = 1e-6

#: 接缝摊配触发下限(秒, plan 26-10-15-0829 P2): 快照台阶的变化点跨度超过
#: max(2 x 接收槽 dt, 本值) 才按真实跨度摊配 —— 2x 槽 dt 即「明显大于单步覆盖」, 本值兜底
#: 防高频采样把普通抖动摊平(计划 §06 R2)。模块常量非配置键(P2 拍板默认: 不新增配置键)。
_V4_SEAM_SPREAD_MIN_S = 60

#: 观测缝停机洞阈值(秒, plan 26-10-15-0829 P2 诚实兜底): 相邻两观测槽的覆盖缝超过
#: 本值 = 停机洞 -> 差分断链(delta=None, 宁可丢弃不摊配 —— G2/E2E3 诚实性); <= 本值 =
#: 重启缝 -> 接缝差按真实跨度摊配回收(P0 实施记录 2, G3/E2E4 受益)。
#: !语义锚定(plan §03 P0 实施记录 REC): 摊配分母 = 变化点跨度(可长达整个 z 游程,
#: 本事故 6.6h), 洞判定分母 = 观测覆盖缝(重启 ~10s)—— 两量分离; 「超 SEAM_NULL_S
#: 标 null」约束的是后者, 若约束前者则长游程陈旧差永不可摊, 与「两缝一并治理」矛盾。
_V4_SEAM_NULL_S = 60

#: 差分链消费下界回看界(秒, plan 26-10-15-0829 P2 实施期扩展落点; 26-11-18-0037 阶段 1
#: 消费下界单点 = traffic_group_assembly.group_null_lo(t0, si) = t0 - si - 本值, 与旧
#: _v4_null_lo 同式): 接缝摊配的变化点跨度锚(冻结值建立点)可能远在窗外(本事故 6.6h),
#: 窗界截断会把摊配分母压回窗内残余跨度, 窄窗重新放大 ~15x(G1「三窗峰值同量级」被破)。
#: 界取写侧游程强制封口上限 ZRUN_FLUSH_S 同值(traffic_sample_mod, 86400s): 陈旧跨度
#: 物理上不可能超过它; 超界槽点只可能是前缀(块按天切, 过滤单调), 差分链在保留首点重锚,
#: 无中断风险。D3 窗首种子语义(窗外前缀只作差分基线)由该消费下界自然包含。
#: !取代 issue 26-10-08-0141 的 _V4_NULL_FLOOR_S=1 秒标记带: 标记与槽同界后, 原 1 秒带
#: 整段被包含 —— 标记窄于槽界会在窗外重建该 issue 的断链失效假尖峰。
_V4_SEAM_LOOKBACK_S = 86_400


def v4_series_slots(blocks: tuple) -> tuple:
    """块序列 -> 扁平槽序(记录时间轴层; S3b agg 段合流的接缝): 块按 start_epoch 升序
    (稳定排序, 同刻保文件序), 逐块 v4_block_slots 展开(复用 S1 游标 dt 链, 不另写推算)。"""
    out: list[Any] = []
    for blk in sorted(blocks, key=lambda b: b.start_epoch):
        out.extend(v4_block_slots(blk))
    return tuple(out)


def _seam_spread_delta(
    d: int,
    step: int,
    span_ms: int,
    cov_ms: int,
    dur_ms: int,
    dt_s: float,
    marked: bool,
    run_list: list,
    run_prefix: int,
    bucket_add,
) -> Optional[int]:
    """接缝摊配判定与份额分配单点(P2 原样提取, 26-11-18-0037 阶段 1): 原挂钟桶面
    _V4SeriesFold.fold 内嵌摊配块逐字平移提取(该 fold 已随桶面退役), 旧电池钉住零改动
    —— 新样本分组装配(traffic_group_assembly)与分组点列缓存共用同一实现, 摊配口径不得
    分叉。

    d = 方向(0=dl / 1=up); step = 本槽台阶差分(bytes); span_ms = 变化点跨度(游程锚到
    本槽); cov_ms = 覆盖毫秒合计(含 run_prefix 与本对); dur_ms = 本槽差分对跨;
    dt_s = 本槽声称覆盖; marked = 断连标记存活; run_list = 等值游程项 (键, 覆盖毫秒,
    是否 z 槽, 槽 ts) —— 键语义由调用方定(旧桶面 = 桶键, 样本分组 = 组标识);
    run_prefix = 已裁剪游程项覆盖毫秒合计(全量路径恒 0); bucket_add(键, 向, 份额) =
    份额入桶回调。返回本槽差分(None = 断链/不摊配)。
    """
    if (
        cov_ms > 0 and dur_ms > 0 and
        (marked or span_ms > cov_ms or span_ms > max(2 * int(round(dt_s * 1000)), _V4_SEAM_SPREAD_MIN_S * 1000)) and
        all(z for _, _, z, _ in run_list)
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
        return step_w - acc
    return None if marked else step


class _V4BucketDayCursor:
    """分组点列缓存的单天消费游标(F4-2 游标模式原样承袭, 消费者 =
    traffic_group_cache.V4SeriesGroupCache): 天文件按「只追加」不变式(R3)增长, 游标 =
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
    """天游标与当前解析产物的结构一致性校验(失效面 b, F4-2 判据承袭): 起点前缀逐一对上 + 停驻块
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


# ======================================================================
# v4 视图映射(S3b, §05.3; 26-11-18-0037 T1c-2 后 = agg 段窗专用): agg 行 -> 响应栅格桶观测
#
# 响应数组 = 窗口栅格上的「桶值 | null」定长数组(§08 形状不变, agg 段窗); 入流在栅格桶
# 观测(BucketObs 表)层面合流, 之后的 rate_points / series_totals_points / group_*
# 与 v2 共用同一差分层:
# - agg 段窗(3d/7d/30d hour / 6mo/1y day / all month): agg 行 --v4_agg_obs--> 栅格桶
#   (行 epoch 即桶键, 直映; 3d+ 窗只读成员 agg 文件, 组图 30d 由 M×31 -> M×1 次读取)。
#   raw 段窗(1m-24h)不走本面 —— 响应 = 样本分组点列(traffic_group_assembly), 旧
#   v4_series_points 桶点流 --v4_grid_obs--> 栅格桶 直映面已随挂钟桶面退役。
# - agg 段活尾合流(S7, 2026-10-14): 磁盘封口行 + 活尾未封口部分行(开放小时/当日/
#   当月)--v4_agg_obs_live--> 栅格桶(按 epoch 合流, v4_merge_agg 口径)—— agg.dat
#   只有封口行, 不合流则图尾停在最后一个封口桶(3d+ 视图尾真空)。
# ======================================================================


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
