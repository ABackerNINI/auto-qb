# 1682 passed + 1 skipped / 0 failed —— 限速曲线手动保护日志节流(持续状态不逐轮刷屏)

> 摘要: 用户实报「重复的『限速曲线 | … 为奇数, 疑似用户手动设置, 本轮不覆盖』LOG 过多」。根因: 手动保护分支
> 逐轮打 INFO, 而手动值是持续状态 ⇒ 每天上百条且永不停。抽 `_log_manual_skip`(进入状态/值变化报 + 每 1h 提醒,
> 其余降 DEBUG), 退出保护清记忆; +3 守阵(变异测试 3 条全红); 无配置/依赖变化
> 基线时间: 2026-09-26 20:55
> 档案: 无(未命中立档阈值; 滚动状态见 activeContext/26-09-26-2054-backend-speed-curve-log-throttle.md)

- **测试增量**: +3 条(`tests/test_speed_curve.py`,「## 测试计划」docstring 同步)——
  `test_speed_curve_manual_log_throttled_same_state`(双向都手动: 首轮 2 条 INFO, 次轮同状态不再记 INFO
  但降 DEBUG; 顺带钉**去重不丢信号** —— 快照 `reasons` 仍逐轮带两个 `manual`)·
  `test_speed_curve_manual_log_periodic_reminder_and_value_change`(monkeypatch `time.time`: 61s 不重复 /
  越过 `_MANUAL_REMIND_GAP` 再提醒 / 手动值 2001→2003 立即重报)·
  `test_speed_curve_manual_log_resets_after_release`(改偶数被正常覆盖 ⇒ 清记忆, 再次手动时重新报)。
- **变异验证**: 临时把源码还原成旧行为(每轮无条件 INFO)后跑 `-k manual_log` ⇒ **3 failed**;
  还原后 43 passed ⇒ 三条守阵确实咬住本次修复, 非空转。
- **既有测试口径**: 未改任何既有断言(纯新增)。
- **采集方式**: `_CurveLogCapture`(给 `auto_qb.core.mixins.speed_curve` logger 挂 StringIO handler,
  默认 DEBUG 级)—— `QbManager` 构造时 `setup_logging` 清空 root handlers, `caplog` 捕获不到, 沿用本文件既有姿势。
- **行为口径未变**: 手动保护仍**不覆盖**该方向; 幂等/取最严/回落逻辑逐字未动 —— 只有日志档位与频率变了。

TOTAL 91%(11308 语句 / 816 未覆盖 / 3726 分支 / 331 partial; `speed_curve.py` 98% = 117 语句 / 3 未覆盖 /
42 分支 / 0 partial; 并行 test.full 27.9–28.4s, 三次采样; 覆盖率口径见 [../baseline.md](../baseline.md))。
