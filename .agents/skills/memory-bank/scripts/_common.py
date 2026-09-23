"""memory-bank 脚本族共用的常量与工具 (gen_tasks_index / gen_kb_index / check_kb_structure)。

**与具体项目无关**: 不出现项目名、不假定 skill 的安装深度、不硬编码 memory-bank 路径 ——
换一个项目直接装上就能跑; 项目专属值 (如 AGENTS.md 的 8000 字符上限) 留在项目脚本里。

单点定义 (守卫 import 这里, 不手抄):
- `CAP_POLICY`: 角色 → 字符上限 (方案 §03「cap 分级」); 改 cap 只改这里
- `PITFALL_CLASSES`: pitfalls 的类枚举 (扩类须三处同步: 本常量 / 新建目录 / README 细路由)
- `find_root()`: 仓库根探测 (向上找 `.git`, 而非按 skill 安装深度反推 `parents[n]`)
- `resolve_mb_dir()`: memory-bank 目录探测 (`--mb-dir` 显式指定优先)
- `read_meta()`: 主题文件三行头元数据 (`# 标题` / `> 摘要:` / `> 触发:`)
- `role_of()`: 仓库相对路径 → 角色 (决定套哪档 cap)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

# --------------------------------------------------------------------------- cap 策略

# 角色 → 字符上限 (方案 §03; 首个匹配生效, 口径同项目脚本 check_context_caps.py: 按**字符**数)
CAP_POLICY: dict[str, int] = {
    "index": 3000,  # `<doc>/_index.md` 与 memory-bank/README.md —— 必须一屏可读
    # `tasks/_index.md` / `issues/_index.md` 是**自动生成、行数随档案/issue 数增长**的索引:
    # 实测 10,790 / 6,937 字符 (2026-09-22), 套 3,000 档必然常红且没有可行的收缩路径
    # (一行一条, 已是最简)。故单列一档 —— 有守卫防无限膨胀, 但不假装它们是一屏索引。
    "index-auto": 12000,
    "pitfall": 6000,  # pitfalls/* 条目集 —— 读法是「扫描找一条」, 比通读更贵
    "evergreen": 10000,  # 常青主题 (叙述型) —— ≈4k token, 一次通读可接受
    "reference": 12000,  # 参考速查 (config-reference / rule-system) —— 查表不是通读
    "volatile": 12000,  # 易变层 (activeContext.md) —— 会话开始必读, 硬顶
    # 目录化后原位置只留 ≤1 KB 存根, 到时这一档要降到 1,000 —— 见计划 W1, 别提前改 (会让现有文件当场报红)
    "slice": 6000,  # activeContext/ 会话切片 —— per-会话 / per-专题, 天然比整份易变层小
    "task": 24000,  # 任务档案
    # append-only 历史流水 (如 `testing/baseline-history.md`) —— **只增不改**, 每次改动追一条。
    # 与任务档案同档: 它按设计就会一直长, 给一个"涨到多少该轮转"的上限, 而不是假装它是一屏文档。
    # 轮转策略见下方 `LOG_ROTATE_KEEP` —— 触顶后按它切, 不要只搬"最老的一条"。
    "log": 24000,
    "agents": 8000,  # 项目引导 (AGENTS.md; 项目脚本 scripts/check_context_caps.py 另有一份权威值)
}

# 下限建议: **只 WARN** —— 主题文件过小会让「读三个文件」取代「读一节」, 反而更贵
CAP_MIN_WARN = 1500

# append-only 流水 (`log` 角色, 如 `*-history.md`) 触顶后的轮转策略:
# **一次切掉约 1/3, 让文件落回 ~2/3 容量** —— 留出足够的追加余量。
# ❌ 只搬"最老的一条"是错的: 最老条目大小不受控, 可能只有几百字符, 下次追加立刻又触顶;
#    2026-09-23 实测 `testing/baseline-history.md` 触顶时只剩 170 字符余量 —— 也就是说**任何**一次
#    追加都会越线, 而按"搬一条"处置等于每次新增都要迁移一次。
# 落点: 同目录 `attachments/`(`iter_topic_files` 是非递归 glob + 该目录在 EXCLUDED_DIRS 里 ⇒ 不计 cap),
# 原位留一行指针; 搬运用脚本按原换行风格切分原样写回, 不手抄。
LOG_ROTATE_KEEP = 2 / 3

# 任务档案的「历史会话纪要」段上限; 超了移 `tasks/attachments/`
TASK_LOG_CAP = 8000

# --------------------------------------------------------------------------- 结构枚举

# pitfalls 的类枚举。**扩类须三处同步**: 本常量 / 新建 `<class>/_about.md` / memory-bank/README.md 细路由。
PITFALL_CLASSES = ("git", "web-ui", "backend", "testing", "ops", "kb", "docs")

# 主题文件名: 小写英文与数字, 短横线分段 (与 create-issue 的 SLUG_RE 同款)
TOPIC_FILE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# activeContext 会话切片文件名: 定宽 `YY-MM-DD-HHMM-<slug>` —— 前缀定宽才能保证**字典序 == 时间序**
# (写成 `26-9-3-34` 立刻乱序)。⚠ 与 tasks/ 档案「不带时分、同天同专题必撞同路径」的故意设计
# **意图相反**: 那边靠撞名暴露重复, 这边靠带时分避撞名 —— 所以两者必须分目录, 别混。
SLICE_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# 切片头部的「最后活动」字段 —— 阅读器的排序键; 缺失则回退文件名时间戳 (= 创建时间)
LAST_ACTIVE_RE = re.compile(r"^>\s*最后活动:\s*(\S.*?)\s*$", re.MULTILINE)

# 会话滚动状态切片所在目录 (目录化后 `memory-bank/activeContext/`)
SLICE_DIR = "activeContext"

# 索引/元数据文件名: `_` 开头, 不参与「主题文件」计数
INDEX_NAME = "_index.md"
ABOUT_NAME = "_about.md"

# 三行头元数据 —— 条目型与叙述型共用同一套 (这是「全库一套机制」的关键)
TITLE_RE = re.compile(r"^#\s+(\S.*?)\s*$", re.MULTILINE)
SUMMARY_RE = re.compile(r"^>\s*摘要:\s*(\S.*?)\s*$", re.MULTILINE)
TRIGGER_RE = re.compile(r"^>\s*触发:\s*(\S.*?)\s*$", re.MULTILINE)

# pitfalls 条目的三个必填字段 (条目以 `### ` 起头, 字段是 `- **触发**: …` 这样的行)
ENTRY_HEADING_RE = re.compile(r"^###\s+(\S.*?)\s*$", re.MULTILINE)
REQUIRED_FIELDS = ("触发", "判别", "处置")

# --------------------------------------------------------------------------- 存根

STUB_MARK = "已迁至"
STUB_CAP = 1000

# 需要存根保护的顶层文档: 拆成同名目录后, 原路径必须降级为 ≤1 KB 存根
# (引用面统计见方案 §08 —— testing.md 132 处 / pitfalls.md 113 处, 大量在历史计划与 issue 报告里)
STUB_CANDIDATES = (
    "pitfalls.md",
    "testing.md",
    "progress.md",
    "systemPatterns.md",
    "modules.md",
    "conventions.md",
    "config-reference.md",
    "rule-system.md",
    "activeContext.md",  # 2026-09-23: 滚动状态迁 activeContext/ 切片目录, 原路径降级为存根
)

# 有独立生成器、不走 gen_kb_index 的目录 (放进 `EXCLUDED_DIRS` 后不会被当成「索引目录」)
# `activeContext` 用 `gen_active_recent.py`(打印而非生成): 若让它自发现, gen_kb_index 会造出一个
# 随切片数增长的 `_index.md`, 终将撞 index 档 —— 而时间戳文件名本身已是索引, 不需要它。
# `plans` / `reports`(2026-09-23 由 docs/ 迁入)用 `gen_docs_index.py`: 内容是 HTML 制品,
# 由 `doc-*` meta 与生成器维护, 没有三行头元数据可扫。
EXCLUDED_DIRS = ("tasks", "issues", "attachments", "activeContext", "plans", "reports")

# --------------------------------------------------------------------------- 探测


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认脚本目录)向上找 `.git`(目录或 worktree 的 `.git` 文件)。

    **不按 skill 的安装深度反推** —— `parents[n]` 只在 `.agents/skills/<name>/scripts/`
    这一种布局下成立 (这条坑已在 KB 里记过)。探测不到时退回 `parents[4]` 兜底,
    并允许调用方用 `--root` 覆盖。
    """
    cur = (start or SCRIPTS_DIR).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]


def resolve_mb_dir(root: Path, dir_arg: str | None = None) -> Path:
    """memory-bank 目录: `--mb-dir` 显式指定优先, 否则 `<root>/memory-bank`。"""
    if dir_arg:
        cand = Path(dir_arg)
        return (cand if cand.is_absolute() else root / cand).resolve()
    return (root / "memory-bank").resolve()


def rel_posix(path: Path, root: Path) -> str:
    """相对仓库根的 posix 路径 (markdown 链接里 `\\` 是错的)。跨盘时返回绝对路径。"""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def rel_link(from_dir: Path, target: Path) -> str:
    """从 from_dir 指向 target 的相对链接 (posix)。"""
    return Path(os.path.relpath(str(target.resolve()), str(from_dir.resolve()))).as_posix()


def char_count(path: Path) -> int:
    """字符数 —— 与 IDE 注入口径一致。

    用 `read_bytes().decode()` 而不是 `read_text()`: 后者走 universal newlines 会把 CRLF
    折成 LF, 每行少算一个字符。卡在临界值时会误判放行。
    """
    return len(path.read_bytes().decode("utf-8"))


def gen_cmd(root: Path, script: str) -> str:
    """脚本的仓库相对命令路径 —— 生成的索引头里写它, 读者可直接复制执行。

    取不到相对路径 (跨盘安装) 时退回 `<skill-dir>/scripts/...` 写法。
    """
    path = SCRIPTS_DIR / script
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"<skill-dir>/scripts/{script}"
    return f"python {rel}"


# --------------------------------------------------------------------------- 元数据


@dataclass
class Meta:
    """主题文件的三行头元数据 (生成器的数据源)。"""

    title: str = ""
    summary: str = ""
    triggers: str = ""

    @property
    def has_summary(self) -> bool:
        return bool(self.summary)

    @property
    def has_triggers(self) -> bool:
        return bool(self.triggers)

    @property
    def complete(self) -> bool:
        return bool(self.title) and self.has_summary and self.has_triggers


def read_meta(path: Path) -> Meta:
    """读三行头元数据; 缺哪行就留空 (由守卫报红, 不在这里抛)。"""
    text = path.read_bytes().decode("utf-8")
    title = TITLE_RE.search(text)
    summary = SUMMARY_RE.search(text)
    triggers = TRIGGER_RE.search(text)
    return Meta(
        title=title.group(1) if title else "",
        summary=summary.group(1) if summary else "",
        triggers=triggers.group(1) if triggers else "",
    )


# --------------------------------------------------------------------------- 角色


def role_of(rel: str) -> str:
    """仓库相对路径 → cap 角色 (首个匹配生效, 顺序即优先级)。"""
    rel = rel.replace("\\", "/")
    if rel == "AGENTS.md":
        return "agents"
    if rel in ("memory-bank/tasks/_index.md", "memory-bank/issues/_index.md", "memory-bank/plans/_index.md",
               "memory-bank/reports/_index.md", "memory-bank/_doc-map.md"):
        return "index-auto"
    if rel.endswith(INDEX_NAME) or rel == "memory-bank/README.md":
        return "index"
    if rel == "memory-bank/activeContext.md":
        return "volatile"
    if rel.startswith(f"memory-bank/{SLICE_DIR}/"):
        return "slice"
    if rel.startswith("memory-bank/tasks/"):
        return "task"
    if rel.endswith("-history.md"):
        return "log"
    if "/pitfalls/" in rel:
        return "pitfall"
    if rel.startswith(("memory-bank/config-reference/", "memory-bank/rule-system/")) or rel in (
        "memory-bank/config-reference.md",
        "memory-bank/rule-system.md",
    ):
        return "reference"
    return "evergreen"


def cap_of(rel: str) -> int:
    return CAP_POLICY[role_of(rel)]


# --------------------------------------------------------------------------- 目录遍历


def is_topic_file(path: Path) -> bool:
    """主题文件 = 不以 `_` 开头的 `.md` (`_index.md` / `_about.md` 不算)。"""
    return path.suffix == ".md" and not path.name.startswith("_")


def iter_topic_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.md") if is_topic_file(p))


def iter_indexed_dirs(mb: Path) -> list[Path]:
    """全部「索引目录」= 含 `_about.md` 的目录 (自发现, 新增目录自动纳入)。

    `tasks/` `issues/` 有自己的生成器, 且没有 `_about.md` —— 天然不在结果里;
    仍显式排除 `EXCLUDED_DIRS` 以免将来误加 `_about.md` 后冲突。
    """
    out: list[Path] = []
    for path in sorted(mb.rglob(ABOUT_NAME)):
        directory = path.parent
        if directory == mb or directory.name in EXCLUDED_DIRS:
            continue
        out.append(directory)
    return out


def iter_index_files(mb: Path) -> list[Path]:
    """全部 `_index.md` (含 tasks/ issues/ —— 它们也要被 README 引用, 否则是孤儿)。"""
    return sorted(mb.rglob(INDEX_NAME))


def split_pitfall_entries(text: str) -> list[tuple[str, str]]:
    """切出 pitfalls 条目: `### 标题` 起头, 到下一个 `###` / `##` / 文件尾。

    返回 [(标题, 块正文)]。
    """
    lines = text.split("\n")
    marks = [(i, line[4:].strip()) for i, line in enumerate(lines) if line.startswith("### ")]
    entries: list[tuple[str, str]] = []
    for idx, (start, title) in enumerate(marks):
        end = len(lines)
        for nxt in range(start + 1, len(lines)):
            if lines[nxt].startswith("## "):
                end = nxt
                break
        entries.append((title, "\n".join(lines[start:end])))
    return entries
