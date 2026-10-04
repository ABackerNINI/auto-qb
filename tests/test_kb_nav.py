"""kb.nav 导航页守阵 (计划 memory-bank/plans/26-10-04-0952-plan-kb-nav-page.html §06)。

守什么: nav 数据层 / 服务层 / 页面壳的三条红线 --
1. **数据形状稳定**: collect_nav() 输出 {stamp, items, topics, counts} 是壳的三视图与未来视图
   共同的数据契约, 字段一漂移前端全线静默空白; stamp 必须取数据自带的 doc-updated 最大值,
   一旦混进当前时钟, 静态导出件与多 clone 合并都会出现"假新"戳 (纪律同 gen_doc_map)。
2. **静态映射防穿越**: 「打开原文」路由 resolve 后必须严格落在 memory-bank/ 内 —— ../ 与
   %2e%2e / ..%2f / 反斜杠等变体一律 403/404, 绝不能把仓库根之外 (config.yml / auto-qb-data/)
   的文件吐给浏览器。
3. **页面壳自足**: 三视图容器与切换控件在位 (壳被误改丢了视图等于丢了用户拍板的三选三)、
   dark 口径 (conventions/webui.md)、零外链资源 (本地工具不得依赖网络)。

另守一条**单点不回归**: nav_data 只许在 collect() 条目上做加法 enrich, 不许改
gen_doc_map.collect() 本体的键集合 —— 它是闸门/守阵消费单点 (计划 §01 拍板: 消费方零变动)。

数据一律用 tests 内桩 memory-bank 目录 (tmp_path 现造), 不依赖真实库的数量; 服务测试起在
127.0.0.1 随机端口 (tests/sidefx.py 放行回环), 不产生网络外呼; 全部进程内起线程, 不起子进程。

## 测试计划

- test_collect_nav_shape: collect_nav() 对桩目录返回 {stamp, items, topics, counts} 完整; topics 含 live / forms; counts 覆盖四形态
- test_collect_nav_issue_enrich_fields: issue 条目带 issue-type / issue-tier / issue-summary; 全形态带 doc-updated (缺省回落 stamp)
- test_collect_nav_stamp_from_data_not_clock: stamp == 桩数据 doc-updated 最大值, 与当前时钟无关
- test_doc_map_collect_keys_unchanged: gen_doc_map.collect() 输出键集合不变 (enrich 不动本体)
- test_shell_has_three_views_and_switcher: 壳含三视图容器 (v-ledger / v-console / v-cards) 与 data-view 切换控件
- test_shell_is_dark: 壳含 color-scheme: dark
- test_shell_no_external_resources: 壳无 http(s) 外链 src/href 资源引用 (属性锚定, 注释/文案不受影响)
- test_static_map_serves_file_and_api: GET / 与 /api/data 200 (壳文本 / JSON 契约), 正常 memory-bank 文件 200 且 .md 给 text/plain
- test_static_map_blocks_traversal: ../ / %2e%2e / ..%2f / %5c 反斜杠变体一律 403/404 且不泄漏目标内容; 未知文件 404
- test_log_filters_polling: 精简 log —— /api/data 轮询与壳加载成功不上屏; 错误与静态映射请求留痕
"""

from __future__ import annotations

import http.client
import json
import re
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

# --------------------------------------------------------------------------- 桩 memory-bank

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


# --------------------------------------------------------------------------- collect_nav 数据形状


def test_collect_nav_shape(tmp_path: Path) -> None:
    data = nav_data.collect_nav(_stub_mb(tmp_path))

    assert set(data) == {"stamp", "items", "topics", "counts"}, f"顶层键漂移: {sorted(data)}"
    assert len(data["items"]) == 5, "桩目录应有 5 件 (1 plan + 2 report + 1 issue + 1 task)"

    by_topic = {t["topic"]: t for t in data["topics"]}
    assert set(by_topic) == {"t-alpha", "t-beta", "t-done"}
    assert by_topic["t-alpha"]["live"] and by_topic["t-beta"]["live"], "有未完结件的专题必须判活跃"
    assert not by_topic["t-done"]["live"], "全完结专题 (Done) 必须判不活跃 (口径同 gen_doc_map.is_live)"
    assert by_topic["t-alpha"]["forms"] == ["plan", "report"], "forms 按 FORM_ORDER 定序"
    assert by_topic["t-beta"]["forms"] == ["issue", "task"]

    assert set(data["counts"]) == set(gen_doc_map.FORM_ORDER), "counts 必须覆盖四形态键"
    assert data["counts"]["plan"] == {"Open": 1}
    assert data["counts"]["report"] == {"Done": 2}
    assert data["counts"]["issue"] == {"Open": 1}
    assert data["counts"]["task"] == {"In Progress": 1}


def test_collect_nav_issue_enrich_fields(tmp_path: Path) -> None:
    items = nav_data.collect_nav(_stub_mb(tmp_path))["items"]
    by_link = {i["link"]: i for i in items}

    issue = by_link["issues/i1.html"]
    assert issue["issue-type"] == "bug"
    assert issue["issue-tier"] == "light"
    assert issue["issue-summary"] == "stub summary for enrich test"

    # doc-updated: HTML 有 meta 用 meta, 没有回落条目 stamp (issue 侧不写 doc-updated)
    assert by_link["plans/p1.html"]["doc-updated"] == "26-10-03-1200"
    assert issue["doc-updated"] == "26-10-04-0800"


def test_collect_nav_stamp_from_data_not_clock(tmp_path: Path) -> None:
    """stamp 是数据自带的 doc-updated 最大值 —— 混进 datetime.now() 会在静态导出与多 clone
    合并里制造"假新"戳, 这里用固定桩数据钉死期望值 (若实现取了当前时钟, 等值断言必红)。"""
    data = nav_data.collect_nav(_stub_mb(tmp_path))
    assert data["stamp"] == "26-10-04-0800", f"stamp 应取数据自带的最大 doc-updated: {data['stamp']!r}"


def test_doc_map_collect_keys_unchanged(tmp_path: Path) -> None:
    """gen_doc_map.collect() 是闸门/守阵消费单点 (计划 §01): enrich 只许 nav 侧加字段, 本体键集合不得动。"""
    mb = _stub_mb(tmp_path)
    expected = {"form", "topic", "status", "stamp", "title", "link", "refs"}
    for item in gen_doc_map.collect(mb):
        assert set(item) == expected, f"collect() 本体键集合变了: {sorted(item)}"


# --------------------------------------------------------------------------- 页面壳完整


def test_shell_has_three_views_and_switcher() -> None:
    text = SHELL.read_text(encoding="utf-8")
    for view in ("ledger", "console", "cards"):
        assert f'id="v-{view}"' in text, f"缺视图容器 v-{view} (三视图并存是用户拍板, 丢一个即回归)"
        assert f'data-view="{view}"' in text, f"缺 {view} 的切换控件"
    assert text.count('class="view') >= 3, "三视图容器应各自独立成 section (切换零重建)"


def test_shell_is_dark() -> None:
    assert "color-scheme: dark" in SHELL.read_text(encoding="utf-8"), "壳必须 dark 口径 (conventions/webui.md)"


def test_shell_no_external_resources() -> None:
    """本地工具不得依赖网络: 锚定**资源属性** (src/href = http...) 判定, 注释与文案里提到 URL 不算。"""
    text = SHELL.read_text(encoding="utf-8")
    external = re.findall(r"""(?:\ssrc|\shref)\s*=\s*["']https?://[^"']*""", text)
    assert not external, f"壳里出现外链资源引用 (本地工具禁止网络依赖): {external[:5]}"


# --------------------------------------------------------------------------- 服务层 (127.0.0.1 随机端口)


@pytest.fixture()
def nav_port(tmp_path: Path):
    """进程内起一份 NavServer (回环 + 随机端口, sidefx 放行), 用例收尾关闭。"""
    mb = _stub_mb(tmp_path)
    server = nav_server.NavServer(("127.0.0.1", 0), nav_server._build_handler(mb, SHELL))
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


def test_static_map_serves_file_and_api(nav_port: int) -> None:
    code, body = _get(nav_port, "/")
    assert code == 200 and b"v-ledger" in body, "GET / 必须返回页面壳"

    code, body = _get(nav_port, "/api/data")
    assert code == 200
    data = json.loads(body.decode("utf-8"))
    assert set(data) == {"stamp", "items", "topics", "counts"}, "/api/data 契约与 collect_nav 顶层键必须一致"

    code, body = _get(nav_port, "/memory-bank/tasks/26-10-01-0000-t1.md")
    assert code == 200 and "Topics" in body.decode("utf-8"), "静态映射应能取到四工位原文"


def test_static_map_blocks_traversal(nav_port: int) -> None:
    """防穿越是本路由的硬红线 (计划 §03「测试钉死」): 所有已知编码/分隔符变体一律 403/404,
    且响应体不得含越界目标的任何内容。"""
    variants = (
        "/memory-bank/../config.yml",  # 明文 ..
        "/memory-bank/%2e%2e/config.yml",  # 点 URL 编码
        "/memory-bank/..%2fconfig.yml",  # 斜杠 URL 编码
        "/memory-bank/%2e%2e%5cconfig.yml",  # 反斜杠 URL 编码
        "/memory-bank/..\\config.yml",  # 明文反斜杠 (Windows 下是真实分隔符)
    )
    for path in variants:
        code, body = _get(nav_port, path)
        assert code in (403, 404), f"{path} 越界变体被放行 (HTTP {code})"
        assert b"doc-topic" not in body and b"[pack]" not in body, f"{path} 响应泄漏了越界文件内容"

    code, _body = _get(nav_port, "/memory-bank/no-such-file.html")
    assert code == 404, "库内不存在的文件应 404 (不是 403 —— 区分越界与缺失)"


def test_log_filters_polling(nav_port: int, capsys) -> None:
    """精简 log (26-10-04 用户定调: log 数量不需要多): /api/data 是 30s 轮询、/ 是壳加载 ——
    成功时不上屏; 错误与其余请求 (如静态映射) 留痕, 常驻期间 stderr 可读。"""
    _get(nav_port, "/")
    _get(nav_port, "/api/data")
    _get(nav_port, "/memory-bank/tasks/26-10-01-0000-t1.md")
    _get(nav_port, "/nope")
    err = capsys.readouterr().err
    assert "GET /api/data" not in err, "/api/data 轮询成功必须被过滤, 否则常驻 log 被刷屏"
    assert "GET / HTTP/1.1" not in err, "壳加载成功不必留痕"
    assert "404" in err and "GET /nope" in err, "错误请求要留痕"
    assert "GET /memory-bank/tasks/26-10-01-0000-t1.md" in err, "静态映射请求要留痕"
