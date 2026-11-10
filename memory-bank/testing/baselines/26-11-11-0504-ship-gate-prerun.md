# 6002 passed + 2 skipped —— ship.gate 预跑批次全量基线

> 摘要: 6002 passed, 2 skipped (181.26s), 覆盖率 99% (26747 stmts / 55 miss / 9362 br / 66 partial) —— ship.gate 闸门预跑批次(计划 26-11-11-0408)收尾全量绿
> 基线时间: 2026-11-11 05:04

**Refs:** memory-bank/tasks/26-11-11-docs-ship-gate-prerun.md, memory-bank/plans/26-11-11-0408-plan-ship-gate-prerun.html

## 验收数字

- 汇总行: `6002 passed, 2 skipped in 181.26s (0:03:01)`(commands run test.full 实测誊写)
- 覆盖率 TOTAL 表: `26747 stmts / 55 miss / 9362 br / 66 partial -> 99%`
- 与上一切片 [26-11-11-0314](26-11-11-0314-bind-guard-fake-server-exclusive.md)(5947/2)差值: +55 passed —— 含远端合流 16 笔(3bfe31bb/a950f353 等, 条件树 ce 透传与 recycle daemon 收口)引入的用例; 本批新增面在 `.commands/` 包内脚本, 不进 tests/ 收集, 由 `test.pkg.scoped` 209 passed 单独兜住(ASCII 守卫 13 passed 亦单独复验)

## 本改动面

- 新增 `.commands/my-commit-flow/scripts/gate.py`(ship.gate 入口: 预跑主体 + CLI)
- 新增 `.commands/my-commit-flow/scripts/test_gate.py`(16 用例, 头部测试计划 docstring)
- 修改 `.commands/my-commit-flow/scripts/_ship_config.py`(GATE_KEYS 扩 when_message + bool STOP 校验)
- 修改 `.commands/my-commit-flow/.my-commit-flow.toml`(review.trace 加 when_message = true)
- 修改 `.commands/my-commit-flow/ship/config.toml`(注册 ship.gate task)
- 修改 `.agents/skills/code-review/SKILL.md`(③ pack 前置加闸门预跑步)
- 修改 `.commands/my-commit-flow/references/pipeline.md`(闸门预跑节 + 脚本表)
- 新增 `memory-bank/plans/26-11-11-0408-plan-ship-gate-prerun.html`(计划档案)
