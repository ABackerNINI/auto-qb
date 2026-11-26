"""test_traffic_source_agent_probe 测试计划: 全局流量监视器联动单点(探测 / 缺席拉起 / 状态, 计划 26-10-17-0339 S16)

## 测试计划(每个测试函数一条)
- test_pointer_path_is_user_level_platform_dir: 指针目录 = 平台用户级数据根 + 叶名
  (Windows %LOCALAPPDATA% / Linux $XDG_DATA_HOME 两支), endpoint.json 尾名同源
- test_read_pointer_absent_and_malformed: 指针缺失 -> None; 内容非法 JSON -> 只告警并当缺席
- test_parse_pointer_schema_guard_and_required_fields: schema 非预期或缺 host/port/token_path
  -> None(只告警不猜字段, D6); 合法载荷 -> 端点(base_url/token_path 等)
- test_default_tool_dir_points_to_repo_tool: 默认工具目录 = <仓库根>/tools/global-traffic-monitor,
  且平台对应的 D19 启动器就在其内
- test_probe_requires_pointer_and_200: 无指针 / 密钥空 / 非 200 / 不可达 -> None; 200 -> 端点(探活走 GET /status)
- test_ensure_running_source_off_does_not_probe_or_launch: 总开关关闭(S1/D1) ->
  ensure_running(enabled=False) 不探活不拉起; status() 不设闸(设置页仍看工具状态)
- test_launch_path_has_no_uv_or_entry_names (S18/§08): agent.py 非 docstring 字符串里不含
  uv / gtm / -m / run / --autostart / --data-dir —— 「怎么起工具」的知识只在工具侧启动器里
- test_pointer_constants_mirror_tool_side (S18): 指针目录名 / 文件名 / schema 版本与工具侧
  gtm/storage.py 同值; 正主注册常量(记录/注记/id/claim 启动器)与 gtm/identity.py 同值
  (计划 26-10-20-1316 §03; 两侧各持一份镜像常量, 只能靠守阵钉住漂移)
- test_tool_runtime_dirs_are_gitignored (S18/§08): 工具运行期目录(data/ run/ 与安装 ID
  tool-id)已被仓库 .gitignore 覆盖 —— 工具跑起来后 git status 仍干净

P1-T1.3 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_pointer_path_macos_branch: 用户级数据根 macOS 支(~/Library/Application Support)——
  Windows/Linux 两支由 test_pointer_path_is_user_level_platform_dir 钉住
- test_parse_pointer_pid_fallback: pid 非数值 -> 0(可选字段, 不影响端点解析); 数值照读
- test_parse_pointer_reads_optional_autostart_error
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
- test_resolve_claim_target_empty_tool_dir_falls_back_to_default: tool_dir 留空兜底默认目录
  (rct_33/36/39, claim 通道)
- test_read_deferred_note_path_and_encoding_pinned: 注记路径单点 + open utf-8 契约(dnp_3/4, rdn_4/7)
- test_read_deferred_note_warning_paths: 注记三条 WARNING 不丢(rdn_14/16/22)
- test_pointer_warning_paths_and_version_default: 指针 WARNING/可选字段缺省/port 边界
  (read_pointer_12, parse_pointer_7/8/36/38/73)
- test_read_pointer_pins_utf8_encoding: 指针 open utf-8 契约(read_pointer_3/6)
- test_stub_conf_without_tool_dir_attr_uses_default_dir: 桩配置缺 tool_dir 属性走默认目录
  (rlt_39/rct_32)

S7b 告警取数(计划 26-11-03-1102, 主告知数据链路) ——
- test_fetch_last_spike_reads_status_and_returns_spike: 复用 discover/read_token/call_tool, 只发一次
  GET /status(默认超时 SPIKE_TIMEOUT_S); 成功 -> (True, last_spike 对象)
- test_fetch_last_spike_failure_matrix: 指针缺失/密钥缺失/不可达(ToolUnreachable)/非 200/响应非对象
  -> (False, None)(前置失败不发请求); 旧工具无键或载荷非对象 -> (True, None)
- test_fetch_last_spike_has_dedicated_short_timeout (26-11-03 review 修 1): 取数默认超时 =
  SPIKE_TIMEOUT_S(3.0) 且严格小于探活超时 —— 主循环线程同步调用, 挂起连接最多拖 3s
- test_parse_pointer_rejects_non_local_host (issue 26-11-07-0527 R1#65; 双面评审收窄为
  回环单点): host 允许面 —— 公网/私网/NAT64 隧道/主机名拒绝(节流 WARNING), localhost/
  回环/IPv4-mapped 回环字面量放行
- test_probe_and_fetch_reject_token_path_outside_data_dir (issue 26-11-07-0527 R1#65):
  密钥归属闸 —— token_path 越界(含 .. 逃逸)不读密钥不发请求, probe None / fetch (False, None)
- test_probe_allows_loopback_hosts_and_rejects_private (issue 26-11-07-0527 R1#65): 合法
  指针不误拒 —— localhost/127.0.0.1/[::1] host + data_dir 内密钥(工具写出形态)照常探活;
  私网 host 收窄后拒绝且零请求(工具侧 fail-fast 只写回环, 私网只会出现在被改写的指针里)
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

from auto_qb.core.traffic_source.agent import fetch_last_spike as real_fetch_last_spike

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


def test_default_tool_dir_points_to_repo_tool():
    """默认工具目录 = <仓库根>/tools/global-traffic-monitor, 启动器在内"""
    base = agent.default_tool_dir()
    assert os.path.basename(base) == "global-traffic-monitor"
    assert os.path.isdir(os.path.join(base, "src", "gtm"))
    assert os.path.isfile(os.path.join(base, _LAUNCHER))


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

    # 密钥文件为空 -> 不发探活请求(文件须在 data_dir 内过归属闸, 才真正走空密钥分支)
    empty = tmp_path / "gtm" / "empty.token"
    empty.write_text("", encoding="utf-8")
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=str(empty))
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (200, {}))
    assert agent.probe() is None


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


# ---------- 守阵: 拉起不携带「怎么起工具」的知识 (§08 判据 9) ----------
#: 只允许出现在工具侧启动器(D19)里的 token: 包管理 / 包名 / 入口 / 子命令 / 参数
_LAUNCH_FORBIDDEN = ("uv", "gtm", "-m", "run", "--autostart", "--data-dir")


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


def test_resolve_claim_target_empty_tool_dir_falls_back_to_default(monkeypatch):
    """tool_dir 留空(生产合法) -> 兜底仓库内默认目录里的 claim 启动器

    rct_33/36(中): 兜底丢失 = 人工易主通道静默失效; rct_39(中): Windows 支强制进支钉 claim.cmd。
    """
    for forced_win, name in ((False, agent.CLAIM_LAUNCHER_POSIX), (True, agent.CLAIM_LAUNCHER_WINDOWS)):
        monkeypatch.setattr(agent, "is_windows", lambda v=forced_win: v)
        target = agent.resolve_claim_target(_conf())
        assert target is not None, "tool_dir 留空必须兜底到仓库内默认目录"
        assert os.path.basename(target.path) == name


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

    ep = agent.parse_pointer({"schema": agent.ENDPOINT_SCHEMA, "host": "127.0.0.1", "port": 1, "token_path": "/t"})
    assert ep is not None and ep.version == "" and ep.base_url == "http://127.0.0.1:1"


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


# ---------- S7b 告警取数(计划 26-11-03-1102) ----------
#: 真实实现按符号直取(conftest 的 gtm_spike_isolation 只替换模块属性, 不拦住本符号)
_SPIKE = {
    "ts": "2026-11-03T10:47:28+08:00",
    "dt_s": 5.0,
    "eff_dt_s": 5.0,
    "threshold_bps": 1024**3,
    "items": [{
        "nic": "以太网",
        "dir": "up",
        "cur": 1115700,
        "last": 800,
        "delta": 273400,
        "rate_bps": 1024**3 * 54,
    }],
}


def test_fetch_last_spike_reads_status_and_returns_spike(tmp_path, monkeypatch):
    """只读取数: 复用发现/鉴权/HTTP 单点, 只发一次 GET /status(默认超时 SPIKE_TIMEOUT_S)"""
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    seen = []
    monkeypatch.setattr(
        tool_client,
        "call_tool",
        lambda base_url, path, method, credential, payload=None, timeout=None:
        (seen.append((base_url, path, method, credential, timeout)) or (200, {
            "ok": True,
            "last_spike": _SPIKE
        })),
    )

    assert real_fetch_last_spike() == (True, _SPIKE)
    assert seen == [("http://127.0.0.1:8099", "/status", "GET", "tool-credential-abc", agent.SPIKE_TIMEOUT_S)]


def test_fetch_last_spike_has_dedicated_short_timeout():
    """26-11-03 review 修 1: 取数走专用短超时(主循环线程同步调用, 允许失败不必等探活级余量).

    SPIKE_TIMEOUT_S 严格小于 PROBE_TIMEOUT_S 且为常数 3.0 —— 快照 refresh() 里一次
    挂起的控制面连接最多拖慢主循环 3s, 而不是探活的 10s。
    """
    assert agent.SPIKE_TIMEOUT_S == 3.0
    assert agent.SPIKE_TIMEOUT_S < agent.PROBE_TIMEOUT_S
    import inspect

    assert inspect.signature(real_fetch_last_spike).parameters["timeout"].default == agent.SPIKE_TIMEOUT_S


def test_fetch_last_spike_failure_matrix(tmp_path, monkeypatch):
    """失败矩阵一律 (False, None) 且前置失败不发请求; 可达但无字段/载荷非对象 -> (True, None)"""
    calls = []
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (calls.append(a) or (200, {})))

    # 指针缺失 -> 不发请求
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    assert real_fetch_last_spike() == (False, None)
    assert calls == []

    # 密钥缺失 -> 不发请求(文件须在 data_dir 内过归属闸, 才真正走空密钥分支)
    empty = tmp_path / "gtm" / "empty.token"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=str(empty))
    assert real_fetch_last_spike() == (False, None)
    assert calls == []

    # 不可达(连接失败 / 响应非 JSON 都归 ToolUnreachable)
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    monkeypatch.setattr(tool_client, "call_tool", _down)
    assert real_fetch_last_spike() == (False, None)

    # 非 200
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (500, {"error": "x"}))
    assert real_fetch_last_spike() == (False, None)

    # 响应非对象
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (200, ["not-a-dict"]))
    assert real_fetch_last_spike() == (False, None)

    # 旧工具无 last_spike 键 / 载荷非对象 -> 可达但无异常
    for payload in ({"ok": True}, {"last_spike": "oops"}):
        monkeypatch.setattr(tool_client, "call_tool", lambda *a, _p=payload, **k: (200, _p))
        assert real_fetch_last_spike() == (True, None)


# ---------- 指针安全闸(issue 26-11-07-0527 R1#65): 改写指针不得把本地文件当凭据外发 ----------


def test_parse_pointer_rejects_non_local_host():
    """host 允许面(双面评审收窄为回环单点): 公网/私网/隧道/主机名拒绝(节流 WARNING);
    合法形态不误拒

    工具侧 gtm/config.py 的 _check_http_host fail-fast 只允许回环绑定 —— 合法指针 host
    只能是回环/localhost 字面量; is_private 会放行可路由出公网的隧道形态(NAT64 实测
    is_private=False), 已删除。IPv4-mapped 显式解包: mapped 回环放行(不随解释器版本
    漂移), mapped 公网照拒。
    """
    agent._send_reject_warn_ts.clear()  # 节流表是模块态: 清掉保证本用例 WARNING 可断言
    base = {"schema": agent.ENDPOINT_SCHEMA, "port": 8099, "token_path": "/t"}
    for host in ("8.8.8.8", "1.2.3.4", "192.168.1.5", "10.0.0.1", "gtm.example.com", "64:ff9b::8.8.8.8"):
        with capture_logs("auto_qb.core.traffic_source.agent") as cap:
            assert agent.parse_pointer({**base, "host": host}) is None, host
        assert any(rec.levelno == logging.WARNING and "host 不在允许面" in rec.getMessage() for rec in cap.records), host
    for host in ("localhost", "LOCALHOST", "127.0.0.1", "[::1]", "::ffff:127.0.0.1", "[::ffff:127.0.0.1]"):
        assert agent.parse_pointer({**base, "host": host}) is not None, host


def test_probe_and_fetch_reject_token_path_outside_data_dir(tmp_path, monkeypatch, probe_env):
    """密钥归属闸: token_path 越界(他目录 / .. 逃逸)-> 不读密钥不发请求(WARNING 节流)

    指针被改写成指向任意本地可读文件时, 文件内容不再作为 Bearer 凭据外发 —— probe 返回
    None、fetch_last_spike 返回 (False, None), call_tool 一次都不触发(拒绝发送并告警,
    保守默认法则 2)。
    """
    agent._send_reject_warn_ts.clear()  # 节流表是模块态: 清掉保证本用例 WARNING 可断言
    _calls, set_tool = probe_env
    set_tool()
    outside = tmp_path / "elsewhere" / "secret.txt"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("secret-content", encoding="utf-8")
    escape = str(tmp_path / "gtm" / ".." / "secret.txt")  # .. 逃逸形态(realpath 后出 data_dir)
    with capture_logs("auto_qb.core.traffic_source.agent") as cap:
        for bad_token in (str(outside), escape):
            write_endpoint_pointer(tmp_path, monkeypatch, token_path=bad_token)
            seen = []
            monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: seen.append(a))
            assert agent.probe() is None, bad_token
            assert real_fetch_last_spike() == (False, None), bad_token
            assert seen == [], bad_token
    assert any(rec.levelno == logging.WARNING and "token_path 不在 data_dir 内" in rec.getMessage() for rec in cap.records)


def test_probe_allows_loopback_hosts_and_rejects_private(tmp_path, monkeypatch, probe_env):
    """合法指针不误拒: localhost / 127.0.0.1 / [::1] host + data_dir 内密钥(工具写出形态
    token_path = <data_dir>/monitor.token)照常探活; 私网 host 收窄后拒绝且零请求 ——
    工具侧 fail-fast 只写回环, 私网只会出现在被改写的指针里"""
    agent._send_reject_warn_ts.clear()  # 节流表是模块态: 与 parse 用例同因, 保证断言确定性
    _calls, set_tool = probe_env
    for host in ("localhost", "127.0.0.1", "[::1]"):
        set_tool()
        write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path), host=host)
        seen = []
        monkeypatch.setattr(
            tool_client,
            "call_tool",
            lambda base_url, path, method, credential, payload=None, timeout=None:
            (seen.append(base_url) or (200, {
                "ok": True
            })),
        )
        assert agent.probe() is not None, host
        assert seen == [f"http://{host}:8099"], host

    # 私网收窄为拒(双面评审 1): 拒绝轮不发请求
    set_tool()
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path), host="192.168.1.5")
    seen = []
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: seen.append(a))
    assert agent.probe() is None
    assert seen == []
