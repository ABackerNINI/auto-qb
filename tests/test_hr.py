"""test_hr 测试计划: HR 规则

## 测试计划(每个测试函数一条)
- test_builtin_hr_category_auto_update_from_state: 内置 HR 分类按状态自动更新
- test_tracker_hr_overrides_global: 站点 HR 覆盖全局配置
- test_hr_required_share_ratio: required_share_ratio 达标判定
- test_tracker_remove_similar_tags_override: 站点 remove_similar_tags 覆盖全局
- test_hr_dlratio_trigger: dlratio 条件达线判定; 未触发但未做种满 -> 仍打 HR 标签(全量纳入, 计划 26-09-30-0559)
- test_hr_dlsize_trigger: dlsize 条件(下载量绝对值)达线判定; 未触发但未做种满 -> 仍打 HR 标签
- test_hr_satisfied_seeding_time: 做种时长 >= required+extra -> satisfied 分类; 否则普通 HR 分类
- test_hr_satisfied_share_ratio: 分享率达标(时长不足) -> satisfied 标签
- test_hr_aux_seed_excluded: downloaded=0(dlratio=0)本地不触发, 但未做种满 -> 打 HR 标签(疑似辅种全量纳入)
- test_hr_overwrite_category_semantics: _set_category 覆盖语义(跳过/覆盖/自动分类可更新)
- test_hr_tracker_without_hr_skips: 站点无 hr 配置 -> 不应用 HR(即使全局有默认)
- test_hr_exclude_tag_skips_tagging: HR 排除命中标签/分类 -> 不加任何 HR 标签/分类(未命中照常)
"""
import os
import tempfile

from auto_qb.core.qbmanager import QbManager
from helpers import FakeClient, FakeConfig, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store


def test_builtin_hr_category_auto_update_from_state():
    """内置 HR 分类保存状态并可更新此前自动设置的分类"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(downloaded=100 * 1024**2, category="")
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        tor.tracker_conf = mgr.config.trackers["HHan"]

        assert mgr._handle_maintenance(tor, dry_run=False)
        mgr.save_state()
        assert mgr.state["auto_categories"]["HASH123"] == "!!HR3D!!"

        mgr2 = make_manager(state_file)
        client2 = FakeClient()
        mgr2.client = client2
        tor.category = "!!HR3D!!"
        client2.torrents["HASH123"] = tor
        seed_store(mgr2)
        tor.tracker_conf = mgr2.config.trackers["HHan"]
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_category="NEW-HR")
        mgr2._handle_maintenance(tor, dry_run=False)
        assert client2.category == "NEW-HR"
        assert mgr2.state["auto_categories"]["HASH123"] == "NEW-HR"


def test_tracker_hr_overrides_global():
    """站点 hr 输出设置覆盖全局(分类格式 + overwrite), 未设置的字段用全局默认"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        # 全局默认: add_category = 全局格式
        cfg.hr = _hr_rule(add_category="GLOBAL-HR", add_category_for_satisfied="GLOBAL-DONE")
        # 站点: 覆盖 add_category, 保留 satisfied 用全局默认
        site_hr = _hr_rule(
            add_category="SITE-HR!!",
            overwrite_category=True,
        )
        cfg.trackers = {"HHan": FakeTracker("HHan", hr=site_hr)}

        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        # seeding_time 未达 required+extra: 只触发 add_category(站点覆盖), 不触发 satisfied 分类
        tor = FakeTorrent(downloaded=100 * 1024**2, seeding_time=100, ratio=1.0)
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        tor.tracker_conf = cfg.trackers["HHan"]

        mgr._handle_maintenance(tor, dry_run=False)

        # 站点覆盖: 分类应为 SITE-HR!!(非全局 GLOBAL-HR)
        assert client.category == "SITE-HR!!", f"站点分类覆盖失败: {client.category}"

        # satisfied 场景: 站点覆盖 satisfied 分类格式 + 允许覆盖
        cfg.trackers["HHan"].hr = _hr_rule(
            add_category_for_satisfied="SITE-DONE!!",
            overwrite_category_for_satisfied=True,
        )
        client2 = FakeClient()
        mgr2 = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        mgr2.client = client2
        tor2 = FakeTorrent(downloaded=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10, ratio=1.0)
        client2.torrents["HASH123"] = tor2
        seed_store(mgr2)
        tor2.tracker_conf = cfg.trackers["HHan"]
        mgr2._handle_maintenance(tor2, dry_run=False)
        assert client2.category == "SITE-DONE!!", f"站点 satisfied 分类覆盖失败: {client2.category}"


def test_hr_required_share_ratio():
    """required_share_ratio 条件(做种时长不够但分享率达标 -> satisfied)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        # 站点: 3D+12H, 分享率 2.0, 但做种时长远不够
        mgr.config.trackers["HHan"].hr = _hr_rule(
            required_seeding_time=3 * 86400,
            required_seeding_time_raw="3D",
            extra_seeding_time=12 * 3600,
            required_share_ratio=2.0,
        )
        tor = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=100, ratio=2.5)  # 时长不足但分享率达标
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        tor.tracker_conf = mgr.config.trackers["HHan"]
        handled = mgr._handle_maintenance(tor, dry_run=False)
        assert handled, "分享率达标应视为 HR satisfied"
        assert client.category == "--HR3D--", f"分享率达标应加 satisfied 分类: {client.category}"

        # 分享率也不达标: 不 satisfied(仅普通 HR 分类)
        client2 = FakeClient()
        mgr2 = make_manager(state_file)
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            required_seeding_time=3 * 86400,
            required_seeding_time_raw="3D",
            extra_seeding_time=12 * 3600,
            required_share_ratio=2.0,
        )
        tor2 = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=100, ratio=1.0)
        client2.torrents["HASH123"] = tor2
        seed_store(mgr2)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        mgr2._handle_maintenance(tor2, dry_run=False)
        assert client2.category != "--HR3D--", "时长与分享率均不达标不应 satisfied"


def test_tracker_remove_similar_tags_override():
    """站点 remove_similar_tags=true 覆盖全局 false, 触发相似标签删除"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.remove_similar_tags = False  # 全局关闭
        cfg.trackers = {
            "HHan":
                FakeTracker("HHan", hr=None, remove_similar_tags=True)  # 站点开启
        }

        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        # 已有类似标签 "hhan"(小写), 站点 tags 为 "HHan"
        tor = FakeTorrent(tags="hhan,other")
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        tor.tracker_conf = cfg.trackers["HHan"]

        mgr._handle_maintenance(tor, dry_run=False)

        # 全局关闭 + 站点开启 -> 应删除类似标签 hhan
        assert ("remove_tags", {"hhan"}) in client.calls or any(
            c[0] == "remove_tags" for c in client.calls
        ), f"站点 remove_similar_tags 未生效: {client.calls}"


def test_hr_dlratio_trigger():
    """HR 打标分流(计划 26-09-30-0559 §4): 本地触发判据只管「本机下载了吗」;
    未触发但未做种满的种子(转移种/疑似辅种)同样打 HR 标签 —— 全量纳入"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(add_tag="!!HR3D!!", add_category="")
        conf = mgr.config.trackers["HHan"]

        # 触发(0.7 >= 0.7)+ 未做种满 -> HR 标签
        tor = FakeTorrent(downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor.tracker_conf = conf
        assert tor.check_hr_condition() is True, "本地触发判据: 0.7 >= 0.7"
        assert mgr._add_hr_tag_or_category(tor, dry_run=False)
        assert ("add_tags", ["!!HR3D!!"]) in client.calls, f"应添加 HR 标签: {client.calls}"

        # 未触发(0.5 < 0.7)+ 未做种满 -> 仍打 HR 标签(旧断言「不触发不打标」作废)
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_tag="!!HR3D!!", add_category="")
        tor2 = FakeTorrent(downloaded=50 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert tor2.check_hr_condition() is False, "本地未触发(展示辅助判据)"
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False) is True
        assert ("add_tags", ["!!HR3D!!"]) in client2.calls, f"未触发但未达标 -> 疑似辅种也打 HR 标签: {client2.calls}"


def test_hr_dlsize_trigger():
    """HR 打标分流: dlsize 条件达线判定; 未触发但未做种满 -> 仍打 HR 标签(全量纳入)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(
            condition=("dlsize", 10 * 1024**2), add_tag="DLSIZE-HR", add_category=""
        )
        conf = mgr.config.trackers["HHan"]

        tor = FakeTorrent(downloaded=10 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor.tracker_conf = conf
        assert mgr._add_hr_tag_or_category(tor, dry_run=False)
        assert ("add_tags", ["DLSIZE-HR"]) in client.calls, f"dlsize 达标应触发: {client.calls}"

        # 下载量不足(即使比例高)-> 本地不触发, 但未做种满 -> 仍打 HR 标签
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            condition=("dlsize", 10 * 1024**2), add_tag="DLSIZE-HR", add_category=""
        )
        tor2 = FakeTorrent(downloaded=9 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert tor2.check_hr_condition() is False, "9MiB < 10MiB: 本地未触发"
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False) is True
        assert ("add_tags", ["DLSIZE-HR"]) in client2.calls, f"未触发但未达标 -> 仍打 HR 标签: {client2.calls}"


def test_hr_dlsize_small_completed_triggers():
    """HR 触发: dlsize 条件, 种子小于触发量但已完全下载 -> 仍视为触发(想法.md 已知问题修复)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(
            condition=("dlsize", 10 * 1024**2), add_tag="DLSIZE-HR", add_category=""
        )
        conf = mgr.config.trackers["HHan"]

        # 完全下载但总量小于触发量: downloaded=5MiB < 10MiB, progress=1.0 -> 应触发
        tor = FakeTorrent(downloaded=5 * 1024**2, total_size=5 * 1024**2, progress=1.0, seeding_time=0)
        tor.tracker_conf = conf
        assert mgr._add_hr_tag_or_category(tor, dry_run=False)
        assert ("add_tags", ["DLSIZE-HR"]) in client.calls, f"小种子完全下载应触发: {client.calls}"

        # 未完全下载的小种子(downloaded < total_size): 本地不触发, 但未做种满 -> 仍打 HR 标签
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            condition=("dlsize", 10 * 1024**2), add_tag="DLSIZE-HR", add_category=""
        )
        tor2 = FakeTorrent(downloaded=2 * 1024**2, total_size=5 * 1024**2, amount_left=3 * 1024**2, seeding_time=0)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert tor2.check_hr_condition() is False, "未完整下载: 本地未触发"
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False) is True
        assert ("add_tags", ["DLSIZE-HR"]) in client2.calls, f"未触发但未达标 -> 仍打 HR 标签: {client2.calls}"


def test_hr_satisfied_seeding_time():
    """HR satisfied: 做种时长 >= required+extra -> satisfied 分类; 否则普通 HR 分类"""
    with tempfile.TemporaryDirectory() as td:
        # satisfied: 时长 3D+12H+10s 达标
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]  # 默认: 分类 !!/--HR3D!!/--HR3D--
        tor = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10)
        tor.tracker_conf = conf
        assert mgr._add_hr_tag_or_category(tor, dry_run=False)
        assert client.category == "--HR3D--", f"时长达标应加 satisfied 分类: {client.category}"

        # 时长不足 -> 普通 HR 分类
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        conf2 = mgr2.config.trackers["HHan"]
        tor2 = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=100)
        tor2.tracker_conf = conf2
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False)
        assert client2.category == "!!HR3D!!", f"时长不足应加普通 HR 分类: {client2.category}"


def test_hr_satisfied_share_ratio():
    """HR satisfied: 做种时长不足但分享率达标 -> satisfied 标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(
            required_share_ratio=2.0,
            add_tag="",
            add_category="",
            add_tag_for_satisfied="DONE",
            add_category_for_satisfied=""
        )
        conf = mgr.config.trackers["HHan"]

        # 时长不足但 ratio 2.5 >= 2.0 -> satisfied
        tor = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=100, ratio=2.5)
        tor.tracker_conf = conf
        assert mgr._add_hr_tag_or_category(tor, dry_run=False)
        assert ("add_tags", ["DONE"]) in client.calls, f"分享率达标应加 satisfied 标签: {client.calls}"

        # 分享率与时长均不达标 -> 无输出(输出字段为空)
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            required_share_ratio=2.0,
            add_tag="",
            add_category="",
            add_tag_for_satisfied="DONE",
            add_category_for_satisfied=""
        )
        tor2 = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=100, ratio=1.0)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False) is False
        assert client2.calls == [], f"均不达标不应有输出: {client2.calls}"


def test_hr_aux_seed_excluded():
    """疑似辅种(downloaded=0, dlratio=0)本地不触发, 但未做种满 -> 打 HR 标签(全量纳入, 计划 26-09-30-0559)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]  # 默认 hr: 3D@70%+12H, add_category=!!HR3D!!
        tor = FakeTorrent(downloaded=0, total_size=100 * 1024**2, seeding_time=0)
        tor.tracker_conf = conf
        assert tor.check_hr_condition() is False, "本地不触发(展示辅助判据)"
        assert mgr._add_hr_tag_or_category(tor, dry_run=False) is True
        assert ("set_category", "!!HR3D!!") in client.calls, f"疑似辅种未做种满 -> 打 HR 分类: {client.calls}"

        # total_size=0 时 dlratio 兜底为 0(除数保护), 本地同样不触发
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        tor2 = FakeTorrent(downloaded=100, total_size=0, seeding_time=0)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert tor2.check_hr_condition() is False
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False) is True
        assert ("set_category", "!!HR3D!!") in client2.calls


def test_hr_overwrite_category_semantics():
    """_set_category 覆盖语义: overwrite=false 跳过已有分类; =true 覆盖; 程序自动分类可更新"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="MANUAL")

        # overwrite=False: 已有非自动分类 -> 跳过(已处理但无 API 调用)
        assert mgr._set_category(tor, "HR-CAT", overwrite=False, dry_run=False)
        assert client.calls == [], f"不应覆盖已有分类: {client.calls}"
        assert tor.category == "MANUAL"

        # overwrite=True: 强制覆盖
        assert mgr._set_category(tor, "HR-CAT", overwrite=True, dry_run=False)
        assert ("set_category", "HR-CAT") in client.calls, f"强制覆盖应设置分类: {client.calls}"
        assert client.category == "HR-CAT"
        assert "HR-CAT" not in mgr.state.get("auto_categories", {}), "强制覆盖不记录自动分类"

        # 程序自动分类(auto_categories 记录) + overwrite=False -> 可更新
        mgr.state.setdefault("auto_categories", {})[tor.hash] = "AUTO-OLD"
        client.calls.clear()
        tor.category = "AUTO-OLD"
        assert mgr._set_category(tor, "AUTO-NEW", overwrite=False, dry_run=False)
        assert ("set_category", "AUTO-NEW") in client.calls, f"自动分类应可更新: {client.calls}"
        assert mgr.state["auto_categories"][tor.hash] == "AUTO-NEW"


def test_hr_tracker_without_hr_skips():
    """站点无 hr 配置 -> 不应用 HR(合并发生在配置加载期; 运行时 hr=None 直接跳过)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.hr = _hr_rule(add_category="GLOBAL-HR")  # 全局有 HR 默认
        cfg.trackers = {"HHan": FakeTracker("HHan", hr=None)}  # 站点未配置 hr

        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10)
        tor.tracker_conf = cfg.trackers["HHan"]
        assert mgr._add_hr_tag_or_category(tor, dry_run=False) is False
        assert client.calls == [], f"站点无 hr 不应应用全局 HR: {client.calls}"


def test_hr_exclude_tag_skips_tagging():
    """HR 排除(计划 26-09-28-1805): 命中 exclude_tags/exclude_categories 的种子不加任何 HR 标签/分类

    触发条件本应满足, 排除压过一切 -> 零写入; 未命中排除表的种子照常打标(零静默变更对照)。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(
            add_tag="!!HR3D!!", add_category="--HR3D--", exclude_tags=["noHR"], exclude_categories=["free"]
        )
        conf = mgr.config.trackers["HHan"]

        # 命中排除标签: 零写入(不打标也不打分类)
        tor = FakeTorrent(tags="HHan,noHR", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor.tracker_conf = conf
        assert mgr._add_hr_tag_or_category(tor, dry_run=False) is False
        assert client.calls == [], f"排除种子不应有任何写入: {client.calls}"

        # 命中排除分类同理
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_tag="!!HR3D!!", exclude_categories=["free"])
        tor2 = FakeTorrent(category="free", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert mgr2._add_hr_tag_or_category(tor2, dry_run=False) is False
        assert client2.calls == [], f"排除分类不应有任何写入: {client2.calls}"

        # 对照: 排除表配了但未命中 -> 照常打标
        mgr3 = make_manager(os.path.join(td, "state3.json"))
        client3 = FakeClient()
        mgr3.client = client3
        mgr3.config.trackers["HHan"].hr = _hr_rule(add_tag="!!HR3D!!", add_category="", exclude_tags=["noHR"])
        tor3 = FakeTorrent(tags="HHan", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        tor3.tracker_conf = mgr3.config.trackers["HHan"]
        assert mgr3._add_hr_tag_or_category(tor3, dry_run=False) is True
        assert ("add_tags", ["!!HR3D!!"]) in client3.calls, f"未命中排除表应照常打标: {client3.calls}"
