# rules 重复代码重构(3 条 refactor issue 认领与修复)

> 摘要: 用户「修复rules部分问题: 26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」。滚动报告 §20(轮 17)对 rules 全包(2187 行 · 18 文件)入池 3 条 refactor issue; 按**保守口径(只做无行为变化的收口 + 删死件)** 全部修完并置 `Done`: ① `rules-expr-disk-helper-dup`(`env.disk_usage_value(path, attr)` 收四处「取数 + 错误映射」); ② `rules-expr-numeric-predicate-dup`(`types.require_number(value, what)` 收三处「必须是数值」校验, 文案逐字不变); ③ `rules-parser-dead-op-constants-dup`(删 parser 四个死件运算符常量)。**零行为变化**, 新增 3 个守阵测试锁单点。全量 `test.full` **3115 passed + 4 skipped / 0 failed / 覆盖率 98.63%**(较上基线 3112 增 3 = 新增守阵测试)。
> 最后活动: 2026-10-11 16:25

**Refs:** memory-bank/tasks/26-10-11-backend-rules-dup-code-fix.md

## 正在进行

- **rules 全包重构已完成**(3 条 issue 置 `Done`): 见任务档案 [26-10-11-backend-rules-dup-code-fix](../tasks/26-10-11-backend-rules-dup-code-fix.md)。改动面仅 rules 包内 5 个源文件 + 1 个测试文件; 跨包(config/core/hr/webui/infra)零改动。
- rules 包 R17 **无暂缓件** —— 3 条 issue 全在包内、报告均标「风险低」, 故全做(与 hr 轮「9 条含 3 条跨包需拍板子集」不同)。

## 关键结论(供后续执行参考)

- **单点落点**: `disk_usage_value` 放 `rules/expr/env.py`(四处中三处在此, conditions 已依赖 `.expr` 包, 无环); `require_number` 放 `rules/expr/types.py`(`is_number`/`type_name`/`label` 三原语都在此, 最内聚)。
- **跨模块 helper 命名**: 沿用 hr 轮惯例 —— 供它模块复用的助手**不带下划线**(`disk_usage_value` / `require_number`), 私有实现才带。
- **口径复核(不照抄报告)**: R17-A01 条件侧原只捕 `OSError`, 单点统一为 `(OSError, ValueError)`(env 侧超集)—— `shutil.disk_usage` 的 Local/Mapped 两实现实际不抛 `ValueError`, 属不可达路径的防御性放宽, 行为等价。R17-A02 的 `isinstance(x,(int,float)) and not isinstance(x,bool)` 与 `types.is_number` 逐值等价, 故无行为变化。
- **删件前复核**: parser 四个运算符常量全仓 grep 确认「本文件零引用 + 外部零导入 + 测试零引用」后才删。
- **收口后清导入**: `conditions.py` 的 `file_access` 收口后成为未用导入, 一并移除。

## 后续候选(未开工)

- 重复代码审查主线: Phase 2 前端(轮 20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(轮 26)仍未开工(见 `26-10-10-backend-dup-code-audit`)。
- rules 包 R17 未入池项(按报告口径只登记): B01(no-HR 缺省语义两处, 合并会改语义) / B02(AST 双类型检查, 刻意分层) / A03(动作 `__init__` 样板, 过薄不宜抽)。
- infra 轮 18 的 5 条 issue(如 `infra-fmt-ladder-dup` / `infra-platform-detect-bypass-dup`)仍在 `Open`, 属后续修复轮候选。
