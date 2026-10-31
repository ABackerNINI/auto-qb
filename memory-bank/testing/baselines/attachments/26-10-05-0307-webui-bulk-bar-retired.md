# 基线切片 26-10-05-0307 — 批量控制条退役 (批量动作统一走右键批量菜单)

> 摘要: 用户拍板移除 WEBUI 筛选行里的"已选 N 个种子 · 开始/暂停/…"批量控制条, 批量动作一律走
> 右键批量菜单(被右键行属于选中集合时升级为 menu.multi 分支)。三套 UI(atlas/prism/console)成对清理:
> 共享模板 topbar.html 删控制条 + 状态条 v-if 去掉 selectedCount 冗余项; 三套 CSS 删
> .bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/.bulk-enter-*/.ico-select/@keyframes bulk-in;
> delete_flow.js 删死方法 bulkHrWarnText/bulkDeleteLabel(保留 bulkAct/bulkDelete/bulkCountText 供右键菜单);
> ui_smoke.cjs P0-4 入口改走右键菜单。新守阵 test_frontend_bulk_bar_retired 钉三套 UI 模板/CSS 零残留。
> 实测 2542 passed + 4 skipped / 99% / 49.79s。
> 基线时间: 2026-10-05 03:07

**Refs:** memory-bank/tasks/26-10-05-webui-bulk-bar-retired.md, memory-bank/activeContext/26-10-05-0307-webui-bulk-bar-retired.md

- 分支: develop @ ff71cf63 (+ 本轮未提交改动: 1 模板 + 6 CSS + 7 JS + 1 冒烟脚本 + tests/test_web.py + 2 文档 + 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2542 passed + 4 skipped, 49.79s (引擎计 51.3s), 覆盖率 TOTAL 99%**
  (14871 语句 / 152 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
  —— 本轮两次采样 49.79s / 51.29s(引擎 51.3s / 52.8s) ⇒ 耗时区间约 50~53s。
- 靶向 (tests/test_web.py `-k "bulk_bar_retired or meta_dialog_paired or ctx_menu_multi_select or hr_safety_wiring"`):
  **4 passed**。新守阵 test_frontend_bulk_bar_retired 逐套 UI 断言模板零残留(.bulk-inline/bulkAct(/
  bulkDeleteLabel(/bulkHrWarnText() 与 CSS 死样式零残留(.bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/
  .bulk-count/.bulk-enter-*/.ico-select/@keyframes bulk-in), 并断言批量链路 bulkAct/bulkDelete 仍在且 ctxAct 复用。
- 相对上基线 (26-10-05-0252: 2541 passed + 4 skipped / 99% / 28.49s): passed **+1** = 本轮新守阵
  test_frontend_bulk_bar_retired; skip 集合不变(Windows 侧 4 条 POSIX 专属); 源语句数不变 14871
  (改动只在前端静态资源 html/css/js + 测试, 不在 src 的 .py, 故 src 语句/覆盖率口径不动)。
- 改动面: src/auto_qb/webui/static/shared/tpl/topbar.html(删控制条块 + status-strip v-if 去 selectedCount)
  · atlas/css/{views,components,dialogs}.css · console/css/views.css · prism/css/{base,views}.css(删控制条死样式)
  · shared/{delete_flow,commands,selection,menu,dialogs,shortcuts}.js(删死方法 + 注释口径 批量浮条→批量动作)
  · shared/tpl/ctx-menus.html(注释) · tests/test_web.py(新守阵 1 条 + hr_safety_wiring/meta_dialog_paired 两处适配)
  · scripts/ui_smoke.cjs(P0-4 改走右键批量菜单) · memory-bank/conventions/webui.md · memory-bank/testing/smoke.md。
