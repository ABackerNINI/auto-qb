# test-notify-handler-thread-leak

> 摘要: 修 issue 26-11-08-0703: test_notify 8 用例 NotifyHandler 补 handler.close() 配对(挂载型 finally 补 close, 直发型六用例包 try/finally), 根治每进程 8 守护线程泄漏与 random-order 级联打红; 两轮评审(P=1/T=1, 修1), test.full 5,869 passed + 2 skipped(140.75s, 99%), 进程内线程残留 0; issue 翻 Done, 基线 26-11-09-0653
> 最后活动: 2026-11-09 06:54

**R0(2026-11-09 06:54):** 修 issue 26-11-08-0703: test_notify 8 用例 NotifyHandler 补 handler.close() 配对(挂载型 finally 补 close, 直发型六用例包 try/finally), 根治每进程 8 守护线程泄漏与 random-order 级联打红; 两轮评审(P=1/T=1, 修1), test.full 5,869 passed + 2 skipped(140.75s, 99%), 进程内线程残留 0; issue 翻 Done, 基线 26-11-09-0653
