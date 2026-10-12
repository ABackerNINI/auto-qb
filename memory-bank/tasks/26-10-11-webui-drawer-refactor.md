# 26-10-11-webui-drawer-refactor — 种子详情面板重构(字符串 DOM 变体 → Vue 面板)

**Status:** In Progress
**Added:** 2026-10-11
**Updated:** 2026-10-12 18:00
**Topics:** webui-drawer-refactor
**Summary:** 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 D1–D4 一律取推荐项 **A**(Vue 3 组件重建 · 收敛为声明式密度变体 · 按页签分波替换 · 三列表注册进 `<aq-table>`)。目标 = 抽屉(种子详情面板)只留**一套渲染技术**: 退役字符串 DOM 设施(`dtHtml` / 变体注册表 / 宿主挂载), 换版式由声明式档位驱动。**W0 已落地**(冻结契约与验收基线, 零代码): 记现状全量数字 + 建「抽屉 DOM dump」临时探针(A/B sha256 判据)。**W1 已落地**(数据层抽离, 零观感变化): 取数 / 竞态 / 等待集合 / 软切换序号从 `shared/drawer.js` 剥成 `shared/drawer_store.js`(`window.AQB_DRAWER_STORE`, 方法体逐字未改只换落点), `app.mixin` 注入 + 三 shell `tpl-manifest` 成对登记; 验收 = 真浏览器 A/B DOM dump **逐字节等价**。**W2 已落地**(四页签 Vue 重建 + 三列表接壳): 用户追加拍板「**全部一起做**」(四页签同波, 不逐页签停)与「**Vue 连变体一起声明式实现**」(变体路线定为声明式, 本体归 W5) —— 四页签正文改由全局组件 `aq-drawer-{general,trackers,peers,content}` 承载(`drawer_pages/*-classic.js` 四件删除), Tracker / 用户 / 文件三表经**独立注册表** `DRAWER_TABLE_DEFS` 并入合壳 `ALL_TABLE_DEFS` 接 `<aq-table>`(拖宽 / 排序 / 右键隐藏**第一次在面板内可用**); 验收 = `test.full` 与基线**逐位一致**(3129/4 skipped) + 新增 `e2e/drawer-tables.spec.mjs` 6 项真浏览器手势(四条新 pin 逐条红验), 数字见基线切片。**W3 已落地**(流量页签与形态收敛, 26-10-12-0009): 用户先拍板「**缺陷留到 W5**」(`esc-attr-quote-dead-class` 不回灌 15 个变体, 随 W5 整体退役消失, 未决项就此了结); 新增 `shared/drawer_head.js` + `tpl/drawer-head.html`(`<aq-drawer-head>` 唯一头部件壳 + `<aq-qb-ctl>` **多根**控件组片段)收掉「两形态各一份头部」复写, 控件组两挂点(traffic 头部 / seed 流量页签 `.qb-statctl`)共用**同一份实现**; `drawer.kind` 形态判据收归 `drawerIsSeed`/`drawerIsTraffic` 两个 computed(全前端字面量仅剩这两处定义, `qb_traffic_chart.js` 谓词按停手点冻结); **有意偏差**: 流量正文留在壳模板不经组件包装 —— 根实例 `$refs` 取不到子组件模板里的 ref, 搬进组件图表会静默不画; 三皮肤 CSS 与 `qb_traffic_chart.js`/uPlot 零改动。验收 = `test.full` 3130 passed(基线 3129 + 新增 1 条守阵)/ 4 skipped + e2e 164 passed 与 W2 基线逐位一致 + 四条红验(RC1 拆双头部 / RC2 包 wrapper / RC3 翻谓词 / RC4 回退 qbCurPending)均 rc=1, 数字见基线切片。**W4 已落地**(合并双列与右键模板选择, 26-10-12-0117): 合并状态(四判据/四方法/两条监听)自 `drawer_templates.js`(插件层)整体收进 `drawer.js`(面板核心**单一状态源**), 合并对常量改列表形态落 `window.AQB_DRAWER_MERGE` 跨文件单点; 合并页签与双列列组改 `dtMergeTabList`/`dtPairCols` 两渲染单点 `v-for` 驱动, 模板不再硬编码 gc/tp 分支(**删「渲染列组 vs 命中」双份判据** —— R2 空列 bug 类永久闭环, `dtMergeTabActive` 随内联判据删除); `_drawerMenuColByX` 复核后**保留**(几何根因与渲染技术无关, 已注结论); 新增「门跨越 / 拉宽自动恢复」真手势 e2e(×2 皮肤)。验收 = `test.full` 3131 passed(HEAD 基线 3130 + W3 的 1 条, W4 零新增; HEAD 在会话间前移已用 worktree 收集清单 diff 对账) + e2e 166 passed(164 + 2) + 四条红验(RC1 高亮脱钩 / RC2 回插分支 / RC3 自建映射 / RC4 监听迁丢)均 rc=1, 数字见基线切片。**W5 已落地**(变体退役与声明式密度档, 26-10-12-0224): 15 个过程式变体(`drawer_tpl/` 15 文件 5739 行)与插件机械(`_dtMount*`/`_dtSync`/`_dtNotify`/`dtHtml` 等)整体删除, 「换版式」收敛为每页签 2 档的密度档(`DRAWER_DENSITY` 一张表: classic/compact, 描述符 `{id,label,cls,raw,hint}`); 旧 id 显式迁移(tall→classic / low·collapsed→compact / 脏值→classic, 读侧一次归一不报错); 结构开关(raw/hint)走 `v-if` 真隐藏; 换档 = Vue 响应式。验收 = `test.full` 3122 passed(worktree 收集清单 diff 逐条闭合: HEAD 3130 + W3 守阵 1 + 本轮 1 − 退役 10) + e2e 156 passed(166 − 退役 14 + 新增 4) + 红验两条均注入即红/还原即绿, 数字见基线切片。**W6 已落地**(收口与退役, 26-10-12-0255, 最后一波): 选择层 `drawer_templates.js` 整文件删除, 余下四件收进 `drawer.js`(密度档单点 / 读侧归一 / 菜单与显隐判据并入 AQB_DRAWER mixin —— app.js 删第二份 mixin 注入); 00-core + 00-density CSS 迁三皮肤(规则逐条未改), `dtInjectCss` 注入单点退役; W3 停手点兑现(`qb_traffic_chart.js` 谓词改吃 `drawerIsTraffic`/`drawerIsSeed`, 全仓 `drawer.kind` 字面量只剩两个定义处); 三份坑档加退役注。验收 = `test.full` 3122 passed + 4 skipped(与 W5 逐位同, 零测试增删) + e2e 156 passed + 红验两条(RC1 迁移错 / RC2 皮肤 CSS 缺失)均注入即红/还原即绿。**终态判据达成: 抽屉只剩一套渲染技术**; 计划 doc-status → Done。
**Refs:** memory-bank/reports/26-10-12-0455-report-webui-drawer-table-unification-audit.html,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-12-0255-webui-drawer-refactor-w6.md,memory-bank/testing/baselines/26-10-12-0224-webui-drawer-refactor-w5.md,memory-bank/testing/baselines/26-10-12-0117-webui-drawer-refactor-w4.md,memory-bank/testing/baselines/26-10-12-0009-webui-drawer-refactor-w3.md,memory-bank/testing/baselines/26-10-11-2259-webui-drawer-refactor-w2.md,memory-bank/testing/baselines/26-10-11-2136-webui-drawer-refactor-w0w1.md,memory-bank/activeContext/26-10-12-0255-webui-drawer-refactor.md,memory-bank/activeContext/26-10-12-0224-webui-drawer-refactor.md,memory-bank/activeContext/26-10-12-0117-webui-drawer-refactor.md,memory-bank/activeContext/26-10-12-0009-webui-drawer-refactor.md,memory-bank/pitfalls/web-ui/frontend-split.md,memory-bank/pitfalls/web-ui/esc-attr-quote-dead-class.md

## 原始请求

> 用户(2026-10-11): 「按推荐实施:26-10-11-2106-plan-webui-drawer-refactor.html」

- 计划于同日另立专题: 表组件计划 `26-10-11-1722` §05 P6「详情面板只留前向契约」处, 用户定调「详情面板问题很多, 后续需要完全重构, 不考虑兼容」, 故把详情面板独立成专题实施。
- 「按推荐实施」= 计划 §09 四个拍板点一律取推荐项 **A**(见「思考过程与决策」)。

## 思考过程与决策

- **拍板点(D1–D4)取推荐项 A**: D1 渲染模型 = Vue 3 组件重建(不保留字符串 DOM 拼串); D2 变体去留 = 收敛为**声明式密度变体**(每页签 2–3 档); D3 切换策略 = **按页签分波**, 旧抽屉当 A/B 基线逐页签替换; D4 列表接入 = Tracker / 用户 / 文件三列表注册进 `<aq-table>`。
- **分波而非一次性替换(计划 R7)**: W0–W6 七步, 双实现期必须「单一挂载点 + 特性开关」, 旧渲染当基线逐页签替换 —— 保证每一步都有可比对的 A/B 面。
- **验收口径 = 逐字节等价**: 项目既有判据(表组件计划同口径)是「真浏览器 A/B DOM dump 归一后取 sha256 相同」。W1 是纯搬迁, 故要求两侧哈希**逐字节相同**(不是"视觉近似")。
- **搬迁的硬约束来自 `_scan_mixin_wiring`**: 新 mixin 成员名与其它片段不得重名(Vue mixin 后者静默覆盖前者, 不报错)⇒ W1 采用「同类成员整体搬家、原文件不再定义」, 不复制任何方法体。
- **守阵读取面必须与代码同轮改(R8)**: 十余条静态守阵按文件名定位方法体, 搬迁不改测试会整批「找不到方法体」判红; 改法是**只换读取文件、断言口径一字不动**(不放宽)。
- **行数硬顶**: `prism/index.html` / `console/index.html` 贴在 shell 行数硬顶, 加一行 manifest 必须腾一行 ⇒ 压相邻两条 `parts` 项到同一行(JSON 空白不被解析, `json.loads` 后清单不变)。

## 实现计划

计划见 [plans/26-10-11-2106](../plans/26-10-11-2106-plan-webui-drawer-refactor.html) §05(W0–W6)与 §10(验收)。本档案只记执行与验证。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| W0 | 冻结契约与验收基线(零代码): 现状全量数字 + DOM dump 临时探针 | **Done** |
| W1 | 数据层抽离(零观感变化): `drawer.js` → `drawer_store.js` | **Done** |
| W2 | 四页签 Vue 重建 + 三列表注册进 `<aq-table>` | **Done** |
| W3 | 流量页签 + 表单收敛 | **Done** |
| W4 | 合并双列 + 右键模板选择 | **Done** |
| W5 | 声明式密度变体(D2) | **Done** |
| W6 | 退役第二套渲染技术(终态) | **Done** |

## 进度日志

### 2026-10-11 · W0 冻结基线(零代码)

- 跑 `test.full` 与全量 e2e 记现状, 新建基线切片 `testing/baselines/26-10-11-2136-webui-drawer-refactor-w0w1.md`(数字的唯一事实源)。
- 点名的五支 spec 单独复核(合计与静态枚举逐支对齐), 数字见基线切片。
- 建「抽屉 DOM dump」临时探针: 打开种子详情 → 四页签(Tracker/用户/内容/常规)+ 回常规, 取 `.drawer-dock` `innerHTML`, 归一 40 位 hash / 大小速度单位 / 时长 / 时刻 等易变位; 双皮肤各 5 项 = 10 项。收口把探针移出 `e2e/`(留 `tmp-analysis/` 备复用), 不影响 e2e 用例计数。

### 2026-10-11 · W1 数据层抽离(零观感变化)

- 新增 `shared/drawer_store.js`(`window.AQB_DRAWER_STORE.methods`): `_fetchDrawerDetail|Trackers|Files|Peers` · `_drawerLoadSeq`/`_drawerStale` · `_drawerWait`/`_drawerWaitSources`/`_drawerDone` · `_drawerBusyArm|Disarm`/`_drawerSwitchEnd` · `_loadDrawerTab` · `_switchDrawerTarget` · `_startDrawerPoll`/`_stopDrawerPoll` · `_drawerMergeSupply` · `_drawerNormPeers`。头注记所有权契约(数据 / 行为层 vs 渲染层)与跨模块登记配对纪律。
- `shared/drawer.js`(1435 → 1169 行)删除这些定义, 只余调用点(几何 / 键盘跟随 / 编辑对话框 / 行派生)。
- `shared/app.js` 加 `app.mixin(window.AQB_DRAWER_STORE)`; 三 shell `tpl-manifest` 各加一行 `/shared/drawer_store.js`(排在 `drawer.js` 之前; prism/console 压相邻 `parts` 项腾行)。
- 守阵读取面同轮改: `test_web_shortcuts.py` 三处 + `test_webui_static_dom_panel.py` 五处(只换读 `drawer_store.js`, 断言口径不变); 首轮漏改两条(tpl a11y fetch 错误态 / groups-shows 轮询)补齐后转绿。
- 验收: 真浏览器 A/B DOM dump sha256 相同 + 全量 `test.full`/e2e 与基线逐位一致(数字见基线切片)。
- 文档回写: `modules/webui-static-contract.md` 加「抽屉数据/行为层落点 `drawer_store.js`」条。

### 2026-10-11 · W2 四页签 Vue 重建 + 三列表接壳

- **拍板补充(用户问答)**: ① 变体处理 = 「**Vue 连变体一起声明式实现**」(变体本体仍归 W5, 此处只定路线); ② 首波页签 = 「**全部一起做**」(四页签同波, 不逐页签停手); ③ 接壳形态 = 「**div 网格, 与主视图完全同源**」; ④ 观感边界 = 「以『与主视图一致』为准则, **观感变化整体接受**」。
- **四页签转组件**: 新增 `shared/drawer_tabs.js`(`AQ_DRAWER_{GENERAL,TRACKERS,PEERS,CONTENT}_COMPONENT`, 只贡献模板 + 最小实例态, 数据/动作全走 `$root` 回调)与 `shared/tpl/drawer-tabs.html`; `tpl/drawer.html` 的 `dt-host` 骨架改成 `v-if="dtVueTab(tab)"` 组件 / `v-else` 旧宿主**互斥**; `drawer_pages/{general,trackers,peers,content}-classic.js` 四件删除。
- **三表接壳**: `app.js` 加三个列模型常量(`DRAWER_{TRACKER,PEER,FILE}_COLUMNS`)+ **独立注册表** `DRAWER_TABLE_DEFS` + 合壳 `ALL_TABLE_DEFS`/`ALL_TABLE_PAGES`(`TABLE_DEFS`/`TABLE_PAGES` 语义零改); 四处逐表遍历改吃新壳。`table.js` + `tpl/xtpl-cells.html` 加三个行模型渲染器(`aq-{tracker,peer,file}-cells`, 单元格是网格行**直接子元素**)。`columns.js` 的 `_headEl` 补 DOM 兜底, 五个遍历点与 `tableDefs` 改吃新壳; `sort.js` 的 `_sortKeys(scope)` 改成「scope 即表 id」+ `sortedDrawer`/`_sortVal`; `state.js` 加六个排序字段。三皮肤 CSS 成对(抽屉作用域 `position:static` / 行态类 / 省略号)。
- **修掉的真 bug**: 表头右键连带弹模板菜单(两个 `.ctx-menu` 同屏)⇒ 表头改 `@contextmenu.prevent.stop`。
- **测试面**: 新增 `e2e/drawer-tables.spec.mjs`(3 用例 × 2 皮肤): ① 拖宽 / 排序 / 右键隐藏 / 列偏好持久化 / 列选择器恢复; ② 面板开着**行键盘仍可用 + 面板跟随**(W2 验收第四件); ③ 单栏正文右键弹**当前页签**模板集 + 变体/经典**单一挂载点**。四支既有 spec 同轮改锚点(`drawer-peers` / `drawer-merge` 从 `table.drawer-table tbody tr` 改到 `.group-row[data-table=…]`)。四条新 pin 逐条**红验**(注入回归 → rc=1)。
- **守阵同轮改版(R8, 不放宽)**: `test_frontend_table_shell_single_point`(组件面 9 项 / xtpl-cells 7 模板 / 抽屉三处调用点)、`test_frontend_table_registry_single_point`(新增 W2 块: `DRAWER_TABLE_DEFS` 形状 + 抽屉 id 不在 `TABLE_DEFS` 体内 + `TABLE_PAGES`/`ALL_TABLE_PAGES` 并存 + 四条接线 pin)、`test_web_shortcuts` / `test_webui_static_dom_panel`。
- **验收**: `test.full` 3129 passed / 4 skipped, `TOTAL 16517 151 5626 134 99%` —— 与 W0/W1 基线**逐位相同**; 全量 e2e 见新基线切片 `testing/baselines/26-10-11-2259-webui-drawer-refactor-w2.md`。
- **文档回写**: 计划 §05 进度注 + W2「落地」条(含两处有意偏差与观感变化逐项) + §07 落地偏差注 + §11 变更记录; `modules/webui-static-contract.md` 新增「抽屉三列表接入公共表壳」条并修正「抽屉 3 表无列模型」的**陈旧口径**; 坑档 `pitfalls/web-ui/esc-attr-quote-dead-class.md`(旧实现条件属性拼进 `dtHtml` 插值 ⇒ 类名带引号 ⇒ `.virtual/.skipped/.sel` 规则全线静默失效)。

### 2026-10-12 · W3 流量页签与形态收敛

- **拍板(用户)**: 「缺陷留到 W5」—— `esc-attr-quote-dead-class` 不回灌 15 个变体, 随 W5 整体退役时一并消失(坑档维持「不许静默修」, W5 前该缺陷是**已知态**); 随后「继续 W3」。
- **头部复写收敛**: 新增 `shared/drawer_head.js`(`AQ_DRAWER_HEAD_COMPONENT` 带 props: tone/icon/text/textTitle/statusTitle, textTitle/statusTitle 缺省 `null` 避免流量形态凭空长出 title 属性被 ui_feedback 迁成 data-aq-tip) + `shared/tpl/drawer-head.html`(`<aq-drawer-head>` = 标题块 + 默认 slot + 关闭钮的唯一头部壳; `<aq-qb-ctl>` = 档位 + 纵轴控件组)。`tpl/drawer.html` 两段 `<header class="drawer-head">` 复写换成 `v-if="drawerIsTraffic"` / `v-else` 两行调用; seed「流量」页签 `.qb-statctl` 挂点同接 `<aq-qb-ctl>` —— 控件组从「两份 byte 级相同实现」变「一份实现 + 两个挂点」。三 shell manifest 成对登记(prism/console 压相邻 parts 项腾行, 208/204/208 行)。
- **两个实现要点**: ① `<aq-qb-ctl>` 必须**多根片段**(`.qb-tabs`/`.qb-tools` 兄弟根) —— 三皮肤 `.drawer-head > .qb-tabs/.qb-tools` 与 `.qb-statctl > .qb-tabs/.qb-tools` 四组规则全是直接子选择器, 包 wrapper 即静默失效; ② **流量正文留在壳模板**(计划「薄包装」的有意偏差) —— `_qbChartBuild` 经根实例 `$refs["qbChartHost"]` 取挂载点, Vue 只在声明 ref 的实例登记 `$refs`, 子组件模板里的 ref 到不了根实例 ⇒ 搬进组件图表静默不画(与 W2 `_headEl` 兜底同病灶族)。
- **形态判据收口**: `drawer.js` 新增 `drawerIsSeed`/`drawerIsTraffic`/`drawerMember`/`drawerMemberKind` 四个 computed; 调用点同轮换(`openTorrentDrawer` / `drawerAfterEnterHook` / `dtMenuMergeOn` / `openDrawerMenu` / `_kbDrawerTab` / `_kbOpenDrawer` / `_kbToggleQbTraffic` / drawer.html 三形态分支)。全前端 `drawer.kind` 字面量仅剩两个谓词定义, `qb_traffic_chart.js` 的 `active/stale` 谓词按 W3 停手点冻结豁免。
- **守阵同轮改版(不放宽)**: `test_webui_static_dom_panel.py` 六条用例的 pin 从旧双 header 结构移到新组件/新谓词(含 `qbSetYAxisMode` 面板零拷贝、`v-for` 带 `$root.` 前缀、关闭钮归 head_tpl、`<aq-drawer-head>` 行锚计数), 旧「两处控件组逐字同源」块换成**更强的单点钉法**(单一实现 + 面板零拷贝 + 恰两挂点)并新增**结构级判根** `_tpl_top_level_tags`(HTML 解析 depth-0 根元素, 钉 `<aq-qb-ctl>` 多根 —— 类名 count 钉不住 wrapper 回潮, 红验证实); 新增 `test_frontend_drawer_form_judge_single_point`(钉谓词原文 + 各文件出现数)。`test_web_shortcuts.py` 七处 pin 同轮换(`drawerIsSeed`/`drawerIsTraffic`/head_tpl 关闭钮/头部标题走组件 props)。
- **红验四条(均 rc=1 非退化)**: RC1 把头部拆回两份 → 3 条守阵红; RC2 给 `<aq-qb-ctl>` 包 wrapper → 结构判根红(类名 count 全绿, 证明只有结构钉得住); RC3 翻 `drawerIsSeed` 谓词比较 → 谓词原文钉红; RC4 `qbCurPending` 回退两段版 → 红。
- **验收**: `test.full` = 3130 passed / 4 skipped, `TOTAL 16517 151 5626 134 99%`(基线 3129 + 本轮新增 1 条守阵用例); 全量 e2e = 164 passed + 0 failed + 10 skipped 与 W2 基线**逐位一致**(W3 验收口径是守阵, 未加 e2e 用例); 三皮肤 CSS 与 `qb_traffic_chart.js`/uPlot **零改动**。数字见新基线切片 `testing/baselines/26-10-12-0009-webui-drawer-refactor-w3.md`。
- **文档回写**: 计划 §05 进度注 + W3「落地」条(含两处取舍与宿主留壳偏差) + 头部 Status + §11 变更记录; `modules/webui-static-contract.md` 新增「抽屉头部件与形态判据」条; 本切片 + activeContext 新切片。

### 2026-10-12 · W4 合并双列与右键模板选择

- **单一状态源**: 合并状态(四判据 `dtMergeOn/dtMergeTabsOn/dtPair/dtSplitOn` + 四方法 `_dtPairOf/dtMergeGateOk/dtToggleMerge/dtMergeTabPick` + 两条监听: resize 防抖回写 `dtWinW` 与 `drawerMerge` $watch)自 `drawer_templates.js`(插件/变体层)整体迁 `drawer.js`(面板核心) —— 合并是**抽屉级布局状态**不属插件层; W5/W6 退役注册表文件时合并不再陪葬。合并对常量改**列表形态**(`[{ id, label, tabs }]`)落 `window.AQB_DRAWER_MERGE` 跨文件单点(赋值形态同 `AQB_DRAWER_TPL_REG` 先建局部量再赋 window, 避开 mixin 接线守阵的字面量识别 —— 它不是 mixin)。
- **删「渲染列组 vs 命中」双份判据**: 合并页签按钮(`dtMergeTabList` v-for)与双列列组(`dtPairCols` v-for, general 列经 props 传详情)由同一份对数据驱动, `tpl/drawer.html` 不再硬编码 gc/tp 两分支/两按钮/标签; `dtMergeTabActive` 方法随内联 `mt.id === dtPair` 删除(高亮与列组同源)。`_dtMountSplit` 改吃 `AQB_DRAWER_MERGE.pairOf`, 插件层零自建映射。
- **_drawerMenuColByX 复核 = 保留**: `align-items:start` + 封顶 2400 + 24px gap 三条几何事实与列渲染技术无关, 短列下方/间隙/两侧留白照旧不落在 `.dt-col` 上; 退役 = R6「右侧空白右键弹左列」复发(menu.js 注 W4 结论, e2e 用例④守着)。
- **e2e 补强**: 新增「门跨越 / 拉宽自动恢复」用例(×2 皮肤): 预置 `drawerMerge=on` → 1280 开面板无合并 → 拉宽 2560 双列自动恢复 + 第二列数据补给 → 缩回回落 → 再拉宽直接恢复。钉住两条监听随迁的行为面(计划 W4 验收动词「拉宽自动恢复」此前无覆盖)。
- **守阵同轮改版(不放宽)**: `test_drawer_tpl_registry_wiring` 合并钉块整体改版(成员清单移 drawer.js / `dtMergeTabActive`·硬编码分支·`MERGE_PAIRS` 残留三组负 pin / 监听**注册形态** pin / 对单点消费 pin / 标签随对数据走); `test_webui_error_history` setItem 基线随落盘落点迁移(drawer.js 3→4 / drawer_templates.js 2→1)。
- **红验四条(均 rc=1 非退化)**: RC1 高亮脱钩(改回硬编码 gc)/ RC2 回插硬编码列组分支 / RC3 插件层自建映射 / RC4 监听迁丢。⚠ RC1/RC4 首轮被**退化钉**放过: 裸字符串 pin 分别被说明性注释(`mt.id === dtPair` 出现在注释里)与声明/摘除处(`_mergeOnResize` 名字仍在)喂饱 —— 同轮改**代码形态锚定**(`:class="{...}"` 表达式 / `addEventListener` 注册行)后重验全红。教训入库: 给注释丰富的文件写 pin 必须锚代码形态。
- **对账(HEAD 前移)**: `test.full` 3131 passed 引发 +1 疑问, 经临时 worktree 收集清单 diff 逐条核实: HEAD `acd0e26f` 基线 = 3130(W2 会话后另有会话提交 +1 用例), 工作树 = 3130 + W3 的 1 条 + W4 零新增 —— 账目吻合, 覆盖率四项逐位不变(`TOTAL 16517 151 5626 134 99%`)。
- **验收**: `test.full` = 3131 passed / 4 skipped; 全量 e2e = 166 passed / 0 failed / 10 skipped(164 + 本轮 2); 四条既有合并 e2e 全绿。数字见新基线切片 `testing/baselines/26-10-12-0117-webui-drawer-refactor-w4.md`。
- **文档回写**: 计划 §05 进度注 + W4「落地」条 + Status + §11; `modules/webui-static-contract.md` 新增「页签合并收进面板核心」条; 本切片 + activeContext 新切片。


### 2026-10-12 · W5 变体退役与声明式密度档

- **声明式密度档(D2 拍板 A 落地形态)**: `drawer_templates.js`(624→约 250 行)收敛为「选择层」—— `DRAWER_DENSITY` 每页签 `{ tiers: ["classic","compact"], legacy: {...} }` + `DD_TIERS` 描述符(`{id,label,cls,raw,hint}`; classic = 经典重建版式, compact = 紧凑密度)+ `window.AQB_DRAWER_DENSITY`(options/tierOf/normalize 三 API)+ `dtInjectCss("00-density")` 密度 CSS 三条。读侧 `readSel` 走 normalize: **旧 id 显式迁移**(tall 01/04/07/10/13→classic、low/collapsed 其余十枚→compact、白名单外脏值→classic, P-01 口径不报错)。
- **退役面**: `shared/drawer_tpl/` 目录(15 文件 5739 行)删除; 三份 index.html 变体 manifest 各删 15 行; 插件机械(`_dtMount*`/`_dtSync`/`_dtNotify`/`_dtRender`/`dtHtml`/`dtRaw`/KIT/HELPERS)全删 —— `drawer.js` 删 `_dtSync`(resize/merge $watch)与 `_dtUnmountAll`, `drawer_store.js` 删 4 处 `_dtNotify`, `state.js` drawerVisible watcher 种子支路 `if (!s) return;`, `menu.js` 删 `data-dt-host` 分支(`_drawerMenuColByX` 按 W4 复核结论保留); `drawer.html`/`drawer-tabs.html` 删宿主与 v-if/v-else 双分支。**换档 = `drawerTplSel[tab]` 赋值 + Vue 响应式**(无通知/无重挂 —— fetcher 落袋通知与回页补挂机制随之退役)。
- **描述符消费**: 四页签组件根与 `.dt-traffic-main` 挂 `drawerTier(tab).cls`(`dd-compact`); 结构开关 `raw`(general `details.drawer-raw`)/`hint`(content `.drawer-toolbar-hint`)走模板 `v-if` **真隐藏**(计划 §08 R7, 不是 CSS 藏)。
- **守阵同轮改版(不放宽, 收集 45→27)**: 删 10 条变体专用守阵; `test_drawer_tpl_registry_wiring` 改密度档接线钉(manifest 装载序 / 三 API / 迁移映射齐 15 / 组件描述符消费 / W4 合并面原样 / dt* 无重名); 新增 `test_drawer_tpl_facility_retired`(**退役确认阵, 活代码形态锚定**防「不得复活」)与 `_DT_DENSITY_NODE_PROBE`(node 电池: normalize 迁移 / readSel 脏值 / dtMenuPick 白名单 / drawerTier 结构开关); 七份守阵文件变体读取面同轮改(a11y 失败标记 / reannounce torrentCmd 兜底 / 右键菜单无插件机械 + data-dt-host 不得残留 / page_guard / traffic 切片锚 / removed_redundant_tooltips 等)。收口轮 154 passed + 2 skipped。
- **红验两条(注入即红 / 还原即绿)**: RC1 迁移去向错(legacy `"01"`→compact → node 电池「旧 tall id → classic」两条红); RC2 结构开关失效(`compact.raw`→true → wiring + node 电池双红)。⚠ **流程教训: 红验注入与 dev.e2e 长跑不得并行** —— 首轮全量 e2e 的 2 条失败是注入窗口撞车(RC2 注入期间 e2e 读到 raw:true), 表现与真缺陷一致; 还原重跑全绿(156 passed)。
- **e2e**: 新增 `drawer-density.spec.mjs`(① 旧 id 混预置〔01/06/zz/10〕→ DOM 逐页签断言档位 + 零报错, traffic 腿因 `qbTrafficOn` 门控不在桩内由 node 电池承接; ② 右键切紧凑 → 落盘不牵连 content → 刷新恢复 → 经典回切); `drawer-merge` 用例⑤改密度档(紧凑/经典 + `dd-compact` + 结构开关断言, 右列空白归列回归保留); `drawer-tables` 用例③改**效果判别**(选紧凑须落 trackers 记忆 + 插件宿主负 pin —— 选项集同名后排除断言失效, 菜单归属只能看落谁的账); 4 条变体专用 spec 退役(dt11-sticky / peers-columns / sticky-flush / trackers-reannounce, 7 用例 × 2 皮肤 = 14 执行, 经 `--list` 实数对账)。
- **验收**: `test.full` = **3122 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`(worktree 收集清单 diff 逐条闭合: HEAD `acd0e26f` 3134 收集 = 3130 passed + W3 未提交守阵 1 + 本轮新增 1 − 退役 10 = 3126 = 3122 + 4 ✓); 全量 e2e = **156 passed + 0 failed + 10 skipped**(166 − 14 + 4 ✓)。W5 验收三条全达成: 每页签档位切换生效并持久化 / 旧 id 不报错有去向 / 停手点守住。数字见基线切片 `testing/baselines/26-10-12-0224-webui-drawer-refactor-w5.md`。
- **文档回写**: 计划 Status + W5 tag + §11; `modules/webui-static-contract.md` 新增「变体退役与声明式密度档」条; 坑档 `sticky-scrollpad-inset.md` / `esc-attr-quote-dead-class.md` 加退役注(缺陷面随变体消失, 机理入库); 本切片 + activeContext 新切片。

### 2026-10-12 · W6 收口与退役(终态)

- **选择层收编**: `drawer_templates.js` 整文件删除; `drawer.js` 新增「模板选择层」段 —— `window.AQB_DRAWER_DENSITY`(DTPL_TIERS/DTPL_DENSITY/options·tierOf·normalize, 先建局部量再赋 window 防 mixin 误判)+ `window.AQB_DRAWER_TPL_REG`(readSel 白名单 + 旧 id 迁移)+ 四 computed(dtMenuTab/dtMenuTplOptions/dtMenuTplCurrent/dtMenuMergeOn)与五 methods(_dtCurTab/dtHostOn/drawerTier/dtMenuPick/dtPersistSel)**并入 AQB_DRAWER mixin 本体**。app.js 删 `app.mixin(window.AQB_DRAWER_TPL)` 第二份注入; 装载序硬约束改 drawer.js < state.js(state data() 调 initialDrawerTpl 依赖 AQB_DRAWER_TPL_REG)。
- **CSS 迁三皮肤(规则逐条未改)**: 00-core 合并 CSS(`.drawer-split`/`.dt-col`/`.dt-col-head`/`.dt-host:empty`/`.dt-traffic-main`)与 00-density 密度 CSS(`.dd-compact` 族)迁三皮肤 views.css; `.ctx-menu .ctx-item.is-gated` 迁 components.css; `dtInjectCss` 注入单点退役。⚠ atlas components.css 贴 700 行单文件上限 —— 迁移注释压行尾、两条规则并一行, 净增 2 行贴线过闸(腾行手法同 pitfalls/frontend-split)。
- **W3 停手点兑现**: `qb_traffic_chart.js` 的 `_QB_SCOPES` 三挂点 active/stale、`qbCurScope`、`openDrawerTraffic` 同目标短路全部改吃 `drawerIsTraffic`/`drawerIsSeed` 单点 —— 全仓 `drawer.kind` 字面量只剩 drawer.js 两个定义处。
- **守阵同轮改版(不放宽, panel 收集 28)**: `test_drawer_tpl_registry_wiring`(文件级退役 + manifest 反转 + drawer.js < state.js 序 + 皮肤聚合 CSS 成对断言 + 成员锚换家缩进 6→4 + mixin 注入负 pin + dtInjectCss 负 pin)、`test_drawer_tpl_facility_retired`(注入活代码负 pin 改锚 drawer.js + space-between/.dt-select 禁令改锚皮肤密度段)、`test_drawer_tpl_menu_right_click_selection`/`test_drawer_tpl_classic_default`(node 电池加载 drawer.js, `window.AQB_DRAWER.methods`)、`test_frontend_drawer_form_judge_single_point`(摘 W3 豁免改钉四件, 图表模块调用面逐个计数)、`test_frontend_qb_traffic_drawer_page_guard`(短路改单点形态)、`test_webui_error_history`(写入基线 drawer.js 4→5: dtPersistSel 写入点随迁移合并, 行内注明合法演化)。
- **坑档收口**: `variant-singleton-shadow` / `vif-host-node-stale` / `drawer-switch-flicker` 加退役注 —— 缺陷面(变体文件/helpers 单点/插件重挂)随退役消失, 机理与不变式入库; 软切换协议与 uPlot 宿主纪律仍现役、对应守阵仍活, 逐档注明。
- **红验两条(注入即红 / 还原即绿)**: RC1 迁移去向错(legacy `"01"`→compact → node 电池「旧 tall id→classic」两断言红); RC2 皮肤 CSS 缺失(删 console `.drawer-split` 规则 → wiring「皮肤聚合 CSS 缺规则」红)。
- **验收**: `test.full` = **3122 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`(与 W5 基线逐位相同 —— 本波零测试增删, 唯一测试面变更 = 写入基线合法演化更新); 全量 e2e = **156 passed + 10 skipped**(与 W5 基线一致 —— 本波只换实现落点不换行为, 无新增 spec)。**终态判据达成: 抽屉只剩一套渲染技术**; 坑档守阵零悬空。数字见基线切片 `testing/baselines/26-10-12-0255-webui-drawer-refactor-w6.md`。
- **文档回写**: 计划 Status → Done(doc-status meta + footer)、§05 进度注、W6 tag、§11 W6 落地条; `modules/webui-static-contract.md` 新增「选择层退役与终态」条; 三坑档退役注; 本切片 + activeContext 新切片(26-10-12-0255)。

### 2026-10-12 · W7 恢复波(修正波: W5/W6 退役裁定越权, 模板原样找回)

- **用户裁定(本轮执行依据)**: 本计划目标 = 「更改详情模板中的表格, 将其与主表能力统一, 减少维护点」= **W2 接壳**, 从未授权动模板 —— W5(变体退役)/W6(选择层退役)属计划越权, 一并撤销; 指令「全部模板原样找回」。W2–W4 成果(三列表接表壳 / 形态判据单点 / 合并机械收 drawer.js)全部保留。
- **考古恢复法**: W2–W6 一锅进 0d07dbdd, W4 期中间态被 W5 重写不可考 —— 恢复基座 = `a05d35da`(W2 前最后形态), 增量按任务档案 W1–W4 日志重放(W1 拆数据层未动模板层 / W2 经典转 Vue 组件 / W3 形态判据单点 / W4 合并机械收 drawer.js)。
- **恢复面**: `drawer_tpl/` 15 文件 `git checkout a05d35da --` 原样恢复; `drawer_templates.js` 从基座(导出 tmp-analysis/dtpl_base.js)做 12 处精确变换重建(555 行, node --check 过), 头注记四条有意适配(① 合并机械住 drawer.js / ② classic=Vue 组件 dtVueTab 双分支 / ③ 00-core 注入只余 .dt-tpl 限宽 / ④ dtMenuPick $nextTick 后 _dtSync); 接线恢复 drawer.js(密度层删+菜单面删+双监听+closeDrawer 卸载)/menu.js(宿主优先分支)/state.js(种子支路 $nextTick)/drawer_store.js(四 _dtNotify)/app.js(第二份 mixin)/三 index(16 装载行)/三皮肤 views.css(.dd-compact 删)。W6 保留项: qb_traffic_chart 吃判据单点、合并布局 CSS 在三皮肤。
- **守阵同轮改版(不放宽)**: panel 六删(W6 版 wiring/facility_retired/a11y/menu_right_click/classic_default/密度电池) + 基座 16 块恢复 + W2–W4 事实适配(menu 放行判据 / close 钮在 aq-drawer-head / page_guard 种子支路 / form_judge 缩进计数 / wiring 钩子段读 drawer_store.js + :data-dt-tab 动态绑定单点 + pairOf 机械消费合法 / reannounce ④ 变体断言面与 tooltip I 组条目回归), 37 全绿; error_history 写入基线回改 drawer.js 5→4、drawer_templates.js 新增 1。
- **e2e 恢复**: 删 drawer-density.spec.mjs; 4 条变体 spec 基座恢复; drawer-merge/drawer-tables 反向 W5 编辑, 锚点按恢复语义改(经典态宿主 v-else 不渲染 → toHaveCount(0))。
- **重建漏项(e2e 抓到)**: dtMenuPick 同步 _dtSync 在双分支下扑空(旧分支在 DOM、新宿主未插入, _dtFindHost 查不到 → 挂载静默失败, general 无轮询永不挂) —— 补 $nextTick(适配④), 4 条失败全复绿。首轮 e2e 另 1 条 trigger-scope 为时序 flaky, 单跑复绿。
- **红验两条(注入即红 / 还原即绿)**: RC1 静态 —— dtPersistSel 落盘短路 → error_history 基线 + classic_default + render_error_fallback 三红; RC2 e2e —— 变体 06 register id 破坏 → drawer-tables 锚点解析两皮肤红。
- **验收**: `test.full` = **3131 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`(W6 3122 → +9: facility_retired 退役, 基座变体守阵九函数回归); 全量 e2e = **166 passed + 10 skipped**(W6 156 → +10 = 恢复变体 spec 用例 × 皮肤)。数字见基线切片 `testing/baselines/26-10-12-0340-webui-drawer-refactor-w7.md`。
- **文档回写**: 计划 §05 进度注 + §11 W7 条; `modules/webui-static-contract.md` 修正条; 本切片 + activeContext 新切片(26-10-12-0340)。
- **缺陷复核(用户指令「修复缺陷」)**: `esc-attr-quote-dead-class` 随变体恢复重新存在的**遗留判定不成立** —— 实证两件: ① 静态全扫描(15 变体 + drawer_templates.js 全部字符串字面量与全部模板插值)零「整段属性进 esc 插值」形态, 变体条件类全走正确形态(`class="x${cond ? " y" : ""}"`), 命中引号字面量全是 CSS 串/选择器构建/KIT 直拼(不经 esc); ② 新增运行时守阵 `e2e/lib/dt-dead-class.mjs`(`expectNoDeadClass` 渲染后全文档 class 值零引号), 钉 drawer-tables(经典+变体 06)/drawer-merge(经典+变体 01+10)五处, 注入坏形态两皮肤即红、还原即绿。**判定: 缺陷不存在, 无需修码** —— W2 时「15 个变体仍带同一缺陷」是未枚举的悲观外推, 真实点位只有 W2 已删的旧经典页。坑档加 W7 复核注; 该遗留就此关闭。

### 2026-10-12 · 表格统一 U0/U1 (计划 26-10-12-0527, 用户拍板 D1–D6 全推荐项)

- **U0 冻结+契约交付**: P6 契约全文落 `shared/table.js` 头注「对外契约(P6)」节(描述符/表壳/渲染器/锚约定/checklist); 1722 档案 P6 状态 待做→已交付; 「变体表格 8 份手搓」债务入账模块文档; 基线切片 26-10-12-0540(test.full 3131+4 / e2e 166+10, 与 W7 逐位相同 = 零行为变化证据)。
- **U1 引擎 spike(硬闸门通过)**: ① 列子集声明(TABLE_COLUMNS + 描述符行); ② 排序 dyn 泛化(sort.js `_sortKeys`/`setSort`/`_resetSort`/`sortedDrawer` 四处 dyn 分支 + `dtSortCell` 取数口, 变体表不再需要 state.js 排序字段); ③ Teleport 桥 = `aq-dt-bridge` 组件(xtpl 分片) + 挂载机械锚代数(`dtBridge: {gen, on}`) + drawer.html 两挂点(单栏 v-for + 合并列) + stub 变体 90(?dtstub 门) + 列选择器变体过滤(`tableDefs` 按 variantTab 反查, 恢复入口不变式保持)。
- **e2e 实测抓到两个关键缺陷(探针定位)**: ① 桥行漏套 `sortedDrawer`——行序不随列头; ② 锚代数回落(卸载清零→再挂回 1, :key 净零)→ Vue 原地补丁把 Teleport 内容写进**游离旧锚**, 软切换后桥静默"消失"。修法: gen 单调自增 + on 摘除。两处均入守阵(`test_drawer_table_bridge_wiring` 九段接线 pin)。
- **验收**: stub 四路径 e2e 10 passed(双皮肤; 手势三件套: 排序/拖宽落盘/右键隐藏落盘 + 刷新双偏好回放); 红验: gen 恒定注入→路径C 两皮肤红→还原绿; 主视图零改动。
- **数字**: `test.full` 3132 passed + 4 skipped(+1 桥守阵); 全量 e2e 176 passed + 10 skipped(+10 桥验证 spec); 基线切片 26-10-12-0641。

**Refs:** memory-bank/reports/26-10-12-0455-report-webui-drawer-table-unification-audit.html,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html

### 2026-10-12 · 表格统一偏差审计 (重审计划的前置输入)

- **触发(用户)**: 「计划偏差太大, 重新审视计划, 我需要的是所有表格统一, 提供类似的交互逻辑, 减少维护点, 先写一个审计报告, 偏差了哪些」——重审 26-10-11-2106 的目标函数: 从「一套渲染技术」修正为「所有表格统一 × 交互逻辑同源 × 维护点下降」。
- **审计结论(联合口径, 含前计划 1722)**: 偏差是一条两计划链条 —— 1722(表格公共组件)在 A+C 系统正主完成(主视图 4 表 + HR 3 表进引擎, P0–P5 落地), 但 P6 前向契约悬置未交付、条件性 DOM 适配被 W7 恢复变体后静默激活; 2106 承接抽屉重构时把目标函数从「表格统一」换成「一套渲染技术」(P0 前提偏差), 且「不考虑兼容 ≠ 可退役」——1722 写的是「预留接入面」, W5/W6 执行成「删宿主」。全局达成率重算 10/18 表面(主视图 4 + HR 3 + 经典 3 已统一), 变体侧 0% —— 8 个列表变体仍是手搓表格(0/8 拖宽、0/8 右键隐藏、0/8 列偏好持久化, 4/8 自带手搓排序状态机); 配套 P1 范围(W2 只圈经典)、P2 验收(目标从未进验收函数)、P3 测试(零守阵钉交互同源)、P4 文档(债务未入账)。
- **报告**: memory-bank/reports/26-10-12-0455-report-webui-drawer-table-unification-audit.html (表格全景 × 能力矩阵 × 维护点账本 × 偏差清单 × 整改方向 A/B/C)。

**Refs:** memory-bank/reports/26-10-12-0455-report-webui-drawer-table-unification-audit.html,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html

## 待办 / 移交

- **W0–W4 + W7 已落地; W5/W6 被裁定越权并由 W7 撤销**。终态 = 「经典 Vue 组件 + 变体字符串 DOM」双实现并存(模板能力全量找回, W2 表格统一成果保留); W5/W6 的「终态判据: 抽屉只剩一套渲染技术」作废。
- **cap 债务**: `modules/webui-static-contract.md` 已超 evergreen cap(W2–W6 各增一条), 需另开新会话跑 `commands run doc.caps -- --strict` 收口。
- **切片数债务**: `kb.check` 报「切片数 > 70」的既有债务(每波新增切片后加深), 需另开新会话收口。
- **工作树**: W2–W6 已随 0d07dbdd 提交; W7 恢复波改动未提交(用户未要求 commit)。
- **dt06 逐行汇报倒计时**: 随 W7 变体恢复**能力回归**(test_drawer_tpl_trackers_per_tracker_reannounce 守阵仍活), 无需另开需求。
- **esc-attr-quote-dead-class 遗留已关闭**: 复核判定变体层从未带该缺陷(W2 外推有误), 运行时守阵 `expectNoDeadClass` 长期防回潮, 见坑档 W7 复核注。

### 2026-10-12 · 回引: 表格统一由修正计划 26-10-12-0527 全量收口

- 本计划的目标函数修正(审计 26-10-12-0455: 「所有表格统一 × 交互逻辑同源 × 维护点下降」)由**修正计划 26-10-12-0527** 承接实施, U0–U5 六波已于 26-10-12-1800 全部落地: 十八表格表面 Q1–Q5 终态 **18/18**(W2 三列表接壳成果扩展至抽屉八变体 04/05/06/07/08/09/10/11 全部引擎消费面), 交互单点守阵定型(`test_drawer_tpl_variant_interaction_single_point`, 声明即受检), 「变体表格 8 份手搓」债务清偿入账模块文档。终态判据与验收数字见计划 §11 各波变更行与基线切片(`testing/baselines/26-10-12-1036` U4 / U5 收口片)。
