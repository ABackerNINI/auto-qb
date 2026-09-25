"""新建一条计划外问题报告(按类型选档位模板), 并重建 issues 索引。

用法:
    python <skill>/scripts/new_issue.py <slug> --type docs \
        --title "中文标题" --summary "一句话简述" [--module webui] [--topic 专题] [--tier light] \
        [--status Open] [--reporter "worktree 名/agent"] [--dir memory-bank/issues] \
        [--project 项目名] [--root <仓库根>] [--at 'YY-MM-DD-HHMM']

产出: `<issues dir>/<YY-MM-DD-HHMM>-<type>-<slug>.html`(时间由脚本取系统当前时间, 不靠记忆),
然后自动重建索引并打印路径。文件已存在则报错退出(不覆盖)。

脚本只填封面与 meta; 正文 TODO 由 agent 按档位补齐 —— 便签档(light)三段、标准档(standard)
五段, 根因与建议修法一律可选(见 SKILL.md「防过期原则」)。

与项目无关: 类型枚举在 `_common.TYPES`, issues 目录用 `--dir`(不传则探测), 仓库根靠 `.git`
向上探测(不传 `--root` 也能用), 模板里的项目名只在传 `--project` 时出现。
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    SLUG_RE,
    STATUSES,
    TIER_BY_TYPE,
    TIER_TEMPLATE,
    TIERS,
    TYPES,
    dir_of,
    find_root,
    long_date,
    resolve_issues_dir,
    stamp,
)

SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS = SKILL_DIR / "assets"

NEXT_STEP = {
    "light": "下一步: 填「现象一句话 / 位置(grep 锚点)」, 建议可留待定 —— 预算 ≤ 2 分钟, 然后回到主线。",
    "standard": "下一步: 填「现象 / 证据 / 影响面 / 定位锚点」; 根因与建议修法默认待查 —— 预算 ≤ 10 分钟, 然后回到主线。",
}


def render_template(
    tier: str, slug: str, title: str, summary: str, module: str, status: str, reporter: str, type_: str, project: str,
    topic: str, now: datetime
) -> str:
    text = (ASSETS / TIER_TEMPLATE[tier]).read_text(encoding="utf-8")
    pairs = {
        "{{SLUG}}": slug,
        "{{STAMP}}": stamp(now),
        "{{DATE}}": long_date(now),
        "{{TITLE}}": title,
        "{{SUMMARY}}": summary,
        "{{MODULE}}": module,
        "{{STATUS}}": status,
        "{{REPORTER}}": reporter,
        "{{TYPE}}": type_,
        "{{TIER}}": tier,
        # doc-topic 是**跨形态串联主键**(doc-forms 约定): 多条 issue 可共用一个专题
        # (如 webui-optimistic-ui 下挂 3 条), 所以允许独立于 slug 指定; 不传则退化为 slug
        # (一题一专题)。**不得省略** —— 缺它该 issue 会从 _doc-map 的专题视图里静默漏掉
        # (守卫 tests/test_docs_forms.py::test_issue_topics_present 会判红)。
        "{{TOPIC}}": topic,
        # 不传 --project 时为空串: 模板里不出现任何项目名(可移植性)
        "{{PROJECT}}": f"{project} · " if project else "",
    }
    # 统一转义(quote=True): meta 的 content 不会被引号截断, 正文里 &quot; 浏览器同样渲染成 "
    for key, value in pairs.items():
        text = text.replace(key, html.escape(value, quote=True))
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="小写英文短横线, 建议 <领域>-<专题>, 例: webui-cols-drift")
    parser.add_argument("--type", required=True, choices=TYPES, help="问题类型(进文件名第二段与 meta)")
    parser.add_argument("--title", required=True, help="中文标题(进 <title> 与 H1)")
    parser.add_argument("--summary", required=True, help="一句话简述(进索引)")
    parser.add_argument("--module", default="未分类", help="涉及模块/领域")
    parser.add_argument("--topic", default=None, help="doc-topic 跨形态串联主键(默认 = slug); 多条 issue 共用一专题时显式指定")
    parser.add_argument("--tier", choices=TIERS, default=None, help="档位(默认由 --type 推导)")
    parser.add_argument("--status", default="Open", choices=STATUSES)
    parser.add_argument("--reporter", default="未署名", help="发现者(worktree / agent / 会话)")
    parser.add_argument(
        "--dir", default=None, help="issues 目录(相对仓库根); 不传则按 memory-bank/issues → issues → docs/issues 探测"
    )
    parser.add_argument("--project", default="", help="项目名(进封面 kicker); 不传则不出现项目名")
    parser.add_argument("--root", type=Path, default=None, help="仓库根(默认向上探测 .git)")
    parser.add_argument("--at", default=None, help="仅测试用: 指定时间 'YY-MM-DD-HHMM'")
    args = parser.parse_args(argv)

    if not SLUG_RE.match(args.slug):
        sys.stderr.write(f"slug 不合规: {args.slug} (要求小写英文短横线, 例 webui-cols-drift)\n")
        return 2

    tier = args.tier or TIER_BY_TYPE[args.type]
    now = datetime.strptime(args.at, "%y-%m-%d-%H%M") if args.at else datetime.now()
    root = (args.root or find_root()).resolve()
    issues_dir = resolve_issues_dir(root, args.dir)
    dir_arg = args.dir
    if dir_arg is None and not issues_dir.is_dir():
        sys.stderr.write("未找到 issues 目录(试过 memory-bank/issues / issues / docs/issues), "
                         "请用 --dir 显式指定\n")
        return 4

    issues_dir.mkdir(parents=True, exist_ok=True)
    path = issues_dir / f"{stamp(now)}-{args.type}-{args.slug}.html"
    if path.exists():
        sys.stderr.write(f"已存在, 不覆盖: {path}\n")
        return 3

    path.write_text(
        render_template(
            tier, args.slug, args.title, args.summary, args.module, args.status, args.reporter, args.type, args.project,
            args.topic or args.slug, now
        ),
        encoding="utf-8"
    )

    from gen_issues_index import main as gen_main  # noqa: E402

    gen_main(["--root", str(root), "--dir", dir_arg or dir_of(issues_dir, root)])
    print(f"报告: {path}")
    print(f"索引: {issues_dir / '_index.md'}")
    print(NEXT_STEP[tier])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
