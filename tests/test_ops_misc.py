"""test_ops_misc 测试计划: test_ops: 危险操作独立操作层(OpsMixin)自测(plan 26-09-30-0109 §5.1, 不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_ops_infer_content_layout_empty_content: content_path 为空不推断布局 (P2-a)
- test_ops_clear_backup_noop_missing_path_and_oserror: _clear_backup 无元数据/path 空/删除失败三态 (P2-a)

跳检闸门扩展(plan 26-10-05-0314 S1b-1: 三分流 detail 单点 + force + 预检):
- test_g6_stale_snapshot_window_recovered_by_deferral: G6 端到端(A 系 S3 D1): 陈旧快照窗口存在 + deferral 拦下 + 回流后保护恢复

覆盖率第三轮 T1a(ops_jobs 同步线对账叶, 26-11-04 快照缺口 8 单位):
- test_ops_sync_line_noop_without_backup_ledger: 无备份账本时同步线对账直接返回(33), 一次性闸照常落
- test_ops_sync_line_missing_backup_file_errors_and_keeps_entry: 不在客户端且备份文件缺失 -> ERROR 交人, 账本条目保留(41-43)
- test_ops_sync_line_readd_failure_keeps_backup: 备份重加抛错 -> ERROR+备份保留, 条目不清、备份文件不动(56-58)
"""

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

from ops_support import (
    _TMP_STATE_DIR,
    capture_ops_logs,
    make_mgr,
    seed_paused,
    wire_group,
)


def test_ops_infer_content_layout_empty_content():
    """测试: content_path 为空(未知内容路径)时不推断布局, 返回 None"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    tor = FakeTorrent(hash="HA", content_path=None)
    assert mgr.ctx.ops._infer_content_layout(tor, client) is None


def test_ops_clear_backup_noop_missing_path_and_oserror():
    """测试: _clear_backup 三态 —— 无元数据直接返回 / path 为空跳过删除仍落盘 / 删除失败只告警"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    mgr.ctx.ops._clear_backup("HA")  # 无元数据: 直接返回, 不落盘不报错

    # path 为空: 跳过文件删除, 但元数据仍清理并落盘
    mgr.state.setdefault("skip_check_backup", {})["HA"] = {"path": ""}
    mgr.ctx.ops._clear_backup("HA")
    assert "HA" not in mgr.state["skip_check_backup"]

    # 删除失败: 只告警不崩溃, 元数据照常清理落盘
    mgr.state.setdefault("skip_check_backup", {})["HB"] = {"path": "R:/Temp/auto-qb/tests/ghost.torrent"}
    real_remove = os.remove

    def boom(path):
        raise OSError("locked")

    os.remove = boom
    try:
        mgr.ctx.ops._clear_backup("HB")
    finally:
        os.remove = real_remove
    assert "HB" not in mgr.state["skip_check_backup"]


def test_g6_stale_snapshot_window_recovered_by_deferral():
    """守阵(A 系 S3 D1): G6「起下载方 D + 跳检同组成员 C」—— 陈旧快照窗口 + deferral 收回

    P1 可达性 witness(W1/W2/W3)的机检。三段式:
      ① **窗口存在**: A1 下 D 自有 resume 后快照仍停 pausedDL ⇒ group_has_downloading 读不到
         下载方(pausedDL 是 is_stopped) ⇒ G6 放行 ⇒ C 被删重加而 D 正写同一物理文件 = 脏数据洗白;
      ② **deferral 拦下**: own_writes 登记 D(同组) ⇒ skip_check(C) 让位, 零副作用;
      ③ **保护恢复**: 快照回流落真值 stalledDL ⇒ G6 重新拦下 —— 证明 deferral 是「推迟到新鲜时」
         而非「放弃保护」。
    红验: 去掉 skip_check 入口的 deferral 闸门 -> ②不再让位(且 G6 因陈旧快照放行), 断言红。
    """
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    # 快照侧(陈旧, A1 下的形态: D 仍显示暂停) 与 客户端真值侧(D 已在下载) 分离
    d_snap = FakeTorrent(hash="HD", state="pausedDL", progress=0.3)
    c_snap = FakeTorrent(hash="HC", state="pausedDL", progress=0.0)
    seed_store(mgr, [d_snap, c_snap])
    client.torrents["HD"] = FakeTorrent(hash="HD", state="stalledDL", progress=0.3)
    client.torrents["HC"] = FakeTorrent(hash="HC", state="pausedDL", progress=0.0)
    wire_group(mgr, "K", "HD", "HC")

    # ① 窗口存在
    assert mgr.store.group_has_downloading("HC") is False, "陈旧快照(pausedDL=is_stopped)读不到下载方"
    assert not any(g.gate == "G6" for g in mgr.ctx.ops._skip_gates_detail("HC", c_snap)), "陈旧快照下 G6 放行(窗口)"

    # ② 自有 resume D -> 登记 own_writes -> C 的跳检让位(零副作用)
    mgr.api.torrents_resume(["HD"])
    client.calls.clear()  # resume 自身是预期调用, 只断言其后零副作用
    assert mgr.store.own_write_pending("HC") is True, "同组成员登记应让 C 命中判据"
    r = mgr.ctx.ops.skip_check("HC", source="web")
    assert r.is_skipped and "稍后" in r.message, f"G6 场景应让位: {r}"
    assert client.calls == [], f"让位零副作用(未删未加): {client.calls}"

    # ③ 回流后保护恢复
    mgr.store.own_writes.clear()
    mgr.store.by_hash["HD"].state = "stalledDL"  # 同步落真值
    assert mgr.store.group_has_downloading("HC") is True, "回流后 G6 判据恢复"
    assert any(g.gate == "G6" for g in mgr.ctx.ops._skip_gates_detail("HC", c_snap)), "回流后 G6 应拦下"


# ============================================================
# 覆盖率第三轮 T1a: ops_jobs 同步线对账叶余量(26-11-04 快照缺口 8 单位)
# ============================================================
def test_ops_sync_line_noop_without_backup_ledger():
    """测试: 无备份账本(state 无 skip_check_backup)时同步线对账直接返回(33), 零动作;
    一次性闸照常落(每进程只对账一次)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HA")
    assert not mgr.state.get("skip_check_backup"), "前提: 无备份账本"
    mgr.ctx.ops.on_sync_line(True)
    assert client.calls == [], "无账本不得有任何客户端动作"
    assert mgr.ctx.ops._skip_recovered is True, "一次性闸已落(后续同步线不再对账)"


def test_ops_sync_line_missing_backup_file_errors_and_keeps_entry(tmp_path):
    """测试: 种子不在客户端且备份文件已丢 -> 无恢复凭据, 只能 ERROR 交人(42-43);
    账本条目保留(清账=静默丢凭据), 零客户端动作"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HA")
    mgr.state.setdefault("skip_check_backup", {})["HLOST"] = {
        "path": str(tmp_path / "nope.torrent"),
        "save_path": "R:/Downloads",
        "ts": 0,
    }
    with capture_ops_logs() as logs:
        mgr.ctx.ops.on_sync_line(True)
    assert any("不在客户端且备份文件缺失" in m and "HLOST"[:8] in m for m in logs), logs
    assert "HLOST" in mgr.state["skip_check_backup"], "无凭据不得清账(交人处理)"
    assert client.calls == [], "备份丢失不得触发任何重加动作"


def test_ops_sync_line_readd_failure_keeps_backup(tmp_path):
    """测试: 备份重加抛错 -> ERROR 点名原因 + 备份保留(56-58); 账本条目不清、备份文件不动"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HA")
    backup = tmp_path / "HRETRY.torrent"
    backup.write_bytes(b"torrent-bytes")
    mgr.state.setdefault("skip_check_backup", {})["HRETRY"] = {
        "path": str(backup),
        "save_path": "R:/Downloads",
        "category": "c",
        "tags": "t",
        "ts": 0,
    }
    client.add_error = RuntimeError("duplicate torrent")
    with capture_ops_logs() as logs:
        mgr.ctx.ops.on_sync_line(True)
    assert any("重加失败" in m and "备份保留" in m and "HRETRY"[:8] in m for m in logs), logs
    assert "HRETRY" in mgr.state["skip_check_backup"], "重加失败不得清账(凭据还在, 下轮可再试)"
    assert backup.exists(), "备份文件不得被改动"
