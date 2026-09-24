"""HR 在线核实的持久化数据模型 (站点文件内的账号级状态)。

设计要点(计划 §5):
- **主键是 (站点, tid)** —— 种子编号站点内唯一、跨站点绝不混用; infohash 在下载算出后回填。
  站点由文件本身承载, 故结构里不带站点名。
- 这些状态**全部是账号级**(与实例数无关) ⇒ 不进 state_file, 落在站点文件里由实例共享。
- 所有字段可 JSON 往返: 落盘一律走 to_json/from_json, 结构变更靠 schema_version 挡。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

# 档位(scope): A 考察中 / B 已达标 / C 未达标 / D 已免罪
LANE_SCOPE = "A"
LANE_SATISFIED = "B"
LANE_UNSATISFIED = "C"
LANE_EXEMPT = "D"
ALL_LANES = (LANE_SCOPE, LANE_SATISFIED, LANE_UNSATISFIED, LANE_EXEMPT)


# 档位语义: B 已达标(仍受管束, 只是落 satisfied 分支) / D 已免罪(明确不受管束 ⇒ 可作放行来源)
def lane_is_satisfied(lane: str) -> bool:
    return lane == LANE_SATISFIED


def lane_is_exempt(lane: str) -> bool:
    return lane == LANE_EXEMPT


# 放行来源
SOURCE_EXEMPT = "absent"  # D 档(已免罪)
SOURCE_NOT_LISTED = "not-listed"  # 完整刷新未列出 A/B/C

# 通道状态(视图层, 用于告警与展示)
CHANNEL_OK = "ok"
CHANNEL_SILENT = "silent"
CHANNEL_DISABLED = "disabled"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class HrEntry:
    """HR 统计页的一行(站点侧事实)。刷新只更新字段, 不触发取数。"""

    tid: int
    name: str = ""
    lane: str = LANE_SCOPE
    uploaded_bytes: Optional[int] = None
    downloaded_bytes: Optional[int] = None
    ratio: Optional[float] = None
    need_seed_seconds: Optional[int] = None
    done_iso: Optional[str] = None
    remain_seconds: Optional[int] = None
    infohash_v1: str = ""
    infohash_v2: str = ""
    first_seen: float = 0.0
    last_seen: float = 0.0
    #: 是否出现在最近一次刷新的清单里。完整刷新会把全部条目置 False 再置 True 命中的;
    #: 不完备刷新只置 True("没抓全"不能证明其它条目已消失) —— 判定只认 active 条目。
    active: bool = True

    @property
    def satisfied_verdict(self) -> Optional[bool]:
        """站点侧对「是否达标」的**明确**结论; None = 站点没给(调用方本地兜底)。

        档位 B/C 是站点的明确结论; 其余档位看剩余达标时间(0 = 已达标)。**缺字段不给结论** ——
        「不知道」不能当成「未达标」, 否则本地已达标(做种时长/分享率够了)的种子会被误判,
        进而漏加 satisfied 标签 / 误报未达标(计划 §9: 站点侧优先, 本地兜底)。
        """
        if self.lane == LANE_SATISFIED:
            return True
        if self.lane == LANE_UNSATISFIED:
            return False
        if self.remain_seconds is not None:
            return self.remain_seconds == 0
        return None

    @property
    def satisfied_by_site(self) -> bool:
        """站点侧达标判据: 档位 B(已达标), 或剩余达标时间为 0 —— 站点数据是权威(计划 §9)。

        两者都不可得时返回 None 语义由调用方承担, 这里保守返回 False(不因缺字段就放行)。
        """
        return self.satisfied_verdict is True

    @property
    def done_epoch(self) -> Optional[float]:
        """完成时间的 epoch 秒; done_iso 缺失或不可解析返回 None(不猜 —— 超龄豁免判据依赖它)。

        naive 时刻按**本地时区**折算: 站点展示的是站点当地时刻, 与本机的时区偏差是小时级,
        对以「天」为单位的超龄判据不构成影响。
        """
        if not self.done_iso:
            return None
        try:
            return datetime.fromisoformat(self.done_iso).timestamp()
        except ValueError:
            return None

    def to_json(self) -> Dict[str, Any]:
        return {
            "tid": self.tid,
            "name": self.name,
            "lane": self.lane,
            "uploaded_bytes": self.uploaded_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "ratio": self.ratio,
            "need_seed_seconds": self.need_seed_seconds,
            "done_iso": self.done_iso,
            "remain_seconds": self.remain_seconds,
            "infohash_v1": self.infohash_v1,
            "infohash_v2": self.infohash_v2,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "active": self.active,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrEntry":
        return cls(
            tid=_as_int(raw.get("tid")),
            name=str(raw.get("name") or ""),
            lane=str(raw.get("lane") or LANE_SCOPE),
            uploaded_bytes=_opt_int(raw.get("uploaded_bytes")),
            downloaded_bytes=_opt_int(raw.get("downloaded_bytes")),
            ratio=_opt_float(raw.get("ratio")),
            need_seed_seconds=_opt_int(raw.get("need_seed_seconds")),
            done_iso=(str(raw["done_iso"]) if raw.get("done_iso") else None),
            remain_seconds=_opt_int(raw.get("remain_seconds")),
            infohash_v1=str(raw.get("infohash_v1") or ""),
            infohash_v2=str(raw.get("infohash_v2") or ""),
            first_seen=_as_float(raw.get("first_seen")),
            last_seen=_as_float(raw.get("last_seen")),
            active=bool(raw.get("active", True)),
        )


def _opt_int(value: Any) -> Optional[int]:
    return None if value is None else _as_int(value)


def _opt_float(value: Any) -> Optional[float]:
    return None if value is None else _as_float(value)


@dataclass(slots=True)
class HrDownloaded:
    """已取记录: 「永不重取」的持久凭据(条目消失 / 翻页遗漏 / 快照淘汰都不重下)"""

    tid: int
    ts: float = 0.0
    name: str = ""
    infohash_v1: str = ""
    infohash_v2: str = ""

    def to_json(self) -> Dict[str, Any]:
        return {
            "tid": self.tid,
            "ts": self.ts,
            "name": self.name,
            "infohash_v1": self.infohash_v1,
            "infohash_v2": self.infohash_v2
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrDownloaded":
        return cls(
            tid=_as_int(raw.get("tid")),
            ts=_as_float(raw.get("ts")),
            name=str(raw.get("name") or ""),
            infohash_v1=str(raw.get("infohash_v1") or ""),
            infohash_v2=str(raw.get("infohash_v2") or ""),
        )


@dataclass(slots=True)
class HrDlFail:
    """单个 .torrent 取数失败记账(达上限后冷却, 防烧配额)"""

    tid: int
    count: int = 0
    last_ts: float = 0.0

    def to_json(self) -> Dict[str, Any]:
        return {"tid": self.tid, "count": self.count, "last_ts": self.last_ts}

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrDlFail":
        return cls(tid=_as_int(raw.get("tid")), count=_as_int(raw.get("count")), last_ts=_as_float(raw.get("last_ts")))


@dataclass(slots=True)
class HrVerified:
    """已核实「不受管束」的放行记录(计划 §9)

    放行**不是永久状态**, 而是「最近一次完整核实」的有时效结论: 有效期 = min(下一次成功完整刷新,
    verified_ts + verified_ttl)。锚点只用于**提前作废本实例**的放行(别的客户端下载本地看不见)。
    """

    infohash: str
    tid: int
    verified_ts: float = 0.0
    source: str = SOURCE_NOT_LISTED
    anchor_added_on: int = 0
    anchor_downloaded: int = 0
    anchor_completion_on: int = -1
    anchor_progress: float = 0.0

    def to_json(self) -> Dict[str, Any]:
        return {
            "infohash": self.infohash,
            "tid": self.tid,
            "verified_ts": self.verified_ts,
            "source": self.source,
            "anchor_added_on": self.anchor_added_on,
            "anchor_downloaded": self.anchor_downloaded,
            "anchor_completion_on": self.anchor_completion_on,
            "anchor_progress": self.anchor_progress,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrVerified":
        return cls(
            infohash=str(raw.get("infohash") or ""),
            tid=_as_int(raw.get("tid")),
            verified_ts=_as_float(raw.get("verified_ts")),
            source=str(raw.get("source") or SOURCE_NOT_LISTED),
            anchor_added_on=_as_int(raw.get("anchor_added_on")),
            anchor_downloaded=_as_int(raw.get("anchor_downloaded")),
            anchor_completion_on=_as_int(raw.get("anchor_completion_on"), -1),
            anchor_progress=_as_float(raw.get("anchor_progress")),
        )


@dataclass(slots=True)
class HrRefreshMeta:
    """覆盖证明: 「安全放行」的唯一依据(计划 §4)

    只有 complete 为真时, 本次未命中才敢判「不受管束」; 否则一律未核实(保守)。
    """

    last_success_ts: float = 0.0
    scopes_done: List[str] = field(default_factory=list)
    pages_fetched: int = 0
    reached_last_page: bool = False
    entry_count: int = 0
    missing_field_rate: float = 0.0
    complete: bool = False
    reason: str = ""

    def to_json(self) -> Dict[str, Any]:
        return {
            "last_success_ts": self.last_success_ts,
            "scopes_done": list(self.scopes_done),
            "pages_fetched": self.pages_fetched,
            "reached_last_page": self.reached_last_page,
            "entry_count": self.entry_count,
            "missing_field_rate": self.missing_field_rate,
            "complete": self.complete,
            "reason": self.reason,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrRefreshMeta":
        return cls(
            last_success_ts=_as_float(raw.get("last_success_ts")),
            scopes_done=[str(s) for s in (raw.get("scopes_done") or [])],
            pages_fetched=_as_int(raw.get("pages_fetched")),
            reached_last_page=bool(raw.get("reached_last_page")),
            entry_count=_as_int(raw.get("entry_count")),
            missing_field_rate=_as_float(raw.get("missing_field_rate")),
            complete=bool(raw.get("complete")),
            reason=str(raw.get("reason") or ""),
        )


@dataclass(slots=True)
class HrQuota:
    """频控账本: 小时/天两级窗口(窗口键变化即重置, 重启不重置 —— 幂等靠窗口键而非进程状态)"""

    hour_window: str = ""
    hour_count: int = 0
    day_window: str = ""
    day_count: int = 0
    last_fetch_ts: float = 0.0

    def to_json(self) -> Dict[str, Any]:
        return {
            "hour_window": self.hour_window,
            "hour_count": self.hour_count,
            "day_window": self.day_window,
            "day_count": self.day_count,
            "last_fetch_ts": self.last_fetch_ts,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrQuota":
        return cls(
            hour_window=str(raw.get("hour_window") or ""),
            hour_count=_as_int(raw.get("hour_count")),
            day_window=str(raw.get("day_window") or ""),
            day_count=_as_int(raw.get("day_count")),
            last_fetch_ts=_as_float(raw.get("last_fetch_ts")),
        )


@dataclass(slots=True)
class HrFuse:
    """站点熔断: 连续失败达阈值后冷却, 期间零请求"""

    failures: int = 0
    until_ts: float = 0.0
    reason: str = ""

    @property
    def active(self) -> bool:
        return self.until_ts > 0.0

    def to_json(self) -> Dict[str, Any]:
        return {"failures": self.failures, "until_ts": self.until_ts, "reason": self.reason}

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrFuse":
        return cls(
            failures=_as_int(raw.get("failures")),
            until_ts=_as_float(raw.get("until_ts")),
            reason=str(raw.get("reason") or ""),
        )


@dataclass(slots=True)
class HrSiteData:
    """一个站点的全部账号级状态(站点文件的内容)"""

    schema_version: int = SCHEMA_VERSION
    revision: int = 0
    fetched_at: float = 0.0
    expires_at: float = 0.0
    writer_instance: str = ""
    writer_heartbeat: float = 0.0
    index: Dict[int, HrEntry] = field(default_factory=dict)
    downloaded: Dict[int, HrDownloaded] = field(default_factory=dict)
    fails: Dict[int, HrDlFail] = field(default_factory=dict)
    verified: Dict[str, HrVerified] = field(default_factory=dict)  # infohash -> 放行记录
    refresh: HrRefreshMeta = field(default_factory=HrRefreshMeta)
    quota: HrQuota = field(default_factory=HrQuota)
    fuse: HrFuse = field(default_factory=HrFuse)

    # ---------- 读写 ----------

    def infohash_of(self, tid: int) -> str:
        """取该 tid 已回填的 infohash(v1 优先, 缺失回落 v2)"""
        entry = self.index.get(tid)
        if entry is None:
            got = self.downloaded.get(tid)
            return (got.infohash_v1 or got.infohash_v2) if got is not None else ""
        return entry.infohash_v1 or entry.infohash_v2

    def index_by_infohash(self) -> Dict[str, int]:
        """(infohash -> tid) 反查表。站点文件只存 tid 主键, 反查表在读取时现建。"""
        out: Dict[str, int] = {}
        for tid, entry in self.index.items():
            if not entry.active:
                continue
            for h in (entry.infohash_v1, entry.infohash_v2):
                if h:
                    out.setdefault(h, tid)
        return out

    def to_json(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "fetched_at": self.fetched_at,
            "expires_at": self.expires_at,
            "writer": {
                "instance_id": self.writer_instance,
                "heartbeat": self.writer_heartbeat
            },
            "index": [e.to_json() for e in self.index.values()],
            "downloaded": [d.to_json() for d in self.downloaded.values()],
            "fails": [f.to_json() for f in self.fails.values()],
            "verified": [v.to_json() for v in self.verified.values()],
            "refresh": self.refresh.to_json(),
            "quota": self.quota.to_json(),
            "fuse": self.fuse.to_json(),
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrSiteData":
        writer = raw.get("writer") or {}
        data = cls(
            schema_version=_as_int(raw.get("schema_version"), SCHEMA_VERSION),
            revision=_as_int(raw.get("revision")),
            fetched_at=_as_float(raw.get("fetched_at")),
            expires_at=_as_float(raw.get("expires_at")),
            writer_instance=str(writer.get("instance_id") or raw.get("writer_instance") or ""),
            writer_heartbeat=_as_float(writer.get("heartbeat") or raw.get("writer_heartbeat")),
            refresh=HrRefreshMeta.from_json(raw.get("refresh") or {}),
            quota=HrQuota.from_json(raw.get("quota") or {}),
            fuse=HrFuse.from_json(raw.get("fuse") or {}),
        )
        for item in raw.get("index") or []:
            entry = HrEntry.from_json(item)
            data.index[entry.tid] = entry
        for item in raw.get("downloaded") or []:
            got = HrDownloaded.from_json(item)
            data.downloaded[got.tid] = got
        for item in raw.get("fails") or []:
            fail = HrDlFail.from_json(item)
            data.fails[fail.tid] = fail
        for item in raw.get("verified") or []:
            ver = HrVerified.from_json(item)
            if ver.infohash and ver.verified_ts > 0:
                data.verified[ver.infohash] = ver
        return data
