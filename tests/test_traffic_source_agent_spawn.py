"""test_traffic_source_agent_spawn 测试计划: 全局流量监视器联动单点(探测 / 缺席拉起 / 状态, 计划 26-10-17-0339 S16)

## 测试计划(每个测试函数一条)
- test_resolve_launch_target_order: 解析序 tool_exe(存在)优先 -> tool_dir 里启动器 -> 都没有 = None
- test_ensure_running_returns_endpoint_when_reachable: 探活成功直接返回端点, 不触发拉起(别的实例已拉起, D14)
- test_ensure_running_launches_then_backs_off: 缺席触发一次拉起; 首次引导窗口 120s 内不重复拉;
  窗口耗尽记失败并固定 30s 退避; 退避耗尽再拉起改用常态窗口 10s
- test_ensure_running_reports_not_installed: 解析不到目标 -> 不进拉起, 记「未安装」
- test_launch_tool_builds_platform_command: 启动器 -> 平台命令(detached, 零参数); 可执行文件 ->
  直执行; Windows `cmd.exe /c` + CREATE_NO_WINDOW / POSIX `/bin/sh` + 新会话
- test_launcher_prefers_pythonw: 工具侧启动器优先 pythonw.exe(去黑框第二道保险), 且保留回退
- test_resolve_claim_target_finds_launcher / _tool_exe_dir_priority / _missing_returns_none
  (D4): claim 入口 = 安装内第二启动器, tool_exe 显式优先 -> tool_dir/默认, 都没有 -> None
- test_run_claim_ok_and_refusal / _timeout_and_spawn_failure (D5): 有界前台跑 claim
  启动器; 退出码 0 -> ok + 人话输出原样; 非 0 -> 拒绝; 超时/起不来 -> ok=False + 原因
- test_status_includes_claim_note (D7): 状态区载荷带 claim_note(工具侧书写, auto-qb 只读展示)

P1-T1.3 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_ensure_running_launch_oserror_backs_off: 拉起本身失败(OSError)-> 记原因 + 固定 30s
  退避 + 本轮不重试; 失败不计入 _launched_once(下轮仍按首次引导窗口)
- test_request_relaunch_clears_backoff_and_failure: 手动重试清等待窗口/退避/失败记忆 ->
  下一轮立刻重新拉起
- test_resolve_claim_target_missing_returns_none
- test_resolve_claim_target_tool_exe_dir_priority
- test_run_claim_timeout_and_spawn_failure
- test_run_foreground_real_execution_with_allowed_binary

W7(R31) S5 补测(变异审计真洞守阵, 2026-11-01; 分类与位点见 tmp-analysis/w7-r31/classify.md) ——
平台支一律**强制进支**钉面(is_windows 打桩)—— WSL 池里 is_windows() 恒 False, Windows 支
变异靠强制进支让守阵在任何环境咬合(平台内断言), 不依赖 WSL 端到端:
- test_ensure_running_success_then_failure_guards: 成功后等待窗归零(er_8/9 状态机崩溃/假失败)
- test_ensure_running_not_installed_backoff: 未安装分支精确文案/退避窗/全新 agent error 空串
  (er_22/23/24/25, init_7/8/9)
- test_launch_window_exhaustion_state_and_logs: 窗口耗尽 INFO/WARNING 逐字 + 退避三态边界
  (er_10/16/41, status_52/60/61)
- test_fresh_agent_success_has_no_fake_recovery_log: 首次成功无假日志(init_13)
- test_error_memory_recovery_semantics: 恢复恰一条 INFO 逐字 + 记忆清空(_clear_error_1/3)
- test_ensure_running_launch_oserror_warning_exact: 拉起 OSError WARNING 逐字(er_33)
- test_run_claim_platform_command_and_contract: claim 平台命令两支逐位 + 回执契约(run_claim_2/3/4/
  6/8/9/29/35/36/46)
- test_resolve_launch_target_labels_and_branch_pinned: 解析标签逐字 + Windows 支(rlt_20/25/26/47/52)
"""

import ast

import builtins

import json

import logging

import os

import re

import shutil

import subprocess

from pathlib import Path

from types import SimpleNamespace

import pytest

from auto_qb.core.traffic_source import agent

from auto_qb.infra.utils import is_windows

from auto_qb.webui import tool_client

from helpers import capture_logs, write_credential_file, write_endpoint_pointer

from traffic_source_agent_support import (
    _LAUNCHER,
    _REPO_ROOT,
    _conf,
    _down,
    probe_env,
)


def test_resolve_launch_target_order(tmp_path):
    """tool_exe(存在)优先 -> tool_dir 里启动器 -> 都没有 = None"""
    # 3. tool_dir 留空 -> 兜底仓库内默认目录(真启动器存在)
    t0 = agent.resolve_launch_target(_conf())
    assert t0 is not None and t0.is_exe is False and os.path.basename(t0.path) == _LAUNCHER

    # 2. tool_dir 指定临时目录里的启动器
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")
    t1 = agent.resolve_launch_target(_conf(tool_dir=str(tmp_path)))
    assert t1 is not None and t1.is_exe is False
    assert t1.path == os.path.join(str(tmp_path), _LAUNCHER)

    # 1. tool_exe 存在 -> 直接执行(优先于启动器)
    exe = tmp_path / "gtm-exe"
    exe.write_text("", encoding="utf-8")
    t2 = agent.resolve_launch_target(_conf(tool_dir=str(tmp_path), tool_exe=str(exe)))
    assert t2 is not None and t2.is_exe is True
    assert t2.path == os.path.abspath(str(exe))

    # tool_exe 指向不存在的文件 -> 落回 tool_dir 启动器
    t3 = agent.resolve_launch_target(_conf(tool_dir=str(tmp_path), tool_exe=str(tmp_path / "nope")))
    assert t3 is not None and t3.is_exe is False

    # 3'. 两者都解析不到 -> None(未安装)
    empty = tmp_path / "empty"
    empty.mkdir()
    assert agent.resolve_launch_target(_conf(tool_dir=str(empty))) is None


def test_ensure_running_returns_endpoint_when_reachable(tmp_path, monkeypatch, probe_env):
    """探活成功直接返回端点, 不触发拉起(别的实例已拉起, D14)"""
    _calls, set_tool = probe_env
    set_tool()
    launches = []
    monkeypatch.setattr(agent, "launch_tool", lambda target: launches.append(target))

    a = agent.TrafficSourceAgent()
    ep = a.ensure_running(_conf())
    assert ep is not None and ep.base_url == "http://127.0.0.1:8099"
    assert launches == []
    assert a.status(_conf())["state"] == "ready"


def test_ensure_running_launches_then_backs_off(tmp_path, monkeypatch):
    """缺席触发一次拉起; 窗口内不重复拉; 窗口耗尽记失败并退避; 退避后改用常态窗口"""
    monkeypatch.setattr(tool_client, "call_tool", _down)
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")
    launches = []
    monkeypatch.setattr(agent, "launch_tool", lambda target: launches.append(target))

    clock = [1000.0]
    a = agent.TrafficSourceAgent(clock=lambda: clock[0])
    conf = _conf(tool_dir=str(tmp_path))

    # 第 1 轮: 缺席 -> 拉起一次, 首次引导窗口 120s
    assert a.ensure_running(conf) is None
    assert len(launches) == 1
    st = a.status(conf)
    assert st["state"] == "launching"
    assert st["retry_s"] == pytest.approx(agent.FIRST_BOOT_WINDOW_S)

    # 窗口内: 不重复拉
    clock[0] = 1000.0 + 60.0
    assert a.ensure_running(conf) is None
    assert len(launches) == 1

    # 窗口耗尽: 记拉起失败 + 固定 30s 退避, 本轮仍不拉起
    clock[0] = 1000.0 + agent.FIRST_BOOT_WINDOW_S + 1.0
    assert a.ensure_running(conf) is None
    assert len(launches) == 1
    st = a.status(conf)
    assert st["state"] == "launch_failed"
    assert "未探活成功" in st["error"]
    assert st["retry_s"] == pytest.approx(agent.RELAUNCH_BACKOFF_S)

    # 退避中: 仍不拉起
    clock[0] = 1000.0 + agent.FIRST_BOOT_WINDOW_S + 10.0
    assert a.ensure_running(conf) is None
    assert len(launches) == 1

    # 退避耗尽: 再拉起, 首次引导已过 -> 常态窗口 10s
    clock[0] = 1000.0 + agent.FIRST_BOOT_WINDOW_S + agent.RELAUNCH_BACKOFF_S + 1.0
    assert a.ensure_running(conf) is None
    assert len(launches) == 2
    st = a.status(conf)
    assert st["state"] == "launching"
    assert st["retry_s"] == pytest.approx(agent.STEADY_WINDOW_S)


def test_ensure_running_reports_not_installed(tmp_path, monkeypatch):
    """解析不到目标 -> 不进拉起, 记「未安装」"""
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    launches = []
    monkeypatch.setattr(agent, "launch_tool", lambda target: launches.append(target))

    empty = tmp_path / "empty"
    empty.mkdir()
    a = agent.TrafficSourceAgent()
    assert a.ensure_running(_conf(tool_dir=str(empty))) is None
    assert launches == []
    st = a.status(_conf(tool_dir=str(empty)))
    assert st["state"] == "not_installed"
    assert "未安装" in st["error"]


def test_launch_tool_builds_platform_command(tmp_path, monkeypatch):
    """启动器 -> 平台命令(detached); 可执行文件 -> 直执行; 不传任何参数"""
    calls = []

    class _FakePopen:
        def __init__(self, args, **kwargs):
            calls.append((list(args), dict(kwargs)))

    fake = SimpleNamespace(
        DEVNULL="DEVNULL",
        Popen=_FakePopen,
        DETACHED_PROCESS=0x00000008,
        CREATE_NO_WINDOW=0x08000000,
    )
    monkeypatch.setattr(agent, "subprocess", fake)

    launcher = str(tmp_path / _LAUNCHER)
    exe = str(tmp_path / "gtm-exe")

    # Windows 支: cmd.exe /c 启动器 + CREATE_NO_WINDOW(不弹控制台窗口)
    monkeypatch.setattr(agent, "is_windows", lambda: True)
    agent.launch_tool(agent.LaunchTarget(launcher, False, "启动器"))
    args, kw = calls[-1]
    assert args == ["cmd.exe", "/c", launcher]
    assert kw["creationflags"] == 0x08000000
    # 回归哨(26-10-17-1737 S5): DETACHED_PROCESS 会让 console 子进程重建可见控制台 -> 黑框
    assert kw["creationflags"] != 0x00000008
    assert kw["cwd"] == str(tmp_path)
    assert kw["stdin"] == "DEVNULL" and kw["stdout"] == "DEVNULL" and kw["stderr"] == "DEVNULL"
    assert kw["close_fds"] is True

    # POSIX 支: /bin/sh 启动器 + 新会话
    monkeypatch.setattr(agent, "is_windows", lambda: False)
    agent.launch_tool(agent.LaunchTarget(launcher, False, "启动器"))
    args, kw = calls[-1]
    assert args == ["/bin/sh", launcher]
    assert kw["start_new_session"] is True

    # 可执行文件: 不经 shell 前缀, 直接执行
    agent.launch_tool(agent.LaunchTarget(exe, True, "可执行文件"))
    args, _kw = calls[-1]
    assert args == [exe]


def test_launcher_prefers_pythonw():
    """工具侧启动器优先 pythonw.exe(去黑框第二道保险), python.exe / uv 逐级回退

    auto-qb 侧 CREATE_NO_WINDOW 只覆盖「由 auto-qb 拉起」这条路; 双击启动器与开机自启
    不经过它 —— 那些路径靠启动器自己选 GUI 子系统的 pythonw。回退必须留着: 有的 venv
    没建 pythonw(非 Windows 打包 / 精简安装), 直接硬要 pythonw 会让工具起不来。
    """
    script = (_REPO_ROOT / "tools" / "global-traffic-monitor" / "launch.cmd").read_text(encoding="utf-8")
    i_w = script.index(r".venv\Scripts\pythonw.exe")
    i_c = script.index(r".venv\Scripts\python.exe")
    i_uv = script.index("uv run")
    assert i_w < i_c < i_uv, "启动器次序必须是 pythonw -> python -> uv"
    # 起法仍是启动器独有的知识(D19), 三类回退跑同一条命令
    assert script.count("-m gtm run --autostart") == 2


#: 本平台对应的 claim 启动器文件名(与安装目录里的文件同名同源, D4)
_CLAIM_LAUNCHER = agent.CLAIM_LAUNCHER_WINDOWS if is_windows() else agent.CLAIM_LAUNCHER_POSIX


def _proc(returncode: int, stdout: str = ""):
    """subprocess.CompletedProcess 替身(run_claim 只读 returncode/stdout)"""
    return SimpleNamespace(returncode=returncode, stdout=stdout)


def test_resolve_claim_target_finds_launcher(tmp_path):
    """tool_dir 里的 claim 启动器 -> ClaimTarget(路径即入口, label 点名文件名)"""
    tool_dir = tmp_path / "inst"
    tool_dir.mkdir()
    (tool_dir / _CLAIM_LAUNCHER).write_text("rem\n", encoding="utf-8")
    target = agent.resolve_claim_target(_conf(tool_dir=str(tool_dir)))
    assert target is not None
    assert target.path == str(tool_dir / _CLAIM_LAUNCHER)
    assert _CLAIM_LAUNCHER in target.label


def test_resolve_claim_target_tool_exe_dir_priority(tmp_path):
    """tool_exe 显式优先(编译态): claim 启动器与 exe 同目录, 优先于 tool_dir"""
    exe_dir = tmp_path / "dist"
    exe_dir.mkdir()
    (exe_dir / "gtm.exe").write_text("MZ\n", encoding="utf-8")
    (exe_dir / _CLAIM_LAUNCHER).write_text("rem\n", encoding="utf-8")
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    (other_dir / _CLAIM_LAUNCHER).write_text("rem\n", encoding="utf-8")
    target = agent.resolve_claim_target(_conf(tool_dir=str(other_dir), tool_exe=str(exe_dir / "gtm.exe")))
    assert target is not None
    assert target.path == str(exe_dir / _CLAIM_LAUNCHER)


def test_resolve_claim_target_missing_returns_none(tmp_path):
    """两处都没有 claim 启动器(旧安装) -> None(按钮照显, 点击时提示升级)"""
    empty = tmp_path / "empty"
    empty.mkdir()
    assert agent.resolve_claim_target(_conf(tool_dir=str(empty))) is None
    # tool_exe 指向不存在的文件 -> 不当候选(回落 tool_dir, 同样没有启动器)
    assert agent.resolve_claim_target(_conf(tool_dir=str(empty), tool_exe=str(empty / "nope.exe"))) is None


def test_run_claim_ok_and_refusal(monkeypatch):
    """退出码 0 -> ok + 人话输出; 非 0 -> 拒绝 + 输出原样(UI 转述不解释)"""
    seen = {}

    def fake_run(args, *, cwd, timeout):
        seen.update(args=args, cwd=cwd, timeout=timeout)
        return _proc(0, "已重登记为正主: install=X data=Y\n")

    monkeypatch.setattr(agent, "_run_foreground", fake_run)
    target = agent.ClaimTarget(path="/inst/claim.cmd", label="claim 启动器(claim.cmd)")
    r = agent.run_claim(target)
    assert r.ok is True and r.exit_code == 0
    assert "已重登记为正主" in r.output
    assert seen["args"][-1] == "/inst/claim.cmd" and seen["cwd"] == "/inst" and seen["timeout"] == agent.CLAIM_TIMEOUT_S

    monkeypatch.setattr(agent, "_run_foreground", lambda args, *, cwd, timeout: _proc(1, "工具正在运行, 请先停止再重登记\n"))
    r2 = agent.run_claim(target)
    assert r2.ok is False and r2.exit_code == 1
    assert "请先停止" in r2.output  # 工具侧人话原样保留


def test_run_claim_timeout_and_spawn_failure(monkeypatch):
    """超时 / 启动器起不来 -> ok=False 且原因进 output(不静默)"""
    def boom_timeout(args, *, cwd, timeout):
        raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)

    monkeypatch.setattr(agent, "_run_foreground", boom_timeout)
    r = agent.run_claim(agent.ClaimTarget(path="/inst/claim.cmd", label="x"))
    assert r.ok is False and r.exit_code == -1 and "超时" in r.output

    def boom_os(args, *, cwd, timeout):
        raise OSError("denied")

    monkeypatch.setattr(agent, "_run_foreground", boom_os)
    r2 = agent.run_claim(agent.ClaimTarget(path="/inst/claim.cmd", label="x"))
    assert r2.ok is False and "执行失败" in r2.output


def test_status_includes_claim_note(monkeypatch):
    """状态区载荷带 claim_note(D7): 工具侧书写, auto-qb 只读展示"""
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: object())
    monkeypatch.setattr(agent, "read_deferred_note", lambda: {"schema": 1, "reason": "refused", "detail": "拒绝启动: 拷贝件"})
    st = agent.TrafficSourceAgent().status(_conf())
    assert st["state"] == "not_running"
    assert st["claim_note"]["reason"] == "refused"


def test_run_foreground_real_execution_with_allowed_binary():
    """_run_foreground 真跑一次白名单内可执行(node, sidefx POPEN 放行): 有界前台 + 合并输出

    其余场景(退出码/超时/起不来)由 run_claim 的注入替身覆盖; 本用例只钉这个单点
    真的把 subprocess.run 拼对(PIPE 合并 stdout/stderr、timeout 透传、退出码可读)。
    无 node 的环境静默跳过(与前端 node 守阵同口径, 不引入 skip 计数)。
    """
    node = shutil.which("node")
    if not node:
        return
    proc = agent._run_foreground([node, "--version"], cwd=None, timeout=30)
    assert proc.returncode == 0 and proc.stdout.strip()


def test_ensure_running_launch_oserror_backs_off(tmp_path, monkeypatch):
    """拉起本身失败(OSError): 记原因 + 固定退避 + 本轮不重试; 起不来不算「拉起过」
    (下轮仍按首次引导窗口 120s, 不因失败提前降档)"""
    monkeypatch.setattr(tool_client, "call_tool", _down)
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")

    def _boom(target):
        raise OSError("拒绝访问")

    monkeypatch.setattr(agent, "launch_tool", _boom)
    clock = [1000.0]
    a = agent.TrafficSourceAgent(clock=lambda: clock[0])
    conf = _conf(tool_dir=str(tmp_path))
    assert a.ensure_running(conf) is None
    st = a.status(conf)
    assert st["state"] == "launch_failed" and "拉起失败" in st["error"] and "拒绝访问" in st["error"]
    assert st["retry_s"] == pytest.approx(agent.RELAUNCH_BACKOFF_S)
    assert a._launched_once is False and a._pending_until == 0.0
    clock[0] += 1.0
    assert a.ensure_running(conf) is None  # 退避中: 不再尝试


def test_request_relaunch_clears_backoff_and_failure(tmp_path, monkeypatch):
    """手动「立即拉起/重试」: 清等待窗口/退避/失败记忆 -> 下一轮立刻重新拉起(设置页按钮走这条)"""
    monkeypatch.setattr(tool_client, "call_tool", _down)
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")
    launches = []
    monkeypatch.setattr(agent, "launch_tool", lambda target: launches.append(target))
    clock = [1000.0]
    a = agent.TrafficSourceAgent(clock=lambda: clock[0])
    conf = _conf(tool_dir=str(tmp_path))
    a.ensure_running(conf)  # 首次拉起
    clock[0] += agent.FIRST_BOOT_WINDOW_S + 1.0
    a.ensure_running(conf)  # 窗口耗尽 -> launch_failed + 退避
    assert a.status(conf)["state"] == "launch_failed"
    clock[0] += 1.0
    assert a.ensure_running(conf) is None and len(launches) == 1  # 退避中不拉
    a.request_relaunch()
    assert a._pending_until == 0.0 and a._retry_after == 0.0 and a._fail_reason == ""
    assert a.ensure_running(conf) is None and len(launches) == 2  # 清退避后立刻重拉


def test_ensure_running_success_then_failure_guards(monkeypatch):
    """探活成功后等待窗必须归零(er_8/9): 成功再失败是正常缺席, 不得 TypeError/记假「窗口耗尽」"""
    good = agent.ToolEndpoint(base_url="http://x", token_path="/t")
    seq = [good]
    monkeypatch.setattr(agent, "probe", lambda timeout=None: seq.pop(0) if seq else None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: agent.LaunchTarget("/x/launch.sh", False, "t"))
    monkeypatch.setattr(agent, "launch_tool", lambda t: None)
    clock = [1000.0]
    a = agent.TrafficSourceAgent(clock=lambda: clock[0])
    conf = _conf()
    assert a.ensure_running(conf) is not None
    assert a._pending_until == 0.0, "成功后等待窗必须归零(残留值下轮崩溃或记假失败)"

    clock[0] += 10.0
    assert a.ensure_running(conf) is None
    assert a._fail_reason == "" and a._retry_after == 0.0, "成功后缺席是正常重拉, 不得记假「窗口耗尽」"
    st = a.status(conf)
    assert st["state"] == "launching"
    assert st["retry_s"] == pytest.approx(agent.FIRST_BOOT_WINDOW_S)  # 探活成功轮不算「已拉起过」
    assert st["data_dir"] == "" and st["autostart_registered"] is False


def test_ensure_running_not_installed_backoff(tmp_path, monkeypatch):
    """未安装分支: 精确失败原因与 WARNING(er_22/25); 退避窗内不重试(er_24); 退避截止后可
    再解析(er_23: retry_after 必须是数值, None 下轮 TypeError); 初值 0.0 不挡首轮解析
    (init_7); 全新 agent 未安装态 error 为空串(init_8/9)。"""
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    resolve_calls = []

    def fake_resolve(conf):
        resolve_calls.append(1)
        return None

    monkeypatch.setattr(agent, "resolve_launch_target", fake_resolve)
    clock = [0.0]
    a = agent.TrafficSourceAgent(clock=lambda: clock[0])
    conf = _conf(tool_dir=str(tmp_path / "empty"))
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert a.ensure_running(conf) is None
    assert resolve_calls == [1]
    assert a._fail_reason == "未安装: 工具目录与可执行文件都解析不到"
    assert any(
        rec.levelno == logging.WARNING and rec.getMessage() == "全局流量监视器联动: 未安装: 工具目录与可执行文件都解析不到(请在设置页指定 tool_exe)"
        for rec in cap.records
    ), "未安装 WARNING 逐字不匹配"

    # 全新 agent: 未安装态 error 为空串(初值语义; status 自身也会调 resolve, 计数清零)
    st = agent.TrafficSourceAgent(clock=lambda: clock[0]).status(conf)
    assert st["state"] == "not_installed" and st["error"] == ""
    resolve_calls.clear()

    clock[0] += 1.0
    assert a.ensure_running(conf) is None
    assert resolve_calls == [], "退避窗内不得重试解析(er_24)"

    clock[0] += agent.RELAUNCH_BACKOFF_S + 1.0
    assert a.ensure_running(conf) is None
    assert resolve_calls == [1], "退避耗尽后应再解析(er_23: retry_after 不得是 None)"


def test_launch_window_exhaustion_state_and_logs(tmp_path, monkeypatch):
    """窗口耗尽: INFO 拉起审计 + WARNING 逐字(er_16/41); 退避三态边界(er_10/status_52/61/
    status_60): 截止一拍即判耗尽, 退避过期后不得恒 launch_failed。"""
    clock = [1000.0]
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: agent.LaunchTarget("/x/launch.sh", False, "启动器"))
    launches = []
    monkeypatch.setattr(agent, "launch_tool", lambda t: launches.append(t))
    a = agent.TrafficSourceAgent(clock=lambda: clock[0])
    conf = _conf()
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert a.ensure_running(conf) is None
    assert len(launches) == 1
    assert any(
        rec.levelno == logging.INFO and "已拉起全局流量监视器(启动器)" in rec.getMessage() for rec in cap.records
    ), "拉起 INFO 审计丢失"
    assert a.status(conf)["state"] == "launching"

    # 恰在窗口截止时刻: 已算耗尽(er_10 边界一拍), 状态区也不再判 launching(status_52)
    clock[0] = 1000.0 + agent.FIRST_BOOT_WINDOW_S
    assert a.status(conf)["state"] != "launching", "窗口截止一拍不算 launching(status_52)"
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert a.ensure_running(conf) is None
    assert a._fail_reason == f"拉起后 {agent.FIRST_BOOT_WINDOW_S:g}s 内未探活成功"
    assert any(
        rec.levelno == logging.WARNING and "拉起后 120s 内未探活成功(30s 后重试)" in rec.getMessage() for rec in cap.records
    ), "窗口耗尽 WARNING 逐字不匹配"
    assert a.status(conf)["state"] == "launch_failed"

    # 恰在退避截止时刻: 状态区不再判 launch_failed(status_61 边界一拍)
    clock[0] = 1000.0 + agent.FIRST_BOOT_WINDOW_S + agent.RELAUNCH_BACKOFF_S
    assert a.status(conf)["state"] != "launch_failed"
    # 退避彻底过期: fail_reason 仍在但退避已过 -> not_running(status_60: and 不得松动成 or)
    clock[0] += 1.0
    assert a.status(conf)["state"] == "not_running"


def test_fresh_agent_success_has_no_fake_recovery_log(monkeypatch):
    """全新 agent 首次成功不得有「已恢复」假 INFO(init_13: _last_error 初值必须是空串)"""
    monkeypatch.setattr(agent, "probe", lambda timeout=None: agent.ToolEndpoint(base_url="http://x", token_path="/t"))
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.TrafficSourceAgent().ensure_running(_conf()) is not None
    assert cap.messages == [], "全新 agent 首次成功不得有日志(假恢复 INFO = 审计噪声)"


def test_error_memory_recovery_semantics():
    """失败记忆与恢复日志(_clear_error_1/3): 恢复恰一条 INFO 且逐字带旧因; 记忆必须清空
    —— 连续成功不得重复「已恢复」假日志; 恢复后同因重新 WARNING(不是 DEBUG)。"""
    a = agent.TrafficSourceAgent()
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        a._note_error("拉起失败: 拒绝访问")
        a._clear_error()  # 恢复: 一条 INFO(先前: ...)
        a._clear_error()  # 再次成功: 记忆已清, 无新日志
        a._note_error("拉起失败: 拒绝访问")  # 恢复后同因: 重新 WARNING
    levels = [rec.levelno for rec in cap.records]
    assert levels == [logging.WARNING, logging.INFO, logging.WARNING]
    assert cap.messages[1] == "全局流量监视器联动已恢复(先前: 拉起失败: 拒绝访问)"


def test_ensure_running_launch_oserror_warning_exact(tmp_path, monkeypatch):
    """拉起 OSError 分支: WARNING 逐字带原因与重试提示(er_33: 失败告警不得丢真)"""
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: agent.LaunchTarget("/x/launch.sh", False, "启动器"))

    def _boom(target):
        raise OSError("拒绝访问")

    monkeypatch.setattr(agent, "launch_tool", _boom)
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.TrafficSourceAgent().ensure_running(_conf()) is None
    assert any(
        rec.levelno == logging.WARNING and "全局流量监视器联动: 拉起失败: 拒绝访问(启动器, 30s 后重试)" == rec.getMessage()
        for rec in cap.records
    ), "拉起失败 WARNING 逐字不匹配"


def test_run_claim_platform_command_and_contract(monkeypatch):
    """claim 执行契约: 平台命令两支强制进支逐位钉(Windows `cmd.exe /c` / POSIX `/bin/sh`);
    空输出原样空串; OSError 分支 exit_code 恒 -1(本层失败语义, 不得落成工具退出码形态)。"""
    seen = []

    def fake_run(args, *, cwd, timeout):
        seen.append(list(args))
        return _proc(0, "")

    monkeypatch.setattr(agent, "_run_foreground", fake_run)
    target = agent.ClaimTarget(path="/inst/claim.cmd", label="x")
    agent.run_claim(target)
    assert seen[-1] == (["cmd.exe", "/c", "/inst/claim.cmd"] if is_windows() else ["/bin/sh", "/inst/claim.cmd"])

    # 两支强制进支: 各自逐位(run_claim_2/3 分支选择子, 4/6 与 8/9 命令构造)
    monkeypatch.setattr(agent, "is_windows", lambda: True)
    agent.run_claim(target)
    assert seen[-1] == ["cmd.exe", "/c", "/inst/claim.cmd"]
    monkeypatch.setattr(agent, "is_windows", lambda: False)
    agent.run_claim(target)
    assert seen[-1] == ["/bin/sh", "/inst/claim.cmd"]

    # 空输出: 原样空串(不落占位文案)
    r = agent.run_claim(target)
    assert r.ok is True and r.exit_code == 0 and r.output == ""

    # OSError 分支: exit_code 恒 -1
    def boom(args, *, cwd, timeout):
        raise OSError("denied")

    monkeypatch.setattr(agent, "_run_foreground", boom)
    r2 = agent.run_claim(target)
    assert r2.ok is False and r2.exit_code == -1 and "执行失败" in r2.output


def test_resolve_launch_target_labels_and_branch_pinned(tmp_path, monkeypatch):
    """解析标签逐字(rlt_20/25/26/52: label 进 f-string 审计日志, None 显 "None");
    Windows 支强制进支钉 launch.cmd(rlt_47)。"""
    exe = tmp_path / "gtm-exe"
    exe.write_text("", encoding="utf-8")
    t = agent.resolve_launch_target(_conf(tool_exe=str(exe)))
    assert t is not None and t.label == "tool_exe 指定的可执行文件"

    (tmp_path / "launch.cmd").write_text("", encoding="utf-8")
    (tmp_path / "launch.sh").write_text("", encoding="utf-8")
    conf = _conf(tool_dir=str(tmp_path))
    monkeypatch.setattr(agent, "is_windows", lambda: True)
    t1 = agent.resolve_launch_target(conf)
    assert t1 is not None and os.path.basename(t1.path) == "launch.cmd"
    assert t1.label == "工具侧启动器(launch.cmd)"
    monkeypatch.setattr(agent, "is_windows", lambda: False)
    t2 = agent.resolve_launch_target(conf)
    assert t2 is not None and t2.label == "工具侧启动器(launch.sh)"
