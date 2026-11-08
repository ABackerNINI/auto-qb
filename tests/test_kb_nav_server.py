"""test_kb_nav_server 测试计划: kb.nav 导航页守阵 (计划 memory-bank/plans/26-10-04-0952-plan-kb-nav-page.html §06)。

守什么: nav 数据层 / 服务层 / 页面壳的三条红线 --
1. **数据形状稳定**: collect_nav() 输出 {stamp, items, topics, counts} 是壳的三视图与未来视图
   共同的数据契约, 字段一漂移前端全线静默空白; stamp 必须取数据自带的 doc-updated 最大值,
   一旦混进当前时钟, 静态导出件与多 clone 合并都会出现"假新"戳 (纪律同 gen_doc_map)。
2. **静态映射防穿越**: 「打开原文」路由 resolve 后必须严格落在 memory-bank/ 内 —— ../ 与
   %2e%2e / ..%2f / 反斜杠等变体一律 403/404, 绝不能把仓库根之外 (config.yml / auto-qb-data/)
   的文件吐给浏览器。
3. **页面壳自足**: 三视图容器与切换控件在位 (壳被误改丢了视图等于丢了用户拍板的三选三)、
   dark 口径 (conventions/webui.md)、零外链资源 (本地工具不得依赖网络)。
3'. **台账可读性**: 状态列钉在形态右侧、标题左侧 (2026-10-04 用户定调); 状态筛选不得被 30s
   轮询重播种 (同日用户报「状态筛选器每隔一会儿自动重置」, 根因见 pitfalls/web-ui/poll-reseed-filter.md)。
3''. **筛选器持久化**: 筛选 / 选择类状态 (台账四组 + 排序 + 双搜索 + 卡片三组 + 展开态) 落
   localStorage, 刷新后不丢 (2026-10-05 用户报「每次刷新重置」); 装载点全壳唯一且在 boot, derive()
   绝不读写 —— 否则 30s 轮询会把用户改的筛选洗掉 (与 pin 同源)。还原须对 schema 校验 (见
   pitfalls/web-ui/ui-location-persist.md), 且已知状态先并入 statusSeeded 台账, 否则刷新后首轮
   derive() 会把用户取消过的已知状态又加回来 (与 3' 同一根因)。
3'''''. **列标题行可分辨**: 台账列头 (时间戳 / 形态 / 状态 / 标题 …) 底色必须与数据行**和**工具栏
   两面都拉开可测的明度差 (2026-10-05 用户报「kb.nav 标题栏颜色与其余部分难区分」, 澄清后
   = 这一行列头)。列头曾与数据行共用 --bg ⇒ 逐通道差 0。
3''''. **顶栏保持原样**: 顶栏底色必须**留在 `--paper`** —— 用户 2026-10-05 明确撤销了顶栏配色改动
   (排查途中把"标题栏"误认成顶栏、改了一版, 澄清后按范围守恒撤销)。顶栏与侧栏 / 工具栏确实
   逐通道差 0 (同款缺陷), 但用户知情后选择不动, 所以本条**反着守** (改了就是越界, 停下来问)。
   修法口径仍留在 pitfalls/web-ui/layout-css.md 同名条。
3'''. **状态色可读**: 状态徽章底色 + 文字色必须一眼可分 (2026-10-05 用户报「open/done 状态底色相近」)。
   两个坑: 1. `.chip{color:var(--dim)}` 与 `.chip.st-*` 同特异性且写在更靠后, 会把状态文字色整个盖掉
   (改前实测五个状态 chip 文字全是 --dim 灰); 2. cyan / green 两个令牌亮度几乎相同, 同透明度时底色
   实测 #16272b vs #1b2624 肉眼不可分 —— 光换色相没用, 必须靠**明度 (alpha)** 拉开。

另守一条**单点不回归**: nav_data 只许在 collect() 条目上做加法 enrich, 不许改
gen_doc_map.collect() 本体的键集合 —— 它是闸门/守阵消费单点 (计划 §01 拍板: 消费方零变动)。

数据一律用 tests 内桩 memory-bank 目录 (tmp_path 现造), 不依赖真实库的数量; 服务测试起在
127.0.0.1 随机端口 (tests/sidefx.py 放行回环), 不产生网络外呼; 全部进程内起线程, 不起子进程 ——
拉取端点用**桩 git 运行器** (monkeypatch nav_server._git) 测分类与编排, 同样不起子进程。

## 测试计划

- test_static_map_serves_file_and_api: GET / 与 /api/data 200 (壳文本 / JSON 契约), 正常 memory-bank 文件 200 且 .md 给 text/plain
- test_static_map_blocks_traversal: ../ / %2e%2e / ..%2f / %5c 反斜杠变体一律 403/404 且不泄漏目标内容; 未知文件 404
- test_classify_pull_cases: 仅快进分类 (up-to-date / fast-forward / ahead-only / diverged) 纯逻辑钉死
- test_pull_ff_only_rejects_non_repo: 非 git 工作树 → 失败
- test_pull_ff_only_rejects_detached_head: 游离 HEAD → 失败
- test_pull_ff_only_offline_reports_unreachable: ls-remote 拿不到远端 → 失败(离线提示)
- test_pull_ff_only_diverged_refuses_without_merge: 分叉 → 失败, 且**绝不执行 merge**(仅快进口径)
- test_pull_ff_only_ahead_only_is_noop: 本地领先(未推送) → 成功且不执行 merge
- test_pull_ff_only_fast_forwards: 纯落后 → merge --ff-only, 回报新 HEAD
- test_pull_endpoint_requires_action_header: 缺 / 错 X-Nav-Action 头 → 403 (CSRF 护栏)
- test_pull_endpoint_rejects_non_pull_routes: GET /api/pull 与 POST 未知路径 → 404
- test_pull_endpoint_reports_result: 带头 → 200 + {ok, message} 原样回传
- test_graph_route_serves_component: GET /nav_graph.js 200 + javascript (关系图组件 2026-11-07 拆分后按路由发货)
- test_gen_static_inlines_graph_and_prefix: --gen-static 落地件是**单文件** (组件内联、无 src 引用) 且链接前缀按 out_dir 实际深度现算
"""

from __future__ import annotations

import http.client

import json

import os

import re

import shutil

import subprocess

import sys

import threading

from pathlib import Path

import pytest

from kb_nav_support import (
    ISSUE_HTML,
    PLAN_HTML,
    SHELL,
    TASK_MD,
    _get,
    _stub_mb,
    nav_port,
    nav_server,
)


def _post(port: int, path: str, headers: dict | None = None) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("POST", path, body=b"", headers=headers or {})
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
    assert set(data) == {"stamp", "items", "topics", "counts", "ext"}, "/api/data 契约与 collect_nav 顶层键必须一致"

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


def _proc(rc: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, out, err)


def _fake_git(handlers: dict):
    """桩 git 运行器: 按命令前缀分发 (值可为 CompletedProcess 或 `args -> CompletedProcess`), 记录调用。"""
    calls: list[tuple] = []

    def runner(root, *args):
        calls.append(args)
        for key, resp in handlers.items():
            if args[:len(key)] == key:
                return resp if isinstance(resp, subprocess.CompletedProcess) else resp(args)
        raise AssertionError("未预期的 git 调用: %r" % (args, ))

    return runner, calls


def test_classify_pull_cases() -> None:
    """仅快进分类纯逻辑: 齐平 / 纯落后 / 本地领先 / 分叉 —— 只有纯落后才允许 merge --ff-only。"""
    a, b = "a" * 40, "b" * 40
    assert nav_server.classify_pull(a, a, 0, 0) == "up-to-date"
    assert nav_server.classify_pull(a, b, 3, 0) == "fast-forward"
    assert nav_server.classify_pull(a, b, 0, 2) == "ahead-only"
    assert nav_server.classify_pull(a, b, 2, 3) == "diverged"


def test_pull_ff_only_rejects_non_repo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(nav_server, "_git", lambda root, *a: _proc(1, "", "fatal: not a git repository"))
    ok, msg = nav_server.pull_ff_only(tmp_path)
    assert ok is False and "git 工作树" in msg


def test_pull_ff_only_rejects_detached_head(tmp_path: Path, monkeypatch) -> None:
    runner, _ = _fake_git(
        {
            ("rev-parse", "--is-inside-work-tree"): _proc(0, "true\n"),
            ("remote", ): _proc(0, "origin\n"),
            ("rev-parse", "--abbrev-ref", "HEAD"): _proc(0, "HEAD\n"),
        }
    )
    monkeypatch.setattr(nav_server, "_git", runner)
    ok, msg = nav_server.pull_ff_only(tmp_path)
    assert ok is False and "游离 HEAD" in msg


def test_pull_ff_only_offline_reports_unreachable(tmp_path: Path, monkeypatch) -> None:
    """远端不可达: fetch 失败 + ls-remote 空 → 报离线; 远端名按 gitee 优先挑出。"""
    runner, _ = _fake_git(
        {
            ("rev-parse", "--is-inside-work-tree"): _proc(0, "true\n"),
            ("remote", ): _proc(0, "gitee\norigin\n"),
            ("rev-parse", "--abbrev-ref", "HEAD"): _proc(0, "develop\n"),
            ("fetch", ): _proc(1, "", "fatal: unable to access"),
            ("ls-remote", ): _proc(0, ""),
        }
    )
    monkeypatch.setattr(nav_server, "_git", runner)
    ok, msg = nav_server.pull_ff_only(tmp_path)
    assert ok is False and "拿不到远端" in msg and "gitee" in msg


def test_pull_ff_only_diverged_refuses_without_merge(tmp_path: Path, monkeypatch) -> None:
    """仅快进口径的硬红线: 分叉时**绝不**执行 merge (不 rebase / 不生成 merge commit), 交人处理。"""
    runner, calls = _fake_git(
        {
            ("rev-parse", "--is-inside-work-tree"): _proc(0, "true\n"),
            ("remote", ): _proc(0, "origin\n"),
            ("rev-parse", "--abbrev-ref", "HEAD"): _proc(0, "develop\n"),
            ("fetch", ): _proc(0, ""),
            ("ls-remote", ): _proc(0, "b" * 40 + "\trefs/heads/develop\n"),
            ("rev-parse", "HEAD"): _proc(0, "a" * 40 + "\n"),
            ("rev-list", ): _proc(0, "2\t3\n"),
        }
    )
    monkeypatch.setattr(nav_server, "_git", runner)
    ok, msg = nav_server.pull_ff_only(tmp_path)
    assert ok is False and "分叉" in msg
    assert not any(call and call[0] == "merge" for call in calls), "分叉时绝不能执行 merge"


def test_pull_ff_only_ahead_only_is_noop(tmp_path: Path, monkeypatch) -> None:
    runner, calls = _fake_git(
        {
            ("rev-parse", "--is-inside-work-tree"): _proc(0, "true\n"),
            ("remote", ): _proc(0, "origin\n"),
            ("rev-parse", "--abbrev-ref", "HEAD"): _proc(0, "develop\n"),
            ("fetch", ): _proc(0, ""),
            ("ls-remote", ): _proc(0, "b" * 40 + "\trefs/heads/develop\n"),
            ("rev-parse", "HEAD"): _proc(0, "a" * 40 + "\n"),
            ("rev-list", ): _proc(0, "0\t4\n"),
        }
    )
    monkeypatch.setattr(nav_server, "_git", runner)
    ok, msg = nav_server.pull_ff_only(tmp_path)
    assert ok is True and "无需拉取" in msg
    assert not any(call and call[0] == "merge" for call in calls), "本地领先不该 merge"


def test_pull_ff_only_fast_forwards(tmp_path: Path, monkeypatch) -> None:
    state = {"head": "a" * 40}
    remote = "b" * 40

    def merge(args):
        state["head"] = args[2]  # merge --ff-only <rsha>
        return _proc(0, "")

    runner, _ = _fake_git(
        {
            ("rev-parse", "--is-inside-work-tree"): _proc(0, "true\n"),
            ("remote", ): _proc(0, "origin\n"),
            ("rev-parse", "--abbrev-ref", "HEAD"): _proc(0, "develop\n"),
            ("fetch", ): _proc(0, ""),
            ("ls-remote", ): _proc(0, remote + "\trefs/heads/develop\n"),
            ("rev-parse", "HEAD"): lambda args: _proc(0, state["head"] + "\n"),
            ("rev-list", ): _proc(0, "1\t0\n"),
            ("merge", ): merge,
        }
    )
    monkeypatch.setattr(nav_server, "_git", runner)
    ok, msg = nav_server.pull_ff_only(tmp_path)
    assert ok is True and "已快进到" in msg and remote[:8] in msg


def test_pull_endpoint_requires_action_header(nav_port: int) -> None:
    """CSRF 护栏: 无自定义头 / 头值不对一律 403 —— 跨站 fetch 带自定义头会先触发 OPTIONS 预检,
    本服务不实现 do_OPTIONS, 浏览器因此拿不到放行 (同源页面带该头不触发预检, 不受影响)。"""
    for headers in ({}, {nav_server.PULL_HEADER: "nope"}):
        code, _body = _post(nav_port, "/api/pull", headers)
        assert code == 403, f"缺 / 错 {nav_server.PULL_HEADER} 头应 403, 得到 {code}"


def test_pull_endpoint_rejects_non_pull_routes(nav_port: int) -> None:
    code, _ = _get(nav_port, "/api/pull")
    assert code == 404, "GET /api/pull 不该被受理 (拉取是 POST 动作)"
    code, _ = _post(nav_port, "/api/nope", {nav_server.PULL_HEADER: "pull"})
    assert code == 404, "未知 POST 路径应 404"


def test_pull_endpoint_reports_result(nav_port: int, monkeypatch) -> None:
    """带头 → 200 + {ok, message}; 服务把 pull_ff_only 的业务结果原样回给前端 (业务失败也是 200)。"""
    monkeypatch.setattr(nav_server, "pull_ff_only", lambda root: (False, "本地已分叉 (领先 1 / 落后 2) —— 仅快进"))
    code, body = _post(nav_port, "/api/pull", {nav_server.PULL_HEADER: "pull"})
    assert code == 200
    data = json.loads(body.decode("utf-8"))
    assert data["ok"] is False and "分叉" in data["message"]

    monkeypatch.setattr(nav_server, "pull_ff_only", lambda root: (True, "已快进到 deadbeef"))
    code, body = _post(nav_port, "/api/pull", {nav_server.PULL_HEADER: "pull"})
    assert code == 200 and json.loads(body.decode("utf-8")) == {"ok": True, "message": "已快进到 deadbeef"}


def test_graph_route_serves_component(nav_port: int) -> None:
    """关系图组件从壳里拆出来 (2026-11-07) 后按路由发货: 服务模式必须能拿到它, 否则抽屉里那块永远空白。"""
    status, body = _get(nav_port, "/nav_graph.js")
    assert status == 200, f"GET /nav_graph.js 应为 200: {status}"
    assert b"MBGraph" in body, "返回的不是关系图组件"
    assert b"<script" not in body[:200], "路由吐回了壳? 组件请求必须拿 js"


def test_gen_static_inlines_graph_and_prefix(tmp_path: Path) -> None:
    """静态导出件必须仍是**单文件** (组件内联, 无 src 引用), 且链接前缀按输出目录实际深度现算 ——
    前缀写死 "../../memory-bank/" 时只有导出到仓库根下两级才碰巧对, 换个目录所有链接都算到仓库外。"""
    mb = _stub_mb(tmp_path)
    out = tmp_path / "x" / "y" / "z"
    assert nav_server.gen_static(mb, SHELL, out) == 0
    html = (out / "nav_page.html").read_text(encoding="utf-8")
    assert 'src="nav_graph.js"' not in html, "静态件仍是两文件: file:// 打开时组件拉不到, 抽屉图直接空白"
    assert "window.MBGraph = { mount" in html, "组件没内联进静态件 (壳里也有 window.MBGraph 的判断, 拿它断言恒真)"
    prefix = os.path.relpath(mb, out).replace(os.sep, "/").rstrip("/") + "/"
    assert ('"%s"' % prefix) in html, f"链接前缀没按输出目录深度现算 (期望 {prefix})"
    assert '"../../memory-bank/"' not in html, "默认前缀还写死在产物里 —— 换目录导出会让所有链接算到仓库外"
