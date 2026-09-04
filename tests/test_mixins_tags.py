"""test_mixins_tags 测试计划: mixins/tags 标签/分类/HR 辅助方法

## 测试计划(每个测试函数一条)
- test_add_tags_direct: _add_tags 直接调用 client
- test_remove_tags_direct: _remove_tags 直接调用 client
- test_remove_similar_tags: 移除相似标签
- test_create_category_if_not_exists: 分类不存在时创建
- test_fmt_hr: ${required_seeding_time} 模板替换
- test_torrent_log_repr: 种子日志描述 log_repr(含 tracker_conf=None -> Unknown)
- test_add_hr_tag_or_category_satisfied: HR 达标 -> 加达标标签/分类
- test_handle_delete_tags: 处理彻底删除标签任务
- test_handle_delete_tags_if_has_no_torrents: 处理无种子标签清理任务
- test_set_category_empty: 空分类种子 -> 设置分类并记录 auto_categories
- test_set_category_overwrite: overwrite=True 覆盖已有分类
- test_set_category_no_overwrite: 已有非 auto 分类且不覆盖 -> 跳过
- test_set_category_auto_update: auto_categories 内分类自动更新
- test_set_category_same: 目标分类相同 -> 无操作
- test_set_category_dry_run: dry-run 只返回不调用
- test_add_hr_tag_or_category_not_met: HR 未触发 -> 无操作
- test_add_hr_tag_or_category_not_satisfied: 触发但未达标 -> 加普通标签
- test_add_tags_empty: 空标签列表 -> False
- test_add_episode_tags_files_error: 文件列表拉取异常 -> 异常上抛
- test_add_episode_tags_no_episodes: 文件列表无集数 -> 不加标签
- test_remove_similar_tags_empty: 空标签列表 -> False
- test_add_hr_tag_or_category_no_hr: tracker 无 hr -> False
- test_add_hr_tag_or_category_dlsize: dlsize 条件分支
- test_add_hr_tag_or_category_satisfied_tag: satisfied 加达标标签
- test_handle_delete_tags_no_patterns: 无删除模式 -> True
- test_handle_delete_tags_tags_error: 标签列表异常 -> True
- test_handle_delete_tags_if_has_no_torrents_no_patterns: 无模式 -> True
- test_handle_delete_tags_if_has_no_torrents_tags_error: 标签列表异常 -> True
- test_handle_delete_tags_if_has_no_torrents_no_tags: 标签列表为空 -> True
- test_handle_delete_tags_if_has_no_torrents_no_match: 无无种子标签 -> 不删除
"""
import os
import tempfile

import pytest

from auto_qb.qbmanager import QbManager
from auto_qb.rules.actions import AddTagsAction
from helpers import FakeClient, FakeConfig, FakeTorrent, _hr_rule, make_manager, seed_store


def _mgr(state_file):
    return make_manager(state_file)


def test_add_tags_direct():
    """_add_tags: 过滤已存在标签, 返回是否新增"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="A,B")
        assert mgr._add_tags(tor, ["B", "C"], dry_run=False) is True
        assert client.calls[-1] == ("add_tags", ["C"])
        # 全部已存在 -> False, 不调用
        client.calls.clear()
        assert mgr._add_tags(tor, ["A"], dry_run=False) is False
        assert client.calls == []
        # dry-run 不调用
        assert mgr._add_tags(tor, ["D"], dry_run=True) is True
        assert client.calls == []


def test_remove_tags_direct():
    """_remove_tags: 正则匹配移除, 无匹配返回 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.tags = {"HHan", "seed-3D"}
        tor = FakeTorrent(tags="HHan,seed-3D")
        assert mgr._remove_tags(tor, ["regex:^seed-"], dry_run=False) is True
        assert client.calls[-1] == ("remove_tags", ["seed-3D"])
        assert mgr._remove_tags(tor, ["NOPE"], dry_run=False) is False


def test_remove_similar_tags():
    """_remove_similar_tags: 移除大小写不同的相似标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="hhan,HHan")
        # 保留精确匹配, 移除其它大小写变体
        removed = mgr._remove_similar_tags(tor, ["HHan"], dry_run=False)
        assert removed
        assert ("remove_tags", ["hhan"]) in client.calls


def test_create_category_if_not_exists():
    """_create_category_if_not_exists: 已存在不创建/不存在创建/dry-run"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 不存在 -> 创建
        mgr._create_category_if_not_exists("NEW-CAT", dry_run=False)
        assert ("create_category", "NEW-CAT") in client.calls
        # dry-run -> 不调用
        client.calls.clear()
        mgr._create_category_if_not_exists("OTHER", dry_run=True)
        assert client.calls == []


def test_fmt_hr():
    """_fmt_hr: ${required_seeding_time} 替换为 hr 原始值"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        hr = _hr_rule()
        assert mgr._fmt_hr("!!HR${required_seeding_time}!!", hr) == "!!HR3D!!"
        assert mgr._fmt_hr("no-placeholder", hr) == "no-placeholder"


def test_torrent_log_repr():
    """log_repr: '名称' [站点] (hash前8); tracker_conf=None -> Unknown"""
    tor = FakeTorrent(name="Movie.2024", hash="ABC123")
    assert tor.log_repr == "'Movie.2024' [Unknown] (ABC123)"


def test_add_hr_tag_or_category_satisfied():
    """_add_hr_tag_or_category: 满足 HR 条件时添加满意标签/分类, 否则普通标签/分类"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=4 * 86400)
        conf = mgr.config.trackers["HHan"]
        # seeding_time 4D >= 3D+12H, ratio 1.0: satisfied
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False) is True
        assert ("set_category", "--HR3D--") in client.calls


def test_handle_delete_tags():
    """_handle_delete_tags: 按全局 delete_tags 模式彻底删除标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags = ["regex:^seed-"]
        client = FakeClient()
        mgr.client = client
        client.tags = {"seed-3D", "HHan"}
        mgr._handle_delete_tags(None, dry_run=False)
        assert ("delete_tags", {"seed-3D"}) in client.calls


def test_handle_delete_tags_if_has_no_torrents():
    """_handle_delete_tags_if_has_no_torrents: 仅删除无种子的标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        client = FakeClient()
        mgr.client = client
        client.tags = {"orphan-1", "orphan-2"}
        # 无种子使用该标签 -> 删除
        mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False)
        assert ("delete_tags", {"orphan-1", "orphan-2"}) in client.calls


def test_set_category_empty():
    """_set_category: 空分类 -> 设置分类并记录 auto_categories"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="")
        assert mgr._set_category(tor, "HR-DONE", overwrite=False, dry_run=False) is True
        assert ("set_category", "HR-DONE") in client.calls
        assert mgr.state["auto_categories"]["HASH123"] == "HR-DONE"


def test_set_category_overwrite():
    """_set_category: overwrite=True 强制覆盖已有分类, 并记录 auto(后续可再自动更新)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="OLD")
        assert mgr._set_category(tor, "NEW", overwrite=True, dry_run=False) is True
        assert ("set_category", "NEW") in client.calls
        assert mgr.state["auto_categories"]["HASH123"] == "NEW"


def test_set_category_no_overwrite():
    """_set_category: 已有非自动分类且不覆盖 -> 跳过(返回 True 但无调用)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="OLD")
        assert mgr._set_category(tor, "NEW", overwrite=False, dry_run=False) is True
        assert client.calls == []


def test_set_category_auto_update():
    """_set_category: 旧分类属 auto_categories 时可被更新(不覆盖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.state.setdefault("auto_categories", {})["HASH123"] = "OLD"
        tor = FakeTorrent(category="OLD")
        assert mgr._set_category(tor, "NEW", overwrite=False, dry_run=False) is True
        assert ("set_category", "NEW") in client.calls
        assert mgr.state["auto_categories"]["HASH123"] == "NEW"


def test_set_category_same():
    """_set_category: 分类相同 -> False 不调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="SAME")
        assert mgr._set_category(tor, "SAME", overwrite=True, dry_run=False) is False
        assert client.calls == []


def test_set_category_dry_run():
    """_set_category: dry_run 不调用客户端也不记录 auto"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="")
        assert mgr._set_category(tor, "NEW", overwrite=False, dry_run=True) is True
        assert client.calls == []
        assert "HASH123" not in mgr.state.get("auto_categories", {})


def test_add_hr_tag_or_category_not_met():
    """_add_hr_tag_or_category: 触发条件未满足(排除辅种) -> 不添加"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.hr = _hr_rule(add_tag="HR", add_category="", add_category_for_satisfied="")
        tor = FakeTorrent(tags="", downloaded=0, total_size=100 * 1024**2)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False) is False
        assert client.calls == []


def test_add_hr_tag_or_category_not_satisfied():
    """_add_hr_tag_or_category: 触发满足但做种不足 -> 添加普通 HR 标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.hr = _hr_rule(add_tag="HR", add_category="", add_category_for_satisfied="")
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False) is True
        assert ("add_tags", ["HR"]) in client.calls


def test_add_tags_empty():
    """_add_tags: 空标签列表 -> False 不调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        assert mgr._add_tags(FakeTorrent(tags=""), [], dry_run=False) is False
        assert client.calls == []


def test_add_episode_tags_files_error():
    """_add_episode_tags: 文件列表拉取异常 -> 异常上抛(不缓存, 由 run 主循环兜底)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client

        def boom(h):
            raise RuntimeError("api down")

        client.torrents_files = boom
        tor = FakeTorrent(hash="H1", tags="")
        seed_store(mgr, [tor])
        with pytest.raises(RuntimeError, match="api down"):
            mgr._add_episode_tags(tor, dry_run=False)
        assert client.calls == []


def test_add_episode_tags_no_episodes():
    """_add_episode_tags: 文件列表无集数(电影) -> 不加标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1", tags="")
        seed_store(mgr, [tor])
        mgr._add_episode_tags(tor, dry_run=False)
        assert client.calls == [], "无集数不应加标签"


def test_remove_similar_tags_empty():
    """_remove_similar_tags: 空标签列表 -> False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        assert mgr._remove_similar_tags(FakeTorrent(tags="HHan"), [], dry_run=False) is False
        assert client.calls == []


def test_add_hr_tag_or_category_no_hr():
    """_add_hr_tag_or_category: tracker 无 hr 配置 -> False 无操作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.hr = None
        assert mgr._add_hr_tag_or_category(FakeTorrent(tags=""), conf, dry_run=False) is False
        assert client.calls == []


def test_add_hr_tag_or_category_dlsize():
    """_add_hr_tag_or_category: dlsize 条件分支(下载量达标)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.hr = _hr_rule(
            condition=("dlsize", 50 * 1024**2),
            add_tag="HR",
            add_category="",
            add_category_for_satisfied="",
        )
        tor = FakeTorrent(tags="", downloaded=60 * 1024**2, seeding_time=0)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False) is True
        assert ("add_tags", ["HR"]) in client.calls


def test_add_hr_tag_or_category_satisfied_tag():
    """_add_hr_tag_or_category: satisfied 且有 add_tag_for_satisfied -> 加达标标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.hr = _hr_rule(
            add_tag="",
            add_category="",
            add_tag_for_satisfied="SATISFIED",
            add_category_for_satisfied="",
        )
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=4 * 86400)
        assert mgr._add_hr_tag_or_category(tor, conf, dry_run=False) is True
        assert ("add_tags", ["SATISFIED"]) in client.calls


def test_handle_delete_tags_no_patterns():
    """_handle_delete_tags: 无删除模式 -> True 不调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags = []
        client = FakeClient()
        mgr.client = client
        assert mgr._handle_delete_tags(None, dry_run=False) is True
        assert client.calls == []


def test_handle_delete_tags_tags_error():
    """_handle_delete_tags: 标签列表拉取异常 -> 返回 True 不中断"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags = ["regex:^seed-"]
        client = FakeClient()
        mgr.client = client

        def boom():
            raise RuntimeError("api down")

        client.torrents_tags = boom
        assert mgr._handle_delete_tags(None, dry_run=False) is True
        assert client.calls == []


def test_handle_delete_tags_if_has_no_torrents_no_patterns():
    """_handle_delete_tags_if_has_no_torrents: 无模式 -> True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags_if_has_no_torrents = []
        client = FakeClient()
        mgr.client = client
        assert mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert client.calls == []


def test_handle_delete_tags_if_has_no_torrents_tags_error():
    """_handle_delete_tags_if_has_no_torrents: 标签列表异常 -> True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        client = FakeClient()
        mgr.client = client

        def boom():
            raise RuntimeError("api down")

        client.torrents_tags = boom
        assert mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert client.calls == []


def test_handle_delete_tags_if_has_no_torrents_no_tags():
    """_handle_delete_tags_if_has_no_torrents: 标签列表为空 -> True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        client = FakeClient()
        mgr.client = client
        client.tags = set()
        assert mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert client.calls == []


def test_handle_delete_tags_if_has_no_torrents_no_match():
    """_handle_delete_tags_if_has_no_torrents: 标签均有种子使用 -> 不删除"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        client = FakeClient()
        mgr.client = client
        client.tags = {"orphan-1"}
        seed_store(mgr, [FakeTorrent(hash="H1", tags="orphan-1")])
        assert mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert client.calls == [], "有种子使用时不删除"
