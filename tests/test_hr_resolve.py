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
- test_judge_record_carries_site_satisfied_verdict: 命中行的达标结论(档位即结论, 计划 §9 v3.0): B -> True / A -> False / C -> False
- test_lane_verdict_ignores_remain_and_local: A 档命中即未达标 —— 剩余达标时间归零 / 缺失都不改变结论(退出达标推导), 本地值不得越级
- test_judge_record_double_hit_prefers_lane_order: hybrid 双命中取达标结论档位序更靠前者(A > B > C), 与键序无关; 受管束结论不变
- test_judge_record_missing_hash_goes_through_policy: 两个 infohash 都空 -> 未核实(仍走 policy, 不是"不适用")
- test_judge_record_mode_all_unlisted_is_managed: mode=all 未列出 -> 受管束
- test_judge_record_without_any_lookup_key_falls_back: 站点侧一个可查键都没有(索引没回填出 infohash)
  -> None(回落本地), **不**把「不知道」当受管束(2026-09-25 实报: 否则整站打标); mode=all 不受此闸门影响
- test_judge_record_carries_site_facts: 命中行带出站点侧值并**拷成不可变对象**(WebUI 两套值对账的数据源)
- test_judge_record_age_exempt_overrides_listing: 完成时间超豁免线 -> 超龄豁免, **压过清单命中**
  (用户显式声明这类种子不再核实/管束)
- test_judge_record_within_age_not_exempt: 完成时间在线内 -> 正常判定, 豁免不掺和
- test_judge_record_age_limit_zero_disables: 豁免线 0(默认) -> 老种子也走正常判定(零静默变更守门)
- test_judge_record_age_exempt_requires_known_completion: completion_on 缺位(0/负)或无锚点 -> 不豁免
- test_judge_record_age_exempt_works_without_lookup_keys: 豁免排在「无可查键回落本地」闸门之前
  (豁免是 qB 侧事实, 不依赖索引建到哪)
- test_judge_record_age_exempt_applies_on_mode_all: mode=all 也认豁免(显式配置压过恒受管束)
- test_judge_record_age_exempt_boundary_is_inclusive: 恰好等于豁免线 -> 豁免; 差一秒 -> 不豁免
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
    """命中行的达标结论原样带出(档位即结论, 计划 §9 v3.0): B -> True / A -> False / C -> False

    A 档(考察中)恒未达标 —— 本地字段再够线也不得越级推翻站点清单结论; 「剩余达标时间」退出推导。
    """
    anchor = HrAnchor(added_on=1, downloaded=0)
    done = judge_record(_view(listed=[(H1, 101, "B")]), (H1, ""), anchor=anchor, now=NOW)
    scope = judge_record(_view(listed=[(H1, 101, "A")]), (H1, ""), anchor=anchor, now=NOW)
    undone = judge_record(_view(listed=[(H1, 101, "C")]), (H1, ""), anchor=anchor, now=NOW)
    assert done.site_satisfied is True and done.state_text == "受管束"
    assert scope.site_satisfied is False, "考察中 = 站点说义务仍在, 恒未达标(不看数值字段)"
    assert undone.site_satisfied is False


def test_lane_verdict_ignores_remain_and_local():
    """A 档命中即未达标: 剩余达标时间归零 / 缺失都不改变结论(remain 退出达标推导)

    旧实现(已废除)用「remain_seconds == 0 ⇒ 已达标」推导 —— v2.8 实证该字段是考核窗口倒计时,
    归零 = 考核到期(方向相反); 「缺字段回落本地」则让本地值越权推翻站点的明确清单结论。
    """
    anchor = HrAnchor(added_on=1, downloaded=0)
    # _view 构造的条目 remain_seconds=None(旧实现此时回落本地): 新语义下 A 档直接 False
    missing = judge_record(_view(listed=[(H1, 101, "A")]), (H1, ""), anchor=anchor, now=NOW)
    assert missing.site_satisfied is False, "缺字段 ≠ 站点没给结论: 档位本身就是结论"
    entry = HrEntry(tid=101, infohash_v1=H1, lane="A", remain_seconds=0)
    view = HrSiteView(site="s", mode="partial", by_infohash={H1: entry})
    zero = judge_record(view, (H1, ""), anchor=anchor, now=NOW)
    assert zero.site_satisfied is False, "剩余达标时间归零 = 考核到期, 不是已达标"


def test_judge_record_double_hit_prefers_lane_order():
    """hybrid 双命中取达标结论档位序更靠前者(计划 §9 v3.0: A 考察中 > B 已达标 > C 未达标)

    旧实现按 infohash 迭代序取首命中, 无档位序; 受管束结论不受影响(任一命中即受管束)。
    """
    anchor = HrAnchor(added_on=1, downloaded=0)
    view = _view(listed=[(H1, 101, "B"), (H2, 102, "A")])
    # v1 -> B(已达标) / v2 -> A(考察中): 取 A, 恒未达标 —— 两个键序都得同一结论
    got = judge_record(view, (H1, H2), anchor=anchor, now=NOW)
    assert got.is_hr is True and got.facts.lane == "A" and got.site_satisfied is False
    got = judge_record(view, (H2, H1), anchor=anchor, now=NOW)
    assert got.is_hr is True and got.facts.lane == "A" and got.site_satisfied is False
    # B > C: v1 -> C / v2 -> B, 取 B(已达标)
    view = _view(listed=[(H1, 101, "C"), (H2, 102, "B")])
    got = judge_record(view, (H2, H1), anchor=anchor, now=NOW)
    assert got.is_hr is True and got.facts.lane == "B" and got.site_satisfied is True


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


# ---------- 超龄豁免(completed_age_limit; 计划 §9 增补) ----------
# 独立时钟: 本文件顶部的 NOW=2000 是「秒级」小时间, 而豁免线以天计 —— 完成时刻必须为正
# (completion_on > 0 守卫), 故这组用例统一用「第 N 天」的绝对时刻表达。

AGE_LIMIT = 365 * 86400.0
AGE_NOW = 400 * 86400.0  # 这组用例的「现在」: 第 400 天
AGE_FRESH_TS = AGE_NOW - 60.0  # 刚刚完整刷新过(放行在有效期内)
OLD_COMPLETION = 10 * 86400.0  # 第 10 天完成: 距今 390 天, 超过豁免线
NEW_COMPLETION = AGE_NOW - 10 * 86400.0  # 10 天前完成: 线内


def test_judge_record_age_exempt_overrides_listing():
    """完成时间超豁免线 -> 超龄豁免(**压过清单命中**): 用户显式声明这类种子不再核实/管束

    站点哪怕还列着 C 档(未达标)也一样 —— 这是配置者自愿接受的漏 HR 风险(schema help 与计划 §13 写明)。
    """
    view = _view(listed=[(H1, 101, "C")])
    got = judge_record(
        view,
        (H1, ""),
        anchor=HrAnchor(added_on=1, completion_on=OLD_COMPLETION),
        now=AGE_NOW,
        completed_age_limit=AGE_LIMIT,
    )
    assert got is not None and got.identity is HrIdentity.EXEMPT
    assert got.is_hr is False and got.state_text == "超龄豁免"
    assert "超龄豁免" in got.reason


def test_judge_record_within_age_not_exempt():
    """完成时间在线内 -> 正常判定(清单命中照旧受管束), 豁免不掺和"""
    view = _view(listed=[(H1, 101, "A")])
    got = judge_record(
        view,
        (H1, ""),
        anchor=HrAnchor(added_on=1, completion_on=NEW_COMPLETION),
        now=AGE_NOW,
        completed_age_limit=AGE_LIMIT,
    )
    assert got.identity is HrIdentity.HR and got.is_hr is True


def test_judge_record_age_limit_zero_disables():
    """豁免线 0(默认) -> 老种子也走正常判定: 没显式配置就一个字的行为都不变(零静默变更守门)"""
    view = _view(listed=[(H1, 101, "A")])
    got = judge_record(view, (H1, ""), anchor=HrAnchor(added_on=1, completion_on=OLD_COMPLETION), now=AGE_NOW)
    assert got.identity is HrIdentity.HR and got.is_hr is True


def test_judge_record_age_exempt_requires_known_completion():
    """completion_on 缺位(0/负 = 从未完成)或没有锚点 -> 不豁免, 走正常判定(不猜)"""
    # 视图带一条新鲜放行记录(让「正常判定」有明确落点: 已核实不受管束), 豁免线开着但没触发
    view = _view(verified=[_verified(ts=AGE_FRESH_TS)])
    for anchor in (HrAnchor(added_on=1, completion_on=0), HrAnchor(added_on=1, completion_on=-1), None):
        got = judge_record(view, (H1, ""), anchor=anchor, now=AGE_NOW, completed_age_limit=AGE_LIMIT)
        assert got is not None and got.identity is HrIdentity.VERIFIED_NON_HR


def test_judge_record_age_exempt_works_without_lookup_keys():
    """豁免排在「无可查键回落本地」闸门**之前**: 索引还没长出任何键, 老种子照样豁免

    豁免是 qB 侧事实, 不依赖站点索引建到哪 —— 否则首刷前老种子会被当「不适用」落回本地逻辑。
    """
    empty = _view(complete=True, last_success_ts=AGE_FRESH_TS)
    assert empty.has_lookup_keys is False
    got = judge_record(
        empty,
        (H1, ""),
        anchor=HrAnchor(added_on=1, completion_on=OLD_COMPLETION),
        now=AGE_NOW,
        completed_age_limit=AGE_LIMIT,
    )
    assert got is not None and got.identity is HrIdentity.EXEMPT and got.is_hr is False


def test_judge_record_age_exempt_applies_on_mode_all():
    """mode=all 也认豁免: 显式配置的豁免线压过「未核实恒受管束」(配置者的显式取舍)"""
    got = judge_record(
        _view(mode="all", complete=False),
        (H1, ""),
        anchor=HrAnchor(completion_on=OLD_COMPLETION),
        now=AGE_NOW,
        completed_age_limit=AGE_LIMIT,
    )
    assert got is not None and got.identity is HrIdentity.EXEMPT and got.is_hr is False


def test_judge_record_age_exempt_boundary_is_inclusive():
    """恰好等于豁免线 -> 豁免(>= 判据); 差一秒不到 -> 不豁免"""
    view = _view(verified=[_verified(ts=AGE_FRESH_TS)])
    edge = judge_record(
        view, (H1, ""), anchor=HrAnchor(completion_on=AGE_NOW - AGE_LIMIT), now=AGE_NOW, completed_age_limit=AGE_LIMIT
    )
    assert edge.identity is HrIdentity.EXEMPT
    inside = judge_record(
        view, (H1, ""),
        anchor=HrAnchor(completion_on=AGE_NOW - AGE_LIMIT + 1),
        now=AGE_NOW,
        completed_age_limit=AGE_LIMIT
    )
    assert inside.identity is HrIdentity.VERIFIED_NON_HR
