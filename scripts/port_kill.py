"""按端口强杀监听进程(桩/e2e 残留清理) — dev-only

为什么是脚本而不是一行 shell: exec 会话 kill 掉的是 `uv run` 包装进程, python 子进程
不死仍占端口(判据见 memory-bank/pitfalls/testing/harness-save-flow.md); PowerShell
一行式经 PS -> cmd 批处理(commands.cmd 包装) -> 引擎多层引号不可靠(实测 2026-10-09),
落成脚本跨 shell 稳定。

用法: commands run dev.port-kill -- 8137 [8138 ...]
"""
import subprocess
import sys


def listening_pids(port: int) -> set:
    """列出正在 Listen 该端口的进程 PID(可能多个: 多 clone 并行工作区各起过桩)"""
    ps = (
        f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue; "
        "if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { $_.ToString() } }"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return {int(x) for x in r.stdout.split() if x.strip().isdigit()}


def main(argv: list) -> int:
    ports = [int(a) for a in argv if a.strip().isdigit()]
    if not ports:
        print("usage: commands run dev.port-kill -- <port> [port...]")
        return 2
    rc = 0
    for port in ports:
        pids = listening_pids(port)
        if not pids:
            print(f"[port-kill] {port}: no-listener")
            continue
        for pid in sorted(pids):
            k = subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, text=True)
            detail = "killed" if k.returncode == 0 else "kill-failed: " + (k.stderr or k.stdout).strip()
            print(f"[port-kill] {port}: pid {pid} -> {detail}")
            rc |= k.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
