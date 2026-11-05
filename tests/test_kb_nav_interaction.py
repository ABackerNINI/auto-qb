"""test_kb_nav_interaction 测试计划: kb.nav 导航页守阵 (计划 memory-bank/plans/26-10-04-0952-plan-kb-nav-page.html §06)。

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

- test_esc_retreat_chain_single_point: 全壳唯一 document-level Escape 链 (escRetreat 退四档齐) + gq/cq per-input 清词恰两处
- test_esc_ime_guard: 链首 IME 守卫 (isComposing || keyCode === 229) 排在退档之前
- test_esc_closes_overlay_first: 遮罩退档 (hideError) 在链里排先于 ctxMenu/drawer 档 + CSS z 序同视觉层叠
- test_esc_closes_drawer: drawer 档判据 open 类 (可见性) 且清 S.sel + closeDrawer 同步, 后于 ctxMenu 档
- test_gsearch_clear_button: 全局搜索清词按钮在位 (内联 SVG / [hidden] 兜底 / syncGclear 单点同步 / 清词还焦点), placeholder 无 (Esc 清空)
- test_slash_focuses_search: "/" 快捷键聚焦搜索框 (slashFocus 命名函数 / 输入态与 IME 不劫 / 挡默认行为), 注册点不混 Esc 关键词
- test_search_matches_file_name_and_relative_path: 全局搜索按 basename / mb 内相对路径 / memory-bank/ 仓库根相对路径都能命中 (2026-11-03 用户复现); 原 title/topic/issue-summary 行为不变 + 大小写/反斜杠归一 + 三处过滤共用 navSearchText 单点 (正文不入索引)
- test_search_excluded_matches_hint_computed: 搜索被排除匹配项提示的计算口径 (task 26-11-06, grilling 拍板): 部分即命中 + 去重总数锚定/按原因分计可跨组重复 + 隐藏独占桶 + 维度按活动视图 (台账三维/卡片墙两维/控制台只显隐藏) + 空词与无排除不提示 (node 回放真实 JS)
- test_search_excluded_hint_ui_wiring: 提示行 UI 接线单点: #ghint 在 .gsearch 内 [hidden] 兜底 + CSS 悬浮省略不设 display + renderGhint 挂满三视图 render + wire 点击委托勾回走 saveFilters+重渲染链 + 文案锚点 (另匹配/另有 N 项隐藏/title 分计口径)
- test_multiselect_renders_in_both_zones: 主表与置顶专区渲染都挂 msel (双区同亮) + CSS tr.msel 与 sel.msel 组合样式在位
- test_ctx_menu_batch_upgrade: 右键批量升级单点 ctxTargets (集合>1 且行∈选区) + openCtx 冻结 links 快照 + 批量文案带 N + 分发走批量链
- test_batch_actions_idempotent: 批量 pin/hide 幂等 (every 动态方向 / 过滤已达态 / 落盘链不绕开) + 批量隐藏剪出选区
- test_multiselect_chrome_and_escapes: 顶栏已选N chip ([hidden] 兜底/点击清空) + Esc 退栈末档清多选 (序在 drawer 后 sel 前) + setView 清空 + Ctrl+A 台账非输入态全选
- test_batch_copy_paths_and_open_links: copyText 双链路降级 + 批量复制每行一个按可见序 + 打开 >5 confirm 走 MB 路由
- test_pin_zone_collapse_toggle: 置顶区标题行的折叠按钮 (原生 button / aria-expanded + aria-controls / 折叠箭头方向) 切换置顶区主体可见性并持久化 (node 回放真实 JS)
- test_pin_row_click_opens_drawer_via_shared_path: 置顶区条目单击与主表共用同一 openRowDetail 单点 (同 renderDrawer / 同 sel 高亮), 不再单开原文
"""

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

from kb_nav_support import (
    SHELL,
    _rule,
    _shell_css,
    _shell_fn,
)


def test_esc_retreat_chain_single_point() -> None:
    """Esc 管制单点 (计划 §05): 全壳只许**一处** document-level Escape 链 (escRetreat), 且它退
    四档齐 (overlay / ctxMenu / drawer / sel) —— 既有两处 per-input 清词 (gq/cq) 之外, 别在别处
    再写一份 document-level Esc 监听 (两处链即触发序竞乱, 26-10-06 同根: 退栈 order 靠注册序)。"""
    text = SHELL.read_text(encoding="utf-8")
    doc_listeners = re.findall(r'document\.addEventListener\("keydown"[^)]*\)', text)
    esc_doc = [s for s in doc_listeners if "Escape" in s or "escRetreat" in s]
    assert len(esc_doc) == 1, f"document-level Escape 监听不止一处: {esc_doc}"
    assert "escRetreat" in text, "缺退栈链函数 escRetreat (单点链是口径)"
    chain = re.search(r"const escRetreat = \(e\) => \{(.*?)\n  \};", text, re.S)
    assert chain, "escRetreat 链不见了? 结构搬家要同步本守阵"
    body = chain.group(1)
    for tier in ("hideError()", "closeCtx()", "closeDrawer()", 'querySelectorAll("tr.sel")'):
        assert tier in body, f"退栈链缺档: {tier}"
    per_input = re.findall(r'\$\("(?:gq|cq)"\)\.addEventListener\("keydown"', text)
    assert len(per_input) == 2, "gq/cq per-input 清词 pair 必须恰两处 (拍板 P3 keep)"


def test_esc_ime_guard() -> None:
    """IME 组合期不劫 (拍板 P4, nav 搜索框中文输入 real): 链首须 IME 守卫 —— 中文输入组合期
    Esc 属于输入法 (取消候选), 不退浮层 / 清词 (webui lifecycle.js 同款口径)."""
    text = SHELL.read_text(encoding="utf-8")
    chain = re.search(r"const escRetreat = \(e\) => \{(.*?)\n  \};", text, re.S)
    assert chain, "escRetreat 链不见了? 同步本守阵"
    body = chain.group(1)
    assert "e.isComposing" in body and "keyCode === 229" in body, "链缺 IME 守卫 (isComposing || keyCode === 229)"
    guard_at = body.index("isComposing")
    assert guard_at < body.index("hideError()"), "IME 守卫必须排在退档之前 (组合期即不劫, 直接放行)"


def test_esc_closes_overlay_first() -> None:
    """退栈 order = visual z-order (红线照 pitfalls/web-ui): overlay 遮罩 (z-50) 压 ctxMenu (z-40)
    与 drawer (z-30), 遮罩档**必先**收它 —— 否则 Esc 穿过遮罩去关被盖住的看不见层 (26-10-06
    同根实测报障), 且拉取失败全屏锁 (doPull 失败弹 overlay, dismiss 原只 applyData 即 ≤30s 轮)
    不消. 守: 遮罩档在链里且排先于 ctxMenu / drawer 档."""
    text = SHELL.read_text(encoding="utf-8")
    chain = re.search(r"const escRetreat = \(e\) => \{(.*?)\n  \};", text, re.S)
    assert chain, "escRetreat 链不见了? 同步本守阵"
    body = chain.group(1)
    ov_at = body.index('$("overlay")')
    assert 'hideError()' in body, "遮罩退档缺 hideError()"
    assert ov_at < body.index("hideError()") < body.index("closeCtx()"), "遮罩档必须先于 ctxMenu 档"
    assert body.index("hideError()") < body.index("closeDrawer()"), "遮罩档必须先于 drawer 档"
    css = _shell_css()
    z = {}
    for sel in (".overlay", ".ctxmenu", ".drawer"):
        m = re.search(r"z-index:\s*(\d+)", _rule(css, sel))
        assert m, f"{sel} 缺 z-index? 层叠钉死同步本守阵"
        z[sel] = int(m.group(1))
    assert z[".overlay"] > z[".ctxmenu"] > z[".drawer"], (
        f"CSS z 序 (overlay {z['.overlay']} / ctxmenu {z['.ctxmenu']} / drawer {z['.drawer']}) "
        "与退栈档序钉 (遮罩先) 需同视觉层叠 —— 改层叠要同步链"
    )


def test_esc_closes_drawer() -> None:
    """drawer 退档 (缺口实测: 详情抽屉原只 dclose 按钮无 Esc 路径): 链里清 S.sel + closeDrawer
    —— 只收抽屉而不清选择 (或反之) 即下一 renderLedger 会把抽屉又弹 (renderLedger 里 S.sel 即 renderDrawer)."""
    text = SHELL.read_text(encoding="utf-8")
    chain = re.search(r"const escRetreat = \(e\) => \{(.*?)\n  \};", text, re.S)
    assert chain, "escRetreat 链不见了? 同步本守阵"
    body = chain.group(1)
    drawer_branch = re.search(r'if \(drawer\.classList\.contains\("open"\)\) \{([^}]*)\}', body)
    assert drawer_branch, "drawer 退档 (判据 open 类 = 可见性, 不状态位) 不见了"
    branch = drawer_branch.group(1)
    assert "S.sel = null" in branch and "closeDrawer()" in branch, "drawer 档必须清 S.sel 并收抽屉 (两处同步, 否则抽屉又弹)"
    assert body.index("closeCtx()"
                     ) < body.index('drawer.classList.contains("open")'), "drawer 档必须后于 ctxMenu 档 (z-30 < z-40)"


def test_gsearch_clear_button() -> None:
    """全局搜索清词按钮: 有词才显形、点按清词并把焦点还给输入框、内联 SVG 无 emoji (code-style)。
    显隐同步必须走 syncGclear 单点 —— gq 的 input / Esc 清词 / 清词按钮 / boot 回填四处共用,
    各处各写一份即某处漂移出幽灵按钮或按钮失踪。placeholder 不写 "(Esc 清空)" (设计口径:
    Esc 清词不在文档化交互里, 按钮才是明面入口)。"""
    text = SHELL.read_text(encoding="utf-8")
    assert 'id="gclear"' in text, "缺清词按钮 #gclear"
    assert ".gclear[hidden]" in text, ".gclear 缺 [hidden]{display:none} 兜底 (flex display 会盖掉 UA hidden)"
    assert "function syncGclear" in text, "缺显隐同步单点 syncGclear()"
    assert text.count("syncGclear(") >= 5, "gq 四个入口 (input / Esc / 按钮 / boot 回填) 都得过 syncGclear 同步"
    assert "S.q = \"\"" in text and "$(\"gq\").focus()" in text, "清词点击须清 S.q 且焦点还给输入框"
    btn = re.search(r'<button class="gclear"[^>]*>(.*?)</button>', text, re.S)
    assert btn and "<svg" in btn.group(1), "清词按钮须内联 SVG 图形 (禁 emoji / 字符叉)"
    css = _shell_css()
    assert ".gsearch svg" not in css and ".gsearch > svg" in css, (
        "放大镜定位必须钉直接子代 (.gsearch > svg) —— 后代选择器会命中 #gclear 里的 ×, "
        "给它套 absolute 导致 flex 居中失效 (2026-10-31 实测居中漂移)"
    )
    gq = re.search(r'<input id="gq"[^>]*>', text)
    assert gq and "Esc" not in gq.group(0), "gq placeholder 不再写 (Esc 清空) —— 按钮是明面入口 (只涉 gq, cq 不动)"


def test_slash_focuses_search() -> None:
    """"/" 快捷键聚焦全局搜索框: 命名函数 slashFocus + document 级注册恰一处; 输入态不劫
    (closest input/textarea/select —— 在框里打 / 是正常字符), IME 组合期不劫 (keyCode 229 同判),
    加修饰键不劫。命名函数注册是给 Esc 单点守阵让路的口径: 监听调用点里不得出现 Esc 关键词。"""
    text = SHELL.read_text(encoding="utf-8")
    assert "function slashFocus" in text, "缺 slashFocus 处理函数"
    assert 'document.addEventListener("keydown", slashFocus)' in text, "slashFocus 须命名函数注册"
    body = re.search(r"function slashFocus\(e\) \{(.*?)\n  \}", text, re.S)
    assert body, "slashFocus 结构搬家要同步本守阵"
    b = body.group(1)
    assert 'e.key !== "/"' in b, "缺键位判据 /"
    assert "e.isComposing" in b and "keyCode === 229" in b, "缺 IME 组合期守卫 (同 escRetreat 口径)"
    assert 'closest("input, textarea, select")' in b, "输入态不劫 (框内打 / 是正常字符)"
    assert "e.preventDefault()" in b and '$("gq").focus()' in b, "须挡下默认行为并聚焦 #gq"
    listener = re.search(r'document\.addEventListener\("keydown"[^)]*\)', text)
    assert listener, "缺 keydown 注册? 壳被改坏"
    assert "Escape" not in listener.group(0) or "escRetreat" in listener.group(0), (
        "document 级 keydown 首个注册点混入 Esc 关键词 —— Esc 单点守阵 (test_esc_retreat_chain_single_point) 数的就是它"
    )


def test_search_matches_file_name_and_relative_path(tmp_path) -> None:
    """2026-11-03 用户复现: 在 #gq 输入 memory-bank/reports/<file> 无匹配 —— 原匹配串只拼
    title/topic/issue-summary, link 未入索引, 故 basename 与路径都不可搜。本守阵钉三件事:
    ①basename / mb 内相对路径 / 仓库根相对路径 (memory-bank/<link>) 三种形态命中该文件;
    ②原有 title / topic / issue-summary 命中行为不变 (加路径只是加法); ③大小写与反斜杠归一;
    ④台账 / 卡片墙 / 控制台频道三处过滤共用 navSearchText 单点, 不得各拼一份 haystack。
    索引只含上述四类字段, 正文不入 (体积口径)。JS 单点用 node 回放 (与仓库其余 JS 守阵同口径)。"""
    text = SHELL.read_text(encoding="utf-8")
    idx_body = re.search(r"function navSearchText\(i\) \{([^}]*)\n\}", text, re.S)
    qry_body = re.search(r"function navSearchQuery\(q\) \{([^}]*)\n\}", text, re.S)
    assert idx_body and qry_body, "搜索索引单点 navSearchText / navSearchQuery 不见了? 改版要同步本守阵"
    assert "i.link" in idx_body.group(1) and 'memory-bank/" + link' in idx_body.group(1), (
        "索引必须含 link (basename 随之可搜) 与 memory-bank/<link> 仓库根相对形态"
    )
    assert text.count('i.title + " " + (i.topic') == 1, ("haystack 拼接必须只存在于 navSearchText 单点 (计数应=1), 否则过滤点各自漂移")

    af = re.search(r"function aFiltered\(\) \{(.*?)\n\}", text, re.S)
    cv = re.search(r"function cVisibleItems\(key\) \{(.*?)\n\}", text, re.S)
    ch = re.search(r"function renderChannels\(\) \{(.*?)\n\}", text, re.S)
    assert af and "navSearchText(i)" in af.group(1) and "navSearchQuery(S.q)" in af.group(1), "台账过滤未走搜索单点"
    assert cv and "navSearchText(i)" in cv.group(1) and "navSearchQuery(S.q)" in cv.group(1), "卡片墙过滤未走搜索单点"
    assert ch and "navSearchText(i)" in ch.group(1), "控制台频道过滤未消费同一索引 (路径搜索在该视图仍空白)"

    node = shutil.which("node")
    if not node:
        pytest.skip("node 不在 PATH (与仓库其余 JS 守阵同口径)")
    item = {
        "title": "规则引擎重设计报告",
        "topic": "rule-engine-redesign",
        "issue-summary": "关键词 alpha-beta",
        "link": "reports/26-11-01-0057-report-rule-engine-redesign.html",
    }
    queries = {
        "basename": "26-11-01-0057-report-rule-engine-redesign.html",
        "mb_rel": "reports/26-11-01-0057-report-rule-engine-redesign.html",
        "repo_rel": "memory-bank/reports/26-11-01-0057-report-rule-engine-redesign.html",
        "upper": "MEMORY-BANK/REPORTS/26-11-01-0057-REPORT-RULE-ENGINE-REDESIGN.HTML",
        "backslash": "memory-bank\\reports\\26-11-01-0057-report-rule-engine-redesign.html",
        "title": "规则引擎重设计",
        "topic": "rule-engine-redesign",
        "summary": "alpha-beta",
        "miss": "zzz-no-such-file",
    }
    probe = tmp_path / "search_probe.js"
    probe.write_text(
        "function navSearchText(i) {" + idx_body.group(1) + "\n}\n" + "function navSearchQuery(q) {" +
        qry_body.group(1) + "\n}\n" + "const item = " + json.dumps(item, ensure_ascii=False) + ";\n" + "const qs = " +
        json.dumps(queries, ensure_ascii=False) + ";\n" + "for (const [k, q] of Object.entries(qs)) "
        "console.log(k + '=' + (navSearchText(item).includes(navSearchQuery(q)) ? '1' : '0'));\n",
        encoding="utf-8",
    )
    out = subprocess.run([node, str(probe)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    got = dict(line.split("=", 1) for line in out.stdout.strip().splitlines())
    for key in ("basename", "mb_rel", "repo_rel", "upper", "backslash", "title", "topic", "summary"):
        assert got.get(key) == "1", f"{key} 未命中 ({queries[key]}): {got}"
    assert got.get("miss") == "0", "无关词不应命中"


def test_search_excluded_matches_hint_computed(tmp_path) -> None:
    """搜索被排除匹配项提示的计算口径 (task 26-11-06-memory-bank-kb-nav-search-ghint, grilling
    两轮拍板)。真实痛点: issues/26-09-30-0052-feat-hr-login-counter-attest 状态 Dropped,
    取消勾选后按完整名搜索 0 结果且无任何提示 —— 勾选过滤在搜索之前 AND, 匹配项被静默吞掉。
    钉: ①部分 slug (stamp / slug 片段) 与完整名同样命中 (索引本就含 basename, 缺的是可见性);
    ②总数 = 去重非隐藏被排除匹配数, 括号按原因分计、同件可跨组重复 (Q3b+w1); ③隐藏件独占一桶,
    不进原因组与总数 (Q10a: 点组名唤不回隐藏件); ④维度按活动视图: 台账三维 / 卡片墙两维 /
    控制台只显隐藏 (Q8a, 频道搜索不做形态/状态过滤); ⑤空词或无排除无隐藏 → null 不提示。
    场景数据按真实 26-09-30-0052 三兄弟 (2 Dropped + 1 Open) 仿造。node 回放真实 JS。"""
    text = SHELL.read_text(encoding="utf-8")
    dims = _shell_fn(text, "ghintExclDims")
    data = _shell_fn(text, "ghintData")
    idx = _shell_fn(text, "navSearchText")
    qry = _shell_fn(text, "navSearchQuery")
    node = shutil.which("node")
    if not node:
        pytest.skip("node 不在 PATH (与仓库其余 JS 守阵同口径)")
    probe = tmp_path / "ghint_probe.js"
    probe.write_text(
        "const FORM_ORD = ['issue','plan','report','task'];\n"
        "const FORM_CN = { issue:'问题', plan:'计划', report:'报告', task:'档案' };\n"
        "const KNOWN_ST = ['Open','In Progress','Done','Dropped','Superseded'];\n"
        "const TYPES = ['bug','perf','docs','test','refactor','feat','chore','question'];\n"
        "const NO_ST = '(无状态)';\n"
        "let statusList = KNOWN_ST.slice();\n"
        "const S = { view:'ledger', q:'', aForms:new Set(FORM_ORD), aStatuses:new Set(KNOWN_ST),\n"
        "  aTypes:new Set(TYPES), cForms:new Set(FORM_ORD), cStatuses:new Set(KNOWN_ST), hidden:[] };\n"
        "const stOf = i => i.status || NO_ST;\n"
        "const isHidden = link => S.hidden.includes(link);\n"
        "let DATA = { items: [] };\n"
        "function navSearchText(i) {" + idx + "\n}\n"
        "function navSearchQuery(q) {" + qry + "\n}\n"
        "function ghintExclDims(i) {" + dims + "\n}\n"
        "function ghintData() {" + data + "\n}\n"
        "DATA.items = [\n"
        "  { title:'HR 计数 looks_like_login 补计数文本佐证', topic:'backend-partial-hr-verify',\n"
        "    'issue-summary':'s1', link:'issues/26-09-30-0052-feat-hr-login-counter-attest.html',\n"
        "    form:'issue', status:'Dropped', 'issue-type':'feat' },\n"
        "  { title:'HR 计数 上限徽章总数轴互证', topic:'backend-partial-hr-verify',\n"
        "    'issue-summary':'s2', link:'issues/26-09-30-0052-feat-hr-badge-total-crosscheck.html',\n"
        "    form:'issue', status:'Dropped', 'issue-type':'perf' },\n"
        "  { title:'HR 计数 末页追翻省略', topic:'backend-partial-hr-verify',\n"
        "    'issue-summary':'s3', link:'issues/26-09-30-0052-perf-hr-lastpage-fetch-skip.html',\n"
        "    form:'issue', status:'Open', 'issue-type':'perf' },\n"
        "  { title:'Z 与搜索词无关的隐藏件', topic:'zzz-unrelated',\n"
        "    'issue-summary':'s4', link:'tasks/26-10-01-0000-unrelated.md',\n"
        "    form:'task', status:'Open' },\n"
        "];\n"
        "/* 常驻隐藏件: 不匹配任何场景搜索词 —— isHidden 判定若被挪到搜索过滤之前 (退化成全量\n"
        "   隐藏数), 各场景 h 会虚增, 本探针即红 (拍板 Q10b: 隐藏计数=搜索相关非全量) */\n"
        "S.hidden = ['tasks/26-10-01-0000-unrelated.md'];\n"
        "const liveOf = () => false; /* 开关边界场景用: 全部专题视为非活跃 */\n"
        "const run = tag => {\n"
        "  const d = ghintData();\n"
        "  console.log(tag + '=' + JSON.stringify(d ? { t:d.total, h:d.hidden,\n"
        "    g:d.groups.map(x => x.dim + ':' + x.val + ':' + x.n) } : null));\n"
        "};\n"
        "S.view = 'ledger';\n"
        "S.aStatuses = new Set(['Open','In Progress','Done','Superseded']);\n"
        "S.q = '26-09-30-0052-feat-hr-login-counter-attest'; run('full_dropped');\n"
        "S.q = '26-09-30-0052'; run('partial_stamp');\n"
        "S.q = 'feat-hr-login-counter'; run('partial_slug');\n"
        "S.hidden = ['issues/26-09-30-0052-feat-hr-login-counter-attest.html', 'tasks/26-10-01-0000-unrelated.md'];\n"
        "S.q = '26-09-30-0052'; run('hidden_exclusive');\n"
        "S.aForms = new Set(['plan','report','task']);\n"
        "run('overlap');\n"
        "S.view = 'cards';\n"
        "S.cStatuses = new Set(['Open','In Progress','Done','Superseded']); S.cForms = new Set(FORM_ORD);\n"
        "S.q = '26-09-30-0052'; run('cards_dims');\n"
        "S.view = 'console';\n"
        "run('console_hidden_only');\n"
        "S.hidden = [];\n"
        "run('console_no_excl_no_hid');\n"
        "S.q = ''; run('empty_q');\n"
        "S.view = 'ledger';\n"
        "S.aStatuses = new Set(KNOWN_ST); S.aForms = new Set(FORM_ORD);\n"
        "S.aTypes = new Set(TYPES.filter(t => t !== 'feat'));\n"
        "S.q = 'feat-hr-login-counter'; run('type_dim');\n"
        "/* 开关边界 (拍板 Q6③): live/chain/cLive 造成的排除不进提示 —— ghintData 不消费开关;\n"
        "   若有人给 ghintExclDims 加 live 维, 本场景 (唯一匹配件仅被活跃性挡住) 会给出 total=1 而红 */\n"
        "S.aStatuses = new Set(KNOWN_ST); S.aForms = new Set(FORM_ORD); S.aTypes = new Set(TYPES);\n"
        "S.aLive = true;\n"
        "S.q = 'perf-hr-lastpage-fetch-skip'; run('switch_live_excluded');\n",
        encoding="utf-8",
    )
    out = subprocess.run([node, str(probe)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    got = dict(line.split("=", 1) for line in out.stdout.strip().splitlines())
    expected = {
        "full_dropped": {
            "t": 1,
            "h": 0,
            "g": ["status:Dropped:1"]
        },
        "partial_stamp": {
            "t": 2,
            "h": 0,
            "g": ["status:Dropped:2"]
        },
        "partial_slug": {
            "t": 1,
            "h": 0,
            "g": ["status:Dropped:1"]
        },
        "hidden_exclusive": {
            "t": 1,
            "h": 1,
            "g": ["status:Dropped:1"]
        },
        "overlap": {
            "t": 2,
            "h": 1,
            "g": ["form:issue:2", "status:Dropped:1"]
        },
        "cards_dims": {
            "t": 1,
            "h": 1,
            "g": ["status:Dropped:1"]
        },
        "console_hidden_only": {
            "t": 0,
            "h": 1,
            "g": []
        },
        "console_no_excl_no_hid": None,
        "empty_q": None,
        "type_dim": {
            "t": 1,
            "h": 0,
            "g": ["type:feat:1"]
        },
        "switch_live_excluded": None,
    }
    for tag, want in expected.items():
        assert got.get(tag) == json.dumps(want, ensure_ascii=False,
                                          separators=(",", ":")), (f"{tag} 口径漂移: 期望 {want}, 实得 {got.get(tag)}")


def test_search_excluded_hint_ui_wiring() -> None:
    """提示行的 UI 接线单点 (task 26-11-06-memory-bank-kb-nav-search-ghint):
    ①#ghint 落在 .gsearch 内、视图切换器之前 (搜索框正下方, 不进视图容器), [hidden] 兜底,
      CSS 悬浮 (absolute) + 单行省略 (ellipsis), 且 .ghint 不得设 display (会盖掉 [hidden]
      的 UA 兜底, 同 #gclear 口径); ②renderGhint 挂满三个视图 render 末尾 —— 过滤切换不经
      renderCurrent (buildFilterRows onToggle 直呼视图 render), 少挂一处 = 该视图切换过滤后
      提示不刷新; ③wire() 点击委托 = 勾上对应值并走各视图 saveFilters+重渲染既有链 (拍板
      Q4a), 五个勾选集都要接; ④计算口径结构: 搜索空即 null、隐藏独占 (isHidden 判定先于维度
      归组)、维度按活动视图; ⑤文案锚点 (拍板 Q9 w1): 总数锚定 + 按原因分计 + 「N项隐藏」+
      title 注明分计口径。"""
    text = SHELL.read_text(encoding="utf-8")
    css = _shell_css()
    at_gsearch = text.index('<div class="gsearch">')
    at_ghint = text.index('<div class="ghint" id="ghint" hidden></div>')
    at_seg = text.index('<div class="seg"')
    assert at_gsearch < at_ghint < at_seg, "#ghint 必须在搜索框内、视图切换器之前 (搜索框正下方)"
    rule = _rule(css, ".ghint")
    assert "position: absolute" in rule and "text-overflow: ellipsis" in rule, "提示行要悬浮于搜索框下方 + 单行省略"
    assert "display" not in rule, ".ghint 不得设 display (盖掉 [hidden] UA 兜底, 同 #gclear 口径)"
    gtag = _rule(css, ".ghint .gtag")
    assert "cursor: pointer" in gtag, "组名可点 (拍板 Q4a)"
    for fn in ("renderLedger", "renderConsole", "renderCards"):
        assert "renderGhint()" in _shell_fn(text, fn), f"{fn} 末尾缺 renderGhint 挂载 (该视图过滤切换后提示不刷新)"
    wire = _shell_fn(text, "wire")
    assert '$("ghint").addEventListener("click"' in wire, "缺提示行点击委托"
    # 断言只看 ghint 委托片 (从注册点起、到本块闭合止): 基线 wire() 其余处理器本就含
    # saveFilters()/renderLedger()/renderCards(), 整函数断言恒真 (review R2-1)
    at_hint = wire.index('$("ghint").addEventListener("click"')
    ghint_wire = wire[at_hint:wire.index("\n  });", at_hint)]
    assert 'closest(".gtag")' in ghint_wire and "dataset.gdim" in ghint_wire and "dataset.gval" in ghint_wire, (
        "委托按组维值分发"
    )
    assert 'S.view === "ledger"' in ghint_wire and 'S.view === "cards"' in ghint_wire, ("视图分支名钉死 (写错分支 = 勾回无声失效)")
    for add in (
        "S.aStatuses.add(val)", "S.aForms.add(val)", "S.aTypes.add(val)", "S.cStatuses.add(val)", "S.cForms.add(val)"
    ):
        assert add in ghint_wire, f"缺 {add} (dim→集合映射钉死, 勾回必须落到对应视图的勾选集)"
    assert "saveFilters()" in ghint_wire and "renderLedger()" in ghint_wire and "renderCards()" in ghint_wire, (
        "勾回走既有 toggle 链 (落盘+重渲染)"
    )
    data = _shell_fn(text, "ghintData")
    assert "if (!S.q) return null" in data, "搜索为空永不提示 (拍板 Q6②)"
    assert data.index("isHidden(i.link)") < data.index("ghintExclDims(i)"), "隐藏独占桶: isHidden 判定须先于维度归组 (拍板 Q10a)"
    dims = _shell_fn(text, "ghintExclDims")
    assert 'S.view === "ledger"' in dims and 'S.view === "cards"' in dims and "return []" in dims, (
        "维度按活动视图: 台账三维 / 卡片墙两维 / 控制台只显隐藏 (拍板 Q8a)"
    )
    assert "另匹配 <b>" in text and "</b> 项 (" in text, "文案锚点: 另匹配 N 项 (…)"
    assert "项隐藏</span>" in text, "文案锚点: 另有 N 项隐藏 (独占桶)"
    assert "按排除原因分计, 同件可跨组重复" in text, "行 title 须注明分计口径 (拍板 Q3b 措辞)"


def test_multiselect_renders_in_both_zones() -> None:
    """多选渲染 (拍板 D13 双区同亮): 状态在 S.multi, 渲染时按 link 重挂 msel —— 主表与置顶专区
    两处都要挂, 只挂一处 = 置顶件选中后在另一处看不见。CSS 侧 msel 与 sel 两态选择器都要在,
    且 msel 左条走**专用靛蓝族** --msel-bar (2026-10-31 验收反馈: 首版 cyan 降透明度与单击预览
    tr.sel 只差明度, 实测混淆 —— 照 auto-qb views.css R10-07 同款坑, 色相分家)。"""
    text = SHELL.read_text(encoding="utf-8")
    ledger = re.search(r"function renderLedger\(\) \{(.*?)\n\}", text, re.S)
    assert ledger and "multiSet()" in ledger.group(1) and "msel" in ledger.group(1), "主表渲染缺 msel 挂类"
    zone = re.search(r"function renderPinZone\(\) \{(.*?)\n\}", text, re.S)
    assert zone and "msel" in zone.group(1), "置顶专区渲染缺 msel 挂类 (双区同亮)"
    css = _shell_css()
    assert "#v-ledger tbody tr.msel" in css, "缺多选行高亮样式 tr.msel"
    assert "#v-ledger tbody tr.sel.msel" in css, "缺 sel+msel 并存组合样式 (拍板 D3: 单击开抽屉不清多选, 两态会同框)"
    msel_rule = re.search(r"#v-ledger tbody tr\.msel \{[^}]*\}", css)
    assert msel_rule and "var(--msel-bar)" in msel_rule.group(0), "msel 左条未走专用靛蓝族 (色相分家)"
    assert "rgba(86,200,215" not in msel_rule.group(0), "msel 回用 cyan 族 = 与单击预览只差明度 (验收反馈的混淆根因)"


def test_ctx_menu_batch_upgrade() -> None:
    """右键菜单批量升级 (拍板 D4/D12, auto-qb menu.js CTX-03 口径): 目标解析单点 ctxTargets
    (行 ∈ 选区且集合 > 1 → 整集合快照, 否则单条); openCtx 冻结 links 快照 (dataset.links),
    批量态四项文案带灰色 N (class="n"), 菜单点击按快照走批量分发链。"""
    text = SHELL.read_text(encoding="utf-8")
    assert "function ctxTargets(link)" in text, "缺右键目标解析单点 ctxTargets"
    tgt = re.search(r"function ctxTargets\(link\) \{(.*?)\n\}", text, re.S)
    assert tgt and "S.multi.length > 1" in tgt.group(1) and "S.multi.includes(link)" in tgt.group(1), (
        "ctxTargets 判据必须是「集合 > 1 且行 ∈ 选区」(集合恰等于该行自身仍是单目标菜单)"
    )
    ctx = re.search(r"function openCtx\(.*?\{(.*?)\n\}", text, re.S)
    assert ctx, "openCtx 不见了"
    c = ctx.group(1)
    assert "ctxTargets(link)" in c, "openCtx 必须经 ctxTargets 解析目标 (口径单点)"
    assert 'm.dataset.links = JSON.stringify(links);' in c, "菜单须冻结 links 快照 (存活期选区漂移不影响本次动作)"
    assert 'links.length > 1 ?' in c and 'class="n"' in c, "批量态文案缺灰色 N 后缀 (拍板 D12)"
    for act in ('data-act="pin"', 'data-act="hide"', 'data-act="open"', 'data-act="copy"'):
        assert act in c, f"批量升级后缺菜单项 {act}"
    menu = re.search(r'\$\("ctxMenu"\)\.addEventListener\("click", e => \{(.*?)\n  \}\);', text, re.S)
    assert menu, "菜单点击分发不见了"
    d = menu.group(1)
    for call in ("togglePinBatch(links)", "toggleHideBatch(links)", "openLinks(links)", "copyPaths(links)"):
        assert call in d, f"菜单分发缺批量动作 {call}"
    assert "JSON.parse" in d, "分发须消费冻结快照 (dataset.links), 不得回读实时选区"


def test_batch_actions_idempotent() -> None:
    """批量 pin/hide 幂等 (拍板 D6 / 黄金法则 1): 动态单项文案来自 every(isPinned/isHidden),
    动作对已达态成员零副作用; 批量隐藏后须把隐掉的 link 剪出选区 (隐藏件从所有内容视图退场,
     留在选区里 = 下一次批量菜单悄悄含不可见行); 落盘链 savePins/saveHidden 不得绕开。"""
    text = SHELL.read_text(encoding="utf-8")
    pin = re.search(r"function togglePinBatch\(links\) \{(.*?)\n\}", text, re.S)
    assert pin, "缺 togglePinBatch"
    p = pin.group(1)
    assert "links.every(isPinned)" in p, "批量 pin 缺动态方向判据 (全已置顶 -> 批量取消)"
    assert "savePins()" in p, "批量 pin 绕开了 savePins 落盘链"
    assert "isPinned(l)" in p, "批量 pin 须过滤已达态成员 (幂等)"
    hide = re.search(r"function toggleHideBatch\(links\) \{(.*?)\n\}", text, re.S)
    assert hide, "缺 toggleHideBatch"
    h = hide.group(1)
    assert "links.every(isHidden)" in h, "批量 hide 缺动态方向判据"
    assert "saveHidden()" in h, "批量 hide 绕开了 saveHidden 落盘链"
    assert "S.multi = S.multi.filter" in h, "批量隐藏后未把隐藏件剪出选区 (拍板 D5 边界情形)"


def test_multiselect_chrome_and_escapes() -> None:
    """多选辅助件 (拍板 D5/D9/D10/D11): 顶栏「已选 N」chip ([hidden] 兜底必写, 点击清空);
    Esc 退栈链末档清多选 (排在 drawer 之后、遗留 tr.sel 之前); 切视图清空 (setView);
    Ctrl+A = 台账视图 + 非输入态全选主表可见行 (preventDefault + IME 守卫, 监听不混 Esc 关键词)。"""
    text = SHELL.read_text(encoding="utf-8")
    assert 'id="mselChip"' in text, "缺顶栏多选计数 chip"
    css = _shell_css()
    assert ".mselchip[hidden] { display: none; }" in css, "chip 缺 [hidden] 兜底 (display 会盖掉 UA hidden)"
    assert "function syncMultiChip" in text, "缺 chip 单点同步函数"
    assert '$("mselChip").addEventListener("click", clearMulti)' in text, "chip 点击未接清空"
    assert "function clearMulti" in text, "缺清空多选单点"

    chain = re.search(r"const escRetreat = \(e\) => \{(.*?)\n  \};", text, re.S)
    assert chain and "clearMulti()" in chain.group(1), "Esc 退栈链缺多选档 (拍板 D9)"
    b = chain.group(1)
    assert b.index('drawer.classList.contains("open")') < b.index("clearMulti()"
                                                                 ) < b.index('querySelectorAll("tr.sel")'), (
                                                                     "多选档必须排在 drawer 之后、遗留 tr.sel 之前 (退栈序 = 视觉 z 序)"
                                                                 )
    setview = re.search(r"function setView\(v\) \{(.*?)\n\}", text, re.S)
    assert setview and "S.multi = []" in setview.group(1), "切视图未清空多选 (拍板 D5: 别处残留看不见的选区)"

    assert "function selectAllVisible" in text, "缺 Ctrl+A 全选处理"
    sel = re.search(r"function selectAllVisible\(e\) \{(.*?)\n  \}", text, re.S)
    s = sel.group(1)
    assert 'e.key !== "a"' in s, "缺键位判据 a/A"
    assert 'closest("input, textarea, select")' in s, "输入态不劫 (框内 Ctrl+A 是全选文本)"
    assert 'S.view !== "ledger"' in s, "须限台账视图 (控制台/卡片墙留浏览器默认)"
    assert "e.preventDefault()" in s and "S.multi = aFiltered().map(i => i.link);" in s, ("全选须挡默认行为且以主表可见行为准 (拍板 D11)")
    assert "e.isComposing" in s and "keyCode === 229" in s, "缺 IME 组合期守卫 (同 escRetreat 口径)"
    assert 'document.addEventListener("keydown", selectAllVisible)' in text, "selectAllVisible 须命名函数注册"


def test_batch_copy_paths_and_open_links() -> None:
    """批量复制与打开 (拍板 D7/D8/D14): 复制走双链路降级低层 copyText (clipboard 优先,
    execCommand 兜底); 批量每行一个 memory-bank/<link>, 顺序 = 主表可见序 + 不可见选中行
    按全量序追加; 打开 >5 先 confirm, 取消则不动; 被弹窗拦截 (open 返回 null) 走 showError
    提醒引导允许弹窗 —— 2026-10-31 验收反馈: 静默失效用户无从知晓。"""
    text = SHELL.read_text(encoding="utf-8")
    assert "function copyText(" in text and "navigator.clipboard" in text and "execCommand" in text, (
        "缺剪贴板双链路低层 copyText"
    )
    cp = re.search(r"function copyPaths\(links\) \{(.*?)\n\}", text, re.S)
    assert cp, "缺 copyPaths"
    c = cp.group(1)
    assert 'links.length === 1' in c and '"memory-bank/" + links[0]' in c, "单条须直出 memory-bank/<link>"
    assert "aFiltered()" in c, "批量复制顺序必须以主表可见序为基准 (拍板 D8)"
    assert '.join("\\n")' in c, "批量复制须每行一个 (join 换行)"
    ol = re.search(r"function openLinks\(links\) \{(.*?)\n\}", text, re.S)
    assert ol, "缺 openLinks"
    o = ol.group(1)
    assert "links.length > 5" in o and "confirm(" in o, "批量打开 >5 缺二次确认 (拍板 D7/D14)"
    assert "window.open(MB + l" in o, "打开须走 MB 前缀路由 (file:// 与 http 双模式)"
    assert "if (!window.open(" in o and "blocked" in o, "缺弹窗拦截检测 (open 返回 null 须记账)"
    assert "showError(" in o and "Esc" in o, "拦截须走 showError 提醒引导允许弹窗 (静默失效 = 2026-10-31 验收反馈)"


# --------------------------------------------------------------------------- 置顶区交互 (折叠 / 单击)


def test_pin_zone_collapse_toggle(tmp_path) -> None:
    """2026-11-03 用户要求: 置顶区标题旁加折叠 / 展开控件 —— 收起后标题行与展开入口仍可见
    (箭头方向随 .collapsed 旋转), 且折叠只动置顶区**主体**, 不重渲染整表 (重建 innerHTML 会把
    键盘焦点从按钮丢回 body)。状态按仓库既有做法落 localStorage (同 PINS_KEY 口径, try/catch
    兜底; boot 唯一装载点, derive 不碰 —— 否则 30s 轮询会把用户收起的区又展开)。
    按钮为原生 <button>: 可聚焦, 回车 / 空格原生触发 click, 无障碍态走 aria-expanded + aria-controls。
    JS 用 node 回放真实函数体 (applyPinCollapse / togglePinCollapsed / savePinCollapsed)。"""
    text = SHELL.read_text(encoding="utf-8")
    assert 'const PIN_COLLAPSE_KEY = "mb-nav-pin-collapsed"' in text, "缺折叠态存储键常量"
    assert "pinCollapsed: false" in text, "S 缺 pinCollapsed 会话 / 持久状态字段"
    assert "function loadPinCollapsed" in text and "function savePinCollapsed" in text, "缺折叠态存 / 读函数"
    assert "function applyPinCollapse" in text and "function togglePinCollapsed" in text, "缺折叠应用 / 切换单点"

    btn = re.search(r'<button class="pztoggle" id="pzToggle".*?>', text, re.S)
    assert btn, "置顶区标题行缺折叠按钮 #pzToggle"
    markup = btn.group(0)
    assert 'type="button"' in markup, "折叠控件必须是原生 button (可聚焦, 回车 / 空格可触发)"
    assert 'aria-expanded="' in markup and 'aria-controls="pzBody"' in markup, "缺无障碍展开态 / 受控区属性"
    assert "aria-label=" in markup, "图标按钮缺无障碍名称"
    css = _shell_css()
    assert ".pinzone.collapsed .pztoggle svg" in css, "收起态缺箭头方向变化 (状态须可见)"
    assert ".pztoggle:focus-visible" in css, "折叠按钮缺键盘焦点可见样式"

    zone = re.search(r"function renderPinZone\(\) \{(.*?)\n\}", text, re.S)
    assert zone and "applyPinCollapse()" in zone.group(1), "渲染末尾必须应用折叠态 (轮询重画后仍收起)"
    assert 'id="pzBody"' in zone.group(1), "置顶区主体缺受控容器 #pzBody (aria-controls 目标)"
    click = re.search(r'\$\("pinZone"\)\.addEventListener\("click", e => \{(.*?)\n  \}\);', text, re.S)
    assert click and "togglePinCollapsed()" in click.group(1), "折叠按钮点击未接切换单点 (委托里缺早退分支)"

    boot = re.search(r"function boot\(\) \{(.*?)\n\}", text, re.S)
    assert boot and boot.group(1).count("S.pinCollapsed = loadPinCollapsed()") == 1, (
        "折叠态装载点必须全壳唯一 (只在 boot 装载一次, 否则刷新即丢)"
    )
    derive = re.search(r"function derive\(\) \{(.*?)\n\}", text, re.S)
    assert derive and "pinCollapsed" not in derive.group(1), "derive() 碰折叠态 = 30s 轮询把收起洗掉"

    node = shutil.which("node")
    if not node:
        pytest.skip("node 不在 PATH (与仓库其余 JS 守阵同口径)")
    apply_body = re.search(r"function applyPinCollapse\(\) \{(.*?)\n\}", text, re.S)
    toggle_body = re.search(r"function togglePinCollapsed\(\) \{(.*?)\n\}", text, re.S)
    save_src = next((ln for ln in text.splitlines() if ln.startswith("function savePinCollapsed()")), None)
    assert apply_body and toggle_body and save_src, "折叠函数结构搬家要同步本守阵"
    key = re.search(r'const PIN_COLLAPSE_KEY = "(.*?)";', text).group(1)
    probe = tmp_path / "pin_collapse_probe.js"
    probe.write_text(
        "const PIN_COLLAPSE_KEY = " + json.dumps(key) + ";\n"
        "const store = {};\n"
        "const localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };\n"
        "const S = { pinCollapsed: false };\n"
        "const cls = new Set();\n"
        "const zone = { hidden: false, classList: { toggle: (n, on) => { if (on) cls.add(n); else cls.delete(n); }, "
        "contains: n => cls.has(n) } };\n"
        "const btn = { attrs: {}, setAttribute(k, v) { this.attrs[k] = String(v); } };\n"
        "const bodyEl = { hidden: false };\n"
        "const els = { pinZone: zone, pzToggle: btn, pzBody: bodyEl };\n"
        "function $(id) { return els[id]; }\n"
        "function applyPinCollapse() {" + apply_body.group(1) + "\n}\n" + save_src + "\n"
        "function togglePinCollapsed() {" + toggle_body.group(1) + "\n}\n"
        "const snap = () => [zone.classList.contains('collapsed'), btn.attrs['aria-expanded'], bodyEl.hidden, "
        "String(store[PIN_COLLAPSE_KEY])].join(',');\n"
        "applyPinCollapse();\n"
        "console.log('init=' + snap());\n"
        "togglePinCollapsed();\n"
        "console.log('after1=' + snap());\n"
        "togglePinCollapsed();\n"
        "console.log('after2=' + snap());\n",
        encoding="utf-8",
    )
    out = subprocess.run([node, str(probe)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    got = dict(line.split("=", 1) for line in out.stdout.strip().splitlines())
    assert got.get("init") == "false,true,false,undefined", f"初始应为展开态: {got}"
    assert got.get("after1") == "true,false,true,1", f"首次点击应收起且落盘: {got}"
    assert got.get("after2") == "false,true,false,0", f"再次点击应展开且落盘: {got}"


def test_pin_row_click_opens_drawer_via_shared_path(tmp_path) -> None:
    """2026-11-03 用户要求: 置顶区条目单击与主区对齐 —— 打开右侧抽屉, 且**复用**同一套详情渲染 /
    打开逻辑 (openRowDetail -> renderDrawer), 不再各写一份。node 回放真实 openRowDetail 函数体,
    断言同一 link 在双区都挂 sel, 且抽屉渲染函数被同一个入参调用。"""
    text = SHELL.read_text(encoding="utf-8")
    shared = re.search(r"function openRowDetail\(link\) \{(.*?)\n\}", text, re.S)
    assert shared, "缺明细打开单点 openRowDetail (主表与置顶区必须共用)"
    body = shared.group(1)
    assert "S.sel = link" in body and "renderDrawer(link)" in body, "单点必须改 S.sel 并调 renderDrawer"
    assert body.count("renderDrawer(") == 1, "抽屉渲染只许调用一次 (不另写第二套打开逻辑)"

    main = re.search(r'\$\("aRows"\)\.addEventListener\("click", e => \{(.*?)\n  \}\);', text, re.S)
    zone = re.search(r'\$\("pinZone"\)\.addEventListener\("click", e => \{(.*?)\n  \}\);', text, re.S)
    assert main and "openRowDetail(tr.dataset.link)" in main.group(1), "主表单击未走共用单点"
    assert zone and "openRowDetail(row.dataset.link)" in zone.group(1), "置顶区单击未走共用单点"
    assert "window.open(MB + row.dataset.link" not in zone.group(1), "置顶区仍残留旧的「单击直开原文」路径"

    node = shutil.which("node")
    if not node:
        pytest.skip("node 不在 PATH (与仓库其余 JS 守阵同口径)")
    probe = tmp_path / "pin_row_probe.js"
    probe.write_text(
        "const mkRow = link => { const s = new Set(); return { dataset: { link }, classList: { "
        "add: n => s.add(n), remove: n => s.delete(n), contains: n => s.has(n) } }; };\n"
        "const rows = ['a.md', 'b.md'].map(mkRow);\n"
        "rows[0].classList.add('sel');\n"
        "const document = { querySelectorAll: sel => sel.includes('tr.sel') "
        "? rows.filter(r => r.classList.contains('sel')) : rows.slice() };\n"
        "const drawer = [];\n"
        "function renderDrawer(link) { drawer.push(link); }\n"
        "const S = { sel: null };\n"
        "function openRowDetail(link) {" + body + "\n}\n"
        "openRowDetail('b.md');\n"
        "console.log('sel=' + S.sel);\n"
        "console.log('drawer=' + drawer.join(','));\n"
        "console.log('a=' + rows[0].classList.contains('sel'));\n"
        "console.log('b=' + rows[1].classList.contains('sel'));\n",
        encoding="utf-8",
    )
    out = subprocess.run([node, str(probe)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    got = dict(line.split("=", 1) for line in out.stdout.strip().splitlines())
    assert got.get("sel") == "b.md", f"S.sel 未指向被点条目: {got}"
    assert got.get("drawer") == "b.md", f"抽屉未走 renderDrawer 同一条路径: {got}"
    assert got.get("a") == "false" and got.get("b") == "true", f"双区 sel 高亮未同步: {got}"
