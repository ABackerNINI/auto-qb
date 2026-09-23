"""create-issue 两个脚本(new_issue / gen_issues_index)共用的常量与工具。

**与具体项目无关**: 不出现项目名、不假定 skill 的安装深度、不硬编码 issues 目录 ——
换一个项目直接装上就能跑(见 SKILL.md「可移植性」)。

单点定义:
- `TYPES`: 类型枚举(增删类型只改这里; 文件名、meta、索引、脚本校验全部读它)
- `TIER_BY_TYPE`: 类型 → 默认档位(light 便签 / standard 标准)
- `find_root()`: 仓库根探测(向上找 .git, 而非按 skill 安装深度反推)
- `resolve_issues_dir()`: issues 目录探测(--dir 显式指定优先)
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

# 状态取值仅五种(与档位无关, 通用); 2026-09-23 起与四形态统一 5 词表 (见 memory-bank/conventions/doc-forms.md)
STATUSES = ("Open", "In Progress", "Done", "Dropped", "Superseded")

# 类型枚举 —— 增删类型只改这一处
TYPES = ("bug", "perf", "docs", "test", "refactor", "feat", "chore", "question")

# 类型 → 默认档位; --tier 可覆盖(如 test 的失败用例用 --tier standard)
TIER_BY_TYPE = {
    "bug": "standard",
    "perf": "standard",
    "feat": "standard",
    "docs": "light",
    "test": "light",
    "refactor": "light",
    "chore": "light",
    "question": "light",
}
TIERS = ("light", "standard")
TIER_TEMPLATE = {
    "light": "issue-light.html",
    "standard": "issue-standard.html",
}

# slug: 小写英文短横线, 允许单段(<领域>-<专题> 只是建议, 分类职责已交给 type)
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 报告文件名: <时间>-<类型>-<slug>.html —— 类型固定在第二段, 扫描目录即可按类型聚合
FILE_RE = re.compile(r"^(?P<stamp>\d{2}-\d{2}-\d{2}-\d{4})-(?P<type>[a-z]+)-(?P<slug>[a-z0-9-]+)$")

# issues 目录探测顺序: 命中第一个已存在的; 都不存在则要求显式 --dir
CANDIDATE_DIRS = ("memory-bank/issues", "issues", "docs/issues")


def stamp(dt: datetime | None = None) -> str:
    return (dt or datetime.now()).strftime("%y-%m-%d-%H%M")


def long_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认脚本目录)向上找 `.git`(目录或 worktree 的 .git 文件)。

    不再按 skill 的安装深度反推(parents[4] 只在 `.agents/skills/<name>/scripts/` 这一种
    布局下成立); 探测不到时退回 parents[4] 兜底, 并允许调用方用 --root 覆盖。
    """
    cur = (start or SCRIPTS_DIR).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]


def resolve_issues_dir(root: Path, dir_arg: str | None = None) -> Path:
    """issues 目录: --dir 显式指定优先, 否则按 CANDIDATE_DIRS 探测已存在的那个。

    不存在(新建项目的第一条 issue)时返回首选候选, 由调用方决定是否报错。
    """
    if dir_arg:
        return (root / dir_arg).resolve()
    for cand in CANDIDATE_DIRS:
        path = root / cand
        if path.is_dir():
            return path.resolve()
    return (root / CANDIDATE_DIRS[0]).resolve()


def dir_of(path: Path, root: Path) -> str:
    """issues 目录相对仓库根的路径(供 --dir 回传与索引文案用); 跨盘时返回绝对路径。

    统一用 `/`(posix)分隔 —— 这个串会进 markdown 链接, Windows 的 `\\` 在链接里是错的。
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def rel_skill(issues_dir: Path) -> str:
    """skill 目录相对 issues 目录的路径(索引 HEADER 的链接用); 跨盘时返回空串(不写链接)。

    用 `os.path.relpath` 而非 `Path.relative_to` —— 后者在目标不是前缀时直接抛错, 而索引
    目录通常在 skill 目录之外, 需要形如 `../../.agents/skills/create-issue` 的回跳路径。
    """
    try:
        rel = os.path.relpath(str(SKILL_DIR.resolve()), str(issues_dir.resolve()))
    except ValueError:
        return ""
    return Path(rel).as_posix()
