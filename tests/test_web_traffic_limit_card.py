"""test_web_traffic_limit_card 测试计划: 「流量与限速」合并卡与通用层两修(计划 26-10-18-0813 P2-B)

本文件只钉 P2-B(B1–B5)的**结构契约**, 不重复既有守阵:
- 后端快照/契约见 test_traffic_snapshot.py(P2-A);
- 工具联动端点见 test_web_traffic_monitor.py(块闸/单位控件/关闭工具一带的细项)。
这里是"结构搬了家、判据不能松"的那一层 —— 全部是源码级断言(无浏览器), 每条都对应一种
**静默故障形态**: 模板在、界面空; 键改了、旧偏好落空; 声明了 show_if、实际上没生效。

## 测试计划(每个测试函数一条)
- test_schema_merged_group_replaces_three: schema 层 8 -> 6 组, traffic_limit 含三字段且序 =
  卡内区序; 旧组 key(speed/traffic/traffic_source)在 schema 里彻底消失(残留 = 首页多一张空卡)
- test_frontend_card_component_wiring: aq-traffic-card 注册 + 分片 x-template id 对齐 + inject/provide
  透传(不透传 -> 卡内 hub-field 拿到的是本组件实例, 字段只显默认值)
- test_frontend_card_three_zones_and_collapse: 三区顺序 / 各自折叠头 / 折叠态不持久化 /
  来源关闭时三区都给出说明而非空白
- test_frontend_card_history_entry: 摘要条「打开历史图表」-> openHistory()(历史图仍在全局弹层)
- test_frontend_dep_hint_shares_affect_labels: 提示条文案与关闭工具确认框同源(tmAffectLabels)
- test_frontend_hub_view_alias_maps_old_keys: 旧 hub.view 三个值都映射到 traffic_limit, 且映射只在
  取值处单点(不清 localStorage)
- test_frontend_show_if_applies_to_sections: 通用渲染对 group/section 项也走 cfgVisible
  (不再 `type !== "field" -> true` 短路) —— 变异: 恢复短路即红
- test_frontend_hub_skip_paths_is_single_point: 排除表是单点常量, 源码里没有散落的路径比较
- test_frontend_settings_fragment_shrinks: settings.html 只剩挂载行(不再含 tm* 调用), 体量 < 400
"""
import os
import re

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

SHARED = os.path.join(STATIC_ROOT, "shared")


def _shared(*parts) -> str:
    return open(os.path.join(SHARED, *parts), encoding="utf-8").read()


def _card() -> str:
    return _shared("tpl", "traffic-card.html")


# ---- B1: schema 合组 ----


def test_schema_merged_group_replaces_three():
    """B1/D13/D17: 三组并一组 —— 组数 6, 字段序 = 卡内区序, 旧组 key 清零

    旧 key 残留的两种后果都是静默的: hub.view 落到旧 key 会渲染空白二级页(模板分支已删),
    首页卡按 schema.groups 生成则多出没有内容的卡。
    """
    from auto_qb.config.schema.groups import GROUPS

    keys = [g.key for g in GROUPS]
    assert keys == ["basic", "trackers", "maintenance", "traffic_limit", "rules", "hr_check"], keys
    for old in ("speed", "traffic", "traffic_source"):
        assert old not in keys, f"旧组 key {old!r} 仍在 schema 里(hub.view 会落到没有模板分支的空页)"

    grp = next(g for g in GROUPS if g.key == "traffic_limit")
    assert [f.key for f in grp.fields] == ["traffic_source", "global_speed_limit_curve", "qb_traffic"], \
        "字段序必须 = 卡内区序(来源 -> 限速曲线 -> 流量图采样), 前端区序与 schema 序是同一个事实"
    # 组 label 是首页卡/面包屑/页头的回落文案(缺 HUB_GROUP_META 时用), 必须与视图名一致
    assert grp.label == "流量与限速"


# ---- B3: 组件与分片接线 ----


def test_frontend_card_component_wiring():
    """B3/D15: 组件注册 + 模板 id 对齐 + inject/provide 透传

    !不透传 ce 是这里最隐蔽的一种: 全局 mixin 给每个组件都 provide 了 `ce: this`, 于是卡内的
    hub-field 注入到的是**本组件实例**(没有 cfg* 方法) —— 表现为字段只显默认值、编辑不进根树,
    而且不报错(注入成功, 只是注入错了对象)。
    """
    js = _shared("traffic_card.js")
    app = _shared("app.js")
    tpl = _card()

    assert 'app.component("aq-traffic-card", window.AQ_TRAFFIC_CARD_COMPONENT)' in app, \
        "app.js 未注册 aq-traffic-card(组件不注册 -> 模板里只剩未知标签, 整卡空白)"
    assert 'name: "aq-traffic-card"' in js
    assert 'template: "#tpl-aq-traffic-card"' in js
    assert 'id="tpl-aq-traffic-card"' in tpl, "模板分片的 x-template id 与组件 template 选择器不一致"
    assert 'inject: ["ce"]' in js and "return { ce: this.ce }" in js, \
        "缺 ce 透传: 卡内 hub-field 注入到的是组件实例而非根实例(字段只显默认值)"
    # 纯模板件: 组件里不得定义 methods(与根 mixin 同名会被静默覆盖)
    assert "methods" not in js, "组件里定义了 methods —— 与 config_hub.js 的同名方法会互相覆盖"

    # 三皮肤清单逐项相等由 test_webui_static_skins 钉住, 这里只断"分片被挂上且落 body"
    for ui in _UI_ALL:
        parts = {os.path.basename(p["src"]): p for p in _ui_manifest(ui)["parts"]}
        assert "traffic-card.html" in parts, f"{ui} 清单漏挂 traffic-card.html(该卡整块消失)"
        assert parts["traffic-card.html"]["into"] == "body", \
            "x-template 必须注入 body(进 #app 会当根模板编译, 多包一层 DOM)"
        assert "/shared/traffic_card.js" in _ui_manifest(ui)["scripts"], f"{ui} 清单缺 traffic_card.js"


# ---- B4: 卡内三区 ----


def test_frontend_card_three_zones_and_collapse():
    """B4/D2/D14: 三区(数据来源 -> 限速曲线 -> 流量图采样) + 可折叠头 + 折叠态不持久化

    区序写在模板里即"读的时候从上到下就是取数链": 先定来源, 再定限速, 最后才是与配置无关的
    qB 采样记录。折叠态**不持久化**是刻意的(与站点状态块/运行日志同口径) —— 记进 localStorage
    只会让下次进来先看到三个标题。
    """
    tpl = _card()
    hub = _shared("config_hub.js")

    # 每个区头都是 <aq-fold>(模板层唯一折叠实现, 见 tpl/ctl-bits.html 头注) —— 标题经 title prop,
    # 切换回调到 hubSubToggle。26-10-20-2231 前这里是三份手写的 hb-blk-hd.hb-sub-toggle 块
    # (role/tabindex/Enter/aria 各抄一遍), 故判据从「段头类名 + @click」换成「组件调用点」。
    # !开标签的正则要绕开 `=>`(on-toggle 是箭头函数, 裸 `[^>]*>` 会断在箭头上: 把 `=>`
    #   当成一个整体字符类吃掉); 先剥注释, 否则注释里举例的 `<aq-fold>` 也被当成调用点。
    body = re.sub(r"<!--[\s\S]*?-->", "", tpl)
    folds = re.findall(r"<aq-fold\s((?:=>|[^>])*)>", body)
    keys = [re.search(r"hubSubOpen\('(\w+)'\)", a).group(1) for a in folds if "hubSubOpen(" in a]
    assert keys == ["source", "curve", "chart"], f"三区折叠头缺或键不对: {keys}"
    heads = [re.search(r'title="([^"]+)"', a).group(1) for a in folds if "hubSubOpen(" in a]
    assert heads == ["数据来源", "限速曲线", "流量图采样"], f"三区标题缺失或顺序漂了: {heads}"

    # 2026-10-19 去嵌套: 三区是**页面级**块(.hb-blk.hb-cut), 不再套在同名外壳卡里 ——
    # 否则二级页上会叠出「面包屑 / h1 / 卡头」三层同名标题, 三个区看起来像嵌在页面里的子页面
    zones = re.findall(r'<div class="hb-blk (hb-cut|hb-sub)">(?:(?!<div class="hb-blk)[\s\S])*?<aq-fold\s', body)
    assert zones == ["hb-cut"] * 3, f"三区仍是嵌套块(hb-sub)或区序漂了: {zones}"
    assert 'class="bh-t">流量与限速' not in tpl, \
        "模板里又有与页头同名的块标题(二级页会出现两条「流量与限速」)"

    # 折叠态只在内存(hub.sub), 不得进 localStorage 的写入点
    assert re.search(r"sub:\s*\{\}", hub), "hub.sub 折叠态未声明(模板读到 undefined 会当展开, 但语义不明)"
    for m in re.finditer(r"localStorage\.setItem\(([^,]+),", hub):
        assert "hub.sub" not in m.group(1), "折叠态被持久化了(D14: 折叠不持久化)"

    # 来源关闭时三区都要有明确说明: 卡头提示条 + 各区的空态/灰显说明
    assert 'v-if="$root.tmSourceOff()"' in tpl, "缺来源关闭的常驻提示条"
    assert "tmSourceOff" in tpl.split('title="限速曲线"')[1], \
        "来源关闭时「限速曲线」区没有任何说明(只剩一个「启用限速曲线」按钮会让人以为是本功能没开)"
    assert "$root.tmSummary()" in tpl, "缺现状摘要(关闭态在摘要条上就该读得出来)"


def test_frontend_card_history_entry():
    """B4/D2: 「打开历史图表」-> openHistory(); 历史图仍留在全局弹层

    不搬进设置页是拍板项(D2): 那张图要天/月/年切换 + 悬停取值, 搬进来就是第二套图表实现。
    2026-10-19: 外壳卡去掉后入口落在页头下方的摘要条 .hb-tl-bar(不是某个区尾的普通按钮) ——
    它管的是整页的历史流量, 挂进任何一区都会暗示"只跟这一区有关"。
    """
    tpl = _card()
    dialogs = _shared("dialogs.js")
    assert "async openHistory()" in dialogs, "openHistory 不在 dialogs.js 里(入口指向了不存在的方法)"
    btn = re.search(r"<button[^>]*@click=\"\$root\.openHistory\(\)\"[^>]*>([^<]+)</button>", tpl)
    assert btn and "打开历史图表" in btn.group(1), "缺「打开历史图表」入口"
    bar = re.search(r'<div class="hb-tl-bar">(.*?)</div>', tpl, re.S)
    assert bar and "openHistory" in bar.group(1), "历史图入口不在摘要条里(应在现状摘要同一行右侧)"


def test_frontend_dep_hint_shares_affect_labels():
    """D6: 提示条与「关闭工具」确认框同源 —— 都从 tmAffectLabels() 取, 不写第二份文案

    两份文案的退化过程很固定: 先各写一句, 然后 schema 新增一个 affects id 只补了其中一份,
    于是"确认框说了三个后果、提示条只说两个"。
    """
    tpl = _card()
    hub = _shared("config_hub.js")
    assert "$root.tmAffectLabels()" in tpl, "提示条没走 tmAffectLabels(文案分叉)"
    # 只认"活代码": 注释里提到映射表名是说明, 不是第二份文案
    code = re.sub(r"<!--.*?-->", "", tpl, flags=re.S)
    assert "TM_AFFECT_LABELS" not in code, "模板里直接引用了 TM_AFFECT_LABELS(应经 tmAffectLabels 单点)"
    # 文案映射表只有一份, 且被 tmAffectLabels 与 tmShutdownTool 共用
    assert hub.count("const TM_AFFECT_LABELS = {") == 1
    body = hub[hub.index("tmAffectLabels() {"):]
    body = body[:body.index("async tmShutdownTool()")]
    assert "TM_AFFECT_LABELS[id]" in body, "tmAffectLabels 没读 schema affects 清单"


# ---- B1: 旧视图映射 ----


def test_frontend_hub_view_alias_maps_old_keys():
    """D13: 旧 hub.view 三个值 -> traffic_limit; 映射在取值处单点, 不清 localStorage

    漏映射的后果: 升级后用户刷新落在设置首页(旧 key 过不了 hubRestore 的 schema 校验),
    并且 localStorage 里那个值永远不会被修正 —— 每次刷新都掉一次。
    """
    hub = _shared("config_hub.js")
    alias = hub[hub.index("const HUB_VIEW_ALIAS = {"):]
    alias = alias[:alias.index("};")]
    for old in ("traffic_source", "speed", "traffic"):
        assert re.search(rf"^\s*{old}:\s*\"traffic_limit\"", alias, re.M), f"旧视图 {old} 未映射"
    # 取值处消费(initialHubView 是 data() 初值单点, hubRestore 拿到的已是新 key)
    init = hub[hub.index("function initialHubView()"):]
    init = init[:init.index("\n}")]
    assert "HUB_VIEW_ALIAS[v]" in init, "initialHubView 没消费映射表(旧值会一路进 hubRestore 被清回首页)"
    assert "localStorage.removeItem" not in hub, "映射不得清 localStorage(D13: 用户其它偏好不陪葬)"


# ---- B2: 通用层两修 ----


def test_frontend_show_if_applies_to_sections():
    """B2/D16: `show_if` 对 object 段(group)与可选段(section)同样生效

    修前 `visible()` 对非叶子恒 true —— schema 在 object 段上挂的 provider 条件形同虚设, 只能靠
    模板手写过滤。这里钉两件事: ①短路分支已删; ②来源两个子段的显隐由 show_if 而不是手工挑 key。
    """
    js = _shared("config_editor.js")
    hub = _shared("config_hub.js")
    body = js[js.index("    visible() {"):]
    body = body[:body.index("    /* 所属功能未启用")]
    assert 'if (this.item.type !== "field") return true;' not in body, \
        "visible() 又对非叶子短路了 —— 段上的 show_if 会重新变成死元数据(变异点)"
    assert "cfgVisible(this.f, this.item.owner)" in body, "非叶子项没走 cfgVisible"

    # 唯一消费点: tmProviderItems 按 cfgVisible 过滤, 不再按 tmProvider() 手工挑子段
    items = hub[hub.index("tmProviderItems() {"):]
    items = items[:items.index("/* 合并卡三区折叠")]
    assert "cfgVisible(sub, base)" in items, "来源参数行没走 show_if 判据"
    assert "tmProvider() ===" not in items.split("return out;")[0], \
        "来源参数行仍在手工挑 provider(两套真相: 手工那份漏改就会出现「选 A 也显示 B 的参数」)"


def test_frontend_hub_skip_paths_is_single_point():
    """B2/D16: 「不走通用渲染」的排除表是单点常量, walk 里只查表

    散落 if 的形态: 每加一个专段就在 walk 里补一行, 删专段时忘了删那一行 —— 于是这一块
    既被通用渲染又被专段渲染(重复)或两边都不渲染(空白), 都无报错。
    """
    hub = _shared("config_hub.js")
    const = hub[hub.index("const HUB_SKIP_PATHS = ["):]
    const = const[:const.index("];")]
    for path in ("config.hr_check.sites", "config.traffic_source", "config.global_speed_limit_curve"):
        assert path in const, f"排除表少了 {path} (该专段会被通用渲染再画一遍)"
    assert "HUB_SKIP_PATHS.indexOf(this.hubKey(it.path))" in hub, "walk 没查排除表"
    # 源码里不得再有"逐条 if 比较某个具体路径"的形态(单点之外即散落)
    assert not re.search(r'hubKey\(it\.path\)\s*===\s*"config\.', hub), \
        "walk 里仍有硬编码路径比较(排除表已不是单点)"


# ---- B3: 分片体量回落 ----


def test_frontend_settings_fragment_shrinks():
    """B3/D15: settings.html 只剩挂载行, 体量回落到 400 以内(债还掉)

    该分片此前 418 行贴着一份 440 的例外额度 —— 例外额度的存在本身会让"再加一点"变成默认选项。
    抽组件后分支缩成三行, 若还有 tm* 调用残留, 就是"抽了一半"(同一份 UI 两处渲染)。
    """
    tpl = _shared("tpl", "settings.html")
    assert "<aq-traffic-card></aq-traffic-card>" in tpl, "settings.html 未挂载合并卡"
    assert 'hub.view === \'traffic_limit\'' in tpl, "二级页分支未改到新视图 key"
    for call in ("tmSourceRows", "tmProvider()", "tmParams", "cfgCurveItems", "cfgCurveList"):
        assert call not in tpl, f"settings.html 仍残留 {call}(该卡已整体搬进 traffic-card.html)"
    n = tpl.count("\n") + (0 if tpl.endswith("\n") else 1)
    assert n < 400, f"settings.html 仍 {n} 行(抽组件后应回落到 400 以内)"
