"""通用索引生成器: 给一个目录, 扫主题文件的三行头元数据 → 渲染 `_index.md`。

一套代码覆盖全库, 两种输入同一个实现:
- 目录下有子目录 (各有 `_about.md`) → 额外渲染「类」区 (`pitfalls/` 的两级指针)
- 没有子目录 → 只渲染「主题」区 (`testing/` 一级指针)

数据源 (手写的只有这些):
    <dir>/<topic>.md     →  # 标题 / > 摘要: … / > 触发: …
    <dir>/_about.md      →  目录元数据 (标题 / 一句话 / 触发条件)
    <dir>/_index.md      →  **生成物** (每个主题一行指针, 或每个类一行指针)

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_kb_index.py                     重建全库所有 _index.md
    python <skill-dir>/scripts/gen_kb_index.py --check             只比对 (闸门与守卫用)
    python <skill-dir>/scripts/gen_kb_index.py --dir memory-bank/testing   只重建一个目录

「索引目录」是**自发现**的: 含 `_about.md` 的目录即纳入 (`tasks/` `issues/` 有自己的生成器,
没有 `_about.md`, 天然不在结果里)。新增一个目录 = 建目录 + 写 `_about.md` + 写主题文件 + 重跑本脚本。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ABOUT_NAME,
    INDEX_NAME,
    find_root,
    gen_cmd,
    iter_indexed_dirs,
    iter_topic_files,
    read_meta,
    rel_link,
    resolve_mb_dir,
)


def _cell(text: str) -> str:
    """表格单元: 转义 `|`, 空值给占位符。"""
    return text.replace("|", "\\|") if text else "—"


def render_dir(directory: Path, root: Path, mb: Path) -> str:
    """渲染一个目录的 `_index.md`。"""
    about = read_meta(directory / ABOUT_NAME)
    title = about.title or directory.name
    readme_link = rel_link(directory, mb / "README.md")

    lines = [
        f"# {title}",
        "",
        f"> **本文件是生成物, 不要手改** —— 由 `{gen_cmd(root, 'gen_kb_index.py')}` 扫描本目录主题文件的"
        "三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。",
        f"> 库内细路由见 [memory-bank/README.md]({readme_link})。",
        "> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。",
    ]
    if about.summary:
        lines.append(f"> **摘要**: {about.summary}")
    if about.triggers:
        lines.append(f"> **触发**: {about.triggers}")

    subdirs = [d for d in sorted(directory.iterdir()) if d.is_dir() and (d / ABOUT_NAME).is_file()]
    if subdirs:
        lines += ["", "## 类", "", "| 类 | 一句话 | 触发 |", "|---|---|---|"]
        for sub in subdirs:
            meta = read_meta(sub / ABOUT_NAME)
            lines.append(
                f"| [{sub.name}]({rel_link(directory, sub / INDEX_NAME)}) "
                f"| {_cell(meta.summary)} | {_cell(meta.triggers)} |"
            )

    topics = iter_topic_files(directory)
    lines += ["", "## 主题", "", "| 主题 | 一句话 | 触发词 |", "|---|---|---|"]
    if topics:
        for path in topics:
            meta = read_meta(path)
            lines.append(f"| [{path.name}]({path.name}) | {_cell(meta.summary)} | {_cell(meta.triggers)} |")
    else:
        lines.append("| (暂无) |  |  |")

    return "\n".join(lines) + "\n"


def build_all(root: Path, mb: Path) -> dict[Path, str]:
    """全库 `_index.md` 的目标内容: {索引路径: 应写内容}。"""
    return {directory / INDEX_NAME: render_dir(directory, root, mb) for directory in iter_indexed_dirs(mb)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件 (不一致则退出码 1)")
    parser.add_argument("--dir", help="只处理这一个目录 (仓库相对路径或绝对路径)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    if not mb.is_dir():
        sys.stderr.write(f"memory-bank 目录不存在: {mb}\n")
        return 2

    targets = build_all(root, mb)
    if args.dir:
        want = Path(args.dir)
        want = (want if want.is_absolute() else root / want).resolve()
        if want not in targets:
            sys.stderr.write(f"{want} 不是索引目录 (缺 {ABOUT_NAME}?)\n")
            return 2
        targets = {want: targets[want]}

    if args.check:
        drifted = []
        for index, rendered in targets.items():
            current = index.read_text(encoding="utf-8") if index.exists() else ""
            if current != rendered:
                drifted.append(index)
        if drifted:
            for index in drifted:
                sys.stderr.write(f"{index.relative_to(root)} 与生成结果不一致\n")
            sys.stderr.write(f"请运行 {gen_cmd(root, 'gen_kb_index.py')} 重建\n")
            return 1
        return 0

    for index, rendered in targets.items():
        index.write_text(rendered, encoding="utf-8")
    print(f"已生成 {len(targets)} 个索引" + (f" (--dir {args.dir})" if args.dir else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
