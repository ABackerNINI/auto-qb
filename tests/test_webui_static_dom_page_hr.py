"""test_webui_static_dom_page_hr 测试计划: webui 前端静态守阵: 页面 / 列模型 / 视图

## 测试计划(每个测试函数一条)
- test_frontend_hr_diag_view_wiring: HR 表② 排障视图前端接线守阵(计划 26-10-01-2216 阶段3) —— 站点卡片 <details> 默认收起(无 open 属性)/ summary 文案 / 站点级 kv 行(hrsKvRows)与各档波次明细行(lanes[].detail 首获展示位)模板绑定 + 展开态不持久化(hr_status.js 无 localStorage)+ .hrs-diag/.hr-diag-kv/.hr-wave-table 三套 UI CSS 成对(波次表同挂 .hr-detail-table 继承表① 徽章色义)
- test_frontend_hr_full_modal_wiring: HR 站点状态折叠 + 覆盖式全屏弹窗守阵(计划 26-10-02-1936 阶段2) —— aqb:hr-full-modal 扫描锚段内遮罩/面板/头部(标题+摘要+✕)绑定齐全、有「展开/收起」钮且无独立「全屏」钮、面板无预展开属性(v-show 挂 hrsOpen); hrsOpen 默认 false(state.js)不持久化(hr_status.js/config_hub.js/state.js 无该键的 localStorage 写读); hubGo 不再自动拉数只复位 hrsOpen; ESC 关闭进 lifecycle 退栈链且同步 escBusy 名单(dialogs.js), 先于 1632 清筛选兜底; 首次展开才拉(hrsToggle 未 loaded 即调 loadHrStatus)、无 setInterval; .hr-full-mask/.hr-full-modal 三套 UI CSS 成对(prism 落 components.css)
- test_frontend_hr_contract_keys_match_backend: HR 两张表消费键契约守阵(计划 26-10-01-2216 阶段4 + 26-10-02-1936 阶段3 扩) —— 从前端源码提取消费键(表① e.*: 模板 aqb:hr-detail-table 段 + hr_status.js 行辅助与行集函数; 表② s.*/ls.*: hr_status.js 全文件 + aqb:hr-diag 模板段), 断言 ⊆ EntryDetail/SiteStatus/LaneStatus 的 to_dict 键集(后端侧闭集钉法 test_entry_details_field_surface 挡不住「上游改键+同步改 expected」的前端静默落空), 每组带核心键在场断言防提取器失效变恒真; 幻键集必须为空(表② 徽章人话 ls.lane_text 曾是幻键致渲染为空, 已修: LaneStatus 补 lane_text 字段由 _lane_statuses 填充, 白名单收空守阵恢复严格; local_present 是响应层 mark_local_present 追加的合法豁免)
- test_frontend_hr_history_wiring: HR 表③ 拉取历史前端接线守阵(计划 26-10-04-0312 §3.5/§05 S4) —— aqb:hr-history 扫描锚 begin/end 成对且段内 <details> 默认收起 + summary 文案 + 站点 chips(hrsHistSiteChips 行内集合现算)+「仅看异常」toggle + 刷新钮 + 「数据截至」时间戳 + 十列表头(时间/站点/触发/结果/页数/行数/回填/放行/耗时/说明)+ 明细行 v-for 与展开明细子行(hr-hist-sub)+ 空态/未启用态文案 + read_errors 点名行; 取数纪律: 首次展开才 fetch(limit=300, @toggle -> hrsHistEnsureLoaded)+ 「刷新」手动重拉(hrsHistReload)+ 无 setInterval + 站点过滤纯前端本地筛不拼 site 查询串; 展开态不持久化(hr_status.js 代码态零 localStorage); .hr-hist-table/.hr-hist-row/.hr-hist-sub/.hr-hres 及五档色义(ok/warn/dim/err/blue)三套 UI CSS 成对

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console, 按 _UI_ALL 枚举的接线守阵随常量自动收编; 单独点名的三套成对面(HR 表②/全屏弹窗/
  表③)已显式加 flux 档。
"""

import base64

import json

import os

import re

import shutil

import subprocess

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
    4. 列定义单点(P5, 计划 26-10-11-1722): 波次表表头改由模板按 HR 表注册表摆列(hrsWaveCols,
      hr_status.js 的 HR_TABLE_DEFS.hrWave) —— 原来 8 个 <th> 是硬编码字面量; 表头仍不接排序
      (sortable 零残留, 排序面由 test_frontend_hr_table_sort_filter_reorg_wiring 钉)。
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
        ("hrsWaveCols()", "波次表列定义取 HR 表注册表(计划 26-10-11-1722 P5 表身份单点)"),
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

    # 3. CSS 各套成对(表② 新类; flux 收编 plan 26-10-31-2316 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
        (_ui_css_aggregate("flux"), "flux css 聚合(link 序)"),
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

    # 5. CSS 各套成对: 遮罩 + 面板 + 上下边界让出声明(flux 收编 plan 26-10-31-2316 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
        (_ui_css_aggregate("flux"), "flux css 聚合(link 序)"),
    ):
        for cls in (".hr-full-mask", ".hr-full-modal"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5 阶段2)"
        assert "--head-h" in css and "--statusbar-h" in css, \
            f"{name} 的全屏覆盖层缺顶栏/状态栏让出声明(--head-h / --statusbar-h)"
    pri_dialogs = open(os.path.join(STATIC_ROOT, "prism", "css", "dialogs.css"), encoding="utf-8").read()
    assert ".hr-full-modal" in pri_dialogs, "prism/css/dialogs.css 缺全屏覆盖层段(与 .modal-mask 同文件)"


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

    # 4. CSS 各套成对: 表③ 新类 + result_tone 五档色义(flux 收编 plan 26-10-31-2316 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
        (_ui_css_aggregate("flux"), "flux css 聚合(link 序)"),
    ):
        for cls in (".hr-hist-table", ".hr-hist-row", ".hr-hist-sub", ".hr-hres"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5.6)"
        for tone in ("ok", "warn", "dim", "err", "blue"):
            assert f".hr-hres.hr-hres-{tone}" in css, f"{name} 缺 .hr-hres-{tone} 色义(result_tone 五档)"
