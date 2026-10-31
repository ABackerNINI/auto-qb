# 种子详情面板重构(字符串 DOM 变体 → Vue 面板) · W6 已落地(全计划 Done)

> 摘要: 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 **D1–D4 一律取推荐项 A**。W0 冻结基线; W1 数据层抽离(A/B dump 逐字节等价); W2 四页签 Vue 重建 + 三列表接壳; W3 流量页签与形态收敛; W4 合并双列收单一状态源; W5 变体退役与声明式密度档。**W6**(本轮 26-10-12-0255, 最后一波)= **收口与退役**: 选择层 `drawer_templates.js` 整文件删除, 余下四件收进 `drawer.js`(密度档单点 / 读侧归一 / 菜单与显隐判据并入 AQB_DRAWER mixin —— app.js 删第二份 mixin 注入); 00-core + 00-density 密度 CSS 迁三皮肤(规则逐条未改), `dtInjectCss` 注入单点退役; **W3 停手点兑现** —— `qb_traffic_chart.js` 三挂点谓词 / qbCurScope / openDrawerTraffic 短路改吃 `drawerIsTraffic`/`drawerIsSeed` 单点, 全仓 `drawer.kind` 字面量只剩两个定义处; 三份坑档(variant-singleton-shadow / vif-host-node-stale / drawer-switch-flicker)加退役注。`test.full` 3122 passed + 4 skipped(与 W5 逐位同, 零测试增删) + e2e 156 passed + 红验两条(RC1 迁移错 → node 电池红 / RC2 皮肤 CSS 缺失 → wiring 红)均注入即红/还原即绿。**终态判据达成: 抽屉只剩一套渲染技术**(四页签正文恒 Vue 组件, 变体/插件/注入设施零残留, 坑档守阵零悬空)。计划 doc-status → Done。
>
> 最后活动: 2026-10-12 02:55

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/testing/baselines/attachments/26-10-12-0255-webui-drawer-refactor-w6.md

## 本轮完成 (W6)

- **选择层收编**: `drawer_templates.js` 删除; `drawer.js` 新增「模板选择层」段 —— `window.AQB_DRAWER_DENSITY`(DTPL_TIERS/DTPL_DENSITY/options·tierOf·normalize, 局部量形态防 mixin 误判)+ `window.AQB_DRAWER_TPL_REG`(readSel 白名单 + 旧 id 迁移)+ 四 computed(dtMenuTab/dtMenuTplOptions/dtMenuTplCurrent/dtMenuMergeOn)与五 methods(_dtCurTab/dtHostOn/drawerTier/dtMenuPick/dtPersistSel)并入 `AQB_DRAWER` mixin。app.js 删 `app.mixin(window.AQB_DRAWER_TPL)`; 装载序硬约束改 drawer.js < state.js。
- **CSS 迁三皮肤**: 合并 CSS(`.drawer-split`/`.dt-col`/`.dt-col-head`/`.dt-host:empty`/`.dt-traffic-main`)与密度 CSS(`.dd-compact` 族)迁三皮肤 views.css; `.ctx-menu .ctx-item.is-gated` 迁 components.css; atlas components.css 贴 700 行上限(注释压行尾净增 2 行贴线过闸)。
- **W3 停手点兑现**: `qb_traffic_chart.js` 全量吃形态判据单点(三挂点谓词 / qbCurScope / openDrawerTraffic 短路)。
- **守阵同轮改版(不放宽, panel 收集 28)**: wiring(反转+换家+皮肤 CSS 成对断言)/facility_retired(文件级退役+注入负 pin+皮肤密度段禁令)/menu_right_click/classic_default(node 电池加载 drawer.js)/form_judge(摘 W3 豁免钉四件)/page_guard(短路改单点)/error_history(写入基线 drawer.js 4→5 合法演化)。
- **验收**: `test.full` 3122 passed + 4 skipped / TOTAL 16517 151 5626 134 99%(与 W5 逐位同); e2e 156 passed + 10 skipped(与 W5 基线同 —— 本波只换实现落点不换行为); 红验两条注入即红/还原即绿。

## 遗留债务(计划外, 需另开会话)

- **cap 债务**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W6 各增一条); 清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**: `kb.check` 报「切片数 > 70」(每波新增切片加深)。
- **工作树**: W2–W6 五轮改动均未提交(用户未要求 commit)。
- **dt06 逐行汇报倒计时**: 变体独有能力随 W5 退役消失, 若用户需要该口径须在经典列表加列(新需求)。
