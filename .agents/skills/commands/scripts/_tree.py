"""平铺视图: 一次列出全部包与命令 (2026-09-29 起默认, 不再逐级下钻)。

旧设计是"一级只出包 + 常显命令, 靠分层防臃肿"; 改平铺的原因: **每下钻一次 = 多一轮引擎调用**,
多轮往返的 token 成本远大于列表本身变长 —— 而全树实测才 ~30 行, 平铺没有成本。
`list <包路径>` 保留为**聚焦**视图(只看某个子树, 同样递归铺开)。

★ = pin 标记(高频命令记号), 仅作视觉锚点 —— 平铺下每条命令本来就可见, 不再有"浮到父级"行为。
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 允许 `python scripts/run.py` 直接跑

from _config import ConfigError, Pack, Task, Tree  # noqa: E402

W_ID = 30
STAR = "★ "  # pin: 高频命令记号


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


def render(tree: Tree, path: str | None = None) -> str:
    """渲染平铺视图。`path` 为空 = 全树; 给定 = 只看该子树(同样递归铺开)。"""
    if not path:
        owner, subs = None, tree.packs
    else:
        owner = resolve(tree, path)
        if owner is None:
            raise ConfigError(f"[STOP] 找不到包: {path}(用 list 看有哪些包)")
        subs = owner.subs
    lines = [_pad("包 / 命令", W_ID + 2) + "何时用", "─" * 78]
    lines += _level(owner, subs, 0)
    lines.append("")
    lines.append("聚焦某包: list <包>   ·   看单条: show <id>")
    return "\n".join(lines)


def _level(owner: Pack | None, subs: dict[str, Pack], indent: int) -> list[str]:
    """递归铺开: 本级命令在前, 子包(连带它们的子树)随后, 缩进体现从属。"""
    lines: list[str] = []
    if owner is not None:
        for task in sorted(owner.tasks.values(), key=lambda t: t.id):
            lines.append(_task_line(task, indent))
        if not owner.tasks:
            lines.append(f"{' ' * indent}(本层没有命令 —— 在下级子包里)")
    for sub in subs.values():
        if not sub.enabled:
            continue
        lines.append(_pack_line(sub, indent))
        lines += _level(sub, sub.subs, indent + 2)
    return lines


def _pad(text: str, width: int) -> str:
    """按**显示宽度**补齐（CJK 占两列, 否则中文行的列会错位）。"""
    wide = sum(1 for ch in text if unicodedata.east_asian_width(ch) in "WF")
    return text + " " * max(1, width - len(text) - wide)


def _task_line(task: Task, indent: int) -> str:
    # 只出 id 与"何时用" —— 命令本体与 note 留给 show, 否则列表会随命令数一起膨胀
    mark = STAR if task.pin else "  "
    return f"{' ' * indent}{mark}{_pad(task.id, W_ID)}{task.when}"


def _pack_line(pack: Pack, indent: int) -> str:
    return f"{' ' * indent}{_pad(pack.name + '/', W_ID + 2)}{pack.when}"
