# 3132 —— WEBUI 抽屉表格重写 U1(计划 26-10-12-0527, 引擎 spike + Teleport 桥四路径闸门)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/testing/baselines/26-10-12-0540-webui-drawer-table-rework-u0.md

> 摘要: U1 = 三件泛化 + Teleport 桥验证(硬闸门)。① 列子集声明: `TABLE_COLUMNS` + 描述符行(stub `drawerStubV0` = `DRAWER_PEER_COLUMNS` 5 列裁剪, D2); ② 排序 dyn 泛化: `sort.js` 四处 dyn 分支 + `dtSortCell` 取数口, 变体表排序状态进 `dtSortState` 映射(按 table-id 通用存取, 不再加 state 字段), 经典表零改动; ③ Teleport 桥: `aq-dt-bridge` 组件 + 挂载机械锚代数(`dtBridge: {gen, on}`, gen **单调自增**) + drawer.html 两挂点(单栏 v-for + 合并列) + stub 变体 90(`?dtstub` 门, 生产零观感) + 列选择器变体过滤。**e2e 实测抓到两缺陷**: 桥行漏套 `sortedDrawer`; 锚代数回落(`:key` 净零 → Vue 原地补丁把内容写进游离旧锚, 软切换后桥"消失")——gen 单调修复, 均入守阵。判据: `test.full` **3132 passed + 4 skipped**(+1 桥守阵); 全量 e2e **176 passed + 10 skipped**(+10 = 桥验证 spec); stub 四路径 **10 passed**; 红验(gen 恒定注入 → 路径C 两皮肤红 → 还原绿)。
> 基线时间: 2026-10-12 06:41

计划：memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html（§05 U1 / §11 U1 行）
上一基线：memory-bank/testing/baselines/26-10-12-0540-webui-drawer-table-rework-u0.md

## 本波改动面(零真实变体改动, 主视图零行为变化)

- `app.js`: `DRAWER_STUB_V0_COLUMNS`(列子集) + `TABLE_COLUMNS.drawerStubV0` + `DRAWER_TABLE_DEFS.drawerStubV0`(变体描述符行: sort.dyn / variantTab / rows / rowKey / rowModel / rowProp) + `window.AQB_DRAWER_TPL_DEFS` 导出口 + 桥组件注册。
- `state.js`: `dtBridge`({gen 单调, on}) + `dtSortState` 两块 data。
- `sort.js`: dyn 分支四处 + `dtSortCell`(单 setSort, 删重构残留)。
- `columns.js`: `drawerStubV0Grid` / `visibleDrawerStubV0Cols` / `visibleColsOf` 公共口 / `tableDefs` 变体过滤(恢复入口不变式保持)。
- `drawer_templates.js`: register 收 `tableId`(字符集校验) + 桥方法四件 + 取数四件 + `_dtMountOne` 锚扫描 gen++ + `_dtUnmountOne` 只摘 on。
- `tpl/drawer.html`: 桥挂点恰两处(`:key="dtBridgeKey(...)"`); `tpl/xtpl.html`: `#tpl-aq-dt-bridge` 分片(表壳+渲染器+syncHeadScroll+sortedDrawer 全走 $root 单点)。
- `drawer_tpl/90-peers-stub-bridge.js`(新): ?dtstub 门 + tableId 声明 + skipUnchanged 稳定 HTML 不变量; 三份 index.html manifest +1 行。
- 守阵: `test_drawer_table_bridge_wiring`(九段接线 pin) + `test_frontend_table_registry_single_point` tableDefs 断言改版(全集遍历 + 变体过滤 pin)。

## 验收数字

- `test.full`: **3132 passed + 4 skipped** / 覆盖率 `TOTAL 16517 151 5626 134 99%`(U0 3131 → +1 桥守阵)。
- 全量 e2e: **176 passed + 0 failed + 10 skipped**(U0 166 → +10 = 桥验证 spec 5 用例 × 2 皮肤)。
- stub 四路径(硬闸门): 初开+手势三件套(排序箭头/拖宽落盘 `autoqb_cols_v5.pages.drawerStubV0.w`/右键隐藏落盘+刷新双偏好回放) / 页签切换重挂 / 软切换稳定存活 / 合并双列点亮 —— 双皮肤 **10 passed**; 生产不可见(无 `?dtstub` 菜单零 stub 项、锚零个)双皮肤 2 passed。
- 红验: 注入 gen 恒定(`gen: 1`)→ 路径C 两皮肤红(内容写游离旧锚, 桥"消失"); 还原即绿。

## Q1–Q5 对账(U1 = 地基波, 数字不变)

| 指标 | U1 现状 | 说明 |
|---|---|---|
| Q1 表面统一 | 10/18 | 桥未接真实变体(U2 起), stub 不计表面 |
| Q2 交互逻辑 | 引擎 1 + 变体 8 份手搓 | 变体接入的**接入口已定型**: 外壳锚 + 描述符一行 + 渲染器复用 |
| Q3 排序 | 引擎 1 + 变体 4 份手搓 | dyn 泛化完成 —— 变体接入即并入, 零额外机制 |
| Q4 注入 CSS | 约 550 条 | U2 起逐变体删 |
| Q5 交互单点守阵 | 就位(桥接线九段 + e2e 四路径) | U5 定型终版 |
