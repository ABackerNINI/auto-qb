#!/usr/bin/env python3
"""`kb.ref` —— 认领链回填一条命令 (issue 26-10-31-2226-feat-kb-docrefs-bidirectional-automation)。

把「issue/档案 认领回填」从两次手工编辑(声明方 doc-refs + 被指方反向声明)收成一条命令,
并把两类复发形态拦死在写入之前:

- **另插一行 meta** (复发 8, 2026-10-30): 模板自带空值 doc-refs meta, 手工「加一行」会让
  空值赢过新插行。本命令走 `html_set_refs`/`md_set_refs` 单点 —— 原位改值, 绝不另插一行;
  声明方**已有重复声明行**时 fail-fast 拒写(先修声明方, 报错指向 gen_doc_map --check)。
- **先回填后落盘** (复发 6, 2026-10-15): issue 先声明、认领方件后建, 窗口期任何全量跑都是红。
  本命令 **fail-fast**: 每个 --add 目标必须已存在且在 memory-bank 内, 否则整笔拒绝、零写入。

收敛口径同样机器化 (复发 5): `plans/` 与 `reports/` **不作 --add 目标**(冻结制品不进认领链,
只在正文提及) —— 引用面收到「对方也能写反向声明」的件 (tasks / activeContext / pitfalls /
testing/baselines / progress / issues)。反向声明自动补: 目标件没有声明则原位补一行
(HTML meta 插在 doc-updated 后 / md 按锚点链), 幂等。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/set_doc_refs.py <path> --add <ref>[,<ref>...]
    python <skill-dir>/scripts/set_doc_refs.py <path> --add <ref> --no-reverse   # 只声明, 不补反向
    python <skill-dir>/scripts/set_doc_refs.py --root <dir> --mb-dir <dir> <path> --add <ref>
- <path>: 声明方 (HTML: doc-refs meta / md: **Refs:** 行; 三种路径形态都认)
- <ref>: 仓库根相对路径, 多目标英文逗号; 目标存在性/收敛口径 fail-fast
退出码: 0 成功(幂等重跑无改动也 0) / 1 拒绝或校验失败 (原因与下一步打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    html_set_refs,
    md_set_refs,
    rel_posix,
    resolve_doc_path,
    resolve_mb_dir,
    find_root,
    split_refs,
)

MD_REFS_LINE_RE = re.compile(r"^\*\*Refs:\*\*", re.MULTILINE)
HTML_DOCREFS_ANCHOR = '<meta name="doc-refs"'
# 收敛口径 (复发 5): 冻结制品不作 --add 目标, 只在正文提及
FROZEN_REF_DIRS = ("plans", "reports")


def _fail(msg: str) -> int:
    sys.stderr.write(f"[STOP] {msg}\n")
    return 1


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _is_html(path: Path) -> bool:
    return path.suffix.lower() == ".html"


def _dup_declarations(path: Path, text: str) -> int:
    """声明方/目标件的重复声明行数 (复发 8 形态; 有即拒写, 先修声明方)。"""
    if _is_html(path):
        return text.count(HTML_DOCREFS_ANCHOR)
    return len(MD_REFS_LINE_RE.findall(text))


def _set_refs(text: str, target_rel: str, is_html: bool) -> str:
    return html_set_refs(text, target_rel) if is_html else md_set_refs(text, target_rel)


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="声明方文档路径 (绝对 / 仓库根相对 / memory-bank 相对, 三种都认)")
    parser.add_argument("--add", required=True, help="仓库根相对路径 (多目标英文逗号); 目标必须已存在且在 memory-bank 内")
    parser.add_argument("--no-reverse", action="store_true", help="只写声明方, 不自动补目标反向声明 (默认双向补链)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    path = resolve_doc_path(args.path, root, mb)
    if not path.is_file():
        return _fail(f"声明方不存在: {rel_posix(path, root)} —— 路径三形态 (绝对/仓库根相对/mb 相对) 都不命中")
    if not path.resolve().is_relative_to(mb.resolve()):
        return _fail(f"声明方必须在 memory-bank 内: {rel_posix(path, root)}")
    if path.name.startswith("_"):
        return _fail(f"生成物 `_` 前缀文件不作认领链载体: {rel_posix(path, root)}")

    refs = split_refs(args.add)
    if not refs:
        return _fail("--add 为空 —— 多目标英文逗号分隔; 要清空声明请直接编辑该文件")

    # --- fail-fast 全量预检, 零写入直到全部通过 (拦「先回填后落盘」悬空窗口: 复发 6)
    problems: list[str] = []
    targets: list[Path] = []
    for ref in refs:
        target = root / ref
        seg = ref.split("/")
        in_frozen = len(seg) >= 2 and seg[1] in FROZEN_REF_DIRS
        if in_frozen:
            problems.append(f"{ref}: plans/ 与 reports/ 不进认领链 (复发 5 收敛法: 冻结制品只在正文提及)")
        elif not target.is_file():
            problems.append(f"{ref}: 目标不存在 —— 认领方件必须先落盘再回填 (复发 6); 建件走 kb.new/kb.wrap")
        elif not target.resolve().is_relative_to(mb.resolve()):
            problems.append(f"{ref}: 目标不在 memory-bank 内")
        elif target.name.startswith("_"):
            problems.append(f"{ref}: 生成物 `_` 前缀文件不作认领链目标")
        elif target.resolve() == path.resolve():
            problems.append(f"{ref}: 自我引用")
        else:
            targets.append(target)
    self_text = path.read_text(encoding="utf-8")
    self_dups = _dup_declarations(path, self_text)
    if self_dups > 1:
        problems.append(
            f"声明方已有 {self_dups} 行声明 ({rel_posix(path, root)}) —— 解析器只读第一条, "
            "空值/旧值会赢过新插行 (复发 8); 先原位改值/删多余行, 再重跑本命令"
        )
    for target in targets:
        t_dups = _dup_declarations(target, target.read_text(encoding="utf-8"))
        if t_dups > 1:
            problems.append(f"目标已有 {t_dups} 行声明 ({rel_posix(target, root)}) —— 先修目标再回填 (复发 8 形态)")
    if problems:
        for p in problems:
            sys.stderr.write(f"[STOP] {p}\n")
        return 1

    # --- 双向补链: 声明方原位并值 + 目标反向声明 (只动元数据行, 幂等)
    self_rel = rel_posix(path, root)
    changed: list[str] = []
    text = self_text
    for target in targets:
        new_text = _set_refs(text, rel_posix(target, root), _is_html(path))
        if new_text != text:
            changed.append(f"声明 {self_rel} += {rel_posix(target, root)}")
        text = new_text
    if not args.no_reverse:
        for target in targets:
            t_text = target.read_text(encoding="utf-8")
            new_t_text = _set_refs(t_text, self_rel, _is_html(target))
            if new_t_text != t_text:
                changed.append(f"反向 {rel_posix(target, root)} += {self_rel}")
                target.write_text(new_t_text, encoding="utf-8", newline="\n")
    if text != self_text:
        path.write_text(text, encoding="utf-8", newline="\n")

    if changed:
        for line in changed:
            print(f"已补链 {line}")
    else:
        print("声明已全部在册 —— 幂等, 无改动")
    print("剩余人工 0 项(判断 0 · 条件 0 · 机械 0)")
    print("NEXT: 若涉及索引可见面变化跑 commands run kb.index; 闸门自证: commands run kb.docmap -- --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
