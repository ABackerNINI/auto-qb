# 26-10-06-webui-detail-panel — WEBUI 种子详情面板重构 · 设计模板轮

**Status:** In Progress
**Added:** 2026-10-06
**Updated:** 2026-10-06
**Topics:** webui-detail-panel-redesign
**Summary:** 设计模板轮闭环: 针对下方面板三痛点(常规页右侧大块留白 / Tracker·用户·内容裸表格无设计感 / 收起态疑似无用)产出 15 份可交互单文件模板(五页 general/trackers/peers/content/traffic × 高·矮·收起三方向, prism ocean 令牌, 每份内置三档高度切换) + `_brief.md` 调研简报 + 汇总报告 26-10-06-0723(内含收起态论证: 有实际作用但反馈弱, 附三条补强点; 逐页推荐供拍板); Playwright 真实浏览器逐份三档+交互全过。用户逐页选型后另立 plan 实施 drawer.html/drawer.js/三皮肤 CSS。未 commit 等用户指令。
**Refs:** memory-bank/reports/26-10-06-0723-report-webui-detail-panel-redesign.html

## 原始请求

用户命题(详情面板从右侧抽屉改为底部停靠面板之后):

1. **常规页右边空一大块** —— 沿用旧竖向排版(分组卡片 + 单列 label/value 行), 面板改下方后宽度拉满列表宽, 行高堆叠导致右侧大量留白, 信息密度极低。
2. **Tracker/用户/内容三页没设计感** —— 近乎裸 `<table>` 平铺, 无分组、无层级、无状态可视化, 与主列表设计水准脱节。
3. **收起状态疑似没有实际作用** —— 要求代码级论证。

要求逐页出可交互 HTML 设计模板供用户选型拍板。

## 思考过程与决策

- **收起态论证(报告 §收起状态论证)**: 正面证据 —— 收起真实回收头部空间(约 44px), 机制存在; 反面证据 —— 反馈极弱, 且持久化是死数据(只写不回读、重开重置)。结论: **收起有实际作用, 但需三条补强**: ①持久化回读 ②收起态点页签自动展开 ③收起态头部摘要化。三条写进报告「补强建议」供实施轮采纳。
- **模板族形态**: 15 份 = 五页(general / trackers / peers / content / traffic) × 三方向(高 tall=信息全景 / 矮 low=卡片紧凑 / 收起 collapsed=表格化); 统一口径 —— prism ocean 令牌、单文件自包含、dark 主题(模拟真实产品 UI), **每份内置 收起/矮/高 三档高度切换**, 一份即可预览全档。
- **信息增量回收**: 模板不止重排现有字段, 顺带回收「有数据但未展示」的字段(报告 §信息增量)。
- **逐页推荐写进报告, 标注「供拍板」** —— 用户可整页采纳, 也可指定吸收组合(如 general = 02 基线 + 01 英雄行)。
- **质检中修复**: 01-12 号模板缺 `[hidden]` 规则共 12 行 —— `[hidden]` 属性会被显式 `display` 规则压掉, 单文件模板必须自带 `[hidden]{display:none}` 才能保证档位切换生效。

## 实现计划

- **设计轮(本轮, 已闭环)**: `_brief.md` 调研简报(唯一输入: 现状实现地图 / prism ocean 令牌 / 产出规格) → 15 份编号模板 01-15 → 汇总报告(论证 + 逐页推荐) → Playwright 真机质检。
- **实施轮(未开工)**: 用户逐页选型后**另立 plan**, 落地 `drawer.html` / `drawer.js` / 三皮肤 CSS; 实施会话在**本档案追加**结论与决策(一个专题一个档案, 不另新建)。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 调研简报 `resources/detail-panel-templates/_brief.md`(现状地图 / 令牌 / 规格) | Done |
| 2 | 15 份编号模板 01-15(五页 × 三方向, 三档高度切换) | Done |
| 3 | 汇总报告 26-10-06-0723(收起论证 + 逐页推荐, reports/_index.md 已登记) | Done |
| 4 | 质检: Playwright 真机逐份三档+交互全过; 修 01-12 缺 `[hidden]` 规则 | Done |
| 5 | 用户逐页选型(拍板) | Open |
| 6 | 实施轮: 另立 plan + drawer.html/drawer.js/三皮肤 CSS | Open |

## 进度日志

- **2026-10-06 07:23 设计轮完成**: 15 份模板 + `_brief.md` + 报告 26-10-06-0723 全部就位, 报告登记进 `reports/_index.md`(kb.index 已重建)。零代码改动(未动 `src/` / `config`), 未 commit 等用户指令。
- **2026-10-06 07:5x 收尾 DoD**: 新建 activeContext 切片 `26-10-06-0751-webui-detail-panel-design.md` + 本档案; 报告补 `doc-refs` 反向声明闭环认领链; `kb.docmap --check` 绿(456 份 / 250 专题, 双向闭环; `--topic webui-detail-panel-redesign` 归组报告 Done + 档案 In Progress); test.full **豁免**(零代码改动, 现役基线 `26-10-06-0713` 不变), 改跑 `test.one tests/test_memory_bank.py` 验 KB 守卫 **32 passed**。
