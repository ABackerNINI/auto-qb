# 5364 passed, 2 skipped —— S3 测试侧假钟统一单点后全量基线

> 摘要: S3 测试侧假钟统一单点后全量基线
> 基线时间: 2026-11-05 04:58
**Refs:** memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

## 验收数字

`commands run test.full` 实测(2026-11-05, 8 worker 并行, 覆盖率门开启):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 113.28s (0:01:53)`
- 覆盖率 TOTAL: `TOTAL 24496 52 8388 34 99%`
- 口径注记: passed/skipped 与上一基线持平(5364/2, 零新增零丢失; 期间净变化 = 退役
  legacy 形态/别名两条旧测 + 新增构造期注入/模块单点换钟两条行为证明, 相互抵消);
  1 warning 为存量(历次基线均在, 非本轮引入)。守阵四条(tests/test_flaky_timing_guards.py)
  全绿, 白名单三组(sleep/e2e/src-time)本轮未动。

## 本改动面

flaky 治理计划 26-11-05-0118 S3 第 1 步: 测试侧假钟统一单点 —— 4 套旧假钟迁删 +
FakeClock 修成 Clock protocol 单一形态。

- tests/clock.py: FakeClock 由「float 属性 now + __call__/time() 四形态」改为 Clock
  protocol 单一形态(`now()`/`monotonic()` 方法 + `advance`/`freeze`, 内部存 `_now`);
  wait_until 删 `poll=` 旧关键字别名; 模块 docstring 清掉「S2 迁移完成前旧 monkeypatch
  形态仍可用」等过期豁免说明。
- tests/test_clock.py: 旧形态测试(可调用/time() 四形态、poll 别名)退役, 新增
  test_fake_clock_plugs_into_constructor_injection(TaskQueue 构造期 clock= 直接吃
  FakeClock, now()/monotonic() 双读数行为证明)与 test_fake_clock_swaps_module_single_point
  (模块属性现取 SYSTEM_CLOCK 的叶子兜底口径换钟证明)。
- hr 域(11 文件): tests/hr_helpers.py 的 Clock 类删除; 消费点 FakeClock 化 ——
  `now_fn=clock` -> `now_fn=clock.now`(service/queue/worker 注入位), `clock.now` 读 ->
  `clock.now()`, `clock()` 可调用形态 -> `clock.now()`, 直接构造 `_Budget(..., clock, ...)`
  -> `clock.now`; hr_service_support/hr_worker_support 两个装配单点的缺省分支同步改写。
- traffic 域(6 文件): tests/traffic_sample_support.py 的 _Clock/_AsClock/_as_clock 退役
  (`monkeypatch.setattr(ts_mod, "SYSTEM_CLOCK", _as_clock(clock))` -> 直接传 FakeClock);
  test_traffic_sample_core/store 共 82 处 `_Clock(...)` -> `FakeClock(start=...)`,
  `clock.now = t` 赋值 -> `clock.freeze(t)`, `clock.now -= 10` -> `clock.freeze(clock.now() - 10)`;
  test_qbmanager_loop 的 _FakeLoopTime 类删除(第 5 套, 经 _as_clock 消费故一并退役),
  `clock.now += x` -> `clock.advance(x)`。
- webui 域(2 文件): webui_helpers._freeze_traffic_endpoint_clock 的
  SimpleNamespace(now=lambda) 桩与 test_web_traffic_qb 的同类桩 -> FakeClock(start=...)
  (S2 已删的两套内嵌 _FixedClock 的遗留替换桩, 收敛到统一假钟)。
- wait_until 直连(6 文件): tests/helpers.py 再导出别名删除, drive_skip 改直调;
  test_notify/test_traffic_monitor_client/test_hr_worker_lifecycle/test_hr_worker_notes/
  hr_worker_support 的 `from helpers import wait_until` 全部直连 `from clock import
  wait_until`, 16 处 `poll=0.01` -> `interval=0.01`(语义逐字等价)。
