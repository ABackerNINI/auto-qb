#!/usr/bin/env python3
"""提交前检查「IDE 上下文注入上限」—— 超限的文件尾部会被**静默截断**, 写了等于没写。

背景 (2026-09-20 取证)
----------------------
IDE 注入项目引导文件时, 超出 `MAX_GUIDANCE_CHARS`(8000) 的部分会被 `slice(0, 8000)` 掉并追加
`\n[...too long, omitted...]` —— **模型根本看不到尾部**。规则写在 AGENTS.md 靠后的位置却一直
不生效, 就是这个原因。所以这条上限必须有闸门, 不能靠自觉。

为什么是项目脚本而不是 skill
----------------------------
`my-commit-flow` 是**通用 skill**, 不该内置"本仓库哪个文件受限、上限多少"这类项目专属值,
所以闸门逻辑落在这里; 而本脚本**是**项目脚本, 上限直接写死在下面的 `CONTEXT_CAPS` 里 ——
项目专属值放在项目脚本中本来就是合适的。

用法
----
    python scripts/check_context_caps.py             # 超限且本次改了它 → 退出码 1(提交前跑这个)
    python scripts/check_context_caps.py --strict    # 只要超限就退出码 1(不管本次有没有改)
    python scripts/check_context_caps.py --quiet     # 只打印非 PASS 项
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 上下文字符上限 —— 直接写死(本脚本是项目脚本, 不是通用 skill)。
# key = 仓库根相对路径, value = 最大**字符**数(不是字节)。
# AGENTS.md 的依据: IDE 注入项目引导文件时 MAX_GUIDANCE_CHARS = 8000, 超出部分被 slice 掉;
# 引导文件按 GUIDANCE_FILES = [CODEBUDDY.md, .codebuddy/CODEBUDDY.md, AGENTS.md] 首个存在即停 ——
# 本仓库前两个都不存在, 项目引导实际走 AGENTS.md。**改这里前先确认 IDE 常量没变。**
# commands 的 SKILL.md 依据不同: 它不走 IDE 注入, 而是**每次加载 skill 都要进上下文** ——
# 它本该是"恒定大小"的文档, 没有硬上限就会被自己慢慢撑大, "省 token"的初衷先被它吃掉。
# 2026-09-24 把收录协议的细节搬去 references/howto-add-command.md 后, 上限从 4200 收到 2600
# (当时实测 ~2140 含 CRLF, 留 ~20% 余量)—— 上限跟着实测收, 才叫"恒定大小"。
CONTEXT_CAPS: dict[str, int] = {
    "AGENTS.md": 8000,
    ".agents/skills/commands/SKILL.md": 2600,
}

PASS, WARN, STOP = "PASS", "WARN", "STOP"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    # 只能 rstrip: `git status --porcelain` 每行前两列是状态位, 未暂存改动的行以空格开头
    # (` M AGENTS.md`)。对整段 stdout 做 .strip() 会吃掉**第一行**的行首空格, 后面的
    # `line[3:]` 就整体左移一位, 变成 "GENTS.md" —— 静默漏检。
    return proc.stdout.rstrip("\n") if proc.returncode == 0 else ""


def changed_files() -> set[str]:
    """本次改动到的文件(仓库根相对路径, 已暂存与未暂存都算)。"""
    out: set[str] = set()
    for line in git("status", "--porcelain").splitlines():
        if line.strip():
            out.add(line[3:].strip())
    return out


def char_count(path: Path) -> int:
    """字符数 —— 必须对齐 IDE 口径。

    用 `read_bytes().decode()` 而不是 `read_text()`: 后者走 universal newlines, 会把 CRLF 折成
    LF, 每行少算一个字符; IDE 侧是 `fs.readFile(utf8)`, 不做这层转换。CRLF 换行的大文件两种
    算法能差近百字符, 卡在临界值时会误判放行。
    """
    return len(path.read_bytes().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="提交前检查 IDE 上下文注入上限")
    parser.add_argument("--strict", action="store_true", help="只要超限就退出码 1(不管本次有没有改它)")
    parser.add_argument("--quiet", action="store_true", help="只打印非 PASS 项")
    args = parser.parse_args()

    caps = CONTEXT_CAPS
    changed = changed_files()
    rows: list[tuple[str, str, str]] = []
    for rel, limit in sorted(caps.items()):
        path = REPO_ROOT / rel
        if not path.is_file():
            rows.append((WARN, rel, "配置里声明了但文件不存在"))
            continue
        size = char_count(path)
        if size <= limit:
            rows.append((PASS, rel, f"{size}/{limit} 字符 (余量 {limit - size})"))
        elif rel in changed or args.strict:
            rows.append(
                (
                    STOP, rel, f"{size} 字符 > 上限 {limit} (超 {size - limit}) —— 超出部分注入时被截断,"
                    f" 模型看不到; **先精简到 {limit} 以内再提交**"
                    f" (建议留 10% 余量: 削到 {int(limit * 0.9)})"
                )
            )
        else:
            rows.append((WARN, rel, f"{size} 字符 > 上限 {limit} (超 {size - limit}) —— 本次没改它,"
                         f" 但尾部目前是截断状态"))

    width = max(len(r[1]) for r in rows)
    print("\n上下文上限检查:\n")
    for level, rel, detail in rows:
        if args.quiet and level == PASS:
            continue
        print(f"  [{level:4}] {rel.ljust(width)}  {detail}")

    stops = [r for r in rows if r[0] == STOP]
    if stops:
        print(f"\n{len(stops)} 项超限且本次改动命中 —— 精简后再提交。")
        return 1
    print("\n无阻塞项。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
