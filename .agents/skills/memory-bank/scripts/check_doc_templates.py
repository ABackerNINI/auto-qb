#!/usr/bin/env python3
"""新增面检查 (计划 memory-bank/plans/26-10-17-0527 §06, D3 存量冻结; P3 扩四族)。

对**冻结线之后新建**的族文件 (plan / task / slice / report / baseline) 校验:
- 命名正则 (单点: `_common.PLAN_FILE_RE` / `TASK_FILE_RE` / `SLICE_FILE_RE` / `REPORT_FILE_RE`)
- 头部字段齐全且状态词在表内 (单点: `_common.DOC_STATUSES` / `TASK_STATUSES`)
- **无残留 SLOT 标记**, 且 SLOT 不出现在头部区 (渲染正确性: 机器字段必须被命令填掉)
- HTML 族 `doc-type` 与族名一致、`doc-topic` 非空、stamp 体例合法
- baseline: `# <TOTAL> —— <标题>` + `> 摘要:` (基线阅读器数据源) + `> 基线时间:` (排序键, 严格格式)

**冻结线 = 实施日 stamp 常量** (`FREEZE_LINE`): 之前 = 存量, 一律豁免 (先例: doc-forms 51 份
旧命名豁免 / `check_wording` 的 FROZEN 常数 —— 防漂移靠守卫拦新增, 不回头改存量)。
⚠ 档案族命名只到天 (`YY-MM-DD`), 文件名分不出「当天冻结线之前/之后」—— 口径取
**文件名日期 ≥ 冻结日**入检查面 (当天既有档案均合规; 这是日期精度下的可行判据)。
⚠ 分不清新旧的面 (缺 doc-added / 非日期前缀命名的存量 / **无时间戳的坑档与进展件**)
跳过, 由既有守卫 (docmap 主键 / timekit / check_kb_structure 三行头与坑档三字段 / gen_active_recent)
兜底 —— 坑档 (`pitfalls/<类>/<主题>.md`) 与进展件 (`progress/<主题>.md`) 命名不带时间戳,
**无法与存量区分**, 故不在冻结线扫描面内 (计划 §06「冻结线之后新建」的可判定边界)。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/check_doc_templates.py           默认 = 全量检查
    python <skill-dir>/scripts/check_doc_templates.py --check   同上 (kb.check / 提交闸门接线)
    python <skill-dir>/scripts/check_doc_templates.py --root <dir> --mb-dir <dir>   # 覆盖探测
退出码: 0 无违规 / 1 有违规 (逐条打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    DOC_STATUSES,
    FAMILIES,
    PLAN_FILE_RE,
    REPORT_FILE_RE,
    SLICE_FILE_RE,
    SLOT_RE,
    TASK_FILE_RE,
    TASK_STATUSES,
    find_root,
    rel_posix,
    resolve_mb_dir,
)

# P1 实施日 stamp (计划 26-10-17-0527 落地的时刻) —— 冻结线, 之前 = 存量豁免
FREEZE_LINE = "26-10-17-0736"
FREEZE_DATE = FREEZE_LINE[:8]  # 档案族命名只到天: 文件名日期 ≥ 冻结日 入检查面

STAMP_VALUE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}$")
DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")
STAMP_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-")
META_RE = re.compile(r'<meta name="(doc-[a-z]+)" content="([^"]*)">')
LAST_ACTIVE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
BASELINE_TIME_VALUE_RE = LAST_ACTIVE_VALUE_RE  # `> 基线时间:` 同款严格格式 (排序键)
STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^\*\*(Added|Updated|Summary|Topics):\*\*\s*(.+?)\s*$", re.MULTILINE)
HEAD_REGION_RE = re.compile(r"<head\b.*?</head>", re.DOTALL | re.IGNORECASE)
# md 头部区 = 首个 `##`+ 级标题之前的行 (三行头/状态行)。`##`+ 而非 `##`: 坑档条目用
# `### ` 起头, 只认 `## ` 会把整份坑档都算成头部区 (SLOT 落点误报)。
MD_HEADER_SPLIT_RE = re.compile(r"^#{2,}\s", re.MULTILINE)


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _head_region(text: str) -> str:
    """头部区: HTML 取 `<head>…</head>`; md 取首个 `## ` 之前的行 (三行头/状态行)。"""
    m = HEAD_REGION_RE.search(text)
    if m:
        return m.group(0)
    parts = MD_HEADER_SPLIT_RE.split(text, maxsplit=1)
    return parts[0] if len(parts) == 2 else text


def _strip_code(text: str) -> str:
    """去掉围栏代码块与行内代码跨度 (可引述豁免, 同 check_wording 口径)。"""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`\n]*`", "", text)


def _residual_slots(text: str) -> list[str]:
    """残留 SLOT 标记 —— **先剥代码跨度与围栏**: 文档里引述模板标记(如基线的
    「全部段首留 `<!-- SLOT: 说明 -->`」)是**可引述**内容, 不算残留 (与 check_wording
    的「代码/围栏 (可引述)」豁免同口径; 模板真实残留 SLOT 从不出现在代码跨度内)。
    """
    return [s.strip() for s in SLOT_RE.findall(_strip_code(text))]


def validate_file(path: Path, family: str, label: str | None = None) -> list[str]:
    """单文件校验 (守卫红绿双验直调本函数, 不经冻结线过滤)。返回问题清单 (空 = 通过)。

    消息只给**裸描述** (不带文件名) —— 文件名由调用方贴 (sweep 贴 rel_posix, 守阵自己断言子串)。
    """
    _ = label
    problems: list[str] = []
    text = path.read_bytes().decode("utf-8", errors="replace")
    spec = FAMILIES[family]

    if not spec.naming_re.match(path.name):
        problems.append(f"命名不合 {family} 族正则 {spec.naming_re.pattern}")

    if family in ("plan", "report"):
        # HTML 制品共用同一组 doc-* 校验 (doc-type 区分族; report 出厂即 Done, 同 5 词表)
        meta = dict(META_RE.findall(text))
        if meta.get("doc-type") != family:
            problems.append(f"doc-type 必须是 {family} (现为 {meta.get('doc-type')!r})")
        if not meta.get("doc-topic"):
            problems.append("缺 doc-topic (专题视图主键, 缺了会被静默漏收)")
        status = meta.get("doc-status", "")
        if status not in DOC_STATUSES:
            problems.append(f"doc-status 不在 5 词表 ({' / '.join(DOC_STATUSES)}): 现为 {status!r}")
        for field in ("doc-added", "doc-updated"):
            value = meta.get(field, "")
            if not STAMP_VALUE_RE.match(value):
                problems.append(f"{field} 必须是 YY-MM-DD-HHMM (现为 {value!r}) —— 取时走 commands run kb.time")
    elif family == "task":
        head = _head_region(text)
        status_match = STATUS_LINE_RE.search(head)
        if not status_match:
            problems.append(f"头部区缺 `**Status:**` 行 (词表: {' / '.join(TASK_STATUSES)})")
        elif status_match.group(1) not in TASK_STATUSES:
            problems.append(f"`**Status:**` 不在 4 词表 ({' / '.join(TASK_STATUSES)}): 现为 {status_match.group(1)!r}")
        fields = dict(FIELD_LINE_RE.findall(head))
        for field in ("Added", "Updated", "Summary", "Topics"):
            if field not in fields:
                problems.append(f"头部区缺 `**{field}:**` 行")
    elif family in ("pitfall", "progress"):
        # 三行头 (# 标题 / > 摘要: / > 触发:) —— 与 check_kb_structure 同口径, 这里管新增面
        head = _head_region(text)
        if not re.search(r"^#\s+\S", head, re.MULTILINE):
            problems.append("缺三行头的 `# 标题`")
        if not re.search(r"^>\s*摘要:\s*\S", head, re.MULTILINE):
            problems.append("缺三行头的 `> 摘要:`")
        if not re.search(r"^>\s*触发:\s*\S", head, re.MULTILINE):
            problems.append("缺三行头的 `> 触发:` (路由判断, 由 --triggers 填入, 裁定 A7 参数分支)")
    elif family == "baseline":
        head = _head_region(text)
        if not re.search(r"^#\s+\S", head, re.MULTILINE):
            problems.append("缺 `# <TOTAL> —— <标题>` 标题行")
        if not re.search(r"^>\s*摘要:\s*\S", head, re.MULTILINE):
            problems.append("缺 `> 摘要:` (基线阅读器 gen_baseline_recent 的数据源)")
        baseline_time = re.search(r"^>\s*基线时间:\s*(\S.*?)\s*$", head, re.MULTILINE)
        if not baseline_time:
            problems.append("缺 `> 基线时间:` (排序键; 须严格 YYYY-MM-DD HH:MM)")
        elif not BASELINE_TIME_VALUE_RE.match(baseline_time.group(1)):
            problems.append(f"`> 基线时间:` 必须是严格 YYYY-MM-DD HH:MM (现为 {baseline_time.group(1)!r})")
    else:  # slice
        head = _head_region(text)
        if not re.search(r"^#\s+\S", head, re.MULTILINE):
            problems.append("缺三行头的 `# 标题`")
        if not re.search(r"^>\s*摘要:\s*\S", head, re.MULTILINE):
            problems.append("缺三行头的 `> 摘要:`")
        last_active = re.search(r"^>\s*最后活动:\s*(\S.*?)\s*$", head, re.MULTILINE)
        if not last_active:
            problems.append("缺三行头的 `> 最后活动:` (须严格 YYYY-MM-DD HH:MM)")
        elif not LAST_ACTIVE_VALUE_RE.match(last_active.group(1)):
            problems.append(f"`> 最后活动:` 必须是严格 YYYY-MM-DD HH:MM (现为 {last_active.group(1)!r})")

    slots = _residual_slots(text)
    if slots:
        where = "头部区" if SLOT_RE.search(_strip_code(_head_region(text))) else "正文区"
        problems.append(f"{where}残留 SLOT 标记 {len(slots)} 处 (建后必须填/删): {slots[0]} …")
    return problems


def check_new_faces(root: Path, mb: Path) -> tuple[list[str], int]:
    """冻结线之后新建的族文件全量检查。返回 (问题清单, 检查件数)。"""
    problems: list[str] = []
    checked = 0

    plans = mb / "plans"
    if plans.is_dir():
        for path in sorted(plans.glob("*.html")):
            text = path.read_text(encoding="utf-8", errors="replace")
            added = dict(META_RE.findall(text)).get("doc-added", "")
            if not STAMP_VALUE_RE.match(added) or added < FREEZE_LINE:
                continue  # 分不清新旧 (缺/坏 doc-added) 或存量 —— 跳过, 既有守卫兜底
            checked += 1
            problems += [f"{rel_posix(path, root)}: {p}" for p in validate_file(path, "plan", path.name)]

    reports = mb / "reports"
    if reports.is_dir():
        # 与 plan 同判据 (doc-added 精确到分); 出厂即 Done, 词表同 5 词
        for path in sorted(reports.glob("*.html")):
            text = path.read_text(encoding="utf-8", errors="replace")
            added = dict(META_RE.findall(text)).get("doc-added", "")
            if not STAMP_VALUE_RE.match(added) or added < FREEZE_LINE:
                continue
            checked += 1
            problems += [f"{rel_posix(path, root)}: {p}" for p in validate_file(path, "report", path.name)]

    baselines = mb / FAMILIES["baseline"].dir  # testing/baselines
    if baselines.is_dir():
        # 命名带时分 (与切片同款): 文件名 stamp 前缀 ≥ 冻结线 入检查面
        for path in sorted(baselines.glob("*.md")):
            if path.name.startswith("_") or not STAMP_PREFIX_RE.match(path.name):
                continue
            if path.name[:13] < FREEZE_LINE:
                continue
            checked += 1
            problems += [f"{rel_posix(path, root)}: {p}" for p in validate_file(path, "baseline", path.name)]
    # ⚠ 坑档 (pitfalls/<类>/<主题>.md) 与进展件 (progress/<主题>.md) 命名**不带时间戳**,
    # 无法与存量区分 —— 不在冻结线扫描面 (计划 §06 可判定边界; 既有守卫 check_kb_structure
    # 兜底三行头与坑档三字段)。它们的头部零 SLOT 由模板契约 + 族注册表同源守阵钉住。

    tasks = mb / "tasks"
    if tasks.is_dir():
        for path in sorted(tasks.glob("*.md")):
            if path.name.startswith("_") or not DATE_PREFIX_RE.match(path.name):
                continue  # 索引/非日期前缀存量 (legacy) 不在本检查面
            if path.name[:8] < FREEZE_DATE:
                continue
            checked += 1
            problems += [f"{rel_posix(path, root)}: {p}" for p in validate_file(path, "task", path.name)]

    slices = mb / FAMILIES["slice"].dir
    if slices.is_dir():
        for path in sorted(slices.glob("*.md")):
            if path.name.startswith("_") or not STAMP_PREFIX_RE.match(path.name):
                continue
            if path.name[:13] < FREEZE_LINE:
                continue
            checked += 1
            problems += [f"{rel_posix(path, root)}: {p}" for p in validate_file(path, "slice", path.name)]

    return problems, checked


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只校验不写 (kb.check / 提交闸门接线; 本脚本本就不写)")
    parser.add_argument("--quiet", action="store_true", help="只打印违规行")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    if not mb.is_dir():
        sys.stderr.write(f"memory-bank 目录不存在: {mb}\n")
        return 2

    problems, checked = check_new_faces(root, mb)

    if not args.quiet:
        print(f"新增面检查 (冻结线 {FREEZE_LINE} 之后新建的 plan/task/slice/report/baseline 族文件; 存量豁免): {checked} 件在检查面")
    for line in problems:
        print(f"  [FAIL] {line}")
    if problems:
        print(f"\n共 {len(problems)} 项不通过。")
        return 1
    if not args.quiet:
        print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
