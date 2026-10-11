#!/usr/bin/env python3
"""相对链接存在性扫描 —— 改名 / 搬家后坏链不会让任何测试失败, 只能靠机检。

背景: 知识库目录化重构(W1–W7)一次新增/改写了 **400+ 处**相对链接。KB 里"改文件名后必须查全仓引用"
这条坑记了很久, 但一直只靠人工扫 —— 本脚本把它变成一条可自动跑的判据。

**随 memory-bank skill 走**(2026-10-06 从根 `scripts/` 迁入): 根探测改用 `_common.find_root()`,
不假定安装深度, 整目录拷走即可移植。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/check_doc_links.py            # 扫 memory-bank/ 与根级 md; 有坏链则退出码 1
    python <skill-dir>/scripts/check_doc_links.py --all      # 再扫 docs/ 与根 README
    python <skill-dir>/scripts/check_doc_links.py --quiet

判据:
- 只查**相对**链接(跳过 `http(s)://` / `mailto:` / 纯锚点 `#x`)。
- 目标存在即通过; 不存在则报"坏链"。
- ❗**存在性按 Linux 口径判**(组件级 `listdir` 精确比对, 见 `link_exists`), **不用 `Path.exists()`**:
  Win32 会静默剥掉结尾的点/空格且大小写不敏感 ⇒ `kb/...` 被判成"存在"(实际塌成父目录 `kb/`)、
  `Cap.md` 能命中 `cap.md` —— 坏链在**本机恒绿**, 只在 Linux CI 红。2026-10-11 一条真坏链
  连过三道本机防线(doc.links 闸门 / test.quick 闸门 / 手工 test.full), 根因就是这个:
  详见 `memory-bank/pitfalls/testing/patching.md`「路径归一化」条。
- 允许"锚点"后缀(`path.md#sec`)—— 只校验 `path.md` 是否存在。
- **历史留档例外**: `memory-bank/plans/*.html` · `memory-bank/reports/*.html` 与 `memory-bank/issues/*.html` 不扫(它们冻结在成文那天,
  按存根策略本就允许指向旧路径)。
- 默认扫 `memory-bank/` 与 `.github/`(后者是规则载体, 也有链接); `--all` 再加 `docs/` 与根级 md。
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _common import find_root  # noqa: E402

# markdown 链接: [文本](目标)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# 行内代码: 文档里讲"链接怎么写"时会写出 `](target)` 这类字面量, 不当链接看
CODE_RE = re.compile(r"`[^`\n]*`")
# 跳过: 绝对 URL / 邮件 / 纯锚点
SKIP_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#)")

SCAN_DIRS = ("memory-bank", ".github")
EXTRA_DIRS = ("docs", )


def is_frozen(path: pathlib.Path) -> bool:
    """历史留档: 按存根策略允许指向旧路径, 不扫 (`plans/` 与 `reports/` 的 HTML 制品 + issue 报告)。"""
    parts = path.parts
    return path.suffix == ".html" and ("plans" in parts or "reports" in parts or "issues" in parts)


def _entries(directory: pathlib.Path, cache: dict[str, frozenset[str]]) -> frozenset[str]:
    """目录里的条目名(**保留原始大小写**); 取不到(不存在 / 无权限)记空集。"""
    key = str(directory)
    if key not in cache:
        try:
            cache[key] = frozenset(os.listdir(directory))
        except OSError:
            cache[key] = frozenset()
    return cache[key]


def _is_literal_name(name: str) -> bool:
    """该组件名能否在 Windows 上"按字面"存在 —— 结尾的点 / 空格会被 Win32 静默剥掉。"""
    return name.rstrip(". ") == name


def link_exists(base: pathlib.Path, rel: str, cache: dict[str, frozenset[str]]) -> bool:
    """相对目标是否存在 —— **组件级精确比对**, 即 Linux / CI 的口径。

    ❗别退回 `(base / rel).exists()`: 实测 Windows 上 `(kb / "...").exists()` 为 `True`
    (Win32 把结尾的点剥掉, 路径塌成 `kb/`), 而 `os.listdir(kb)` 里根本没有 `...` ——
    同一行判据在两套文件系统语义下答案相反, 坏链于是**本机恒绿、只在 Linux CI 红**。
    同族还有大小写不敏感(本机 `cap-counting.MD` 也判存在)。
    另外**探针自己也别用 `resolve()` / `abspath()`** —— 它们同样走 Win32 归一, 会把 `...` 吃掉
    (2026-10-11 写核对脚本时先被骗过一次, 报假绿)。
    """
    cur = base
    for comp in rel.replace("\\", "/").split("/"):
        if comp in ("", "."):
            continue
        if comp == "..":
            cur = cur.parent
            continue
        if not _is_literal_name(comp):
            return False  # Windows 存不出这种名字 ⇒ 该链接在 CI(Linux)上必坏
        if comp not in _entries(cur, cache):
            return False
        cur = cur / comp
    return True


def scan_file(path: pathlib.Path, root: pathlib.Path) -> list[tuple[str, int, str]]:
    """返回 [(文件, 行号, 目标)] 的坏链清单。"""
    broken: list[tuple[str, int, str]] = []
    cache: dict[str, frozenset[str]] = {}
    text = path.read_bytes().decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        for target in LINK_RE.findall(CODE_RE.sub("", line)):
            if SKIP_RE.match(target):
                continue
            rel = target.split("#", 1)[0]
            if not rel:
                continue
            if not link_exists(path.parent, rel, cache):
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
    ap.add_argument("--root", help="仓库根 (默认向上找 .git)")
    ap.add_argument("--all", action="store_true", help="连 docs/ 与根级 md 一起扫")
    ap.add_argument("--quiet", action="store_true", help="只打印坏链")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve() if args.root else find_root()
    files = collect_files(root, args.all)
    broken = scan_all(root, args.all)

    if not args.quiet:
        print(f"相对链接扫描: {len(files)} 个文件, {len(broken)} 处坏链")
    for rel, lineno, target in broken:
        print(f"  [坏链] {rel}:{lineno}  → {target}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
