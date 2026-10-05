# 基线切片 26-10-05-0846 — CI 假红修复: 50 成员聚合耗时上界改 CPU 时间口径

> 摘要: 用户给 GitHub Actions `test-windows` 失败摘要(`test_group_50_members_correct_and_time_bound`
> 耗时上界实测 4.012s > 3.0s)要求修复。定性为**假红非回归**(v3 读路径占绝大部分, 组聚合本身 ~0.08s);
> 修法 = 计时改 `time.process_time`(CPU 时间, 抗并行 worker 抢占)+ 上界 3.0 → 8.0s, 单文件测试改动,
> `src/` 零改动。命中既有坑档 [timing-tolerance](../../pitfalls/testing/timing-tolerance.md)
> 「不要为对称加挂钟上界」→ 复发 +1。
> 基线时间: 2026-10-05 08:46

**Refs:** memory-bank/activeContext/26-10-05-0846-test-ci-timing-upper-bound.md

- 分支: develop @ 911af7ef (+ 本轮未提交改动: tests/test_traffic_grid.py / 坑档 timing-tolerance.md 及其 `_index.md` / activeContext 切片 / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2589 passed + 4 skipped, 40.29s / 51.84s(两次采样), 覆盖率 TOTAL 99%**
  (15576 语句 / 162 未覆盖 / 5296 分支 / 137 partial; 门槛 98% 达标)
- 相对上一条基线 (26-10-05-0800: 2567 passed + 4 skipped / 99% / 49.9s): passed **+22** /
  语句 +99 / 分支 +56 / partial +1 —— **全部来自其后并入 develop 的 webui 危险动作防护分支**
  (该分支基线 [26-10-05-0737](26-10-05-0737-webui-danger-guards.md) 自记 +22/+99/+56), **与本笔无关**;
  本笔只改一个断言的计时口径与上界, 不增删用例、不动 `src/`, 故 passed / skip / 语句 三组**零增量**。
  耗时 40.3~51.8s 落在近几条切片 43.5~51.1s 的噪声带附近, 非回归。
- 靶向 (tests/test_traffic_grid.py -k group_50): **1 passed**; 红验(临时把上界压到 1.0)断言真触发
  —— 实测 CPU **1.328s** 超上界, 复原 8.0 后回归绿。**实测计时分布**(本机, coverage 插桩口径):
  裸跑 0.62s / 插桩 1.27s(中位); CI(windows-latest, `-n 4` + 插桩) 墙钟 4.01s(改口径前的假红值)。
- 改动面: `tests/test_traffic_grid.py`(计时 `perf_counter` → `process_time`; 上界 3.0 → 8.0;
  函数 docstring 与文件头「## 测试计划」行同步) —— `src/` 零改动。
- 未验证面: CI 侧复跑(以 GitHub Actions 运行为准); 若仍偶发, 按坑档余量口径再抬, 或改计数守阵。
