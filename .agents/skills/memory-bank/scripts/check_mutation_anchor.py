#!/usr/bin/env python3
"""常驻锚防流水守卫: 变异测试排期锚 issue 只记「哪个包/模块 · 什么时候 · 大致成果 · 指针」。

━━ 背景 (2026-10-31) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
常驻锚 `issues/26-10-08-0642-test-mutation-audit-standing.html` 的 §01 明写「它不记流水(轮次
记录在任务档案与基线切片)」, 但 §08「轮次台账」(R0–R23 逐轮结果表)与 §09「状态变更日志」(每轮
一条千字报告)恰恰就是流水 —— 与任务档案/基线切片大面积重复, 必然漂移 (已实证: hr 行漏记 R22、
core 行计划指针落后)。2026-10-31 蒸馏改版: 台账与逐轮日志整体移除, 本件只留 §07 覆盖进度总表
一张记录表 (口径单点 = mutation-testing skill 硬约束 12 与「四段职责」)。

本守卫钉住改版结果, 防止后续轮次又把逐轮报告写回来:

    扫描面   memory-bank/issues/ 下文件名以 `test-mutation-audit-standing.html` 结尾的常驻锚
    判据①   全文禁出现「轮次台账」—— 轮次明细的事实源是任务档案 + 基线切片, 锚里重建该节 = 回归
    判据②   h2 节白名单 —— 新增节 (如再立台账/日志节) = 红; 要加节必须有意识地改本白名单
    判据③   状态变更日志 ≤ 8 条且单条 ≤ 300 字符 —— 状态翻转/结构性修订留一行, 逐轮报告写回 = 红
    判据④   全文禁逐轮流水形态: 「存活 N → M」对差 / 「红验 N/M」逐轮红验数字 / 「复发 +N」
             坑复发计数 —— 这些只在基线切片、任务档案与坑档里记 (§04/§05 的方法论表述不带数字, 不受影响)

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/check_mutation_anchor.py --check    常驻锚守卫, 有违规退出码 1
    python <skill-dir>/scripts/check_mutation_anchor.py --safety   冒烟探针 (回答「无参跑我是否即真动作」)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, rel_posix, resolve_mb_dir  # noqa: E402

# --------------------------------------------------------------------------- 判据

ANCHOR_GLOB = "*-test-mutation-audit-standing.html"

# 判据②: h2 节白名单 (蒸馏改版后的 8 节)。新增节必须显式改这里 —— 这是 poka-yoke 而非灵活优先。
ALLOWED_SECTIONS = {
    "这个锚是干什么的",
    "为什么不进提交闸门",
    "覆盖范围与节奏",
    "怎么跑",
    "一轮的标准动作",
    "产物落在哪",
    "覆盖进度总表",
    "状态变更日志",
}

# 判据①: 该字符串的出现即代表台账节被重建 (正文引用它时换措辞, 如「逐轮台账」)。
ROUND_LEDGER_MARK = "轮次台账"

# 判据③: 状态变更日志体量上限。状态翻转/结构性修订 = 一行; 千字逐轮报告 = 流水。
MAX_LOG_ENTRIES = 8
MAX_LOG_ENTRY_CHARS = 300

# 判据④: 逐轮流水形态 (锚里不记, 记录面在基线切片 / 任务档案 / 坑档)。
ROUND_ARTIFACT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("存活对差", re.compile(r"存活\s*[\d,]{1,7}\s*→\s*[\d,]{1,7}")),
    ("逐轮红验数字", re.compile(r"红验\s*\d")),
    ("坑复发计数", re.compile(r"复发\s*\+\d")),
)

H2_RE = re.compile(r"<h2>(.*?)</h2>", re.S)
H2_NO_RE = re.compile(r"<span class=\"no\">\d+</span>\s*")
TAG_RE = re.compile(r"<[^>]+>")
SECTION_RE = re.compile(r"<section\b.*?</section>", re.S)
LI_RE = re.compile(r"<li>(.*?)</li>", re.S)


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", text)).strip()


def scan_anchor(text: str) -> list[str]:
    """常驻锚 HTML → 违规行 (不带文件前缀)。"""
    problems: list[str] = []
    if ROUND_LEDGER_MARK in text:
        problems.append(f"[台账回归] 出现「{ROUND_LEDGER_MARK}」—— 轮次明细的事实源是任务档案 + 基线切片, 锚里不记")
    for m in H2_RE.findall(text):
        h2_text = _strip_tags(H2_NO_RE.sub("", m))
        if h2_text not in ALLOWED_SECTIONS:
            problems.append(f"[节白名单] h2「{h2_text}」不在白名单 —— 新增节须有意识地改 check_mutation_anchor.py 的 ALLOWED_SECTIONS")
    for name, rx in ROUND_ARTIFACT_PATTERNS:
        for m in rx.finditer(text):
            problems.append(f"[{name}] 「{m.group(0)}」—— 逐轮数字只在基线切片 / 任务档案 / 坑档里记")
    for sec in SECTION_RE.findall(text):
        if "状态变更日志" not in sec:
            continue
        entries = [_strip_tags(m) for m in LI_RE.findall(sec)]
        if len(entries) > MAX_LOG_ENTRIES:
            problems.append(f"[日志体量] 状态变更日志 {len(entries)} 条 > 上限 {MAX_LOG_ENTRIES} —— 逐轮报告不得写进状态日志")
        for entry in entries:
            if len(entry) > MAX_LOG_ENTRY_CHARS:
                problems.append(
                    f"[日志体量] 状态变更日志单条 {len(entry)} 字符 > 上限 {MAX_LOG_ENTRY_CHARS}: {entry[:80]}… —— 明细写任务档案 / 切片, 这里留一行"
                )
    return problems


def collect_violations(root: Path, mb: Path) -> list[str]:
    """全部常驻锚的违规 → 可打印行。锚文件缺失本身判红 (守卫就是为它而设, 静默跳过 = 静默绿)。"""
    problems: list[str] = []
    anchors = sorted((mb / "issues").glob(ANCHOR_GLOB)) if (mb / "issues").is_dir() else []
    if not anchors:
        return [f"未找到常驻锚文件 (issues/{ANCHOR_GLOB}) —— 守卫无对象, 确认锚是否被有意移除"]
    for path in anchors:
        text = path.read_bytes().decode("utf-8", errors="replace")
        for problem in scan_anchor(text):
            problems.append(f"{rel_posix(path, root)}: {problem}")
    return problems


# --------------------------------------------------------------------------- CLI


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="跑常驻锚守卫 (唯一动作)")
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟过滤用)")
    parser.add_argument("--quiet", action="store_true", help="只打印违规行")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    # ❗必须在任何动作之前: 冒烟闸门用 `--safety` 探活。本脚本无参 = 只打印, 属 read-only-default。
    if args.safety:
        print("read-only-default")
        return 0

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    if not mb.is_dir():
        sys.stderr.write(f"memory-bank 目录不存在: {mb}\n")
        return 2

    problems = collect_violations(root, mb)
    for p in problems:
        print(p)
    if problems:
        sys.stderr.write(
            f"\n常驻锚守卫: {len(problems)} 项。排期锚只记「哪个包/模块 · 什么时候 · 大致成果 · 指针」"
            "(§07 覆盖进度总表 + 一行式状态日志); 轮次明细的事实源是任务档案与基线切片, 写回锚里 = 回归。\n"
        )
        return 1
    if not args.quiet:
        print("常驻锚守卫: 无违规 (无台账节 / 节白名单内 / 状态日志一行式 / 无逐轮流水数字)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
