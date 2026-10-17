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
- test_status_reports_states: ready / not_running 两态与端点字段读数(launching / launch_failed /
  not_installed 由拉起用例覆盖)
- test_launch_tool_builds_platform_command: 启动器 -> 平台命令(detached, 零参数); 可执行文件 ->
  直执行; Windows `cmd.exe /c` + DETACHED_PROCESS / POSIX `/bin/sh` + 新会话
- test_launch_path_has_no_uv_or_entry_names (S18/§08): agent.py 非 docstring 字符串里不含
  uv / gtm / -m / run / --autostart / --data-dir —— 「怎么起工具」的知识只在工具侧启动器里
- test_pointer_constants_mirror_tool_side (S18): 指针目录名 / 文件名 / schema 版本与工具侧
  gtm/storage.py 同值(两侧各持一份镜像常量, 只能靠守阵钉住漂移)
- test_tool_runtime_dirs_are_gitignored (S18/§08): 工具运行期目录(data/ 与 run/)已被仓库
  .gitignore 覆盖 —— 工具跑起来后 git status 仍干净
"""
import ast
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from auto_qb.core.traffic_source import agent
from auto_qb.infra.utils import is_windows
from auto_qb.webui import tool_client

#: 本平台对应的 D19 启动器文件名(与工具目录里的文件同名同源)
_LAUNCHER = agent._LAUNCHER_WINDOWS if is_windows() else agent._LAUNCHER_POSIX

# ---------- 构造辅助 ----------


def _conf(*, tool_dir="", tool_exe=""):
    """拉起源参数段替身: resolve_launch_target / ensure_running 只鸭子类型读 tool_dir / tool_exe"""
    return SimpleNamespace(tool_dir=tool_dir, tool_exe=tool_exe)


def _write_token(tmp_path, text="tool-credential-abc") -> str:
    """写一个假的工具密钥文件(值仅用于断言透传, 与真工具凭据无关)"""
    path = tmp_path / "gtm" / "monitor.token"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _write_pointer(
    tmp_path, monkeypatch, *, token_path, host="127.0.0.1", port=8099, schema=agent.ENDPOINT_SCHEMA
) -> str:
    """写发现指针 endpoint.json 并把 agent 的指针路径重定向到它(S16/D6)

    载荷字段名与工具侧 gtm 的写出契约一致(镜像非 import)。
    """
    path = tmp_path / "pointer" / agent.ENDPOINT_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": schema,
        "version": "0.1.0",
        "pid": 4321,
        "started_at": "2026-10-17T00:00:00+08:00",
        "host": host,
        "port": port,
        "data_dir": str(tmp_path / "gtm"),
        "token_path": token_path,
        "exe_path": "",
        "autostart_registered": True,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(path))
    return str(path)


@pytest.fixture()
def probe_env(tmp_path, monkeypatch):
    """探活环境: 真指针 + 真密钥文件 + 可换的假控制面 -> (monkeypatch 出的调用记录, 切换函数)"""
    token_path = _write_token(tmp_path)
    _write_pointer(tmp_path, monkeypatch, token_path=token_path)
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
    _write_pointer(tmp_path, monkeypatch, token_path=_write_token(tmp_path))
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
    _write_pointer(tmp_path, monkeypatch, token_path=str(empty))
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


# ---------- 拉起命令构造(注入假 subprocess, 规避 sidefx POPEN 越界) ----------


def test_launch_tool_builds_platform_command(tmp_path, monkeypatch):
    """启动器 -> 平台命令(detached); 可执行文件 -> 直执行; 不传任何参数"""
    calls = []

    class _FakePopen:
        def __init__(self, args, **kwargs):
            calls.append((list(args), dict(kwargs)))

    fake = SimpleNamespace(DEVNULL="DEVNULL", Popen=_FakePopen, DETACHED_PROCESS=0x00000008)
    monkeypatch.setattr(agent, "subprocess", fake)

    launcher = str(tmp_path / _LAUNCHER)
    exe = str(tmp_path / "gtm-exe")

    # Windows 支: cmd.exe /c 启动器 + DETACHED_PROCESS
    monkeypatch.setattr(agent, "is_windows", lambda: True)
    agent.launch_tool(agent.LaunchTarget(launcher, False, "启动器"))
    args, kw = calls[-1]
    assert args == ["cmd.exe", "/c", launcher]
    assert kw["creationflags"] == 0x00000008
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
    """指针目录名 / 文件名 / schema 版本必须与工具侧 gtm/storage.py 同值

    工具是独立包(自带 venv), auto-qb **不 import 它**, 两侧各持一份镜像常量 —— 只改一边的
    后果是「工具在跑、auto-qb 永远发现不了」(或反过来读到旧格式瞎猜字段)。D6 已把指针定为
    唯一事实源, 这份镜像契约因此值得一条守阵。
    """
    tool = _module_constants(_REPO_ROOT / "tools" / "global-traffic-monitor" / "src" / "gtm" / "storage.py")
    assert tool["POINTER_DIR_NAME"] == agent.POINTER_DIR_NAME
    assert tool["ENDPOINT_FILE_NAME"] == agent.ENDPOINT_FILE_NAME
    assert tool["ENDPOINT_SCHEMA"] == agent.ENDPOINT_SCHEMA
    # D16: 用户可见面用全称(目录名与 CLI 同名), 包名 gtm 不外泄到指针路径
    assert agent.POINTER_DIR_NAME == "global-traffic-monitor"


# ---------- 守阵: 工具运行期目录不得污染 git status (§08 判据 8) ----------


def test_tool_runtime_dirs_are_gitignored():
    """工具数据默认落进仓库(<工具目录>/data 与 run), 必须被 .gitignore 覆盖

    这两条是 S14 补的忽略项; 删掉或改路径的后果不是测试红, 而是运行中的工具把
    history_traffic.dat 与临时物写进 git status —— 踩本仓「树脏即停」的 git 纪律红线。
    判据直接读 .gitignore 文本(不起 git 进程: tests/sidefx.py 的 POPEN 白名单不放行)。
    """
    lines = {ln.strip() for ln in (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    for entry in ("tools/global-traffic-monitor/data/", "tools/global-traffic-monitor/run/"):
        assert entry in lines, f".gitignore 缺运行期目录忽略项: {entry}"
