"""test_qbmanager_connect 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_connect_failure: 连接失败返回 False 且 client 为 None
- test_connect_success: 连接成功返回 True 并登录(客户端经 new_client 构造)
- test_new_client_local_disables_trust_env: 本地地址用 LocalQbClient, Session(含重建)trust_env 恒为 False
- test_new_client_sets_request_timeout: P1-5 守卫——客户端必须带请求超时(否则 qB 假死时界面永久假死)
- test_new_client_local_host_variants: localhost/IPv6 本机写法同样判定为本地
- test_new_client_remote_keeps_default_trust_env: 远程地址用原生 Client 且保留 trust_env 默认
- test_throttle_sleeps_without_stop_event: 非托管模式节流真实睡眠且返回 False
- test_throttle_waits_stop_event: 托管模式节流走 Event.wait 并回传停止信号
- test_run_loop_throttles_without_stop_event: 非托管模式主循环每轮 sleep(main_tick)(回归守卫)
- test_run_connect_failure: 非托管首连失败抛 QbConnectError(fail-fast -> CLI 退出码 1), 不进入主循环
- test_reconnect_backoff_and_reset: 重连指数退避(间隔翻倍、上限 30s、未到点不重试)且连接成功后归零
- test_run_client_none_reconnects_without_error_spam: 守阵(26-10-31-1029)——断连稳态(client=None+_last_conn_ok=False)跳过请求线走 _reconnect_due 重连, 成功即补同步并记「已重新连接」, 不得落「主循环异常」逐拍刷屏且 connect() 不再被调
- test_p2a_run_managed_stop_event_exits_during_connect_retry: 托管模式连接失败遇停止信号干净返回 (P2-a)
- test_a07_connect_non_api_error_transition_throttled: 守阵(26-10-06-0028 A-07)——非 API 连接异常(凭据错)与连接类同用转换节流, 失败态重复 connect 不重复 ERROR
- test_a07_managed_first_connect_retry_warns_once: 守阵(A-07)——托管首连重试 WARNING 只说明白一次, 停止信号仍即时响应
- test_connect_recovery_logged
- test_connect_throttle_repeated_failures
- test_w6_connect_false_on_api_connection_error: 守阵(W6)——APIConnectionError 分支必须报失败(fail-fast 契约)
- test_w6_connect_error_detail_logged: 守阵(W6)——连接失败 ERROR 必须带异常详情(两分支)
- test_w6_conn_recovery_flag_flip: 守阵(W6)——线跑通后连接状态必须翻回已连接
- test_w6_conn_failed_error_detail: 守阵(W6)——断连 ERROR 必须带异常详情
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

from clock import FakeClock
from platform_tolerance import SLEEP_LOWER_MARGIN_S

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


def test_connect_failure():
    """连接失败返回 False 且 client 保持 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("conn refused")):
            assert mgr.connect() is False
        assert mgr.client is None


def test_connect_success():
    """连接成功返回 True 并登录(客户端经 new_client 构造: 本地地址由它选 LocalQbClient)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        fake = mock.Mock()
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=fake) as new_client:
            assert mgr.connect() is True
        new_client.assert_called_once_with(mgr.config.qbittorrent)
        fake.auth_log_in.assert_called_once()
        assert mgr.client is fake


def test_new_client_local_disables_trust_env():
    """本地地址: LocalQbClient 使 trust_env 在**每次(重)建 Session** 后都为 False

    旧实现(连上后给 client._session.trust_env 赋 False)会在库重建 Session 时静默失效 ——
    此处用 _trigger_session_initialization() 显式复现该重建(库在 build_base_url()/
    _initialize_context() 中就是这样丢弃旧 Session 的)。
    """
    cfg = QbittorrentConfig(host="127.0.0.1", port=1, username="u", password="p")
    client = new_client(cfg)
    assert type(client) is LocalQbClient
    first = client._session
    assert first.trust_env is False
    client._trigger_session_initialization()
    second = client._session
    assert second is not first, "库应已重建 Session(证明控制点在 property 上而非一次性赋值)"
    assert second.trust_env is False


def test_new_client_sets_request_timeout():
    """P1-5 守卫: 客户端必须带请求超时(连接 3s / 读 10s)

    不设超时时 qB 假死(进程还在但不再响应)会让请求**无限期挂起**: 主循环线程被命令执行占住 ⇒
    连重连退避都跑不起来, 表现为"点一下之后整个界面再也不动"。
    读超时刻意宽松(10s): /files 在几千文件的种子上响应体很大, 截窄会把它误判成断连。
    """
    cfg = QbittorrentConfig(host="127.0.0.1", port=1, username="u", password="p")
    client = new_client(cfg)
    assert client._REQUESTS_ARGS.get("timeout"
                                    ) == REQUESTS_TIMEOUT, (f"客户端缺少请求超时, 实际 {client._REQUESTS_ARGS} —— qB 假死时请求会无限期挂起")
    # 远程地址同样要带(企业代理下连接阶段更可能卡住)
    remote = new_client(QbittorrentConfig(host="qb.example.com", port=8080))
    assert remote._REQUESTS_ARGS.get("timeout") == REQUESTS_TIMEOUT


def test_new_client_local_host_variants():
    """localhost / IPv6 本机写法同样判定为本地(取 base_url 的 hostname, 容忍带端口/带协议)"""
    for host in ("localhost", "[::1]", "127.0.0.1"):
        client = new_client(QbittorrentConfig(host=host, port=8080))
        assert type(client) is LocalQbClient, host


def test_new_client_remote_keeps_default_trust_env():
    """远程地址: 用原生 Client 且 trust_env 保持 requests 默认(企业代理/netrc 可能真实需要)"""
    client = new_client(QbittorrentConfig(host="qb.example.com", port=8080))
    assert type(client) is Client
    assert client._session.trust_env is True


def test_throttle_sleeps_without_stop_event():
    """非托管模式(stop_event=None): 真实阻塞 main_tick 秒且返回 False(不当作停止信号)

    阻塞语义用真实经过时间验证(S3 monkeypatch 收敛: 不再经 stdlib time 名 patch 观测
    sleep 调用), 与 test_run_loop_throttles_without_stop_event 同口径下界余量。档位 50ms:
    Windows 等待按 15.6ms 定时器刻度取整可提前(实测 46.8ms), 下界余量用平台刻度容差单点
    SLEEP_LOWER_MARGIN_S(>=2 tick, tests/platform_tolerance.py) —— 阻塞被退化成空转
    (微秒级)当场红, 余量依据与判别法见 pitfalls/testing/timing-tolerance.md。
    """
    tick = 0.05
    start = time.monotonic()
    assert _throttle(None, tick) is False
    assert time.monotonic() - start >= tick - SLEEP_LOWER_MARGIN_S


def test_throttle_waits_stop_event():
    """托管模式: 走 Event.wait(保持对停止信号的即时响应), 原样回传其停止信号"""
    ev = mock.Mock()
    ev.wait.return_value = True
    assert _throttle(ev, 3.0) is True
    ev.wait.assert_called_once_with(3.0)


def test_run_loop_throttles_without_stop_event():
    """回归守卫: 非托管模式下主循环每轮必须真实阻塞到"下一条时间线", 不得空转

    曾因 `if stop_event is not None and stop_event.wait(main_tick)` 的短路使非托管模式
    完全不阻塞 -> 满速空转(py-spy 实证约 2800 tick/s), CPU 打满且 sync/maindata 请求量放大数千倍。

    分层节拍后阻塞原语换成了 `_wait_next`(非托管模式走 wake_event.wait(剩余时间)),
    故判据改为**真实经过时间**: 循环若不阻塞, 两次 _tick 会在微秒内连续发生。
    下界留 sleep 精度余量(见断言处注释)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        main_tick = 0.05
        # 两条线同拍 -> 每轮走完整 _tick(与改造前"单一 cadence"的循环结构等价)
        mgr.config.main_tick = main_tick
        mgr.config.sync_interval = main_tick
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        start = time.monotonic()
        mgr.run(dry_run=False)
        elapsed = time.monotonic() - start
        assert mgr._tick.call_count == 2
        # 下界余量 = 平台刻度容差单点 SLEEP_LOWER_MARGIN_S(>=2 tick, tests/platform_tolerance.py):
        # Windows 等待粒度按 15.6ms 定时器刻度取整, 50ms 等待可提前到 46.8ms(2026-09-22 实测假红)
        # —— 空转是微秒级, 余量不损失判别力
        assert elapsed >= main_tick - SLEEP_LOWER_MARGIN_S, f"每轮循环后应阻塞到下一条时间线, 实际 {elapsed:.3f}s —— 主循环在空转"


def test_run_connect_failure():
    """run: 非托管首连失败抛 QbConnectError(fail-fast, 经 finally 清理后穿透到 CLI 退出码 1), 不进入主循环"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=False)
        with pytest.raises(QbConnectError):
            mgr.run(dry_run=False)  # 抛错前 finally 应已清理; 不应调用 _tick
        mgr.connect.assert_called_once()


def test_reconnect_backoff_and_reset():
    """重连指数退避: 未到点不重试 / 间隔翻倍 / 上限 30s / 连接成功后归零

    修复前主循环每 tick 都 `client = None; connect()` —— qB 长时间宕机时每 2s 重建一次
    Client(含 netrc / 代理解析), 纯空转。退避后重试间隔逐步拉长到 30s, 恢复即归零。
    """
    with tempfile.TemporaryDirectory() as td:
        # 构造期注入(S3 收敛: 不再经 stdlib time 名 patch): _reconnect_due / connect 节流
        # 读注入钟 monotonic, 读数与旧「钉 time.monotonic」逐值一致
        clock = FakeClock(start=1000.0)
        mgr = make_manager(os.path.join(td, "state.json"), clock=clock)
        tick = 2.0
        assert mgr._reconnect_due(tick) is True, "首次应立即重试"
        assert mgr._reconnect_at == pytest.approx(1000.0 + tick)
        # 未到点: 不重试
        clock.advance(tick - 0.01)
        assert mgr._reconnect_due(tick) is False
        # 到点: 重试, 间隔翻倍
        clock.freeze(1000.0 + tick)
        assert mgr._reconnect_due(tick) is True
        assert mgr._reconnect_at == pytest.approx(1000.0 + tick + 2 * tick)
        # 连续失败推到上限 30s 后不再增长
        for _ in range(12):
            clock.freeze(mgr._reconnect_at)
            mgr._reconnect_due(tick)
        assert mgr._reconnect_interval == pytest.approx(RECONNECT_MAX_INTERVAL), (
            f"退避应封顶 {RECONNECT_MAX_INTERVAL}s: {mgr._reconnect_interval}"
        )
        # 连接成功(走真实 connect)后归零: 下次断开从最短间隔重新开始
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=mock.Mock()):
            assert mgr.connect() is True
        assert mgr._reconnect_interval == 0.0 and mgr._reconnect_at == 0.0
        assert mgr._reconnect_due(tick) is True, "归零后应能立即重试"


def test_run_client_none_reconnects_without_error_spam():
    """回归守阵(issue 26-10-31-1029): 断连稳态必须走重连判定, 不得落进请求线

    修复前: except APIConnectionError 分支置 client=None 后, 未到 _reconnect_due 时下一拍
    照常跑同步线 —— store 把 AttributeError(None client 误入 _SYNC_UNAVAILABLE)当「qB 不
    支持 sync/maindata」降级, 回退 torrents_info 再次 AttributeError, 穿到 except Exception
    记「主循环异常」逐拍 ERROR; 且该路径不调 connect(), qB 恢复后永不回连。
    修法: 主循环加断连稳态守卫(client=None 且 _last_conn_ok=False)——跳过请求线, 直接
    _reconnect_due → connect(), 成功后本轮立即补同步并记「已重新连接 qBittorrent」。
    红验(修复前): AttributeError 路径逐拍炸「主循环异常」, connect() 首连后再不被调,
    无回连 INFO —— 本用例当时判红(红验兜底 60 拍后置位停止信号, 防用例挂死)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        stop_event = threading.Event()
        connect_attempts: list = []

        def fake_connect():
            connect_attempts.append(1)
            n = len(connect_attempts)
            if n == 1:
                # 启动首连成功(与真 connect 同语义: 成功即留下非 None client)
                mgr.client = mock.Mock()
                return True
            if n == 2:
                # 首次重连仍失败(真实现中 new_client 抛 APIConnectionError: client 保持 None)
                return False
            # 第二次重连成功(qB 恢复): 真 connect 成功路径 = 落 client + _note_conn_ok
            stop_event.set()
            mgr.client = mock.Mock()
            mgr._note_conn_ok()
            return True

        tick_calls: list = []

        def boom_tick(dry_run, force=False):
            # 模拟 issue 现场态: 断连转换早已记录(_last_conn_ok=False), client 停在 None,
            # 同步线误入 None client 炸 AttributeError(修复前从这里逐拍刷「主循环异常」)
            tick_calls.append(1)
            if len(tick_calls) >= 60:  # 红验兜底: 修复前 AttributeError 路径无出口, 防用例挂死
                stop_event.set()
            mgr._last_conn_ok = False
            mgr.client = None
            raise AttributeError("'NoneType' object has no attribute 'torrents_info'")

        mgr.connect = fake_connect
        mgr._tick = mock.Mock(side_effect=boom_tick)
        mgr._sync_line = mock.Mock()
        mgr._task_line = mock.Mock()
        with mock.patch("auto_qb.core.qbmanager.logger") as mock_logger:
            mgr.run(dry_run=True, stop_event=stop_event)
        assert mgr._tick.call_count == 1, (f"断连后请求线必须被守卫跳过, _tick 只应首轮执行一次, 实际 {mgr._tick.call_count}")
        assert len(connect_attempts) == 3, f"应走到第 3 次 connect(重连成功): {len(connect_attempts)}"
        assert mgr._sync_line.call_count == 1, "重连成功后守卫应立即补一次同步, 不等下一节拍"
        errors = [str(c.args[0]) for c in mock_logger.error.call_args_list]
        spam = [m for m in errors if "主循环异常" in m]
        assert len(spam) == 1, f"「主循环异常」只应首轮一条(断连后由守卫接管), 实际 {len(spam)}: {errors}"
        infos = [str(c.args[0]) for c in mock_logger.info.call_args_list]
        assert any("已重新连接 qBittorrent" in m for m in infos), f"重连成功必须记 INFO 收尾: {infos}"


def test_connect_throttle_repeated_failures():
    """连接失败节流: 主循环内 _tick 多次抛 APIConnectionError 只记录一次错误, 断开期间静默不刷屏"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)

        # connect 替身与真实现同语义(26-10-31-1029): 成功必须留下非 None client ——
        # 否则断连稳态守卫会把 None client 拦在请求线之外, 三次线级失败序列走不到
        def fake_connect():
            mgr.client = mock.Mock()
            return True

        mgr.connect = mock.Mock(side_effect=fake_connect)
        # 第一次失败记录, 第二次失败静默, 第三次抛 KeyboardInterrupt 退出循环
        mgr._refresh_torrents = mock.Mock(
            side_effect=[APIConnectionError("conn down"),
                         APIConnectionError("conn down"),
                         KeyboardInterrupt()]
        )
        with mock.patch("auto_qb.core.qbmanager.logger") as mock_logger:
            mgr.run(dry_run=False)  # 等待原语统一 _wait_next(事件等待), run() 不触 time.sleep(S3 收敛)
        errors = [c for c in mock_logger.error.call_args_list]
        assert len(errors) == 1, f"连接失败应只记录一条(节流), 实际 {len(errors)}: {errors}"
        assert "连接 qBittorrent 失败" in errors[0][0][0], f"应记录连接失败: {errors[0]}"
        assert mgr._last_conn_ok is False, "连接失败后状态应为断开"
        # 确认 _tick 确实被调用了 3 次(第一次记录错误, 第二次静默, 第三次退出)
        assert mgr._refresh_torrents.call_count == 3


def test_connect_recovery_logged():
    """连接恢复: 断开后重新连接成功记录'已重新连接'

    !必须 patch `new_client`(不是 `Client`): `connect()` 走的是 `qbclient.new_client`,
    patch `qbmanager.Client` 根本不生效 ⇒ 会真的去连 `127.0.0.1:16585`。那条路径是否抛异常
    **取决于机器/网络环境**(2026-09-19 Linux CI 上 connect() 返回 False, Windows 本地却绿),
    用例因此时好时坏。换成 patch 真正被调用的那个名字, 用例与网络彻底解耦。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr._last_conn_ok = False  # 模拟此前断开
        fake = mock.Mock()
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=fake):
            with mock.patch("auto_qb.core.qbmanager.logger") as mock_logger:
                assert mgr.connect() is True
        assert mgr._last_conn_ok is True, "重连成功后状态应为已连接"
        infos = [c for c in mock_logger.info.call_args_list]
        assert any("已重新连接" in c[0][0] for c in infos), f"应记录重新连接日志: {infos}"


def test_p2a_run_managed_stop_event_exits_during_connect_retry():
    """托管模式: 连接失败且停止信号已置位 -> 等待中被唤醒, run 干净返回(不抛 QbConnectError)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=False)
        stop_event = threading.Event()
        stop_event.set()
        mgr.run(dry_run=False, stop_event=stop_event)  # 不抛即通过
        assert mgr.connect.call_count == 1, "停止信号生效: 不无限重试连接"


def test_a07_connect_non_api_error_transition_throttled():
    """守阵(26-10-06-0028 A-07): 非 API 类连接异常(典型凭据错 LoginError)与连接类同用转换节流

    修复前 connect() 的 except Exception 无条件 ERROR —— 托管模式首连重试循环每 main_tick
    调一次 connect(), 凭据错误场景逐拍 ERROR 刷屏。守阵: 失败态下重复 connect 不再重复
    ERROR(同因只说明白一次); 连接恢复后再失败重新报一次(状态转换)。
    (日志断言用 capture_logs 不用 caplog: QbManager 构造链清 root handlers, 见 helpers。)
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("Login failed")):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                assert mgr.connect() is False  # 首次失败: ERROR 一次
                assert mgr.connect() is False  # 失败态再失败: 静默
        errors = [r for r in cap.records if r.levelno == logging.ERROR]
        assert len(errors) == 1, f"同因失败只说明白一次, 实际 {len(errors)} 条 ERROR"
        # 状态转换: 连接成功(翻转 _last_conn_ok)后再失败, 重新报一次
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=mock.Mock()):
            assert mgr.connect() is True
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("Login failed")):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                assert mgr.connect() is False
        assert len([r for r in cap.records if r.levelno == logging.ERROR]) == 1


def test_a07_managed_first_connect_retry_warns_once():
    """守阵(A-07): 托管模式首连重试循环的 WARNING 只说明白一次, 停止信号仍即时响应"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.main_tick = 0.01
        stop = threading.Event()
        calls = {"n": 0}

        def fake_connect():
            calls["n"] += 1
            if calls["n"] >= 5:
                stop.set()  # 重试数次后置位停止: 验证循环仍即时退出
            return False

        mgr.connect = fake_connect
        with capture_logs("auto_qb.core.qbmanager", level=logging.WARNING) as cap:
            mgr.run(dry_run=False, stop_event=stop)  # 不抛即通过(停止即时响应)
        warns = [m for m in cap.messages if "重试" in m]
        assert len(warns) == 1, f"重试 WARNING 只说明白一次, 实际 {len(warns)} 条"
        assert calls["n"] >= 5


def test_w6_connect_false_on_api_connection_error():
    """守阵(W6, 中): APIConnectionError 分支必须报 False(True 会破非托管 fail-fast 契约)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=APIConnectionError("conn refused")):
            assert mgr.connect() is False, "连接失败报成功=主循环无客户端带病运行"
        assert mgr.client is None


def test_w6_connect_error_detail_logged():
    """守阵(W6, 低): 两个连接失败分支的 ERROR 都必须带异常详情(丢 None=审计丢真)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=APIConnectionError("boom-net")):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.connect()
        assert any("boom-net" in m for m in cap.messages), "APIConnectionError 分支 ERROR 必须带详情"
        mgr._last_conn_ok = None  # 复位转换节流(断开期间静默是另一条纪律)
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("boom-cred")):
            with capture_logs("auto_qb.core.qbmanager") as cap2:
                mgr.connect()
        assert any("boom-cred" in m for m in cap2.messages), "通用异常分支 ERROR 必须带详情"


def test_w6_conn_recovery_flag_flip():
    """守阵(W6, 低): 线跑通后连接状态必须翻回已连接(is False 门反转/改 True = UI 永显断开)

    connect 替身与真实现同构(成功即落非 None client, 见 pitfalls/testing/manager-connect-stub.md):
    否则断连稳态守卫(client is None + _last_conn_ok is False)命中, 请求线整段被跳过, 本用例
    测的就不再是「线跑通后翻转」而是守卫轮。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))

        def fake_connect():
            mgr.client = mock.Mock()
            return True

        mgr.connect = fake_connect
        mgr._last_conn_ok = False  # 断开态进入主循环
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        stop = threading.Event()
        timer = _daemon_timer(3.0, stop.set)
        mgr._sync_line = lambda dry_run, flush=True, force=False: None

        def task_line(dry_run, force=False):
            stop.set()

        mgr._task_line = task_line
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert mgr._last_conn_ok is True, "线跑通后必须 _note_conn_ok(否则 UI 永显断开)"


def test_w6_conn_failed_error_detail():
    """守阵(W6, 低): 主循环断连 ERROR 必须带异常详情(丢 None=审计丢真)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=APIConnectionError("detail-net-down"))
        mgr.config.main_tick = 0.05
        stop = threading.Event()
        timer = _daemon_timer(0.8, stop.set)
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert any("detail-net-down" in m for m in cap.messages), "断连 ERROR 必须带异常详情"
