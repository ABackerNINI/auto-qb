# 26-10-09-webui-drawer-collapse-removal — WEBUI 种子详情面板折叠状态整体移除

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Summary:** 用户动议移除种子详情面板(底部停靠抽屉)的折叠状态 —— `drawer.collapsed` 字段、收起/展开钮、44px 收起态头部摘要条、收起态鼠标换目标(peek)、`toggleDrawerCollapse`、各处收起守卫与三皮肤 CSS 全部摘除; 收起态专供的核心摘要管线(dtSummaryHtml/_dtDefaultSummary/注册表 summary 槽)与 7 个变体的 `summary()` 同撤(全成死代码); 面板行为回归纯「开/关 + 拖拽调高」; 两份守阵文件同步改写, test.full 绿(基线见 Refs)。

**Refs:** memory-bank/testing/baselines/26-10-09-2044-webui-drawer-collapse-removal.md
**Topics:** drawer-dock

## 原始请求

> WEBUI移除种子详情面板的折叠状态

## 思考过程与决策

- **判定范围**: 折叠状态(`drawer.collapsed`, 收起 = 只留 ~44px 头部)是一条贯穿前端的功能链, 不是单个开关 —— 状态字段 / 模板钮 / 摘要条 / 收起态鼠标换目标(peek)/ 各挂点收起守卫 / CSS / 守阵测试全要动。`drawer_tpl/*-collapsed.js` 的「collapsed」是设计稿档位命名(tall/low/collapsed 物理形态), 与本功能无关, **不涉及**(守阵 Q4 也钉了这一点)。
- **摘要条管线一并撤的理由**: `.dt-summary` 摘要条只在收起态渲染(`v-if="drawer.collapsed"`), 核心层 `dtSummaryHtml`/`_dtDefaultSummary`、注册表 `entry.summary` 槽、7 个变体(03/06/09/10/11/12/15)的 `summary()` 函数与其 dtXX-cs CSS 全是它的供数链 —— 折叠移除后全成死代码, 按「删死代码/删模板连带清 CSS」纪律一并清(符合 template-render 坑档口径)。
- **保留面**: `persistDrawerOpen`(autoqb.ui.drawerOpen 只写不回读)保留但条件简化为只看 `drawer.open`; D1「首屏默认关闭」语义不变(原「首屏默认收起」里的收起即关闭)。
- **孤儿助手**: 变体 06 的 `countsOf`、09 的 `BUCKETS` 仅被已删 summary 引用, 一并删; 03 的 STATE_TEXT/SEEDING_STATES/present 与 09 的 bucketOf 等仍被 render 消费, 保留(grep 引用数核对)。
- **守阵处置**: `test_frontend_drawer_collapsed_click_peek_target` 整函数删(钉的就是被移除的行为); `test_drawer_height_collapse_w3` 改名 `test_drawer_height_w3` 并删收起断言; dt-select 定宽守阵删 .dt-summary 段; aria 守阵删 fold 钮; 模块索引条目同步。

## 实现计划

1. 核心逻辑: state.js / drawer.js / selection.js / shortcuts.js / qb_traffic_chart.js 摘除 collapsed 与 peek。
2. 模板与样式: tpl/drawer.html 删 fold 钮 + 摘要条 + collapsed 类; 三皮肤 CSS 删 `.drawer.collapsed` 与 `.drawer-fold`; drawer_templates.js 删摘要管线。
3. 变体: 7 个变体删 `summary()` + dtXX-cs CSS + 注册行, 头注标明收起档已移除。
4. 守阵: 两份测试文件同步; node --check 全部 JS; `commands run test.full` 记基线。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 核心逻辑摘除(5 文件) | ✅ |
| 模板/CSS/核心层摘要管线摘除 | ✅ |
| 7 变体 summary 供数链摘除 | ✅ |
| 守阵同步(test_webui_static_dom_panel / test_web_shortcuts) | ✅ |
| 事实回写(pitfalls×2 / progress / activeContext×2) | ✅ |
| test.full 基线切片 | ✅ |

## 进度日志

- **2026-10-09**: 开工先 `my-commit-flow.sync` → 已同步 `11c40a9a`。摸底: grep `collapsed|toggleDrawerCollapse|_drawerPeek|dt-summary|drawer-fold|__peek` 全 src, 确认无第二副本。三轮编辑(核心逻辑 → 模板/CSS/管线 → 变体)完成, node --check 全绿; 守阵改写后 py_compile 绿; `test.full` 2870 passed + 4 skipped。dt12 两处过时注释修正后复跑 test.full 记最终基线(见 Refs 基线切片)。知识库回写: drawer-switch-flicker「收起态重按 = 展开」尾巴标注已随折叠移除; dock-panel 收起措辞摘除; 26-10-09-0740 切片未验证面②标注不再适用; progress/implemented-webui.md 新条目。改动 20 个源文件(19 代码/测试 + 回写件), 命中立档阈值(≥3 源文件)。
