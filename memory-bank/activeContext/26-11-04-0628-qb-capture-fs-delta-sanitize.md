# qb-capture-fs-delta-sanitize

> 摘要: 修复 fs_delta 未脱敏: sanitize_all 补逐帧分支(同源派生/未知行丢弃+WARN), self_test 增 fs_delta 判据; 补 3 条测试+2 条扩形态; test.quick/test.full 全绿, 数字见新基线切片
> 最后活动: 2026-11-04 11:49
**Refs:** memory-bank/issues/26-11-03-1144-bug-qb-capture-fs-delta-sanitize.html, memory-bank/testing/baselines/26-11-04-0627-qb-capture-fs-delta-sanitize.md, memory-bank/testing/baselines/26-11-04-1121-qb-capture-sanitize.md

**R0(2026-11-04 06:28):** 修复 fs_delta 未脱敏: sanitize_all 补逐帧分支(同源派生/未知行丢弃+WARN), self_test 增 fs_delta 判据; 补 3 条测试+2 条扩形态; test.quick/test.full 全绿, 数字见新基线切片

**R1(2026-11-04 11:17):** 认领并修复 issue 26-11-04-0943(test_qb_capture 随机盐假红): 三处夹具的非 hex 假 hash H1 改为合法 40 位 hex, 断言口径不变; 同进程多轮复验 0 红, 定向与全量数字见 kb.baseline

**R2(2026-11-04 11:49):** review(全能档, 1 只读子代理, 125 行): blocker 清零; 修 3(1 minor 回写口径 + 2 nit), 入池 0; review.check 引文 3/3 通过; 修复后全量数字见 kb.baseline
