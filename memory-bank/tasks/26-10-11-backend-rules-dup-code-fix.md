# 26-10-11-backend-rules-dup-code-fix — rules 重复代码重构(3 条 refactor issue 认领与修复)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-21
**Summary:** 用户指令「修复 rules 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」。滚动报告 §20(轮 17)对 rules 全包(2187 行 · 18 文件)入池 **3 条 refactor issue**; 本轮按**保守口径(只做无行为变化的收口)** 全部修完并置 `Done`: ① `rules-expr-disk-helper-dup`(env 三取值器 + `FreespaceCondition` 四处逐字同的「取数 + 错误映射」收成单点 `disk_usage_value(path, attr)`); ② `rules-expr-numeric-predicate-dup`(env 数值函数与 eval 算术运算符的「必须是数值」校验收成 `types.require_number(value, what)`, 报错文案逐字不变); ③ `rules-parser-dead-op-constants-dup`(删 parser 四个本文件不用的运算符常量死件)。**零行为变化**(结构收口 + 删死件), 新增 3 个守阵测试锁单点。全量 `test.full` **3115 passed + 4 skipped / 0 failed / 覆盖率 98.63%**。
**Topics:** dup-code-audit

**Refs:** memory-bank/issues/26-10-11-0352-refactor-rules-expr-disk-helper-dup.html, memory-bank/issues/26-10-11-0352-refactor-rules-expr-numeric-predicate-dup.html, memory-bank/issues/26-10-11-0352-refactor-rules-parser-dead-op-constants-dup.html, memory-bank/testing/baselines/26-10-11-1625-backend-rules-dup-code-fix.md
## 原始请求

> 用户(2026-10-11): 「修复rules部分问题:26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」

> 报告 §20(R17 rules)入池 3 条 refactor issue, 均在本包内且报告自标「收益低-中 / 风险低」; 用户「相关 issue 一并认领」即指派全部 3 条, 无跨包/歧义项, 故无需再收敛范围(与 hr 轮「9 条含 3 条跨包需拍板子集」不同)。

## 思考过程与决策

- **请求边界判定**: **执行任务**(改代码 + 认领 issue)。用户显式给出「修复」与「认领」两项指令 —— 认领(用户指派)与改代码都在授权内。3 条 issue 全部落在 `src/auto_qb/rules/` 包内、无跨包依赖, 与 hr 轮的 9 条(含 3 条跨包)不同, 不存在需拍板的范围歧义, 故直接全做。
- **保守口径的落地判据**(沿用 hr 轮): 「无行为变化」= 只抽公共助手/单点、不改数据形状、不合并有语义差异的分支、**不改用户可见文案**。三处都按此执行。
- **报告口径复核, 不照抄**(沿用 hr 轮教训): 逐处比对报告描述与实际代码 ——
  - R17-A01 报告称「四处同构」属实; 唯一差异是条件侧原只捕 `OSError` 而 env 侧捕 `(OSError, ValueError)`。取**超集** `(OSError, ValueError)` 作单点口径: `shutil.disk_usage` 的 Local/Mapped 两实现实际不抛 `ValueError`(Local 走 `shutil.disk_usage`, Mapped 走 `_require_mapped` → `FileAccessError`/`OSError`), 故对条件侧是「不可达路径的防御性放宽」, 行为等价。
  - R17-A02 报告称「三处各写」属实; 关键点是 env 两处的 `isinstance(x,(int,float)) and not isinstance(x,bool)` 与 `types.is_number` **逐值等价**, 故改走 `is_number` 无行为变化; 三处文案不同(函数参数 vs 运算符操作数), 故 helper 用 `what` 参数承载主体短语、文案骨架单点。
  - R17-C02 报告称 parser 四个运算符常量「本文件从不使用」属实 —— 删前全仓 grep 复核: parser 内零引用、外部无导入、`tests/` 零引用, 属真死件。
- **单点的落点选择**: `disk_usage_value` 放 `rules/expr/env.py`(四处中三处在此, conditions 已依赖 `.expr` 包, 无环); `require_number` 放 `rules/expr/types.py`(`is_number`/`type_name`/`label` 三原语都在此, 最内聚)。
- **删 `file_access` 导入**: `conditions.py` 的 `file_access` 仅 `FreespaceCondition.match` 一处使用, 收口后成为未用导入, 一并移除(避免 lint 未用导入)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步(`my-commit-flow.sync`: `98e7abf5`) | Done |
| S2 | 修 `rules-parser-dead-op-constants-dup`(删死件) | Done |
| S3 | 修 `rules-expr-numeric-predicate-dup`(`types.require_number` + 三处委托) | Done |
| S4 | 修 `rules-expr-disk-helper-dup`(`env.disk_usage_value` + 四处委托) | Done |
| S5 | 3 条 issue 置 `Done` + 填 `doc-refs` 认领链 | Done |
| S6 | 收尾: `dev.fmt` / `test.full` 基线切片 / 本档案 + 切片 / 审计档案 R7 / `kb.index` + `kb.check` | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| rules-expr-disk-helper-dup | Done | `env.disk_usage_value(path, attr)`; `_freespace/_disk_total/_disk_used` + `FreespaceCondition.match` 四处收单点 |
| rules-expr-numeric-predicate-dup | Done | `types.require_number(value, what)`; `env._num_unary/_min_max` + `eval._as_num` 三处收单点(文案不变) |
| rules-parser-dead-op-constants-dup | Done | 删 `parser.py` 四个死件运算符常量(types 活件保留) |
| 守阵测试 | Done | 3 个新测试: `test_disk_usage_value_single_point` / `test_require_number_single_point` / `test_parser_has_no_dead_op_constants` |
| 认领链 | Done | 3 条 issue `doc-refs` ↔ 本档案 `**Refs:**` 双向闭环 |
| 收尾(测试 / 索引 / 基线) | Done | 见进度日志 |

## 进度日志

### 2026-10-11 R1 — rules 全包重构(3 条 issue)

- **开工同步**: `commands run my-commit-flow.sync` → 已同步 `98e7abf5`(无落后)。
- **① 盘用量取数单点**(`rules-expr-disk-helper-dup`): `rules/expr/env.py` 新增模块级 `disk_usage_value(path, attr)`(取数 + `FileAccessError`/`(OSError, ValueError)` → `ExprError` 映射, 保留「不可判定显式报错、绝不降级成假值」口径); `_freespace`/`_disk_total`/`_disk_used` 各降为一行委托; `rules/conditions.py` 的 `FreespaceCondition.match` 改 `from .expr.env import disk_usage_value` 复用同一单点, 并删去不再使用的 `file_access` 导入。四处逐字同 → 一处。
- **② 数值谓词单点**(`rules-expr-numeric-predicate-dup`): `rules/expr/types.py` 新增 `require_number(value, what)`(判据走既有 `is_number` 单点, 文案骨架 `f"{what}必须是数值, 得到 {label(type_name(value))}"`); `env._num_unary`/`_min_max` 传 `what="该函数的参数"`、`eval._as_num` 传 `what=f"'{op}' 的操作数"` —— **用户可见文案逐字不变**, 判据实现收成一处。编译期 `check_op_types`/`check_unary_types`(ExprSyntaxError)不属本项, 未动。
- **③ parser 死件**(`rules-parser-dead-op-constants-dup`): 删 `rules/expr/parser.py:20-23` 的 `_ARITH_OPS`/`_ORDER_OPS`/`_EQ_OPS`/`_LOGIC_OPS`(本文件零引用、外部零导入、测试零引用); 保留 `_BINOPS`/`_UNARY_OPS`/`_LITERAL_KINDS`。
- **守阵**: `tests/test_expr_eval.py` 新增 3 个测试(patch 单点断言 env/conditions/eval 均经其路由; `hasattr` 断言 parser 不再持有四个死件名), 并同步该文件头 `## 测试计划` 清单 3 行。
- **验证**: `dev.fmt` 格式化 6 个改动文件; 定向 `tests/test_expr_eval.py` + `test_expr_parse.py` + `test_conditions.py` + `test_file_access.py` 106→(含新增)全绿; 全量 `commands run test.full` → **3115 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 98.63%**(见基线切片)。数字较上基线 3112 增 3 = 新增的 3 个守阵测试。
- **认领链**: 3 条 issue 置 `Open`→`Done`(徽标 + meta 双改), 补「实际修法 / 验证方式」段与状态日志, 填 `doc-refs` 指向本档案; 本档案 `**Refs:**` 反向列 3 条 + 切片 + 基线。
- **零改动确认**: 改动面仅 `src/auto_qb/rules/` 内 5 源文件 + `tests/test_expr_eval.py`; 跨包(config/core/hr/webui/infra)零改动; `config.yml` / `auto-qb-data/` 未触碰。
- **计划外发现(已入池, 未修)**: 收尾跑 `kb.check` 时发现 3 份 webui 基线切片(`26-10-10-2245/2306/2335`)缺三行头的 `> 摘要:` 行, 致 `gen_baseline_recent --check` 恒红(提交闸门未含此条故不拦); 属 webui-selection-trigger-parity 专题的既有文档缺陷, 按范围守恒入池 `26-10-11-1630-docs-baselines-missing-summary-header`。

## 待办（下一轮）

- 重复代码审查主线: Phase 2 前端(轮 20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(轮 26)仍未开工(见 `26-10-10-backend-dup-code-audit`)。
- rules 包 R17 的 B 类项(no-HR 缺省语义两处 / AST 双类型检查)与 A03(动作 `__init__` 样板)按报告口径**只登记不修**(前者合并会改语义, 后者样板过薄), 未入池。

- 2026-10-21 02:26 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)

- 2026-10-21 03:11 认领并修复 issue 26-10-20-2231(refactor-fe-config-entity-crud-dup): config_editor.js 抽 cfgEntityAdd/Rename/Remove 三骨架 + cfgTrackerDef/RuleGroupDef/RuleDef 三份差异清单, config_hub.js 三处 promptDialog 包装合并为 hubAddEntity(def), 九处入口收敛; 连带删中间态 newXName×3/addOpen/cfgAddCancel/cfgTracker(name); 50 项等价性 harness 对 HEAD 版与改后各跑一遍均全绿(开发中抓出 _rules 后缀回归并修), issue 置 Done
