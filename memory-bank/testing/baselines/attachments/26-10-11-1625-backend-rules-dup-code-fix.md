# 3115 —— rules 重复代码重构执行基线

> 摘要: 任务档案 [26-10-11-backend-rules-dup-code-fix](../../tasks/26-10-11-backend-rules-dup-code-fix.md)。用户「修复 rules 部分问题: 26-10-11-0033-report-dup-code-audit.html, 相关 issue 一并认领」→ 报告 §20(轮 17 rules)入池 3 条 refactor issue 全部修完并置 `Done`, 保守口径(无行为变化的收口 + 删死件)。改动面: rules 包内 5 个源文件(`expr/{parser,types,env,eval}.py` / `conditions.py`)+ 1 个测试文件(`test_expr_eval.py`)。**数字较上基线(`26-10-11-1555`)增 3 passed**(3112→3115)= 新增 3 个守阵测试(`test_disk_usage_value_single_point` / `test_require_number_single_point` / `test_parser_has_no_dead_op_constants`); 语句数 16562→16542(−20, 删死件 + 收口)。
> 基线时间: 2026-10-11 16:25

**Refs:** memory-bank/tasks/26-10-11-backend-rules-dup-code-fix.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `98e7abf5`; 工作树含本轮全部改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3115 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 98.63%**
  (16542 语句 / 156 未覆盖 / 5708 分支 / 143 partial; 门槛 98% 达标; 实测 56.8s)
- 增量明细(本轮真正新增 / 改动):
  - `src/auto_qb/rules/expr/parser.py`(删 `_ARITH_OPS`/`_ORDER_OPS`/`_EQ_OPS`/`_LOGIC_OPS` 四行死件)
  - `src/auto_qb/rules/expr/types.py`(+`require_number`; docstring 补运行期断言说明; 导入 `ExprError`)
  - `src/auto_qb/rules/expr/env.py`(+`disk_usage_value`; `_freespace`/`_disk_total`/`_disk_used` 委托; `_num_unary`/`_min_max` 走 `require_number`)
  - `src/auto_qb/rules/expr/eval.py`(`_as_num` 走 `require_number`)
  - `src/auto_qb/rules/conditions.py`(`FreespaceCondition.match` 复用 `disk_usage_value`; 删未用 `file_access` 导入)
  - `tests/test_expr_eval.py`(+3 守阵测试与其测试计划清单行)
  - `memory-bank/` 回写: 本档案 + activeContext 切片 + 3 条 issue(状态/认领链/修复后补充)+ 审计档案 R7 + 各 `_index.md`(`kb.index` 重建)+ 本基线切片
- 机检(本轮相关): 定向 `test_expr_eval.py` / `test_expr_parse.py` / `test_conditions.py` / `test_file_access.py` 全绿; `kb.index` 重建生成物; `kb.check` 主键纪律 / 认领链闭环 / 日期守卫全过; `test_docs_forms.py` + `test_memory_bank.py` 全过。
- 未纳入本轮(刻意不越界): rules 包 R17 的 B 类项(no-HR 缺省语义两处 / AST 双类型检查)与 A03(动作 `__init__` 样板)按报告口径只登记不修、未入池; 跨包(config/core/hr/webui/infra)零源码改动; `config.yml` / `auto-qb-data/` 未触碰。
