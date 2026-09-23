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

from _common import find_root, gen_cmd, resolve_mb_dir  # noqa: E402

STATUSES = ("In Progress", "Open", "Done", "Dropped")
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
SUMMARY_MAX = 80


def build_header(root: Path) -> str:
    cmd = gen_cmd(root, "gen_tasks_index.py")
    return f"""# Tasks Index

> **本文件是生成物, 不要手改** —— 由 `{cmd}` 扫描 `tasks/*.md` 的 `Status` / `Summary` / 标题生成; 新增或改状态后跑它重建即可, 合并冲突也只需重跑。
> 档案命名 `YY-MM-DD-<slug>.md`(见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md)); 旧编号保留在各档案的 `**Legacy-ID:**` 字段, 供历史文档回溯。
> 粒度为**专题**(一个功能线一个档案, 不逐会话建文件); 历史流水账原文归档在各档案的 `## 历史会话纪要 (原文归档)` 段, 超 24 KB 的档案把该段移入 `tasks/attachments/`(索引守卫按 `tasks/*.md` 扫描, 不递归)。
> 本索引里摘要按 `SUMMARY_MAX` **截断**(全文在档案里): 这样索引大小由**档案数**决定, 不随摘要写得多长而膨胀 —— 否则迟早撞 `index-auto` cap, 而靠"外迁老档案"化解会打坏外部引用。
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
    out = [header]
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
                summary = item["summary"]
                if len(summary) > SUMMARY_MAX:
                    summary = summary[:SUMMARY_MAX].rstrip() + "…"
                line += f" - {summary}"
            out.append(line)
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

    rendered = build(root, mb)
    if args.check:
        current = index.read_text(encoding="utf-8") if index.exists() else ""
        if current != rendered:
            sys.stderr.write(f"{index.name} 与生成结果不一致, 请运行 {gen_cmd(root, 'gen_tasks_index.py')}\n")
            return 1
        return 0

    index.write_text(rendered, encoding="utf-8")
    print(f"已生成 {index.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
