"""test_webui_static_dom_page_layout 测试计划: webui 前端静态守阵: 页面 / 列模型 / 视图

## 测试计划(每个测试函数一条)
- test_frontend_member_window_functions_live_in_methods: 成员行窗口三个带参函数(memberWin/memberPadTop/memberPadBottom)必须落在 methods 块, 不能进 computed —— Vue 3 computed 是无参 getter, 带参会导致整表白屏(issue 26-09-21-0247)
- test_frontend_computed_not_invoked_as_function: computed 成员不得以 `this.X()` 调用(拿到的是 getter 的值, 再 () 会 TypeError) —— 经典设置页改"数值+单位"字段的数字会整页白屏
- test_frontend_template_no_reserved_prefix_identifiers: 模板表达式(插值+指令)禁止 `_`/`$` 前缀裸标识符 —— Vue 内部保留域解析不到, 抛 ReferenceError 且整块渲染失败(issue 26-10-03-1412 复制钮 `_copyText`); `$event`/`$root`/`$emit` 白名单, 成员访问不拦; 扫描抽单点 `_reserved_prefix_problems` + 恒久活性探针(issue 26-10-11-2030: 指令分支曾取错捕获组整支变死, 死时全绿无征兆)
- test_frontend_dist_segments_aggregates_per_view: distSegments 必须按 viewMode 取数(torrents / shows / groups), 不能只数 this.groups —— 种子页次导航 chips 会全空(issue 26-09-21-0247)
- test_frontend_persist_page_takes_intent_only: persistPage 只收意图态(colHidden/colOrder/colW), 生效宽度 colWidths 不得进持久化路径(双轨模型铁律, plan 26-09-21-1551)
- test_frontend_col_manual_flag_not_revived: 反向守阵 —— manual 标志位(colManual)不得复活(v5 下 w 非空即固化页)
- test_frontend_page_location_persisted: 顶层 page 与设置分区必须持久化(读侧白名单 / 写侧单漏斗) + 启动补一次 cfgLoad + 分区 key 对 schema 校验 —— 否则"设置页刷新掉回种子页"复发(2026-09-25 用户报)
- test_frontend_unsaved_changes_guard_wiring: 设置页未保存改动防护接线守阵(issue 26-09-25-1702 / 报告 26-10-02-0508 U1-b) —— 键盘刷新(F5/Ctrl+R)走自绘三选一框(保存并刷新/放弃并刷新/留在此页)+ 其余导航走原生 beforeunload 兜底 + 兜底随脏态挂摘成对 + 主动刷新前摘兜底防双框连击 + 不做草稿恢复(不碰 Web Storage)
- test_frontend_expand_state_survives_view_switch: 展开态跨视图记忆守阵 —— 切视图不得置空 expandedKey/expandedShows/expandedShowEp(辅种页→种子页→辅种页 展开的组会收起, 2026-09-25 用户报); 还回前必须验那一行还在, 且 groupWin 的退避判据要同步(否则为不存在的面板永久退化成全量渲染)
- test_frontend_hub_field_covers_non_leaf_items: 设置页 hub-field 模板必须显式覆盖 cfgFlatten 产出的**全部**非叶子项类型(section/group/subcard) —— 缺一支, 段项就落进叶子字段的兜底 `<input>`, 值被 String(对象) 成 "[object Object]"(2026-09-25 用户报)
- test_frontend_hub_field_renders_readonly_fields: schema Field.readonly(程序托管字段, issue 26-09-28-2135)接线守阵 —— CE_FIELD_BASE 有 readonly/readonlyComplex/readonlySummary 三成员, 控件链首支是只读摘要分支、全部可编辑控件挂 :disabled、行带「程序维护」徽标、settings-detail 块级 section 开关对 readonly 段换徽标(缺一处 = 该类字段仍可编辑, 保存却被后端覆盖/回退, 反馈误导)
- test_frontend_statusbar_speed_reads_server_totals: 静态防回潮 —— 前端 totalDl/totalUl 必须读 status.totals, 不得改回对 this.groups 求和
- test_frontend_flatten_skips_hidden_fields: 静态守阵 —— cfgFlatten 必须 `if (f.hidden) continue`(两套 UI 同源于此函数; 不跳过 = 隐藏字段照旧渲染, 报障复发)
- test_frontend_keyed_list_toggle_deletes_key_when_emptied: 静态防回潮 —— keyed_list 的 toggleKey 取消最后一项必须 cfgDelPath 删键(写空列表 = 脏标记消不掉 + 保存被"必须是非空列表"拒, 2026-10-10 报障), cfgSetPath 必须挂长度守卫
- test_frontend_bulk_bar_retired: 批量控制条退役守阵 —— 三套 UI 模板零残留(.bulk-inline/bulkAct(/bulkDeleteLabel(/bulkHrWarnText() 与三套 CSS 死样式零残留(.bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/.bulk-enter-*/.ico-select/@keyframes bulk-in), 批量链路 bulkAct/bulkDelete 仍在且 ctxAct/ctxDelete 复用
- test_frontend_selection_size_summary_wiring: 选中摘要(个数+合计+实际占用)接线守阵(计划 26-10-18-2013) —— 三套 UI 聚合模板 .sel-summary 指示器(v-if=selectedCount / fmtSize(selectedSize.total) / Y 段条件 occupy<total / 无 .bulk-* 复活) + selection.js 算法单点 selSizeSummaryOf 与 selectedSize computed(早退 + memberByHash + selHashSet) + delete_flow.js 实际占用条件行复用单点(不另写 size 求和) + popovers.html 详情行 title 吃 d.hint
- test_api_group_commands_enqueue: pause/resume/reannounce/delete 命令入队(key 编解码回原值)
- test_api_group_malformed_key_returns_400: 畸形分组 key(base64 非法/非 JSON/结构不符)回 400 而非 500
- test_api_delete_with_files_flag: delete 命令透传 delete_files 标志
- test_api_cmd_result_endpoint: 命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)
- test_api_traffic_history_endpoint: /api/traffic/history 透出快照 history; 缺省空数组
- test_frontend_password_field_ignores_autofill: 密码框的浏览器/密码管理器自动填充不得写进配置树(2026-10-20 报障「进常规就显示有改动还没保存」)—— 模板密码分支须 autocomplete=new-password 且写回走 setSecret, setSecret 须按「是否焦点」判据(未聚焦不写树并回填显示)
- test_frontend_config_default_ladder_single_point: schema→默认值梯单点守阵(issue 26-10-20-2231 / R20-C-05) —— 三入口(可选段 cfgDefaultForField / 插件 spec / 插件 section)不得再各写一份「按 schema 形状造初值」的循环(插件侧零手搓循环、enum 首选项默认值全仓一处、旧 cfgPluginDefaultSpec/Section 零残留); 三个单点(cfgDefaultScalar/cfgDefaultForFields/cfgDefaultForPlugin)各定义一处且入口只转调; 有 node 时真跑语义电池钉行为(插件 bool="true" vs 字段 bool="false" / list=[] / enum=options[0] / str=placeholder / object 只填必填且子段按全字段口径 / 未知形态沿用子表单 / 可选段非 object=[])
- test_frontend_retired_rule_keys_upgrade_surface: 两键退役升级提示面守阵(plan 26-11-01-0106 W1/D1) —— 旧伪动作判断 isIgnoreNext 及「忽略下一个动作的错误」友好话术零残留; 退役键检测/提示单点(cfgRuleRetiredKeys/cfgIsRetiredAction/cfgRuleRetiredHint)在 config_rules.js 各定义一处; settings.html 规则卡「未启用·含退役键」徽标(hb-badge warn)与卡脚提示接线齐全(webui 侧自测键名, 不依赖后端回写 config.yml); hubPluginText 退役标记判定必须在 meta 判空之前(退役键不在插件索引); 有 node 时真跑语义电池(四规则形态 × 检测/提示/动作行人话)
- test_frontend_list_row_pad_and_empty_single_point
- test_frontend_action_on_error_control: 动作级 on_error 控件守阵(plan 26-11-01-0106 W2/D8) ——
  cfgOnError* 方法族单点(config_rules.js); settings.html 动作卡失败策略行(policy 三档下拉 +
  retry 档 retries/backoff 数字输入)接线齐全; 有 node 时真跑语义电池(缺省值同源读侧/混合形与
  规范形识别/非缺省才写树/全缺省整键摘除)
- test_frontend_rule_tree_and_choose_editor: 规则结构树 + choose 编辑器守阵(plan 26-11-01-0106
  W3-A/W3-B, D2/D8) —— 草稿规范化单点(cfgNormalizeRulesDraft 恰在 cfgSetTree 挂一次: conditions
  扁平包 all 树 + actions 规范形 + choose 键面保留, 打开即归一形/保存写新形态); 条件树方法族
  (cfgCond*)与 choose 方法族(cfgChoose*/cfgAction*At/cfgOnError*At)在 config_rules.js 各定义一处;
  settings.html 挂 <aq-cond-node> 与 <aq-choose-block>(旧扁平条件写入路径 hubPickPlugin
  conditions 零残留), tpl/rule-tree.html 双模板 + 三清单接线 + app.js 注册 + 共用层 CSS 成对;
  有 node 时真跑语义电池(归一幂等/树形读侧/建树切换删除收敛/choose 分支增删与 on_error 路径版)
- test_frontend_window_source_kind_descriptor_parameterized: 行窗口化窗口源按 kind 参数化守阵
  (计划 26-11-02-0351 W2 参数化 + W3 抽屉接线) —— columns.js 的 WIN-SOURCES 哨兵段是窗口化几何对
  window.scrollY/innerHeight 的唯一直读点(主表三 kind = 文档型 WIN_SRC_DOC 原行为搬入, 行键
  group=item.key / 其余=item.hash), 窗口化方法节(_winContainer.._onWinResize)零直读;
  _winSrc(kind) 未注册回落文档型(保守默认), _rowKeyOf/_ensureWinTop/_onWinScroll/_onWinResize
  全走描述符; W3: WIN_SOURCES 注册 drawerContent(容器型 winSrcContainer + 行键 item.k),
  抽屉两表(V10/V11)挂 window:"drawerContent" 而 segs 分段桥(08/05)显式不接窗(恒 null),
  桥消费面(drawer_templates.js drawerWinView/dtWinRows/dtWinPad/dtBridgeLines/dtWinKbd)与
  xtpl.html 桥模板接线(aq-row-pad 占位 ×2 / dtBridgeLines 行源 / @keydown 跨窗回焦)在位;
  有 node 时真跑语义电池: 容器型 winSrcContainer 下桩 scrollTop/clientHeight
  的切片起点/终点/上下占位与文档型同输入同输出(三滚动位), 源族分流(容器族只读 _winCtn /
  文档族只读 _winScrollY 对, 未注册 kind 回落文档型), 描述符几何(scrollY/viewH/topOffset)
  与绑定契约(bindScroll passive/unbind)逐项钉值, 零差异回退(低于 ROW_WIN_MIN/未量齐/rowWin 关)
  不回潮; 首访路径边界二条(issue 26-11-02-0902 二轮空档2): _winMeasured=false 时 n=199 走
  off(全量渲染) / n=200 走估算开窗(active) —— 门控被误改成恒窗口/恒 off 时必有一条红
- test_frontend_row_window_sig_and_ctn_sync_guard: 行窗失效签名守阵(2026-11-02 关抽屉/切页卡死
  取证) —— ① _measureRowH 行高签名不含 viewMode(含则每次切页作废三 kind 行高 + 翻 _winMeasured,
  返回该视图全量渲染量齐, 3000 行实测 5.8~8.4s 长任务 = 「切标签页卡死几秒」; _winResize/列集合
  两真变化因子必须在); ② _winCtnSync 的 drawer.open 守卫先于 clientWidth 读取(收场动画 .drawer
  转 absolute, .drawer-body clientWidth 1894->1918 是过渡假象, 采信即假 bump 共享 _winResize →
  下一拍全量重渲 5.6s 长任务 = 「关抽屉后卡死; 能滚不能点」)

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

from webui_dom_page_support import (
    _NODE_CFG_DEFAULT_PROBE,
    _NODE_LIST_EMPTY_PROBE,
    _NODE_ON_ERROR_PROBE,
    _NODE_RETIRED_KEYS_PROBE,
    _NODE_RULE_TREE_PROBE,
    _NODE_WIN_SRC_PROBE,
    _RESERVED_PREFIX_SPAN_PATS,
    _RESERVED_PREFIX_WHITELIST,
    _bundle_iter,
    _computed_member_names,
    _reserved_prefix_problems,
)


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
    白名单放行 **Vue 内建**(组件实例上真实存在、模板可解析, 与"用户成员被排除在组件代理之外"
    是两回事): `$event` 事件形参; `$root` = 根实例代理 —— 表壳/明细单元格渲染器组件(计划
    26-10-11-1722 P1/P2)是「单根组件 + 全局 mixin」架构下的**纯模板**片段, 行为经 `$root`
    回调根实例(根数据只在根实例上), 组件自身不复制方法实现; `$emit` = 组件向调用方发事件
    (P5 表壳 thead 模式: 排序状态归调用方, 组件只 `$emit("sort", key)`);
    `$slots` = 本实例插槽分布(aq-modal 动作栏条件渲染 issue 26-10-20-2231: hist 无底部条,
    空 .modal-actions 会多出 16px margin —— Vue 内建对象, 组件实例真实存在)。
    `obj._x` 成员访问(点号后)不属于裸标识符, 不拦。

    issue 26-10-11-2030: 指令分支曾取错捕获组(组 1 是引号, 表达式在组 2), 整支变死且全绿无征兆
    —— 扫描抽成单点 `_reserved_prefix_problems` 并加恒久活性探针: 已知违规必须命中、
    白名单内建必须放行, 分支再死 = 本守阵红, 不再依赖一次性红验碰运气。
    """
    sources = []  # (rel, text): 盘上全部分片 + 各 UI shell 的 #app 内联段(与运行时编译输入同源)
    tpl_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    for name in sorted(os.listdir(tpl_dir)):
        if name.endswith(".html"):
            rel = "shared/tpl/" + name
            sources.append((rel, open(os.path.join(tpl_dir, name), encoding="utf-8").read()))
    for ui in _UI_ALL:
        sources.append((f"{ui}/index.html(#app 内联)", _ui_shell_inline(ui)))
    problems = [p for rel, text in sources for p in _reserved_prefix_problems(rel, text)]

    # 恒久活性探针(issue 26-10-11-2030): 两条形态各喂一条已知违规必须命中; 白名单内建必须放行。
    probe_hits = _reserved_prefix_problems("活性探针", '<div @click="_probeTap()" :prop="$root.ok">{{ _probeVar }}</div>')
    probe_toks = sorted(re.search(r"`([^`]+)`", p).group(1) for p in probe_hits)
    assert probe_toks == ["_probeTap", "_probeVar"], (
        f"守阵活性探针未命中已知违规(指令形态 _probeTap + 插值形态 _probeVar, 实测 {probe_toks}) —— "
        "扫描分支有死支或捕获组取错(issue 26-10-11-2030), 同步本守阵"
    )
    whitelist_probe = _reserved_prefix_problems(
        "白名单探针",
        '<div v-if="$slots.actions" @click="$emit(\'sort\', k)" :prop="$root.x" @input="$event">{{ $root.y }}</div>',
    )
    assert not whitelist_probe, (f"白名单探针误拦 Vue 内建($event/$root/$emit/$slots): {whitelist_probe} —— 白名单口径漂移, 同步本守阵")

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


def test_frontend_password_field_ignores_autofill():
    """密码框的自动填充不得写进配置树(2026-10-20 报障「点进常规就显示有改动还没保存」, 静态防回潮)

    现象: 进设置页「常规」分区, 没碰任何控件, actbar 已显示「有改动还没保存」; 放弃改动再来一遍
    照样复现。根因: 密码框被包成「用户名 + 密码」的表单形状(为消 Chrome 的两条可访问性警告),
    浏览器 / 密码管理器把它当登录表单, 把同源(登录页, autocomplete=current-password)保存的凭据
    **自动填**进来, 并在**未聚焦**时派发 input 事件 —— 原 @input="set()" 把自动填充的值原样写进
    配置树, 脏标记凭空变真, 而框里显示的是掩码, 用户看不出改的是哪一项(实测: 未聚焦派发一次
    input, cfgDirty 立即为真; 加守卫后仍为假, 而聚焦后键入照旧写树)。

    钉三件, 缺一件都复发:
      ① 模板密码分支必须 autocomplete="new-password" —— 从源头劝退凭据自动填充;
      ② 模板必须走 setSecret($event), 不得直连 set() —— 直连就是把自动填充当用户编辑;
      ③ setSecret 必须按「是否焦点」判据: 未聚焦不写树并回填显示值, 聚焦才写。
    """
    for skin in _UI_ALL:
        html = _ui_aggregate(skin)
        m = re.search(r'<form v-if="f\.kind === \'password\'".*?</form>', html, re.S)
        assert m, f"{skin} 找不到密码字段分支(改名/挪走了? 同步本守阵)"
        branch = m.group(0)
        assert 'autocomplete="new-password"' in branch, (
            f"{skin} 的密码框缺 autocomplete=\"new-password\" —— 浏览器会把同源登录页保存的凭据自动填进来, "
            "未聚焦的 input 事件会把密码写进配置树(脏标记凭空变真)"
        )
        assert 'setSecret($event)' in branch, (f"{skin} 的密码框写回未走 setSecret —— 自动填充会被当成用户编辑写进配置树")
        assert "set($event.target.value)" not in branch, (f"{skin} 的密码框直连 set() —— 自动填充造脏的根因(2026-10-20 报障)原样复发")

    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    m2 = re.search(r"\n    setSecret\(ev\) \{(.*?)\n    \},", editor, re.S)
    assert m2, "config_editor.js 的 CE_FIELD_BASE 找不到 setSecret(ev)(改名或挪走了? 同步本守阵)"
    body = m2.group(1)
    assert "document.activeElement" in body, ("setSecret 缺焦点判据 —— 未聚焦的自动填充(页面加载/密码管理器)会照旧写树, 脏标记凭空变真")
    assert "el.value" in body and "return;" in body, ("setSecret 未聚焦时必须把显示拉回树值再返回(否则界面显示自动填充值、树里还是掩码, 两套值)")
    assert "cfgSetPath" in body, "setSecret 缺写树分支 —— 用户真实键入会失效"


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


def test_frontend_selection_size_summary_wiring():
    """选中摘要(个数 + 合计 + 实际占用)接线守阵(2026-10-18, 计划 26-10-18-2013)

    用户拍板 D1-D13: 筛选行纯文本指示器「已选 N 个种子 · 合计 X · 实际占用 Y」(Y 仅在
    X≠Y 时出现, 纯展示零按钮), 删除确认框同口径条件行。逐层钉住:
      1. 三套 UI 聚合模板: .sel-summary 指示器在场(v-if=selectedCount), 消费 selectedSize
         的 total/occupy 与 fmtSize; Y 段条件 = occupy < total; 不复活 .bulk-* 符号;
      2. selection.js: selSizeSummaryOf 算法单点 + selectedSize computed(无选中早退,
         经 memberByHash 解析 selHashSet);
      3. delete_flow.js: _deleteDetails 的「实际占用」条件行复用 selSizeSummaryOf(不另写
         求和) + popovers.html 详情行 title 吃 d.hint(口径说明)。
    """
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        m = re.search(r'<span v-if="selectedCount" class="strip-note sel-summary">(.*?)</span>', text, re.S)
        assert m, f"{ui} 聚合模板缺选中摘要指示器(.sel-summary) —— 位置/类名被改? 同步本守阵"
        block = m.group(1)
        assert "{{ selectedCount }}" in block and "个种子" in block, "指示器必须显示已选个数"
        assert "fmtSize(selectedSize.total)" in block, "合计 X 必须走 fmtSize(selectedSize.total)"
        assert "selectedSize.occupy < selectedSize.total" in block, "实际占用 Y 仅在 X≠Y 时出现"
        assert "fmtSize(selectedSize.occupy)" in block, "实际占用 Y 必须走 fmtSize(selectedSize.occupy)"
        for token in (".bulk-inline", "bulkAct(", "bulkDeleteLabel(", "bulkHrWarnText("):
            assert token not in block, f"{ui} 选中摘要复用了退役批量控制条符号 {token!r}"

    sel = open(os.path.join(STATIC_ROOT, "shared", "selection.js"), encoding="utf-8").read()
    assert "selSizeSummaryOf(members) {" in sel, "选中摘要算法单点 selSizeSummaryOf 消失(两处各自演化即漂移)"
    m = re.search(r"selectedSize\(\) \{(.*?)\n    \},", sel, re.S)
    assert m, "selection.js 缺 selectedSize computed"
    body = m.group(1)
    assert "selSizeSummaryOf" in body and "memberByHash" in body and "selHashSet" in body, (
        f"selectedSize 必须经 memberByHash 解析 selHashSet 交算法单点: {body.strip()}"
    )
    assert "this.selectedCount" in body, "selectedSize 必须早退(无选中不建成员索引)"

    dfl = open(os.path.join(STATIC_ROOT, "shared", "delete_flow.js"), encoding="utf-8").read()
    m = re.search(r"_deleteDetails\(keys, hashes\) \{(.*?)\n    \},", dfl, re.S)
    assert m, "delete_flow.js 缺 _deleteDetails"
    det = m.group(1)
    assert "this.selSizeSummaryOf(members)" in det, "删除框实际占用行必须复用 selSizeSummaryOf 单点"
    assert "实际占用" in det, "删除框缺「实际占用」条件行(D12)"
    assert "m.size || 0" not in det, "删除框又自己写了一遍 size 求和 —— 应走 selSizeSummaryOf(口径单点)"

    pop = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    assert 'd.hint || String(d.value)' in pop, "详情行 title 必须吃 d.hint(实际占用行的口径说明入口)"


def test_frontend_config_default_ladder_single_point():
    """schema→默认值梯单点守阵(issue 26-10-20-2231, 台账 R20-C-05)

    「按 schema 形状造初值」这条阶梯曾有三份实现(可选段 cfgDefaultForField / 插件 spec /
    插件 section), 插件两份还互相嵌套 —— 加一种 kind 的默认值规则要三处同改, 漏一处新条目
    就过不了后端校验或写出非法空值(默认值直接影响保存合法性)。已收敛成一条下降链
    (cfgDefaultScalar → cfgDefaultForFields, 插件侧只做 spec_kind 分派), 本守阵钉两件事:

    1. **形态**(静态): 三份手搓循环不得回潮 —— 插件侧 config_rules.js 零手搓字段循环、
       enum 首选项(options[0])默认值全仓一处、旧 cfgPluginDefaultSpec/Section 零残留;
       三个单点各定义一处; 两个入口(cfgDefaultForField / cfgDefaultForPlugin)体内不得再有循环,
       只转调单点。**恒久活性探针**: 两个入口的调用点(cfgToggleSection / cfgPluginAdd)必须还在
       —— 否则"入口被删光"会让上面所有断言恒真。
    2. **行为**(有 node 时真跑): 合成 schema 语义电池 11 项, 把三处合并前**各自保留的分歧**
       逐条钉死 —— 插件 bool = "true" 而字段 bool = "false" / list = [] / enum = options[0] /
       str = placeholder / object 只填必填且 object 子段按全字段口径 / 未知形态沿用子表单 /
       可选段非 object = []。日后谁"顺手统一"了某条口径, 这里立刻红。

    无 node 的机器只跑静态那一半(静默跳过电池, 不引入 pytest skip, 基线 0 skipped)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    ed = open(os.path.join(shared, "config_editor.js"), encoding="utf-8").read()
    ru = open(os.path.join(shared, "config_rules.js"), encoding="utf-8").read()

    # 1. 三个单点各定义一处(两文件合计): 拆回多份 = 加 kind 又要多处同改
    for fn in ("cfgDefaultScalar", "cfgDefaultForFields", "cfgDefaultForPlugin"):
        defs = re.findall(rf"^    {fn}\(", ed + "\n" + ru, re.M)
        assert len(defs) == 1, (
            f"{fn} 定义 {len(defs)} 处(应为 1) —— schema→默认值梯被拆回多份, "
            "加一种 kind 的默认值规则又要多处同改(issue 26-10-20-2231)"
        )
    # 2. 旧的两份手搓实现零残留(连名字一起): 留着就会有人继续往里加分支
    for dead in ("cfgPluginDefaultSpec", "cfgPluginDefaultSection"):
        assert dead not in ed and dead not in ru, (f"{dead} 残留 —— 旧的插件 spec/section 手搓默认值实现回潮(改回三处同构)")
    # 3. 插件侧不再有手搓的字段循环; enum 首选项默认值单点
    assert "for (const f of" not in ru, ("config_rules.js 又出现了手搓的字段循环 —— 造初值必须走 cfgDefaultForFields/cfgDefaultScalar")
    assert len(re.findall(r"options\[0\]", ed + ru)) == 1, ("enum 首选项默认值(options[0])出现多处 —— 该口径的单点已漂移")
    # 4. 两个入口只转调单点(体内不得再有循环)
    for host, fn in (("config_editor.js", "cfgDefaultForField"), ("config_rules.js", "cfgDefaultForPlugin")):
        text = ed if host == "config_editor.js" else ru
        # 函数体切片: 从 `    <fn>(...) {` 起, 到同级 `    },` 止(花括号转义段单独写, 免得进 f-string)
        m = re.search(rf"\n    {fn}\([^)]*\) " + r"\{\n(.*?)\n    \},", text, re.S)
        assert m, f"{host} 找不到 {fn}(改名或挪走了? 同步本守阵)"
        body = m.group(1)
        assert "for (" not in body, f"{host}::{fn} 体内又有循环 —— 造初值必须走阶梯单点"
        assert "cfgDefaultForFields(" in body, f"{host}::{fn} 未转调 cfgDefaultForFields(阶梯断了)"
    assert "cfgDefaultScalar(" in ru, "config_rules.js 的插件分派未走 cfgDefaultScalar(叶子阶梯)"
    # 5. 恒久活性探针: 入口的调用点还在(删光入口会让上面 1-4 恒真)
    assert "this.cfgDefaultForField(field)" in ed, \
        "config_editor.js::cfgToggleSection 未调 cfgDefaultForField(可选段初值入口断了? 同步本守阵)"
    assert "this.cfgDefaultForPlugin(this.cfgPluginIndex[" in ru, \
        "config_rules.js::cfgPluginAdd 未调 cfgDefaultForPlugin(插件 spec 初值入口断了? 同步本守阵)"

    # 6. 有 node 时真跑语义电池(行为面, 不只是文本)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [
                node, "-e", _NODE_CFG_DEFAULT_PROBE,
                os.path.join(shared, "config_editor.js"),
                os.path.join(shared, "config_rules.js")
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"默认值梯 node 探针跑挂了: {(proc.stderr or '').strip()[:400]}"
        res = json.loads(proc.stdout.strip())
        assert res["total"] >= 11, f"语义电池只有 {res['total']} 项(被删减? 同步本守阵)"
        assert not res["failed"], ("schema→默认值梯行为漂移: " + "、".join(res["failed"]) + " —— 三处合并前各自保留的口径被改掉了(新条目可能过不了后端校验)")


def test_frontend_rule_tree_and_choose_editor():
    """规则结构树 + choose 编辑器守阵(plan 26-11-01-0106 W3-A/W3-B, D2/D8)

    本守阵钉(静态 + 有 node 时行为):
    1. 草稿规范化单点(D2): cfgNormalizeRulesDraft 在 config_editor.cfgSetTree 恰挂一次 ——
       conditions 旧扁平列表包隐式 all 树 + actions 旧扁平/混合形翻译 {type, params, on_error}
       规范形并注入缺省 on_error + choose 键面保留(W3-B), 打开即归一形、保存即写新形态;
       旧扁平条件写入路径(hubPickPlugin conditions)零残留;
    2. 条件树方法族(cfgCond*)与 choose 方法族(cfgChoose*/cfgActionEntry*/cfgOnError*At/
       cfgListEntryRemove)在 config_rules.js 各定义一处(单点不拆分);
    3. settings.html 挂 <aq-cond-node>(组合树编辑入口 + 根级添加下拉)与 <aq-choose-block>
       (choose 卡), 动作区有「添加分支」按钮; tpl/rule-tree.html 双 x-template 恰一份,
       三皮肤清单接线 + app.js 注册 + 共用层 CSS(.hb-cond-node/.hb-branch)成对;
    4. 有 node 时真跑语义电池: 归一幂等 / 树形读侧(根键/孩子/叶子计数)/ 建树-切换-删除收敛
       (空列表向上收敛删 conditions 键 = 无条件直过)/ choose 分支增删 + then 动作规范形写入 +
       on_error 路径版三档控件 + default 开关。

    无 node 的机器只跑静态那一半(与本文件其它守阵同口径, 不引入 pytest skip)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    ru = open(os.path.join(shared, "config_rules.js"), encoding="utf-8").read()
    ce = open(os.path.join(shared, "config_editor.js"), encoding="utf-8").read()
    hub = open(os.path.join(shared, "config_hub.js"), encoding="utf-8").read()
    tpl = open(os.path.join(shared, "tpl", "settings.html"), encoding="utf-8").read()
    tree_tpl = open(os.path.join(shared, "tpl", "rule-tree.html"), encoding="utf-8").read()
    app = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    css = open(os.path.join(shared, "console_hub.css"), encoding="utf-8").read()

    # 1. 草稿规范化单点: cfgSetTree 恰挂一次; 旧扁平条件写入路径零残留
    assert ce.count("cfgNormalizeRulesDraft()") == 1, "cfgSetTree 必须恰挂一次草稿规范化(D2 单点)"
    assert "hubPickPlugin(cfg.ruleGroupKey, rn, 'conditions'" not in tpl, \
        "旧扁平条件写入路径残留 —— 条件区应写组合树(D2)"
    for fn in (
        "cfgNormalizeRulesDraft",
        "cfgNormalizeActionEntryDraft",
        "cfgCondRootPath",
        "cfgCondNodeKey",
        "cfgCondSetCombo",
        "cfgCondAddAt",
        "cfgCondRootAdd",
        "cfgCondRemoveAt",
        "cfgCondMoveAt",
        "cfgCondSpecItems",
        "cfgCondCount",
        "cfgIsChooseEntry",
        "cfgChooseAdd",
        "cfgChooseBranches",
        "cfgChooseBranchAdd",
        "cfgChooseBranchRemove",
        "cfgChooseDefaultToggle",
        "cfgListEntryRemove",
        "cfgActionEntryAddAt",
        "cfgActionEntryMoveAt",
        "cfgThenList",
        "cfgThenEntryPath",
        "cfgDefaultList",
        "cfgDefaultEntryPath",
        "cfgOnErrorPathAt",
        "cfgOnErrorValueAt",
        "cfgOnErrorSetAt",
        "cfgSpecItemsAt",
    ):
        defs = re.findall(rf"^    {fn}\(", ru, re.M)
        assert len(defs) == 1, f"{fn} 定义 {len(defs)} 处(应为 1) —— 条件树/choose 方法族被拆分"
    # 2. settings.html 接线: 组合树挂载 + 根级添加 + choose 卡与「添加分支」
    assert ":path=\"cfgCondRootPath(cfg.ruleGroupKey, rn)\"" in tpl, "settings.html 条件区缺 <aq-cond-node> 挂载(D2/D8)"
    assert "cfgCondRootAdd(cfg.ruleGroupKey, rn" in tpl, "settings.html 缺根级「添加条件」下拉(无条件直过入口断了)"
    assert "<aq-choose-block" in tpl and "cfgChooseAdd(cfg.ruleGroupKey, rn)" in tpl, \
        "settings.html 缺 choose 编排块卡/「添加分支」入口(W3-B/D8)"
    # 3. 模板/注册/清单/CSS 成对
    for tpl_id in ("tpl-aq-cond-node", "tpl-aq-choose-block"):
        assert tree_tpl.count(f'id="{tpl_id}"') == 1, f"rule-tree.html 里 {tpl_id} 必须恰一份"
    assert 'app.component("aq-cond-node", window.AQ_COND_NODE_COMPONENT);' in app, "app.js 缺 aq-cond-node 注册"
    assert 'app.component("aq-choose-block", window.AQ_CHOOSE_BLOCK_COMPONENT);' in app, "app.js 缺 aq-choose-block 注册"
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        assert shell.count('{"src": "/shared/tpl/rule-tree.html", "into": "body"}') == 1, f"{ui} 清单缺 rule-tree.html 分片"
    assert ".hb-cond-node" in css and ".hb-branch" in css, "共用层 CSS 缺规则结构树版式段(三皮肤共用单点 console_hub.css)"
    assert "cfgIsChooseEntry" in hub, "hubPluginText 缺 choose 行话分支(choose 不在插件索引, 裸键名展示)"
    # 4. 有 node 时真跑语义电池
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [
                node, "-e", _NODE_RULE_TREE_PROBE,
                os.path.join(shared, "config_editor.js"),
                os.path.join(shared, "config_rules.js")
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"规则树 node 探针跑挂了: {(proc.stderr or '').strip()[:400]}"
        res = json.loads(proc.stdout.strip())
        assert res["total"] >= 16, f"语义电池只有 {res['total']} 项(被删减? 同步本守阵)"
        assert not res["failed"], ("条件树/choose 编辑器行为漂移: " + "、".join(res["failed"]))


def test_frontend_action_on_error_control():
    """动作级 on_error 控件守阵(plan 26-11-01-0106 W2/D8)

    本守阵钉(静态 + 有 node 时行为):
    1. cfgOnError* 方法族在 config_rules.js 各定义一处(单点不拆分);
    2. settings.html 动作卡失败策略行接线齐全(policy 三档下拉 + retry 档 retries/backoff
       数字输入), 伪动作项不渲染该行;
    3. 读侧缺省值与后端 schema constants(on_error_policies/on_error_defaults)同源;
    4. 写侧: 非缺省组合才写树(混合形 {动作键: 值, on_error: {...}}, 载入链 normalize
       单点翻译规范形), 全缺省整键摘除;
    5. 混合形/规范形动作项的名称/路径识别(cfgPluginName/cfgSpecPath/cfgIsRetiredAction)不因
       on_error 键面扩展而漂移。

    无 node 的机器只跑静态那一半(与默认值梯/两键守阵同口径。)
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    ru = open(os.path.join(shared, "config_rules.js"), encoding="utf-8").read()
    tpl = open(os.path.join(shared, "tpl", "settings.html"), encoding="utf-8").read()

    # 1. 方法族单点(各定义一处)
    for fn in (
        "cfgOnErrorDefaults", "cfgOnErrorPolicies", "cfgOnErrorPath", "cfgOnErrorValue", "cfgOnErrorIsRetry",
        "cfgOnErrorSet"
    ):
        defs = re.findall(rf"^    {fn}\(", ru, re.M)
        assert len(defs) == 1, f"{fn} 定义 {len(defs)} 处(应为 1) —— on_error 控件口径被拆分"
    # 2. 模板接线: 失败策略行在动作卡内, 三档下拉 + retry 数字输入, 伪动作不渲染
    assert "cfgOnErrorValue(cfg.ruleGroupKey, rn, i, 'policy')" in tpl, "settings.html 动作卡缺失败策略下拉(W2/D8)"
    assert "cfgOnErrorIsRetry(cfg.ruleGroupKey, rn, i)" in tpl, "settings.html 缺 retry 档条件渲染"
    assert tpl.count("cfgOnErrorSet(cfg.ruleGroupKey, rn, i") >= 3, "policy/retries/backoff 三个输入须都接 cfgOnErrorSet"
    oe_row = re.search(r'<div [^>]*class="hb-oe-row"[^>]*>', tpl)
    assert oe_row and "cfgIsRetiredAction(entry)" in oe_row.group(0), "伪动作项不应渲染 on_error 行"
    # 3. 有 node 时真跑语义电池
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [
                node,
                "-e",
                _NODE_ON_ERROR_PROBE,
                os.path.join(shared, "config_editor.js"),
                os.path.join(shared, "config_rules.js"),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"on_error node 探针跑挂了: {(proc.stderr or '').strip()[:400]}"
        res = json.loads(proc.stdout.strip())
        assert res["total"] >= 13, f"语义电池只有 {res['total']} 项(被删减? 同步本守阵)"
        assert not res["failed"], ("on_error 控件行为漂移: " + "、".join(res["failed"]))


def test_frontend_retired_rule_keys_upgrade_surface():
    """两键退役升级提示面守阵(plan 26-11-01-0106 W1, D1/D8)

    stop_following_rules_if / ignore_next_action_error 已随 W1 退场: 载入层(rules_mod)把
    含键规则转未启用 + warning, 但**不回写 config.yml** —— webui 是主配置面, 升级提示必须
    在界面上可见(不能只靠日志)。本守阵钉:

    1. 旧伪动作判断(isIgnoreNext)与其友好话术「忽略下一个动作的错误」零残留 —— 留着就是
       把退役键当活键展示;
    2. 检测/提示单点(cfgRuleRetiredKeys / cfgIsRetiredAction / cfgRuleRetiredHint)在
       config_rules.js 各定义一处, 模板只引用不重算;
    3. settings.html 规则卡升级提示面接线齐全: 卡头「未启用·含退役键」徽标(hb-badge warn,
       与现有 dark 主题令牌同族) + 卡脚提示(话术含等价新写法);
    4. hubPluginText 的退役标记判定必须在 meta 判空**之前** —— 退役键不在插件索引里,
       meta 恒空, 判空先行会让该分支永远走不到(静默回落裸键名);
    5. 有 node 时真跑语义电池 9 项: 四规则形态(无键/仅规则级/仅伪动作/两键并存)×
       检测/提示/动作行人话, 把「webui 自测键名」这条口径钉在行为上。

    无 node 的机器只跑静态那一半(与默认值梯守阵同口径, 不引入 pytest skip)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    ru = open(os.path.join(shared, "config_rules.js"), encoding="utf-8").read()
    hub = open(os.path.join(shared, "config_hub.js"), encoding="utf-8").read()
    tpl = open(os.path.join(shared, "tpl", "settings.html"), encoding="utf-8").read()

    # 1. 旧伪动作判断零残留(连友好话术一起)
    assert "isIgnoreNext" not in ru + hub + tpl, \
        "isIgnoreNext 残留 —— 伪动作已退役, 不得再按活键判断/展示(plan 26-11-01-0106 W1)"
    assert "忽略下一个动作的错误" not in hub + tpl, \
        "「忽略下一个动作的错误」话术残留 —— 退役键按升级提示展示, 不再当动作能力"
    # 2. 检测/提示单点各定义一处(config_rules.js)
    for fn in ("cfgRuleRetiredKeys", "cfgIsRetiredAction", "cfgRuleRetiredHint"):
        defs = re.findall(rf"^    {fn}\(", ru, re.M)
        assert len(defs) == 1, f"{fn} 定义 {len(defs)} 处(应为 1, config_rules.js) —— 口径单点漂移"
    assert "cfgRuleRetiredKeys(" in ru and "cfgIsRetiredAction(" in ru, "退役键检测单点缺失"
    # 3. 模板接线: 徽标 + 卡脚提示(缺一处 = 升级提示面不可见, 只剩日志)
    assert 'v-if="cfgRuleRetiredKeys(cfg.ruleGroupKey, rn).length"' in tpl and 'hb-badge warn' in tpl, \
        "settings.html 规则卡缺「未启用·含退役键」徽标(D1: 升级提示要在 webui 可见)"
    assert "cfgRuleRetiredHint(cfg.ruleGroupKey, rn)" in tpl, \
        "settings.html 规则卡缺卡脚升级提示(等价新写法入口断了)"
    # 4. hubPluginText 退役标记在 meta 判空之前(退役键无插件元数据, 判空先行 = 分支死)
    m = re.search(r"\n    hubPluginText\(entry\) \{\n(.*?)\n    \},", hub, re.S)
    assert m, "config_hub.js 找不到 hubPluginText(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "cfgIsRetiredAction" in body, "hubPluginText 未做退役标记判定(伪动作回潮裸键名展示)"
    assert body.index("cfgIsRetiredAction") < body.index("cfgPluginMeta(entry)"), \
        "hubPluginText 退役标记判定落到了 meta 判空之后 —— 退役键不在插件索引, 该分支永远走不到"

    # 5. 有 node 时真跑语义电池(行为面)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [
                node,
                "-e",
                _NODE_RETIRED_KEYS_PROBE,
                os.path.join(shared, "config_editor.js"),
                os.path.join(shared, "config_rules.js"),
                os.path.join(shared, "config_hub.js"),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"退役键 node 探针跑挂了: {(proc.stderr or '').strip()[:400]}"
        res = json.loads(proc.stdout.strip())
        assert res["total"] >= 9, f"语义电池只有 {res['total']} 项(被删减? 同步本守阵)"
        assert not res["failed"], ("退役键提示面行为漂移: " + "、".join(res["failed"]) + " —— 检测/提示口径被改掉了")


def test_frontend_list_row_pad_and_empty_single_point():
    """列表外壳两件套单点守阵(issue 26-10-20-2231, 台账 R23-A-05 / R23-B-06)

    两件事此前各抄多遍, 且**互相独立地漂**:

    1. **行容器三明治**(row-pad 上下占位撑高)四处手写 —— 它是 P1-2 行窗口化契约(占位撑住总高,
       滚动条长度与「滚到底」才与全量渲染一致), 一处改了 aria-hidden / px 口径另三处不同步**零报错**,
       只表现为两个视图的滚动几何悄悄分叉。现挂同一组件 `<aq-row-pad>`(上下两个实例 —— 占位必须
       夹住中间的 v-for 行, 单个实例的渲染结果只能是连续的一段); 行本身仍由调用方 v-for 内联,
       「不引入逐行组件实例」的性能纪律不动(计划 26-10-11-1722 §06 风险 4)。
    2. **空态块** `.empty` 12 处手写同一三件套, 其中 4 处(设置页 HR 表三态 + 变体表兜底)**连 svg
       都没有**。现挂同一组件 `<aq-empty>`; 组件必须保留 `<div class="empty">` + `svg.ico` + `span`
       的结构 —— 三皮肤 CSS 按 `.empty` / `.empty .ico` 选择, 包一层包裹或改类名会让整条空态样式
       静默失效。图标语义口径(inbox 空 / hourglass 加载中 / warn 出错)就此单点在分片头注里。

    本守阵钉两件事:
      · **形态**: 除单点分片 list-shell.html 外, 任何模板分片不得再手写这两个块; 两个组件各定义
        一处且 template 指向自己的 x-template; app.js 各注册一处。
      · **活性探针**: 调用点计数下限(aq-row-pad ≥ 8 · aq-empty ≥ 12)—— 否则「把调用点全删光」
        会让上面所有断言恒真进行检测力为零。计数**必须先剥掉 HTML 注释**: 各分片头注与行内注释里
        大量出现 `<aq-row-pad>` / `<aq-empty>` 字样(解释收敛缘由), 直接 count 会让下限被注释撑满,
        删掉真实调用点照样达标 —— 红验突变 C 就是这么绿过去的。
      · **行为**(有 node 时真跑): 三张列表 × 五种空态场景共 15 项, 把收敛时刻意保留的分歧钉死 ——
        辅种页搜索分支说「种子」(服务端匹配裁决落在成员不在组)而面筛分支说 l10nGroup; 追剧页全空
        是「暂无剧集可展示」; 以及**种子页补上的「正在构建文件索引…」分支**(收敛前它缺这一支,
        索引构建期把中间态说成了「无匹配种子」)。

    无 node 的机器只跑静态那一半(静默跳过电池, 不引入 pytest skip)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl_dir = os.path.join(shared, "tpl")
    single = "list-shell.html"

    # 注释剥离: 头注里就写着 `<aq-row-pad>` / `<aq-empty>`(解释收敛缘由), 不剥会让活性探针的下限
    # 被注释字样撑满 —— 删掉真实调用点仍然达标, 探针失效。
    def _live(html):
        return re.sub(r"<!--.*?-->", "", html, flags=re.S)

    problems = []
    for f in sorted(os.listdir(tpl_dir)):
        if not f.endswith(".html") or f == single:
            continue
        text = open(os.path.join(tpl_dir, f), encoding="utf-8").read()
        n_pad = text.count('class="row-pad"')
        if n_pad:
            problems.append(f"tpl/{f} 手写了 {n_pad} 处 .row-pad 占位 —— 必须挂 <aq-row-pad>(行窗口化三明治四处同源自此)")
        n_empty = len(re.findall(r'<div\b[^>]*\bclass="empty"', text))
        if n_empty:
            problems.append(f"tpl/{f} 手写了 {n_empty} 处空态块 —— 必须挂 <aq-empty>(12 处三件套只剩单点一份)")
    # 手写回潮先行报出(否则会被下面活性探针的「计数掉了」抢先, 症状说不清病因)
    assert not problems, "列表外壳两件套回潮: " + "; ".join(problems)
    # 单点分片自身: 两个 x-template 各一处
    single_text = open(os.path.join(tpl_dir, single), encoding="utf-8").read()
    for tid in ("tpl-aq-row-pad", "tpl-aq-empty"):
        hits = re.findall(r'<script type="text/x-template" id="%s">' % tid, single_text)
        assert len(hits) == 1, f"{single} 的 #{tid} x-template 出现 {len(hits)} 处(应为 1)"
    # 组件定义各一处, 且 template 指回自己的 x-template
    tbl = open(os.path.join(shared, "table.js"), encoding="utf-8").read()
    bundle = _app_bundle_text()
    for comp, tid in (("AQ_ROW_PAD_COMPONENT", "tpl-aq-row-pad"), ("AQ_EMPTY_COMPONENT", "tpl-aq-empty")):
        assert len(re.findall(rf"^window\.{comp} = \{{", bundle, re.M)) == 1, \
            f"window.{comp} 定义不是恰好一处 —— 列表外壳两件套被拆回多份"
        m = re.search(rf"window\.{comp} = \{{(.*?)\n\}};", tbl, re.S)
        assert m, f"table.js 找不到 window.{comp}(改名或挪走了? 同步本守阵)"
        assert f'template: "#{tid}"' in m.group(1), f"window.{comp} 的 template 未指向 #{tid}"
    # app.js 各注册一处
    app = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    for tag, comp in (("aq-row-pad", "AQ_ROW_PAD_COMPONENT"), ("aq-empty", "AQ_EMPTY_COMPONENT")):
        assert len(re.findall(rf'^app\.component\("{tag}"', app, re.M)) == 1, \
            f"app.js 未注册 <{tag}> 或注册多处 —— 注册面是模板无线索的唯一接线点"
    # 活性探针: 调用点还在(删光调用点 = 上面所有断言恒真)。计数排除单点分片自身 ——
    # 它头注里也有若干次 `<aq-row-pad>`/`<aq-empty>` 字样, 算进来会让下限形同虚设。
    n_pad_call = 0
    n_empty_call = 0
    for f in sorted(os.listdir(tpl_dir)):
        if not f.endswith(".html") or f == single:
            continue
        text = _live(open(os.path.join(tpl_dir, f), encoding="utf-8").read())
        n_pad_call += len(re.findall(r"<aq-row-pad\b", text))
        n_empty_call += len(re.findall(r"<aq-empty\b", text))
    # 四个同形体: groups 组行 / groups 明细成员 / torrents 种子行 / shows 集明细成员, 各上下一个
    assert n_pad_call >= 8, \
        f"列表外的 <aq-row-pad> 调用点只剩 {n_pad_call} 处(下限 8) —— 调用点被删会让本守阵恒真"
    assert n_empty_call >= 12, \
        f"列表外的 <aq-empty> 调用点只剩 {n_empty_call} 处(下限 12 = 收敛前的 12 处空态) —— 调用点被删会让本守阵恒真"
    # 空态文案单点必须在 methods(Vue 3 computed 是无参 getter, 带参会 TypeError)
    filt = open(os.path.join(shared, "filters.js"), encoding="utf-8").read()
    methods_seg = filt.split("  methods: {", 1)[1].split("\n  computed: {", 1)[0]
    assert "    listEmptyText(hitNoun, noun, noneText) {" in methods_seg, \
        "filters.js::listEmptyText 不在 methods 段 —— 带参 helper 落进 computed 会 TypeError(整块空态白屏)"
    # 图标选择的语义口径文档必须还在单点分片头注里(此前就是没有文档才各处各写)
    for sym in ("#i-inbox", "#i-hourglass", "#i-warn"):
        assert sym in single_text, f"{single} 头注丢了 {sym} 的语义口径 —— 图标选择又变成「各处写了什么」"

    # 行为电池: 三张列表 × 五种空态场景
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_LIST_EMPTY_PROBE, os.path.join(shared, "filters.js")],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"列表空态文案 node 探针跑挂了: {(proc.stderr or '').strip()[:400]}"
        res = json.loads(proc.stdout.strip())
        assert res["total"] == 15, f"语义电池只有 {res['total']} 项(应为 15 —— 三视图 × 五场景; 被删减? 同步本守阵)"
        assert not res["failed"], (
            "列表空态文案行为漂移: " + "、".join(res["failed"]) + " —— 收敛时刻意保留的分歧(辅种页搜索说「种子」/面筛说 l10nGroup、追剧页「暂无剧集可展示」、"
            "种子页补回「正在构建文件索引…」)被改掉了"
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


def test_frontend_window_source_kind_descriptor_parameterized():
    """行窗口化窗口源按 kind 参数化守阵(计划 26-11-02-0351 W2, 主表零变化纯重构)

    W2 把 columns.js 窗口化一节对 window.scrollY / window.innerHeight 的硬编码(全页滚动)抽成
    按 kind 的「窗口源描述符」: 滚动源 / 视口 / 容器顶偏移 / 滚动绑定 / 行键, 每 kind 一份 ——
    为 W3 给抽屉表挂容器 kind(滚动源 = .drawer-body 的 scrollTop)铺路。主表三 kind 必须逐行等价。

    钉四件事:
    1. **唯一直读点**(机检): columns.js 的 WIN-SOURCES 哨兵段是窗口化几何对 window.scrollY /
       window.innerHeight 的唯一直读区; 窗口化方法节零直读 —— 参数化回潮(方法里又摸 window)即红。
    2. **主表路径等价**: _rowKeyOf / _ensureWinTop / _onWinScroll / _onWinResize 全走描述符且
       _winSrc 未注册回落文档型(保守默认 = 现行为); _rowWindow 三个调用点仍在。
    3. **W3 接线(计划 26-11-02-0351)**: columns.js WIN_SOURCES 注册 drawerContent(容器型
       winSrcContainer + 行键 item.k); app.js 抽屉两表(drawerContentV10/V11)挂
       window:"drawerContent" 且 segs 分段桥(08/05)显式不接窗; drawer_templates.js 桥消费面
       (drawerWinView/dtWinRows/dtWinPad/dtBridgeLines/dtWinKbd)与 xtpl.html 桥模板接线
       (aq-row-pad 占位 ×2 / dtBridgeLines 行源 / @keydown 跨窗回焦)在位。
    4. **行为**(有 node 时真跑): 容器型 winSrcContainer 下桩 scrollTop/clientHeight 后,
       窗口切片起点/终点/上下占位与文档型同输入同输出(三个滚动位); 源族分流(容器族只读
       _winCtn / 文档族只读 _winScrollY 对, 未注册 kind 回落文档型); 描述符几何与绑定契约
       逐项钉值; 零差异回退(行数 < ROW_WIN_MIN / 未量齐 / rowWin 关)不回潮。

    无 node 的机器只跑静态那一半(静默跳过电池, 不引入 pytest skip, 基线 0 skipped)。
    """
    cols = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
    app = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()

    # 1. WIN-SOURCES 哨兵段成对且唯一; window.scrollY 全文件只出现在段内(列菜单/横滚条摸的是
    #    innerWidth/innerHeight, 属各自特性, 不在本断言面)
    m_begin = re.search(r"/\* WIN-SOURCES-BEGIN", cols)
    m_end = re.search(r"WIN-SOURCES-END \*/", cols)
    assert m_begin and m_end and m_begin.start() < m_end.start(), (
        "columns.js WIN-SOURCES 哨兵段缺失/不成对 —— 窗口源描述符的单点区段被拆散? 同步本守阵"
    )
    for m in re.finditer(r"window\.scrollY", cols):
        assert m_begin.start() < m.start() < m_end.start(), (
            f"columns.js 偏移 {m.start()} 处直读 window.scrollY —— 窗口化几何必须经窗口源描述符"
            "(计划 26-11-02-0351 W2: WIN-SOURCES 段是唯一直读点)"
        )
    # 1b. 窗口化方法节(方法区 P1-2 标记 -> winMembers)零 window.scrollY / innerHeight 直读
    m_sec = re.search(r"/\* -+ P1-2 行窗口化 -+\s*\n", cols)
    m_member = re.search(r"^\s{4}winMembers\(", cols, re.M)
    assert m_sec and m_member, "columns.js 窗口化方法节标记漂移(P1-2 行窗口化 / winMembers) —— 同步本守阵"
    sec = cols[m_sec.start():m_member.start()]
    for pat in ("window.scrollY", "window.innerHeight"):
        assert pat not in sec, (f"窗口化方法节又出现了 {pat} 直读 —— 滚动几何必须经窗口源描述符(W2 参数化回潮)")

    # 2. 主表路径等价: 四个消费方法各走描述符; _winSrc 未注册回落文档型
    def _body(text, fn):
        m = re.search(rf"\n    {fn}\([^)]*\) " + r"\{\n(.*?)\n    \},", text, re.S)
        assert m, f"columns.js 找不到 {fn}( 改名或挪走了? 同步本守阵"
        return m.group(1)

    assert "WIN_SOURCES[kind] || WIN_SRC_DOC" in _body(cols, "_winSrc"
                                                      ), ("_winSrc 缺保守回落 —— 描述符缺失必须回落文档型(现行为), 否则未知 kind 直接炸")
    assert "this._winSrc(kind).keyOf(item)" in _body(cols, "_rowKeyOf"), "_rowKeyOf 未走描述符"
    assert "this._winSrc(kind).topOffset(el)" in _body(cols, "_ensureWinTop"), "_ensureWinTop 未走描述符"
    assert "WIN_SRC_DOC.scrollY()" in _body(cols, "_onWinScroll"), "_onWinScroll 未走描述符"
    assert "WIN_SRC_DOC.viewH()" in _body(cols, "_onWinResize"), "_onWinResize 未走描述符"
    for call in ('_rowWindow("member"', '_rowWindow("torrent"', '_rowWindow("group"'):
        assert call in cols, f"{call} 调用点消失 —— 主表三窗口断了(恒久活性探针)"

    # 3. W3 接线(计划 26-11-02-0351): 抽屉两表挂 window:"drawerContent"(必须为注册过的 kind 名);
    #    segs 分段桥描述符(08/05)显式不接窗(恒 null); 桥模板消费面三件就位(切片/占位/跨窗键盘)
    assert "drawerContent: 27" in app, ("app.js ROW_WIN_EST_H 缺 drawerContent 档(27 = --tbl-row-minh 校准值)")
    m_src = re.search(r"drawerContent: Object\.assign\(winSrcContainer\(", cols)
    assert m_src, ("columns.js WIN_SOURCES 缺 drawerContent 注册(容器型 winSrcContainer)—— W3 滚动源未接")
    assert 'keyOf: (item) => item.k' in cols, "columns.js drawerContent 描述符缺行键 keyOf(item.k)"
    for tid in ("drawerContentV10", "drawerContentV11"):
        m = re.search(rf"{tid}: " + r"\{(.*?)\n  \},", app, re.S)
        assert m, f"app.js 找不到 {tid} 注册条目(改名了? 同步本守阵)"
        assert 'window: "drawerContent"' in m.group(1), (
            f"{tid} 未挂 window:\"drawerContent\" —— 千文件窗口化接线断了(打回 null 即回退全量渲染)"
        )
    for seg_tid in ("drawerPeerV08", "drawerTrackerV05"):
        m = re.search(rf"{seg_tid}: " + r"\{(.*?)\n  \},", app, re.S)
        assert m, f"app.js 找不到 {seg_tid}(segs 分段桥, 改名了? 同步本守阵)"
        assert "window: null" in m.group(1), (f"{seg_tid} 的 window 被动了 —— segs:true 分段桥显式不接窗(一段一锚, 占位件无位可插)")
    dtpl = open(os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"), encoding="utf-8").read()
    for fn in ("drawerWinView", "dtWinRows", "dtWinPad", "dtBridgeLines", "dtWinKbd"):
        assert fn in dtpl, f"drawer_templates.js 缺 W3 桥窗口化消费面 {fn}(切片/占位/跨窗回焦三件)"
    xtpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl.html"), encoding="utf-8").read()
    m_bridge = re.search(r'id="tpl-aq-dt-bridge">(.*?)</script>', xtpl, re.S)
    assert m_bridge, "xtpl.html 桥模板 tpl-aq-dt-bridge 找不到(改名了? 同步本守阵)"
    bridge = m_bridge.group(1)
    assert "aq-row-pad" in bridge and "dtWinPad(tab, 'top')" in bridge and "dtWinPad(tab, 'bottom')" in bridge, (
        "桥模板缺上下占位件(aq-row-pad × dtWinPad)—— 窗口化折叠段的撑高契约断了"
    )
    assert "dtBridgeLines(tab, seg)" in bridge, "桥模板 v-for 未走 dtBridgeLines 行源单点(窗切片/全量回落)"
    assert "dtWinKbd($event, tab)" in bridge, "桥模板 .group-table 缺 @keydown 跨窗回焦接线"

    # 4. 有 node 时真跑语义电池(行为面)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_WIN_SRC_PROBE,
             os.path.join(STATIC_ROOT, "shared", "columns.js")],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"窗口源描述符 node 探针跑挂了: {(proc.stderr or '').strip()[:400]}"
        res = json.loads(proc.stdout.strip())
        assert res["total"] >= 18, f"语义电池只有 {res['total']} 项(被删减? 同步本守阵)"
        assert not res["failed"], ("窗口源描述符行为漂移: " + "、".join(res["failed"]) + " —— 主表等价/容器型几何被改掉")


def test_frontend_row_window_sig_and_ctn_sync_guard():
    """行窗失效签名守阵(2026-11-02 关抽屉/切页卡死取证, 报告 26-11-02-0339 后续)——两根因防回潮

    1. _measureRowH 的行高签名**不含 viewMode**: 签名含 viewMode 时每次切页把三 kind 行高全表
       作废并翻 _winMeasured=false, 返回该视图即走一轮全量渲染量齐(3000 种子实测 5.8~8.4s 长任务,
       用户所见「切标签页卡死几秒」)。行宽几何不随 viewMode 变 —— 列集合(colcounts)与视口宽
       (_winResize)两因子独立在签名里, 真变化仍能作废。e2e 对面: window-invalidation.spec.mjs。
    2. _winCtnSync 必须先过 drawer.open 守卫再读 .drawer-body 几何: 收场动画 .drawer 转 absolute
       出流(三皮肤 dialogs.css .drawer-leave-active), clientWidth 实测跳 1894->1918 是过渡假象;
       采信就假 bump 与主表**共用**的 _winResize, 下一拍 updated 钩子按签名失配全量重渲主表
       (3000 行实测 5.6s 长任务, 用户所见「关抽屉后卡死; 能滚不能点」—— 滚轮走合成器不进主线程)。
    """
    rel = "shared/columns.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()

    # 1) 行高签名: 无 viewMode, 有 _winResize 与列集合因子
    m = re.search(r"_measureRowH\(\)\s*\{(.*?\n    \},)", text, re.S)
    assert m, f"{rel} 找不到 _measureRowH()(改名或挪走了? 同步本守阵)"
    sm = re.search(r"const sig = `([^`]*)`", m.group(1))
    assert sm, "_measureRowH 缺行高签名模板(结构变了? 同步本守阵)"
    sig = sm.group(1)
    assert "viewMode" not in sig, (
        "_measureRowH 行高签名重新出现 viewMode —— 每次切页把三 kind 行高"
        "全表作废并翻 _winMeasured, 返回该视图即全量渲染量齐(3000 行实测 5.8~8.4s 长任务, "
        "2026-11-02 切页卡死根因); 行宽几何不随 viewMode 变, 列集合/视口宽两因子已独立在签名里"
    )
    assert "${this._winResize}" in sig and ".cols].length" in sig, ("行高签名缺 _winResize/列集合因子 —— 真宽度/列变化必须仍能作废行高")

    # 2) _winCtnSync: drawer.open 守卫先于 clientWidth 读取(判定只认代码态, 注释里提到不算)
    m2 = re.search(r"_winCtnSync\(\)\s*\{(.*?\n    \},)", text, re.S)
    assert m2, f"{rel} 找不到 _winCtnSync()(改名或挪走了? 同步本守阵)"
    code_lines = [ln.strip() for ln in m2.group(1).splitlines() if not ln.strip().startswith(("*", "//"))]
    code = "\n".join(code_lines)
    guard_idx = code.find("!this.drawer || !this.drawer.open")
    assert guard_idx != -1, (
        "_winCtnSync 代码里缺 drawer.open 守卫 —— 收场动画期 .drawer 转 absolute, "
        ".drawer-body clientWidth 是过渡假象(1894->1918), 采信即假 bump 共享 _winResize"
    )
    cw_idx = code.find("clientWidth")
    assert cw_idx != -1 and cw_idx > guard_idx, (
        "_winCtnSync 的 drawer.open 守卫必须先于 clientWidth 读取 —— 守卫被挪到读取之后 = "
        "关抽屉假 bump 回潮(2026-11-02 关抽屉卡死根因)"
    )
