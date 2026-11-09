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
- test_start_all_failure_runs_stop_all_and_skips_state: start_all 抛错时 finally 仍执行 stop_all, 失败启动不落空态 state.json (S3)
- test_start_all_failure_releases_lock: 启动期抛错后锁与 state.lock.meta.json 均已释放, 他实例可接管 (S3)
- test_hr_bind_error_on_start_releases_lock_and_skips_state: HR 的 HrChannelBindError 走同一 finally 路径, 既有漏锁已修 (S3)

覆盖率第三轮 T2b 补测(26-11-05):
- test_run_cmd_driven_sync_not_by_time_keeps_next_sync: tick 到期而同步时间未到的命令轮, 白刷不重设 next_sync_at(619->633; 假时钟直驱)
- test_run_refresh_gate_reset_beat_observable_window: 补刷新闸(637/642)重设节拍的可观测分歧必须落进用例观察窗内(26-11-05-0200; 假时钟直驱)
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

from clock import FakeClock

from auto_qb.config import QbittorrentConfig

from auto_qb.config import PathMapEntry

from auto_qb.config.models import FsConfig

from auto_qb.infra.errors import AutoQbError

from auto_qb.infra import file_access

from auto_qb.infra.file_access import MappedFileAccess

from auto_qb.core.module import ApplyResult, BaseModule

from auto_qb.hr import HrChannelBindError

from auto_qb.core import qbmanager as _qbm

from auto_qb.core.qbclient import REQUESTS_TIMEOUT, LocalQbClient, new_client

from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _wait_next

from auto_qb.torrents import QbCompatError

from helpers import LEGACY_V1, FakeClient, FakeConfig, FakeTorrent, capture_logs, make_manager, seed_store


def test_run_loop_managed_never_sleeps():
    """托管模式(传 stop_event): 阻塞走事件等待, 绝不经 time.sleep 系节流(托盘停止信号即时响应)

    分层节拍后停止信号与命令唤醒是两个独立事件(Python 无多事件等待原语), 等待原语统一是
    `_wait_next`(托管分支按 STOP_POLL_INTERVAL 分段 wait 并在段间检查唤醒)。S3 monkeypatch
    收敛后守阵不再 patch stdlib time(进程级面过宽), 改钉 run() 的实际等待站点: 透传 spy
    包住 `_wait_next`, 断言 run() 的等待全部经该原语 —— 绕开原语直 sleep 的回归当场红;
    裸 time.sleep 混进 run() 则由 test_run_loop_throttles_without_stop_event 的
    真实经过时间判据兜住(空转/不阻塞当场红)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        # 两条线同拍 -> 每轮走完整 _tick
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        stop_event = threading.Event()
        real_wait = _qbm._wait_next
        with mock.patch.object(_qbm, "_wait_next", side_effect=real_wait) as fake_wait:
            mgr.run(dry_run=True, stop_event=stop_event)
        assert fake_wait.call_count >= 1, "run() 的等待必须全部经 _wait_next 原语(绕开直 sleep 即回归)"
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
        # !无需 stub sleep: 等待原语统一 _wait_next(事件等待), run() 不触 time.sleep(S3 收敛)
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
        mgr.run(dry_run=False)  # 等待原语统一 _wait_next(事件等待), run() 不触 time.sleep(S3 收敛)
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
        mgr.run(dry_run=True)  # 等待原语统一 _wait_next(事件等待), run() 不触 time.sleep(S3 收敛)
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
    assert "self.ctx.state.next_flush_at = self._clock.now()" in src, "run() 加载状态后必须重置周期落盘到期点(S2 时钟注入后的字面)"


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
        with pytest.raises(StopIteration):  # 等待原语统一 _wait_next, run() 不触 time.sleep(S3 收敛)
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


class _StartBoomModule(BaseModule):
    """S3 测试替身: start 抛指定异常(模拟 WebUI/HR 启动期失败), stop 只记调用"""

    name = "s3_start_boom"

    def __init__(self, exc):
        self._exc = exc
        self.stopped = False

    def start(self, ctx, dry_run):
        raise self._exc

    def stop(self):
        self.stopped = True


def test_start_all_failure_runs_stop_all_and_skips_state():
    """守阵(S3): start_all 抛错必须进 finally —— stop_all 仍执行, 且失败启动不落空态 state.json

    修复前 start_all 在 try 之外, 抛错直接穿透 run(), finally 被跳过: 模块未停、锁未放。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        boom = _StartBoomModule(RuntimeError("start boom"))
        mgr.host.register(boom)
        with pytest.raises(RuntimeError, match="start boom"):
            mgr.run(dry_run=False)
        assert boom.stopped, "启动期抛错必须走 stop_all(模块 stop 被调用)"
        assert not os.path.exists(state_file), "失败启动不得落空态 state.json(fresh 目录)"


def test_start_all_failure_releases_lock():
    """守阵(S3): 启动期抛错后单实例锁与其伴生 meta 均已释放, 他实例可接管"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_manager(cfg=cfg, no_lock=False)
        boom = _StartBoomModule(RuntimeError("start boom"))
        mgr.host.register(boom)
        assert os.path.exists(mgr._lock.meta_path), "前置: 构造期持锁应已写 state.lock.meta.json"
        with pytest.raises(RuntimeError, match="start boom"):
            mgr.run(dry_run=False)
        assert mgr._lock._held is False, "finally 必须释放单实例锁"
        assert not os.path.exists(mgr._lock.meta_path), "finally 必须移除 state.lock.meta.json"
        from auto_qb.infra.locking import SingleInstanceLock

        lock2 = SingleInstanceLock(cfg.state_file)
        lock2.acquire()  # 不抛 = 锁确实已释放
        lock2.release()
        assert not os.path.exists(cfg.state_file), "失败启动不得落空态 state.json"


def test_hr_bind_error_on_start_releases_lock_and_skips_state():
    """守阵(S3): HR 的 HrChannelBindError 在启动期抛出同样走 finally —— 既有漏锁行为已修

    修复前该异常与其它模块 start 抛错一样跳过 finally: 锁与 meta 残留(HR fail-fast 的
    既有缺陷)。S3 把 start_all 移入 try 后, 同一路径必须释放锁且不落 state.json。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_manager(cfg=cfg, no_lock=False)
        boom = _StartBoomModule(HrChannelBindError("HR 端点端口被占用"))
        mgr.host.register(boom)
        with pytest.raises(HrChannelBindError):
            mgr.run(dry_run=False)
        assert boom.stopped, "HrChannelBindError 也必须走 stop_all"
        assert mgr._lock._held is False, "HR fail-fast 不得漏锁"
        assert not os.path.exists(mgr._lock.meta_path), "HR fail-fast 不得残留 meta"
        assert not os.path.exists(cfg.state_file), "失败启动不得落空态 state.json"


# ---------- 覆盖率第三轮 T2b 补测(26-11-05): 命令驱动补刷新不重设同步节拍 ----------


def test_run_cmd_driven_sync_not_by_time_keeps_next_sync(monkeypatch):
    """(T2b)tick 到期而同步时间未到的命令轮(619->633): sync_due_by_time 假 + _sync_moved()
    假(白刷) -> 不重设 next_sync_at —— 命令驱动的白刷不能把下一次自然校正推后一个周期。
    假时钟 + _wait_next 步进直驱: 唤醒时刻不再是真实挂钟, 分支判据(轮次到点关系)确定化"""
    from auto_qb.core import qbmanager as qbm

    clock = FakeClock(start=1_800_000_000.0)  # 纪元取 2027 年附近: 避开 Windows 1970 邻域 timestamp OSError 坑
    # 注入须先于 QbManager 构造(缺省钟在构造期解析模块属性; 旧「换模块 time 名」在调用期
    # 生效, 时序等价面 = 构造前替换)
    monkeypatch.setattr(qbm, "SYSTEM_CLOCK", clock)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.sync_interval = 1.5
        mgr.config.main_tick = 2.0

        steps = iter([1.8, 0.2, 1.0, 1.0])  # 各轮推进量: 1001.8 / 1002 / 1003 / 1004

        def _fake_wait(stop_event, wake_event, timeout):
            clock.advance(next(steps, 1.0))
            return False

        monkeypatch.setattr(qbm, "_wait_next", _fake_wait)
        mgr.host.run_command_line = mock.Mock(return_value=True)  # 每轮都有命令改状态
        mgr._tick = mock.Mock(side_effect=[None, None, KeyboardInterrupt()])
        sync_times = []
        mgr._sync_line = lambda dry_run, flush=True, force=False: sync_times.append(clock.now())
        mgr.run(dry_run=False)
        assert mgr._tick.call_count == 3, "命令轮(614 支)恰好三轮后 KI 退出"
        assert sync_times == [1_800_000_001.8, 1_800_000_003.0], sync_times


# ---------- 补刷新闸观察窗收口(26-11-05-0200): 重设节拍的分歧落进窗内 ----------


def test_run_refresh_gate_reset_beat_observable_window(monkeypatch):
    """(26-11-05-0200)补刷新闸(637/642 的 `if sync_due_by_time or self._sync_moved()`)
    重设同步节拍的可观测分歧必须落在用例观察窗内 —— 上一版 T2b 的窗止于第 4 轮 KI 退出前,
    闸门改写 next_sync_at 的后果(下一次按点同步的时刻后移)永远落在退出之后, P2 红验注入
    三型变异(`if True`x2 / `or`->`and`)全部存活。本用例把窗拉长到第 6 轮: 节拍表经变异
    模拟器逐世界验证(裸 float 累加口径, 最小闸门裕度 0.2s 无刀锋判据), 4 个变异世界的
    sync 时刻表都与正确世界不同 = 全杀。

    轮次表(相对 T0, sync_interval=1.5, main_tick=2.0, 每轮都有 run_command_line 之外的
    命令驱动由 cmds 序列控制; moved 恒假 = 与被 lambda 掉的 _sync_line 同口径的白刷):
      R1 t=0.0  cmd=T  tick#1(双 due)  闸: by_time 真 -> 重设 next_sync=1.5
      R2 t=0.7  cmd=T  命令驱动 sync   闸: by_time 假+moved 假 -> 不重设(白刷, T2b 语义)
      R3 t=1.7  cmd=F  按点 sync        闸: by_time 真 -> 重设 next_sync=3.2
      R4 t=2.3  cmd=T  tick#2          闸: by_time 假+moved 假 -> 不重设 <- 若被 `if True`
                  改写则重设到 3.8, R5 的按点同步(3.5>=3.2)当场消失 = 分歧进窗
      R5 t=3.5  cmd=F  按点 sync        闸: by_time 真 -> 重设 next_sync=5.0
      R6 t=4.7  cmd=T  tick#3 -> KI
    假时钟 + _wait_next 步进直驱(与 T2b 同款), 期望值按与时钟一致的累加顺序书写(浮点逐位相等)。
    """
    from auto_qb.core import qbmanager as qbm

    clock = FakeClock(start=1_800_000_000.0)  # 2027 年附近: 避开 Windows 1970 邻域 timestamp OSError 坑
    monkeypatch.setattr(qbm, "SYSTEM_CLOCK", clock)  # 构造前替换(缺省钟在构造期解析模块属性)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.sync_interval = 1.5
        mgr.config.main_tick = 2.0

        steps = iter([0.7, 1.0, 0.6, 1.2, 1.2])  # 各轮推进量: 0.7 / 1.7 / 2.3 / 3.5 / 4.7(R6 KI)

        def _fake_wait(stop_event, wake_event, timeout):
            clock.advance(next(steps, 1.0))
            return False

        monkeypatch.setattr(qbm, "_wait_next", _fake_wait)
        # 命令驱动序列(逐轮): R1..R6; R3/R5 无命令 -> 只有按点同步可驱动 sync 分支,
        # 正是"重设节拍是否被闸门放行"的可观测面
        mgr.host.run_command_line = mock.Mock(side_effect=[True, True, False, True, False, True])
        mgr._tick = mock.Mock(side_effect=[None, None, KeyboardInterrupt()])
        mgr._task_line = mock.Mock()  # 防御性: 轮次表设计保证任何世界都不进任务分支
        sync_times = []
        mgr._sync_line = lambda dry_run, flush=True, force=False: sync_times.append(clock.now())
        moved_seq = iter([False, False])

        def _fake_moved():
            return next(moved_seq, False)

        mgr._sync_moved = mock.Mock(side_effect=_fake_moved)
        # 恒假: 快照零变化(白刷口径), 与被 lambda 掉的 _sync_line 一致。留 Mock 是为了数
        # 闸门对它的求值次数: 正确世界仅 R2/R4 两道闸(其余轮 by_time 短路)恰调 2 次;
        # 双行同时 or->and 注入的世界(单行注入各自可被 sync_times 杀, 双行下 next_sync_at
        # 恒 0 -> 每轮 by_time 恒真, 线选择与 sync/tick 计数都同正确世界, 闸门结局的分歧
        # 跨 R1/R3/R5 且横跨 tick/sync 两分支)每道闸都求值 = 5 次, 下面的 call_count 断言把它也杀掉。
        mgr.run(dry_run=False)
        t_r2 = 1_800_000_000.0 + 0.7
        t_r3 = t_r2 + 1.0
        t_r5 = t_r3 + 0.6 + 1.2  # R5 时刻; 本式末位 +1.2 是 R4 的等待步(steps[3], 落到 3.5),
        # steps 末位(第 5 个)1.2 才是 R6 的推进(落到 4.7, 其后第 3 次 _tick 即 KI), 不计入本式
        assert mgr._tick.call_count == 3, "恰三次 _tick(第 3 次抛 KI 退出)"
        assert sync_times == [t_r2, t_r3, t_r5], sync_times
        assert mgr._task_line.call_count == 0, "轮次表内不得误入任务分支"
        assert mgr._sync_moved.call_count == 2, "正确世界恰 R2/R4 两道闸求值 moved(其余轮 by_time 短路)"
