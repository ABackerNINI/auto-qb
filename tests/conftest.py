"""pytest 全局夹具: 测试期禁止**真实系统副作用**。

覆盖三件事, 都是会话级 autouse 夹具 —— 拦在"真实副作用入口"之前:
① 系统通知: 通知器进程不启动; ② AUMID 注册表键: 不落盘; ③ 全程记账: 越界副作用直接让本次运行失败。

## ① 真实系统通知 (2026-09-18 实测)

**背景**: `notify.py` 的通知渠道在**后台线程真实执行外部命令** ——
win32 = PowerShell 调 WinRT toast / linux = `notify-send` / darwin = `osascript`。
测试里写 `PlatformChannel("linux")` 只是**换了个后端**, 并不等于"不发": 实测跑全量测试时
确实启动过 `notify-send` 进程(用 subprocess 探针抓到的)。在装了通知器的机器
(Linux 开发机 / CI)上, 那就是**真的弹出系统通知** —— 即"跑测试时弹出系统通知框"。

**处置**: 会话级把"通知器可执行名"统一拦在 `subprocess.run` 之前 —— 进程不启动、
通知不弹出; 且 `PlatformChannel.send()` 仍走"发送失败"分支(返回 False, 只记 DEBUG),
与"机器上没装通知器"的表现完全一致, 调用方语义不变。

**不拦什么**:
- 通知命令的**构造**不拦 —— `PlatformChannel._build_windows/_build_linux/_build_darwin` 照常返回命令列表,
  `test_notify_channel_*` 的命令结构断言不受影响;
- 需要真实 `subprocess.run` 行为的用例(如 `test_notify_channel_send_failure`)自行 monkeypatch
  `subprocess.run`, 会自然覆盖本夹具;
- `node --check` 等**非通知器**子进程原样放行。

## ② AUMID 注册表键 (2026-09-18 副作用普查发现)

**背景**: `PlatformChannel("win32")` 构造时会调 `_ensure_appid_registered()` 真写
`HKCU\\Software\\Classes\\AppUserModelId\\AutoQB.UI`(通知来源显示名/图标)。
**它写完不清理** —— 每跑一次测试就在用户注册表里留一个持久键。与 `autostart` 的
`...\\CurrentVersion\\Run` 键不同: 后者由 `test_autostart_windows_registry` 在 `finally` 里
`disable()` 自清理(见 testing.md 的明文说明), 前者没有任何清理。

**处置**: 会话级把**只属于 AUMID 键**的写入变成空操作(`CreateKeyEx` 返回不落盘的替身、
`SetValueEx` 对它直接返回), 其余注册表写入**原样放行** —— 所以 `autostart` 的 Run 键
测试行为完全不变。让写入"静默成功"而不是抛异常是刻意的: `_ensure_appid_registered()`
只 catch `OSError` 并在异常时回退 `WINDOWS_TOAST_APPID_FALLBACK`, 抛异常会让
`channel._appid` 变成回退值、打乱既有断言。

**不拦什么**: 非 AUMID 键(如 `autostart` 的 Run 键)照常真实读写 —— 那是既有明文约定且自清理。

## ③ 副作用记账器 (2026-09-18 普查的临时探针固化而来)

**背景**: ①②都是"已经发现的"副作用。普查用的临时探针在 `%TEMP%` 里会随会话消失,
同类问题下次还得靠人肉发现。本文件把它固化成常驻守卫 —— `sidefx.py` 记账器全程记录五类
真实副作用, 收尾时按放行清单判定, **有越界项就让本次 pytest 失败**。

放行清单与判定策略见 [sidefx.py](sidefx.py) 模块 docstring; 策略本身有单测
(`tests/test_sidefx.py`), 改清单时同步。
"""
import os
import re
import subprocess

import pytest

import sidefx

# 通知器可执行名(小写、不含 .exe): 与 notify.PlatformChannel 的三个平台后端一一对应
NOTIFIER_EXECUTABLES = frozenset({"notify-send", "osascript", "powershell", "pwsh"})

# AUMID 键前缀: PlatformChannel("win32") 构造时会真写这个键(见模块 docstring ②)
AUMID_KEY_PREFIX = "Software\\Classes\\AppUserModelId\\"

_real_run = subprocess.run


def _guard_run(cmd, *args, **kwargs):
    """拦掉通知器命令(抛 OSError 等价于"机器上没装通知器"); 其余子进程原样交给真实 subprocess.run"""
    exe = ""
    if isinstance(cmd, (list, tuple)) and cmd:
        exe = os.path.basename(str(cmd[0])).lower().removesuffix(".exe")
    if exe in NOTIFIER_EXECUTABLES:
        raise FileNotFoundError(2, "测试期禁止真实系统通知(conftest 拦截)", exe)
    return _real_run(cmd, *args, **kwargs)


# AUMID 键的空操作替身由 sidefx 提供 —— 记账器据此识别"被守卫拦下的调用", 两个夹具谁先安装都不影响判定
_StubRegKey = sidefx.StubRegKey

# 并行(xdist)下各 worker 回传的台账原文(串行跑时恒为空 —— 那时台账在 sidefx.LAST_REPORT)
_WORKER_REPORTS = []

# 台账首行形如「副作用台账: 共 2036 条, 越界 0 条」
_SIDEFX_HEAD = re.compile(r"共 (\d+) 条, 越界 (\d+) 条")


def pytest_testnodedown(node, error):
    """xdist 钩子: 收各 worker 回传的副作用台账(串行跑时不会被调用; xdist 未装时本钩子不被注册)"""
    report = (getattr(node, "workeroutput", None) or {}).get("sidefx_report")
    if report:
        _WORKER_REPORTS.append(report)


def pytest_terminal_summary(terminalreporter):
    """把副作用台账打进收尾总结 —— 没有越界时守卫是静默的, 不打印就没人知道它在工作

    ❗并行(xdist)下每个 worker 各跑一个会话, 而**终端总结只在控制器上产出** ⇒ worker 的台账若不回传,
    「越界 0 条」这行在日常输出里会**静默消失**(拦截仍在: 越界时 worker 自己的会话夹具已让本次运行失败,
    见 `sidefx_recorder` —— 丢的只是**可见性**)。回传走 xdist 的 `workeroutput`:
    worker 侧写进 `config.workeroutput`, 控制器侧在 `pytest_testnodedown` 里从 `node.workeroutput` 收。
    串行跑时 `pytest_testnodedown` 不会被调用, 走下面的原路径。
    """
    if _WORKER_REPORTS:
        # 汇总成一行 —— 逐 worker 打 8 行会把收尾刷屏, 而这行的用处正是"扫一眼确认越界 0";
        # 但**只要有越界就把该 worker 的全文打出来**, 否则真出事时反而看不到细节。
        total = violations = 0
        offending = []
        for i, rep in enumerate(_WORKER_REPORTS, 1):
            m = _SIDEFX_HEAD.search(rep)
            if not m:
                continue
            total += int(m.group(1))
            bad = int(m.group(2))
            violations += bad
            if bad:
                offending.append((i, rep))
        terminalreporter.write_sep("=", "测试期真实系统副作用台账 (守卫见 tests/sidefx.py)")
        terminalreporter.write_line(f"副作用台账({len(_WORKER_REPORTS)} 个并行 worker 汇总): 共 {total} 条, 越界 {violations} 条")
        for i, rep in offending:
            terminalreporter.write_line(f"--- worker {i} 有越界 ---")
            for line in rep.splitlines():
                terminalreporter.write_line(line)
        return
    report = sidefx.LAST_REPORT
    if not report:
        return
    terminalreporter.write_sep("=", "测试期真实系统副作用台账 (守卫见 tests/sidefx.py)")
    for line in report.splitlines():
        terminalreporter.write_line(line)


@pytest.fixture(scope="session", autouse=True)
def sidefx_recorder(request):
    """会话级: 全程记录真实系统副作用; 收尾时如有越界项**让本次运行失败**(详见模块 docstring ③)

    测试可请求本夹具取用记账器(如断言"某个操作没有产生副作用")。
    """
    recorder = sidefx.SideFxRecorder()
    sidefx.SESSION = recorder
    recorder.install()
    try:
        yield recorder
    finally:
        recorder.uninstall()
        sidefx.SESSION = None
        sidefx.LAST_REPORT = recorder.report()  # 交给 pytest_terminal_summary 打印
        # 并行时把台账回传给控制器 —— 否则终端总结(只在控制器上产出)看不到它, 「越界 0 条」会静默消失
        workeroutput = getattr(request.config, "workeroutput", None)
        if workeroutput is not None:
            workeroutput["sidefx_report"] = sidefx.LAST_REPORT
        violations = recorder.violations
        if violations:
            raise AssertionError(
                f"测试期出现 {len(violations)} 条越界的真实系统副作用"
                "(放行清单见 tests/sidefx.py, 确认新出现的副作用是必须的再到那里登记):\n" + recorder.report()
            )


@pytest.fixture(scope="session", autouse=True)
def _no_real_system_notification():
    """会话级: 通知器命令一律不启动(详见模块 docstring ①)"""
    subprocess.run = _guard_run
    try:
        yield
    finally:
        subprocess.run = _real_run


@pytest.fixture(scope="session", autouse=True)
def _no_real_aumid_registry_write():
    """会话级: 只把 AUMID 键的写入变成空操作, 其余注册表写入放行(详见模块 docstring ②)"""
    try:
        import winreg
    except ImportError:  # 非 Windows: notify 不会走 win32 后端, 无需处理
        yield
        return

    real_create_key_ex = winreg.CreateKeyEx
    real_set_value_ex = winreg.SetValueEx

    def create_key_ex(key, sub_key, *args, **kwargs):
        if str(sub_key).startswith(AUMID_KEY_PREFIX):
            return _StubRegKey()
        return real_create_key_ex(key, sub_key, *args, **kwargs)

    def set_value_ex(key, name, *args, **kwargs):
        if isinstance(key, _StubRegKey):
            return None
        return real_set_value_ex(key, name, *args, **kwargs)

    winreg.CreateKeyEx = create_key_ex
    winreg.SetValueEx = set_value_ex
    try:
        yield
    finally:
        winreg.CreateKeyEx = real_create_key_ex
        winreg.SetValueEx = real_set_value_ex
