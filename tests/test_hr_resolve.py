"""test_hr_resolve 测试计划: v3 四行判定表 + 12 格矩阵(计划 26-09-28-1932 §3.1/§3.2)

## 测试计划(每个测试函数一条)
- test_row1_scope_hit_is_hr: 行 1 命中考察中 → 管束, site_satisfied=False
- test_row1_hit_revokes_release_semantics_in_view_builder: 命中优先于旧放行记录
- test_row2_terminal_hit_releases: 行 2 终态档 B/C/D → 放行(B satisfied / C 未达标终态 / D 免罪)
- test_row2_c_is_terminal_not_managed: 「网站显示未达标是终态」—— 本地未达标也放行
- test_row3_release_record_releases: 行 3 放行记录放行
- test_row3_release_permanent_no_expiry: 放行永续有效(一年前签发仍有效, 无 verified_ttl)
- test_row3_anchor_drift_invalidates_to_local_fallback: 锚点漂移 → 行 4 本地兜底
- test_row3_exempt_source_keeps_label: D 免罪来源标签保留
- test_row4_no_evidence: 无证据 → NO_EVIDENCE(行 4, is_hr 恒 False 由调用方合成)
- test_row4_missing_infohash: infohash 缺位 → 行 4
- test_row4_local_satisfied_hint_not_judged_here: 行 4 达标判据在调用方, 本模块不代答
- test_none_when_view_missing: 站点未接入 → None
- test_none_when_listing_none: 全站型(listing=none) → None(恒行 4 本地兜底)
- test_dual_hash_conservative_merge_hr_wins: 双 hash 保守合并 —— 命中压过放行
- test_dual_hash_conservative_merge_released_wins_over_unknown: 双 hash 保守合并 —— 放行压过无证据
- test_matrix_local_satisfied: 12 格矩阵本地已达标行(A 管束, 其余放行)
- test_matrix_local_unsatisfied: 12 格矩阵本地未达标行(A 与无证据管束, 终态放行)
- test_matrix_counts: 管束恰好三格(管束只发生在三格的不变量)
- test_safety_display_local_fallback: 本地兜底展示(satisfied 决定 danger/safe)
- test_safety_display_site_scope_danger: 考察中 → danger/site_scope
- test_safety_display_site_unsatisfied_failed: C 终态 → failed/site_unsatisfied(独立红档)
- test_safety_display_released_safe: 放行记录 → safe/site_released
- test_safety_display_no_evidence: 行 4 → 本地兜底 / 未核实展示
"""
from typing import Optional

import pytest

from auto_qb.hr.model import (
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
from auto_qb.hr.resolve import (
    HrAnchor,
    HrIdentity,
    HrSiteView,
    judge_record,
    safety_display,
)

NOW = 1_700_000_000.0
TID = 101


def make_view(
    *,
    entry: Optional[HrEntry] = None,
    verified: Optional[HrVerified] = None,
    listing: str = "list",
) -> HrSiteView:
    lane_a = {}
    lane_terminal = {}
    if entry is not None:
        target = lane_a if entry.lane == LANE_SCOPE else lane_terminal
        for h in (entry.infohash_v1, entry.infohash_v2):
            if h:
                target.setdefault(h, entry)
    verified_map = {verified.infohash: verified} if verified is not None else {}
    return HrSiteView(
        site="example",
        listing=listing,
        lane_a=lane_a,
        lane_terminal=lane_terminal,
        verified=verified_map,
        healthy_ts=NOW - 60,
    )


def make_entry(lane: str, infohash: str = "h1", *, remain: Optional[int] = 3600) -> HrEntry:
    return HrEntry(tid=TID, name=f"EXAMPLE {TID}", lane=lane, infohash_v1=infohash, remain_seconds=remain)


def make_verified(
    infohash: str = "h1",
    source: str = SOURCE_NOT_LISTED,
    *,
    anchor_downloaded: int = 1 << 30,
    anchor_added_on: int = 100
) -> HrVerified:
    return HrVerified(
        infohash=infohash,
        tid=TID,
        verified_ts=NOW - 60,
        source=source,
        anchor_added_on=anchor_added_on,
        anchor_downloaded=anchor_downloaded,
        anchor_completion_on=-1,
        anchor_progress=1.0,
    )


def anchor(**kw) -> HrAnchor:
    base = dict(added_on=100, downloaded=1 << 30, completion_on=-1, progress=1.0, seeding_time=0, name="EXAMPLE")
    base.update(kw)
    return HrAnchor(**base)


# ---------------- 行 1: 命中考察中(A) → 管束 ----------------


def test_row1_scope_hit_is_hr():
    view = make_view(entry=make_entry(LANE_SCOPE))
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.HR
    assert j.is_hr is True
    assert j.site_satisfied is False  # A 考察中: 义务仍在
    assert j.facts is not None and j.facts.lane == LANE_SCOPE


def test_row1_hit_revokes_release_semantics_in_view_builder():
    """命中 A 的条目在视图里进 lane_a —— 即便它同时还有旧放行记录, 命中优先(管束)"""
    view = make_view(entry=make_entry(LANE_SCOPE), verified=make_verified())
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.HR


# ---------------- 行 2: 终态档 B/C/D → 放行(终态不可逆) ----------------


@pytest.mark.parametrize(
    "lane,src,satisfied", [
        (LANE_SATISFIED, SOURCE_SATISFIED, True),
        (LANE_UNSATISFIED, "", False),
        (LANE_EXEMPT, SOURCE_EXEMPT, None),
    ]
)
def test_row2_terminal_hit_releases(lane, src, satisfied):
    view = make_view(entry=make_entry(lane, remain=0))
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    assert j.is_hr is False
    assert j.released_src == src
    assert j.site_satisfied is satisfied


def test_row2_c_is_terminal_not_managed():
    """「网站显示未达标是终态」(20:43 定稿): 考核结论已定, 即便本地未达标也放行"""
    view = make_view(entry=make_entry(LANE_UNSATISFIED, remain=0))
    j = judge_record(view, ("h1", ), anchor=anchor(seeding_time=0), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    assert j.is_hr is False


# ---------------- 行 3: 放行记录(未列出 / D 免罪) → 放行; 锚点漂移作废 ----------------


def test_row3_release_record_releases():
    view = make_view(verified=make_verified())
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    assert j.is_hr is False


def test_row3_release_permanent_no_expiry():
    """终态不可逆: 放行记录远超任何旧 verified_ttl 仍有效(v3 无时效概念)"""
    ver = make_verified()
    ver.verified_ts = NOW - 365 * 86400  # 一年前的放行
    view = make_view(verified=ver)
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED


def test_row3_anchor_drift_invalidates_to_local_fallback():
    """本机重下(锚点漂移) ⇒ 放行作废 → 行 4 本地兜底(调用方会把未达标种子管住)"""
    view = make_view(verified=make_verified())
    j = judge_record(view, ("h1", ), anchor=anchor(downloaded=2 << 30), now=NOW)  # downloaded 增长
    assert j.identity is HrIdentity.NO_EVIDENCE


def test_row3_exempt_source_keeps_label():
    view = make_view(verified=make_verified(source=SOURCE_EXEMPT))
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    assert j.released_src == SOURCE_EXEMPT


# ---------------- 行 4: 无证据 → 本地兜底(NO_EVIDENCE) ----------------


def test_row4_no_evidence():
    view = make_view()
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.NO_EVIDENCE
    assert j.is_hr is False  # 行 4 由调用方本地判据兜底; is_hr 只表达站点侧明确结论


def test_row4_missing_infohash():
    view = make_view(entry=make_entry(LANE_SCOPE))
    j = judge_record(view, ("", ), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.NO_EVIDENCE


def test_row4_local_satisfied_hint_not_judged_here():
    """行 4 的「达标放行」判据在调用方(本地字段), 本模块只交回 NO_EVIDENCE"""
    view = make_view()
    j = judge_record(view, ("h1", ), anchor=anchor(seeding_time=100 * 86400), now=NOW)
    assert j.identity is HrIdentity.NO_EVIDENCE


# ---------------- 不适用(None): 未接入 / 全站型 ----------------


def test_none_when_view_missing():
    assert judge_record(None, ("h1", ), anchor=anchor(), now=NOW) is None


def test_none_when_listing_none():
    """全站型(listing=none)不取数, 判定恒行 4 本地兜底 —— 与未接入同效(返回 None)"""
    view = make_view(entry=make_entry(LANE_SCOPE), listing="none")
    assert judge_record(view, ("h1", ), anchor=anchor(), now=NOW) is None


# ---------------- 双 infohash 保守合并 ----------------


def test_dual_hash_conservative_merge_hr_wins():
    """v1 命中考察中 / v2 未列出放行 → 取更保守者(管束)"""
    entry = make_entry(LANE_SCOPE, "h1")
    ver = make_verified("h2")
    view = make_view(entry=entry, verified=ver)
    j = judge_record(view, ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.HR


def test_dual_hash_conservative_merge_released_wins_over_unknown():
    """v1 无证据 / v2 放行记录 → 放行"""
    ver = make_verified("h2")
    view = make_view(verified=ver)
    j = judge_record(view, ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED


# ---------------- §3.2 十二格情形矩阵(逐格参数化) ----------------
# 本地轴用 satisfied_local 模拟调用方行 4 的本地判据(达标=seeding_time 超额);
# 网站轴用视图内容模拟。断言 = (站点侧 identity, 最终 is_hr —— 行 4 由本地兜底合成)。


def _final(view, *, seeding_time: int) -> bool:
    """模拟 record.check_hr_condition 的行 4 合成: 达标放行 / 未达标管束(行 1/2/3 直接按站点)"""
    j = judge_record(view, ("h1", ), anchor=anchor(seeding_time=seeding_time), now=NOW)
    if j.identity is HrIdentity.NO_EVIDENCE:
        return not (seeding_time >= 3 * 86400)  # 未达标 → 管束
    return j.is_hr


def _view_for(site_state: str) -> HrSiteView:
    if site_state == "A":
        return make_view(entry=make_entry(LANE_SCOPE))
    if site_state == "B":
        return make_view(entry=make_entry(LANE_SATISFIED, remain=0))
    if site_state == "C":
        return make_view(entry=make_entry(LANE_UNSATISFIED, remain=0))
    if site_state == "D":
        return make_view(entry=make_entry(LANE_EXEMPT, remain=0))
    if site_state == "not-listed":
        return make_view(verified=make_verified())
    if site_state == "none":
        return make_view()
    raise ValueError(site_state)


@pytest.mark.parametrize("site_state", ["A", "B", "C", "D", "not-listed", "none"])
def test_matrix_local_satisfied(site_state):
    """本地已达标行: × A 管束(绝对权威); 其余全放行"""
    view = _view_for(site_state)
    is_hr = _final(view, seeding_time=10 * 86400)  # 本地达标(超额)
    expected = site_state == "A"
    assert is_hr is expected, f"本地已达标 × {site_state}"


@pytest.mark.parametrize("site_state", ["A", "B", "C", "D", "not-listed", "none"])
def test_matrix_local_unsatisfied(site_state):
    """本地未达标行: × A 管束; × 无证据管束(兜底); 其余放行(终态不可逆)"""
    view = _view_for(site_state)
    is_hr = _final(view, seeding_time=0)
    expected = site_state in ("A", "none")
    assert is_hr is expected, f"本地未达标 × {site_state}"


def test_matrix_counts():
    """管束恰好三格(2×6 矩阵): A×达标 / A×未达标 / 无证据×未达标"""
    managed = 0
    for local_ok in (True, False):
        for site_state in ("A", "B", "C", "D", "not-listed", "none"):
            view = _view_for(site_state)
            if _final(view, seeding_time=10 * 86400 if local_ok else 0):
                managed += 1
    assert managed == 3


# ---------------- safety_display 转译 ----------------


def test_safety_display_local_fallback():
    d = safety_display(None, triggered=True, satisfied=False)
    assert (d.safety, d.src) == ("danger", "local")
    d = safety_display(None, triggered=True, satisfied=True)
    assert (d.safety, d.src) == ("safe", "local")


def test_safety_display_site_scope_danger():
    view = make_view(entry=make_entry(LANE_SCOPE))
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    d = safety_display(j, triggered=True, satisfied=False)
    assert (d.safety, d.src) == ("danger", "site_scope")


def test_safety_display_site_unsatisfied_failed():
    view = make_view(entry=make_entry(LANE_UNSATISFIED, remain=0))
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    d = safety_display(j, triggered=True, satisfied=False)
    assert (d.safety, d.src) == ("failed", "site_unsatisfied")


def test_safety_display_released_safe():
    view = make_view(verified=make_verified())
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    d = safety_display(j, triggered=False, satisfied=False)
    assert (d.safety, d.src) == ("safe", "site_released")


def test_safety_display_no_evidence():
    view = make_view()
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    d = safety_display(j, triggered=True, satisfied=False)
    assert (d.safety, d.src) == ("danger", "local")
    d = safety_display(j, triggered=False, satisfied=False)
    assert (d.safety, d.src) == ("unknown", "unverified")
