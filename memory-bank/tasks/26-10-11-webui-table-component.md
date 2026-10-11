# 26-10-11-webui-table-component — WEBUI 表格公共组件(辅种表/追剧表抽公共表壳)

**Status:** In Progress
**Added:** 2026-10-11
**Updated:** 2026-10-11
**Summary:** 用户「将种子页列表辅种表和追剧表提取为一个公共模板组件, 支持拖拽换位/拖拽调整宽度/点击排序/右键隐藏, 方便后续重构种子详情页用户列表/文件列表/设置中的各种表; 先写一个计划」→ 计划 [26-10-11-1722-plan-webui-table-component.html](../plans/26-10-11-1722-plan-webui-table-component.html)(topic `webui-table-component`, `In Progress`)出后, 用户定调「详情面板问题很多, 后续需要完全重构, 不考虑兼容」并按推荐开始实施。**盘点结论改变了落点**: 四项交互的**行为已单点**(`columns.js` + `sort.js`), **未单点的是模板**(表头块 5 份 / 单元格 `v-if` 分支 127 条 / 列选择器 4 段 / 横滚同步 3 份 / 页枚举硬编码 18+ 处) ⇒ 本轮重心 = 抽表壳 + 表注册表化, 行为层只在既有单点上参数化。**P0 已落地**(零行为变化): app.js 顶部新增表注册表 `TABLE_DEFS`, `TABLE_PAGES` 由它派生, `columns.js`/`sort.js` 里十处页字面量与 ref 名映射一律改为按 id 取; 新增守阵 `test_frontend_table_registry_single_point`。**P1/P2 已落地**: 表头块 5 份收敛为单份表壳组件 `<aq-table>`, 明细成员单元格 2 份收敛为单份行模型渲染器 `<aq-member-cells>`(辅种页/追剧页共用); 组件只贡献模板, 行为经 `$root` 回调根实例; `_headEl` 统一 unwrap 组件实例, 三个横滚同步单点与成员容器随之改走它; 新增守阵 `test_frontend_table_shell_single_point`, `_scan_column_cells_paired` 的明细列改扫渲染器。验收 = 真浏览器 A/B **DOM 逐字节等价**(17 项探针 × 2 皮肤, 差异 0)+ e2e 与基线逐位一致 + 全量守阵绿(数字见 `commands run kb.baseline`)。P3–P6 待续。
**Topics:** webui-table-component

## 原始请求

> 用户(2026-10-11): 「将种子页列表辅种表和追剧表提取为一个公共模板组件, 需要支持拖拽换位/拖拽调整宽度/点击排序/右键隐藏等相关功能, 方便后续重构种子详情页用户列表/文件列表/设置中的各种表。将大部分表的行为统一, 减少维护点, 各个表差异派生, 先写一个计划」

> 追加定调(2026-10-11): 「目前的详情面板问题很多, 后续需要完全重构, 不考虑兼容」

> 再追加(2026-10-11): 「按推荐开始实施」

## 思考过程与决策

- **请求边界判定**: 第一轮 = **执行任务**(写计划, 用户显式要「先写一个计划」, 且本仓计划制品规定单文件 HTML 入 `memory-bank/plans/`)。第二轮 = 修订同一计划(同文件 `## 变更记录` + 抬 `doc-updated`, 不新建 `-v2`)。第三轮 = **执行任务**(改代码), 用户「按推荐开始实施」即授权按计划 §07 的推荐口径落地。
- **盘点改变落点(本轮最重要的判断)**: 原以为是「交互要重写」, 读码后确认四项交互**已单点**在 `shared/columns.js`(显隐 `toggleColumn` / 重排 `startColDrag`+`applyColOrder` / 调宽 `startResize`+`autoFitColumn` / 对齐 `colAlignCss` / 持久化 `persistPage` / 窗口化 `_rowWindow`)与 `shared/sort.js`(三态 `setSort`)。**未单点的是模板**: 表头块 5 份(`groups.html` 组头+明细头 / `shows.html` 剧头+明细头 / `torrents.html` 种子头)、单元格 `v-if` 分支 127 条、成员行 2 份逐字近似、列选择器 4 段、横滚同步 3 份、页枚举字面量 18+ 处。⇒ 计划把重心放在**抽表壳 + 表注册表化**, 行为层不搬家。
- **详情面板移出范围**: 用户定调「完全重构、不考虑兼容」后, 计划把系统 B(详情面板, 字符串 DOM + 15 变体)从迁移范围移除; DOM 适配降级为**条件项**(仅当重构后的面板仍走字符串 DOM); P6 改为「只留前向契约、零代码迁移」; 拍板点 D1 推荐随之从「双适配 C」升级为「单适配 A(Vue 组件)」; 新增风险 10(为将废弃的面板投入适配 = 沉没成本)。
- **P0 的边界(零行为变化)**: 只做「按 id 迭代」的地基 —— 不改模板、不改 CSS、不动 DOM 结构(表壳抽取属 P1)。列定义常量(`GROUP_COLUMNS` 等)**原样保留**: 守阵 `_scan_column_cells_paired` 按 `const 名 + 模板字面` 扫, 注册表只**引用**它们, 因此该守阵不需要动(P2 才改扫注册表)。
- **注册表的字段选择**: 只收「表身份」—— `columns` / `headRef` / `tableRef` / `grid` / `cols` / `window` / `sort`。`grid`/`cols` 存的是 **computed 名**(模板仍按 `groupGrid`/`visibleGroupCols` 这些既有名字取用, 名字不动), 注册表只做 id→名字的映射单点。行窗口化的 kind(`group`/`torrent`/`member`)与表 id 并非一一对应(明细表 id 是 `detail`、其 kind 是 `member`), 故 `window` 单独一列并在 `_winGapOf`/`_ensureWinTop` 里按 `TABLE_DEFS[kind]` 取值 —— `member` 无表定义 ⇒ 回 `null` ⇒ 走 `.detail` 父容器(与旧分支等价)。
- **排序键也收进注册表**: `sort.js` 的 `_sortKeys` 原来按 `viewMode` 三段分派、`_resetSort` 再按 `viewMode` 二选一 —— 现统一为 `TABLE_DEFS[id].sort = {gk, gd, defKey, defDir}`, 表 id 由 `VIEW_TABLE`(视图→表)解析。默认序目标值(分组/种子 = 最近添加降序、追剧 = 最近动静降序、明细 = 空键)随之单点化, `DEFAULT_SORT` 仍作为分组/种子的取值来源被注册表引用(state.js 初值不动)。
- **`_measureRowH` 的签名**: 它是私有缓存键(只与自身比较), 但仍按 `[TABLE_DEFS.group, .torrent, .detail]` 现算 —— `map(...).join("|")` 产出的字符串与旧模板串**逐字节相同**, 保证零行为变化。
- **e2e 34 项失败不是本轮的**: 首次跑全量 e2e 得 34 failed, 先按「改动前后 A/B」定位 —— 把三个 JS 文件 `git checkout` 回 HEAD 后在基线重跑同一批 spec, 得到**逐项相同的失败集**(trigger-scope 10 / multiselect-shows 10 / optimistic 10 / menus 4), 故判定为**存量失败**(HEAD `cfe9a8d5` 即如此), 与 P0 无关。

## 实现计划

计划见 [plans/26-10-11-1722](../plans/26-10-11-1722-plan-webui-table-component.html) §05(P0–P6); 本档案只记执行与验证。推荐口径(用户「按推荐实施」): D1 = 单适配(纯引擎 + Vue 组件) / D2 = 声明式单元格按行模型收敛 / D3 = HR 表只借壳 / D4 = 详情面板只留契约 / D5 = P0 落地后立档(本轮已立)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| P0 | 注册表骨架: `TABLE_DEFS` + `TABLE_PAGES` 派生 + `columns.js`/`sort.js` 按 id 取 + 守阵 | **Done** |
| P1 | 抽表壳组件 `<aq-table>`, 先只接辅种表(验收 = 真浏览器 DOM 逐字节等价) | **Done** |
| P2 | 追剧表接入 + 两处成员明细合并; 守阵 `_scan_column_cells_paired` 改扫注册表 | **Done** |
| P3 | 单元格渲染器收敛(127 条分支按行模型归拢) | 待做 |
| P4 | 列选择器 / 横滚同步 / 排序键 三处重复收敛 | 待做 |
| P5 | 设置页 HR 表接入(只借壳, D3=B) | 待做 |
| P6 | 详情面板: 只留前向契约, 零代码迁移(D4=A) | 待做 |

## 进度日志

### 2026-10-11 · P0 注册表骨架(零行为变化)

- `shared/app.js`(+52/-1): 新增 `TABLE_DEFS`(四张表各一行, 字段见「思考过程」) + `VIEW_TABLE`(视图→表 id); `TABLE_PAGES` 从 `["group","detail","torrent","show"]` 字面量改为 `Object.keys(TABLE_DEFS)`(顺序即定义序, 逐位一致)。列定义常量与 `TABLE_COLUMNS` 一字未动。
- `shared/columns.js`: `gridStyle`(computed 名映射)/`_headEl`(ref 名映射)/`_winContainer`(成员容器取 `TABLE_DEFS.detail.headRef`)/`_winGapOf`/`_ensureWinTop`(容器 ref 取 `tableRef`) 全部改为注册表取值; `recomputeEffective` / `colAlignCss` 的两处四页字面量 → `TABLE_PAGES`; `_measureRowH` 签名按注册表现算(字符串与旧值相同); `torrentWin`/`groupWin` 的 `_rowWindow` ref 参数取 `tableRef`。
- `shared/sort.js`: `_sortKeys` 由三段 `viewMode` 分派改为 `TABLE_DEFS[id].sort`(`id` 由 `scope==="detail"` 或 `VIEW_TABLE[viewMode]` 解析); `_resetSort` 由二选一分支改为读 `defKey`/`defDir`。
- `tests/test_webui_static_skins.py`: 新增 `test_frontend_table_registry_single_point`(同步模块头「测试计划」清单)—— 钉 ①`TABLE_DEFS` 存在且 `TABLE_PAGES` 由它派生; ②四张表的 `columns`/`headRef`/`tableRef` 指向既有单点且顺序 = 定义序; ③`columns.js`/`sort.js` 里四页字面量与 `viewMode` 分派零残留。**红绿双验过**: 把 `group.columns` 改成 `DETAIL_COLUMNS` ⇒ 1 failed; 还原 ⇒ 1 passed(改动用 `cp` 备份 + sha256 复核还原一致)。
- 文档回写: `modules/webui-static-contract.md`(表身份单点 + app.js 行数 488→582); `pitfalls/git/editing-traps.md`(行尾坑 `复发 +1`)。

### 2026-10-11 · P1/P2 表壳组件 + 明细单元格渲染器(模板单点)

- **新增 `shared/table.js`(47 行)**: 两个**只贡献模板**的全局组件 —— `window.AQ_TABLE_COMPONENT`(`<aq-table>`: 表头块 = 列名/排序箭头/拖宽把手/重排指示线/表头右键) 与 `window.AQ_MEMBER_CELLS_COMPONENT`(`<aq-member-cells>`: 明细成员行的 28 个列分支, member 行模型)。模板放 `tpl/xtpl.html` 的 x-template(与 `hub-field` 同范式; 该分片注入 **body**, 不被当作根模板编译也不多包 DOM 层)。
- **组件↔根实例接线 = `$root` 回调**: 全局 mixin 让子组件也有方法域, 但**根数据**(`sortKey`/`colDrag`/`viewMode`/`timeFmt`/filters)只在根实例上 ⇒ 组件模板一律 `$root.xxx(...)`(`this` 仍是根实例, 与内联模板逐字节等价), 且**不复制**任何方法实现(复制会触发 `_scan_mixin_wiring` 重名守阵)。连带把 `$root` 加进 `test_frontend_template_no_reserved_prefix_identifiers` 的**内建白名单**(与 `$event` 同口径 —— 该守阵拦的是**用户成员** `_x`/`$x`, Vue 内建不在此列)。
- **`shared/app.js`**: 尾部补两行 `app.component("aq-table"/"aq-member-cells", window.AQ_*)`; 头部注释补「组件片段」形态说明。
- **`shared/columns.js`**: `_headEl(page)` 统一 unwrap —— 表头组件化后 `$refs[headRef]` 是**组件实例**, 取 `el.$el || el`(组件前 ref 即元素, 原样返回); `_winContainer` 的成员分支改走 `_headEl("detail")`(原来直读 `$refs[TABLE_DEFS.detail.headRef]`, 组件化后 `head.parentElement` 会静默得 null ⇒ 成员行窗口化退化成全量渲染)。
- **`shared/menu.js` / `selection.js` / `shows.js`**: 三个横滚同步单点的表头元素一律改走 `_headEl(<表>)`(直接读 `$refs` 再 `head.style.transform = …` 会 TypeError ⇒ 横滚同步整条挂)。种子页表头**本轮未迁移**, 但 `_headEl` 对普通元素原样返回 ⇒ 三处写法统一。
- **`tpl/groups.html` / `tpl/shows.html`**: 四个表头块(辅种组头 + 明细头 · 追剧剧头 + 明细头)替换为 `<aq-table ref=… table-id=… :cols=… :sort-key=… :sort-dir=… :drag="colDrag">`; 明细成员单元格的 `<template v-for>` 链替换为 `<aq-member-cells :cols="visibleDetailCols" :m="m">`(行容器与行仍在本页内联 —— 计划停手点: 行渲染不进组件)。
- **`tpl/xtpl.html`**: 追加两份 x-template(`#tpl-aq-table` / `#tpl-aq-member-cells`); 成员单元格分支**逐字复制**原内联文本(仅去掉一层缩进), 以便 DOM 等价比对可按文本核对。
- **三份 `index.html`**: 清单 `scripts` 各加一行 `/shared/table.js`(排在 `/shared/sort.js` 之后); **prism 贴着 210 行硬顶** ⇒ 同轮删掉 `#app` 与清单之间那行空行(纯排版, 不参与 JSON 解析也不进 DOM)。
- **守阵同轮改版(不是放宽)**:
  - `_scan_column_cells_paired`: 明细列(DETAIL_COLUMNS)从"扫 `groups.html` + `shows.html` 两处成对"改为"扫渲染器所在分片 `tpl/xtpl.html`", 并补两条 —— `aq-member-cells` 必须 `app.component` 注册、两个页面模板都必须用 `<aq-member-cells>`(漏一处 = 该页退回内联副本, 静默回潮)。
  - 新增 `test_frontend_table_shell_single_point`: ①两组件注册; ②`shared/table.js` 两个 `window.AQ_*` 定义; ③`tpl/xtpl.html` 里两个 x-template 各恰一份, 且 `#tpl-aq-table` 含四件交互把手(`.h-cell`/`.h-label`/`.arrow`/`.resizer`/`.col-drop-line`); ④`groups.html`/`shows.html` 各 2 个 `<aq-table>` 调用点(先剥注释再数)、页面模板 `.h-cell` 零残留。**红绿双验过**(见「验证」)。
  - `test_frontend_hr_safety_wiring`: 做种时长列的**触发面计数 3 → 2**(明细单元格两份并为一份渲染器; 渲染器 + 种子页各一), pattern 改为兼容裸名/`$root.` 前缀两种形态。**计数变了必须补覆盖**: 「两页共用同一渲染器」的关系由上面两条守阵钉住, 覆盖不丢。
  - `test_sel_visual_parity_and_site_cell`: 站点格从"扫两页"改为"扫渲染器 + 钉两个调用点都走 `<aq-member-cells>`"。
- 文档回写: `modules/webui-static-contract.md`(三层拆分段的 JS 数 27→28 / app.js 行数 582→587 / 新增组件形态; 表身份单点补 `_headEl` unwrap; 列模型段明细列改述为单份渲染器; 列对齐段补表头由组件渲染) + `pitfalls/web-ui/frontend-split.md`(新增一条「组件片段只贡献模板, 行为/根数据经 `$root` 回调」)。

### 验证

- `commands run test.full`: 全绿(与上一片基线相比 = 仅新增守阵那一条; 数字见 `commands run kb.baseline`)。
- 前端静态守阵 `test_webui_static_skins.py` + `test_webui_static_dom_page.py` + `test_webui_static_dom_panel.py`: 全绿(含新增 1 条)。
- **真浏览器 A/B DOM 逐字节等价(本轮硬验收)**: 写一次性探针 spec(不进仓库)在 atlas/prism 两皮肤各 dump 17 项 —— 辅种/追剧表头与明细表头 `outerHTML`、三处子节点骨架(**含注释与文本节点**, 专抓多根片段的锚点/占位)、成员行 `outerHTML` 与骨架、`grid-template-columns` 内联样式、注入的 `col-align-css` 全文、`.content` 直接子元素序。**A 侧 = 把 11 个改动文件 `git show HEAD:` 还原 + 删掉 `table.js`**(跑完按 sha256 逐文件复核还原一致); **B 侧 = 本轮构建**。**差异 0 项 / 34 项**。
- 真浏览器 e2e `commands run dev.e2e`: 与上一片基线**逐位一致**(通过 / 失败 / 跳过三项数字与上片相同; 全量轮里多出的 2 条就是那支临时探针 spec, 已删)。失败项仍是**存量**(trigger-scope / multiselect-shows / optimistic / menus, 见「思考过程」末条), 本轮未新增; `column-prefs.spec.mjs` 单跑全绿。
- **四项交互真浏览器取证(本轮硬验收的另一半)**: e2e 现有轨道只覆盖了**拖宽**(`column-prefs.spec.mjs` 的 `dragCol`)与表头盒子模型(`views.spec.mjs`), **排序 / 表头右键 / 拖拽重排**三项无覆盖 ⇒ 另写一次性探针 spec(不进仓库), 两皮肤各验: ①点击排序三态(首点降 → 再点升 → 第三击恢复默认)+ 箭头图标只出现在命中列 + 行序真的重排; ②表头右键打开菜单(`headMenu.page/key` 正确)、Escape 关闭; ③菜单里「隐藏「总上传」」→ `colHidden` 记上且表头少一格; ④拖拽重排 → 拖拽中组件渲染出 `.col-drop-line`、`colDrag` 置位/释放、`colOrder` 变化且**表头可见列序 == 可见列模型序**; ⑤明细表头(组件)排序 scope=detail / 右键 page=detail; ⑥追剧剧头排序键独立 + 右键 page=show + 拖宽固化 `colW.show`。**全绿**。
  - 探针期踩到两个**探针自身**的坑(都不是产品缺陷, 但会伪装成"改造坏了"): ①`startColDrag` 收尾会装一个 capture 阶段 swallow 吃掉紧随的一次 click(既有防误触设计)⇒ 拖拽之后的第一个点击会被吞, 故探针里"右键隐藏"必须排在拖拽之前; ②表头菜单是 `<transition name="pop">` 包裹的, Escape 后元素要等离场动画结束才摘除, 期间 `elementFromPoint` 仍命中 `.ctx-menu pop-leave-active` 并**盖在表头上** ⇒ 不等就拖, mousedown 落在菜单上, 拖宽静默不生效(实测 `colW.show` 恒空)。
- 结构自检: 6 个改动 JS `node --check` 通过; `git ls-files --eol` 14 个改动件**全部 `w/lf`**(P0 的行尾坑未复发 —— 本轮每次写完文本文件都扫一遍)。

### 坑与意外

- **行尾事故(已修, 复发 +1, 本轮未再复发)**: 见上一条 P0 段与 [pitfalls/git/editing-traps.md](../pitfalls/git/editing-traps.md)。
- **`dev.harness` 是阻塞桩服务, 不是断言合集**: 见 P0 段。
- **「模板禁 `_`/`$` 前缀标识符」守阵会拦住 `$root`**: 设计组件↔根实例接线时第一版直接在模板里写 `$root.gridStyle(...)`, 全量测试当场红 —— 该守阵(issue 26-10-03-1412)只白名单了 `$event`。**定式**: 该守阵拦的是**用户成员**(data/methods 里的 `_x`/`$x` 被 Vue 排除在组件代理外); Vue **内建**(`$event`/`$root`/`$refs`/`$el`…)在实例上真实存在且模板可解析, 不属同类 ⇒ 按内建白名单放行(而不是改用无前缀别名中转 28 个方法 —— 那反而多一层手抄名单)。
- **收敛会连带改守阵的"计数锚"**: 明细单元格并成一份后, HR 安全档位守阵的 3 处触发面变 2 处。**处置原则 = 同轮补覆盖而不是放宽**: 把「两页共用同一渲染器」钉在 `_scan_column_cells_paired` 与新的表壳守阵里, 计数照改。反之若只改数字不补覆盖, 等于悄悄丢掉"某页漏改"的检出能力。
- **DOM 等价必须逐字节比, 目测/截图不算**: 多根片段(成员单元格)最危险的形态是 Vue 插了锚点节点或多包一层 —— 肉眼看不出来, 只有比子节点骨架才现形(本轮实测差异 0, 说明 Vue 对 `v-for` 根片段不插占位节点)。

### 下一步

- P3: 单元格渲染器收敛(127 条 `v-if` 分支按行模型 `group`/`torrent`/`show-ep`/`member` 归拢; D2=B 保留声明式模板)。**种子页表头本轮未迁移**, P3/P4 一并接入 `<aq-table>` 时把 `test_frontend_table_shell_single_point` 里那条 `.h-cell` 例外删掉。
- P4: 列选择器(`topbar.html` 四段 → 按注册表 `v-for`)/ 横滚同步(三个 `sync*HeadScroll` → 一个; 注意守阵 `test_frontend_frozen_column_boundary_wiring` 钉住三个单点, 收敛必须同轮改守阵)/ 排序键三处重复。
- P5: 设置页 HR 表接入(只借壳, D3=B)。P6: 详情面板只留前向契约(零代码迁移, D4=A)。
- e2e 存量 34 项失败(trigger-scope / multiselect-shows / optimistic / menus)仍只登记未修 —— 范围守恒; 需要时单独入池或并入既有 issue。
