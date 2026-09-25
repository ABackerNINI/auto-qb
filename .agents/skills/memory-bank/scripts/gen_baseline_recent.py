"""测试基线切片阅读器 —— 扫 `memory-bank/testing/baselines/` 的时间戳切片, 按「基线时间」倒序输出, 默认最近 3 条。

名字沿用 `gen_*` 前缀是与 `gen_active_recent.py` 等对齐, 但**本脚本不写任何文件**。

数据源 (手写的只有切片文件):
    <mb>/testing/baselines/YY-MM-DD-HHMM-<slug>.md
        # <数字> —— <事件>
        > 摘要: 一句话说清这轮基线为什么变/不变
        > 基线时间: YYYY-MM-DD HH:MM   ← 排序键; 缺失则回退文件名时间戳
        > 档案: <task-slug>            ← 选填

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_baseline_recent.py                 列最近 3 条 (默认窗口)
    python <skill-dir>/scripts/gen_baseline_recent.py -n 5 / --all    改条数 / 全量排障
    python <skill-dir>/scripts/gen_baseline_recent.py --check         只校验 (闸门 / 守卫用)

四条设计约束 (2026-09-26 定, 与 gen_active_recent.py 同构; 想改前先重读这段):

1. **不写任何文件, 不设 `_index.md`** —— 时间戳文件名自带时间与主题, `ls` 本身就是索引;
   缓存式的索引文件比没有更危险。**也不许补 `_index.md`** (口径见 testing/baseline.md)。
2. **默认截取最近 3 条** —— 这与 activeRecent 的「不做截断」**故意相反**: 会话切片是活的专题
   (创建早但仍在推进, 截断会漏); 基线切片是**不可变的一次性快照**, 写完不改, 最新一条恒为
   事实源 ⇒ 截断语义成立 (用户定案 2026-09-26: ①每文件一条基线 ②脚本列最近 3 条 ③无 _index)。
   `--all` / `-n N` 供排障回看。
3. **文件名不带 clone 标记** —— 同分钟同名 add/add 概率极低, 撞了改个 slug 重来即可。
4. **排序键是切片头「基线时间」字段, 文件名前缀只是回退与人类检索** —— 存量回填时两者可能
   分叉 (文件名沿计划定案、字段取考据值), 字段为主键、文件名为次级稳定键。
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    SLICE_FILE_RE, SUMMARY_RE, TITLE_RE, cap_of, find_root, gen_cmd, resolve_mb_dir,
)

DEFAULT_RECENT = 3

# 切片目录 (相对 memory-bank/) —— 无 _about.md ⇒ gen_kb_index 自发现不纳入, 无 _index 是特性
BASELINE_DIR = Path("testing") / "baselines"

# 文件名前缀 `YY-MM-DD-HHMM` → 记录时间 (回退用)
_CREATED_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})-(\d{2})(\d{2})")

# 文件内「基线时间」字段的值 `YYYY-MM-DD HH:MM`
_BASELINE_FMT = "%Y-%m-%d %H:%M"

# 文件内「基线时间」字段 —— 排序键; 缺失则回退文件名时间戳
BASELINE_TIME_RE = re.compile(r"^>\s*基线时间:\s*(\S.*?)\s*$", re.MULTILINE)


def _utf8_stdout() -> None:
    """Windows 控制台可能是 GBK, 打中文/符号会崩 —— CLI 入口统一 UTF-8 兜底。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_created(name: str) -> datetime | None:
    """文件名前缀 → 记录时间; 不合命名约定返回 None。"""
    m = _CREATED_RE.match(name)
    if not m:
        return None
    yy, mm, dd, hh, mi = (int(x) for x in m.groups())
    try:
        return datetime(2000 + yy, mm, dd, hh, mi)
    except ValueError:
        return None


def parse_baseline_time(text: str) -> datetime | None:
    """文件内 `> 基线时间:` 字段 → 时间; 缺失返回 None (调用方回退文件名前缀)。"""
    m = BASELINE_TIME_RE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1).strip(), _BASELINE_FMT)
    except ValueError:
        return None


def collect(slice_dir: Path, root: Path) -> tuple[list[dict], list[str]]:
    """扫切片目录 → (按基线时间倒序的行, 问题清单)。排序 = 基线时间为主键、文件名为次级稳定键。"""
    rows: list[dict] = []
    problems: list[str] = []

    for path in sorted(slice_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        rel = path.relative_to(root).as_posix()

        if not SLICE_FILE_RE.match(path.name):
            problems.append(f"{rel}: 文件名不合 `YY-MM-DD-HHMM-<slug>.md` 约定 (定宽前缀保证字典序 == 时间序)")
            continue

        text = path.read_bytes().decode("utf-8")
        created = parse_created(path.name)
        if created is None:  # 正则已保证可解析, 这里只挡 2026-02-31 这类非法日期
            problems.append(f"{rel}: 文件名里的日期不是合法日期")
            continue

        title = TITLE_RE.search(text)
        summary = SUMMARY_RE.search(text)
        if not title:
            problems.append(f"{rel}: 缺三行头元数据中的 `# 标题`")
        if not summary:
            problems.append(f"{rel}: 缺三行头元数据中的 `> 摘要:`")

        cap = cap_of(rel)
        if len(text) > cap:
            problems.append(f"{rel}: {len(text)} 字符 > 切片 cap {cap} (明细下沉对应任务档案, 不是调 cap)")

        when = parse_baseline_time(text) or created
        prefix_len = len(_CREATED_RE.match(path.name).group(0))
        slug = path.name[prefix_len + 1:-len(".md")]
        rows.append(
            {
                "rel": rel,
                "slug": slug,
                "created": created,
                "when": when,
                "summary": summary.group(1) if summary else "",
            }
        )

    rows.sort(key=lambda r: (r["when"], r["rel"]), reverse=True)
    return rows, problems


def render(rows: list[dict], limit: int | None) -> str:
    shown = rows if limit is None else rows[:limit]
    width = max((len(r["slug"]) for r in shown), default=10)
    lines = [_pad("基线时间", 17) + _pad("切片 slug", width + 2) + "摘要", ""]
    for r in shown:
        lines.append(_pad(f"{r['when']:%y-%m-%d %H:%M}", 17) + _pad(r["slug"], width + 2) + r["summary"])
    lines.append("")
    if limit is not None and len(rows) > len(shown):
        lines.append(f"共 {len(rows)} 条基线 · 显示最近 {len(shown)} 条 (--all / -n N 看更旧)")
    else:
        lines.append(f"共 {len(rows)} 条基线")
    lines.append("记录新基线: 新建切片文件, 命名与体例见 testing/baseline.md 口径段; 数字不许手抄到别处")
    return "\n".join(lines)


def _pad(text: str, width: int) -> str:
    """按终端**显示宽度**补空格 —— CJK 占两列, 直接用 ljust 会让表头歪掉。"""
    shown = sum(2 if ord(c) > 0x2E80 else 1 for c in text)
    return text + " " * max(0, width - shown)


def main() -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只校验, 不打印摘要 (闸门与守卫用)")
    parser.add_argument("-n", type=int, default=DEFAULT_RECENT, help=f"列最近 N 条, 默认 {DEFAULT_RECENT}")
    parser.add_argument("--all", action="store_true", help="全量输出 (排障回看, 不截断)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    slice_dir = mb / BASELINE_DIR

    if not slice_dir.is_dir():
        # 尚未目录化 —— 不是错误, 别堵住闸门 (首条基线切片落地后自动生效)
        sys.stderr.write(f"尚无 {BASELINE_DIR.as_posix()}/ 目录, 本脚本在基线切片化后生效\n")
        return 0

    rows, problems = collect(slice_dir, root)

    if args.check:
        for p in problems:
            sys.stderr.write(f"{p}\n")
        if problems:
            sys.stderr.write(f"请修正后重跑 {gen_cmd(root, 'gen_baseline_recent.py')}\n")
            return 1
        return 0

    print(render(rows, None if args.all else max(1, args.n)))
    for p in problems:
        sys.stderr.write(f"[warn] {p}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
