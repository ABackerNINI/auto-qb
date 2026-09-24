"""判定收口(计划 §9): 受管束 / 已核实不受管束 / 未核实, 外加 qB 侧的**超龄豁免**。

**站点数据是权威数据**: 接入 hr_check 的站点「是否触发 / 是否达标」一律看站点侧, 本地 qB 字段
降为兜底与展示 —— 否则转移种子(A 客户端下载 → B 客户端保种, B 的 downloaded=0 被当辅种)
与多客户端场景会直接漏管。

不变量(两个方向的取舍):
- **不漏 HR 是首要**: unknown_policy 默认 hr + 新鲜度闸门 + 不完备刷新不产生放行 +
  放行有效期(verified_ttl)。
- **安全放行** 只由「完整核实过、且不在清单里」产生, 而不是「没看见就放行」。
- **超龄豁免是唯一由本地事实单方面给出的「不受管束」**: 完成时间超过 completed_age_limit 的
  种子, 用户已显式声明「不再核实、不再管束」—— 它优先于站点侧一切结论(含清单命中),
  且只在站点级显式配置了该键时存在(默认 0 = 永不出现, 零静默变更)。

本模块是**纯函数 + 不可变视图**: 视图由取数线程整体替换引用(项目先例: 搜索索引整体替换引用),
Web 线程与主循环并发只读安全; 「是否还在有效期」这类时间敏感判定在**读取时现算**,
不需要为时间流逝重发布视图。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Mapping, Optional, Sequence

from .model import (
    CHANNEL_DISABLED,
    LANE_EXEMPT,
    SOURCE_EXEMPT,
    HrEntry,
    HrVerified,
)

# unknown_policy 取值
POLICY_HR = "hr"
POLICY_NOT_HR = "not-hr"


class HrIdentity(str, Enum):
    """种子的 HR 身份(三态 + qB 侧超龄豁免)"""

    HR = "hr"  # 受管束(站点清单命中; 或 mode=all 下的未核实)
    VERIFIED_NON_HR = "verified_non_hr"  # 已核实不受管束(安全放行)
    UNKNOWN = "unknown"  # 未核实
    EXEMPT = "exempt"  # 超龄豁免(完成时间超过 completed_age_limit; 见模块 docstring)


@dataclass(frozen=True, slots=True)
class HrAnchor:
    """本实例的下载锚点 —— **辅助信号, 不是放行的充分条件**。

    它只能提前让**本实例**的放行失效(本实例二次下载 / 文件被删重下 / 删种重加), 覆盖不到
    别的客户端; 故放行判定 = 「刷新背书(必需) + 锚点未漂移(本实例辅助)」。
    """

    added_on: int = 0
    downloaded: int = 0
    completion_on: int = -1
    progress: float = 0.0

    def drift_reason(self, ver: HrVerified) -> str:
        """与放行记录里的锚点比对, 漂移返回人话原因, 未漂移返回空串"""
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
    """判定结果: 三态 + 依据(展示与审计用) + 是否「恒受管束」(policy 不适用)"""

    identity: HrIdentity
    reason: str = ""
    forced: bool = False

    def is_hr(self, unknown_policy: str = POLICY_HR) -> bool:
        """落到「是否按 HR 对待」的布尔语义(四个消费点最终要的就是它)

        未核实时按 unknown_policy; 但 forced(新鲜度闸门)恒受管束, **不可被 policy 绕过**。
        超龄豁免恒为 False —— 它不经过 policy, 是用户对这类种子的显式声明。
        """
        if self.identity in (HrIdentity.HR, ):
            return True
        if self.identity in (HrIdentity.VERIFIED_NON_HR, HrIdentity.EXEMPT):
            return False
        return self.forced or unknown_policy != POLICY_NOT_HR


@dataclass(frozen=True, slots=True)
class HrSiteFacts:
    """命中那一行的**站点侧展示值**(计划 §9: 站点侧 / 本地两套值都显示, 便于对账)

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
    """四个消费点最终要的语义(计划 §9): 身份 + 达标结论 + 依据 + 站点

    `is_hr`: 已把 `unknown_policy` 与本实例锚点算进去的最终布尔(打标 / 规则 / 表达式 / 视图共用)。
    `site_satisfied`: 站点侧对「是否达标」的**明确**结论; None = 站点没给 ⇒ 调用方本地兜底。
    `facts`: 命中行的站点侧展示值(未命中 = None); `state_text`: 三态的中文说法单一来源。
    """

    identity: HrIdentity
    is_hr: bool
    reason: str = ""
    site_satisfied: Optional[bool] = None
    site: str = ""
    facts: Optional[HrSiteFacts] = None

    @property
    def state_text(self) -> str:
        if self.identity is HrIdentity.HR:
            return "受管束"
        if self.identity is HrIdentity.VERIFIED_NON_HR:
            return "已核实·安全放行"
        if self.identity is HrIdentity.EXEMPT:
            return "超龄豁免"
        return "未核实"


@dataclass(frozen=True, slots=True)
class HrSiteView:
    """一个站点的**不可变**判定视图(取数线程整体替换引用; 读者只读)

    by_infohash: 清单命中(A/B/C)的 infohash -> 页面行
    verified: 放行记录 infohash -> 记录
    complete: 覆盖证明是否成立(不完备刷新不产生新放行)
    channel_state: ok / silent / disabled(通道静默要告警)
    """

    site: str
    mode: str = "off"
    revision: int = 0
    complete: bool = False
    last_success_ts: float = 0.0
    verified_ttl: float = 0.0
    refresh_interval: float = 0.0
    channel_state: str = CHANNEL_DISABLED
    generated_at: float = 0.0
    by_infohash: Mapping[str, HrEntry] = field(default_factory=dict)
    verified: Mapping[str, HrVerified] = field(default_factory=dict)
    notes: str = ""

    @classmethod
    def empty(cls, site: str, mode: str = "off") -> "HrSiteView":
        return cls(site=site, mode=mode)

    def backed_until(self, backed_ts: float) -> float:
        """一次刷新背书的有效截止时刻 = backed_ts + verified_ttl"""
        return backed_ts + self.verified_ttl if self.verified_ttl > 0 else backed_ts

    def freshness_ok(self, backed_ts: float, now: float) -> bool:
        return backed_ts > 0 and now <= self.backed_until(backed_ts)

    @property
    def has_lookup_keys(self) -> bool:
        """站点侧是否**至少有一个可查的键**(清单命中的 infohash 或放行记录)

        一个都没有时, 这个视图对判定没有任何信息量 —— 任何种子都只会得到「未核实」。
        它的成因通常是「索引还没回填出第一个 infohash」(取数通道刚接通 / 下载被饿死),
        详见 `judge_record` 里对应那道闸门。
        """
        return bool(self.by_infohash or self.verified)


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
    view: Optional[HrSiteView],
    infohash: str,
    *,
    anchor: Optional[HrAnchor] = None,
    now: float = 0.0,
) -> HrResolution:
    """按 (站点, infohash) 判三态 —— 完整判定表见计划 §9。

    调用前提: `view.mode != "off"`(off 站点走既有逻辑, 不进入本函数)。
    """
    if view is None or view.mode == "off":
        return HrResolution(HrIdentity.UNKNOWN, "站点未接入 hr_check")

    if not infohash:
        return HrResolution(HrIdentity.UNKNOWN, "身份缺位(infohash 未回填)")

    entry = view.by_infohash.get(infohash)
    if entry is not None:
        return HrResolution(HrIdentity.HR, f"清单命中(档位 {entry.lane})")

    ver = view.verified.get(infohash)
    if ver is not None:
        if anchor is not None:
            drift = anchor.drift_reason(ver)
            if drift:
                return HrResolution(HrIdentity.UNKNOWN, f"锚点漂移: {drift}")
        if view.freshness_ok(ver.verified_ts, now):
            src = "D 档已免罪" if ver.source == SOURCE_EXEMPT else "完整刷新未列出"
            return HrResolution(HrIdentity.VERIFIED_NON_HR, f"已核实放行({src}, 依据刷新 {ver.verified_ts:.0f})")
        return HrResolution(HrIdentity.UNKNOWN, "放行已过期(超 verified_ttl 无新刷新背书)")

    # 没有逐种放行记录: 由「完整刷新 + 未列出」当场推出结论(反应式, 索引天然滞后于下载)
    if view.complete and view.last_success_ts > 0:
        if anchor is not None and anchor.added_on > view.last_success_ts:
            # 新鲜度闸门: 该种子不可能出现在那次清单里 ⇒ 恒受管束, 不可被 unknown_policy 绕过
            return HrResolution(
                HrIdentity.UNKNOWN,
                "新鲜度闸门(本实例 added_on 晚于最近一次完整刷新)",
                forced=True,
            )
        if view.freshness_ok(view.last_success_ts, now):
            return HrResolution(
                HrIdentity.VERIFIED_NON_HR,
                f"完整刷新未列出(依据 {view.last_success_ts:.0f})",
            )
        return HrResolution(HrIdentity.UNKNOWN, "放行已过期(通道静默 / 未获新刷新背书)")

    if view.mode == "all":
        return HrResolution(HrIdentity.HR, "mode=all 且未核实 ⇒ 恒受管束")

    return HrResolution(HrIdentity.UNKNOWN, view.notes or "刷新不完备 / 从未成功刷新")


# 判定优先级(两个 infohash 取更保守者): 清单命中 > 恒受管束 > 已核实放行 > 未核实。
# 宁可多想一个, 不可漏一个 —— 漏 HR 的代价远大于多打一个标签。
_RANK_HR = 3
_RANK_FORCED = 2
_RANK_RELEASED = 1
_RANK_UNKNOWN = 0


def _rank(res: HrResolution) -> int:
    if res.identity is HrIdentity.HR:
        return _RANK_HR
    if res.forced:
        return _RANK_FORCED
    if res.identity in (HrIdentity.VERIFIED_NON_HR, HrIdentity.EXEMPT):
        return _RANK_RELEASED
    return _RANK_UNKNOWN


def judge_record(
    view: Optional[HrSiteView],
    infohashes: Sequence[str],
    *,
    anchor: Optional[HrAnchor] = None,
    now: float = 0.0,
    unknown_policy: str = POLICY_HR,
    completed_age_limit: float = 0.0,
) -> Optional[HrJudgement]:
    """给 TorrentRecord 用的收口判定(四个消费点唯一入口; 读取时现算)。

    返回 None 表示**本模块不适用**(站点未接入 / mode=off / 站点侧一个可查键都没有)
    ⇒ 调用方走既有本地字段逻辑 —— 这就是「零静默变更」的闸门: 没显式配 `hr_check` 的站点,
    行为一个字都不变。

    infohash 传 (v1, v2): 命中清单是站点侧事实, 两个键哪个命中都算命中(v2-only 页面同样成立);
    取两者中**更保守**的结论(命中 > 恒受管束 > 已放行 > 未核实)。

    `completed_age_limit` > 0 时(站点级配置, 记录侧从 tracker_conf 带进来): 锚点里**本地完成
    时刻**超过该线的种子直接超龄豁免 —— 不查索引、不看 unknown_policy、也**压过清单命中**
    (站点真还在管的超龄种子会漏 HR, 这是配置者显式接受的风险, 见模块 docstring「不变量」)。
    它排在「无可查键回落本地」的闸门**之前**: 豁免是 qB 侧事实, 不依赖站点索引建到哪了。
    """
    if view is None or view.mode == "off":
        return None
    if completed_age_limit > 0 and anchor is not None and anchor.completion_on > 0 and \
            now - anchor.completion_on >= completed_age_limit:
        age_days = (now - anchor.completion_on) / 86400
        return HrJudgement(
            identity=HrIdentity.EXEMPT,
            is_hr=False,
            reason=f"超龄豁免(本地完成于 {age_days:.0f} 天前, 超过豁免线 {completed_age_limit / 86400:.0f} 天, "
            "不再在线核实)",
            site=view.site,
        )
    if view.mode != "all" and not view.has_lookup_keys:
        # ❗站点侧**一个可查键都没有**(索引里没回填出任何 infohash、也没有放行记录): 这时
        # 所有种子都会落到「未核实」, 而 unknown_policy 默认 hr ⇒ **整站种子集体按受管束处理**
        # (2026-09-25 实测: 30 分钟能打出一片 HR 标)。与「站点还没发布过视图」同口径 ——
        # 没有可依据的数据时**回落本地字段逻辑**, 而不是把「不知道」当成「受管束」的结论。
        # mode=all 例外: 那是用户显式要的「全站受管束」, 不看索引现状。
        return None
    keys = [h for h in infohashes if h] or [""]
    best: Optional[HrResolution] = None
    best_key = keys[0]
    for h in keys:
        res = resolve_identity(view, h, anchor=anchor, now=now)
        if best is None or _rank(res) > _rank(best):
            best, best_key = res, h
        if _rank(best) == _RANK_HR:
            break  # 命中清单: 没有更保守的结论了
    assert best is not None
    entry = view.by_infohash.get(best_key)
    return HrJudgement(
        identity=best.identity,
        is_hr=best.is_hr(unknown_policy),
        reason=best.reason,
        site_satisfied=entry.satisfied_verdict if entry is not None else None,
        site=view.site,
        facts=HrSiteFacts.of(entry) if entry is not None else None,
    )


def build_site_view(
    site: str,
    mode: str,
    data,
    *,
    verified_ttl: float,
    refresh_interval: float,
    channel_state: str,
    generated_at: float,
    retention: float = 0.0,
) -> HrSiteView:
    """由站点数据构造不可变视图(取数线程在数据实质变化时调用一次, 然后整体替换引用)。

    只把**判定需要的**东西放进视图: 命中清单按 infohash 索引(A/B/C 三档; D 档已免罪不算受管束),
    放行记录原样带上。页面快照的其余字段仍留在站点文件里, 视图不复制(省内存也避免双份真相)。
    """
    by_infohash: Dict[str, HrEntry] = {}
    for entry in data.index.values():
        if not entry.active or entry.lane == LANE_EXEMPT:
            continue
        for h in (entry.infohash_v1, entry.infohash_v2):
            if h:
                by_infohash.setdefault(h, entry)
    return HrSiteView(
        site=site,
        mode=mode,
        revision=data.revision,
        complete=data.refresh.complete,
        last_success_ts=data.refresh.last_success_ts,
        verified_ttl=verified_ttl,
        refresh_interval=refresh_interval,
        channel_state=channel_state,
        generated_at=generated_at,
        by_infohash=by_infohash,
        verified=dict(data.verified),
        notes=data.refresh.reason,
    )


__all__ = [
    "POLICY_HR",
    "POLICY_NOT_HR",
    "HrAnchor",
    "HrIdentity",
    "HrJudgement",
    "HrResolution",
    "HrSiteFacts",
    "HrSiteView",
    "HrViewSet",
    "build_site_view",
    "judge_record",
    "resolve_identity",
]
