# 5364 passed, 2 skipped —— S2 webui/traffic 域时钟注入后全量基线

> 摘要: S2 webui/traffic 域时钟注入后全量基线
> 基线时间: 2026-11-05 04:21
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-05, 8 worker 并行, 覆盖率门开启):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 127.41s (0:02:07)`
- 覆盖率 TOTAL: `TOTAL 24494 52 8388 34 99%`
- 口径注记: passed/skipped 与上一基线持平(5364/2, 零新增零丢失); 耗时为本次实测瞬时值
  (本机波动面, 不作判据)。守阵四条(tests/test_flaky_timing_guards.py)全绿 ——
  src/ 裸取时白名单 59→24 处(S2 webui/traffic 域 11 文件 35 处条目删净, 只减不涨)。

## 本改动面

flaky 治理计划 26-11-05-0118 S2 第 3/4 域提交: webui/traffic 域生产时钟注入(D8)。

- 构造期注入: WebUIRuntime 收 `clock`(缺省 SYSTEM_CLOCK 模块属性现取; QbManager 装配链
  透传 `clock=self._clock`), runtime_commands 7 点 / runtime_stream 6 点 / runtime.py 版本
  播种 2 点 / commands_torrents t0 1 点 / views.refresh_tracker_health 1 点走 `self._clock`;
  `_timing` 加 clock 参(三段埋点同钟); ChainCache / RoCache(WebContext 透传)同款注入。
- 叶子单点: routes/hr.py 4 点、traffic_qb.py 5 点(含 _SERVER_STARTED_AT)、relocate_chain
  _result 走 `SYSTEM_CLOCK.now()`; lifecycle 节流与启动等待预算 3 点走 `SYSTEM_CLOCK.
  monotonic()`(阻塞预算不入假钟, 与 hr 域同口径)。
- 白名单: tests/flaky_allowlist.py 删 webui/traffic 域 11 条目(59→24 处/11 文件)。
- 测试面(仅修被本任务破坏的桩): test_webui_delta_mirror / test_webui_delta_delta 的
  _ViewHost 补 `_clock`; test_web_commands_reannounce 的 SimpleNamespace 宿主补 `_clock`;
  webui_helpers._freeze_traffic_endpoint_clock 与 test_web_traffic_qb / test_traffic_
  sample_store 的端点冻结钟改 patch `traffic_qb.SYSTEM_CLOCK`。
