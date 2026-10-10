# 26-10-05-webui-bulk-bar-retired — WEBUI 批量控制条退役(批量动作统一走右键菜单)

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05
**Summary:** 用户拍板移除筛选行里的"已选 N 个种子 · 开始/暂停/…"批量控制条, 批量动作一律走右键批量菜单(被右键行属于选中集合时升级为 menu.multi 分支)。三套 UI(atlas/prism/console)成对清理: 共享模板 topbar.html 删控制条 + 状态条 v-if 去掉 selectedCount 冗余项; 三套 CSS 删 .bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/.bulk-enter-*/.ico-select/@keyframes bulk-in; delete_flow.js 删死方法 bulkHrWarnText/bulkDeleteLabel(保留 bulkAct/bulkDelete/bulkCountText 供右键菜单); ui_smoke.cjs P0-4 入口改走右键菜单。新守阵 test_frontend_bulk_bar_retired。基线 26-10-05-0307: 2542 passed + 4 skipped / 99% / 49.79s。
**Topics:** webui-bulk-bar-retired
**Refs:** memory-bank/testing/baselines/26-10-05-0307-webui-bulk-bar-retired.md

## 原始请求

用户: "WEBUI移除选择种子后的控制栏"已选?个种子 开始 暂停 ...", 其功能由右键菜单替代, 注意有3套UI"。

## 思考过程与决策

- **替代关系已成立**: 右键批量菜单(ctx-menus.html `menu.multi` 分支, 计划 26-10-02-1955 落地)已是批量动作的**超集** —— 含 开始/暂停/汇报/校验/跳检/限速/移动/标签分类/导出/删除, 比原控制条还多 跳检/限速/移动/导出 四项。故控制条纯属重复入口, 直接删除, 无需往右键菜单补动作。
- **"清除"按钮**: 原控制条的"清除选择"不在右键菜单语义内; 清除选择已有 Esc 通道(lifecycle.js 退栈兜底 + shortcuts `clear-esc`), 无需补入口。
- **状态条显隐**: `.status-strip` 的 v-if 原含 `|| selectedCount`(为控制条占位)—— 去掉; 分布条/筛选器由 distTotal 与 viewMode 决定, 不受影响。
- **三套 UI**: 模板是共享的(static/shared/tpl/topbar.html), 但 CSS 按 UI 分片(atlas/prism/console)—— 三套 CSS 都要删, 否则某套皮肤残留死样式; 守阵按 `_UI_ALL` 三档钉零残留。
- **死代码处置**: bulkHrWarnText(HR 风险计数)/bulkDeleteLabel(删除按钮文案)只被控制条消费, 随控制条删除; bulkCountText 仍被 bulkDelete(右键批量删除确认框)消费, 保留。

## 实现计划

1. topbar.html 删 `.bulk-inline` 块 + status-strip v-if 去 selectedCount;
2. 三套 CSS 删死样式(.bulk-inline/.bulk-btn/.bulk-count/.bulk-sep/.bulk-hr-warn/.bulk-enter-*/.ico-select/@keyframes bulk-in);
3. delete_flow.js 删死方法; commands.js/selection.js/menu.js/dialogs.js/shortcuts.js 注释口径 批量浮条→批量动作;
4. tests/test_web.py 两处守阵适配 + 新增 test_frontend_bulk_bar_retired;
5. scripts/ui_smoke.cjs P0-4 入口改走右键批量菜单。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 模板删除(topbar.html 控制条块 + status-strip v-if) | Done |
| S2 | 三套 CSS 死样式清理(atlas/prism/console) | Done |
| S3 | JS 死方法删除 + 注释口径改"批量动作" | Done |
| S4 | 守阵适配 + 新增防回潮守阵 test_frontend_bulk_bar_retired | Done |
| S5 | 冒烟脚本 P0-4 改走右键批量菜单 | Done |
| S6 | 全量测试 + 基线切片 + 文档回写 | Done |

## 进度日志

- **2026-10-05 03:07**(单会话完成): S1-S6 全量实施。改动面 = 1 模板(topbar.html) + 6 CSS + 7 JS + 1 冒烟脚本(ui_smoke.cjs) + tests/test_web.py + conventions/webui.md + testing/smoke.md。test.full **2542 passed + 4 skipped / 99% / 49.79s**(两次采样约 50~53s; 基线 [26-10-05-0307](../testing/baselines/26-10-05-0307-webui-bulk-bar-retired.md))。改动留在工作树, 等用户显式提交指令。
