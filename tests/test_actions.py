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
- test_add_category_create_error: 创建分类失败被吞掉, set_category 仍执行
- test_find_reference_piecehashes_cand_error: piecehashes 候选拉取异常 -> 忽略候选
- test_find_reference_dedup: 候选与 verified_references 重合 -> 去重
- test_run_custom_check_error: custom 程序执行异常 -> 视为非参考
- test_skip_checking_export_error: 导出 .torrent 失败 -> fail
- test_skip_checking_export_empty: 导出为空 -> fail
- test_skip_checking_delete_error: 删除种子失败 -> fail(无损失)
- test_skip_checking_not_appeared: 重加后轮询未确认 -> fail
- test_skip_checking_auto_start_error: 自动开始失败 -> fail
- test_speed_limit_fmt_bytes: 小值限速格式化为 B/s
"""
import os
import tempfile
from unittest.mock import patch

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
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager, seed_store


def _seg(mode, auto_start=True):
    return {"mode": mode, "auto_start": auto_start}


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


def _check_action(basic_check="filelist", with_seg=None, without_seg=None, custom_program=None):
    spec = {
        "basic_check": basic_check,
        "with_reference": with_seg or _seg("full-checking"),
        "without_reference": without_seg or _seg("full-checking"),
    }
    if custom_program:
        spec["custom_basic_check_program_path"] = custom_program
    return CheckAction(spec)


def _grouped_mgr(state_file, hashes):
    """构造已归组 manager: store 分组结构 + 快照齐全"""
    mgr = make_manager(state_file)
    mgr.store.groups[("KEY", )] = list(hashes)
    for h in hashes:
        mgr.store.member_to_key[h] = ("KEY", )
    mgr.store.apply(list(hashes.values()))
    return mgr


def test_find_reference_piecehashes_cand_error():
    """checking: piecehashes 模式候选拉取异常 -> 忽略该候选, 不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": t1, "H2": t2})

        class BoomClient(FakeClient):
            def torrents_piece_hashes(self, torrent_hashes=None):
                self.calls.append(("piece_hashes", torrent_hashes))
                if torrent_hashes == "H2":
                    raise RuntimeError("cand api error")
                return [b"a", b"b"]

        client = BoomClient()
        ctx = make_ctx(mgr, t1, client)
        action = _check_action(basic_check="piecehashes")
        refs = action._find_reference(ctx, ["H1", "H2"])
        assert refs == [], "候选拉取失败不应作为参考"


def test_find_reference_dedup():
    """checking: 候选与 verified_references 重合 -> 去重"""
    with tempfile.TemporaryDirectory() as td:
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": t1, "H2": t2})
        mgr.store.verified_references = {"H2"}
        client = FakeClient()
        ctx = make_ctx(mgr, t1, client)
        action = _check_action(basic_check="filelist")
        refs = action._find_reference(ctx, ["H1", "H2"])
        assert [t.hash for t in refs] == ["H2"], "verified 重合应去重"


def test_run_custom_check_error():
    """checking: custom 程序执行异常 -> 视为非参考, 不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        action = _check_action(basic_check="custom", custom_program="fake_prog")
        with patch("subprocess.run", side_effect=OSError("no prog")):
            assert action._run_custom_check(ctx, tor) is False


def _skip_ctx(state_file, **client_patches):
    """构造 skip-checking 执行环境: 未归组 + 单种子快照 + 自定义 client"""
    mgr = make_manager(state_file)
    tor = FakeTorrent(hash="HASH123", name="T1", state="pausedDL", tags="")  # 暂停未完成, 满足决策链 0
    seed_store(mgr, [tor])
    client = FakeClient()
    client.torrents["HASH123"] = {"state": "pausedUP"}  # 重加后出现
    for attr, fn in client_patches.items():
        setattr(client, attr, fn)
    ctx = make_ctx(mgr, tor, client)
    return ctx, client


def test_skip_checking_export_error():
    """checking skip-checking: 导出 .torrent 失败 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("export failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_export=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        r = action.execute(ctx)
        assert r.is_failed and "导出" in r.message, f"应失败: {r}"


def test_skip_checking_export_empty():
    """checking skip-checking: 导出为空 -> fail"""
    with tempfile.TemporaryDirectory() as td:
        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        client.exported = b""
        action = _check_action(without_seg=_seg("skip-checking"))
        r = action.execute(ctx)
        assert r.is_failed and "为空" in r.message, f"应失败: {r}"


def test_skip_checking_delete_error():
    """checking skip-checking: 删除种子失败 -> fail(种子未删除, 无损失)"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("delete failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_delete=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        r = action.execute(ctx)
        assert r.is_failed and "删除种子失败" in r.message, f"应失败: {r}"


def test_skip_checking_not_appeared():
    """checking skip-checking: 重加后轮询未确认到种子 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("info failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_info=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        with patch("auto_qb.rules.actions.time.sleep"):
            r = action.execute(ctx)
        assert r.is_failed and "未确认到种子" in r.message, f"应失败: {r}"


def test_skip_checking_auto_start_error():
    """checking skip-checking: 自动开始失败 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("start failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_start=boom)
        action = _check_action(without_seg=_seg("skip-checking", auto_start=True))
        r = action.execute(ctx)
        assert r.is_failed and "自动开始失败" in r.message, f"应失败: {r}"


def test_speed_limit_fmt_bytes():
    """限速动作: 小值(<1KiB) 格式化为 B/s(与 utils.fmt_speed 一致)"""
    from auto_qb import utils
    assert utils.fmt_speed(512) == "512 B/s"
    assert utils.fmt_speed(2048) == "2.00 KiB/s"
    assert utils.fmt_speed(0) == "0 B/s"
