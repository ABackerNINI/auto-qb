#!/usr/bin/env python3
"""上下文字符上限检查 —— 严重度分两档: **硬规定**(超了拦提交) 与 **债务**(只报告, 不拦)。

背景 (2026-09-20 取证)
----------------------
IDE 注入项目引导文件时, 超出 `MAX_GUIDANCE_CHARS`(8000) 的部分会被 `slice(0, 8000)` 掉并追加
`\n[...too long, omitted...]` —— **模型根本看不到尾部**。规则写在 AGENTS.md 靠后的位置却一直
不生效, 就是这个原因。所以 AGENTS.md 这条上限必须有闸门, 不能靠自觉。

2026-09-30 债务制改造 (计划 memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html)
-----------------------------------------------------------------------------------------
旧的口径是「任何 cap 超限且本次改动命中 → STOP」。实测后果: 触顶都发生在**任务后期**,
此时压字数要带着满载的会话历史反复返工, token 成本远大于文件变长本身 —— 而债务记了也还不上
(切片 26-09-27-1812 待办①记了 3 天仍是 7,975)。改造后:

- **硬规定**(只有 `AGENTS.md`): 越过它发生的是**注入截断**(尾部真不可见), 不是"读起来贵"。
  超 8,000 且本次改动命中 → **仍 STOP**。它不进债务清单、不套 50% 收缩(用户 2026-09-30 拍板)。
- **债务**(其余全部): 违反只是多花阅读/加载 token, 无截断 —— 报告为 `[债务]`, **不拦提交**。
  债务是**派生**的: 每次由本脚本从真实文件尺寸现算, 不设手写债务表(手记会陈旧、会与事实分叉)。
- **触发点 = 提交时**: 那一刻 agent 必读输出、用户就在会话另一端; 警告文案自带处置指令
  「请在回复中提醒用户: 文档数字已超标, 需另开新会话清理」—— agent 开不了新会话, 清理由**用户**
  另开一场会话执行, `--strict` 是它的收口开关。

为什么是项目脚本而不是 skill
----------------------------
`my-commit-flow` 是**通用 skill**, 不该内置"本仓库哪个文件受限、上限多少"这类项目专属值,
所以闸门逻辑落在这里; 而本脚本**是**项目脚本, 上限直接写死在下面的常量里 ——
项目专属值放在项目脚本中本来就是合适的。

严重度单点
----------
知识库角色 cap 的严重度由 skill 侧 `check_kb_structure.HARD_CAP_ROLES` 决定, 本脚本**进程内
import 它**(与 `tests/test_memory_bank.py` 同做法) —— 不在两处各写一份判定逻辑。

用法
----
    python scripts/check_context_caps.py             # 默认: 只有 AGENTS.md 超限且本次改了它 → 退出码 1
    python scripts/check_context_caps.py --strict    # 收口模式: 债务非空(或 AGENTS.md 超限) → 退出码 1
    python scripts/check_context_caps.py --quiet     # 只打印非 PASS 项
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- 硬规定
# 越过它 = **内容真的没了**(IDE 注入时被 slice 掉), 不是"读起来贵一点" ⇒ 超了仍拦提交。
# key = 仓库根相对路径, value = 最大**字符**数(不是字节)。
# AGENTS.md 的依据: IDE 注入项目引导文件时 MAX_GUIDANCE_CHARS = 8000, 超出部分被 slice 掉;
# 引导文件按 GUIDANCE_FILES = [CODEBUDDY.md, .codebuddy/CODEBUDDY.md, AGENTS.md] 首个存在即停 ——
# 本仓库前两个都不存在, 项目引导实际走 AGENTS.md。**改这里前先确认 IDE 常量没变。**
# 2026-09-30 用户拍板: 它是硬规定 —— 不能超、不套 50% 收缩、不进债务体系。
HARD_CAPS: dict[str, int] = {
    "AGENTS.md": 8000,
}

# --------------------------------------------------------------------------- 债务型上限
# 这些文件**不被 IDE 注入截断**, 超限只是多花加载 / 阅读 token ⇒ 2026-09-30 起降级为债务。
# 2026-09-29 用户定调过一次翻倍: 旧值频繁触顶, 每次触顶都逼出一轮"压文案"返工,
# 返工轮次的 token 成本远大于文件变长; 2026-09-30 再往前一步 —— 连"必须当场返工"都取消。
SKILL_CAPS: dict[str, int] = {
    ".agents/skills/commands/SKILL.md": 5200,
    ".agents/skills/memory-bank/SKILL.md": 15000,
}

# 阅读预算 —— 与"注入上限"不是一回事: 这些文件不被 IDE 注入, 但**指针一旦指向它们就只能整读**。
# 上限的意义是让"包内说明文档"维持**索引形态**: 细节必须能外置到 references/ 按需读, 而不是长在这份文件里。
# 否则省下的 token 会从另一头漏回来(实测: 提交流程里被当入口整读一次 ≈ 4–5k token)。
READ_BUDGET_CAPS: dict[str, int] = {
    ".commands/my-commit-flow/README.md": 6000,
}

PASS, WARN, STOP, DEBT, GROUP = "PASS", "WARN", "STOP", "债务", "GROUP"

# 债务汇总行 —— 提交时打印出来, 读到它的人(agent)不必先查规则就知道该做什么
DEBT_SUMMARY = (
    "\ncap 债务 {n} 项 —— 请在回复中提醒用户: 文档数字已超标, 需另开新会话清理"
    "\n  → 提交照常: 债务不拦提交; AGENTS.md 除外 —— 它超限即拦"
    "\n  → 清理会话收口: commands run doc.caps -- --strict (债务非空即 rc=1)"
)


def _pad(text: str, width: int) -> str:
    """按终端**显示宽度**补空格 —— CJK 占两列, 直接 `ljust` 会让 `[债务]` 行与其它行歪开。"""
    shown = sum(2 if ord(c) > 0x2E80 else 1 for c in text)
    return text + " " * max(0, width - shown)


def _why(rel: str) -> str:
    """超限的后果按文件而异 —— 各类上限的理由不同, 提示得说中各自的那一处。"""
    if rel in READ_BUDGET_CAPS:
        return "被当作入口时只能整读, 省下的 token 从另一头漏回来; **细节应外置到 references/ 按需读**"
    if rel in SKILL_CAPS:
        return "每次加载该 skill 都要整读, 省 token 的初衷会漏回来; **细节应外置到 references/ 按需读**"
    return "超出部分注入时被截断, 模型看不到"


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


def _kb_checker():
    """定位并 import memory-bank skill 的 `check_kb_structure`(项目级 → 用户级)。

    KB 角色 cap 的**严重度单点在 skill 源码里**(`HARD_CAP_ROLES`), 这里只消费它的输出 ——
    不在两处各写一份判定。找不到 skill 返回 None(报告一次, 不拦提交)。
    """
    bases = (REPO_ROOT / ".agents" / "skills", Path.home() / ".workbuddy" / "skills")
    for base in bases:
        scripts = base / "memory-bank" / "scripts"
        if not (scripts / "check_kb_structure.py").is_file():
            continue
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import check_kb_structure

        return check_kb_structure
    return None


def kb_cap_rows() -> tuple[list[tuple[str, str]], str, str]:
    """知识库角色 cap 的债务行 —— 由 skill 单点现算, 剔除 `agents`(它走硬规定行)。

    返回 ([(相对路径, 详情)], 硬错误, 软提示):
    - **硬错误**: 剔除硬规定角色后 `check_caps` 仍报 problem —— 说明严重度单点被绕过, 抬成 STOP;
    - **软提示**: skill / memory-bank 目录找不到 ⇒ **只报告, 不拦** —— "KB 没检查到"是环境
      问题, 让它去拦一次无关提交, 正是债务制要取消的那类误伤(2026-09-30)。
    """
    checker = _kb_checker()
    if checker is None:
        return [], "", "未找到 memory-bank skill 的 scripts/check_kb_structure.py —— KB 角色 cap 未检查"
    mb = REPO_ROOT / "memory-bank"
    if not mb.is_dir():
        return [], "", f"未找到 {mb} —— KB 角色 cap 未检查"
    # 剔除硬规定角色: AGENTS.md 单列在「硬规定」组, 不进债务清单、不累计进债务数
    roles = tuple(r for r in checker.DEFAULT_ROLES if r not in checker.HARD_CAP_ROLES)
    problems, warns = checker.check_caps(REPO_ROOT, mb, roles)
    rows = []
    for line in warns:
        # 只挑**债务**行: warns 里还混着下限 `CAP_MIN_WARN` 的"文件过小"建议 —— 那是提示不是欠债,
        # 算进债务数的话这个数字永远清零不了(清理会话按它收口会徒劳)。
        if not line.startswith(checker.DEBT_MARK):
            continue
        body = line[len(checker.DEBT_MARK):]
        rel, _, detail = body.partition(" 超 cap: ")
        rows.append((rel or body, detail))
    # 剔除后不该再有 problems; 真出现了说明单点被绕过, 直接抬成阻塞项交给调用方
    return rows, "".join(problems), ""


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 IDE 上下文注入上限与包内文档的阅读预算(2026-09-30 起: 除 AGENTS.md 外均为债务)")
    parser.add_argument("--strict", action="store_true", help="收口模式: 债务非空(或 AGENTS.md 超限) → 退出码 1")
    parser.add_argument("--quiet", action="store_true", help="只打印非 PASS 项")
    args = parser.parse_args()

    changed = changed_files()
    rows: list[tuple[str, str, str]] = []

    # ---- 1. 硬规定: 超了内容真的会被截断, 不降级、不挂账 ----
    rows.append((GROUP, "硬规定 (不降级 · 不挂账)", ""))
    for rel, limit in sorted(HARD_CAPS.items()):
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
                    STOP, rel, f"{size} 字符 > 上限 {limit} (超 {size - limit}) —— {_why(rel)};"
                    f" **必须回到 ≤ {limit} 才能提交**(它是 IDE 注入入口, 没有挂账通道)"
                )
            )
        else:
            rows.append((WARN, rel, f"{size} 字符 > 上限 {limit} (超 {size - limit}) —— 本次没改它,"
                         f" 但{_why(rel)}"))

    # ---- 2. SKILL / 阅读预算: 债务 (不拦提交) ----
    rows.append((GROUP, "两份 SKILL.md / 包内阅读预算 (债务)", ""))
    for rel, limit in sorted({**SKILL_CAPS, **READ_BUDGET_CAPS}.items()):
        path = REPO_ROOT / rel
        if not path.is_file():
            rows.append((WARN, rel, "配置里声明了但文件不存在"))
            continue
        size = char_count(path)
        if size <= limit:
            rows.append((PASS, rel, f"{size}/{limit} 字符 (余量 {limit - size})"))
        else:
            rows.append((DEBT, rel, f"{size} 字符 > 上限 {limit} (超 {size - limit}) —— {_why(rel)};"
                         " 本会话不修"))

    # ---- 3. 知识库角色 cap: 债务 (由 skill 单点现算) ----
    rows.append((GROUP, "知识库角色 cap (债务 · 由 skill 单点现算)", ""))
    kb_rows, kb_hard, kb_soft = kb_cap_rows()
    for rel, detail in kb_rows:
        rows.append((DEBT, rel, f"超 cap: {detail}"))
    if kb_hard:
        # 剔除 agents 后仍报 problem = 严重度单点被绕过; 抬成阻塞
        rows.append((STOP, "check_kb_structure", kb_hard))
    if kb_soft:
        rows.append((WARN, "check_kb_structure", kb_soft))
    if not kb_rows and not kb_hard and not kb_soft:
        rows.append((PASS, "(全部 KB 角色)", "均在 cap 内"))

    width = max(len(r[1]) for r in rows if r[0] != GROUP)
    print("\n上下文上限检查:\n")
    for level, rel, detail in rows:
        if level == GROUP:
            print(f"{rel}:")
            continue
        if args.quiet and level == PASS:
            continue
        print(f"  [{_pad(level, 4)}] {_pad(rel, width)}  {detail}")

    stops = [r for r in rows if r[0] == STOP]
    debts = [r for r in rows if r[0] == DEBT]

    if stops:
        print(f"\n{len(stops)} 项超限且本次改动命中 —— 硬规定, 精简后再提交。")
        return 1
    if debts:
        print(DEBT_SUMMARY.format(n=len(debts)))
    else:
        print("\n无阻塞项 · 无 cap 债务。")
    return 1 if args.strict and debts else 0


if __name__ == "__main__":
    raise SystemExit(main())
