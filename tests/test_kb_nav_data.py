"""test_kb_nav_data 测试计划: kb.nav 导航页守阵 (计划 memory-bank/plans/26-10-04-0952-plan-kb-nav-page.html §06)。

守什么: nav 数据层 / 服务层 / 页面壳的三条红线 --
1. **数据形状稳定**: collect_nav() 输出 {stamp, items, topics, counts, ext} 是壳的三视图、关系图
   与未来视图共同的数据契约, 字段一漂移前端全线静默空白; stamp 必须取数据自带的 doc-updated 最大值,
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

1'. **认领链可跳 (2026-11-07 关联图)**: 每条 ref 必须解析成五态 (ok / ext / repo / basename / dead) ——
   实测 1811 条 ref 里 578 条目标"看起来不存在", 其中 323 条其实是库内非台账件、253 条被归档搬进
   testing/baselines/attachments/、2 条在仓库根下, 真失效 0 条。解析只在导航层做, 不扩 collect() 扫描面
   (那是 kb.check / 索引生成的共同消费单点)。

另守一条**单点不回归**: nav_data 只许在 collect() 条目上做加法 enrich, 不许改
gen_doc_map.collect() 本体的键集合 —— 它是闸门/守阵消费单点 (计划 §01 拍板: 消费方零变动)。

数据一律用 tests 内桩 memory-bank 目录 (tmp_path 现造), 不依赖真实库的数量; 服务测试起在
127.0.0.1 随机端口 (tests/sidefx.py 放行回环), 不产生网络外呼; 全部进程内起线程, 不起子进程 ——
拉取端点用**桩 git 运行器** (monkeypatch nav_server._git) 测分类与编排, 同样不起子进程。

## 测试计划

- test_collect_nav_shape: collect_nav() 对桩目录返回 {stamp, items, topics, counts, ext} 完整; topics 含 live / forms; counts 覆盖四形态
- test_collect_nav_targets_four_states: 每条 ref 解析成 ok / ext / basename / dead (另有 repo 态), 归档回退命中 attachments 真实路径且只对 baselines 开头的 ref 生效
- test_collect_nav_target_guardrails: 归档回退只对 baselines 前缀生效 + 穿越路径 (memory-bank/../config.yml) 判死, 不得生成可点链接
- test_collect_nav_ext_backrefs: 库外件 (坑档) 的 Ref 反向边只收"被台账件引用到的"那批
- test_collect_nav_issue_enrich_fields: issue 条目带 issue-type / issue-tier / issue-summary; 全形态带 doc-updated (缺省回落 stamp)
- test_collect_nav_stamp_from_data_not_clock: stamp == 桩数据 doc-updated 最大值, 与当前时钟无关
- test_collect_nav_stale_hint_respects_frozen_forms: doc-age-days / doc-stale 只提示不拦截; plan/report 冻结不审, 其余按 90 天 (2026-11-05 计划 §07 P4)
- test_doc_map_collect_keys_unchanged: gen_doc_map.collect() 输出键集合不变 (enrich 不动本体)
- test_titles_and_meta_unescaped_in_data_layer: HTML 源里的实体 (issue-title / issue-summary / <title>) 在数据层反转义, 前端 esc 只转义一次 (否则 nav 显示 "-&gt;", 2026-10-31 用户报)
"""

from __future__ import annotations

import http.client

import json

import re

import shutil

import subprocess

import sys

import threading

from datetime import datetime

from pathlib import Path

import pytest

from kb_nav_support import (
    ISSUE_HTML,
    PLAN_HTML,
    TASK_MD,
    _stub_mb,
    gen_doc_map,
    nav_data,
)


def test_collect_nav_shape(tmp_path: Path) -> None:
    data = nav_data.collect_nav(_stub_mb(tmp_path))

    assert set(data) == {"stamp", "items", "topics", "counts", "ext"}, f"顶层键漂移: {sorted(data)}"
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


def test_collect_nav_targets_four_states(tmp_path: Path) -> None:
    """认领链解析 (2026-11-07 关联图的前置): 不解析就画图, 578 条边会悬空。

    四条 ref 各打一态:
      ok       = 目标在台账四类件里 (可下钻)
      ext      = 文件存在但不在台账扫描面 (坑档 / 基线 / 切片)
      basename = 声明路径失效, 按 basename 在 testing/baselines/attachments/ 找回
      dead     = 真找不到
    (第五态 repo = 文件在仓库根下但不在 memory-bank/, 导航页不代理; 桩里不造, 由真库实测覆盖)
    """
    nl = chr(10)
    mb = _stub_mb(tmp_path)
    (mb / "pitfalls" / "kb").mkdir(parents=True)
    (mb / "pitfalls" / "kb" / "note.md").write_text(nl.join(["# note", "> 摘要: 桩坑档", ""]), encoding="utf-8")
    (mb / "testing" / "baselines" / "attachments").mkdir(parents=True)
    (mb / "testing" / "baselines" / "attachments" /
     "26-10-01-0000-b1.md").write_text(nl.join(["# 26-10-01-0000 —— 归档基线", ""]), encoding="utf-8")
    refs = ", ".join(
        [
            "memory-bank/tasks/26-10-01-0000-t1.md",
            "memory-bank/pitfalls/kb/note.md",
            "memory-bank/testing/baselines/26-10-01-0000-b1.md",
            "memory-bank/reports/nope.html",
        ]
    )
    (mb / "plans" / "p2.html").write_text(
        PLAN_HTML.format(topic="t-refs", status="Open", added="26-10-06-1000", updated="26-10-06-1000").replace(
            '<meta name="doc-refs" content="">', '<meta name="doc-refs" content="%s">' % refs
        ),
        encoding="utf-8",
    )

    items = {i["link"]: i for i in nav_data.collect_nav(mb)["items"]}
    targets = items["plans/p2.html"]["targets"]
    assert [x["st"] for x in targets] == ["ok", "ext", "basename", "dead"], f"四态解析漂移: {targets}"
    assert targets[0]["t"] == "tasks/26-10-01-0000-t1.md", "ok 态必须落到台账 link (memory-bank/ 前缀已剥)"
    assert targets[0]["raw"].startswith("memory-bank/"), "raw 保留声明原值 (悬停要看它写得对不对)"
    assert targets[2]["t"] == "testing/baselines/attachments/26-10-01-0000-b1.md", "归档回退要给出真实路径"


def test_collect_nav_target_guardrails(tmp_path: Path) -> None:
    """两条围栏, 缺任一条都会把"不该能点"的东西说成能点:

    1. 归档回退只对 `memory-bank/testing/baselines/` 开头的 ref 生效 —— 否则台账件被删、attachments
       里恰好有同名切片时, 真死链会被标成「归档回退」并链到一份不相干的基线 (守卫仍判红, 页面却绿)。
    2. 穿越路径 (`memory-bank/../config.yml`) 必须判死, 不能算 `ext` 并生成可点链接 —— 那等于在
       静态导出件里给红线文件开了一扇门。
    """
    nl = chr(10)
    mb = _stub_mb(tmp_path)
    (mb / "testing" / "baselines" / "attachments").mkdir(parents=True)
    (mb / "testing" / "baselines" / "attachments" /
     "26-10-01-0000-b1.md").write_text(nl.join(["# 26-10-01-0000 —— 归档基线", ""]), encoding="utf-8")
    (tmp_path / "config.yml").write_text("redline: true" + nl, encoding="utf-8")
    refs = ", ".join([
        "memory-bank/reports/26-10-01-0000-b1.md",
        "memory-bank/../config.yml",
    ])
    (mb / "plans" / "p4.html").write_text(
        PLAN_HTML.format(topic="t-gate", status="Open", added="26-10-08-1000", updated="26-10-08-1000").replace(
            '<meta name="doc-refs" content="">', '<meta name="doc-refs" content="%s">' % refs
        ),
        encoding="utf-8",
    )

    targets = {i["link"]: i for i in nav_data.collect_nav(mb)["items"]}["plans/p4.html"]["targets"]
    assert [x["st"] for x in targets] == ["dead", "dead"], (f"围栏失效 —— 非 baselines 前缀不得回退、红线路径不得算仓库根件: {targets}")


def test_collect_nav_ext_backrefs(tmp_path: Path) -> None:
    """库外件的反向边: 坑档声明了某件, 那个件就多一条「谁认领我」。

    没有这一步, 库外件的反向引用永远是空的 —— 它们不进 DATA.items, 壳的反查只扫台账件。
    扫描面只限"已被台账件引用到的"库外件 (有界), 不扩 collect() 的全族扫描。
    """
    nl = chr(10)
    mb = _stub_mb(tmp_path)
    (mb / "pitfalls" / "kb").mkdir(parents=True)
    (mb / "pitfalls" / "kb" / "note.md").write_text(
        nl.join(["# note", "> 摘要: 桩坑档", "", "**Refs:** memory-bank/tasks/26-10-01-0000-t1.md", ""]),
        encoding="utf-8",
    )
    (mb / "plans" / "p3.html").write_text(
        PLAN_HTML.format(topic="t-ext", status="Open", added="26-10-07-1000", updated="26-10-07-1000").replace(
            '<meta name="doc-refs" content="">',
            '<meta name="doc-refs" content="memory-bank/pitfalls/kb/note.md">',
        ),
        encoding="utf-8",
    )

    data = nav_data.collect_nav(mb)
    assert data["ext"] == {"pitfalls/kb/note.md": ["tasks/26-10-01-0000-t1.md"]}, (f"库外件反向边丢了: {data['ext']}")


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


def test_titles_and_meta_unescaped_in_data_layer(tmp_path: Path) -> None:
    """HTML 源里的实体必须在数据层反转义 (gen_doc_map.collect 的标题 + nav_data enrich 的 meta):
    前端一律 esc() 当纯文本渲染, 数据层再带者 "-&gt;" 就双重转义 (2026-10-31 用户报;
    数据层反转义口径 —— 消费端 (索引/导航) 因此一直是对的)。"""
    mb = _stub_mb(tmp_path)
    (mb / "issues" / "i2.html").write_text(
        ISSUE_HTML.replace('content="stub issue"', 'content="filelock 3.32.6 -&gt; 4.2.5 升级(major)"').replace(
            'content="stub summary for enrich test"', 'content="a &lt;b&gt; &amp; c"'
        ),
        encoding="utf-8",
    )
    (mb / "plans" / "p2.html").write_text(
        PLAN_HTML.format(topic="t-esc", status="Open", added="26-10-05-1000", updated="26-10-05-1000").replace(
            "<title>stub plan t-esc</title>", "<title>x &gt; y plan</title>"
        ),
        encoding="utf-8",
    )

    items = nav_data.collect_nav(mb)["items"]
    by_link = {i["link"]: i for i in items}
    assert by_link["issues/i2.html"]["title"] == "filelock 3.32.6 -> 4.2.5 升级(major)", "issue 标题不得残留实体"
    assert by_link["issues/i2.html"]["issue-summary"] == "a <b> & c", "issue 摘要不得残留实体"
    assert by_link["plans/p2.html"]["title"] == "x > y plan", "plan <title> 不得残留实体"

    # 底层单点同验: gen_doc_map.collect() 本体 (闸门/守阵消费单点) 已反转义, nav 只是继承
    raw = {i["link"]: i for i in gen_doc_map.collect(mb)}
    assert raw["issues/i2.html"]["title"] == "filelock 3.32.6 -> 4.2.5 升级(major)"


def test_collect_nav_stamp_from_data_not_clock(tmp_path: Path) -> None:
    """stamp 是数据自带的 doc-updated 最大值 —— 混进 datetime.now() 会在静态导出与多 clone
    合并里制造"假新"戳, 这里用固定桩数据钉死期望值 (若实现取了当前时钟, 等值断言必红)。"""
    data = nav_data.collect_nav(_stub_mb(tmp_path))
    assert data["stamp"] == "26-10-04-0800", f"stamp 应取数据自带的最大 doc-updated: {data['stamp']!r}"


def test_collect_nav_stale_hint_respects_frozen_forms(tmp_path: Path) -> None:
    """陈旧度软提示 (2026-11-05 计划 26-11-05-1049 §07 P4): 只加字段、只提示。

    阈值: plan/report 出厂冻结不审; 其余 90 天 (`_common.STALE_DAYS_REFERENCE`)。
    `now` 由调用方注入 —— 测试用固定远期时钟, 不靠真墙钟。
    """
    data = nav_data.collect_nav(_stub_mb(tmp_path), now=datetime(2027, 6, 5))
    by_link = {i["link"]: i for i in data["items"]}

    old_issue = by_link["issues/i1.html"]
    assert old_issue["doc-age-days"] > 90
    assert old_issue["doc-stale"] is True, "超过 90 天的非冻结件必须给陈旧提示"

    for link in ("plans/p1.html", "reports/r1.html"):
        frozen = by_link[link]
        assert frozen["doc-age-days"] > 90, "年龄仍要如实显示 (提示依据不藏)"
        assert frozen["doc-stale"] is False, f"plan/report 冻结不审, 不得报陈旧: {link}"


def test_doc_map_collect_keys_unchanged(tmp_path: Path) -> None:
    """gen_doc_map.collect() 是闸门/守阵消费单点 (计划 §01): enrich 只许 nav 侧加字段, 本体键集合不得动。"""
    mb = _stub_mb(tmp_path)
    expected = {"form", "topic", "status", "stamp", "title", "link", "refs"}
    for item in gen_doc_map.collect(mb):
        assert set(item) == expected, f"collect() 本体键集合变了: {sorted(item)}"
