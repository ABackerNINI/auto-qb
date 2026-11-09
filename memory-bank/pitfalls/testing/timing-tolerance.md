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
  `elapsed >= main_tick - SLEEP_LOWER_MARGIN_S`(余量单点 tests/platform_tolerance.py, 2026-11-06
  S6 收敛: 由各点手写 0.02 抬升为 >=2 tick=31.2ms; 空转是微秒级, 余量不损失判别力; 而 0.9 倍下界=45ms 距 46.8ms 假红值仅
  1.8ms 仍会抖)。**不要**为对称加挂钟上界: 负载合法拉长等待, 上界会制造新的假红模式。相关: 同根双 issue
  [26-09-20-0952](../../issues/26-09-20-0952-test-mainloop-tick-timing-flaky.html) /
  [26-09-22-2052](../../issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html)(2026-09-28 修复关闭)。
- **复发**: 3
  - ① 2026-10-05 CI 假红: `tests/test_traffic_grid_group.py::test_group_50_members_correct_and_time_bound`
    的**挂钟上界** `elapsed < 3.0` 在 windows-latest 实测 4.01s(同一负载本机插桩中位 ~1.26s) —— 正是上面
    「不要为对称加挂钟上界」形态的**首次真兑现**(上界零容差, 合法负载直接撞线)。处置: 计时改
    `time.process_time`(CPU 时间, 不受 `-n 4` worker 抢占 / 调度放大), 上界 3.0 → 8.0s(≈30s 采样间隔的 1/4,
    仍拦数量级劣化)。**为什么没命中**: 断言 2026-09-19(P4, v2 口径)就写下, 早于本条坑档(09-28); 且本条
    `触发` 词面偏「节流 / 节拍守阵」(下界), 性能**上界**守阵不在路由视野 —— 上界此前只作为「别这么写」的
    告诫存在, 无实测个案可路由; windows-latest job 2026-10-04 才加, 假红此前无处现形。
  - ② 2026-11-07 CI 假红: `tests/test_modules_p5.py::test_rebuild_benchmark_5000_seeds` rebuild
    median-of-5 挂钟 8.158ms >= 4.0ms 阈值(基线采于本机 7950X, 同口径中位 0.864ms) —— ubuntu-latest
    少核 runner + `-n 8` xdist 抢占 + coverage 插桩, 合法调度放大近 10x。**处置不能照抄 ①**:
    `ci.yml` 的 test(ubuntu-latest) 与 test-windows(windows-latest) 跑**同一份测试代码**, 计时
    口径须取两 OS 交集; 本机实测 Windows 侧 `time.process_time` 最小刻度 **15.625ms**(与等待
    原语刻度 WIN_TIMER_TICK_S=0.0156s 数值接近但**不同源**: 后者是 Event.wait/Sleep 定时器
    刻度, 不是 CPU 时钟分辨率), 而被测操作是**亚毫秒级**(0.85ms), 换 CPU 时间会把测量打废
    (读数量化到 0 或 15.625ms)。Linux 侧该钟基于 CLOCK_PROCESS_CPUTIME_ID 通常纳秒级,
    本轮无 Linux 环境(Docker 不可用)**未实测**, 不声称它也不可用; 若只跑 Linux 一侧, 改 CPU
    时间是更优解。故走 platform_tolerance 规范第 2 条「非用挂钟不可 → 放宽到不可撞线量级」
    分支: 上线**两档阈值**(开发机严格档 0.1/4.0ms 不动; CI 档 1.0/20.0ms 只由
    GITHUB_ACTIONS 启用), 数字单点 `tests/fixtures/perf_baseline.json`, `[5000-seed benchmark]`
    打印行带档位与阈值可追溯, 灾难线 1s/30s 保留。**已知取舍**: 分档只放宽上界、未从测量层
    消除抢占放大, CI 侧需 ~23x 中位劣化才报; 本地严格档保留检测力。**为什么没命中**:
    该测试 docstring 已写明基线机器与重采样流程, 却把「换机器」只理解成开发者换开发机,
    没把 CI runner 当独立机器档; 改测试时读的是基线切片与 docstring, 没回扫本条
    (词面「性能基准 / 回归阈值」不在本条 `触发` 视野); 且 ① 修的是**秒级**操作,
    「换 process_time」在**亚毫秒**口径下不成立, 照抄前应先量计时器分辨率。
  - **评审补钉(同轮)**: 初版拿通用 `CI` 环境变量判档, 会让开发机严格档形同虚设(放走真回归);
    已改为只认 `GITHUB_ACTIONS` 并加 2 条参数化守阵。根因与判据单点见
    [ci-env-var-profile.md](ci-env-var-profile.md)。
  - **新增判据**: 性能上界守阵换 CPU 时间前, 先量当前平台 `time.process_time` 的最小刻度;
    刻度 >= 被测量量级(Windows 15.625ms vs 亚毫秒)即不可用; 且当同一测试函数要跨 OS 跑时,
    须按**两 OS 交集**选口径, 不能拿一侧的刻度下结论, 也不能拿另一侧的高精度反证。
  - ③ 2026-11-10 CI 假红: `e2e/perf.spec.mjs:361` W5「主表轮询节拍不被放大」把**不定长交互窗**
    当成固定 4.4s, 用绝对拍数上界 `ticks.length <= 3` —— 40 步匀速滚动 + 多段 settle 在
    ubuntu-latest 共享 runner 上被拉长, 正常节拍也累出 4 拍 => 稳定假红(本地 3 拍贴边过)。
    **处置不是放宽到 4 也不是按 CI 分档**, 而是从测量层消掉假设: 注入时记 `window.__tickT0`
    与 `window.__pollMs = vm.basePollMs()`, 读取时按 `ceil(elapsed / pollMs) + 1` 归一上界
    (600 种子档真实节拍是 **1500ms**, 旧注释写 2000ms 也是漂移)。前端若把轮询加倍,
    `basePollMs()` 标称值不变而实测拍数翻倍, 仍会撞线 —— 检测力不靠固定窗口。
    **为什么没命中**: ①② 都挂在 Python 侧挂钟/CPU 时间守阵, 本条是 JS 侧「窗口内事件计数」,
    词面「节拍 / 拍数」不在本条 `触发` 视野; 评审轮 1 又抓出初版硬编码 2000ms 与真实档不符,
    说明「放宽上界」类修法必须先问分母(节拍/窗口)是不是常量。
- **守阵**: `tests/test_qbmanager_*.py` `test_run_loop_throttles_without_stop_event` 断言处注释写明余量依据;
  改守阵判据时先读该注释再动数字。性能**上界**形态的守阵见 `tests/test_traffic_grid_*.py`
  `test_group_50_members_correct_and_time_bound`(CPU 时间口径, 余量依据同样写在注释 / docstring 里)。
