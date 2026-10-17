#!/usr/bin/env python3
"""`kb.status` —— 翻转文档状态 (计划 memory-bank/plans/26-10-17-0527 P2, §03)。

一次逻辑动作 = 一条命令: 取时 (timekit 单点) / 载体探测 / 词表校验 (单点 import) /
改状态行 / 自动抬 doc-updated 或 Updated / 重跑索引, 全部派生; 终态提醒内嵌在输出里
(Done → 同专题切片迁出 / Summary 收口), 不必另开一次编辑。

载体与词表 (单点: `_common.DOC_KIND_*` / `DOC_KIND_STATUSES`):
- 计划 / 报告 (`plans|reports/*.html`): `doc-status` 5 词表, 翻转抬 `doc-updated` (stamp)
- 任务档案 (`tasks/*.md`): `**Status:**` 4 词表, 翻转抬 `**Updated:**` (日期)
- 会话切片 (`activeContext/*.md`): **无状态** —— 拒绝并指路迁出流程 (切片走 kb.wrap)
- issue (`issues/*.html`): 自己的词表与索引生成器在 create-issue skill (跨 skill 不 import
  单点纪律) —— 拒绝并指路, 不在 kb.status 范围

幂等与 fail-fast (黄金法则): 同状态翻转 = 幂等无改动 (不抬时间戳、不重建索引);
词表外值 / 载体不认识 / 缺状态行一律 rc=1 拒绝 (原因与下一步打在输出里)。
末尾固定输出「剩余人工 N 项(判断 0 · 条件 b · **机械 0**)」契约 (§5.4 收录断言)。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/flip_status.py <path> <to>
    python <skill-dir>/scripts/flip_status.py --root <dir> --mb-dir <dir> <path> <to>
退出码: 0 成功 / 1 拒绝或校验失败 (原因与下一步打在输出里)
"""

from __future__ import annotations

import argparse
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
    DOC_KIND_STATUSES,
    DOC_KIND_TASK,
    SLICE_FILE_RE,
    TERMINAL_DOC_STATUSES,
    StatusVocabularyError,
    detect_doc_kind,
    find_root,
    html_meta,
    md_field,
    rel_posix,
    rebuild_index,
    resolve_doc_path,
    resolve_mb_dir,
    set_html_meta,
    set_md_field,
    sync_body_meta,
)

# 终态的子集 (两个词表的并集口径: 5 词表的完结态; 档案 4 词表的完结态 = Done/Dropped,
# 不在 TERMINAL_DOC_STATUSES 里的 "Superseded" 是制品专属, 对档案无意义)
TASK_TERMINAL = frozenset({"Done", "Dropped"})


def _fail(msg: str) -> int:
    sys.stderr.write(f"[STOP] {msg}\n")
    return 1


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _same_topic_slices(mb: Path, topic: str) -> list[Path]:
    """同专题切片 (文件名 `<stamp>-<topic>.md`; endswith 精确匹配, 不误伤更长 slug)。"""
    if not topic:
        return []
    return sorted(p for p in (mb / "activeContext").glob(f"*-{topic}.md") if SLICE_FILE_RE.match(p.name))


def _flip_plan(path: Path, to: str, moment, root: Path, mb: Path) -> tuple[int, list[str], bool]:
    """计划/报告: doc-status 翻转 + 抬 doc-updated (stamp)。返回 (rc, 条件提醒, 是否有改动)。"""
    text = path.read_text(encoding="utf-8")
    current = html_meta(text, "doc-status")
    if current is None:
        return _fail(f"{rel_posix(path, root)}: 缺 `doc-status` meta —— 先补上再翻转"), [], False
    if current == to:
        return 0, [], False  # 幂等: 不抬时间戳、不重建索引 (main 统一打印)
    text = set_html_meta(text, "doc-status", to)
    text = set_html_meta(text, "doc-updated", moment.strftime("%y-%m-%d-%H%M"))
    text = sync_body_meta(text, "doc-status", to)
    text = sync_body_meta(text, "doc-updated", moment.strftime("%y-%m-%d-%H%M"))
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"已翻转 {rel_posix(path, root)}: doc-status {current} → {to} (doc-updated 已抬)")

    hints: list[str] = []
    if to in TERMINAL_DOC_STATUSES:
        topic = html_meta(text, "doc-topic") or ""
        slices = _same_topic_slices(mb, topic)
        if slices:
            names = ", ".join(rel_posix(p, root) for p in slices)
            hints.append(
                f"同专题切片 {len(slices)} 份 ({names}) —— 专题已完结, 蒸馏/迁出 activeContext "
                "(只住活切片): 有结论的迁 testing/baselines/ 或专题目录, 无结论的直接删"
            )
        else:
            hints.append(f"无同专题切片可迁出 (doc-topic={topic!r}); 如另有手工切片, 收尾统一走 kb.wrap")
    return 0, hints, True


def _flip_task(path: Path, to: str, moment, root: Path) -> tuple[int, list[str], bool]:
    """任务档案: **Status:** 翻转 + 抬 **Updated:** (日期)。返回 (rc, 条件提醒, 是否有改动)。"""
    text = path.read_text(encoding="utf-8")
    current = md_field(text, "Status")
    if current is None:
        return _fail(f"{rel_posix(path, root)}: 头部区缺 `**Status:**` 行 —— 先补上再翻转"), [], False
    if current == to:
        return 0, [], False  # 幂等
    text = set_md_field(text, "Status", to)
    text = set_md_field(text, "Updated", moment.strftime("%Y-%m-%d"))
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"已翻转 {rel_posix(path, root)}: Status {current} → {to} (**Updated:** 已抬)")

    hints: list[str] = []
    if to in TASK_TERMINAL:
        summary = md_field(text, "Summary") or ""
        hints.append(f"Summary 收口 (裁定 A1: 首次追加进度时精修, 可选不计步): 当前 = 「{summary}」; "
                     "完结时精修成一句结论 —— 它是索引里的摘要, 空/糙比待提交更伤索引")
    return 0, hints, True


def _print_remaining(condition_count: int) -> None:
    """§5.4 输出契约: 三分类清单 + 「机械 0」收录断言 (§5.3: kb.status 判断 0 / 条件 = 终态提醒)。"""
    print(f"剩余人工 0 项(判断 0 · 条件 {condition_count} · 机械 0)")
    if condition_count:
        print("【条件】终态提醒见上 (切片迁出 / Summary 收口) —— 做与不做都不拦提交, 但做完更干净")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="文档路径 (绝对 / 仓库根相对 / memory-bank 相对, 三种都认)")
    parser.add_argument("to", help="目标状态 (计划/报告 5 词表; 档案 4 词表; 单点 import 校验)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    path = resolve_doc_path(args.path, root, mb)
    if not path.is_file():
        return _fail(f"文件不存在: {rel_posix(path, root)} —— 路径三形态 (绝对/仓库根相对/mb 相对) 都不命中")

    kind = detect_doc_kind(path, mb)
    if kind == DOC_KIND_SLICE:
        return _fail(
            "会话切片无状态可翻 (拍板: 切片统一由 kb.wrap 收尾处理) —— "
            '续作抬最后活动/追加 R 行走 commands run kb.wrap --topic <slug> --did ".."; '
            "专题完结的切片蒸馏/迁出, 不是改状态"
        )
    if kind == DOC_KIND_ISSUE:
        return _fail(
            "issue 状态有自己的词表与索引生成器 (create-issue skill, 跨 skill 不 import 单点纪律) —— "
            "不在 kb.status 范围; 直改 issue-status meta 后重跑 commands run kb.index"
        )
    if kind not in DOC_KIND_STATUSES:
        return _fail(
            f"载体不在改面范围: {rel_posix(path, root)} "
            f"(只认 plans|reports/tasks/activeContext/issues 四类; 当前识别为 {DOC_KIND_CN.get(kind, kind) or '未知'})"
        )

    # --- 词表校验 (fail-fast: 之后假定状态合法; 表外值会让索引静默漏收, 见 doc-status-meta 坑档)
    statuses = DOC_KIND_STATUSES[kind]
    if args.to not in statuses:
        return _fail(
            f"状态 {args.to!r} 不在 {DOC_KIND_CN[kind]}词表 ({' / '.join(statuses)}) —— "
            "单点 import, 别凭记忆写; 表外值会让索引静默漏收该件"
        )

    moment = timekit.now()
    if kind == DOC_KIND_PLAN:
        rc, hints, changed = _flip_plan(path, args.to, moment, root, mb)
    else:  # DOC_KIND_TASK
        rc, hints, changed = _flip_task(path, args.to, moment, root)
    if rc != 0:
        return rc
    if not changed:
        print(f"状态已是 {args.to} —— 幂等, 无改动 (不抬时间戳、不重建索引)")
        print()
        _print_remaining(0)
        return 0

    # --- 翻转后重建受影响索引 (与 kb.index 同一 build 实现)
    try:
        rebuilt = rebuild_index(root, mb, DOC_KIND_INDEX_SCRIPT[kind])
    except StatusVocabularyError as exc:
        sys.stderr.write(f"[STOP] 状态已翻, 但索引重建失败 (词表问题必须先修): {exc}\n"
                         "处置后运行 commands run kb.index 重建索引\n")
        return 1
    if rebuilt:
        print("已重建索引: " + ", ".join(rel_posix(p, root) for p in rebuilt))

    print()
    _print_remaining(len(hints))
    for hint in hints:
        print(f"【条件】{hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
