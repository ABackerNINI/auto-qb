#!/usr/bin/env python3
"""`kb.status` —— 翻转文档状态 (计划 memory-bank/plans/26-10-17-0527 P2, §03; issue 分支 W4 收编,
计划 26-11-07-0549 D5)。

一次逻辑动作 = 一条命令: 取时 (timekit 单点) / 载体探测 / 词表校验 (单点 import) /
改状态行 / 自动抬 doc-updated 或 Updated, 全部派生; 终态提醒内嵌在输出里
(Done → 同专题切片迁出 / Summary 收口 / issue 修法·理由·指向), 不必另开一次编辑。

载体与词表 (单点: `_common.DOC_KIND_*` / `DOC_KIND_STATUSES`):
- 计划 / 报告 (`plans|reports/*.html`): `doc-status` 5 词表, 翻转抬 `doc-updated` (stamp)
- 任务档案 (`tasks/*.md`): `**Status:**` 4 词表, 翻转抬 `**Updated:**` (日期)
- issue (`issues/*.html`): `issue-status` 5 词表 (与 doc-* 制品同一单点 `DOC_STATUSES`) ——
  状态徽标 + issue-status meta **两处一次改** (徽标锚 = check_status_drift.BADGE_RE, tier B
  机检的同一份正则, 漏改任一处当轮判红) + 「状态变更日志」节追加一行
- 会话切片 (`active-context/*.md`): **无状态** —— 拒绝并指路迁出流程 (切片走 kb.wrap)

幂等与 fail-fast (黄金法则): 同状态翻转 = 幂等无改动 (不追加日志行、不抬时间戳);
词表外值 / 载体不认识 / 缺徽标或 meta / 缺「状态变更日志」节一律 rc=1 拒绝, 且校验全部
先于写盘 (不落半文件 —— 徽标/meta 只改其一正是 tier B 要抓的病态)。
(2026-11-08 重构 W3: 翻转后重建索引的步骤已退役 —— 改面四族的 `_index.md` 随低价值层
移除, kb.status 不再重建任何索引, 见 `_common.rebuild_index` 的收口注记。)
末尾固定输出「剩余人工 N 项(判断 0 · 条件 b · **机械 0**)」契约 (§5.4 收录断言)。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/flip_status.py <path> <to>
    python <skill-dir>/scripts/flip_status.py --root <dir> --mb-dir <dir> <path> <to>
退出码: 0 成功 / 1 拒绝或校验失败 (原因与下一步打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import timekit  # noqa: E402  (时间单点: UTC+8 naive 墙钟, 与 kb.time 同源)
from check_status_drift import BADGE_RE  # noqa: E402  (徽标锚单点: 写侧与 tier B 读侧同一份正则)
from _common import (  # noqa: E402
    DOC_KIND_CN,
    DOC_KIND_ISSUE,
    DOC_KIND_PLAN,
    DOC_KIND_SLICE,
    DOC_KIND_STATUSES,
    DOC_KIND_TASK,
    SLICE_DIR,
    SLICE_FILE_RE,
    TERMINAL_DOC_STATUSES,
    detect_doc_kind,
    find_root,
    html_meta,
    md_field,
    rel_posix,
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
    return sorted(p for p in (mb / SLICE_DIR).glob(f"*-{topic}.md") if SLICE_FILE_RE.match(p.name))


def _flip_plan(path: Path, to: str, moment, root: Path, mb: Path) -> tuple[int, list[str], bool]:
    """计划/报告: doc-status 翻转 + 抬 doc-updated (stamp)。返回 (rc, 条件提醒, 是否有改动)。"""
    text = path.read_text(encoding="utf-8")
    current = html_meta(text, "doc-status")
    if current is None:
        return _fail(f"{rel_posix(path, root)}: 缺 `doc-status` meta —— 先补上再翻转"), [], False
    if current == to:
        return 0, [], False  # 幂等: 不抬时间戳 (main 统一打印)
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
                f"同专题切片 {len(slices)} 份 ({names}) —— 专题已完结, 蒸馏/迁出 active-context "
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
                     "完结时精修成一句结论 —— 空/糙的摘要比待提交更伤续作")
    return 0, hints, True


# issue 终态提醒 (W4): 与计划/档案的终态提醒同一输出面 (【条件】行), 措辞钉住收尾动作。
# Done 对齐标准档模板的「修复后补充」小节 (实际修法/验证方式/测试数字); Dropped/Superseded
# 的理由与指向补在状态变更日志 (行内或再追加一行), 机械行只记翻转本身。
ISSUE_TERMINAL_HINTS = {
    "Done": "补「实际修法 / 验证方式」到正文 (标准档写「修复后补充」小节) —— 日志行只记了状态翻转,"
            " 怎么修的、验证数字是多少要落在正文",
    "Dropped": "在状态变更日志补写明放弃理由 (为何不修 / 不再修)",
    "Superseded": "在状态变更日志补写明指向 (被哪件收编 / 替代)",
}

# 「状态变更日志」节标题锚 (模板 light §04 / standard §07 与存量件同款 `<h2>…状态变更日志</h2>`;
# 形态同 bump_doc.CHANGELOG_H2_RE 的 `变更记录` 锚)。TOC 里的同文名链接不匹配 —— 只认 h2。
ISSUE_LOG_H2_RE = re.compile(r"<h2[^>]*>(?:(?!</h2>).)*状态变更日志(?:(?!</h2>).)*</h2>", re.DOTALL)
NEXT_H2_RE = re.compile(r"<h2\b")


def _append_issue_log(text: str, current: str, to: str, date: str) -> str | None:
    """「状态变更日志」节的 ul 末尾追加一行 `<li>YYYY-MM-DD — 状态 A → B（kb.status）</li>`。

    节按标题锚定位, 追加行缩进对齐节内已有 li; **节或 ul 缺失返回 None** (调用方 fail-fast ——
    不猜位置硬塞, 同 kb.bump 对无变更记录段的纪律); 只追加, 已有行零触碰。
    """
    m = ISSUE_LOG_H2_RE.search(text)
    if not m:
        return None
    nxt = NEXT_H2_RE.search(text, m.end())
    sec_end = nxt.start() if nxt else len(text)
    section = text[m.end():sec_end]
    ul = re.search(r"<ul>.*?</ul>", section, re.DOTALL)
    if not ul:
        return None
    body = ul.group(0)
    ind = re.search(r"\n([ \t]*)<li>", body)
    pad = ind.group(1) if ind else "  "  # 空 ul 缩退 2 空格
    row = f"{pad}<li>{date} — 状态 {current} → {to}（kb.status）</li>"
    inner = body[4:-5].rstrip()  # 剥 <ul>/</ul> 与尾白, 闭合形态保持
    new_ul = f"<ul>{inner}\n{row}\n</ul>"
    new_section = section[:ul.start()] + new_ul + section[ul.end():]
    return text[:m.end()] + new_section + text[sec_end:]


def _flip_issue(path: Path, to: str, moment, root: Path) -> tuple[int, list[str], bool]:
    """issue: 状态徽标 + issue-status meta 两处一次改 + 状态变更日志追加一行 (W4, 计划 26-11-07-0549 D5)。

    返回 (rc, 条件提醒, 是否有改动)。三处锚 (meta / 徽标 / 日志节) **全部先验后写**: 徽标锚 =
    check_status_drift.BADGE_RE (tier B 机检的同一份正则 —— 写侧漏改任一处, tier B 当轮判红);
    日志节按标题锚定位, 缺节不硬塞 (同 kb.bump 对无变更记录段的纪律)。不抬时间戳 —— issue 无
    doc-updated 机制, 留痕就是日志行本身。
    """
    text = path.read_text(encoding="utf-8")
    current = html_meta(text, "issue-status")
    if current is None:
        return _fail(f"{rel_posix(path, root)}: 缺 `issue-status` meta —— 先补上再翻转"), [], False
    if current == to:
        return 0, [], False  # 幂等: 不追加日志行 (main 统一打印)
    badge = BADGE_RE.search(text)
    if badge is None:
        return _fail(
            f"{rel_posix(path, root)}: 状态徽标缺失 (封面「状态」项无 `<span class=\"badge\">`) —— "
            "issue 翻转必须徽标与 meta 两处一致 (check_status_drift tier B 机检), 不做只改一半的翻转; "
            "先补徽标再翻"
        ), [], False
    dated = _append_issue_log(text, current, to, moment.strftime("%Y-%m-%d"))
    if dated is None:
        return _fail(
            f"{rel_posix(path, root)}: 无「状态变更日志」节 (或节内无 ul) —— kb.status 不硬塞: "
            "补一节 `<h2>状态变更日志</h2>` + `<ul>` 后再翻, 或直改徽标与 issue-status meta"
        ), [], False
    # 两处改 + 日志行, 全是内存串操作、写盘在最后 (任一锚缺失都已在上面 fail-fast, 不落半文件):
    # 徽标替换用原文上的位置锚 (BADGE_RE 组 1 的文本 span), 必须最先做; meta 走正则替换; 日志行
    # 按节锚追加 —— 徽标/meta 的改动不影响日志节定位, 追加在改后的文本上重算一次即可。
    text = text[:badge.start(1)] + to + text[badge.end(1):]
    text = set_html_meta(text, "issue-status", to)
    dated = _append_issue_log(text, current, to, moment.strftime("%Y-%m-%d"))
    path.write_text(dated, encoding="utf-8", newline="\n")
    print(f"已翻转 {rel_posix(path, root)}: issue-status {current} → {to} (徽标 + meta 两处一致, "
          "状态变更日志已追加一行)")

    hints: list[str] = []
    if to in TERMINAL_DOC_STATUSES:
        hints.append(f"issue 翻 {to}: {ISSUE_TERMINAL_HINTS[to]}")
    return 0, hints, True


def _print_remaining(condition_count: int) -> None:
    """§5.4 输出契约: 三分类清单 + 「机械 0」收录断言 (§5.3: kb.status 判断 0 / 条件 = 终态提醒)。"""
    print(f"剩余人工 0 项(判断 0 · 条件 {condition_count} · 机械 0)")
    if condition_count:
        print("【条件】终态提醒见上 (切片迁出 / Summary 收口 / issue 修法·理由·指向) "
              "—— 做与不做都不拦提交, 但做完更干净")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="文档路径 (绝对 / 仓库根相对 / memory-bank 相对, 三种都认)")
    parser.add_argument("to", help="目标状态 (计划/报告/issue 5 词表; 档案 4 词表; 单点 import 校验)")
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
    if kind not in DOC_KIND_STATUSES:
        return _fail(
            f"载体不在改面范围: {rel_posix(path, root)} "
            f"(只认 plans|reports/tasks/active-context/issues 四类; 当前识别为 {DOC_KIND_CN.get(kind, kind) or '未知'})"
        )

    # --- 词表校验 (fail-fast: 之后假定状态合法; 词表纪律的活体校验在 gen_doc_map --check)
    statuses = DOC_KIND_STATUSES[kind]
    if args.to not in statuses:
        return _fail(
            f"状态 {args.to!r} 不在 {DOC_KIND_CN[kind]}词表 ({' / '.join(statuses)}) —— "
            "单点 import, 别凭记忆写 (词表纪律的活体校验在 gen_doc_map --check)"
        )

    moment = timekit.now()
    if kind == DOC_KIND_PLAN:
        rc, hints, changed = _flip_plan(path, args.to, moment, root, mb)
    elif kind == DOC_KIND_ISSUE:
        rc, hints, changed = _flip_issue(path, args.to, moment, root)
    else:  # DOC_KIND_TASK
        rc, hints, changed = _flip_task(path, args.to, moment, root)
    if rc != 0:
        return rc
    if not changed:
        print(f"状态已是 {args.to} —— 幂等, 无改动 (不抬时间戳、不追加日志行)")
        print()
        _print_remaining(0)
        return 0

    # (2026-11-08 重构 W3: 翻转后重建索引的步骤已退役 —— 改面四族的 `_index.md` 随低价值层
    # 移除 (D4/D5), kb.status 不再重建任何索引, 也不会重新生已删索引。)

    print()
    _print_remaining(len(hints))
    for hint in hints:
        print(f"【条件】{hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
