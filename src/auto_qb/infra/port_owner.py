"""端口占用者探针: 三平台定位监听某端口的进程(pid / 进程名 / 命令行)

用途(计划 26-11-03-0930 §4.4): WebUI 启动期监听失败时的旁路诊断 —— 结果只进日志文件,
绝不参与退出判定, 也不进 WebUIBindError 消息 / stderr / notify_fatal 内容。

设计:
- 三态且不抛错: found / absent / unavailable。命令缺失、权限不足、超时、输出不可解析
  一律降级为 unavailable(带原因), 调用方永远拿到一个 PortProbe。
- 超时: 每步 0.5s(Linux 的 ss / lsof、macOS 的 lsof / ps), Windows 的单次 PowerShell 1.0s;
  总硬预算 1.5s —— 每步实际 timeout 由剩余预算截断, 超时由 subprocess.run 杀掉子进程。
- Linux 优先 `ss -ltnp`(失败回退 `lsof`), 命令行直读 `/proc/<pid>/cmdline`(不再 spawn);
  Windows 用一次 PowerShell 合并 Get-NetTCPConnection + Get-CimInstance(输出 pid|name|cmdline);
  macOS 先用 `lsof` 取 pid, 再 `ps -o command= -p` 取命令行。
- 命令行可能含凭据: 换行压成空格并截断到 160 字符; 本模块只返回结构, 落不落日志由调用方定。

依赖纪律: infra 只被依赖 —— 本模块只 import 标准库与 .utils(平台判定走 utils.is_* 单点)。
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass

from .utils import is_linux, is_mac, is_windows

logger = logging.getLogger(__name__)

#: Linux/macOS 每个平台命令的硬超时
STEP_TIMEOUT_S = 0.5
#: Windows 单次 PowerShell 的硬超时(启动开销大, 给 1.0s)
WINDOWS_STEP_TIMEOUT_S = 1.0
#: 一次 describe_port_owner 的总硬预算上限
TOTAL_BUDGET_S = 1.5
#: 命令行落日志前的截断长度(可能含凭据)
CMDLINE_MAX_LEN = 160

STATE_FOUND = "found"
STATE_ABSENT = "absent"
STATE_UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class PortOwner:
    """监听端口的进程: pid / 进程名 / 命令行"""
    pid: int
    name: str
    cmdline: str


@dataclass(frozen=True, slots=True)
class PortProbe:
    """探针三态结果: found(带 owner) / absent(无监听者) / unavailable(未识别, 带原因)"""
    state: str
    owner: PortOwner | None = None
    reason: str = ""

    @classmethod
    def found(cls, owner: PortOwner) -> PortProbe:
        return cls(STATE_FOUND, owner)

    @classmethod
    def absent(cls) -> PortProbe:
        return cls(STATE_ABSENT)

    @classmethod
    def unavailable(cls, reason: str) -> PortProbe:
        return cls(STATE_UNAVAILABLE, None, reason)


def describe_port_owner(host: str, port: int, budget: float = TOTAL_BUDGET_S) -> PortProbe:
    """查询监听 host:port 的进程; 永不抛出, 任何失败都降级为 unavailable。

    host 只为调用方语义保留: 平台命令都按端口过滤(ss -ltnp / lsof -iTCP:<port> /
    Get-NetTCPConnection -LocalPort), 因为通配监听(0.0.0.0 / [::])同样会占用该端口,
    再按 host 筛会漏掉它们。
    """
    deadline = time.monotonic() + budget
    try:
        if is_windows():
            return _probe_windows(port, deadline)
        if is_mac():
            return _probe_macos(port, deadline)
        if is_linux():
            return _probe_linux(port, deadline)
        return PortProbe.unavailable("不支持的平台(仅 Windows / Linux / macOS)")
    except Exception as exc:  # 探针是旁路: 任何异常都不得影响调用方
        logger.debug("端口占用者探针异常: %s", exc)
        return PortProbe.unavailable(f"查询异常: {exc}")


def _remaining(deadline: float) -> float:
    return deadline - time.monotonic()


def _run(cmd: list[str], step_timeout: float, deadline: float) -> subprocess.CompletedProcess | None:
    """跑一条平台命令; 失败/超时返回 None(超时由 subprocess.run 杀掉子进程), 不抛出。

    实际超时取「单步上限」与「剩余总预算」的较小值 —— 这是总预算 1.5s 的机械保证。
    """
    timeout = min(step_timeout, _remaining(deadline))
    if timeout <= 0:
        logger.debug("端口占用者探针预算耗尽, 跳过: %s", cmd[0])
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("端口占用者探针命令失败(%s): %s", cmd[0], exc)
        return None


def _clean_cmdline(text: str) -> str:
    """命令行落日志前的安全整形: 换行压空格 + 截断到 CMDLINE_MAX_LEN"""
    return re.sub(r"[\r\n]+", " ", text).strip()[:CMDLINE_MAX_LEN]


def _read_proc_cmdline(pid: int) -> str:
    """Linux: 直读 /proc/<pid>/cmdline(NUL 分隔), 读不到返回空串(进程名仍可用)"""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        logger.debug("读取 /proc/%s/cmdline 失败: %s", pid, exc)
        return ""
    return _clean_cmdline(raw.replace(b"\x00", b" ").decode("utf-8", errors="replace"))


def _parse_ss(text: str, port: int) -> tuple[bool, PortOwner | None]:
    """解析 `ss -ltnp`: (是否命中该端口, owner)。

    命中但输出没有 pid=(非 root 时 ss 不显示 process 列)时返回 (True, None) —— 那是权限
    问题, 不能当成「没人占」。
    """
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != "LISTEN":
            continue
        if parts[3].rsplit(":", 1)[-1] != str(port):
            continue
        pid_match = re.search(r"pid=(\d+)", line)
        if pid_match is None:
            return True, None
        name_match = re.search(r'\("([^"]*)"', line)
        return True, PortOwner(int(pid_match.group(1)), name_match.group(1) if name_match else "", "")
    return False, None


def _probe_linux(port: int, deadline: float) -> PortProbe:
    proc = _run(["ss", "-ltnp"], STEP_TIMEOUT_S, deadline)
    if proc is not None and proc.returncode == 0:
        matched, owner = _parse_ss(proc.stdout or "", port)
        if owner is None:
            if matched:
                return PortProbe.unavailable("ss 命中端口但未给出 pid(权限不足?)")
            return PortProbe.absent()
        return PortProbe.found(PortOwner(owner.pid, owner.name, _read_proc_cmdline(owner.pid)))
    # ss 不可用/非零退出 -> lsof 回退
    return _probe_lsof(port, deadline)


def _parse_lsof(text: str, port: int) -> PortOwner | None:
    """解析 lsof 表: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME(按端口命中的首个 pid)"""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[1].isdigit():
            continue  # 表头
        if not any(part.rsplit(":", 1)[-1] == str(port) for part in parts[2:]):
            continue
        return PortOwner(int(parts[1]), parts[0], "")
    return None


def _probe_lsof(port: int, deadline: float) -> PortProbe:
    proc = _run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], STEP_TIMEOUT_S, deadline)
    if proc is None:
        return PortProbe.unavailable("lsof 不可用或查询超时")
    stdout = proc.stdout or ""
    if proc.returncode == 1 and not stdout.strip():
        return PortProbe.absent()  # lsof 的「无匹配」退出码
    if proc.returncode != 0:
        return PortProbe.unavailable(f"lsof 退出码 {proc.returncode}")
    owner = _parse_lsof(stdout, port)
    if owner is None:
        return PortProbe.unavailable("lsof 输出不可解析") if stdout.strip() else PortProbe.absent()
    return PortProbe.found(owner)


def _probe_macos(port: int, deadline: float) -> PortProbe:
    probe = _probe_lsof(port, deadline)
    if probe.state != STATE_FOUND:
        return probe
    owner = probe.owner
    ps = _run(["ps", "-o", "command=", "-p", str(owner.pid)], STEP_TIMEOUT_S, deadline)
    cmdline = (ps.stdout or "").strip() if ps is not None and ps.returncode == 0 else ""
    return PortProbe.found(PortOwner(owner.pid, owner.name, _clean_cmdline(cmdline)))


def _windows_script(port: int) -> str:
    """单次 PowerShell: 一次取监听 pid + 进程名 + 命令行, 输出 pid|name|cmdline"""
    return (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        f"$ids = Get-NetTCPConnection -LocalPort {port} -State Listen | "
        "Select-Object -ExpandProperty OwningProcess -Unique; "
        "foreach ($procId in $ids) { "
        "$p = Get-CimInstance Win32_Process -Filter \"ProcessId = $procId\"; "
        "if ($p) { '{0}|{1}|{2}' -f $procId, $p.Name, ($p.CommandLine -replace '[\\r\\n]+', ' ') } "
        "else { '{0}||' -f $procId } }"
    )


def _probe_windows(port: int, deadline: float) -> PortProbe:
    proc = _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         _windows_script(port)], WINDOWS_STEP_TIMEOUT_S, deadline
    )
    if proc is None:
        return PortProbe.unavailable("PowerShell 不可用或查询超时")
    if proc.returncode != 0:
        return PortProbe.unavailable(f"PowerShell 退出码 {proc.returncode}")
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        return PortProbe.absent()  # 命令成功且无监听者
    parts = lines[0].split("|", 2)
    if len(parts) < 2 or not parts[0].strip().isdigit():
        return PortProbe.unavailable("PowerShell 输出不可解析")
    cmdline = parts[2] if len(parts) > 2 else ""
    return PortProbe.found(PortOwner(int(parts[0].strip()), parts[1].strip(), _clean_cmdline(cmdline)))
