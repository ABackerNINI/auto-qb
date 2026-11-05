"""test_qbmanager_tasks 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_create_global_tasks: 按配置创建 delete_tags 等全局任务
- test_wake_drains_commands_without_extra_ticks: 命令唤醒只走命令线, 命令风暴下 tick 次数不增加
- test_run_loop_expect_landing_pulls_sync_forward: 添加种子后的有界追平(issue 26-10-30-0626) —— store 有待落地 hash 时同步线被提前到 ~80ms(不等 sync_interval), 追平轮带 force, 次数用尽后自动放弃
- test_drain_web_commands_reports_resync_needed: P0-5 门控——只有改种子状态的命令置 changed
- test_command_batch_triggers_single_resync: P0-5 一批命令后补**一次**完整刷新(整批合单)
- test_sync_moved_proxy: S4(26-10-21-2323) —— 「本轮是否有变化」代理判据: delta/新增/删除任一非空即为真
- test_cmd_resync_keeps_schedule_when_nothing_moved: S4(26-10-21-2323) —— 补刷新没拿到变化时不推后下一次同步(否则校正反而更晚)
- test_drain_web_commands_bumps_write_seq: P1-4 失效接线——写命令自增 web.write_seq, 自投递不自增
- test_drain_bumps_write_seq_before_writing_receipt: BUG-5 顺序——回执写入时写序号须已自增
- test_run_due_requeues: handler 成功 -> run_due 收尾重入队(run_count+1, 回 PENDING)
- test_run_due_dies: handler 返回 False -> 不重入(消亡)
- test_own_write_defer_gate_targets_group_members: A 系 S2 D-1 队列闸门判据 —— 目标 hash 或其组任一成员 ∈ own_writes 即让位
- test_create_torrent_tasks_tor_missing: 种子不在快照 -> 直接返回
- test_create_torrent_tasks_with_rules: 匹配 tracker -> 创建 maintenance + 规则任务
- test_execute_due_respects_max: 每 tick 最多执行 max_tasks_per_tick 个, 超额留队列
- test_tick_no_due_task_empty_queue: 任务队列空时 tick 不执行任何任务
- test_p2a_sync_line_flush_propagates_to_host: _sync_line flush=True 经 host.run_sync_line; False 不调 (P2-a)
- test_w6_task_line_receives_dry_run: 守阵(W6)——任务线必须收到 dry_run 位置实参(缺参=TypeError 退避环)
- test_w6_truth_pending_one_shot_no_extra_sync: 守阵(W6)——真值落地(flush 清空)后不得继续重试弧
- test_w6_sync_line_contract: 守阵(W6)——同步线默认 flush/force 与 dry_run 传递契约
- test_w6_task_line_contract: 守阵(W6)——任务线 run_due 实参契约(defer_gate 身份) + 收尾 force 默认
"""

import json

import logging

import os

import tempfile

import threading

import time

from unittest import mock

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, Task, TaskQueue

import pytest

from qbittorrentapi import APIConnectionError, Client

from auto_qb.config import QbittorrentConfig

from auto_qb.config import PathMapEntry

from auto_qb.config.models import FsConfig

from auto_qb.infra.errors import AutoQbError

from auto_qb.infra import file_access

from auto_qb.infra.file_access import MappedFileAccess

from auto_qb.core.module import ApplyResult

from auto_qb.core import qbmanager as _qbm

from auto_qb.core.qbclient import REQUESTS_TIMEOUT, LocalQbClient, new_client

from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _wait_next

from auto_qb.torrents import QbCompatError

from helpers import LEGACY_V1, FakeClient, FakeConfig, FakeTorrent, capture_logs, make_manager, seed_store

from qbmanager_support import (
    _daemon_timer,
)


def test_create_global_tasks():
    """delete_tags 配置存在时创建 internal 全局任务并入队"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 无 delete_tags 配置: 不创建
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert "delete_tags" not in names
        # 配置 delete_tags: 创建任务
        mgr.config.delete_tags = ["regex:^seed-"]
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert "delete_tags" in names
        assert "delete_tags_if_has_no_torrents" in names


def test_wake_drains_commands_without_extra_ticks():
    """P0-1 命令唤醒: 只走命令线 —— 命令风暴下 tick/同步线次数**不增加**, 但命令被立即消费

    反过来若退化成"投递即跑一轮 tick", 本用例的 task 计数会随唤醒次数一起涨。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        # 两条线都设成 5s: 若没有唤醒, 观测窗口内一次 drain 都不会发生
        mgr.config.main_tick = 5.0
        mgr.config.sync_interval = 5.0
        calls = {"drain": 0, "task": 0, "sync": 0}
        real_drain = mgr.web.consume_commands
        drained = threading.Event()

        def drain():
            calls["drain"] += 1
            drained.set()  # 每次命令线落袋都亮一次灯: waker 见灯再投下一条(事件同步, 不睡赌)
            return real_drain()

        mgr.web.consume_commands = drain  # 命令线入口(门面), 主循环每轮调用它
        mgr._sync_line = lambda dry_run, flush=True, force=False: calls.__setitem__("sync", calls["sync"] + 1)
        mgr._task_line = lambda dry_run, force=False: calls.__setitem__("task", calls["task"] + 1)
        stop = threading.Event()

        def waker():
            for _ in range(3):
                mgr.wake()  # 模拟 Web 线程连续投递 3 条命令
                if not drained.wait(5.0):
                    break  # 唤醒没被立即消费: 收掉循环让主线程断言报实情, 不挂死
                drained.clear()
            stop.set()
            mgr.wake()

        threading.Thread(target=waker, daemon=True).start()
        mgr.run(dry_run=False, stop_event=stop)
        # 命令线: 首轮 + 3 次唤醒(第 4 次唤醒与停止同时, 可能不再 drain)
        assert calls["drain"] >= 3, f"唤醒后应立即消费命令, 实际 drain {calls['drain']} 次"
        # 任务线/同步线: 只有首轮, 不因唤醒而增加
        assert calls["task"] == 1, f"唤醒不应触发任务线, 实际 {calls['task']}"
        assert calls["sync"] == 1, f"唤醒不应触发同步线, 实际 {calls['sync']}"


def test_run_loop_expect_landing_pulls_sync_forward():
    """添加种子后的有界追平: store 有待落地 hash 时, 同步线被提前到 ~80ms 而不是等节拍

    issue 26-10-30-0626 候选 A: qB 的 add 是四跳异步管线, 命令后那次补刷新必然只拿到一部分,
    剩下的原本要等 sync_interval(1.5s)。登记待落地后主循环应按 store 给的到期时刻再问一次;
    本用例把 sync_interval 设成 5s —— 没有追平, 观测窗口内根本不会有第二次同步。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.sync_interval = 5.0
        mgr.config.main_tick = 5.0
        stamps, forces = [], []

        def sync_line(dry_run, flush=True, force=False):
            stamps.append(time.time())
            forces.append(force)
            if len(stamps) == 1:
                mgr.store.expect_hashes(["H1"])  # 模拟 add 命令受理后登记
                return
            # 同步跑了但这一批还没进 session: 零变化轮(走 _apply 早退分支, 结算同样生效)
            mgr.store._apply({}, [], full=False)
            if len(stamps) >= 4:
                raise KeyboardInterrupt

        mgr._sync_line = sync_line
        mgr._task_line = mock.Mock()
        mgr.run(dry_run=False)

        assert len(stamps) == 4, f"应有首次补刷新 + 3 次追平, 实际 {len(stamps)} 次"
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        assert all(g < 1.0 for g in gaps), f"追平间隔应 ~80ms 而非 5s 节拍, 实际 {gaps}"
        assert forces[1:] == [True] * 3, "追平轮必须 force(否则被「上一版已取走」门控挡掉)"
        assert mgr.store._expect_pending == {"H1"}, "次数未用尽前应保留待办"


def test_drain_web_commands_reports_resync_needed():
    """P0-5 门控: 只有"改 qB 种子状态"的命令(RESYNC_COMMANDS)才置 changed"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # handler 用替身(不碰 qB), 只验证 changed 判定
        mgr._cmd_pause_torrent = mock.Mock()
        mgr._cmd_reload_config = mock.Mock()
        mgr._cmd_build_search_index = mock.Mock()
        mgr.web.commands.put(("reload_config", {"cmd_id": "c1"}))
        mgr.web.commands.put(("build_search_index", {"cmd_id": "c2"}))
        assert mgr.web.consume_commands() is False, "配置热重载/索引构建改的不是种子状态, 不补刷新"
        mgr.web.commands.put(("pause_torrent", {"cmd_id": "c3", "hash": "HA"}))
        assert mgr.web.consume_commands() is True


def test_command_batch_triggers_single_resync():
    """P0-5: 一批改状态命令后补**一次**完整刷新(整批合单), 而不是每条一次

    判据: 同步线设成 5s(观测窗口内本不会再同步), 一批 5 条命令后刷新应恰好 +1。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 5.0
        mgr.config.sync_interval = 5.0  # 无补刷新时观测窗口内不会再次同步
        calls = {"refresh": 0}
        first_refresh = threading.Event()

        def refresh(dry_run=False):
            calls["refresh"] += 1
            if calls["refresh"] == 1:
                first_refresh.set()  # 首轮落定再投命令批(否则首轮直接吃掉, 合单语义无从谈起)
            if calls["refresh"] >= 2:
                raise KeyboardInterrupt  # 观测到"补的那一次"即退出

        mgr._refresh_torrents = refresh
        mgr._task_line = lambda dry_run, force=False: None
        mgr._cmd_pause_torrent = mock.Mock()
        stop = threading.Event()
        # 兜底: 补刷新缺失时循环不会自行退出(刷新停在 1 次), 到点置 stop 防挂死(正常路径自行 cancel)
        timer = _daemon_timer(10.0, stop.set)

        def poster():
            first_refresh.wait(4.0)
            for i in range(5):
                mgr.web.commands.put(("pause_torrent", {"cmd_id": f"c{i}", "hash": "HA"}))
            mgr.wake()

        threading.Thread(target=poster, daemon=True).start()
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        # 首轮(两条线都到期)一次 + 命令批一次 = 2; 5 条命令不产生 5 次
        assert calls["refresh"] == 2, f"一批 5 条命令应只补一次刷新, 实际 {calls['refresh']}"


def test_sync_moved_proxy():
    """S4: `_sync_moved()` 只看本轮是否真有变化(delta/新增/删除任一非空)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr._sync_moved() is False, "空库/无变化轮应为假"
        mgr.store.delta_fields = {"HA": frozenset({"progress"})}
        assert mgr._sync_moved() is True, "有字段变化应为真"
        mgr.store.delta_fields = {}
        mgr.store.last_added = ["HA"]
        assert mgr._sync_moved() is True, "有新增应为真"
        mgr.store.last_added = []
        mgr.store.last_removed = ["HA"]
        assert mgr._sync_moved() is True, "有删除应为真"


def test_cmd_resync_keeps_schedule_when_nothing_moved():
    """S4: 补刷新没拿到变化时**不推后**下一次同步

    时间线: sync_interval=1.0s, 首轮(t≈0)按时同步 -> 下次到期 1.0s; t≈0.9s 一条改状态命令触发
    补刷新, 但它读到同一份节流缓存(delta 全空) -> 到期点必须仍是 1.0s(旧行为会推到 1.9s)。
    判据: 观测到 3 次刷新, 且第 3 次与首轮的间隔 ≈1.0s(阈值 1.4s, 旧行为约 1.9s)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 10.0
        mgr.config.sync_interval = 1.0
        stamps = []

        def refresh(dry_run=False):
            stamps.append(time.time())
            if len(stamps) >= 3:
                raise KeyboardInterrupt  # 观测到第 3 次即退出(不必等满窗口)

        mgr._refresh_torrents = refresh
        mgr._task_line = lambda dry_run, force=False: None
        mgr._cmd_pause_torrent = mock.Mock()
        stop = threading.Event()
        # 兜底: 第 3 次没来时循环不会自行退出, 到点置 stop 防挂死(正常路径自行 cancel)
        timer = _daemon_timer(4.0, stop.set)

        # 命令到达时刻是本用例的**时间语义量**(t≈0.9s, 落在 1.0s 节拍之前一点点):
        # 「补刷新不推后节拍」与旧行为「推到 1.9s」的分差全靠它 —— 提前到 t≈0 会让
        # 旧行为也落在 <1.4s 容差内, 断言失去判别力。用一次性定时器在既定墙钟偏移
        # 投递(不是等它完成, 是模拟外部命令的到达时刻), 不用裸 sleep 赌线程进度。
        def poster():
            mgr.web.commands.put(("pause_torrent", {"cmd_id": "c1", "hash": "HA"}))
            mgr.wake()

        poster_timer = threading.Timer(0.9, poster)
        poster_timer.daemon = True
        poster_timer.start()
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        poster_timer.join(1.0)
        assert len(stamps) >= 3, f"应观测到 3 次刷新(按时/补刷新/下一个按时): {len(stamps)}"
        gap = stamps[2] - stamps[0]
        assert gap < 1.4, f"补刷新无变化时不得推后节拍(第 3 次应 ≈1.0s, 实得 {gap:.2f}s)"


def test_drain_web_commands_bumps_write_seq():
    """P1-4 只读缓存**失效接线**: 写命令执行后 `_web_write_seq` 必须自增; 自投递命令不得自增

    缓存以 `(key, write_seq)` 组键 ⇒ 序号不自增则缓存**永不失效**(改完分类仍看到旧列表);
    而自投递命令(build_search_index)频次高, 计进去会让缓存在建索引期间完全失效。
    此前全仓只测了缓存机制本身, 没有任何用例断言这条接线 —— 字段改名或把自增挪走
    都会让测试全绿而缓存静默失效。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._cmd_reload_config = mock.Mock()
        mgr._cmd_build_search_index = mock.Mock()
        before = mgr.web.write_seq

        mgr.web.commands.put(("reload_config", {"cmd_id": "c1"}))
        mgr.web.consume_commands()
        assert mgr.web.write_seq == before + 1, "写命令执行后写序号必须自增(否则只读缓存永不失效)"

        mgr.web.commands.put(("build_search_index", {"cmd_id": "c2"}))
        mgr.web.consume_commands()
        assert mgr.web.write_seq == before + 1, "自投递命令不得自增(否则建索引期间缓存全废)"


def test_drain_bumps_write_seq_before_writing_receipt():
    """BUG-5: 先让缓存失效, 再宣布命令成功 —— 回执写入时写序号必须**已经**自增

    前端拿到回执会立刻重取只读端点(如改完分类重取 /api/categories); 若回执先写, 那一瞬的
    读会命中旧写序号的缓存键。用 spy 在 _set_web_result 内部观察当时看到的序号, 把顺序钉死。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._cmd_reload_config = mock.Mock()
        seen = {}
        real_set = mgr.web.set_result

        def spy(cmd_id, status, error="", timing=None, truth=None):
            seen["seq"] = mgr.web.write_seq  # 回执写入那一刻的序号
            return real_set(cmd_id, status, error, timing, truth)

        mgr.web.set_result = spy  # 回执的唯一落点在门面(见 WebUIRuntime.set_result)
        before = mgr.web.write_seq
        mgr.web.commands.put(("reload_config", {"cmd_id": "c1"}))
        mgr.web.consume_commands()
        assert seen.get("seq") == before + 1, (f"回执写入时写序号应已自增(先失效缓存再宣布成功), 实际 {seen.get('seq')} vs 期望 {before + 1}")


def test_run_due_requeues():
    """run_due: handler 返回 True -> 收尾按 interval 重入队(run_count+1, 回 PENDING)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: REQUEUE)
        now = time.time()
        mgr.task_queue.add_task(task, now=now)
        assert mgr.task_queue.run_due(dry_run=False, now=now) == 1
        assert task.run_count == 1
        assert task.state == PENDING


def test_run_due_dies():
    """run_due: handler 返回 False -> 不重入(任务消亡)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: FINISHED)
        now = time.time()
        mgr.task_queue.add_task(task, now=now)
        assert mgr.task_queue.run_due(dry_run=False, now=now) == 1
        assert task.run_count == 0, "消亡任务不应重入队"


def test_own_write_defer_gate_targets_group_members():
    """守阵(A 系 S2 D-1): 队列级 deferral 闸门判据 —— 目标 hash 或其组任一成员 ∈ own_writes 即让位

    红验: 去掉 _own_write_defer_gate 的组维度(只判 hash ∈ own_writes) -> `HC` 断言红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        seed_store(mgr, [FakeTorrent(hash="HD"), FakeTorrent(hash="HC"), FakeTorrent(hash="HX")])
        mgr.store.groups["K"] = ["HD", "HC"]
        mgr.store.member_to_key["HD"] = "K"
        mgr.store.member_to_key["HC"] = "K"
        gate = mgr._own_write_defer_gate

        assert gate(Task("rule", "r", hash="HX")) is None, "无登记时不拦"
        assert gate(Task("rule", "r", hash="")) is None, "无 hash 全局任务不拦"
        mgr.store.note_own_write("HD")
        assert gate(Task("rule", "r", hash="HD")) is not None, "自身命中"
        assert gate(Task("rule", "r", hash="HC")) is not None, "同组成员命中(组维度)"
        assert gate(Task("rule", "r", hash="HX")) is None, "非同组不拦"


def test_create_torrent_tasks_tor_missing():
    """_create_torrent_tasks: 种子不在快照 -> 直接返回 False, 不建任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        assert mgr.host.get("rules")._create_torrent_tasks("NOPE") is False
        assert mgr.task_queue._fast == []


def test_create_torrent_tasks_with_rules():
    """_create_torrent_tasks: 匹配 tracker -> 创建 maintenance + 全部规则任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="HASH123", tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 显式 setUp: 模拟 _refresh_torrents 匹配
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        mgr.host.get("rules")._create_torrent_tasks("HASH123")
        names = [t.name for t in mgr.task_queue._fast]
        assert "maintenance" in names, f"应创建内置任务: {names}"
        assert "example_rules.add_site_tag" in names, f"应创建规则任务: {names}"


def test_execute_due_respects_max():
    """_tick: 每 tick 最多执行 max_tasks_per_tick 个到期任务, 超额留在队列"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.task_queue = TaskQueue()
        mgr.config.max_tasks_per_tick = 2
        for i in range(3):
            t = Task("rule", f"t{i}", interval=60, handler=lambda t, d: REQUEUE)
            mgr.task_queue.add_task(t)  # next_run=now, 全部到期
        mgr._refresh_torrents = mock.Mock()
        mgr._tick(dry_run=False)
        executed = [t.name for t in mgr.task_queue._fast if t.run_count == 1]
        remaining = [t.name for t in mgr.task_queue._fast if t.run_count == 0]
        assert len(executed) == 2, f"每 tick 最多执行 max_tasks_per_tick=2: {executed}"
        assert len(remaining) == 1, f"超额任务应留在队列: {remaining}"


def test_tick_no_due_task_empty_queue():
    """任务队列为空: tick 刷新后无到期任务, 不执行任何任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()  # 无种子
        mgr._tick(dry_run=True)
        assert mgr.task_queue.run_due(time.time(), max_tasks=10) == 0


def test_p2a_sync_line_flush_propagates_to_host():
    """_sync_line flush=True: 视图收尾钩子经 host.run_sync_line 执行; flush=False 不调"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        with mock.patch.object(mgr.host, "run_sync_line") as hook:
            mgr._sync_line(dry_run=True, flush=True, force=True)
            hook.assert_called_once_with(True)
        with mock.patch.object(mgr.host, "run_sync_line") as hook2:
            mgr._sync_line(dry_run=True, flush=False, force=False)
            assert hook2.call_count == 0, "flush=False 不执行视图收尾钩子"


def test_w6_task_line_receives_dry_run():
    """守阵(W6, 中): 任务线分派必须传 dry_run 位置实参(丢参 = 每轮 TypeError 退避环)且真值等待轮 force=True

    elif tick_due 分派点: dry_run 缺参即 TypeError; force 丢失/None 化 = 表现层收尾门控失效
    (真值等待轮必须绕"上一版是否被取走"门控)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 5.0
        mgr.web.truth_pending = {"c1": {"cmd": "pause", "args": {"hashes": ["H1"]}, "ts": time.time()}}
        mgr.web.flush_truths = lambda: None  # 真值恒未落地: 每轮 cmd_forced=True
        stop = threading.Event()
        timer = _daemon_timer(4.0, stop.set)
        task_calls = []
        sync_calls = []

        def task_line(dry_run, force=False):
            task_calls.append((dry_run, force))
            if len(task_calls) >= 2:
                stop.set()

        def sync_line(dry_run, flush=True, force=False):
            sync_calls.append(dry_run)

        mgr._task_line = task_line
        mgr._sync_line = sync_line
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert task_calls == [(False, True), (False, True)], f"任务线必须收到 dry_run 位置实参且 force=True: {task_calls}"
        assert not [r for r in cap.records if r.levelname == "ERROR"], \
            "任务线分派不得抛 TypeError 缺参进退避环(主循环异常 ERROR 即红)"


def test_w6_truth_pending_one_shot_no_extra_sync():
    """守阵(W6, 低): 真值已落地(flush 清空 pending)后不得继续 0.2s 重试弧(and 不得退化成 or)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 5.0
        mgr.config.sync_interval = 5.0
        mgr.web.truth_pending = {"c1": {"cmd": "pause", "args": {"hashes": ["H1"]}, "ts": time.time()}}

        def drain_once():
            mgr.web.truth_pending = {}

        mgr.web.flush_truths = drain_once
        stop = threading.Event()
        timer = _daemon_timer(1.5, stop.set)
        sync_calls = []
        mgr._sync_line = lambda dry_run, flush=True, force=False: sync_calls.append(dry_run)
        mgr._task_line = lambda dry_run, force=False: None
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(sync_calls) == 1, f"真值落地后不得继续重试弧(and 退化成 or = 0.2s 白刷): {len(sync_calls)} 次"


def test_w6_sync_line_contract():
    """守阵(W6, 中/低): 同步线默认 flush 开/force 关, dry_run 直传刷新(生产调用不传 flush)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._refresh_torrents = mock.Mock()
        mgr.host.run_sync_line = mock.Mock()
        mgr._sync_line(False)
        assert mgr._refresh_torrents.call_args == mock.call(False), "同步线必须把 dry_run 原样传刷新(None≈False=dry-run 真写)"
        assert mgr.host.run_sync_line.call_args_list == [mock.call(False)], "flush 缺省必须收尾 on_sync_line 且 force=False"
        mgr._sync_line(False, flush=False)
        assert mgr.host.run_sync_line.call_count == 1, "flush=False 不收尾"


def test_w6_task_line_contract():
    """守阵(W6, 中/低): 任务线 run_due 实参契约(defer_gate 身份直传) + 收尾 force 默认 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.task_queue.run_due = mock.Mock()
        mgr.host.run_task_line = mock.Mock()
        mgr._task_line(True)
        call = mgr.task_queue.run_due.call_args
        assert call.args == (True, ), f"run_due 必须收到 dry_run 位置实参: {call}"
        assert call.kwargs["defer_gate"] == mgr._own_write_defer_gate, "defer_gate 必须接到队列级闸门(None=闸失效)"
        assert call.kwargs["max_tasks"] == mgr.config.max_tasks_per_tick
        assert mgr.host.run_task_line.call_args_list == [mock.call(False)], "收尾 force 缺省 False 且不得为 None"
