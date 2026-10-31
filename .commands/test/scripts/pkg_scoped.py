"""test.pkg.scoped —— 提交闸门的按包收窄执行器(计划 memory-bank/plans/26-11-01-0434 方案 C)。

用法(提交闸门两条 run, 经 commands 引擎调进来):
    run.py run test.pkg.scoped -- <changed:.commands/**>                      → 归并受影响包
    run.py run test.pkg.scoped --full -- <changed:.agents/skills/commands/**> → 引擎改动, 整跑

归并规则(D4, 2026-11-01 拍板): 改动文件按 `.commands/<包>/` 前缀归并出受影响包集合 ——
单包 → 只跑该包(`uv run pytest .commands/<包> -q --no-cov -n 8`, TMPDIR 在此内置, 不走
cmd.exe 引号配方); ≥2 包或 --full → 转调 `run.py run test.pkg`(TMPDIR/写法配方单点在
test 包, 这里不抄第二份; 引擎测试贴着引擎放, 改引擎永远全跑); 0 包 → 静默 rc 0
(闸门 `<changed:>` 无匹配本应整条跳过, 这里只兜底)。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # .commands/test/scripts/ → 仓库根
RUN_PY = REPO_ROOT / ".agents" / "skills" / "commands" / "scripts" / "run.py"
# 与 test 包 config.toml 同源的本机约定(H:\Temp 是坏默认, symlink 陷阱见
# memory-bank/pitfalls/testing/tmpdir.md); scoped 的 pytest 子进程用, 转调 test.pkg 时不碰
# (配方在 task 定义里)。
TMPDIR = r"R:\Temp\auto-qb\tests"


def plan(argv: list[str]) -> tuple[bool, list[str]]:
    """argv → (是否整跑, 受影响包名列表[排序去重])。纯函数, 便于单测。"""
    full = "--full" in argv
    pkgs: set[str] = set()
    for a in argv:
        if a in ("--full", "--"):
            continue
        parts = a.replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[0] == ".commands" and parts[1]:
            pkgs.add(parts[1])
    return full, sorted(pkgs)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    full, pkgs = plan(argv)
    if full or len(pkgs) >= 2:  # D4: 引擎必整跑; 受影响包 ≥2 保守整跑
        if not RUN_PY.is_file():
            print(f"[STOP] 找不到引擎 run.py: {RUN_PY}", file=sys.stderr)
            return 2
        return subprocess.run([sys.executable, str(RUN_PY), "run", "test.pkg"]).returncode
    if not pkgs:
        return 0
    target = f".commands/{pkgs[0]}"
    env = dict(os.environ)
    try:
        Path(TMPDIR).mkdir(parents=True, exist_ok=True)
        env["TMPDIR"] = TMPDIR
    except OSError:
        print(f"[WARN] TMPDIR {TMPDIR} 建不了, 沿用环境默认(symlink 陷阱见 memory-bank/pitfalls/testing/tmpdir.md)")
    print(f"[pkg.scoped] 受影响包: {pkgs[0]} → 只跑 {target}")
    proc = subprocess.run(
        ["uv", "run", "pytest", target, "-q", "--no-cov", "-n", "8"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
