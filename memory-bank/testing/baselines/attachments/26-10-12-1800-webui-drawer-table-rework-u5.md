# 3145 —— WEBUI 抽屉表格统一重写 U5 收口(26-10-12-0527 计划, 交互单点守阵定型 + 债务入账 + Q1–Q5 终态对账)

**Refs:** memory-bank/tasks/26-10-12-webui-drawer-table-rework.md,memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html,memory-bank/testing/baselines/26-10-12-1036-webui-drawer-table-rework-u4.md

> 摘要: U5 收口波(计划 §05 U5①–⑤)。判据: ① `test.full` **3145 passed + 4 skipped** / `TOTAL 16708 161 5688 140 99%`(U4 基线 3144 → +1 = 新增定型守阵 `test_drawer_tpl_variant_interaction_single_point`, 变体文件零改动); ② 全量 e2e **196 passed + 0 failed + 10 skipped**(206 用例, 与 U4 基线逐位一致 —— 本波零代码改动面, 359s); ③ **红验两条闭环**(变体 07 注入 `ui.sort` 状态机 → 定型守阵即红; 变体 11 注入 `.dt11-r` 列宽 grid → 即红; 还原即绿); ④ 债务入账:「变体表格 8 份手搓」在模块文档改「**已清偿 + 新判据**」, 1722 档案 P6 **闭环**(Status → Done, P0–P6 全阶段完成), 2106 档案回引本计划; ⑤ **Q1–Q5 终态对账(18/18)定格**(下表)。
> 基线时间: 2026-10-12 18:00

计划：memory-bank/plans/26-10-12-0527-plan-webui-drawer-table-rework.html（§11 26-10-12-1800 条）
上一基线：memory-bank/testing/baselines/26-10-12-1036-webui-drawer-table-rework-u4.md

## Q1–Q5 终态对账(定格)

| 项 | 终态判据 | 结果 |
|---|---|---|
| Q1 表面统一 | 18/18 表面统一到引擎 | **18/18**: 主视图/设置侧 10 面(1722 P0–P5, `<aq-table>` 消费面) + 抽屉变体 8 面(04/05/06/07/08/09/10/11, `DRAWER_TABLE_DEFS` 描述符 + Teleport 锚桥 + rowsFn + 渲染器分片) |
| Q2 交互逻辑 | 1 份 | **引擎 1 份**: 表壳四件交互把手(拖宽/排序/右键隐藏/列偏好持久化)全在 `<aq-table>`/桥; 变体只留版式外壳 + rowsFn 行装配(判据零复制)+ anchTouch 触碰 |
| Q3 排序 | 1 份(或 1 + 记档特例) | **引擎 1 份比较器** + 记档特例: 04 分段钮经 `dtSortSet` 直设(选择器语义非状态机); 05/10 无表头设计 → 列交互不适用(非缺能力); 06 next 列混合口径不可排; 10/11 树序 = 树语义不适用。手搓排序状态机全目录零残留(守阵钉死) |
| Q4 列宽 | 零手搓列宽 grid | **全部表面零手搓列宽**: 列宽唯一来源 = 引擎列集 computed; 原约 550 条硬编码列宽规则随八变体重写退役; 版式 grid(卡片/双栏/图例)是 D5 保留面(非列宽语义) |
| Q5 守阵 | 交互单点守阵就位 | **定型**: `test_drawer_tpl_variant_interaction_single_point` —— **声明即受检**(drawer_tpl 全目录零 `ui.sort`; 凡 tableId+rowsFn 双声明的桥变体零表格容器列宽 grid, 已知八变体清单兜底防判据缩水), 未来新变体接引擎自动落入, 无需改守阵 |

终态判据(计划 §08): **新增一个变体表格表面 = 外壳输出一个锚 + 注册一行描述符 + 一个行渲染器, 表壳/交互/持久化/对齐零改动** —— 1722 终态判据在抽屉侧兑现(G1–G3 全达成)。

## 本波改动面

- **守阵**(`tests/test_webui_static_skins.py`): 新增 `test_drawer_tpl_variant_interaction_single_point`(U5① 定型, 声明即受检 + 已知八变体兜底; 文件头注测试计划同步)。
- **模块文档**(`modules/webui-static-contract.md`): 「已知债务: 变体表格 8 份手搓」→「**已清偿 + 新判据**」(26-10-12-1800 清偿, 终态形态 + 守阵定型判据)。
- **1722 档案**(`tasks/26-10-11-webui-table-component.md`): P6 已交付 → **Done 闭环**(承接方 0527 U0–U5 全部落地, 18/18 兑现契约承诺); Status In Progress → **Done**(P0–P6 全阶段完成)。
- **2106 档案**(`tasks/26-10-11-webui-drawer-refactor.md`): 回引本计划(目标函数修正由 0527 承接, U0–U5 全量收口, 18/18); Refs 补 0527 计划。
- **变体文件与引擎**: 零改动(U5 为收口波, 只加守阵与回写 —— 停手点「不留中间产物」兑现, 红验探针未进仓库)。

## 验收数字

- `test.full`: **3145 passed + 4 skipped** / 覆盖率 `TOTAL 16708 161 5688 140 99%`(U4 基线 3144 → +1 = 定型守阵)。首轮 3 failed 为收口回写的**索引生成物漂移**(1722 档案 Status → Done 后 `_index.md` 分区未重建, 非代码问题), `kb.index` 重建后全绿。
- 全量 e2e(dev.e2e, 206 用例): **196 passed + 0 failed + 10 skipped**, 实测 359s —— 与 U4 基线**逐位一致**(本波零代码改动面的直接证据)。
- 红验两条(注入即红 → 还原即绿): ① 变体 07 尾部注入 `var __probe = ui.sort;` → 定型守阵红(残留手搓排序状态机); ② 变体 11 注入 `.dt11-r { grid-template-columns:90px minmax(0,1fr) }` → 红(表格容器残留列宽 grid); `git checkout` 还原后守阵绿。探针未进仓库。

## 已知偏差 / 移交

- 无新增技术债。存量转告: ① `modules/webui-static-contract.md` 超 evergreen cap(本波又增「已清偿」条, 清理走 `commands run doc.caps -- --strict`, 需另开会话); ② 切片数债务(kb.check 报 > 70); ③ 引擎表头 a11y 缺口 issue 26-10-12-0800(Open 未认领, 计划外不修)。
- 停手点兑现: 不留中间产物; 一次性红验探针不进仓库; 12/13/14/15 等非表变体一行未动(全程 U0–U5 口径)。
