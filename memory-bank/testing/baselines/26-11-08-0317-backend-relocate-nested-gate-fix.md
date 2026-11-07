# 5653 passed + 2 skipped —— 计划 1300 收尾基线: 措辞守卫清零 + 评审修复后全绿

> 摘要: 计划 1300 收尾基线: 措辞守卫清零 + 评审修复后全绿
> 基线时间: 2026-11-08 03:17

## 验收数字

- 汇总行: `5653 passed, 2 skipped, 1 warning in 133.86s (0:02:13)`(2026-11-08, `commands run test.full` 实测誊写)
- 覆盖率: TOTAL 25532 stmts / 6 miss / 8816 branch / 28 partial;`Required test coverage of 99.5% reached. Total coverage: 99.90%`
- 差值口径: 对 26-11-08-0132 切片(5651 passed + 1 failed)净变化 = 措辞守卫清零转绿(+1)+ 评审修复批次新增用例(equal_root 等值面/R2 旧账回落/R4 执行面双相/R6b 阈值钉,+1);0 failed 为本分支首次全绿。0132 切片留档为带存量失败的历史切片,以本片为最新基线。

## 本改动面

- 评审修复(`9f0cbe4e` + 收尾补测): `relocate_units.py`(chain_gate_hits 增 equal_root 仅等值面/nested_target_on R2 回落与文案/member_save_paths 注释)、`relocate_exec.py`(_chain_gate_deps 等值并列/_chain_deps_text 文案)、`test_relocate_exec_verify.py`(equal_root 用例+夹具真嵌套)、`test_relocate_fastresume_gates.py`(旧账 R2 回落用例)、`test_relocate_supersede.py`(断言归因)、`test_web_relocate.py`(>1 阈值钉)、`test_relocate_paths.py`(R4 执行面双相用例+测试计划清单)。
- 回写面: 计划 26-11-07-1300 改版 R2 置 Done(§03 R7/R2 行、§10)、任务档案 R6 节与 S7-S9 收口、issues 索引/各生成物经 `kb.index` 重建。
