# 分类: src/auto_qb/rules/actions/skip_checking.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__actions__skip_checking.py.txt`
- 机器实测: 7 条全部真存活
- 计数: 7 条 = 真洞 5 / 等价 2 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_4` | _execute_skip_checking | 实参 `has_reference=has_reference` → `None` | 等价 | 唯一消费点 ops_mod.py:1147 只用来决定一条 `logger.warning`（无参考跳检高风险告警），不改闸门、不改 job 字段以外的任何分支；跳检是否执行由 `_skip_begin` 的 source/force 决定，与 has_reference 无关。代价是高风险告警静默丢失，属文案面 |
| 2 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_5` | _execute_skip_checking | `origin=getattr(ctx, "task", None)` → `origin=None` | 真洞 | `origin` 是终态重新入队的唯一凭据（ops_mod.py:961-962 `if job.origin is not None: task_queue.add_task(...)`）；置 None ⇒ 跳检结算后规则任务永不回队，整条动作链停在该种子、后续动作全不执行，且无任何日志/失败痕迹。`ctx.task` 在队列驱动下恒非空（rules/base.py:106），该分支是生产主路径。**建议守阵**: rule 源跳检走到终态后断言 `origin` 任务被 `task_queue.add_task` 重新入队（keep_progress 随相位） |
| 3 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_10` | _execute_skip_checking | 删除 `origin=...` 实参整行 | 真洞 | 与 #2 同因：缺省 `origin=None`（ops_mod.py:454），规则任务链断裂。**建议守阵**: 同上，且断言 skip_submit 收到的 origin 与 `ctx.task` 同一对象 |
| 4 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_15` | _execute_skip_checking | `getattr(ctx, "task", None)` → `getattr(None, "task", None)` | 真洞 | 恒返回 None，等价于 #2 的断链后果；同时说明「取不到就静默」这种写法在测试里不可见。**建议守阵**: 同上 |
| 5 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_19` | _execute_skip_checking | `getattr(ctx, "task", None)` → `getattr(ctx, "task", )` | 等价 | 省略默认值后 `getattr` 的默认仍是 None（Python 语义），与原式逐字节同义，任何输入都不可区分 |
| 6 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_20` | _execute_skip_checking | 属性名 `"task"` → `"XXtaskXX"` | 真洞 | 属性名不存在 ⇒ 恒 None，与 #2 同因（规则任务不回队）。**建议守阵**: 同上 |
| 7 | `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_21` | _execute_skip_checking | 属性名 `"task"` → `"TASK"` | 真洞 | 大小写不符 ⇒ 恒 None，与 #2 同因。**建议守阵**: 同上 |

## 高风险面说明（供主控核）

本文件是跳检的**一行委托**，四阶段执行体（前置闸门/导出准备/删除-重加/收尾、R2 实时复核、备份先于删除）已迁至 `core/modules/ops_mod.py`。因此本分片的 7 条变异**没有一条触及「哪些种子允许跳检」或「默认不跳」**——闸门判据（source/force/deferral/保护策略）全在 ops 层，不在这 7 条的作用面上。本批 7 条的语义后果只有两类：

1. `has_reference` 一类（#1）：只影响「无参考跳检(高风险)」告警日志，不放宽任何跳检条件 ⇒ 等价。
2. `origin` 一类（#2/#3/#4/#6/#7）：跳检**照常执行**，但结算后规则任务不回队 ⇒ 动作链静默停摆（不是跳检错放，是跳检之后什么都不发生）。这类最危险的地方是「无声」：既没有失败回执也没有日志，种子会停在跳检后的中间态。

结论：**本文件不存在「错放 = 对未校验种子跳过哈希检查」的存活变异**；需要补的守阵是 origin 回队契约（5 条同一根因，一条用例即可覆盖）。
