# 5462 passed + 2 skipped —— gtm-alert 日期炸弹修复后全量基线

> 摘要: gtm-alert 日期炸弹修复后全量基线
> 基线时间: 2026-11-06 04:49
**Refs:** memory-bank/issues/26-11-06-0330-test-e2e-gtm-alert-date-bomb.html

## 验收数字

`commands run test.full`(2026-11-06 04:45-04:49, 8 worker 带覆盖率)实测:

- 汇总行: **5462 passed, 2 skipped, 1 warning**, 耗时 189.25s(3:09);前一轮(04:40, 索引未重建)为 5461 passed + 1 failed(`test_gen_all_check_is_green` 生成物漂移), 重建索引后归零 —— 差值 +1 即该守卫。
- TOTAL 表: 24538 statements / 57 missed / 8396 branches / 36 partial, 覆盖率 **99%**。
- 与上基线 [26-11-06-0302](26-11-06-0302-flaky-governance-s6-baseline.md) 差: 5367 → **5462 passed(+95)**, skipped 持平 2 —— 增量来自本 clone 快进的 52 笔提交(未随各自基线切片落在本 clone), 非本轮改动。
- 1 warning 为既有告警(非本轮引入)。

### e2e fast(串行口径, 单轮)

- `npm run test:e2e:fast` → **290 passed, 0 failed**, 11.0m(修前同口径 288 passed + 2 failed, 总数同为 290)。
- 归零的 2 条 = gtm-alert 双皮肤(prism/atlas), 本轮修复对象, 见 [issue 26-11-06-0330](../../issues/26-11-06-0330-test-e2e-gtm-alert-date-bomb.html)。
- 注: 本行为**串行**口径; shard=3 口径(含 perf-serial 补跑)的 302 总数与本行不可直接比, 见上基线。

## 本改动面

- `e2e/gtm-alert.spec.mjs`: T1-T3 硬编码 `2026-11-03T…+08:00` 改为相对 `Date.now()` 生成(T1/T2/T3/T4 = 1h/30min/2h/25h 前), 新增第 ④ 条「超 TTL 判空」负向断言, 原降级面顺延为 ⑤; 头部判据清单与时间口径注释同步。
- 产品代码零改动(`dialogs.js` 的 `GTM_ALERT_TTL_MS=24h` 是设计口径, 不动)。
- 文档回写: issue 26-11-06-0330 翻 Done(含实际修法/验证方式), `testing/flaky-ledger.md` 该行翻 Done, 坑档两处复发计数 +1(`ops/venv-trampoline-clone-copy.md`、`testing/tmpdir.md`)。
