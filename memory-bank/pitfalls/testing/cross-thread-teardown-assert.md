# 跨线程收尾的终态断言不能单点采样

> 摘要: starlette 1.6 把 SSE 的同步生成器包进 `iterate_in_threadpool`, 它跑在 anyio 工作线程里; 该线程帧里的最后一个引用(`item`/`func`/`args` 元组)是在 `call_soon_threadsafe` **之后**才 `del` 的 —— 而正是同一次调用(写 self-pipe)唤醒消费端 ⇒ 消费端 `aclose()` 返回时工作线程可能还没走到那几个 `del`, 此刻采样 `subscriber_count()` 会读到 1(CI windows job 2026-10-16 红 `assert 1 == 0`)。生产语义无误, 缺的是**有界等待**: 退订必须发生, 但不保证与 aclose 在同一瞬间发生。
> 触发: 跨线程终态断言, 断流退订, subscriber_count, anyio 工作线程, iterate_in_threadpool, 生成器 finally 退订, 单点采样, 竞态, 偶发红, 句柄堆叠, aclose 后仍订阅, gc.collect 不生效

### 断流退订: `aclose()` 回来时引用链未必已断

- **触发**: 给「消费端关闭 → 退订」这类**跨线程终态**写断言(关闭后立刻断言 `subscriber_count() == 0`), 或只在断言前补一句 `gc.collect()` 就以为「终结已确定性发生」。
- **判别**: ①失败恒为「还剩 1 个订阅」(CI 原文 `assert 1 == 0`), 单跑/单文件恒绿, `-n 8` 全量或 CI 偶发红; ②**压满机器可稳定复现**: 本机 16 核起 24 进程 × 120 轮(每进程 1 个忙线程)忠实照抄用例体, 旧断言按约 1%~3% 的轮次判红; ③**每轮都在有限时间内自愈**(改成先等再采样恒为 0)——「最终会退订、但当前瞬间还没退订」正是本形态; 真回归时它**永不为 0**。
- **处置**: 断言改**有界等待**(退订仍必须发生, 只是给调度留窗口): `del resp` → `gc.collect()` → `while count and monotonic() < deadline: sleep(0.005)`(必须 `sleep` 让出 GIL, 否则工作线程跑不到那几个 `del`) → 兜底再 `gc.collect()`(生成器可能落在环里, 交环回收器终结) → 断言。实测最长自愈 515ms ⇒ 定时取 5s(约 10 倍余量)。**不要**改成弱断言或删断言 —— 那会把真回归一起放过(红验: 拔掉 `events.py` 的 `finally` 退订 → 判红, 字节恒等还原后复绿)。
- **守阵**: `tests/test_web_hr.py::test_api_events_sse_stream_lifecycle`(断言处注释写明竞态率与余量依据); 同族 `timing-tolerance.md`(计时断言留余量) / `poll-last-round-race.md`(末轮竞态)。
