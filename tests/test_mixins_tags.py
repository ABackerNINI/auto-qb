"""mixins/tags 模块测试: 标签/分类/HR 辅助方法"""
import os
import tempfile

from auto_qb.qbmanager import QbManager
from auto_qb.rules.actions import AddTagsAction
from helpers import FakeClient, FakeConfig, FakeTorrent, _hr_rule, make_ctx, make_manager


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
        assert ("remove_tags", "hhan") in client.calls


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


def test_torrent_desc():
    """_torrent_desc: '名称 [hash]'"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        tor = FakeTorrent(name="Movie.2024", hash="ABC123")
        assert mgr._torrent_desc(tor) == "Movie.2024 [ABC123]"


def test_add_hr_tag_or_category_satisfied():
    """_add_hr_tag_or_category: 满足 HR 条件时添加满意标签/分类, 否则普通标签/分类"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=4 * 86400)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.matched_tracker_confs()[0]
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
