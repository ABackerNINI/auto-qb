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
   两个坑: ①`.chip{color:var(--dim)}` 与 `.chip.st-*` 同特异性且写在更靠后, 会把状态文字色整个盖掉
   (改前实测五个状态 chip 文字全是 --dim 灰); ②cyan / green 两个令牌亮度几乎相同, 同透明度时底色
   实测 #16272b vs #1b2624 肉眼不可分 —— 光换色相没用, 必须靠**明度 (alpha)** 拉开。

另守一条**单点不回归**: nav_data 只许在 collect() 条目上做加法 enrich, 不许改
gen_doc_map.collect() 本体的键集合 —— 它是闸门/守阵消费单点 (计划 §01 拍板: 消费方零变动)。

数据一律用 tests 内桩 memory-bank 目录 (tmp_path 现造), 不依赖真实库的数量; 服务测试起在
127.0.0.1 随机端口 (tests/sidefx.py 放行回环), 不产生网络外呼; 全部进程内起线程, 不起子进程 ——
拉取端点用**桩 git 运行器** (monkeypatch nav_server._git) 测分类与编排, 同样不起子进程。

## 测试计划

- test_collect_nav_shape: collect_nav() 对桩目录返回 {stamp, items, topics, counts} 完整; topics 含 live / forms; counts 覆盖四形态
- test_collect_nav_issue_enrich_fields: issue 条目带 issue-type / issue-tier / issue-summary; 全形态带 doc-updated (缺省回落 stamp)
- test_collect_nav_stamp_from_data_not_clock: stamp == 桩数据 doc-updated 最大值, 与当前时钟无关
- test_doc_map_collect_keys_unchanged: gen_doc_map.collect() 输出键集合不变 (enrich 不动本体)
- test_shell_has_three_views_and_switcher: 壳含三视图容器 (v-ledger / v-console / v-cards) 与 data-view 切换控件
- test_shell_is_dark: 壳含 color-scheme: dark
- test_shell_no_external_resources: 壳无 http(s) 外链 src/href 资源引用 (属性锚定, 注释/文案不受影响)
- test_ledger_status_column_between_form_and_title: 台账列序 # 时间戳 形态 状态 标题 专题 链 (表头与共用行模板 ledgerCells 同步)
- test_status_badge_colors_distinguishable: 状态徽章文字色写在 .chip.st-* 上 (不被同特异性的 .chip --dim 盖掉) + Open/Done 底色 alpha 必须不同 (同亮度令牌只能靠明度拉开) + 控制台 .rs 与台账同口径 + 出局态无底
- test_topbar_surface_is_left_at_paper: 顶栏底色必须留在 --paper (2026-10-05 用户撤销了顶栏配色改动; 改了即越界, 先问用户)
- test_ledger_thead_surface_distinguishable: 列标题行底色不得借回 --bg / --paper / --paper-2 + 与数据行 (--bg) 和工具栏 (--paper) 两面最大通道差均 >= 24 + 表头文字对比度 >= 4.5:1 + 置顶专区表头与主表表头同一枚令牌 + 专区表头与置顶行**合成色**最大通道差 >= 24
- test_status_filter_not_reseeded_every_poll: derive() 对状态候选只自动入选一次 (statusSeeded 闸门在前), 30s 轮询不得盖回用户取消的选择
- test_shell_has_filter_persistence: 筛选器持久化骨架 (FILTERS_KEY + 存/读/还原三函数 + boot 装载一次 + 输入框/下拉回填初值)
- test_filter_state_not_reseeded_on_poll: derive() 不得读写筛选器持久化 (与 pin 同源: 轮询不得洗掉用户筛选)
- test_restore_filters_seeds_known_statuses: 还原筛选器时已知状态 (KNOWN_ST) 先并入 statusSeeded 台账 (否则刷新后首轮 derive 把取消的已知状态加回)
- test_filter_mutations_persist: 各筛选入口 (台账四组 / 排序 / 双搜索 / 卡片三组) 均落盘, 少一处即该筛选刷新后仍旧重置
- test_shell_has_pin_zone_and_ctxmenu: 置顶骨架在位 (#pinZone / #ctxMenu / PINS_KEY / contextmenu 监听)
- test_pin_state_not_reseeded_by_derive: derive() 不碰 pins; S.pins = loadPins() 全壳唯一 (轮询不得洗掉 pin)
- test_pinned_rendered_in_both_zones: 同一份 pin 状态被专区渲染 (pinZoneItems) 与共用行模板 (isPinned) 双处消费
- test_pin_zone_reuses_ledger_columns: 置顶专区与主表**同栏** —— 列定义单点 (全壳仅一处表头) + 克隆主表 thead + 共用 ledgerCells
- test_pin_icon_is_inline_svg_no_emoji: 图钉为内联 SVG (无外链图标库), 且壳内无 emoji 图钉字符 (code-style)
- test_static_map_serves_file_and_api: GET / 与 /api/data 200 (壳文本 / JSON 契约), 正常 memory-bank 文件 200 且 .md 给 text/plain
- test_static_map_blocks_traversal: ../ / %2e%2e / ..%2f / %5c 反斜杠变体一律 403/404 且不泄漏目标内容; 未知文件 404
- test_log_filters_polling: 精简 log —— /api/data 轮询与壳加载成功不上屏; 错误与静态映射请求留痕
- test_shell_has_pull_button: 壳含拉取按钮 + POST /api/pull + CSRF 自定义头 + 静态/file 模式隐藏; doPull 成功刷新 / 失败提示
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
"""

from __future__ import annotations

import http.client
import json
import re
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

# --------------------------------------------------------------------------- 壳 CSS 取值小工具
# 颜色可分辨类守阵共用 (顶栏 / 列标题行 / 状态徽章): 一律**按令牌真值算**, 不写死颜色常量 ——
# 换色只改壳里的令牌, 守阵自动跟着走。判据见 pitfalls/web-ui/layout-css.md
# (同视图内两两 RGB 最大通道差 <20 即"分不出"; 文字另按 WCAG 对比度 4.5:1 起)。


def _shell_css() -> str:
    """壳的 CSS 文本, 已去注释 (免得注释里的示例选择器被当成规则)。"""
    return re.sub(r"/\*.*?\*/", "", SHELL.read_text(encoding="utf-8"), flags=re.S)


def _rule(css: str, sel: str) -> str:
    m = re.search(re.escape(sel) + r"[^{}]*\{([^}]*)\}", css)
    assert m, f"{sel} 规则不见了? 改版要同步本守阵"
    return m.group(1)


def _hex_token(css: str, name: str) -> tuple[int, int, int]:
    m = re.search(re.escape(name) + r"\s*:\s*#([0-9a-fA-F]{6})", css)
    assert m, f"令牌 {name} 不见了 (或不再是 6 位 hex, 本守阵只认 hex)"
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _bg_token(body: str) -> str:
    m = re.search(r"background:\s*var\((--[a-z0-9-]+)\)", body)
    assert m, f"background 不是显式令牌 (解析不了就守不住): {body!r}"
    return m.group(1)


def _color_token(body: str) -> str:
    m = re.search(r"[^-]color:\s*var\((--[a-z0-9-]+)\)", body)
    assert m, f"没写 color 令牌 (解析不了就守不住): {body!r}"
    return m.group(1)


def _max_channel_diff(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return max(abs(a[i] - b[i]) for i in range(3))


def _rel_lum(c: tuple[int, int, int]) -> float:
    def f(v: int) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055)**2.4

    r, g, b = (f(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = _rel_lum(a), _rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


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


def test_ledger_status_column_between_form_and_title() -> None:
    """台账列序 (用户 2026-10-04 定调): 状态挨着形态、在标题左侧 —— 塞到专题右边要横向拖
    才能看见, 等于没有。表头与**共用行模板** ledgerCells 必须同步改: 只改一头会让整行数据
    错位一列 (主表与置顶专区共用 ledgerCells, 栏序单点即在此)。"""
    text = SHELL.read_text(encoding="utf-8")

    head = re.search(r"<thead><tr>(.*?)</tr></thead>", text, re.S)
    assert head, "台账表头不见了? 表格结构搬家要同步本守阵"
    cols = [c.strip() for c in re.findall(r"<th[^>]*>([^<]*)</th>", head.group(1))]
    assert cols[:3] == ["#", "时间戳", "形态"], f"前三列变了: {cols}"
    assert cols.index("状态") == cols.index("形态") + 1, f"状态列必须在形态右侧: {cols}"
    assert cols.index("状态") < cols.index("标题"), f"状态列必须在标题左侧: {cols}"

    body = re.search(r'<tbody id="aRows">', text)
    assert body, "台账行容器不见了"
    row = re.search(r"function ledgerCells\(.*?\) \{(.*?)\n\}", text, re.S)
    assert row, "行模板 (ledgerCells) 不见了? 渲染方式变了要同步本守阵"
    cells = re.findall(r'<td class="([a-z-]+)"', row.group(1))
    assert cells == ["idx", "stamp", "formc", "statc", "title-cell", "topic", "refs"], f"行模板列序漂移: {cells}"


def test_status_badge_colors_distinguishable() -> None:
    """状态徽章 (台账 .chip.st-* / 控制台 .rs.st-*) 的底色与文字色必须一眼可分 ——
    2026-10-05 用户报「open/done 状态底色相近, 需要优化」。两条红线:

    1. **文字色必须落在 `.chip.st-*` 上**: 它与 `.chip { color: var(--dim) }` 同特异性 (0,1,0),
       而后者在壳里写得更靠后 —— 只靠 `.st-*` 那条会被盖掉 (改前实测五个状态 chip 文字全成
       --dim 灰, 状态色白给, 与 pitfalls/web-ui/layout-css.md「例外色别靠书写顺序赢」同源)。
    2. **Open 与 Done 的底色不能同透明度**: cyan / green 两个令牌亮度几乎相同, 同样 12% 时实测
       底色 #16272b vs #1b2624, 肉眼不可分 —— 只换色相没用, 必须靠明度 (alpha) 拉开;
       方向固定: Open (待关注) 比 Done (已收口) 实, Done 比出局态 (无底) 实。
    """
    css = _shell_css()

    def rule(sel: str) -> str:
        return _rule(css, sel)

    def alpha(body: str) -> float | None:
        m = re.search(r"background:\s*rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)", body)
        return float(m.group(1)) if m else None

    for st in ("Open", "InProgress", "Done"):
        body = rule(f".chip.st-{st}")
        assert "color:" in body, (f".chip.st-{st} 没写 color —— 会被同特异性的 .chip{{color:var(--dim)}} 盖掉, 状态色白给")
        assert alpha(body) is not None, f".chip.st-{st} 的底色不是显式 rgba: {body!r}"

    a_open, a_done = alpha(rule(".chip.st-Open")), alpha(rule(".chip.st-Done"))
    assert a_open != a_done, (
        f"Open / Done 底色用了同一个透明度 ({a_open}) —— cyan 与 green 令牌亮度几乎相同, "
        "暗底上只换色相分不出来, 必须靠明度 (alpha) 拉开"
    )
    assert a_open > a_done, f"Open (待关注) 应比 Done (已收口) 更实: {a_open} vs {a_done}"

    # 出局态一律无底, 靠文字色区分; 也保证 Done 的"有底"有对照物
    for sel in (".chip.st-Dropped", ".rs.st-Dropped"):
        assert "background: transparent" in rule(sel), f"{sel} 应为无底 (出局态)"

    # 控制台状态条与台账 chip 同一套口径: 只定底, 透明度逐档对齐 (文字色由 .st-* 给)
    for st in ("Open", "InProgress", "Done"):
        assert alpha(rule(f".rs.st-{st}")) == alpha(rule(f".chip.st-{st}")
                                                   ), (f"控制台 .rs.st-{st} 与台账 .chip.st-{st} 底色透明度不一致 —— 两视图状态口径必须同一套")


def test_topbar_surface_is_left_at_paper() -> None:
    """顶栏底色必须**留在 `--paper`** —— 这是用户 2026-10-05 拍板的现状, 不是待修项。

    来龙去脉: 用户当轮报的「标题栏颜色与其余部分难区分」经澄清指的是**台账列标题行** (见下一条),
    排查途中我先误认成顶栏并改了一版 (底色换专用令牌 + 下缘 cyan 缝), 澄清后用户明确要求撤销。
    撤销 ≠ 缺陷消失 —— 实测事实是: 顶栏与台账左侧栏 / 工具栏逐通道差 **0** (三处共用 `--paper`),
    与表格区 `--bg` 只差 **7**, 按判据 (<20 即"分不出") 两条都不合格。用户知情后仍选择保持原样
    (范围守恒), 所以本条**反着守**: 顶栏底色一旦不再是 `--paper`, 就说明有人又"顺手"改了,
    先停下来问用户, 别自己决定。真要修时的口径见 pitfalls/web-ui/layout-css.md 同名条。
    """
    body = _rule(_shell_css(), ".topbar")
    assert _bg_token(body) == "--paper", (
        f"顶栏底色不再是 --paper ({_bg_token(body)}) —— 2026-10-05 用户明确要求撤销顶栏配色改动、"
        "保持与侧栏 / 工具栏同色的现状。要改先问用户 (口径见 pitfalls/web-ui/layout-css.md)"
    )


def test_ledger_thead_surface_distinguishable() -> None:
    """台账**列标题行** (时间戳 / 形态 / 状态 / 标题 …) 的底色必须与相邻两面都拉开可测的明度差
    —— 2026-10-05 用户报「kb.nav 标题栏颜色与其余部分难区分」(经澄清 = 这一行列头, 不是顶栏)。

    改前实测 (headless 截元素图取众数填充色): 列头 #0e1114 与数据行**逐通道差 0** (两处都是
    --bg), 与紧挨其上的 .toolbar (--paper) 只差 7 —— 按判据 (<20 即"分不出") 两条都不合格,
    列头读不出"这是一行表头", 只剩一条 hairline。

    四条红线:
    1. 底色不许再用 --bg / --paper / --paper-2 —— --bg 是数据行本身, --paper-2 与数据行只差 16;
    2. 与数据行 (--bg) 最大通道差 >= 24;
    3. 与工具栏 (--paper) 最大通道差 >= 24 —— 只满足第 2 条的话列头会看着像工具栏的延伸
       (--paper-3 正是这种: 与数据行 26 过线, 与工具栏只有 19 ⇒ "几乎一样但不是");
    4. 表头文字在表头底色上的对比度 >= 4.5:1 —— 底色一抬, 原 --faint 就从 4.09:1 掉到 2.97:1;
    5. 置顶专区表头 (克隆主表 thead 的那张) 必须与主表表头**同一枚令牌** —— 两个同款表头长得
       不一样, 比两个都不明显更糟;
    6. 置顶专区表头还必须与**置顶行**拉开 >= 24 —— 置顶行是"淡 cyan 叠在专区底上"的**合成色**
       (`rgba(86,200,215,.05)` over `.pinzone` 的 `--paper-2`), 不是令牌, 所以本守阵**真算一遍**
       合成结果再比。这是本页最难的一对: 专区底 (--paper-2) 与置顶行只差 9, 表头能用的明度空间
       被两头挤住 —— 2026-10-05 首次修完只有 14, 把 --chrome 从 #232e3b 抬到 #2b3947 才到 26。
    """
    css = _shell_css()

    body = _rule(css, "#v-ledger thead th")
    tok = _bg_token(body)
    assert tok not in ("--bg", "--paper", "--paper-2"), (f"列标题行又借回 {tok} 了 —— 它离数据行 / 工具栏太近, 借了就读不出是表头")

    c = _hex_token(css, tok)
    for other in ("--bg", "--paper"):
        c_other = _hex_token(css, other)
        d = _max_channel_diff(c, c_other)
        assert d >= 24, (f"列标题行底色 {tok}{c} 与 {other}{c_other} 的最大通道差只有 {d} (<24)")

    # 文字色必须跟着底色一起抬 (10px 大字距标签, 4.5:1 是 WCAG AA 正文下限)
    col_tok = _color_token(body)
    ratio = _contrast(_hex_token(css, col_tok), c)
    assert ratio >= 4.5, (f"列标题行文字 ({col_tok}) 在表头底色 {tok} 上对比度只有 {ratio:.2f}:1 (<4.5) —— "
                          "底色抬起来后原来的 --faint 就看不见了")

    # 置顶专区表头 = 主表表头同一枚令牌 (专区表头是克隆主表 thead 来的, 两处必须长得一样)
    pin_tok = _bg_token(_rule(css, "#v-ledger .pinzone thead th"))
    assert pin_tok == tok, (f"置顶专区表头底色 ({pin_tok}) 与主表表头 ({tok}) 不一致 —— 两个同款表头长得不一样"
                            "比两个都不明显更糟")

    # 专区表头 vs **置顶行**: 置顶行是合成色 (淡 cyan 叠在专区底上), 必须真算合成再比
    pz_bg = _hex_token(css, _bg_token(_rule(css, ".pinzone")))
    m = re.search(
        r"background:\s*rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)",
        _rule(css, "#v-ledger tbody tr.pin-row"),
    )
    assert m, "置顶行底色不再是显式 rgba? 合成色算不出来, 同步本守阵"
    a = float(m.group(4))
    pin_row = tuple(round(a * int(m.group(i)) + (1 - a) * pz_bg[i - 1]) for i in (1, 2, 3))
    d_pin = _max_channel_diff(c, pin_row)  # type: ignore[arg-type]
    assert d_pin >= 24, (
        f"置顶专区表头底色 {tok}{c} 与置顶行合成色 {pin_row} 的最大通道差只有 {d_pin} (<24) —— "
        "表头压不住置顶行的淡 cyan 底, 行滚到它下面就读不出表头还在"
    )


def test_status_filter_not_reseeded_every_poll() -> None:
    """状态候选值不定长, derive() 每轮数据都得扫一遍补新值 —— 但**只许自动入选一次**:
    每 30s 轮询都把数据里存在的状态 add 回 S.aStatuses / S.cStatuses, 用户刚取消的状态
    就被盖回来, 表现是「状态筛选器隔一会儿自己重置」(2026-10-04 用户报; 形态 / issue 类型
    是定长常量数组、不进这条派生逻辑, 所以只有状态中招)。"""
    text = SHELL.read_text(encoding="utf-8")
    block = re.search(r"function derive\(\) \{(.*?)\n\}", text, re.S)
    assert block, "derive() 不见了? 数据派生逻辑搬家要同步本守阵"
    body = block.group(1)

    guard = "if (statusSeeded.has(s)) continue;"
    assert guard in body, "缺少 statusSeeded 闸门: 状态会被每轮轮询无条件 add 回选中集合"
    assert "S.aStatuses.add(s)" in body and "S.cStatuses.add(s)" in body, "自动入选逻辑不见了"
    assert body.index(guard) < body.index("S.aStatuses.add(s)"), "闸门必须排在自动入选之前"
    assert body.count("statusSeeded.add(s)") == 1, "入选记账只能落一处, 多处会让闸门失效"


# --------------------------------------------------------------------------- 筛选器持久化


def test_shell_has_filter_persistence() -> None:
    """筛选器必须落 localStorage (2026-10-05 用户报「每次刷新重置」): 存储键 + 存/读/还原三函数
    齐备, boot() 调 restoreFilters() 装载一次, 且把受控控件 (搜索框 / 排序下拉) 回填初值 ——
    状态还原了但控件还显示默认值, 用户会当成"没生效"。"""
    text = SHELL.read_text(encoding="utf-8")
    assert 'const FILTERS_KEY = "mb-nav-filters"' in text, "缺筛选器存储键常量"
    for fn in ("function saveFilters()", "function loadFilters()", "function restoreFilters()"):
        assert fn in text, f"缺筛选器持久化函数: {fn}"
    boot = re.search(r"function boot\(\) \{(.*?)\n\}", text, re.S)
    assert boot, "boot() 不见了? 装载逻辑搬家要同步本守阵"
    body = boot.group(1)
    assert "restoreFilters();" in body, "boot() 必须装载一次筛选器状态 (否则刷新回默认)"
    assert '$("gq").value = S.q' in body and '$("sort").value = S.sort' in body, "boot() 必须回填受控控件初值"


def test_filter_state_not_reseeded_on_poll() -> None:
    """与 pin 同源 (坑 pitfalls/web-ui/poll-reseed-filter.md): derive() 每 30s 跑一次, 绝不能读回
    localStorage / 重播筛选器默认 / 回写持久化 —— 否则轮询会把用户刚改的筛选洗掉。"""
    text = SHELL.read_text(encoding="utf-8")
    block = re.search(r"function derive\(\) \{(.*?)\n\}", text, re.S)
    assert block, "derive() 不见了? 数据派生逻辑搬家要同步本守阵"
    body = block.group(1)
    for forbidden in ("loadFilters", "restoreFilters", "saveFilters"):
        assert forbidden not in body, f"derive() 里出现 {forbidden}: 30s 轮询会与用户筛选打架"


def test_restore_filters_seeds_known_statuses() -> None:
    """还原筛选器时, 已知状态 (KNOWN_ST) 必须先计入 statusSeeded 台账 —— 否则首轮 derive()
    会把用户取消过的已知状态又 add 回来, 「刷新即重置」的根因就藏在这里 (与 3' 同源)。"""
    text = SHELL.read_text(encoding="utf-8")
    block = re.search(r"function restoreFilters\(\) \{(.*?)\n\}", text, re.S)
    assert block, "restoreFilters() 不见了? 持久化还原逻辑搬家要同步本守阵"
    body = block.group(1)
    assert "statusSeeded" in body and "KNOWN_ST" in body, "还原时必须把 KNOWN_ST 并入 statusSeeded 台账"


def test_filter_mutations_persist() -> None:
    """每个改筛选的入口都要落盘: 少一处 = 该筛选器刷新后仍旧重置 (用户报的就是这个)。
    台账四组筛选 (形态/状态/类型/关联) 是核心, 排序 / 双搜索 / 卡片三组一并守。"""
    text = SHELL.read_text(encoding="utf-8")
    for set_name in ("aForms", "aStatuses", "aTypes"):
        assert re.search(r"toggleSet\(S\." + set_name + r", v\); saveFilters\(\);", text), \
            f"台账 {set_name} 筛选落盘缺失"
    assert "S.aChain = !S.aChain; saveFilters();" in text, "台账「关联」筛选落盘缺失"
    assert text.count("saveFilters();") >= 12, \
        f"筛选落盘点偏少 (期望 >=12): {text.count('saveFilters();')}"


# --------------------------------------------------------------------------- 置顶 (pin)


def test_shell_has_pin_zone_and_ctxmenu() -> None:
    """置顶 (pin) 交互骨架: 专区容器 / 右键浮层 / 存储键 / contextmenu 监听 —— 缺任一即回归。"""
    text = SHELL.read_text(encoding="utf-8")
    assert 'id="pinZone"' in text, "缺置顶专区容器 #pinZone"
    assert 'id="ctxMenu"' in text, "缺右键菜单浮层 #ctxMenu"
    assert "PINS_KEY" in text, "缺 pin 存储键常量 (localStorage 落点)"
    assert "contextmenu" in text, "缺右键监听 (pin 的主入口之一)"


def test_pin_state_not_reseeded_by_derive() -> None:
    """pin 与「状态筛选器自动重置」同源风险: derive() 每 30s 跑一次, 绝不能碰 S.pins
    (坑档案 pitfalls/web-ui/poll-reseed-filter.md)。装载点必须全壳唯一, 且只在 boot() 发生。"""
    text = SHELL.read_text(encoding="utf-8")
    block = re.search(r"function derive\(\) \{(.*?)\n\}", text, re.S)
    assert block, "derive() 不见了? 数据派生逻辑搬家要同步本守阵"
    assert "pins" not in block.group(1), "derive() 里出现 pins: 30s 轮询会把用户 pin 洗掉"
    assert text.count("S.pins = loadPins()") == 1, "pin 装载点必须全壳唯一 (只在 boot 装载一次)"


def test_pinned_rendered_in_both_zones() -> None:
    """需求 3「pin 后同时显示在专区和非专区」: 同一份 pin 状态必须被两处消费 —— 专区渲染
    (pinZoneItems) 与**共用行模板** ledgerCells (isPinned)。只改一处 = 悄悄退化成单边显示。"""
    text = SHELL.read_text(encoding="utf-8")
    row = re.search(r"function ledgerCells\(.*?\) \{(.*?)\n\}", text, re.S)
    assert row, "行模板 (ledgerCells) 不见了? 渲染方式变了要同步本守阵"
    assert "isPinned(" in row.group(1), "行模板必须按 isPinned 渲染图钉 (非专区那一路)"

    zone = re.search(r"function renderPinZone\(\) \{(.*?)\n\}", text, re.S)
    assert zone, "renderPinZone() 不见了"
    assert "pinZoneItems(" in zone.group(1), "专区必须消费同一份 pin 状态 (双向显示)"


def test_pin_zone_reuses_ledger_columns() -> None:
    """置顶专区 = 与主表**同栏**的详细列表 (2026-10-05 用户定调: 同主区域, 只置顶展示 + 强调)。
    栏对齐靠「列定义单点」结构性保证, 而非各写一份再对表: 全壳只许有一处表头 (主表), 专区在
    renderPinZone 里**克隆主表 thead**, 行单元格两处共用 ledgerCells。任一处另写一份列定义,
    两张表就会各按自身内容算宽而逐栏错位 (这正是本次要修的问题形态)。"""
    text = SHELL.read_text(encoding="utf-8")

    # 列定义单点: 全壳只有主表一处 <thead><tr> (专区克隆它, 不另写)
    assert text.count("<thead><tr>") == 1, "置顶专区另写了一份列定义 (表头不止一处), 两表会逐栏错位"

    # 行单元格共用: 主表模板与专区都调 ledgerCells
    main_row = re.search(r"list\.map\(\(i, n\) => `(.*?)`\)\.join", text, re.S)
    assert main_row and "ledgerCells(i, n)" in main_row.group(1), "主表行必须走共用 ledgerCells"

    zone = re.search(r"function renderPinZone\(\) \{(.*?)\n\}", text, re.S)
    assert zone, "renderPinZone() 不见了"
    body = zone.group(1)
    assert "ledgerCells(" in body, "置顶专区行必须复用 ledgerCells (同栏), 不能另写一套 <td>"
    assert "ledgerwrap thead" in body, "置顶专区必须克隆主表 thead (列宽同源), 而非另写一份列头"


def test_pin_icon_is_inline_svg_no_emoji() -> None:
    """图钉为内联 SVG (守 test_shell_no_external_resources: 无外链图标库); 且按 code-style
    口径, 代码/资源里禁止 emoji 图形符号。"""
    text = SHELL.read_text(encoding="utf-8")
    m = re.search(r"const PIN_SVG = '(.*?)';", text, re.S)
    assert m and "<svg" in m.group(1), "图钉必须是内联 SVG (PIN_SVG 常量)"
    for ch in ("\U0001F4CC", "\U0001F4CD"):  # 图钉 / 圆图钉 emoji
        assert ch not in text, f"壳里出现 emoji 图钉字符 (code-style 禁图形符号): {ch!r}"


# --------------------------------------------------------------------------- 服务层 (127.0.0.1 随机端口)


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


# --------------------------------------------------------------------------- 拉取 (仅快进同步本仓库)


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


def test_shell_has_pull_button() -> None:
    """拉取按钮: 顶栏控件 + POST /api/pull + CSRF 自定义头; 静态 / file 模式隐藏 (无服务端可拉);
    doPull 成功刷新数据、失败走提示浮层 —— 少任一处即功能缺失或退化。"""
    text = SHELL.read_text(encoding="utf-8")
    assert 'id="pullBtn"' in text, "缺拉取按钮 #pullBtn"
    assert '"/api/pull"' in text, "按钮必须请求 /api/pull"
    assert "PULL_HEADER" in text and '"X-Nav-Action"' in text, "缺 CSRF 自定义头常量"
    assert '$("pullBtn").hidden = true' in text, "静态 / file 模式必须隐藏拉取按钮"

    block = re.search(r"async function doPull\(\) \{(.*?)\n\}", text, re.S)
    assert block, "doPull() 不见了? 拉取交互搬家要同步本守阵"
    body = block.group(1)
    assert 'method: "POST"' in body, "拉取必须用 POST (GET 会被跨站 <img> 直接触发)"
    assert "refresh(" in body, "同步成功后必须刷新数据"
    assert "showError(" in body, "同步失败必须提示 (仅快进失败要让人看见原因)"


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
