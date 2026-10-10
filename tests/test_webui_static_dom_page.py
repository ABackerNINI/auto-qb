"""test_webui_static_dom_page 测试计划: webui 前端静态守阵: 页面 / 列模型 / 视图

## 测试计划(每个测试函数一条)
- test_frontend_hr_diag_view_wiring: HR 表② 排障视图前端接线守阵(计划 26-10-01-2216 阶段3) —— 站点卡片 <details> 默认收起(无 open 属性)/ summary 文案 / 站点级 kv 行(hrsKvRows)与各档波次明细行(lanes[].detail 首获展示位)模板绑定 + 展开态不持久化(hr_status.js 无 localStorage)+ .hrs-diag/.hr-diag-kv/.hr-wave-table 三套 UI CSS 成对(波次表同挂 .hr-detail-table 继承表① 徽章色义)
- test_frontend_hr_full_modal_wiring: HR 站点状态折叠 + 覆盖式全屏弹窗守阵(计划 26-10-02-1936 阶段2) —— aqb:hr-full-modal 扫描锚段内遮罩/面板/头部(标题+摘要+✕)绑定齐全、有「展开/收起」钮且无独立「全屏」钮、面板无预展开属性(v-show 挂 hrsOpen); hrsOpen 默认 false(state.js)不持久化(hr_status.js/config_hub.js/state.js 无该键的 localStorage 写读); hubGo 不再自动拉数只复位 hrsOpen; ESC 关闭进 lifecycle 退栈链且同步 escBusy 名单(dialogs.js), 先于 1632 清筛选兜底; 首次展开才拉(hrsToggle 未 loaded 即调 loadHrStatus)、无 setInterval; .hr-full-mask/.hr-full-modal 三套 UI CSS 成对(prism 落 components.css)
- test_frontend_hr_contract_keys_match_backend: HR 两张表消费键契约守阵(计划 26-10-01-2216 阶段4 + 26-10-02-1936 阶段3 扩) —— 从前端源码提取消费键(表① e.*: 模板 aqb:hr-detail-table 段 + hr_status.js 行辅助与行集函数; 表② s.*/ls.*: hr_status.js 全文件 + aqb:hr-diag 模板段), 断言 ⊆ EntryDetail/SiteStatus/LaneStatus 的 to_dict 键集(后端侧闭集钉法 test_entry_details_field_surface 挡不住「上游改键+同步改 expected」的前端静默落空), 每组带核心键在场断言防提取器失效变恒真; 幻键集必须为空(表② 徽章人话 ls.lane_text 曾是幻键致渲染为空, 已修: LaneStatus 补 lane_text 字段由 _lane_statuses 填充, 白名单收空守阵恢复严格; local_present 是响应层 mark_local_present 追加的合法豁免)
- test_frontend_hr_history_wiring: HR 表③ 拉取历史前端接线守阵(计划 26-10-04-0312 §3.5/§05 S4) —— aqb:hr-history 扫描锚 begin/end 成对且段内 <details> 默认收起 + summary 文案 + 站点 chips(hrsHistSiteChips 行内集合现算)+「仅看异常」toggle + 刷新钮 + 「数据截至」时间戳 + 十列表头(时间/站点/触发/结果/页数/行数/回填/放行/耗时/说明)+ 明细行 v-for 与展开明细子行(hr-hist-sub)+ 空态/未启用态文案 + read_errors 点名行; 取数纪律: 首次展开才 fetch(limit=300, @toggle -> hrsHistEnsureLoaded)+ 「刷新」手动重拉(hrsHistReload)+ 无 setInterval + 站点过滤纯前端本地筛不拼 site 查询串; 展开态不持久化(hr_status.js 代码态零 localStorage); .hr-hist-table/.hr-hist-row/.hr-hist-sub/.hr-hres 及五档色义(ok/warn/dim/err/blue)三套 UI CSS 成对
- test_frontend_member_window_functions_live_in_methods: 成员行窗口三个带参函数(memberWin/memberPadTop/memberPadBottom)必须落在 methods 块, 不能进 computed —— Vue 3 computed 是无参 getter, 带参会导致整表白屏(issue 26-09-21-0247)
- test_frontend_computed_not_invoked_as_function: computed 成员不得以 `this.X()` 调用(拿到的是 getter 的值, 再 () 会 TypeError) —— 经典设置页改"数值+单位"字段的数字会整页白屏
- test_frontend_template_no_reserved_prefix_identifiers: 模板表达式(插值+指令)禁止 `_`/`$` 前缀裸标识符 —— Vue 内部保留域解析不到, 抛 ReferenceError 且整块渲染失败(issue 26-10-03-1412 复制钮 `_copyText`); `$event` 白名单, 成员访问不拦
- test_frontend_dist_segments_aggregates_per_view: distSegments 必须按 viewMode 取数(torrents / shows / groups), 不能只数 this.groups —— 种子页次导航 chips 会全空(issue 26-09-21-0247)
- test_frontend_cols_store_single_setitem_site: COLS_STORE_KEY 的 setItem 全仓恰好一处(persistPage 内) —— 散写回潮即红
- test_frontend_persist_page_takes_intent_only: persistPage 只收意图态(colHidden/colOrder/colW), 生效宽度 colWidths 不得进持久化路径(双轨模型铁律, plan 26-09-21-1551)
- test_frontend_col_manual_flag_not_revived: 反向守阵 —— manual 标志位(colManual)不得复活(v5 下 w 非空即固化页)
- test_frontend_cols_legacy_keys_have_migration: LEGACY_COLS_KEYS 键链必须伴随 migrateLegacyToV5 迁移(v3->v4 清零事故的机检)
- test_frontend_cols_empty_hint_names_browser_clear_cause: 空存储提示必须点名浏览器站点级"关闭窗口时清除 Cookie 和站点数据"这条通道 + 给自查路径 + sessionStorage 会话级去重(2026-09-24 取证: cookie 例外 127.0.0.1,* setting=4)
- test_frontend_dir_browse_and_search_stale_guard: 目录浏览与搜索的请求代际守卫(F2-03, issue 26-10-06-0028) —— add_torrent.js loadDir 发请求即记 _dirReqPath 戳, 落袋/报错/finally 三处比对(过期响应丢弃且不动 loading 态) + view.js doSearch 落袋与报错前比对 searchQuery 当前词(慢响应不覆盖新词状态), 任一处守卫被摘除即红
- test_web_store_iteration_snapshot_race_guard: Web 读侧快照竞态守阵(E-01, issue 26-10-06-0028) —— 写线程高频原地增删 store.by_hash/groups/cross_group_conflict_warned 期间, 连续跑 search_torrents/_build_* 系/mark_local_present 不抛 "dictionary changed size during iteration"(修复前大库下必抛)
- test_frontend_page_location_persisted: 顶层 page 与设置分区必须持久化(读侧白名单 / 写侧单漏斗) + 启动补一次 cfgLoad + 分区 key 对 schema 校验 —— 否则"设置页刷新掉回种子页"复发(2026-09-25 用户报)
- test_frontend_unsaved_changes_guard_wiring: 设置页未保存改动防护接线守阵(issue 26-09-25-1702 / 报告 26-10-02-0508 U1-b) —— 键盘刷新(F5/Ctrl+R)走自绘三选一框(保存并刷新/放弃并刷新/留在此页)+ 其余导航走原生 beforeunload 兜底 + 兜底随脏态挂摘成对 + 主动刷新前摘兜底防双框连击 + 不做草稿恢复(不碰 Web Storage)
- test_frontend_expand_state_survives_view_switch: 展开态跨视图记忆守阵 —— 切视图不得置空 expandedKey/expandedShows/expandedShowEp(辅种页→种子页→辅种页 展开的组会收起, 2026-09-25 用户报); 还回前必须验那一行还在, 且 groupWin 的退避判据要同步(否则为不存在的面板永久退化成全量渲染)
- test_frontend_hub_field_covers_non_leaf_items: 设置页 hub-field 模板必须显式覆盖 cfgFlatten 产出的**全部**非叶子项类型(section/group/subcard) —— 缺一支, 段项就落进叶子字段的兜底 `<input>`, 值被 String(对象) 成 "[object Object]"(2026-09-25 用户报)
- test_frontend_hub_field_renders_readonly_fields: schema Field.readonly(程序托管字段, issue 26-09-28-2135)接线守阵 —— CE_FIELD_BASE 有 readonly/readonlyComplex/readonlySummary 三成员, 控件链首支是只读摘要分支、全部可编辑控件挂 :disabled、行带「程序维护」徽标、settings-detail 块级 section 开关对 readonly 段换徽标(缺一处 = 该类字段仍可编辑, 保存却被后端覆盖/回退, 反馈误导)
- test_frontend_statusbar_speed_reads_server_totals: 静态防回潮 —— 前端 totalDl/totalUl 必须读 status.totals, 不得改回对 this.groups 求和
- test_frontend_flatten_skips_hidden_fields: 静态守阵 —— cfgFlatten 必须 `if (f.hidden) continue`(两套 UI 同源于此函数; 不跳过 = 隐藏字段照旧渲染, 报障复发)
- test_frontend_keyed_list_toggle_deletes_key_when_emptied: 静态防回潮 —— keyed_list 的 toggleKey 取消最后一项必须 cfgDelPath 删键(写空列表 = 脏标记消不掉 + 保存被"必须是非空列表"拒, 2026-10-10 报障), cfgSetPath 必须挂长度守卫
- test_frontend_bulk_bar_retired: 批量控制条退役守阵 —— 三套 UI 模板零残留(.bulk-inline/bulkAct(/bulkDeleteLabel(/bulkHrWarnText() 与三套 CSS 死样式零残留(.bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/.bulk-enter-*/.ico-select/@keyframes bulk-in), 批量链路 bulkAct/bulkDelete 仍在且 ctxAct/ctxDelete 复用
- test_api_group_commands_enqueue: pause/resume/reannounce/delete 命令入队(key 编解码回原值)
- test_api_group_malformed_key_returns_400: 畸形分组 key(base64 非法/非 JSON/结构不符)回 400 而非 500
- test_api_delete_with_files_flag: delete 命令透传 delete_files 标志
- test_api_cmd_result_endpoint: 命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)
- test_api_traffic_history_endpoint: /api/traffic/history 透出快照 history; 缺省空数组
"""
import base64
import os
import re
import time

from auto_qb.infra.utils import encode_group_key

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _UI_ALL,
    _ui_shell_inline,
    _ui_aggregate,
    _ui_css_aggregate,
    _app_bundle_files,
    _app_bundle_text,
)


def _bundle_iter():
    """(rel, text) 对迭代: 整包按清单序 —— 「恰好只在一处」类不变量改整包扫描用"""
    for p, rel in _app_bundle_files():
        yield rel, open(p, encoding="utf-8").read()


def test_frontend_hr_diag_view_wiring():
    """HR 表② 排障视图前端接线守阵(2026-10-01, 计划 26-10-01-2216 阶段3)

    表② 是站点卡片里原生 <details> 默认收起的排障视图(上半张站点级 kv 行 + 下半张各档波次明细,
    数据全来自 /api/hr/status 现有载荷, 零新请求零新定时器), 三类"漏一处 = 静默失效 / 拍板被推翻"
    的故障形态机械钉住:
    1. 模板绑定: <details> 默认收起(无 open 属性, 计划 §5.3: 默认收起是拍板交互, 浏览器原生
      open 会让排障噪音常驻)/ summary 文案 / kv 行 v-for(hrsKvRows)/ 波次明细行 v-for
      (lanes[].detail 首次获得展示位, 拍板①a: --hr-status 文本表格化);
    2. 展开态不持久化: 排障是临时动作, hr_status.js 不得出现 localStorage(计划 §5.3);
    3. CSS 三处成对(计划 §5.6): .hrs-diag / .hr-diag-kv / .hr-wave-table 在 atlas / console /
      prism 聚合各 ≥1 —— 波次表同挂 .hr-detail-table 继承表① 徽章色义, 那一段的成对由
      test_frontend_hr_detail_table_wiring 钉住, 这里钉表② 自己的新类。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-diag:begin.*?-->(.*?)<!-- aqb:hr-diag:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-diag 扫描锚 —— 表② 排障视图被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. details 默认收起 + 模板绑定
    dm = re.search(r"<details\b[^>]*>", frag)
    assert dm, "排障视图缺 <details>(收起交互是拍板交互)"
    assert not re.search(r"<details\b[^>]*\bopen\b", dm.group(0)), "排障视图 <details> 不得带默认 open(计划 §5.3: 默认收起)"
    for needle, what in (
        ("排障视图", "summary 文案"),
        ("hrsKvRows(s)", "站点级 kv 行渲染"),
        ('v-for="ls in s.lanes"', "各档波次明细行渲染(lanes[].detail 展示位)"),
        ('class="drawer-table hr-diag-kv"', "kv 表骨架(同挂 .drawer-table 一类)"),
        ("hr-wave-table", "波次明细表类名(同挂 .hr-detail-table 继承徽章色义)"),
    ):
        assert needle in frag, f"排障视图缺 {what}(应有 `{needle}`)"

    # 2. 展开态不持久化 + JS 拼行单点(无新请求/定时器由 hr_detail_table 守阵的 setInterval 断言一并覆盖)
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    for needle in ("hrsKvRows", "hrsWaveCutoff", "hrsWaveCount"):
        assert needle in js, f"hr_status.js 缺 {needle}(表② 人话拼接单点)"
    # 剥块注释再查(注释里提到"不写 localStorage"的说明文字不算使用 —— 判定只认代码态)
    js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js_code = re.sub(r"//[^\n]*", "", js_code)
    assert "localStorage" not in js_code, "展开态不持久化(计划 §5.3: 排障是临时动作): hr_status.js 代码态不得出现 localStorage"

    # 3. CSS 三处成对(表② 新类)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for cls in (".hrs-diag", ".hr-diag-kv", ".hr-wave-table"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5.6)"


def test_frontend_hr_full_modal_wiring():
    """HR 站点状态折叠 + 覆盖式全屏弹窗前端接线守阵(2026-10-02, 计划 26-10-02-1936 阶段2)

    「站点状态」块改两态状态机: 折叠(仅头部) ⇄ 覆盖式全屏弹窗(用户拍板①改判: 「展开」即全屏,
    无中间内嵌展开态; 决策点⑤a: 首次展开才拉数)。五类"漏一处 = 静默失效 / 拍板被推翻"的
    故障形态机械钉住:
    1. 模板绑定: aqb:hr-full-modal 扫描锚段内遮罩(点遮罩关)/面板(v-show 挂 hrsOpen, 无预展开
      属性)/头部(标题 + 摘要 hrsSummaryText + ✕)齐全; 头部有「展开/收起」钮(:aria-expanded 随态,
      运行日志块同款范式)且**无独立「全屏」钮**(拍板①改判后工具条全屏钮已取消);
    2. 状态纪律: hrsOpen 默认 false(state.js, logs.open 同款先例)且不持久化 —— 三个承载文件
      代码态零 localStorage; hubGo 打开分区不再自动拉数、只复位 hrsOpen(每次进分区回折叠);
    3. 取数时机(决策点⑤a): hrsToggle 首次展开且未 loaded 才调 loadHrStatus; 折叠态点
      「全部立即拉取/刷新」顺手展开再拉(hrsExpandAnd* 方法在场); 无 setInterval(不轮询);
    4. ESC 三路关闭: lifecycle.js 退栈链有 hrsOpen 分支(先于 26-10-02-1632 清筛选兜底,
      不抢不漏)且 dialogs.js::escBusy 名单同步(否则设置页 Esc 关弹窗会顺带退回设置首页);
    5. CSS 三处成对: .hr-full-mask / .hr-full-modal 在三套 UI 聚合各 ≥1(prism 落 components.css,
      与 .modal-mask 同文件), 让出顶栏(--head-h)/状态栏(--statusbar-h)的边界声明成对。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-full-modal:begin.*?-->(.*?)<!-- aqb:hr-full-modal:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-full-modal 扫描锚 —— 覆盖层被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. 覆盖层模板绑定(遮罩/面板/头部三件套) + 折叠默认态
    for needle, what in (
        ('class="hr-full-mask"', "遮罩(点遮罩关闭路径)"),
        ('class="hr-full-modal"', "全屏面板"),
        ("hrsCollapse()", "关闭动作(✕ 与遮罩两处复用)"),
        ("hrsSummaryText()", "头部摘要(N 站点 · 数据截至)"),
        ('aria-label="关闭"', "✕ 关闭钮可访问名"),
        ('v-show="hrsOpen"', "显隐挂 hrsOpen(两态: 折叠 ⇄ 全屏覆盖层)"),
    ):
        assert needle in frag, f"全屏覆盖层缺 {what}(应有 `{needle}`)"
    assert not re.search(r'class="hr-full-modal[^"]*\bopen\b', frag), "全屏面板不得带预展开属性(默认折叠是拍板交互)"
    # 头部按钮(在 hb-blk-hd, 锚段之外): 展开/收起钮在场, 独立「全屏」钮不得存在(拍板①改判)
    assert ':aria-expanded="hrsOpen"' in tpl, "头部缺「展开/收起」钮的 aria-expanded 随态绑定"
    assert "hrsToggle()" in tpl, "头部缺展开/收起切换(hrsToggle)"
    for legacy in ("hrsSiteFullscreen", ">全屏<", "'全屏'", '"全屏"'):
        assert legacy not in tpl, f"不得复活独立「全屏」钮(拍板①改判: 展开即全屏) —— 命中 `{legacy}`"

    # 2. 状态纪律: 默认折叠 + 不持久化
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    assert "hrsOpen: false" in state_js, "state.js 缺 hrsOpen: false(默认折叠, logs.open 同款先例)"
    # 不持久化只约束 hrsOpen 本身: config_hub.js 存量就有 hub 视图键的 localStorage 读写(合法),
    # 这里钉的是「展开态不许新增存储通道」—— 任何含 localStorage 的行不得提及 hrsOpen/hrs.open,
    # 且三个承载文件代码态不得出现新的 hrs 存储键字面量。
    for name in ("hr_status.js", "config_hub.js", "state.js"):
        code = open(os.path.join(shared, name), encoding="utf-8").read()
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        for ln in code.splitlines():
            if "localStorage" in ln:
                assert "hrsOpen" not in ln and "hrs.open" not in ln, \
                    f"{name} 把展开态写进 localStorage —— 不持久化被破坏: {ln.strip()}"
        assert 'localStorage.setItem("autoqb.hrs' not in code, \
            f"{name} 新增了 hrs 存储键 —— 展开态不持久化(计划 §3.1)"

    # 3. 取数时机: 首次展开才拉 + 折叠态点拉取/刷新顺手展开
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    js_flat = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    for needle, what in (
        ("hrsToggle()", "展开/收起切换单点"),
        ("if (!this.hrs.loaded) this.loadHrStatus();", "首次展开才拉(决策点⑤a)"),
        ("hrsExpandAndRefreshAll()", "折叠态点「全部立即拉取」顺手展开再拉"),
        ("hrsExpandAndReload()", "折叠态点「刷新」顺手展开再拉"),
        ("hrsSummaryText()", "摘要拼行单点"),
    ):
        assert needle in js_flat, f"hr_status.js 缺 {what}(应有 `{needle}`)"
    assert "setInterval" not in js, "hr_status.js 不得有轮询定时器(计划 §5.5 刷新纪律)"
    hub_js = open(os.path.join(shared, "config_hub.js"), encoding="utf-8").read()
    assert 'if (key === "hr_check") this.hrsOpen = false;' in hub_js, \
        "hubGo 打开 HR 分区必须复位 hrsOpen(每次进分区回折叠), 且不得再自动 loadHrStatus"
    assert 'key === "hr_check" && !this.hrs.loaded' not in hub_js, \
        "hubGo 不得在打开分区时自动 loadHrStatus(决策点⑤a: 取数时机收进 hrsToggle)"

    # 4. ESC 关闭: 退栈链分支 + escBusy 名单两处同步(不抢不漏)
    lc = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    dl = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    chain = re.search(r"if \(e\.key !== \"Escape\"\) return;.*?\}\);", lc, re.S)
    assert chain, "lifecycle.js 找不到 Esc 退栈链 —— 结构变了? 同步本守阵"
    assert "this.hrsOpen) this.hrsCollapse()" in chain.group(0), \
        "Esc 退栈链缺 hrsOpen 分支(覆盖层 ESC 关闭不生效或被清筛选兜底抢走)"
    clear_idx = chain.group(0).find("clearFilters()")
    hrs_idx = chain.group(0).find("hrsCollapse()")
    assert 0 <= hrs_idx < clear_idx, "hrsOpen 分支必须排在清筛选兜底之前(26-10-02-1632 优先级: 关弹窗不顺带清筛选)"
    busy = re.search(r"escBusy\(\) \{\n(.*?)\n    \},", dl, re.S)
    assert busy and "this.hrsOpen" in busy.group(1), \
        "escBusy 名单缺 hrsOpen —— 漏同步时设置页按 Esc 关弹窗会顺带退回设置首页(hubOnKey)"

    # 5. CSS 三处成对: 遮罩 + 面板 + 上下边界让出声明
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for cls in (".hr-full-mask", ".hr-full-modal"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5 阶段2)"
        assert "--head-h" in css and "--statusbar-h" in css, \
            f"{name} 的全屏覆盖层缺顶栏/状态栏让出声明(--head-h / --statusbar-h)"
    pri_components = open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read()
    assert ".hr-full-modal" in pri_components, "prism/css/components.css 缺全屏覆盖层段(与 .modal-mask 同文件)"


def test_frontend_hr_contract_keys_match_backend():
    """HR 两张表「前端消费键 ⊆ 后端导出键」契约守阵(2026-10-01, 计划 26-10-01-2216 阶段4)

    表① 行字段的后端导出面已由 test_hr_status.test_entry_details_field_surface 钉死(闭集),
    但那是**后端侧**钉法: 上游改键名 + 同步改那条 expected 后 pytest 照样全绿, 前端消费的
    旧键名却静默落空 —— 渲染成空串/undefined, 不报错不看页面发现不了(与
    test_frontend_hr_status_fields_match_backend 同一故障族, 但那里只扫模板里的 `s.*`,
    表② 的 kv 拼行与波次取数在 hr_status.js 里, 模板只有 hrsKvRows(s) 一个调用点, 扫不到)。

    这里从**前端源码**提取消费键(双向都能红: 前端新增幻键 / 上游改键名都会撞):
    - 表① 行: 共享模板 aqb:hr-detail-table 段的直接 `e.*` + hr_status.js 的行辅助/行集函数
      (参数把行对象传进来的: hrsDetailRows 的 `e` / hrsVerdictText/hrsVerdictSub/hrsSrcCls/
      hrsPresenceText/hrsPresenceCls/hrsPresenceSub 的 `e`, 26-10-02-1936 阶段3 随三列重组换名),
      对照 EntryDetail.to_dict; 全文件扫 `e.*` 会误吞 catch(e) 的 auth/message, 故按函数体提;
    - 表② 站点级: hr_status.js 全文件(拼行单点 hrsKvRows 与摘要层 hrsState*/hrsLaneText
      的参数都叫 s)`s.*` + aqb:hr-diag 模板段, 对照 SiteStatus.to_dict;
    - 表② 波次级: hr_status.js 全文件 `ls.*`(hrsWaveCutoff/hrsWaveCount/hrsLaneClass)
      + aqb:hr-diag 模板段, 对照 LaneStatus.to_dict。
    每组都带「核心键必须在场」断言 —— 提取器本身失效(函数改名/文件挪走)时守阵变红而不是
    静默变恒真。
    """
    from auto_qb.hr.status import EntryDetail, LaneStatus, SiteStatus

    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    # 判定只认代码态(与 test_frontend_hr_diag_view_wiring 的 localStorage 检查同款剥注释)
    js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js_code = re.sub(r"//[^\n]*", "", js_code)

    frag_table = re.search(r"<!-- aqb:hr-detail-table:begin.*?-->(.*?)<!-- aqb:hr-detail-table:end.*?-->", tpl, re.S)
    frag_diag = re.search(r"<!-- aqb:hr-diag:begin.*?-->(.*?)<!-- aqb:hr-diag:end.*?-->", tpl, re.S)
    assert frag_table and frag_diag, "settings-detail.html 缺 aqb 扫描锚(表①/表②) —— 模板被移走? 同步本守阵"

    # --- 表① 行字段: 模板直接消费 + JS 行辅助/行集函数(行对象经参数传入) ---
    used_e = set(re.findall(r"\be\.([a-z_]+)\b", frag_table.group(1)))
    for fn in (
        "hrsDetailRows", "hrsVerdictText", "hrsVerdictSub", "hrsSrcCls", "hrsPresenceText", "hrsPresenceCls",
        "hrsPresenceSub"
    ):
        # 行集函数参数是 site(体内 lambda 参数 e), 行辅助函数参数是 e —— 统一按「函数头到方法尾」切块
        m = re.search(rf"\n    {fn}\((?:e|site)\) \{{\n(.*?)\n    \}},", js, re.S)
        assert m, f"hr_status.js 找不到 {fn} 函数体 —— 表① 行消费单点被移走或改名? 同步本守阵"
        used_e |= set(re.findall(r"\be\.([a-z_]+)\b", m.group(1)))
    assert {"tid", "verified_ts", "last_seen"} <= used_e, f"表① 消费键提取失效(只扫到 {sorted(used_e)}) —— 守阵变恒真, 同步提取器"
    # local_present 是响应层 mark_local_present 追加的只读标记(routes/hr.py 单点, 决策点③a),
    # 不在 EntryDetail.to_dict —— 有意豁免; 其余幻键仍然是真缺陷。
    phantom_e = sorted(used_e - set(EntryDetail(tid=0).to_dict()) - {"local_present"})
    assert not phantom_e, f"表① 消费了 EntryDetail 不导出的键 {phantom_e}(渲染成空, 打错/上游改名都会这样)"

    # --- 表② 站点级(s.*)与波次级(ls.*) ---
    used_s = set(re.findall(r"\bs\.([a-z_]+)\b", js_code)) | set(re.findall(r"\bs\.([a-z_]+)\b", frag_diag.group(1)))
    assert {"fresh_text", "index_total", "empty_confirmed"} <= used_s, f"表② 站点级消费键提取失效(只扫到 {sorted(used_s)}) —— 同步提取器"
    phantom_s = sorted(used_s - set(SiteStatus(site="probe").to_dict()))
    assert not phantom_s, f"表② 消费了 SiteStatus 不导出的键 {phantom_s}(kv 行静默落空)"
    used_ls = set(re.findall(r"\bls\.([a-z_]+)\b", js_code)) | set(re.findall(r"\bls\.([a-z_]+)\b", frag_diag.group(1)))
    assert {"full_depth", "count_claim", "lane_text"} <= used_ls, f"表② 波次级消费键提取失效(只扫到 {sorted(used_ls)}) —— 同步提取器"
    # 严格闭集(2026-10-01 收空): 曾有已知幻键 ls.lane_text(徽章人话渲染为空), 修法 = LaneStatus
    # 补该字段由 _lane_statuses 填充(LANE_TEXTS 单点), 白名单已收 —— 任何幻键在这里都是真缺陷。
    phantom_ls = sorted(used_ls - set(LaneStatus().to_dict()))
    assert not phantom_ls, f"表② 波次级消费了 LaneStatus 不导出的键 {phantom_ls}(渲染成空, 打错/上游改名都会这样)"


def test_frontend_hr_history_wiring():
    """HR 表③ 拉取历史前端接线守阵(2026-10-04, 计划 26-10-04-0312 §3.5/§05 S4)

    表③ 是全屏覆盖层里 .hrs-list 之后的全局 <details>(拉取历史跨站点成时间轴, 不进 per-site
    article; 数据 /api/hr/history, S1-S3 交付; 状态挂 hr_status.js 伴生键 hrsHist, 方法前缀
    hrsHist*), 五类"漏一处 = 静默失效 / 拍板被推翻"的故障形态机械钉住:
    1. 模板绑定: aqb:hr-history 扫描锚 begin/end 成对且段内 <details> 默认收起(表② 同款折叠
      范式)/ summary 文案 / 站点 chips(hrsHistSiteChips, 行内站点集合现算)/ 「仅看异常」toggle /
      刷新钮 / 「数据截至」时间戳 / 十列表头(计划 §3.5 mock 列面: 时间/站点/触发/结果/页数/行数/
      回填/放行/耗时/说明)/ 明细行 v-for + 行点击展开明细子行(hr-hist-sub)/ 空态与未启用态文案 /
      read_errors 点名行(坏站点文件不静默);
    2. 取数纪律(计划 §3.5): 首次展开才 fetch(limit=300, 模板 @toggle -> hrsHistOnToggle ->
      hrsHistEnsureLoaded), 「刷新」手动重拉(hrsHistReload), 无 setInterval(不轮询);
      站点过滤纯前端本地筛不回后端(端点拼串不得出现 site 查询参数);
    3. 展开态不持久化: 排障动作不写存储, hr_status.js 代码态零 localStorage(表② 同款);
    4. CSS 三处成对(计划 §5.6): .hr-hist-table / .hr-hist-row / .hr-hist-sub / .hr-hres 及
      result_tone 五档色义(ok/warn/dim/err/blue)在 atlas / console / prism 聚合各 ≥1
      (骨架 .drawer-table + .hr-detail-table 与 chips 行复用件的成对由既有守阵钉住)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    begins = re.findall(r"<!-- aqb:hr-history:begin", tpl)
    ends = re.findall(r"<!-- aqb:hr-history:end", tpl)
    assert len(begins) == 1 and len(ends) == 1, \
        f"aqb:hr-history 扫描锚必须 begin/end 恰好成对各一(实得 begin={len(begins)} / end={len(ends)}) —— 表③ 段被移走或锚被删? 同步本守阵"
    m = re.search(r"<!-- aqb:hr-history:begin.*?-->(.*?)<!-- aqb:hr-history:end.*?-->", tpl, re.S)
    frag = m.group(1)

    # 1. 折叠范式 + 模板绑定
    dm = re.search(r"<details\b[^>]*>", frag)
    assert dm, "表③ 缺 <details>(表② 同款折叠范式)"
    assert not re.search(r"<details\b[^>]*\bopen\b", dm.group(0)), "表③ <details> 不得带默认 open(默认收起是拍板交互)"
    for needle, what in (
        ("拉取历史 · 最近取数与波次明细", "summary 文案"),
        ("hrsHistOnToggle($event)", "首次展开触发(@toggle)"),
        ("hrsHistSiteChips()", "站点 chips(行内站点集合现算)"),
        ("hrsHistSetSite(", "chips 点击切换"),
        ("仅看异常", "「仅看异常」toggle 文案"),
        ("hrsHistToggleBad()", "「仅看异常」点击切换"),
        ("hrsHistReload()", "「刷新」手动重拉"),
        ("hrsHistFreshText()", "「数据截至」时间戳(拼行单点在 hrsHistFreshText)"),
        ('class="drawer-table hr-detail-table hr-hist-table"', "表格骨架(同挂 .drawer-table + .hr-detail-table)"),
        ('v-for="r in hrsHistRows()"', "明细行渲染(前端本地过筛行集)"),
        ('class="hr-hist-row"', "可点击主行(展开触发)"),
        ('class="hr-hist-sub"', "展开明细子行"),
        ("hrsHistSubText(r)", "子行文案单点(各档 lanes 明细)"),
        ('class="hr-hres"', "结果徽章(result_tone 色档)"),
        ("hrsHistResCls(r)", "结果徽章色档映射"),
        ("正在读取拉取历史", "加载态文案"),
        ("最近还没有拉取记录", "空态文案"),
        ("HR 在线核实未启用", "未启用态文案"),
        ("文件读取失败", "read_errors 点名行(坏站点文件不静默)"),
    ):
        assert needle in frag, f"表③ 模板缺 {what}(应有 `{needle}`)"
    # 十列列面(计划 §3.5 mock): 时间/站点/触发/结果/页数/行数/回填/放行/耗时/说明(数值列挂 .num)
    for col in ("时间", "站点", "触发", "结果", "页数", "行数", "回填", "放行", "耗时", "说明"):
        assert f"<th>{col}</th>" in frag or f'<th class="num">{col}</th>' in frag, \
            f"表③ 表头缺「{col}」列(计划 §3.5 mock 列面)"

    # 2. 取数纪律: 首次展开才拉 + 手动刷新 + 不轮询 + 本地过滤不回后端
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    for needle, what in (
        ("/api/hr/history?limit=", "历史端点拼接"),
        ("HRS_HIST_LIMIT = 300", "单页拉取条数(计划拍板值)"),
        ("hrsHistOnToggle(ev)", "toggle 入口(开与合都触发, 只有展开才拉)"),
        ("hrsHistEnsureLoaded", "首次展开才拉单点"),
        ("hrsHistReload", "手动重拉单点"),
        ("hrsHistSiteChips", "站点 chips 现算单点"),
        ("hrsHistRows", "本地过筛行集单点"),
        ("hrsHistIsBad", "仅看异常判据单点"),
        ('r.kind === "defer"', "拦下行一律算异常(计划 §3.5 拍板)"),
        ("hrsHistSubText", "展开子行文案单点"),
        ("hrsHistResCls", "徽章色档映射单点"),
        ("数据截至", "「数据截至」拼行单点(hrsHistFreshText)"),
    ):
        assert needle in js, f"hr_status.js 缺 {what}({needle})"
    assert "setInterval" not in js, "hr_status.js 不得有轮询定时器(表③ 不轮询, 计划 §3.5)"
    assert "/api/hr/history?site" not in js and "&site=" not in js, \
        "站点过滤必须纯前端本地筛, 不得回后端拼 site 查询串(计划 §3.5)"

    # 3. 展开态不持久化(剥块/行注释再查 —— 说明文字不算使用, 判定只认代码态)
    js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js_code = re.sub(r"//[^\n]*", "", js_code)
    assert "localStorage" not in js_code, "展开态不持久化: hr_status.js 代码态不得出现 localStorage"

    # 4. CSS 三处成对: 表③ 新类 + result_tone 五档色义
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for cls in (".hr-hist-table", ".hr-hist-row", ".hr-hist-sub", ".hr-hres"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5.6)"
        for tone in ("ok", "warn", "dim", "err", "blue"):
            assert f".hr-hres.hr-hres-{tone}" in css, f"{name} 缺 .hr-hres-{tone} 色义(result_tone 五档)"


def test_frontend_member_window_functions_live_in_methods():
    """成员行窗口三个函数(memberWin / memberPadTop / memberPadBottom)必须在 methods 块, 不能在 computed

    现象与定性(issue 26-09-21-0247):
    这三个函数**带参数**(`list`), Vue 3 computed 是无参 getter —— 模板里 `memberPadTop(g.members)`
    调用时, Vue 把 `this.memberWin` 当 getter 触发, 拿到的是 `{padTop:0,…}` 这个**值**;
    再 `(list)` 把它当函数调 → "this.memberWin is not a function" → 辅种页展开任一行即整表白屏
    (chips / 状态条 / 表头 / 行 全部消失, 控制台报错)。同一份代码在拆分前(afef7ce^)
    就在 computed, 之前未塌是因为没人走"辅种页展开"路径; 守不住就会再塌。

    断言: 这三个名字的定义行必须在 `methods: {` 之后、`computed: {` 之前。
    """
    rel = "shared/columns.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m_methods = re.search(r"^\s*methods:\s*\{", text, re.M)
    m_computed = re.search(r"^\s*computed:\s*\{", text, re.M)
    assert m_methods, f"{rel} 找不到 methods 块(文件结构改了? 同步本守阵)"
    assert m_computed, f"{rel} 找不到 computed 块(文件结构改了? 同步本守阵)"
    methods_end = m_methods.end()
    computed_start = m_computed.start()
    assert methods_end < computed_start, f"{rel} methods 块不在 computed 之前(顺序倒了?)"
    for name in ("memberWin", "memberPadTop", "memberPadBottom"):
        m_def = re.search(rf"^\s*{name}\s*\(", text, re.M)
        assert m_def, f"{rel} 找不到 {name}(... 定义(改名了? 同步本守阵)"
        assert methods_end < m_def.start() < computed_start, (
            f"{rel} {name}(...) 定义落在 computed 块里 —— Vue 3 computed 不能带参, "
            f"模板里 memberPadTop(g.members) 会把 this.memberWin 当 getter 触发,"
            f"拿到值再 (list) 当函数调 → 整表白屏(issue 26-09-21-0247)"
        )


def _computed_member_names(lines):
    """取一个片段文件里所有 `computed: {` 块的成员名(块缩进 + 2 的成员行)

    比 `_section_members` 多两件事: 1.**所有** computed 块都要取(组件里的 computed 也在内,
    不只看顶层 mixin); 2.终止行按**块的缩进**判定 —— 用 `line.strip() in ("},", "}")`
    会被深层嵌套的 `},`(如 `return {...};` 之后那一行)提前关掉块, 从而漏掉后面的成员。
    """
    out, in_block, indent = set(), False, 0
    for line in lines:
        if not in_block:
            if line.strip() == "computed: {":
                in_block = True
                indent = len(line) - len(line.lstrip())
            continue
        if line.rstrip() in (" " * indent + "},", " " * indent + "}"):
            in_block = False
            continue
        m = re.match(r"^\s{%d}(?:async\s+)?([A-Za-z_$][\w$]*)\s*[(:]" % (indent + 2), line)
        if m:
            out.add(m.group(1))
    return out


def test_frontend_computed_not_invoked_as_function():
    """computed 成员不许以 `this.X()` 形式调用 —— 拿到的是 getter 的**值**, 不是函数

    现象与定性(2026-09-21, 经典设置页「数值 + 单位」字段):
    `unitParts` 是 computed(返回 `{num, unit}`), 而 `setUnitNum` 里写成了
    `this.unitParts().unit` —— 这是把 getter 的**返回值**当函数调用 ⇒ `TypeError:
    this.unitParts is not a function` ⇒ **一改数字框就整页白屏**(设置页整段消失)。
    此前没人发现是因为: 1. 模板里 `unitParts.num` 是对的(只错在 JS 方法里);
    2. 只有真的去改"主循环间隔 / 轮转大小"这类带单位的值才会触发。

    为什么必须机检: 这类错误**只在真浏览器里跑特定交互**才现形, `node --check` 查不出来
    (语法完全合法), 静态守阵里也天然看不见; 与 `test_frontend_member_window_functions_live_in_methods`
    是同一族("computed 看起来对, 实际废掉"), 但那一条守的是"带参函数放错了块",
    这一条守的是"无参 computed 被当成函数调" —— 两个方向都要钉。

    断言: 任一片段文件里, 出现在 `computed: {` 块中的成员名, 不得在该文件中以 `this.<名>(` 出现。
    """
    problems = []
    for path, rel in _app_bundle_files():
        text = open(path, encoding="utf-8").read()
        lines = text.splitlines()
        for name in sorted(_computed_member_names(lines)):
            for m in re.finditer(r"this\.%s\(" % re.escape(name), text):
                ln = text[:m.start()].count("\n") + 1
                stripped = lines[ln - 1].strip()
                # 注释行里引用这个写法(说明"别这么写")不算违规, 否则守阵会逼人删文档
                if stripped.startswith(("*", "//", "#")):
                    continue
                problems.append(
                    f"{rel}:{ln} `{name}` 是 computed 却以 this.{name}() 调用"
                    "(拿到的是 getter 的值, 再 () 会 TypeError ⇒ 触发该路径的界面整段白屏)"
                )
    assert not problems, "computed 被当函数调用: " + "; ".join(problems)


def test_frontend_template_no_reserved_prefix_identifiers():
    """模板表达式里禁止 `_`/`$` 前缀裸标识符 —— Vue 把两类前缀当内部保留域, 模板解析不到

    现象与定性(issue 26-10-03-1412, 坑位 web-ui/vue-reactivity.md「模板里不允许下划线前缀标识符」):
    drawer.html / popovers.html 的复制钮处理器写成 `@click="_copyText(...)"`, 真浏览器点击恒抛
    `ReferenceError: _copyText is not defined`(用户复验原文, 2026-10-03)且**整块渲染失败** ——
    Vue 把 `_`/`$` 前缀成员排除在组件代理之外, data/methods 里的 `_` 方法对模板不可见;
    vue.global.prod 无 dev 警告, 失败是静默的。

    覆盖两类形态(上次复发 1 的根子就是判别只记了插值形态, `@click="_x()"` 没被认出来):
    插值 `{{ ... }}` 与指令表达式(v-on / v-bind / v-if 等的属性值)。
    `$event` 是 Vue 内建事件形参, 白名单放行; `obj._x` 成员访问(点号后)不属于裸标识符, 不拦。
    """
    problems = []
    sources = []  # (rel, text): 盘上全部分片 + 各 UI shell 的 #app 内联段(与运行时编译输入同源)
    tpl_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    for name in sorted(os.listdir(tpl_dir)):
        if name.endswith(".html"):
            rel = "shared/tpl/" + name
            sources.append((rel, open(os.path.join(tpl_dir, name), encoding="utf-8").read()))
    for ui in _UI_ALL:
        sources.append((f"{ui}/index.html(#app 内联)", _ui_shell_inline(ui)))

    # 逐文件剥 HTML 注释(注释里的"别这么写"示例不算违规, 否则守阵会逼人删文档)
    stripped = [(rel, re.sub(r"<!--.*?-->", "", text, flags=re.S)) for rel, text in sources]
    for rel, text in stripped:
        spans = [(m.group(1), m.start()) for m in re.finditer(r"\{\{(.*?)\}\}", text, re.S)]
        spans += [
            (m.group(1), m.start())
            for m in re.finditer(r"""(?:^|\s)(?:v-[\w:.\-]+|@[\w.\-]+|:[\w.\-]+)\s*=\s*(["'])(.*?)\1""", text, re.S)
        ]
        for expr, pos in spans:
            for m in re.finditer(r"(?<![\w$.])([_$][A-Za-z_$][\w$]*)", expr):
                tok = m.group(1)
                if tok == "$event":  # Vue 内建事件形参, 模板里合法
                    continue
                ln = text[:pos].count("\n") + 1
                problems.append(
                    f"{rel}:{ln} 模板表达式含保留前缀标识符 `{tok}` —— Vue 解析不到(_/$ 前缀不对模板暴露, "
                    f"成员定义在 methods/data 里也会抛 ReferenceError 且整块渲染失败); "
                    f"模板处理器一律去前缀, 内部 `_` 方法经无前缀别名中转(issue 26-10-03-1412)"
                )
    assert not problems, "模板保留前缀标识符: " + "; ".join(problems)


def test_frontend_dist_segments_aggregates_per_view():
    """状态分布 distSegments 必须按当前 viewMode 取数, 不能只数 this.groups

    现象与定性(issue 26-09-21-0247):
    后端按视图回传(P1-1, 见 mixins/web_view.VIEW_ARRAYS): view=torrent 只回 torrents,
    view=group 只回 groups+singles。旧版 distSegments 只数 this.groups[].members[].kind,
    于是两种场景 chips 全空:
    1. localStorage 持久化 `autoqb.ui.view=torrents` 后首进种子页(首轮 groups=[]);
    2. 在种子页停得久(轮询只刷 torrents, groups 永远是空/旧)。
    表现是「做种10 错误1」整行消失。

    断言: distSegments 实现里必须包含三个 viewMode 分支(torrents / shows / 其余即 groups)。
    """
    rel = "shared/dialogs.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"distSegments\s*\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, f"{rel} 找不到 distSegments computed(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    for token, label in (
        ('this.viewMode === "torrents"', "torrents 视图分支"),
        ('this.viewMode === "shows"', "shows 视图分支"),
        ("this.groups", "groups 视图分支(else 兜底, 直接读 this.groups)"),
    ):
        assert token in body, f"distSegments 缺少{label}({token!r}) —— 种子页/追剧页次导航统计会全空(issue 26-09-21-0247)"


def test_frontend_cols_store_single_setitem_site():
    """全仓前端对 COLS_STORE_KEY 的 setItem 必须恰好一处(persistPage 内) —— 唯一持久化漏斗

    plan 26-09-21-1551: 旧模型 6 个落盘点各自决定写入时机, "先存后算/先算后存"选错 3 处,
    内存/存储长期漂移(失败分析实测: 内存 12 键 / 存储 0 键)。新模型只有一个漏斗,
    散写回潮 = 本守阵红。
    """
    hits = []
    for name, text in _bundle_iter():
        text = open(os.path.join(STATIC_ROOT, name), encoding="utf-8").read()
        for i, ln in enumerate(text.splitlines(), 1):
            code = ln.split("//")[0]
            if "localStorage.setItem(COLS_STORE_KEY" in code:
                hits.append(f"{name}:{i}")
    assert len(hits) == 1 and hits[0].startswith("shared/columns.js"), (
        f"COLS_STORE_KEY 的 setItem 必须只存在于 columns.js 的 persistPage 内, 实测: {hits}"
    )
    cols = open(os.path.join(STATIC_ROOT, "shared/columns.js"), encoding="utf-8").read()
    m = re.search(r"persistPage\s*\(\s*page\s*\)\s*\{(.*?)\n    \},", cols, re.S)
    assert m, "columns.js 找不到 persistPage(page)(改名或挪走了? 同步本守阵)"
    assert "localStorage.setItem(COLS_STORE_KEY" in m.group(1), "setItem 不在 persistPage 内? 同步本守阵"


def test_frontend_persist_page_takes_intent_only():
    """persistPage 只收意图态(colHidden/colOrder/colW), 生效宽度 colWidths 不得出现在其代码里

    "派生值没有资格落盘"是双轨模型唯一铁律(plan 26-09-21-1551)。旧模型 colWidths 混装
    意图与"按窗口算出的自适应 px", 靠 manual 标志在读写两侧过滤, 任何一侧失配即复发
    (issue 26-09-20-1800, 四轮修复未绝根)。取代旧守阵 test_frontend_save_col_state_skips_widths_for_auto_pages。
    """
    rel = "shared/columns.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"persistPage\s*\(\s*page\s*\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, f"{rel} 找不到 persistPage(page)(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    # !只看**代码行**(同旧守阵教训: 注释里提到不算)
    code_lines = [ln.strip() for ln in body.splitlines() if not ln.strip().startswith(("*", "//", "#"))]
    assert not any("colWidths" in ln for ln in code_lines
                  ), ("persistPage 的**代码**里出现 colWidths(生效态/派生值) —— 派生值落盘会让"
                      "'列宽被别的窗口改写'原样复发(plan 26-09-21-1551 铁律)")
    assert any("this.colW" in ln for ln in code_lines), ("persistPage 的**代码**里必须写意图态 this.colW(结构变了? 同步本守阵)")


def test_frontend_col_manual_flag_not_revived():
    """反向守阵: manual 标志位不得复活 —— 双轨模型下 w 非空即固化页, 标志位是旧模型的失配源

    v4 模型靠 manual:{page:bool} 门控"现算能不能覆盖 / 持久化要不要过滤", 读写两侧必须
    永远成对同步, 任何一侧失配 = "列设置被重置"复发(issue 26-09-20-1800 全史)。
    v5 删除该标志; 连注释里也不得出现该标识, 防止有人照着历史注释"顺手加回来"。
    """
    for name, text in _bundle_iter():
        text = open(os.path.join(STATIC_ROOT, name), encoding="utf-8").read()
        assert "colManual" not in text, (
            f"{name} 出现 colManual —— manual 标志位在双轨模型(v5)下已删除, "
            "不得复活(w 非空即固化页); 如确需重引, 先重审 plan 26-09-21-1551"
        )


def test_frontend_cols_legacy_keys_have_migration():
    """LEGACY_COLS_KEYS 键链必须伴随迁移函数 —— 升版必挂迁移(定案口径)

    v3->v4 升版没挂迁移, 用户手调的宽/隐/序一次性清零(四轮修复复盘第1.轮, "时不时被重置"
    的机制性来源)。v5 挂 migrateLegacyToV5; 本守阵钉住键链与迁移的耦合。
    """
    rel = "shared/app.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"const LEGACY_COLS_KEYS = \[(.*?)\];", text, re.S)
    assert m, f"{rel} 找不到 LEGACY_COLS_KEYS"
    keys = re.findall(r'"([^"]+)"', m.group(1))
    assert keys == [
        "autoqb_cols_v4", "autoqb_cols_v3"
    ], (f"LEGACY_COLS_KEYS 变更了({keys}) —— 升版/换键必须同步 migrateLegacyToV5 与迁移测试"
        "(plan 26-09-21-1551; v3->v4 清零事故的机检)")
    assert "function migrateLegacyToV5" in text, "LEGACY_COLS_KEYS 非空但找不到 migrateLegacyToV5(迁移函数)"
    assert "migrateLegacyToV5(raw)" in text, "readColStateRaw 未使用 migrateLegacyToV5(旧键不会被迁移)"


def test_frontend_cols_empty_hint_names_browser_clear_cause():
    """空存储提示必须点出"浏览器站点级关闭时清除站点数据"这条通道 + 自查路径 + 会话级去重

    2026-09-24 取证(真因, 非应用 bug): 用户 Edge/Chrome 的 `content_settings.exceptions.cookies`
    里都有 `127.0.0.1,*` setting=4(Chromium `CONTENT_SETTING_SESSION_ONLY`, 界面文案 = "关闭窗口时
    清除 Cookie 和站点数据") ⇒ 关浏览器时该 host 的 Cookie 与 localStorage **一起**被清, 于是
    "浏览器重启后偏好全回默认"。旧提示只写了 origin 隔离(换地址/端口), 把排查方向带偏了好几轮。
    另一层: 清站点数据的环境下 localStorage 里的"已提示"标记也一起没了 ⇒ 没有 sessionStorage
    兜底就会每次关浏览器重开都弹。
    """
    text = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
    m = re.search(r"_showColsOriginHint\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, "columns.js 找不到 _showColsOriginHint(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "关闭窗口时清除" in body, (
        "空存储提示没提浏览器站点级『关闭窗口时清除 Cookie 和站点数据』—— 用户会把整站数据被清"
        "误判成应用 bug(2026-09-24 取证: Edge/Chrome 的 cookie 例外 127.0.0.1,* setting=4)"
    )
    assert "edge://settings/content/all" in body, "提示必须给出可自查的浏览器设置路径(否则用户无从下手)"
    assert "sessionStorage" in body, "缺少 sessionStorage 兜底 ⇒ 清站点数据的环境下每次开浏览器都弹"
    assert "localStorage.setItem(COLS_ORIGIN_HINT_KEY" in body, "普通场景的跨会话去重标记(只记一次)被删了"


def test_frontend_cols_empty_hint_is_not_a_floating_banner():
    """空存储提示的出口 = 通知面板, **不得是页面浮层**(2026-10-09 用户实报: 遮挡自动化测试截图)

    旧实现运行时往 body 插一条 fixed 横幅(可点关 / 15s 自灭): 它压在页面内容上, 且**每次跑自动化
    测试都触发** —— 测试用全新浏览器上下文, 没有"已提示"去重标记, 于是每张截图底部都被盖一截。
    改道后只进通知面板(ui_feedback.js::_recordNotice): 面板默认收起、不占版面、不进截图, 入口留
    一个未读徽标。本守阵钉死"不再建浮层"这个不变量(文案 / 去重标记的守阵在上一条)。
    """
    text = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
    m = re.search(r"_showColsOriginHint\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, "columns.js 找不到 _showColsOriginHint(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "this._recordNotice(" in body, ("空存储提示没走 _recordNotice —— 出口必须是通知面板(陈述型告知一律进面板, 不占版面/不进截图)")
    for banned in ("document.createElement", "appendChild", "position:fixed", "z-index:9999"):
        assert banned not in body, (
            f"空存储提示里出现 {banned} —— 页面级浮层会压住页面内容并遮挡自动化测试截图"
            "(2026-10-09 用户实报; 陈述型提示一律走 _recordNotice)"
        )


def test_frontend_dir_browse_and_search_stale_guard():
    """目录浏览与搜索的请求代际守卫(F2-03, issue 26-10-06-0028) —— 慢响应不得覆盖新状态

    add_torrent.loadDir 快速连点 A→B 时 A 的响应后到会把 dirBrowse 覆写回 A; view.doSearch
    连续输入 a→b 时 a 的响应后到会把命中集覆写成 a(搜索框显示 b、高亮集却是 a, 无轮询
    自动纠正)。修法 = 与 drawer.js _drawerStale 同式收口: loadDir 以 path 戳(_dirReqPath)、
    doSearch 以 query 戳(落袋前比对当前 searchQuery), 守卫覆盖落袋与报错两路, 且过期请求
    不动 loading 态(新在途请求持有它, 免闪一帧"加载完"假象)。
    """
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    vw = open(os.path.join(STATIC_ROOT, "shared", "view.js"), encoding="utf-8").read()

    # ① loadDir: 发请求即记 path 戳
    m = re.search(r"async loadDir\(path\)\s*\{(.*?)\n    \},", at, re.S)
    assert m, "add_torrent.js 找不到 loadDir(改名或挪走了? 同步本守阵)"
    body = re.sub(r"//[^\n]*", "", m.group(1))
    assert re.search(r"const reqPath = path \|\| \"\";\s*this\._dirReqPath = reqPath;", body), \
        "loadDir 未在发请求前记录 path 戳(_dirReqPath) —— A→B 连点旧响应会覆盖新状态"
    # 落袋与报错两路都比对(截获 return 而非 continue 写状态)
    assert body.count("if (this._dirReqPath !== reqPath) return;") == 2, \
        "loadDir 落袋/报错两路都须有过期响应丢弃守卫(恰两处)"
    assert "if (this._dirReqPath === reqPath) this.dirBrowse.loading = false;" in body, \
        "loadDir finally 未按戳守卫 —— 过期请求会闪一帧\"加载完\"假象(新在途请求持有 loading)"

    # ② doSearch: 落袋前比对当前搜索词
    m = re.search(r"async doSearch\(\)\s*\{(.*?)\n    \},", vw, re.S)
    assert m, "view.js 找不到 doSearch(改名或挪走了? 同步本守阵)"
    body = re.sub(r"//[^\n]*", "", m.group(1))
    assert body.count('if ((this.searchQuery || "").trim() !== q) return;') == 2, \
        "doSearch 落袋/报错两路都须比对当前搜索词(query 戳) —— 慢响应会把命中集覆写成旧词的"


def test_web_store_iteration_snapshot_race_guard(tmp_path):
    """Web 读侧快照竞态守阵(E-01, issue 26-10-06-0028) —— 迭代 store 期间原地增删不 500

    remove_torrent/restore_torrent(原地 pop/赋值)/reset_runtime(groups.clear)/
    grouping_mod._leave_group(del) 都在主循环线程; /api/search、/api/paths、/api/hr/*/entries
    与 Web 请求触发的视图重建(_build_* 系)在 Web 线程无锁迭代同一批 dict —— 修复前大库
    重叠窗口内必抛 "dictionary changed size during iteration"。守阵 = 写线程高频原地增删
    by_hash/groups/cross_group_conflict_warned 期间连续跑全部读侧迭代面, 断言零异常
    (读侧快照后 mutation 不再打进迭代中的 dict 视图; 写线程只碰非组员 hash, 免得踩
    组员快照的 by_hash[h] 查找 —— 那是成员一致性语义, 不属本条)。
    """
    import threading

    from auto_qb.webui.server.routes.hr import mark_local_present
    from helpers import FakeTorrent, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    n = 20000
    for i in range(n):
        mgr.store.by_hash[f"h{i}"] = FakeTorrent(hash=f"h{i}", name=f"t{i} 2026")
    # 分组索引给一点真形: 组 key = (save_path, files); 组员固定不动(见 docstring 口径)
    gkey = ("R:/seeds", ("a.mkv", ))
    mgr.store.groups[gkey] = ["h0", "h1", "h2"]
    mgr.store.cross_group_conflict_warned.add(("R:/seeds", "R:/other"))

    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            h = f"new{i}"
            mgr.store.by_hash[h] = FakeTorrent(hash=h, name="x")  # restore_torrent 形
            mgr.store.by_hash.pop(h, None)  # remove_torrent 形
            if i % 100 == 0:
                mgr.store.groups[(f"R:/tmp{i}", ())] = []  # _leave_group / reset_runtime 形
                mgr.store.groups.pop((f"R:/tmp{i}", ()), None)
                mgr.store.cross_group_conflict_warned.add((f"R:/tmp{i}", "R:/x"))
                mgr.store.cross_group_conflict_warned.discard((f"R:/tmp{i}", "R:/x"))
            i += 1

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    errors = []
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and not errors:
            try:
                mgr.search_torrents("t1")
                mgr._build_group_view()
                mgr._build_singles_view()
                mgr._build_flat_view()
                mgr._build_speed_totals()
                mgr._build_shows_view()
                mark_local_present([{"infohash_v1": "h1", "infohash_v2": ""}], mgr.store.by_hash)
            except RuntimeError as e:  # 修复前必抛: dictionary changed size during iteration
                errors.append(e)
    finally:
        stop.set()
        t.join()
    assert not errors, f"Web 读侧迭代与主循环原地增删并发仍崩溃: {errors[0]!r}"


def test_frontend_page_location_persisted():
    """顶层 page 与设置分区必须持久化 —— 刷新后停在原页(2026-09-25 用户报"设置页刷新会回到种子页")

    `page` 原本是**纯内存态**、初值恒 "groups" ⇒ 在设置页按 F5 必掉回辅种页, 编辑位置全丢;
    设置页里的分区(`hub.view`)同理, 只持久化顶层页会让「设置 → 站点」刷新后落到设置首页。
    两条都只有真浏览器看得见(pytest 全绿、界面行为退化), 故在此静态钉住四件事:
    1. 读侧**白名单**(只认 "settings", 不信任存储内容) + 写侧唯一漏斗;
    2. **启动必须补一次 cfgLoad** —— 设置页的配置树是按需加载的, 只改初值不改启动路径,
       首屏会停在「配置加载失败 + 重试」(`cfg.schema` 永远为 null);
    3. 恢复的分区 key 必须**对 schema 校验** —— 分区会随版本改名/删除, 否则停在空白分区;
    4. 恢复走 `hubGo`(懒加载与默认选中项都在那条路径里, 自己重写必漏一半)。
    """
    app = _app_bundle_text()
    m = re.search(r"function initialPage\(\)\s*\{(.*?)\n\}", app, re.S)
    assert m, "app.js 找不到 initialPage()(改名或挪走了? 同步本守阵)"
    assert "autoqb.ui.page" in m.group(1), "initialPage 未读 autoqb.ui.page —— 页面位置没有持久化"
    assert '=== "settings" ? "settings" : "groups"' in m.group(1), (
        "initialPage 必须白名单式取值(只认 settings, 其余落 groups) —— 直接回填存储内容会把脏值当页名"
    )
    assert re.search(r"^\s*page:\s*initialPage\(\),", app, re.M), "data() 的 page 初值未走 initialPage()"

    m = re.search(r"persistUiPage\(\)\s*\{(.*?)\n    \},", app, re.S)
    assert m, "app.js 找不到 persistUiPage()(改名或挪走了? 同步本守阵)"
    assert "autoqb.ui.page" in m.group(1), "persistUiPage 未写 autoqb.ui.page"
    m_watch = re.search(r"^\s*page\(\)\s*\{(.*?)\n    \},", app, re.S | re.M)
    assert m_watch and "this.persistUiPage()" in m_watch.group(1), ("watch(page) 未调 persistUiPage —— 切页不落盘, 刷新后仍掉回辅种页")
    m_poll = re.search(r"startPolling\(\)\s*\{(.*?)\n    \},", app, re.S)
    assert m_poll, "app.js 找不到 startPolling()(改名或挪走了? 同步本守阵)"
    poll = m_poll.group(1)
    assert 'this.page === "settings"' in poll and "this.cfgLoad()" in poll, (
        "startPolling 未在恢复到设置页时补一次 cfgLoad —— 首屏停在「配置加载失败 + 重试」"
        "(设置页的配置树是按需加载的)"
    )

    hub = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
    m = re.search(r"function initialHubView\(\)\s*\{(.*?)\n\}", hub, re.S)
    assert m and "autoqb.ui.hub" in m.group(1), "config_hub.js 的 initialHubView 未读 autoqb.ui.hub"
    assert re.search(r"^\s*view:\s*initialHubView\(\),", hub, re.M), "hub.view 初值未走 initialHubView()"
    assert re.search(r'"hub\.view"\(v\)\s*\{', hub), "缺少 hub.view 的 watcher —— 分区切换不落盘"
    assert 'localStorage.setItem("autoqb.ui.hub"' in hub, "hub.view 的 watcher 未写 autoqb.ui.hub"
    m = re.search(r"hubRestore\(\)\s*\{(.*?)\n    \},", hub, re.S)
    assert m, "config_hub.js 找不到 hubRestore()(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "this.cfg.schema" in body and "groups.some" in body, ("hubRestore 未对 schema 校验分区 key —— 分区改名/删除后刷新会停在空白分区")
    assert "this.hubGo(" in body, "hubRestore 应复用 hubGo(否则漏掉 trackers/rules 选中项与日志/HR 懒加载)"
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    assert "this.hubRestore()" in ed, "cfgLoad 成功后未调 hubRestore(schema 到手那一刻才校验得了分区 key)"


def test_frontend_unsaved_changes_guard_wiring():
    """设置页未保存改动防护接线守阵(issue 26-09-25-1702 / 报告 26-10-02-0508, 路线 U1-b)

    现象: 设置页改了配置没保存就刷新, 整棵树被服务端配置整体替换, 改动**静默丢**。
    定性: 页签切换是纯内存态(全仓无 pushState / location.hash), 丢失只发生在**真实页面重载**
    这一条路径上 —— 正好是 beforeunload 的覆盖区间。选的路线是 **U1-b 自绘框 + 原生兜底**:
      · 键盘刷新(F5 / Ctrl+R 族): keydown 里 preventDefault 拦掉默认刷新, 弹**自绘**三选一框
        (可写中文, 且多出「保存并刷新」这一支 —— 这是选 U1-b 而不选 U1-a 唯一买到的东西);
      · 其余真实导航(地址栏回车 / 关标签 / 后退): JS **取消不了**导航, 只能靠原生 beforeunload 框。
    两条链少一条就漏一半; 且**主动刷新前必须先摘掉原生兜底**(否则自绘框答完接着 reload 又弹一次
    原生框 = 双框连击, 报告 §6 的"去重")。不做草稿恢复(刷新即回到磁盘配置), 判据沿用 cfgDirty 单点。

    静态守阵钉住六件事(全是"pytest 全绿、界面行为退化"的形态):
    1. 自绘三选一框的基础设施(模板第三钮 + confirmThreeDialog + resolveModal("extra") 结算);
    2. 原生兜底随脏态**挂载 / 摘除成对**(常驻挂载 => Firefox 放弃 bfcache + 无改动也弹框的疲劳);
    3. 只拦 F5 / Ctrl+R 族(不抢任何其它键), 脏态为假时一声不吭, 已有弹窗时不叠框(交给原生兜底);
    4. 三分支语义(保存并刷新必须先看 cfgSave 的成败 / 放弃并刷新 / 留在此页);
    5. 主动刷新前摘兜底;
    6. 键盘监听在 lifecycle 注册、unmounted 撤除, 脏态 watcher 在 state.js 接线(漏接 = 整块静默消失)。
    """
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    fb = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    pop = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    st = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    lc = open(os.path.join(STATIC_ROOT, "shared", "lifecycle.js"), encoding="utf-8").read()

    # 1. 自绘三选一框: 第三钮(模板) + 入口(confirmThreeDialog) + "extra" 结算(resolveModal)
    assert 'v-if="modal.extraText"' in pop and "@click=\"resolveModal('extra')\"" in pop, \
        "popovers.html 缺第三钮渲染(三选一框退化成两钮 = 白选 U1-b)"
    assert 'extraText: "",' in fb, "ui_feedback.js _modalInit 缺 extraText(漏声明 = 模板键 undefined)"
    three = re.search(r"confirmThreeDialog\(title, body, opts = \{\}\) \{(.*?)\n    \},", fb, re.S)
    assert three and "extraText: opts.extraText" in three.group(1), \
        "缺 confirmThreeDialog(自绘刷新守卫的入口; 改名或挪走了? 同步本守阵)"
    assert 'resolve(choice === "extra" ? "extra" : true)' in fb, \
        "resolveModal 未把第三钮结算为 \"extra\"(三分支拿不到区分 = 只会保存或只会丢弃)"
    # 反向: 既有两钮契约不得被第三钮污染(confirmDialog 仍返回布尔)
    assert "okText: opts.okText || \"确认\", cancelText: opts.cancelText || \"取消\", danger: !!opts.danger," in fb

    # 2. 原生兜底: 挂 / 摘成对 + 幂等(只在 dirty 期存在)
    sync = re.search(r"cfgGuardSync\(on\) \{(.*?)\n    \},", ed, re.S)
    assert sync, "config_editor.js 缺 cfgGuardSync(原生兜底的挂摘单点; 改名? 同步本守阵)"
    body = sync.group(1)
    assert 'window.addEventListener("beforeunload"' in body and 'window.removeEventListener("beforeunload"' in body, \
        "beforeunload 必须挂摘成对 —— 只挂不摘 = 常驻监听(伤 bfcache + 无改动也弹框)"
    assert "if (want === !!this._cfgGuardOn) return;" in body, "cfgGuardSync 必须幂等(重复挂载 = 句柄堆叠)"
    # 判据单点: 与 actbar「有改动还没保存」同一条 cfgDirty, 不另立状态机
    guard = re.search(r"cfgGuardActive\(\) \{(.*?)\n    \},", ed, re.S)
    assert guard and "this.cfgDirty" in guard.group(1), \
        "守卫判据必须是 cfgDirty(另立判据 = 与页面上「有改动还没保存」两处各说各话)"
    # 反向: 不做草稿恢复 —— 配置树含 qbittorrent.password, 一律不得进 Web Storage(报告 §6)
    assert "sessionStorage" not in ed and "localStorage" not in ed, \
        "config_editor.js 不得碰 Web Storage(整树入存会把 qbittorrent.password 摆上 XSS 面; 草稿另开议题)"

    # 3. 只拦 F5 / Ctrl+R 族; 无改动放行; 已有弹窗不叠框
    key = re.search(r"_cfgOnReloadKey\(e\) \{(.*?)\n    \},", ed, re.S)
    assert key, "config_editor.js 缺 _cfgOnReloadKey(键盘刷新拦截; 改名? 同步本守阵)"
    body = key.group(1)
    assert 'e.code === "F5"' in body, "键盘拦截必须覆盖 F5(硬刷新 Ctrl/Shift+F5 同族)"
    assert 'e.code === "KeyR"' in body and "e.ctrlKey || e.metaKey" in body, \
        "键盘拦截必须覆盖 Ctrl+R / Cmd+R 族(用 e.code 物理键位, 与快捷键引擎同口径)"
    assert "e.preventDefault();" in body, "命中刷新键必须 preventDefault(不取消默认刷新 = 自绘框白弹)"
    assert "if (!this.cfgGuardActive()) return;" in body, \
        "无未保存改动时必须放行(每次刷新都弹 = 弹框疲劳, 用户会闭眼点离开)"
    assert "if (this.modal.visible) return;" in body, \
        "已有弹窗时必须放行(自绘框叠在弹窗上 = 上一个悬空 Promise 被静默结算为取消)"

    # 4. 三分支语义: 保存并刷新必须先看 cfgSave 成败(保存失败带着改动刷新 = 白丢)
    rel = re.search(r"async cfgReloadGuard\(\) \{(.*?)\n    \},", ed, re.S)
    assert rel, "config_editor.js 缺 cfgReloadGuard(自绘刷新守卫; 改名? 同步本守阵)"
    body = rel.group(1)
    assert "confirmThreeDialog(" in body, "刷新守卫必须弹自绘三选一框(U1-b 的落点)"
    for token in ("保存并刷新", "放弃改动并刷新", "留在此页"):
        assert token in body, f"三选一框缺「{token}」分支(自绘的意义就在这三个选项上)"
    assert "await this.cfgSave()" in body and "if (!saved) return;" in body, \
        "「保存并刷新」必须判 cfgSave 的成败 —— 保存失败却刷新 = 改动照样丢"
    save = re.search(r"async cfgSave\(\) \{(.*?)\n    \},", ed, re.S)
    assert save and "return true;" in save.group(1) and "return false;" in save.group(1), \
        "cfgSave 必须返回成败布尔(「保存并刷新」靠它决定刷不刷新)"

    # 5. 主动刷新前摘兜底(否则 reload 会再弹一次原生框 = 双框连击)
    assert "this.cfgGuardRelease();" in body and "location.reload()" in body, \
        "刷新前必须 cfgGuardRelease() + location.reload()(漏摘 = 自绘框答完又答一遍原生框)"
    assert "cfgGuardSync(false)" in re.search(r"cfgGuardRelease\(\) \{(.*?)\n    \},", ed, re.S).group(1)

    # 6. 接线: lifecycle 注册 / 撤除 + state.js 脏态 watcher
    assert 'this._cfgGuardKey = (e) => this._cfgOnReloadKey(e);' in lc and \
        'document.addEventListener("keydown", this._cfgGuardKey)' in lc, \
        "lifecycle.js 未注册键盘刷新拦截(漏注册 = 整块功能静默消失)"
    unm = re.search(r"unmounted\(\) \{(.*?)\n  \},", lc, re.S)
    assert unm and 'removeEventListener("keydown", this._cfgGuardKey)' in unm.group(1), \
        "lifecycle.js unmounted 未撤除键盘拦截(热重载后句柄堆叠, 一次按键弹 N 个框)"
    assert "this.cfgGuardRelease();" in unm.group(1), "unmounted 未摘原生兜底(同上, 防堆叠)"
    assert re.search(r"cfgDirty\(v\) \{\s*this\.cfgGuardSync\(v\);", st), \
        "state.js 缺 cfgDirty watcher —— 兜底不随脏态挂载(要么永不弹, 要么常驻弹)"


def test_frontend_expand_state_survives_view_switch():
    """展开态必须跨视图带走 —— 切走收进桶、切回还回去(2026-09-25 用户报「辅种页切到种子页再切回, 展开的组收起来了」)

    现象与定性:
    旧 `setViewMode` 里三行 `expandedKey / expandedShows / expandedShowEp = null`, 展开态**随切页丢掉**。
    展开态是"我正盯着这一组"这种临时意图, 跟"停在哪个视图"一样该跟着人走 —— 切到种子页再切回来,
    应该还是原来展开的那一组(不是"重新点开一次")。
    改法是**按视图分桶暂存**(`expandMemo`): 切走收进桶并清空实时字段(展开态仍不串台到别的视图),
    切回还回该视图最后一次的展开。

    两条反向约束(少一条就会把修好的东西又弄坏):
    1. **还回前必须验"那一行还在"** —— 组可能已被删或被筛掉;
    2. `groupWin` 的退避判据必须同步成"**当前真的有面板**" —— 只判 `expandedKey` 非空的话,
       一个过期的键会让行窗口永久退避(大库上 = 悄悄关掉 P1-2 优化, 界面看着完全正常, 只是滚动变卡)。
    """
    app = _app_bundle_text()
    m = re.search(r"setViewMode\(mode\)\s*\{(.*?)\n    \},", app, re.S)
    assert m, "app.js 找不到 setViewMode(mode)(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "this.stashExpandState()" in body, "setViewMode 未 stash 展开态 —— 切页即丢, 切回不还原"
    assert "this.restoreExpandState(mode)" in body, "setViewMode 未 restore 展开态 —— 切回分组页展开的组收起来了"
    dropped = re.findall(r"this\.expanded(?:Key|Shows|ShowEp)\s*=", body)
    assert not dropped, (f"setViewMode 里仍有 {len(dropped)} 处置空展开态的赋值 —— 展开态会随切页丢掉(应走 stash/restore)")

    m = re.search(r"restoreExpandState\(mode\)\s*\{(.*?)\n    \},", app, re.S)
    assert m, "app.js 找不到 restoreExpandState(mode)(改名或挪走了? 同步本守阵)"
    restore = m.group(1)
    assert "this.groups.some(" in restore, ("restoreExpandState 未验展开的组是否还在 —— 组已被删/被筛掉时留下悬空 expandedKey")
    assert "this.expandedKey = key" in restore, "restoreExpandState 未把分组展开键还回 expandedKey"

    cols = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
    m = re.search(r"groupWin\(\)\s*\{(.*?)\n    \},", cols, re.S)
    assert m, "columns.js 找不到 groupWin()(改名或挪走了? 同步本守阵)"
    win = m.group(1)
    assert "if (this.expandedKey) return" not in win, ("groupWin 仍只按 expandedKey 非空退避 —— 过期的键会让行窗口永久退化成全量渲染")
    assert "this.expandedKey" in win and ".some(" in win, ("groupWin 的退避判据必须带上'展开的组确实在可见集合里'这一条")


def test_frontend_hub_field_covers_non_leaf_items():
    """hub-field 必须覆盖 cfgFlatten 产出的**全部**项类型 —— 缺了非叶子那三支就显示 `[object Object]`

    现象与定性(2026-09-25 用户报「设置页部分设置项显示 [object Object]」):
    `cfgFlatten` 把嵌套 object 展开成 **四种** item.type —— field(叶子) / section(可选段) /
    group(普通 object 段) / subcard(父字段的相关设置子卡)。`tpl-hub-field` 的控件分支
    (bool / enum / list / rules_ref / keyed_list / 数值+单位) 末尾是一个**无条件**的 `<input v-else>`,
    值取 `cfgInputValue` → `cfgScalar` → `String(value)`: 叶子字段存的是标量没问题, 而
    section / group / subcard 这条路径上存的是**对象**(如 `config.trackers.<站点>.hr`),
    `String({...})` 恰好是 "[object Object]" ⇒ 站点页「HR 规则」「HR 在线核实」与规则页
    checking 的 with_reference / without_reference 两个分支整行都显示这个串; 更糟的是**随手一改
    就把配置写成这个字符串**, 保存时后端校验才报错。

    根因: 经典设置页的 `tpl-ce-field` 有这三支, 清理死代码时随模板一起被删, 而 `cfgFlatten`
    仍会产出这三类项, 站点 / 规则两个专段又把扁平结果直接交给 hub-field(普通分区页的
    `hubBlocks` 只挑 `type === "field"`, 所以只有这两个专段暴露出来)。

    守阵两条:
    1. 两套皮肤的模板都必须**逐个**判 `item.type === '<非叶子类型>'`, 类型名单从 config_editor.js
       的 cfgFlatten 实读(将来新增类型忘了加分支 → 立刻红, 不靠人记);
    2. 叶子分支必须是链尾的 `v-else` —— 否则非叶子项会有绕回兜底 input 的路径。
    """
    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    kinds = set(re.findall(r'type:\s*"(field|section|group|subcard)"', editor))
    assert "field" in kinds, "config_editor.js 里找不到 cfgFlatten 的 type: \"field\"(改名/挪走了? 同步本守阵)"
    non_leaf = sorted(k for k in kinds if k != "field")
    assert non_leaf, ("config_editor.js 的 cfgFlatten 不再产出任何非叶子项类型 —— "
                      "若嵌套段真的取消了, 本守阵该跟着撤, 别让它空转")

    for skin in _UI_ALL:
        html = _ui_aggregate(skin)
        m = re.search(r'<script type="text/x-template" id="tpl-hub-field">(.*?)\n  </script>', html, re.S)
        assert m, f"{skin}/index.html 找不到 tpl-hub-field 模板(改名/挪走了? 同步本守阵)"
        tpl = m.group(1)
        for kind in non_leaf:
            assert f"item.type === '{kind}'" in tpl, (
                f"{skin} 的 tpl-hub-field 缺 `item.type === '{kind}'` 分支 —— 该类项会落进叶子字段的"
                "兜底 <input>, 值被 String(对象) 成 '[object Object]'(且一改就把配置写成这个串)"
            )
            assert "item.items" in tpl, f"{skin} 的 tpl-hub-field 未递归渲染 item.items —— 段内子字段会整段消失"
        assert re.search(
            r'<div\s+v-else\s+class="hb-row"', tpl
        ), (f"{skin} 的 tpl-hub-field 叶子分支不是链尾的 <div v-else class=\"hb-row\"> —— "
            "非叶子项仍有掉进兜底 input 的路径")
        assert 'v-if="item.type === \'section\'"' in tpl, (
            f"{skin} 的 tpl-hub-field 首个分支必须带 v-if(链头), 否则 v-else-if 链不成立"
        )


def test_frontend_hub_field_renders_readonly_fields():
    """schema Field.readonly(程序托管字段)在设置页必须渲染为禁用控件(静态防回潮)

    issue 26-09-28-2135: schema_version/data_dir/state_file/fs 打 readonly 标 —— 这些字段的
    用户输入会被后端无条件覆盖/回退(程序盖章、R 级回退、readonly 键面防线), UI 若仍渲染
    可编辑控件, 反馈就是误导性的「已保存」。守阵四查(每套皮肤):

    1. CE_FIELD_BASE 必须有 readonly/readonlyComplex/readonlySummary 三个成员 ——
       HUB_FIELD_COMPONENT 经 Object.assign 继承, 缺一个模板引用就是 undefined 静默失效;
    2. tpl-hub-field 控件链**首支**必须是 readonly 的只读摘要分支(readonlyComplex) ——
       列表/对象值(fs.path_map)落进输入框会 String 化成 "[object Object]";
    3. 全部可编辑控件都挂 :disabled="readonly"(bool/enum/list/rules_ref/keyed_list/
       数值+单位两件套/文本 至少 7 处, 漏一处 = 该类 readonly 字段仍可改);
    4. 叶子行带「程序维护」徽标; settings-detail 的块级 section 开关对 readonly 段换徽标
       (fs 段的启用/关闭开关在那里, 不禁用就能把整段从 UI 删掉)。
    """
    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    for member in ("readonly()", "readonlyComplex()", "readonlySummary()"):
        assert member in editor, f"config_editor.js 的 CE_FIELD_BASE 缺 computed {member} (模板引用会 undefined 静默失效)"

    for skin in _UI_ALL:
        html = _ui_aggregate(skin)
        m = re.search(r'<script type="text/x-template" id="tpl-hub-field">(.*?)\n  </script>', html, re.S)
        assert m, f"{skin} 找不到 tpl-hub-field 模板(改名/挪走了? 同步本守阵)"
        tpl = m.group(1)
        assert 'v-if="readonlyComplex"' in tpl, (
            f"{skin} 的 tpl-hub-field 缺 readonly 只读摘要分支(链首) —— "
            "列表/对象值(fs.path_map)会落进输入框 String 化成 '[object Object]'"
        )
        n_disabled = tpl.count(':disabled="readonly"')
        assert n_disabled >= 7, (
            f"{skin} 的 tpl-hub-field 只有 {n_disabled} 处 :disabled=\"readonly\"(须 >= 7) —— "
            "bool/enum/list/rules_ref/keyed_list/数值+单位两件套/文本 的控件要全挂禁用"
        )
        assert '<span v-if="readonly" class="hb-badge">程序维护</span>' in tpl, (f"{skin} 的 tpl-hub-field 叶子行缺「程序维护」徽标")
        # 块级 section 开关(settings-detail 分片): readonly 段不渲染启用/关闭, 换「程序维护」徽标
        assert "b.item.field && b.item.field.readonly" in html, (
            f"{skin} 的 settings-detail 块级 section 开关未对 readonly 段收口 —— fs 段可从 UI 整段删除"
        )


def test_frontend_keyed_list_toggle_deletes_key_when_emptied():
    """keyed_list 勾选框取消**最后一项**必须删键, 不能写空列表(静态防回潮)

    现象(2026-10-10 报障, notify.channels 是当时唯一用上该 kind 的字段): toggleKey 把最后
    一项 splice 掉后仍 `cfgSetPath(path, [])` —— 两个后果同源:
    ① 空列表与"键缺失"**不同构**, 而脏标记是全树 JSON 对比(cfgDirty), 于是「勾选再取消」
       之后照样提示"有改动还没保存", 界面上却看不出任何差异(用户无从自救);
    ② 空列表过不了后端校验(config.notify.channels: 必须是非空列表), 保存必败 —— 报错里还
       带一个临时文件路径, 用户看不到是哪一项有问题。

    定稿口径 = 与同文件 cfgItemRemove 一致: 清空即 cfgDelPath(删键 = 回到"未配置"), 勾选再
    取消因此是零副作用的可逆操作。本守阵钉住: 写回必须挂在长度守卫里, 空则走删键。
    """
    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    m = re.search(r"toggleKey\(name\)\s*\{(.*?)\n    \},", editor, re.S)
    assert m, "config_editor.js 里找不到 toggleKey(name)(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "cfgDelPath(this.path)" in body, ("toggleKey 取消最后一项时未删键 —— 写空列表会让脏标记消不掉, 且保存被后端「必须是非空列表」拒")
    assert re.search(r"if \(list\.length\) this\.ce\.cfgSetPath\(this\.path, list\);",
                     body), ("toggleKey 的 cfgSetPath 未挂长度守卫 —— 空列表会原样写回树(见 cfgItemRemove 的同口径写法)")


def test_frontend_flatten_skips_hidden_fields():
    """schema Field.hidden(暂不图形化)必须在 cfgFlatten 里被跳过(静态守阵)

    背景(2026-10-10 报障, notify.channels 是第一个用到它的字段): 键合法但 UI 表达不出有效
    差异时, 正确处置是打 hidden 让设置页不渲染 —— **不是**从 schema 摘字段(键面守卫以 schema
    为键面单点, 摘了会被判成删键, 要走抬版本 + 注册迁移的破坏性流程)。而 hidden 只有在
    cfgFlatten 里跳过才真的生效: 两套 UI 的 hub 页与经典设置页都由它供给渲染项, 漏了这条
    skip = 字段照样出现在界面上, 报障原样复发。
    """
    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    m = re.search(r"cfgFlatten\(fields, basePath, depth, ownerPath[^\n]*\n(.*?)\n      const byKey", editor, re.S)
    assert m, "config_editor.js 里找不到 cfgFlatten 的分组循环(改名或挪走了? 同步本守阵)"
    assert "f.hidden" in m.group(1), ("cfgFlatten 未跳过 f.hidden —— 打了 hidden 的字段仍会渲染进设置页(两套 UI 同源于此函数)")
    assert re.search(r"if \(f\.hidden\) continue;", m.group(1)), "hidden 的跳过必须是 continue(整项不进渲染项表)"


def test_frontend_statusbar_speed_reads_server_totals():
    """状态栏速度必须读服务端标量 status.totals, 不得改回对 groups 求和(静态防回潮)

    issue 26-09-20-1646: 旧实现是 `totalDl() { return this.groups.reduce(...) }` —— 而 groups
    **按视图回传**(VIEW_ARRAYS: 种子页不回它), 于是状态栏在种子页恒为 0(首屏即种子页)或
    停在**冻结的旧值**(先开过辅种页再切过来), 并且漏掉未归组 singles(实测少算 88.7%)。
    Python 侧单测看不见这种"界面废掉", 只能静态钉住这两个 computed。
    """
    import re

    text = open(os.path.join(STATIC_ROOT, "shared", "decorate.js"), encoding="utf-8").read()
    for name in ("totalDl", "totalUl"):
        m = re.search(rf"\n    {name}\(\) \{{(.*?)\n    \}},", text, re.S)
        assert m, f"decorate.js 里找不到 computed {name}(改名或挪走了? 同步本守阵)"
        body = m.group(1)
        assert "this.groups" not in body, (
            f"{name} 又在对 this.groups 求和: groups 是按视图回传的(种子页不回) "
            f"⇒ 状态栏恒为 0 或停在旧值(issue 26-09-20-1646)"
        )
        assert "status.totals" in body, f"{name} 必须读服务端恒回传的 status.totals: {body.strip()}"


def test_frontend_bulk_bar_retired():
    """批量控制条退役守阵(2026-10-05) —— 防回潮

    用户拍板: 移除筛选行里"已选 N 个种子 · 开始/暂停/…"的批量控制条, 批量动作一律走
    **右键批量菜单**(被右键行属于选中集合时升级为 menu.multi 分支, 见 ctx-menus.html)。
    控制条是模板 + 三套 CSS + 一批 JS 助手的组合, 最容易的退化形态是"只删模板、CSS/JS 残留"
    或"某套 UI 的 CSS 没删干净"(皮肤间静默不一致 —— 用户看到的仍是半残控制条)。逐层钉住:
      1. 三套 UI 的聚合模板里 .bulk-inline / bulkAct( / bulkDeleteLabel( / bulkHrWarnText( /
         name="bulk" 零残留;
      2. 三套 UI 的 CSS 聚合里 .bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/
         .bulk-enter-*/.ico-select 与 @keyframes bulk-in 零残留(死样式零残留纪律);
      3. 批量链路本身仍在(右键菜单要用): bulkAct/bulkDelete 定义保留, ctxAct/ctxDelete 复用。
    """
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        for token in (".bulk-inline", "bulkAct(", "bulkDeleteLabel(", "bulkHrWarnText(", 'name="bulk"'):
            assert token not in text, f"{ui} 模板仍残留批量控制条痕迹 {token!r} —— 已退役, 应零残留"
        css = _ui_css_aggregate(ui)
        for token in (
            ".bulk-inline", ".bulk-btn", ".bulk-hr-warn", ".bulk-sep", ".bulk-count", ".bulk-enter", ".bulk-leave",
            ".ico-select", "@keyframes bulk-in"
        ):
            assert token not in css, f"{ui} CSS 仍残留死样式 {token!r} —— 批量控制条已退役, 应删除"
    # 批量链路仍在: 右键批量菜单要用(定义在 shared/commands.js / delete_flow.js)
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    assert "async bulkAct(action) {" in cmd, "bulkAct 定义消失 —— 右键批量菜单的动作链断了"
    assert "return this.bulkAct(action);" in cmd, "ctxAct 必须继续复用 bulkAct"
    dfl = open(os.path.join(STATIC_ROOT, "shared", "delete_flow.js"), encoding="utf-8").read()
    assert "async bulkDelete() {" in dfl, "bulkDelete 定义消失 —— 右键批量删除断了"
    assert "bulkHrWarnText" not in dfl and "bulkDeleteLabel" not in dfl, (
        "死方法 bulkHrWarnText/bulkDeleteLabel 应已随批量控制条删除(零消费方)"
    )


def test_api_group_commands_enqueue(web_env):
    """pause/resume/reannounce 命令入队: key 解码回原 tuple, 主循环侧执行"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    enc = encode_group_key(KEY)
    for action in ("pause", "resume", "reannounce"):
        resp = client.post(f"/api/groups/{enc}/{action}", headers=auth)
        assert resp.status_code == 200, resp.text
    cmds = [mgr.web.commands.get_nowait() for _ in range(3)]
    assert [c for c, _ in cmds] == ["pause_group", "resume_group", "reannounce_group"]
    assert all(p["key"] == KEY for _, p in cmds), "key 应解码回原 tuple"


def test_api_group_malformed_key_returns_400(web_env):
    """畸形分组 key -> 400(客户端错误), 不是 500

    `decode_group_key` 对 base64 非 ASCII / 非法 JSON / 结构不符分别抛 ValueError 系与
    TypeError/IndexError; 不拦截就是 500 + 栈回溯 —— 手输或被篡改的 URL 都能打出服务端错误页。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    bad_keys = [
        "!!!not-base64!!!",  # 非法 base64 → binascii.Error
        base64.urlsafe_b64encode(b"not json{").decode(),  # 合法 base64, 解出非法 JSON
        base64.urlsafe_b64encode(b"123").decode(),  # 合法 JSON 但结构不符(不可下标)→ TypeError
    ]
    for bad in bad_keys:
        resp = client.post(f"/api/groups/{bad}/pause", headers=auth)
        assert resp.status_code == 400, f"{bad!r} 应回 400, 实际 {resp.status_code}: {resp.text}"
        assert mgr.web.commands.empty(), "畸形 key 不该投递命令"


def test_api_delete_with_files_flag(web_env):
    """delete 命令透传 delete_files 标志(默认 False 保留文件)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    enc = encode_group_key(KEY)
    client.post(f"/api/groups/{enc}/delete", headers=auth, json={"delete_files": True})
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "delete_group" and payload["delete_files"] is True


def test_api_cmd_result_endpoint(web_env):
    """命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/torrents/HA/reannounce", headers=auth)
    assert resp.status_code == 200
    cmd_id = resp.json()["cmd_id"]
    assert cmd_id, "投递响应应携带 cmd_id"
    assert client.get(f"/api/cmd/{cmd_id}", headers=auth).json() == {"status": "pending"}
    mgr.web.results[cmd_id] = {"status": "ok", "error": "", "ts": 123.0}
    assert client.get(f"/api/cmd/{cmd_id}", headers=auth).json() == {"status": "ok", "error": "", "ts": 123.0}
    # 其余命令端点同样携带 cmd_id(delete 返回体保留 delete_files 标志)
    enc = encode_group_key(KEY)
    assert client.post(f"/api/groups/{enc}/pause", headers=auth).json()["cmd_id"]
    delete_resp = client.post(f"/api/groups/{enc}/delete", headers=auth, json={"delete_files": True}).json()
    assert delete_resp["cmd_id"] and delete_resp["delete_files"] is True


def test_api_traffic_history_endpoint(web_env):
    """/api/traffic/history: 透出限速曲线任务发布的按日 history; 未启用时返回空数组"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/traffic/history", headers=auth).json() == {"state": "disabled", "history": []}
    mgr.web.traffic_view = {
        "state": "ok",
        "history": [{
            "date": "2026-09-14",
            "up": 1024,
            "down": 2048
        }],
    }
    data = client.get("/api/traffic/history", headers=auth).json()
    assert data["state"] == "ok" and data["history"][0]["date"] == "2026-09-14"
