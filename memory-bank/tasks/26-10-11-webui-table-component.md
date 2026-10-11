# 26-10-11-webui-table-component — WEBUI 表格公共组件(辅种表/追剧表抽公共表壳)

**Status:** In Progress
**Added:** 2026-10-11
**Updated:** 2026-10-11
**Summary:** 用户「将种子页列表辅种表和追剧表提取为一个公共模板组件, 支持拖拽换位/拖拽调整宽度/点击排序/右键隐藏, 方便后续重构种子详情页用户列表/文件列表/设置中的各种表; 先写一个计划」→ 计划 [26-10-11-1722-plan-webui-table-component.html](../plans/26-10-11-1722-plan-webui-table-component.html)(topic `webui-table-component`, `Open`)出后, 用户定调「详情面板问题很多, 后续需要完全重构, 不考虑兼容」并按推荐开始实施。**盘点结论改变了落点**: 四项交互的**行为已单点**(`columns.js` 715 行 + `sort.js`), **未单点的是模板**(表头块 5 份 / 单元格 `v-if` 分支 127 条 / 列选择器 4 段 / 横滚同步 3 份 / 页枚举硬编码 18+ 处) ⇒ 本轮重心 = 抽表壳 + 表注册表化, 行为层只在既有单点上参数化。**P0 已落地**(零行为变化): app.js 顶部新增表注册表 `TABLE_DEFS`, `TABLE_PAGES` 由它派生, `columns.js`/`sort.js` 里十处页字面量与 ref 名映射一律改为按 id 取; 新增守阵 `test_frontend_table_registry_single_point` 钉住单点。全量 `test.full` 与上一片基线仅差新增守阵一条(数字见 `commands run kb.baseline`)。P1–P6 待续。
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
| P1 | 抽表壳组件 `<aq-table>`, 先只接辅种表(验收 = 真浏览器 DOM 逐字节等价) | 待做 |
| P2 | 追剧表接入 + 两处成员明细合并; 守阵 `_scan_column_cells_paired` 改扫注册表 | 待做 |
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

### 验证

- `commands run test.full`: 全绿(与上一片基线相比 = 仅新增守阵那一条; 数字见 `commands run kb.baseline`)。
- 前端静态守阵 `test_webui_static_skins.py` + `test_webui_static_dom_page.py` + `test_webui_static_dom_panel.py`: 全绿(含新增 1 条)。
- 真浏览器 e2e `commands run dev.e2e`: **124 passed / 34 failed / 10 skipped** —— 34 项失败经 A/B 证实为**存量**(见「思考过程」末条), P0 未引入新失败。e2e 内的列模型相关 spec(`column-prefs.spec.mjs` 4 场景等)均通过。
- 结构自检: 三个改动文件 `node --check` 通过; `git ls-files --eol` 三文件均 `w/lf`。

### 坑与意外

- **行尾事故(已修, 复发 +1)**: Edit 工具改 `shared/sort.js` 时把整份从 `LF=77 / CRLF=0` 写成全 CRLF(同一批的 `app.js` / `columns.js` 仍是 LF)。`git diff --stat` 只显示改动行, 靠 `git status` 末尾的 `warning: … CRLF will be replaced by LF` 露头。已按字节归一回 LF, 并在 [pitfalls/git/editing-traps.md](../pitfalls/git/editing-traps.md) 该条记 `复发 +1`(为什么没命中: 本轮路由只读了 `pitfalls/web-ui/`, 行尾类条目在 `pitfalls/git/` 未被翻到)。
- **`dev.harness` 是阻塞桩服务, 不是断言合集**: 按计划「真浏览器冒烟」先跑了 `dev.harness`, 6 分钟无输出 —— 读 `scripts/ui_harness.py` 发现它就是起 uvicorn 常驻(超时 900s), 断言在 `dev.e2e`(Playwright 自带 webServer)。**跑前端验证用 `dev.e2e`**; `dev.harness` 只用于手动开浏览器看。
- 计划制品本身无 `src/` 改动(纯文档轮), 其 `doc-topic` = `webui-table-component`, 与本档案 `**Topics:**` 同键, 故 `kb.docmap` 可跨形态串联(未声明 `**Refs:**`, 无 issue 认领链)。

### 下一步

- P1: 抽 Vue 全局组件 `<aq-table>`(D1=A 单适配), 先只接辅种表, 以真浏览器 DOM 逐字节等价比对为验收。
- P1 落地后把 P0/P1 结论迁出 activeContext, 并把 e2e 存量 34 项失败(trigger-scope / multiselect-shows / optimistic / menus)单独入池或并入既有 issue(本轮只登记, 未修 —— 范围守恒)。
- P6 的「前向契约」可先行起草(用户列表 9 列 / 文件列表树与平铺两形态), 待详情面板重构方案立计划时引用。
