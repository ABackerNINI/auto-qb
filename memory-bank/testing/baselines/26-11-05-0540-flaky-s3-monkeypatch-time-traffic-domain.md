# 5364 passed, 2 skipped —— S3 monkeypatch time 收敛第一半(traffic/feeder/qbmanager 域)

> 摘要: S3 monkeypatch time 收敛第一半(traffic/feeder/qbmanager 域)
> 基线时间: 2026-11-05 05:40
**Refs:** memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

## 验收数字

`commands run test.full` 实测(2026-11-05 05:40, 分支 flaky-governance, 本轮改动全部在内):

- TOTAL 24495 语句 / 52 缺失 / 8388 分支 / 34 部分分支, 覆盖率 99%(门通过)
- **5364 passed, 2 skipped**, 1 warning, 114.88s
- 与上基线(26-11-05-0511-flaky-s3-priority-sleep-cleanup, 5364 passed / 2 skipped)用例数持平: 本轮零新增用例, 纯 monkeypatch 形态收敛

## 本改动面

S3 第 3 步之一(monkeypatch time 收敛第一半): traffic/feeder/qbmanager 域不再经 stdlib time 名寻址。

- **src 两处(通道开闸)**: `core/qbmanager.py` 把 `self._clock` 向下透传给 TrafficSampleModule / TrafficSnapshotModule(与 WebUIRuntime 同口径, 原「不向下传递」注释随存量换钟测试一并退役); `core/traffic_limits.py` 删 `import time  # noqa`(唯一消费者 test_traffic_limits 已收敛)
- **构造期注入取代 SYSTEM_CLOCK 寻址位(S2 应急产物 50 处)**: test_traffic_sample_core 31 处 / test_traffic_sample_store 19 处(1280 行 webui traffic_qb 叶子单点 patch 保留)改 `clock=clock` 经 `_mgr_with_traffic`/`make_manager(clock=)` 注入; store_store 5 处 stdlib time.time 进程 patch 同改(t["now"] 字典推进改 freeze); traffic_sample_support `_drive_full_day` 进程级 time.time 改 FakeClock + freeze、`_w5_mgr` 改注入; traffic_store_support `_mgr` / test_traffic_snapshot `_mgr` 加 clock 参数
- **qbmanager 域 time 名 patch 清零**: test_qbmanager_loop 5 处(4 处 vestigial 解包 + 1 处守阵改钉 `_throttle` 模块站点)、connect 3 处(真实经过时间下界 / reconnect 退避改注入钟 / 1 处 vestigial)、query 1 处(vestigial)
- **其余本域**: test_web_traffic_qb 24h 窗进程级 time.time 改 patch traffic_qb.SYSTEM_CLOCK 单点; test_traffic_limits 3 处改 SpeedLimitRecorder(clock=FakeClock); test_traffic_snapshot ts 严格推进守阵改注入 FakeClock + 显式 advance(1s) 保判别力; test_hr_discovery 删退避 sleep 桩(0.05s x 真实发生); test_traffic_store_paths 2 处 no-op sleep 桩删除 + real_sleep 局部别名盲区改真实经过时间下界(守阵口径无需扩展, 无白名单条目)
- **helpers.make_manager 加 clock=None** 参数(构造单点透传); `_add_backlog` 加 clock 形参(任务入队时刻须同取假钟, 真实 time.time() 会落到假钟读数之后致任务永不到期 —— 本轮实测踩坑)
- 改完 `dev.fmt` 16 文件; 定向跑本域 14 文件全绿; `test_flaky_timing_guards` + `test_clock` 随全量绿
