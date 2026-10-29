# 4073 passed, 2 skipped —— 全量测试基线: HR 结论行对齐守阵加入后

> 摘要: 全量测试基线: HR 结论行对齐守阵加入后
> 基线时间: 2026-10-29 22:42

## 验收数字

- TOTAL: 21070 stmts, 99 miss, 7136 branch, 103 partial, 覆盖率 99.27%（≥99% 门槛达标）
- 汇总行: 4073 passed, 2 skipped in 148.08s (0:02:28)
- 口径注记: `commands run test.full` 全绿（本 clone, Windows, Python 3.13.12, 8 并行 worker）; 同轮首轮曾 1 failed（`test_memory_bank.py::test_gen_all_check_is_green`, 原因是 issue 状态翻转后未重建 `issues/_index.md` 生成物, `kb.index` 重建后消除, 非代码问题, 已在重建后的本轮全量中转绿）
- 覆盖率缺口面（既有, 非本轮引入）: ops_mod 95% / relocate_mod 97% / runtime.py 98% 等零星行, 与历史基线同族

## 本改动面

- `src/auto_qb/webui/static/shared/drawer_tpl/03-general-dossier-collapsed.js`: `hrLine` 触发态补 `if (d.hr_state)` 结论行分支（与 01/02 同措辞, issue 26-10-29-1341）
- `tests/test_webui_static_dom_panel.py`: 新增 `test_drawer_general_hr_state_line_parity`（三变体各含 `if (d.hr_state)` 闸）+ 头部测试计划清单同步
