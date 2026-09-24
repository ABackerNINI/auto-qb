"""HR 站点现状的**纯数据**快照(计划 §11 M4「索引新鲜度与进度展示」)。

为什么单独一层: 「某个站点现在到底是什么状态」有三个消费者 ——
1. `--hr-status` 报告(给人核数据用, 终端文本);
2. WebUI(设置页「HR 在线核实」章节, 只在需要时拉一次);
3. 日后的 notify / 运维脚本。
它们必须看到**同一套数值口径**(尤其是「待回填几条」「还能取几次」「新鲜度到没到」这类派生量) ——
各写一遍就会出现「报告说待回填 2 条、界面说 3 条」这种没法排查的偏差, 故收口到 `site_status()`。

本模块**只读**: 不取数、不加锁、不写盘(读的是原子替换后的完整快照, 与 `--hr-status` 同款口径),
取数节奏由取数线程决定, 展示层永远只是"看一眼"。

时间相关字段的语义(易混, 明写):
- `fetched_at`: 上次**尝试**取数的时刻(失败也会前进 —— 它回答"上次动过是什么时候");
- `last_success_ts`: 上次**完整成功**刷新的时刻 —— 它才是新鲜度基准(不完备刷新不推进);
- `expires_at`: 本次数据的有效期截止(完整刷新 = 周期, 不完备 = 至少 2×轮询间隔的短暂窗口、
  以周期封顶 —— 窗口必须盖过下一轮, 否则「复用轮只补下载」永远轮不上, 见 service._do_fetch);
- `next_refresh_at`: 下次**可能**去取的时刻(现在算: fetched_at + 刷新周期) —— 站点文件里不存它,
  因为它随周期配置变化, 存下来就会重复一份可能过期的副本。
"""
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .model import (
    CHANNEL_DISABLED,
    CHANNEL_OK,
    CHANNEL_SILENT,
    LANE_EXEMPT,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    HrSiteData,
)
from .ratelimit import day_key, fuse_active, hour_key, quota_left
from .resolve import HrSiteView

#: 通道状态的人话(与 `--hr-status` 逐字一致 —— 两处口径必须相同)
CHANNEL_TEXTS = {
    CHANNEL_OK: "正常",
    CHANNEL_SILENT: "静默(长期没有成功刷新)",
    CHANNEL_DISABLED: "未启用",
}

#: 档位顺序(展示固定顺序: A 考察中 / B 已达标 / C 未达标 / D 已免罪)
LANE_ORDER = (LANE_SCOPE, LANE_SATISFIED, LANE_UNSATISFIED, LANE_EXEMPT)

#: 档位人话(明细表等展示共用; 键 = 站点 scope 字母)
LANE_TEXTS = {
    LANE_SCOPE: "考察中",
    LANE_SATISFIED: "已达标",
    LANE_UNSATISFIED: "未达标",
    LANE_EXEMPT: "已免罪",
}


@dataclass(slots=True)
class QuotaStatus:
    """配额窗口状态(两级: 小时 / 天)"""

    hour: int = 0
    hour_max: int = 0
    day: int = 0
    day_max: int = 0
    left: int = 0
    last_fetch_ts: float = 0.0
    min_interval: float = 0.0
    text: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(slots=True)
class FuseStatus:
    """熔断状态(退避冷却)"""

    active: bool = False
    until_ts: float = 0.0
    failures: int = 0
    reason: str = ""
    text: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(slots=True)
class SiteStatus:
    """单站点 HR 现状(全部字段都由 `site_status()` 算好; 前端只展示, 不重算)"""

    site: str
    mode: str = "off"
    #: 生成本快照的时刻 —— 所有相对时间(「N 前」)的**唯一基准**, 界面拿它算「多久前拉的」
    now: float = 0.0
    complete: bool = False
    channel_state: str = CHANNEL_DISABLED
    channel_text: str = ""
    revision: int = 0
    file_path: str = ""
    read_error: str = ""
    #: 上次**尝试**取数 / 上次**完整成功**刷新 / 有效期截止 / 下次可能取数(现算)
    fetched_at: float = 0.0
    last_success_ts: float = 0.0
    expires_at: float = 0.0
    next_refresh_at: float = 0.0
    #: 数据是否已过有效期(读取时现算; 过期 ≠ 没数据, 只是不能再当背书用)
    stale: bool = False
    fresh_text: str = ""
    refresh_interval: float = 0.0
    verified_ttl: float = 0.0
    scopes_done: Tuple[str, ...] = ()
    pages_fetched: int = 0
    entry_count: int = 0
    missing_field_rate: float = 0.0
    writer_instance: str = ""
    writer_heartbeat: float = 0.0
    reason: str = ""
    index_total: int = 0
    index_active: int = 0
    lanes: Dict[str, int] = field(default_factory=dict)
    #: 待回填 infohash 条数 + 回填进度(活跃条目里已有 infohash 的比例) —— 取数通道刚接通时它是唯一的进度信号
    pending_infohash: int = 0
    backfill_ratio: float = 0.0
    managed: int = 0
    keys: int = 0
    downloaded: int = 0
    fails: int = 0
    verified: int = 0
    quota: QuotaStatus = field(default_factory=QuotaStatus)
    fuse: FuseStatus = field(default_factory=FuseStatus)
    allow_window: str = ""
    #: 覆盖证明成立但数据已过期时, 判定会保守回落 —— 界面上要能一眼看出「差在哪一步」
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


def site_status(site: str, data: HrSiteData, view: HrSiteView, service, now: float, read_error: str = "") -> SiteStatus:
    """把「站点文件 + 视图」折成一份只读快照(数值口径的单点)"""
    conf = service.site_confs[site]
    limits = service.limits_for(site)
    lanes = lane_counts(data)
    active = [e for e in data.index.values() if e.active]
    pending = sum(1 for e in active if not e.infohash_v1 and not e.infohash_v2)
    filled = len(active) - pending
    backfill = (filled / len(active)) if active else 0.0
    stale = bool(data.expires_at) and now > data.expires_at
    fuse = FuseStatus(
        active=fuse_active(data.fuse, now),
        until_ts=data.fuse.until_ts,
        failures=data.fuse.failures,
        reason=data.fuse.reason,
    )
    fuse.text = (f"熔断中至 {stamp_text(fuse.until_ts)}({fuse.reason})" if fuse.active else f"正常(连续失败 {fuse.failures})")
    # 展示口径与 quota_left 同源: 窗口键已翻篇(上一小时 / 昨天)的计数不能标成「本小时 / 本天」,
    # 否则会出现「本小时 7/12 · 还能取 12 次」的自相矛盾(2026-09-25 实报)
    hk, dk = hour_key(now), day_key(now)
    quota = QuotaStatus(
        hour=data.quota.hour_count if data.quota.hour_window == hk else 0,
        hour_max=limits.max_per_hour,
        day=data.quota.day_count if data.quota.day_window == dk else 0,
        day_max=limits.max_per_day,
        left=quota_left(data.quota, limits, now),
        last_fetch_ts=data.quota.last_fetch_ts,
        min_interval=limits.min_interval,
    )
    quota.text = (
        f"本小时 {quota.hour}/{quota.hour_max} · 本天 {quota.day}/{quota.day_max} · 还能取 {quota.left} 次 · "
        f"最近请求 {ago_text(quota.last_fetch_ts, now)} · 最小间隔 {quota.min_interval:g}s"
    )
    fresh = f"上次取数 {ago_text(data.fetched_at, now)} · 最近完整刷新 {ago_text(data.refresh.last_success_ts, now)}"
    if data.expires_at:
        fresh += f" · 数据有效期至 {stamp_text(data.expires_at)}" + ("(已过期)" if stale else "")
    next_at = data.fetched_at + site_conf_interval(conf) if data.fetched_at else 0.0
    return SiteStatus(
        site=site,
        mode=conf.mode,
        now=now,
        complete=view.complete,
        channel_state=view.channel_state,
        channel_text=CHANNEL_TEXTS.get(view.channel_state, "未启用"),
        revision=data.revision,
        file_path=service.site_path(site),
        read_error=read_error,
        fetched_at=data.fetched_at,
        last_success_ts=data.refresh.last_success_ts,
        expires_at=data.expires_at,
        next_refresh_at=next_at,
        stale=stale,
        fresh_text=fresh,
        refresh_interval=site_conf_interval(conf),
        verified_ttl=view.verified_ttl,
        scopes_done=tuple(data.refresh.scopes_done),
        pages_fetched=data.refresh.pages_fetched,
        entry_count=data.refresh.entry_count,
        missing_field_rate=data.refresh.missing_field_rate,
        writer_instance=data.writer_instance,
        writer_heartbeat=data.writer_heartbeat,
        reason=data.refresh.reason,
        index_total=len(data.index),
        index_active=len(active),
        lanes=lanes,
        pending_infohash=pending,
        backfill_ratio=backfill,
        managed=len({e.tid
                     for e in view.by_infohash.values()}),
        keys=len(view.by_infohash),
        downloaded=len(data.downloaded),
        fails=len(data.fails),
        verified=len(data.verified),
        quota=quota,
        fuse=fuse,
        allow_window=limits.allow_window or "",
        blocking=blocking_reason(view, data, stale),
    )


def site_conf_interval(conf) -> float:
    """站点刷新周期(秒); 单独提出来是为了让「下次刷新」这类字段的算法只有一处"""
    return float(getattr(conf, "refresh_interval", 0.0) or 0.0)


def blocking_reason(view: HrSiteView, data: HrSiteData, stale: bool) -> str:
    """一句话说明「为什么现在不产生新放行」(按判定链的顺序, 取第一个挡路的原因)

    判定链: 站点没接入 → 覆盖证明不成立 → 数据过期 → 没有任何可查键。用户看到「种子没被放行」时
    最想知道的就是它卡在哪一步, 而这一步光看数据看不出来。
    """
    if view.mode == "off":
        return "站点未接入 hr_check(mode: off)"
    if not view.complete:
        return "覆盖证明不成立(刷新不完备, 不产生新放行)"
    if stale:
        return "数据已过有效期(会保守回落未核实)"
    if not view.has_lookup_keys:
        return "索引里还没有任何 infohash(待回填; 先让浏览器扩展跑一轮取数)"
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
    "FuseStatus",
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
