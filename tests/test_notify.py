"""test_notify 测试计划: 主动通知(notify.py)

## 测试计划(每个测试函数一条)
- test_notify_throttle_hourly_cap: 每小时上限, 超出丢弃, 窗口滑出后恢复
- test_notify_throttle_dedup: 同键去重窗口内丢弃, 窗口外放行; dedup_window=0 不去重
- test_notify_handler_level_filter: 低于 min_level 的日志不通知(经 logger 全链路)
- test_notify_handler_dispatch: WARNING/ERROR 日志入队并由后台线程派发, ERROR 标记 urgent
- test_notify_handler_self_loop_guard: auto_qb.notify 来源的记录被忽略(防自环)
- test_notify_handler_quiet_hours: 免打扰时段(含跨午夜)跳过发送, 时段外照常
- test_notify_handler_throttle_drops: 同键重复与超限的记录不派发
- test_notify_channel_windows_command: Windows 命令构造(powershell -EncodedCommand, toast XML 经双层 base64, AUMID 注册跳过)
- test_notify_windows_appid_ensure: AUMID 幂等注册(已存在复用/无 APPDATA/注册失败回退 PowerShell 来源)
- test_notify_register_windows_appid_command: AUMID 注册命令(快捷方式指向当前解释器/非零退出报错)
- test_notify_channel_linux_darwin_commands: Linux notify-send / macOS osascript 命令构造
- test_notify_channel_unsupported_platform: 不支持平台构造抛 ValueError
- test_notify_channel_send_failure: 命令失败返回 False 且不外抛
- test_setup_notify_disabled: 未启用返回 None 且不挂载 handler
- test_setup_notify_attaches_and_unsupported: 启用挂载到 auto_qb logger; 不支持平台抛 AutoQbError
- test_notify_fatal_skips_when_disabled: notify_fatal 在无配置/未启用时不发送
"""
import base64
import logging
import re
import sys
import time
from datetime import datetime

import pytest

from auto_qb import notify as notify_mod
from auto_qb.config import NotifyConfig
from auto_qb.notify import (
    NOTIFY_LOGGER_PREFIX,
    NotifyHandler,
    NotifyThrottle,
    PlatformChannel,
    notify_fatal,
    setup_notify,
)


class FakeChannel:
    """记录 send 调用的假渠道"""
    def __init__(self):
        self.sent = []

    def send(self, title, body, urgent=False):
        self.sent.append((title, body, urgent))
        return True


def _wait_for(cond, timeout=2.0):
    """等待后台派发线程消费完成(避免测试与 worker 竞态)"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.01)
    return False


def _make_handler(**cfg) -> tuple:
    """构造 (handler, FakeChannel); 默认 WARNING 级别 + 不去重不限量, 便于单点测试"""
    config = NotifyConfig(
        enabled=True,
        min_level=cfg.pop("min_level", "WARNING"),
        quiet_hours=cfg.pop("quiet_hours", ""),
        max_per_hour=cfg.pop("max_per_hour", 1000),
        dedup_window=cfg.pop("dedup_window", 0),
    )
    channel = FakeChannel()
    handler = NotifyHandler(config, channel, now=cfg.pop("now", None))
    return handler, channel


def test_notify_throttle_hourly_cap():
    """每小时上限: 超出丢弃, 1 小时窗口滑出后恢复"""
    throttle = NotifyThrottle(max_per_hour=3, dedup_window=0, now=lambda: 1000.0)
    assert all(throttle.allow(f"k{i}") for i in range(3))
    assert not throttle.allow("k3"), "超出每小时上限应丢弃"
    # 时间推进 1 小时: 窗口滑出, 恢复放行
    throttle = NotifyThrottle(max_per_hour=3, dedup_window=0, now=lambda: 1000.0 + 3600.0)
    assert throttle.allow("k3")


def test_notify_throttle_dedup():
    """同键去重: 窗口内丢弃, 窗口外放行; 不同键互不影响; dedup_window=0 不去重"""
    clock = {"t": 0.0}
    throttle = NotifyThrottle(max_per_hour=100, dedup_window=10.0, now=lambda: clock["t"])
    assert throttle.allow("same")
    assert not throttle.allow("same"), "去重窗口内应丢弃"
    assert throttle.allow("other"), "不同键不受影响"
    clock["t"] = 10.0
    assert throttle.allow("same"), "窗口外应放行"

    no_dedup = NotifyThrottle(max_per_hour=100, dedup_window=0, now=lambda: 0.0)
    assert all(no_dedup.allow("same") for _ in range(5)), "dedup_window=0 不去重"


def test_notify_handler_level_filter():
    """低于 min_level(WARNING)的 INFO 日志不产生通知(经 logger 全链路)"""
    handler, channel = _make_handler(min_level="WARNING")
    test_logger = logging.getLogger("auto_qb.test_notify.level")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)
    try:
        test_logger.info("不应通知的 INFO")
        test_logger.warning("应当通知的 WARNING")
        assert _wait_for(lambda: len(channel.sent) == 1), f"应仅派发 WARNING: {channel.sent}"
        assert channel.sent[0][0] == "auto-qb WARNING"
        assert channel.sent[0][1] == "应当通知的 WARNING"
    finally:
        test_logger.removeHandler(handler)


def test_notify_handler_dispatch():
    """ERROR 日志派发并标记 urgent; 消息内容为原始日志消息"""
    handler, channel = _make_handler()
    record = logging.LogRecord(
        name="auto_qb.mixins.grouping",
        level=logging.ERROR,
        pathname="p",
        lineno=1,
        msg="文件丢失, 暂停整组: %s",
        args=("HASH123 [HHan]", ),
        exc_info=None,
    )
    handler.emit(record)
    assert _wait_for(lambda: len(channel.sent) == 1), f"应派发 ERROR 通知: {channel.sent}"
    title, body, urgent = channel.sent[0]
    assert title == "auto-qb ERROR"
    assert body == "文件丢失, 暂停整组: HASH123 [HHan]"
    assert urgent is True, "ERROR 级别应标记 urgent"


def test_notify_handler_self_loop_guard():
    """notify 模块来源的记录被忽略(防'通知触发通知'自环), 同步不入队"""
    handler, channel = _make_handler()
    record = logging.LogRecord(
        name=f"{NOTIFY_LOGGER_PREFIX}.sub",
        level=logging.ERROR,
        pathname="p",
        lineno=1,
        msg="通知模块自身的日志",
        args=None,
        exc_info=None,
    )
    handler.emit(record)
    assert channel.sent == []
    assert handler._queue.empty(), "防自环记录不应入队"


def test_notify_handler_quiet_hours():
    """免打扰时段跳过发送(含跨午夜区间), 时段外照常"""
    # 23:30 落在 "23:00-08:00" 跨午夜区间内 -> 跳过
    night = datetime(2026, 9, 12, 23, 30)
    handler, channel = _make_handler(quiet_hours="23:00-08:00", now=lambda: night)
    record = logging.LogRecord(
        name="auto_qb.test",
        level=logging.ERROR,
        pathname="p",
        lineno=1,
        msg="夜间错误",
        args=None,
        exc_info=None,
    )
    handler.emit(record)
    assert channel.sent == [], "免打扰时段应跳过"
    assert handler._queue.empty(), "免打扰记录不应入队"

    # 12:00 不在区间 -> 照常派发
    handler.quiet_hours = "23:00-08:00"
    handler._now = lambda: datetime(2026, 9, 12, 12, 0)
    handler.emit(record)
    assert _wait_for(lambda: len(channel.sent) == 1), "时段外应照常派发"


def test_notify_handler_throttle_drops():
    """同键重复(去重窗)与超出每小时上限的记录不派发"""
    handler, channel = _make_handler(max_per_hour=2, dedup_window=600.0)
    for i in range(5):
        handler.emit(
            logging.LogRecord(
                name="auto_qb.test",
                level=logging.WARNING,
                pathname="p",
                lineno=1,
                msg=f"消息 {i}",
                args=None,
                exc_info=None,
            )
        )
    assert _wait_for(lambda: len(channel.sent) == 2), f"应按上限仅派发 2 条: {channel.sent}"
    time.sleep(0.05)
    assert len(channel.sent) == 2, "节流后不应再派发"


def test_notify_channel_windows_command(monkeypatch):
    """Windows: powershell -EncodedCommand 结构; 脚本内 toast XML 双层 base64 可还原且含标题正文;
    AUMID 注册过程被跳过(避免测试真实写快捷方式)"""
    monkeypatch.setattr(PlatformChannel, "_ensure_windows_appid", lambda self: notify_mod.WINDOWS_TOAST_APPID)
    channel = PlatformChannel("win32")
    cmd = channel._build("auto-qb ERROR", '文件<丢失> & "引号"', False)
    assert cmd[0] == "powershell"
    assert "-EncodedCommand" in cmd and "-NoProfile" in cmd and "-NonInteractive" in cmd
    script = base64.b64decode(cmd[-1]).decode("utf-16-le")
    assert notify_mod.WINDOWS_TOAST_APPID in script, "toast 来源应为已注册的 AUMID"
    xml_b64 = re.search(r"FromBase64String\('([A-Za-z0-9+/=]+)'\)", script).group(1)
    toast_xml = base64.b64decode(xml_b64).decode("utf-8")
    assert "ToastText02" in toast_xml
    assert '文件&lt;丢失&gt; &amp; "引号"' in toast_xml, "XML 特殊字符应转义且标题正文完整"


def test_notify_windows_appid_ensure(monkeypatch):
    """AUMID 幂等注册: 快捷方式已存在直接复用; 无 APPDATA / 注册失败回退 PowerShell 来源"""
    # 已存在 -> 直接复用, 不触发注册
    monkeypatch.setattr(notify_mod.os.path, "exists", lambda p: True)
    assert PlatformChannel("win32")._appid == notify_mod.WINDOWS_TOAST_APPID

    # 无 APPDATA(异常环境) -> 回退
    monkeypatch.setattr(notify_mod.os.path, "exists", lambda p: False)
    monkeypatch.setenv("APPDATA", "")
    assert PlatformChannel("win32")._appid == notify_mod.WINDOWS_TOAST_APPID_FALLBACK

    # 注册失败(权限等) -> 回退, 不外抛
    monkeypatch.setenv("APPDATA", r"C:\fake-appdata")

    def boom(self, shortcut):
        raise OSError("无权限")

    monkeypatch.setattr(PlatformChannel, "_register_windows_appid", boom)
    assert PlatformChannel("win32")._appid == notify_mod.WINDOWS_TOAST_APPID_FALLBACK


def test_notify_register_windows_appid_command(monkeypatch):
    """AUMID 注册命令: WScript.Shell 快捷方式指向当前解释器; 非零退出报 OSError"""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(notify_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(notify_mod.os.path, "exists", lambda p: True)  # 注册后已落盘
    channel = PlatformChannel.__new__(PlatformChannel)  # 跳过 __init__, 单测注册方法
    channel._register_windows_appid(r"C:\fake\AutoQB.lnk")
    script = base64.b64decode(captured["cmd"][-1]).decode("utf-16-le")
    assert "CreateShortcut('C:\\fake\\AutoQB.lnk')" in script
    assert f"$lnk.TargetPath = '{sys.executable}'" in script

    monkeypatch.setattr(notify_mod.subprocess, "run", lambda *a, **k: _FakeCompleted(returncode=1))
    with pytest.raises(OSError):
        channel._register_windows_appid(r"C:\fake\AutoQB.lnk")


class _FakeCompleted:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stderr = b""


def test_notify_channel_linux_darwin_commands():
    """Linux notify-send / macOS osascript 命令构造(monkeypatch 平台, 不真实发送)"""
    linux = PlatformChannel("linux")
    assert linux._build("t", "b", True) == ["notify-send", "-a", "auto-qb", "-u", "critical", "t", "b"]
    assert linux._build("t", "b", False)[-3:] == ["normal", "t", "b"]

    darwin = PlatformChannel("darwin")
    cmd = darwin._build("标题", '含"引号"\\反斜杠', False)
    assert cmd[0] == "osascript" and cmd[1] == "-e"
    assert '含\\"引号\\"\\\\反斜杠' in cmd[2], "AppleScript 字符串应转义引号与反斜杠"


def test_notify_channel_unsupported_platform():
    """不支持的平台构造时抛 ValueError(启动期 fail-fast)"""
    with pytest.raises(ValueError):
        PlatformChannel("sunos")


def test_notify_channel_send_failure(monkeypatch):
    """send 内命令失败(OSError/非零退出)返回 False 且不外抛"""
    def boom(*args, **kwargs):
        raise OSError("命令不存在")

    monkeypatch.setattr(notify_mod.subprocess, "run", boom)
    channel = PlatformChannel("linux")
    assert channel.send("t", "b") is False

    monkeypatch.setattr(notify_mod.subprocess, "run", lambda *a, **k: _FakeCompleted(returncode=1))
    assert channel.send("t", "b") is False


def test_setup_notify_disabled():
    """notify.enabled=False(默认) -> 返回 None 且不挂载 handler"""
    assert setup_notify(NotifyConfig()) is None
    assert setup_notify(None) is None
    assert not any(isinstance(h, NotifyHandler) for h in logging.getLogger("auto_qb").handlers)


def test_setup_notify_attaches_and_unsupported(monkeypatch):
    """启用时挂载到 auto_qb logger(测试后清理); 不支持平台抛 AutoQbError;
    AUMID 注册被跳过(测试不得在真机开始菜单产生真实快捷方式副作用)"""
    monkeypatch.setattr(PlatformChannel, "_ensure_windows_appid", lambda self: notify_mod.WINDOWS_TOAST_APPID)
    handler = setup_notify(NotifyConfig(enabled=True, min_level="ERROR", max_per_hour=5, dedup_window=0))
    try:
        assert isinstance(handler, NotifyHandler)
        assert handler in logging.getLogger("auto_qb").handlers
    finally:
        logging.getLogger("auto_qb").removeHandler(handler)
        handler.close()

    from auto_qb.errors import AutoQbError

    monkeypatch.setattr(sys, "platform", "sunos")
    with pytest.raises(AutoQbError):
        setup_notify(NotifyConfig(enabled=True))


def test_notify_fatal_skips_when_disabled(monkeypatch):
    """notify_fatal: 无配置/未启用时不发送; 启用时走渠道发送"""
    notify_fatal("不应发送", None)
    notify_fatal("不应发送", NotifyConfig(enabled=False))

    sent = []

    def fake_channel():
        return type("C", (), {"send": staticmethod(lambda t, b, urgent=False: sent.append((t, b, urgent)) or True)})

    monkeypatch.setattr(notify_mod, "PlatformChannel", fake_channel)
    notify_fatal("致命: qB 字段不兼容", NotifyConfig(enabled=True))
    assert sent == [("auto-qb 已停止", "致命: qB 字段不兼容", True)]
