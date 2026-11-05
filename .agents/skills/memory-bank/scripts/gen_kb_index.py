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
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ABOUT_NAME,
    CAP_POLICY,
    INDEX_NAME,
    find_root,
    gen_cmd,
    iter_indexed_dirs,
    iter_topic_files,
    read_meta,
    rel_link,
    resolve_mb_dir,
)

# 单份索引的字符预算 = `index-auto` 的 cap(单点: `_common.CAP_POLICY`)。
# 主题多到一份装不下时按文件名**分卷**(`_index-1.md` …), 主索引退化为分卷路由 ——
# 2026-11-05 B4: 缩摘要救不回 96 个主题(`web-ui` 26,615), 但每行都要保留「一句话/触发词」,
# 所以选择「一处只回答一件事」: 主索引给路由, 卷内给定位。
INDEX_BUDGET = CAP_POLICY["index-auto"]


def _cell(text: str) -> str:
    """表格单元: 转义 `|`, 空值给占位符。"""
    return text.replace("|", "\\|") if text else "—"


# 索引行里「一句话 / 触发词」的截断长度 —— 与 `gen_tasks_index.SUMMARY_MAX` 同款病:
# 摘要与触发词**只增不减**, 整条打进索引后索引大小由「元数据写得多长」决定, 而不是由「有几个主题」。
# 2026-10-11 实测: `pitfalls/web-ui/_index.md` 55 个主题 ⇒ 25,940 撞 `index-auto` cap (25,200),
# 其中摘要总长 14,868(均值 270!) / 触发词总长 7,378(均值 134) —— 主题数远没到上限, 是元数据顶爆。
# 截断到 (140, 120) 后 15,647(余量 9,553, 还够 ~20 个新主题); 摘要/触发词全文点开主题文件就有,
# 无信息损失。**触发词也截**是无奈: 它同样是索引行的大头(均值 134), 只截摘要的话余量不够。
# ⚠ 别条件反射抬 cap: 先量「去掉两列后占 cap 多少」 —— 那才是条目数本身能否容纳的判据。
SUMMARY_MAX = 140
TRIGGER_MAX = 120


def _clip(text: str, limit: int) -> str:
    """截断到 `limit` 字符, 超长加省略号(中文一字一字符, 与 cap 口径一致)。"""
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


TOPIC_TABLE = ["", "## 主题", "", "| 主题 | 一句话 | 触发词 |", "|---|---|---|"]


def _header(directory: Path, root: Path, mb: Path) -> list[str]:
    """目录级头部(不含类表/主题表) —— 主索引与卷页共用, 保证「谁生成的」只有一个说法。"""
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
    return lines


def _class_rows(directory: Path) -> list[str]:
    """子目录类表 (pitfalls/ 的两级指针); 无子目录返回空表。"""
    subdirs = [d for d in sorted(directory.iterdir()) if d.is_dir() and (d / ABOUT_NAME).is_file()]
    if not subdirs:
        return []
    lines = ["", "## 类", "", "| 类 | 一句话 | 触发 |", "|---|---|---|"]
    for sub in subdirs:
        meta = read_meta(sub / ABOUT_NAME)
        lines.append(
            f"| [{sub.name}]({rel_link(directory, sub / INDEX_NAME)}) "
            f"| {_cell(_clip(meta.summary or '', SUMMARY_MAX))} "
            f"| {_cell(_clip(meta.triggers or '', TRIGGER_MAX))} |"
        )
    return lines


def _topic_row(path: Path) -> str:
    meta = read_meta(path)
    return (
        f"| [{path.name}]({path.name}) | {_cell(_clip(meta.summary or '', SUMMARY_MAX))} "
        f"| {_cell(_clip(meta.triggers or '', TRIGGER_MAX))} |"
    )


def _title(directory: Path) -> str:
    return read_meta(directory / ABOUT_NAME).title or directory.name


def _single_page(directory: Path, root: Path, mb: Path, rows: list[str]) -> str:
    lines = _header(directory, root, mb) + _class_rows(directory) + TOPIC_TABLE
    lines += rows or ["| (暂无) |  |  |"]
    return "\n".join(lines) + "\n"


def _volume_page(directory: Path, root: Path, mb: Path, n: int, total: int, rows: list[str], names: list[str]) -> str:
    """卷页(只含主题表) —— 主索引给路由, 卷内给定位, 每卷一问。"""
    lines = [
        f"# {_title(directory)} · 卷 {n}/{total}",
        "",
        f"> **本文件是生成物, 不要手改** —— 由 `{gen_cmd(root, 'gen_kb_index.py')}` 生成; "
        f"主索引 [_index.md]({INDEX_NAME}) 是分卷路由。",
        f"> 本卷主题: `{names[0]}` … `{names[-1]}`(共 {len(names)} 条); "
        f"主题越多时索引按文件名分卷, 每卷 ≤ {INDEX_BUDGET:,} 字符。",
        "> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。",
        *TOPIC_TABLE,
        *rows,
    ]
    return "\n".join(lines) + "\n"


def _router_page(directory: Path, root: Path, mb: Path, names: list[str], chunks: list[tuple[int, list]]) -> str:
    lines = _header(directory, root, mb) + _class_rows(directory) + [
        "",
        "## 主题(分卷)",
        "",
        f"> 主题较多, 按文件名分卷存放(每卷 ≤ {INDEX_BUDGET:,} 字符): 先按「主题范围」选卷, 再进卷内定位。",
        "",
        "| 卷 | 主题范围 | 条数 |",
        "|---|---|---|",
    ]
    for n, (start, chunk) in enumerate(chunks, 1):
        lines.append(
            f"| [{n}]({volume_name(n)}) | `{names[start]}` … `{names[start + len(chunk) - 1]}` "
            f"| {len(chunk)} |"
        )
    return "\n".join(lines) + "\n"


def volume_name(n: int) -> str:
    return f"_index-{n}.md"


def _chunks(seq: list, parts: int) -> list[tuple[int, list]]:
    """均匀切片 (按条数, 不按字符) —— 卷数确定后各卷长度尽量一致, 便于「范围」浏览。
    返回 `(起始下标, 切片)`。"""
    size = math.ceil(len(seq) / parts)
    return [(i, seq[i:i + size]) for i in range(0, len(seq), size)]


def render_pages(directory: Path, root: Path, mb: Path) -> dict[Path, str]:
    """一个索引目录的全部页面: {主索引或卷页路径: 内容}。

    单份装得下就是一份(`_index.md`); 装不下按文件名分卷, 主索引退化为路由。
    卷数从 2 递增试算, 第一个「每卷都 ≤ `INDEX_BUDGET`」的方案即采用 —— 确定性, 无随机。
    """
    topics = iter_topic_files(directory)
    rows = [_topic_row(p) for p in topics]
    names = [p.name for p in topics]
    single = _single_page(directory, root, mb, rows)
    if len(single) <= INDEX_BUDGET:
        return {directory / INDEX_NAME: single}
    for parts in range(2, len(rows) + 1):
        name_chunks = _chunks(names, parts)
        pages: dict[Path, str] = {}
        for n, (start, name_chunk) in enumerate(name_chunks, 1):
            text = _volume_page(
                directory, root, mb, n, len(name_chunks), rows[start:start + len(name_chunk)], name_chunk
            )
            if len(text) > INDEX_BUDGET:
                pages = {}
                break
            pages[directory / volume_name(n)] = text
        if pages:
            pages[directory / INDEX_NAME] = _router_page(directory, root, mb, names, name_chunks)
            return pages
    # 单条都装不下(极端): 退回单页, 让 `doc.caps` 照实报债 —— 不静默丢内容
    return {directory / INDEX_NAME: single}


def render_dir(directory: Path, root: Path, mb: Path) -> str:
    """渲染一个目录的 `_index.md`(分卷时为主索引/路由页)。"""
    return render_pages(directory, root, mb)[directory / INDEX_NAME]


def build_all(root: Path, mb: Path) -> dict[Path, str]:
    """全库索引的目标内容: {索引/卷页路径: 应写内容}。"""
    out: dict[Path, str] = {}
    for directory in iter_indexed_dirs(mb):
        out.update(render_pages(directory, root, mb))
    return out


def stale_volume_pages(mb: Path, expected: dict[Path, str]) -> list[Path]:
    """磁盘上有、生成结果不再需要的卷页(主题变少/改名后残留) —— 由重建入口删除。"""
    return [p for p in sorted(mb.rglob("_index-*.md")) if p not in expected]


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
        # newline="\n": 生成物一律 LF —— write_text 默认按 os.linesep 翻换行, Windows 上会写成 CRLF
        # (纯行尾噪音, 见 pitfalls/git/editing-traps.md)。守阵 test_generated_indexes_are_lf_only。
        index.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"已生成 {len(targets)} 个索引" + (f" (--dir {args.dir})" if args.dir else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
