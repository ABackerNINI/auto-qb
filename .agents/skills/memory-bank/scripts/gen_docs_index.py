"""生成 `memory-bank/plans/_index.md` 与 `memory-bank/reports/_index.md`(都是生成物, 不要手改)。

数据源: 两份 HTML 制品 `<head>` 里的 `doc-*` meta (协议见 memory-bank/conventions/doc-forms.md):
    doc-type / doc-topic / doc-status / doc-added / doc-updated / doc-refs

`doc-status` 必须 ∈ 5 词表 (`_common.DOC_STATUSES`) —— 表外值不落任何分区、会被**静默漏收**
(仍打印「已生成 N 个」), 故 `build()` fail-fast (`StatusVocabularyError`); 见
pitfalls/kb/doc-status-meta.md。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_docs_index.py          写回两份 _index.md
    python <skill-dir>/scripts/gen_docs_index.py --check  只比对, 不一致则退出码 1
    python <skill-dir>/scripts/gen_docs_index.py --root <dir> --mb-dir <dir>   # 覆盖探测
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import DOC_STATUSES, StatusVocabularyError, find_root, gen_cmd, resolve_mb_dir  # noqa: E402

KINDS = ("plans", "reports")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.MULTILINE | re.DOTALL)
META_RE = re.compile(r'<meta name="(doc-[a-z]+)" content="([^"]*)">')
STAMP_RE = re.compile(r"^(\d\d-\d\d-\d\d)-(\d{4})-")

EMPTY_HINT = {
    "In Progress": "(暂无)",
    "Open": "(暂无)",
    "Done": "(暂无)",
    "Dropped": "(暂无)",
    "Superseded": "(暂无 —— 被新版取代的计划落这里)",
}

KIND_CN = {"plans": "计划", "reports": "报告"}


def collect(directory: Path) -> list[dict]:
    items = []
    for path in sorted(directory.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        meta = dict(META_RE.findall(text))
        title_match = TITLE_RE.search(text)
        stamp_match = STAMP_RE.match(path.stem)
        stamp = "-".join(p for p in (stamp_match.group(1), stamp_match.group(2)) if p) if stamp_match else ""
        items.append(
            {
                "file": path.name,
                "stamp": stamp,
                "title": (title_match.group(1).strip() if title_match else path.stem),
                "status": meta.get("doc-status", "Open"),
                "topic": meta.get("doc-topic", ""),
                "type": meta.get("doc-type", ""),
            }
        )
    return items


def header(root: Path, kind: str) -> str:
    cmd = gen_cmd(root, "gen_docs_index.py")
    return f"""# {KIND_CN[kind]} Index

> **本文件是生成物, 不要手改** —— 由 `{cmd}` 扫描 `{kind}/*.html` 的 `doc-*` meta 生成;
> 新增制品或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = `[时间戳] 标题 — 专题`(分区即状态); 状态取值: {" / ".join(f"`{s}`" for s in DOC_STATUSES)}。
> 状态写在制品 `<head>` 的 `<meta name="doc-status">` 一行(单处); 协议与决策树见
> [conventions/doc-forms.md](../conventions/doc-forms.md), 跨形态专题视图用 `commands run kb.docmap` 查(不落盘)。
> 机械守卫: `tests/test_docs_forms.py`(索引 == 生成结果 / meta 完整 / 命名合规 / dark 主题)。
"""


def render(items: list[dict], head: str) -> str:
    out = [head]
    for status in DOC_STATUSES:
        group = [i for i in items if i["status"] == status]
        out.append(f"## {status}\n")
        if not group:
            out.append(EMPTY_HINT.get(status, "(暂无)"))
            out.append("")
            continue
        for item in sorted(group, key=lambda i: i["stamp"], reverse=True):
            line = f"- [{item['stamp']}] [{item['title']}]({item['file']})"
            if item["topic"]:
                line += f" — `{item['topic']}`"
            out.append(line)
        out.append("")
    return "\n".join(out)


def _vocab_error(bad: list[str]) -> str:
    return (
        "doc-status 不在 5 词表 —— 索引会**静默漏收**这些件 (仍打印「已生成 N 个生成物」, 零警告; "
        "见 pitfalls/kb/doc-status-meta.md):\n  " + "\n  ".join(bad) + f"\n5 词表: {' / '.join(DOC_STATUSES)}"
        "  (待拍板/待实施=Open · 实施中=In Progress · 报告恒 Done · 被新版取代=Superseded)"
        "\n改 meta 后重跑 `commands run kb.index`, 并确认件已进 <dir>/_index.md"
    )


def build(root: Path, mb: Path) -> dict[str, str]:
    """一步出两份索引全文 (守卫与 --check 共用, 保证两条路径同一实现)。

    遇 `doc-status` 不在 5 词表即 **fail-fast**: 表外值不落任何分区, 会被**静默漏收** ——
    生成器跳过该件、索引 == 生成结果自洽, 于是 `--check` / `kb.check` / `kb.docmap --check`
    全绿, 只有 `test.full` 才红 (见 pitfalls/kb/doc-status-meta.md)。两份制品目录的表外值
    **聚合**后一次性报出。
    """
    rendered: dict[str, str] = {}
    bad: list[str] = []
    for kind in KINDS:
        items = collect(mb / kind)
        bad += [f"{kind}/{i['file']}: doc-status={i['status']!r}" for i in items if i["status"] not in DOC_STATUSES]
        rendered[kind] = render(items, header(root, kind))
    if bad:
        raise StatusVocabularyError(_vocab_error(bad))
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    try:
        rendered = build(root, mb)
    except StatusVocabularyError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    rc = 0
    for kind, text in rendered.items():
        index = mb / kind / "_index.md"
        if args.check:
            current = index.read_text(encoding="utf-8") if index.exists() else ""
            if current != text:
                sys.stderr.write(f"{index.name}({kind}) 与生成结果不一致, "
                                 f"请运行 {gen_cmd(root, 'gen_docs_index.py')}\n")
                rc = 1
            continue
        # newline="\n": 生成物一律 LF —— write_text 默认按 os.linesep 翻换行, Windows 上会写成 CRLF
        # (纯行尾噪音, 见 pitfalls/git/editing-traps.md)。守阵 test_generated_indexes_are_lf_only。
        index.write_text(text, encoding="utf-8", newline="\n")
        print(f"已生成 {index.relative_to(root)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
