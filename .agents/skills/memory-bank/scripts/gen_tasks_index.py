"""生成 `memory-bank/tasks/_index.md`(生成物, 不要手改)。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录, 本仓库是
`.agents/skills/memory-bank`):
    python <skill-dir>/scripts/gen_tasks_index.py          写回 _index.md
    python <skill-dir>/scripts/gen_tasks_index.py --check  只比对, 不一致则退出码 1(供守卫调用)
    python <skill-dir>/scripts/gen_tasks_index.py --root <dir> --mb-dir <dir>   # 覆盖探测

设计要点(见 memory-bank/plans/26-09-18-1928-memory-bank-task-id-plan.html):
- 索引从"人人手改的源文件"降级为生成物, 合并冲突的解决方式变成"任一方重跑一次脚本"。
- 分区内按 `**Updated:**`(缺失则 `**Added:**` / `**Started:**`)**倒序** —— 活跃度信号来自更新时间,
  不来自文件名的创建日期, 避免"老但仍在进行的任务沉底"。
- 摘要数据源是档案头部的 `**Summary:**` 一行; 缺失则该条目只显示标题。

落位: 本脚本 2026-09-22 从仓库根 `scripts/` 迁入 memory-bank skill (它实现的是 Memory Bank
**模式**本身, 不是本项目业务) —— 这样跨 clone / 跨项目共用一份, 也避免各项目各写一版慢慢分叉。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    ARCHIVE_REL, CLOSED_KEEP, TASK_STATUSES as STATUSES, TERMINAL_TASK_STATUSES,
    closed_hidden_note, find_root, gen_cmd, keep_closed_window, resolve_mb_dir,
)

# 4 词表单点 = `_common.TASK_STATUSES` (2026-10-17 P1 收敛: 原先本地定义, `kb.new` / 检查器
# 要同源校验档案状态行, 两处定义必然漂移)。
STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(In Progress|Open|Done|Dropped)")
SUMMARY_RE = re.compile(r"\*\*Summary:\*\*\s*(.+)")
TITLE_RE = re.compile(r"^#\s+(\S+)\s*[—-]\s*(.+?)\s*$", re.MULTILINE)
UPDATED_RE = re.compile(r"\*\*Updated:\*\*\s*(\d{4}-\d{2}-\d{2})")
ADDED_RE = re.compile(r"\*\*(?:Added|Started):\*\*\s*(\d{4}-\d{2}-\d{2})")

EMPTY_HINT = {
    "Open": "(暂无 — 下一步候选见 `想法.md` 待办与 [../progress/roadmap.md](../progress/roadmap.md))",
}

# 索引行里摘要的截断长度。**这是索引不膨胀的关键**: 摘要全文只增不减, 若整条打进索引,
# 索引大小就由「摘要写得多长」决定而不是由「有几个档案」决定 —— 2026-09-23 实测 33 个档案
# 平均 350 字符/行、索引 12,299 撞 `index-auto` cap, 而条目数本身远没到上限。
# 截断后索引 ≈ 626 + 33×~120, 同样 12,000 的 cap 能容纳 ~90 个档案; 摘要全文点开档案就有, 无信息损失。
# 2026-10-09 二次校准 80 → 60: 169 个档案(Done 160 恒增)索引 26,162 撞 `index-auto` cap (25,200);
# 判据同 issues 侧 —— **无摘要**口径 12,086(48%) < cap ⇒ 仍是摘要顶爆, 继续压截断而不外迁档案
# (外迁打坏 `**Refs:**` 引用); 压到 60 后 22,869(余量 2,331)。
# 2026-10-11 三次校准 60 → 30: 档案涨到 193(Done 182)索引 25,974 复撞; 判据同前 —— **无摘要**
# 口径 14,427(57%)仍 < cap ⇒ 仍是摘要顶爆, 继续压截断(压到 30 → 20,190, 余量 5,010 ≈ 还能容纳
# ~40 个新档案)。⚠ 无摘要占比已从 48% 升到 57%, 条目数本身成为病根只是时间问题 —— 届时
# 走 issues 侧同款出口(已完结档案只渲染最近 N 条 + 归档索引), 别条件反射抬 cap。
# 2026-10-31 —— 后备出口兑现 (计划 26-10-31-0534 R3): 档案涨到 272(Done 250)索引 28,868 已越
# cap(25,200), 无摘要口径 15,603(62%) ⇒ 摘要砍到 0 都救不回来, 病根确证是条目数本身。
# 正解与 issues 侧同款: Done / Dropped 区只渲染最近 `CLOSED_KEEP` 条, 全量清单另落
# `tasks/attachments/_archive.md`(不计 cap)。实测: 保留 60 条 + 在办 22 条 → 主索引 9,867(余量 15,333)。
SUMMARY_MAX = 30


def build_header(root: Path) -> str:
    cmd = gen_cmd(root, "gen_tasks_index.py")
    archive_rel = ARCHIVE_REL
    return f"""# Tasks Index

> **本文件是生成物, 不要手改** —— 由 `{cmd}` 扫描 `tasks/*.md` 的 `Status` / `Summary` / 标题生成; 新增或改状态后跑它重建即可, 合并冲突也只需重跑。
> 档案命名 `YY-MM-DD-<slug>.md`(见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md)); 旧编号保留在各档案的 `**Legacy-ID:**` 字段, 供历史文档回溯。
> 粒度为**专题**(一个功能线一个档案, 不逐会话建文件); 历史流水账原文归档在各档案的 `## 历史会话纪要 (原文归档)` 段, 超 48 KB 的档案把该段移入 `tasks/attachments/`(索引守卫按 `tasks/*.md` 扫描, 不递归)。
> 本索引里摘要按 `SUMMARY_MAX` **截断**(全文在档案里): 这样索引大小由**档案数**决定, 不随摘要写得多长而膨胀 —— 否则迟早撞 `index-auto` cap, 而靠"外迁老档案"化解会打坏外部引用。
> **已完结状态**(Done / Dropped)只列**最近** `CLOSED_KEEP` 条(更老的**档案原地不动**, 只是不出本索引):
> 条数涨到 250 时索引 28,868 已越 cap(25,200), 压摘要救不回来; 全量清单见
> [{archive_rel}]({archive_rel}), 该目录不计 cap。
> 日常短周期工作只记 [../activeContext/](../activeContext/_about.md) 的会话切片; 完成项沉淀进 [../progress.md](../progress.md)。
> 机械守卫: `tests/test_memory_bank.py`(索引 == 生成结果 / slug 唯一 / 命名规范 / 状态分区 / 必备章节)。
"""


def _sort_key(item: dict) -> str:
    return item["updated"] or item["added"] or ""


def collect(tasks_dir: Path) -> list[dict]:
    items = []
    for path in sorted(tasks_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")

        status_match = STATUS_RE.search(text)
        summary_match = SUMMARY_RE.search(text)
        title_match = TITLE_RE.search(text)
        updated_match = UPDATED_RE.search(text)
        added_match = ADDED_RE.search(text)

        items.append(
            {
                "slug": path.stem,
                "status": status_match.group(1) if status_match else "Open",
                "title": title_match.group(2) if title_match else path.stem,
                "summary": summary_match.group(1).strip() if summary_match else "",
                "updated": updated_match.group(1) if updated_match else "",
                "added": added_match.group(1) if added_match else "",
            }
        )
    return items


def render(items: list[dict], header: str) -> str:
    """主索引: 已完结状态(Done / Dropped)只留最近 `CLOSED_KEEP` 条(档案原地不动, 只是不出索引)。"""
    out = [header]
    for status in STATUSES:
        group = [i for i in items if i["status"] == status]
        out.append(f"## {status}\n")
        if not group:
            out.append(EMPTY_HINT.get(status, "(暂无)"))
            out.append("")
            continue
        ordered, hidden = keep_closed_window(sorted(group, key=_sort_key, reverse=True), status, TERMINAL_TASK_STATUSES)
        for item in ordered:
            line = f"- [{item['slug']}] {item['title']}"
            if item["summary"]:
                summary = item["summary"]
                if len(summary) > SUMMARY_MAX:
                    summary = summary[:SUMMARY_MAX].rstrip() + "…"
                line += f" - {summary}"
            out.append(line)
        if hidden:
            out.append("")
            out.append(closed_hidden_note(hidden, "tasks", "档案"))
        out.append("")
    return "\n".join(out)


def build_archive(root: Path, mb: Path) -> str:
    """归档索引: 全量清单(只列 slug 与标题), 落 `tasks/attachments/`(不计 cap), 保住老档案的可检索性。

    与 `_index.md` **同批**生成(`gen_all` / `rebuild_index` / 本脚本 main 都写两份) ——
    缺了它 `--check` 恒红, 同 `gen_issues_index` 的同批纪律。
    ⚠ 归档行**不带摘要**: 档案 `**Summary:**` 里可能带相对 `tasks/` 的链接, 搬进
    `attachments/` 会位移成坏链(`check_doc_links` 实测首跑就抓出一批) —— 摘要全文点开档案就有。
    """
    items = collect(mb / "tasks")
    out = [
        "# Tasks 归档索引 (全量)",
        "",
        f"> **本文件是生成物, 不要手改** —— 由 `{gen_cmd(root, 'gen_tasks_index.py')}` 与 `_index.md` 同批生成;",
        f"> 主索引的已完结区只列最近 `CLOSED_KEEP` 条(控 cap), **本文件是全量**(只列 slug 与标题; 摘要全文在档案里)。",
        f"> 每条链接指回 `tasks/` 下的档案原文(文件未搬动); 本目录在 `EXCLUDED_DIRS`, 不计 cap。",
        "",
    ]
    for status in STATUSES:
        group = sorted((i for i in items if i["status"] == status), key=_sort_key, reverse=True)
        out.append(f"## {status} ({len(group)})\n")
        if not group:
            out.append("(暂无)")
            out.append("")
            continue
        for item in group:
            out.append(f"- [{item['slug']}](../{item['slug']}.md) {item['title']}")
        out.append("")
    return "\n".join(out)


def build(root: Path, mb: Path) -> str:
    """一步出全文 (守卫与 --check 共用, 保证两条路径同一实现)。"""
    return render(collect(mb / "tasks"), build_header(root))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    index = mb / "tasks" / "_index.md"
    archive = mb / "tasks" / ARCHIVE_REL

    rendered = build(root, mb)
    rendered_archive = build_archive(root, mb)
    if args.check:
        ok = True
        for path, target in ((index, rendered), (archive, rendered_archive)):
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != target:
                sys.stderr.write(f"{path.name} 与生成结果不一致, 请运行 {gen_cmd(root, 'gen_tasks_index.py')}\n")
                ok = False
        return 0 if ok else 1

    # newline="\n": 生成物一律 LF —— write_text 默认按 os.linesep 翻换行, Windows 上会写成 CRLF
    # (纯行尾噪音, 见 pitfalls/git/editing-traps.md)。守阵 test_generated_indexes_are_lf_only。
    index.write_text(rendered, encoding="utf-8", newline="\n")
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(rendered_archive, encoding="utf-8", newline="\n")
    print(f"已生成 {index.relative_to(root)} 与 {archive.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
