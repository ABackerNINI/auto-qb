# rule-system — 规则系统

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 规则定义与触发、process 语义与去重、17 条件 + expr + 12 动作、checking 高风险动作单独成篇。
> **触发**: 规则, 触发, 条件, 动作, expr, ActionResult, checking, 跳检

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [checking.md](checking.md) | `CheckAction` 的决策链与七道防护 —— 高风险动作单独成篇, 与 pitfalls/backend/high-risk-ops.md 互指。 | checking, 校验, full-checking, skip-checking, 跳检, 七道防护 |
| [conditions-and-actions.md](conditions-and-actions.md) | 17 种条件 + `expr` 速查 + 12 种动作 + 限速单数值保护 + 状态映射表 + 变量替换。 | 条件, 动作, expr, 表达式, 状态映射, 变量替换, 限速保护 |
| [rules-and-triggers.md](rules-and-triggers.md) | 规则怎么定义与绑定、触发时机、`Rule.process()` 执行语义、去重语义与 ActionResult 四态。 | 规则定义, 绑定, 触发时机, trigger, process, execute_once, cooldown, ActionResult |
