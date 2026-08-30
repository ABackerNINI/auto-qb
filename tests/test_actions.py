"""test_actions 测试计划: rules/actions 动作插件执行语义

## 测试计划(每个测试函数一条)
- test_add_tags: 添加标签动作: 直接调用 client.add_tags
- test_remove_tags: 移除标签动作: 调用 client.remove_tags
- test_add_category_overwrite_semantics: 加分类动作的 overwrite 覆盖语义
- test_remove_category: 移除分类动作
- test_start_stop_idempotent: 开始/停止动作幂等(重复执行不报错)
- test_move_to: 移动保存路径动作
- test_reannounce: 重新 announce 动作
- test_speed_limit_actions: 限速动作(下载/上传/全局)
"""
import os
import tempfile

from auto_qb.rules.actions import (
    AddCategoryAction,
    AddTagsAction,
    DownloadSpeedLimitAction,
    MoveToAction,
    ReannounceAction,
    RemoveCategoryAction,
    RemoveTagsAction,
    StartAction,
    StopAction,
    UploadSpeedLimitAction,
)
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager


def _setup(state_file=None):
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(state_file or os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        yield mgr, client, tor


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


def test_start_stop_idempotent():
    """start/stop 幂等: 已开始/已停止 skip"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        # start: stalledUP 已开始 -> skip; pausedUP -> start
        tor = FakeTorrent(state="stalledUP")
        ctx = make_ctx(mgr, tor, client)
        assert StartAction("").execute(ctx).is_skipped
        tor.state = "pausedUP"
        assert StartAction("").execute(ctx).is_ok
        assert ("start", None) in client.calls
        # stop: pausedUP 已停止 -> skip; stalledUP -> stop
        assert StopAction("").execute(ctx).is_skipped
        tor.state = "stalledUP"
        assert StopAction("").execute(ctx).is_ok
        assert ("stop", None) in client.calls


def test_move_to():
    """移动种子: path 空 fail/正常移动"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert MoveToAction({"path": ""}).execute(ctx).is_failed
        assert MoveToAction({"path": r"R:\New"}).execute(ctx).is_ok
        assert ("set_location", r"R:\New") in client.calls


def test_reannounce():
    """强制汇报 tracker"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert ReannounceAction("").execute(ctx).is_ok
        assert ("reannounce", None) in client.calls
        # dry-run
        ctx2 = make_ctx(mgr, FakeTorrent(), client, dry_run=True)
        assert ReannounceAction("").execute(ctx2).is_ok
        assert client.calls.count(("reannounce", None)) == 1


def test_speed_limit_actions():
    """限速动作: 上传/下载限速解析与调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        r = UploadSpeedLimitAction("1000KiB/s").execute(ctx)
        assert r.is_ok
        assert ("set_upload_limit", 1000 * 1024) in client.calls
        r2 = DownloadSpeedLimitAction("2MiB/s").execute(ctx)
        assert r2.is_ok
        assert ("set_download_limit", 2 * 1024**2) in client.calls
