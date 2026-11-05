# 拆分与统一后前端守阵口径的完整处置与实测证据 — 外迁详情(原 `pitfalls/web-ui/frontend-split.md` 段落原文)

> 摘要: `pitfalls/web-ui/frontend-split.md` 的详细处置/实测证据原文外迁(主档为控 cap 原位留指针); 判据与实测证据原样保留。
> 触发: 同主档 `pitfalls/web-ui/frontend-split.md` 的触发词(完整列表见主档头部)。

> 本文件是**外迁存档**: 主档该段原文一字未改搬来 (仅相对链接整体下移一层 —— 本文件在 `pitfalls/web-ui/attachments/`); 本目录不计 cap, 主档原位留指针。
## 找模板/CSS/JS 内容: 一律读「聚合」, 别单读拆分前的文件

- **处置**: 统一走聚合助手 —— 模板 `_ui_aggregate(ui)`(shell 内联段 + 分片按 tpl-manifest 清单序)、CSS `_ui_css_aggregate(ui)`(按 shell link 序, 级联序=link 序)、JS `_app_bundle_text()`(清单序整包); 清单本身就是单一来源(tpl-manifest / head link / manifest scripts), 别在守阵里另抄一份顺序。
  机器索引 (2026-10-31, issue 26-10-31-2226-feat-webui-agg-content-map): `commands run dev.ui-map -- <关键词>`
  单点输出四域(shell 内联/tpl/css/JS)落点 + tpl 挂载面 + css link 序 + JS 清单序, 本节降为解释。

## 模板级 UI 差异只走「差异口」, 私拷副本即红

- **处置**: `<template v-if="ui === 'atlas'|'prism'">` 条件块 + 块前 `ui-diff:` 注释说明原因; `_scan_ui_diff_registry` 收集全部条件块作为「活差异清单」(取值只认两 UI, 注册表为空也红 —— 机制必须保持存活)。参数化小差异(如界面切换下拉的选项表)优先走 computed(`uiCurrent`/`uiOptions`, 数据单点 `UI_HOME`)而非条件块。
- **守阵**: `test_frontend_template_split_wiring`。

## 三份 shell 内联段(sprite / #app+login) parity 守阵

- **处置**: `tests/test_webui_static_skins_skin.py::test_frontend_shell_sprite_login_parity` —— ①sprite 段锚点切片(`<svg class="icon-sprite"` 起配套 `</svg>` 止)三份**逐字相等**, 另钉 symbol 数 ≥40 下限(实测 67): sprite 若被整体外提成共享文件, 三份会同时消失、相等断言恒真, 下限逼那种迁移显式改守阵; ②`#app`+login 段(`<div id="app"` 起 `tpl-manifest` 前止)**归一 HTML 注释与空行后**相等 —— console 合法多一行皮肤说明注释(§现象已记"仅差 1 行注释"), 照"逐字相等"字面执行会恒红, 故注释不参与比对(注释不渲染), 标记/属性/文本 drift 一律红。失败信息带首个差异行(行号 + 两侧原文)并提示"改图标/改登录遮罩须三皮肤同步"。
- **守阵**: `test_frontend_shell_sprite_login_parity`(issue 26-10-20-2231, 2026-10-21 认领并修; 红验三类突变: console sprite 单边漂移红 / prism login 标记漂移红 / prism login 仅注释漂移绿, 突变精确反向还原后三份 shell `git diff` 零改动)。
- **复发**: 0

## schema→默认值梯单点(cfgDefaultScalar / cfgDefaultForFields / cfgDefaultForPlugin)

- **处置**: 只剩一条下降链 —— `cfgDefaultScalar(node, opts)`(叶子 → 标量)与 `cfgDefaultForFields(fields, opts)`(字段清单 → 对象), 三处的差异退化成 opts 三个开关 `requiredOnly` / `recurse` / `boolOn`; 插件形态分派 `cfgDefaultForPlugin(meta)` 只按 `spec_kind` 选 list / 子表单 / 叶子(取值域单点 `SPEC_SCALAR_KINDS`, 与后端 `Plugin.spec_kind` 对应)。改默认值规则 = 只改 `cfgDefaultScalar` 一处。
- **守阵**: `test_frontend_config_default_ladder_single_point`(issue 26-10-20-2231, 2026-10-21 认领并修)—— 形态六查(三单点各定义一处 / 旧 `cfgPluginDefaultSpec|Section` 零残留 / 插件侧零手搓字段循环 / `options[0]` 全仓一处 / 两入口体内无循环只转调 / 恒久活性探针钉调用点) + 有 node 时真跑 11 项语义电池(把上述分歧逐条钉死)。合并当轮做了**行为等价性实证**: 真实 `schema_payload()` 下 25 个插件 spec 初值 + 18 个 object 段初值, 改动前后两份 JSON `diff` 为空。
- **复发**: 0

## 列表外壳两件套单点(`aq-row-pad` / `aq-empty`)—— 几何契约与三皮肤 CSS 契约都在结构里

- **处置**: 单点分片 `tpl/list-shell.html` 放两个 `x-template`, 组件定义在 `shared/table.js`(`AQ_ROW_PAD_COMPONENT` / `AQ_EMPTY_COMPONENT`)、`app.js` 末尾 `app.component(...)` 注册、三份 shell 的 `tpl-manifest` 以 `{"into": "body"}` 挂载(在 `#app` 外, 不当根模板编译)。三条硬约束: ①`<aq-row-pad :height>` **挂两次**(上占位在 `v-for` 前、下占位在后) —— 不要试图做成"一个实例渲上下两块": 占位必须**夹住**中间的行, 而组件实例的渲染结果只能出现在自己位置上(多根片段也只是连续一段); ②**行本身不收敛**, 仍由调用方 `v-for` 内联渲染 —— 每列表两个占位实例(不是每行), 守住"窗口化热路径不引入逐行组件实例"的纪律; ③`<aq-empty>` 根元素必须仍是 `div.empty`、内部必须仍是 `svg.ico` + `span`, 并把图标语义(`#i-hourglass` 加载中 / `#i-warn` 出错 / `#i-inbox` 空·缺省)写进分片头注。
- **守阵**: `test_frontend_list_row_pad_and_empty_single_point`(issue 26-10-20-2231, 2026-10-21 认领并修)—— 形态查(除单点分片外任何模板不得手写 `class="row-pad"` / `div.empty`; 组件定义与注册各一处; `template` 指回自己的 x-template) + 活性探针(调用点下限 8 / 12) + `listEmptyText` 必须在 `methods` 段(落进 `computed` 会 TypeError ⇒ 空态整块白屏) + 图标口径三段文档在头注里 + 有 node 时 15 项语义电池(三列表 × 五场景)。
- **⚠ 活性探针的陷阱**: 计数**必须先剥掉 HTML 注释** —— 各分片头注里就写着 `<aq-row-pad>` / `<aq-empty>` 字样(解释收敛缘由), 直接 `count` 会让下限被注释撑满, 删掉真实调用点照样达标。本轮红验突变 ③ 就是这么**绿过去的**(删了种子页一个占位仍 8 处), 剥注释后实测 8 / 12 恰好等于下限, 删任一处即红。
- **复发**: 0

## data/computed/watch/生命周期不许进 app.mixin —— 根选项专属

- **处置**: 根组件的 data/computed/watch 在 `state.js`、生命周期在 `lifecycle.js`, 经 app.js 的 `...window.X` **展开进 createApp 根选项**(只命中根); 方法域(auth/polling/view 与业务片段)才走全局 mixin。接线由 `_scan_mixin_wiring` 形态④钉住(只认 app.js 内 `...window.X` 展开, 不放宽)。
- **守阵**: `test_frontend_mixin_wiring`(挂 test_frontend_static_bundle_health)。

## 片段文件里定义「非 mixin 的 window.* 单例」会被接线守阵判漏注入

- **处置**: 写成 `const X_ADAPTER = {...}; window.X = X_ADAPTER;`(赋值右侧不是 `{` 字面量,
  守阵不命中), 并在注释里写明「这是被直接消费的单例, 不走 app.mixin」。键盘快捷键 W1 实测
  (shortcuts.js AQB_KEYS, 2026-09-30); W6 后端存储接入时同形态。
- **复发**: 0

## 新增 shared/ 片段文件的接线清单(三份清单 + app.mixin + prism 的 shell 218 行硬顶)

- **处置**: `.js` 按「加文件 → 三份 `index.html` 的 `scripts` 各加一行 → `app.js` 补 `app.mixin(window.X)`」; `.html` 按「加文件 → 三份 `index.html` 的 `parts` 各加一行(`into` 取 `app`/`body`/`.选择器`)」。**⚠ 两个体量硬顶必须同时算**: ①shell 上限 **218 行**, prism 已贴满(实测 26-10-31: prism 218 / console 217 / atlas 213 —— 但别赌, 三份都要按上限管); ②**单分片 ≤400 行**(`settings-detail.html` 单独给到 560)。`tpl/xtpl.html` 收行模型单元格渲染器时会**先撞 400 行**(P3 实测: 302 + 211 = 513)⇒ 必须另开一个分片(`tpl/xtpl-cells.html`), 而不是硬塞。
- **腾行**: 加清单行时 shell 超顶,**先从该 shell 腾掉一行**(纯排版空行优先 —— atlas/console 各有空行可删; prism 无空行时**把两个相邻的 `parts` 数组项合并到同一行**是安全的: JSON 空白不参与解析, 清单等价断言比对的是 `json.loads` 结果)。合并**只对 `parts` 做**; `scripts` 保持一行一项(它是加载序的阅读面)。
- **守阵**: `_scan_mixin_wiring`(list/注入双向) + `test_frontend_template_split_wiring`(清单完整性 / 三 shell 清单等价 / 孤儿分片 / shell ≤218 / 单分片 ≤400) + `test_frontend_static_bundle_health` 的 shell 行数上限。
- **复发**: 0

## 再拆前端大文件: 等价性验证 = 切割自验 + 真 API stub 冒烟 DOM 比对

- **处置**: ①程序化切割(解析器地标定切点 + 切点锚断言 + 多重集完整性自验), 不手抄; ②改造前先抓 DOM 基线, 改造后跑同一 stub(真 app.js + 最小 API: /api/config/public 免鉴权 + /api/state 定态 + /api/events 即回即关)比对渲染 DOM 逐字节等价(归一相对时间/脚本清单); ③工装是临时目录产物不入仓库(注入点适配见 [../testing/ui-preview-harness.md](../../testing/ui-preview-harness.md))。

## 搬迁方法体(拆文件)时: 按文件名定位的静态守阵要同轮改「读取面」, 不是放宽断言

- **处置**: **只换读取的文件名, 断言口径一字不动** —— 新增 `store_js = _read("<new>.js")` 并把该批断言指向它(必要时两文件都读)。**不得**为了让测试变绿而放宽/删除断言: 搬迁的等价性只能靠 A/B DOM dump 与全量数字证明, 不能靠守阵松绑。动手前先穷举守阵面(`grep -rn "<方法名>" tests/`), 否则会一轮一轮补漏 —— 实测首轮漏两条(`tpl a11y fetch 错误态` / `groups-shows 轮询`), 二次跑才红出来。
- **复发**: 0

## 组件片段只贡献模板: 行为与根数据一律经 `$root` 回调根实例

- **处置**: 组件模板一律写 `$root.xxx(...)`(`this` 仍是根实例, 与内联模板逐字节等价), 且
  **不复制**任何方法实现(复制会触发 `_scan_mixin_wiring` 的重名守阵: 后者覆盖前者, 被盖掉的
  实现永不执行)。⚠ 随之而来一条: 「模板禁 `_`/`$` 前缀标识符」守阵
  (`tests/test_webui_static_dom_page_*.py`, issue 26-10-03-1412)会把 `$root` 一起拦下 —— 该守阵拦的
  是**用户成员**(data/methods 里的 `_x`/`$x` 被 Vue 排除在组件代理之外), Vue **内建**
  (`$event`/`$root`/`$refs`/`$el`…)在实例上真实存在且模板可解析, 不属同类 ⇒ 加进**内建白名单**
  放行(别改用无前缀别名中转几十个方法 —— 那反而多一层手抄名单 + 漏一个就静默退化)。
- **另两条连带(同轮实测)**: ①**表头组件化后 `$refs[headRef]` 是组件实例不是元素** —— 取表头
  元素的唯一入口是 `_headEl(page)`(它 unwrap `$el`), 否则 `head.style.transform` TypeError
  (横滚同步整条挂)、`head.parentElement` 静默 null(成员行窗口化退化成全量渲染); ②**多根片段
  组件**(渲染一组兄弟节点)不包 wrapper —— 单元格必须仍是行容器的**直接子元素**(行是 grid,
  `:nth-child` 列对齐与 `data-table` 都依赖它), 故每**行**一个实例而不是每格一个(patch 开销差
  一个量级); 实测 Vue 对 `v-for` 根片段**不插占位节点**, 故 `outerHTML` 与改造前逐字节相同
  (⚠ 2026-10-11 P5 修正: 这句的**结论错了, 证据也不成立** —— P2 的 A/B 两侧都是同一个
  `v-for`, 锚点两侧相消所以 diff=0, 并不能证明"不插"; 实测任何 v-for 片段都在 DOM 里插
  **2 个零长文本锚点**, 见下一条)。
- **守阵**: `test_frontend_table_shell_single_point` + `_scan_column_cells_paired`(明细列改扫
  渲染器) + `test_frontend_template_no_reserved_prefix_identifiers`(内建白名单)。
- **复发**: 0

## 原生 `<table>` 里上组件必须借 `<tr is="vue:…">` 占位; v-for 会插零长文本锚点(P5)

- **触发**: 把公共表壳组件接进**真 `<table>`** 的表头(计划 26-10-11-1722 P5, 设置页 HR 详情表)。
- **判别(坑一 · foster-parent)**: 本应用根模板是 **in-DOM 的**(`boot.js` 把分片
  `insertAdjacentHTML` 进 `#app`, `app.mount("#app")` 用 innerHTML 编译), 浏览器解析遵守表格
  内容模型 —— **自定义元素(`<aq-table>`)直接放 `<thead>`/`<table>` 里会被 foster-parent 移出
  表格**: 表头整段消失、无任何报错, pytest 全绿(守阵扫的是源码字面, 不是渲染产物)。
  `<slot>` 方案同样不可行: slot 内容在**非表格上下文**被浏览器按 in-body 规则解析,
  `<tr>`/`<td>` start tag 会被**直接丢弃**。
- **处置(坑一)**: 占位写成合法的 `<tr is="vue:aq-table" mode="thead">` —— `<tr>` 在 `<thead>`
  里合法, `is` 属性带 **`vue:` 前缀**让编译器把它当组件(已核 vendored vue.global.prod.js 的
  解析器确实认 `vue:` 并置 tagType=COMPONENT; 不带前缀的裸 `is` 会被当自定义内置元素)。
  组件自身的根由 x-template 字符串编译, 不过浏览器解析, `<tr>` 根随便写。
- **判别(坑二 · v-for 锚点)**: 表头改由注册表 `v-for` 摆列后, 子节点骨架比对多出**零长文本
  节点**(`nodeValue === ""`), 而 `outerHTML` 序列化**不含它们**(零长) —— 只比 outerHTML 会假绿。
  实测(2026-10-11, 真 chromium): 纯 `v-for` = **2 个**锚点(fragment start/end); `v-for` 里再有
  `v-if/v-else` 分支 = **每次迭代再插 2 个**(分支切换靠锚点定位) ⇒ 8 列两支 = 8×2+2 = **18 个**。
- **处置(坑二)**: 锚点是 Vue 片段实现的不变量, 消不掉; 只能**记录在案**并在骨架比对时排除
  (零长文本对 CSS 表格修正是 whitespace-only、不参与布局, `:nth-child` 只数元素 ⇒ 视觉与
  行为零影响)。**避坑**: ①`v-for` 的 `<template>` 内不留换行缩进(空白会被折成零长文本节点,
  与锚点混在一起更难数); ②列的 `class` 别用 `:class="{num}"` —— normalizeClass 恒回字符串,
  非 num 列会渲出空 `class=""`, 与静态字面 `<th>` 不等价, 走 `v-if` 两支。
- **复发**: 0

## 收敛模板会连带改掉按「字面调用」计数的守阵 —— 同轮补覆盖, 不是放宽

- **处置**: 改计数可以, 但**必须同轮把"原本靠份数保证的覆盖"钉到别处**: 例如「两个页面共用同一
  渲染器」由 `_scan_column_cells_paired`(两个调用点都必须用 `<aq-member-cells>`)与
  `test_frontend_table_shell_single_point`(调用点计数)钉住。**只改数字不补覆盖 = 悄悄丢掉"某页
  漏改"的检出能力**, 是这类守阵最常见的失效方式。另: 模板里的方法调用带 `$root.` 前缀后, 按裸名
  匹配的 pattern 会全部落空 —— 改成兼容两种形态的正则, 别把断言删了。
- **守阵**: `test_frontend_hr_safety_wiring` · `test_sel_visual_parity_and_site_cell`(本轮同轮改版)。
- **复发**: 0

## 设置页分区模板: `v-if/v-else-if` 链**跨分片**延续 —— 新分区只能作链尾 `v-else-if`, 且 settings.html 逼近 400 行上限

- **处置**: 新分区一律作 `v-else-if="hub.view === '<key>'"` 加在 **settings.html 末尾**(rules 分支之后、
  settings-detail.html 的 `v-else-if speed` 之前), 与链自然续接。该分支若要渲染本段通用键(通用 `v-else`
  分支不再命中), 用 `<hub-field>` + 一个返回叶子字段的 helper(`cfgFlatten` 同源)显式渲染 —— 别抄通用块模板。
  ⚠ 体量: `settings.html` 单分片上限 400 行; S6(计划 26-10-16-0541)加分区后曾到 **392**, 其后视图已拆出
  独立分片(实测 26-10-31: 313)—— 再逼近 400 先拆(sanctioned 路径), 别硬塞。
- **守阵**: `test_frontend_template_split_wiring`(shell ≤212 / 单分片 ≤400 / 聚合标签配平)+ `test_webui_static_dom_page`。
- **复发**: 0
