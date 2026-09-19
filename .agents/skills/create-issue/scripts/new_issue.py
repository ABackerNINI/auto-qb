"""新建一条计划外问题报告, 并重建 `memory-bank/issues/_index.md`。

用法:
    python .agents/skills/create-issue/scripts/new_issue.py <slug> --title "中文标题" --summary "一句话简述"
        [--module webui] [--status Open] [--reporter "worktree 名/agent"] [--root <仓库根>]

产出: `memory-bank/issues/<YY-MM-DD-HHMM>-<slug>.html`(时间由脚本取系统当前时间, 不靠记忆),
然后自动重建索引并打印路径。文件已存在则报错退出(不覆盖)。
脚本只填封面与 meta; 正文段落(TODO)由 agent 接着填成"别人能直接开工"的程度。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "assets" / "issue-template.html"
# .agents/skills/<name>/scripts/x.py → 上四级才是仓库根
DEFAULT_ROOT = Path(__file__).resolve().parents[4]
STATUSES = ("Open", "In Progress", "Fixed", "WontFix", "Duplicate")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def stamp(dt: datetime | None = None) -> str:
    return (dt or datetime.now()).strftime("%y-%m-%d-%H%M")


def long_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def render_template(slug: str, title: str, summary: str, module: str, status: str, reporter: str,
                    now: datetime) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    pairs = {
        "{{SLUG}}": slug,
        "{{STAMP}}": stamp(now),
        "{{DATE}}": long_date(now),
        "{{TITLE}}": title,
        "{{SUMMARY}}": summary,
        "{{MODULE}}": module,
        "{{STATUS}}": status,
        "{{REPORTER}}": reporter,
    }
    # 统一转义(quote=True): meta 的 content 不会被引号截断, 正文里 &quot; 浏览器同样渲染成 "
    for key, value in pairs.items():
        text = text.replace(key, html.escape(value, quote=True))
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="英文短横线, <领域>-<专题>, 例: webui-cols-drift")
    parser.add_argument("--title", required=True, help="中文标题(进 <title> 与 H1)")
    parser.add_argument("--summary", required=True, help="一句话简述(进 _index.md)")
    parser.add_argument("--module", default="未分类", help="涉及模块/领域")
    parser.add_argument("--status", default="Open", choices=STATUSES)
    parser.add_argument("--reporter", default="未署名", help="发现者(worktree / agent / 会话)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="仓库根(默认取 skill 的上三级)")
    parser.add_argument("--at", default=None, help="仅测试用: 指定时间 'YY-MM-DD-HHMM'")
    args = parser.parse_args(argv)

    if not SLUG_RE.match(args.slug):
        sys.stderr.write(f"slug 不合规: {args.slug} (要求小写英文短横线, 例 webui-cols-drift)\n")
        return 2

    now = datetime.strptime(args.at, "%y-%m-%d-%H%M") if args.at else datetime.now()
    issues_dir = args.root / "memory-bank" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    path = issues_dir / f"{stamp(now)}-{args.slug}.html"
    if path.exists():
        sys.stderr.write(f"已存在, 不覆盖: {path}\n")
        return 3

    path.write_text(
        render_template(args.slug, args.title, args.summary, args.module, args.status, args.reporter, now),
        encoding="utf-8")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gen_issues_index import main as gen_main  # noqa: E402

    gen_main(["--root", str(args.root)])
    print(f"报告: {path}")
    print(f"索引: {issues_dir / '_index.md'}")
    print("下一步: 填正文 TODO(现象/证据/影响面/根因/建议修法/涉及文件), 然后回到主线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
