# 5364 passed, 2 skipped —— S3 优先域裸 sleep 改造后基线(feeder+qbmanager_tasks 清零)

> 摘要: S3 优先域裸 sleep 改造后基线(feeder+qbmanager_tasks 清零)
> 基线时间: 2026-11-05 05:11
**Refs:** memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

## 验收数字

`commands run test.full` 实测(2026-11-05, 8 worker 并行, 覆盖率门开启):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 124.97s (0:02:04)`
- 覆盖率 TOTAL: `TOTAL 24496 52 8388 34 99%`
- 口径注记: passed/skipped 与上一基线持平(5364/2 —— 本轮只改测试等待机制, 零新增零
  退役用例); 1 warning 为存量(历次基线均在, 非本轮引入)。守阵
  tests/test_flaky_timing_guards.py 四条全绿, 白名单 ALLOW_SLEEP_TESTS 收紧: 删
  test_hr_runtime_feeder.py(3 处)与 test_qbmanager_tasks.py(5 处)两文件条目,
  27 处/15 文件 -> 19 处/13 文件。改动面 5 连跑(-n 2)无竞态复现。

## 本改动面

flaky 治理计划 26-11-05-0118 S3 第 2 步: 优先域裸 sleep 改造 —— 4 个计划点名文件里
真有裸 time.sleep 实调用的是 2 个(另 2 个只余 monkeypatch 字符串/文档形态, 见下):

- tests/test_hr_runtime_feeder.py(3 处清零): ①/③两处「睡一拍赌线程睡进 wait()」
  (test_sleeper_is_interruptible_by_stop / test_sleeper_interrupt_during_wait_message_
  is_precise)改为 _WaitProbe(threading.Event 子类, wait() 入口置 entered, set/clear
  语义不变)替换 runtime._sleep_stop, 用例等 entered 命中再打断 —— 打断必然落在等待内,
  不再依赖真睡步长; ②test_runtime_uses_anchors_provider 的手写轮询循环(deadline +
  time.sleep(0.02))改 wait_until(calls, timeout=3.0)。
- tests/test_qbmanager_tasks.py(5 处清零): ①test_wake_drains_commands_without_extra_
  ticks 的 waker 线程 3 次 time.sleep(0.15) 步进改 drained Event 同步(每轮 drain 落袋
  亮灯, waker 见灯再投下一条; 线程内不 assert, 超时 break 交主线程断言报实情防挂死);
  ②test_command_batch_triggers_single_resync 的 time.sleep(0.15)「等首轮」改
  first_refresh Event(refresh 首轮落定亮灯) + time.sleep(0.8) 兜底改 _daemon_timer
  (10.0, stop.set) 防挂死定时器; ③test_cmd_resync_keeps_schedule_when_nothing_moved
  的 time.sleep(0.9)「命令到达时刻」是本用例的时间语义量(提前到 t≈0 会让旧行为也落进
  <1.4s 容差, 断言失去判别力), 改 threading.Timer(0.9, poster) 在既定墙钟偏移投递;
  time.sleep(1.5) 兜底改 _daemon_timer(4.0, stop.set)。
- tests/flaky_allowlist.py: 上两文件条目删除, 头部实测存量注记同步(27 处/15 文件 ->
  19 处/13 文件)。
- 计划点名但**零真调用**未动的 2 文件: tests/test_qbmanager_loop.py(7 处命中全为
  docstring 提及 + mock.patch("auto_qb.core.qbmanager.time.sleep") 字符串形态, 守阵
  AST 口径不拦)与 tests/test_traffic_store_paths.py(5 处同为 monkeypatch.setattr
  字符串 + `real_sleep = time.sleep` 局部别名间接真睡 —— test_v4_write_text_payload_
  permission_backoff_real_sleep 有意真睡的变异面用例, docstring 带理由, 不属裸
  time.sleep 实调用)。两者归后续 monkeypatch 收敛步骤。
