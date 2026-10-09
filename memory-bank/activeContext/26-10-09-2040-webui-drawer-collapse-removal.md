# WEBUI 种子详情面板折叠状态整体移除

> 摘要: 用户动议「WEBUI移除种子详情面板的折叠状态」—— 折叠状态(`drawer.collapsed`)全链摘除: 状态字段/收起钮/44px 摘要条/收起态鼠标换目标(peek)/各挂点收起守卫/三皮肤 CSS, 收起档专供的核心摘要管线(dtSummaryHtml/_dtDefaultSummary/注册表 summary 槽)与 7 个变体 `summary()` 同撤; 面板行为回归纯「开/关 + 拖拽调高」; 守阵同步(peek 守阵整函数删, D1/W3 守阵改写), test.full 绿。**正在进行**: 无 —— 本轮已完成, 随本专题入库。
> 最后活动: 2026-10-09 20:40

**Refs:** memory-bank/tasks/26-10-09-webui-drawer-collapse-removal.md

- 改动面: state.js / drawer.js / drawer_templates.js / selection.js / shortcuts.js / qb_traffic_chart.js / tpl/drawer.html / 三皮肤 CSS(console+atlas dialogs.css, prism views.css) / 变体 03·06·09·10·11·12·15 / 守阵两文件。
- 不涉及: `drawer_tpl/*-collapsed.js` 文件名是设计稿档位命名(tall/low/collapsed), 与折叠功能无关。
- 保留面: `persistDrawerOpen`(autoqb.ui.drawerOpen 只写不回读)简化为只看 `drawer.open`; D1 首屏默认关闭语义不变; 拖拽调高/高度记忆/软切换/跟随换目标全部原样。
