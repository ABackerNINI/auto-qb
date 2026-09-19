"""重建 `memory-bank/issues/_index.md`(生成物, 不要手改)。

用法:
    python .agents/skills/create-issue/scripts/gen_issues_index.py           重建
    python .agents/skills/create-issue/scripts/gen_issues_index.py --check   只比对, 不一致退出码 1
    python .agents/skills/scope-guard/scripts/gen_issues_index.py --root D:/tmp/x   指定仓库根(测试用)

数据源是各报告 HTML 的 meta 标签(aqb-issue-status / -stamp / -summary / -title), 与
`scripts/gen_tasks_index.py` 同思路: 索引降级为生成物, 9 个 worktree 并行时冲突的解法是
重跑脚本, 不是人工合并两版文本。索引每行 = 状态 · 日期 · 简述 · 报告链接。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
# .agents/skills/<name>/scripts/x.py → 上四级才是仓库根
DEFAULT_ROOT = Path(__file__).resolve().parents[4]

STATUSES = ("Open", "In Progress", "Fixed", "WontFix", "Duplicate")
EMPTY_HINT = {
    "Open": "(暂无 — 撞见计划外问题时用 new_issue.py 入池)",
}

META_RE = {
    key: re.compile(r'<meta[^>]*name="aqb-issue-%s"[^>]*content="([^"]*)"' % key, re.IGNORECASE)
    for key in ("slug", "stamp", "status", "title", "summary")
}

HEADER = """# Issues Index

> **本文件是生成物, 不要手改** —— 由 `.agents/skills/create-issue/scripts/gen_issues_index.py` 扫描
> `issues/*.html` 的 meta 生成; 新增报告或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = **状态 · 日期 · 简述 · 报告链接**; 状态改在报告 HTML 的封面徽标与 `<meta name="aqb-issue-status">`(两处一起改)。
> 状态取值仅五种: `Open` / `In Progress` / `Fixed` / `WontFix` / `Duplicate`。
> **入池规则**: 计划外问题一律不改码, 只入池 —— 见 [create-issue skill](../../.agents/skills/create-issue/SKILL.md)
> (该不该现在修, 见 [scope-guard skill](../../.agents/skills/scope-guard/SKILL.md))。
"""


def collect(issues_dir: Path) -> list[dict]:
    items = []
    for path in sorted(issues_dir.glob("*.html")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")

        def meta(key: str) -> str:
            m = META_RE[key].search(text)
            return html.unescape(m.group(1)).strip() if m else ""

        items.append(
            {
                "file": path.name,
                "slug": meta("slug") or path.stem,
                "stamp": meta("stamp") or "",
                "status": meta("status") or "Open",
                "title": meta("title") or path.stem,
                "summary": meta("summary"),
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
        for item in sorted(group, key=lambda i: i["stamp"], reverse=True):
            date = item["stamp"][:8] if item["stamp"] else "----"
            line = f"- `{status}` · {date} · [{item['title']}]({item['file']})"
            if item["summary"]:
                line += f" — {item['summary']}"
            out.append(line)
        out.append("")
    return "\n".join(out)


def build(root: Path) -> str:
    return render(collect(root / "memory-bank" / "issues"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="仓库根(默认取 skill 的上三级)")
    args = parser.parse_args(argv)

    issues_dir = args.root / "memory-bank" / "issues"
    index = issues_dir / "_index.md"
    rendered = build(args.root)

    if args.check:
        current = index.read_text(encoding="utf-8") if index.exists() else ""
        if current != rendered:
            sys.stderr.write("_index.md 与生成结果不一致, 请运行 gen_issues_index.py\n")
            return 1
        return 0

    issues_dir.mkdir(parents=True, exist_ok=True)
    index.write_text(rendered, encoding="utf-8")
    print(f"已生成 {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
