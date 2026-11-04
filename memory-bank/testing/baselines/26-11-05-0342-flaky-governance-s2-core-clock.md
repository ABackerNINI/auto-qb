# 5364 —— S2 core 域时钟注入后全量基线

> 摘要: S2 core 域时钟注入后全量基线
> 基线时间: 2026-11-05 03:42
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-05, 8 worker 并行, 覆盖率门开启):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 143.77s (0:02:23)`
- 覆盖率 TOTAL: `TOTAL 24489 52 8388 34 99%` —— `Required test coverage of 99.5% reached`
- 口径注记: passed/skipped 与上一基线持平(5364/2, 零新增零丢失); 耗时为本次实测瞬时值
  (本机波动面, 不作判据)。守阵四条(tests/test_flaky_timing_guards.py)全绿 ——
  src/ 裸取时白名单 161→71 处(S2 core 域 16 文件 90 处条目删净, 只减不涨)。

## 本改动面

flaky 治理计划 26-11-05-0118 S2 第 1/4 域提交: core 域生产时钟注入(D8 构造期统一制)。

- 生产 16 文件 90 点(src/auto_qb/core/**): qbmanager(17)/taskqueue(6)/ops_mod(6)/
  ops_skip(12)/fuse_mod(1)/speed_curve_mod(1)/rules_mod(2)/relocate_exec(20)/
  relocate_probe(10)/relocate_mod(3)/relocate_lifecycle(1)/traffic_sample_mod(6)/
  traffic_snapshot_mod(1)/traffic_grid(1)/traffic_limits(2)/traffic_store(1)。
- 注入形态: 组件构造期收 `clock: Optional[Clock] = None`(缺省 = 模块属性现取 SYSTEM_CLOCK
  单点, 兼容存量测试按模块换假钟; S3 收敛为显式 FakeClock); 叶子函数(qbmanager._wait_next/
  relocate_probe/traffic_grid.grid_for_now/traffic_store._warn_bad_lines)走
  `clock.SYSTEM_CLOCK` 单点。monotonic/time 语义逐点保源, 行为零漂移。
- tests/: flaky_allowlist.py 删 16 条目(90 处) + 头部计数 161→71 更新;
  traffic_sample_support/_Clock 增 `_as_clock` Clock 协议适配; 三测试文件 52 处
  模块 time 名替换位改寻址 `SYSTEM_CLOCK`(S3 迁删); test_qbmanager_loop 接线守阵
  字面同步(`next_flush_at = self._clock.now()`)。
