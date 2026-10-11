# 3125 —— WEBUI 表注册表 P0(四页硬编码泛化为 `TABLE_DEFS`)

> 摘要: 计划 `26-10-11-1722-plan-webui-table-component` 的 **P0**(注册表骨架, **零行为变化**)—— app.js 顶部新增表注册表 `TABLE_DEFS`(每张表一行: 列定义 / 宿主 ref / grid 与可见列 computed 名 / 行窗口化 kind / 排序键), `TABLE_PAGES` 改为 `Object.keys(TABLE_DEFS)`; `columns.js` 的 `gridStyle`/`_headEl`/`_winContainer`/`_winGapOf`/`_ensureWinTop`/`_measureRowH`/`recomputeEffective`/`colAlignCss` 与 `sort.js` 的 `_sortKeys`/`_resetSort` 一律按 id 取(十处页字面量与 ref 名映射清零)。列定义常量(`GROUP_COLUMNS` 等)原样保留, 模板 / CSS / DOM 结构零改动。新增守阵 `test_frontend_table_registry_single_point`(红绿双验过)。
> 基线时间: 2026-10-11 18:04

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `cfe9a8d5`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3125 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16464 语句 / 148 未覆盖 / 5608 分支 / 133 partial; 门槛 98% 达标, 实到 98.70%; 本轮 35.02s)
- 与上一片 `26-10-11-1712-docs-baseline-gate-fix` 的对照(仅这一处差异): **passed 3124 → 3125(+1 = 新增守阵 `test_frontend_table_registry_single_point`)**, 语句 / 未覆盖 / 分支 / partial 四项**逐位相同**(16464 / 148 / 5608 / 133) —— 零行为变化的直接证据(结构收口, 不增删业务用例)。
- 增量明细(本轮真正新增): `memory-bank/plans/26-10-11-1722-plan-webui-table-component.html`(计划) + `memory-bank/tasks/26-10-11-webui-table-component.md`(档案) + 本切片 + `activeContext/26-10-11-1748-webui-table-registry-p0.md` + `modules/webui-static-contract.md`(回写 `TABLE_DEFS` 单点 + app.js 行数 488→582) + `pitfalls/git/editing-traps.md`(行尾坑 `复发 +1`)。代码面: `shared/app.js`(+52/-1) · `shared/columns.js` · `shared/sort.js`; 测试面: `tests/test_webui_static_skins.py`(+1 守阵)。
- 机检: `commands run kb.check` 全绿。真浏览器 e2e `commands run dev.e2e` = **124 passed / 34 failed / 10 skipped**, 34 项失败经 A/B 证实为**存量**(把三个 JS 文件 `git checkout` 回 HEAD 后重跑同批 spec 得逐项相同的失败集: trigger-scope 10 / multiselect-shows 10 / optimistic 10 / menus 4), 与 P0 无关; e2e 内列模型相关 spec(`column-prefs.spec.mjs` 等)全部通过。
