"""重建 issues 索引 `_index.md`(生成物, 不要手改)。

用法:
    python <skill>/scripts/gen_issues_index.py                      重建
    python <skill>/scripts/gen_issues_index.py --check              只比对, 不一致退出码 1
    python <skill>/scripts/gen_issues_index.py --root D:/tmp/x --dir issues   指定仓库根与 issues 目录

数据源是各报告 HTML 的 meta 标签(issue-status / -stamp / -summary / -title / -type), 与
`scripts/gen_tasks_index.py` 同思路: 索引降级为生成物, 多个 worktree 并行时冲突的解法是
重跑脚本, 不是人工合并两版文本。

索引按状态分区, 每行 = **类型 · 简述 · 报告链接**; 顶部另有 Open 状态的按类型计数表。
文件名必须是 `<YY-MM-DD-HHMM>-<type>-<slug>.html` 且 type 在枚举内 —— 不合规直接报错退出
(护栏建在生成器里, 不靠自觉)。

与项目无关: 目录用 `--dir`(不传则探测), 仓库根靠 `.git` 向上探测, HEADER 的 skill 链接动态计算。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    FILE_RE,
    STATUSES,
    TYPES,
    dir_of,
    find_root,
    rel_skill,
    resolve_issues_dir,
)

META_RE = {
    key: re.compile(r'<meta[^>]*name="issue-%s"[^>]*content="([^"]*)"' % key, re.IGNORECASE)
    for key in ("slug", "stamp", "type", "status", "title", "summary")
}

EMPTY_HINT = {
    "Open": "(暂无 — 撞见计划外问题时用 new_issue.py 入池)",
}


def header(issues_dir: Path, root: Path) -> str:
    skill_rel = rel_skill(issues_dir)
    script_rel = f"{skill_rel}/scripts/gen_issues_index.py" if skill_rel else "gen_issues_index.py"
    skill_link = f"({skill_rel}/SKILL.md)" if skill_rel else ""
    dir_name = dir_of(issues_dir, root)
    return f"""# Issues Index

> **本文件是生成物, 不要手改** —— 由 `{script_rel}` 扫描 `{dir_name}/*.html` 的 meta
> (`issue-status` / `issue-stamp` / `issue-title` / `issue-summary` / `issue-type`)生成;
> 新增报告或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = **类型 · 简述 · 报告链接**(分区即状态); 状态改在报告 HTML 的封面徽标与
> `<meta name="issue-status">`(两处一起改)。状态取值: {" / ".join(f"`{s}`" for s in STATUSES)}。
> 文件名 = `<YY-MM-DD-HHMM>-<type>-<slug>.html`, type 取值: {" / ".join(TYPES)}。
> **入池规则**: 计划外问题一律不改码, 只入池 —— 见 create-issue skill {skill_link}
> (该不该现在修, 见 scope-guard skill)。
"""


def collect(issues_dir: Path) -> list[dict]:
    """扫描目录; 文件名缺 type 或 type 不在枚举 → 抛 ValueError(由 main 转成退出码 2)。"""
    items = []
    for path in sorted(issues_dir.glob("*.html")):
        if path.name.startswith("_"):
            continue
        matched = FILE_RE.match(path.stem)
        if not matched:
            raise ValueError(f"{path.name}: 文件名应为 <YY-MM-DD-HHMM>-<type>-<slug>.html")
        file_type = matched.group("type")
        if file_type not in TYPES:
            raise ValueError(f"{path.name}: type `{file_type}` 不在枚举内 ({' / '.join(TYPES)})")

        text = path.read_text(encoding="utf-8")

        def meta(key: str) -> str:
            m = META_RE[key].search(text)
            return html.unescape(m.group(1)).strip() if m else ""

        status = meta("status") or "Open"
        if status not in STATUSES:
            raise ValueError(f"{path.name}: status `{status}` 不在枚举内 ({' / '.join(STATUSES)})")
        items.append(
            {
                "file": path.name,
                "slug": meta("slug") or path.stem,
                "stamp": meta("stamp") or "",
                "type": meta("type") or file_type,
                "status": status,
                "title": meta("title") or path.stem,
                "summary": meta("summary"),
            }
        )
    return items


def count_table(items: list[dict]) -> list[str]:
    """Open 状态的按类型计数(没有 Open 就不出表, 免得空表占位)。"""
    opened = [i for i in items if i["status"] == "Open"]
    if not opened:
        return []
    counts = {t: sum(1 for i in opened if i["type"] == t) for t in TYPES}
    rows = [f"| {t} | {n} |" for t, n in counts.items() if n]
    if not rows:
        return []
    return ["", "## 待处理分布（Open）", "", "| 类型 | 条数 |", "|---|---|", *rows, ""]


def render(items: list[dict], issues_dir: Path, root: Path) -> str:
    out = [header(issues_dir, root)]
    out.extend(count_table(items))
    for status in STATUSES:
        group = [i for i in items if i["status"] == status]
        out.append(f"## {status}\n")
        if not group:
            out.append(EMPTY_HINT.get(status, "(暂无)"))
            out.append("")
            continue
        for item in sorted(group, key=lambda i: i["stamp"], reverse=True):
            line = f"- [{item['type']}] [{item['title']}]({item['file']})"
            if item["summary"]:
                line += f" — {item['summary']}"
            out.append(line)
        out.append("")
    return "\n".join(out)


def build(root: Path, issues_dir: Path) -> str:
    return render(collect(issues_dir), issues_dir, root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件")
    parser.add_argument("--dir", default=None,
                        help="issues 目录(相对仓库根); 不传则按 memory-bank/issues → issues → docs/issues 探测")
    parser.add_argument("--root", type=Path, default=None, help="仓库根(默认向上探测 .git)")
    args = parser.parse_args(argv)

    root = (args.root or find_root()).resolve()
    issues_dir = resolve_issues_dir(root, args.dir)
    index = issues_dir / "_index.md"

    try:
        rendered = build(root, issues_dir)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

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
