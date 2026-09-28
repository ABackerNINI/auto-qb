# 计时断言的 OS 粒度余量

> 摘要: 挂钟下界断言零容差是通用假红反模式 —— Windows 等待原语按 15.6ms 定时器刻度取整, 50ms 等待实测可提前到 46.8ms(3 刻度); 节流/节拍守阵的下界必须留余量, 余量以"被守回归的量级"定界。
> 触发: 计时断言, 挂钟, elapsed, sleep 精度, 定时器刻度, 假红, 节流守阵, 节拍, Event.wait, 抖动, flaky

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
- **守阵**: `tests/test_qbmanager.py` `test_run_loop_throttles_without_stop_event` 断言处注释写明余量依据;
  改守阵判据时先读该注释再动数字。
