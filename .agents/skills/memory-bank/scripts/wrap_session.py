#!/usr/bin/env python3
"""`kb.wrap` —— 收尾的机械面 (计划 memory-bank/plans/26-10-17-0527 P1, D6)。

**只做机械面** (切片 / 档案 / 索引 / 清单); 蒸馏与判断仍是 agent 的活:
- 切片: 不存在则按模板建(**判断剩余 0** —— 模板的可选骨架段在建件时剥掉, 只留三行头 + R0 行;
  `--did` 即合法摘要, 裁定 A6), 存在则抬「最后活动」+ 追加一条带日期的 R 行 (编号 = 现有最大 + 1)
- 档案: `**Topics:**` 同专题的 tasks/ 档案 → 抬 `**Updated:**` + 进度日志追加一行带日期条目
  (日期属派生面, 裁定 A5 —— 轮内不逐行写日期, 收尾统一带)
- 索引: 动了档案就重建 `tasks/_index.md` (与 `kb.index` 同一 build 实现)
- 清单: 末尾输出剩余收尾清单 (基线? 新坑? 债务转告?) —— 收尾知识内嵌, 不必重读 DoD

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/wrap_session.py --topic <slug> --did "一句话说清本轮做了什么"
    python <skill-dir>/scripts/wrap_session.py --root <dir> --mb-dir <dir> --topic .. --did ..
退出码: 0 成功 / 1 参数或校验失败 (原因与下一步打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import timekit  # noqa: E402  (时间单点: UTC+8 naive 墙钟, 与 kb.time 同源)
from _common import (  # noqa: E402
    SKILL_DIR, SLICE_FILE_RE, find_root, rel_posix, resolve_mb_dir,
)

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOPICS_LINE_RE = re.compile(r"^\*\*Topics:\*\*\s*(.+)$", re.MULTILINE)
UPDATED_LINE_RE = re.compile(r"^\*\*Updated:\*\*\s*.*$", re.MULTILINE)
R_ENTRY_RE = re.compile(r"^\*\*R(\d+)\(", re.MULTILINE)
SLICE_R0_RE = re.compile(r"^\*\*R0\(.*\):\*\*.*$", re.MULTILINE)


def _fail(msg: str) -> int:
    sys.stderr.write(f"[STOP] {msg}\n")
    return 1


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _find_slices(slice_dir: Path, slug: str) -> list[Path]:
    """同 slug 的切片 (文件名 `<stamp>-<slug>.md`; endswith 精确匹配, 不误伤更长 slug)。"""
    return sorted(p for p in slice_dir.glob(f"*-{slug}.md") if SLICE_FILE_RE.match(p.name))


def _create_slice(slug: str, did: str, moment, slice_dir: Path) -> Path:
    """按模板建最小切片: 三行头 + R0 行, **零 SLOT** (可选骨架段剥掉 —— 判断剩余 0, 裁定 A6)。"""
    rendered = (SKILL_DIR / "templates" / "slice.md").read_text(encoding="utf-8")
    rendered = rendered.replace("@@SLUG@@", slug).replace("@@DID@@",
                                                          did).replace("@@TIME@@", moment.strftime("%Y-%m-%d %H:%M"))
    lines = rendered.split("\n")
    keep: list[str] = []
    for line in lines:
        keep.append(line)
        if SLICE_R0_RE.match(line):
            break
    text = "\n".join(keep).rstrip("\n") + "\n"
    path = slice_dir / f"{moment.strftime('%y-%m-%d-%H%M')}-{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _touch_slice(path: Path, did: str, moment) -> int:
    """存在切片: 抬「最后活动」+ 追加 R 行 (编号 = 现有最大 + 1)。返回新编号。"""
    text = path.read_text(encoding="utf-8")
    numbers = [int(n) for n in R_ENTRY_RE.findall(text)]
    next_no = max(numbers) + 1 if numbers else 1
    stamp = moment.strftime("%Y-%m-%d %H:%M")
    new_last_active = f"> 最后活动: {stamp}"
    text = re.sub(r"^>\s*最后活动:\s*\S.*$", new_last_active, text, count=1, flags=re.MULTILINE)
    if not re.search(r"^>\s*最后活动:", text, re.MULTILINE):
        text = re.sub(r"^(> 摘要:.*)$", rf"\1\n{new_last_active}", text, count=1, flags=re.MULTILINE)
    entry = f"\n**R{next_no}({stamp}):** {did}\n"
    path.write_text(text.rstrip("\n") + "\n" + entry, encoding="utf-8", newline="\n")
    return next_no


def _touch_archive(path: Path, did: str, moment) -> bool:
    """同专题档案: 抬 `**Updated:**` + 进度日志追加一行带日期条目。返回是否改了 Updated 行。"""
    text = path.read_text(encoding="utf-8")
    stamp = moment.strftime("%Y-%m-%d %H:%M")
    date = moment.strftime("%Y-%m-%d")
    changed = False
    if UPDATED_LINE_RE.search(text):
        text = UPDATED_LINE_RE.sub(f"**Updated:** {date}", text, count=1)
        changed = True
    entry = f"\n- {stamp} {did}\n"
    path.write_text(text.rstrip("\n") + "\n" + entry, encoding="utf-8", newline="\n")
    return changed


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="专题 slug (切片文件名后缀 / 档案 **Topics:** 主键)")
    parser.add_argument("--did", required=True, help="一句话: 本轮做了什么 (切片摘要预填 + R 行, 裁定 A5/A6)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    if not SLUG_RE.match(args.topic):
        return _fail(f"--topic 必须是 kebab (小写英文数字 + 短横线): {args.topic!r}")

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    moment = timekit.now()

    # --- 切片 (不存在则按模板建; 存在则抬最后活动 + 追加 R 行)
    slice_dir = mb / "activeContext"
    existing = _find_slices(slice_dir, args.topic)
    if existing:
        if len(existing) > 1:
            print(f"[提示] 同 slug 切片 {len(existing)} 份, 取最新: {existing[-1].name}")
        next_no = _touch_slice(existing[-1], args.did, moment)
        print(f"已更新切片 {rel_posix(existing[-1], root)} (最后活动 + R{next_no} 行)")
    else:
        created = _create_slice(args.topic, args.did, moment, slice_dir)
        print(f"已建切片 {rel_posix(created, root)} (三行头 + R0, 零 SLOT; 可选骨架段需要时再补)")

    # --- 同专题档案 (**Topics:** 匹配)
    touched: list[Path] = []
    tasks_dir = mb / "tasks"
    if tasks_dir.is_dir():
        for path in sorted(tasks_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            text = path.read_text(encoding="utf-8")
            m = TOPICS_LINE_RE.search(text)
            if m and m.group(1).strip() == args.topic:
                changed = _touch_archive(path, args.did, moment)
                note = "Updated + 进度日志" if changed else "进度日志 (无 Updated 行, 未抬)"
                print(f"已更新档案 {rel_posix(path, root)} ({note})")
                touched.append(path)
    if not touched:
        print(
            f"[提示] 未找到同专题档案 (**Topics:** == {args.topic}) —— 跳过; "
            f"如需立档: commands run kb.new task --title \"..\" --topic <领域>-{args.topic}"
        )

    # --- 索引 (动了档案才需要重建; 切片无索引)
    if touched:
        import gen_tasks_index  # noqa: PLC0415

        index = mb / "tasks" / "_index.md"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(gen_tasks_index.build(root, mb), encoding="utf-8", newline="\n")
        print(f"已重建索引: {rel_posix(index, root)}")

    print()
    print("剩余人工 1 项(判断 0 · 条件 1 · 机械 0)")
    print("【条件】涉码轮 → commands run test.full, 数字誊写新基线切片 (裁定 A4); "
          "踩到新坑 → 写 pitfalls/<类>/<主题>.md; cap 债务转告用户另开会话清理")
    print("【可选】切片摘要/档案 Summary 精编 (复杂会话, 不计步)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
