"""test_notify 测试计划: 主动通知(notify.py)

## 测试计划(每个测试函数一条)
- test_notify_throttle_hourly_cap: 每小时上限, 超出丢弃, 窗口滑出后恢复
- test_notify_throttle_dedup: 同键去重窗口内丢弃, 窗口外放行; dedup_window=0 不去重
- test_notify_handler_level_filter: 低于 min_level 的日志不通知(经 logger 全链路)
- test_notify_handler_dispatch: WARNING/ERROR 日志入队并由后台线程派发, ERROR 标记 urgent
- test_notify_handler_self_loop_guard: auto_qb.infra.notify 来源的记录被忽略(防自环)
- test_notify_handler_quiet_hours: 免打扰时段(含跨午夜)跳过发送, 时段外照常
- test_notify_quiet_hours_does_not_consume_quota: 免打扰判定在节流**之前**, 免打扰期间不消耗每小时配额/不刷新去重窗口
- test_notify_throttle_dedup_table_evicted: 去重表按窗口淘汰(长跑进程里唯一的无界增长点)
- test_notify_handler_throttle_drops: 同键重复与超限的记录不派发
- test_notify_channel_windows_command: Windows 命令构造(powershell -EncodedCommand, toast XML 经双层 base64, AUMID 注册跳过)
- test_notify_windows_appid_ensure: AUMID 幂等注册(已存在复用/无 APPDATA/注册失败回退 PowerShell 来源)
- test_notify_channel_linux_darwin_commands: Linux notify-send / macOS osascript 命令构造
- test_notify_channel_unsupported_platform: 不支持平台构造抛 ValueError
- test_notify_channel_send_failure: 命令失败返回 False 且不外抛
- test_setup_notify_disabled: 未启用返回 None 且不挂载 handler
- test_setup_notify_attaches_and_unsupported: 启用挂载到 auto_qb logger; 不支持平台抛 AutoQbError
- test_setup_notify_force_hot_attach: 配置未启用时 force=True 热挂载(UI 开关), 不带 force 返回 None
- test_notify_fatal_skips_when_disabled: notify_fatal 在无配置/未启用时不发送
- test_notify_emit_exception_swallowed: emit 内部异常(如 getMessage 抛错)不外抛(handleError 兜底)
- test_notify_close_twice_safe: close 幂等(重复调用/队列已空均不炸)
- test_notify_fatal_channel_error_swallowed: notify_fatal 渠道构造异常 -> 静默(不外抛)
- test_notify_legacy_shortcut_cleanup: legacy lnk 清理: 存在的旧快捷方式被删除(APPDATA 显式给定, winreg 注入替身, 文件操作经 monkeypatch, 不动真实开始菜单)
- test_notify_real_send_blocked_under_pytest: conftest 会话夹具拦截通知器命令(不启动真实进程), send 走失败分支返回 False
- test_notify_fatal_enabled_does_not_launch_process: 通知**启用且全程不 mock** 走 `notify_fatal` 真实路径 ⇒ 一个进程都不启动(用户原始诉求"测试时弹出通知框"的最直接回归点)
"""
import base64
import logging
import re
import sys
import time
from datetime import datetime

import pytest

from auto_qb.infra import notify as notify_mod
from auto_qb.config import NotifyConfig
from auto_qb.infra.notify import (
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


def test_notify_quiet_hours_does_not_consume_quota():
    """免打扰期间的通知**不吃配额**: 判定必须在 `throttle.allow` 之前

    `allow` 有副作用(计入 `_sent_at` + 刷新 `_dedup_at`)。若先 allow 再判安静时段, 免打扰
    期间产生的通知会白白吃掉每小时配额并推迟去重窗口 ⇒ 时段一结束, 本该立刻发出的通知
    仍被挡住 —— 用户体感是"免打扰结束后反而收不到通知"。
    """
    night = datetime(2026, 9, 12, 23, 30)
    # 上限 1 条: 免打扰期间发 5 条, 配额必须仍是满的
    handler, channel = _make_handler(quiet_hours="23:00-08:00", max_per_hour=1, dedup_window=600.0, now=lambda: night)
    for i in range(5):
        handler.emit(
            logging.LogRecord(
                name="auto_qb.test",
                level=logging.WARNING,
                pathname="p",
                lineno=1,
                msg=f"夜间消息 {i}",
                args=None,
                exc_info=None,
            )
        )
    assert channel.sent == []
    assert handler.throttle._sent_at == [], f"免打扰不该消耗配额: {handler.throttle._sent_at}"
    assert handler.throttle._dedup_at == {}, f"免打扰不该刷新去重窗口: {handler.throttle._dedup_at}"

    # 免打扰结束: 第一条必须立刻放行(配额与去重窗口都没被夜间那条吃掉)
    handler.quiet_hours = None
    handler.emit(
        logging.LogRecord(
            name="auto_qb.test",
            level=logging.WARNING,
            pathname="p",
            lineno=1,
            msg="夜间消息 0",
            args=None,
            exc_info=None,
        )
    )
    assert _wait_for(lambda: len(channel.sent) == 1), "免打扰结束后应立刻放行(未被配额挡住)"


def test_notify_throttle_dedup_table_evicted():
    """去重表按窗口淘汰: 窗口滑出的键被清掉, 窗口内的保留"""
    clock = {"t": 1000.0}
    throttle = NotifyThrottle(max_per_hour=100, dedup_window=10.0, now=lambda: clock["t"])
    assert throttle.allow("a")
    assert throttle.allow("b")
    assert set(throttle._dedup_at) == {"a", "b"}
    clock["t"] += 5.0
    assert throttle.allow("c")  # 触发一次淘汰: a/b 仍在窗口内
    assert set(throttle._dedup_at) == {"a", "b", "c"}
    clock["t"] += 6.0  # a/b 已超窗口(11s > 10s), c 仍在(6s)
    assert throttle.allow("d")
    assert set(throttle._dedup_at) == {"c", "d"}, f"过期键应被淘汰: {throttle._dedup_at}"


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
    monkeypatch.setattr(PlatformChannel, "_ensure_appid_registered", lambda self: notify_mod.WINDOWS_TOAST_APPID)
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
    """AUMID 注册表注册(注册表键 + legacy lnk 清理); 注册失败回退 PowerShell 来源, 不外抛"""
    monkeypatch.setattr(notify_mod.os, "remove", lambda p: None)  # 屏蔽 legacy lnk 真删(测试不得动开始菜单)
    removed = []
    monkeypatch.setattr(notify_mod.os.path, "exists", lambda p: True)
    monkeypatch.setattr(PlatformChannel, "_register_appid_registry", lambda shortcut: removed.append(shortcut))
    assert PlatformChannel("win32")._appid == notify_mod.WINDOWS_TOAST_APPID
    assert len(removed) == 1, "注册时应执行一次"

    # 注册失败(权限等) -> 回退, 不外抛
    def boom(shortcut):
        raise OSError("无权限")

    monkeypatch.setattr(PlatformChannel, "_register_appid_registry", boom)
    assert PlatformChannel("win32")._appid == notify_mod.WINDOWS_TOAST_APPID_FALLBACK


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


class _FakeCompleted:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stderr = b""


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
    monkeypatch.setattr(PlatformChannel, "_ensure_appid_registered", lambda self: notify_mod.WINDOWS_TOAST_APPID)
    handler = setup_notify(NotifyConfig(enabled=True, min_level="ERROR", max_per_hour=5, dedup_window=0))
    try:
        assert isinstance(handler, NotifyHandler)
        assert handler in logging.getLogger("auto_qb").handlers
    finally:
        logging.getLogger("auto_qb").removeHandler(handler)
        handler.close()

    from auto_qb.infra.errors import AutoQbError

    monkeypatch.setattr(sys, "platform", "sunos")
    with pytest.raises(AutoQbError):
        setup_notify(NotifyConfig(enabled=True))


def test_setup_notify_force_hot_attach(monkeypatch):
    """通知热开启: 配置未启用时不带 force 返回 None, 带 force=True 挂载(UI 开关热开启, 会话级)"""
    monkeypatch.setattr(PlatformChannel, "_ensure_appid_registered", lambda self: notify_mod.WINDOWS_TOAST_APPID)
    monkeypatch.setattr(PlatformChannel, "_register_appid_registry", lambda shortcut: None)  # 防真写开始菜单
    disabled_cfg = NotifyConfig(enabled=False, min_level="WARNING", max_per_hour=5, dedup_window=0)
    assert setup_notify(disabled_cfg) is None
    handler = setup_notify(disabled_cfg, force=True)
    try:
        assert isinstance(handler, NotifyHandler)
        assert handler in logging.getLogger("auto_qb").handlers
    finally:
        logging.getLogger("auto_qb").removeHandler(handler)
        handler.close()


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


def test_notify_emit_exception_swallowed():
    """emit 内部异常(如 getMessage 抛错)不外抛(handleError 兜底)"""
    handler = NotifyHandler(
        NotifyConfig(enabled=True, min_level="WARNING", max_per_hour=100, dedup_window=0),
        PlatformChannel("linux"),
    )
    try:
        bad = logging.LogRecord("auto_qb.test", logging.WARNING, "p", 1, "msg", None, None)
        bad.getMessage = lambda: (_ for _ in ()).throw(RuntimeError("格式化炸了"))
        handler.emit(bad)  # 不应抛出
        handler.close()
    except Exception as e:
        pytest.fail(f"emit 异常外泄: {e}")


def test_notify_close_twice_safe():
    """close 幂等(重复调用/队列已空均不炸)"""
    handler = NotifyHandler(
        NotifyConfig(enabled=True, min_level="WARNING", max_per_hour=100, dedup_window=0),
        PlatformChannel("linux"),
    )
    handler.close()
    handler.close()


def test_notify_fatal_channel_error_swallowed(monkeypatch):
    """notify_fatal 渠道构造异常 -> 静默(不外抛)"""
    def boom():
        raise OSError("无 APPDATA")

    monkeypatch.setattr(notify_mod, "PlatformChannel", boom)
    notify_fatal("消息", NotifyConfig(enabled=True))


def test_notify_legacy_shortcut_cleanup(monkeypatch):
    """legacy lnk 清理: 存在的旧快捷方式被删除(文件操作经 monkeypatch, 不动真实开始菜单)

    APPDATA 必须**显式给定**: `_legacy_shortcut_paths()` 在 APPDATA 缺失时直接返回 `[]` ——
    不设的话路径清单为空、`os.path.exists` 根本不会被问到, `removed` 恒空、断言必失败。
    这是**环境依赖**(某些 CI/沙箱不设 APPDATA), 不是逻辑错误; 显式 setenv 后该用例也顺带
    真正覆盖了 `_legacy_shortcut_paths` 的路径拼接分支(此前在无 APPDATA 环境下等于空跑)。

    `winreg` 也要**注入替身**: `PlatformChannel("win32")` 构造时会 `import winreg`, 而 Linux/macOS
    **没有这个模块** —— `ModuleNotFoundError` 不属于 `_ensure_appid_registered` 捕获的 `OSError`,
    会直接外抛(2026-09-19 Linux CI 实测失败)。注入替身后本用例在**任何平台**都跑得到
    `_register_appid_registry` 的真实分支, 符合"平台相关测试不依赖运行环境"的约定。
    """
    class _StubWinreg:
        """`winreg` 替身: 键/值写入全部不落盘(测试不得动真实注册表)"""

        HKEY_CURRENT_USER = 1
        KEY_SET_VALUE = 2
        REG_SZ = 1

        class _Key:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        @staticmethod
        def CreateKeyEx(key, sub_key, *a, **kw):
            return _StubWinreg._Key()

        @staticmethod
        def SetValueEx(key, name, *a, **kw):
            return None

    monkeypatch.setitem(sys.modules, "winreg", _StubWinreg)
    removed = []
    monkeypatch.setenv("APPDATA", r"C:\Users\tester\AppData\Roaming")
    monkeypatch.setattr(notify_mod.os.path, "exists", lambda p: "AutoQB.lnk" in str(p) or "AutoQB.UI.lnk" in str(p))
    monkeypatch.setattr(notify_mod.os, "remove", lambda p: removed.append(p))
    channel = PlatformChannel("win32")
    assert any("AutoQB.lnk" in p for p in removed), removed
    assert channel._appid == notify_mod.WINDOWS_TOAST_APPID


def test_notify_real_send_blocked_under_pytest():
    """conftest 会话夹具: 测试期通知器命令被拦截(不启动真实进程), send 走失败分支返回 False

    回归点: 此前测试里写 PlatformChannel("linux") 只是"换了个后端", **并不阻止真实执行**
    notify-send —— 在装了通知器的机器(Linux 开发机/CI)上跑测试会真的弹出系统通知。
    """
    with pytest.raises(OSError):
        notify_mod.subprocess.run(["notify-send", "-a", "auto-qb", "标题", "正文"])
    assert PlatformChannel("linux").send("标题", "正文") is False


def test_notify_fatal_enabled_does_not_launch_process(sidefx_recorder):
    """通知**启用且全程不 mock** 走 `notify_fatal` 真实路径 ⇒ **一个进程都不启动**

    这是用户原始诉求("测试时会弹出系统通知框")的**最直接**回归点: 与
    `test_notify_real_send_blocked_under_pytest`(直接断言 `subprocess.run` 被拦)不同,
    这里**不 mock 任何东西** —— 真的构造 `PlatformChannel()`、真的走 `send()`,
    靠 `tests/conftest.py` 的会话夹具把命令拦在启动之前, 再用副作用记账器验证零进程启动。

    之所以要这条: 真凶是 `test_cli.py` 里 MagicMock 配置绕过 `notify_fatal` 守卫; 那条已单独 mock。
    本条守的是**第二层** —— 万一将来又有测试忘了 mock, 夹具仍能兜住, 不会真的弹框。
    """
    before = len(sidefx_recorder.records)
    notify_fatal("致命: 测试期不应弹出", NotifyConfig(enabled=True))  # 不 mock: 走真实发送路径
    launched = [r for r in sidefx_recorder.records[before:] if r[0] == "POPEN"]
    assert not launched, f"通知启用时竟启动了外部进程(会真弹系统通知): {launched}"
