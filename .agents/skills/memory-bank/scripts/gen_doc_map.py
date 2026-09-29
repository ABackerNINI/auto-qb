"""跨形态专题视图查询 CLI (只打印, 不写文件) —— 「一件事的全部材料」入口。

一行一专题: 列出该专题名下的 issue / 计划 / 报告 / 档案与各自状态。
2026-09-29 起 `_doc-map.md` 物化视图退役 (写热点 + `index-auto` cap 反复触顶, 复盘见
pitfalls/kb/cap-counting.md「生成式跨形态视图」条的收口注记), 改为查询时现算 —— 命名沿用
`gen_*` 前缀与 gen_active_recent.py / gen_baseline_recent.py 对齐, 但**本脚本不写任何文件**。

数据源 (单点在 collect()):
    plans / reports : `<meta name="doc-topic">` + `doc-status` + `doc-added`
    issues          : `<meta name="doc-topic">` + `issue-status`
    tasks           : `**Topics:**` + `**Status:**` (时间戳取文件名日期)

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_doc_map.py                   默认: 活跃多件专题全行, 完结/单件专题只列名
    python <skill-dir>/scripts/gen_doc_map.py --topic <key>     单专题全行 (出件前先查主键是否已有)
    python <skill-dir>/scripts/gen_doc_map.py --all             全量全行 (等价退役的物化视图, 审计用)
    python <skill-dir>/scripts/gen_doc_map.py --check           主键纪律: 任一形态缺主键即退码 1 (挂 kb.check)
    python <skill-dir>/scripts/gen_doc_map.py --forks           近似主键提示 (子串包含), 只提示不判红

轮转口径 (「生成器内轮转完结专题」): 状态 ∈ TERMINAL_STATUSES 为完结。默认视图只给**活跃多件
专题**全行; 全完结专题退成名录, 单件专题永远只列名 (无跨形态材料可对照, 详见各形态 `_index.md`)
—— 视图大小跟着**活工作**走, 不跟历史总量走。未知 / 缺失状态一律按**活跃**算 (宁多展示不漏活口)。
⚠ 不生成任何依赖当前时钟的内容; 判新旧读条目自带的时间戳, 不靠脚本。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, resolve_mb_dir  # noqa: E402

FORM_ORDER = ("issue", "plan", "report", "task")
FORM_CN = {"issue": "issue", "plan": "计划", "report": "报告", "task": "档案"}
TERMINAL_STATUSES = frozenset({"Done", "Dropped", "Superseded"})
NO_KEY = "(无主键)"
META_RE = re.compile(r'<meta name="([a-z-]+)" content="([^"]*)">')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.MULTILINE | re.DOTALL)
TASK_TITLE_RE = re.compile(r"^#\s+(\S+)\s*[—-]\s*(.+?)\s*$", re.MULTILINE)
TASK_TOPICS_RE = re.compile(r"^\*\*Topics:\*\*\s*(.+)$", re.MULTILINE)
TASK_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(In Progress|Open|Done|Dropped)")
TASK_UPDATED_RE = re.compile(r"\*\*Updated:\*\*\s*(\d{4}-\d{2}-\d{2})")
STAMP_RE = re.compile(r"^(\d\d-\d\d-\d\d)-(\d{4})-")
NAME_WRAP = 4000  # 名录折行宽度, 只影响换行 —— 零信息损失 (150→400→4000 三轮收口, 见 git 历史)


def _utf8_stdout() -> None:
    """Windows 控制台可能是 GBK, 打中文/符号会崩 —— CLI 入口统一 UTF-8 兜底。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _stamp_of(name: str) -> str:
    m = STAMP_RE.match(name)
    return f"{m.group(1)}-{m.group(2)}" if m else name


def _task_stamp(name: str, updated: str) -> str:
    """档案时间戳: 文件名日期段优先 (带时分则全取), 否则用 `**Updated:**`, 最后退回空。"""
    m = STAMP_RE.match(name)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    d = re.match(r"^(\d\d-\d\d-\d\d)-", name)
    return d.group(1) if d else updated


def _date_stamp(stamp: str) -> str:
    """展示戳截到日期精度 (2026-09-28 口径, 见 pitfalls/kb/cap-counting.md「两个出口」处置①):
    与任务档案行本就一致; 时分仍留在链接指向的文件名里, 零信息损失。
    只在确为 `NN-NN-NN-NNNN` 形态时截断, 异常格式原样保留。"""
    return stamp[:8] if re.fullmatch(r"\d{2}-\d{2}-\d{2}-\d{4}", stamp or "") else stamp


def collect(mb: Path) -> list[dict]:
    items: list[dict] = []
    for kind, form in (("plans", "plan"), ("reports", "report")):
        for path in sorted((mb / kind).glob("*.html")):
            text = path.read_text(encoding="utf-8")
            meta = dict(META_RE.findall(text))
            title = TITLE_RE.search(text)
            items.append(
                {
                    "form": form,
                    "topic": meta.get("doc-topic", ""),
                    "status": meta.get("doc-status", ""),
                    "stamp": _date_stamp(meta.get("doc-added", "")) or _stamp_of(path.name),
                    "title": title.group(1).strip() if title else path.stem,
                    "link": f"{kind}/{path.name}",
                }
            )
    for path in sorted((mb / "issues").glob("*.html")):
        meta = dict(META_RE.findall(path.read_text(encoding="utf-8")))
        items.append(
            {
                "form": "issue",
                "topic": meta.get("doc-topic", ""),
                "status": meta.get("issue-status", ""),
                "stamp": meta.get("issue-stamp", "") or _stamp_of(path.name),
                "title": meta.get("issue-title", path.stem),
                "link": f"issues/{path.name}",
            }
        )
    for path in sorted((mb / "tasks").glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        topics = TASK_TOPICS_RE.search(text)
        status = TASK_STATUS_RE.search(text)
        updated = TASK_UPDATED_RE.search(text)
        title = TASK_TITLE_RE.search(text)
        items.append(
            {
                "form": "task",
                "topic": topics.group(1).strip() if topics else "",
                "status": status.group(1) if status else "",
                "stamp": _task_stamp(path.name,
                                     updated.group(1) if updated else ""),
                "title": title.group(2) if title else path.stem,
                "link": f"tasks/{path.name}",
            }
        )
    return items


def group_by_topic(items: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["topic"] or NO_KEY, []).append(item)
    return groups


def is_live(group: list[dict]) -> bool:
    """专题是否活跃: 有任一条目未完结 (未知 / 缺失状态按活跃算, 宁可多展示)。"""
    return any(i["status"] not in TERMINAL_STATUSES for i in group)


def _segments(group: list[dict]) -> str:
    group = sorted(group, key=lambda i: FORM_ORDER.index(i["form"]))
    return " ".join(f"{FORM_CN[i['form']]} [{i['stamp']}]({i['link']}) {i['status']}".rstrip() for i in group)


def _topic_sort(groups: dict[str, list[dict]]) -> list[str]:
    return sorted(groups, key=lambda t: (-len(groups[t]), t))


def _name_list(names: list[str]) -> list[str]:
    out = []
    line = " ".join(names)
    while line:
        cut = line.rfind(" ", 0, NAME_WRAP)
        cut = cut if cut > 0 else min(len(line), NAME_WRAP)
        out.append(f"- {line[:cut]}")
        line = line[cut:].lstrip(" ·")
    return out


def render_live(items: list[dict]) -> str:
    """默认视图: **活跃多件专题全行** + 已完结多件专题与单件专题只列名 (轮转)。

    只列名的口径沿旧物化版: 单件专题没有跨形态材料可对照, 详细行在各自形态的 `_index.md`;
    全完结专题退成名录 —— 默认输出大小跟着**活工作**走, 不跟历史总量走。
    """
    groups = group_by_topic(items)
    live_multi = {t: g for t, g in groups.items() if len(g) > 1 and is_live(g)}
    done_multi = sorted(t for t, g in groups.items() if len(g) > 1 and not is_live(g))
    single = sorted(t for t, g in groups.items() if len(g) == 1)
    out = [
        "# 跨形态专题视图 (查询时现算)",
        "",
        "> `kb.docmap` [--topic <key> | --all | --check | --forks]; 完结 (Done/Dropped/Superseded) 与单件专题只列名,",
        "> 全行见 --topic / --all; 协议见 [doc-forms.md](conventions/doc-forms.md)。",
        "",
        f"## 活跃专题 ({len(live_multi)})",
        "",
    ]
    out += [f"- **{t}** — {_segments(g)}" for t, g in sorted(live_multi.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    for title, names in ((f"已完结专题 ({len(done_multi)})", done_multi), (f"单件专题 ({len(single)})", single)):
        out += ["", f"## {title}"]
        if names:
            out += [""] + _name_list(names)
    return "\n".join(out) + "\n"


def render_all(items: list[dict]) -> str:
    """全量视图: 等价退役的 `_doc-map.md` 渲染 (多件专题全行 + 单件专题名录)。"""
    groups = group_by_topic(items)
    multi = {t: g for t, g in groups.items() if len(g) > 1}
    single = sorted(t for t, g in groups.items() if len(g) == 1)
    out = [
        "# 文档形态总览 (按专题, 全量)",
        "",
        "> `kb.docmap --all` —— 等价退役的 `_doc-map.md`; 协议见 [doc-forms.md](conventions/doc-forms.md)。",
        "",
        f"## 跨形态专题 (≥2 件) · {len(multi)}",
        "",
    ]
    out += [f"- **{t}** — {_segments(g)}" for t, g in sorted(multi.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    out += ["", f"## 单件专题 ({len(single)})"]
    if single:
        out += [""] + _name_list(single)
    return "\n".join(out) + "\n"


def render_topic(items: list[dict], key: str) -> int:
    groups = group_by_topic(items)
    if key not in groups:
        sys.stderr.write(f"无此专题: {key}\n现有专题 ({len(groups)} 个, 按件数降序):\n")
        for t in _topic_sort(groups):
            sys.stderr.write(f"  {t} ({len(groups[t])})\n")
        return 1
    group = groups[key]
    print(f"{key} ({len(group)} 件, {'活跃' if is_live(group) else '已完结'})")
    print(f"  {_segments(group)}")
    return 0


def check_topics(items: list[dict]) -> int:
    """主键纪律: 缺 `doc-topic` / `**Topics:**` 的文档会从专题视图里静默漏掉 —— 列出即退码 1。"""
    orphans = [i for i in items if not i["topic"]]
    if orphans:
        sys.stderr.write("下列文档缺跨形态主键 (doc-topic / **Topics:**), 会从专题视图里静默漏掉:\n")
        for i in orphans:
            sys.stderr.write(f"  {i['form']}: {i['link']}\n")
        sys.stderr.write("补 meta / **Topics:** 行后重跑本命令\n")
        return 1
    groups = group_by_topic(items)
    print(f"主键纪律 OK: {len(items)} 份文档 / {len(groups)} 个专题, 无缺主键")
    return 0


def find_forks(groups: dict[str, list[dict]]) -> list[str]:
    """近似主键 (子串包含, 如 webui-hr-popup 与 -t1/t2/t3): 疑似分叉, 只提示不判红。"""
    names = [t for t in groups if t != NO_KEY]
    return sorted(f"{a} ⊂ {b} (疑似分叉: 短键并入长键或改名)" for a in names for b in names if a != b and a in b)


def main() -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="只看一个专题的全行 (未知键退码 1 并列出现有键)")
    parser.add_argument("--all", action="store_true", help="全量全行 (等价退役的 _doc-map.md)")
    parser.add_argument("--check", action="store_true", help="主键纪律: 缺 doc-topic/Topics 即退码 1 (闸门/守卫用)")
    parser.add_argument("--forks", action="store_true", help="近似主键提示 (stderr), 只提示不判红")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    items = collect(mb)

    if args.forks:
        found = find_forks(group_by_topic(items))
        for f in found:
            sys.stderr.write(f"[fork] {f}\n")
        if not found:
            sys.stderr.write("[fork] 无近似主键\n")

    if args.check:
        return check_topics(items)
    if args.topic:
        return render_topic(items, args.topic)
    if args.all:
        print(render_all(items))
        return 0
    print(render_live(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
