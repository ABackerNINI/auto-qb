"""test_qbmanager_loop 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_run_loop_managed_never_sleeps: 传 stop_event 时不 sleep(托盘模式停止信号即时响应)
- test_run_loop_layered_cadence: 分层节拍——同步线按 sync_interval、任务线按 main_tick, 两线次数不等
- test_run_main_loop: 主循环: _tick 异常被捕获, KeyboardInterrupt 停止, finally 清理
- test_tick_full_flow: 快速队列到期任务执行全流程(含 check 轮询任务首轮发送)
- test_handle_maintenance_tor_missing: 种子不存在 -> False(任务消亡)
- test_run_save_state_on_exit: run 退出后保存状态文件且为有效 JSON dict
- test_run_dry_run_no_save: dry_run=True 退出后不写状态文件
- test_periodic_flush_is_wired_in_run_loop: 接线守阵——周期落盘必须挂在主循环(not dry_run 门内), run() 加载状态后重置到期点
- test_run_stopiteration_from_tick_not_swallowed: 守阵(26-10-02-0442)——_tick 的 StopIteration 在 except Exception 之前单独接住并重抛, 不得吞掉后继续下一拍
- test_run_exception_backs_off_next_tick: 守阵(26-10-02-0728)——主循环 except Exception 路径必须把 next_*_at 推到 max(原值, now+main_tick) 退避, 不得 wait_for=0 快速重试
- test_p2a_init_with_lock_cleans_orphan_tmp_and_releases: 持锁构造清孤儿 tmp; 释放后可再持锁 (P2-a)
- test_p2a_run_with_lock_releases_in_finally: run() finally 释放锁 (P2-a)
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

from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _throttle, _wait_next

from auto_qb.torrents import QbCompatError

from helpers import LEGACY_V1, FakeClient, FakeConfig, FakeTorrent, capture_logs, make_manager, seed_store


def test_run_loop_managed_never_sleeps():
    """托管模式(传 stop_event): 阻塞走 Event.wait, 绝不调用 time.sleep(托盘停止信号即时响应)

    分层节拍后停止信号与命令唤醒是两个独立事件(Python 无多事件等待原语), `_wait_next`
    按 STOP_POLL_INTERVAL 分段 wait(stop_event) 并在段间检查唤醒 —— 分段不影响本用例
    的判据: 只要没走 time.sleep, 停止信号就仍是即时响应的。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        # 两条线同拍 -> 每轮走完整 _tick
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        stop_event = threading.Event()
        with mock.patch("auto_qb.core.qbmanager.time.sleep") as fake_sleep:
            mgr.run(dry_run=True, stop_event=stop_event)
        fake_sleep.assert_not_called()
        assert mgr._tick.call_count == 2


def test_run_loop_layered_cadence():
    """分层节拍: 同步线按 sync_interval、任务线按 main_tick, 两条线各有各的节拍

    这是"状态新鲜度不再被任务节拍拖累"的直接判据 —— 若退化成单一 cadence, 两线次数会相等。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.sync_interval = 0.05
        mgr.config.main_tick = 0.2
        calls = {"sync": 0, "task": 0}

        def sync_line(dry_run, flush=True, force=False):
            calls["sync"] += 1
            if calls["sync"] >= 12:
                raise KeyboardInterrupt  # 同步线 12 次 ≈ 0.6s 后退出

        def task_line(dry_run, force=False):
            calls["task"] += 1

        mgr._sync_line = sync_line
        mgr._task_line = task_line
        mgr.run(dry_run=False)
        assert calls["sync"] == 12
        # 0.6s / 0.2s ≈ 3 次(允许调度抖动); 关键是远小于同步线的 12 次
        assert 2 <= calls["task"] <= 4, f"任务线不应跟同步线同频, 实际 {calls['task']}"


def test_run_main_loop():
    """run: 连接成功进入主循环; _tick 异常被捕获; KeyboardInterrupt 停止; finally 清理+保存"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # !节拍调小(26-10-02-0728): 异常路径现在会推进 next_*_at 退避, 第一次异常后主循环
        # 真等一个 main_tick 才进下一拍 —— 默认 1.0s 会让本用例多挂 1s。
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        mgr._tick = mock.Mock(side_effect=[RuntimeError("boom"), KeyboardInterrupt()])
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        assert mgr._tick.call_count == 2, "异常应被捕获继续循环, KeyboardInterrupt 退出"
        assert os.path.exists(state_file), "finally 应保存状态"


def test_tick_full_flow():
    """_tick: 快速队列到期任务执行(含 check 轮询任务首轮执行 + 常规任务 reschedule)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(hash="HASH123", state="pausedUP")
        mgr.task_queue = TaskQueue()
        # check 轮询任务: 首轮执行后消亡(handler 返回 False)
        check_calls = []

        def check_poll(t, d):
            check_calls.append(1)
            return FINISHED

        mgr.task_queue.add_task(
            Task("check", "check-checking-result", hash="HASH123", interval=2.0, handler=check_poll)
        )
        # 常规到期任务
        due_task = Task("rule", "t", interval=0, handler=lambda t, d: REQUEUE)
        due_task.next_run = time.time() - 1
        mgr.task_queue._fast.append(due_task)
        mgr._refresh_torrents = mock.Mock()
        mgr._tick(dry_run=False)
        assert check_calls == [1], "check 任务应执行"
        assert due_task.run_count == 1, "到期任务应执行并 reschedule"


def test_handle_maintenance_tor_missing():
    """_handle_maintenance_task_interface: 种子不存在 -> False(任务消亡, 不重入队)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        task = Task("internal", "maintenance", hash="NOPE", store=mgr.store)
        assert mgr.host.get("maintenance").handle_maintenance(task.torrent, dry_run=False) is False


def test_run_save_state_on_exit():
    """run: 非 dry_run 退出后保存状态文件, 且内容为有效 JSON dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=KeyboardInterrupt())
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "状态文件应为 JSON dict"


def test_run_dry_run_no_save():
    """run: dry_run=True 退出后不写状态文件"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=KeyboardInterrupt())
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=True)
        assert not os.path.exists(state_file), "dry_run 不应写状态文件"


def test_periodic_flush_is_wired_in_run_loop():
    """接线守阵: 周期落盘必须挂在主循环正常路径(not dry_run 门内), 到期点在加载状态后重置

    maybe_flush 只在主循环线程调用是单一写线程约束的一部分; dry_run 门保证观察
    模式零磁盘写入(与退出路径 `if not dry_run` 口径一致); 启动即到期会造成无意义重写。
    """
    import inspect

    from auto_qb.core.qbmanager import QbManager

    src = inspect.getsource(QbManager.run)
    i_hook = src.find("maybe_flush")
    assert i_hook >= 0, "run() 必须接线周期落盘"
    assert "not dry_run" in src[max(0, i_hook - 200):i_hook], "周期落盘必须在 not dry_run 门内(dry-run 零磁盘写入)"
    assert "self.ctx.state.next_flush_at = time.time()" in src, "run() 加载状态后必须重置周期落盘到期点"


def test_run_stopiteration_from_tick_not_swallowed():
    """回归守阵(issue 26-10-02-0442): _tick 抛 StopIteration 不得被 except Exception 吞掉后继续下一拍

    StopIteration 是 Exception 子类, 修复前被吞后本轮 next_sync_at/next_tick_at 未推进,
    wait_for=0, while True 立即进下一拍 —— 「无 sleep、无工作」的静默空转死循环。修法:
    主循环在 except Exception 之前单独接住, ERROR 落日志后重抛(PEP 479 精神: StopIteration
    逃出 _tick 调用链 = 生成器误用 bug, 显式失败优于静默空转)。红验(修复前): StopIteration
    被吞, run() 正常返回, _tick 被调到第 2 个兜底退出点 —— 本用例当时判红。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # 连续 StopIteration: 修复前每一拍都被吞下去(第 2 个 KeyboardInterrupt 只是红验时的兜底退出点)
        mgr._tick = mock.Mock(side_effect=[StopIteration(), KeyboardInterrupt()])
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            with pytest.raises(StopIteration):
                mgr.run(dry_run=False)
        assert mgr._tick.call_count == 1, "StopIteration 必须当场穿透 run(), 不得进入下一拍"


def test_run_exception_backs_off_next_tick():
    """守阵(26-10-02-0728): 主循环异常路径必须推进 next_*_at 退避, 不得 wait_for=0 快速重试

    except Exception 只记日志不推进 next_sync_at/next_tick_at —— 首轮两者是 0.0, 非首轮是
    已到期的过去值, wait_for 恒算出 0, while True 立即进下一拍重跑同一条线再炸一次, 形成
    无退避的快速重试循环(ERROR 刷屏 + CPU 空转)。StopIteration 已重抛(26-10-02-0442)、
    APIConnectionError 走 _reconnect_due 退避, 均不在此列; 修法: 异常分支把两条时间线推到
    max(原值, now + main_tick), 失败的线最早下个节拍重试(退避起步与 _reconnect_due 一致)。
    三条线都替换成炸点: 异常发生在哪条线(双到期走 _tick / 单到期走 _sync_line/_task_line)
    取决于浮点时间边界, 全替换保证判据与分支选择解耦。
    红验(修复前): 异常拍之间间隔 ≈ 0(wait_for=0), gaps 断言当时判红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.2
        mgr.config.sync_interval = 0.2
        stop_event = threading.Event()
        tick_at: list = []

        def boom(dry_run, flush=True, force=False):
            tick_at.append(time.monotonic())
            if len(tick_at) >= 3:
                stop_event.set()
            raise RuntimeError("tick boom")

        mgr._tick = boom
        mgr._sync_line = boom
        mgr._task_line = boom
        mgr.run(dry_run=True, stop_event=stop_event)
        assert len(tick_at) == 3, f"应恰好 3 拍后停: {len(tick_at)}"
        gaps = [b - a for a, b in zip(tick_at, tick_at[1:])]
        assert all(g >= 0.15 for g in gaps), f"异常拍之间必须退避 >= main_tick(0.2s): {gaps}"


def test_p2a_init_with_lock_cleans_orphan_tmp_and_releases():
    """持锁构造(no_lock=False): acquire 后清上次崩溃遗留的孤儿 tmp; 释放后可再次持锁"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        orphan = state_file + ".crashleft.tmp"
        with open(orphan, "w", encoding="utf-8") as f:
            f.write("{}")
        cfg = FakeConfig()
        cfg.state_file = state_file
        mgr = make_manager(cfg=cfg, no_lock=False)
        try:
            assert not os.path.exists(orphan), "持锁后应清掉孤儿 tmp 文件"
            assert mgr._lock is not None
        finally:
            mgr._lock.release()
        # 锁已释放: 第二个实例可再次持锁(证明第一个真的持有过)
        mgr2 = make_manager(cfg=cfg, no_lock=False)
        mgr2._lock.release()


def test_p2a_run_with_lock_releases_in_finally():
    """run() 正常退出路径(finally): 持锁构造下锁必须被释放(停机后其他实例可接管)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_manager(cfg=cfg, no_lock=False)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        mgr.run(dry_run=False)
        assert mgr.connect.call_count == 1
        # 锁已释放: 再次持锁应成功
        from auto_qb.infra.locking import SingleInstanceLock

        SingleInstanceLock(cfg.state_file).acquire()  # 不抛 = 已释放
        lock2 = SingleInstanceLock(cfg.state_file)
        lock2.acquire()
        lock2.release()
