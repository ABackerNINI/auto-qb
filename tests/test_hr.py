"""test_hr 测试计划: HR 规则

## 测试计划(每个测试函数一条)
- test_builtin_hr_category_auto_update_from_state: 内置 HR 分类按状态自动更新
- test_tracker_hr_overrides_global: 站点 HR 覆盖全局配置
- test_hr_required_share_ratio: required_share_ratio 达标判定
- test_tracker_remove_similar_tags_override: 站点 remove_similar_tags 覆盖全局
- test_hr_dlratio_trigger: dlratio 条件达标才添加 HR 标签, 未达标排除(辅种保护)
- test_hr_dlsize_trigger: dlsize 条件(下载量绝对值)达标才触发
- test_hr_satisfied_seeding_time: 做种时长 >= required+extra -> satisfied 分类; 否则普通 HR 分类
- test_hr_satisfied_share_ratio: 分享率达标(时长不足) -> satisfied 标签
- test_hr_aux_seed_excluded: downloaded=0(dlratio=0) -> 不触发任何 HR 输出
- test_hr_overwrite_category_semantics: _set_category 覆盖语义(跳过/覆盖/自动分类可更新)
- test_hr_tracker_without_hr_skips: 站点无 hr 配置 -> 不应用 HR(即使全局有默认)
"""
import os
import tempfile

from auto_qb.qbmanager import QbManager
from auto_qb.taskqueue import Task
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
        task = Task(
            "internal",
            "maintenance",
            hash="HASH123",
            interval=60,
            tracker_conf=mgr.config.trackers["HHan"],
            handler=mgr._handle_maintenance
        )

        assert mgr._handle_maintenance(task, dry_run=False)
        mgr.save_state()
        assert mgr.state["auto_categories"]["HASH123"] == "!!HR3D!!"

        mgr2 = make_manager(state_file)
        client2 = FakeClient()
        mgr2.client = client2
        tor.category = "!!HR3D!!"
        client2.torrents["HASH123"] = tor
        seed_store(mgr2)
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_category="NEW-HR")
        task2 = Task(
            "internal",
            "maintenance",
            hash="HASH123",
            interval=60,
            tracker_conf=mgr2.config.trackers["HHan"],
            handler=mgr2._handle_maintenance
        )
        mgr2._handle_maintenance(task2, dry_run=False)
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

        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # seeding_time 未达 required+extra: 只触发 add_category(站点覆盖), 不触发 satisfied 分类
        tor = FakeTorrent(downloaded=100 * 1024**2, seeding_time=100, ratio=1.0)
        client.torrents["HASH123"] = tor
        seed_store(mgr)

        task = Task(
            "internal",
            "maintenance",
            hash="HASH123",
            interval=60,
            tracker_conf=cfg.trackers["HHan"],
            handler=mgr._handle_maintenance
        )
        mgr._handle_maintenance(task, dry_run=False)

        # 站点覆盖: 分类应为 SITE-HR!!(非全局 GLOBAL-HR)
        assert client.category == "SITE-HR!!", f"站点分类覆盖失败: {client.category}"

        # satisfied 场景: 站点覆盖 satisfied 分类格式 + 允许覆盖
        cfg.trackers["HHan"].hr = _hr_rule(
            add_category_for_satisfied="SITE-DONE!!",
            overwrite_category_for_satisfied=True,
        )
        client2 = FakeClient()
        mgr2 = QbManager("", config=cfg)
        mgr2.client = client2
        tor2 = FakeTorrent(downloaded=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10, ratio=1.0)
        client2.torrents["HASH123"] = tor2
        seed_store(mgr2)
        mgr2._handle_maintenance(task, dry_run=False)
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
        task = Task(
            "internal",
            "maintenance",
            hash="HASH123",
            interval=60,
            tracker_conf=mgr.config.trackers["HHan"],
            handler=mgr._handle_maintenance
        )
        handled = mgr._handle_maintenance(task, dry_run=False)
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
        task2 = Task(
            "internal",
            "maintenance",
            hash="HASH123",
            interval=60,
            tracker_conf=mgr2.config.trackers["HHan"],
            handler=mgr2._handle_maintenance
        )
        mgr2._handle_maintenance(task2, dry_run=False)
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

        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # 已有类似标签 "hhan"(小写), 站点 tags 为 "HHan"
        tor = FakeTorrent(tags="hhan,other")
        client.torrents["HASH123"] = tor
        seed_store(mgr)

        task = Task(
            "internal",
            "maintenance",
            hash="HASH123",
            interval=60,
            tracker_conf=cfg.trackers["HHan"],
            handler=mgr._handle_maintenance
        )
        mgr._handle_maintenance(task, dry_run=False)

        # 全局关闭 + 站点开启 -> 应删除类似标签 hhan
        assert ("remove_tags", {"hhan"}) in client.calls or any(
            c[0] == "remove_tags" for c in client.calls
        ), f"站点 remove_similar_tags 未生效: {client.calls}"


def test_hr_dlratio_trigger():
    """HR 触发: dlratio 条件(下载比例 >= 阈值)达标才添加标签, 未达标排除(辅种保护)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(add_tag="!!HR3D!!", add_category="")
        conf = mgr.config.trackers["HHan"]

        # 达标: downloaded/total = 0.7 >= 0.7 -> 添加 HR 标签
        tor = FakeTorrent(downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False)
        assert ("add_tags", ["!!HR3D!!"]) in client.calls, f"应添加 HR 标签: {client.calls}"

        # 未达标: 0.5 < 0.7 -> 不触发(无任何调用)
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_tag="!!HR3D!!", add_category="")
        tor2 = FakeTorrent(downloaded=50 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        assert mgr2._add_hr_tag_or_category(tor2, mgr2.config.trackers["HHan"], dry_run=False) is False
        assert client2.calls == [], f"未达标不应触发: {client2.calls}"


def test_hr_dlsize_trigger():
    """HR 触发: dlsize 条件(下载量绝对值 >= 阈值)达标才触发"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers["HHan"].hr = _hr_rule(
            condition=("dlsize", 10 * 1024**2), add_tag="DLSIZE-HR", add_category=""
        )
        conf = mgr.config.trackers["HHan"]

        tor = FakeTorrent(downloaded=10 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False)
        assert ("add_tags", ["DLSIZE-HR"]) in client.calls, f"dlsize 达标应触发: {client.calls}"

        # 下载量不足(即使比例高) -> 不触发
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            condition=("dlsize", 10 * 1024**2), add_tag="DLSIZE-HR", add_category=""
        )
        tor2 = FakeTorrent(downloaded=9 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        assert mgr2._add_hr_tag_or_category(tor2, mgr2.config.trackers["HHan"], dry_run=False) is False
        assert client2.calls == [], f"下载量不足不应触发: {client2.calls}"


def test_hr_satisfied_seeding_time():
    """HR satisfied: 做种时长 >= required+extra -> satisfied 分类; 否则普通 HR 分类"""
    with tempfile.TemporaryDirectory() as td:
        # satisfied: 时长 3D+12H+10s 达标
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]  # 默认: 分类 !!/--HR3D!!/--HR3D--
        tor = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False)
        assert client.category == "--HR3D--", f"时长达标应加 satisfied 分类: {client.category}"

        # 时长不足 -> 普通 HR 分类
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        conf2 = mgr2.config.trackers["HHan"]
        tor2 = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=100)
        assert mgr2._add_hr_tag_or_category(tor2, conf2, dry_run=False)
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
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False)
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
        assert mgr2._add_hr_tag_or_category(tor2, mgr2.config.trackers["HHan"], dry_run=False) is False
        assert client2.calls == [], f"均不达标不应有输出: {client2.calls}"


def test_hr_aux_seed_excluded():
    """HR 辅种排除: downloaded=0(total_size>0 时 dlratio=0) -> 不触发任何 HR 输出"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]  # 默认 hr: 3D@70%+12H
        tor = FakeTorrent(downloaded=0, total_size=100 * 1024**2, seeding_time=0)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False) is False
        assert client.calls == [], f"辅种不应触发 HR: {client.calls}"

        # total_size=0 时 dlratio 兜底为 0(除数保护), 同样排除
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        client2 = FakeClient()
        mgr2.client = client2
        tor2 = FakeTorrent(downloaded=100, total_size=0, seeding_time=0)
        assert mgr2._add_hr_tag_or_category(tor2, mgr2.config.trackers["HHan"], dry_run=False) is False
        assert client2.calls == []


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

        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10)
        assert mgr._add_hr_tag_or_category(tor, cfg.trackers["HHan"], dry_run=False) is False
        assert client.calls == [], f"站点无 hr 不应应用全局 HR: {client.calls}"
