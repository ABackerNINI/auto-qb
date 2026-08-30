"""test_hr 测试计划: HR 规则

## 测试计划(每个测试函数一条)
- test_builtin_hr_category_auto_update_from_state: 内置 HR 分类按状态自动更新
- test_tracker_hr_overrides_global: 站点 HR 覆盖全局配置
- test_hr_required_share_ratio: required_share_ratio 达标判定
- test_tracker_remove_similar_tags_override: 站点 remove_similar_tags 覆盖全局
"""
import os
import tempfile

from auto_qb.qbmanager import QbManager
from auto_qb.taskqueue import Task
from helpers import FakeClient, FakeConfig, FakeTorrent, FakeTracker, _hr_rule, make_manager


def test_builtin_hr_category_auto_update_from_state():
    """内置 HR 分类保存状态并可更新此前自动设置的分类"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(downloaded=100 * 1024**2, category="")
        client.torrents["HASH123"] = tor
        task = Task(
            "internal",
            "maintenance",
            torrent_hash="HASH123",
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
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_category="NEW-HR")
        task2 = Task(
            "internal",
            "maintenance",
            torrent_hash="HASH123",
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

        task = Task(
            "internal",
            "maintenance",
            torrent_hash="HASH123",
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
        tor = FakeTorrent(tags="HHan", seeding_time=100, ratio=2.5)  # 时长不足但分享率达标
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "分享率达标应视为 HR satisfied"
        assert client.category == "HR-DONE", f"分享率达标应加 HR-DONE: {client.category}"

        # 分享率也不达标: 不处理
        client2 = FakeClient()
        mgr2 = make_manager(state_file)
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            required_seeding_time=3 * 86400,
            required_seeding_time_raw="3D",
            extra_seeding_time=12 * 3600,
            required_share_ratio=2.0,
        )
        tor2 = FakeTorrent(tags="HHan", seeding_time=100, ratio=1.0)
        handled2 = mgr2.process_torrent(tor2, dry_run=False)
        assert handled2 is False or "HR-DONE" not in client2.tags, \
            f"时长与分享率均不达标不应 satisfied: {client2.calls}"


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

        task = Task(
            "internal",
            "maintenance",
            torrent_hash="HASH123",
            interval=60,
            tracker_conf=cfg.trackers["HHan"],
            handler=mgr._handle_maintenance
        )
        mgr._handle_maintenance(task, dry_run=False)

        # 全局关闭 + 站点开启 -> 应删除类似标签 hhan
        assert ("remove_tags", {"hhan"}) in client.calls or any(
            c[0] == "remove_tags" for c in client.calls
        ), f"站点 remove_similar_tags 未生效: {client.calls}"
