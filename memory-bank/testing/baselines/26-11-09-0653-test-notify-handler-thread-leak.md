# 5871 —— 5,869 passed + 2 skipped —— test_notify 8 用例补 handler.close() 收线(issue 0703)

> 摘要: 5,869 passed + 2 skipped —— test_notify 8 用例补 handler.close() 收线(issue 0703)
> 基线时间: 2026-11-09 06:53

## 验收数字

`commands run test.full` 2026-11-09 06:56 实测(本轮收尾时点): **5,869 passed, 2 skipped in 140.75s**; 覆盖率 99% (TOTAL 26,153 语句 / 42 未覆盖 / 9,100 分支 / 54 未覆盖分支)。用例总数与基线 26-11-09-0619(5,869+2)持平 —— 本批只给既有 8 个用例补清理配对, 未新增用例。

## 本改动面

- `tests/test_notify.py`: 8 个经 `_make_handler` 构造 `NotifyHandler` 的用例补 `handler.close()` 配对(修 issue 26-11-08-0703 每进程泄漏 8 个 `auto-qb-notify` 守护线程): 109/127 两挂载型在既有 finally 里 `removeHandler` 后补 close; 146/166/186/218/248/309 六直发型把用例体包进 try/finally, finally 里 close —— 断言失败路径也收线(评审 round1 minor 指出只在成功路径收线仍会级联打红其它用例的同名线程断言)。
- `memory-bank/issues/26-11-08-0703-test-test-notify-handler-thread-leak.html`: 状态 Open → Done(kb.status) + 复验行 + 修复后补充(实际修法/验证方式)。
- 验证: `commands run test.full` 全量绿 + 进程内直跑 8 用例后 `auto-qb-notify` 线程残留 = 0(逐用例 0.2s 静置采样; 修复前该口径为 8)。
- 评审: 两轮, round1 全能档 1 派发(20 行)出 1 minor(直发型失败路径未收线), 修后 round2 复评(240 行, AST 逐语句比对确认 try/finally 包裹语义等价)零发现; 引文过检 P=1/T=1, 修 1 入池 0。
