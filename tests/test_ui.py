"""test_ui 测试计划: 托盘 UI 支撑设施(ui.py 可测部分 + run 事件参数 + autostart)

## 测试计划(每个测试函数一条)
- test_run_stop_event_exit: stop_event 置位 -> run 立即退出并落盘
- test_run_unmanaged_connect_fail_returns: 非托管模式首连失败直接返回(历史行为)
- test_run_managed_connect_retry: 托管模式首连失败按 tick 重试直至成功, 期间不退出
- test_run_pause_event_skips_ticks: pause_event 置位期间完全不执行 _tick, 停止信号仍响应
- test_status_snapshot: 只读快照(种子数/连接态/暂停态)
- test_ui_log_handler_drain: 日志环形缓冲 drain 增量消费
- test_ipc_show_roundtrip: IPC server 真实回环收 "show" 触发回调, stop 后端口文件清理
- test_send_show_missing_port_file: 端口文件缺失 -> send_show 返回 False
- test_notify_handler_enabled_toggle: 通知热开关关闭时 emit 不入队
- test_autostart_windows_registry: Windows 注册表注册/注销(真注册表, 专属键名, 测试后清理)
- test_autostart_linux_desktop: XDG autostart desktop 文件写入/注销(平台 patch)
- test_autostart_macos_plist: macOS LaunchAgents plist 写入/注销(平台 patch)
- test_log_dir_resolves_and_creates: 日志目录解析(相对路径绝对化/file 为空兜底 state_file 目录/确保存在)
"""
import logging
import os
import sys
import threading
import time

import pytest

from auto_qb import autostart, notify as notify_mod
from auto_qb.config import NotifyConfig
from auto_qb.notify import NotifyHandler, PlatformChannel
from auto_qb.ui import ShowIpcServer, TrayUi, UiLogHandler, send_show
from helpers import FakeClient, FakeTorrent, make_manager, seed_store


def test_log_dir_resolves_and_creates(tmp_path):
    """_log_dir: 相对路径绝对化并确保目录存在; logging.file 为空兜底 state_file 目录(data_dir)

    注意用新 LoggingConfig 实例替换(FakeConfig.logging 是类属性共享实例, 直接改 file 会污染后续测试)。
    """
    from auto_qb.config import LoggingConfig

    mgr = make_manager(str(tmp_path / "data" / "state.json"))
    mgr.client = FakeClient()

    mgr.config.logging = LoggingConfig(level="WARNING", file="", max_bytes=10 * 1024**2)
    log_dir = TrayUi._log_dir(mgr)
    expected = os.path.dirname(os.path.abspath(str(tmp_path / "data" / "state.json")))
    assert os.path.isdir(log_dir) and os.path.samefile(log_dir, expected)

    mgr.config.logging = LoggingConfig(
        level="WARNING", file=str(tmp_path / "logs" / "auto-qb.log"), max_bytes=10 * 1024**2
    )
    log_dir = TrayUi._log_dir(mgr)
    assert os.path.isdir(log_dir) and log_dir.endswith("logs")


def _make_ready_manager(tmp_path):
    """构造 connect 直通的管理器(测试不连真实 qB)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    mgr.connect = lambda: True
    return mgr


def test_run_stop_event_exit(tmp_path):
    """stop_event 置位 -> run 立即退出并落盘(退出语义)"""
    mgr = _make_ready_manager(tmp_path)
    stop = threading.Event()
    stop.set()
    mgr.run(dry_run=False, stop_event=stop)
    assert (tmp_path / "state.json").exists(), "退出前应保存状态"


def test_run_unmanaged_connect_fail_returns(tmp_path):
    """非托管模式(无 stop_event)首连失败直接返回, 不重试(历史行为)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    calls = []
    mgr.connect = lambda: calls.append(1) and False
    mgr.run(dry_run=True)
    assert len(calls) == 1, "首连失败应直接返回, 不重试"


def test_run_managed_connect_retry(tmp_path):
    """托管模式首连失败按 tick 重试直至成功(托盘应用保持常驻)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    stop = threading.Event()
    mgr.config.main_tick = 0.01
    calls = []

    def fake_connect():
        calls.append(1)
        if len(calls) >= 3:
            stop.set()
            return True
        return False

    mgr.connect = fake_connect
    mgr.run(dry_run=False, stop_event=stop)
    assert len(calls) == 3, "应重试至连接成功"


def test_run_pause_event_skips_ticks(tmp_path):
    """pause_event 置位期间完全不执行 _tick(纯旁观), 停止信号仍即时响应"""
    mgr = _make_ready_manager(tmp_path)
    pause = threading.Event()
    pause.set()
    stop = threading.Event()
    mgr.config.main_tick = 0.02
    ticks = []
    mgr._tick = lambda dry_run: ticks.append(1)

    def stopper():
        time.sleep(0.2)
        stop.set()

    threading.Thread(target=stopper, daemon=True).start()
    mgr.run(dry_run=True, stop_event=stop, pause_event=pause)
    assert ticks == [], "暂停期间不应执行任何 tick"


def test_status_snapshot(tmp_path):
    """只读快照: 种子数/连接态/暂停态, 基本类型"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    seed_store(mgr, [FakeTorrent()])
    snap = mgr.status_snapshot()
    assert snap["torrents"] == 1
    assert snap["paused"] is False
    assert snap["connected"] is None  # 未连接过
    mgr._last_conn_ok = False
    mgr._pause_event = threading.Event()
    mgr._pause_event.set()
    snap = mgr.status_snapshot()
    assert snap["paused"] is True
    assert snap["connected"] is False


def test_ui_log_handler_drain():
    """UiLogHandler: emit 入队, drain 增量取走后清空"""
    handler = UiLogHandler()
    record = logging.LogRecord("auto_qb.test", logging.WARNING, "p", 1, "hello %s", ("world", ), None)
    handler.emit(record)
    assert handler.drain() == ["[WARNING] hello world"]
    assert handler.drain() == []


def test_ipc_show_roundtrip(tmp_path):
    """IPC 真实回环: server 收 "show" 触发回调; stop 后端口文件清理"""
    port_file = tmp_path / "ui.port"
    got = []
    server = ShowIpcServer(str(port_file), lambda: got.append(True))
    server.start()
    try:
        deadline = time.time() + 2
        while not port_file.exists() and time.time() < deadline:
            time.sleep(0.01)
        assert port_file.exists(), "server 启动后应写入端口文件"
        assert send_show(str(port_file)) is True
        deadline = time.time() + 2
        while not got and time.time() < deadline:
            time.sleep(0.01)
        assert got == [True], "应收到第二实例的唤起请求"
    finally:
        server.stop()
    assert not port_file.exists(), "stop 后应删除端口文件"


def test_send_show_missing_port_file(tmp_path):
    """端口文件缺失(首实例非托盘/已清理) -> send_show 返回 False"""
    assert send_show(str(tmp_path / "none.port")) is False


def test_notify_handler_enabled_toggle():
    """通知热开关: enabled=False 时 emit 直接丢弃"""
    handler = NotifyHandler(
        NotifyConfig(enabled=True, min_level="WARNING", max_per_hour=100, dedup_window=0),
        PlatformChannel("linux"),
    )
    try:
        record = logging.LogRecord("auto_qb.test", logging.WARNING, "p", 1, "x", None, None)
        handler.enabled = False
        handler.emit(record)
        assert handler._queue.empty()
        handler.enabled = True
        handler.emit(record)
        assert not handler._queue.empty()
    finally:
        handler.close()


@pytest.mark.skipif(not sys.platform.startswith("win32"), reason="Windows 注册表专属(真注册表, 专属键名, 测试后清理)")
def test_autostart_windows_registry():
    """Windows: HKCU Run 键注册/查询/注销"""
    autostart.enable("config.yml")
    try:
        assert autostart.is_enabled("config.yml")
    finally:
        autostart.disable()
    assert not autostart.is_enabled("config.yml")


def test_autostart_linux_desktop(monkeypatch, tmp_path):
    """Linux: XDG autostart desktop 文件写入/注销(平台与路径均 patch)"""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(autostart, "LINUX_DESKTOP", tmp_path / "autostart" / "auto-qb.desktop")
    autostart.enable("cfg.yml")
    text = autostart.LINUX_DESKTOP.read_text(encoding="utf-8")
    assert "Exec=" in text and "--tray" in text
    assert autostart.is_enabled("cfg.yml")
    autostart.disable()
    assert not autostart.is_enabled("cfg.yml")


def test_autostart_macos_plist(monkeypatch, tmp_path):
    """macOS: LaunchAgents plist 写入/注销(平台与路径均 patch)"""
    import plistlib

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(autostart, "MACOS_PLIST", tmp_path / "com.autoqb.app.plist")
    autostart.enable("cfg.yml")
    with open(autostart.MACOS_PLIST, "rb") as f:
        data = plistlib.load(f)
    assert data["RunAtLoad"] is True and data["ProgramArguments"][-1] == "--tray"
    assert autostart.is_enabled("cfg.yml")
    autostart.disable()
    assert not autostart.is_enabled("cfg.yml")
