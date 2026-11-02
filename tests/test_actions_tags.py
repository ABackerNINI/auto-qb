"""test_actions_tags 测试计划: rules/actions 动作插件执行语义

## 测试计划(每个测试函数一条)
- test_add_tags: 添加标签动作: 直接调用 client.add_tags
- test_remove_tags: 移除标签动作: 调用 client.remove_tags
- test_add_category_overwrite_semantics: 加分类动作的 overwrite 覆盖语义
- test_remove_category: 移除分类动作
- test_add_category_create_error: 创建分类失败被吞掉, set_category 仍执行
- test_remove_tags_dry_run: remove_tags dry-run 命中不打 API (P2-a)
- test_add_category_existing_no_recreate_and_dry_run: add_category 已存在不重建 / dry-run 跳过整段 (P2-a)
- test_remove_category_dry_run: remove_category dry-run (P2-a)
- test_add_category_overwrite_switch: add_category 的 overwrite 开关读取(显式 true/false 与缺省)
- test_add_remove_tags_string_spec_not_split: 字符串 spec 不得被 list() 拆成单字符
- test_add_category_format_default: add_category 缺 format 键时兜底空串(不得产出 "None"/"XXXX")
- test_add_category_creates_named_category: 建分类时 create_category 收到真实分类名
"""

import os

import tempfile

from unittest.mock import patch

from auto_qb.rules.base import ActionResult, Rule, VERDICT_EXECUTED, VERDICT_RETRY

from auto_qb.rules.actions import (
    AddCategoryAction,
    AddTagsAction,
    CheckAction,
    DownloadSpeedLimitAction,
    MoveToAction,
    ReannounceAction,
    RemoveCategoryAction,
    RemoveTagsAction,
    StartAction,
    StopAction,
    UploadSpeedLimitAction,
)

from helpers import capture_logs, drive_skip, FakeClient, FakeTorrent, make_ctx, make_manager, seed_store


def test_add_tags():
    """添加标签: 新标签/已存在 skip/变量替换/dry-run"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="HHan")
        ctx = make_ctx(mgr, tor, client)
        r = AddTagsAction(["HHan", "seed-${required_seeding_time}"]).execute(ctx)
        assert r.is_ok, f"应添加标签: {r}"
        assert ("add_tags", ["seed-3D"]) in client.calls
        # 已存在 -> skip
        r2 = AddTagsAction(["HHan"]).execute(ctx)
        assert r2.is_skipped
        # dry-run 无调用
        client.calls.clear()
        ctx2 = make_ctx(mgr, tor, client, dry_run=True)
        assert AddTagsAction(["NEW"]).execute(ctx2).is_ok
        assert client.calls == []


def test_remove_tags():
    """删除标签: 正则/无匹配 skip/dry-run"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.tags = {"HHan", "seed-3D"}
        tor = FakeTorrent(tags="HHan,seed-3D")
        ctx = make_ctx(mgr, tor, client)
        r = RemoveTagsAction(["regex:^seed-"]).execute(ctx)
        assert r.is_ok
        assert ("remove_tags", ["seed-3D"]) in client.calls
        # 无匹配 -> skip
        assert RemoveTagsAction(["NOPE"]).execute(ctx).is_skipped


def test_add_category_overwrite_semantics():
    """分类动作: 手动分类不覆盖/自动分类可更新/同分类 skip"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)
        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        assert mgr.state["auto_categories"] == {"HASH123": "AUTO-A"}
        # 当前分类 == 上次自动设置 -> 可更新
        tor.category = "AUTO-A"
        assert AddCategoryAction({"format": "AUTO-B"}).execute(ctx).is_ok
        assert mgr.state["auto_categories"]["HASH123"] == "AUTO-B"
        # 手动分类 -> 不覆盖
        tor.category = "MANUAL"
        assert AddCategoryAction({"format": "AUTO-C"}).execute(ctx).is_skipped
        # 同分类 -> skip
        assert AddCategoryAction({"format": "MANUAL"}).execute(ctx).is_skipped


def test_remove_category():
    """清空分类: 空分类 skip/正常清空"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)
        assert RemoveCategoryAction("").execute(ctx).is_skipped
        tor.category = "HR-DONE"
        assert RemoveCategoryAction("").execute(ctx).is_ok
        assert ("set_category", "") in client.calls


def test_add_category_create_error():
    """分类动作: 创建分类失败被吞掉, set_category 仍执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)

        def boom():
            raise RuntimeError("create failed")

        client.torrents_create_category = boom
        r = AddCategoryAction({"format": "NEW"}).execute(ctx)
        assert r.is_ok
        assert ("set_category", "NEW") in client.calls


def test_remove_tags_dry_run():
    """remove_tags dry-run: 命中匹配标签但不打 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="a, b")
        ctx = make_ctx(mgr, tor, client, dry_run=True)
        result = RemoveTagsAction(["a"]).execute(ctx)
        assert result.is_ok and "a" in result.message
        assert not any(c[0] == "remove_tags" for c in client.calls)


def test_add_category_existing_no_recreate_and_dry_run():
    """add_category: 分类已存在(store 惰性缓存)不重复创建; dry-run 跳过创建与设置整段"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_categories = lambda: {"HR-DONE": {"savePath": ""}}  # 分类定义已存在
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        result = AddCategoryAction({"format": "HR-DONE", "overwrite": False}).execute(ctx)
        assert result.is_ok
        assert not any(c[0] == "create_category" for c in client.calls), "已存在分类不应重复创建"
        assert any(c[0] == "set_category" for c in client.calls)

        before = list(client.calls)
        tor2 = FakeTorrent(hash="H2", tags="")
        ctx2 = make_ctx(mgr, tor2, client, dry_run=True)
        result2 = AddCategoryAction({"format": "NEWCAT", "overwrite": False}).execute(ctx2)
        assert result2.is_ok
        assert client.calls == before, "dry-run 不创建也不设置分类"


def test_remove_category_dry_run():
    """remove_category dry-run: 有分类但不打 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="c")
        ctx = make_ctx(mgr, tor, client, dry_run=True)
        result = RemoveCategoryAction(True).execute(ctx)
        assert result.is_ok and result.message == "清空分类"
        assert not any(c[0] == "set_category" for c in client.calls)


def test_add_category_overwrite_switch():
    """add_category 的 overwrite 开关: 显式 true 必须为 True, 缺省/显式 false 为 False

    键名错位或置 None 会让 overwrite 恒 False —— 用户配了覆盖却永远不覆盖。
    """
    assert AddCategoryAction({"format": "X", "overwrite": True}).overwrite is True
    assert AddCategoryAction({"format": "X", "overwrite": "true"}).overwrite is True
    assert AddCategoryAction({"format": "X", "overwrite": False}).overwrite is False
    assert AddCategoryAction({"format": "X"}).overwrite is False


def test_add_remove_tags_string_spec_not_split():
    """字符串 spec 必须当成单个标签/模式, 不得被 list() 拆成单字符"""
    assert AddTagsAction("TAG").tags == ["TAG"]
    assert RemoveTagsAction("NOPE").patterns == ["NOPE"]
    assert AddTagsAction(["A", "B"]).tags == ["A", "B"]


def test_add_category_format_default():
    """add_category 缺 format 键时兜底空串(不得产出 "None"/"XXXX" 脏分类名)"""
    assert AddCategoryAction({}).format == ""
    assert AddCategoryAction({"format": "AUTO-${required_seeding_time}"}).format == "AUTO-${required_seeding_time}"


def test_add_category_creates_named_category():
    """建分类时 create_category 必须收到真实分类名(None 会在 qB 侧留下名为 None 的脏分类)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(category=""), client)
        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        assert ("create_category", "AUTO-A") in client.calls, f"分类名丢失: {client.calls}"
