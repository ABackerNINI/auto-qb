# 6084 —— longtask 量级口径批: e2e fast 356P/0F + test.full 6084+19 覆盖 99.08%

> 摘要: longtask 量级口径批: e2e fast 356P/0F + test.full 6084+19 覆盖 99.08%
> 基线时间: 2026-11-14 00:05

## 验收数字

`commands run test.full` 实测(2026-11-14 00:03, clone2 本机, issue 26-11-13-0519 修复批收尾):

- 汇总行: `6084 passed, 19 skipped in 104.85s (0:01:44)`
- 覆盖: `Required test coverage of 99.0% reached. Total coverage: 99.08%`
- TOTAL 表: `27113 stmts / 219 miss / 9480 branch / 89 miss / 99%`
- 对照上切片(26-11-13 08:16, 6101+2, 另一宿主): 总收集数恒等 6103(6084+19 == 6101+2), 17 条
  通过/跳过分布在两宿主不同(环境条件 skip 组); 本批 pytest 面零改动(纯 e2e 测试面 + 文档), 分布
  差非本批引入

e2e 面(同批实测, 非本切片口径的誊写源, 供追溯): `npm run test:e2e:fast` **356P/0F/flaky 0/40.6m**
(原假红场景 349P/1F/44.8m 复跑全绿); dt-live-update.spec.mjs 静机单跑 14/14(1.9m);
红验注入 130ms 双皮红 / 63ms 双皮绿。

## 本改动面

- `e2e/dt-live-update.spec.mjs` — #10/#11 longtask 预算断言 `lt.length === 0` → 量级口径
  `Math.max(0, ...lt) < LT_REGRESSION_MS(=100)`(单点常量 + 锚点注释); 文件头 docstring 与
  W1 注释块同步。零生产代码改动, 纯测试面。
- `memory-bank/testing/flaky-ledger.md` — 台账 +1 行(time(边界/粒度), Done, 去向 0519)。
- `memory-bank/pitfalls/testing/timing-tolerance.md` — 复发 3→4, 新增 ④(longtask 计数零容差 →
  量级口径; 归一化不适用的判别), 触发词补 longtask/长任务/PerformanceObserver/窗口内计数。
- `memory-bank/pitfalls/testing/longtask-redverify-page-task.md` — 新档(CDP evaluate 忙等不计
  longtask, 红验注入必须页面自调度任务)。
- `memory-bank/issues/26-11-13-0519-...html` — §07 复验 + 修复后补充, 状态 Open → Done。
