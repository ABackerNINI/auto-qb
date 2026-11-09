"""按端口强杀监听进程(桩/e2e 残留清理) — dev-only

为什么是脚本而不是一行 shell: exec 会话 kill 掉的是 `uv run` 包装进程, python 子进程
不死仍占端口(判据见 memory-bank/pitfalls/testing/harness-save-flow.md); PowerShell
一行式经 PS -> cmd 批处理(commands.cmd 包装) -> 引擎多层引号不可靠(实测 2026-10-09),
落成脚本跨 shell 稳定。

用法: commands run dev.port-kill -- 8137 [8138 ...]
Usage with explicit confirm: commands run dev.port-kill -- <port> [port...] [--yes]

Kill safety (2026-11-07): every kill is gated by a Win32_Process verify first -- the
listener's name/cmdline is printed for attribution, python-like listeners (the stub
interpreters this script exists to clean) keep the old flow, non-python listeners
require explicit --yes, and a failed verify refuses to kill (fail-safe). This
scripted, attribution-checked channel is the exemption recorded under AGENTS.md's
taskkill red line; running taskkill directly in the AI shell is still banned.
"""
import json
import subprocess
import sys


def listening_pids(port: int) -> set:
    """列出正在 Listen 该端口的进程 PID(可能多个: 多 clone 并行工作区各起过桩)"""
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


def process_info(pids) -> dict:
    """Pre-kill attribution verify: pid -> (process_name, command_line).

    Same channel as listening_pids (PowerShell), this time querying Win32_Process.
    Pids the query cannot answer (raced exit / query error) are simply absent from
    the result; callers MUST treat absence as verify-failure and refuse to kill
    (fail-safe, never kill blind). P5 review item #9.
    """
    if not pids:
        return {}
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
    """Pure kill gate, called by main for every pid before taskkill (P5 review #9).

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
            k = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            detail = "killed" if k.returncode == 0 else "kill-failed: " + (k.stderr or k.stdout).strip()
            print(f"[port-kill] {port}: pid {pid} -> {detail}")
            rc |= k.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
