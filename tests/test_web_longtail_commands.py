"""test_web_longtail_commands 测试计划: P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)

## 测试计划(每个测试函数一条)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_web_commands_delete_with_files_and_reannounce_gone_receipt: 删除透传 delete_files; 汇报缺失显式回执
- test_reannounce_group_empty_snapshot_error_receipt: 组命令空组回执(E-03) —— 组内成员执行时刻全不在快照时显式 error 回执, 不发指令不登记跟踪(对齐单发口径, 前端不再挂到超时)
- test_web_commands_recheck_and_skip_check_receipts: recheck/skip-check 拒绝回执带文案
- test_web_commands_limits_partial_directions: 限速只下发提供的方向; 分享限制缺省 -2 补齐
- test_web_commands_rename_fs_folder_branch: 重命名文件夹分支
- test_web_commands_bulk_argument_errors: 批量参数四类错误回执
- test_web_commands_bulk_missing_targets_reported: 批量缺失种子/组分列计数
- test_web_commands_bulk_recheck_via_ops: 批量 recheck 经 ops 聚合回执
- test_web_commands_add_torrents_receipt: 添加种子三态回执(全受理 ok / 部分受理 warn / 全拒 error)
"""

import base64

import errno

import os

import re

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

from helpers import capture_logs

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _enable_qb_traffic,
    _qb_v4,
    _make_grouped_manager,
    _attach_live_tail_host,
)


def test_web_commands_delete_with_files_and_reannounce_gone_receipt():
    """删除透传 delete_files; 汇报种子已不存在 -> 显式 error 回执(不静默)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True, "cmd_id": "d1"}))
        mgr.web.commands.put(("reannounce_torrent", {"hash": "GONE", "cmd_id": "r1"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), "delete_files 透传给 API"
        assert mgr.web.results["d1"]["status"] == "ok"
        assert mgr.web.results["r1"]["status"] == "error" and "不存在" in mgr.web.results["r1"]["error"]


def test_reannounce_group_empty_snapshot_error_receipt():
    """组强制汇报空组回执(E-03): 组内成员执行时刻全不在快照 -> 显式 error 回执, 不发指令不登记

    组快照渲染后、命令执行前组内成员全被删除(主循环被长任务占住时窗口秒级): _group_hashes
    回空 -> 修复前不发指令不写回执, 前端 waitCmd 挂到自身超时才弹「超时」。对齐单发
    reannounce_torrent 对缺失的显式 error 回执口径。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.store.remove_torrent("HA")
        mgr.store.remove_torrent("HB")
        assert mgr._group_hashes(key) == [], "前置: 组内成员已全部不在快照"
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "r-gone"}))
        mgr.web.consume_commands()
        assert client.calls == [], "空组不得发任何指令"
        assert mgr.web.reannounce_pending == {}, "空组不登记确认跟踪"
        r = mgr.web.results["r-gone"]
        assert r["status"] == "error" and "不存在" in r["error"], "空组必须显式 error 回执"


def test_web_commands_recheck_and_skip_check_receipts():
    """重新校验/右键跳检经 ops 提交: 拒绝时回执带自解释文案; 种子不存在同样显式报"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("recheck_torrent", {"hash": "GONE", "cmd_id": "c-gone"}))
        mgr.web.commands.put(("skip_check_torrent", {"hash": "GONE", "cmd_id": "s-gone"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-gone"]["status"] == "error" and "不存在" in mgr.web.results["c-gone"]["error"]
        assert mgr.web.results["s-gone"]["status"] == "error", "跳检拒绝(种子消失) -> error 回执带文案"
        assert mgr.web.results["s-gone"]["error"], "拒绝文案不为空"


def test_web_commands_limits_partial_directions():
    """限速只下发提供的方向(up/dl 可各自缺省); 分享限制同理"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._cmd_set_torrent_limits("HA", up_limit=1024)
        mgr._cmd_set_torrent_limits("HA", dl_limit=2048)
        mgr._cmd_set_share_limits("HA", ratio_limit=1.5)
        kinds = [c[0] for c in client.calls]
        assert kinds.count("set_upload_limit") == 1 and kinds.count("set_download_limit") == 1
        assert client.calls[-1] == ("set_share_limits", (1.5, -2, -2, "Default", "Default")), \
            "缺失维度按 -2(全局默认)补齐; mode/action 恒传 Default(5.3/5.0+ 必填)"


def test_web_commands_rename_fs_folder_branch():
    """重命名文件夹走 torrents_rename_folder(文件走 rename_file 已有守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._cmd_rename_fs("HA", old_path="old/dir", new_path="new/dir", is_folder=True)
        assert client.calls[-1] == ("rename_folder", ("HA", "old/dir", "new/dir"))


def test_web_commands_bulk_argument_errors():
    """批量动作参数错误: 未知动作 / 空目标 / 标签动作无标签 / set_category 无分类 /
    limits 两方向全空 / location 空路径 -> error 回执且不调 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cases = [
            ({
                "hashes": ["HA"],
                "action": "purge"
            }, "purge"),
            ({
                "action": "pause"
            }, "未提供任何 hash"),
            ({
                "hashes": ["HA"],
                "action": "add_tags"
            }, "未提供标签"),
            ({
                "hashes": ["HA"],
                "action": "set_category"
            }, "未提供分类"),
            ({
                "hashes": ["HA"],
                "action": "limits"
            }, "未提供限速值"),
            ({
                "hashes": ["HA"],
                "action": "location"
            }, "未提供目标路径"),
        ]
        for i, (payload, want) in enumerate(cases):
            mgr.web.commands.put(("bulk_torrents", dict(payload, cmd_id=f"b{i}")))
            mgr.web.consume_commands()
            assert mgr.web.results[f"b{i}"]["status"] == "error", (payload, mgr.web.results)
            assert want in mgr.web.results[f"b{i}"]["error"]
        assert client.calls == [], "参数错误不触达 qB"


def test_web_commands_bulk_missing_targets_reported():
    """批量: 缺失种子与缺失组分列计数(部分缺失也进 error 文案, 拒绝计数可见)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        ghost_key = ("R:/Nowhere", ("none.mkv", ))
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "GONE"],
                "keys": [ghost_key],
                "action": "pause",
                "cmd_id": "bm"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["bm"]
        assert rec["status"] == "error"
        assert "1/2 个种子不存在" in rec["error"] and "1/1 个组不存在" in rec["error"]


def test_web_commands_bulk_recheck_via_ops():
    """批量 recheck 经 ops 逐个提交: 提交/跳过/缺失聚合进回执(部分成功也报错)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        with capture_logs("auto_qb.webui.commands") as cap:
            mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "GONE"], "action": "recheck", "cmd_id": "br"}))
            mgr.web.consume_commands()
        rec = mgr.web.results["br"]
        assert rec["status"] == "error" and "1/2 个种子不存在" in rec["error"]
        assert any("批量 recheck(提交 1" in m for m in cap.messages), "提交/跳过计数落日志(回执只带缺失文案)"


def test_web_commands_add_torrents_receipt():
    """添加种子: 文件+链接都受理 -> ok 回执; 部分受理 -> warn 回执; qB 全拒 -> error 回执带详情"""
    from hr_helpers import torrent_blob

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        blob = torrent_blob(name="added.bin")
        mgr.web.commands.put(
            (
                "add_torrents",
                {
                    "files": [blob],
                    "urls": ["magnet:?xt=urn:btih:xyz"],
                    "save_path": "R:/Drop",
                    "category": "cat",
                    "tags": ["t1"],
                    "paused": False,
                    "skip_checking": False,
                    "sequential": False,
                    "first_last_piece_prio": False,
                    "auto_tmm": False,
                    "cmd_id": "a1",
                },
            )
        )
        mgr.web.consume_commands()
        assert mgr.web.results["a1"]["status"] == "ok", mgr.web.results["a1"]
        assert any(c[0] == "add" for c in client.calls)
        # 部分受理 -> warn 回执(2026-10-18 报障「部分种子添加失败(已存在)时添加窗口不消失」):
        # qB 对重复种子是**整批里挑着拒**(HTTP 200 + failure_count>0), 部分成功是常态路径。
        # 形态一(API>=2.14.0 元数据, 真机主路径): 单次调用 success=1 / failure=1
        from qbittorrentapi.torrents import TorrentsAddedMetadata

        client.torrents_add = lambda *a, **kw: TorrentsAddedMetadata(
            {
                "success_count": 1,
                "failure_count": 1,
                "pending_count": 0,
                "added_torrent_ids": ["HASH123"]
            }
        )
        mgr.web.commands.put(("add_torrents", {"files": [blob], "urls": [], "cmd_id": "a3"}))
        mgr.web.consume_commands()
        rec3 = mgr.web.results["a3"]
        assert rec3["status"] == "warn" and "成功 1 / 失败 1" in rec3["error"], rec3
        # 形态二(API<2.14.0 旧文本): 文件调用 "Ok." + 链接调用 "Fails." 跨两次调用混合
        seq = iter(["Ok.", "Fails."])
        client.torrents_add = lambda *a, **kw: next(seq)
        mgr.web.commands.put(("add_torrents", {"files": [blob], "urls": ["magnet:?xt=urn:btih:xyz"], "cmd_id": "a4"}))
        mgr.web.consume_commands()
        rec4 = mgr.web.results["a4"]
        assert rec4["status"] == "warn" and "Ok." in rec4["error"] and "Fails." in rec4["error"], rec4
        # qB 全拒(旧文本形态 "Fails.") -> error 回执(新形态元数据由既有守阵钉)
        client.torrents_add = lambda *a, **kw: "Fails."
        mgr.web.commands.put(("add_torrents", {"files": [blob], "urls": [], "cmd_id": "a2"}))
        mgr.web.consume_commands()
        assert mgr.web.results["a2"]["status"] == "error" and "qB 未接受" in mgr.web.results["a2"]["error"]
