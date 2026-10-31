# 3122 —— WEBUI 抽屉重构 W6 收口与退役(26-10-11-2106 计划, 终态)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-12-0224-webui-drawer-refactor-w5.md

> 摘要: 计划 `memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html`(专题 `webui-drawer-refactor`)的 **W6**(最后一波) —— 选择层 `drawer_templates.js` 整文件退役, 四件收进 `shared/drawer.js`(密度档单点 / 读侧归一 / 菜单与显隐判据并入 AQB_DRAWER mixin); 00-core + 00-density CSS 迁三皮肤(规则逐条未改), `dtInjectCss` 退役; W3 停手点兑现(`qb_traffic_chart.js` 谓词改吃 `drawerIsTraffic`/`drawerIsSeed` 单点); 三份坑档加退役注。判据: ① `test.full` 3122 passed + 4 skipped 与 W5 逐位同(本波零测试增删, 唯一测试面变更 = error_history 写入基线合法演化); ② e2e 156 passed + 10 skipped 与 W5 基线一致; ③ 红验两条(RC1 迁移错 → node 电池 / RC2 皮肤 CSS 缺失 → wiring)均注入即红/还原即绿; ④ **终态判据「抽屉只剩一套渲染技术」达成**, 坑档守阵零悬空。
> 基线时间: 2026-10-12 02:55

计划：memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html（W6 = 收口与退役，最后一波）
上一基线：memory-bank/testing/baselines/26-10-12-0224-webui-drawer-refactor-w5.md

## 本波改动面

- `shared/drawer_templates.js` **整文件删除**（W5 收敛后的选择层四件收进 `shared/drawer.js`）：
  ① `window.AQB_DRAWER_DENSITY`（DTPL_TIERS / DTPL_DENSITY / options·tierOf·normalize）；
  ② `window.AQB_DRAWER_TPL_REG`（tabs + readSel，白名单 + 旧 id 迁移）；
  ③ 菜单/显隐判据并入 `AQB_DRAWER` mixin（computed: dtMenuTab/dtMenuTplOptions/dtMenuTplCurrent/dtMenuMergeOn；
  methods: _dtCurTab/dtHostOn/drawerTier/dtMenuPick/dtPersistSel）—— app.js 删 `app.mixin(window.AQB_DRAWER_TPL)`；
  ④ `dtInjectCss` 退役，00-core / 00-density CSS 迁三皮肤 views.css，`.ctx-menu .ctx-item.is-gated` 迁 components.css（规则逐条未改）。
- 三份 index.html manifest 各删 `"/shared/drawer_templates.js"` 一行；装载序硬约束改 drawer.js < state.js。
- `qb_traffic_chart.js`（W3 停手点兑现）：`_QB_SCOPES` 三挂点 active/stale、`qbCurScope`、`openDrawerTraffic`
  同目标短路改吃 `drawerIsTraffic` / `drawerIsSeed` 单点 —— 全仓 `drawer.kind` 字面量只剩 drawer.js 两处定义。
- 注释引用面更新：drawer.js / drawer_tabs.js / qb_traffic_chart.js / tpl/drawer.html / tpl/drawer-tabs.html / app.js。

## 验收数字

- `test.full`：**3122 passed + 4 skipped** / 覆盖率 `TOTAL 16517 151 5626 134 99%`（与 W5 基线逐位相同；
  本波零测试增删，唯一测试面变更 = `test_webui_error_history` 写入基线 drawer.js 4→5 的合法演化更新）。
- 全量 e2e：**156 passed + 0 failed + 10 skipped**（与 W5 基线一致，见 e2e 汇总）。
- 红验两条均「注入即红 / 还原即绿」：
  - RC1 迁移去向错：general legacy `"01"`→compact → node 电池（`_DT_DENSITY_NODE_PROBE`）抓到
    「旧 tall id(01/04/07/10/13)→classic」「旧 id 01 显式迁移为 classic」两条红（23/25）；
  - RC2 皮肤 CSS 缺失：删 console views.css 的 `.drawer .drawer-split` 规则 →
    `test_drawer_tpl_registry_wiring`「console: 皮肤聚合 CSS 缺 .drawer .drawer-split {」红。
- 终态判据：**抽屉只剩一套渲染技术** —— 四页签正文恒 Vue 组件；变体 / 插件机械 / JS 运行时 CSS 注入零残留；
  坑档守阵零悬空（variant-singleton-shadow / vif-host-node-stale / drawer-switch-flicker 已加退役注，
  现役守阵与机理不变式逐档注明）。

## 守阵同轮改版清单（tests/test_webui_static_dom_panel.py，收集 28）

- `test_drawer_tpl_registry_wiring`：W6 收编版 —— 文件级退役断言 + manifest 反转 + drawer.js < state.js 序 +
  皮肤聚合 CSS 成对断言（合并/密度/置灰）+ 成员锚换家（缩进 6→4）+ `app.mixin(window.AQB_DRAWER_TPL)` 负 pin +
  dtInjectCss 负 pin + classic 描述符锚改 `DTPL_CLASSIC`。
- `test_drawer_tpl_facility_retired`：W5+W6 退役确认阵 —— 插件机械/注入活代码负 pin 改锚 drawer.js
  （含 `function dtInjectCss`），space-between/.dt-select 禁令改锚三皮肤聚合 CSS 密度段。
- `test_drawer_tpl_menu_right_click_selection` / `test_drawer_tpl_classic_default`：锚 drawer.js；
  node 电池 `M = window.AQB_DRAWER.methods`。
- `test_frontend_drawer_form_judge_single_point`：摘 W3 qb_traffic_chart 豁免 → 钉四件
  （图表模块 `t.drawerIsTraffic`×4 / `t.drawerIsSeed`×2 / `this.drawerIs*`×3 调用面逐个计数）；
  drawer.js `this.drawerIsSeed` 计数 2→3（+dtMenuMergeOn）。
- `test_frontend_qb_traffic_drawer_page_guard`：openDrawerTraffic 同目标短路断言改单点形态。
- `test_webui_error_history.py`：`STORAGE_WRITE_BASELINE` 更新（drawer_templates.js 1 并入 drawer.js → 5）。

## e2e

与 W5 基线同一集合（17 spec × 2 皮肤 = 156 passed + 10 skipped）：W5 的 drawer-density / drawer-merge /
drawer-tables 密度档口径直接覆盖 W6 迁移后的行为面（读侧迁移 / 右键切档 / 持久化 / 结构开关 / 合并双列）——
本波只换实现落点不换行为，无新增 spec。
