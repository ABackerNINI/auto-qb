# 拆分与统一后的前端守阵口径

> 摘要: 模板/样式/内核三层拆分 + 单一语义模板收敛(2026-09-27)后, 找前端内容与加守阵的固定口径 —— 一律读「聚合」, 模板级 UI 差异只走「差异口」, data/生命周期不许进 app.mixin。
> 触发: 改守阵, 找模板内容, 加断言, 两套 UI 差异, 拆分, 聚合读法, 差异口, ui-diff, 根选项, app.mixin, hub-field, boot.js, 冒烟等价, 搬迁方法体, 拆文件守阵假红, v-if 链跨分片, 新分区, settings.html 上限

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md, memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

### 找模板/CSS/JS 内容: 一律读「聚合」, 别单读拆分前的文件

- **触发**: 给前端加守阵 / 找某段模板或样式在哪 / 断言某成员存在。
- **判别**: 拆分后单读 `index.html` / `atlas/style.css` / `app.js` 会**假绿或假红** —— 模板在 `shared/tpl/*.html`、atlas 样式在 `css/{components,views,dialogs}.css`、根组件成员在 `state.js`/`lifecycle.js`、方法域在 `auth.js`/`polling.js`/`view.js`。
- **处置**: 统一走聚合助手 —— 模板 `_ui_aggregate(ui)`(shell 内联段 + 分片按 tpl-manifest 清单序)、CSS `_ui_css_aggregate(ui)`(按 shell link 序, 级联序=link 序)、JS `_app_bundle_text()`(清单序整包); 清单本身就是单一来源(tpl-manifest / head link / manifest scripts), 别在守阵里另抄一份顺序。

### 模板级 UI 差异只走「差异口」, 私拷副本即红

- **触发**: 两套 UI 某块要长得/行为不一样时(如棱镜的主题切换器)。
- **判别**: 绕开机制复制一份分片 = 双模板副本回潮 —— 静默恢复「成对改」人肉纪律。守阵三查: 残留 `<ui>/tpl/` 目录、双 shell 清单漂移、`shared/tpl` 孤儿分片。
- **处置**: `<template v-if="ui === 'atlas'|'prism'">` 条件块 + 块前 `ui-diff:` 注释说明原因; `_scan_ui_diff_registry` 收集全部条件块作为「活差异清单」(取值只认两 UI, 注册表为空也红 —— 机制必须保持存活)。参数化小差异(如界面切换下拉的选项表)优先走 computed(`uiCurrent`/`uiOptions`, 数据单点 `UI_HOME`)而非条件块。
- **守阵**: `test_frontend_template_split_wiring`。

### 三份 shell 内联段(sprite / #app+login) parity 守阵

- **触发**: 改任一 `src/auto_qb/webui/static/<ui>/index.html` 的图标 sprite 段(加/改图标)或登录遮罩段(`#app` + `login-mask`)。
- **判别**: 三 shell 除 head 资源清单外逐字同约 87.5%(manifest 74 行 / sprite 80 行 / `#app`+login 31 行), 但是**三份物理拷贝** —— 漏改一份的表现是"某皮肤下该图标空白且无任何报错"(登录遮罩则是首屏第一眼、在任何 JS 之前渲染的块)。合并唯一路径是后端渲染时注入, 会让 `index.html` 失去"可直接静态打开"的能力(测试亦直接读盘), 属**能力回退** —— 定案是"不合并, 补齐守阵"(R23-C, 台账 `tasks/26-10-20-frontend-dup-code-audit.md`)。
- **处置**: `tests/test_webui_static_skins.py::test_frontend_shell_sprite_login_parity` —— ①sprite 段锚点切片(`<svg class="icon-sprite"` 起配套 `</svg>` 止)三份**逐字相等**, 另钉 symbol 数 ≥40 下限(实测 67): sprite 若被整体外提成共享文件, 三份会同时消失、相等断言恒真, 下限逼那种迁移显式改守阵; ②`#app`+login 段(`<div id="app"` 起 `tpl-manifest` 前止)**归一 HTML 注释与空行后**相等 —— console 合法多一行皮肤说明注释(§现象已记"仅差 1 行注释"), 照"逐字相等"字面执行会恒红, 故注释不参与比对(注释不渲染), 标记/属性/文本 drift 一律红。失败信息带首个差异行(行号 + 两侧原文)并提示"改图标/改登录遮罩须三皮肤同步"。
- **守阵**: `test_frontend_shell_sprite_login_parity`(issue 26-10-20-2231, 2026-10-21 认领并修; 红验三类突变: console sprite 单边漂移红 / prism login 标记漂移红 / prism login 仅注释漂移绿, 突变精确反向还原后三份 shell `git diff` 零改动)。
- **复发**: 0

### data/computed/watch/生命周期不许进 app.mixin —— 根选项专属

- **触发**: 给根组件加状态字段 / 侦听器 / 生命周期钩子时。
- **判别**: `app.mixin` 是**全局** mixin, 波及该 app 下**所有**组件实例(含 hub-field)—— mounted 双份 = 监听器翻倍 + fetch 双发, watch 双份 = 回调双跑; 全部静默, pytest 不可见。
- **处置**: 根组件的 data/computed/watch 在 `state.js`、生命周期在 `lifecycle.js`, 经 app.js 的 `...window.X` **展开进 createApp 根选项**(只命中根); 方法域(auth/polling/view 与业务片段)才走全局 mixin。接线由 `_scan_mixin_wiring` 形态④钉住(只认 app.js 内 `...window.X` 展开, 不放宽)。
- **守阵**: `test_frontend_mixin_wiring`(挂 test_frontend_static_bundle_health)。

### 片段文件里定义「非 mixin 的 window.* 单例」会被接线守阵判漏注入

- **触发**: 在 shared/*.js 片段里定义一个**不是 Vue mixin** 的全局单例(如快捷键存储适配器
  `window.AQB_KEYS`)供同文件或跨文件直接消费。
- **判别**: `_scan_mixin_wiring` 只认 `^window\.(\w+) = \{` 字面量形态并要求它被
  app.mixin/app.component/`...window.X`/Object.assign 基座四种形态接线 —— 适配器这类「被 JS
  直接调用」的单例不在名单里, pytest 直接红「定义了 window.X 但 app.js 没有 app.mixin(window.X)
  (片段漏注入)」。它不是守阵误报要放宽, 而是书写形态约定。
- **处置**: 写成 `const X_ADAPTER = {...}; window.X = X_ADAPTER;`(赋值右侧不是 `{` 字面量,
  守阵不命中), 并在注释里写明「这是被直接消费的单例, 不走 app.mixin」。键盘快捷键 W1 实测
  (shortcuts.js AQB_KEYS, 2026-09-30); W6 后端存储接入时同形态。
- **复发**: 0

### 新增 shared/ 片段文件的接线清单(三份清单 + app.mixin + prism 的 210 行硬顶)

- **触发**: 往 `shared/` 下**新增一个 `.js` 片段文件**(不是改现有文件), 或新增一个 `shared/tpl/*.html` **模板分片**。
- **判别**: 漏一处都**静默或半静默** —— ①`.js` 漏进 `tpl-manifest.scripts` / `.html` 漏进 `parts` → 文件根本不加载, 页面不报错、那块功能整块不存在(盘上有、清单没挂的 `tpl/*.html` 还会被 `test_frontend_template_split_wiring` 的**孤儿分片**项单独判红); ②三份 shell 的清单必须**逐项一致**(清单等价断言比对的是**解析后的 manifest**, 不是 shell 文本); ③`.js` 里写了 `^window.X = {` 却没接 `app.mixin` → `_scan_mixin_wiring` 判「定义了 window.X 但 app.js 没有 app.mixin」(**模板分片无此步** —— 它只贡献 markup)。
- **处置**: `.js` 按「加文件 → 三份 `index.html` 的 `scripts` 各加一行 → `app.js` 补 `app.mixin(window.X)`」; `.html` 按「加文件 → 三份 `index.html` 的 `parts` 各加一行(`into` 取 `app`/`body`/`.选择器`)」。**⚠ 两个体量硬顶必须同时算**: ①`prism/index.html` 贴着 shell 上限 **210 行**(atlas/console 各有 2~4 行余量, 但别赌 —— 三份都要按上限管); ②**单分片 ≤400 行**(`settings-detail.html` 单独给到 560)。`tpl/xtpl.html` 收行模型单元格渲染器时会**先撞 400 行**(P3 实测: 302 + 211 = 513)⇒ 必须另开一个分片(`tpl/xtpl-cells.html`), 而不是硬塞。
- **腾行**: 加清单行时 shell 超顶,**先从该 shell 腾掉一行**(纯排版空行优先 —— atlas/console 各有空行可删; prism 无空行时**把两个相邻的 `parts` 数组项合并到同一行**是安全的: JSON 空白不参与解析, 清单等价断言比对的是 `json.loads` 结果)。合并**只对 `parts` 做**; `scripts` 保持一行一项(它是加载序的阅读面)。
- **守阵**: `_scan_mixin_wiring`(list/注入双向) + `test_frontend_template_split_wiring`(清单完整性 / 三 shell 清单等价 / 孤儿分片 / shell ≤210 / 单分片 ≤400) + `test_frontend_static_bundle_health` 的 shell 行数上限。
- **复发**: 0

### 再拆前端大文件: 等价性验证 = 切割自验 + 真 API stub 冒烟 DOM 比对

- **触发**: 拆任何模板/样式/JS 大文件时(W1/W2a/W2b 已各有一套, 复用方法)。
- **判别**: 静态守阵抓不住**载入期**错误 —— 实测 W2b 切分脚本把原 `const app = createApp({` 残留造成双重声明, pytest 全绿而页面不挂载, 是 stub 冒烟的 `data-drv-mounted` 现形的。
- **处置**: ①程序化切割(解析器地标定切点 + 切点锚断言 + 多重集完整性自验), 不手抄; ②改造前先抓 DOM 基线, 改造后跑同一 stub(真 app.js + 最小 API: /api/config/public 免鉴权 + /api/state 定态 + /api/events 即回即关)比对渲染 DOM 逐字节等价(归一相对时间/脚本清单); ③工装是临时目录产物不入仓库(注入点适配见 [../testing/ui-preview-harness.md](../testing/ui-preview-harness.md))。

### 搬迁方法体(拆文件)时: 按文件名定位的静态守阵要同轮改「读取面」, 不是放宽断言

- **触发**: 把一段实现从 `<old>.js` **搬到**新文件(不是新增片段)时(计划 26-10-11-2106 W1: `drawer.js` → `drawer_store.js` 的数据/行为层)。
- **判别**: 一批守阵是**按文件名读取**来定位方法体的(`_read("<file>.js")` / `open(os.path.join(shared, "<file>.js"))` 后对文本跑正则), **不读聚合** —— 方法体一搬走, 它们整批判「找不到方法体」。这与上一条「加**新**守阵一律读聚合」不冲突: 老守阵的 `_read(<文件>)` 本身就是它钉的契约(方法住在哪个文件), 搬迁即改了契约。
- **处置**: **只换读取的文件名, 断言口径一字不动** —— 新增 `store_js = _read("<new>.js")` 并把该批断言指向它(必要时两文件都读)。**不得**为了让测试变绿而放宽/删除断言: 搬迁的等价性只能靠 A/B DOM dump 与全量数字证明, 不能靠守阵松绑。动手前先穷举守阵面(`grep -rn "<方法名>" tests/`), 否则会一轮一轮补漏 —— 实测首轮漏两条(`tpl a11y fetch 错误态` / `groups-shows 轮询`), 二次跑才红出来。
- **复发**: 0

### 组件片段只贡献模板: 行为与根数据一律经 `$root` 回调根实例

- **触发**: 往 `shared/` 加一个**只渲染模板**的 Vue 组件(表壳 `<aq-table>` / 明细单元格渲染器
  `<aq-member-cells>`, 计划 26-10-11-1722 P1/P2), 组件里要调格式化 / 筛选 / HR 口径等方法。
- **判别**: 全局 mixin 让**子组件也有方法域**, 于是 `this.fmtSizeOrDash(...)` 看着能用 —— 但
  **根数据**(`sortKey`/`colDrag`/`viewMode`/`timeFmt`/filters…)只挂在**根实例**上, 子组件里读到
  的是 undefined: 轻则排序键恒空 / 筛选高亮失灵, 重则 `this.timeFmt[key]` 直接 TypeError —— 两种
  都是「页面照常渲染」的形态, 静态守阵看不出, 只能靠真浏览器。
- **处置**: 组件模板一律写 `$root.xxx(...)`(`this` 仍是根实例, 与内联模板逐字节等价), 且
  **不复制**任何方法实现(复制会触发 `_scan_mixin_wiring` 的重名守阵: 后者覆盖前者, 被盖掉的
  实现永不执行)。⚠ 随之而来一条: 「模板禁 `_`/`$` 前缀标识符」守阵
  (`tests/test_webui_static_dom_page.py`, issue 26-10-03-1412)会把 `$root` 一起拦下 —— 该守阵拦的
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

### 原生 `<table>` 里上组件必须借 `<tr is="vue:…">` 占位; v-for 会插零长文本锚点(P5)

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

### 收敛模板会连带改掉按「字面调用」计数的守阵 —— 同轮补覆盖, 不是放宽

- **触发**: 把 N 份重复模板并成一份(或把内联片段搬进组件)之后跑全量测试。
- **判别**: 一批守阵是靠**在聚合模板里数某个字面调用出现几次**来钉接线的(HR 安全档位: 做种时长
  列的 `hrDurClass(m)`/`hrSrcHalf(m)`/`hrPopEnter($event, m)` 各 3 处触发面; 站点格守阵扫两页
  模板)。副本一合并, 计数必然变(3 → 2), 页面本身没坏 —— 这是**收敛的必然**, 不是漏改。
- **处置**: 改计数可以, 但**必须同轮把"原本靠份数保证的覆盖"钉到别处**: 例如「两个页面共用同一
  渲染器」由 `_scan_column_cells_paired`(两个调用点都必须用 `<aq-member-cells>`)与
  `test_frontend_table_shell_single_point`(调用点计数)钉住。**只改数字不补覆盖 = 悄悄丢掉"某页
  漏改"的检出能力**, 是这类守阵最常见的失效方式。另: 模板里的方法调用带 `$root.` 前缀后, 按裸名
  匹配的 pattern 会全部落空 —— 改成兼容两种形态的正则, 别把断言删了。
- **守阵**: `test_frontend_hr_safety_wiring` · `test_sel_visual_parity_and_site_cell`(本轮同轮改版)。
- **复发**: 0

### 设置页分区模板: `v-if/v-else-if` 链**跨分片**延续 —— 新分区只能作链尾 `v-else-if`, 且 settings.html 逼近 400 行上限

- **触发**: 给设置页加一个新分区(新 schema Group 的二级页)。
- **判别**: 二级页分支是一条 `v-if`(trackers) / `v-else-if`(rules) / … / `v-else` 的**连续链**, 起点在
  `tpl/settings.html`、中途在 `tpl/settings-detail.html`(链的 `v-else-if speed/keys` 与收尾 `v-else` 都在后者;
  后者还自带 `</main>`)。分片按清单顺序拼进 `#app`, 于是**链跨文件延续**:
  - 想在**链中**插分支(settings.html 末尾与 settings-detail.html 之间插一个 `v-else-if`)会**打断链** ——
    其后所有 `v-else-if` 立刻失配(整块静默不渲染, pytest 全绿);
  - 想插在**链尾之后**又落在 `</main>` 之外(`hub.view` 是持久化值, 面板会在非设置页也渲染)。
- **处置**: 新分区一律作 `v-else-if="hub.view === '<key>'"` 加在 **settings.html 末尾**(rules 分支之后、
  settings-detail.html 的 `v-else-if speed` 之前), 与链自然续接。该分支若要渲染本段通用键(通用 `v-else`
  分支不再命中), 用 `<hub-field>` + 一个返回叶子字段的 helper(`cfgFlatten` 同源)显式渲染 —— 别抄通用块模板。
  ⚠ 体量: `settings.html` 单分片上限 400 行, S6(计划 26-10-16-0541)加分区后已到 **392** —— 下次再加内容前
  先把某个视图拆成独立分片(sanctioned 路径), 别硬塞。
- **守阵**: `test_frontend_template_split_wiring`(shell ≤212 / 单分片 ≤400 / 聚合标签配平)+ `test_webui_static_dom_page`。
- **复发**: 0
