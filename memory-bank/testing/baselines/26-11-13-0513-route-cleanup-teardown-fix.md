# 6077 passed, 19 skipped, 7 warnings in 123.57s (0:02:03) | 覆盖率 99% (TOTAL 27113 219 9480 89 99%) | TZ=Asia/Shanghai(本机 America/Los_Angeles 撞已入池 TZ 用例 26-11-12-2347 逃生门) + PATH 补 ~/.local/node/bin(node 电池依赖) | develop@56b0a82e + 未提交批(route-cleanup 修复面) —— test.full 基线: route-cleanup 收尾竞态修复批次

> 摘要: test.full 基线: route-cleanup 收尾竞态修复批次
> 基线时间: 2026-11-13 05:13

## 验收数字

实测(2026-11-13, clone2 本机, develop@56b0a82e + 未提交批):

```
TOTAL                                                27113    219   9480     89    99%
6077 passed, 19 skipped, 7 warnings in 123.57s (0:02:03)
```

环境注记: `TZ=Asia/Shanghai`(本机 America/Los_Angeles 撞已入池 TZ 用例 26-11-12-2347, 逃生门同 issue 自证) + `PATH` 补 `~/.local/node/bin`(node 电池依赖, 本工具 shell 不加载 zshrc)。同轮 e2e 实测(非本切片口径, 详见 issue 26-11-13-0234 §07): 锚点 spec repeat-each=3 18/18、6 接线 spec 28/28、fast 全量 349P/1F(1F = dt-live-update 产量具预算负载假红<strong>候选</strong> [26-11-13-0519](../../issues/26-11-13-0519-test-e2e-dt-live-update-longtask-budget-flake.html), 静机单跑 14/14 复绿)。

## 本改动面

- 新增 `e2e/lib/route-cleanup.mjs`: `installRouteCleanup(test)` 单点兜底(file 级 afterEach `page.unrouteAll({ behavior: 'ignoreErrors' })`)。
- 8 个 e2e spec 顶层接线: traffic-source-switch / ctx-custom / settings-bt-backup / traffic-gap-zones / gtm-alert / drawer-general-variants / drawer-trackers-reannounce(issue 26-11-13-0234)、drawer-merge(评审轮守阵点名上游新增调用位后补接)。
- `tests/test_flaky_timing_guards.py`: 扫描器 5(`scan_route_fetch_unwired`, 违例侧调用位原文/接线侧剥注释判**文件顶层**调用形态)+ 全仓守卫 + lib 本体静态钉 + 八形态活性探针; docstring 升五类(评审 6 轮 20 发现全修)。
- 文档: issue 26-11-13-0234 翻 Done(复验行 + 修复后补充)、`testing/flaky-ledger.md` 登记行、新坑档 `pitfalls/testing/route-callback-teardown-race.md`。
- 生成物: `pitfalls/testing/_index*.md`(kb.index/kb.wrap 再生)。
