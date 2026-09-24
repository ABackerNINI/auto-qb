"""test_hr_resolve 测试计划: 三态判定(受管束 / 已核实不受管束 / 未核实)与不可变视图

判定表逐行覆盖(计划 §9): 两个方向上的取舍都要钉住 —— 首要不漏 HR, 其次让确认为非 HR 的真的放行。

## 测试计划(每个测试函数一条)
- test_listed_entry_is_managed: 清单命中(A/B/C) -> 受管束(不看本地 downloaded)
- test_unlisted_with_complete_refresh_is_released: 完整刷新未列出 + 未过期 -> 安全放行
- test_release_requires_fresh_backing: 超 verified_ttl 无新刷新背书 -> 回落未核实
- test_verified_record_backs_release: 有逐种放行记录时按记录时刻算有效期(D 档与未列出两种来源)
- test_verified_record_expired_is_unknown: 放行记录超期 -> 未核实
- test_freshness_gate_forces_hr: 本实例 added_on 晚于最近一次完整刷新 -> 恒受管束
- test_freshness_gate_not_applied_before_first_success: 从未成功刷新走 unknown_policy, 不是闸门
- test_unknown_policy_is_conservative_by_default: 未核实默认按 hr(保守)
- test_unknown_policy_not_hr_releases: unknown_policy=not-hr 时未核实按非 HR 对待
- test_incomplete_refresh_produces_no_release: 覆盖证明不成立 -> 未核实(不产生放行)
- test_mode_all_unknown_is_managed: mode=all 站点未核实恒受管束(不看 policy)
- test_anchor_drift_invalidates_release: 锚点四种漂移各一条 -> 放行立即作废
- test_anchor_intact_keeps_release: 反向用例 —— 锚点未漂移且未过期时放行保持(防误杀)
- test_missing_infohash_is_unknown: 身份缺位(infohash 未回填) -> 未核实
- test_site_not_activated_is_unknown: 站点未接入 hr_check -> 未核实
- test_build_site_view_filters_lane_and_active: 视图只收「受管束且最近一次刷新仍列出」的条目
- test_judge_record_not_applicable_when_site_off: 站点未接入 / mode=off -> None(调用方走本地字段逻辑)
- test_judge_record_hit_any_hash_wins: 两个 infohash 有一个命中清单 -> 受管束(命中即站点事实)
- test_judge_record_prefers_conservative_over_release: 一键放行 + 一键恒受管束 -> 取恒受管束(policy 绕不过)
- test_judge_record_carries_site_satisfied_verdict: 命中行的达标结论: B -> True / C -> False / 缺字段 -> None
- test_judge_record_missing_hash_goes_through_policy: 两个 infohash 都空 -> 未核实(仍走 policy, 不是"不适用")
- test_judge_record_mode_all_unlisted_is_managed: mode=all 未列出 -> 受管束
- test_judge_record_without_any_lookup_key_falls_back: 站点侧一个可查键都没有(索引没回填出 infohash)
  -> None(回落本地), **不**把「不知道」当受管束(2026-09-25 实报: 否则整站打标); mode=all 不受此闸门影响
- test_judge_record_carries_site_facts: 命中行带出站点侧值并**拷成不可变对象**(WebUI 两套值对账的数据源)
"""
import pytest

from auto_qb.hr.model import (
    LANE_EXEMPT,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    HrEntry,
    HrRefreshMeta,
    HrSiteData,
    HrVerified,
)
from auto_qb.hr.resolve import (
    POLICY_HR,
    POLICY_NOT_HR,
    HrAnchor,
    HrIdentity,
    HrSiteView,
    build_site_view,
    judge_record,
    resolve_identity,
)

NOW = 2000.0
TTL = 3600.0
OK_TS = 1000.0  # 有效期内(1000 + 3600 = 4600 > 2000)
STALE_NOW = 5000.0  # 在 OK_TS + TTL 之后: 放行已过期
OLD_TS = -3000.0  # 连 positive 都不满足的最早期时间戳
H1, H2, H3 = "aa" * 20, "bb" * 20, "cc" * 20


def _view(*, mode="partial", complete=True, last_success_ts=OK_TS, ttl=TTL, listed=(), verified=()):
    """构造判定视图; listed: [(infohash, tid, lane)]; verified: [HrVerified]"""
    by_infohash = {h: HrEntry(tid=tid, infohash_v1=h, lane=lane) for h, tid, lane in listed}
    return HrSiteView(
        site="s",
        mode=mode,
        complete=complete,
        last_success_ts=last_success_ts,
        verified_ttl=ttl,
        by_infohash=by_infohash,
        verified={v.infohash: v
                  for v in verified},
    )


def _verified(ts=OK_TS, source=SOURCE_NOT_LISTED, **anchor) -> HrVerified:
    return HrVerified(infohash=H1, tid=101, verified_ts=ts, source=source, **anchor)


def test_listed_entry_is_managed():
    """清单命中 -> 受管束; 本地 downloaded=0 的转移副本与真辅种一视同仁(站点数据是权威)"""
    view = _view(listed=[(H1, 101, "A")])
    got = resolve_identity(view, H1, anchor=HrAnchor(added_on=1, downloaded=0), now=NOW)
    assert got.identity is HrIdentity.HR
    assert "档位 A" in got.reason
    assert got.is_hr(POLICY_NOT_HR) is True  # policy 对已命中的条目不适用


def test_unlisted_with_complete_refresh_is_released():
    """完整刷新未列出 + 未过期 -> 安全放行(这就是本功能的主要收益)"""
    got = resolve_identity(_view(), H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.VERIFIED_NON_HR
    assert got.is_hr(POLICY_HR) is False


def test_release_requires_fresh_backing():
    """超 verified_ttl 无新刷新背书 -> 回落未核实(通道静默期不得无限放行)"""
    got = resolve_identity(_view(last_success_ts=OK_TS), H1, anchor=HrAnchor(added_on=1), now=STALE_NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert "放行已过期" in got.reason
    assert got.is_hr(POLICY_HR) is True


def test_verified_record_backs_release():
    """有逐种放行记录时按**记录时刻**算有效期(而不是最近刷新时刻)"""
    got = resolve_identity(_view(verified=[_verified()]), H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.VERIFIED_NON_HR
    assert "完整刷新未列出" in got.reason

    exempt = _view(verified=[_verified(source=SOURCE_EXEMPT)])
    got = resolve_identity(exempt, H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.VERIFIED_NON_HR
    assert "D 档已免罪" in got.reason


def test_verified_record_expired_is_unknown():
    """放行记录超期 -> 未核实"""
    got = resolve_identity(_view(verified=[_verified(ts=OLD_TS)]), H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert "放行已过期" in got.reason


def test_freshness_gate_forces_hr():
    """新鲜度闸门: 本实例 added_on 晚于最近一次完整刷新 -> 恒受管束, 不可被 policy 绕过"""
    got = resolve_identity(_view(), H1, anchor=HrAnchor(added_on=int(OK_TS) + 10), now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert got.forced is True
    assert "新鲜度闸门" in got.reason
    # ❗关键: 即使显式配了 not-hr, 闸门命中时也必须按 HR(否则新种子会漏管)
    assert got.is_hr(POLICY_NOT_HR) is True


def test_freshness_gate_not_applied_before_first_success():
    """从未成功刷新走 unknown_policy(与「刷新不完备」同类); 闸门需要一次成功刷新做基准"""
    view = _view(complete=False, last_success_ts=0.0)
    got = resolve_identity(view, H1, anchor=HrAnchor(added_on=99999), now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert got.forced is False
    assert got.is_hr(POLICY_NOT_HR) is False


def test_unknown_policy_is_conservative_by_default():
    """未核实默认按 hr 保守(唯一能保证「不漏 HR」的默认值)"""
    got = resolve_identity(_view(complete=False), H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert got.is_hr() is True
    assert got.is_hr(POLICY_HR) is True


def test_unknown_policy_not_hr_releases():
    """unknown_policy=not-hr 时未核实按非 HR 对待(等于自愿放弃第一重保证, 配置文案要写清)"""
    got = resolve_identity(_view(complete=False), H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.is_hr(POLICY_NOT_HR) is False


def test_incomplete_refresh_produces_no_release():
    """覆盖证明不成立(分页未到底 / scope 失败 / 解析可疑)-> 未核实, 不产生放行"""
    view = _view(complete=False, last_success_ts=OK_TS)
    got = resolve_identity(view, H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert got.is_hr(POLICY_HR) is True


def test_mode_all_unknown_is_managed():
    """mode=all 站点未核实恒受管束(全站 HR 的保守默认; 与 partial 的唯一差别)"""
    got = resolve_identity(_view(mode="all", complete=False), H1, anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.HR
    assert "mode=all" in got.reason


@pytest.mark.parametrize(
    "anchor,needle",
    [
        (HrAnchor(added_on=2, downloaded=1, completion_on=500, progress=0.8), "added_on"),
        (HrAnchor(added_on=1, downloaded=0, completion_on=500, progress=0.8), "downloaded 变小"),
        (HrAnchor(added_on=1, downloaded=5, completion_on=500, progress=0.8), "downloaded 增长"),
        (HrAnchor(added_on=1, downloaded=1, completion_on=500, progress=0.4), "progress 退回"),
    ],
)
def test_anchor_drift_invalidates_release(anchor, needle):
    """锚点漂移(本实例二次下载 / 文件被删重下 / 删种重加)-> 放行立即作废"""
    rec = _verified(anchor_added_on=1, anchor_downloaded=1, anchor_completion_on=500, anchor_progress=0.8)
    got = resolve_identity(_view(verified=[rec]), H1, anchor=anchor, now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert "锚点漂移" in got.reason and needle in got.reason


def test_anchor_intact_keeps_release():
    """反向用例: 锚点未漂移且未过期 -> 放行保持(防误杀, 收益所在)"""
    rec = _verified(anchor_added_on=1, anchor_downloaded=1, anchor_completion_on=500, anchor_progress=0.8)
    view = _view(verified=[rec])
    intact = HrAnchor(added_on=1, downloaded=1, completion_on=500, progress=0.8)
    assert resolve_identity(view, H1, anchor=intact, now=NOW).identity is HrIdentity.VERIFIED_NON_HR
    # 无锚点(别的客户端下载的种子)时仍按刷新背书放行
    assert resolve_identity(view, H1, now=NOW).identity is HrIdentity.VERIFIED_NON_HR


def test_missing_infohash_is_unknown():
    """身份缺位(infohash 未回填 / 站点未匹配)-> 未核实"""
    got = resolve_identity(_view(), "", anchor=HrAnchor(added_on=1), now=NOW)
    assert got.identity is HrIdentity.UNKNOWN
    assert "身份缺位" in got.reason


def test_site_not_activated_is_unknown():
    """站点未接入 hr_check(mode=off / 视图缺失)-> 未核实(既有逻辑不受影响)"""
    assert resolve_identity(None, H1, now=NOW).identity is HrIdentity.UNKNOWN
    assert resolve_identity(_view(mode="off"), H1, now=NOW).identity is HrIdentity.UNKNOWN


def test_build_site_view_filters_lane_and_active():
    """视图只收「受管束且最近一次刷新仍列出」的条目; D 档与非 active 都不进受管束集合"""
    data = HrSiteData()
    data.index[1] = HrEntry(tid=1, lane="A", infohash_v1=H1, active=True)
    data.index[2] = HrEntry(tid=2, lane=LANE_EXEMPT, infohash_v1=H2, active=True)
    data.index[3] = HrEntry(tid=3, lane="C", infohash_v1=H3, active=False)
    data.refresh = HrRefreshMeta(last_success_ts=OK_TS, complete=True, scopes_done=["A"])
    data.verified[H2] = HrVerified(infohash=H2, tid=2, verified_ts=OK_TS, source=SOURCE_EXEMPT)

    view = build_site_view(
        "s", "partial", data, verified_ttl=TTL, refresh_interval=TTL, channel_state="ok", generated_at=NOW
    )

    assert set(view.by_infohash) == {H1}
    assert view.complete is True and view.last_success_ts == OK_TS
    assert view.revision == data.revision
    assert resolve_identity(view, H2, now=NOW).identity is HrIdentity.VERIFIED_NON_HR  # D 档免罪
    assert resolve_identity(view, H3, now=NOW).identity is HrIdentity.VERIFIED_NON_HR  # 未列出 = 放行


# ---------- judge_record: 四个消费点的收口入口(record 拿到的就是它) ----------


def test_judge_record_not_applicable_when_site_off():
    """站点未接入 / mode=off -> None = 「本模块不适用」, 调用方必须继续走本地字段逻辑

    这是「零静默变更」的闸门: 返回 False 会让未接入站点全体变成不触发 HR(静默改行为)。
    """
    assert judge_record(None, (H1, ""), now=NOW) is None
    assert judge_record(_view(mode="off"), (H1, ""), now=NOW) is None


def test_judge_record_hit_any_hash_wins():
    """两个 infohash 有一个命中清单 -> 受管束(v2-only 页面同样成立); 达标结论随命中行"""
    view = _view(listed=[(H2, 102, "C")])
    got = judge_record(view, (H1, H2), anchor=HrAnchor(added_on=1, downloaded=0), now=NOW)
    assert got is not None and got.is_hr is True
    assert got.identity is HrIdentity.HR and "清单命中" in got.reason
    assert got.site == "s"


def test_judge_record_prefers_conservative_over_release():
    """一个键已核实放行 + 另一个键撞上新鲜度闸门 -> 取更保守的(恒受管束), policy 也绕不过"""
    view = _view(verified=[_verified()])
    anchor = HrAnchor(added_on=int(OK_TS) + 10)  # > last_success_ts: H2 走闸门(恒受管束)
    got = judge_record(view, (H1, H2), anchor=anchor, now=NOW, unknown_policy=POLICY_NOT_HR)
    assert got is not None
    assert got.identity is HrIdentity.UNKNOWN and "新鲜度闸门" in got.reason
    assert got.is_hr is True, "恒受管束不可被 unknown_policy=not-hr 绕过"


def test_judge_record_carries_site_satisfied_verdict():
    """命中行的达标结论原样带出: B -> True / C -> False / A 且无剩余时间字段 -> None(本地兜底)"""
    anchor = HrAnchor(added_on=1, downloaded=0)
    done = judge_record(_view(listed=[(H1, 101, "B")]), (H1, ""), anchor=anchor, now=NOW)
    undone = judge_record(_view(listed=[(H1, 101, "C")]), (H1, ""), anchor=anchor, now=NOW)
    unknown = judge_record(_view(listed=[(H1, 101, "A")]), (H1, ""), anchor=anchor, now=NOW)
    assert done.site_satisfied is True and done.state_text == "受管束"
    assert undone.site_satisfied is False
    assert unknown.site_satisfied is None, "站点没给结论时必须回落本地, 不能当成未达标"


def test_judge_record_missing_hash_goes_through_policy():
    """两个 infohash 都空 -> 未核实(**不是**「不适用」): 该按 policy 保守处理, 不能静默放行

    前提: 站点侧**有**可查的键(否则走 `test_judge_record_without_any_lookup_key_falls_back` 那道闸门)。
    """
    view = _view(listed=[(H3, 103, "A")])  # 视图里有键, 只是这个种子自己没有 infohash
    got = judge_record(view, ("", ""), now=NOW)
    assert got is not None
    assert got.identity is HrIdentity.UNKNOWN and got.is_hr is True
    assert "身份缺位" in got.reason
    relaxed = judge_record(view, ("", ""), now=NOW, unknown_policy=POLICY_NOT_HR)
    assert relaxed.is_hr is False, "policy=not-hr 时未核实才放行(用户显式选的取舍)"


def test_judge_record_mode_all_unlisted_is_managed():
    """mode=all 站点未列出 -> 恒受管束(与 policy 无关)"""
    got = judge_record(_view(mode="all", complete=False), (H1, ""), now=NOW, unknown_policy=POLICY_NOT_HR)
    assert got is not None and got.is_hr is True
    assert "mode=all" in got.reason


def test_judge_record_carries_site_facts():
    """命中行带出站点侧值(档位/还需做种/剩余达标/分享率/下载量)—— WebUI 两套值对账的数据源

    拷成不可变对象是刻意的: 视图里的行对象会被取数线程复用改写, 直接带引用会读到半新半旧的行。
    """
    entry = HrEntry(
        tid=101,
        infohash_v1=H1,
        lane="C",
        need_seed_seconds=3600,
        remain_seconds=0,
        ratio=1.25,
        downloaded_bytes=4096,
    )
    view = HrSiteView(site="s", mode="partial", by_infohash={H1: entry})
    got = judge_record(view, (H1, ""), anchor=HrAnchor(added_on=1, downloaded=0), now=NOW)
    assert got is not None and got.facts is not None
    assert got.facts.lane == "C" and got.facts.need_seed_seconds == 3600
    assert got.facts.remain_seconds == 0 and got.facts.ratio == 1.25 and got.facts.downloaded_bytes == 4096
    entry.remain_seconds = 99  # 取数线程复用行对象: 已拷出的判定结果不得跟着变
    assert got.facts.remain_seconds == 0
    assert judge_record(_view(mode="all", complete=False), (H1, ""), now=NOW).facts is None, "未命中无站点侧值"


def test_judge_record_without_any_lookup_key_falls_back():
    """站点侧**一个可查键都没有** ⇒ None(回落本地), 而不是「未核实 ⇒ unknown_policy=hr ⇒ 全站受管束」

    2026-09-25 用户实报: 取数通道刚接通时索引还没有任何 infohash(下载被频控饿死), 而按「未核实」判会
    让该站**全部**种子集体触发打标。判据取「有没有可查的键」而不是「有没有抓过页面」: 抓过但一个键都
    回填不出来时, 这个视图对判定同样没有信息量。
    """
    empty = _view(complete=True, last_success_ts=OK_TS)  # 抓得完整, 但索引里 0 个 infohash / 0 条放行
    assert empty.has_lookup_keys is False
    assert judge_record(empty, (H1, ""), now=NOW) is None
    # 一旦有了键(哪怕只是一条放行记录), 闸门就打开, 回到正常判定
    assert judge_record(_view(verified=[_verified()]), (H1, ""), now=NOW) is not None
    # mode=all 是用户显式要的「全站受管束」: 不看索引现状
    forced = judge_record(_view(mode="all", complete=False), (H1, ""), now=NOW)
    assert forced is not None and forced.is_hr is True
