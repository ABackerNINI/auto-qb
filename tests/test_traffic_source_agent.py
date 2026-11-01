"""test_traffic_source_agent 测试计划: 全局流量监视器联动单点(探测 / 缺席拉起 / 状态, 计划 26-10-17-0339 S16)

## 测试计划(每个测试函数一条)
- test_pointer_path_is_user_level_platform_dir: 指针目录 = 平台用户级数据根 + 叶名
  (Windows %LOCALAPPDATA% / Linux $XDG_DATA_HOME 两支), endpoint.json 尾名同源
- test_read_pointer_absent_and_malformed: 指针缺失 -> None; 内容非法 JSON -> 只告警并当缺席
- test_parse_pointer_schema_guard_and_required_fields: schema 非预期或缺 host/port/token_path
  -> None(只告警不猜字段, D6); 合法载荷 -> 端点(base_url/token_path 等)
- test_default_tool_dir_points_to_repo_tool: 默认工具目录 = <仓库根>/tools/global-traffic-monitor,
  且平台对应的 D19 启动器就在其内
- test_resolve_launch_target_order: 解析序 tool_exe(存在)优先 -> tool_dir 里启动器 -> 都没有 = None
- test_probe_requires_pointer_and_200: 无指针 / 密钥空 / 非 200 / 不可达 -> None; 200 -> 端点(探活走 GET /status)
- test_ensure_running_returns_endpoint_when_reachable: 探活成功直接返回端点, 不触发拉起(别的实例已拉起, D14)
- test_ensure_running_launches_then_backs_off: 缺席触发一次拉起; 首次引导窗口 120s 内不重复拉;
  窗口耗尽记失败并固定 30s 退避; 退避耗尽再拉起改用常态窗口 10s
- test_ensure_running_reports_not_installed: 解析不到目标 -> 不进拉起, 记「未安装」
- test_ensure_running_source_off_does_not_probe_or_launch: 总开关关闭(S1/D1) ->
  ensure_running(enabled=False) 不探活不拉起; status() 不设闸(设置页仍看工具状态)
- test_status_reports_states: ready / not_running 两态与端点字段读数(launching / launch_failed /
  not_installed 由拉起用例覆盖)
- test_launch_tool_builds_platform_command: 启动器 -> 平台命令(detached, 零参数); 可执行文件 ->
  直执行; Windows `cmd.exe /c` + CREATE_NO_WINDOW / POSIX `/bin/sh` + 新会话
- test_launcher_prefers_pythonw: 工具侧启动器优先 pythonw.exe(去黑框第二道保险), 且保留回退
- test_launch_path_has_no_uv_or_entry_names (S18/§08): agent.py 非 docstring 字符串里不含
  uv / gtm / -m / run / --autostart / --data-dir —— 「怎么起工具」的知识只在工具侧启动器里
- test_pointer_constants_mirror_tool_side (S18): 指针目录名 / 文件名 / schema 版本与工具侧
  gtm/storage.py 同值; 正主注册常量(记录/注记/id/claim 启动器)与 gtm/identity.py 同值
  (计划 26-10-20-1316 §03; 两侧各持一份镜像常量, 只能靠守阵钉住漂移)
- test_tool_runtime_dirs_are_gitignored (S18/§08): 工具运行期目录(data/ run/ 与安装 ID
  tool-id)已被仓库 .gitignore 覆盖 —— 工具跑起来后 git status 仍干净
- test_resolve_claim_target_finds_launcher / _tool_exe_dir_priority / _missing_returns_none
  (D4): claim 入口 = 安装内第二启动器, tool_exe 显式优先 -> tool_dir/默认, 都没有 -> None
- test_run_claim_ok_and_refusal / _timeout_and_spawn_failure (D5): 有界前台跑 claim
  启动器; 退出码 0 -> ok + 人话输出原样; 非 0 -> 拒绝; 超时/起不来 -> ok=False + 原因
- test_read_deferred_note_states (D7): 注记只读; 损坏/schema 未知 -> None(不猜字段)
- test_status_includes_claim_note (D7): 状态区载荷带 claim_note(工具侧书写, auto-qb 只读展示)

P1-T1.3 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_pointer_path_macos_branch: 用户级数据根 macOS 支(~/Library/Application Support)——
  Windows/Linux 两支由 test_pointer_path_is_user_level_platform_dir 钉住
- test_parse_pointer_pid_fallback: pid 非数值 -> 0(可选字段, 不影响端点解析); 数值照读
- test_read_deferred_note_non_dict_payload: 注记顶层非对象 -> None(只告警, 不猜字段)
- test_ensure_running_launch_oserror_backs_off: 拉起本身失败(OSError)-> 记原因 + 固定 30s
  退避 + 本轮不重试; 失败不计入 _launched_once(下轮仍按首次引导窗口)
- test_request_relaunch_clears_backoff_and_failure: 手动重试清等待窗口/退避/失败记忆 ->
  下一轮立刻重新拉起
- test_note_error_throttles_same_reason: 同因首次 WARNING、其后 DEBUG, 换因重新 WARNING
- test_parse_pointer_reads_optional_autostart_error
- test_resolve_claim_target_missing_returns_none
- test_resolve_claim_target_tool_exe_dir_priority
- test_run_claim_timeout_and_spawn_failure
- test_run_foreground_real_execution_with_allowed_binary
- test_run_foreground_subprocess_contract_with_probe (issue 26-11-01-0953): 注入
  subprocess.run 探针钉逐位实参(args/cwd/stdin/stdout/stderr/text/timeout/close_fds),
  不依赖环境二进制(node), 让函数体在任意环境可执行(mutmut no-tests 面闭合)

W7(R31) S5 补测(变异审计真洞守阵, 2026-11-01; 分类与位点见 tmp-analysis/w7-r31/classify.md) ——
平台支一律**强制进支**钉面(is_windows 打桩)—— WSL 池里 is_windows() 恒 False, Windows 支
变异靠强制进支让守阵在任何环境咬合(平台内断言), 不依赖 WSL 端到端:
- test_platform_data_home_windows_branch_pinned: Windows 支逐段(LOCALAPPDATA 主路径 + fallback)
- test_platform_data_home_posix_fallback_pinned: POSIX 生产面 fallback ~/.local/share 逐段
- test_probe_and_status_pin_call_contract: 探活契约(base_url/GET /status/timeout 钉死, probe_8/status_2)
- test_ensure_running_pins_probe_timeout: 订阅线程探活超时钉 PROBE_TIMEOUT_S(er_6)
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
- test_resolve_claim_target_empty_tool_dir_falls_back_to_default: tool_dir 留空兜底默认目录
  (rct_33/36/39, claim 通道)
- test_resolve_launch_target_labels_and_branch_pinned: 解析标签逐字 + Windows 支(rlt_20/25/26/47/52)
- test_read_deferred_note_path_and_encoding_pinned: 注记路径单点 + open utf-8 契约(dnp_3/4, rdn_4/7)
- test_read_deferred_note_warning_paths: 注记三条 WARNING 不丢(rdn_14/16/22)
- test_pointer_warning_paths_and_version_default: 指针 WARNING/可选字段缺省/port 边界
  (read_pointer_12, parse_pointer_7/8/36/38/73)
- test_read_pointer_pins_utf8_encoding: 指针 open utf-8 契约(read_pointer_3/6)
- test_stub_conf_without_tool_dir_attr_uses_default_dir: 桩配置缺 tool_dir 属性走默认目录
  (rlt_39/rct_32)
- test_status_ready_and_not_running_fields: 状态区字段读数(status_19/21/26/36)
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

#: 本平台对应的 D19 启动器文件名(与工具目录里的文件同名同源)
_LAUNCHER = agent._LAUNCHER_WINDOWS if is_windows() else agent._LAUNCHER_POSIX

# ---------- 构造辅助 ----------


def _conf(*, tool_dir="", tool_exe=""):
    """拉起源参数段替身: resolve_launch_target / ensure_running 只鸭子类型读 tool_dir / tool_exe"""
    return SimpleNamespace(tool_dir=tool_dir, tool_exe=tool_exe)


@pytest.fixture()
def probe_env(tmp_path, monkeypatch):
    """探活环境: 真指针 + 真密钥文件 + 可换的假控制面 -> (monkeypatch 出的调用记录, 切换函数)"""
    token_path = write_credential_file(tmp_path)
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=token_path)
    calls = []

    def set_tool(result=None, exc=None):
        """把 call_tool 换成给定返回 / 抛错的替身(默认 200)"""
        def fake(base_url, path, method, credential, payload=None, timeout=None):
            calls.append((path, method, credential, timeout))
            if exc is not None:
                raise exc
            return result if result is not None else (200, {"ok": True})

        monkeypatch.setattr(tool_client, "call_tool", fake)

    return calls, set_tool


def _down(*_a, **_k):
    """探活替身: 工具不可达(缺席)"""
    raise tool_client.ToolUnreachable("down")


# ---------- 指针发现 ----------


def test_pointer_path_is_user_level_platform_dir(tmp_path, monkeypatch):
    """指针目录 = 平台用户级数据根 + 叶名(Windows / XDG 两支)"""
    if is_windows():
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert agent.pointer_dir() == os.path.join(str(tmp_path), agent.POINTER_DIR_NAME)
        assert agent.endpoint_path() == os.path.join(agent.pointer_dir(), agent.ENDPOINT_FILE_NAME)

    # Linux/XDG 支: 关掉 Windows 判定, 给 XDG_DATA_HOME
    monkeypatch.setattr(agent, "is_windows", lambda: False)
    monkeypatch.setattr(agent.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    expected = os.path.join(str(tmp_path / "xdg"), agent.POINTER_DIR_NAME)
    assert agent.pointer_dir() == expected
    assert agent.endpoint_path() == os.path.join(expected, agent.ENDPOINT_FILE_NAME)


def test_read_pointer_absent_and_malformed(tmp_path, monkeypatch):
    """指针缺失 -> None; 内容非法 JSON -> 只告警并当缺席"""
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "nope" / agent.ENDPOINT_FILE_NAME))
    assert agent.read_pointer() is None

    bad = tmp_path / agent.ENDPOINT_FILE_NAME
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(bad))
    assert agent.read_pointer() is None


def test_parse_pointer_schema_guard_and_required_fields():
    """schema 非预期或缺关键字段 -> None(不猜字段, D6); 合法载荷 -> 端点"""
    assert agent.parse_pointer(None) is None
    assert agent.parse_pointer(["not", "a", "dict"]) is None

    good = {"schema": agent.ENDPOINT_SCHEMA, "host": "127.0.0.1", "port": 8099, "token_path": "/t"}
    ep = agent.parse_pointer(good)
    assert ep is not None
    assert ep.base_url == "http://127.0.0.1:8099"
    assert ep.token_path == "/t"

    assert agent.parse_pointer({**good, "schema": agent.ENDPOINT_SCHEMA + 1}) is None
    for drop in ("host", "port", "token_path"):
        assert agent.parse_pointer({k: v for k, v in good.items() if k != drop}) is None
    assert agent.parse_pointer({**good, "port": "not-a-number"}) is None  # port 非数 -> 0 -> 缺


def test_parse_pointer_reads_optional_autostart_error():
    """autostart_error 是可选字段: 有则读成 str, 缺/空 -> None(旧指针与成功态都落这里)"""
    base = {"schema": agent.ENDPOINT_SCHEMA, "host": "127.0.0.1", "port": 8099, "token_path": "/t"}
    assert agent.parse_pointer(base).autostart_error is None
    assert agent.parse_pointer({**base, "autostart_error": None}).autostart_error is None
    ep = agent.parse_pointer({**base, "autostart_error": "写注册表失败: 拒绝访问"})
    assert ep.autostart_error == "写注册表失败: 拒绝访问"


# ---------- 拉起目标解析 ----------


def test_default_tool_dir_points_to_repo_tool():
    """默认工具目录 = <仓库根>/tools/global-traffic-monitor, 启动器在内"""
    base = agent.default_tool_dir()
    assert os.path.basename(base) == "global-traffic-monitor"
    assert os.path.isdir(os.path.join(base, "src", "gtm"))
    assert os.path.isfile(os.path.join(base, _LAUNCHER))


def test_resolve_launch_target_order(tmp_path):
    """tool_exe(存在)优先 -> tool_dir 里启动器 -> 都没有 = None"""
    # ③ tool_dir 留空 -> 兜底仓库内默认目录(真启动器存在)
    t0 = agent.resolve_launch_target(_conf())
    assert t0 is not None and t0.is_exe is False and os.path.basename(t0.path) == _LAUNCHER

    # ② tool_dir 指定临时目录里的启动器
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")
    t1 = agent.resolve_launch_target(_conf(tool_dir=str(tmp_path)))
    assert t1 is not None and t1.is_exe is False
    assert t1.path == os.path.join(str(tmp_path), _LAUNCHER)

    # ① tool_exe 存在 -> 直接执行(优先于启动器)
    exe = tmp_path / "gtm-exe"
    exe.write_text("", encoding="utf-8")
    t2 = agent.resolve_launch_target(_conf(tool_dir=str(tmp_path), tool_exe=str(exe)))
    assert t2 is not None and t2.is_exe is True
    assert t2.path == os.path.abspath(str(exe))

    # tool_exe 指向不存在的文件 -> 落回 tool_dir 启动器
    t3 = agent.resolve_launch_target(_conf(tool_dir=str(tmp_path), tool_exe=str(tmp_path / "nope")))
    assert t3 is not None and t3.is_exe is False

    # ③' 两者都解析不到 -> None(未安装)
    empty = tmp_path / "empty"
    empty.mkdir()
    assert agent.resolve_launch_target(_conf(tool_dir=str(empty))) is None


# ---------- 探活 ----------


def test_probe_requires_pointer_and_200(tmp_path, monkeypatch, probe_env):
    """无指针 / 密钥空 / 非 200 / 不可达 -> None; 200 -> 端点"""
    _calls, set_tool = probe_env

    # 无指针
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    assert agent.probe() is None

    # 复位指针: 探活走 GET /status, 凭据从密钥文件读
    set_tool()
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    calls = []
    monkeypatch.setattr(
        tool_client,
        "call_tool",
        lambda base_url, path, method, credential, payload=None, timeout=None:
        (calls.append((path, method, credential, timeout)) or (200, {
            "ok": True
        }))
    )
    ep = agent.probe()
    assert ep is not None and ep.base_url == "http://127.0.0.1:8099"
    assert calls == [("/status", "GET", "tool-credential-abc", agent.PROBE_TIMEOUT_S)]

    # 非 200 -> 不存在(残留指针不算就绪, D7)
    set_tool(result=(500, {"error": "x"}))
    assert agent.probe() is None

    # 不可达
    monkeypatch.setattr(tool_client, "call_tool", _down)
    assert agent.probe() is None

    # 密钥文件为空 -> 不发探活请求
    empty = tmp_path / "empty.token"
    empty.write_text("", encoding="utf-8")
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=str(empty))
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (200, {}))
    assert agent.probe() is None


# ---------- 保障可达(拉起 / 退避) ----------


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


def test_ensure_running_source_off_does_not_probe_or_launch(tmp_path, monkeypatch, probe_env):
    """总开关关闭(S1/D1, 26-10-17-1737): ensure_running(enabled=False) 不探活不拉起

    工具就绪(探活会成功)也不例外 —— 关源即停自动拉起。status() 不设闸: 设置页关来源后
    仍要能看工具状态(探活是权威判据, 与订阅/取数闸门是两件事)。
    """
    calls, set_tool = probe_env
    set_tool()  # 探活会成功(工具就绪)
    launches = []
    monkeypatch.setattr(agent, "launch_tool", lambda target: launches.append(target))

    a = agent.TrafficSourceAgent()
    assert a.ensure_running(_conf(), enabled=False) is None
    assert calls == []  # 一次控制面调用都没发(不探活)
    assert launches == []  # 也不拉起
    # 默认实参保持旧语义: 不传 enabled = 照常探活
    assert a.ensure_running(_conf()) is not None
    assert calls  # 探活发生了
    # status 不设闸: 关源后仍能读工具状态
    assert a.status(_conf())["state"] == "ready"


# ---------- 状态五态 ----------


def test_status_reports_states(tmp_path, monkeypatch, probe_env):
    """ready / not_running 两态与端点字段读数"""
    _calls, set_tool = probe_env
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")
    conf = _conf(tool_dir=str(tmp_path))
    a = agent.TrafficSourceAgent()

    # 探活失败 + 目标可解析 + 无拉起/退避记忆 -> not_running
    monkeypatch.setattr(tool_client, "call_tool", _down)
    st = a.status(conf)
    assert st["state"] == "not_running"
    assert st["endpoint"] is None
    assert st["pid"] == 0 and st["version"] == ""

    # 探活成功 -> ready, 端点字段回填
    set_tool(result=(200, {"ok": True}))
    st = a.status(conf)
    assert st["state"] == "ready"
    assert st["endpoint"] is not None
    assert st["pid"] == 4321 and st["version"] == "0.1.0"
    assert st["autostart_registered"] is True
    assert st["autostart_error"] is None  # 没失败 -> None(issue 26-10-17-1455)


# ---------- 拉起命令构造(注入假 subprocess, 规避 sidefx POPEN 越界) ----------


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


# ---------- 守阵: 拉起不携带「怎么起工具」的知识 (§08 判据 9) ----------
#: 只允许出现在工具侧启动器(D19)里的 token: 包管理 / 包名 / 入口 / 子命令 / 参数
_LAUNCH_FORBIDDEN = ("uv", "gtm", "-m", "run", "--autostart", "--data-dir")

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _string_literals_without_docstrings(path):
    """模块内全部**非 docstring** 字符串常量 -> [(行号, 文本)]

    注释与 docstring 不在判定面内: 它们可以自由讨论 `uv`(如首次引导窗口为何给 120s),
    但**可执行的知识**(会拼进命令行的字符串)不许出现在 auto-qb 侧。
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc_nodes.add(id(body[0].value))
    return [
        (n.lineno, n.value)
        for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes
    ]


def test_launch_path_has_no_uv_or_entry_names():
    """§08: auto-qb 的拉起动作只有「执行启动器」一步 —— 不拼 uv、不认识入口名与子命令

    运行时形状由 test_launch_tool_builds_platform_command 逐 token 钉住(`cmd.exe /c <启动器>`);
    本用例守**静态面**: agent.py 里不许出现 uv / gtm / -m / run / --autostart / --data-dir
    这些字符串常量。工具升级换命令形态时只改启动器内容、本侧零改动 —— 一旦有人图省事在
    auto-qb 里拼 `uv run gtm run`, 这条当场红。
    """
    pattern = re.compile(r"(?<![A-Za-z0-9_-])(%s)(?![A-Za-z0-9_-])" % "|".join(re.escape(t) for t in _LAUNCH_FORBIDDEN))
    offenders = [
        (lineno, text) for lineno, text in _string_literals_without_docstrings(agent.__file__) if pattern.search(text)
    ]
    assert offenders == [], f"auto-qb 侧出现「怎么起工具」的知识(应沉进工具侧启动器): {offenders}"


# ---------- 守阵: 指针常量跨侧镜像 (§05 契约字段) ----------


def _module_constants(path):
    """模块顶层 `NAME = 字面量` 赋值 -> {NAME: 值}(AST 读, 不 import 工具包)"""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                continue
    return out


def test_pointer_constants_mirror_tool_side():
    """指针目录名 / 文件名 / schema 版本必须与工具侧 gtm/storage.py 同值;
    正主注册常量(记录/注记/id/claim 启动器)与 gtm/identity.py 同值(计划 26-10-20-1316 §03)

    工具是独立包(自带 venv), auto-qb **不 import 它**, 两侧各持一份镜像常量 —— 只改一边的
    后果是「工具在跑、auto-qb 永远发现不了」(或反过来读到旧格式瞎猜字段)。D6 已把指针定为
    唯一事实源, 这份镜像契约因此值得一条守阵。
    """
    tool_src = _REPO_ROOT / "tools" / "global-traffic-monitor" / "src" / "gtm"
    tool = _module_constants(tool_src / "storage.py")
    assert tool["POINTER_DIR_NAME"] == agent.POINTER_DIR_NAME
    assert tool["ENDPOINT_FILE_NAME"] == agent.ENDPOINT_FILE_NAME
    assert tool["ENDPOINT_SCHEMA"] == agent.ENDPOINT_SCHEMA
    # D16: 用户可见面用全称(目录名与 CLI 同名), 包名 gtm 不外泄到指针路径
    assert agent.POINTER_DIR_NAME == "global-traffic-monitor"
    # 正主注册(§03): auto-qb 只读注记展示/定位 claim 入口, 记录本身零读写(D7/D8)
    identity = _module_constants(tool_src / "identity.py")
    assert identity["PRIMARY_FILE_NAME"] == agent.PRIMARY_FILE_NAME
    assert identity["DEFERRED_FILE_NAME"] == agent.DEFERRED_FILE_NAME
    assert identity["DEFERRED_SCHEMA"] == agent.DEFERRED_SCHEMA
    assert identity["ID_FILE_NAME"] == agent.ID_FILE_NAME
    assert identity["CLAIM_LAUNCHER_WINDOWS"] == agent.CLAIM_LAUNCHER_WINDOWS
    assert identity["CLAIM_LAUNCHER_POSIX"] == agent.CLAIM_LAUNCHER_POSIX
    # claim 是 launch 之外的第二启动器(D4), 文件名不得与 D19 启动器族撞车
    assert agent.CLAIM_LAUNCHER_WINDOWS != agent._LAUNCHER_WINDOWS
    assert agent.CLAIM_LAUNCHER_POSIX != agent._LAUNCHER_POSIX


# ---------- 守阵: 工具运行期目录不得污染 git status (§08 判据 8) ----------


def test_tool_runtime_dirs_are_gitignored():
    """工具数据默认落进仓库(<工具目录>/data 与 run), 必须被 .gitignore 覆盖

    这两条是 S14 补的忽略项; 删掉或改路径的后果不是测试红, 而是运行中的工具把
    history_traffic.dat 与临时物写进 git status —— 踩本仓「树脏即停」的 git 纪律红线。
    判据直接读 .gitignore 文本(不起 git 进程: tests/sidefx.py 的 POPEN 白名单不放行)。
    tool-id 是正主注册的安装 ID(计划 26-10-20-1316 §03): 仓库内安装根首次启动即生成。
    """
    lines = {ln.strip() for ln in (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    for entry in (
        "tools/global-traffic-monitor/data/",
        "tools/global-traffic-monitor/run/",
        "tools/global-traffic-monitor/tool-id",
    ):
        assert entry in lines, f".gitignore 缺运行期目录忽略项: {entry}"


# ---------- 守阵: claim 人工易主通道 (计划 26-10-20-1316 §03, D4/D5) ----------

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


def test_read_deferred_note_states(tmp_path, monkeypatch):
    """缺失 -> None; 合法 -> 载荷; 损坏 / schema 未知 -> None(不猜字段, 指针同族纪律)"""
    note_path = tmp_path / "ptr" / "deferred.json"
    monkeypatch.setattr(agent, "deferred_note_path", lambda: str(note_path))
    assert agent.read_deferred_note() is None  # 缺失
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        json.dumps({
            "schema": agent.DEFERRED_SCHEMA,
            "reason": "relayed",
            "detail": "已让位"
        }), encoding="utf-8"
    )
    note = agent.read_deferred_note()
    assert note["reason"] == "relayed" and note["detail"] == "已让位"
    note_path.write_text("{ not json", encoding="utf-8")
    assert agent.read_deferred_note() is None  # 损坏按无注记
    note_path.write_text(json.dumps({"schema": 999, "reason": "relayed"}), encoding="utf-8")
    assert agent.read_deferred_note() is None  # schema 未知不猜字段


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


def test_run_foreground_subprocess_contract_with_probe(monkeypatch):
    """_run_foreground 的 subprocess.run 拼装契约: 注入探针逐位钉实参, 不依赖环境二进制

    issue 26-11-01-0953: 既有直跑用例依赖 node, 无 node 环境静默 return, 函数体在
    mutmut 的 stats/覆盖映射阶段从未执行 -> 18 条参数变异记 no tests。本用例把
    subprocess.run 换成记录器, 函数体必执行, 且对 args 透传 / cwd / DEVNULL / PIPE 合并
    / text / timeout / close_fds 逐位断言(任一被 None 化或丢失即红)。
    """
    seen = {}

    def probe(args, **kwargs):
        seen.update(args=args, **kwargs)
        return SimpleNamespace(returncode=7, stdout="probe-out", stderr="probe-err")

    monkeypatch.setattr(agent.subprocess, "run", probe)
    proc = agent._run_foreground(["probe-bin", "--flag"], cwd="probe-cwd", timeout=3.5)
    assert proc.returncode == 7 and proc.stdout == "probe-out"
    assert seen["args"] == ["probe-bin", "--flag"]
    assert seen["cwd"] == "probe-cwd"
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["stdout"] is subprocess.PIPE
    assert seen["stderr"] is subprocess.STDOUT
    assert seen["text"] is True
    assert seen["timeout"] == 3.5
    assert seen["close_fds"] is True


# ---------- P1-T1.3 守卫与容错簇(计划 26-10-20-2101) ----------


def test_pointer_path_macos_branch(monkeypatch):
    """用户级数据根 macOS 支(D6): ~/Library/Application Support —— Windows 走 LOCALAPPDATA,
    Linux 走 XDG_DATA_HOME, 三支都是「平台惯例单点」, 工具侧镜像同一口径"""
    monkeypatch.setattr(agent, "is_windows", lambda: False)
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    expected = os.path.join(os.path.expanduser("~"), "Library", "Application Support", agent.POINTER_DIR_NAME)
    assert agent.pointer_dir() == expected


def test_parse_pointer_pid_fallback():
    """pid 是可选字段: 非数值 -> 0(不影响端点解析, 只丢「谁在跑」的展示); 数值照读"""
    base = {"schema": agent.ENDPOINT_SCHEMA, "host": "127.0.0.1", "port": 8099, "token_path": "/t"}
    assert agent.parse_pointer({**base, "pid": "not-a-number"}).pid == 0
    assert agent.parse_pointer({**base, "pid": "4321"}).pid == 4321
    assert agent.parse_pointer(base).pid == 0  # 缺省


def test_read_deferred_note_non_dict_payload(tmp_path, monkeypatch):
    """注记顶层非对象(如数组)-> None: 只告警不猜字段, 与指针 schema 守卫同族纪律"""
    note_path = tmp_path / "ptr" / "deferred.json"
    monkeypatch.setattr(agent, "deferred_note_path", lambda: str(note_path))
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(json.dumps([agent.DEFERRED_SCHEMA]), encoding="utf-8")
    assert agent.read_deferred_note() is None


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


def test_note_error_throttles_same_reason():
    """失败日志节流(同一原因只说明白一次): 首条 WARNING, 同因降 DEBUG; 换原因重新 WARNING
    —— 工具没起是常态, 逐轮 WARNING 会刷屏"""
    lg = logging.getLogger("auto_qb.core.traffic_source.agent")
    records = []

    class _Rec(logging.Handler):
        def emit(self, record):
            records.append((record.levelno, record.getMessage()))

    handler = _Rec()
    handler.setLevel(logging.DEBUG)
    old_level = lg.level
    lg.setLevel(logging.DEBUG)
    lg.addHandler(handler)
    try:
        a = agent.TrafficSourceAgent()
        a._note_error("拉起失败: 拒绝访问")
        a._note_error("拉起失败: 拒绝访问")
        assert [lv for lv, _ in records] == [logging.WARNING, logging.DEBUG]
        a._note_error("未安装: 工具目录解析不到")
        assert records[-1][0] == logging.WARNING and "未安装" in records[-1][1]
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)


# ---------- W7(R31) S5 补测(变异审计真洞守阵): 平台支强制进支钉面 ----------


def test_platform_data_home_windows_branch_pinned(monkeypatch):
    """Windows 支强制走(平台内断言): LOCALAPPDATA 主路径 + 未置位 fallback 逐段钉死

    WSL 池里 is_windows() 恒 False, Windows 支变异对套件不可见(平台盲区) —— 强制进支让
    守阵在任何环境咬合: or→and / 键名漂移 / join 缺参与错词全部当场红。
    """
    monkeypatch.setattr(agent, "is_windows", lambda: True)
    monkeypatch.setenv("LOCALAPPDATA", "C:/custom/appdata")
    assert agent._platform_data_home() == "C:/custom/appdata"
    assert agent.pointer_dir() == os.path.join("C:/custom/appdata", agent.POINTER_DIR_NAME)

    # 未置位: fallback ~/AppData/Local(逐段: ~ 展开 / AppData / Local)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert agent._platform_data_home() == os.path.join(os.path.expanduser("~"), "AppData", "Local")


def test_platform_data_home_posix_fallback_pinned(monkeypatch):
    """POSIX 生产面强制走: XDG 未置位 -> ~/.local/share 逐段钉死(指针整链的目录根)"""
    monkeypatch.setattr(agent, "is_windows", lambda: False)
    monkeypatch.setattr(agent.sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    expected = os.path.join(os.path.expanduser("~"), ".local", "share")
    assert agent._platform_data_home() == expected
    assert agent.pointer_dir() == os.path.join(expected, agent.POINTER_DIR_NAME)


def test_probe_and_status_pin_call_contract(tmp_path, monkeypatch):
    """探活契约单点: base_url 来自指针、GET /status、timeout 钉 PROBE_TIMEOUT_S

    probe_8(中): base_url 丢失 = rstrip AttributeError 崩溃面; status_2(中): UI 线程
    探活无超时 = 状态区可被吊死 —— 契约断言把两个调用参数钉死。
    """
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    seen = []
    monkeypatch.setattr(
        tool_client,
        "call_tool",
        lambda base_url, path, method, credential, payload=None, timeout=None:
        (seen.append((base_url, path, timeout)) or (200, {
            "ok": True
        })),
    )
    assert agent.probe() is not None
    assert seen == [("http://127.0.0.1:8099", "/status", agent.PROBE_TIMEOUT_S)]

    # 状态区同一契约(status_2)
    seen.clear()
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: object())
    st = agent.TrafficSourceAgent().status(_conf())
    assert st["state"] == "ready"
    assert seen == [("http://127.0.0.1:8099", "/status", agent.PROBE_TIMEOUT_S)]


def test_ensure_running_pins_probe_timeout(monkeypatch):
    """订阅线程探活超时钉 PROBE_TIMEOUT_S(er_6): 回环挂起时不得无超时吊住订阅线程"""
    seen = []
    monkeypatch.setattr(agent, "probe", lambda timeout=None: seen.append(timeout) or None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: agent.LaunchTarget("/x/launch.sh", False, "t"))
    monkeypatch.setattr(agent, "launch_tool", lambda t: None)
    assert agent.TrafficSourceAgent().ensure_running(_conf()) is None
    assert seen == [agent.PROBE_TIMEOUT_S]


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


def test_resolve_claim_target_empty_tool_dir_falls_back_to_default(monkeypatch):
    """tool_dir 留空(生产合法) -> 兜底仓库内默认目录里的 claim 启动器

    rct_33/36(中): 兜底丢失 = 人工易主通道静默失效; rct_39(中): Windows 支强制进支钉 claim.cmd。
    """
    for forced_win, name in ((False, agent.CLAIM_LAUNCHER_POSIX), (True, agent.CLAIM_LAUNCHER_WINDOWS)):
        monkeypatch.setattr(agent, "is_windows", lambda v=forced_win: v)
        target = agent.resolve_claim_target(_conf())
        assert target is not None, "tool_dir 留空必须兜底到仓库内默认目录"
        assert os.path.basename(target.path) == name


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


def test_read_deferred_note_path_and_encoding_pinned(tmp_path, monkeypatch):
    """注记路径 = pointer_dir/deferred.json(dnp_3/4: 丢目录/丢文件名都读不到, 可见性便利失效);
    open 显式 encoding="utf-8"(rdn_4/7: GBK locale 下非 ASCII 注记不得读丢)。"""
    pdir = tmp_path / "ptr"
    pdir.mkdir()
    monkeypatch.setattr(agent, "pointer_dir", lambda: str(pdir))
    payload = {"schema": agent.DEFERRED_SCHEMA, "reason": "让位", "detail": "拷贝件在跑"}
    (pdir / agent.DEFERRED_FILE_NAME).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert agent.read_deferred_note() == payload

    real_open = builtins.open
    captured = {}

    def spy_open(file, mode="r", *args, **kwargs):
        captured["mode"] = mode
        captured["encoding"] = kwargs.get("encoding")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    agent.read_deferred_note()
    assert captured == {"mode": "r", "encoding": "utf-8"}


def test_read_deferred_note_warning_paths(tmp_path, monkeypatch):
    """注记三条 WARNING 不丢(rdn_14/16/22): 读失败/格式非法/schema 非预期都留排障轨迹"""
    pdir = tmp_path / "ptr"
    pdir.mkdir()
    (pdir / agent.DEFERRED_FILE_NAME).mkdir()  # 注记路径是目录 -> IsADirectoryError(OSError 非 FileNotFoundError)
    monkeypatch.setattr(agent, "pointer_dir", lambda: str(pdir))
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.read_deferred_note() is None
    assert any(rec.levelno == logging.WARNING and "让位注记失败" in rec.getMessage() for rec in cap.records)

    (pdir / agent.DEFERRED_FILE_NAME).rmdir()  # 换回文件形态
    note = pdir / agent.DEFERRED_FILE_NAME
    note.write_text("[1]", encoding="utf-8")
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.read_deferred_note() is None
    assert any(rec.levelno == logging.WARNING and "格式非法" in rec.getMessage() for rec in cap.records)

    note.write_text(json.dumps({"schema": 999}), encoding="utf-8")
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.read_deferred_note() is None
    assert any(rec.levelno == logging.WARNING and "schema 非预期" in rec.getMessage() for rec in cap.records)


def test_pointer_warning_paths_and_version_default(tmp_path, monkeypatch):
    """指针排障轨迹与可选字段缺省: 读失败/schema 非预期/缺关键字段三条 WARNING
    (read_pointer_12, parse_pointer_7/8/38); 旧指针无 version -> 空串不显示占位
    (parse_pointer_73); port=1 也在合法面(parse_pointer_36: 拒绝边界只在 <=0)。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(bad))
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.read_pointer() is None
    assert any(rec.levelno == logging.WARNING and "读取全局流量监视器指针失败" in rec.getMessage() for rec in cap.records)

    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.parse_pointer({"schema": 999}) is None
    assert any(
        rec.levelno == logging.WARNING and
        rec.getMessage() == f"全局流量监视器指针 schema 非预期(读到 999, 期望 {agent.ENDPOINT_SCHEMA}): 不猜字段, 视为未就绪"
        for rec in cap.records
    ), "schema 告警逐字不匹配"

    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        assert agent.parse_pointer({"schema": agent.ENDPOINT_SCHEMA}) is None
    assert any(rec.levelno == logging.WARNING and "缺关键字段" in rec.getMessage() for rec in cap.records)

    ep = agent.parse_pointer({"schema": agent.ENDPOINT_SCHEMA, "host": "h", "port": 1, "token_path": "/t"})
    assert ep is not None and ep.version == "" and ep.base_url == "http://h:1"


def test_read_pointer_pins_utf8_encoding(tmp_path, monkeypatch):
    """指针读取 open 显式 encoding="utf-8"(read_pointer_3/6: GBK locale 下非 ASCII 指针不得读丢)"""
    p = tmp_path / "ptr" / agent.ENDPOINT_FILE_NAME
    p.parent.mkdir()
    p.write_text(json.dumps({"schema": agent.ENDPOINT_SCHEMA, "note": "非ASCII注记"}), encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(p))
    real_open = builtins.open
    captured = {}

    def spy_open(file, mode="r", *args, **kwargs):
        captured["mode"] = mode
        captured["encoding"] = kwargs.get("encoding")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    assert agent.read_pointer() == {"schema": agent.ENDPOINT_SCHEMA, "note": "非ASCII注记"}
    assert captured == {"mode": "r", "encoding": "utf-8"}


def test_stub_conf_without_tool_dir_attr_uses_default_dir():
    """桩配置(无 tool_dir 属性) -> getattr 缺省空串走仓库内默认目录

    rlt_39/rct_32: 缺省落占位串会跳过 default_tool_dir -> 误报「未安装」。
    """
    assert agent.resolve_launch_target(SimpleNamespace(tool_exe="")) is not None
    assert agent.resolve_claim_target(SimpleNamespace(tool_exe="")) is not None


def test_status_ready_and_not_running_fields(tmp_path, monkeypatch):
    """ready 态端点字段读数(status_19: data_dir 不得恒空)与 retry_s 基线(status_36)"""
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (200, {"ok": True}))
    st = agent.TrafficSourceAgent().status(_conf())
    assert st["state"] == "ready"
    assert st["data_dir"] == str(tmp_path / "gtm")
    assert st["retry_s"] == 0.0
