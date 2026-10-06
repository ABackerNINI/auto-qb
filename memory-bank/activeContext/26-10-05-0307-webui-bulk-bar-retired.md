# 批量控制条退役 — 批量动作统一走右键菜单

> 摘要: 用户拍板移除 WEBUI 筛选行里的"已选 N 个种子 · 开始/暂停/…"批量控制条, 批量动作一律走右键批量菜单
> (被右键行属于选中集合时升级为 menu.multi 分支)。三套 UI(atlas/prism/console)成对清理: 共享模板 topbar.html 删控制条 +
> 状态条 v-if 去掉 selectedCount 冗余项; 三套 CSS 删 .bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/
> .bulk-enter-*/.ico-select/@keyframes bulk-in; delete_flow.js 删死方法 bulkHrWarnText/bulkDeleteLabel
> (保留 bulkAct/bulkDelete/bulkCountText 供右键菜单); ui_smoke.cjs P0-4 入口改走右键菜单。新守阵
> test_frontend_bulk_bar_retired。test.full 2542 passed + 4 skipped / 99% / 49.79s (基线
> [26-10-05-0307](../testing/baselines/26-10-05-0307-webui-bulk-bar-retired.md))。
> 最后活动: 2026-10-05 03:07

**Refs:** memory-bank/tasks/26-10-05-webui-bulk-bar-retired.md, memory-bank/testing/baselines/26-10-05-0307-webui-bulk-bar-retired.md

## 现状

- 全部实施完成(单会话)
- 改动面: 1 模板(topbar.html) + 6 CSS + 7 JS + 1 冒烟脚本(ui_smoke.cjs) + tests/test_web.py + conventions/webui.md + testing/smoke.md + 本切片/档案/基线。
- 待用户侧动作: 真机走查(三皮肤: 选中行右键出批量菜单 / Esc 清选择) + 提交。
