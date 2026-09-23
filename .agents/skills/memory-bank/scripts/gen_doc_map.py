"""生成 `memory-bank/_doc-map.md`(生成物, 不要手改) —— 跨形态的**专题视图**。

一行一专题: 列出该专题名下的 issue / 计划 / 报告 / 档案与各自状态 —— 「一件事的全部材料」的唯一入口。
数据源(四份 meta 的映射表就在本文件, 这是唯一一处):
    plans / reports : `<meta name="doc-topic">` + `doc-status` + `doc-added/updated`
    issues          : `<meta name="doc-topic">` + `issue-status`
    tasks           : `**Topics:**` + `**Status:**` (时间戳取文件名日期)

⚠ **不生成任何依赖当前时钟的内容**(如「陈旧 ⚠」) —— 那会让 `--check` 隔天就红(生成物必须可复现);
   需要判新旧时读列出的时间戳, 不靠脚本。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_doc_map.py          写回 _doc-map.md
    python <skill-dir>/scripts/gen_doc_map.py --check  只比对, 不一致则退出码 1
    python <skill-dir>/scripts/gen_doc_map.py --root <dir> --mb-dir <dir>   # 覆盖探测
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, gen_cmd, resolve_mb_dir  # noqa: E402

FORM_ORDER = ("issue", "plan", "report", "task")
FORM_CN = {"issue": "issue", "plan": "计划", "report": "报告", "task": "档案"}
META_RE = re.compile(r'<meta name="([a-z-]+)" content="([^"]*)">')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.MULTILINE | re.DOTALL)
TASK_TITLE_RE = re.compile(r"^#\s+(\S+)\s*[—-]\s*(.+?)\s*$", re.MULTILINE)
TASK_TOPICS_RE = re.compile(r"^\*\*Topics:\*\*\s*(.+)$", re.MULTILINE)
TASK_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(In Progress|Open|Done|Dropped)")
TASK_UPDATED_RE = re.compile(r"\*\*Updated:\*\*\s*(\d{4}-\d{2}-\d{2})")
STAMP_RE = re.compile(r"^(\d\d-\d\d-\d\d)-(\d{4})-")


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


def collect(mb: Path) -> list[dict]:
    items: list[dict] = []
    for kind, form in (("plans", "plan"), ("reports", "report")):
        for path in sorted((mb / kind).glob("*.html")):
            meta = dict(META_RE.findall(path.read_text(encoding="utf-8")))
            title = TITLE_RE.search(path.read_text(encoding="utf-8"))
            items.append({
                "form": form,
                "topic": meta.get("doc-topic", ""),
                "status": meta.get("doc-status", ""),
                "stamp": meta.get("doc-added", "") or _stamp_of(path.name),
                "title": title.group(1).strip() if title else path.stem,
                "link": f"{kind}/{path.name}",
            })
    for path in sorted((mb / "issues").glob("*.html")):
        meta = dict(META_RE.findall(path.read_text(encoding="utf-8")))
        items.append({
            "form": "issue",
            "topic": meta.get("doc-topic", ""),
            "status": meta.get("issue-status", ""),
            "stamp": meta.get("issue-stamp", "") or _stamp_of(path.name),
            "title": meta.get("issue-title", path.stem),
            "link": f"issues/{path.name}",
        })
    for path in sorted((mb / "tasks").glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        topics = TASK_TOPICS_RE.search(text)
        status = TASK_STATUS_RE.search(text)
        updated = TASK_UPDATED_RE.search(text)
        title = TASK_TITLE_RE.search(text)
        items.append({
            "form": "task",
            "topic": topics.group(1).strip() if topics else "",
            "status": status.group(1) if status else "",
            "stamp": _task_stamp(path.name, updated.group(1) if updated else ""),
            "title": title.group(2) if title else path.stem,
            "link": f"tasks/{path.name}",
        })
    return items


def render(items: list[dict], head: str) -> str:
    by_topic: dict[str, list[dict]] = {}
    for item in items:
        by_topic.setdefault(item["topic"] or "(无主键)", []).append(item)
    multi = {t: v for t, v in by_topic.items() if len(v) > 1}
    single = {t: v for t, v in by_topic.items() if len(v) == 1}

    out = [head, f"## 跨形态专题 (≥2 件) —— {len(multi)} 个\n"]
    for topic in sorted(multi, key=lambda t: (-len(multi[t]), t)):
        group = sorted(multi[topic], key=lambda i: FORM_ORDER.index(i["form"]))
        parts = [
            f"{FORM_CN[i['form']]} [{i['stamp']}]({i['link']}) `{i['status']}`" for i in group
        ]
        out.append(f"- **{topic}** ({len(group)}) — " + " · ".join(parts))
    out.append("")
    # 单件专题只列名: 它们没有跨形态材料要对照, 详细行在各自形态的 `_index.md`;
    # 这里保留一行紧凑清单是为了「覆盖 100%」可判定 (每个 topic 都出现在本文件里)。
    out.append(f"## 单件专题 (仅登记, {len(single)} 个)\n")
    names = sorted(single)
    line = " · ".join(names)
    while line:
        cut = line.rfind(" · ", 0, 150)
        cut = cut if cut > 0 else min(len(line), 150)
        out.append(f"- {line[:cut]}")
        line = line[cut:].lstrip(" ·")
    out.append("")
    return "\n".join(out)


def build(root: Path, mb: Path) -> str:
    cmd = gen_cmd(root, "gen_doc_map.py")
    head = f"""# 文档形态总览 (按专题)

> **本文件是生成物, 不要手改** —— 由 `{cmd}` 扫描四形态 (plans / reports / issues / tasks) 的
> `doc-topic` / `**Topics:**` 与各自状态生成; 新增制品或改状态后重跑即可, 合并冲突也只需重跑。
> **一行一专题**: 该专题名下的 issue / 计划 / 报告 / 档案与各自状态 —— 「一件事的全部材料」的唯一入口。
> 协议与决策树见 [conventions/doc-forms.md](conventions/doc-forms.md); 各形态索引见
> [plans/_index.md](plans/_index.md) · [reports/_index.md](reports/_index.md) ·
> [issues/_index.md](issues/_index.md) · [tasks/_index.md](tasks/_index.md)。
"""
    return render(collect(mb), head)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    target = mb / "_doc-map.md"

    rendered = build(root, mb)
    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != rendered:
            sys.stderr.write(f"{target.name} 与生成结果不一致, 请运行 {gen_cmd(root, 'gen_doc_map.py')}\n")
            return 1
        return 0

    target.write_text(rendered, encoding="utf-8")
    print(f"已生成 {target.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())