"""test_web_hr_views 测试计划: HR web 端点与搜索 / 文件系统端点

## 测试计划(每个测试函数一条)
- test_views_published_atomically_when_rebuilt_concurrently: 并发重建(主循环线程 vs Web 线程)时四份视图与版本号必须**同一轮**发布, 不得出现"半新半旧"
- test_flush_views_marks_dirty_on_hr_revision_change: HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2) —— hr.revision 变化后 flush_views 置脏, 重建后基线前移、再次 flush 不再置脏(无循环置脏)
- test_flush_views_hr_facade_missing_null_defense: hr 门面缺失(None)时判空防御 —— 重建记基线与 flush 比对都跳过, 不炸不置脏
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
- test_build_group_view_added_on_is_latest_member
- test_build_group_view_hr_counts
- test_build_group_view_hr_tags
"""

import json

import os

import re

import sys

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from unittest import mock

import pytest

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from webui_helpers import _UI_ALL, _ui_aggregate, _hr_status_env, ENTRY_ROW_KEYS_API, HISTORY_ROW_KEYS


def test_build_group_view_hr_counts(tmp_path):
    """组级 H&R 计数: 分母 = 已触发 HR 的成员数, 分子 = 其中未达标的成员数(前端 H&R 栏)"""
    from helpers import FakeClient, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store

    hr = _hr_rule(required_share_ratio=2.0)
    conf = FakeTracker("HHan", hr=hr)
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    def tor(h, seeding_time, ratio):
        return FakeTorrent(
            hash=h,
            name="Show",
            state="stalledUP",
            size=512**2,
            total_size=512**2,
            downloaded=512**2,
            amount_left=0,
            progress=1.0,
            seeding_time=seeding_time,
            ratio=ratio,
            save_path=r"R:/s",
            tracker_conf=conf,
        )

    seed_store(
        mgr,
        [
            tor("HA", 100, 0.5),  # 已触发但未达标(时长与分享率都不够)
            tor("HB", 100, 3.0),  # 已触发且分享率达标
            tor("HC", 4 * 86400, 0.1),  # 已触发且时长达标
        ]
    )
    key = ("R:/s", ("a.mkv", ))
    mgr.store.groups[key] = ["HA", "HB", "HC"]
    for h in ("HA", "HB", "HC"):
        mgr.store.member_to_key[h] = key

    g = mgr._build_group_view()[0]
    assert g["hr_triggered"] == 3
    assert g["hr_pending"] == 1


def test_build_group_view_added_on_is_latest_member(tmp_path):
    """组级 added_on = 组内**最近添加**成员的时间(前端默认按此降序排序)

    用 max 而非 min: "刚补进来的那个辅种"才是用户最关心的新条目。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="Show", added_on=1000, save_path=r"R:/s")
    t2 = FakeTorrent(hash="HB", name="Show", added_on=3000, save_path=r"R:/s")
    t3 = FakeTorrent(hash="HC", name="Other", added_on=2000, save_path=r"R:/o")
    seed_store(mgr, [t1, t2, t3])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    key2 = ("R:/o", ("c.mkv", ))
    mgr.store.groups[key2] = ["HC"]
    mgr.store.member_to_key["HC"] = key2

    groups = {g["name"]: g for g in mgr._build_group_view()}
    assert groups["Show"]["added_on"] == 3000  # max(1000, 3000)
    assert groups["Other"]["added_on"] == 2000
    assert groups["Show"]["members"] == ["HA", "HB"], "P-02 二期: 组行 members = hash 引用数组"
    # 成员级也透出 added_on(排序/展示共用的原始值): P-02 二期后成员明细经平铺行(_seed_view
    # 继承 _member_view)取 —— 组行不再内嵌明细
    flat = {m["hash"]: m for m in mgr._build_flat_view()}
    assert sorted(flat[h]["added_on"] for h in groups["Show"]["members"]) == [1000, 3000]


def test_views_published_atomically_when_rebuilt_concurrently(tmp_path):
    """并发重建: 四份视图与版本号必须**同一轮**发布(主循环线程 vs Web 线程)

    web.py 的同步 `def` 处理器跑在 FastAPI 线程池里, 会与主循环同时走 `rebuild_views`。
    无锁时后者的"逐条赋值 + 版本号自增"会被前者插到中间 ⇒ 1.`_group_view_ver += 1` 是
    读-改-写, 丢失更新; 2.Web 线程可能拿到"groups 来自本轮、flat 来自上一轮"的错位组合,
    而版本号只有一个 ⇒ 前端按 rid 判定 updated=true 却把错位数据整表换上去。

    检测手法(刻意做成**确定性**, 不依赖线程调度): 让重建卡在 builder 里不放行, 再把脏标记
    置为 False —— 于是读取路径不需要重建, 它能否返回**只取决于有没有锁**, 与交错时序无关。
    (更直觉的"比对四份视图的 build 号"写法是 flaky 的: 无锁时若两个线程各自完整发布一轮,
    最后发布者胜出, 四份仍是自洽的, 用例会假绿。)
    """
    import threading as _threading

    from helpers import FakeClient, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    inside = _threading.Event()  # 重建已进入 builder
    release = _threading.Event()  # 放行重建
    errors = []

    def _build_group():
        inside.set()
        release.wait(5)  # 卡在临界区里, 模拟"重建尚未发布"
        return []

    mgr._build_group_view = _build_group

    def _main_loop_path():
        try:
            mgr.web.rebuild_views()  # 主循环 _tick 走的重建路径(持锁)
        except Exception as e:  # 线程内异常不能静默吞掉
            errors.append(e)

    t = _threading.Thread(target=_main_loop_path)
    t.start()
    assert inside.wait(5), "前置: 重建线程应已进入 builder"

    # 关键: 置脏为 False, 让读取路径**不需要重建** —— 于是它是否返回只取决于"有没有锁",
    # 不再受线程调度影响(若改成依赖交错时序, 用例会变 flaky)。
    mgr.web.group_view_dirty = False

    read_done = _threading.Event()

    def _web_path():
        try:
            mgr.web.ensure_view()  # Web 线程路径
        finally:
            read_done.set()

    r = _threading.Thread(target=_web_path)
    r.start()
    assert not read_done.wait(0.5), ("重建进行中读取不应立即返回 —— 锁未生效时, "
                                     "Web 线程会读到半新半旧的四视图组合")
    release.set()
    t.join()
    r.join()
    assert not errors, f"重建线程异常: {errors}"


def test_flush_views_marks_dirty_on_hr_revision_change(tmp_path):
    """HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2): hr.revision 变化 -> flush_views 置脏

    HR 判定结果不是 store 快照字段, store.view_changed 覆盖不到它(与「错误原因」预取
    同一判别法): 取数线程发布新判定(revision 自增)必须显式翻译成一次置脏, 否则界面
    挂在旧判定上直到别的原因碰巧重建。基线随重建前移 => 只置一拍, 无循环置脏。
    """
    from auto_qb.hr.resolve import HrSiteView, HrViewSet

    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    seed_store(mgr, [FakeTorrent(hash="HA", name="A")])
    mgr.store.consume_view_changed()  # 排掉 store 构造期置脏(TorrentStore 初始 view_changed=True), 只考察 HR 通道
    mgr.web.group_view_dirty = False
    mgr.web.rebuild_views()  # 重建完成: 基线记下当刻 revision(0)
    assert mgr.web.group_view_dirty is False
    assert mgr.web._hr_rev_at_build == 0

    # 直接推 publisher 模拟取数线程发布新判定(内容指纹变化 => revision 自增)
    pushed = mgr.hr.publisher.publish(HrViewSet(views={"HHan": HrSiteView(site="HHan")}, generated_at=1.0))
    assert pushed is True, "前置: 首个站点视图必须抬 revision"

    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is True, "revision 变化必须置脏"

    # 重建后基线前移, 再次 flush 不再置脏(无循环置脏)
    mgr.web.rebuild_views()
    assert mgr.web.group_view_dirty is False
    assert mgr.web._hr_rev_at_build == mgr.hr.publisher.revision, "基线必须随重建前移"
    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is False, "基线已前移, 不得循环置脏"


def test_flush_views_hr_facade_missing_null_defense(tmp_path):
    """hr 门面缺失(None)时判空防御: 重建记基线与 flush 比对都跳过, 不炸不置脏"""
    from helpers import make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.hr = None
    mgr.store.consume_view_changed()  # 排掉 store 构造期置脏, 只考察 HR 通道
    mgr.web.group_view_dirty = False
    mgr.web.rebuild_views()
    assert mgr.web._hr_rev_at_build is None, "无 HR 运行时: 基线记 None"
    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is False, "无 HR 运行时: 新鲜度比对跳过, 不得置脏"


def test_build_group_view_hr_tags(tmp_path):
    """分组视图透出 HR 标签展示值: 已触发未达标 -> hr_tag, 已达标 -> hr_tag_done

    判定与打标签流程同源(torrents.check_hr_condition/check_hr_satisfied), 标签文本经
    utils.replace_vars 展开 ${required_seeding_time} —— 前端只按文本相等着色, 故两者必须逐字一致。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store

    hr = _hr_rule(add_tag="!!HR${required_seeding_time}!!", add_tag_for_satisfied="--HR${required_seeding_time}--")
    conf = FakeTracker("HHan", hr=hr)
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    def tor(h, name, seeding_time, downloaded=512**2):
        return FakeTorrent(
            hash=h,
            name=name,
            state="stalledUP",
            size=512**2,
            total_size=512**2,
            downloaded=downloaded,
            amount_left=0,
            progress=1.0,
            seeding_time=seeding_time,
            save_path=r"R:/s",
            tracker_conf=conf
        )

    seed_store(
        mgr,
        [
            tor("HA", "Pending.Show", 3600),  # 1 小时: 已触发 HR 但未达标(3D + 12H)
            tor("HB", "Done.Show", 4 * 86400),  # 4 天: 已达标
            tor("HC", "NoHR.Show", 4 * 86400, downloaded=0),  # 纯辅种(无下载量): 不触发 HR
        ]
    )
    for h, key in (("HA", ("R:/p", ("a.mkv", ))), ("HB", ("R:/d", ("b.mkv", ))), ("HC", ("R:/n", ("c.mkv", )))):
        mgr.store.groups[key] = [h]
        mgr.store.member_to_key[h] = key

    # P-02 二期: 组行 members = hash 引用数组(每组单成员), 成员明细经平铺行(_seed_view
    # 继承 _member_view 全字段, HR 展示字段同源)取
    flat = {m["hash"]: m for m in mgr._build_flat_view()}
    members = {g["name"]: flat[g["members"][0]] for g in mgr._build_group_view()}
    assert members["Pending.Show"]["hr_tag"] == "!!HR3D!!"
    assert members["Pending.Show"]["hr_tag_done"] == ""
    assert members["Done.Show"]["hr_tag"] == ""
    assert members["Done.Show"]["hr_tag_done"] == "--HR3D--"
    # 未触发 HR 条件时两字段都为空 -> 前端保持普通标签配色
    assert members["NoHR.Show"]["hr_tag"] == "" and members["NoHR.Show"]["hr_tag_done"] == ""
    # 新增展示字段(前端 H&R 栏 / 做种时长与分享率对照列的数据源): 触发与达成布尔 + 要求阈值
    assert members["Pending.Show"]["hr_triggered"] is True
    assert members["Pending.Show"]["hr_satisfied"] is False
    assert members["Pending.Show"]["hr_req_time"] == 3 * 86400 + 12 * 3600
    assert members["Pending.Show"]["hr_req_ratio"] == 0.0
    assert members["Done.Show"]["hr_triggered"] is True and members["Done.Show"]["hr_satisfied"] is True
    assert members["NoHR.Show"]["hr_triggered"] is False


def testhr_view_fields_three_state(tmp_path):
    """详情字段透出站点侧三态与依据 + 删除安全档位×来源(WebUI 可观测性): 接入站点才有值, 未接入全空"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.hr.resolve import HrIdentity, HrJudgement, HrSiteFacts
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="HA", state="stalledUP", downloaded=0))
    conf = TrackerConfig(
        name="HHan", domains=["hhanclub.net"], hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7))
    )
    rec.tracker_conf = conf

    # 未接入 hr_check: 三态四项全空(前端据此不显示三态行, 与既有四个字段的空值口径一致);
    # 本地未触发 + 未做种满 => 删除安全 = warning 疑似辅种黄档(计划 26-09-30-0559 §5, 旧「不适用」作废)
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_state"] == "" and fields["hr_state_text"] == "" and fields["hr_reason"] == ""
    assert fields["hr_safety"] == "warning" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·未达标(疑似辅种)"

    conf.hr_check = SiteHrCheckConfig(
        enabled=True, tracker="hhanclub", hr_page_url="https://hhanclub.net/myhr.php", required_seeding_time=86400.0
    )
    link = mock.Mock()
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR, reason="清单命中·考察中(档位 A)", site_satisfied=False, site="HHan"
    )
    rec.hr_link = link
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False, "hr_triggered = 纯本地触发判据(展示辅助), downloaded=0 不触发"
    assert fields["hr_satisfied"] is False, "命中考察中 => 义务仍在, 恒未达标"
    assert fields["hr_state"] == "hr" and fields["hr_state_text"] == "受管束"
    assert fields["hr_reason"] == "清单命中·考察中(档位 A)"
    # 删除安全档位: 命中考察中 => 在线·考察中, 不能删(v3: identity=HR 恒映射 site_scope)
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "site_scope"
    assert fields["hr_safety_text"] == "在线·考察中"

    # 命中行带档位(A 考察中): 档位即结论 —— 在线·考察中, 不能删(本地值不参与)
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR,
        reason="清单命中·考察中(档位 A)",
        site_satisfied=False,
        facts=HrSiteFacts(lane="A"),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "site_scope"
    assert fields["hr_safety_text"] == "在线·考察中"

    # 命中 B 已达标(终态): 放行 + satisfied —— 可删, 来源「在线·已达标」
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="清单命中·已达标(B, 终态放行)",
        site_satisfied=True,
        facts=HrSiteFacts(lane="B", remain_seconds=0, ratio=1.5),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_satisfied"] is True
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_satisfied"
    assert fields["hr_safety_text"] == "在线·已达标"
    # 站点侧值(两套值对账): 已给的照传, 没给的空串 —— 未知与 0 必须可分(0 = 已达标)
    assert fields["hr_site_lane"] == "B" and fields["hr_site_remain"] == 0
    assert fields["hr_site_ratio"] == 1.5 and fields["hr_site_need"] == "" and fields["hr_site_dl"] == ""

    # 命中 C 未达标(终态): 放行但「考核未通过」红档(不能删桶) —— 站点结论已定
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="清单命中·未达标(C, 考核结论已定, 终态放行)",
        site_satisfied=False,
        facts=HrSiteFacts(lane="C"),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "released_non_hr"
    assert fields["hr_safety"] == "failed" and fields["hr_safety_src"] == "site_unsatisfied"

    # 放行记录(覆盖范围内未列出): 可删, 来源「在线·已核实」
    link.judge.return_value = HrJudgement(identity=HrIdentity.RELEASED, reason="放行记录(覆盖范围内未列出)")
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "released_non_hr"
    assert fields["hr_state_text"] == "已核实·放行"
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_released"
    assert fields["hr_safety_text"] == "在线·已核实，安全放行"

    # D 档已免罪(v3.4, 2026-09-26 用户指令): 站点明确终态结论, 来源单列「在线·已免罪」,
    # 不与缺席证据 site_released 混一个 token
    from auto_qb.hr.model import SOURCE_EXEMPT, SOURCE_SATISFIED

    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="放行记录(D 档已免罪)",
        released_src=SOURCE_EXEMPT,
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_exempt"
    assert fields["hr_safety_text"] == "在线·已免罪"

    # 放行记录无命中行事实 + released_src=satisfied(计划 26-10-02-1936 §3.5): 无事实分支与
    # 带事实分支同文「在线·已达标」—— 同一结论两种写法(旧「在线·已达标(毕业)」)消灭
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="放行记录(已达标移出)",
        released_src=SOURCE_SATISFIED,
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_satisfied"
    assert fields["hr_safety_text"] == "在线·已达标"

    # 本地兜底路径(judge 返回 None: 站点侧无可查键/未发布视图): triggered/satisfied 就是本地结论,
    # 来源统一 local —— 呈现口径与打标流程同源, 不会出现"标签说达标、徽章说不能删"
    rec2 = TorrentRecord.from_torrent(
        FakeTorrent(hash="HB", state="stalledUP", size=512**2, total_size=512**2, downloaded=512**2, seeding_time=3600)
    )
    rec2.tracker_conf = conf
    rec2.hr_link = link
    link.judge.return_value = None
    fields = QbManager.hr_view_fields(rec2)
    assert fields["hr_triggered"] is True and fields["hr_satisfied"] is False
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·未达标"
    rec3 = TorrentRecord.from_torrent(
        FakeTorrent(
            hash="HC", state="stalledUP", size=512**2, total_size=512**2, downloaded=512**2, seeding_time=4 * 86400
        )
    )
    rec3.tracker_conf = conf
    rec3.hr_link = link
    fields = QbManager.hr_view_fields(rec3)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·达标"


def testhr_view_fields_excluded(tmp_path):
    """HR 排除态视图(计划 26-09-28-1805): hr_excluded=True, 触发/达标恒 False,
    删除安全档位短路成空串(「不适用」空白由组装层保证, 计划 26-09-30-0559 §5);
    hr_excluded_by 透出命中来源 token(2026-10-02: 悬停弹窗依据行「按什么排除」的数据源)"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent, make_manager

    make_manager(str(tmp_path / "state.json"))  # 与其它视图测试同构(本函数直调类方法, 不读实例态)
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="HD", state="stalledUP", downloaded=0, tags="noHR"))
    conf = TrackerConfig(
        name="HHan",
        domains=["hhanclub.net"],
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7), exclude_tags=["noHR"]),
    )
    conf.hr_check = SiteHrCheckConfig(
        enabled=True, tracker="hhanclub", hr_page_url="https://hhanclub.net/myhr.php", required_seeding_time=86400.0
    )
    rec.tracker_conf = conf
    rec.hr_link = mock.Mock()  # 排除种子连判定桥都不该被打扰
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_excluded"] is True
    assert fields["hr_excluded_by"] == "tag"
    assert fields["hr_triggered"] is False and fields["hr_satisfied"] is False
    assert fields["hr_state"] == "" and fields["hr_safety"] == "" and fields["hr_safety_text"] == ""
    assert fields["hr_safety_src"] == "" and fields["hr_site_lane"] == ""
    rec.hr_link.judge.assert_not_called()

    # 分类命中(2026-10-02 实报的主场景)与双命中: 来源 token 随命中列表走
    conf.hr.exclude_categories = ["keep"]
    rec_cat = TorrentRecord.from_torrent(FakeTorrent(hash="HG", state="stalledUP", downloaded=0, category="keep"))
    rec_cat.tracker_conf = conf
    fields_cat = QbManager.hr_view_fields(rec_cat)
    assert fields_cat["hr_excluded"] is True and fields_cat["hr_excluded_by"] == "category"
    rec.tags = "noHR"
    rec.category = "keep"
    fields_both = QbManager.hr_view_fields(rec)
    assert fields_both["hr_excluded_by"] == "tag+category", "标签与分类同时命中时 token 合并"

    # 未命中排除表: hr_excluded=False, 行为照旧
    rec2 = TorrentRecord.from_torrent(FakeTorrent(hash="HE", state="stalledUP", downloaded=0, tags="HHan"))
    rec2.tracker_conf = conf
    assert QbManager.hr_view_fields(rec2)["hr_excluded"] is False

    # 空配置分支也带 hr_excluded/hr_excluded_by 键(前端字段一致性守阵消费全键集)
    empty = QbManager.hr_view_fields(TorrentRecord.from_torrent(FakeTorrent(hash="HF")))
    assert empty["hr_excluded"] is False and empty["hr_excluded_by"] == ""
