# 5364 passed, 2 skipped —— S3 monkeypatch time 收敛第二半(ops/relocate/speed_curve/utils/webui 域)

> 摘要: S3 monkeypatch time 收敛第二半(ops/relocate/speed_curve/utils/webui 域)
> 基线时间: 2026-11-05 06:07
**Refs:** memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

## 验收数字

`commands run test.full` 实测(2026-11-05 06:0x, 本 clone flaky-governance, 改后全量):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 177.89s (0:02:57)`
- 覆盖率 TOTAL: `24495 语句 / 52 miss / 8388 分支 / 34 部分分支, 99%`
- 副作用台账: 越界 0 条
- 与上基线(26-11-05-0540, 第一半)逐位一致: 零用例增减(收敛是测试内部形态改造, 断言语义零漂移)

## 本改动面

S3 第 3 步之二(monkeypatch time 收敛第二半): ops/relocate/speed_curve/utils/webui 域不再经 stdlib time 名寻址。

- **src 三处(通道开闸)**: `core/qbmanager.py` 把 `self._clock` 向下透传给 OpsModule / SpeedCurveModule / RelocateModule(与 WebUIRuntime、流量两模块同口径); 三模块 `__init__` 原本就收 `clock` 参数, 零接口变化
- **ops 域(13 处)**: `ops_mod.time.sleep` 桩 10 处 —— 该寻址经 `ops_mod.time` 拿到的是 **stdlib time 模块对象**, patch 即进程级改写; 处置: 成功路径 2 处 vestigial 解包(test_actions_skip; 成功路径零退避由相位调用序断言结构性证明)、失败路径 6 处改**真实退避**(10/20/50/50/50ms 名义 170ms 真睡, 测试 +~0.2s/条)、守阵 1 处(test_guard_drive_backoff_sleeps)改**真实经过时间下界断言**(elapsed >= 0.11s, Windows 15.6ms 刻度留 60ms 余量)、竞态 1 处(test_skip_drive_settle_during_backoff_sleep_race)改后台线程在真实退避窗内并发步进(生产主循环微步线形态)
- **ops 域进程级直赋(新发现 7 处, 首半清单外)**: test_ops_recheck 4 用例 5 块 + test_ops_guard 1 块的 `time.time = lambda: now+601`(宽限耗尽模拟)→ `make_mgr(clock=FakeClock)` 构造期注入 + `clock.advance(601)`(ops_support.make_mgr 加 clock 参; 队列时间线照旧 run_queue 显式传真实 now, 两轴无交叉)
- **relocate(2 处)**: test_relocate_exec_reconcile 两处 `setattr(time, "monotonic", ...)`(开机窗口复现)→ `_armed_env(clock=FakeClock(start=120/30))` 构造期注入(helpers.relocate_env 加 clock 参); 心跳年龄判据的 journal ts 改落注入钟时间线(`boot_clock.now() - 999`, 原 `time.time()-999` 依赖"monotonic 被钉而墙钟走真钟"的进程级改写)
- **speed_curve(1 处)**: test_speed_curve_dispatch 395 `speed_curve_mod.time.time` 字典钟 → `FakeClock(start=1_000_000)` 构造期注入(advance/freeze 推进)
- **utils(3 处)**: test_utils_path `utils.time.sleep` 退避桩 2 处解包改真实退避(50ms × 2/4, 同先例)、1 处 pytest.fail 桩解包(非 PermissionError 不退避由 `len(attempts)==1` 结构性证明)
- **webui(2 处)**: test_web_longtail_traffic 77 进程级 `setattr(time, "time", ...)` → `_freeze_traffic_endpoint_clock`(patch traffic_qb.SYSTEM_CLOCK 单点, 助手既有); test_traffic_sample_store 1264 SimpleNamespace 手拼替身 → FakeClock 统一形态; webui_helpers 625 已是 FakeClock(合规, 零改)
- **保留(裁决)**: ①绊线 3 处(test_actions_on_error ×2 / test_modules_p5 ×1) `patch("time.sleep", AssertionError)` —— 是"run 内禁睡"守卫不是取时控制, 形态已统一; 不改模块级站点因守卫路径(规则引擎/任务队列)无单一 sleep 站点可比照 qbmanager `_throttle` 先例; ②datetime 族 5 处(test_conditions ×3 / test_expr_eval ×2)patch 模块 datetime —— 非 time 模块口径; conditions/expr 求值面无 clock 注入通道, FakeDatetime 冻钟是跨午夜语义的唯一钉法, 迁 FakeClock 属形式主义改造不做
- 改完 `dev.fmt` 15 文件; 定向跑本域 11 文件全绿后 `test.full` 全量绿; `test_flaky_timing_guards` + `test_clock` 随全量绿
