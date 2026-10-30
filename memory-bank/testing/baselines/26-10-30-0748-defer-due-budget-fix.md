# 4168 passed + 10 skipped(根) —— defer 预算面修复: 让位者不占 max_tasks 名额 + 让位扫描面上界

> 摘要: defer 预算面修复: 让位者不占 max_tasks 名额 + 让位扫描面上界
> 基线时间: 2026-10-30 08:30

## 验收数字

`commands run test.full`(pytest `-n 8 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-30 实测, 本片单次采样 38.71s —— 同环境其余采样 40.5s / 70.0s, 耗时按区间看, 勿拿单次当基准; **数字取自合流后**(本地提交 rebase 到 origin/develop `3e56ca4f` 之后)实测, 首次在合流前测得 4159):

```
  TOTAL                                                20875    113   7144    105    99%
  4168 passed, 10 skipped in 38.71s
```

- 汇总行: **4168 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 113)。
- 逐条口径注记:
  - 本片数字是**合流后**的全量: 除本改动新增的 2 条, 还包含同期远端乐观UI扩面批次(`a156cd1f`..`3e56ca4f`)带入的用例 —— 合流前独测两次(远端片 / 本改动片)都是 4159, 合流后 4168, 两者不可直接相减归因。
  - 本轮**新增 2 条 pytest 用例**(均在 `tests/test_taskqueue.py`): `test_run_due_defer_gate_does_not_consume_budget`(让位者不占 `max_tasks` 预算) / `test_run_due_defer_scan_bounded`(让位扫描面上界); 另**修订 1 条既有判据** —— `test_run_due_defer_gate_defers_then_resumes` 的返回数断言由 1 改 0(让位不再计入 `run_due` 返回值), 是语义变更而非功能回退。
  - 两条新守阵**先在旧实现上跑红**(旧实现: 预算测试返回 3 且 `ran == []`, 扫描测试返回 1 且队尾任务被扫出), 修后转绿 —— 非事后补测。
  - 零 `src/` 之外的生产改动; 未跑 e2e(改动不涉前端面)。
  - Linux (WSL 沙箱) 侧未重测, 仍是上片记录值。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/core/taskqueue.py` | 新增模块常量 `_DEFER_SCAN_FACTOR = 5`(让位扫描上界系数);`_pop_due` 增 `defer_gate` 参数并返回 `(可执行批次, 让位批次)` —— `max_tasks` 只约束可执行名额, 让位者本轮留在堆外由 `run_due` 事后回填, 扫描面以 `max_tasks × _DEFER_SCAN_FACTOR` 封顶;`run_due` 移除逐个过闸分支, 让位回填挪到执行批次之后, 返回值改为实际执行数;两处 docstring 同步语义 |
| `tests/test_taskqueue.py` | 新增 2 条守阵(预算面 / 扫描上界) + 修订 1 条既有 defer 用例的返回数断言;头部「测试计划」清单同步 |
| `memory-bank/issues/26-10-30-0616-bug-defer-due-budget.html` | 认领 → 复验(仍复现, 计数确在过闸之前)→ 已修, 状态置 Done 并补「实际修法 / 验证方式 / 测试数字」 |
| `memory-bank/pitfalls/backend/concurrency.md` | D-1 队列级闸门条目补「预算面」段: 让位者不占预算 / 扫描面另需上界 / 返回值语义 / 守阵入口 |
