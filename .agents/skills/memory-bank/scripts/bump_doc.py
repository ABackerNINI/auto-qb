#!/usr/bin/env python3
"""`kb.bump` —— 文档改版的一次落盘 (计划 memory-bank/plans/26-10-17-0527 P2, §03)。

一次逻辑动作 = 一条命令: note 随参数带入, **不为 bump 再开一次编辑** —— 抬时间戳
(timekit 单点) / 写变更记录行 / 抬 Updated / 抬切片最后活动 / 重跑索引, 全部派生。

载体与动作 (单点: `_common.DOC_KIND_*`):
- 计划 (`plans/*.html`): 抬 `doc-updated` (stamp) + `## 变更记录` 追加 R 行 (编号 = 段内最大 + 1)
- 报告 (`reports/*.html`): 同上 —— **但多数报告无变更记录段**: 缺段即 fail-fast 并指路
  (直编辑正文 / 补段), 不猜位置硬塞
- 任务档案 (`tasks/*.md`): 抬 `**Updated:**` (日期)
- 会话切片 (`activeContext/*.md`): 抬 `> 最后活动:` (严格 YYYY-MM-DD HH:MM)
- issue (`issues/*.html`): 自己的约定 (create-issue skill, 跨 skill 不 import 单点纪律) —— 拒绝并指路

fail-fast (黄金法则): 载体不认识 / 缺状态行或变更记录段一律 rc=1 (原因与下一步打在输出里);
HTML 变更记录只追加 li 行, 已有行零触碰。末尾固定输出「剩余人工 0 项(判断 0 · 条件 0 ·
**机械 0**)」契约 (§5.4 收录断言, §5.3: kb.bump 判断 0 / 条件 0 / 机械 0)。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/bump_doc.py <path> --note "一句话说清这版改了什么"
    python <skill-dir>/scripts/bump_doc.py --root <dir> --mb-dir <dir> <path> --note ".."
退出码: 0 成功 / 1 拒绝或校验失败 (原因与下一步打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import timekit  # noqa: E402  (时间单点: UTC+8 naive 墙钟, 与 kb.time 同源)
from _common import (  # noqa: E402
    DOC_KIND_CN,
    DOC_KIND_INDEX_SCRIPT,
    DOC_KIND_ISSUE,
    DOC_KIND_PLAN,
    DOC_KIND_SLICE,
    DOC_KIND_TASK,
    StatusVocabularyError,
    detect_doc_kind,
    find_root,
    rel_posix,
    rebuild_index,
    resolve_doc_path,
    resolve_mb_dir,
    set_html_meta,
    set_last_active,
    set_md_field,
    sync_body_meta,
)

# `## 变更记录` 段标题 (模板 §10 / 计划实例同款: `<h2><span class="no">§10</span>变更记录</h2>`)
CHANGELOG_H2_RE = re.compile(r"<h2[^>]*>(?:(?!</h2>).)*变更记录(?:(?!</h2>).)*</h2>", re.DOTALL)
NEXT_H2_RE = re.compile(r"<h2\b")
R_NUMBER_RE = re.compile(r'<span class="tag">R(\d+)')


def _fail(msg: str) -> int:
    sys.stderr.write(f"[STOP] {msg}\n")
    return 1


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _bump_changelog(text: str, note: str, stamp: str) -> tuple[str, int] | None:
    """HTML 变更记录: 在 `## 变更记录` 段的 `<ul>` 末尾追加 R 行 (编号 = 段内最大 + 1)。

    返回 (新 text, 新编号); **段或 ul 缺失返回 None** (调用方 fail-fast —— 不猜位置硬塞)。
    只追加, 已有行零触碰。
    """
    m = CHANGELOG_H2_RE.search(text)
    if not m:
        return None
    section_start = m.end()
    nxt = NEXT_H2_RE.search(text, section_start)
    section_end = nxt.start() if nxt else len(text)
    section = text[section_start:section_end]
    ul = re.search(r"<ul>.*?</ul>", section, re.DOTALL)
    if not ul:
        return None
    numbers = [int(n) for n in R_NUMBER_RE.findall(ul.group(0))]
    next_no = max(numbers) + 1 if numbers else 1
    row = f'  <li><span class="tag">R{next_no} · {stamp}</span> {note}</li>'
    body = ul.group(0)
    inner = body[4:-5]  # 剥掉 <ul> 与 </ul>
    if inner and not inner.endswith("\n"):
        inner += "\n"
    new_ul = f"<ul>{inner}{row}\n</ul>"
    new_section = section[:ul.start()] + new_ul + section[ul.end():]
    return text[:section_start] + new_section + text[section_end:], next_no


def _bump_plan(path: Path, note: str, moment, root: Path) -> tuple[int, list[str]]:
    """计划/报告: 抬 doc-updated + 变更记录追加 R 行。"""
    text = path.read_text(encoding="utf-8")
    stamp = moment.strftime("%y-%m-%d-%H%M")
    bumped = _bump_changelog(text, _html_escape(note), stamp)
    if bumped is None:
        return _fail(
            f"{rel_posix(path, root)}: 无 `## 变更记录` 段 (或段内无 ul) —— kb.bump 不改没有变更记录"
            "档的件: 直接编辑正文; 要留改版痕迹就补一个 `## 变更记录` 段 (ul + R 行) 后再 bump"
        ), []
    text, next_no = bumped
    text = set_html_meta(text, "doc-updated", stamp)
    text = sync_body_meta(text, "doc-updated", stamp)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"已抬 {rel_posix(path, root)}: doc-updated = {stamp}, 变更记录追加 R{next_no} 行")
    return 0, []


def _bump_task(path: Path, note: str, moment, root: Path) -> tuple[int, list[str]]:
    """任务档案: 抬 **Updated:** (日期; note 由调用方带上, 档案进度日志是 kb.wrap 的活)。"""
    text = path.read_text(encoding="utf-8")
    date = moment.strftime("%Y-%m-%d")
    text = set_md_field(text, "Updated", date)
    if text is None:
        return _fail(f"{rel_posix(path, root)}: 头部区缺 `**Updated:**` 行 —— 先补上再 bump"), []
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"已抬 {rel_posix(path, root)}: **Updated:** = {date} (note 只随命令带入; "
          "进度日志追加走 commands run kb.wrap)")
    return 0, []


def _bump_slice(path: Path, note: str, moment, root: Path) -> tuple[int, list[str]]:
    """会话切片: 抬最后活动 (note 只用于回显; 切片正文编辑是判断面, 不走本命令)。"""
    text = path.read_text(encoding="utf-8")
    stamp = moment.strftime("%Y-%m-%d %H:%M")
    text = set_last_active(text, stamp)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"已抬 {rel_posix(path, root)}: 最后活动 = {stamp} (正文编辑是判断面, 自己来)")
    return 0, []


def _print_remaining() -> None:
    """§5.4 输出契约: 三分类清单 + 「机械 0」收录断言 (§5.3: kb.bump 判断 0 / 条件 0 / 机械 0)。"""
    print("剩余人工 0 项(判断 0 · 条件 0 · 机械 0)")
    print("【判断】无 —— note 已随参数带入, 不为 bump 再开一次编辑")
    print("【可选】变更记录行的措辞精修 (复杂改版, 不计步)")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="文档路径 (绝对 / 仓库根相对 / memory-bank 相对, 三种都认)")
    parser.add_argument("--note", required=True, help="一句话: 这版改了什么 (HTML 进变更记录行, 不回显进正文)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    path = resolve_doc_path(args.path, root, mb)
    if not path.is_file():
        return _fail(f"文件不存在: {rel_posix(path, root)} —— 路径三形态 (绝对/仓库根相对/mb 相对) 都不命中")

    kind = detect_doc_kind(path, mb)
    if kind == DOC_KIND_ISSUE:
        return _fail(
            "issue 改版有自己的约定 (create-issue skill, 跨 skill 不 import 单点纪律) —— 不在 kb.bump "
            "范围; 直改正文与 issue-stamp, 重建索引走 commands run kb.index"
        )
    if kind == DOC_KIND_SLICE:
        pass  # 切片可 bump: 只抬最后活动 (正文编辑是判断面)
    elif kind not in (DOC_KIND_PLAN, DOC_KIND_TASK):
        return _fail(
            f"载体不在改面范围: {rel_posix(path, root)} "
            f"(只认 plans|reports/tasks/activeContext/issues 四类; 当前识别为 {DOC_KIND_CN.get(kind, kind) or '未知'})"
        )

    moment = timekit.now()
    if kind == DOC_KIND_PLAN:
        rc, hints = _bump_plan(path, args.note, moment, root)
    elif kind == DOC_KIND_TASK:
        rc, hints = _bump_task(path, args.note, moment, root)
    else:  # DOC_KIND_SLICE
        rc, hints = _bump_slice(path, args.note, moment, root)
    if rc != 0:
        return rc

    # --- bump 后重建受影响索引 (切片无索引 → 空表; 与 kb.index 同一 build 实现)
    try:
        rebuilt = rebuild_index(root, mb, DOC_KIND_INDEX_SCRIPT.get(kind, ""))
    except StatusVocabularyError as exc:
        sys.stderr.write(f"[STOP] 已 bump, 但索引重建失败 (词表问题必须先修): {exc}\n"
                         "处置后运行 commands run kb.index 重建索引\n")
        return 1
    if rebuilt:
        print("已重建索引: " + ", ".join(rel_posix(p, root) for p in rebuilt))

    print()
    _print_remaining()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
