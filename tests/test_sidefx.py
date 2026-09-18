"""test_sidefx 测试计划: 测试期真实系统副作用的**记账与判定策略**(tests/sidefx.py)

**背景**: 2026-09-18 用户报"测试时会弹出系统通知框", 修完后做了一次全量副作用普查,
又挖出 AUMID 注册表键真写且不清理。普查用的探针在临时目录里会随会话消失, 于是把能力固化成
`tests/sidefx.py`(记账器 + 放行清单) + `tests/conftest.py` 的会话夹具(收尾有越界项就失败)。

## 测试计划(每个测试函数一条)
- test_sidefx_is_temp_path: 临时目录判定, 含 Windows `\\\\?\\` 长路径前缀(普查时 157 条假阳性的根因)
- test_sidefx_is_loopback: 回环地址判定(放行 127.* / ::1 / localhost, 拒绝 0.0.0.0 与局域网)
- test_sidefx_policy_allows_known_effects: 放行清单逐条 —— node 子进程 / autostart Run 键 / 临时目录删除与建链 / 回环监听
- test_sidefx_policy_flags_unknown_effects: 越界判定逐条 —— 通知器进程 / AUMID 键 / 其它值名 / 非临时目录删除与建链 / 非回环监听
- test_sidefx_recorder_installed_and_records: 会话夹具已安装且真在记账(删临时文件应留 FSDEL 记录)
- test_sidefx_launch_entry_points_wrapped: `os.startfile`/`webbrowser.open` 已接进记账器(只验证包装关系, 不真调用 —— 那会真弹窗口)
- test_sidefx_connect_entry_points_wrapped: `socket.connect`/`create_connection` 已接进记账器(只验证包装关系, 不真连外网)
- test_sidefx_recorder_install_uninstall_restores: 装卸安全 —— uninstall 还原各入口, 不污染后续
- test_sidefx_aumid_write_is_stubbed: AUMID 键写入被拦成 StubRegKey; 且它**不在**放行清单(真落盘即越界)
- test_sidefx_report_shape: 台账报告可读(总数/越界数/分类计数)
"""
import os
import tempfile

import pytest

import sidefx


def test_sidefx_is_temp_path(tmp_path):
    """临时目录判定: 含 Windows 扩展长度前缀 `\\\\?\\`(abspath 不剥它, 直接比前缀会误判)"""
    assert sidefx.is_temp_path(tempfile.gettempdir())
    assert sidefx.is_temp_path(tmp_path), "pytest 的 tmp_path 也在临时目录下"
    assert sidefx.is_temp_path(os.path.join(tempfile.gettempdir(), "x", "y"))
    # 关键回归点: 普查时 157 条"仓库外删除"其实是这个前缀导致的假阳性
    assert sidefx.is_temp_path("\\\\?\\" + tempfile.gettempdir())
    assert not sidefx.is_temp_path("C:/Windows/System32")
    assert not sidefx.is_temp_path("/etc/passwd")


def test_sidefx_is_loopback():
    """回环判定: 测试只允许监听本机"""
    assert sidefx.is_loopback(("127.0.0.1", 0))
    assert sidefx.is_loopback(("127.0.0.1", 8080))
    assert sidefx.is_loopback(("::1", 0))
    assert sidefx.is_loopback(("localhost", 9000))
    assert not sidefx.is_loopback(("0.0.0.0", 8080)), "监听所有网卡 = 对外暴露, 不放行"
    assert not sidefx.is_loopback(("192.168.1.1", 80))


def test_sidefx_policy_allows_known_effects(tmp_path):
    """放行清单逐条(与 2026-09-18 普查实测一一对应)"""
    assert not sidefx.is_violation(("POPEN", ["node", "--check", "app.js"])), "前端静态守阵的 node 语法校验"
    assert not sidefx.is_violation(("REG", r"Software\Microsoft\Windows\CurrentVersion\Run")), "autostart(自清理)"
    assert not sidefx.is_violation(("REGVAL", "auto-qb")), "autostart 自己那个值"
    assert not sidefx.is_violation(("FSDEL", tmp_path / "x")), "临时目录内删除"
    assert not sidefx.is_violation(("SYMLINK", tmp_path / "l")), "临时目录内建链"
    assert not sidefx.is_violation(("BIND", ("127.0.0.1", 0))), "回环监听"
    assert not sidefx.is_violation(("CONNECT", ("127.0.0.1", 8080))), "连本地假服务"


def test_sidefx_policy_flags_unknown_effects():
    """越界判定逐条: 放行清单外的真实副作用必须被抓出来"""
    assert sidefx.is_violation(("POPEN", ["notify-send", "-a", "auto-qb", "t", "b"]))
    assert sidefx.is_violation(("REG", r"Software\Classes\AppUserModelId\AutoQB.UI")), "AUMID 键不在放行清单"
    assert sidefx.is_violation(("REGVAL", "SomeOtherApp"))
    assert sidefx.is_violation(("FSDEL", "C:/Windows/System32/drivers/etc/hosts"))
    assert sidefx.is_violation(("SYMLINK", "C:/Windows/escape"))
    assert sidefx.is_violation(("BIND", ("0.0.0.0", 8080)))
    assert sidefx.is_violation(("CONNECT", ("1.2.3.4", 443))), "连外网"
    assert sidefx.is_violation(("CONNECT", ("tracker.example.com", 80))), "连外网(域名)"
    # LAUNCH: 不走 subprocess, 但同样会弹窗口 —— 一律越界, 没有"测试期可以忍"的情形
    assert sidefx.is_violation(("LAUNCH", "C:/Users/me/Downloads")), "os.startfile 开资源管理器"
    assert sidefx.is_violation(("LAUNCH", "http://localhost:12200")), "webbrowser.open 开浏览器"


def test_sidefx_recorder_installed_and_records(sidefx_recorder, tmp_path):
    """会话夹具已安装且真的在记账: 删一个临时文件应留下 FSDEL 记录(且不判越界)"""
    assert sidefx_recorder.installed
    assert sidefx.SESSION is sidefx_recorder, "模块级单例应指向会话记账器, 便于测试取用"
    target = tmp_path / "x.txt"
    target.write_text("x", encoding="utf-8")
    before = len(sidefx_recorder.records)
    os.remove(target)
    new = sidefx_recorder.records[before:]
    assert any(kind == "FSDEL" and str(detail).endswith("x.txt") for kind, detail in new), f"未记录到删除: {new}"
    assert not any(kind == "FSDEL" for kind, _ in sidefx_recorder.violations), "临时目录内删除不应判越界"


def test_sidefx_launch_entry_points_wrapped():
    """LAUNCH 类入口确实接进了记账器 —— **只验证包装关系, 不真调用**

    真调 `os.startfile`/`webbrowser.open`/`os.system` 就是真弹资源管理器/浏览器/起 shell,
    那本身就是越界副作用(会让会话夹具报错)。所以这里只装一层记账器、看入口是否已被包装。
    """
    import webbrowser

    original_browser_open = webbrowser.open
    original_startfile = getattr(os, "startfile", None)
    recorder = sidefx.SideFxRecorder()
    recorder.install()
    try:
        assert webbrowser.open is not original_browser_open, "webbrowser.open 应被包装"
        if original_startfile is not None:  # 非 Windows 上 os.startfile 不存在, 跳过
            assert os.startfile is not original_startfile, "os.startfile 应被包装"
    finally:
        recorder.uninstall()
    assert webbrowser.open is original_browser_open, "uninstall 必须还原"


def test_sidefx_connect_entry_points_wrapped():
    """出站连接入口已接进记账器 —— 同样**只验证包装关系, 不真连外网**

    真连一次外网既是越界副作用、又慢且不稳定; 这里只确认入口已被包装。
    """
    import socket

    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    recorder = sidefx.SideFxRecorder()
    recorder.install()
    try:
        assert socket.socket.connect is not original_connect, "socket.connect 应被包装"
        assert socket.create_connection is not original_create_connection, "create_connection 应被包装"
    finally:
        recorder.uninstall()
    assert socket.socket.connect is original_connect, "uninstall 必须还原"


def test_sidefx_recorder_install_uninstall_restores():
    """装卸安全: uninstall 后各入口还原(会话记账器之外再装一层也不留痕)"""
    original_remove = os.remove
    recorder = sidefx.SideFxRecorder()
    recorder.install()
    try:
        assert os.remove is not original_remove, "安装后入口应被包装"
    finally:
        recorder.uninstall()
    assert os.remove is original_remove, "uninstall 必须还原"
    assert not recorder.installed


def test_sidefx_aumid_write_is_stubbed():
    """AUMID 键写入被 conftest 拦成 StubRegKey(不落盘); 且它**不在**放行清单

    回归点: 普查发现 `PlatformChannel("win32")` 会真写 HKCU 的 AUMID 键且写完不清理。
    **本测试刻意不构造 PlatformChannel** —— 那会顺带跑 `.lnk` 清理循环(可能真删开始菜单
    里的旧快捷方式); 直接调 `CreateKeyEx` 验证守卫即可。
    """
    try:
        import winreg
    except ImportError:
        pytest.skip("非 Windows: 无 winreg, AUMID 守卫不适用")
    aumid_key = "Software\\Classes\\AppUserModelId\\AutoQB.UI"
    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, aumid_key, 0, winreg.KEY_SET_VALUE)
    assert isinstance(key, sidefx.StubRegKey), "AUMID 键应被拦成不落盘的替身"
    # 反向断言: 放行清单里没有 AUMID —— 守卫一旦失效、真的写下去, 记账器必须判越界
    assert sidefx.is_violation(("REG", aumid_key))


def test_sidefx_report_shape():
    """台账报告可读: 含总数 / 越界数 / 分类计数"""
    recorder = sidefx.SideFxRecorder()
    recorder.records = [
        ("FSDEL", tempfile.gettempdir() + "/a"), ("BIND", ("127.0.0.1", 0)),
        ("REG", r"Software\Classes\AppUserModelId\AutoQB.UI")
    ]
    text = recorder.report()
    assert "共 3 条" in text and "越界 1 条" in text
    assert "FSDEL" in text and "BIND" in text
    assert "!!" in text, "越界项要逐条列出来"
