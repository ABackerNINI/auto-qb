# 7026 —— issue 26-11-19-0754 修复批后基线 —— _measureRowH 在案行跳过 gBCR + 字体令牌并入 reprobe 签名, 新增 node 电池与静态守阵

> 摘要: issue 26-11-19-0754 修复批后基线 —— _measureRowH 在案行跳过 gBCR + 字体令牌并入 reprobe 签名, 新增 node 电池与静态守阵
> 基线时间: 2026-11-23 13:12
**Refs:** memory-bank/issues/26-11-19-0754-perf-webui-rowmeasure-updated-rescan.html

## 验收数字

TOTAL                                                31412    108  11190     93    99%
7026 passed, 6 skipped, 1 warning in 130.37s (0:02:10)

`commands run test.full` 实测(2026-11-23 13:12, 远端合流至 5fa38d25 后, 覆盖率 99% 达标)。用例数与上一条基线持平(本轮无新增 pytest 用例; 新增守阵是对既有 node 电池的扩展与静态断言)。

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`: `_measureRowH` 主表量高循环对存值在案行 `continue` 跳过 gBCR(issue 26-11-19-0754 修法); 新增 `_rowHFontTok()` 纯读字体状态令牌并入 `_reprobeRenderedRowH` 调用签名末项(评审增强: 字体落定触发重探修正异步布局变化的陈旧存值)
- `tests/test_webui_static_r4_node_batteries.py`: 新增 node 电池 `test_r4_rowmeasure_skips_measured_rows_no_regb`(红绿双验, 修正版 5/5 + strip 版反证); reprobe 电池加 2 项字体令牌断言(22→24); zoom 电池 2 项 gBR 期望随新行为更新(N→0)
- `tests/test_webui_static_dom_page_layout.py`: `test_frontend_outgoing_rowh_reprobe_guard` 增第 6 面(跳过分支存在 + 顺序 + 字体令牌)
- `e2e/perf.spec.mjs` 未改: `FIRST_VISIT_GBR_BUDGET=185` 保持(回抬属放宽判据, 未授权); 动态量具实测首访 gBR 从 143–158 降到 80(600 档双皮)
- 评审 2 轮零 actionable; issue 26-11-19-0754 翻 Done; 未 commit/push(用户未授权)
