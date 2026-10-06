# 主循环异常路径退避 — issue 26-10-02-0728 认领完成 (Done)

> 摘要: 认领 issue 26-10-02-0728 (主循环 except Exception 不推进 next_*_at → wait_for=0 无退避快速重试)。复验实证影响面为全周期不止首轮: 时间线推进写在动作之后 (qbmanager.py :518-527), 抛异常时 next_*_at 保持「已到期」过去值, wait_for 恒 0, 红验连炸 3 拍间隔 0.003s/0.001s。拍板 §06 候选① (异常分支 +3 行: 两条时间线推到 max(原值, now+main_tick), 退避起步与 _reconnect_due 口径一致; 候选②状态机复杂度不成比例, ③与认领修复预期相悖): 新守阵 test_run_exception_backs_off_next_tick (三条线全替换炸点, 与分支选择解耦; 红验→绿) + 既有 2 用例 main_tick 调小 0.05s 适配 (异常路径现在真等一拍, 判据不变)。test.full 2533 passed + 4 skipped / 99% / 28.6s (基线 [26-10-05-0127](../testing/baselines/26-10-05-0127-mainloop-exception-backoff.md))。不满足立档阈值, 无任务档案。
> 最后活动: 2026-10-05 01:27

**Refs:** memory-bank/issues/26-10-02-0728-bug-mainloop-first-tick-exception-no-backoff.html(Done)

## 现状

- issue Done, 认领链闭合。主循环异常语义: 意外异常退避一拍 (main_tick) 重试; StopIteration 重抛 (26-10-02-0442) / APIConnectionError 走 _reconnect_due 指数退避 / AutoQbError 穿透 —— 四类异常路径各有归宿, 互不重叠。
- 改动面: src/auto_qb/core/qbmanager.py / tests/test_qbmanager.py + issue HTML + 基线切片 + 本切片
