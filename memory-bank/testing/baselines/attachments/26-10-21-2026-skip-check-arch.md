# 3988 passed + 2 skipped —— S3 微步线 + 批量异步 + 窗口抑制

> 摘要: S3 微步线 + 批量异步 + 窗口抑制
> 基线时间: 2026-10-21 20:26
**Refs:** memory-bank/plans/26-10-21-1857-plan-skip-check-async-refactor.html

## 验收数字

```text
TOTAL                                                20950      89   7076      96    99%
3988 passed, 2 skipped in 154.07s (0:02:34)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%, 实测 99.34%), 在 S3 改动后的工作树上实测。
- 本轮新增 2 例守阵: `test_skip_submit_async_scheduler_and_failure_isolation`(异步受理 + 调度器并行推进 + 逐 hash 失败隔离 + 抑制登记随终态撤销) / `test_skip_window_suppression_ignores_sync_removal`(窗口内 torrents_removed 不算删除, 增量轮与全量轮都豁免)。
- 批量链路测试改为「提交 → drive_skip 驱动调度器 → 断言回执」(`test_web_skip_check` 2 处 / `test_web_keys` 2 处), 单发与规则侧仍走同步 `skip_check` 不受影响。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/core/module.py`: 新增微步线 hook 契约 —— `run_micro_line(dry_run)`(逐模块调 `on_micro_line`) 与 `next_micro_run_at()`(取各模块最早到期时刻); 内核等待超时 = min(同步线, 任务线, 微步线) - now。
- `src/auto_qb/core/qbmanager.py`: 暂停判断之后调 `host.run_micro_line(dry_run)`; 等待超时并入 `host.next_micro_run_at()` —— 走 hook 而非直调模块方法(内核只知「何时」, 不知「何事」, 守阵 `test_kernel_run_wiring_delegates_to_host` 覆盖)。
- `src/auto_qb/core/modules/ops_mod.py`: 拆出 `_skip_begin`(同步/异步共用前置与闸门) + 新增 `skip_submit`(异步入口, 返回 pending, 终态经 `on_done` 回调) + `_skip_settle`(终态结算单点: 落 result → 出账 → 撤抑制 → origin 重入队 → 回调) + `advance_due(budget_ms, budget_calls)` / `next_run_at()` / `on_micro_line` / `next_micro_run_at`; `SkipJob` 增 `on_done`/`origin`/`result`/`settled`。
- `src/auto_qb/torrents/store.py`: 新增 `skipping_hashes`; `_apply` 增量轮过滤 `removed`、全量轮豁免缺席者(否则全量重建会把窗口内记录当删除)。
- `src/auto_qb/webui/commands.py`: 批量跳检改走 `skip_submit`, 回执由最后一个 job 的终态回调按原因聚合写入(前端 `waitCmd` 契约不变)。
- 测试: 新增 2 例守阵; 批量链路 4 处插入 `drive_skip`; `test_web_force_passthrough` 的批量段改 mock `skip_submit`(wraps 保留真实链路)。
