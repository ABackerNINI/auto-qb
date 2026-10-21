# 3989 passed + 2 skipped —— S4 规则侧异步 + 崩溃恢复对账 + 进度事件

> 摘要: S4 规则侧异步 + 崩溃恢复对账 + 进度事件
> 基线时间: 2026-10-21 21:22
**Refs:** memory-bank/plans/26-10-21-1857-plan-skip-check-async-refactor.html

## 验收数字

```text
TOTAL                                                20992      97   7090      99    99%
3989 passed, 2 skipped in 148.10s (0:02:28)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%, 实测 99.30%), 在 S4 改动后的工作树上实测。
- 本轮新增 1 例守阵: `test_skip_recovery_reconciles_backup_ledger`(备份账本三分流 + 每进程一次)。
- 规则侧跳检改异步后, 既有 104 条 checking/actions 用例通过测试夹具吸收异步性(`process_rule` / `run_queue` 末尾驱动 `drive_skip`, `test_actions` 7 处改 `_run_action`), 断言语义未放宽。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/rules/actions/skip_checking.py`: 改走 `ctx.ops.skip_submit(origin=ctx.task)` —— 规则侧拿 pending 记断点让出队列, 终态由 ops 重新入队(成功 keep_progress 续跑 / 失败默认重置)。
- `src/auto_qb/core/modules/ops_mod.py`: 新增终态结果缓存 `skip_result(hash)`(有界 64 条, 纯观测) + SSE 进度事件 `skip_check`(终态结算时广播) + 崩溃恢复对账 `on_sync_line` / `_recover_skip_backups`(按 `skip_check_backup` 账本三分流)。
- `src/auto_qb/webui/static/shared/polling.js` / `commands.js`: 订阅 `skip_check` 事件, 仅失败时浮条提示(规则侧发起的跳检没有回执, 失败靠这条兜底)。
- 测试: 新增 1 例守阵; `test_checking.process_rule` / `run_queue` 末尾驱动微步线; `test_actions` 7 处 `action.execute` 改 `_run_action`(驱动到终态后取 `skip_result`)。
