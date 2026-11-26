"""`checking_support` 支撑: 从 `test_checking.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import os

import tempfile

import time

import uuid

from datetime import date

from types import SimpleNamespace

from unittest.mock import patch

from auto_qb.config import Config

from auto_qb.rules.actions import RECHECK_FAIL_LIMIT, CheckAction

from auto_qb.rules.actions.full_checking import bump_recheck_fail, recheck_fail_count

from auto_qb.rules.base import VERDICT_EXECUTED, VERDICT_PENDING

from auto_qb.rules.checking_meta import PieceCheckingStates, PollVerdict, is_piece_checking, poll_verdict

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, TaskQueue

from helpers import drive_skip, FakeClient, FakeConfig, FakeTorrent, make_ctx, make_manager, seed_store


# ---------- 增强模拟客户端(piece hashes API / recheck 失败注入) ----------
class CheckingFakeClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.piece_hashes_map = {}  # hash -> piece hash 列表(参考判定用)
        self.piece_hashes_error = False  # 模拟 API 异常
        self.recheck_error = None  # 模拟 recheck 请求失败

    def torrents_piece_hashes(self, torrent_hashes=None):
        """模拟 qbittorrentapi 的 torrents_piece_hashes(直接返回列表, 无需导出 .torrent)"""
        self.calls.append(("piece_hashes", torrent_hashes))
        if self.piece_hashes_error:
            raise RuntimeError("simulated piece hashes api error")
        return self.piece_hashes_map.get(torrent_hashes, [])

    def torrents_recheck(self, torrent_hashes=None):
        if self.recheck_error:
            raise self.recheck_error
        super().torrents_recheck(torrent_hashes=torrent_hashes)


# ---------- 测试辅助 ----------
def make_check_cfg(
    basic_check="filelist",
    with_mode="skip-checking",
    with_start=True,
    without_mode="full-checking",
    without_start=True,
    custom_program=None,
    extra_actions=None,
    execute_once="never",
    fail_cooldown=None
):
    """构造 checking 规则配置(条件: 标签含"需校验"); extra_actions 追加到动作序列(续跑测试用)

    fail_cooldown: checking spec 的 recheck_fail_cooldown(校验失败冷却窗口, 时间串);
    None = 不配置该键(运行时走 1h 缺省档)。

    跳检标签名全局统一(config.skip_checking_tag), spec 不配置该键。
    """
    cfg = FakeConfig()
    action = {
        "checking":
            {
                "basic_check": basic_check,
                "with_reference": {
                    "enabled": True,
                    "mode": with_mode,
                    "auto_start": with_start
                },
                "without_reference": {
                    "enabled": True,
                    "mode": without_mode,
                    "auto_start": without_start
                },
            }
    }
    if custom_program:
        action["checking"]["custom_basic_check_program_path"] = custom_program
    if fail_cooldown is not None:
        action["checking"]["recheck_fail_cooldown"] = fail_cooldown
    actions = [action] + (extra_actions or [])
    cfg.rules_config = {
        "example_rules":
            {
                "check_rule":
                    {
                        "enabled": True,
                        "execute_once": execute_once,
                        "conditions": [{
                            "tags": "需校验"
                        }],
                        "actions": actions,
                    },
            }
    }
    return cfg


# 跳检会在删除前**真实落盘** .torrent 备份、重加成功后**真实删除**它(issue 26-09-21-1347 的
# 崩溃窗口修复) —— 于是每条走跳检的用例都有真实文件系统副作用, state_file 必须落在临时目录
# (留空会写到 CWD=仓库根: 既污染仓库, 又会被 tests/sidefx.py 判成越界删除)。未显式指定
# state_file 的用例在这里自动领一份唯一文件名(唯一 = 同一用例内多个 manager 不会互相读到
# 对方落盘的 state)。
_TMP_STATE_DIR = tempfile.TemporaryDirectory(prefix="autoqb-checking-state-")


def make_mgr(cfg, with_tq=False):
    """构造 QbManager(可选任务队列); 未指定 state_file 时自动分配一份临时 state 文件"""
    if not cfg.state_file:
        cfg.state_file = os.path.join(_TMP_STATE_DIR.name, f"state-{uuid.uuid4().hex}.json")
    mgr = make_manager(cfg=cfg, load_rules=True)
    if with_tq:
        mgr.task_queue = TaskQueue()
    return mgr


def run_queue(mgr, now=None, dry_run=False):
    """驱动快速队列一轮: 执行所有到期任务并收尾(校验轮询任务状态机推进)
    now: 显式时间点(校验任务 interval=2s, 多轮推进需递增 now)
    """
    now = time.time() if now is None else now
    out = mgr.task_queue.run_due(dry_run, now=now)
    # 跳检自 S4 起是异步入口: 相位由主循环微步线推进, 测试里随队列一并驱动到终态
    drive_skip(mgr)
    return out


def process_rule(mgr, client, tor, dry_run=False):
    """同步执行 example_rules.check_rule 于种子(等价旧 process_torrent 入口)

    新架构规则由任务队列驱动(process_torrent 兼容入口已删); 测试为同步确定性, 这里用
    无任务上下文直接执行规则: 动作内部 full-checking 仍会把轮询任务注册到 task_queue
    (由 run_queue 推进); pending 分支在无任务时按成功继续, 与队列驱动的 defer 系列测试
    互不冲突。skip-checking 的删除-重加流程需要删除后快照仍可用(真实 qB 中重加立即以同
    hash 出现; 与 test_actions._skip_ctx 同思路): 包装 torrents_delete, 真实删除后恢复
    快照记录(不改 src)。
    """
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    store = mgr.store
    ctx = make_ctx(mgr, tor, client, dry_run=dry_run)  # 1. 注入 by_hash(make_ctx 后捕获, 覆盖未 seed_store 的测试)
    prev = dict(store.by_hash)
    orig_delete = mgr.api.torrents_delete

    def wrapped_delete(torrent_hashes=None, delete_files=False, **kw):
        orig_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kw)
        hashes = [torrent_hashes] if isinstance(torrent_hashes, str) else list(torrent_hashes or [])
        for h in hashes:
            if h in prev and store.by_hash.get(h) is not prev[h]:
                store.restore_torrent(prev[h])  # 重加后同 tick 快照恢复(并撤销待报删除)

    mgr.api.torrents_delete = wrapped_delete
    try:
        out = rule.process(ctx)
        # 跳检自 S4 起是异步入口(规则侧拿 pending, 相位由微步线推进): 测试里驱动到终态
        drive_skip(mgr)
        # W1 verdict 契约(rules.base.VERDICT_*): 收敛为旧 handled 语义供既有断言使用
        return out in (VERDICT_EXECUTED, VERDICT_PENDING)
    finally:
        mgr.api.torrents_delete = orig_delete


def inject_group(mgr, *hashes, key=("KEY", )):
    """把 hashes 注入同一组(绕过归组流程, 直接构造 store 分组结构) """
    mgr.store.groups[key] = list(hashes)
    for h in hashes:
        mgr.store.member_to_key[h] = key


def make_target(state="pausedDL", hash="HASH123", progress=0.0, tags="需校验"):
    return FakeTorrent(hash=hash, name="T", tags=tags, state=state, progress=progress)


def _seg(mode, start=True):
    return {"mode": mode, "auto_start": start}
