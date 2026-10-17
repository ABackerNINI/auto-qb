"""全局流量监视器联动单点(计划 26-10-17-0339 S16): 探测 -> 保障可达(缺席拉起) -> 状态.

发现层的唯一事实源是工具写在**用户级平台目录**的指针 endpoint.json(D6):

- `probe()` 读指针 -> 用指针里的 host/port/token_path 发 `GET /status` 探活, 200 才算在跑
  (D7); **残留指针**(文件在但探活失败)不算就绪、不阻止拉起; pid 仅作展示。
- `ensure_running()` 缺席时按 D10 解析启动目标(tool_exe 优先, 否则 tool_dir / 仓库内默认目录
  里的 D19 启动器)并 detached 执行 —— **零参数**(自启意图写死在启动器里, D13); 拉起失败按
  D14 **固定 30s 退避**重试; 探活成功即直接订阅(别的实例已拉起也不重复拉)。
- `status()` 供设置页状态区读五态(plan §05)。

「启动工具」是可注入的**模块级单点** `launch_tool` —— tests/sidefx.py 的 POPEN 白名单只放行
`node` 与临时 wrapper, 测试一律注入假动作(`monkeypatch.setattr(agent, "launch_tool", fake)`),
生产走真 Popen(Windows `DETACHED_PROCESS` / POSIX 新会话)。

HTTP 与密钥读取复用 `webui.tool_client` 的单点(`call_tool` / `read_token`): 工具控制面契约只在
那里定义一次; 函数内延迟 import 规避与 tool_client 的循环依赖(它要 import 本模块用订阅编排)。
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...infra.utils import is_windows

logger = logging.getLogger(__name__)

#: 指针目录叶名与文件名(D6): 与工具侧 gtm.storage 的常量同源 —— **镜像而非 import**
#: (工具是独立包/venv, auto-qb 不 import 它); 改这里必须同步 ../tools/global-traffic-monitor。
POINTER_DIR_NAME = "global-traffic-monitor"
ENDPOINT_FILE_NAME = "endpoint.json"

#: 指针格式版本(plan §05): 读到未知值只告警不猜字段(D6) —— 不改写、不臆断
ENDPOINT_SCHEMA = 1

#: 工具根目录的仓库内默认位置(D10 ②): tool_dir 留空时的兜底(源码态)
_DEFAULT_TOOL_DIR_PARTS = ("tools", "global-traffic-monitor")

#: 启动器文件名(D19): 工具侧唯一知道「怎么起」的地方; Windows 用 .cmd, 其余用 .sh
_LAUNCHER_WINDOWS = "launch.cmd"
_LAUNCHER_POSIX = "launch.sh"

#: 单次 `GET /status` 探活的请求超时(秒): 本机回环, 正常亚毫秒级; 给足余量但不无限等
PROBE_TIMEOUT_S = 10.0

#: 拉起后等探活的窗口(秒, plan §05 默认): 首次引导 120s(含 uv 装依赖) / 常态 10s
FIRST_BOOT_WINDOW_S = 120.0
STEADY_WINDOW_S = 10.0

#: 拉起失败退避(秒, D14): **固定值**不做指数增长 —— 工具起不来多半是配置问题, 不是抖动
RELAUNCH_BACKOFF_S = 30.0


def _platform_data_home() -> str:
    """用户级数据根目录(平台惯例)单点: 镜像 gtm.storage._platform_data_home()(D6)

    Windows %LOCALAPPDATA% / macOS ~/Library/Application Support / Linux $XDG_DATA_HOME
    或 ~/.local/share。平台判定走 infra.utils 单点, 与工具侧口径一致。
    """
    if is_windows():
        return os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    return os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")


def pointer_dir() -> str:
    """发现指针所在的用户级平台目录(D6): 整机共享一处(多 auto-qb 实例发现同一工具)"""
    return os.path.join(_platform_data_home(), POINTER_DIR_NAME)


def endpoint_path() -> str:
    """发现指针 endpoint.json 的绝对路径(D6); 测试按需 monkeypatch 本函数重定向"""
    return os.path.join(pointer_dir(), ENDPOINT_FILE_NAME)


def default_tool_dir() -> str:
    """仓库内工具默认安装目录(D10 ②): tool_dir 留空时的兜底(源码态 <仓库根>/tools/...)"""
    return str(Path(__file__).resolve().parents[4].joinpath(*_DEFAULT_TOOL_DIR_PARTS))


@dataclass(frozen=True)
class ToolEndpoint:
    """指针解析出的工具控制面端点(D6/§05): 密钥与端口全部来自这里"""
    base_url: str
    token_path: str
    data_dir: str = ""
    version: str = ""
    pid: int = 0
    autostart_registered: bool = False
    # 启动期自启注册的失败原因(issue 26-10-17-1455): 指针可选字段, 缺省/旧指针 -> None
    autostart_error: Optional[str] = None


@dataclass(frozen=True)
class LaunchTarget:
    """D10 解析出的拉起目标: 可执行文件(tool_exe)或工具侧启动器脚本(D19)"""
    path: str
    is_exe: bool
    label: str


def read_pointer() -> Optional[dict]:
    """读指针载荷; 指针缺失 -> None, 读/解析失败只告警并当缺席"""
    try:
        with open(endpoint_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        logger.warning(f"读取全局流量监视器指针失败({endpoint_path()}): {e}")
        return None


def parse_pointer(payload) -> Optional[ToolEndpoint]:
    """指针载荷 -> 端点; schema 未知或关键字段缺失 -> None(只告警, 不猜字段, D6)"""
    if not isinstance(payload, dict):
        return None
    schema = payload.get("schema")
    if schema != ENDPOINT_SCHEMA:
        logger.warning(f"全局流量监视器指针 schema 非预期(读到 {schema!r}, 期望 {ENDPOINT_SCHEMA}): "
                       "不猜字段, 视为未就绪")
        return None
    host = str(payload.get("host") or "").strip()
    try:
        port = int(payload.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    token_path = str(payload.get("token_path") or "").strip()
    if not host or port <= 0 or not token_path:
        logger.warning(f"全局流量监视器指针缺关键字段(host/port/token_path): {payload}")
        return None
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    return ToolEndpoint(
        base_url=f"http://{host}:{port}",
        token_path=token_path,
        data_dir=str(payload.get("data_dir") or ""),
        version=str(payload.get("version") or ""),
        pid=pid,
        autostart_registered=bool(payload.get("autostart_registered")),
        autostart_error=(str(payload["autostart_error"]) if payload.get("autostart_error") else None),
    )


def discover() -> Optional[ToolEndpoint]:
    """只读指针(不探活) -> 端点或 None"""
    return parse_pointer(read_pointer())


def probe(timeout: float = PROBE_TIMEOUT_S) -> Optional[ToolEndpoint]:
    """读指针 + 探活(D7): 可达(200) -> 端点, 否则 None(残留指针不算就绪)"""
    ep = discover()
    if ep is None:
        return None
    # 延迟 import: tool_client 顶层要 import 本模块(订阅编排), 顶层互引会成环
    from ...webui.tool_client import ToolUnreachable, call_tool, read_token
    token = read_token(ep.token_path)
    if not token:
        logger.debug(f"全局流量监视器密钥尚未就绪({ep.token_path}): 视为未在跑")
        return None
    try:
        code, _resp = call_tool(ep.base_url, "/status", "GET", token, None, timeout)
    except ToolUnreachable:
        return None
    return ep if code == 200 else None


def resolve_launch_target(conf) -> Optional[LaunchTarget]:
    """D10 拉起解析顺序 -> 目标或 None(未安装)

    ① `tool_exe` 非空且存在 -> 直接执行该可执行文件(显式覆盖 / 编译态逃生门);
    ② 否则 `tool_dir`(空 = 仓库内默认目录)里的 D19 启动器;
    ③ 两者都找不到 -> None(UI 报「未安装」并引导写 tool_exe)。

    auto-qb **不拼 uv、不认识入口名与子命令** —— 那些全部沉在工具侧启动器里(D19)。
    """
    exe = str(getattr(conf, "tool_exe", "") or "").strip()
    if exe:
        exe = os.path.abspath(os.path.expanduser(exe))
        if os.path.isfile(exe):
            return LaunchTarget(exe, True, "tool_exe 指定的可执行文件")
    tool_dir = str(getattr(conf, "tool_dir", "") or "").strip() or default_tool_dir()
    launcher = os.path.join(os.path.expanduser(tool_dir), _LAUNCHER_WINDOWS if is_windows() else _LAUNCHER_POSIX)
    if os.path.isfile(launcher):
        return LaunchTarget(launcher, False, f"工具侧启动器({os.path.basename(launcher)})")
    return None


def launch_tool(target: LaunchTarget) -> None:
    """执行拉起目标(detached, 零参数) —— 模块级可注入单点(测试替换本函数)

    D19: Windows `cmd.exe /c <启动器>` / POSIX `/bin/sh <启动器>`; `tool_exe` 直接执行。
    就绪判据是探活(D7), 不看退出码(detached 拿不到); 自启意图恒定, 故不传任何参数(D13)。
    """
    if target.is_exe:
        args = [target.path]
    elif is_windows():
        args = ["cmd.exe", "/c", target.path]
    else:
        args = ["/bin/sh", target.path]
    kwargs = {
        "cwd": os.path.dirname(target.path) or None,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if is_windows():
        # DETACHED_PROCESS: 不继承本进程控制台(关掉 auto-qb 不带走工具)
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(args, **kwargs)


class TrafficSourceAgent:
    """探测 -> 保障可达 -> 状态(plan §05 五态)

    状态归属: `ensure_running()` 只在**订阅线程**里被调用(单写者); `status()` 只读、可由 UI
    线程随时调用 —— 读到的可能是上一轮的事实(探活是权威判据, 过期一瞬无妨)。
    """
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._pending_until = 0.0  # 已拉起等探活的截止时刻(0 = 不在等)
        self._pending_window = 0.0  # 本次等待窗口(秒), 失败文案用
        self._retry_after = 0.0  # 拉起失败退避截止
        self._fail_reason = ""  # 最近一次拉起失败原因(空 = 无)
        self._launched_once = False  # 本进程是否拉起过(定首次引导 120s / 常态 10s)
        self._last_error = ""  # 日志节流记忆(同一原因只 WARNING 一次)

    # ---------------- 订阅线程侧 ----------------

    def ensure_running(self, conf) -> Optional[ToolEndpoint]:
        """保障可达: 可达 -> 端点; 不可达 -> 按 D10/D14 拉起并返回 None(下轮再探)

        探活成功即返回(含「别的实例已拉起」—— D14: 不重复拉、不通信, 直接订阅)。
        """
        now = self._clock()
        ep = probe(PROBE_TIMEOUT_S)
        if ep is not None:
            self._pending_until = 0.0
            self._clear_error()
            return ep
        if now < self._pending_until:  # 已拉起, 探活窗口内 -> 继续等
            return None
        if self._pending_until:  # 窗口耗尽仍不可达 -> 记拉起失败并退避(D14 固定 30s)
            self._pending_until = 0.0
            self._fail_reason = f"拉起后 {self._pending_window:g}s 内未探活成功"
            self._retry_after = now + RELAUNCH_BACKOFF_S
            self._note_error(f"{self._fail_reason}({RELAUNCH_BACKOFF_S:g}s 后重试)")
            return None
        if now < self._retry_after:  # 退避中
            return None
        target = resolve_launch_target(conf)
        if target is None:
            self._fail_reason = "未安装: 工具目录与可执行文件都解析不到"
            self._retry_after = now + RELAUNCH_BACKOFF_S
            self._note_error(f"{self._fail_reason}(请在设置页指定 tool_exe)")
            return None
        window = STEADY_WINDOW_S if self._launched_once else FIRST_BOOT_WINDOW_S
        try:
            launch_tool(target)
        except OSError as e:
            self._fail_reason = f"拉起失败: {e}"
            self._retry_after = now + RELAUNCH_BACKOFF_S
            self._note_error(f"{self._fail_reason}({target.label}, {RELAUNCH_BACKOFF_S:g}s 后重试)")
            return None
        self._launched_once = True
        self._pending_until = now + window
        self._pending_window = window
        self._fail_reason = ""
        self._clear_error()
        logger.info(f"已拉起全局流量监视器({target.label}): 等探活(窗口 {window:g}s)")
        return None

    # ---------------- UI 侧(只读) ----------------

    def request_relaunch(self) -> None:
        """手动「立即拉起/重试」: 清失败记忆与退避, 下轮 ensure_running 立刻重新拉起

        !只能在**订阅线程**里被调用(单写者, 与 ensure_running 同) —— 设置页按钮经
        `TrafficMonitorSubscriber.request_relaunch` 置一个跨线程布尔标志, 订阅线程读到后调本方法,
        agent 内部状态(退避/失败原因/等待窗口)因此仍只在单一写线程里被改。
        """
        self._pending_until = 0.0
        self._retry_after = 0.0
        self._fail_reason = ""

    def status(self, conf) -> dict:
        """状态区五态(plan §05): ready / launching / launch_failed / not_running / not_installed"""
        ep = probe(PROBE_TIMEOUT_S)
        now = self._clock()
        base = {
            "endpoint": ep,
            "version": ep.version if ep else "",
            "pid": ep.pid if ep else 0,
            "data_dir": ep.data_dir if ep else "",
            "autostart_registered": ep.autostart_registered if ep else False,
            "autostart_error": ep.autostart_error if ep else None,
            "error": "",
            "retry_s": 0.0,
        }
        if ep is not None:
            return {**base, "state": "ready"}
        if resolve_launch_target(conf) is None:
            return {**base, "state": "not_installed", "error": self._fail_reason}
        if now < self._pending_until:
            return {**base, "state": "launching", "retry_s": self._pending_until - now}
        if self._fail_reason and now < self._retry_after:
            return {**base, "state": "launch_failed", "error": self._fail_reason, "retry_s": self._retry_after - now}
        return {**base, "state": "not_running"}

    # ---------------- 日志节流(同一原因只说明白一次) ----------------

    def _note_error(self, msg: str) -> None:
        """失败: 同一原因首次 WARNING, 之后同因降 DEBUG(工具没起是常态, 逐轮 WARNING 会刷屏)"""
        if msg != self._last_error:
            self._last_error = msg
            logger.warning(f"全局流量监视器联动: {msg}")
        else:
            logger.debug(f"全局流量监视器联动: {msg}")

    def _clear_error(self) -> None:
        """成功: 清失败记忆; 从失败中恢复时补一条 INFO(失败不静默消失)"""
        if self._last_error:
            logger.info(f"全局流量监视器联动已恢复(先前: {self._last_error})")
            self._last_error = ""
