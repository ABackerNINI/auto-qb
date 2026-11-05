# 5367 passed + 2 skipped —— flaky 治理 S6 收口全量基线(时钟注入+假钟统一+e2e shard=3 验收 10 轮)

> 摘要: flaky 治理 S6 收口全量基线(时钟注入+假钟统一+e2e shard=3 验收 10 轮)
> 基线时间: 2026-11-06 03:02
**Refs:** memory-bank/tasks/26-11-06-test-flaky-governance.md, memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

## 验收数字

`commands run test.full` 连续 5 轮实测(2026-11-06 02:00-02:45, 8 worker 带覆盖率):

- 5 轮汇总行均为 **5367 passed, 2 skipped, 1 warning**, 逐轮耗时 142.93s / 146.30s / 145.19s / 140.12s / 145.29s(区间约 2:20-2:26, 报耗时带区间口径)。
- TOTAL 表: 24495 statements / 52 missed / 8388 branches / 34-35 partial, 覆盖率 **99%**(partial 34/35 在轮间抖 1, 属既有采样噪声)。
- 与上基线 [26-11-05-0639](26-11-05-0639-flaky-s3-sleep-zero-baseline.md) 差: 5364 → **5367 passed(+3, S5/S6 新守阵与平台容差单点), skipped 持平 2**。
- 1 warning 为既有告警(非本计划引入)。

### e2e fast 验收(shard=3 口径, 连续 5 轮)

每轮 = `dev.e2e-fast-shard`(shard 1/3 → 2/3 → 3/3 轮转) + `dev.e2e-perf-serial`(CPU 敏感量具串行补跑), 相加==fast 全量:

| 轮 | shard 1/3 | shard 2/3 | shard 3/3 | perf-serial | 汇总 |
|---|---|---|---|---|---|
| 1 | 102 passed, 4.4m | 86 passed, 4.1m | 92 passed, 3.4m | 20 passed, 1.0m | 300 passed + 2 failed(既有) |
| 2 | 102 passed, 4.1m | 86 passed, 4.1m | 92 passed, 3.3m | 20 passed, 1.0m | 300 passed + 2 failed(既有) |
| 3 | 102 passed, 4.5m | 86 passed, 4.1m | 92 passed, 3.3m | 20 passed, 59.3s | 300 passed + 2 failed(既有) |
| 4 | 102 passed, 4.3m | 86 passed, 4.2m | 92 passed, 3.5m | 20 passed, 1.0m | 300 passed + 2 failed(既有) |
| 5 | 102 passed, 4.4m | 86 passed, 3.9m | 92 passed, 3.3m | 20 passed, 57.2s | 300 passed + 2 failed(既有) |

- **2 failed = gtm-alert 日期炸弹既有项**(每轮同为 `e2e/gtm-alert.spec.mjs:73` prism + atlas 两条, 2026-11-03 硬编码日期过 TTL, 台账在案、有意不修)—— 按验收口径排除并注明, **5 轮零新增失败**。
- 本轮实测为「shard1 先行 + shard2∥3 并行」布局, 单轮 wall 约 9.3-9.8m; 三档对照(S5 拍板实测, 任务档案在案): **串行 690s / shard=2 366s / shard=3 约 263s + perf-serial 约 60s** —— shard=3 全并行 wall 口径下, 本轮各 shard 实测 3.9-4.5m(234-270s)与其相符。
- 门禁口径: e2e fast shard=3(推荐口径见任务档案与计划 §06 D14)。

## 本改动面

- **本切片承载 S6 收口轮的验收测量**(S1-S6a 各步改动随各自基线切片在案, 见 `commands run kb.baseline --all`): 本轮只做文档回写(根因十类覆盖表/坑档两件/计划翻 Done/任务档案)与本切片, 零代码/测试改动 —— passed +3 全部来自 S5/S6a 已落盘提交(守阵与平台容差单点)。
- e2e fast 5 轮与 test.full 5 轮为最终验收测量(计划 §01 验收口径: 连续 5 次绿=无新增失败)。
