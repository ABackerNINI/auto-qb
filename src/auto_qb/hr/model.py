"""HR 在线核实的持久化数据模型 (站点文件内的账号级状态)。

设计要点(v3 波次模型, 计划 26-09-28-1932 §7.2):
- **主键是 (站点, tid)** —— 种子编号站点内唯一、跨站点绝不混用; infohash 在下载算出后回填。
  站点由文件本身承载, 故结构里不带站点名。
- 这些状态**全部是账号级**(与实例数无关) ⇒ 不进 state_file, 落在站点文件里由实例共享。
- 所有字段可 JSON 往返: 落盘一律走 to_json/from_json, 结构变更靠 schema_version 挡。

v3 模型变化(相对 v2):
- **证据无时效, 只有真伪**(§3.4): 两级证据年龄与整波「覆盖证明」退役, 换成**档位级数据
  有效性**(HrLaneState: 截断式 —— 失效点之前的数据全部有效)。
- **频控单模型**(§5.1): 双令牌桶/熔断/停用/登录退避全部删除; 账本只剩 day 窗口 +
  last_fetch_ts(间隔基准); Retry-After 是站点明确指令, 单独存 retry_after_until。
- **新增**: 行数基线高水位 / 上波 A 档 tid 集(证据防伪 §5.3) / 种子级 missing_streak
  (失踪观察期 §3.4) / empty_confirmed_at(人工对账戳 §5.3)。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from ..infra.versioning import CURRENT_VERSIONS

# 站点文件 schema 版本: 单一事实来源是 infra.versioning.CURRENT_VERSIONS(升级链框架,
# 计划 26-09-26-0506), 这里保留原名作别名。注意本别名是**导入期取值**, 只作 dataclass 默认 /
# from_json 回填; 写盘盖章由 store 调用时动态读 CURRENT_VERSIONS(测试替换版本表才不会错位)。
SCHEMA_VERSION = CURRENT_VERSIONS["hr_site"]

# 档位(scope): A 考察中 / B 已达标 / C 未达标 / D 已免罪
LANE_SCOPE = "A"
LANE_SATISFIED = "B"
LANE_UNSATISFIED = "C"
LANE_EXEMPT = "D"
ALL_LANES = (LANE_SCOPE, LANE_SATISFIED, LANE_UNSATISFIED, LANE_EXEMPT)
#: 取数翻页的档位(D 已免罪不翻 —— 命中 D 与「未列出」同为放行, D 档没有增量信息, §4.1)
FETCH_LANES = (LANE_SCOPE, LANE_SATISFIED, LANE_UNSATISFIED)
#: 终态档位(命中即放行, 终态不可逆, §3.2)
TERMINAL_LANES = (LANE_SATISFIED, LANE_UNSATISFIED, LANE_EXEMPT)


def lane_is_satisfied(lane: str) -> bool:
    return lane == LANE_SATISFIED


def lane_is_exempt(lane: str) -> bool:
    return lane == LANE_EXEMPT


def lane_is_terminal(lane: str) -> bool:
    """终态档(B/C/D): 站点结论已定, 放行不可逆(§3.2 判定表行 2)"""
    return lane in TERMINAL_LANES


# 放行来源(verified.source)
SOURCE_EXEMPT = "absent"  # D 档(已免罪)
SOURCE_NOT_LISTED = "not-listed"  # 覆盖范围内未列出(移出/从未列出)
SOURCE_SATISFIED = "satisfied"  # B 档毕业后移出清单(B 命中时的达标结论要留住)

# 档位波次状态(§3.4 档位级数据有效性)
LANE_IDLE = ""  # 从未跑过
LANE_OK = "ok"  # 本波有效(覆盖完成或截断, 失效点之前数据有效)
LANE_FAILED = "failed"  # 本波结构性失效(表头缺失/字段缺失, 第 1 页即截断)

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
    #: 下载用种子 id(页面行内链接提取): CarPT 等站点 H&R ID 与种子 id 是**两个 id 空间**
    #: (实测 2026-09-27: H&R ID=8017746 的行, 详情链接是 details.php?id=173107),
    #: 取 .torrent 必须用种子 id; None = 站点两者同空间(标准 NexusPHP), 回落 tid。
    dl_id: Optional[int] = None
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
    #: 是否仍被站点列出(最近一次见到的位置)。v3 语义: 命中即 True; 消失的处理分档 ——
    #: A 档(考察中)失踪走观察期(missing_streak, 维持管束), 终态档消失且位置被证明才置 False
    #: 并写放行记录(终态不可逆, §3.4)。
    active: bool = True
    #: 失踪观察期计数(§3.4): 上波命中考察中、本波未重见且自身位置被覆盖 ⇒ +1;
    #: 连续 MISSING_GRACE_WAVES(service 常量) 波 ⇒ 判「移出」放行。重见即清零。
    missing_streak: int = 0

    @property
    def satisfied_verdict(self) -> Optional[bool]:
        """站点侧对「是否达标」的结论; None = 无档位结论(调用方本地兜底)。

        档位即结论: B 已达标 ⇒ 已达标 / C 未达标 ⇒ 未达标(站点明确判定考核未通过) /
        A 考察中 ⇒ 未达标(义务仍在, 管束中)。命中档位就是站点的权威结论, **不看页面数值
        字段、不回落本地**(本地值不得越级推翻站点清单结论)。「剩余达标时间」是考核窗口倒计时
        (v2.8 实证, 归零 = 考核到期而非已达标), 不参与达标推导, 只作展示。D 已免罪是放行
        (终态), 不参与达标轴(satisfied = 本地达标 ∨ 命中 B)。
        """
        if self.lane == LANE_SATISFIED:
            return True
        if self.lane in (LANE_SCOPE, LANE_UNSATISFIED):
            return False
        return None

    @property
    def satisfied_by_site(self) -> bool:
        """站点侧达标判据: 档位即结论 —— B 已达标 True, A 考察中 / C 未达标 False。"""
        return self.satisfied_verdict is True

    @property
    def done_epoch(self) -> Optional[float]:
        """完成时间的 epoch 秒; done_iso 缺失或不可解析返回 None(不猜 —— 覆盖判据依赖它)。

        naive 时刻按**本地时区**折算: 站点展示的是站点当地时刻, 与本机的时区偏差是小时级,
        对以「天」为单位的覆盖判据不构成影响。
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
            "dl_id": self.dl_id,
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
            "missing_streak": self.missing_streak,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrEntry":
        return cls(
            tid=_as_int(raw.get("tid")),
            dl_id=_opt_int(raw.get("dl_id")),
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
            missing_streak=_as_int(raw.get("missing_streak")),
        )


def _opt_int(value: Any) -> Optional[int]:
    return None if value is None else _as_int(value)


def _opt_float(value: Any) -> Optional[float]:
    return None if value is None else _as_float(value)


@dataclass(slots=True)
class HrDownloaded:
    """已取记录: 「永不重取」的持久凭据(条目消失 / 翻页遗漏 / 快照淘汰都不重下)

    v3 下载语义(§4.5): 下载 = 给清单行**登记身份**(同 tid 永不重下), 状态追踪靠 tid 读页面。
    """

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
    """「不受管束」的放行记录(§3.2 判定表行 2/3)

    v3: 放行**永续有效**(终态不可逆, §3.4) —— 不设过期、不需要每波重验; 反转必然伴随重新下载
    (本机重下 ⇒ 锚点漂移作废; 非本机重下为接受的残余风险)。锚点只用于**提前作废本实例**的
    放行(别的客户端下载本地看不见)。
    """

    infohash: str
    tid: int
    verified_ts: float = 0.0
    source: str = SOURCE_NOT_LISTED
    anchor_added_on: int = 0
    anchor_downloaded: int = 0
    anchor_completion_on: int = -1
    anchor_progress: float = 0.0

    @property
    def has_anchor_snapshot(self) -> bool:
        """记录是否带锚点快照

        全零 = **无快照可比**(早于快照落盘期的旧记录 / 写入方漏带)—— 判定侧据此不作废放行:
        行 3 的「放行永续有效」优先于「本机重下提前作废」这条辅助机制; 把 anchor_downloaded=0
        读成「downloaded 增长」会让每条无快照的放行在签发当刻被判漂移, 种子回落本地兜底。
        """
        return bool(
            self.anchor_added_on or self.anchor_downloaded or self.anchor_completion_on >= 0 or self.anchor_progress > 0
        )

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
class HrLaneState:
    """单档位最近一波的取数状态(§3.4 档位级数据有效性, 截断式)

    **失效点之前的数据全部有效**(命中照常、覆盖范围内的「未列出」可判), 之后的一概不取:
    - status=ok 且 full_depth: 覆盖证明达全深度(翻到末页 / 2.到期段停翻 —— 深处全是到期行,
      无论看到与否结论相同) ⇒ 该档对**任意位置**的缺席证明成立;
    - status=ok 且非 full_depth(1.完成时间覆盖 / 3.本地全集停翻): 缺席证明只对
      done >= cutoff_done 的位置成立(更深未翻, 不可判);
    - status=ok 且是截断(预算/解析失效点截断): 同上按位置判, 截断点之前有效;
    - status=failed: 结构性失效(第 1 页即无表头/字段缺失) ⇒ 本档无有效数据, 缺席不可判。
    """

    lane: str = ""
    wave_ts: float = 0.0  #: 本档最近一波完成取的时刻(新鲜度闸门与展示用)
    status: str = LANE_IDLE
    pages: int = 0  #: 本波本档抓取页数(含截断页)
    rows: int = 0  #: 本波本档有效行数
    cutoff_done: float = 0.0  #: 已见最深行的完成时刻(epoch; 0 = 没有位置概念)
    full_depth: bool = False  #: 覆盖证明是否达全深度(末页 / 2.到期段停翻)
    detail: str = ""  #: 截断/失效原因(展示与排障)
    #: 连续失效波数(§5.2 告警升级: 连续 3 波同档失效 → ERROR 告警疑似改版; 干净波清零)
    fail_streak: int = 0
    #: 本波该档站点声明行数(计划 26-09-29-2036 §2.3; None = 无计数 / 本波未证到 —— 键缺即降级, 绝不猜 0)
    count_claim: Optional[int] = None
    #: None = 无从对平; True/False = 实抓 rows 与声明是否对平(只有全深度档的 False 才冻批量签发)
    count_match: Optional[bool] = None
    #: 连续全深度对不平波数(对平/无计数/截断波清零); ≥3 触发 ERROR 升级(疑似口径校准错误, §2.4)
    count_mismatch_streak: int = 0

    @property
    def ok(self) -> bool:
        return self.status == LANE_OK

    def to_json(self) -> Dict[str, Any]:
        return {
            "lane": self.lane,
            "wave_ts": self.wave_ts,
            "status": self.status,
            "pages": self.pages,
            "rows": self.rows,
            "cutoff_done": self.cutoff_done,
            "full_depth": self.full_depth,
            "detail": self.detail,
            "fail_streak": self.fail_streak,
            "count_claim": self.count_claim,
            "count_match": self.count_match,
            "count_mismatch_streak": self.count_mismatch_streak,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrLaneState":
        # !count_claim/count_match 必须显式判空(计划 §2.3 陷阱 T1): 旧站点文件没有这些键,
        # raw.get 返回 None —— 走 _as_int 缺省路径会被折成 0, 全部存量档案瞬间变「声明 0 行」
        # ⇒ 全站假 mismatch ⇒ 批量签发永久冻结。None 语义必须原样穿过。
        claim = raw.get("count_claim")
        match = raw.get("count_match")
        return cls(
            lane=str(raw.get("lane") or ""),
            wave_ts=_as_float(raw.get("wave_ts")),
            status=str(raw.get("status") or LANE_IDLE),
            pages=_as_int(raw.get("pages")),
            rows=_as_int(raw.get("rows")),
            cutoff_done=_as_float(raw.get("cutoff_done")),
            full_depth=bool(raw.get("full_depth")),
            detail=str(raw.get("detail") or ""),
            fail_streak=_as_int(raw.get("fail_streak")),
            count_claim=None if claim is None else _as_int(claim),
            count_match=None if match is None else bool(match),
            count_mismatch_streak=_as_int(raw.get("count_mismatch_streak")),
        )


@dataclass(slots=True)
class HrWaveMeta:
    """最近一波的波次元数据(波次引擎 §4 的状态面; 取代 v2 的 HrRefreshMeta 覆盖证明语义)"""

    wave_ts: float = 0.0  #: 最近一波完成的时刻
    healthy_ts: float = 0.0  #: 最近「健康波」时刻(至少一档有有效数据) —— 新鲜度闸门基准
    lanes: Dict[str, HrLaneState] = field(default_factory=dict)  # 档位 -> 状态
    #: 本波是否允许批量签发「未列出」放行(三档全有有效数据 + 防伪通过, §5.3)
    releases_enabled: bool = False
    zero_rows: bool = False  #: 本波全部档位 0 行(结构完好) —— 不签发放行, 除非人工确认戳
    #: A 档流转守恒观测(§5.3): 上波 A 档行在本波 A/B/C 的留存率(0~1; -1 = 无上波 A 行不适用)
    retention_ratio: float = -1.0
    retention_ok: bool = True
    prev_a_tids: Dict[int, str] = field(default_factory=dict)  # 上波 A 档 tid -> infohash(守恒校验用)
    notes: str = ""

    def to_json(self) -> Dict[str, Any]:
        return {
            "wave_ts": self.wave_ts,
            "healthy_ts": self.healthy_ts,
            "lanes": {
                k: v.to_json()
                for k, v in self.lanes.items()
            },
            "releases_enabled": self.releases_enabled,
            "zero_rows": self.zero_rows,
            "retention_ratio": self.retention_ratio,
            "retention_ok": self.retention_ok,
            "prev_a_tids": {
                str(k): v
                for k, v in self.prev_a_tids.items()
            },
            "notes": self.notes,
        }

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrWaveMeta":
        return cls(
            wave_ts=_as_float(raw.get("wave_ts")),
            healthy_ts=_as_float(raw.get("healthy_ts")),
            lanes={
                str(k): HrLaneState.from_json(v)
                for k, v in (raw.get("lanes") or {}).items()
            },
            releases_enabled=bool(raw.get("releases_enabled")),
            zero_rows=bool(raw.get("zero_rows")),
            retention_ratio=_as_float(raw.get("retention_ratio"), -1.0),
            retention_ok=bool(raw.get("retention_ok", True)),
            prev_a_tids={
                _as_int(k): str(v)
                for k, v in (raw.get("prev_a_tids") or {}).items()
            },
            notes=str(raw.get("notes") or ""),
        )


@dataclass(slots=True)
class HrRateLedger:
    """频控账本(单模型, §5.1): 日额窗口 + 上次请求时刻(最小间隔基准)

    页面与 .torrent 下载统一记同一本账(不再有页面/下载双桶); 幂等靠窗口键 —— 重启不重置、
    重放不重复消耗。
    """

    day_window: str = ""  # 自然日窗口键(如 "2026-09-28"; 变化即视为 0)
    day_count: int = 0  # 本自然日已发请求数(页面 + 下载合计)
    last_fetch_ts: float = 0.0  # 上次请求发出时刻(下一次间隔门槛的基准)

    def to_json(self) -> Dict[str, Any]:
        return {"day_window": self.day_window, "day_count": self.day_count, "last_fetch_ts": self.last_fetch_ts}

    @classmethod
    def from_json(cls, raw: Dict[str, Any]) -> "HrRateLedger":
        return cls(
            day_window=str(raw.get("day_window") or ""),
            day_count=_as_int(raw.get("day_count")),
            last_fetch_ts=_as_float(raw.get("last_fetch_ts")),
        )


@dataclass(slots=True)
class HrSiteData:
    """一个站点的全部账号级状态(站点文件的内容)"""

    schema_version: int = SCHEMA_VERSION
    revision: int = 0
    fetched_at: float = 0.0  #: 上次**尝试**取数的时刻(失败也会前进 —— "上次动过是什么时候")
    expires_at: float = 0.0  #: 数据复用窗口截止(多实例: 别的实例刚抓过就不再抓)
    writer_instance: str = ""
    writer_heartbeat: float = 0.0
    index: Dict[int, HrEntry] = field(default_factory=dict)
    downloaded: Dict[int, HrDownloaded] = field(default_factory=dict)
    fails: Dict[int, HrDlFail] = field(default_factory=dict)
    verified: Dict[str, HrVerified] = field(default_factory=dict)  # infohash -> 放行记录
    wave: HrWaveMeta = field(default_factory=HrWaveMeta)
    rate: HrRateLedger = field(default_factory=HrRateLedger)
    #: 人工对账戳(§5.3): --hr-confirm-empty / WebUI 按钮写入; 零行波凭它才可签发放行;
    #: 清单再现任何非零行自动清除。
    empty_confirmed_at: float = 0.0
    #: 站点明确要求的等待时刻(Retry-After, §5.2): 之前零请求; 不是退避机制 —— 是站点指令
    retry_after_until: float = 0.0

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
            "wave": self.wave.to_json(),
            "rate": self.rate.to_json(),
            "empty_confirmed_at": self.empty_confirmed_at,
            "retry_after_until": self.retry_after_until,
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
            wave=HrWaveMeta.from_json(raw.get("wave") or {}),
            rate=HrRateLedger.from_json(raw.get("rate") or {}),
            empty_confirmed_at=_as_float(raw.get("empty_confirmed_at")),
            retry_after_until=_as_float(raw.get("retry_after_until")),
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
