"""会话滚动状态切片阅读器 —— 扫 `memory-bank/activeContext/` 的时间戳切片, 按「最后活动」倒序输出一行摘要。

名字沿用 `gen_*` 前缀是与 `gen_tasks_index.py` / `gen_kb_index.py` 对齐, 但**本脚本不写任何文件**。

数据源 (手写的只有切片文件):
    <mb>/activeContext/YY-MM-DD-HHMM-<slug>.md
        # <标题>
        > 摘要: 一句话说清这个会话在做什么
        > 最后活动: YYYY-MM-DD HH:MM      ← 排序键; 缺失则回退文件名时间戳 (= 创建时间)

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_active_recent.py                   全量倒序输出一行摘要
    python <skill-dir>/scripts/gen_active_recent.py --check           只校验 (闸门 / 守卫用)
    python <skill-dir>/scripts/gen_active_recent.py --stale-days 14   改陈旧阈值

四条设计约束 (2026-09-23 定, 想加回某条前先重读这段):

1. **不写任何文件** —— 没有 `_recent.md`。缓存会过期: 一个看着可读、实际是上次运行快照的文件,
   比「没跑脚本」更危险 (后者一眼看得出)。时间戳文件名自带时间与主题, `ls` 本身就是索引。
2. **不做「取最近 N 条」截断** —— 条数不是稳定的时间尺度 (活跃期一天十条会把半天挤出去,
   安静期三条可能跨一个月), 而且截断会漏掉「创建早但仍在推进」的切片。
   改为**全量倒序 + 陈旧标记**, 目录规模靠归档阈值控制, 不靠 N。
3. **文件名不带 clone 标记** —— 同分钟同名 add/add 概率极低, 撞了改个 slug 重来即可。
   「我上次做到哪」靠 **slug 复用** (同一专题跨会话沿用同一个 slug) 检索 —— 这给出的是
   专题维度的时间线, 比 clone 维度分区信息价值更高。
4. **activeContext 不含长青职能** —— 定案口径 / 下一步候选 / 待走查 / 历史归档各自有真实归属
   (根 AGENTS.md · conventions/ · pitfalls/ · 想法.md + progress/roadmap.md · checklists/ · tasks/),
   本目录只承载会话滚动状态。所以这里没有 global.md, 也不需要全局索引。
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    LAST_ACTIVE_RE,
    SLICE_DIR,
    SLICE_FILE_RE,
    SUMMARY_RE,
    TITLE_RE,
    cap_of,
    find_root,
    gen_cmd,
    resolve_mb_dir,
)

DEFAULT_STALE_DAYS = 14

# 文件名前缀 `YY-MM-DD-HHMM` → 创建时间
_CREATED_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})-(\d{2})(\d{2})")

# 文件内「最后活动」字段的值 `YYYY-MM-DD HH:MM`
_ACTIVE_FMT = "%Y-%m-%d %H:%M"


def _utf8_stdout() -> None:
    """Windows 控制台可能是 GBK, 打中文/符号会崩 —— CLI 入口统一 UTF-8 兜底。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_created(name: str) -> datetime | None:
    """文件名前缀 → 创建时间; 不合命名约定返回 None。"""
    m = _CREATED_RE.match(name)
    if not m:
        return None
    yy, mm, dd, hh, mi = (int(x) for x in m.groups())
    try:
        return datetime(2000 + yy, mm, dd, hh, mi)
    except ValueError:
        return None


def parse_last_active(text: str) -> datetime | None:
    """文件内 `> 最后活动:` 字段 → 时间; 缺失返回 None (调用方回退创建时间)。"""
    m = LAST_ACTIVE_RE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1).strip(), _ACTIVE_FMT)
    except ValueError:
        return None


def collect(slice_dir: Path, root: Path) -> tuple[list[dict], list[str]]:
    """扫切片目录 → (按最后活动倒序的行, 问题清单)。"""
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
            problems.append(f"{rel}: {len(text)} 字符 > 切片 cap {cap} (超了就该归档, 不是继续往上堆)")

        last = parse_last_active(text) or created
        slug = path.name[len(_CREATED_RE.match(path.name).group(0)) + 1:-len(".md")]
        rows.append(
            {
                "rel": rel,
                "slug": slug,
                "created": created,
                "last": last,
                "summary": summary.group(1) if summary else "",
            }
        )

    rows.sort(key=lambda r: r["last"], reverse=True)
    return rows, problems


def _pad(text: str, width: int) -> str:
    """按终端**显示宽度**补空格 —— CJK 占两列, 直接用 ljust 会让表头歪掉。"""
    shown = sum(2 if ord(c) > 0x2E80 else 1 for c in text)
    return text + " " * max(0, width - shown)


def render(rows: list[dict], stale_days: int, now: datetime) -> str:
    # 不截断 slug —— 截断会丢信息, 且 slug 长度本来就有界
    width = max((len(r["slug"]) for r in rows), default=10)
    lines = [_pad("创建", 17) + _pad("最后活动", 17) + _pad("切片 slug", width + 2) + "摘要", ""]
    for r in rows:
        stale = (now - r["last"]).days
        mark = f"  [陈旧 {stale} 天 → 待归档]" if stale > stale_days else ""
        lines.append(
            _pad(f"{r['created']:%y-%m-%d %H:%M}", 17) + _pad(f"{r['last']:%y-%m-%d %H:%M}", 17) +
            _pad(r["slug"], width + 2) + r["summary"] + mark
        )
    stale_n = sum(1 for r in rows if (now - r["last"]).days > stale_days)
    lines.append("")
    lines.append(f"共 {len(rows)} 个切片 · {stale_n} 个待归档 (阈值 {stale_days} 天未动)")
    lines.append("长青焦点不在这里 —— 「下一步」看 想法.md + progress/roadmap.md, 定案口径看根 AGENTS.md / conventions/ / pitfalls/")
    return "\n".join(lines)


def main() -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只校验, 不打印摘要 (闸门与守卫用)")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS, help=f"陈旧阈值, 默认 {DEFAULT_STALE_DAYS} 天")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    slice_dir = mb / SLICE_DIR

    if not slice_dir.is_dir():
        # 尚未目录化 —— 不是错误, 别堵住闸门
        sys.stderr.write(f"尚无 {slice_dir.name}/ 目录 (仍是单文件 activeContext.md), 本脚本在 W1 目录化后生效\n")
        return 0

    rows, problems = collect(slice_dir, root)

    if args.check:
        for p in problems:
            sys.stderr.write(f"{p}\n")
        if problems:
            sys.stderr.write(f"请修正后重跑 {gen_cmd(root, 'gen_active_recent.py')}\n")
            return 1
        return 0

    print(render(rows, args.stale_days, datetime.now()))
    for p in problems:
        sys.stderr.write(f"[warn] {p}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
