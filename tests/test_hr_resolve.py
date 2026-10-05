"""test_hr_resolve 测试计划: v3 四行判定表 + 12 格矩阵(计划 26-09-28-1932 §3.1/§3.2)

## 测试计划(每个测试函数一条)
- test_row1_scope_hit_is_hr: 行 1 命中考察中 → 管束, site_satisfied=False
- test_row1_hit_revokes_release_semantics_in_view_builder: 命中优先于旧放行记录
- test_row2_terminal_hit_releases: 行 2 终态档 B/C/D → 放行(B satisfied / C 未达标终态 / D 免罪)
- test_row2_c_is_terminal_not_managed: 「网站显示未达标是终态」—— 本地未达标也放行
- test_row3_release_record_releases: 行 3 放行记录放行
- test_row3_release_permanent_no_expiry: 放行永续有效(一年前签发仍有效, 无 verified_ttl)
- test_row3_anchor_drift_invalidates_to_local_fallback: 锚点漂移 → 行 4 本地兜底
- test_row3_record_without_anchor_snapshot_is_not_drift: 记录无锚点快照 → 不凭空判漂移(不作废)
- test_row3_exempt_source_keeps_label: D 免罪来源标签保留
- test_row4_no_evidence: 无证据 → NO_EVIDENCE(行 4, is_hr 恒 False 由调用方合成)
- test_row4_missing_infohash: infohash 缺位 → 行 4
- test_row4_local_satisfied_hint_not_judged_here: 行 4 达标判据在调用方, 本模块不代答
- test_none_when_view_missing: 站点未接入 → None
- test_none_when_listing_none: 全站型(listing=none) → None(恒行 4 本地兜底)
- test_dual_hash_conservative_merge_hr_wins: 双 hash 保守合并 —— 命中压过放行
- test_dual_hash_conservative_merge_released_wins_over_unknown: 双 hash 保守合并 —— 放行压过无证据
- test_tie_release_takes_stronger_source: 平局合并(issue B2-02 P-04)—— 同为放行取依据更强者(D 免罪 > 缺席)
- test_tie_release_exempt_beats_satisfied: 平局合并 —— D 免罪 > B 达标
- test_tie_release_both_safe_no_flip: 平局合并 —— 两态同为 SAFE 无判定翻转
- test_tie_hr_takes_less_remain: 平局合并 —— 同为管束取剩余时间更少(None 未知视为无穷大)
- test_tie_no_evidence_keeps_first: 平局合并 —— 同为无证据无差异保先到
- test_tie_c_terminal_preserved_over_release: 平局合并 —— C 终态未达标(failed)不被更强放行依据盖掉(保守序)
- test_matrix_local_satisfied: 12 格矩阵本地已达标行(A 管束, 其余放行)
- test_matrix_local_unsatisfied: 12 格矩阵本地未达标行(A 与无证据管束, 终态放行)
- test_matrix_counts: 管束恰好三格(管束只发生在三格的不变量)
- test_safety_display_local_fallback: 本地三分(satisfied 决定 safe/danger/warning)
- test_safety_display_site_scope_danger: 考察中 → danger/site_scope
- test_safety_display_site_unsatisfied_failed: C 终态 → failed/site_unsatisfied(独立红档)
- test_safety_display_released_safe: 放行记录 → safe/site_released
- test_safety_display_no_evidence: 行 4 / 未接入 → satisfied×triggered 三分(达标 safe / 未达标+触发 danger / 未达标+未触发 warning 疑似辅种; 计划 26-09-30-0559)

### P1 覆盖率提升轮: 判定与漂移长尾
- test_drift_reason_all_branches: 漂移四条人话分支 + 无快照可比不判漂移
- test_state_text_three_states: state_text 三态人话
- test_site_view_empty_and_has_evidence: HrSiteView.empty 与 has_evidence 三来源判据
- test_row3_release_without_anchor_skips_drift_check: 行 3 不传锚点跳过漂移检查
- test_safety_display_exempt_and_graduation_labels: 免罪/毕业展示标签(带事实按档位, 无事实按来源)
- test_build_site_view_skips_unknown_lane_entries: 空档位条目不进判定面
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
    SAFETY_FAILED,
    SAFETY_SAFE,
    SRC_SITE_EXEMPT,
    SRC_SITE_SATISFIED,
    HrAnchor,
    HrIdentity,
    HrJudgement,
    HrSiteView,
    build_site_view,
    judge_record,
    resolve_identity,
    safety_display,
)
from auto_qb.hr.model import CHANNEL_OK

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


def test_row3_record_without_anchor_snapshot_is_not_drift():
    """记录无锚点快照(旧记录 / 写入方漏带) ⇒ 不作废: 「永续有效」优先于漂移这条辅助机制

    !把 anchor_downloaded=0 读成「downloaded 增长」会让每条无快照的放行在**签发当刻**被判漂移,
    种子回落本地兜底(2026-09-29 实报「已在线核实过却显示本地兜底」)。
    """
    ver = HrVerified(infohash="h1", tid=TID, verified_ts=NOW, source=SOURCE_NOT_LISTED)
    assert not ver.has_anchor_snapshot
    view = make_view(verified=ver)
    j = judge_record(view, ("h1", ), anchor=anchor(downloaded=7 << 30), now=NOW)
    assert j.identity is HrIdentity.RELEASED


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


# ---------------- 双 hash 平局合并(issue B2-02, P-04 补平局合并; 纯展示口径) ----------------


def _two_entry_view(e1, e2, verified=None):
    """两个条目各占一个 infohash 的视图(平局合并用; 与 build_site_view 同款分桶; 条目可为 None)"""
    lane_a, lane_terminal = {}, {}
    for e in (e1, e2):
        if e is None:
            continue
        target = lane_a if e.lane == LANE_SCOPE else lane_terminal
        for h in (e.infohash_v1, e.infohash_v2):
            if h:
                target.setdefault(h, e)
    return HrSiteView(
        site="example",
        listing="list",
        lane_a=lane_a,
        lane_terminal=lane_terminal,
        verified=verified or {},
        healthy_ts=NOW - 60,
    )


def test_tie_release_takes_stronger_source():
    """同为放行: 取依据更强者 —— D 免罪 > 缺席式放行(v1 先到不被保留, 兑现 docstring 承诺)"""
    ver = make_verified("h1")  # 放行记录(缺席式, SRC_SITE_RELEASED)
    e2 = make_entry(LANE_EXEMPT, "h2", remain=0)
    view = _two_entry_view(None, e2, verified={ver.infohash: ver})
    j = judge_record(view, ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    assert j.released_src == SOURCE_EXEMPT
    assert safety_display(j, triggered=False, satisfied=True).src == SRC_SITE_EXEMPT


def test_tie_release_exempt_beats_satisfied():
    """同为放行: D 免罪 > B 达标"""
    e1 = make_entry(LANE_SATISFIED, "h1", remain=0)
    e2 = make_entry(LANE_EXEMPT, "h2", remain=0)
    j = judge_record(_two_entry_view(e1, e2), ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    assert j.released_src == SOURCE_EXEMPT


def test_tie_release_both_safe_no_flip():
    """两态同为 SAFE: B(已达标) 与缺席式放行合并仍 SAFE —— 无判定翻转(纯展示口径)"""
    e1 = make_entry(LANE_SATISFIED, "h1", remain=0)
    ver = make_verified("h2")
    view = _two_entry_view(e1, None, verified={ver.infohash: ver})
    j = judge_record(view, ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.RELEASED
    d = safety_display(j, triggered=False, satisfied=True)
    assert d.safety == SAFETY_SAFE and d.src == SRC_SITE_SATISFIED


def test_tie_no_evidence_keeps_first():
    """同为无证据: 无差异保先到(NO_EVIDENCE 平局不翻转)"""
    j = judge_record(make_view(), ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.NO_EVIDENCE


def test_tie_hr_takes_less_remain():
    """同为管束: 取「剩余时间更少」的行展示; 两边都未知/相等保先到"""
    e1 = make_entry(LANE_SCOPE, "h1", remain=3600)
    e2 = make_entry(LANE_SCOPE, "h2", remain=100)
    j = judge_record(_two_entry_view(e1, e2), ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.identity is HrIdentity.HR
    assert j.facts is not None and j.facts.remain_seconds == 100
    # remain_seconds None(未知)视为无穷大: 具体更小值的行胜出未知行
    e3 = make_entry(LANE_SCOPE, "h1", remain=None)
    e4 = make_entry(LANE_SCOPE, "h2", remain=100)
    j2 = judge_record(_two_entry_view(e3, e4), ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j2.facts is not None and j2.facts.remain_seconds == 100


def test_tie_c_terminal_preserved_over_release():
    """C 终态未达标(failed 展示)不被「更强的放行依据」盖掉 —— 把不能删洗成可删违背保守序

    两个键序都断言: C 在后要翻转为 C, C 在前不被缺席式放行替换。
    """
    ver = make_verified("h1")
    c = make_entry(LANE_UNSATISFIED, "h2", remain=0)
    j = judge_record(_two_entry_view(None, c, verified={ver.infohash: ver}), ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j.facts is not None and j.facts.lane == LANE_UNSATISFIED
    assert safety_display(j, triggered=False, satisfied=False).safety == SAFETY_FAILED
    ver2 = make_verified("h2")
    c1 = make_entry(LANE_UNSATISFIED, "h1", remain=0)
    j2 = judge_record(_two_entry_view(c1, None, verified={ver2.infohash: ver2}), ("h1", "h2"), anchor=anchor(), now=NOW)
    assert j2.facts is not None and j2.facts.lane == LANE_UNSATISFIED


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
    """未接入(judged None)与行 4 同落本地三分(计划 26-09-30-0559 §5)"""
    d = safety_display(None, triggered=True, satisfied=False)
    assert (d.safety, d.src) == ("danger", "local")
    d = safety_display(None, triggered=True, satisfied=True)
    assert (d.safety, d.src) == ("safe", "local")
    d = safety_display(None, triggered=False, satisfied=False)
    assert (d.safety, d.src) == ("warning", "local"), "未达标+未触发 = 疑似辅种黄档"


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
    """行 4 三分(计划 26-09-30-0559 §5): 达标 → safe / 未达标+触发 → danger / 未达标+未触发 → warning"""
    view = make_view()
    j = judge_record(view, ("h1", ), anchor=anchor(), now=NOW)
    d = safety_display(j, triggered=True, satisfied=False)
    assert (d.safety, d.src) == ("danger", "local")
    d = safety_display(j, triggered=False, satisfied=False)
    assert (d.safety, d.src) == ("warning", "local"), "疑似辅种黄档(转移种常态, 不代表无义务)"
    d = safety_display(j, triggered=False, satisfied=True)
    assert (d.safety, d.src) == ("safe", "local"), "达标即 safe(触发与否不再影响档位)"


# ==================== P1 覆盖率提升轮: 判定与漂移长尾 ====================


def _ver(**kw):
    from auto_qb.hr.model import HrVerified

    base = dict(
        infohash="H",
        tid=1,
        verified_ts=1.0,
        source=SOURCE_NOT_LISTED,
        anchor_added_on=100,
        anchor_downloaded=1000,
        anchor_completion_on=500,
        anchor_progress=1.0,
    )
    base.update(kw)
    return HrVerified(**base)


def test_drift_reason_all_branches():
    """锚点漂移四条人话分支(added_on / downloaded 缩水 / downloaded 增长 / completion_on / progress 退回)"""
    a = HrAnchor(added_on=100, downloaded=1000, completion_on=500, progress=1.0)
    assert a.drift_reason(_ver()) == "", "全等不算漂移"
    assert "added_on" in a.drift_reason(_ver(anchor_added_on=999))
    assert "变小" in HrAnchor(added_on=100, downloaded=900, completion_on=500, progress=1.0).drift_reason(_ver())
    assert "增长" in HrAnchor(added_on=100, downloaded=2000, completion_on=500, progress=1.0).drift_reason(_ver())
    assert "completion_on" in HrAnchor(added_on=100, downloaded=1000, completion_on=501,
                                       progress=1.0).drift_reason(_ver())
    assert "progress" in HrAnchor(added_on=100, downloaded=1000, completion_on=500, progress=0.5).drift_reason(_ver())
    # 记录侧未记的字段不参与漂移(缺省快照不凭空判)
    no_snap = _ver(anchor_added_on=0, anchor_downloaded=0, anchor_completion_on=-1, anchor_progress=0.0)
    assert a.drift_reason(no_snap) == "", "无快照可比"


def test_state_text_three_states():
    """state_text 三态人话(管束 / 放行 / 无证据)"""
    assert HrJudgement(identity=HrIdentity.HR).state_text == "受管束"
    assert HrJudgement(identity=HrIdentity.RELEASED).state_text == "已核实·放行"
    assert HrJudgement(identity=HrIdentity.NO_EVIDENCE).state_text == "无站点证据(本地兜底)"


def test_site_view_empty_and_has_evidence():
    """HrSiteView.empty 工厂与 has_evidence 判据(三来源任一即有证据)"""
    v = HrSiteView.empty("s")
    assert v.site == "s" and v.has_evidence is False
    from auto_qb.hr.model import HrEntry

    entry = HrEntry(tid=1, name="x")
    with_hit = HrSiteView(site="s", lane_a={"H": entry})
    assert with_hit.has_evidence is True
    with_verified = HrSiteView(site="s", verified={"H": _ver()})
    assert with_verified.has_evidence is True


def test_row3_release_without_anchor_skips_drift_check():
    """行 3 放行记录不传锚点 -> 不做漂移检查, 直接放行(别的客户端下载本地看不见)"""
    from auto_qb.hr.resolve import resolve_identity

    view = HrSiteView(site="s", verified={"H": _ver()})
    res = resolve_identity(view, "H", anchor=None)
    assert res.identity is HrIdentity.RELEASED


def test_safety_display_exempt_and_graduation_labels():
    """免罪/毕业两类放行的展示标签(带命中行事实时按档位, 无事实时按放行来源)"""
    from auto_qb.hr.model import HrEntry
    from auto_qb.hr.resolve import HrSiteFacts, HrJudgement

    j = HrJudgement(identity=HrIdentity.RELEASED, facts=HrSiteFacts.of(HrEntry(tid=1, lane=LANE_EXEMPT)))
    d = safety_display(j, triggered=False, satisfied=True)
    assert (d.safety, d.src) == (SAFETY_SAFE, SRC_SITE_EXEMPT)
    j2 = HrJudgement(identity=HrIdentity.RELEASED, released_src=SOURCE_SATISFIED)
    d2 = safety_display(j2, triggered=False, satisfied=True)
    assert (d2.safety, d2.src) == (SAFETY_SAFE, SRC_SITE_SATISFIED)


def test_build_site_view_skips_unknown_lane_entries():
    """档位为空(IDLE)的条目不进任何判定面(既非考察中也非终态)"""
    from auto_qb.hr.model import HrEntry, HrSiteData

    data = HrSiteData()
    idle = HrEntry(tid=1, name="x")
    idle.lane = ""
    idle.infohash_v1 = "H1"
    data.index[1] = idle
    view = build_site_view("s", "list", data, channel_state=CHANNEL_OK, generated_at=1.0)
    assert view.lane_a == {} and view.lane_terminal == {}
