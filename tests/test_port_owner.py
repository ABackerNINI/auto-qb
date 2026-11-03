"""test_port_owner 测试计划: 三平台端口占用者探针(计划 26-11-03-0930 §4.4)

## 测试计划
- test_linux_ss_hit_returns_owner_with_proc_cmdline: Linux `ss -ltnp` 命中 -> found, 命令行由 /proc 直读
- test_linux_ss_absent: ss 成功且无该端口 -> absent(不退化成"未识别")
- test_linux_ss_hit_without_pid_unavailable: ss 命中端口但无 pid(权限不足)-> unavailable, 不谎报 absent
- test_linux_ss_failure_falls_back_to_lsof: ss 命令缺失 -> 回退 lsof 并 found
- test_linux_lsof_absent_exit1: lsof 退出码 1 且无输出 -> absent
- test_linux_lsof_empty_success_absent: lsof 退出码 0 且无输出 -> absent
- test_linux_lsof_nonzero_exit_unavailable: lsof 非 0/1 退出码 -> unavailable
- test_linux_lsof_unparsable_unavailable: lsof 有输出但解析不出 -> unavailable
- test_linux_ss_and_lsof_missing_unavailable: 两者皆缺 -> unavailable, 不抛出
- test_linux_proc_cmdline_reader_replaces_nul: /proc/<pid>/cmdline 的 NUL 分隔转空格
- test_linux_proc_cmdline_reader_failure_returns_empty: /proc 读失败 -> 空命令行(进程名仍可用)
- test_clean_cmdline_strips_newlines_and_truncates: 命令行换行压空格 + 截断 160 字符
- test_windows_single_powershell_hit: Windows 一次 PowerShell 命中 -> found(不沿用 scripts 的两次调用)
- test_windows_missing_cmdline_field: 输出缺第三段 -> 命令行空串, 仍 found
- test_windows_no_listener_absent: 命令成功且无输出 -> absent
- test_windows_nonzero_exit_unavailable: PowerShell 非零退出 -> unavailable
- test_windows_timeout_unavailable: PowerShell 超时 -> unavailable
- test_windows_unparsable_output_unavailable: PowerShell 输出不可解析 -> unavailable
- test_macos_lsof_hit_then_ps_fails_keeps_found: macOS lsof 命中 + ps 失败 -> found, 命令行空串
- test_macos_lsof_hit_with_ps_cmdline: macOS lsof 命中 + ps 成功 -> 命令行来自 ps
- test_macos_lsof_missing_unavailable: macOS lsof 缺失 -> unavailable
- test_unknown_platform_unavailable: 非三平台 -> unavailable, 不 spawn 任何命令
- test_probe_failures_never_raise: 三平台任意异常 -> 调用方拿到 unavailable(统一"异常不影响调用方")
- test_budget_caps_step_timeouts: 预算 1.5s 常量与逐步 timeout 截断(总硬预算机械保证)
- test_budget_exhausted_skips_commands: 预算耗尽 -> 不 spawn, 直接 unavailable
"""
from __future__ import annotations

import subprocess
from unittest import mock

import pytest

from auto_qb.infra import port_owner

SS_OUTPUT = (
    "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
    'LISTEN 0      4096   127.0.0.1:9090     0.0.0.0:*    users:(("nginx",pid=999,fd=4))\n'
    'LISTEN 0      4096   127.0.0.1:8080     0.0.0.0:*    users:(("python3",pid=12345,fd=3))\n'
)
SS_OUTPUT_NO_PID = (
    "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
    "LISTEN 0      4096   127.0.0.1:8080     0.0.0.0:*\n"
)
LSOF_OUTPUT = (
    "COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
    "nginx     999 user    4u  IPv4  54321      0t0  TCP 127.0.0.1:9090 (LISTEN)\n"
    "python3 23456 user    3u  IPv4  12345      0t0  TCP 127.0.0.1:8080 (LISTEN)\n"
)


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["cmd"], returncode, stdout=stdout, stderr="")


def _platform(monkeypatch, name: str) -> None:
    monkeypatch.setattr(port_owner, "is_windows", lambda: name == "windows")
    monkeypatch.setattr(port_owner, "is_linux", lambda: name == "linux")
    monkeypatch.setattr(port_owner, "is_mac", lambda: name == "mac")


def _install_run(monkeypatch, handler):
    """把 subprocess.run 换成按调用序号作答的假实现, 返回调用记录 [(cmd, kwargs), ...]"""
    calls: list = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return handler(cmd, kwargs, len(calls) - 1)

    monkeypatch.setattr(port_owner.subprocess, "run", fake_run)
    return calls


def test_linux_ss_hit_returns_owner_with_proc_cmdline(monkeypatch):
    _platform(monkeypatch, "linux")
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(SS_OUTPUT))
    monkeypatch.setattr(port_owner, "_read_proc_cmdline", lambda pid: f"python3 -m auto_qb --pid={pid}")

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_FOUND
    assert probe.owner == port_owner.PortOwner(12345, "python3", "python3 -m auto_qb --pid=12345")
    assert [cmd[0] for cmd, _ in calls] == ["ss"]
    assert calls[0][0] == ["ss", "-ltnp"], "argv 必须精确等于 ss -ltnp(改旗标=探针行为变了)"
    assert calls[0][1]["timeout"] <= port_owner.STEP_TIMEOUT_S


def test_linux_ss_absent(monkeypatch):
    _platform(monkeypatch, "linux")
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("State  Recv-Q\n"))

    probe = port_owner.describe_port_owner("127.0.0.1", 9090)

    assert probe.state == port_owner.STATE_ABSENT
    assert [cmd[0] for cmd, _ in calls] == ["ss"]


def test_linux_ss_hit_without_pid_unavailable(monkeypatch):
    _platform(monkeypatch, "linux")
    _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(SS_OUTPUT_NO_PID))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert "pid" in probe.reason


def test_linux_ss_failure_falls_back_to_lsof(monkeypatch):
    _platform(monkeypatch, "linux")

    def handler(cmd, kwargs, index):
        if index == 0:
            raise FileNotFoundError(2, "no ss", "ss")
        return _cp(LSOF_OUTPUT)

    calls = _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_FOUND
    assert probe.owner == port_owner.PortOwner(23456, "python3", "")
    assert [cmd[0] for cmd, _ in calls] == ["ss", "lsof"]


def test_linux_lsof_absent_exit1(monkeypatch):
    _platform(monkeypatch, "linux")
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("", returncode=1))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_ABSENT
    assert [cmd[0] for cmd, _ in calls] == ["ss", "lsof"]


def test_linux_lsof_empty_success_absent(monkeypatch):
    _platform(monkeypatch, "linux")

    def handler(cmd, kwargs, index):
        return _cp("", returncode=1) if index == 0 else _cp("")

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_ABSENT


def test_linux_lsof_nonzero_exit_unavailable(monkeypatch):
    _platform(monkeypatch, "linux")

    def handler(cmd, kwargs, index):
        return _cp("", returncode=1) if index == 0 else _cp("lsof: error", returncode=2)

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert "2" in probe.reason


def test_linux_lsof_unparsable_unavailable(monkeypatch):
    _platform(monkeypatch, "linux")

    def handler(cmd, kwargs, index):
        return _cp("", returncode=1) if index == 0 else _cp("garbage output\n")

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert "不可解析" in probe.reason


def test_linux_ss_and_lsof_missing_unavailable(monkeypatch):
    _platform(monkeypatch, "linux")

    def handler(cmd, kwargs, index):
        raise FileNotFoundError(2, f"no {cmd[0]}", cmd[0])

    calls = _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert [cmd[0] for cmd, _ in calls] == ["ss", "lsof"]


def test_linux_proc_cmdline_reader_replaces_nul(monkeypatch):
    fake_open = mock.mock_open(read_data=b"python3\x00-m\x00auto_qb\x00")
    monkeypatch.setattr(port_owner, "open", fake_open, raising=False)

    assert port_owner._read_proc_cmdline(777) == "python3 -m auto_qb"


def test_linux_proc_cmdline_reader_failure_returns_empty(monkeypatch):
    def boom(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(port_owner, "open", boom, raising=False)

    assert port_owner._read_proc_cmdline(777) == ""


def test_clean_cmdline_strips_newlines_and_truncates():
    raw = "a\nb\r\n" + "x" * 300

    cleaned = port_owner._clean_cmdline(raw)

    assert "\n" not in cleaned and "\r" not in cleaned
    assert cleaned.startswith("a b ")
    assert len(cleaned) <= port_owner.CMDLINE_MAX_LEN
    assert port_owner.CMDLINE_MAX_LEN == 160


def test_windows_single_powershell_hit(monkeypatch):
    _platform(monkeypatch, "windows")
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("4242|python.exe|python.exe -m auto_qb\n"))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_FOUND
    assert probe.owner == port_owner.PortOwner(4242, "python.exe", "python.exe -m auto_qb")
    assert len(calls) == 1, "Windows 必须一次 PowerShell 合并查询, 不得两次调用"
    cmd, kwargs = calls[0]
    assert cmd[0] == "powershell" and "-NoProfile" in cmd and "-NonInteractive" in cmd
    script = cmd[-1]
    assert "Get-NetTCPConnection" in script and "Get-CimInstance" in script
    assert kwargs["timeout"] <= port_owner.WINDOWS_STEP_TIMEOUT_S


def test_windows_missing_cmdline_field(monkeypatch):
    _platform(monkeypatch, "windows")
    _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("4242|python.exe"))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_FOUND
    assert probe.owner == port_owner.PortOwner(4242, "python.exe", "")


def test_windows_no_listener_absent(monkeypatch):
    _platform(monkeypatch, "windows")
    _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(""))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_ABSENT


def test_windows_nonzero_exit_unavailable(monkeypatch):
    _platform(monkeypatch, "windows")
    _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("", returncode=1))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert "1" in probe.reason


def test_windows_timeout_unavailable(monkeypatch):
    _platform(monkeypatch, "windows")

    def handler(cmd, kwargs, index):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert "超时" in probe.reason


def test_windows_unparsable_output_unavailable(monkeypatch):
    _platform(monkeypatch, "windows")
    _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("not-a-record\n"))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert "不可解析" in probe.reason


def test_macos_lsof_hit_then_ps_fails_keeps_found(monkeypatch):
    _platform(monkeypatch, "mac")

    def handler(cmd, kwargs, index):
        if index == 0:
            return _cp(LSOF_OUTPUT)
        raise FileNotFoundError(2, "no ps", "ps")

    calls = _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_FOUND
    assert probe.owner == port_owner.PortOwner(23456, "python3", "")
    assert [cmd[0] for cmd, _ in calls] == ["lsof", "ps"]


def test_macos_lsof_hit_with_ps_cmdline(monkeypatch):
    _platform(monkeypatch, "mac")

    def handler(cmd, kwargs, index):
        return _cp(LSOF_OUTPUT) if index == 0 else _cp("python3 -m auto_qb --server\n")

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_FOUND
    assert probe.owner == port_owner.PortOwner(23456, "python3", "python3 -m auto_qb --server")


def test_macos_lsof_missing_unavailable(monkeypatch):
    _platform(monkeypatch, "mac")

    def handler(cmd, kwargs, index):
        raise FileNotFoundError(2, "no lsof", "lsof")

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE


def test_unknown_platform_unavailable(monkeypatch):
    _platform(monkeypatch, "other")
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(""))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert calls == []


@pytest.mark.parametrize("platform", ["linux", "mac", "windows"])
def test_probe_failures_never_raise(monkeypatch, platform):
    _platform(monkeypatch, platform)

    def handler(cmd, kwargs, index):
        raise RuntimeError("boom")

    _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert isinstance(probe, port_owner.PortProbe)
    assert probe.state == port_owner.STATE_UNAVAILABLE


def test_budget_caps_step_timeouts(monkeypatch):
    _platform(monkeypatch, "linux")

    def handler(cmd, kwargs, index):
        raise FileNotFoundError(2, f"no {cmd[0]}", cmd[0])

    calls = _install_run(monkeypatch, handler)

    probe = port_owner.describe_port_owner("127.0.0.1", 8080, budget=0.3)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert all(kwargs["timeout"] <= 0.3 for _, kwargs in calls)
    assert port_owner.TOTAL_BUDGET_S == 1.5
    assert port_owner.STEP_TIMEOUT_S == 0.5
    assert port_owner.WINDOWS_STEP_TIMEOUT_S == 1.0


def test_budget_exhausted_skips_commands(monkeypatch):
    _platform(monkeypatch, "linux")
    ticks = iter([100.0, 101.6, 101.7])
    monkeypatch.setattr(port_owner.time, "monotonic", lambda: next(ticks))
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(""))

    probe = port_owner.describe_port_owner("127.0.0.1", 8080)

    assert probe.state == port_owner.STATE_UNAVAILABLE
    assert calls == []
