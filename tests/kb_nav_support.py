"""`kb_nav_support` 支撑: 从 `test_kb_nav.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

from __future__ import annotations

import http.client
import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"
SHELL = SKILL_SCRIPTS / "nav_page.html"

if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import gen_doc_map  # noqa: E402
import nav_data  # noqa: E402
import nav_server  # noqa: E402


def _shell_css() -> str:
    """壳的 CSS 文本, 已去注释 (免得注释里的示例选择器被当成规则)。"""
    return re.sub(r"/\*.*?\*/", "", SHELL.read_text(encoding="utf-8"), flags=re.S)


def _rule(css: str, sel: str) -> str:
    m = re.search(re.escape(sel) + r"[^{}]*\{([^}]*)\}", css)
    assert m, f"{sel} 规则不见了? 改版要同步本守阵"
    return m.group(1)


def _shell_fn(text: str, name: str) -> str:
    """按花括号配平抽取壳内 `function <name>(...) {` 的函数体 (嵌套体安全) ——
    `function X\\(\\) \\{(.*?)\\n\\}` 一类非贪婪写法只配得上无嵌套体的函数。"""
    sig = f"function {name}("
    at = text.index(sig)
    open_at = text.index("{", at)
    depth = 0
    for pos in range(open_at, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:pos]
    raise AssertionError(f"function {name} 未闭合? 改版要同步本守阵")


PLAN_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="doc-type" content="plan">
<meta name="doc-topic" content="{topic}">
<meta name="doc-status" content="{status}">
<meta name="doc-added" content="{added}">
<meta name="doc-updated" content="{updated}">
<meta name="doc-refs" content="">
<title>stub plan {topic}</title></head><body></body></html>
"""

ISSUE_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="issue-slug" content="stub-issue">
<meta name="issue-stamp" content="26-10-04-0800">
<meta name="issue-type" content="bug">
<meta name="doc-topic" content="t-beta">
<meta name="issue-tier" content="light">
<meta name="issue-status" content="Open">
<meta name="issue-title" content="stub issue">
<meta name="issue-summary" content="stub summary for enrich test">
<meta name="doc-refs" content="">
<title>stub issue</title></head><body></body></html>
"""

TASK_MD = """# t-beta — stub task

**Status:** In Progress
**Topics:** t-beta
**Refs:**
"""


def _stub_mb(tmp_path: Path) -> Path:
    """现造一个最小四工位 memory-bank: 3 个专题 (活跃双件 / 活跃双形态 / 全完结) + 全形态各一。"""
    mb = tmp_path / "memory-bank"
    (mb / "plans").mkdir(parents=True)
    (mb / "reports").mkdir()
    (mb / "issues").mkdir()
    (mb / "tasks").mkdir()
    (mb / "plans" / "p1.html").write_text(
        PLAN_HTML.format(topic="t-alpha", status="Open", added="26-10-01-1000", updated="26-10-03-1200"),
        encoding="utf-8",
    )
    (mb / "reports" / "r1.html").write_text(
        PLAN_HTML.format(topic="t-alpha", status="Done", added="26-10-02-0900", updated="26-10-02-0900"),
        encoding="utf-8",
    )
    (mb / "reports" / "r2.html").write_text(
        PLAN_HTML.format(topic="t-done", status="Done", added="26-09-30-1111", updated="26-09-30-1111"),
        encoding="utf-8",
    )
    (mb / "issues" / "i1.html").write_text(ISSUE_HTML, encoding="utf-8")
    (mb / "tasks" / "26-10-01-0000-t1.md").write_text(TASK_MD, encoding="utf-8")
    return mb


@pytest.fixture()
def nav_port(tmp_path: Path):
    """进程内起一份 NavServer (回环 + 随机端口, sidefx 放行), 用例收尾关闭。"""
    mb = _stub_mb(tmp_path)
    server = nav_server.NavServer(("127.0.0.1", 0), nav_server._build_handler(mb, SHELL, tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(port: int, path: str) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()
