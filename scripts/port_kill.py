"""按端口强杀监听进程(桩/e2e 残留清理) — dev-only

为什么是脚本而不是一行 shell: exec 会话 kill 掉的是 `uv run` 包装进程, python 子进程
不死仍占端口(判据见 memory-bank/pitfalls/testing/harness-save-flow.md); PowerShell
一行式经 PS -> cmd 批处理(commands.cmd 包装) -> 引擎多层引号不可靠(实测 2026-10-09),
落成脚本跨 shell 稳定。

平台双支(issue 26-11-13-0234): 查询与实杀三步都按 os.name 分派 -- Windows 支走
PowerShell(Get-NetTCPConnection / Win32_Process) + taskkill; POSIX 支直读 /proc 零外部
依赖(/proc/net/tcp{,6} Listen 态 inode -> /proc/*/fd socket 反查 PID; comm/cmdline 取
归属), 实杀 SIGKILL。POSIX 可见性前提: 监听者与运行者同用户(桩进程恒同用户); 别用户
进程的 /proc/<pid>/fd 不可读, 表现为查不到 PID("no-listener") -- 不误报也不盲杀。

用法: commands run dev.port-kill -- 8137 [8138 ...]
Usage with explicit confirm: commands run dev.port-kill -- <port> [port...] [--yes]

Kill safety (2026-11-07): every kill is gated by an attribution verify first -- the
listener's name/cmdline is printed for attribution, python-like listeners (the stub
interpreters this script exists to clean) keep the old flow, non-python listeners
require explicit --yes, and a failed verify refuses to kill (fail-safe). This
scripted, attribution-checked channel is the exemption recorded under AGENTS.md's
taskkill red line; running taskkill directly in the AI shell is still banned. Both
platform branches sit behind the same gate (kill_decision); the verify is not
Windows-only.
"""
import json
import os
import signal
import subprocess
import sys

# POSIX 支的 /proc 根单点(守阵用假 /proc 树钉双支, 见 tests/test_legacy_review4_scripts.py)
PROC_ROOT = "/proc"
# POSIX 实杀信号单点: Windows CPython 无 signal.SIGKILL 属性 -- 生产 nt 支永不评估它,
# 但守阵把 os.name 钉成 posix 会在 nt 宿主激活本支, getattr 兜 9(SIGKILL 的 POSIX 数值)
_SIGKILL = getattr(signal, "SIGKILL", 9)


def listening_pids(port: int) -> set:
    """列出正在 Listen 该端口的进程 PID(可能多个: 多 clone 并行工作区各起过桩)

    按 os.name 分派: nt 走 PowerShell(Get-NetTCPConnection), 其余走 /proc 直读
    (_listening_pids_posix); 两支判据一致 = 正在 Listen 该端口的 PID 集合。
    """
    if os.name != "nt":
        return _listening_pids_posix(port)
    ps = (
        f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue; "
        "if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { $_.ToString() } }"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {int(x) for x in r.stdout.split() if x.strip().isdigit()}


def _listening_pids_posix(port: int) -> set:
    """/proc 直读: /proc/net/tcp{,6} 的 Listen 态(st=0A)inode -> /proc/*/fd socket 反查 PID.

    别用户进程的 fd 目录不可读 -> 跳过(该监听查不到, 返回值可能偏少); IPv6 关闭时
    /proc/net/tcp6 不存在 -> 跳过。其余语义与 Windows 支一致: 只报 Listen 态, 不含
    TIME_WAIT 等残留。
    """
    inodes = set()
    for name in ("tcp", "tcp6"):
        try:
            with open(PROC_ROOT + "/net/" + name, "r", encoding="ascii") as fh:
                for line in fh:
                    parts = line.split()
                    # 列序: sl local_address rem_address st ... inode(第10列); st=0A 即 LISTEN
                    if len(parts) < 10 or parts[3] != "0A":
                        continue
                    hex_port = parts[1].rpartition(":")[2]
                    try:
                        if int(hex_port, 16) != port:
                            continue
                    except ValueError:
                        continue
                    inodes.add(parts[9])
        except OSError:
            continue
    if not inodes:
        return set()
    pids = set()
    for entry in os.listdir(PROC_ROOT):
        if not entry.isdigit():
            continue
        fd_dir = PROC_ROOT + "/" + entry + "/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(fd_dir + "/" + fd)
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                pids.add(int(entry))
                break
    return pids


def process_info(pids) -> dict:
    """Pre-kill attribution verify: pid -> (process_name, command_line).

    Same channel as listening_pids, dispatched by os.name: nt queries Win32_Process
    via PowerShell; elsewhere /proc/<pid>/comm + cmdline are read directly. Pids the
    query cannot answer (raced exit / query error) are simply absent from the
    result on BOTH branches; callers MUST treat absence as verify-failure and refuse
    to kill (fail-safe, never kill blind). P5 review item #9.
    """
    if not pids:
        return {}
    if os.name != "nt":
        return _process_info_posix(pids)
    filt = " or ".join("ProcessId=" + str(int(p)) for p in pids)
    ps = (
        '$r = Get-CimInstance Win32_Process -Filter "' + filt + '" | '
        "Select-Object ProcessId,Name,CommandLine; "
        "ConvertTo-Json -InputObject @($r) -Compress"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return {}
    if isinstance(data, dict):  # some PS hosts unwrap a single-element array
        data = [data]
    infos = {}
    for row in data or []:
        pid = row.get("ProcessId")
        name = row.get("Name")
        if pid is None or not name:
            continue
        infos[int(pid)] = (str(name), str(row.get("CommandLine") or ""))
    return infos


def _process_info_posix(pids) -> dict:
    """POSIX 支: /proc/<pid>/comm + /proc/<pid>/cmdline 取 (name, cmdline).

    comm 是去路径短名(python3 / python3.13 / uv, 无 .exe 后缀), _is_python_listener
    对两种形态同样成立; cmdline 内核以 NUL 分隔 argv, 这里拼回空格(等价 Windows
    CommandLine)。读不了的 pid 缺席 = verify-failure(调用方拒杀, 与 Windows 支同语义)。
    """
    infos = {}
    for pid in pids:
        pid = int(pid)
        try:
            with open(PROC_ROOT + "/" + str(pid) + "/comm", "r", encoding="utf-8", errors="replace") as fh:
                name = fh.read().strip()
            with open(PROC_ROOT + "/" + str(pid) + "/cmdline", "rb") as fh:
                cmdline = fh.read().decode("utf-8", "replace").replace("\0", " ").strip()
        except OSError:
            continue
        if name:
            infos[pid] = (name, cmdline)
    return infos


def _is_python_listener(name: str, cmdline: str) -> bool:
    """python-like listener = the dev/e2e stub interpreters this script cleans up.

    Judgment is deliberately narrow (anything unrecognized must go through --yes):
    - bare interpreter images whose name starts with "python" (python.exe /
      pythonw.exe / python3.x.exe; case-insensitive, extension stripped)
    - uv.exe whose command line runs python (`uv run python ...`): the wrapper
      owning the stub session
    Browsers, qBittorrent, editors and any other app are NOT python-like.
    """
    base = str(name).strip().lower()
    if "." in base:
        base = base.rsplit(".", 1)[0]
    if base.startswith("python"):
        return True
    return base == "uv" and "python" in str(cmdline).lower()


def kill_decision(info, confirmed: bool):
    """Pure kill gate, called by main for every pid before the kill (_kill_pid, both
    platform branches; P5 review #9).

    info: (process_name, command_line) from process_info; None when the verify
    query failed or the pid vanished -- always refuse (fail-safe).
    confirmed: whether the operator passed --yes (default off: high-risk action,
    AGENTS.md golden rule 2).

    Returns (allowed, reason); reason is ASCII and printable as-is, and for
    refusals explains why plus how to confirm explicitly.
    """
    if info is None:
        return False, "verify-failed: no process info (query failed or pid exited); refusing to kill blind"
    name, cmdline = info
    if _is_python_listener(name, cmdline):
        return True, "python-listener"
    if not confirmed:
        return False, (
            "non-python listener; refusing without explicit confirmation"
            " -- re-run with --yes after checking the attribution line above"
        )
    return True, "non-python listener, explicit --yes given"


def _kill_pid(pid: int) -> tuple:
    """实杀单点(按 os.name 分派): Windows taskkill /F /PID, POSIX SIGKILL。

    归属闸(kill_decision)在调用方先过, 两平台同闸; 返回 (ok, detail), ok=False 时
    detail 以 "kill-failed: " 开头并带可读原因(与旧 taskkill rc!=0 输出形态一致)。
    """
    if os.name == "nt":
        k = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if k.returncode == 0:
            return True, "killed"
        return False, "kill-failed: " + (k.stderr or k.stdout).strip()
    try:
        os.kill(pid, _SIGKILL)
    except ProcessLookupError:
        return False, "kill-failed: no such process (already exited)"
    except PermissionError:
        return False, "kill-failed: permission denied"
    return True, "killed"


def main(argv: list) -> int:
    confirmed = "--yes" in argv
    ports = [int(a) for a in argv if a.strip().isdigit()]
    if not ports:
        print("usage: commands run dev.port-kill -- <port> [port...] [--yes]")
        return 2
    rc = 0
    for port in ports:
        pids = listening_pids(port)
        if not pids:
            print(f"[port-kill] {port}: no-listener")
            continue
        infos = process_info(pids)
        for pid in sorted(pids):
            info = infos.get(pid)  # absent = verify failed -> kill_decision refuses
            if info is not None:
                name, cmdline = info
                if len(cmdline) > 160:
                    cmdline = cmdline[:157] + "..."
                print(f"[port-kill] {port}: pid {pid} = {name} : {cmdline}")
            ok, why = kill_decision(info, confirmed)
            if not ok:
                print(f"[port-kill] {port}: pid {pid} -> REFUSED: {why}")
                rc = 1
                continue
            ok, detail = _kill_pid(pid)
            print(f"[port-kill] {port}: pid {pid} -> {detail}")
            if not ok:
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
