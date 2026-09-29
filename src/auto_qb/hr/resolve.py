"""判定收口(v3 四行判定表, 计划 26-09-28-1932 §3): 受管束 / 放行 / 无证据本地兜底。

**站点数据是权威数据**, 优先级用户 2026-09-28 定稿:
- **命中考察中(A) → 管束(绝对权威)** —— 本机此刻删了它前功尽弃真吃 H&R; 本地达标与否都管
  (本地达标只说明快转 B 了), 管到站点把它转出为止。
- **终态档 B/C/D 与移出未列出 → 放行(终态不可逆)** —— 站点结论已定, 管束改变不了任何事;
  放行一经签发永续有效, 反转必然伴随重新下载(本机重下由锚点漂移作废)。
- **无有效站点证据 → 本地判据兜底(行 4, 硬编码无配置)** —— 「本地做种达到要求就可视为完成,
  在线核实只是保障准确」: 达标放行 / 未达标管束。本地判据在调用方(它才有完整本地字段),
  本模块以 `NO_EVIDENCE` 身份交回。

被删除的旧概念: unknown_policy / mode 分叉 / suspended 回落 / 超龄豁免(completed_age_limit、
auto_age_limit) / 豁免 B(seeding_exempt_ratio) —— 前四者并入行 4, 做种超额线(常量 3×,
§3.3)只作用于取数侧对象集, 不构成判定身份(超额种子被动命中考察中仍管束, 网站绝对权威)。

本模块是**纯函数 + 不可变视图**: 视图由取数线程整体替换引用, Web 线程与主循环并发只读安全。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Mapping, Optional, Sequence

from .model import (
    CHANNEL_DISABLED,
    LANE_EXEMPT,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrEntry,
    HrVerified,
)


class HrIdentity(str, Enum):
    """种子的 HR 身份(v3 三态; 四行判定表逐行落身)"""

    HR = "hr"  # 受管束(行 1: 命中考察中 —— 含本地已达标者; 判定表行 1)
    RELEASED = "released_non_hr"  # 放行(行 2: 终态档命中 / 行 3: 覆盖范围内未列出)
    NO_EVIDENCE = "no_evidence"  # 行 4: 无有效站点证据 ⇒ 调用方本地判据兜底(达标放行/未达标管束)


@dataclass(frozen=True, slots=True)
class HrAnchor:
    """本实例的下载锚点 —— **辅助信号, 不是放行的充分条件**。

    它只能提前让**本实例**的放行失效(本实例二次下载 / 文件被删重下 / 删种重加), 覆盖不到
    别的客户端; 放行判定 = 站点终态事实 + 锚点未漂移(本实例辅助)。
    seeding_time: 本实例做种时长(秒, qB 快照) —— 取数侧超额线(常量 3×, §3.3)的判据;
    0 = 未知。name: 本地种子名称(取数侧 B/C/D 行宽泛名称粗配要用, §4.5 D1)。
    """

    added_on: int = 0
    downloaded: int = 0
    completion_on: int = -1
    progress: float = 0.0
    seeding_time: int = 0
    name: str = ""

    def drift_reason(self, ver: HrVerified) -> str:
        """与放行记录里的锚点比对, 漂移返回人话原因, 未漂移返回空串"""
        if not ver.has_anchor_snapshot:
            return ""  # 无快照可比: 不凭空判漂移(见 HrVerified.has_anchor_snapshot)
        if ver.anchor_added_on and self.added_on != ver.anchor_added_on:
            return "added_on 变化(删种重加 / 重新添加)"
        if self.downloaded < ver.anchor_downloaded:
            return "downloaded 变小(文件被删重下)"
        if self.downloaded > ver.anchor_downloaded:
            return "downloaded 增长(本实例二次下载)"
        if ver.anchor_completion_on >= 0 and self.completion_on != ver.anchor_completion_on:
            return "completion_on 变化"
        if ver.anchor_progress > 0 and self.progress + 1e-9 < ver.anchor_progress:
            return "progress 退回(重新下载)"
        return ""


@dataclass(frozen=True, slots=True)
class HrResolution:
    """单个 infohash 的判定结果(内部; judge_record 对双 hash 取保守合并)"""

    identity: HrIdentity
    reason: str = ""
    released_src: str = ""


@dataclass(frozen=True, slots=True)
class HrSiteFacts:
    """命中那一行的**站点侧展示值**(站点侧 / 本地两套值都显示, 便于对账)

    从 HrEntry 拷成不可变对象: 视图里的 entry 是取数线程写入时复用的**可变**行对象,
    直接把它带进判定结果会让读数方看到半新半旧的一行(映射不可变 ≠ 行不可变)。
    """

    lane: str = ""
    need_seed_seconds: Optional[int] = None
    remain_seconds: Optional[int] = None
    ratio: Optional[float] = None
    downloaded_bytes: Optional[int] = None

    @classmethod
    def of(cls, entry: HrEntry) -> "HrSiteFacts":
        return cls(
            lane=entry.lane,
            need_seed_seconds=entry.need_seed_seconds,
            remain_seconds=entry.remain_seconds,
            ratio=entry.ratio,
            downloaded_bytes=entry.downloaded_bytes,
        )


@dataclass(frozen=True, slots=True)
class HrJudgement:
    """四个消费点最终要的语义: 身份 + 达标结论 + 依据 + 站点

    `identity is NO_EVIDENCE` = 判定表行 4: 站点无话可说, `is_hr` 与达标结论由**调用方本地
    判据**兜底(达标放行 / 未达标管束; 硬编码无配置) —— 本模块没有本地字段, 不代答。
    `site_satisfied`: 站点侧对「是否达标」的**明确**结论; None = 站点没给 ⇒ 调用方本地兜底。
    `facts`: 命中行的站点侧展示值(未命中 = None)。
    """

    identity: HrIdentity
    reason: str = ""
    site_satisfied: Optional[bool] = None
    site: str = ""
    facts: Optional[HrSiteFacts] = None
    #: 放行依据: SOURCE_EXEMPT = D 档已免罪 / SOURCE_SATISFIED = B 毕业移出 / 空 = 缺席式放行
    released_src: str = ""

    @property
    def is_hr(self) -> bool:
        """「是否按 HR 对待」的布尔语义(打标 / 规则 / 表达式 / 视图共用)

        !NO_EVIDENCE 恒 False —— 行 4 的管束/放行由调用方按本地判据现算(hr_managed),
        本属性只表达**站点侧**的明确结论。
        """
        return self.identity is HrIdentity.HR

    @property
    def state_text(self) -> str:
        if self.identity is HrIdentity.HR:
            return "受管束"
        if self.identity is HrIdentity.RELEASED:
            return "已核实·放行"
        return "无站点证据(本地兜底)"


@dataclass(frozen=True, slots=True)
class HrSiteView:
    """一个站点的**不可变**判定视图(取数线程整体替换引用; 读者只读)

    lane_a: 考察中命中的 infohash -> 页面行(行 1 管束的正证据)
    lane_terminal: 终态档(B/C/D)命中的 infohash -> 页面行(行 2 放行)
    verified: 放行记录 infohash -> 记录(行 3; 永续有效, 终态不可逆)
    healthy_ts: 最近健康波时刻(新鲜度闸门: added_on 晚于它 ⇒ 行 4)
    """

    site: str
    listing: str = "list"  # "list" 清单型 | "none" 全站型(不取数, 判定恒行 4 ⇒ judge 返回 None)
    revision: int = 0
    channel_state: str = CHANNEL_DISABLED
    generated_at: float = 0.0
    healthy_ts: float = 0.0
    lane_a: Mapping[str, HrEntry] = field(default_factory=dict)
    lane_terminal: Mapping[str, HrEntry] = field(default_factory=dict)
    verified: Mapping[str, HrVerified] = field(default_factory=dict)
    notes: str = ""

    @classmethod
    def empty(cls, site: str) -> "HrSiteView":
        return cls(site=site)

    @property
    def has_evidence(self) -> bool:
        """站点侧是否**至少有一条可判数据**(命中 / 放行记录)

        一个都没有时任何种子都落行 4 —— 调用方本地兜底(与「站点未接入」同效)。
        """
        return bool(self.lane_a or self.lane_terminal or self.verified)


@dataclass(frozen=True, slots=True)
class HrViewSet:
    """全部站点的视图集合(同样整体替换引用)"""

    views: Mapping[str, HrSiteView] = field(default_factory=dict)
    generated_at: float = 0.0

    @classmethod
    def empty(cls) -> "HrViewSet":
        return cls()

    def get(self, site: str) -> Optional[HrSiteView]:
        return self.views.get(site)


def resolve_identity(
    view: HrSiteView,
    infohash: str,
    *,
    anchor=None,
    now: float = 0.0,
) -> HrResolution:
    """按 (站点, infohash) 走四行判定表(§3.1, 按序求值先命中先出)。

    行 1: 命中考察中(A) → 管束(含失踪观察期未出期的种子 —— 它们的 A 档条目仍 active)。
    行 2: 命中终态档(B/C/D) → 放行(终态不可逆)。
    行 3: 放行记录(覆盖范围内未列出 / D 免罪) → 放行; 本实例锚点漂移 = 本机重下 ⇒ 放行作废,
          落行 4(本地兜底会把未达标种子管住 —— 保守方向)。
    行 4: 无有效站点证据 → NO_EVIDENCE(调用方本地判据兜底)。
    """
    entry = view.lane_a.get(infohash)
    if entry is not None:
        remain = f", 还差 {entry.remain_seconds // 3600}h" if entry.remain_seconds else ""
        return HrResolution(HrIdentity.HR, f"清单命中·考察中(档位 A{remain})")

    entry = view.lane_terminal.get(infohash)
    if entry is not None:
        if entry.lane == LANE_SATISFIED:
            return HrResolution(HrIdentity.RELEASED, "清单命中·已达标(B, 终态放行)", released_src=SOURCE_SATISFIED)
        if entry.lane == LANE_UNSATISFIED:
            return HrResolution(HrIdentity.RELEASED, "清单命中·未达标(C, 考核结论已定, 终态放行)")
        return HrResolution(HrIdentity.RELEASED, "清单命中·已免罪(D, 终态放行)", released_src=SOURCE_EXEMPT)

    # 行 3: 放行记录(永续有效 —— 不存在「过期」; 只被锚点漂移与重新命中作废)
    ver = view.verified.get(infohash)
    if ver is not None:
        if anchor is not None:
            drift = anchor.drift_reason(ver)
            if drift:
                return HrResolution(HrIdentity.NO_EVIDENCE, f"锚点漂移(本机重下, 放行作废): {drift}")
        src = {
            SOURCE_EXEMPT: "D 档已免罪",
            SOURCE_SATISFIED: "B 档毕业后移出",
        }.get(ver.source, "覆盖范围内未列出")
        return HrResolution(HrIdentity.RELEASED, f"放行记录({src}, 依据 {ver.verified_ts:.0f})", released_src=ver.source)

    # 行 4: 无有效站点证据(硬编码无配置)
    return HrResolution(HrIdentity.NO_EVIDENCE, view.notes or "无有效站点证据(本地判据兜底)")


def judge_record(
    view: Optional[HrSiteView],
    infohashes: Sequence[str],
    *,
    anchor=None,
    now: float = 0.0,
) -> Optional["HrJudgement"]:
    """给 TorrentRecord 用的收口判定(四个消费点唯一入口; 读取时现算)。

    返回 None 表示**本模块不适用**(站点未接入 hr_check / 全站型 listing=none ⇒ 恒行 4 本地
    兜底, 与未接入同效)⇒ 调用方走既有本地字段逻辑 —— 零静默变更的闸门。
    返回 NO_EVIDENCE = 判定表行 4 命中: 调用方按本地判据兜底(达标放行 / 未达标管束)。

    infohash 传 (v1, v2): 命中是站点侧事实, 两个键哪个命中都算命中; 取两者中**更保守**的结论
    (管束 > 放行 > 无证据)。同为放行时取依据更强者(D 免罪 > B > 缺席); 同为管束时取
    「剩余时间更少」的行展示(无判定差异, 纯展示)。
    """
    if view is None or view.listing == "none":
        return None
    keys = [h for h in infohashes if h]
    if not keys:
        return HrJudgement(identity=HrIdentity.NO_EVIDENCE, reason="身份缺位(infohash 未回填)", site=view.site)
    best: Optional[HrResolution] = None
    best_key = keys[0]
    best_entry: Optional[HrEntry] = None
    for h in keys:
        res = resolve_identity(view, h, anchor=anchor, now=now)
        entry = view.lane_a.get(h) or view.lane_terminal.get(h)
        if best is None or _rank(res) > _rank(best):
            best, best_key, best_entry = res, h, entry
    assert best is not None
    return HrJudgement(
        identity=best.identity,
        reason=best.reason,
        site_satisfied=best_entry.satisfied_verdict if best_entry is not None else None,
        site=view.site,
        facts=HrSiteFacts.of(best_entry) if best_entry is not None else None,
        released_src=best.released_src,
    )


# 保守合并序(两个 infohash 取更保守者): 管束 > 放行 > 无证据。
# 宁可多想一个, 不可漏一个 —— 漏 HR 的代价远大于多打一个标签。
_RANK = {HrIdentity.HR: 3, HrIdentity.RELEASED: 2, HrIdentity.NO_EVIDENCE: 1}


def _rank(res: HrResolution) -> int:
    return _RANK.get(res.identity, 0)


# ---------------- 删除安全档位 × 来源档位(WEB UI 展示单点) ----------------
# views.py 与 CLI 报告共用; 前端只做 token -> 徽标文字映射, 不重算判定。

SAFETY_DANGER = "danger"  # 不能删(进行中): 考察中, 删除可能吃 H&R
SAFETY_FAILED = "failed"  # 不能删(终态): 考核期已过仍未达标, 结果已成立 —— 独立醒目红色
SAFETY_SAFE = "safe"  # 可删: 义务已了
SAFETY_WARNING = "warning"  # 注意: 本地未达标且疑似辅种 —— 可能有义务也可能原机已完成, 黄档警示不拦删
SAFETY_NONE = "none"  # 不适用: 站点未配 HR / 命中排除表(调用方组装层短路成空串, 本函数不再产出)

SRC_SITE_SCOPE = "site_scope"  # 在线·考察中(清单命中档位 A)
SRC_SITE_SATISFIED = "site_satisfied"  # 在线·已达标(档位 B)
SRC_SITE_UNSATISFIED = "site_unsatisfied"  # 在线·未达标(档位 C, 终态)
SRC_SITE_RELEASED = "site_released"  # 在线·已核实(放行记录 = 覆盖范围内未列出)
SRC_SITE_EXEMPT = "site_exempt"  # 在线·已免罪(D 档终态)
SRC_LOCAL = "local"  # 本地判据(行 4 无有效站点证据 / 站点未接入, 按本地字段)


@dataclass(frozen=True, slots=True)
class HrSafetyDisplay:
    """删除安全档位的展示三元组(safety 决定颜色, src 决定来源徽标, text 是全 UI 唯一的人话口径)"""

    safety: str
    src: str
    text: str


def _safety_display_dataclass(safety: str, src: str, text: str) -> "HrSafetyDisplay":
    return HrSafetyDisplay(safety=safety, src=src, text=text)


def safety_display(judged: Optional[HrJudgement], *, triggered: bool, satisfied: bool) -> HrSafetyDisplay:
    """由判定结果派生「删除安全档位 × 来源档位」—— 不新造判定, 只转译既有结论。

    `judged is None` = 站点未接入 / 全站型 / 调用方回落(judge_record 返回 None), NO_EVIDENCE(行 4)
    同落本地判据 —— 站点无话可说时本地说了算, 两态走同一「satisfied × triggered」三分
    (计划 26-09-30-0559 §5): 达标 ⇒ safe「本地·达标」; 未达标+触发 ⇒ danger「本地·未达标」;
    未达标+未触发 ⇒ warning「本地·未达标(疑似辅种)」(转移种常态, 可能负有义务也可能原机
    已完成, 黄档警示不拦删)。命中行的档位即结论: A 考察中 ⇒ 不能删(danger);
    C 未达标 ⇒ 不能删(failed 红, 终态); B 已达标 / D 已免罪 / 放行记录 ⇒ 可删。
    """
    if judged is None or judged.identity is HrIdentity.NO_EVIDENCE:
        if satisfied:
            return _safety_display_dataclass(SAFETY_SAFE, SRC_LOCAL, "本地·达标")
        if triggered:
            return _safety_display_dataclass(SAFETY_DANGER, SRC_LOCAL, "本地·未达标")
        return _safety_display_dataclass(SAFETY_WARNING, SRC_LOCAL, "本地·未达标(疑似辅种)")
    if judged.identity is HrIdentity.RELEASED:
        if judged.facts is not None:
            lane = judged.facts.lane
            if lane == LANE_SATISFIED:
                return _safety_display_dataclass(SAFETY_SAFE, SRC_SITE_SATISFIED, "在线·已达标")
            if lane == LANE_UNSATISFIED:
                return _safety_display_dataclass(SAFETY_FAILED, SRC_SITE_UNSATISFIED, "在线·未达标(终态)")
            if lane == LANE_EXEMPT:
                return _safety_display_dataclass(SAFETY_SAFE, SRC_SITE_EXEMPT, "在线·已免罪")
        if judged.released_src == SOURCE_EXEMPT:
            return _safety_display_dataclass(SAFETY_SAFE, SRC_SITE_EXEMPT, "在线·已免罪")
        if judged.released_src == SOURCE_SATISFIED:
            return _safety_display_dataclass(SAFETY_SAFE, SRC_SITE_SATISFIED, "在线·已达标(毕业)")
        return _safety_display_dataclass(SAFETY_SAFE, SRC_SITE_RELEASED, "在线·已核实，安全放行")
    # identity == HR: 命中考察中(行 1 管束)
    return _safety_display_dataclass(SAFETY_DANGER, SRC_SITE_SCOPE, "在线·考察中")


def build_site_view(
    site: str,
    listing: str,
    data,
    *,
    channel_state: str,
    generated_at: float,
) -> HrSiteView:
    """由站点数据构造不可变视图(取数线程在数据实质变化时调用一次, 然后整体替换引用)。

    只把**判定需要的**东西放进视图: 考察中命中(lane_a)与终态命中(lane_terminal)按 infohash
    索引, 放行记录原样带上。D 档命中也进 lane_terminal(终态放行, §3.2 行 2)。
    """
    lane_a: Dict[str, HrEntry] = {}
    lane_terminal: Dict[str, HrEntry] = {}
    for entry in data.index.values():
        if not entry.active:
            continue
        target = lane_a if entry.lane == LANE_SCOPE else (
            lane_terminal if entry.lane in (LANE_SATISFIED, LANE_UNSATISFIED, LANE_EXEMPT) else None
        )
        if target is None:
            continue
        for h in (entry.infohash_v1, entry.infohash_v2):
            if h:
                target.setdefault(h, entry)
    return HrSiteView(
        site=site,
        listing=listing,
        revision=data.revision,
        channel_state=channel_state,
        generated_at=generated_at,
        healthy_ts=data.wave.healthy_ts,
        lane_a=lane_a,
        lane_terminal=lane_terminal,
        verified=dict(data.verified),
        notes=data.wave.notes,
    )


__all__ = [
    "HrAnchor",
    "HrIdentity",
    "HrJudgement",
    "HrResolution",
    "HrSafetyDisplay",
    "HrSiteFacts",
    "HrSiteView",
    "HrViewSet",
    "SAFETY_DANGER",
    "SAFETY_FAILED",
    "SAFETY_NONE",
    "SAFETY_SAFE",
    "SAFETY_WARNING",
    "SRC_LOCAL",
    "SRC_SITE_EXEMPT",
    "SRC_SITE_RELEASED",
    "SRC_SITE_SATISFIED",
    "SRC_SITE_SCOPE",
    "SRC_SITE_UNSATISFIED",
    "build_site_view",
    "judge_record",
    "resolve_identity",
    "safety_display",
]
