"""真机实测轨的运行入口 —— 被 `.commands/real` 包按 task id 调, 不直接手敲。

设计口径:
  - **默认 dry-run**: 任何会改 qB / 起停进程的动作用例, 不给 `--yes` 就只打印将要发生什么;
  - **守卫先行**: `guard` 不过就非 0 退出, 没有 --force 逃生门(逃生门就是下一次事故);
  - **不挂闸门**: 本脚本永不被 `ship.commit` / `test.full` 调用, 它是人按排期跑的。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib import guard, instances  # noqa: E402

CASE_RE = re.compile(r"\[(RM\d{2}-\d{2})\]\s*(.+)")


def _qb(port: int):
    return instances.make(port)


def _ports(value: str) -> list[int]:
    if value == "all":
        return list(guard.WHITELIST_PORTS)
    port = int(value)
    if port not in guard.WHITELIST_PORTS:
        raise SystemExit(f"端口 {port} 不在白名单 {guard.WHITELIST_PORTS} —— 拒跑")
    return [port]


def _wait_port(port: int, timeout: float = 40.0) -> bool:
    import socket

    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def cmd_guard(args) -> int:
    rc = 0
    for port in _ports(args.port):
        try:
            rep = guard.check_port(port)
            qb = _qb(port)
            version = qb.version()
            status = guard.check_online(qb)
            hashes = guard.snapshot(qb)
            print(f"[ok] {port} pid={rep['pid']} v{version} {status} 真实种子 {len(hashes)} 个, 已全部暂停")
        except Exception as exc:
            rc = 1
            print(f"[FAIL] {port}: {exc}")
    return rc


def cmd_pause_all(args) -> int:
    rc = 0
    for port in _ports(args.port):
        try:
            qb = _qb(port)
            hashes = guard.snapshot(qb)
            print(f"[ok] {port} 暂停 {len(hashes)} 个种子")
        except Exception as exc:
            rc = 1
            print(f"[FAIL] {port}: {exc}")
    return rc


def cmd_up(args) -> int:
    for port in _ports(args.port):
        if _wait_port(port, timeout=0.5):
            print(f"[skip] {port} 已在监听")
            continue
        exe = guard.EXE[port]
        if args.dry_run:
            print(f"[dry-run] 将启动 {exe}")
            continue
        # 必须经 explorer 拉起: 工具 shell 里 Start-Process / cmd start 起的进程会随命令结束被杀
        subprocess.run(["explorer.exe", exe], check=False)
        ok = _wait_port(port)
        print(f"[{'ok' if ok else 'FAIL'}] {port} 启动{'成功' if ok else '超时(40s)'}")
        if not ok:
            return 1
    return 0


def cmd_down(args) -> int:
    for port in _ports(args.port):
        if args.dry_run:
            print(f"[dry-run] 将关闭 {port} 的实例({guard.EXE[port]})")
            continue
        ps = (
            "Get-Process qbittorrent -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.Path -eq '{guard.EXE[port]}' }} | "
            "ForEach-Object { Stop-Process -Id $_.Id -Force; $_.Id }"
        )
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
        killed = [x for x in (r.stdout or "").split() if x.strip().isdigit()]
        print(f"[{'ok' if killed else 'skip'}] {port} 关闭 pid={killed or '无(未在跑)'}")
    return 0


def _cases() -> list[tuple[str, str, str]]:
    """扫 tests-real/**/*.py, 从 docstring 首行的 `[RMxx-nn] 标题` 抽用例表。"""
    out = []
    for path in sorted(HERE.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        for m in CASE_RE.finditer(text):
            out.append((m.group(1), m.group(2).strip(), str(path.relative_to(HERE))))
    return out


def cmd_list(args) -> int:
    rows = _cases()
    if not rows:
        print("(没有用例)")
        return 0
    print(f"{'id':<9}{'文件':<34}标题")
    for cid, title, rel in rows:
        print(f"{cid:<9}{rel:<34}{title}")
    print(f"\n共 {len(rows)} 条")
    return 0


def _pytest(target: list[str], extra: list[str]) -> int:
    cmd = ["uv", "run", "pytest", *target, "-q", "--no-cov", "-p", "no:cacheprovider", "-n", "0", *extra]
    print("[cmd] " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(HERE.parent), env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode


def cmd_run(args) -> int:
    rows = {cid: (title, rel) for cid, title, rel in _cases()}
    if args.case not in rows:
        print(f"未知用例 {args.case}; 先 real.list 看清单")
        return 2
    title, rel = rows[args.case]
    key = args.case.lower().replace("-", "_")
    print(f"[case] {args.case} {title}  ({rel})")
    if not args.yes:
        print("[dry-run] 加 --yes 才真跑(会改 qB 状态 / 起停进程)")
        return 0
    return _pytest([str(HERE / rel)], ["-k", key])


def cmd_suite(args) -> int:
    slice_id = args.slice.upper()
    files = sorted({rel for cid, _t, rel in _cases() if cid.startswith(slice_id + "-")})
    if not files:
        print(f"片 {slice_id} 下没有用例")
        return 2
    print(f"[slice] {slice_id} → {len(files)} 个文件")
    if not args.yes:
        print("[dry-run] 加 --yes 才真跑")
        return 0
    return _pytest([str(HERE / f) for f in files], [])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="real-runner", description="真机实测轨运行入口")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("guard", help="三层守卫自检(白名单 + 种子归零)")
    p.add_argument("--port", default="all")
    p.set_defaults(fn=cmd_guard)

    p = sub.add_parser("pause-all", help="暂停目标实例全部种子")
    p.add_argument("--port", default="all")
    p.set_defaults(fn=cmd_pause_all)

    for name, fn, text in (("up", cmd_up, "启动白名单实例(经 explorer, 不会被工具 shell 连带杀掉)"),
                           ("down", cmd_down, "关闭白名单实例")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--port", default="all")
        p.add_argument("--dry-run", action="store_true")
        p.set_defaults(fn=fn)

    p = sub.add_parser("list", help="列出全部用例(id / 文件 / 标题)")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("run", help="跑单条用例")
    p.add_argument("--case", required=True)
    p.add_argument("--yes", action="store_true", help="真跑(默认 dry-run)")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("suite", help="跑一片全部用例")
    p.add_argument("--slice", required=True, help="如 RM00")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_suite)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
