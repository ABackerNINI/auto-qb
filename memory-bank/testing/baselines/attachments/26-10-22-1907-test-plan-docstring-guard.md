# 3998 —— 测试计划机械守阵落地与全量回填后全量基线

> 摘要: 「## 测试计划」docstring 机械守阵(tests/test_test_plan_docstring_guard.py)落地 + 存量全量回填后全量基线
> 基线时间: 2026-10-22 19:07
**Refs:** memory-bank/tasks/26-10-22-test-plan-docstring-guard.md

## 验收数字

`commands run test.full` 实测输出（基线 `40cceff8`，守阵+回填改动后同基线）：

- 汇总行: **3998 passed, 10 skipped in 140.38s (0:02:20)**
- TOTAL 表: `20728  116   7088   106    99%`（语句 / missed / 分支 / partial / 覆盖率）
- 覆盖率门槛 99% 达标，无 FAIL 行；零失败零回归
- 守阵自身: 合成源红验单测 6/6 绿; 活体突变红验过（测试文件追加未登记 def → 守阵当场红 → 原字节还原后复绿）
- `src/` 零改动（纯 tests/ + memory-bank/ 制品），覆盖率与上基线同档

口径注记：passed/skipped/覆盖率数字由 agent 从本次实测输出誊写；相对上基线的逐位对比不写（看差值 `commands run kb.baseline -n 2`）。

## 本改动面

认领并修复 issue `26-10-21-0502-test-test-plan-docstring-guard`（用户指派）：

- 新增守阵 `tests/test_test_plan_docstring_guard.py`：扫描器（段定位/列表行/缺列/幽灵/豁免名单）+ 合成源红验单测 5 条 + 全仓零漂移断言 1 条；守阵自身「## 测试计划」列出全部 6 条用例，自受管辖
- 存量回填 53 文件：51 漂移文件补 295 条裸名条目；`test_hr_discovery`/`test_snapshot_sync` docstring 尾新建全量段（30+16 条）；`test_sync`/`test_logging` 伪清单标题（「测试清单:」「计划覆盖:」）升格为正式 `## 测试计划` 标题
- 幽灵条目 6 处清理：dom_panel 2 条就地改名（`test_drawer_tpl_default_sel` / `test_drawer_tpl_render_error_fallback_default`，后继 def docstring 有「原名」声明）；hr_worker silence 拆分对 2 条后继接手旧描述；删 3 条（hr_worker 2 条改版重写无 1:1 后继 + hr_status 1 条已并入 `test_site_status_rich_snapshot_fields`）
- 改动面合计 tests/ 56 文件（55 修改 + 1 新增守阵），全部过 `dev.fmt`（yapf 零扰动）；`src/` 零改动
