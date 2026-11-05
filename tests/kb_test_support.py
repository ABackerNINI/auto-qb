"""`kb_test_support` 支撑: 从 `test_memory_bank.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

from __future__ import annotations

import re

import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MB = ROOT / "memory-bank"

TASKS = MB / "tasks"

INDEX = TASKS / "_index.md"

SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"

GEN = SKILL_SCRIPTS / "gen_tasks_index.py"

SKILL = ROOT / ".agents" / "skills" / "memory-bank" / "SKILL.md"

STATUSES = ("In Progress", "Open", "Done", "Dropped")

REQUIRED_SECTIONS = ("## 原始请求", "## 思考过程与决策", "## 实现计划", "## 子任务状态表", "## 进度日志")

# 非 `_index.md` 的生成物 —— 新增一个必须显式登记(详见 test_gen_all_declares_exactly_all_indexes)
# 分卷页(`_index-<n>.md`)不在此列: 它们按 `_index*.md` 通配, 与主索引同批产出。
EXTRA_GENERATED = (
    "memory-bank/issues/attachments/_archive.md",
    "memory-bank/tasks/attachments/_archive.md",
    "memory-bank/plans/attachments/_archive.md",
    "memory-bank/reports/attachments/_archive.md",
)

DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")

LEGACY_PREFIX_RE = re.compile(r"^TASK\d{3}-")

FILE_RE = re.compile(r"^(?:TASK\d{3}-|\d{2}-\d{2}-\d{2}-)[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

INDEX_ID_RE = re.compile(r"- \[(TASK\d{3}|\d{2}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*)\]")

STATUS_RE = re.compile(r"\*\*Status:\*\* (In Progress|Open|Done|Dropped)")


def _task_files() -> list[Path]:
    return sorted(p for p in TASKS.glob("*.md") if not p.name.startswith("_"))


def _slug_of(path: Path) -> str:
    """去掉编号前缀 (`TASKnnn-`) 或日期前缀 (`YY-MM-DD-`) 后的专题 slug。"""
    stem = path.stem
    stem = LEGACY_PREFIX_RE.sub("", stem)
    return DATE_PREFIX_RE.sub("", stem)


def _indexed_sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            continue
        for key in INDEX_ID_RE.findall(line):
            sections[key] = current
    return sections


def _kb_checker():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_kb_structure

    return check_kb_structure


def _doc_links_module():
    """载入 memory-bank skill 的链接检查器 (**进程内 import** —— 本项目测试禁止起子进程)。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_doc_links", SKILL_SCRIPTS / "check_doc_links.py")
    assert spec and spec.loader, "缺少 memory-bank skill 的 scripts/check_doc_links.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _gen_all():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_all

    return gen_all


def _timekit():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import timekit

    return timekit


def _wording():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_wording

    return check_wording


def _mutation_anchor():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_mutation_anchor

    return check_mutation_anchor


def _doc_templates():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_doc_templates

    return check_doc_templates


def _new_doc():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import new_doc

    return new_doc


def _wrap():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import wrap_session

    return wrap_session


def _fill_slots(path: Path) -> None:
    """模拟 agent 的「一次填空」: 把所有 SLOT 标记替换为内容。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    text = path.read_text(encoding="utf-8")
    path.write_text(_common.SLOT_RE.sub("已填内容", text), encoding="utf-8")


def _flip_status():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import flip_status

    return flip_status


def _bump_doc():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import bump_doc

    return bump_doc


def _gen_doc_map():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_doc_map

    return gen_doc_map


def _kb_clock():
    """实现侧的时间单点(`timekit.now()`, UTC+8 墙钟 —— `kb.status`/`kb.bump` 都取自它)。

    断言必须与实现**同源取时**, 不能写死日期: 本文件曾把运行当天 (2026-10-17) 写成字面量,
    过零点必红, 与业务无关 (issue 26-10-18-0608-test-memory-bank-test-hardcoded-today)。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import timekit

    return timekit.now()


def _p2_fixture(tmp_path: Path) -> Path:
    """P2 夹具: 最小可跑的 memory-bank (plans / tasks / activeContext / issues)。"""
    mb = tmp_path / "memory-bank"
    for sub in ("plans", "tasks", "activeContext", "issues"):
        (mb / sub).mkdir(parents=True)
    return mb


def _write_plan(mb: Path, name: str = "26-10-17-0900-plan-p2.html") -> Path:
    path = mb / "plans" / name
    path.write_text(
        """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>P2 冒烟计划</title>
<meta name="doc-type" content="plan">
<meta name="doc-topic" content="p2-topic">
<meta name="doc-status" content="Open">
<meta name="doc-added" content="26-10-17-0900">
<meta name="doc-updated" content="26-10-17-0900">
</head>
<body>
<div class="meta">
  <b>doc-added</b> 26-10-17-0900 · <b>doc-updated</b> 26-10-17-0900 · <b>doc-status</b> Open · <b>载体</b> 单文件 HTML(dark)<br>
</div>
<h2><span class="no">§10</span>变更记录</h2>
<ul>
  <li><span class="tag">R0 · 26-10-17-0900</span> 初版。</li>
</ul>
</body>
</html>
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_task(mb: Path, name: str = "26-10-17-backend-p2.md") -> Path:
    path = mb / "tasks" / name
    path.write_text(
        """# 26-10-17-backend-p2 — P2 冒烟档案

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-17
**Summary:** P2 冒烟档案标题
**Topics:** backend-p2

## 原始请求

x
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_slice(mb: Path, name: str = "26-10-17-0900-p2-topic.md") -> Path:
    path = mb / "activeContext" / name
    path.write_text(
        """# P2 冒烟切片

> 摘要: 冒烟
> 最后活动: 2026-10-17 09:00

## 产出

x
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_issue(mb: Path, name: str = "26-10-17-0900-bug-p2.html") -> Path:
    path = mb / "issues" / name
    path.write_text(
        '<html><head>\n<meta name="issue-status" content="Open">\n<meta name="doc-topic" content="p2-bug">\n</head><body>x</body></html>\n',
        encoding="utf-8",
        newline="\n",
    )
    return path


def _p3_family_paths(mb: Path) -> dict[str, Path]:
    """P3 冒烟四件的落点 (同 build 顺序)。"""
    return {
        "pitfall": mb / "pitfalls" / "kb" / "smoke-pitfall.md",
        "report": next((mb / "reports").glob("*-report-smoke-report.html")),
        "baseline": next((mb / "testing" / "baselines").glob("*-smoke-baseline.md")),
        "progress": mb / "progress" / "smoke-progress.md",
    }


def _kb_tier():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import kb_tier

    return kb_tier


def _tier_fixture(tmp_path: Path) -> Path:
    """kb.tier 夹具: 最小可跑的 pitfalls/git/ (只建 kb.tier 扫描的那一层)。"""
    mb = tmp_path / "memory-bank"
    (mb / "pitfalls" / "git").mkdir(parents=True)
    return mb


def _tier_pitfall(mb: Path, stem: str, crlf: bool = False) -> Path:
    """标准坑档夹具: 三行头 + `### ` 条目正文 (含各类链接, 供 migrate 断言)。"""
    body = (
        f"# {stem}\n"
        "\n"
        "> 摘要: 判据单点一句话。\n"
        "> 触发: git, sync\n"
        "\n"
        "### 旧叙事\n"
        "\n"
        "- 判别: 见 [运行口径](../../testing/run.md) 与 [同目录](refs.md)。\n"
        "- 外链: [文档](https://example.com/a.md) 与 [锚点](#sec) 原样。\n"
        "- 叙事: 事故时间线。\n"
    )
    if crlf:
        body = body.replace("\n", "\r\n")
    path = mb / "pitfalls" / "git" / f"{stem}.md"
    path.write_bytes(body.encode("utf-8"))
    return path


def _closed_keep_module():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_tasks_index

    return gen_tasks_index


def _closed_keep_fixture(tmp_path: Path, done: int = 0, dropped: int = 0, inflight: int = 0) -> tuple[Path, Path]:
    """CLOSED_KEEP 夹具: `done` 件 Done + `dropped` 件 Dropped + `inflight` 件 In Progress。

    排序键 `**Updated:**` 从 2001-01-01 起逐件递增一天 —— "最近 60 条"才有唯一答案;
    001 号的摘要超长(> SUMMARY_MAX), "主索引截断 / 归档不截断"的对照正好用它。
    """
    from datetime import date, timedelta

    mb = tmp_path / "memory-bank"
    (mb / "tasks").mkdir(parents=True)
    n = 0
    for status, count in (("Done", done), ("Dropped", dropped), ("In Progress", inflight)):
        for _ in range(count):
            n += 1
            slug = f"26-01-01-test-closed-keep-{n:03d}"
            day = (date(2001, 1, 1) + timedelta(days=n - 1)).isoformat()
            summary = f"档案 {n:03d} 摘要" + ("x" * 80 if n == 1 else "")
            (mb / "tasks" / f"{slug}.md").write_text(
                f"# {slug} - CLOSED_KEEP 档案 {n:03d}\n\n"
                f"**Status:** {status}\n"
                f"**Added:** {day}\n"
                f"**Updated:** {day}\n"
                f"**Summary:** {summary}\n"
                f"**Topics:** closed-keep-{n:03d}\n",
                encoding="utf-8",
                newline="\n",
            )
    return tmp_path, mb


def _index_section(text: str, status: str) -> str:
    """切出主索引单一状态分区的正文(到下一个 `## ` 或文件尾)。"""
    m = re.search(rf"^## {re.escape(status)}\n\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, f"索引缺状态分区 `## {status}`"
    return m.group(1)


def _entry_lines(section: str) -> list[str]:
    return [line for line in section.splitlines() if line.startswith("- ")]


def _status_drift():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_status_drift

    return check_status_drift


def _drift_fixture(tmp_path: Path) -> Path:
    """漂移夹具: 最小可跑的 memory-bank (progress/tasks/issues/plans/reports)。"""
    mb = tmp_path / "memory-bank"
    for sub in ("progress", "tasks", "issues", "plans", "reports"):
        (mb / sub).mkdir(parents=True)
    return mb


def _drift_task(mb: Path, name: str, status: str | None, body: str = "x") -> Path:
    """tasks 档案夹具; status=None 造「缺 **Status:** 行」的异常件。"""
    head = "" if status is None else f"**Status:** {status}\n"
    path = mb / "tasks" / name
    path.write_text(f"# {name[:-3]} - drift fixture\n\n{head}\n## 原始请求\n\n{body}\n", encoding="utf-8", newline="\n")
    return path


def _drift_issue(mb: Path, name: str, status: str | None, badge: str | None = None, body: str = "<p>x</p>") -> Path:
    """issue 夹具; badge=None 造「无封面 badge」件 (文档化边界), status=None 造缺 meta 异常件。"""
    badge_html = "" if badge is None else (
        f'<div class="item"><div class="k">状态</div><div class="v"><span class="badge">{badge}</span></div></div>'
    )
    meta_html = "" if status is None else f'<meta name="issue-status" content="{status}">\n'
    path = mb / "issues" / name
    path.write_text(
        f"<html><head>\n{meta_html}</head><body>{badge_html}{body}</body></html>\n", encoding="utf-8", newline="\n"
    )
    return path


def _drift_doc(mb: Path, sub: str, name: str, status: str) -> Path:
    """plan/report 夹具 (doc-status 5 词表)。"""
    path = mb / sub / name
    path.write_text(
        f'<html><head>\n<meta name="doc-status" content="{status}">\n</head><body>x</body></html>\n',
        encoding="utf-8",
        newline="\n",
    )
    return path


def _drift_run(tmp_path: Path, mb: Path, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    """进程内跑 check_status_drift.main (不 --quiet: 无硬拦时输出 all-clear 行)。
    extra_args 透传给 main (例如 ["--verbose"])。"""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    drift = _status_drift()
    out, err = io.StringIO(), io.StringIO()
    args = ["--root", str(tmp_path), "--mb-dir", str(mb)] + (extra_args or [])
    with redirect_stdout(out), redirect_stderr(err):
        rc = drift.main(args)
    return rc, out.getvalue(), err.getvalue()


def _check_html():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_html

    return check_html
