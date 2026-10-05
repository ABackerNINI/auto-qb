# 计时断言的 OS 粒度余量

> 摘要: 挂钟计时断言的两个假红面 —— ①**下界**零容差: Windows 等待原语按 15.6ms 定时器刻度取整, 50ms 等待实测可提前到 46.8ms(3 刻度); ②**上界**零容差: 合法负载 / CI 抢占直接撞线(2026-10-05 实测)。守阵余量一律以"被守回归的量级"定界; 上界优先换 CPU 时间(process_time)而非挂钟。
> 触发: 计时断言, 挂钟, elapsed, sleep 精度, 定时器刻度, 假红, 节流守阵, 节拍, Event.wait, 抖动, flaky, 耗时上界, 性能上界, CPU 时间, process_time, 并行 worker, xdist

### 挂钟下界断言零容差: Windows 等待按 15.6ms 刻度取整, `elapsed >= main_tick` 必假红

- **触发**: 给节流/节拍行为写守阵, 断言 `elapsed >= main_tick`(下界恰好等于一个节拍, 零余量)。
- **判别**: 失败值与阈值只差几毫秒(如 0.046 vs 0.05)而**不是**微秒级 ⇒ 是 OS 等待提前返回, 不是被守的空转/失效
  (空转是 µs 量级); 单跑恒绿、文件级/全量偶发红、过几天又不红 ⇒ 与系统定时器分辨率状态相关
  (其它进程 timeBeginPeriod / Win11 timer coalescing 改变取整方向: 3 刻度=46.8ms 红, 4 刻度=62.4ms 绿)。
  同日 regime 微基准可直接量化: `Event.wait(0.05)` 3000 次 min=59.1ms(过冲 regime, 0 假红)。
- **处置**: 下界留余量, 余量按"被守回归的量级"定, 不按"抖动实测"定 —— throttle 守阵取
  `elapsed >= main_tick - 0.02`(空转是微秒级, 20ms 余量不损失判别力; 而 0.9 倍下界=45ms 距 46.8ms 假红值仅
  1.8ms 仍会抖)。**不要**为对称加挂钟上界: 负载合法拉长等待, 上界会制造新的假红模式。相关: 同根双 issue
  [26-09-20-0952](../../issues/26-09-20-0952-test-mainloop-tick-timing-flaky.html) /
  [26-09-22-2052](../../issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html)(2026-09-28 修复关闭)。
- **复发**: 1 —— 2026-10-05 CI 假红: `tests/test_traffic_grid.py::test_group_50_members_correct_and_time_bound`
  的**挂钟上界** `elapsed < 3.0` 在 windows-latest 实测 4.01s(同一负载本机插桩中位 ~1.26s) —— 正是上面
  「不要为对称加挂钟上界」形态的**首次真兑现**(上界零容差, 合法负载直接撞线)。处置: 计时改
  `time.process_time`(CPU 时间, 不受 `-n 4` worker 抢占 / 调度放大), 上界 3.0 → 8.0s(≈30s 采样间隔的 1/4,
  仍拦数量级劣化)。**为什么没命中**: 断言 2026-09-19(P4, v2 口径)就写下, 早于本条坑档(09-28); 且本条
  `触发` 词面偏「节流 / 节拍守阵」(下界), 性能**上界**守阵不在路由视野 —— 上界此前只作为「别这么写」的
  告诫存在, 无实测个案可路由; windows-latest job 2026-10-04 才加, 假红此前无处现形。
- **守阵**: `tests/test_qbmanager.py` `test_run_loop_throttles_without_stop_event` 断言处注释写明余量依据;
  改守阵判据时先读该注释再动数字。性能**上界**形态的守阵见 `tests/test_traffic_grid.py`
  `test_group_50_members_correct_and_time_bound`(CPU 时间口径, 余量依据同样写在注释 / docstring 里)。
