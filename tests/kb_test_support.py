"""`kb_test_support` 支撑: 从 `test_memory_bank.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

from __future__ import annotations

import re

import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MB = ROOT / "memory-bank"

TASKS = MB / "tasks"

SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"

SKILL = ROOT / ".agents" / "skills" / "memory-bank" / "SKILL.md"

STATUSES = ("In Progress", "Open", "Done", "Dropped")

REQUIRED_SECTIONS = ("## 原始请求", "## 思考过程与决策", "## 实现计划", "## 子任务状态表", "## 进度日志")

# 非 `_index.md` 的生成物 —— 新增一个必须显式登记(详见 test_gen_all_declares_exactly_all_indexes)
# 分卷页(`_index-<n>.md`)不在此列: 它们按 `_index*.md` 通配, 与主索引同批产出。
# 2026-11-08 重构: 四个归档清单 `_archive.md` 已随低价值层移除退役, 生成集合收缩后暂无成员。
EXTRA_GENERATED = ()

DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")

LEGACY_PREFIX_RE = re.compile(r"^TASK\d{3}-")

FILE_RE = re.compile(r"^(?:TASK\d{3}-|\d{2}-\d{2}-\d{2}-)[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

STATUS_RE = re.compile(r"\*\*Status:\*\* (In Progress|Open|Done|Dropped)")


def _task_files() -> list[Path]:
    return sorted(p for p in TASKS.glob("*.md") if not p.name.startswith("_"))


def _slug_of(path: Path) -> str:
    """去掉编号前缀 (`TASKnnn-`) 或日期前缀 (`YY-MM-DD-`) 后的专题 slug。"""
    stem = path.stem
    stem = LEGACY_PREFIX_RE.sub("", stem)
    return DATE_PREFIX_RE.sub("", stem)


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
    """P2 夹具: 最小可跑的 memory-bank (plans / tasks / active-context / issues)。"""
    mb = tmp_path / "memory-bank"
    for sub in ("plans", "tasks", "active-context", "issues"):
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
    path = mb / "active-context" / name
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
    """issue 夹具: W2 机读形态 (issue-status meta + 状态徽标/类型徽标 + 状态变更日志节)。

    类型徽标放在状态徽标**之前** (同模板封面行序) —— kb.status 的徽标替换若误锚到首个
    badge (类型), 断言立即判红; 翻状态 (W4) 的两处改与日志追加都依赖这份形态。
    """
    path = mb / "issues" / name
    path.write_text(
        """<html><head>
<meta name="issue-status" content="Open">
<meta name="doc-topic" content="p2-bug">
</head><body>
<div class="meta-row">
  <div class="item"><div class="k">类型</div><div class="v"><span class="badge type">bug</span></div></div>
  <div class="item"><div class="k">状态</div><div class="v"><span class="badge">Open</span></div></div>
</div>
<h2>状态变更日志</h2>
<ul>
  <li>2026-10-17 — 入池，状态 <strong>Open</strong>（计划外，未修）</li>
</ul>
</body></html>
""",
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
    }


def _status_drift():
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import check_status_drift

    return check_status_drift


def _drift_fixture(tmp_path: Path) -> Path:
    """漂移夹具: 最小可跑的 memory-bank (tasks/issues/plans/reports)。

    (2026-11-08 重构 W5: progress/ 目录已全灭, 夹具不再造它。)
    """
    mb = tmp_path / "memory-bank"
    for sub in ("tasks", "issues", "plans", "reports"):
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
