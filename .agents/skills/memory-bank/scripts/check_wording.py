#!/usr/bin/env python3
"""回写守卫 (两个判据族): ①时点相对的「待提交」措辞 ②KB 正文手抄测试数字。

━━ 判据族 A: 待提交断言 (2026-10-07) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
背景 (自指不可能): `commit` 的 hash 由 tree + parent + author + 时间戳决定 —— 想把它写进
文件就改变了 tree, hash 随之变化。**一个提交永远无法包含自己的 hash**。而收尾 DoD 要求回写件
(任务档案 / activeContext 切片)**随主提交一并暂存**, 于是「待提交」必然写在 hash 逻辑上尚不
存在的时点 —— 提交一落地, 那句断言当场变成假话。2026-09-27 审计 (reports/26-09-27-1547) 已
实证这条兜底会失败: 切片停在「等待提交」而提交实际已完成, 切片与计划 meta 双陈旧。

口径 (单点在 skill 的「收尾 DoD」): 回写件**不写时间相对的待提交断言** ——
  ✗ 待提交 / 未提交(状态) / 等用户「提交」指令 / 等显式指令
  ✓ 时不变措辞: 「随本专题入库」(提交前=将要, 提交后=已); 或直接省去 —— git 状态自证,
     hash 需要时用 `git log --grep <专题键>` 找回 (坑档 pitfalls/kb/commit-hash-refs.md 同旨)。

━━ 判据族 B: 手抄测试数字 (2026-10-08, 方案 C) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
背景 (数字只有一个事实源): 测试数字的**唯一**权威是 `testing/baselines/` 的切片 —— 每次全量
跑完新建一条, 最新一条恒为当前事实源 (`commands run kb.baseline` 列最近 3 条)。但历史上同一
个数字被**手抄**进档案 / 切片 / 计划的正文, 每轮要改 4 处、且必然漂移 (口径早已写在
`testing/baseline.md`, 只是没有守卫, 于是反复违反)。

方案 C (2026-10-08 用户定案): **数字只写切片一处, 其余文档一律引用不手抄** ——
  ✗ 档案 / activeContext 正文里写「2772 passed」这类裸数字 (必然与切片分叉)
  ✓ 写「见 `commands run kb.baseline`」或「与上基线持平」(量级可, 精确值不抄)

守卫判据 (2026-10-08):
    扫描面   `memory-bank/tasks/*.md` + `memory-bank/activeContext/*.md` (两个滚动更新面)
             跳过 `_` 开头的生成物 (`tasks/_index.md` 镜像手写件且不可就地修, 源头已扫到)
    判红     三位以上 passed (或 N+M skipped) 这类**裸测试数字**
    豁免①   **带日期前缀的行** —— 历史流水条目自带时点, 是不变日志, 改写反而是篡改历史
    豁免②   **围栏 / 行内代码** —— 元讨论里必须能**引述** (`2772 passed` 在反引号里 = 引述)
    豁免③   行内 `<!-- wording:allow -->` 标记
    存量冻结 已有违规**冻结为债务**: 数目不得增加 (`frozen_counts`), 只拦**新增**手抄 ——
             与 cap 债务制 (2026-09-30) 同构: 存量是历史记录, 一行不改, 只保证不再恶化。
    ❗已知边界 日期豁免**只认首行**: 多行流水条目的**续行**不以日期开头, 照常入判 (见
             `pitfalls/kb/scripts.md`) —— 处置 = 续行回避禁写形态 (写数字改「见 kb.baseline」)。

**不扫 `testing/baselines/`**: 它是数字的**唯一事实源**, 当然要写数字。
**不扫 `plans/` `reports/` `issues/` 的 HTML**: 出厂即冻结的快照 (同 check_doc_links.is_frozen),
其 `未提交` / 数字都是成文那天的测量快照, 不随提交更新, 缺陷形态在那里不成立。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/check_wording.py --check    回写守卫, 有违规退出码 1
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

# ── 判据族 B: 手抄测试数字 ────────────────────────────────────────────────────────────
# 裸测试数字: 三位以上 passed (可带 +N skipped)。这是 KB 正文里**唯一**该去切片查的数字。
# 只认 `passed` —— 它是测试结论的锚, 且形态稳定; 单说「+2」或「99%」独立出现时歧义太大不认。
TEST_NUM_RES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("裸 passed 数字", re.compile(r"\b\d{3,5}\s*passed\b")),
    ("裸 skipped 数字", re.compile(r"\b\d{3,5}\s*\+\s*\d{1,3}\s*skipped\b")),
)

# 存量冻结 (债务制, 同 cap 债务 2026-09-30): 已有手抄**一行不改** (是不可变历史记录),
# 只保证**不再新增**。实际命中数 ≤ 本常数即放行, 超出即判红 (新增的手抄)。
# 重算口径: 跑 `--count-numbers` 现算, 数变多说明本轮又手抄了, 数变少说明清理了 (可下调本值)。
# 2026-10-08 首测 = 394 (扫 tasks/ + activeContext/, 日期行/代码/生成物已豁免)。
FROZEN_TEST_NUM_COUNT = 394


def scan_text_numbers(text: str) -> list[tuple[int, str, str]]:
    """判据族 B: 正文 → [(行号, 分类, 原文行)] 裸测试数字。

    豁免同 A 族: 围栏/行内代码 (可引述) · 日期行 (历史流水, 不改写) · `<!-- wording:allow -->`。
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
            continue  # 历史流水条目: 自带时点, 属不可变日志
        probe = MD_INLINE_CODE_RE.sub("", line)  # 反引号内 = 引述, 不判红
        for kind, rx in TEST_NUM_RES:
            if rx.search(probe):
                hits.append((lineno, kind, line.strip()))
                break
    return hits


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
    """滚动更新面的全部违规 (判据族 A + 存量之外的族 B) → 可打印行。

    跳过 `_` 开头的**生成物** (`tasks/_index.md` 等): 它镜像手写件的内容且不可就地修
    (改了下次重跑又回来) —— 源头 (档案 / 切片) 已被扫到, 报两处只是重复信号。
    """
    problems: list[str] = []
    num_hits: list[str] = []
    for sub in SCAN_DIRS:
        directory = mb / sub
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name.startswith("_"):
                continue
            text = _read(path)
            rel = rel_posix(path, root)
            for lineno, kind, line in scan_text(text):
                problems.append(f"{rel}:{lineno}: [{kind}] {line[:140]}")
            for lineno, kind, line in scan_text_numbers(text):
                num_hits.append(f"{rel}:{lineno}: [{kind}] {line[:140]}")
    # 族 B 债务制: 存量冻结 (≤ FROZEN), 只拦**新增**的手抄。
    # 报**新增**的那几条 (取扫描序末 N 条 —— 按路径排序, 新增件通常排在末尾), 不刷全部存量:
    # 存量 394 条全打会把提交闸门刷屏, 而清理会话要全量用 `--count-numbers` / `--list-numbers` 现取。
    if len(num_hits) > FROZEN_TEST_NUM_COUNT:
        over = len(num_hits) - FROZEN_TEST_NUM_COUNT
        problems.extend(num_hits[-over:])
        problems.append(
            f"(手抄测试数字新增 {over} 处 —— 数字只写 testing/baselines/ 切片, 正文改「见 kb.baseline」; "
            f"存量已冻结 {FROZEN_TEST_NUM_COUNT} 处, 全量清单 `--list-numbers`)"
        )
    return problems


def count_test_numbers(root: Path, mb: Path) -> int:
    """族 B 实测命中数 —— 供 `--count-numbers` 现算 (存量冻结常数的重算口径)。"""
    return len(list_test_numbers(root, mb))


def list_test_numbers(root: Path, mb: Path) -> list[str]:
    """族 B 全量命中行 —— 供 `--list-numbers` (清理会话) 与 `--count-numbers` 共用。"""
    hits: list[str] = []
    for sub in SCAN_DIRS:
        directory = mb / sub
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name.startswith("_"):
                continue
            rel = rel_posix(path, root)
            for lineno, kind, line in scan_text_numbers(_read(path)):
                hits.append(f"{rel}:{lineno}: [{kind}] {line[:140]}")
    return hits


# --------------------------------------------------------------------------- CLI


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="跑回写守卫 (唯一动作)")
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟过滤用)")
    parser.add_argument("--quiet", action="store_true", help="只打印违规行")
    parser.add_argument("--count-numbers", action="store_true", help="现算族 B 手抄测试数字命中数 (存量冻结常数重算口径)")
    parser.add_argument("--list-numbers", action="store_true", help="列出族 B 全量命中行 (清理会话用)")
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

    if args.list_numbers:
        for line in list_test_numbers(root, mb):
            print(line)
        return 0

    if args.count_numbers:
        actual = count_test_numbers(root, mb)
        print(f"手抄测试数字实测 {actual} 处 (存量冻结 FROZEN_TEST_NUM_COUNT = {FROZEN_TEST_NUM_COUNT})")
        if actual > FROZEN_TEST_NUM_COUNT:
            print(f"⚠ 超出 {actual - FROZEN_TEST_NUM_COUNT} 处 —— 本轮新增了手抄; 清理后可将常数下调到 {actual}")
        return 0

    problems = collect_violations(root, mb)
    for p in problems:
        print(p)
    if problems:
        sys.stderr.write(
            f"\n回写守卫: {len(problems)} 项。判据族 A = 不写「待提交」这类时点相对断言 (提交后必然过期), "
            "改用时不变措辞「随本专题入库」或直接省去 (git 状态自证); 判据族 B = 不在正文手抄测试数字, "
            "数字只写 testing/baselines/ 切片、正文改「见 kb.baseline」(存量已冻结, 只拦新增)。"
            "引述原文等一次性场景用行内 `<!-- wording:allow -->` 豁免。\n"
        )
        return 1
    if not args.quiet:
        print("回写守卫: 无违规 (待提交措辞 + 手抄测试数字)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
