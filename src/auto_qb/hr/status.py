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
- `wave.healthy_ts`: 上次**健康波**时刻(至少一档有有效数据) —— 它才是新鲜度与**拉取节奏**的基准
  (计划 26-09-30-0240: 拉取间隔闸门与「下次核对清单」展示都从它算, 失败波不推进 ⇒ 失败档下一轮重试);
- `expires_at`: 复用窗截止(别的实例刚抓过就不再抓; 时长 = min(复用窗, 拉取间隔));
- `next_wave_at`: 下次**可能**取的时刻(现算: healthy_ts + 拉取间隔, 稳态期用 idle_refresh_interval,
  单点见 `site_conf_interval`) —— 站点文件里不存它, 因为它随周期配置变化, 存下来就会重复一份
  可能过期的副本。
"""
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .model import (
    CHANNEL_DISABLED,
    CHANNEL_OK,
    CHANNEL_SILENT,
    FETCH_LANES,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrHistoryEvent,
    HrSiteData,
)
from .ratelimit import day_key, next_day_reset, quota_left
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

#: 放行来源人话(种子明细导出用; 原始值一并透出, 前端不重算。计划 26-10-01-2216 §3)
SOURCE_TEXTS = {
    SOURCE_EXEMPT: "D 免罪",
    SOURCE_NOT_LISTED: "未列出",
    SOURCE_SATISFIED: "已达标",
}

#: 拉取历史 · 事件种类人话(计划 26-10-04-0312 §3.4): defer 与 wave 的 waiting 徽章同为
#: 「拦下」档, 语义区分(自动波被拦 vs 立即拉取被拦)靠 kind_text, 不另设第二套 action 映射
HISTORY_KIND_TEXTS = {
    "wave": "取数波",
    "defer": "立即拉取被拦",
    "confirm_empty": "人工对账",
}

#: 拉取历史 · 触发方式人话(表③ 触发列; 与 service 的 trigger 口径一一对应)
HISTORY_TRIGGER_TEXTS = {
    "auto": "自动",
    "manual": "立即",
    "confirm": "对账",
}

#: 拉取历史 · 结果徽章映射(单点): action -> (人话, 色档)。色档取值 = 前端 pill 档位
#: (ok / warn / dim / err / blue); 键 = service.ACTION_* 波终态的字面量 —— 刻意不反向
#: import 引擎模块(本模块保持纯展示), 字面量由测试钉死对齐。
#: kind='confirm_empty' 特判优先于查表(其 action='confirm-empty' 本就不在表内)。
HISTORY_RESULT_BADGES = {
    "refreshed": ("完成", "ok"),
    "partial": ("部分·截断", "warn"),
    "waiting": ("拦下·未到时刻", "dim"),
    "no-channel": ("通道不可用", "err"),
    "error": ("失败", "err"),
    "skipped-locked": ("锁忙", "dim"),
}
HISTORY_RESULT_CONFIRM = ("对账", "blue")  #: confirm_empty 事件的特判徽章(计划 §3.4)


@dataclass(slots=True)
class LaneStatus:
    """单档位波次状态(展示层; 与 model.HrLaneState 一一对应的人话折算)"""

    lane: str = ""
    status: str = ""
    status_text: str = ""
    lane_text: str = ""  #: 档位人话(表② 波次表徽章「A 考察中」; 取自 LANE_TEXTS 单点, 计划 26-10-01-2216 §6.2)
    wave_ts: float = 0.0
    pages: int = 0
    rows: int = 0
    cutoff_done: float = 0.0
    full_depth: bool = False
    fail_streak: int = 0
    count_claim: Optional[int] = None  #: 站点声明行数(None = 无计数, 计划 26-09-29-2036 §2.6)
    count_match: Optional[bool] = None  #: None = 无从对平; False = 对不平
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
    #: 上次**尝试**取波 / 上次**健康波** / 复用窗截止 / 下次可能取波(现算: 健康波 + 拉取间隔)
    fetched_at: float = 0.0
    healthy_ts: float = 0.0
    expires_at: float = 0.0
    next_wave_at: float = 0.0
    refresh_interval: float = 0.0
    #: 稳态降频旗标(计划 26-10-05-0555 §2.4「展示链的桥」): 透传落盘的 wave.idle_mode, 前端 kv 行
    #: 只读旗标挑文案(同 stale/(已过) 先例), 不重算判据(§06 R6 分工)
    idle_mode: bool = False
    stale: bool = False
    fresh_text: str = ""
    #: 波次视图(各档独立状态: 有效/失效/截断、页数、行数、覆盖边界、连续失效)
    lanes: List[LaneStatus] = field(default_factory=list)
    lanes_text: str = ""
    releases_enabled: bool = False
    zero_rows: bool = False
    empty_confirmed: bool = False
    #: 页头计数自证空集(§2.5): 零行波 ∧ 各档声明全 0 —— 无需人工戳, 前端据此摘掉「零行未确认」
    count_attested_empty: bool = False
    retention_text: str = ""
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


def need_seed_text(seconds: Optional[int]) -> str:
    """还需做种时间, 镜像站点书写形态(「16:57:06」/「9天06:05:11」)方便逐格核对; 缺字段 = -

    原是 CLI 报告的私有件(report.py `_need_seed_text`), 随种子明细导出上收为本模块的口径单点
    (计划 26-10-01-2216 §7 阶段1): CLI 明细表与 WebUI 表① 必须是同一份人话, 不另写第二份。
    """
    if seconds is None:
        return "-"
    days, rem = divmod(max(0, int(seconds)), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    prefix = f"{days}天" if days else ""
    return f"{prefix}{hours:02d}:{minutes:02d}:{secs:02d}"


def lane_counts(data: HrSiteData) -> Dict[str, int]:
    """四档位计数(含免罪档)"""
    counts: Dict[str, int] = {}
    for entry in data.index.values():
        counts[entry.lane] = counts.get(entry.lane, 0) + 1
    return counts


def count_attested_empty(data: HrSiteData) -> bool:
    """页头计数自证空集(计划 26-09-29-2036 §2.5): 零行波 ∧ 各档站点声明全为 0。

    与 service._finish_wave 里 confirmed_empty 的 OR 分支同一公式(对持久化后的波次状态复算)
    —— 展示面与行为面必须同一口径: 计数自证的站点不需要人工戳, 就不该再被标
    「零行未确认」/「需 --hr-confirm-empty」。任一档声明为 None(未证到/无计数)参与全称量词
    即为假, 保守方向自动成立。
    """
    return bool(data.wave.zero_rows) and all(st.count_claim == 0 for st in data.wave.lanes.values())


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
            lane_text=LANE_TEXTS.get(lane, lane),
            wave_ts=st.wave_ts,
            pages=st.pages,
            rows=st.rows,
            cutoff_done=st.cutoff_done,
            full_depth=st.full_depth,
            fail_streak=st.fail_streak,
            count_claim=st.count_claim,
            count_match=st.count_match,
            detail=st.detail,
        )
        ls.text = (
            f"{LANE_TEXTS.get(lane, lane)} {ls.status_text}: {ls.pages} 页 / {ls.rows} 行" +
            ("(全深度)" if ls.full_depth else "") + (f" / 声明 {ls.count_claim} 行" if ls.count_claim is not None else "") +
            (" 对不平" if ls.count_match is False else "") + (f", {ls.detail}" if ls.detail else "") +
            (f", 连续失效 {ls.fail_streak} 波" if ls.fail_streak > 1 else "")
        )
        out.append(ls)
        parts.append(
            f"{lane}:{'[x]' if st.status == LANE_OK else ('x' if st.status == LANE_FAILED else '-')}"
            f"{st.pages}页{st.rows}行" + ("(全)" if st.full_depth else "") + (
                f"/声明{st.count_claim}" +
                (" 对不平" if st.count_match is False else "") if st.count_claim is not None else ""
            )
        )
    return out, " ".join(parts)


def _retention_text(data: HrSiteData) -> str:
    """A 档流转守恒观测(§5.3)"""
    meta = data.wave
    if meta.retention_ratio < 0:
        return "不适用(上波无 A 档行)"
    tail = "正常" if meta.retention_ok else "WARN: 不达标(批量未列出签发已冻结)"
    return f"上波 A 档 {len(meta.prev_a_tids)} 行, 本波留存率 {meta.retention_ratio:.0%}, {tail}"


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
    # 拉取节奏基准 = 上次健康波(计划 26-09-30-0240): 与 service 的拉取间隔闸门同一算法(单一出处);
    # 失败波不推进 healthy_ts ⇒ 「下次核对」不因失败波顺延, 与「下一轮重试」的处置一致。
    # 文案口径(2026-10-03 修 B2): 这是**对账节奏**(下一次核对站点清单的时刻), 不是取种进度 ——
    # 「下次拉取」易被读成「还有多少没拉完」, 故改「下次核对清单」(与「立即拉取」按钮区分)。
    next_at = data.wave.healthy_ts + site_conf_interval(conf, data.wave) if data.wave.healthy_ts else 0.0
    fresh = f"上次取波 {ago_text(data.fetched_at, now)} · 最近健康波 {ago_text(data.wave.healthy_ts, now)}"
    if data.expires_at:
        fresh += f" · 复用窗至 {stamp_text(data.expires_at)}" + ("(已过)" if stale else "")
    if next_at:
        # 拍板 D1(计划 26-10-05-0555 §05): 稳态期给「下次核对清单」补一句降频注记 ——
        # 不加则 24H 倒计时空降无解释; 数据源是落盘旗标 wave.idle_mode(§2.4), 常态期不出现。
        fresh += f" · 下次核对清单 {stamp_text(next_at)}" + ("(稳态降频)" if data.wave.idle_mode else "")
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
        refresh_interval=site_conf_interval(conf, data.wave),
        idle_mode=data.wave.idle_mode,
        stale=stale,
        fresh_text=fresh,
        lanes=lanes,
        lanes_text=lanes_text,
        releases_enabled=data.wave.releases_enabled,
        zero_rows=data.wave.zero_rows,
        empty_confirmed=data.empty_confirmed_at > 0,
        count_attested_empty=count_attested_empty(data),
        retention_text=_retention_text(data),
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
        blocking=blocking_reason(view, data, stale, site, next_wave_at=next_at),
    )


@dataclass(slots=True)
class EntryDetail:
    """单条 HR 种子明细(WebUI 表① 的行; 计划 26-10-01-2216 §3 P0+P1 全集)

    数值字段原样透传, 人话(lane_text / need_seed_text / verified_source_text)由后端算好
    —— 前端只展示不重算(契约: 前端消费后端算好字段)。`verified_ts`(放行判定时刻)与
    `last_seen`(被站点见到时刻)是**两个独立口径**, 分键呈现(决策点④); `remain_seconds`
    刻意不导出(决策点③ —— 考核窗口倒计时不是还需做种的量, 2026-09-25 误读教训)。
    """

    tid: int
    dl_id: Optional[int] = None
    name: str = ""
    lane: str = ""
    lane_text: str = ""
    uploaded_bytes: Optional[int] = None
    downloaded_bytes: Optional[int] = None
    ratio: Optional[float] = None
    need_seed_seconds: Optional[int] = None
    need_seed_text: str = ""
    infohash_v1: str = ""
    infohash_v2: str = ""
    verified_ts: float = 0.0
    verified_source: str = ""
    verified_source_text: str = ""
    done_iso: Optional[str] = None
    active: bool = True
    missing_streak: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


def entry_details(data: HrSiteData) -> List[EntryDetail]:
    """种子明细导出(WebUI 表① 行集; 计划 26-10-01-2216 §7 阶段1) —— 与 CLI 明细表同一套口径

    - 排序沿用 CLI 明细表的 key(档位·下载量, report._print_status_rows 同一公式);
    - 行集**含失踪行**(active=False 也导出 —— 「哪些种子已核实/未核实」的全量清单一览是
      issue 本意; CLI 明细表只显示活跃行, 失踪行在界面上靠状态列弱化呈现);
    - verified join 走 data.verified(infohash→放行记录): v1 优先、缺失落 v2(终态冻结给
      v1/v2 各写一条, 观察期出口只写主键 —— 任一命中即该种子的放行记录);
    - remain_seconds 与 P2 字段(已取/失败记录、本地对照 join)刻意不导出(决策点③ / §8)。
    """
    entries = sorted(data.index.values(), key=lambda e: (e.lane, -(e.downloaded_bytes or 0)))
    out: List[EntryDetail] = []
    for e in entries:
        ver = None
        for h in (e.infohash_v1, e.infohash_v2):
            ver = data.verified.get(h) if h else None
            if ver is not None:
                break
        out.append(
            EntryDetail(
                tid=e.tid,
                dl_id=e.dl_id,
                name=e.name,
                lane=e.lane,
                lane_text=LANE_TEXTS.get(e.lane, e.lane),
                uploaded_bytes=e.uploaded_bytes,
                downloaded_bytes=e.downloaded_bytes,
                ratio=e.ratio,
                need_seed_seconds=e.need_seed_seconds,
                need_seed_text=need_seed_text(e.need_seed_seconds),
                infohash_v1=e.infohash_v1,
                infohash_v2=e.infohash_v2,
                verified_ts=ver.verified_ts if ver else 0.0,
                verified_source=ver.source if ver else "",
                verified_source_text=SOURCE_TEXTS.get(ver.source, ver.source) if ver else "未核实",
                done_iso=e.done_iso,
                active=e.active,
                missing_streak=e.missing_streak,
                first_seen=e.first_seen,
                last_seen=e.last_seen,
            )
        )
    return out


@dataclass(slots=True)
class HistoryLane:
    """单档终态快照(拉取历史展开小表的一行; 与 HrHistoryEvent.lanes 同构 + 人话)"""

    lane: str = ""
    lane_text: str = ""  #: 档位人话(取自 LANE_TEXTS 单点)
    status: str = ""
    status_text: str = ""  #: 档位状态人话(取自 LANE_STATUS_TEXTS 单点)
    pages: int = 0
    rows: int = 0
    detail: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(slots=True)
class HistoryRow:
    """单条拉取历史(WebUI 表③ 的行; 计划 26-10-04-0312 §3.4)

    数值字段原样透传, 人话(ts_text / elapsed_text / kind_text / trigger_text / result_text /
    result_tone / 各档 lane_text)全部由后端算好 —— 前端只展示不重算(表① 同款契约)。
    `result_tone` 是结果徽章色档(ok/warn/dim/err/blue, 直接对应前端 pill 档位);
    `ts`(epoch)与 `ts_text` 并给 —— 排序用原值、展示用文案。
    """

    ts: float = 0.0
    ts_text: str = ""
    site: str = ""
    kind: str = ""
    kind_text: str = ""
    trigger: str = ""
    trigger_text: str = ""
    action: str = ""
    result_text: str = ""
    result_tone: str = ""
    reason: str = ""
    reason_kind: str = ""
    pages: int = 0
    rows: int = 0
    torrents_ok: int = 0
    torrents_fail: int = 0
    verified: int = 0
    elapsed_s: float = 0.0
    elapsed_text: str = ""
    lanes: List[HistoryLane] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    by: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


def _history_lanes(raw_lanes: List[Dict]) -> List[HistoryLane]:
    """事件档位快照 -> 展示行(补 lane_text / status_text 人话; 脏键按缺省兜住不抛)"""
    out: List[HistoryLane] = []
    for item in raw_lanes:
        if not isinstance(item, dict):
            continue
        lane = str(item.get("lane") or "")
        status = str(item.get("status") or "")
        out.append(
            HistoryLane(
                lane=lane,
                lane_text=LANE_TEXTS.get(lane, lane),
                status=status,
                status_text=LANE_STATUS_TEXTS.get(status, status),
                pages=int(item.get("pages") or 0),
                rows=int(item.get("rows") or 0),
                detail=str(item.get("detail") or ""),
            )
        )
    return out


def history_rows(datas: Mapping[str, HrSiteData], limit: int, now: float = 0.0) -> List[HistoryRow]:
    """拉取历史导出(WebUI 表③ 行集; 计划 26-10-04-0312 §3.4) —— 跨站点合并成一条时间轴

    - 合并各站点 history、按 ts 降序、截 limit(limit <= 0 回空表, 上限钳制是调用方的
      参数卫生); 站点归属记进行 site 列(历史跨站点成时间轴, 站点列是前端过滤键);
    - 结果徽章映射单点在 HISTORY_RESULT_BADGES(kind='confirm_empty' 特判优先于查表);
      未知 action 回落原值 + dim(原值与人话并给的既有兜底范式, 不静默丢);
    - `now` 为本次快照基准入参(与 site_status / build_site_statuses 同范式收口):
      行内时刻均为绝对值, 当前无「N 前」类相对折算 —— 预留给后续同基准的相对时间字段。
    """
    merged: List[Tuple[float, str, HrHistoryEvent]] = []
    for site, data in datas.items():
        for ev in data.history:
            merged.append((ev.ts, site, ev))
    merged.sort(key=lambda item: item[0], reverse=True)
    out: List[HistoryRow] = []
    for ts, site, ev in merged[:max(0, int(limit))]:
        if ev.kind == "confirm_empty":
            result_text, tone = HISTORY_RESULT_CONFIRM
        else:
            result_text, tone = HISTORY_RESULT_BADGES.get(ev.action, (ev.action, "dim"))
        out.append(
            HistoryRow(
                ts=ts,
                ts_text=stamp_text(ts),
                site=site,
                kind=ev.kind,
                kind_text=HISTORY_KIND_TEXTS.get(ev.kind, ev.kind),
                trigger=ev.trigger,
                trigger_text=HISTORY_TRIGGER_TEXTS.get(ev.trigger, ev.trigger),
                action=ev.action,
                result_text=result_text,
                result_tone=tone,
                reason=ev.reason,
                reason_kind=ev.reason_kind,
                pages=ev.pages,
                rows=ev.rows,
                torrents_ok=ev.torrents_ok,
                torrents_fail=ev.torrents_fail,
                verified=ev.verified,
                elapsed_s=ev.elapsed_s,
                elapsed_text=duration_text(ev.elapsed_s),
                lanes=_history_lanes(ev.lanes),
                notes=list(ev.notes),
                by=ev.by,
            )
        )
    return out


def site_conf_interval(conf, wave) -> float:
    """站点拉取间隔(秒, 计划 26-09-30-0240 改名: 原名「对账波周期」); 单独提出来是为了让
    「下次核对清单」这类字段的算法只有一处。

    按落盘稳态旗标取值(计划 26-10-05-0555 §2.6): wave.idle_mode 为真(引擎在稳态期翻转落盘,
    §2.4)返回 idle_refresh_interval, 展示与闸门真实行为一致; 常态期与存量站点文件(旗标缺省
    False)返回 refresh_interval。展示只读落盘旗标、不现算判据(§06 R6 分工)。"""
    if getattr(wave, "idle_mode", False):
        return float(getattr(conf, "idle_refresh_interval", 0.0) or 0.0)
    return float(getattr(conf, "refresh_interval", 0.0) or 0.0)


def blocking_reason(view: HrSiteView, data: HrSiteData, stale: bool, site: str = "", next_wave_at: float = 0.0) -> str:
    """一句话说明「为什么现在不签发新放行」(按判定链的顺序, 取第一个挡路的原因)

    用户看到「种子没被放行」时最想知道的就是它卡在哪一步, 而这一步光看数据看不出来。
    """
    if not view.lane_a and not view.lane_terminal and not view.verified:
        return "索引里还没有任何可判数据(先让浏览器扩展跑一轮取数)"
    if data.wave.zero_rows and not data.empty_confirmed_at and not count_attested_empty(data):
        return "结构完好但清单为 0: 不签发放行 —— 需 --hr-confirm-empty 人工对账一次"
    if not data.wave.releases_enabled:
        return "本波未全部档位有效(截断/失效): 命中照常, 批量「未列出」待下波续判"
    if stale:
        nxt = f" 下次核对清单 {stamp_text(next_wave_at)}" if next_wave_at else ""
        return f"数据已过复用窗,{nxt}(可点『立即拉取』提前)"
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
    "EntryDetail",
    "HistoryLane",
    "HistoryRow",
    "LaneStatus",
    "QuotaStatus",
    "SiteStatus",
    "SOURCE_TEXTS",
    "ago_text",
    "blocking_reason",
    "build_site_statuses",
    "count_attested_empty",
    "duration_text",
    "entry_details",
    "history_rows",
    "lane_counts",
    "LANE_TEXTS",
    "need_seed_text",
    "site_status",
    "stamp_text",
]
