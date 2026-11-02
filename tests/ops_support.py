"""`ops_support` 支撑: 从 `test_ops.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import copy

import inspect

import logging

import os

import tempfile

import time

import uuid

from contextlib import contextmanager

from datetime import date

from types import SimpleNamespace

from auto_qb.core.modules.ops_mod import OpsModule

from auto_qb.core.taskqueue import REQUEUE, Task, TaskQueue

from auto_qb.rules.actions import RECHECK_FAIL_LIMIT

from auto_qb.rules.checking_meta import INFLIGHT_TTL, is_piece_checking

from auto_qb.rules.actions.full_checking import bump_recheck_fail

from helpers import FakeClient, FakeConfig, FakeTorrent, capture_logs, drive_skip, make_manager, seed_store

# 跳检会真实落盘 .torrent 备份(issue 26-09-21-1347): state_file 必须落临时目录, 与 test_checking 同口径
_TMP_STATE_DIR = tempfile.TemporaryDirectory(prefix="autoqb-ops-state-")


def make_mgr(cfg):
    """构造 QbManager(独立任务队列); 自动分配临时 state 文件"""
    if not cfg.state_file:
        cfg.state_file = os.path.join(_TMP_STATE_DIR.name, f"state-{uuid.uuid4().hex}.json")
    mgr = make_manager(cfg=cfg, load_rules=True)
    mgr.task_queue = TaskQueue()
    return mgr


def run_queue(mgr, now):
    return mgr.task_queue.run_due(False, now=now)


@contextmanager
def capture_ops_logs(level=logging.DEBUG):
    """ops_mod 模块日志消息捕获 —— 统一实现已上移 helpers.capture_logs(issue 26-10-04-2311),
    本地只保消息列表形状, 既有用例零改动。不用 caplog 的原因见 capture_logs docstring。"""
    with capture_logs("auto_qb.core.modules.ops_mod", level) as cap:
        yield cap.messages


def seed_paused(mgr, client, hash="HA"):
    """灌一个暂停未完成种子进快照与客户端(ops 直调测试的标的)"""
    t = FakeTorrent(hash=hash, state="pausedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents[hash] = t
    return t


# ============================================================
# E. 跳检闸门扩展(plan 26-10-05-0314 S1b-1): 三分流 detail 单点 + force 语义 + 只读预检
#    谓词单点在 ops._skip_gates_detail; 规则侧决策链 0/1 恒先于 ops 调用, 新闸门对规则源等价 no-op
#    (A 系 26-10-13-0540 S2 起规则侧另有 D-3 让位闸门, 与执行路径的 D-2 同判据 store.own_write_pending)
# ============================================================
def wire_group(mgr, key, *hashes):
    """把若干 hash 直写进 store 分组索引(group_has_downloading 的判定数据源)"""
    for h in hashes:
        mgr.store.member_to_key[h] = key
    mgr.store.groups[key] = list(hashes)


def seed_inflight(mgr, hash_):
    """登记一个在途校验(active_check_hashes 的判定数据源, 即 G5 的视野)"""
    task = Task("check", "check-checking-result", hash=hash_, store=mgr.store, handler=lambda t, d: REQUEUE)
    assert mgr.task_queue.add_task(task)


def _wrap_client(client, method, sink):
    """包装 client.<method> 把 kwargs 记进 sink(高危 None="all" 全库面/参数 pin 的判定源)"""
    orig = getattr(client, method)

    def rec(**kw):
        sink.append(kw)
        return orig(**kw)

    setattr(client, method, rec)
    return sink
