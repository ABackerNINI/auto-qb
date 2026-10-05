# 26-10-05-test-plan-docstring-drift — 测试文件头部「## 测试计划」清单与实际函数漂移

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05
**Topics:** test-plan-docstring-drift
**Summary:** 认领 issue 26-10-05-0922 (docs 便签档: tests/test_config_schema.py 头部清单列着已删用例)。复验仍复现; 按 issue 建议「顺手 grep 其他测试文件」把范围扩到全 tests/ —— 79 份带「## 测试计划」的文件里, 11 份 / 21 条清单条目指向全仓不存在的函数(幽灵条目)。逐条裁决「有明确后继则改名 / 无后继则删除」: 改名或合并 15 条 · 删除 5 条 · 跨文件指针修正 1 条, 另补登 2 条漏登用例。只改 docstring, 不动测试代码。复扫幽灵 0 条; test.full **2603 passed + 4 skipped / 99%**。

**Refs:** memory-bank/issues/26-10-05-0922-docs-config-schema-docstring-drift.html, memory-bank/testing/baselines/26-10-05-0945-test-plan-docstring-drift.md, memory-bank/activeContext/26-10-05-0945-test-plan-docstring-drift.md

## 原始请求

用户: 「认领issue: memory-bank/issues/26-10-05-0922-docs-config-schema-docstring-drift.html」→ 复验后「修复issue」→ 收尾问答选定「补完整 DoD + 提交」并把扫出的同类漂移「并入本件一起修」。

## 思考过程与决策

- **认领前先同步**: 该 issue 文件本 clone 没有 —— 远端 `757b61d2` 推上来的, `commands run my-commit-flow.sync` 同步成功 `ef93db56` 后才可见。跨 clone 刚入池的件必须先 sync 才能认领。
- **复验 (09:36)**: 原锚点仍复现 —— 清单里的 `test_hr_check_field_levels_cover_validation_keys` 全仓零定义(该守阵随 impact 级别表退役时删除, 清单未跟删); 反向另有两条实存用例未入清单。
- **范围裁决 (用户拍板「并入本件」)**: issue 建议段本就写了「顺手 grep 其他测试文件头部清单是否有同类漂移」, 故扫描本身在件内; 扫出的 21 条同类条目一并修, 不再另开 issue。
- **逐条裁决口径**: 幽灵条目只有两种正确处置 —— ①**有明确后继**(同名改写/改名/合并)则把条目改成现役名与现语义; ②**无后继**(特性整体退役)则删条目。**不凭猜测保留**。判据 = 全仓 `def test_*` 名单 + 后继函数 docstring 语义比对 + `src/` 侧特性是否仍在。
- **只修文档不动测试代码**: 本件是 docs 类, 测试用例本身与覆盖不受影响(改前改后 passed 数一致, 只 docstring 变化)。
- **误报剔除**: 扫描器会把「清单里引用的**文件名**」(如 `test_conditions.py`)与「跨文件引用的用例名」当幽灵。逐条人工甄别后剔除 2 类误报 —— 其中 `test_web.py` 里 `test_entry_details_field_surface` 是**准确**的跨模块引用(该用例在 test_hr_status.py), 未动。
- **`test_hr_config.py` 的 6 条 impact 字段级条目**属合并而非逐条改名: W4 级别表退役后粒度由「字段」升为「段」, 现役两条是 `test_impact_hr_check_is_single_section_change` / `test_impact_trackers_whole_section_change`, 故 6 条替换为这 2 条(同时补上漏登)。
- **`test_hr_report.py` 的 `test_run_hr_resume_clears_suspension`**: `src/` 侧 `hr-resume` / `hr_resume` 零命中, `--hr-resume` CLI 已不存在 → 删除条目(非改名)。
- **`test_hr_runtime.py` 的 `test_judge_passes_completed_age_limit`**: `src/auto_qb/hr/resolve.py:12` 明写「被删除的旧概念: … 超龄豁免(completed_age_limit、auto_age_limit)」→ 删除条目。
- **`test_state_matrix.py` 的指针**: 原指向 `test_conditions.py(test_state_condition_invalid_attr_fails_fast)`, 该测试全仓不存在; StateCondition 现 docstring 称「spec 合法性由 config 校验阶段保证」, 实际守阵是 `tests/test_config.py::test_validate_state_condition_spec`(第 562 行) → 改指针, 不删(它是有用的跨文件导航)。

## 实现计划

- tests/test_config_schema.py: 删 1 条幽灵 + 补 2 条漏登(按文件内实际用例重建清单)
- 全 tests/ 幽灵扫描(79 份带清单文件) → 逐条甄别 → 11 份文件按「改名 / 删除 / 改指针」处置
- 复扫确认幽灵清零 → `commands run test.full`
- 回写: 立档(阈值②: 改动 ≥3 个源文件) · issue 状态与修法回填 · activeContext 切片 · 基线切片 · 索引重建

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 认领 + 复验 + 置 In Progress | Done |
| test_config_schema.py 清单重建(删 1 / 补 2) | Done |
| 全 tests/ 幽灵扫描 + 逐条甄别 | Done |
| 11 份文件清单处置(改名 15 / 删 5 / 改指针 1) | Done |
| 复扫幽灵清零 + test.full | Done |
| 回写(issue / 切片 / 基线 / 本档案 / 索引) | Done |
| 「文件内有、清单无」的漏登全量排查 | Open (范围守恒: 除 test_config_schema.py 外未做, 多数文件清单本就不穷举) |

## 进度日志

- 2026-10-05 09:34–09:36: 会话开工同步(`ef93db56`); 认领并置 In Progress; 复验锚点仍复现。
- 2026-10-05 09:38–09:41: test_config_schema.py 清单重建完成(幽灵 0 / 漏登 0), test.full 2603 passed + 4 skipped; 顺手扫描发现 10 文件 / 21 条同类幽灵, 报给用户。
- 2026-10-05 09:42–09:45: 用户拍板「并入本件一起修」+「补完整 DoD + 提交」。逐条裁决并改完 11 份文件; 复扫 79 份文件幽灵 **0 条**; test.full **2603 passed + 4 skipped / 99% / 40.15s**(语句 15605 / 未覆盖 163 / 分支 5308 / partial 138)。
