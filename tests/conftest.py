"""pytest 全局夹具: 测试期禁止真实系统通知。

**背景(2026-09-18 实测)**: `notify.py` 的通知渠道在**后台线程真实执行外部命令** ——
win32 = PowerShell 调 WinRT toast / linux = `notify-send` / darwin = `osascript`。
测试里写 `PlatformChannel("linux")` 只是**换了个后端**, 并不等于"不发": 实测跑全量测试时
确实启动过 `notify-send` 进程(用 subprocess 探针抓到的)。在装了通知器的机器
(Linux 开发机 / CI)上, 那就是**真的弹出系统通知** —— 即"跑测试时弹出系统通知框"。

**本夹具的处置**: 会话级把"通知器可执行名"统一拦在 `subprocess.run` 之前 —— 进程不启动、
通知不弹出; 且 `PlatformChannel.send()` 仍走"发送失败"分支(返回 False, 只记 DEBUG),
与"机器上没装通知器"的表现完全一致, 调用方语义不变。

**不拦什么**:
- 通知命令的**构造**不拦 —— `PlatformChannel._build_windows/_build_linux/_build_darwin` 照常返回命令列表,
  `test_notify_channel_*` 的命令结构断言不受影响;
- 需要真实 `subprocess.run` 行为的用例(如 `test_notify_channel_send_failure`)自行 monkeypatch
  `subprocess.run`, 会自然覆盖本夹具;
- `node --check` 等**非通知器**子进程原样放行。
"""
import os
import subprocess

import pytest

# 通知器可执行名(小写、不含 .exe): 与 notify.PlatformChannel 的三个平台后端一一对应
NOTIFIER_EXECUTABLES = frozenset({"notify-send", "osascript", "powershell", "pwsh"})

_real_run = subprocess.run


def _guard_run(cmd, *args, **kwargs):
    """拦掉通知器命令(抛 OSError 等价于"机器上没装通知器"); 其余子进程原样交给真实 subprocess.run"""
    exe = ""
    if isinstance(cmd, (list, tuple)) and cmd:
        exe = os.path.basename(str(cmd[0])).lower()
        if exe.endswith(".exe"):
            exe = exe[:-4]
    if exe in NOTIFIER_EXECUTABLES:
        raise FileNotFoundError(2, "测试期禁止真实系统通知(conftest 拦截)", exe)
    return _real_run(cmd, *args, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def _no_real_system_notification():
    """会话级: 通知器命令一律不启动(详见模块 docstring)"""
    subprocess.run = _guard_run
    try:
        yield
    finally:
        subprocess.run = _real_run
