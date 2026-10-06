#!/usr/bin/env python3
"""时间单点 (UTC+8 钉死) + 知识库日期守卫 —— memory-bank 的一切日期只有一个来源。

背景: `conventions/doc-forms.md` 与 `webui.md` 早写着「时间戳用命令取当前值」, 但那条命令
从来不存在 —— 日期实际全是 agent 按会话上下文手敲的, 未来时间与错体例由此而来。本脚本把
「取时」落成一条真命令 (`commands run kb.time`), 并把「值」变成可机检的判据。

时区实现: `datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)` ——
**naive UTC+8 墙钟**: 与全库现有 naive 解析 (`gen_active_recent` 等) 一致, 不引入 aware/naive
混算; 与机器本地时区无关 (TZ 无关性由测试钉住)。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/timekit.py           三行全打 (date / time / stamp)
    python <skill-dir>/scripts/timekit.py date      YYYY-MM-DD (Added / Updated / 正文日期)
    python <skill-dir>/scripts/timekit.py time      YYYY-MM-DD HH:MM (最后活动 / 正文时刻)
    python <skill-dir>/scripts/timekit.py stamp     YY-MM-DD-HHMM (文件名前缀)
    python <skill-dir>/scripts/timekit.py check     日期守卫, 有违规退出码 1
    python <skill-dir>/scripts/timekit.py --safety  冒烟探针 (回答「无参跑我是否即真动作」)

守卫三层 (严宽有别, 见计划 plans/26-09-30-0931):
    文件名   tasks 的 `YY-MM-DD` / 切片与 HTML 制品的 `YY-MM-DD-HHMM` —— 合法日期 + 不晚于当前
    元数据   Added / Updated / 最后活动 / doc-added / doc-updated —— 合法 + 非未来;
             「最后活动」必须严格 `YYYY-MM-DD HH:MM`
    正文     全部 .md / .html 的日期 token —— 非规范变体 (斜杠 / 不补零 / 中文 / 紧凑 8 位 /
             ISO-T) 判违规; 规范 token **不查未来** (正文可合法引用未来日程)
豁免: md 跳过围栏代码块与行内代码; html 跳过 code/pre/script/style 与 URL 串;
      行内 `<!-- time:allow -->` 标记豁免整行 (机器数据样例用)。
**过去日期的错值兜不住** (无真值可比), 靠流程 (只从本脚本取) 规避。
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, rel_posix, resolve_mb_dir  # noqa: E402

# --------------------------------------------------------------------------- 时间单点

# UTC+8 固定偏移。**不读机器时区** —— 换个时区的机器跑, 输出必须仍是 +08 墙钟。
TZ_OFFSET = timedelta(hours=8)


def now() -> datetime:
    """当前 UTC+8 **naive** 墙钟 (无 tzinfo)。全库一切日期都从它派生。"""
    return datetime.now(timezone(TZ_OFFSET)).replace(tzinfo=None)


DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%Y-%m-%d %H:%M"
STAMP_FMT = "%y-%m-%d-%H%M"

# --------------------------------------------------------------------------- 守卫: 常量

ALLOW_MARK = "<!-- time:allow -->"

# 文件名前缀: tasks 用 `YY-MM-DD-`, 切片与 HTML 制品用 `YY-MM-DD-HHMM-`
TASK_PREFIX_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})-")
STAMP_PREFIX_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})-(\d{2})(\d{2})-")

# 元数据字段
META_FIELD_RE = re.compile(r"^\*\*(Added|Updated):\*\*\s*(\S.*?)\s*$", re.MULTILINE)
LAST_ACTIVE_LINE_RE = re.compile(r"^>\s*最后活动:\s*(\S.*?)\s*$", re.MULTILINE)
LAST_ACTIVE_STRICT_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$")

# HTML meta: <meta name="doc-added" content="YY-MM-DD-HHMM">
META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
NAME_ATTR_RE = re.compile(r'\bname="([^"]*)"', re.IGNORECASE)
CONTENT_ATTR_RE = re.compile(r'\bcontent="([^"]*)"', re.IGNORECASE)
DOC_META_FIELDS = ("doc-added", "doc-updated")
DOC_META_VALUE_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})-(\d{2})(\d{2})$")

# 正文非规范变体 (规范 token = `YYYY-MM-DD` 与 `YYYY-MM-DD HH:MM`, 不在此列)
BODY_BAD_PATTERNS = (
    # 紧凑 8 位: 边界排除路径/标识符里的数字 (`audit-20260921/`、`git-backup-20260922-2343`
    # 这类不是日期 token, 是目录名) —— 只在真正独立出现时才判违规。
    (
        "紧凑 8 位日期",
        re.compile(r"(?<![0-9A-Za-z_\-/.])(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?![0-9A-Za-z_\-/.])"),
        "改用 `YYYY-MM-DD`"
    ),
    ("ISO-T 分隔", re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"), "改用 `YYYY-MM-DD HH:MM`"),
    ("斜杠日期", re.compile(r"(?<!\d)\d{4}/\d{1,2}/\d{1,2}(?!\d)"), "改用 `YYYY-MM-DD`"),
    ("中文日期", re.compile(r"(?<!\d)\d{4}年\d{1,2}月\d{1,2}日"), "改用 `YYYY-MM-DD`"),
)
# 不补零: `YYYY-M-D` / `YYYY-MM-D` 等 (至少一段为 1 位); `…` 负向排除挡住索引摘要截断
NON_PADDED_RE = re.compile(r"(?<!\d)\d{4}-(\d{1,2})-(\d{1,2})(?![\d…])")

URL_RE = re.compile(r"https?://\S+")
MD_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HTML_BLOCK_TAGS = ("code", "pre", "script", "style")

# 需要做文件名日期校验的目录 → 前缀形态
TASK_DIR = "tasks"
STAMP_DIRS = ("activeContext", "testing/baselines", "plans", "reports", "issues")

# --------------------------------------------------------------------------- 解析工具


def parse_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_stamp(yy: int, mm: int, dd: int, hh: int, mi: int) -> datetime | None:
    try:
        return datetime(2000 + yy, mm, dd, hh, mi)
    except ValueError:
        return None


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def _html_strip_blocks(text: str) -> str:
    """把 code/pre/script/style 块内容清空但**保留换行数** (行号不漂)。"""
    for tag in HTML_BLOCK_TAGS:
        text = re.sub(
            rf"<{tag}\b.*?</{tag}>",
            lambda m: "\n" * m.group(0).count("\n"),
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return text


def _md_body_lines(text: str) -> list[tuple[int, str]]:
    """md 正文行 (行号, 去掉围栏代码块与行内代码后的文本)。"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append((i, ""))
            continue
        out.append((i, "" if in_fence else MD_INLINE_CODE_RE.sub("", line)))
    return out


def _html_body_lines(text: str) -> list[tuple[int, str]]:
    return list(enumerate(_html_strip_blocks(text).split("\n"), 1))


def _scan_body_line(line: str) -> list[tuple[str, str]]:
    """一行正文里的非规范日期 token → [(类型, 修复提示)]。"""
    if ALLOW_MARK in line:
        return []
    clean = URL_RE.sub("", line)
    hits: list[tuple[str, str]] = []
    for kind, rx, hint in BODY_BAD_PATTERNS:
        for m in rx.finditer(clean):
            hits.append((kind, f"{m.group(0)} —— {hint}"))
    for m in NON_PADDED_RE.finditer(clean):
        if len(m.group(1)) == 1 or len(m.group(2)) == 1:
            hits.append(("不补零日期", f"{m.group(0)} —— 改用 `YYYY-MM-DD` (月/日补零)"))
    return hits


# --------------------------------------------------------------------------- 三层守卫


def check_filenames(root: Path, mb: Path) -> list[str]:
    """文件名层: tasks 的 `YY-MM-DD` / 切片与 HTML 制品的 `YY-MM-DD-HHMM`。"""
    problems: list[str] = []
    today = now().date()
    moment = now()
    for rel_dir, rx in ((TASK_DIR, TASK_PREFIX_RE), ) + tuple((d, STAMP_PREFIX_RE) for d in STAMP_DIRS):
        directory = mb / rel_dir
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_dir() or path.name.startswith("_"):
                continue
            m = rx.match(path.name)
            if not m:
                continue  # 无日期前缀的命名由别的守卫管, 这里只管值
            rel = rel_posix(path, root)
            if rx is TASK_PREFIX_RE:
                d = parse_date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if d is None:
                    problems.append(f"{rel}: 文件名日期不是合法日期")
                elif d > today:
                    problems.append(f"{rel}: 文件名日期在未来 ({d.isoformat()}) —— 取时走 `commands run kb.time`")
            else:
                dt = parse_stamp(*(int(g) for g in m.groups()))
                if dt is None:
                    problems.append(f"{rel}: 文件名时间戳不是合法时间")
                elif dt > moment:
                    problems.append(f"{rel}: 文件名时间戳在未来 ({dt:%Y-%m-%d %H:%M}) —— 取时走 `commands run kb.time`")
    return problems


def _check_meta_value(value: str, today: date) -> str | None:
    """Added / Updated 值: 以 `YYYY-MM-DD` 起头, 可跟 ` HH:MM` 或 ` (附注)`。返回错误提示或 None。"""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(.*)$", value)
    if not m:
        return "日期必须以 `YYYY-MM-DD` 起头"
    d = parse_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if d is None:
        return "不是合法日期"
    if d > today:
        return f"日期在未来 ({d.isoformat()})"
    rest = m.group(4)
    if rest == "" or rest.startswith(" ("):
        return None
    tm = re.match(r"^\s(\d{2}):(\d{2})(?:\D.*)?$", rest)
    if tm and int(tm.group(1)) <= 23 and int(tm.group(2)) <= 59:
        return None
    return "后缀非规范 (应为 ` HH:MM` 或 ` (附注)`), 时刻取 `commands run kb.time`"


def check_metadata(root: Path, mb: Path) -> list[str]:
    """元数据层: Added / Updated / 最后活动 / doc-added / doc-updated。"""
    problems: list[str] = []
    today = now().date()
    moment = now()
    for path in sorted(mb.rglob("*")):
        if path.is_dir():
            continue
        suffix = path.suffix.lower()
        if suffix not in (".md", ".html", ".htm"):
            continue
        rel = rel_posix(path, root)
        text = _read(path)

        for m in META_FIELD_RE.finditer(text):
            lineno = text[:m.start()].count("\n") + 1
            err = _check_meta_value(m.group(2), today)
            if err:
                problems.append(f"{rel}:{lineno}: `**{m.group(1)}:**` {err}")

        for m in LAST_ACTIVE_LINE_RE.finditer(text):
            lineno = text[:m.start()].count("\n") + 1
            value = m.group(1)
            sm = LAST_ACTIVE_STRICT_RE.match(value)
            if not sm:
                problems.append(
                    f"{rel}:{lineno}: `最后活动` 必须是严格 `YYYY-MM-DD HH:MM`, 现为 `{value}` "
                    "—— 取时走 `commands run kb.time`"
                )
                continue
            dt = parse_stamp(
                int(sm.group(1)) - 2000, int(sm.group(2)), int(sm.group(3)), int(sm.group(4)), int(sm.group(5))
            )
            if dt is None:
                problems.append(f"{rel}:{lineno}: `最后活动` 不是合法时间 (`{value}`)")
            elif dt > moment:
                problems.append(f"{rel}:{lineno}: `最后活动` 在未来 ({value}) —— 取时走 `commands run kb.time`")

        if suffix in (".html", ".htm"):
            for tag in META_TAG_RE.finditer(text):
                name_m = NAME_ATTR_RE.search(tag.group(0))
                if not name_m or name_m.group(1) not in DOC_META_FIELDS:
                    continue
                content_m = CONTENT_ATTR_RE.search(tag.group(0))
                value = content_m.group(1) if content_m else ""
                lineno = text[:tag.start()].count("\n") + 1
                vm = DOC_META_VALUE_RE.match(value)
                if not vm:
                    problems.append(
                        f"{rel}:{lineno}: `<meta name=\"{name_m.group(1)}\">` 必须是 `YY-MM-DD-HHMM`, "
                        f"现为 `{value}` —— 取时走 `commands run kb.time`"
                    )
                    continue
                dt = parse_stamp(*(int(g) for g in vm.groups()))
                if dt is None:
                    problems.append(f"{rel}:{lineno}: `<meta name=\"{name_m.group(1)}\">` 不是合法时间 (`{value}`)")
                elif dt > moment:
                    problems.append(
                        f"{rel}:{lineno}: `<meta name=\"{name_m.group(1)}\">` 在未来 ({value}) "
                        "—— 取时走 `commands run kb.time`"
                    )
    return problems


def check_body(root: Path, mb: Path) -> list[str]:
    """正文层: 全部 .md / .html 的非规范日期变体 (规范 token 不查未来)。"""
    problems: list[str] = []
    for path in sorted(mb.rglob("*")):
        if path.is_dir():
            continue
        suffix = path.suffix.lower()
        if suffix == ".md":
            lines = _md_body_lines(_read(path))
        elif suffix in (".html", ".htm"):
            lines = _html_body_lines(_read(path))
        else:
            continue
        rel = rel_posix(path, root)
        for lineno, line in lines:
            if not line:
                continue
            for kind, detail in _scan_body_line(line):
                problems.append(f"{rel}:{lineno}: 正文日期体例 —— {kind}: {detail}")
    return problems


def collect_violations(root: Path, mb: Path) -> list[str]:
    """三层守卫合并 (顺序: 文件名 → 元数据 → 正文)。"""
    return check_filenames(root, mb) + check_metadata(root, mb) + check_body(root, mb)


# --------------------------------------------------------------------------- CLI


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _three_lines(moment: datetime) -> str:
    return (
        f"date:  {moment.strftime(DATE_FMT)}\n"
        f"time:  {moment.strftime(TIME_FMT)}\n"
        f"stamp: {moment.strftime(STAMP_FMT)}"
    )


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "command", nargs="?", choices=("date", "time", "stamp", "check"), help="date / time / stamp / check; 省略则三行全打"
    )
    parser.add_argument("--check", action="store_true", help="日期守卫 (等价于 `check`)")
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟过滤用)")
    parser.add_argument("--quiet", action="store_true", help="只打印违规行")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    # ❗必须在任何动作之前: 冒烟闸门用 `--safety` 探活。本脚本无参 = 只打印, 属 read-only-default,
    #   所以它会**留在**冒烟名单里, 随后被 `<脚本> --help` 跑一次 (argparse 天然支持)。
    if args.safety:
        print("read-only-default")
        return 0

    moment = now()
    if args.command == "date":
        print(moment.strftime(DATE_FMT))
        return 0
    if args.command == "time":
        print(moment.strftime(TIME_FMT))
        return 0
    if args.command == "stamp":
        print(moment.strftime(STAMP_FMT))
        return 0

    if args.check or args.command == "check":
        root = Path(args.root).resolve() if args.root else find_root()
        mb = resolve_mb_dir(root, args.mb_dir)
        if not mb.is_dir():
            sys.stderr.write(f"memory-bank 目录不存在: {mb}\n")
            return 2
        problems = collect_violations(root, mb)
        for p in problems:
            print(p)
        if problems:
            sys.stderr.write(
                f"\n日期守卫: {len(problems)} 项违规 —— 取时一律 `commands run kb.time`; "
                "确有需要豁免的机器数据用行内 `<!-- time:allow -->`。\n"
            )
            return 1
        if not args.quiet:
            print("日期守卫: 无违规。")
        return 0

    print(_three_lines(moment))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
