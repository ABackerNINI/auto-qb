# 3131 —— WEBUI 抽屉表格重写 U0(计划 26-10-12-0527, 冻结 + 契约交付)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/testing/baselines/26-10-12-0340-webui-drawer-refactor-w7.md

> 摘要: U0 = 冻结 + 1722 P6 契约交付 + 验收函数确认, **零行为变化**。① 契约全文落在 `shared/table.js` 头注「对外契约(P6)」节(纯注释, 无 runtime diff): 描述符字段(含变体扩展 rowModel/features/hostAnchor)/表壳 props 与 emit/行渲染器「纯消费方」接口/变体表格体 Teleport 锚约定(`data-dt-table-anchor`)/接入 checklist; ② 1722 任务档案 P6 状态 待做 → 已交付; ③ 「变体表格 8 份手搓」债务入账模块文档(U5 改已清偿); ④ Q1–Q5 已在计划 §08 验收函数(起草时含), 本波确认。判据: `test.full` **3131 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`; 全量 e2e **166 passed + 10 skipped** —— 与 W7 基线逐位相同(零行为变化的直接证据)。
> 基线时间: 2026-10-12 05:40

计划：memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html（§05 U0）
上一基线：memory-bank/testing/baselines/26-10-12-0340-webui-drawer-refactor-w7.md

## 本波改动面

- `shared/table.js` 头注追加「对外契约(P6)」节(注释, 1732 P6 欠账交付; 承接方 = 本计划 D1 Teleport 锚桥)。
- `memory-bank/tasks/26-10-11-webui-table-component.md`: P6 波次行 + 下一步 → 已交付。
- `memory-bank/modules/webui-static-contract.md`: 「变体表格 8 份手搓」债务入账 + P6 契约指针。
- 计划 26-10-12-0527: 26-10-12-0533 拍板定稿(D1–D6 全推荐项, 状态 In Progress)。

## 验收数字(与 W7 基线逐位相同)

- `test.full`: **3131 passed + 4 skipped** / 覆盖率 `TOTAL 16517 151 5626 134 99%`。
- 全量 e2e: **166 passed + 0 failed + 10 skipped**。

## Q1–Q5 对账(U0 起点 = 审计账本)

| 指标 | U0 现状 | 终态目标 |
|---|---|---|
| Q1 表面统一 | 10/18(主视图 4 + HR 3 + 经典 3) | 18/18 |
| Q2 交互逻辑份数 | 引擎 1 + 变体手搓 8 份表格体 | 1 份 |
| Q3 排序份数 | 引擎 1 + 变体手搓 4 份状态机 | 1 份 |
| Q4 注入 CSS 列宽规则 | 约 550 条(8 变体) | −约 500 条 |
| Q5 交互单点守阵 | 0(钉「变体与主表交互一致」) | 就位(U5 定型) |
