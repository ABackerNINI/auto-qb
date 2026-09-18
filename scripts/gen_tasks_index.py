"""生成 `memory-bank/tasks/_index.md`(生成物, 不要手改)。

用法:
    python scripts/gen_tasks_index.py          写回 _index.md
    python scripts/gen_tasks_index.py --check  只比对, 不一致则退出码 1(供 pytest 守卫调用)

设计要点(见 docs/plans/26-09-18-1928-memory-bank-task-id-plan.html):
- 索引从"人人手改的源文件"降级为生成物, 合并冲突的解决方式变成"任一方重跑一次脚本"。
- 分区内按 `**Updated:**`(缺失则 `**Added:**` / `**Started:**`)**倒序** —— 活跃度信号来自更新时间,
  不来自文件名的创建日期, 避免"老但仍在进行的任务沉底"。
- 摘要数据源是档案头部的 `**Summary:**` 一行; 缺失则该条目只显示标题。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "memory-bank" / "tasks"
INDEX = TASKS / "_index.md"

STATUSES = ("In Progress", "Pending", "Completed", "Abandoned")
STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(In Progress|Pending|Completed|Abandoned)")
SUMMARY_RE = re.compile(r"\*\*Summary:\*\*\s*(.+)")
TITLE_RE = re.compile(r"^#\s+(\S+)\s*[—-]\s*(.+?)\s*$", re.MULTILINE)
UPDATED_RE = re.compile(r"\*\*Updated:\*\*\s*(\d{4}-\d{2}-\d{2})")
ADDED_RE = re.compile(r"\*\*(?:Added|Started):\*\*\s*(\d{4}-\d{2}-\d{2})")

HEADER = """# Tasks Index

> **本文件是生成物, 不要手改** —— 由 `scripts/gen_tasks_index.py` 扫描 `tasks/*.md` 的 `Status` / `Summary` / 标题生成; 新增或改状态后跑 `python scripts/gen_tasks_index.py` 重建即可, 合并冲突也只需重跑。
> 档案命名 `YY-MM-DD-<slug>.md`(见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md)); 旧编号保留在各档案的 `**Legacy-ID:**` 字段, 供历史文档回溯。
> 粒度为**专题**(一个功能线一个档案, 不逐会话建文件); 历史流水账原文归档在各档案的 `## 历史会话纪要 (原文归档)` 段。
> 日常短周期工作只记 [../activeContext.md](../activeContext.md); 完成项沉淀进 [../progress.md](../progress.md)。
> 机械守卫: `tests/test_memory_bank.py`(索引 == 生成结果 / slug 唯一 / 命名规范 / 状态分区 / 必备章节)。
"""

EMPTY_HINT = {
    "Pending": "(暂无 — 下一步候选见 [../activeContext.md](../activeContext.md) 的\"下一步候选\"段)",
}


def _sort_key(item: dict) -> str:
    return item["updated"] or item["added"] or ""


def collect() -> list[dict]:
    items = []
    for path in sorted(TASKS.glob("*.md")):
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
                "status": status_match.group(1) if status_match else "Pending",
                "title": title_match.group(2) if title_match else path.stem,
                "summary": summary_match.group(1).strip() if summary_match else "",
                "updated": updated_match.group(1) if updated_match else "",
                "added": added_match.group(1) if added_match else "",
            }
        )
    return items


def render(items: list[dict]) -> str:
    out = [HEADER]
    for status in STATUSES:
        group = [i for i in items if i["status"] == status]
        out.append(f"## {status}\n")
        if not group:
            out.append(EMPTY_HINT.get(status, "(暂无)"))
            out.append("")
            continue
        for item in sorted(group, key=_sort_key, reverse=True):
            line = f"- [{item['slug']}] {item['title']}"
            if item["summary"]:
                line += f" - {item['summary']}"
            out.append(line)
        out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件")
    args = parser.parse_args()

    rendered = render(collect())
    if args.check:
        current = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if current != rendered:
            sys.stderr.write("_index.md 与生成结果不一致, 请运行 python scripts/gen_tasks_index.py\n")
            return 1
        return 0

    INDEX.write_text(rendered, encoding="utf-8")
    print(f"已生成 {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
