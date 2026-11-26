# 7052 passed, 6 skipped, 1 warning in 148.42s (0:02:28) —— 启动自愈清理全量测试基线

> 摘要: 启动自愈清理全量测试基线
> 基线时间: 2026-11-27 02:50
**Refs:** memory-bank/tasks/26-11-24-backend-relocate-foreign-notified-cleanup.md

## 验收数字

TOTAL                                                31451  31451     0%
7052 passed, 6 skipped, 1 warning in 148.42s (0:02:28)

`commands run test.full` 实测(2026-11-27)。覆盖率行本次实测输出为 0%(与上一条基线不同),照输出逐字誊写,不归因于改动面;全绿(见上汇总行)。

## 本改动面

- 后端 relocate 模块: 新增启动自愈清理函数(清 job 缺失/已终态的 A 与 mismatch 账、保留 B 与活跃 A),`_load_jobs` 尾部接线并受 dry-run 保护; 换代改走只读视图先判「账已在」,避免无账时 materialize 账键(见计划 D9)。
- 测试: 启动清理守阵 + D4 交叉守阵用例(含删调用即红的敏感度验证)。
- 文档: 本基线切片、active-context 会话切片、任务档案 T5 状态、计划文档 D9 变更记录; 三轮评审零 blocker、1 条 minor 已修、检 1/1。
