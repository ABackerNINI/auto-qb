"""test_webui_static_skins_widget 测试计划: webui 前端资产静态守阵: 皮肤清单 / CSS / 挂件类名

## 测试计划(每个测试函数一条)
- test_frontend_search_syntax_wiring: 搜索匹配**服务端单点**的前端接线守阵 —— 清除钮 @mousedown.prevent 成对(焦点态清除失灵回归)/前端不得复活任何文本匹配实现(filters.js _parseSearchQuery 等四函数、hr.js/shows.js 旧整句 includes、app.js searchHitsQ 均已删, 复活即红)/filteredTorrents 必须消费 searchHits
- test_frontend_search_pending_no_collapse: 搜索待响应期空命中集不得接管列表(2026-10-07 修详情面板/流量图搜索跳动) —— view.js searchPending 生命周期(输入武装防抖即置位/doSearch 直达入口补武装/resetSearch 清除/落袋且过代际守卫后清除) + filters.js _searchGateActive 单点(待响应且命中集未落袋 = 门不生效, 两个派生 filteredTorrents/filteredGroups 都走它; 渐进输入命中集非空仍按旧集过滤) + 三皮肤 .layout min-height: calc(100vh - var(--head-h)) 撑满首屏(停靠面板 sticky 锚点与列表长短无关, 筛到短列表不再脱锚跳)
- test_frontend_hr_safety_wiring: 删除安全档位前端接线守阵 —— hr.js 的 token 映射表与后端 resolve.py 的 SRC_* 常量逐字一致、做种时长列每套 UI 2 处换绑 hrDurClass/hrSrcClass(计划 26-10-11-1722 P2 起明细成员单元格收敛为单份 <aq-member-cells> 渲染器, 触发面 3→2, 该渲染器由辅种页/追剧页共用)+ 挂 hrSrcFull/hrSrcHalf 底线与 hrPopEnter 触发 + 来源与已排除文案都走 hrDurHint 进 title(行内不留 chip) + 弹窗单例 DOM 每套 UI 恰一份、三套 CSS 的 hr-warn/hr-line/hr-pop 成对定义、js 引用的 m.hr_* 字段都在后端 hr_view_fields 键集里(字段打错 = 页面静默空白)
- test_frontend_site_alert_icon_wiring: 站点 chip 改色表达守阵(计划 26-10-19-2206 S4, 取代 26-10-19-2007 的两槽口径) —— 站点问题走**颜色**(缺配置橙底+虚线下边 / tracker 报错红底)、命令结果走**图标**且固定放站点名之后: 三皮肤样式键集相等(含 reduced-motion 降级/搜索命中让出底色/明细行染色)/模板三处 cell 只剩一个图标槽且 tooltip 挂整块 chip/旧图标类 `.sa` 零残留/token->符号单点只含命令结果四种
- test_drawer_tpl_variant_interaction_single_point: 变体交互单点定型守阵(计划 26-10-12-0527 U5①) —— drawer_tpl/*.js 全目录扫 ui.sort(手搓排序状态机不允许在任何变体复活); 凡声明 tableId+rowsFn(桥表格变体)的文件**声明即受检**, 另强制零表格容器列宽 grid(列宽唯一来源 = 引擎列集 computed; 版式 grid 卡片/双栏/图例是 D5 保留面) —— 未来新变体接引擎即自动落入本守阵, 无需改守阵, 即「定型」之义

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console、只换令牌取值与视觉规则(类名/DOM/令牌名不动), 上述按 _UI_ALL 枚举的守阵随常量自动收编;
  单独点名的守阵(表头 a11y 落点/令牌 parity/按钮成对/HR 各族成对面)已显式加 flux 档。
"""

import json

import os

import re

import shutil

import subprocess

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_files,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
    _tpl_path,
)


def test_drawer_tpl_variant_interaction_single_point():
    """变体交互单点定型守阵(计划 26-10-12-0527 U5①)。

    判据**按声明识别(声明即受检)**: drawer_tpl/*.js 全目录扫 ui.sort —— 手搓排序状态机
    (ui.sortKey/ui.sortDir)不允许在任何变体复活; 凡声明 tableId+rowsFn(桥表格变体)的文件
    另强制零表格容器列宽 grid —— 列宽唯一来源 = 引擎列集(columns.js computed), 变体 CSS
    不得对表格容器(.group-head/.group-row/旧手搓容器命名族 .dtNN-h|r|head|row|gcols)写
    grid-template-columns。版式 grid(卡片栅格/双栏/图例, 含 04 的 .group-table 双列卡片栅格
    —— 卡片布局不是列宽, 等高由 test_drawer_tpl_trackers_card_uniform_height 另行钉住)是
    D5 保留面, 不在禁令内。未来新变体接引擎(tableId+rowsFn 落地)即自动落入本守阵,
    无需改守阵 —— 即「定型」之义; 已知八桥变体清单兜底(判据不得静默缩水)。
    """
    import os
    import re
    shared = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static", "shared"
    )
    tpl_dir = os.path.join(shared, "drawer_tpl")
    # 已知八桥变体兜底: 每个都必须被「声明即受检」识别到(识别失灵 = 判据空转)
    known_bridge = {
        "07-peers-dashboard-tall.js",
        "08-peers-groups-low.js",
        "09-peers-density-collapsed.js",
        "04-trackers-status-cards-tall.js",
        "05-trackers-health-groups-low.js",
        "06-trackers-table-collapsed.js",
        "10-content-tree-detail-tall.js",
        "11-content-treegrid-batch-low.js",
    }
    # 表格容器选择器族(⑪ 同口径): 引擎行/列头容器 + 旧手搓表格容器命名族(.dtNN-list 等版式
    # 类不在此族 —— 04 的 .group-table 卡片栅格与 07 的 .group-table 表壳栅格是 D5 保留面)
    colgrid_sel = re.compile(r"\.group-head|\.group-row|\.dt\d\d-(?:h|r|head|row|gcols)\b")

    seen_bridge = set()
    for fname in sorted(f for f in os.listdir(tpl_dir) if f.endswith(".js")):
        text = open(os.path.join(tpl_dir, fname), encoding="utf-8").read()
        # 全目录: 手搓排序状态机零残留(排序并引擎 D3, 任何变体不得复活)
        assert "ui.sort" not in text, f"{fname} 残留手搓排序状态机 ui.sort(U5 定型: 排序归引擎单点)"
        # 声明即受检: tableId+rowsFn 双声明 = 桥表格变体 → 列宽 grid 禁令生效
        if re.search(r"\btableId\s*:", text) and re.search(r"\browsFn\s*:", text):
            seen_bridge.add(fname)
            for ln in text.splitlines():
                if "grid-template-columns" in ln and colgrid_sel.search(ln):
                    raise AssertionError(f"{fname} 表格容器残留列宽 grid 硬编码(U5 定型 Q4: 列宽归引擎): {ln.strip()[:80]}")
    missing = known_bridge - seen_bridge
    assert not missing, f"已知桥变体未被「声明即受检」识别到(判据空转或声明丢失): {sorted(missing)}"


def test_frontend_search_syntax_wiring():
    """搜索匹配**服务端单点**的前端接线守阵(2026-09-26 统一, 治"同一语义修三遍")

    两类"pytest 全绿但交互废掉 / 前端再长出第二套匹配实现"的故障形态, 一律机械钉住:
    1. 顶栏搜索清除钮必须挂 @mousedown.prevent —— 缺了它, 按下瞬间输入框失焦收窄
      (focus 时 240→300px 的宽度过渡回退), 绝对定位在右沿的按钮随收窄移出光标,
      click 落空 => "有焦点时点 x 清不掉, 无焦点正常"; 两套 index.html 成对断言。
    2. 三页(辅种/种子/追剧)搜索命中一律消费服务端 searchHits(views.py::search_torrents 的
      行级裁决, 候选行 = 名字/站点/分类/路径/标签/文件名): 前端**不得再出现**任何文本匹配
      实现 —— 26-09-26 统一前 filters.js(_parseSearchQuery/_searchNorm/_torrentTextMatch)、
      hr.js(更早的整句 includes)、shows.js(剧名整句 includes)各持一份, 同一语义
      (恶女 10 / 季包"cat 12")前后端修了三遍; 复活任何一个即与单点漂移, 直接红。
      语法(词 AND/-排除/短语/归一)行为级用例在服务端侧: test_parse_query_tokens /
      test_search_torrents_*(对账守阵已无对象 —— 客户端没有解析器了)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    filters_js = open(os.path.join(shared, "filters.js"), encoding="utf-8").read()
    hr_js = open(os.path.join(shared, "hr.js"), encoding="utf-8").read()
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    shows_js = open(os.path.join(shared, "shows.js"), encoding="utf-8").read()

    # 1. 清除钮 mousedown.prevent 成对(两套模板的 search-clear 按钮逐个检查)
    for theme in _UI_ALL:
        html = _ui_aggregate(theme)
        m = re.search(r'<button[^>]*class="search-clear"[^>]*>', html)
        assert m, f"{theme} 模板找不到 search-clear 按钮"
        tag = m.group(0)
        assert "@mousedown.prevent" in tag, f"{theme} search-clear 缺 @mousedown.prevent(焦点态清除失灵回归)"
        assert '@click="clearSearch"' in tag, f"{theme} search-clear 缺 clearSearch 接线"

    # 2. 前端无第二匹配实现(反漂移: 任何一个复活即红); 三页接线走 searchHits
    # (注释里允许引用旧函数名讲历史, 故断言"名字+括号"—— 定义或调用才算复活)
    for name in ("_parseSearchQuery", "_searchNorm", "_torrentTextMatch", "_torrentSearchPass"):
        assert not re.search(rf"{name}\s*\(", filters_js), \
            f"filters.js 复活了客户端匹配 {name}(搜索匹配单点在 views.py, 复活即漂移)"
    assert "_torrentTextMatch" not in hr_js, "hr.js 不得再留 _torrentTextMatch 旧整句实现(双实现漂移)"
    assert 'searchHitsQ' not in app_js, "app.js 残留 searchHitsQ(客户端匹配时代的陈旧守卫, 已随单点化删除)"
    assert "hits.has(r.hash)" in filters_js, "filteredTorrents 未消费 searchHits(种子页搜索断线)"
    assert "(s.name || \"\").toLowerCase().includes(q)" not in shows_js, \
        "shows.js 复活了剧名整句 includes 旧匹配(剧名命中应来自服务端名字行)"


def test_frontend_search_pending_no_collapse():
    """搜索待响应期空命中集不得接管列表守阵(2026-10-07 修详情面板/流量图搜索/筛选时跳动)

    两层缺陷各钉一处, 都是"首词待响应窗把整个列表塌成 0 行"的上下游:
    1. view.js/filters.js: 首词的 searchHits 还是空集(没有"上一查询"可沿用), filteredTorrents/
      filteredGroups 的命中门照常生效 => 防抖 400ms + 请求往返的整个待响应窗里列表塌成 0 行:
      文档高塌掉 -> 滚动位置被钳回 0(列表中部搜一次整页跳顶), 底部停靠面板失去 sticky 锚点
      跟着弹(实测 docH 18582→800→1141、面板 top 430↔416 反复横跳)。
      钉住 searchPending 生命周期(输入武装防抖即置位 / doSearch 直达入口补武装 / resetSearch
      清除 / 落袋且过代际守卫后清除)与 _searchGateActive 单点(两个派生都走它, 任何一个绕开
      单点现写命中门即红; 渐进输入命中集非空时仍按旧集过滤, 标准 search-as-you-type 不变)。
    2. 三皮肤 .layout min-height 撑满首屏: 停靠面板(.drawer-dock)的 sticky 吸底只在"自然落点
      低于视口下界"时生效, 列表被筛短(真 0 命中/筛选到短列表)后文档变矮, 面板脱锚跟着内容
      末尾上浮(视口越高跳得越多)。内容列恒撑满(顶栏实测高走既有单点 --head-h)后锚点稳定。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    view_js = open(os.path.join(shared, "view.js"), encoding="utf-8").read()
    filters_js = open(os.path.join(shared, "filters.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()

    # 1a. searchPending 声明与生命周期(缺任何一环 = 待响应窗判定失真, 空集照样接管或永挂 pending)
    assert "searchPending: false" in state_js, "state.js 缺 searchPending 声明(待响应期判定无载体)"
    assert view_js.count("this.searchPending = true") == 2, \
        "view.js 武装点应恰两处(onSearchInput 防抖武装 + doSearch 直达入口补武装)"
    on_input = view_js[view_js.index("onSearchInput(event)"):]
    assert on_input.index("this.searchPending = true") < on_input.index("setTimeout(() => this.doSearch()"), \
        "onSearchInput 必须在武装防抖前置位 pending(否则首词防抖窗 400ms 里空集照样接管列表)"
    assert "this.searchPending = false;" in view_js[view_js.index("resetSearch()"):view_js.index("async doSearch")], \
        "resetSearch 必须清除 pending(清空搜索立即恢复全列表, 不得挂死在待响应态)"
    landing = view_js[view_js.index("this.searchHits = new Set(results.map"):]
    assert "this.searchPending = false" in landing[:landing.index("this.searchUncovered")], \
        "doSearch 落袋必须在写命中集后、派生消费前清除 pending(迟清一帧 = 真结果被当待响应态跳过)"
    # 落袋清除必须排在代际守卫**之后**(失配弃单不得清掉新词在途的 pending)
    do_search = view_js[view_js.index("async doSearch"):]
    assert do_search.index("(this.searchQuery || \"\").trim() !== q") < do_search.index("this.searchPending = false;"), \
        "doSearch 落袋清除 pending 必须在请求代际守卫之后(失配弃单不得清新词的待响应态)"

    # 1b. 命中门收单点: 两个派生都走 _searchGateActive, 不得绕开单点现写命中门
    assert "_searchGateActive(q)" in filters_js, "filters.js 缺 _searchGateActive 单点"
    assert filters_js.count("_searchGateActive(") >= 3, \
        "_searchGateActive 定义 + 两个派生(filteredTorrents/filteredGroups)都要消费"
    assert "if (!q) return base;" not in filters_js, \
        "filteredGroups 残留旧门 `if (!q) return base;`(未走 _searchGateActive, 待响应空集照样塌列表)"
    assert re.search(r"if \(!this\._searchGateActive\(q\)\) return base;", filters_js), \
        "filteredGroups 的文本段必须整段走 _searchGateActive 门"
    assert re.search(r"const gate = this\._searchGateActive\(q\);", filters_js) and "if (gate && !hits.has(r.hash)) continue;", \
        "filteredTorrents 的命中门必须走 _searchGateActive(绕开单点现写 = 待响应塌列表回归)"

    # 2. 三皮肤 .layout min-height 撑满首屏(dock sticky 锚点与列表长短无关)
    for theme in _UI_ALL:
        css_path = os.path.join(STATIC_ROOT, theme, "css", "views.css" if theme == "prism" else "components.css")
        css = open(css_path, encoding="utf-8").read()
        m = re.search(r"\.layout \{[^}]*\}", css, re.S)
        assert m, f"{theme} 找不到 .layout 规则"
        assert "min-height: calc(100vh - var(--head-h" in m.group(0), \
            f"{theme} .layout 缺 min-height 撑满首屏(列表筛短后停靠面板脱锚跳)"


def test_frontend_hr_safety_wiring():
    """删除安全档位的前端接线守阵(2026-09-25, 计划 webui-hr-safety-display)

    四类"字段/令牌打错 = pytest 全绿但页面静默空白或配色失效"的故障形态, 一律机械钉住:
    1. hr.js 的 token 映射表(HR_SRC_CLASSES / HR_SRC_BUCKETS)必须与后端 resolve.py 的 SRC_* 常量
      逐字一致 —— 来源档位是前后端契约, 打错字来源标记静默消失; 三档类名驱动单元格底线三编码(CSS),
      文字结论改由悬停弹窗承载(原生 title 已移除, 避免与弹窗叠出被遮挡的冗余提示);
    2. 做种时长列在两套 UI 各 3 处(组内成员/种子页/明细)都必须换绑 hrDurClass + hrSrcClass, 并由
      hrSrcFull/hrSrcHalf 挂底线 + hrPopEnter 触发 —— 漏一处那一列就不显示安全档位/来源线/悬停弹窗;
      弹窗单例 DOM(teleport body)每套 UI 恰一份(26-09-26-webui-hr-popup 起 :title 换成悬停弹窗触发);
      要求时长的渲染门只认「已做种非空 + 有要求」, 不得依赖 hr_triggered(2026-09-29 实报:
      未核/在线行被一并藏掉要求, 只剩孤立的来源芯片);
    3. hr-unk / hr-fail / hr-line 新样式必须三套 CSS 成对定义(改这里时同步另一套的纪律);
      hr-pop 弹窗规则(浮层/箭头/双轨)同理成对;
      整格线(在线)必须挂**文字包裹层** .dur-body 而不是单元格 .m-dur —— 行是 grid, 单元格被拉满整列宽,
      挂它上面 width:100% 的空 <i> 就画成整列一条(线随列宽不随文字, 2026-09-29 真机实报);
    4. 前端 js 里引用的 m.hr_* 字段必须都在后端 hr_view_fields 的键集里(字段一致性守阵,
      M4 设置页守阵同款思路)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    hr_js = open(os.path.join(shared, "hr.js"), encoding="utf-8").read()
    resolve_py = open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "hr", "resolve.py"),
        encoding="utf-8",
    ).read()

    # 1. 来源 token 契约: 后端常量集 == 前端两张映射表的键集
    src_tokens = set(re.findall(r'^SRC_[A-Z_]+ = "([a-z_]+)"', resolve_py, re.M))
    assert len(
        src_tokens
    ) == 6, f"resolve.py 的 SRC_* 常量应为 6 个(v3: 删 policy/local_exempt; 26-09-30 计划 hr-trigger-semantics: 删 unverified), 实测 {sorted(src_tokens)}"
    assert "unverified" not in src_tokens, "SRC_UNVERIFIED 应已随「未核实」灰档退役(本地统一 SRC_LOCAL)"

    def _map_keys(name):
        m = re.search(rf"const {name} = \{{(.*?)\}};", hr_js, re.S)
        assert m, f"hr.js 缺 const {name}"
        return set(re.findall(r"([a-z_]+):", m.group(1)))

    assert _map_keys("HR_SRC_CLASSES") == src_tokens, "HR_SRC_CLASSES 键与后端 SRC_* 不一致"
    assert _map_keys("HR_SRC_BUCKETS") == src_tokens, "HR_SRC_BUCKETS 键与后端 SRC_* 不一致"
    # 来源文案不再进原生 title(2026-09-29 晚: 原生 title 与悬停弹窗叠出, 出现「来源:未核实」等
    #   被弹窗遮挡的冗余提示; 来源改由 hrSrcClass → CSS 底线编码, 文字结论在悬停弹窗内)。
    #   故 hrDurHint / HR_SRC_TITLES / HR_EXCLUDED_TITLE 整套应已退役。
    assert "hrDurHint" not in hr_js, "hr.js 仍残留 hrDurHint(来源+已排除的 title 组装) —— 原生 title 已移除"
    assert "HR_SRC_TITLES" not in hr_js, "hr.js 仍残留 HR_SRC_TITLES —— 来源文案不再进 title"
    assert "HR_EXCLUDED_TITLE" not in hr_js, "hr.js 仍残留 HR_EXCLUDED_TITLE —— 已排除文案不再进 title"
    # 四个安全档位(2026-09-25 用户修正起 failed=未达标终态红档; 2026-09-30 计划
    # hr-trigger-semantics: unknown 灰档退役, 换 warning 黄档=疑似辅种): warning 由前端映射 hr-warn 黄
    for name in ("HR_SAFETY_CLASSES", "HR_SAFETY_BUCKETS"):
        assert _map_keys(name) == {"danger", "failed", "safe", "warning"}, f"{name} 键集应为四个安全档位"

    # 2. 做种时长列换绑 + 弹窗单例: 每套 UI 2 处触发面 / 各 1 份弹窗 DOM
    # !触发面自 3 收敛为 2(计划 26-10-11-1722 P2): 明细成员单元格的两份副本(辅种页 / 追剧集)
    #   合并为**单份**渲染器 <aq-member-cells>(模板在 tpl/xtpl.html#tpl-aq-member-cells), 该渲染器
    #   由两页共用 ⇒ 计数 3 → 2 是收敛的结果, 不是漏换绑。!渲染器里的行为经 `$root.` 回调根实例
    #   (根数据只在根实例上), 故下列 pattern 两种形态都收 —— 裸名(页面模板) / `$root.` 前缀(渲染器)。
    #   两页共用关系由 test_frontend_table_shell_single_point 与 _scan_column_cells_paired 兜住
    #   (两处调用点都必须用 <aq-member-cells>), 覆盖不丢。
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        for pattern, want in (
            (r':class="\[(?:\$root\.)?hrDurClass\(m\), (?:\$root\.)?hrSrcClass\(m\)\]"', 2),
            (r'v-if="(?:\$root\.)?hrSrcHalf\(m\)"', 2),  # 半格线(本地 / 未核实)画在数值上
            (r'v-if="(?:\$root\.)?hrSrcFull\(m\)"', 2),  # 整格线(在线)画在**文字包裹层**上
            (r'class="dur-body"', 2),  # 文字包裹层: 整格线随文字不随列宽(挂单元格 = 随列宽)
            (r'@mouseenter="(?:\$root\.)?hrPopEnter\(\$event, m\)"', 2),
            (r'@mouseleave="(?:\$root\.)?hrPopLeave"', 3),  # 2 处触发面 + 弹窗自身(移入弹窗不隐藏)
            (r'<teleport to="body">', 1),
            (r'ref="hrPop"', 1),
        ):
            got = len(re.findall(pattern, html))
            assert got == want, f"{ui} 里 `{pattern}` 应出现 {want} 处, 实测 {got}"
        # 旧绑定不得残留(换绑遗漏的形态)
        assert ':class="hrTimeClass(m)"' not in html, f"{ui} 仍有做种时长列挂着旧 hrTimeClass —— 漏换绑"
        assert "hrSrcBadge" not in html, f"{ui} 仍挂着旧的 2 字来源徽标 hrSrcBadge —— 漏换绑"
        assert "hrDurTitle" not in html, f"{ui} 仍有做种时长列挂原生 :title —— 应已换悬停弹窗触发"
        assert ':title="hrDurHint(m)"' not in html, f"{ui} 做种时长列仍挂原生 :title(hrDurHint) —— 应只靠悬停弹窗"
        # 行内文字 chip 零残留(2026-09-29 非文字化的对象就是这两个 chip, 复活即列宽问题回归)
        assert 'class="hr-src"' not in html, f"{ui} 做种时长列仍有 .hr-src 文字 chip —— 文案应只走 title"
        assert ">已排除<" not in html, f"{ui} 做种时长列仍有「已排除」文字 chip —— 应已撤进 title"
        # 要求时长必须「有要求就显示」(2026-09-29 用户实报: 未核/在线行只剩来源芯片, 看不到要求):
        # 门只能是「已做种非空 + 有要求」—— 依赖 hr_triggered 会把未触发行连要求一起藏掉。
        # !自计划 26-10-11-1722 P3 起该列也搬进了渲染器(种子页 <aq-torrent-cells>), 行为经 $root
        #   回调根实例 —— 故 pattern 两种形态都收(裸名 / $root. 前缀), 与上方其它换绑项同口径。
        assert re.search(r'v-if="(?:\$root\.)?cellSeedingTime\(m\) && m\.hr_req_time"', html), \
            f"{ui} 做种时长列的要求渲染门被改 —— 应只按 hr_req_time 判定(未触发行也要看得到要求)"

    # 弹窗「无时长要求」收起条件: 不得再把 unverified 包进去(它有本地要求, 收起就看不到),
    # 真放行/免罪(义务已了)仍收起——2026-09-29 实报后定稿
    collapse = re.search(r"if \(\[([^\]]*)\]\.includes\(src\) \|\| !\(req > 0\)\)", hr_js)
    assert collapse, "hr.js 弹窗的「无时长要求」收起条件找不到了 —— 渲染规则被改? 同步本守阵"
    assert "unverified" not in collapse.group(1), "未核实行不得收起为「无时长要求」(本地有要求, 收起即失真)"
    assert "site_released" in collapse.group(1) and "site_exempt" in collapse.group(1), "真放行/免罪仍应收起轨道"

    # 3. 新样式各套 CSS 成对(flux 收编 plan 26-10-31-2316 S5)
    atlas_css = _ui_css_aggregate("atlas")
    prism_css = _ui_css_aggregate("prism")  # issue 26-10-20-2231: hr-pop 段已并入 prism/css/dialogs.css, 改读聚合
    console_css = _ui_css_aggregate("console")
    flux_css = _ui_css_aggregate("flux")
    for css, name in (
        (atlas_css, "atlas css 聚合(link 序)"), (prism_css, "prism css 聚合(link 序)"),
        (console_css, "console css 聚合(link 序)"), (flux_css, "flux css 聚合(link 序)")
    ):
        for rule in (
            ".m-pair.hr-warn",
            ".m-pair.hr-fail",
            ".m-dur .hr-line",
            ".hr-pop",
            ".hp-arrow",
            ".hp-gauge",
            ".hp-badge",
            # 排除命中行的中性灰档(2026-10-02): 弹窗 lane=excluded 的点与结论色, 三套成对
            ".hp-dot.excluded",
            ".hp-verdict.excluded",
        ):
            assert rule in css, f"{name} 缺 {rule} 规则 —— 三套 UI 必须成对定义"
        # 死样式零残留: 最后一个 .hr-src 消费方(已排除 chip)已撤进 title
        assert ".m-pair .hr-src" not in css, f"{name} 仍留着 .hr-src chip 样式 —— 已无消费方, 应删除"
        assert "z-index: 140" in css, f"{name} 缺弹窗 z-index: 140(须高于 ctx-menu 100 与 speed-pop 131)"
        # 半格线是空 <i>: 只给 left:0 而 width:auto 会收缩成 0 —— 线整条不可见(2026-09-29 实报)
        for half in (".m-dur .dur-val > .hr-line", ".m-dur.src-local .hr-line"):
            assert half in css, f"{name} 缺 {half} 规则 —— 本地的半格线会消失"
        # 死档位样式零残留(2026-09-30 计划 hr-trigger-semantics: unknown/unverified 随灰档退役)
        assert ".m-pair.hr-unk" not in css, f"{name} 仍留着 .hr-unk 死样式 —— 未核实档已退役"
        assert ".src-unver" not in css, f"{name} 仍留着 .src-unver 死样式 —— unverified 来源档已退役"
        assert re.search(r"\.m-dur \.dur-val > \.hr-line \{[^}]*width: 100%", css), \
            f"{name} 半格线没写显式 width:100% —— 空 <i> 的 width:auto 会收缩成 0(线整条不可见)"
        # 整格线(在线)必须挂文字包裹层 .dur-body —— 挂 .m-dur 上会随列宽(2026-09-29 真机实报:
        # 行是 grid, 单元格被拉满整列宽, width:100% 的空 <i> 画成整列一条, 与「随文字」相反)
        for full in (".m-dur .dur-body {", ".m-dur .dur-body > .hr-line"):
            assert full in css, f"{name} 缺 {full} 规则 —— 在线的整格线会随列宽而不是随文字"
        assert re.search(r"\.m-dur \.dur-body > \.hr-line \{[^}]*width: 100%", css), \
            f"{name} 整格线没写显式 width:100% —— 空 <i> 的 width:auto 会收缩成 0(线整条不可见)"
        assert ".m-dur > .hr-line" not in css, \
            f"{name} 整格线仍挂在单元格 .m-dur 上 —— 单元格是 grid item 会被拉满列宽, 线随列宽不随文字"
        # 做种时长单元格不得用 padding 给底线留位(2026-11-03 真机实报): padding-bottom 会把**有文案**
        # 的单元格撑高 6px(整行 43.05→48.69), 种子完成后一刷新就多出一片"变高"的行; --dur-pad 只做
        # 线的下移偏移, 行底 10px 内边距足够容纳线身 —— 一旦写回 padding, 有/无文案行高不再相等。
        dur_rule = re.search(r"\.m-pair\.m-dur \{[^}]*\}", css)
        assert dur_rule, f"{name} 缺 .m-pair.m-dur 规则 —— 做种时长单元格的 --dur-pad 偏移找不到"
        assert "padding" not in dur_rule.group(0), \
            f"{name} 的 .m-pair.m-dur 又加了 padding —— 有文案/无文案行高将不再相等(43.05 vs 48.69)"
        for line_rule in (".m-dur .dur-body > .hr-line", ".m-dur .dur-val > .hr-line"):
            assert re.search(rf"{re.escape(line_rule)} \{{[^}}]*bottom: calc\(-1 \* var\(--dur-pad\)\)", css), \
                f"{name} 的 {line_rule} 没按 var(--dur-pad) 下移 —— 去掉单元格 padding 后线会压住文字"

    # 4. 前端引用的 m.hr_* 字段 ⊆ 后端 hr_view_fields 键集(字段一致性)
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent

    keys = set(QbManager.hr_view_fields(TorrentRecord.from_torrent(FakeTorrent(hash="HX"))))
    assert keys, "hr_view_fields 连空配置分支都该返回全键集"
    used = set()
    for name in sorted(os.listdir(shared)):
        if name.endswith(".js"):
            used |= set(re.findall(r"\bm\.(hr_[a-z_]+)", open(os.path.join(shared, name), encoding="utf-8").read()))
    for ui in _UI_ALL:
        used |= set(re.findall(r"\bm\.(hr_[a-z_]+)", _ui_aggregate(ui)))
    unknown = used - keys
    assert not unknown, f"前端引用了后端不存在的 HR 字段: {sorted(unknown)}(字段打错 = 页面静默空白)"


def test_frontend_site_alert_icon_wiring():
    """站点 chip 改色表达守阵(计划 26-10-19-2206 S4, 取代 26-10-19-2007 的两槽口径)

    通道分工: 站点问题(缺配置 / tracker 报错)走**颜色**, 命令结果走**图标**(固定放站点名之后)。
    三件事必须同时成立, 缺一条就是"pytest 全绿但界面废掉":
      ① 三皮肤样式**键集合相等**(漏一套 = 某皮肤下 chip 不变色/图标没颜色, 只在一套皮肤上看得见);
         缺配置的虚线底边(非颜色通道, D4)与搜索命中"让出底色改描边"(D6)同属可读性契约, 一并钉住;
      ② 站点 chip 骨架收敛为单点组件 <aq-site-chip>(issue 26-10-20-2231 / R23-B-09, 此前种子页/
         组行/集行各抄一份 11 行骨架、torrent 版还漏 search-hit): 单点模板里**一个**图标槽
         (命令结果), 三处调用点都走它, tooltip 挂整块 chip; 旧图标类(`.sa` / `sa-<token>`)
         必须零残留 —— 残留 = 某个视图还在画第二个图标;
      ③ 图标 token -> 符号映射单点在 commands.js(模板里不得出现第二份 `#i-xxx` 映射),
         且该表**只含命令结果四种 token**(站点问题不该再有图标)。
    """
    CMD_TOKENS = ("pending", "ok", "warn", "error")
    NEED = {".site-chip .sx", ".g-status.k-error .ico", ".site-chip.search-hit"}
    NEED |= {f".site-chip .sx-{t}" for t in CMD_TOKENS}
    NEED |= {".site-chip.sa-no-conf", ".site-chip.sa-tracker"}

    def _selectors(css):
        """从 CSS 文本里收集本守阵关心的选择器(注释先剥, 避免注释里的示例文字被当成规则)

        只收三类: 命令结果图标槽(.site-chip .sx*) / 站点问题变色类(.site-chip.sa-*) /
        搜索命中(.site-chip.search-hit); 另加状态列错误图标强化(.g-status.k-error)。
        种子状态色(.site-chip.seeding 等)不在本守阵范围(它们由 components.css 各自维护)。
        """
        body = re.sub(r"/\*[\s\S]*?\*/", "", css)
        keys = (".site-chip .sx", ".site-chip.sa-", ".site-chip.search-hit", ".g-status.k-error")
        found = set()
        for sel in re.findall(r"(?m)^\s*([^{}@/][^{}]*)\{", body):
            for one in sel.split(","):
                one = " ".join(one.split())
                if one.startswith(keys):
                    found.add(one)
        return found

    per_skin = {}
    for ui in _UI_ALL:
        css = _ui_css_aggregate(ui)
        per_skin[ui] = _selectors(css)
        missing = NEED - per_skin[ui]
        assert not missing, f"{ui} 缺站点 chip 样式: {sorted(missing)}"
        assert "animation: none" in css, f"{ui} 缺 prefers-reduced-motion 降级"
        # 旧图标类零残留(R6): 站点问题已改走底色, 图标类必须清零(只删模板不删样式 = 两套语义并存)
        assert "sa-no_site_conf" not in css and "sa-tracker_error" not in css, (
            f"{ui} 仍残留旧站点图标类 sa-<token> —— 站点问题已改走 chip 底色, 图标类必须清零"
        )
        assert not re.search(r"\.site-chip \.sa\b", css), f"{ui} 仍残留 .sa 图标槽规则"
        # D4: 缺配置必须带非颜色通道(虚线底边) —— 灰度/色盲下与实底红可区分
        body = re.search(r"\.site-chip\.sa-no-conf\s*\{([^}]*)\}", css)
        assert body, f"{ui} 缺 .site-chip.sa-no-conf 规则体"
        assert "dashed" in body.group(1), f"{ui} 缺配置 chip 缺虚线底边(D4 非颜色通道)"
        # D6: 搜索命中让出底色 —— 不得再用 accent 柔底占住 chip 填充
        hit = re.search(r"\.site-chip\.search-hit\s*\{([^}]*)\}", css)
        assert hit, f"{ui} 缺 .site-chip.search-hit 规则体"
        assert "--accent-soft" not in hit.group(1), (f"{ui} 搜索命中仍占 accent 柔底 —— 站点问题/种子状态的底色被吞(D6)")
        assert "inset" in hit.group(1) and "--accent-line" in hit.group(1), (f"{ui} 搜索命中未改 accent 描边(D6/R2)")
        # D9: 明细行站点文本同语义(只染文字色)
        assert ".m-site.sa-no-conf" in css and ".m-site.sa-tracker" in css, (f"{ui} 缺明细行站点文本染色规则(D9)")

    base = per_skin[_UI_ALL[0]]
    for ui in _UI_ALL[1:]:
        assert per_skin[ui] == base, (
            f"{ui} 的站点 chip 样式键集与 {_UI_ALL[0]} 不一致 —— 三皮肤必须齐备(计划 R3): "
            f"{_UI_ALL[0]}-{ui}={sorted(base - per_skin[ui])} / {ui}-{_UI_ALL[0]}={sorted(per_skin[ui] - base)}"
        )

    # ② 站点 chip 骨架单点(issue 26-10-20-2231 / R23-B-09): 组件模板一个图标槽, 三处调用点都走它
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl-cells.html"), encoding="utf-8").read()
    assert 'id="tpl-aq-site-chip"' in tpl, "xtpl-cells.html 缺 #tpl-aq-site-chip 单点模板(site-chip 三份回潮?)"
    assert tpl.count("<aq-site-chip ") == 3, "站点 chip 必须恰三处调用点(种子页/组行/集行)且都走单点组件(调用点必带 :m prop, 故标签后一定有空格; 注释里的字面提及不计)"
    assert tpl.count('class="ico sx"') == 1, "chip 单点模板里要有一个命令结果图标槽"
    assert tpl.count("'search-hit': m.hit") == 1, "chip 单点必须带 search-hit 绑定(torrent 版曾漏, 见 issue 26-10-20-2231)"
    assert 'class="ico sa"' not in tpl, "站点问题不再走图标 —— 模板里不得再有 .sa 图标槽"
    assert "'sa-' + m.site_alert" not in tpl, "旧站点图标类拼接必须清零"
    # tooltip 挂整块 chip(D8): 单点模板绑合并文案, 图标不再各自挂 title
    assert tpl.count("$root.siteAlertClass(m)") == 1, "chip 单点按站点问题染色"
    assert tpl.count("$root.chipAlertTip(m)") == 1, "tooltip 必须挂整块 chip"
    assert tpl.count("$root.siteAlertAria(m)") == 1, "站点问题必须补 aria-label(D4)"
    for seg in re.findall(r"<svg[^>]*class=\"ico sx\"[^>]*>", tpl):
        assert ":title" not in seg, "命令结果图标不再单独挂 title(触发面已放大到整块 chip)"

    # ③ token -> 符号单点: 命令结果符号一律经 alertIconHref 取, 不得内联第二份映射
    # (单点模板 × 1 槽 = 1 次; 模板里既有的 #i-warn/#i-caret 属于别的语义, 不在此列)
    assert tpl.count("$root.alertIconHref(") == 1, "命令结果图标必须经 alertIconHref 单点取符号"
    cmds = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    m = re.search(r"const ALERT_ICON = \{([\s\S]*?)\};", cmds)
    assert m, "commands.js 必须有 ALERT_ICON 单点"
    assert set(re.findall(r"(\w+):\s*\"#i-",
                          m.group(1))) == set(CMD_TOKENS), ("ALERT_ICON 键集必须只含命令结果四种 token(站点问题已改走颜色, 不得留图标映射)")
