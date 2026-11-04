# qbmanager-loop

> 摘要: 修复 issue 26-11-05-0035(时序敏感用例偶发红): 根因为用例按 flush 序数绑定轮次, 改按轮记账; 生产代码未改
> 最后活动: 2026-11-05 01:00
**Refs:** memory-bank/issues/26-11-05-0035-test-qbmanager-flush-fallback-flaky.html, memory-bank/testing/baselines/26-11-05-0059-test-qbmanager-flush-fallback.md

**R0(2026-11-05 00:48):** 认领 issue 26-11-05-0035(test_w6_flush_fallback_once_per_round 偶发红): 置 In Progress, 复现与根因定位中

**R1(2026-11-05 01:00):** 修复 issue 26-11-05-0035(时序敏感用例偶发红): 只改用例按轮记账, 注入空转轮确定性复现与验证; 全量数字见 kb.baseline
