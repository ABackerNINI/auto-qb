"""e2e/冒烟环境开机自检(dev-only, 只读不动手) —— issue 26-10-31-2226-feat-e2e-smoke-env-selfcheck。

把 smoke.md 的三类高频环境条目从「读文档排障」搬进工具: 在 `dev.e2e` 进 spec 之前
当场探测, 不过就打印修复动作(NEXT:)并退非 0 —— commands 引擎对 run 列表逐条执行、
任一条非 0 即整任务 FAIL, 所以把它挂进 dev.e2e run 列表头部即「自检不过不进 spec」。

三查(判据单点: memory-bank/pitfalls/testing/smoke.md):
1. node_modules/@playwright/test 在位 —— 多 clone 工作区 node_modules/ 不跟 git 走,
   新 clone 从未 npm i 时 npx 会自作主张装错包(playwright 而非 @playwright/test),
   报错对象与真实病因差一层。
2. e2e 端口(默认 8137, 随 E2E_PORT)监听占用 —— playwright.config reuseExistingServer=false,
   占用即起不来; 且 uvicorn 端口被占只打一行 [Errno 10048] 就退出, 报错面极差。
3. 8099(人工桩惯用值)残留监听告警 —— 多 clone 下反复被别会话/别 clone 的残留 harness 占用。
   默认仅告警不拦(e2e 轨不用 8099); `--blocking 8099` 可给 dev.harness 做同款前置。

占用归属判定**不走 curl**: 本环境有透明代理, curl 直连被占端口拿到代理 502, 判据不可靠
(smoke.md 已记); 一律 Get-NetTCPConnection 现查 PID + Win32_Process.CommandLine ——
命令行里带 clone 路径, "旧桩是哪个 clone 的"一眼可判, 不猜。

用法:
    commands run dev.e2e-check                  # 单跑(默认: blocking=E2E_PORT||8137, warn=8099)
    python scripts/e2e_selfcheck.py --blocking 8099 --warn ""   # dev.harness 口径
退出码: 0 全过 / 1 有拦断面不过(修复动作在 NEXT: 行)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from port_kill import listening_pids  # noqa: E402  (端口探测单点, dev.port-kill 同源)

DEFAULT_E2E_PORT = "8137"
DEFAULT_WARN_PORTS = "8099"
# 命令行里抓 clone 路径段(多 clone 工作区 ../auto-qb-* 平级, 残留桩归属一眼可判)
CLONE_HINT_RE = re.compile(r"[A-Za-z]:\\[^\"']*auto-qb[^\"']*")


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _proc_info(pid: int) -> tuple[str, str]:
    """(进程名, 命令行摘要) —— Get-CimInstance 一次查一个 PID; 查不到给占位。"""
    ps = (
        f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' -ErrorAction SilentlyContinue; "
        "if ($p) { Write-Output ($p.Name + '|' + $p.CommandLine) }"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    out = (r.stdout or "").strip()
    if "|" in out:
        name, _, cmdline = out.partition("|")
        hint = CLONE_HINT_RE.search(cmdline or "")
        summary = hint.group(0) if hint else (cmdline or "").strip()[:160]
        return name, summary
    return "?", "(命令行不可读)"


def _check_node_modules(root: Path, problems: list[str], notes: list[str]) -> None:
    nm = root / "node_modules"
    pkg = nm / "@playwright" / "test"
    if not nm.is_dir() or not any(nm.iterdir()):
        problems.append(
            "node_modules 缺失/为空 —— 本 clone 未 npm i(npm i 不跟 git 走, 每 clone 各装一次)\n"
            "  NEXT: npm i --no-save @playwright/test@1.63.0 (10s 内装完, --no-save 免改 package.json)"
        )
        return
    if not pkg.is_dir():
        problems.append(
            "node_modules/@playwright/test 缺失 —— npx 会自作主张装 playwright 包(不是配置要的), "
            "报错对象与真实病因差一层(smoke.md「Playwright 从哪来」条)\n"
            "  NEXT: npm i --no-save @playwright/test@1.63.0"
        )
        return
    notes.append(f"node_modules 在位 ({len(list(nm.iterdir()))} 项, @playwright/test 已装)")


def _check_port(port: int, blocking: bool, problems: list[str], notes: list[str]) -> None:
    pids = listening_pids(port)
    tag = "blocking" if blocking else "warn"
    if not pids:
        notes.append(f"端口 {port} 无监听 ({tag})")
        return
    lines = [f"端口 {port} 已被占用 ({tag}) —— uvicorn 起不来只打 [Errno 10048] 一行, 先看这里:"]
    for pid in sorted(pids):
        name, summary = _proc_info(pid)
        lines.append(f"  pid {pid} {name}: {summary}")
    if blocking:
        lines.append(
            "  NEXT: commands run dev.port-kill -- " + str(port) +
            " (确认别 clone 的桩已无用再杀; 不确定就用 E2E_PORT=<空闲端口> commands run dev.e2e 排障复跑)"
        )
    else:
        lines.append(
            "  提示: 8099 是人工桩惯用值, 多 clone 下常是别会话残留 harness —— "
            "手看页面前先确认归属(别验错对象); 清理: commands run dev.port-kill -- 8099"
        )
    (problems if blocking else notes).append("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    args = [a for a in (argv if argv is not None else sys.argv[1:])]
    blocking_raw = DEFAULT_E2E_PORT
    warn_raw = DEFAULT_WARN_PORTS
    i = 0
    while i < len(args):
        if args[i] == "--blocking":
            blocking_raw = args[i + 1]
            i += 2
        elif args[i] == "--warn":
            warn_raw = args[i + 1]
            i += 2
        else:
            print(f"未知参数: {args[i]} (支持 --blocking <ports> / --warn <ports>, 逗号分隔, 空串关闭)")
            return 2
    root = Path(__file__).resolve().parents[1]
    e2e_port = int(os.environ.get("E2E_PORT") or blocking_raw)
    blocking_ports = [p for p in (e2e_port, ) if p]
    warn_ports = [int(p) for p in warn_raw.split(",") if p.strip().isdigit()]
    # blocking 显式传参时以传参为准(E2E_PORT 只在未传参时作默认)
    if "--blocking" in args:
        blocking_ports = [int(p) for p in blocking_raw.split(",") if p.strip().isdigit()]

    problems: list[str] = []
    notes: list[str] = []
    _check_node_modules(root, problems, notes)
    for port in blocking_ports:
        _check_port(port, blocking=True, problems=problems, notes=notes)
    for port in warn_ports:
        if port in blocking_ports:
            continue  # 已在拦断面报过, 不重复念
        _check_port(port, blocking=False, problems=problems, notes=notes)

    for n in notes:
        print(f"[ok] {n}")
    if problems:
        for p in problems:
            print(f"WHY: {p}")
        print("RESULT: 环境自检未过 —— 不进 spec, 按 NEXT: 修复后重跑 (判据: memory-bank/pitfalls/testing/smoke.md)")
        return 1
    print("RESULT: 环境自检通过 (node_modules 在位; 拦断端口无占用; 8099 无残留)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
