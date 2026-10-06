# 测试 CI 假红修复: 50 成员聚合耗时上界改 CPU 时间口径

> 摘要: GitHub Actions `test-windows` 红 —— `tests/test_traffic_grid.py::test_group_50_members_correct_and_time_bound` 的**挂钟上界** `elapsed < 3.0` 在 windows-latest 实测 4.012s(同一负载本机裸跑 0.62s / 覆盖率插桩 1.27s)。定性为**假红非回归**: cProfile 显示 0.65s 里绝大部分是 v3 读路径(`v3_series_points` 0.29s tottime + `v3_grid_obs` 0.18s), 组聚合本身只有 `group_rate_points` 0.03s / `group_totals_points` 0.05s。修法(单文件, `src/` 零改动): 计时 `time.perf_counter` → `time.process_time`(CPU 时间, 抗 `-n 4` worker 抢占 / 调度放大), 上界 3.0 → 8.0s(≈30s 采样间隔的 1/4, 余量按被守回归量级定)。命中既有坑档 [timing-tolerance](../pitfalls/testing/timing-tolerance.md)「不要为对称加挂钟上界」→ 该条 **复发 +1** 并扩 `触发` 词。红绿双验过。
> 最后活动: 2026-10-05 08:46

**Refs:** memory-bank/testing/baselines/26-10-05-0846-test-ci-timing-upper-bound.md

## 现状

- **修复完成**。改动面: `tests/test_traffic_grid.py`(计时口径 + 上界 + 函数 docstring + 文件头「## 测试计划」行) · `memory-bank/pitfalls/testing/timing-tolerance.md`(复发 +1 / 触发词扩容 / 守阵指到新测试) · `memory-bank/pitfalls/testing/_index.md`(`kb.index` 重生) · 本切片 · 基线切片。
- 验证: `commands run test.full` **2589 passed + 4 skipped / 99%**(40.29s / 51.84s 两次采样); 红验(临时把上界压到 1.0)→ 断言真触发, 实测 CPU **1.328s** 超上界; 复原 8.0 后回归绿。
- 未验证面 / 残留风险: CI 侧复跑以 GitHub Actions 运行为准; 若仍偶发(8s 余量 ≈ 2x 于本次 CI 实测), 按坑档余量口径再抬, 或按仓库「刻意用计数不用计时」先例改为**计数守阵**(钉 O(桶 × 成员) 工作量)。
- 不满足立档阈值(单文件小修), 无任务档案。
