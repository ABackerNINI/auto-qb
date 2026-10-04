"""test_tray 测试计划: tray 逻辑缝 (plan 26-10-01-2157 §3 T2.1 / P2-b)

只测 headless 可测的纯逻辑缝 (UiLogHandler / IPC 端口文件协议 / poll 队列消费 / 状态->UI 映射
/ uptime 格式化 / 日志目录推导 / 动作分派 / run_tray 错误包装)。widget 构建主体
(_build_window / _card / _build_tray / run) 属真实窗口域, 在 src/auto_qb/tray/app.py 按块
pragma 豁免 (逐块理由见源码), 不在此伪造 GUI 栈。TrayUi 实例经 __new__ 绕过 __init__ 的
widget 构建, 手工装配最小字段集 (manager 用 tests/helpers.make_manager 的真实 QbManager)。
ctx.notify 用四公开口替身 (enabled_state/is_enabled/set_enabled) —— 真挂载会启动真实通知
链路 (conftest 虽拦执行, 但 handler 会话级残留污染), 通知模块自身行为由其专属测试覆盖。

## 测试计划 (每个测试函数一条)
- test_uilog_handler_collects_non_debug_lines: 非 DEBUG 记录格式化为 "[级别] 消息" 入队; drain 取走并清空
- test_uilog_handler_skips_debug_records: DEBUG 记录不入队 (UI 只显 INFO+)
- test_uilog_handler_swallows_format_errors: getMessage 抛错 (如 %d 配 str) 被吞, 不入队不外抛
- test_uilog_handler_integration_via_module_logger: 经模块 logger 真实 emit -> handler 收到 (自挂 handler, 非 caplog)
- test_ipc_start_writes_port_file_and_serves_show: start 写整数端口文件; send_show 成功; on_show 回调触发
- test_ipc_ignores_non_show_payload: 非 "show" 载荷不触发回调且连接关闭后服务存活
- test_ipc_survives_client_reset: 客户端 SO_LINGER=0 RST 断连 -> recv OSError -> continue, 服务存活
- test_ipc_swallows_on_show_error: on_show 首次抛错被吞 (logger.debug), 后续唤起仍可达
- test_ipc_accept_error_returns: accept OSError (socket 已关) -> _serve 直接返回
- test_ipc_stop_removes_port_file_and_idempotent: stop 删端口文件; 二次 stop 幂等; stop 后 send_show False
- test_ipc_stop_without_start_is_noop: 未 start (_sock=None) stop 不抛
- test_send_show_bad_port_file[missing/garbage/empty/half-json]: 端口文件缺失/垃圾字节/空文件/半截内容 -> False
- test_send_show_refused_when_no_listener: 端口无监听 (bound-not-listening) -> OSError -> False
- test_poll_quit_stops_poll_chain: quit 事件 -> root.quit 且不再 re-arm after
- test_poll_dispatches_toggle_pause_and_drains_logs: 事件分派到 handler (toggle_pause 置位) + 日志增量进视图
- test_poll_handler_failure_does_not_kill_chain: 单个 handler 抛错 -> logger.exception, 轮询链与后续事件存活
- test_poll_empty_queue_goes_to_refresh_and_rearms: 空队列 -> 直落 drain+refresh 并按 POLL_MS re-arm
- test_drain_logs_trims_excess_lines: 超过 LOG_VIEW_LINES 的旧行按 excess 裁掉
- test_show_and_hide_window_delegation: _show_window 委托 deiconify/lift/topmost/focus; _hide_window 委托 withdraw
- test_toggle_window_by_state: withdrawn -> 显示; 非 withdrawn -> 隐藏
- test_refresh_status_maps_quadrants[4]: (paused, connected) 四象限 -> 徽章文案/连接文案/按钮文案
- test_refresh_status_syncs_notify_switch_on: 开关未选 + 模块已启用 -> select
- test_refresh_status_syncs_notify_switch_off: 开关已选 + 模块停用 -> deselect
- test_refresh_status_leaves_consistent_switch_alone: 开关与模块一致 -> 不动作
- test_refresh_status_updates_tray_title_once: 托盘标题随状态更新且不变时跳过
- test_format_uptime_three_tiers[9]: <1h 分秒 / <1d 时分 / >=1d 天时
- test_log_dir_from_config_file: 绝对路径 -> dirname 且目录被确保存在
- test_log_dir_empty_falls_back_to_state_dir: logging.file 为空 -> 回落 state_file 目录
- test_log_dir_relative_resolves_against_cwd: 相对路径按 cwd 绝对化
- test_open_logs_delegates_to_utils: _open_logs 委托 utils.open_path (不真开资源管理器)
- test_notify_on_reflects_ctx: _notify_on 取 ctx.notify 布尔态
- test_toggle_pause_roundtrip: 暂停 <-> 恢复 往返
- test_toggle_notify_from_unmounted_enables: 未挂载 -> set_enabled(True) + 开关选中 (会话级)
- test_toggle_notify_unmount_error_shows_warning: 平台不支持 -> AutoQbError -> 弹窗, 开关不选中
- test_toggle_notify_mounted_toggles[2]: 已挂载热开关翻转 -> 开关跟随
- test_toggle_autostart_disables_when_enabled: 已启用 -> disable
- test_toggle_autostart_enables_when_disabled: 未启用 -> enable(config_path)
- test_toggle_autostart_error_shows_warning: enable 抛 AutoQbError -> 弹窗不外抛
- test_run_tray_wraps_generic_init_failure: 初始化任意异常 -> 包成 AutoQbError ("托盘 UI 初始化失败")
- test_run_tray_reraises_autoqb_error: AutoQbError 原样重抛 (不二次包装)
- test_trayui_init_sets_appid_before_first_window: TrayUi.__init__ 里 AUMID 设置先于 _build_window (时序钉死, issue 26-10-02-0727)
- test_set_windows_appid_success_no_readback: (Win32 替身) hr=0 -> 留「已设置」debug, 无读回动作 (读回判据已删, issue 26-10-02-0441)
- test_set_windows_appid_set_failure_warns: hr != 0 -> warning 后直接返回
- test_set_windows_appid_setter_raises_is_swallowed: 设置 API 抛错 -> 吞掉 (进程静默继续)
"""
import contextlib
import ctypes
import logging
import os
import queue
import socket
import struct
import sys
import threading
import time
import types

import pytest

from auto_qb.infra.errors import AutoQbError
from auto_qb.tray import UI_PORT_FILE_NAME, ShowIpcServer, TrayUi, UiLogHandler, run_tray, send_show
from auto_qb.tray import app as tray_app
from helpers import make_manager

MODULE_LOGGER = logging.getLogger("auto_qb.tray.app")

# ============================ 替身与夹具 ============================


class _WidgetStub:
    """Tk 控件替身: 只记录 configure 调用 (托盘逻辑缝测试用, 不渲染)"""
    def __init__(self):
        self.configured = []
        self.text = None

    def configure(self, **kw):
        self.configured.append(kw)
        if "text" in kw:
            self.text = kw["text"]


class _SwitchStub:
    """CTkSwitch 替身: 记录 select/deselect, get 返回当前勾选态"""
    def __init__(self, checked=False):
        self.checked = checked
        self.actions = []

    def get(self):
        return self.checked

    def select(self):
        self.checked = True
        self.actions.append("select")

    def deselect(self):
        self.checked = False
        self.actions.append("deselect")


class _LogBoxStub:
    """CTkTextbox 替身: 记录插入/裁剪; index 按预置行号返回 (驱动 excess 裁剪分支)"""
    def __init__(self, line_count=0):
        self.lines = []
        self.configured = []
        self.deleted = []
        self.seen = []
        self._line_count = line_count

    def configure(self, **kw):
        self.configured.append(kw)

    def insert(self, index, text):
        self.lines.append(text)

    def index(self, _index):
        return f"{self._line_count}.0"

    def delete(self, start, end):
        self.deleted.append((start, end))

    def see(self, index):
        self.seen.append(index)


class _RootStub:
    """Tk root 替身: 记录窗口动作; state 可脚本化 (驱动 toggle_window 分支)"""
    def __init__(self, state="normal"):
        self.calls = []
        self.after_args = None
        self._state = state

    def quit(self):
        self.calls.append("quit")

    def after(self, ms, fn):
        self.after_args = (ms, fn)

    def deiconify(self):
        self.calls.append("deiconify")

    def lift(self):
        self.calls.append("lift")

    def attributes(self, key, value):
        self.calls.append(("attributes", key, value))

    def focus_force(self):
        self.calls.append("focus_force")

    def withdraw(self):
        self.calls.append("withdraw")

    def state(self):
        return self._state


class _IconStub:
    """pystray Icon 替身: 记录悬浮提示标题写入"""
    def __init__(self):
        self.titles = []

    @property
    def title(self):
        return self.titles[-1] if self.titles else ""

    @title.setter
    def title(self, value):
        self.titles.append(value)


class _NotifyStub:
    """ctx.notify 替身: 只覆盖托盘读写的四个公开口, 不真挂通知 handler (见模块 docstring)"""
    def __init__(self, state=None, enabled=False, error=None):
        self._state = state
        self._enabled = enabled
        self.error = error
        self.set_calls = []

    def enabled_state(self):
        return self._state

    def is_enabled(self):
        return self._enabled

    def set_enabled(self, on):
        self.set_calls.append(on)
        if self.error is not None:
            raise self.error


def _make_tray_ui(mgr):
    """绕过 __init__ 的 widget 构建装配 headless 可测的 TrayUi (真实 manager + 控件替身)"""
    ui = TrayUi.__new__(TrayUi)
    ui.manager = mgr
    ui.dry_run = True
    ui.events = queue.Queue()
    ui.stop_event = threading.Event()
    ui.pause_event = threading.Event()
    ui.log_handler = UiLogHandler()
    ui.root = _RootStub()
    ui.log_box = _LogBoxStub()
    ui.badge = _WidgetStub()
    ui.card_torrents = _WidgetStub()
    ui.card_uptime = _WidgetStub()
    ui.card_conn = _WidgetStub()
    ui.pause_btn = _WidgetStub()
    ui.notify_switch = _SwitchStub()
    ui._icon = None
    ui._icon_title = ""
    ui._paused = False
    ui._started = time.time() - 125  # 固定运行时长 2分05秒, 断言 uptime 文案
    return ui


@contextlib.contextmanager
def _capture_on_module_logger(handler, level=logging.INFO):
    """自挂 handler 到 tray 模块 logger + 显式 setLevel + finally 恢复 (pitfalls/testing/log-capture.md)"""
    old_level, old_propagate = MODULE_LOGGER.level, MODULE_LOGGER.propagate
    MODULE_LOGGER.addHandler(handler)
    MODULE_LOGGER.setLevel(level)
    MODULE_LOGGER.propagate = False
    try:
        yield
    finally:
        MODULE_LOGGER.removeHandler(handler)
        MODULE_LOGGER.setLevel(old_level)
        MODULE_LOGGER.propagate = old_propagate


def _stub_messagebox(monkeypatch):
    """tkinter.messagebox 替身: 有/无 tkinter 的机器上都确定性接到 showwarning 调用"""
    recorded = []
    mb = types.ModuleType("tkinter.messagebox")
    mb.showwarning = lambda *a, **k: recorded.append(a)
    pkg = types.ModuleType("tkinter")
    pkg.messagebox = mb
    monkeypatch.setitem(sys.modules, "tkinter", pkg)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", mb)
    return recorded


def _setup_snapshot(mgr, paused=False, connected=None, torrents=3):
    """按场景设置真实 manager 的只读快照源 (status_snapshot 读 store/_last_conn_ok/_pause_event)"""
    mgr.store.by_hash = {f"h{i}": object() for i in range(torrents)}
    mgr._last_conn_ok = connected
    if paused:
        mgr._pause_event = threading.Event()
        mgr._pause_event.set()
    else:
        mgr._pause_event = None


def _cleanup_tray_handlers():
    """TrayUi.__init__ 异常路径残留: 从 auto_qb logger 摘掉已挂的 UiLogHandler (run() 正常路径才会摘)"""
    aq = logging.getLogger("auto_qb")
    for h in list(aq.handlers):
        if isinstance(h, UiLogHandler):
            aq.removeHandler(h)


# ============================ UiLogHandler ============================


def _record(level, msg, args=()):
    return logging.LogRecord("auto_qb.tray.app", level, __file__, 1, msg, args, None)


def test_uilog_handler_collects_non_debug_lines():
    handler = UiLogHandler()
    handler.emit(_record(logging.INFO, "hello %s", ("world", )))
    handler.emit(_record(logging.WARNING, "beware"))
    assert handler.drain() == ["[INFO] hello world", "[WARNING] beware"]
    assert handler.drain() == [], "drain 必须取走并清空, 二次 drain 为空"


def test_uilog_handler_skips_debug_records():
    handler = UiLogHandler()
    handler.emit(_record(logging.DEBUG, "noisy internals"))
    assert handler.drain() == []


def test_uilog_handler_swallows_format_errors():
    handler = UiLogHandler()
    handler.emit(_record(logging.INFO, "val %d", ("not-a-number", )))  # getMessage 抛 TypeError
    assert handler.drain() == [], "格式化异常必须被 emit 吞掉, 不入队不外抛"


def test_uilog_handler_integration_via_module_logger():
    handler = UiLogHandler()
    with _capture_on_module_logger(handler):
        MODULE_LOGGER.warning("tray seam probe")
    assert handler.drain() == ["[WARNING] tray seam probe"]


# ============================ IPC 端口文件协议 ============================


def test_ipc_start_writes_port_file_and_serves_show(tmp_path):
    port_file = str(tmp_path / UI_PORT_FILE_NAME)
    shown = threading.Event()
    srv = ShowIpcServer(port_file, on_show=lambda: shown.set())
    srv.start()
    try:
        assert os.path.isfile(port_file), "start 必须把监听端口写进端口文件"
        with open(port_file, encoding="ascii") as f:
            port = int(f.read().strip())
        assert 0 < port < 65536
        assert send_show(port_file) is True
        assert shown.wait(5.0), "send_show 后首实例的 on_show 回调必须被触发"
    finally:
        srv.stop()


def test_ipc_ignores_non_show_payload(tmp_path):
    port_file = str(tmp_path / UI_PORT_FILE_NAME)
    calls = []
    srv = ShowIpcServer(port_file, on_show=lambda: calls.append(1))
    srv.start()
    try:
        with open(port_file, encoding="ascii") as f:
            port = int(f.read().strip())
        conn = socket.create_connection(("127.0.0.1", port), timeout=2)
        conn.sendall(b"hide\n")  # 非 show 载荷: 回调不得触发
        conn.close()
        assert send_show(port_file) is True  # 真实 show 证明服务仍存活
        deadline = time.time() + 5
        while not calls and time.time() < deadline:
            time.sleep(0.01)
        assert calls == [1], "非 show 载荷不得触发 on_show (真实 show 恰好触发一次)"
    finally:
        srv.stop()


def test_ipc_survives_client_reset(tmp_path):
    port_file = str(tmp_path / UI_PORT_FILE_NAME)
    shown = threading.Event()
    srv = ShowIpcServer(port_file, on_show=lambda: shown.set())
    srv.start()
    try:
        with open(port_file, encoding="ascii") as f:
            port = int(f.read().strip())
        # SO_LINGER(1,0) -> close 即发 RST -> 服务端 recv 抛 ConnectionResetError(OSError) -> continue
        rst = socket.create_connection(("127.0.0.1", port), timeout=2)
        rst.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        rst.close()
        assert send_show(port_file) is True, "RST 断连后服务必须存活并继续处理 show"
        assert shown.wait(5.0)
    finally:
        srv.stop()


def test_ipc_swallows_on_show_error(tmp_path):
    port_file = str(tmp_path / UI_PORT_FILE_NAME)
    calls, done = [], threading.Event()

    def on_show():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("首实例处理失败")
        done.set()

    srv = ShowIpcServer(port_file, on_show=on_show)
    srv.start()
    try:
        assert send_show(port_file) is True
        assert send_show(port_file) is True
        assert done.wait(5.0), "on_show 抛错必须被吞掉, 第二次唤起仍可达"
        assert len(calls) == 2
    finally:
        srv.stop()


def test_ipc_accept_error_returns(tmp_path):
    srv = ShowIpcServer(str(tmp_path / UI_PORT_FILE_NAME), on_show=lambda: None)
    srv._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv._sock.bind(("127.0.0.1", 0))
    srv._sock.listen(1)
    srv._sock.close()  # accept 必然 OSError -> _serve 直接返回 (模拟退出时 socket 已关)
    srv._serve()  # 同步调用: 不挂起、不抛即通过


def test_ipc_stop_removes_port_file_and_idempotent(tmp_path):
    port_file = str(tmp_path / UI_PORT_FILE_NAME)
    srv = ShowIpcServer(port_file, on_show=lambda: None)
    srv.start()
    with open(port_file, encoding="ascii") as f:
        assert 0 < int(f.read().strip()) < 65536  # 端口文件是整数端口
    srv.stop()
    assert not os.path.exists(port_file), "stop 必须删除端口文件"
    srv.stop()  # 幂等: 二次 stop 不抛
    assert send_show(port_file) is False, "stop 后端口文件已删, send_show 退化 False"


def test_ipc_stop_without_start_is_noop(tmp_path):
    srv = ShowIpcServer(str(tmp_path / UI_PORT_FILE_NAME), on_show=lambda: None)
    srv.stop()  # _sock=None 且端口文件不存在: 不抛即通过


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(None, id="missing"),
        pytest.param("65536abc", id="garbage-bytes"),
        pytest.param("", id="empty-file"),
        pytest.param('{"po', id="half-json"),
    ],
)
def test_send_show_bad_port_file(tmp_path, content):
    port_file = str(tmp_path / UI_PORT_FILE_NAME)
    if content is not None:
        with open(port_file, "w", encoding="ascii") as f:
            f.write(content)
    assert send_show(port_file) is False, "残缺端口文件必须退化为 False, 不得抛 OSError/ValueError"


def test_send_show_refused_when_no_listener(tmp_path):
    # bind 后不 listen: 连接必然被拒 (无 backlog), 等价"首实例已退出"的 connect 失败路径
    hold = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hold.bind(("127.0.0.1", 0))
    port = hold.getsockname()[1]
    try:
        port_file = str(tmp_path / UI_PORT_FILE_NAME)
        with open(port_file, "w", encoding="ascii") as f:
            f.write(str(port))
        assert send_show(port_file) is False
    finally:
        hold.close()


# ============================ poll 队列消费 ============================


def test_poll_quit_stops_poll_chain(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        ui.events.put(("quit", None))
        ui._poll()
        assert "quit" in ui.root.calls
        assert ui.root.after_args is None, "quit 后不得再续 after 轮询链"
    finally:
        _cleanup_tray_handlers()


def test_poll_dispatches_toggle_pause_and_drains_logs(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        ui.events.put(("toggle_pause", None))
        ui.events.put(("totally-unknown-kind", None))  # 未知事件: 分派表 miss, 不得崩
        with _capture_on_module_logger(ui.log_handler):
            ui._poll()
        assert ui.pause_event.is_set(), "toggle_pause 事件必须分派到 _toggle_pause"
        assert any("已暂停自动管理" in line for line in ui.log_box.lines), "事件产生的日志增量必须 drain 进日志视图"
        assert ui.root.after_args[0] == tray_app.POLL_MS, "处理后必须按 POLL_MS re-arm 轮询"
    finally:
        _cleanup_tray_handlers()


def test_poll_handler_failure_does_not_kill_chain(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)

        def _boom():
            raise RuntimeError("open 日志目录失败")

        ui._open_logs = _boom
        ui.events.put(("open_logs", None))  # handler 抛错
        ui.events.put(("toggle_pause", None))  # 后续事件必须仍被处理
        with _capture_on_module_logger(ui.log_handler, level=logging.ERROR):
            ui._poll()
        assert any("托盘事件处理失败" in line for line in ui.log_box.lines), "handler 异常必须被记录"
        assert ui.pause_event.is_set(), "单个事件失败不得杀死 after 轮询链"
    finally:
        _cleanup_tray_handlers()


def test_poll_empty_queue_goes_to_refresh_and_rearms(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        _setup_snapshot(mgr)
        ui = _make_tray_ui(mgr)
        ui._poll()
        assert ui.badge.text == "运行中", "空队列也必须走一轮状态刷新"
        assert ui.card_torrents.text == "3"
        assert ui.root.after_args[0] == tray_app.POLL_MS
    finally:
        _cleanup_tray_handlers()


def test_drain_logs_trims_excess_lines(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        ui.log_box = _LogBoxStub(line_count=250)  # index("end-1c") 报 250 行
        ui.log_handler.emit(_record(logging.INFO, "new line"))
        ui._drain_logs()
        assert ui.log_box.lines == ["[INFO] new line\n"]
        assert ui.log_box.deleted == [("1.0", "50.0")], "excess=250-200 -> 必须裁掉前 50 行"
        assert ui.log_box.seen == ["end"]
    finally:
        _cleanup_tray_handlers()


# ============================ 窗口动作委托 ============================


def test_show_and_hide_window_delegation(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        ui._show_window()
        assert ui.root.calls == ["deiconify", "lift", ("attributes", "-topmost", True), "focus_force"]
        assert ui.root.after_args[0] == 200, "置顶 200ms 后须回落"
        ui._hide_window()
        assert "withdraw" in ui.root.calls, "关闭按钮语义 = 隐藏到托盘"
    finally:
        _cleanup_tray_handlers()


def test_toggle_window_by_state(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        ui.root._state = "withdrawn"
        ui._toggle_window()
        assert "deiconify" in ui.root.calls, "隐藏态 -> 显示"
        ui.root._state = "normal"
        ui.root.calls.clear()
        ui._toggle_window()
        assert "withdraw" in ui.root.calls, "可见态 -> 隐藏到托盘"
    finally:
        _cleanup_tray_handlers()


# ============================ 状态 -> UI 映射 ============================


@pytest.mark.parametrize(
    "paused, connected, badge, conn_text, btn_text",
    [
        pytest.param(True, True, "已暂停", "已连接", "恢复自动管理", id="paused"),
        pytest.param(False, False, "qB 断开", "已断开", "暂停自动管理", id="disconnected"),
        pytest.param(False, True, "运行中", "已连接", "暂停自动管理", id="connected"),
        pytest.param(False, None, "运行中", "连接中…", "暂停自动管理", id="connecting"),
    ],
)
def test_refresh_status_maps_quadrants(tmp_path, paused, connected, badge, conn_text, btn_text):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        _setup_snapshot(mgr, paused=paused, connected=connected)
        ui = _make_tray_ui(mgr)
        ui._refresh_status()
        assert ui.badge.text == badge
        assert ui.card_conn.text == conn_text
        assert ui.pause_btn.text == btn_text
        assert ui.card_torrents.text == "3"
        assert ui.card_uptime.text == "2分05秒"
    finally:
        _cleanup_tray_handlers()


def test_refresh_status_syncs_notify_switch_on(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        _setup_snapshot(mgr)
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = _NotifyStub(state=True)
        ui.notify_switch.checked = False
        ui._refresh_status()
        assert ui.notify_switch.actions == ["select"], "开关未选而模块已启用 -> 补选"
    finally:
        _cleanup_tray_handlers()


def test_refresh_status_syncs_notify_switch_off(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        _setup_snapshot(mgr)
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = _NotifyStub(state=False)
        ui.notify_switch.checked = True
        ui._refresh_status()
        assert ui.notify_switch.actions == ["deselect"], "开关已选而模块停用 -> 补退"
    finally:
        _cleanup_tray_handlers()


def test_refresh_status_leaves_consistent_switch_alone(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        _setup_snapshot(mgr)
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = _NotifyStub(state=True)
        ui.notify_switch.checked = True
        ui._refresh_status()
        assert ui.notify_switch.actions == [], "开关与模块一致 -> 不得动作"
    finally:
        _cleanup_tray_handlers()


def test_refresh_status_updates_tray_title_once(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        _setup_snapshot(mgr)
        ui = _make_tray_ui(mgr)
        icon = _IconStub()
        ui._icon = icon
        ui._refresh_status()
        ui._refresh_status()
        assert icon.titles == ["auto-qb (运行中)"], "标题只在变化时写入托盘 (悬浮提示跟随状态)"
        assert ui._icon_title == "auto-qb (运行中)"
    finally:
        _cleanup_tray_handlers()


# ============================ 纯函数与目录推导 ============================


@pytest.mark.parametrize(
    "seconds, expected",
    [
        pytest.param(0, "0分00秒", id="zero"),
        pytest.param(59, "0分59秒", id="sub-minute"),
        pytest.param(61, "1分01秒", id="minute"),
        pytest.param(3599, "59分59秒", id="just-under-hour"),
        pytest.param(3600, "1时00分", id="hour"),
        pytest.param(3661, "1时01分", id="hour-and-minute"),
        pytest.param(86399, "23时59分", id="just-under-day"),
        pytest.param(86400, "1天00时", id="day"),
        pytest.param(90061, "1天01时", id="day-and-hour"),
    ],
)
def test_format_uptime_three_tiers(seconds, expected):
    assert TrayUi._format_uptime(seconds) == expected


def test_log_dir_from_config_file(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.logging.file = str(tmp_path / "logs" / "app.log")
    d = TrayUi._log_dir(mgr)
    assert os.path.samefile(d, tmp_path / "logs")
    assert os.path.isdir(d), "打开前必须确保目录存在"


def test_log_dir_empty_falls_back_to_state_dir(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.logging.file = ""
    d = TrayUi._log_dir(mgr)
    assert os.path.samefile(d, tmp_path), "logging.file 为空 -> 回落 state_file 所在目录"
    assert os.path.isdir(d)


def test_log_dir_relative_resolves_against_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # 相对路径以 cwd 绝对化, 防止在仓库根落目录
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.logging.file = os.path.join("logs", "app.log")
    d = TrayUi._log_dir(mgr)
    assert d == os.path.join(str(tmp_path), "logs")
    assert os.path.isdir(d)


def test_open_logs_delegates_to_utils(tmp_path, monkeypatch):
    mgr = make_manager(str(tmp_path / "state.json"))
    opened = []
    monkeypatch.setattr(tray_app.utils, "open_path", lambda p: opened.append(p))
    ui = _make_tray_ui(mgr)
    ui._open_logs()
    assert len(opened) == 1 and os.path.samefile(opened[0], tmp_path), "委托 utils.open_path 打开日志目录"


def test_notify_on_reflects_ctx(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = _NotifyStub(state=None)
        assert ui._notify_on() is False
        ui.manager.ctx.notify = _NotifyStub(state=True)
        assert ui._notify_on() is True
    finally:
        _cleanup_tray_handlers()


# ============================ 动作分派 ============================


def test_toggle_pause_roundtrip(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        ui = _make_tray_ui(mgr)
        with _capture_on_module_logger(ui.log_handler):
            ui._toggle_pause()
        assert ui.pause_event.is_set(), "首次切换 -> 暂停"
        ui._toggle_pause()
        assert not ui.pause_event.is_set(), "二次切换 -> 恢复"
    finally:
        _cleanup_tray_handlers()


def test_toggle_notify_from_unmounted_enables(tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        notify = _NotifyStub(state=None)
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = notify
        with _capture_on_module_logger(ui.log_handler):
            ui._toggle_notify()
        assert notify.set_calls == [True], "未挂载 -> 会话级开启"
        assert ui.notify_switch.actions == ["select"]
    finally:
        _cleanup_tray_handlers()


def test_toggle_notify_unmount_error_shows_warning(monkeypatch, tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        recorded = _stub_messagebox(monkeypatch)
        notify = _NotifyStub(state=None, error=AutoQbError("平台不支持"))
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = notify
        ui._toggle_notify()  # 不外抛
        assert recorded and "平台不支持" in recorded[0][1], "平台不支持 -> 弹窗提示"
        assert ui.notify_switch.actions == [], "开关由勾选态回弹, 不得选中"
    finally:
        _cleanup_tray_handlers()


@pytest.mark.parametrize(
    "state, enabled, expected_on",
    [
        pytest.param(True, True, False, id="on->off"),
        pytest.param(False, False, True, id="off->on"),
    ],
)
def test_toggle_notify_mounted_toggles(tmp_path, state, enabled, expected_on):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        notify = _NotifyStub(state=state, enabled=enabled)
        ui = _make_tray_ui(mgr)
        ui.manager.ctx.notify = notify
        with _capture_on_module_logger(ui.log_handler):
            ui._toggle_notify()
        assert notify.set_calls == [expected_on], "已挂载 -> 热开关翻转"
        expected_action = "select" if expected_on else "deselect"
        assert ui.notify_switch.actions == [expected_action]
    finally:
        _cleanup_tray_handlers()


def test_toggle_autostart_disables_when_enabled(monkeypatch, tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        calls = []
        monkeypatch.setattr(tray_app.autostart, "is_enabled", lambda p: True)
        monkeypatch.setattr(tray_app.autostart, "disable", lambda: calls.append("disable"))
        monkeypatch.setattr(tray_app.autostart, "enable", lambda p: calls.append("enable"))
        ui = _make_tray_ui(mgr)
        with _capture_on_module_logger(ui.log_handler):
            ui._toggle_autostart()
        assert calls == ["disable"], "已启用 -> 关闭"
    finally:
        _cleanup_tray_handlers()


def test_toggle_autostart_enables_when_disabled(monkeypatch, tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        calls = []
        monkeypatch.setattr(tray_app.autostart, "is_enabled", lambda p: False)
        monkeypatch.setattr(tray_app.autostart, "disable", lambda: calls.append("disable"))
        monkeypatch.setattr(tray_app.autostart, "enable", lambda p: calls.append("enable"))
        ui = _make_tray_ui(mgr)
        with _capture_on_module_logger(ui.log_handler):
            ui._toggle_autostart()
        assert calls == ["enable"], "未启用 -> 开启"
    finally:
        _cleanup_tray_handlers()


def test_toggle_autostart_error_shows_warning(monkeypatch, tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))
    try:
        recorded = _stub_messagebox(monkeypatch)

        def _boom(_p):
            raise AutoQbError("自启注册失败")

        monkeypatch.setattr(tray_app.autostart, "is_enabled", lambda p: False)
        monkeypatch.setattr(tray_app.autostart, "enable", _boom)
        ui = _make_tray_ui(mgr)
        ui._toggle_autostart()  # 不外抛
        assert recorded and "自启注册失败" in recorded[0][1], "AutoQbError -> 弹窗提示不外抛"
    finally:
        _cleanup_tray_handlers()


# ============================ run_tray 错误包装 ============================


def test_run_tray_wraps_generic_init_failure(monkeypatch, tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))

    def _boom(self):
        raise ValueError("无显示环境")

    monkeypatch.setattr(TrayUi, "_build_window", _boom)
    try:
        with pytest.raises(AutoQbError, match="托盘 UI 初始化失败"):
            run_tray(mgr, dry_run=True)
    finally:
        _cleanup_tray_handlers()


def test_run_tray_reraises_autoqb_error(monkeypatch, tmp_path):
    mgr = make_manager(str(tmp_path / "state.json"))

    def _boom(self):
        raise AutoQbError("桌面会话缺失")

    monkeypatch.setattr(TrayUi, "_build_window", _boom)
    try:
        with pytest.raises(AutoQbError, match="桌面会话缺失"):
            run_tray(mgr, dry_run=True)  # AutoQbError 原样重抛, 不二次包装
    finally:
        _cleanup_tray_handlers()


def test_trayui_init_sets_appid_before_first_window(monkeypatch, tmp_path):
    """issue 26-10-02-0727: AUMID 设置调用须先于首个窗口创建 —— 时序钉死防调用点再丢失"""
    order = []
    mgr = make_manager(str(tmp_path / "state.json"))
    monkeypatch.setattr(tray_app, "_set_windows_appid", lambda: order.append("appid"))
    monkeypatch.setattr(TrayUi, "_build_window", lambda self: order.append("window"))
    monkeypatch.setattr(TrayUi, "_build_tray", lambda self: order.append("tray"))
    try:
        TrayUi(mgr, dry_run=True)
    finally:
        _cleanup_tray_handlers()
    assert order == ["appid", "window", "tray"], ("AUMID 必须在 _build_window(首个窗口)之前设置, 否则 Windows 任务栏按钮回退 python 默认图标")


# ---------- _set_windows_appid: Win32 边界替身 (设置调用 hr=0 即成功; 读回校验已删 ——
# 非打包进程读回恒 APPMODEL_ERROR(15703) 而非 122, 判据无真实命中场景, issue 26-10-02-0441) ----------


class _ListHandler(logging.Handler):
    """轻量记录 handler: 抓模块 logger 消息文本 (替代 caplog, 见 log-capture.md)"""
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class _FakeSetter:
    """SetCurrentProcessExplicitAppUserModelID 替身: 回预置 hr, 可注入异常"""
    def __init__(self, hr=None, error=None):
        self.hr = hr
        self.error = error
        self.calls = []
        self.argtypes = None
        self.restype = None

    def __call__(self, aumid):
        self.calls.append(aumid)
        if self.error is not None:
            raise self.error
        return self.hr


def _patch_windll(monkeypatch, setter):
    """把 ctypes.windll 换成只含 shell32 的替身 (函数内 import ctypes 拿到同一模块对象)

    不给 kernel32: 删读回校验后函数不应再触碰它 —— 读回若回归, windll.kernel32 属性
    AttributeError 会被函数吞掉并留「设置失败」debug, 被用例的精确断言判红。

    `raising=False`: POSIX 的 ctypes 没有 windll 属性, 不给这个开关会在 Linux CI 上
    直接 AttributeError 判红; `_set_windows_appid` 本身不判平台(全靠 try/except 兜底),
    补上假门面即可两平台同跑。
    """
    fake = types.SimpleNamespace(shell32=types.SimpleNamespace(SetCurrentProcessExplicitAppUserModelID=setter), )
    monkeypatch.setattr(ctypes, "windll", fake, raising=False)


def test_set_windows_appid_success_no_readback(monkeypatch):
    setter = _FakeSetter(hr=0)
    _patch_windll(monkeypatch, setter)
    probe = _ListHandler()
    with _capture_on_module_logger(probe, level=logging.DEBUG):
        tray_app._set_windows_appid()
    assert setter.calls == [tray_app.WINDOWS_TOAST_APPID], "AUMID 必须取 toast 来源身份"
    assert probe.messages == [f"AppUserModelID 已设置: {tray_app.WINDOWS_TOAST_APPID}"
                             ], ("hr=0 即成功且无任何读回动作 (有读回会触碰不存在的 kernel32, 只留「设置失败」debug)")


def test_set_windows_appid_set_failure_warns(monkeypatch):
    setter = _FakeSetter(hr=5)
    _patch_windll(monkeypatch, setter)
    probe = _ListHandler()
    with _capture_on_module_logger(probe, level=logging.WARNING):
        tray_app._set_windows_appid()
    assert probe.messages == ["AppUserModelID 设置失败: HRESULT=5"], "hr != 0 必须 warning, 且此后不得再有动作"


def test_set_windows_appid_setter_raises_is_swallowed(monkeypatch):
    setter = _FakeSetter(error=OSError("no shell32"))
    _patch_windll(monkeypatch, setter)
    probe = _ListHandler()
    with _capture_on_module_logger(probe, level=logging.DEBUG):
        tray_app._set_windows_appid()  # 异常被吞, 进程静默继续
    assert probe.messages == ["AppUserModelID 设置失败"], "只走 logger.debug (与 hr!=0 的 warning 文案区分)"
