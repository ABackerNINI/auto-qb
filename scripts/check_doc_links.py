#!/usr/bin/env python3
"""相对链接存在性扫描 —— 改名 / 搬家后坏链不会让任何测试失败, 只能靠机检。

背景: 知识库目录化重构(W1–W7)一次新增/改写了 **400+ 处**相对链接。KB 里"改文件名后必须查全仓引用"
这条坑记了很久, 但一直只靠人工扫 —— 本脚本把它变成一条可自动跑的判据。

用法:
    python scripts/check_doc_links.py            # 扫 memory-bank/ 与根级 md; 有坏链则退出码 1
    python scripts/check_doc_links.py --all      # 再扫 docs/ 与根 README
    python scripts/check_doc_links.py --quiet

判据:
- 只查**相对**链接(跳过 `http(s)://` / `mailto:` / 纯锚点 `#x`)。
- 目标存在即通过; 不存在则报"坏链"。
- 允许"锚点"后缀(`path.md#sec`)—— 只校验 `path.md` 是否存在。
- **历史留档例外**: `memory-bank/plans/*.html` 与 `memory-bank/issues/*.html` 不扫(它们冻结在成文那天,
  按存根策略本就允许指向旧路径)。
- 默认扫 `memory-bank/` 与 `.github/`(后者是规则载体, 也有链接); `--all` 再加 `docs/` 与根级 md。
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# markdown 链接: [文本](目标)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# 行内代码: 文档里讲"链接怎么写"时会写出 `](target)` 这类字面量, 不当链接看
CODE_RE = re.compile(r"`[^`\n]*`")
# 跳过: 绝对 URL / 邮件 / 纯锚点
SKIP_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#)")

SCAN_DIRS = ("memory-bank", ".github")
EXTRA_DIRS = ("docs", )


def is_frozen(path: pathlib.Path) -> bool:
    """历史留档: 按存根策略允许指向旧路径, 不扫。"""
    parts = path.parts
    return ("plans" in parts and path.suffix == ".html") or ("issues" in parts and path.suffix == ".html")


def scan_file(path: pathlib.Path, root: pathlib.Path) -> list[tuple[str, int, str]]:
    """返回 [(文件, 行号, 目标)] 的坏链清单。"""
    broken: list[tuple[str, int, str]] = []
    text = path.read_bytes().decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        for target in LINK_RE.findall(CODE_RE.sub("", line)):
            if SKIP_RE.match(target):
                continue
            rel = target.split("#", 1)[0]
            if not rel:
                continue
            if not (path.parent / rel).exists():
                broken.append((str(path.relative_to(root)), lineno, target))
    return broken


def collect_files(root: pathlib.Path, all_dirs: bool = False) -> list[pathlib.Path]:
    """要扫的文件清单(供 CLI 与 pytest 守卫共用, 保证两条路径同一实现)。"""
    dirs = list(SCAN_DIRS) + (list(EXTRA_DIRS) if all_dirs else [])
    files: list[pathlib.Path] = []
    for d in dirs:
        base = root / d
        if base.is_dir():
            files.extend(p for p in sorted(base.rglob("*.md")) if not is_frozen(p))
    if all_dirs:
        files.extend(p for p in sorted(root.glob("*.md")))
        files.extend(p for p in sorted((root / "docs").rglob("*.md")) if not is_frozen(p))
    return files


def scan_all(root: pathlib.Path, all_dirs: bool = False) -> list[tuple[str, int, str]]:
    """全量坏链清单: [(相对路径, 行号, 目标)]。守卫直接调它, **不起子进程**。"""
    broken: list[tuple[str, int, str]] = []
    for path in collect_files(root, all_dirs):
        broken.extend(scan_file(path, root))
    return broken


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO_ROOT), help="仓库根")
    ap.add_argument("--all", action="store_true", help="连 docs/ 与根级 md 一起扫")
    ap.add_argument("--quiet", action="store_true", help="只打印坏链")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    files = collect_files(root, args.all)
    broken = scan_all(root, args.all)

    if not args.quiet:
        print(f"相对链接扫描: {len(files)} 个文件, {len(broken)} 处坏链")
    for rel, lineno, target in broken:
        print(f"  [坏链] {rel}:{lineno}  → {target}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
