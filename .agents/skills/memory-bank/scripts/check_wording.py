#!/usr/bin/env python3
"""回写措辞守卫: 回写件不得写「待提交」这类**时点相对的状态断言**。

背景 (自指不可能): `commit` 的 hash 由 tree + parent + author + 时间戳决定 —— 想把它写进
文件就改变了 tree, hash 随之变化。**一个提交永远无法包含自己的 hash**。而收尾 DoD 要求回写件
(任务档案 / activeContext 切片)**随主提交一并暂存**, 于是「待提交」必然写在 hash 逻辑上尚不
存在的时点 —— 提交一落地, 那句断言当场变成假话。2026-09-27 审计 (reports/26-09-27-1547) 已
实证这条兜底会失败: 切片停在「等待提交」而提交实际已完成, 切片与计划 meta 双陈旧。

口径 (单点在 skill 的「收尾 DoD」): 回写件**不写时间相对的待提交断言** ——
  ✗ 待提交 / 未提交(状态) / 等用户「提交」指令 / 等显式指令
  ✓ 时不变措辞: 「随本专题入库」(提交前=将要, 提交后=已); 或直接省去 —— git 状态自证,
     hash 需要时用 `git log --grep <专题键>` 找回 (坑档 pitfalls/kb/commit-hash-refs.md 同旨)。

守卫判据 (2026-10-07):
    扫描面   `memory-bank/tasks/*.md` + `memory-bank/activeContext/*.md` (两个滚动更新面)
             跳过 `_` 开头的生成物 (`tasks/_index.md` 镜像手写件且不可就地修, 源头已扫到)
    判红     `待提交` / `待推送` / `提交中` / `等…指令` / 粗体「未提交 · 未 commit · 未入库」状态标记
    豁免①   **带日期前缀的行** —— 历史流水条目自带时点, 不会过期, 改写反而是篡改日志
    豁免②   **围栏 / 行内代码** —— 元讨论里必须能**引述**被禁措辞 (`待提交` 在反引号里 = 引述)
    豁免③   行内 `<!-- wording:allow -->` 标记 (其它一次性场景)
    豁免④   `未提交` + 名词 (未提交改动 / 未提交的工作树) —— 这是**树态描述**, 不是状态断言
             (基线切片里 76 处这类合法用法; 冻结快照**不在**本守卫扫描面内, 见下)

**不扫 `testing/baselines/`**: 基线切片是**出厂即冻结的测量快照**, 其 `未提交` 描述「这条基线
测在哪棵树上」, 是解释数字差异的必需元数据 (例: baselines/26-10-06-0547 用它解释 passed 对不齐),
不是会过期的状态断言。冻结件不随提交更新, 所以本缺陷形态在那里不成立。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/check_wording.py --check    回写措辞守卫, 有违规退出码 1
    python <skill-dir>/scripts/check_wording.py --safety   冒烟探针 (回答「无参跑我是否即真动作」)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, rel_posix, resolve_mb_dir  # noqa: E402

# --------------------------------------------------------------------------- 判据

ALLOW_MARK = "<!-- wording:allow -->"

# 扫描面: 两个**滚动更新**面。baselines 是冻结快照, 不入 (见模块 docstring)。
SCAN_DIRS = ("tasks", "activeContext")

# 待提交状态断言 (短语类)。顺序即报错时的分类名。
PENDING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("待提交", re.compile(r"待提交")),  # 含「等待提交」
    ("待推送", re.compile(r"待推送")),
    ("提交中", re.compile(r"提交中")),
    ("等…指令", re.compile(r"等[^，。\n]{0,12}指令")),
)

# 粗体状态标记: `**未提交**` / `**本轮代码未提交**` / `**未 commit**` / `**未入库**`。
# ❗必须是**配对好的粗体段内容**里含它 —— 用 `\*\*[^*\n]*未…[^*\n]*\*\*` 会从上一个粗体的
# 收尾横跨到下一个粗体的开头 (中间恰好没有 `*`), 把普通行文里的「未入库」误判成状态标记
# (2026-10-07 首跑实测: 26-09-21-webui-filter-data-and-color-flicker.md:19 误报)。
BOLD_SPAN_RE = re.compile(r"\*\*([^*\n]+)\*\*")
BOLD_STATUS_RE = re.compile(r"未\s*(?:提交|commit|入库)")

# 行首 (去掉列表 / 引用 / 表格 / 标题前缀与粗体标记后) 是日期 ⇒ 历史流水条目。
LINE_PREFIX_RE = re.compile(r"^\s*(?:[-*+>|]\s*|\#{1,6}\s*)*\*{0,2}\s*")
DATE_HEAD_RE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{2})")

# 行内代码 / 围栏代码: 跳过 —— 元讨论里必须能**引述**被禁的措辞 (与 timekit 跳过代码上下文同构)。
# 于是 `待提交` 写在反引号里 = 引述, 不判红; 光写 待提交 = 断言, 判红。
MD_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# `未提交` 后接名词 = 树态描述 (合法), 报错时用来提示"这条不是违规形态"。
TREE_STATE_RE = re.compile(r"未提交(?:的)?(?:改动|工作树|工作区|回写|代码|内容|文件|文档|线|工作|部分|状态)")


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """正文 → [(行号, 分类, 原文行)]。

    豁免: 围栏/行内代码 (可引述) · 日期行 (自带时点) · `<!-- wording:allow -->` · 树态描述行。
    """
    hits: list[tuple[int, str, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.split("\n"), 1):
        if line.strip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or ALLOW_MARK in line:
            continue
        if DATE_HEAD_RE.match(LINE_PREFIX_RE.sub("", line)):
            continue  # 历史流水条目: 自带时点, 不会过期
        probe = TREE_STATE_RE.sub("«树态»", MD_INLINE_CODE_RE.sub("", line))
        for kind, rx in PENDING_PATTERNS:
            if rx.search(probe):
                hits.append((lineno, kind, line.strip()))
                break
        else:
            if any(BOLD_STATUS_RE.search(span) for span in BOLD_SPAN_RE.findall(probe)):
                hits.append((lineno, "粗体未提交标记", line.strip()))
    return hits


def collect_violations(root: Path, mb: Path) -> list[str]:
    """两个滚动更新面的全部违规 → 可打印行。

    跳过 `_` 开头的**生成物** (`tasks/_index.md` 等): 它镜像手写件的内容且不可就地修
    (改了下次重跑又回来) —— 源头 (档案 / 切片) 已被扫到, 报两处只是重复信号。
    """
    problems: list[str] = []
    for sub in SCAN_DIRS:
        directory = mb / sub
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name.startswith("_"):
                continue
            for lineno, kind, line in scan_text(_read(path)):
                problems.append(f"{rel_posix(path, root)}:{lineno}: [{kind}] {line[:140]}")
    return problems


# --------------------------------------------------------------------------- CLI


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="跑回写措辞守卫 (唯一动作)")
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
            f"\n回写措辞守卫: {len(problems)} 项 —— 回写件不写「待提交」这类时点相对断言 "
            "(提交后必然过期); 改用时不变措辞「随本专题入库」或直接省去 (git 状态自证)。"
            "引述原文等一次性场景用行内 `<!-- wording:allow -->` 豁免。\n"
        )
        return 1
    if not args.quiet:
        print("回写措辞守卫: 无违规。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
