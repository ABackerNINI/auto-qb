"""三态判定收口(计划 §9): 受管束 / 已核实不受管束 / 未核实。

**站点数据是权威数据**: 接入 hr_check 的站点「是否触发 / 是否达标」一律看站点侧, 本地 qB 字段
降为兜底与展示 —— 否则转移种子(A 客户端下载 → B 客户端保种, B 的 downloaded=0 被当辅种)
与多客户端场景会直接漏管。

不变量(两个方向的取舍):
- **不漏 HR 是首要**: unknown_policy 默认 hr + 新鲜度闸门 + 不完备刷新不产生放行 +
  放行有效期(verified_ttl)。
- **安全放行** 只由「完整核实过、且不在清单里」产生, 而不是「没看见就放行」。

本模块是**纯函数 + 不可变视图**: 视图由取数线程整体替换引用(项目先例: 搜索索引整体替换引用),
Web 线程与主循环并发只读安全; 「是否还在有效期」这类时间敏感判定在**读取时现算**,
不需要为时间流逝重发布视图。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Mapping, Optional

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
    """种子的 HR 身份三态"""

    HR = "hr"  # 受管束(站点清单命中; 或 mode=all 下的未核实)
    VERIFIED_NON_HR = "verified_non_hr"  # 已核实不受管束(安全放行)
    UNKNOWN = "unknown"  # 未核实


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
        """
        if self.identity is HrIdentity.HR:
            return True
        if self.identity is HrIdentity.VERIFIED_NON_HR:
            return False
        return self.forced or unknown_policy != POLICY_NOT_HR


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
    "HrResolution",
    "HrSiteView",
    "HrViewSet",
    "build_site_view",
    "resolve_identity",
]
