# 基线切片 26-10-05-0127 — 主循环异常路径退避 (issue 26-10-02-0728 认领修复)

> 摘要: 认领 issue 26-10-02-0728 (主循环 except Exception 不推进 next_*_at → wait_for=0 无退避快速重试)。
> 拍板 §06 候选①: 异常分支把 next_sync_at/next_tick_at 推到 max(原值, now+main_tick), 退避起步与
> _reconnect_due 口径一致; 复验实证影响面为全周期 (非首轮同样不推进), 不止 issue 原记载的首轮。
> 基线时间: 2026-10-05 01:27

**Refs:** memory-bank/issues/26-10-02-0728-bug-mainloop-first-tick-exception-no-backoff.html, memory-bank/activeContext/mainloop-exception-backoff.md

- 分支: develop @ 488c93e6 (+ 本轮未提交改动: src/auto_qb/core/qbmanager.py / tests/test_qbmanager.py / issue HTML / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2533 passed + 4 skipped, 27.79s (引擎计 28.6s), 覆盖率 TOTAL 99%**
  (14871 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向 (tests/test_qbmanager.py): **52 passed**(8.78s, 含新守阵)。红验: 修复前连炸 3 拍间隔实测
  0.003s / 0.001s (wait_for=0 快速重试), gaps 断言判红; 修复后转绿。
- 相对上基线 (26-10-05-0058: 2532 passed + 4 skipped / 99% / 26.98s): passed **+1** = 本轮新守阵
  (test_run_exception_backs_off_next_tick); skip 集合不变 (Windows 侧 4 条 POSIX 专属)。
- 改动面: src/auto_qb/core/qbmanager.py(主循环 except Exception 分支 +3 行退避推进, 源语句 14868→14871)
  · tests/test_qbmanager.py(新守阵 1 条 + 既有 2 用例 main_tick/sync_interval 调小 0.05s 适配
  —— 异常路径现在真等一个节拍, 默认 1.0s 会让用例各多挂 1s; 判据不变)。
