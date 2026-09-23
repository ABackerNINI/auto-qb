"""层级视图: 包 → 子包 → 命令。

关键约束: 一级视图**只出当前层级**(包 + 常显命令), 所以命令总数从十条长到两百条,
一级视图都还是"几个包 + 几条常显" —— 不臃肿靠的是分层, 不是靠写得短。

`--all` 是排障兜底, 不是入口: 一旦被当成常规入口, 臃肿就从那张平表搬到这里。
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 允许 `python scripts/run.py` 直接跑

from _config import ConfigError, Pack, Task, Tree  # noqa: E402

W_ID = 30
STAR = "★ "  # 常显: 从子包浮到父级列表, 不必进到所属包就能看到


def resolve(tree: Tree, path: str) -> Pack | None:
    """按 `a/b/c` 形式的路径在树里定位包; 找不到返回 None。"""
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    packs = tree.packs
    node: Pack | None = None
    for i, part in enumerate(parts):
        node = packs.get(part)
        if node is None:
            return None
        packs = node.subs
    return node


def render(tree: Tree, path: str | None = None, show_all: bool = False) -> str:
    """渲染某一层的视图。`path` 为空 = 一级(顶级包)。"""
    if not path:
        owner, subs = None, tree.packs
    else:
        owner = resolve(tree, path)
        if owner is None:
            raise ConfigError(f"[STOP] 找不到包: {path}(用 list 看有哪些包)")
        subs = owner.subs
    lines = [_pad("包 / 命令", W_ID + 2) + "何时用", "─" * 78]
    lines += _level(owner, subs, 0, show_all)
    if not show_all and subs:
        lines.append("")
        lines.append("下钻: list <包>/<子包>   ·   全量(排障): list --all")
    return "\n".join(lines)


def _level(owner: Pack | None, subs: dict[str, Pack], indent: int, show_all: bool) -> list[str]:
    lines: list[str] = []
    if owner is not None:
        for task in sorted(owner.tasks.values(), key=lambda t: t.id):
            lines.append(_task_line(task, indent))
        if not owner.tasks:
            lines.append(f"{' ' * indent}(本层没有命令 —— 在下级子包里)")
    for sub in subs.values():
        if not sub.enabled and not show_all:
            continue
        lines.append(_pack_line(sub, indent))
        # 常显浮一级: 子包里标了 pin 的命令, 在父级列表就能看到
        for task in sorted(sub.tasks.values(), key=lambda t: t.id):
            if task.pin:
                lines.append(_task_line(task, indent + 2, star=True))
        if show_all:
            lines += _level(sub, sub.subs, indent + 2, show_all)
    return lines


def _pad(text: str, width: int) -> str:
    """按**显示宽度**补齐（CJK 占两列, 否则中文行的列会错位）。"""
    wide = sum(1 for ch in text if unicodedata.east_asian_width(ch) in "WF")
    return text + " " * max(1, width - len(text) - wide)


def _task_line(task: Task, indent: int, star: bool = False) -> str:
    # 只出 id 与"何时用" —— 命令本体与 note 留给 show, 否则一级视图会随命令数一起膨胀
    mark = STAR if (star or task.pin) else "  "
    return f"{' ' * indent}{mark}{_pad(task.id, W_ID)}{task.when}"


def _pack_line(pack: Pack, indent: int) -> str:
    tag = "" if pack.enabled else "  [已禁用]"
    return f"{' ' * indent}{_pad(pack.name + '/', W_ID + 2)}{pack.when}{tag}"
