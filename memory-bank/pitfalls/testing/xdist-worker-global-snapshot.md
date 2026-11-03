# xdist 共享 worker 进程里量进程级全局快照当模块不变式 —— 偶发红

> 摘要: xdist 每个 worker 是常驻进程, 量「全进程线程数/句柄数等全局快照不变」的断言会被同 worker 其它用例的线程启停污染 —— 单跑恒绿、全量偶发红, 且失败方向与被测模块无关。
> 触发: active_count, threading.active_count, 线程计数, 全局快照, xdist, worker 进程, 偶发红, 单跑通过, 全量红, flaky, 不变式断言, 模块不建线程
**Refs:** memory-bank/issues/26-11-04-0600-test-testing-persist-thread-active-count.html

### 量「进程级全局快照不变」守「本模块不建 X」不变式 —— 全量并行偶发红, 单跑恒绿

- **触发**: 用 `threading.active_count()` / `threading.enumerate()` 这类**进程级**全局量, 在用例前后取快照比相等, 借此守「本模块不建线程」类不变式(2026-11-04 实证: `test_all_persist_writes_on_caller_thread` 全量并行两次 `3 == 4` 判红, 同 HEAD 单跑恒绿; issue 26-11-04-0600)。
- **判别**: ①pytest-xdist 每个 worker 是**常驻进程**, 前后跑了同 worker 的**其它用例**; 它们启停的线程/打开的资源只要落在采样窗口内退出(或启动), 快照就漂 —— 失败值方向(本例 4→3, 减少)与被测模块的行为(若违规应是新增)相反, 这本身就是「量错对象」的信号; ②同 HEAD 单跑恒绿 + 全量偶发红, 且两次全量红在**同一断言**; ③产品代码经查根本不碰该全局量对应的东西(本例只用 `threading.Lock`)⇒ 不变式本身成立, 红的是量法。
- **处置**: 不量全局快照, 改量**不变式本身的可观测对象**: monkeypatch 机制入口(本例 spy `threading.Thread.start` 记录线程名), 在被测调用的**同步窗口**内断言「没发生」—— 窗口是同步的, 只有被测代码经过 spy, 对无关线程启停天然免疫; 还比快照强(窗口内建线程又 join 掉的形态快照抓不到、spy 抓得到)。不要用「失败自动重试」掩盖(丢门禁信号), 也不要给用例加 xdist 独占标记(治标拖慢全量)。红绿双验: 临时往被测调用里注入一次真实违规(建一个线程), 确认 spy 断言红。
- **同族**: 全局状态跨测试共享的其它形态见 [log-capture.md](log-capture.md)(caplog/root handlers)与 [fake-config-shared-mutables.md](fake-config-shared-mutables.md)(类属性); 「量错对象」总判据见 [assertions.md](assertions.md)。
