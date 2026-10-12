# 抽屉表格统一重写 · U5 收口完结（守阵定型 + 债务入账 + 终态定格，U0–U5 全部完成）

> 摘要: 计划 26-10-12-0527 **U5 收口完成, U0–U5 六波全部完结（计划 Status → Done）**：① 定型守阵 `test_drawer_tpl_variant_interaction_single_point`——**声明即受检**（drawer_tpl 全目录零 `ui.sort` 手搓排序状态机；凡 tableId+rowsFn 双声明的桥表格变体强制零表格容器列宽 grid，版式 grid 是 D5 保留面），已知八变体清单兜底防判据缩水，**未来新变体接引擎自动落入、无需改守阵**；红验两条闭环（07 注入 ui.sort 即红 / 11 注入 .dt11-r 列宽 grid 即红，还原即绿，探针未进仓库）。② 债务入账：模块文档「变体表格 8 份手搓」→「**已清偿 + 新判据**」；1722 档案 P6 已交付 → **Done 闭环**（P0–P6 全阶段完成，Status → Done）；2106 档案回引本计划。③ Q1–Q5 终态对账**定格 18/18**（终态表见基线切片）：Q1 十八表面全引擎（主视图/设置 10 + 抽屉变体 8）；Q2 交互逻辑引擎 1 份；Q3 引擎 1 份比较器 + 记档特例（04 dtSortSet 直设 / 05·10 无表头不适用 / 06 next 混合口径 / 10·11 树序）；Q4 全表面零手搓列宽（约 550 条硬编码规则退役）；Q5 定型守阵就位。④ 验收：test.full **3145 passed + 4 skipped**（+1 = 定型守阵；首轮 3 failed 为档案 Status 改动的索引生成物漂移，kb.index 重建后转绿）；dev.e2e **196 passed + 0 failed + 10 skipped**（206 用例 359s，与 U4 基线逐位一致 = 本波零代码改动面的直接证据）。**终态判据达成**：新增变体表格表面 = 外壳一个锚 + 描述符一行 + 一个行渲染器，表壳/交互/持久化/对齐零改动——1722 终态判据在抽屉侧兑现，用户目标函数 G1–G3 全达成。停手点兑现：不留中间产物、红验探针不进仓库、12/13/14/15 等非表变体全程一行未动。

> 最后活动: 2026-10-12 18:00

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/issues/26-10-12-0800-bug-webui-table-head-a11y.html,memory-bank/testing/baselines/26-10-12-1800-webui-drawer-table-rework-u5.md

## 遗留债务(需另开会话)

- **cap 债务**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W7 各一条 + U5「已清偿」条)；清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**: `kb.check` 报「切片数 > 70」(每波新增切片加深)。
- 引擎表头 a11y 缺口(26-10-12-0800 issue, Open)：属计划外，未认领不修。
