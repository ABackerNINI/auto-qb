# 7051 passed, 7 skipped, 1 warning in 230.45s (0:03:50) —— webui/server/auth.py 变异测试计划全量测试基线

> 摘要: webui/server/auth.py 变异测试计划全量测试基线
> 基线时间: 2026-11-27 05:02
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

TOTAL                                                31451  31451     0%
7051 passed, 7 skipped, 1 warning in 230.45s (0:03:50)

`commands run test.full` 实测(2026-11-27)。覆盖率行照实测输出逐字誊写；本轮全绿。

## 本改动面

- 计划: `memory-bank/plans/26-11-27-0321-plan-mutation-webui-auth.html`，目标为 `src/auto_qb/webui/server/auth.py`，定向池冻结为 `tests/unit/test_web_auth.py` 与 `tests/unit/test_web_traffic_stream.py`。
- 记录: 常驻 issue 与任务档案补计划引用；新增 active-context 切片与本基线切片。
- 边界: 本轮仅完成计划与文档收尾，零 `src/`、零 `tests/` 改动，未执行 `mutants.run`、补测、复跑或常驻锚覆盖进度更新。
