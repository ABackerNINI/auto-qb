"""`actions_support` 支撑: 从 `test_actions.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

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


def _seg(mode, auto_start=True, enabled=True):
    """构造 with_reference/without_reference 段配置(新架构: 段需显式 enabled=True 才启用)"""
    return {"enabled": enabled, "mode": mode, "auto_start": auto_start}


def _setup(state_file=None):
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(state_file or os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        yield mgr, client, tor


def _check_action(basic_check="filelist", with_seg=None, without_seg=None, custom_program=None):
    spec = {
        "basic_check": basic_check,
        "with_reference": with_seg or _seg("full-checking"),
        "without_reference": without_seg or _seg("full-checking"),
    }
    if custom_program:
        spec["custom_basic_check_program_path"] = custom_program
    return CheckAction(spec)


def _run_action(action, ctx):
    """执行动作; 跳检自 S4 起是异步入口(pending), 这里驱动微步线到终态并返回终态结果

    生产由主循环微步线推进; 测试无主循环, 用 drive_skip 替身。非 pending 动作原样返回。
    """
    r = action.execute(ctx)
    if r.is_pending:
        drive_skip(ctx.manager)
        return ctx.manager.ctx.ops.skip_result(ctx.hash) or r
    return r
