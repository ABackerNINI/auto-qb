"""HR 站点现状的**纯数据**快照(v3 波次视图, 计划 26-09-28-1932 §8 M5)。

为什么单独一层: 「某个站点现在到底是什么状态」有三个消费者 ——
1. `--hr-status` 报告(给人核数据用, 终端文本);
2. WebUI(设置页「HR 在线核实」章节, 只在需要时拉一次);
3. 日后的 notify / 运维脚本。
它们必须看到**同一套数值口径**(尤其是「各档到哪了」「还能取几次」「为什么没放行」这类派生量)
—— 各写一遍就会出现「报告说 A 档截断、界面说正常」这种没法排查的偏差, 故收口到 `site_status()`。

本模块**只读**: 不取数、不加锁、不写盘(读的是原子替换后的完整快照, 与 `--hr-status` 同款口径),
取数节奏由取数线程决定, 展示层永远只是"看一眼"。

时间相关字段的语义(易混, 明写):
- `fetched_at`: 上次**尝试**取波的刻(失败也会前进 —— 它回答"上次动过是什么时候");
- `wave.healthy_ts`: 上次**健康波**时刻(至少一档有有效数据) —— 它才是新鲜度基准;
- `expires_at`: 复用窗截止(别的实例刚抓过就不再抓);
- `next_wave_at`: 下次**可能**取的时刻(现算: fetched_at + refresh_interval) —— 站点文件里不存它,
  因为它随周期配置变化, 存下来就会重复一份可能过期的副本。
"""
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .model import (
    CHANNEL_DISABLED,
    CHANNEL_OK,
    CHANNEL_SILENT,
    FETCH_LANES,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    HrSiteData,
)
from .ratelimit import day_key, next_allowed_at, next_day_reset, quota_left
from .resolve import HrSiteView

#: 通道状态的人话(与 `--hr-status` 逐字一致 —— 两处口径必须相同)
CHANNEL_TEXTS = {
    CHANNEL_OK: "正常",
    CHANNEL_SILENT: "静默(长期没有健康波)",
    CHANNEL_DISABLED: "未启用",
}

#: 档位人话(明细表等展示共用; 键 = 站点 scope 字母)
LANE_TEXTS = {
    "A": "考察中",
    "B": "已达标",
    "C": "未达标",
    "D": "已免罪",
}

LANE_STATUS_TEXTS = {
    LANE_OK: "有效",
    LANE_FAILED: "失效",
    LANE_IDLE: "-",
}


@dataclass(slots=True)
class LaneStatus:
    """单档位波次状态(展示层; 与 model.HrLaneState 一一对应的人话折算)"""

    lane: str = ""
    status: str = ""
    status_text: str = ""
    wave_ts: float = 0.0
    pages: int = 0
    rows: int = 0
    cutoff_done: float = 0.0
    full_depth: bool = False
    fail_streak: int = 0
    detail: str = ""
    text: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(slots=True)
class QuotaStatus:
    """频控账本状态(单模型: 日额 + 间隔)"""

    day: int = 0
    day_max: int = 0
    left: int = 0
    last_fetch_ts: float = 0.0
    min_interval: float = 0.0
    next_reset: float = 0.0
    text: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(slots=True)
class SiteStatus:
    """单站点 HR 现状(全部字段都由 `site_status()` 算好; 前端只展示, 不重算)"""

    site: str
    enabled: bool = False
    listing: str = "list"
    #: 生成本快照的时刻 —— 所有相对时间(「N 前」)的**唯一基准**, 界面拿它算「多久前拉的」
    now: float = 0.0
    channel_state: str = CHANNEL_DISABLED
    channel_text: str = ""
    revision: int = 0
    file_path: str = ""
    read_error: str = ""
    #: 上次**尝试**取波 / 上次**健康波** / 复用窗截止 / 下次可能取波(现算)
    fetched_at: float = 0.0
    healthy_ts: float = 0.0
    expires_at: float = 0.0
    next_wave_at: float = 0.0
    refresh_interval: float = 0.0
    stale: bool = False
    fresh_text: str = ""
    #: 波次视图(各档独立状态: 有效/失效/截断、页数、行数、覆盖边界、连续失效)
    lanes: List[LaneStatus] = field(default_factory=list)
    lanes_text: str = ""
    releases_enabled: bool = False
    zero_rows: bool = False
    empty_confirmed: bool = False
    retention_text: str = ""
    plunge_text: str = ""
    notes: str = ""
    writer_instance: str = ""
    writer_heartbeat: float = 0.0
    index_total: int = 0
    index_active: int = 0
    lane_counts: Dict[str, int] = field(default_factory=dict)
    #: 待回填 infohash 条数 + 回填进度(活跃条目里已有 infohash 的比例) —— 取数通道刚接通时它是唯一的进度信号
    pending_infohash: int = 0
    backfill_ratio: float = 0.0
    managed: int = 0
    keys: int = 0
    downloaded: int = 0
    fails: int = 0
    verified: int = 0
    observing: int = 0
    quota: QuotaStatus = field(default_factory=QuotaStatus)
    allow_window: str = ""
    #: 一句话说明「为什么现在不签发新放行」(判定链顺序, 取第一个挡路的原因)
    blocking: str = ""

    def to_dict(self) -> Dict:
        """JSON 友好(WebUI 用): 时间戳保留原始值, 人话文案另给字段"""
        return asdict(self)


def duration_text(seconds: float) -> str:
    """人话时长(1d2h / 3h4m / 5m6s / 7s) —— 报告与界面共用一处口径"""
    seconds = int(max(0, seconds))
    if seconds >= 86400:
        return f"{seconds // 86400}d{seconds % 86400 // 3600}h"
    if seconds >= 3600:
        return f"{seconds // 3600}h{seconds % 3600 // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m{seconds % 60}s"
    return f"{seconds}s"


def ago_text(ts: float, now: float) -> str:
    """相对时间(绝对时间戳要心算, 只有排障才想看绝对值)"""
    if not ts or ts <= 0:
        return "从未"
    return duration_text(now - ts) + "前"


def stamp_text(ts: float) -> str:
    """绝对时刻(报告用; 0 = 未设置)"""
    return time.strftime("%m-%d %H:%M:%S", time.localtime(ts)) if ts and ts > 0 else "-"


def lane_counts(data: HrSiteData) -> Dict[str, int]:
    """四档位计数(含免罪档)"""
    counts: Dict[str, int] = {}
    for entry in data.index.values():
        counts[entry.lane] = counts.get(entry.lane, 0) + 1
    return counts


def _lane_statuses(data: HrSiteData, now: float) -> Tuple[List[LaneStatus], str]:
    """各档波次状态折算(展示单点)"""
    out: List[LaneStatus] = []
    parts: List[str] = []
    for lane in FETCH_LANES:
        st = data.wave.lanes.get(lane)
        if st is None:
            parts.append(f"{lane}:无")
            continue
        ls = LaneStatus(
            lane=lane,
            status=st.status,
            status_text=LANE_STATUS_TEXTS.get(st.status, st.status),
            wave_ts=st.wave_ts,
            pages=st.pages,
            rows=st.rows,
            cutoff_done=st.cutoff_done,
            full_depth=st.full_depth,
            fail_streak=st.fail_streak,
            detail=st.detail,
        )
        ls.text = (
            f"{LANE_TEXTS.get(lane, lane)} {ls.status_text}: {ls.pages} 页 / {ls.rows} 行" +
            ("(全深度)" if ls.full_depth else "") + (f", {ls.detail}" if ls.detail else "") +
            (f", 连续失效 {ls.fail_streak} 波" if ls.fail_streak > 1 else "")
        )
        out.append(ls)
        parts.append(
            f"{lane}:{'✓' if st.status == LANE_OK else ('✗' if st.status == LANE_FAILED else '-')}"
            f"{st.pages}页{st.rows}行" + ("(全)" if st.full_depth else "")
        )
    return out, " ".join(parts)


def _retention_text(data: HrSiteData) -> str:
    """A 档流转守恒观测(§5.3)"""
    meta = data.wave
    if meta.retention_ratio < 0:
        return "不适用(上波无 A 档行)"
    tail = "正常" if meta.retention_ok else "⚠ 不达标(批量未列出签发已冻结)"
    return f"上波 A 档 {len(meta.prev_a_tids)} 行, 本波留存率 {meta.retention_ratio:.0%}, {tail}"


def _plunge_text(data: HrSiteData) -> str:
    """总行数骤降观测(§5.3)"""
    meta = data.wave
    if not meta.baseline_rows:
        return "尚无基线(首波)"
    total = sum(st.rows for st in meta.lanes.values() if st.status == LANE_OK)
    if meta.plunge:
        return f"⚠ 本波合计 {total} vs 基线 {meta.baseline_rows} ⇒ 骤降可疑(批量未列出签发已冻结)"
    return f"本波合计 {total} vs 基线 {meta.baseline_rows}, 正常"


def site_status(site: str, data: HrSiteData, view: HrSiteView, service, now: float, read_error: str = "") -> SiteStatus:
    """把「站点文件 + 视图」折成一份只读快照(数值口径的单点)"""
    conf = service.site_confs[site]
    limits = service.limits_for(site)
    active = [e for e in data.index.values() if e.active]
    pending = sum(1 for e in active if not e.infohash_v1 and not e.infohash_v2)
    filled = len(active) - pending
    backfill = (filled / len(active)) if active else 0.0
    stale = bool(data.expires_at) and now > data.expires_at
    lanes, lanes_text = _lane_statuses(data, now)
    observing = sum(1 for e in active if e.lane == "A" and e.missing_streak > 0)
    dk = day_key(now)
    quota = QuotaStatus(
        day=data.rate.day_count if data.rate.day_window == dk else 0,
        day_max=limits.max_requests_per_day,
        left=quota_left(data, limits, now),
        last_fetch_ts=data.rate.last_fetch_ts,
        min_interval=limits.min_interval,
        next_reset=next_day_reset(now),
    )
    quota.text = (
        f"今天 {quota.day}/{quota.day_max}(零点重置) · 还能取 {quota.left} 次 · "
        f"最近请求 {ago_text(quota.last_fetch_ts, now)} · 最小间隔 {quota.min_interval:g}s"
    )
    next_at = data.fetched_at + site_conf_interval(conf) if data.fetched_at else 0.0
    fresh = f"上次取波 {ago_text(data.fetched_at, now)} · 最近健康波 {ago_text(data.wave.healthy_ts, now)}"
    if data.expires_at:
        fresh += f" · 复用窗至 {stamp_text(data.expires_at)}" + ("(已过)" if stale else "")
    return SiteStatus(
        site=site,
        enabled=conf.enabled,
        listing=conf.listing,
        now=now,
        channel_state=view.channel_state,
        channel_text=CHANNEL_TEXTS.get(view.channel_state, "未启用"),
        revision=data.revision,
        file_path=service.site_path(site),
        read_error=read_error,
        fetched_at=data.fetched_at,
        healthy_ts=data.wave.healthy_ts,
        expires_at=data.expires_at,
        next_wave_at=next_at,
        refresh_interval=site_conf_interval(conf),
        stale=stale,
        fresh_text=fresh,
        lanes=lanes,
        lanes_text=lanes_text,
        releases_enabled=data.wave.releases_enabled,
        zero_rows=data.wave.zero_rows,
        empty_confirmed=data.empty_confirmed_at > 0,
        retention_text=_retention_text(data),
        plunge_text=_plunge_text(data),
        notes=data.wave.notes,
        writer_instance=data.writer_instance,
        writer_heartbeat=data.writer_heartbeat,
        index_total=len(data.index),
        index_active=len(active),
        lane_counts=lane_counts(data),
        pending_infohash=pending,
        backfill_ratio=backfill,
        managed=len({e.tid
                     for e in view.lane_a.values()}),
        keys=len(view.lane_a) + len(view.lane_terminal),
        downloaded=len(data.downloaded),
        fails=len(data.fails),
        verified=len(data.verified),
        observing=observing,
        quota=quota,
        allow_window=limits.allow_window or "",
        blocking=blocking_reason(view, data, stale, site),
    )


def site_conf_interval(conf) -> float:
    """站点对账波周期(秒); 单独提出来是为了让「下次取波」这类字段的算法只有一处"""
    return float(getattr(conf, "refresh_interval", 0.0) or 0.0)


def blocking_reason(view: HrSiteView, data: HrSiteData, stale: bool, site: str = "") -> str:
    """一句话说明「为什么现在不签发新放行」(按判定链的顺序, 取第一个挡路的原因)

    用户看到「种子没被放行」时最想知道的就是它卡在哪一步, 而这一步光看数据看不出来。
    """
    if not view.lane_a and not view.lane_terminal and not view.verified:
        return "索引里还没有任何可判数据(先让浏览器扩展跑一轮取数)"
    if data.wave.zero_rows and not data.empty_confirmed_at:
        return "结构完好但清单为 0: 不签发放行 —— 需 --hr-confirm-empty 人工对账一次"
    if not data.wave.releases_enabled:
        return "本波未全部档位有效(截断/失效): 命中照常, 批量「未列出」待下波续判"
    if stale:
        return "复用窗已过(等待下一波)"
    return ""


def build_site_statuses(service, now: float, sites: Optional[Sequence[str]] = None) -> List[SiteStatus]:
    """逐站点读站点文件并折成快照(不加锁、不取数、不写盘 —— 与 `--hr-status` 同款只读口径)

    站点文件读坏时**不抛**: 如实把 `read_error` 带出去(读坏本身就是要人看的信息, 报告与界面
    都该显示它, 而不是整个视图消失)。
    """
    out: List[SiteStatus] = []
    names = list(sites if sites is not None else service.enabled_sites())
    for site in names:
        data, err = service.store(site).read_unlocked()
        view = service.build_view_for(site, data)
        out.append(site_status(site, data, view, service, now, read_error=err or ""))
    return out


__all__ = [
    "CHANNEL_TEXTS",
    "LaneStatus",
    "QuotaStatus",
    "SiteStatus",
    "ago_text",
    "blocking_reason",
    "build_site_statuses",
    "duration_text",
    "lane_counts",
    "LANE_TEXTS",
    "site_status",
    "stamp_text",
]
