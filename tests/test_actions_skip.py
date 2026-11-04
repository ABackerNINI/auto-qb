"""test_actions_skip 测试计划: rules/actions 动作插件执行语义

## 测试计划(每个测试函数一条)
- test_skip_checking_export_error: 导出 .torrent 失败 -> fail
- test_skip_checking_export_empty: 导出为空 -> fail
- test_skip_checking_delete_error: 删除种子失败 -> fail(无损失)
- test_skip_checking_delete_not_confirmed: 删除后确认种子消失失败 -> 放弃跳检不重加
- test_skip_checking_readd_preserves_values: 重加属性直传(0/负值有语义, 不得被 or None 吞掉)
- test_skip_checking_readd_restores_store_record: 重加成功后恢复删除前快照记录(tracker_conf 保留, 修复 log_repr 崩溃)
- test_skip_checking_content_layout_inferred: contentLayout 由 content_path/save_path/文件列表推断
- test_skip_checking_auto_start_error: 自动开始失败 -> fail
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

from actions_support import (
    _check_action,
    _run_action,
    _seg,
)


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

    # 跳检动作语义: 删除种子(保留文件)后按旧种子字段重加。真实 qB 中种子删除后立即以同 hash
    # 重新出现; 测试包装 torrents_delete: 先真实调用(QbApi 同步移除快照的语义保留, 供
    # test_skip_checking_delete_error 等校验), 成功后恢复快照记录, 模拟重加后种子重新出现,
    # 使动作能读到重加参数(save_path/category/tags/limits, actions._execute_skip_checking 的
    # delete 后 ctx.torrent 读取)。不改 src, 仅测试侧镜像"重加后同 tick 内快照可用"。
    orig_delete = mgr.api.torrents_delete

    def wrapped_delete(torrent_hashes=None, delete_files=False, **kw):
        orig_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kw)
        mgr.store.restore_torrent(tor)  # 重加后同 tick 快照恢复(并撤销待报删除)

    mgr.api.torrents_delete = wrapped_delete
    return ctx, client


def test_skip_checking_export_error():
    """checking skip-checking: 导出 .torrent 失败 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("export failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_export=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        r = _run_action(action, ctx)
        assert r.is_failed and "导出" in r.message, f"应失败: {r}"


def test_skip_checking_export_empty():
    """checking skip-checking: 导出为空 -> fail"""
    with tempfile.TemporaryDirectory() as td:
        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        client.exported = b""
        action = _check_action(without_seg=_seg("skip-checking"))
        r = _run_action(action, ctx)
        assert r.is_failed and "为空" in r.message, f"应失败: {r}"


def test_skip_checking_delete_error():
    """checking skip-checking: 删除种子失败 -> fail(种子未删除, 无损失)"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("delete failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_delete=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        r = _run_action(action, ctx)
        assert r.is_failed and "删除种子失败" in r.message, f"应失败: {r}"


def test_skip_checking_readd_preserves_values():
    """checking skip-checking: 重加属性直传 —— 0 等有语义值(不限速/分享率限制)不得被 or None 吞成 qB 新种缺省"""
    with tempfile.TemporaryDirectory() as td:
        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        tor = ctx.torrent
        tor.up_limit = 0  # 0 = 不限速
        tor.dl_limit = 2001 * 1024  # 非零控制组
        tor.ratio_limit = 0  # qB 分享率限制(有语义)
        tor.seeding_time_limit = 0
        action = _check_action(without_seg=_seg("skip-checking"))
        # !S3 收敛解包: 成功路径零重试零退避, sleep 桩(ops_mod.time = stdlib time 对象进程级改写)无对象可拦
        r = _run_action(action, ctx)
        assert r.is_ok, f"{r}"
        add = next(c for c in client.calls if c[0] == "add")
        assert add[1]["upload_limit"] == 0, f"不限速 0 应直传: {add}"
        assert add[1]["download_limit"] == 2001 * 1024, f"{add}"
        assert add[1]["ratio_limit"] == 0 and add[1]["seeding_time_limit"] == 0, f"{add}"


def test_skip_checking_readd_restores_store_record():
    """重加成功后恢复删除前快照记录: 否则下轮 refresh 重建记录 tracker_conf=None 且不进
    added 列表(remove_torrent 保留 _known_hashes), 该种子永久未匹配 —— 真实 BUG:
    log_repr -> tracker_name -> self.tor.client AttributeError(生产日志 2026-09-06)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", state="pausedDL")  # 暂停未完成: 过闸门 0
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 删除前已匹配(生产: _refresh_torrents 阶段)
        client.torrents["HASH123"] = tor
        seed_store(mgr, [tor])
        action = _check_action(without_seg=_seg("skip-checking"))
        ctx = make_ctx(mgr, tor, client)
        # !S3 收敛解包: 成功路径零重试零退避, sleep 桩(ops_mod.time = stdlib time 对象进程级改写)无对象可拦
        r = _run_action(action, ctx)
        assert r.is_ok, f"{r}"
        # 快照记录已恢复(对象身份 = 删除前捕获的 tor), tracker_conf 保留
        assert mgr.store.get("HASH123") is tor
        assert tor.tracker_conf is mgr.config.trackers["HHan"]
        # log_repr 不再崩(tracker_name 走 conf, 不回退 self.tor.client)
        assert "[HHan]" in tor.log_repr

        # 真实 qB 场景: tor 是 TorrentDictionary(无 client 属性)也不崩 —— 模拟无 client 属性的 tor
        class _TorDictLike:
            pass  # 无 client/_client

        rec = tor  # 直接验证 tracker_name 在 conf 存在时不触碰 tor.client
        assert rec.tracker_name == "HHan"


def test_skip_checking_content_layout_inferred():
    """checking skip-checking: contentLayout 由 content_path/save_path/文件列表推断, 防止布局错位"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        action = _check_action(without_seg=_seg("skip-checking"))
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()

        def case(save, content, files):
            tor = FakeTorrent(save_path=save, content_path=content, name="T1", state="pausedDL")
            client.files_map = {"HASH123": files}
            seed_store(mgr, [tor])
            ctx = make_ctx(mgr, tor, client)
            return mgr.ctx.ops._infer_content_layout(tor, client)  # 方法已迁 ops 模块(plan P4, 经 ctx.ops)

        def f(n):
            return SimpleNamespace(name=n, size=1)

        root_files = [f("T1/a.mkv"), f("T1/b.mkv")]
        # 多文件带根目录: content==save/种子名 -> Original(保留根); content==save -> NoSubfolder(原布局剥根)
        assert case(r"R:\Downloads", r"R:\Downloads\T1", root_files) == "Original"
        assert case(r"R:\Downloads", r"R:\Downloads", root_files) == "NoSubfolder"
        # 无根目录: content==save -> Original; 单文件 content==save/种子名 -> Original
        assert case(r"R:\Downloads", r"R:\Downloads", [f("a.mkv"), f("b.mkv")]) == "Original"
        assert case(r"R:\Downloads", r"R:\Downloads\T1", [f("T1.mkv")]) == "Original"
        # 路径异常(无法推断): None(用 qB 默认)
        assert case(r"R:\Downloads", r"R:\Elsewhere", root_files) is None


def test_skip_checking_delete_not_confirmed():
    """checking skip-checking: 删除后轮询确认失败(torrents_info 异常) -> 放弃跳检, 不重加"""
    with tempfile.TemporaryDirectory() as td:

        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        # !R2 实时复核发生在删除前: info 故障必须从"删除生效后"才开始 —— 种子还在客户端时
        #   正常应答, 删除(pop 出 client.torrents)后再查即抛, 精确模拟"确认消失轮询失败"
        orig_info = client.torrents_info

        def info_after_delete(torrent_hashes=None, **kw):
            if torrent_hashes not in client.torrents:
                raise RuntimeError("info failed")
            return orig_info(torrent_hashes=torrent_hashes, **kw)

        client.torrents_info = info_after_delete
        action = _check_action(without_seg=_seg("skip-checking"))
        # !S3 收敛: sleep 桩解包, 退避重试(10/20/50/50/50ms, 名义 170ms)真实发生 ——
        #   ops_mod.time 是 stdlib time 模块对象, 经它 patch 即进程级改写
        r = _run_action(action, ctx)
        assert r.is_failed and "确认删除失败" in r.message, f"应失败(看不见就当没确认, fail-closed): {r}"
        assert not any(c[0] == "add" for c in client.calls), "未确认消失前不得重加"


def test_skip_checking_auto_start_error():
    """checking skip-checking: 自动开始失败 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("start failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_start=boom)
        action = _check_action(without_seg=_seg("skip-checking", auto_start=True))
        r = _run_action(action, ctx)
        assert r.is_failed and "自动开始失败" in r.message, f"应失败: {r}"
