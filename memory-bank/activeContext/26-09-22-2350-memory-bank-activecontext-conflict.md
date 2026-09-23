# activeContext 多 clone 冲突治理
> 摘要: 已定为时间戳切片方案，W1–W3 实施中；脚本与 skill 已先行落地
> 触发: activeContext 冲突, 多 clone, 会话切片, gen_active_recent
> 最后活动: 2026-09-23 15:35

## 状态

**W1–W3 已实施**（2026-09-23），W4（merge-tree 预检 + rerere）可选未做。
根因：多 clone 并行下 activeContext.md 是全体收尾必写热点，「最后更新」滚动栈每会话重写头部同一段。
解法定为 **A′ 时间戳切片 + D**：把「重写头部」改成「新增 / 更新自己的切片」。

相对初稿（A+B+D）的三处修订：取消 `global.md`（长青四段各有归属，实测占 3,516 字节 / 27%，
留在原处只是副本）、取消 `_index.md`（时间戳文件名自带时间与主题，`ls` 即索引）、
取消「取最近 N 条」与 `_recent.md` 缓存（条数不是稳定时间尺度，且截断会漏掉活跃切片）。

- [计划 v1.1](../../docs/plans/26-09-22-2350-activecontext-conflict-plan.html)
- [档案](../tasks/26-09-22-memory-bank-activecontext-conflict.md)

## 子任务

| 波次 | 内容 | 状态 |
|---|---|---|
| W1 | 结构拆分（本目录 + 9 切片 + 存根 + `_common` 常量） | 已完成 |
| W2 | 阅读脚本 + EXCLUDED_DIRS + 3 条守卫 + 闸门 | 已完成 |
| W3 | 协议接线（含三个常驻规则载体） | 已完成 |
| W4 | merge-tree 预检 + rerere（可选） | 未开始 |

**待拍板**：归档阈值（现按 14 天默认落地，`--stale-days` 可调）。

## 遗留红灯（非本轮引入，待用户定夺）

`tests/test_memory_bank.py::test_kb_files_respect_caps` 红 ——
`memory-bank/tasks/_index.md` 12,261 字符 > index-auto 12,000。`gen_tasks_index --check` 却是 0
（索引是最新的，只是真长过了 cap）。按范围守恒未修。
