"""test_qbmanager_w6 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_w6_wait_next_waits_full_timeout: 守阵(W6)——托管等待必须睡满 timeout(等待归零=CPU 空转回归)
- test_w6_init_signature_and_field_contracts: 守阵(W6)——签名默认值与构造期字段契约(no_lock/dry_run 默认 False、api.store 绑定、初始值)
- test_w6_init_loads_config_from_path: 守阵(W6)——config 未传时必须以 config_path 加载配置
- test_w6_init_wires_fs_notify_relocate: 守阵(W6)——fs.path_map 产出 Mapped 映射访问层 + notify/relocate 模块挂真 ctx
- test_w6_init_creates_state_dir_console_only: 守阵(W6)——console-only 配置下数据目录必须显式创建
- test_w6_pause_branch_keeps_looping: 守阵(W6)——暂停分支等待实参契约 + 暂停不退化为停机 + 停止 INFO
- test_w6_next_flush_at_respects_save_interval: 守阵(W6)——周期落盘到期点 = now+interval(0=关闭不得强转)
- test_w6_periodic_flush_gate_and_migration_arg: 守阵(W6)——周期落盘 not dry_run 门 + materialize_migration 实参
- test_w6_truth_pending_drives_retry_arc: 守阵(W6)——真值未落地按 0.2s 重试弧持续补同步且 force=True
- test_w6_cmd_forced_and_t_line_contract: 守阵(W6)——cmd_forced 门控契约 + 命令线计时弧恰发一次
- test_w6_micro_deadline_merged_into_wait: 守阵(W6)——微步到期必须并入等待超时
- test_w6_micro_deadline_does_not_delay_lines: 守阵(W6)——更晚的微步到期不得推迟同步/任务线
- test_w6_flush_fallback_once_per_round: 守阵(W6)——回执 flush 每轮恰一次(异常轮兜底/正常轮不重复) + KI 停止 INFO
- test_w6_stopiteration_error_detail: 守阵(W6)——StopIteration ERROR 消息与堆栈不得丢真
- test_w6_generic_exception_error_detail: 守阵(W6)——主循环异常 ERROR 消息与堆栈不得丢真
- test_w6_migration_and_start_stop_logs: 守阵(W6)——迁移/启动/停止 INFO 审计面 + desc 空不打迁移日志
- test_w6_apply_new_config_contract: 守阵(W6)——热重载回执契约 + qbittorrent 段变重连(双向) + 汇总日志
- test_w6_apply_new_config_restart_gate: 守阵(W6)——R 级闸返回需重启段且日志保留提示
- test_w6_apply_new_config_unclaimed_fallback: 守阵(W6)——未认领段兜底: WARNING + rebuild_runtime 相位 + 回执条目契约
- test_w6_tick_contract: 守阵(W6)——_tick 双线合轮实参契约(sync flush=False / task force 直传)
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

from qbmanager_support import (
    _daemon_timer,
)


def test_w6_wait_next_waits_full_timeout():
    """守阵(W6, 中): _wait_next 必须睡满 timeout 再返回

    deadline 排进过去 / while False / remaining<=1 三类变异都把等待归零 —— 托管模式
    主循环变 CPU 空转(_throttle 2026-09-14 回归同型, 请求/CPU 放大面)。
    """
    stop = threading.Event()
    wake = threading.Event()
    t0 = time.monotonic()
    ret = _wait_next(stop, wake, 0.3)
    elapsed = time.monotonic() - t0
    assert ret is False, "未收到停止信号必须返回 False(不是 None/True)"
    assert elapsed >= 0.25, f"必须睡满 timeout 再返回(等待归零=空转回归): {elapsed:.3f}s"
    assert elapsed <= 1.5, f"不得超时过久(分段轮询粒度 0.5s): {elapsed:.3f}s"


def test_w6_init_signature_and_field_contracts():
    """守阵(W6, 极低/契约面): 构造与入口签名默认值 + 构造期字段初始值契约

    no_lock/dry_run 默认翻 True 会把缺省调用变成"跳过锁/静默 dry-run"; QbApi 不带 store、
    next_flush_at 初值漂移、_pause_event 非 None 都是仅契约面可区分的极低危。
    """
    import inspect

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        sig = inspect.signature(QbManager.__init__)
        assert sig.parameters["no_lock"].default is False, "no_lock 缺省必须 False(锁是保守默认)"
        rsig = inspect.signature(QbManager.run)
        assert rsig.parameters["dry_run"].default is False, "run 的 dry_run 缺省必须 False(真写是默认语义)"
        fsig = inspect.signature(QbManager._refresh_torrents)
        assert fsig.parameters["dry_run"].default is False, "_refresh_torrents 的 dry_run 缺省必须 False"
        assert mgr.api.store is mgr.store, "QbApi 必须在构造期绑定 store"
        assert mgr.ctx.state.next_flush_at == 0.0, "周期落盘到期点初值 0.0(run() 会重置)"
        assert mgr._pause_event is None, "_pause_event 构造期必须为 None(run() 注入前无暂停态)"


def test_w6_init_loads_config_from_path():
    """守阵(W6, 中): config 未传时必须以 config_path 调 load_config(open(None) 即构造崩溃)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        with mock.patch("auto_qb.core.qbmanager.load_config", return_value=cfg) as lc:
            make_manager(cfg=cfg, pass_config_none=True, qb_config_path=os.path.join(td, "config.yml"))
        lc.assert_called_once_with(os.path.join(td, "config.yml"))


def test_w6_init_wires_fs_notify_relocate():
    """守阵(W6, 中/低): fs.path_map 必须产出 MappedFileAccess; notify/relocate 模块必须挂真 ctx

    init_file_access(None) 让映射静默整体退回 Local(缺文件扫描/搬家的路径面);
    NotifyModule/RelocateModule(None) 后写路径读 _ctx 即 AttributeError(可选特性面)。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        cfg.fs = FsConfig(path_map=(PathMapEntry(src="R:/Downloads", dst="/downloads"), ))
        mgr = make_manager(cfg=cfg)
        fa = file_access.get_file_access()
        assert isinstance(fa, MappedFileAccess), "fs.path_map 配置必须产出 MappedFileAccess(退回 Local=映射整体失效)"
        assert fa.entries == cfg.fs.path_map, "映射表必须原样进访问层"
        assert mgr.ctx.notify._ctx is mgr.ctx, "NotifyModule 必须挂真 ctx"
        assert mgr.ctx.relocate._ctx is mgr.ctx, "RelocateModule 必须挂真 ctx"


def test_w6_init_creates_state_dir_console_only():
    """守阵(W6, 中): 构造必须显式建数据目录(console-only 无日志文件代建, 不建则首次落盘崩)"""
    with tempfile.TemporaryDirectory() as td:
        sub = os.path.join(td, "statedir")
        make_manager(os.path.join(sub, "state.json"))
        assert os.path.isdir(sub), "数据目录必须在构造期创建(console-only 时无日志代建兜底)"


def test_w6_pause_branch_keeps_looping():
    """守阵(W6, 中/低): 暂停分支等待实参契约 + 暂停不退化为停机(continue) + 停止 INFO

    _wait_next 实参错位/缺参 → TypeError 即崩; continue→break 让暂停语义退化为停机;
    _pause_event 未挂载则状态快照 paused 恒 False。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.1
        mgr.config.sync_interval = 0.1
        pause = threading.Event()
        pause.set()
        stop = threading.Event()
        real_wait = _qbm._wait_next
        calls = []
        pause_seen = []

        def spy(stop_event, wake_event, timeout):
            calls.append((stop_event, wake_event, timeout))
            pause_seen.append(mgr._pause_event is pause)
            if len(calls) >= 3:
                stop_event.set()
            return real_wait(stop_event, wake_event, timeout)

        with mock.patch.object(_qbm, "_wait_next", spy):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.run(dry_run=False, stop_event=stop, pause_event=pause)
        assert len(calls) == 3, f"暂停期间主循环必须继续轮询(continue 语义), 实际 {len(calls)} 次"
        assert all(se is stop for se, _, _ in calls), "暂停等待必须传 stop_event"
        assert all(we is mgr._wake_event for _, we, _ in calls), "暂停等待必须传唤醒事件"
        assert all(t == 0.1 for *_, t in calls), "暂停等待超时 = main_tick"
        assert all(pause_seen), "run() 必须把 pause_event 挂到 _pause_event(状态快照依赖)"
        assert "收到停止信号, 退出主循环" in cap.text, "暂停分支停止 INFO 不得丢"


def test_w6_next_flush_at_respects_save_interval():
    """守阵(W6, 中/低): 周期落盘到期点 = now+max(interval, 0.0)

    interval=0(显式关闭)被强转 1s = 关闭语义反转(保守默认面); +max 变 -max = 到期点排进
    过去, 启动即冗余写一次。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.state_save_interval = 0  # 显式关闭周期落盘
        stop = threading.Event()
        stop.set()
        mgr.run(dry_run=False, stop_event=stop)
        assert mgr.ctx.state.next_flush_at <= time.time() + 0.5, "state_save_interval=0 必须保持 0 间隔(不得强转 1s 周期写盘)"

        mgr2 = make_manager(os.path.join(td, "state2.json"))
        mgr2.connect = mock.Mock(return_value=True)
        mgr2.config.state_save_interval = 30.0
        stop2 = threading.Event()
        stop2.set()
        mgr2.run(dry_run=False, stop_event=stop2)
        assert mgr2.ctx.state.next_flush_at >= time.time() + 25, "到期点必须排向未来 now+interval(排进过去=启动即冗余写)"


def test_w6_periodic_flush_gate_and_migration_arg():
    """守阵(W6, 中/低): 周期落盘挂在 not dry_run 门内(反转=正常轮全停) + materialize_migration 实参"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr._sync_line = lambda dry_run, flush=True, force=False: None
        mgr._task_line = lambda dry_run, force=False: None
        stop = threading.Event()
        timer = _daemon_timer(3.0, stop.set)
        flush_calls = []
        mgr.ctx.state.materialize_migration = mock.Mock()

        def maybe_flush(now, interval):
            flush_calls.append((now, interval))
            stop.set()

        mgr.ctx.state.maybe_flush = maybe_flush
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(flush_calls) == 1, "非 dry-run 轮必须走周期落盘(gate 反转=状态丢失窗口回归)"
        assert mgr.ctx.state.materialize_migration.call_args == mock.call(
            False
        ), "materialize_migration 必须收到 dry_run 实参(None≠False, 变异后 dry-run 会话也落盘)"

        mgr2 = make_manager(os.path.join(td, "state2.json"))
        mgr2.connect = mock.Mock(return_value=True)
        mgr2._sync_line = lambda dry_run, flush=True, force=False: None
        mgr2._task_line = lambda dry_run, force=False: None
        stop2 = threading.Event()
        timer2 = _daemon_timer(2.0, stop2.set)
        flush2 = []
        mgr2.ctx.state.maybe_flush = lambda *a, **k: flush2.append(a)
        mgr2.run(dry_run=True, stop_event=stop2)
        timer2.cancel()
        assert flush2 == [], "dry-run 会话不得周期落盘"


def test_w6_truth_pending_drives_retry_arc():
    """守阵(W6, 中/低): 真值未落地(pending 常驻)必须按 0.2s 重试弧持续补同步, 且各线 force=True

    重试弧断(属性名/求值变异)→ 真值落地等满 sync_interval; cmd_forced/_tick/_sync_line 的
    force/dry_run 实参契约同轮锁定; 弧内 next_sync_at=None 会在下拍 now>=None TypeError 崩溃。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.5
        mgr.config.sync_interval = 5.0
        mgr.web.truth_pending = {"c1": {"cmd": "pause", "args": {"hashes": ["H1"]}, "ts": time.time()}}
        mgr.web.flush_truths = lambda: None  # 真值恒未落地: pending 常驻
        stop = threading.Event()
        timer = _daemon_timer(1.8, stop.set)
        tick_calls, sync_calls = [], []

        def tick(dry_run, force=False):
            tick_calls.append((dry_run, force))

        def sync_line(dry_run, flush=True, force=False):
            sync_calls.append((dry_run, flush, force))

        mgr._tick = tick
        mgr._sync_line = sync_line
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert tick_calls == [(False, True)], f"真值等待轮 _tick force 必须为 True: {tick_calls}"
        assert len(sync_calls) >= 3, f"真值未落地必须按 0.2s 重试弧持续补同步: {len(sync_calls)} 次"
        assert all(f is True for _, _, f in sync_calls), "重试弧同步线 force 必须为 True"
        assert all(d is False for d, _, _ in sync_calls), "同步线 dry_run 实参不得为 None"
        assert all(fl is True for _, fl, _ in sync_calls), "独立同步线 flush 必须保持开启"
        assert "收到停止信号, 退出主循环" in cap.text, "主循环停止 INFO 不得丢"


def test_w6_cmd_forced_and_t_line_contract():
    """守阵(W6, 低): cmd_forced 门控契约(命令轮 True/非命令轮 False) + 命令线计时弧恰发一次

    force 门控反转 → 每轮绕"上一版是否被取走"门控(视图强制重建放大); _t_line 计时弧
    反转/恒真/else 1.0 → 遥测噪声或丢真。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 5.0
        n = {"c": 0}

        def fake_cmd():
            n["c"] += 1
            return n["c"] == 1  # 仅首轮有命令

        mgr.host.run_command_line = fake_cmd
        resync = []
        mgr.web.resync_elapsed_ms = lambda t0: resync.append(t0)
        stop = threading.Event()
        timer = _daemon_timer(4.0, stop.set)
        task_calls = []
        sync_calls = []

        def task_line(dry_run, force=False):
            task_calls.append((dry_run, force))
            if len(task_calls) >= 4:
                stop.set()

        def sync_line(dry_run, flush=True, force=False):
            sync_calls.append((dry_run, flush, force))

        mgr._task_line = task_line
        mgr._sync_line = sync_line
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert task_calls == [(False, True), (False, False), (False, False), (False, False)], \
            f"命令轮 force=True, 非命令轮必须 False: {task_calls}"
        assert len(resync) == 1, f"命令线计时弧必须在命令轮恰发一次: {len(resync)} 次"
        assert isinstance(resync[0], float) and resync[0] > 0, "计时弧实参必须是真实时间戳"
        assert sync_calls == [(False, False, False)] * 4, f"每轮双线合轮经 _tick(压 flush): {sync_calls}"


def test_w6_micro_deadline_merged_into_wait():
    """守阵(W6, 中): 微步到期必须并入等待超时(退化=跳检步进从 10~50ms 劣化到 main_tick)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 2.0
        mgr.config.sync_interval = 5.0
        mgr.host.next_micro_run_at = lambda: time.time() + 0.05
        stop = threading.Event()
        timer = _daemon_timer(5.0, stop.set)
        micro = []

        def micro_line(dry_run):
            micro.append(dry_run)
            if len(micro) >= 5:
                stop.set()

        mgr.host.run_micro_line = micro_line
        mgr._sync_line = lambda dry_run, flush=True, force=False: None
        mgr._task_line = lambda dry_run, force=False: None
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(micro) == 5, f"微步到期必须并入等待超时(按 0.05s 节拍推进): 实际 {len(micro)} 步"
        assert all(d is False for d in micro), "微步线 dry_run 实参不得为 None"


def test_w6_micro_deadline_does_not_delay_lines():
    """守阵(W6, 中): 更晚的微步到期不得推迟同步/任务线(min 压缩变异=min(单参))"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 2.0
        mgr.config.sync_interval = 0.1
        mgr.host.next_micro_run_at = lambda: time.time() + 1.0  # 微步退避晚于同步线
        stop = threading.Event()
        timer = _daemon_timer(0.8, stop.set)
        sync_calls = []
        mgr._sync_line = lambda dry_run, flush=True, force=False: sync_calls.append(dry_run)
        mgr._task_line = lambda dry_run, force=False: None
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(sync_calls) >= 4, f"同步线节拍不得被更晚的微步到期推迟: {len(sync_calls)} 次"


def test_w6_flush_fallback_once_per_round():
    """守阵(W6, 低): 回执 flush 每轮恰一次 —— 异常轮走兜底、正常轮不重复(_flushed 旗标契约)

    旗标恒真 → 异常轮不补回执(waitCmd 干等); 旗标恒假/None → 正常轮双 flush;
    兜底判据反转 → 轮归属错乱。KI 退出必须落"停止" INFO。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        rounds = {"refresh": 0}
        flushes = []

        def _refresh(dry_run=False):
            rounds["refresh"] += 1
            if rounds["refresh"] >= 2:
                raise RuntimeError("refresh boom")

        def _flush():
            # 以 refresh 计数(而非 flush 自身调用次数)判定异常轮: flush 每轮无条件调用,
            # 两条时间线各自取时, 负载下可能先出现只跑任务线/空转的轮次 —— 按 flush 序数
            # 判定会让第 2 次 flush 提前抛 KI 退出, 只剩 1 次 refresh(issue 26-11-05-0035)。
            flushes.append(rounds["refresh"])
            if rounds["refresh"] >= 2:
                raise KeyboardInterrupt()

        mgr._refresh_torrents = _refresh
        mgr.web.flush_truths = _flush
        waits = []
        real_wait = _qbm._wait_next

        def _wait_spy(stop_event, wake_event, timeout):
            waits.append(timeout)
            # 兜底出口: 若回执兜底被改坏(异常轮不 flush), KI 永不到来 —— 迭代上限后按停止信号退出,
            # 让断言干净地红, 而不是让 refresh 反复抛错直到测试超时。
            if len(waits) > 10:
                return True
            return real_wait(stop_event, wake_event, timeout)

        with mock.patch.object(_qbm, "_wait_next", _wait_spy):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.run(dry_run=False)
        assert rounds["refresh"] == 2, "两条同步线: 正常轮 + 异常轮"
        # 回执 flush 每轮无条件调用 + 异常轮兜底: 轮数 = 等待次数 + 1(异常轮由 KI 退出, 不再等待)。
        # 不绑定 refresh 调用数, 空转轮/只跑单线的轮次不再破坏记账。
        assert len(flushes) == len(waits) + 1, "每轮恰一次回执 flush(异常轮兜底补, 正常轮不双发)"
        assert "停止" in cap.text, "KeyboardInterrupt 退出必须落'停止' INFO"


def test_w6_stopiteration_error_detail():
    """守阵(W6, 低): StopIteration ERROR 的消息与堆栈不得丢真(仍重抛不变)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=StopIteration("gen-misuse-marker"))
        with capture_logs("auto_qb.core.qbmanager") as cap:
            with pytest.raises(StopIteration):
                mgr.run(dry_run=False)
        errs = [r for r in cap.records if r.levelname == "ERROR"]
        assert errs and "gen-misuse-marker" in errs[-1].getMessage(), "StopIteration ERROR 必须带异常详情"
        assert errs[-1].exc_info, "StopIteration ERROR 必须带堆栈(exc_info=None/False 均丢真)"


def test_w6_generic_exception_error_detail():
    """守阵(W6, 低): 主循环异常 ERROR 的消息与堆栈不得丢真"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr._tick = mock.Mock(side_effect=[RuntimeError("boom-marker"), KeyboardInterrupt()])
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False)
        errs = [r for r in cap.records if r.levelname == "ERROR" and "主循环异常" in r.getMessage()]
        assert errs and "boom-marker" in errs[-1].getMessage(), "主循环异常 ERROR 必须带异常详情"
        assert errs[-1].exc_info, "主循环异常 ERROR 必须带堆栈(exc_info=None/False 均丢真)"


def test_w6_migration_and_start_stop_logs():
    """守阵(W6, 低): 迁移/启动/停止 INFO 审计面 + desc 空时不得打迁移日志(or 反转恒打"落后(None)")"""
    with tempfile.TemporaryDirectory() as td:
        with mock.patch("auto_qb.core.qbmanager.materialize_schema_migration", return_value=("desc-v2", "bak")):
            mgr = make_manager(os.path.join(td, "state.json"))
            mgr.connect = mock.Mock(return_value=True)
            mgr.ctx.state.materialize_migration = mock.Mock()
            stop = threading.Event()
            stop.set()
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.run(dry_run=True, stop_event=stop)
            assert "dry-run 仅内存生效" in cap.text, "dry-run 迁移提示 INFO 不得丢"
            assert "启动 qB 管理器" in cap.text, "启动 INFO 不得丢"
            assert "收到停止信号, 退出主循环" in cap.text, "停止 INFO 不得丢"
            assert mgr.ctx.state.materialize_migration.call_args == mock.call(True)

        with mock.patch("auto_qb.core.qbmanager.materialize_schema_migration", return_value=("", None)):
            mgr2 = make_manager(os.path.join(td, "state2.json"))
            mgr2.connect = mock.Mock(return_value=True)
            stop2 = threading.Event()
            stop2.set()
            with capture_logs("auto_qb.core.qbmanager") as cap2:
                mgr2.run(dry_run=True, stop_event=stop2)
            assert "schema 落后" not in cap2.text, "无迁移时不得打迁移 INFO"

        with mock.patch("auto_qb.core.qbmanager.materialize_schema_migration", return_value=("desc-v3", "bak3")):
            mgr3 = make_manager(os.path.join(td, "state3.json"))
            mgr3.connect = mock.Mock(return_value=True)
            stop3 = threading.Event()
            stop3.set()
            with capture_logs("auto_qb.core.qbmanager") as cap3:
                mgr3.run(dry_run=False, stop_event=stop3)
            assert "已迁移" in cap3.text and "desc-v3" in cap3.text, "已迁移 INFO 不得丢"


def test_w6_apply_new_config_contract():
    """守阵(W6, 中/低): 热重载回执契约 + qbittorrent 段变重连(双向) + 完成 INFO 汇总过滤"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.reconnect = mock.Mock()
        mgr.host.apply_all = mock.Mock(return_value=[ApplyResult("alpha", "reloaded", "ok"), ApplyResult("beta")])
        cfg2 = FakeConfig()
        # 与现配置共享可变段(FakeTracker 无 __eq__, 身份比较会误判为变更), 只改 qbittorrent 段
        cfg2.trackers = mgr.config.trackers
        cfg2.rules_config = mgr.config.rules_config
        cfg2.state_file = mgr.config.state_file
        cfg2.qbittorrent = QbittorrentConfig(host="127.0.0.1", port=16586, username="u", **{"pass" + "word": "p"})
        with capture_logs("auto_qb.core.qbmanager") as cap:
            result = mgr.apply_new_config(cfg2)
        assert result["applied"] is True
        assert set(result) == {"applied", "actions", "changes", "restart_required"}, f"回执键面契约: {set(result)}"
        assert result["changes"] == 1
        assert result["restart_required"] == []
        assert result["actions"] == [
            {
                "module": "alpha",
                "action": "reloaded",
                "detail": "ok"
            },
            {
                "module": "beta",
                "action": "none",
                "detail": ""
            },
        ], f"回执条目契约: {result['actions']}"
        assert mgr.reconnect.call_count == 1, "qbittorrent 段变必须重连"
        text = cap.text
        assert "配置热重载完成" in text, "完成 INFO 不得丢"
        assert "alpha:reloaded" in text, "完成 INFO 必须列真实动作"
        assert "beta:none" not in text, "no-op 动作不得混入汇总"
        assert "需重启进程" not in text, "无重启项不得误报需重启"
        assert "XXXX" not in text, "非重启轮不得拼噪声后缀"
        # 段相同: 不得重连(== 反转会在段同时重连)
        mgr.host.apply_all = mock.Mock(return_value=[])
        mgr.apply_new_config(cfg2)
        assert mgr.reconnect.call_count == 1, "qbittorrent 段相同不得重连"


def test_w6_apply_new_config_restart_gate():
    """守阵(W6, 中/低): R 级闸必须返回需重启段(None=闸失效照常热应用)且日志保留提示"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.reconnect = mock.Mock()
        mgr.host.apply_all = mock.Mock(return_value=[ApplyResult("alpha")])
        cfg2 = FakeConfig()
        cfg2.state_file = os.path.join(td, "other.json")
        with capture_logs("auto_qb.core.qbmanager") as cap:
            result = mgr.apply_new_config(cfg2)
        assert result["restart_required"] == ["state_file"], "R 级闸(state_file 变更)必须进需重启回执"
        assert "需重启进程才能生效" in cap.text, "需重启 INFO 不得丢"
        assert "需重启进程: ['state_file']" in cap.text, "完成 INFO 必须带需重启后缀"


def test_w6_apply_new_config_unclaimed_fallback():
    """守阵(W6, 中/低): 未认领段兜底 —— WARNING + rebuild_runtime 相位载荷 + 回执条目逐字契约

    相位失联/载荷缺失 → 兜底重建静默失效; join(None) 直接崩; 回执条目字段/值变异即损坏。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.reconnect = mock.Mock()
        mgr.host.apply_all = mock.Mock(return_value=[ApplyResult("alpha", "reloaded", "ok")])
        rebuilds = []
        mgr.events.on("rebuild_runtime", lambda event: rebuilds.append((event.phase, event.payload)))
        cfg2 = FakeConfig()
        # 与现配置共享可变段(FakeTracker 无 __eq__), 只动未认领段 —— 两段才能观察 join 分隔符
        cfg2.trackers = mgr.config.trackers
        cfg2.rules_config = mgr.config.rules_config
        cfg2.state_file = mgr.config.state_file
        cfg2.check_missing_files = True  # 无模块认领的顶层段
        cfg2.custom_unknown_section = {"probe": 1}  # 仅存在于新配置的幽灵段(同样无认领)
        with capture_logs("auto_qb.core.qbmanager") as cap:
            result = mgr.apply_new_config(cfg2)
        assert "check_missing_files" in cap.text and "未被任何模块认领" in cap.text, "未认领段 WARNING 不得丢"
        assert rebuilds == [("rebuild_runtime", {"sections": ["check_missing_files", "custom_unknown_section"]})], \
            f"兜底重建必须广播 rebuild_runtime 相位并带未认领段: {rebuilds}"
        assert result["actions"][-1] == {
            "module": "kernel",
            "action": "rebuild_fallback",
            "detail": "未认领段: check_missing_files, custom_unknown_section",
        }, f"兜底回执条目契约: {result['actions'][-1]}"


def test_w6_tick_contract():
    """守阵(W6, 低): _tick 双线合轮实参契约 —— sync 收 flush=False, task 直传 force"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._sync_line = mock.Mock()
        mgr._task_line = mock.Mock()
        mgr._tick(True, force=True)
        mgr._sync_line.assert_called_once_with(True, flush=False), "_tick 合轮必须压 flush(视图只重建一次)"
        mgr._task_line.assert_called_once_with(True, force=True), "_tick 必须把 force 直传任务线"
