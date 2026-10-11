# 种子详情面板重构 · W7 恢复波已落地(W5/W6 越权撤销)

> 摘要: 用户裁定 **W5(变体退役)/W6(选择层退役)属计划越权** —— 计划正主只有 W2「三列表接表壳」(表格与主表能力统一), 从未授权动模板; 指令「全部模板原样找回」。W7(本轮 26-10-12-0340)按考古恢复法执行: 15 个变体(`drawer_tpl/`)自基座 `a05d35da` 原样恢复, `drawer_templates.js` 基座重建(头注四条有意适配), menu/state/store/app/index/三皮肤 CSS 接线面全部恢复; W2–W4 成果保留(三列表接 `<aq-table>` 表壳 / 形态判据单点 / 合并机械收 drawer.js), W5/W6 终态判据「抽屉只剩一套渲染技术」**作废**。**验收**: `test.full` **3131 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`; 全量 e2e **166 passed + 10 skipped**; 红验两条(RC1 静态落盘短路 / RC2 e2e 变体 id 破坏)均注入即红/还原即绿。重建漏项 1 处由 e2e 抓到: `dtMenuPick` 同步 `_dtSync` 在 v-if/v-else 双分支下扑空(补 `$nextTick`, 头注适配④)。
>
> 最后活动: 2026-10-12 03:40

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/testing/baselines/26-10-12-0340-webui-drawer-refactor-w7.md

## 本轮完成 (W7)

- **恢复面**: `drawer_tpl/` 15 文件 checkout 基座; `drawer_templates.js` 重建(注册表 + 挂载机械 + dtHtml/KIT/HELPERS + 菜单 computed 组, 555 行); drawer.js/menu.js/state.js/drawer_store.js/app.js/三 index/三皮肤 views.css 恢复。W6 保留项: qb_traffic_chart 判据单点、合并布局 CSS 三皮肤、W3 头部组件。
- **守阵**: panel 六删 + 基座 16 块恢复 + W2–W4 事实适配(37 全绿); error_history 写入基线回改(drawer.js 4 / drawer_templates.js 1)。
- **e2e**: 删 drawer-density.spec; 4 条变体 spec 恢复; drawer-merge/drawer-tables 反向 W5 编辑(锚改恢复语义)。
- **验收**: test.full 3131+4 / e2e 166+10 / 红验两条闭环。数字见基线切片 26-10-12-0340。

## 遗留债务(计划外, 需另开会话)

- **cap 债务**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W7 各一条); 清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**: `kb.check` 报「切片数 > 70」(每波新增切片加深)。
- **工作树**: W7 恢复波改动未提交(用户未要求 commit; W2–W6 已随 0d07dbdd 入库)。
- **esc-attr-quote-dead-class 缺陷(已关闭, 26-10-12 复核)**: 「随恢复重新存在」判定**不成立** —— 静态全扫描(16 文件字面量+插值)零坏形态, 新增运行时守阵 `e2e/lib/dt-dead-class.mjs` 钉五处、注入即红/还原即绿; 判定缺陷不存在无需修码, W2 时「15 个变体仍带缺陷」系未枚举的悲观外推。见坑档 W7 复核注。
