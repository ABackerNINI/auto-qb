# 3131 —— WEBUI 抽屉重构 W7 恢复波(26-10-11-2106 计划, 修正波)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-12-0255-webui-drawer-refactor-w6.md

> 摘要: 用户裁定 W5(变体退役)/W6(选择层退役)**计划越权**(计划正主只有 W2「三列表接表壳」, 从未授权动模板), W7 按「全部模板原样找回」执行恢复: 15 个变体(`drawer_tpl/`)自基座 `a05d35da` 原样恢复, `drawer_templates.js` 按基座重建(四条有意适配记头注), 接线面(menu/state/store/app/index/三皮肤 CSS)全部恢复; W2–W4 表格统一成果保留, W5/W6 终态判据作废。判据: ① `test.full` **3131 passed + 4 skipped** / `TOTAL 16517 151 5626 134 99%`(W6 3122 → +9); ② 全量 e2e **166 passed + 10 skipped**(W6 156 → +10); ③ 红验两条(RC1 静态落盘短路 → 三红 / RC2 e2e 变体 id 破坏 → 两红)均注入即红/还原即绿。
> 基线时间: 2026-10-12 03:40

计划：memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html（§11 W7 条）
上一基线：memory-bank/testing/baselines/26-10-12-0255-webui-drawer-refactor-w6.md

## 本波改动面

- **恢复**: `shared/drawer_tpl/` 15 文件 `git checkout a05d35da --`; `shared/drawer_templates.js` 基座重建
  (注册表 + `_dtMount*` 挂载机械 + dtHtml/dtRaw/KIT/HELPERS + 菜单 computed 组, 555 行)。
  头注四条有意适配(均为 W2–W4 已定案或 e2e 实测补): ① 合并机械住 drawer.js(本层只经
  `window.AQB_DRAWER_MERGE.pairOf` 机械消费); ② 「经典」住 Vue 组件(`dtVueTab` v-if/v-else 双分支);
  ③ 00-core 注入只余 `.dt-tpl` 限宽; ④ `dtMenuPick` 落盘后 `$nextTick` 再 `_dtSync`。
- **接线恢复**: drawer.js(密度层删 + 菜单四件/方法五件删 + 双监听 + closeDrawer `_dtUnmountAll`);
  menu.js(宿主 `data-dt-host` 优先分支); state.js(drawerVisible 种子支路 `$nextTick` 重挂);
  drawer_store.js(四 fetcher `_dtNotify` + `_loadDrawerTab` 尾 `_dtSync`); app.js(`app.mixin(AQB_DRAWER_TPL)` 恢复);
  三份 index.html(drawer_templates.js + 15 变体装载行); 三皮肤 views.css(`.dd-compact` 密度段删);
  tpl/drawer.html(宿主 x6 + traffic 双宿主 + 合并列 dtVueTab 双分支 + `:data-dt-tab` 动态绑定);
  tpl/drawer-tabs.html(组件根去密度类)。
- **W6 保留项**(不随撤销回退): `qb_traffic_chart.js` 吃 `drawerIsTraffic`/`drawerIsSeed` 判据单点;
  合并布局 CSS 在三皮肤; W3 头部组件 aq-drawer-head。
- **e2e**: 删 `drawer-density.spec.mjs`; 恢复 4 条变体 spec(dt11-sticky / peers-columns / peers-sticky-flush /
  trackers-reannounce); drawer-merge / drawer-tables 反向 W5 编辑(右键模板选择 / 锚点解析回归, 锚按恢复语义改:
  经典态宿主 v-else 不渲染 → `toHaveCount(0)`)。

## 验收数字

- `test.full`: **3131 passed + 4 skipped** / 覆盖率 `TOTAL 16517 151 5626 134 99%`
  (W6 基线 3122 → +9: `test_drawer_tpl_facility_retired` 退役, 基座变体守阵九函数回归
  〔width_discipline / field_icons / scrollleft_restore / per_tracker_reannounce / roving /
  no_singleton_shadowing / cross_seed_fold / render_error_fallback / seed_reentry_variant_remount〕)。
- 全量 e2e: **166 passed + 0 failed + 10 skipped**(W6 基线 156 → +10 = 恢复变体 spec 用例 × 皮肤)。
  首轮曾 5 failed: 4 条 = `dtMenuPick` 同步挂载扑空(重建漏项, 补 $nextTick 修复); 1 条 trigger-scope 时序
  flaky, 单跑复绿。
- 红验两条均「注入即红 / 还原即绿」:
  - RC1 静态: `dtPersistSel` 落盘短路 → `test_webui_error_history`(写入基线) +
    `test_drawer_tpl_classic_default` + `test_drawer_tpl_render_error_fallback_classic`(两 node 电池)三红;
  - RC2 e2e: 变体 06 register id `"06"`→`"XX"` → drawer-tables 锚点解析两皮肤红。
- 终态: 抽屉回到「经典 Vue 组件 + 变体字符串 DOM」双实现并存, 模板能力全量找回
  (dt06 逐行汇报倒计时等变体独有能力回归)。

## 守阵同轮改版清单(tests/test_webui_static_dom_panel.py, 收集 37)

- 删 W6 版六块: registry_wiring(退役版) / facility_retired / a11y(W5 收敛版) / menu_right_click(W6 版) /
  classic_default(W6 版) / `_DT_DENSITY_NODE_PROBE`; 自基座恢复 16 块变体守阵。
- 恢复块的 W2–W4 事实适配: menu 放行判据 `!drawerIsSeed && !drawerIsTraffic`; close 钮单点在
  aq-drawer-head; page_guard 种子支路 `$nextTick` 形态; form_judge 钉 drawer_templates.js(6 空格)+ drawer.js
  计数 2; wiring 钩子段读 drawer_store.js + `:data-dt-tab="col.tab"` 动态绑定单点 + 合并成员住 drawer.js
  (核心层 pairOf 机械消费合法); reannounce ④ 三变体断言面与 tooltip I 组变体条目回归。
- `test_webui_error_history.py`: `STORAGE_WRITE_BASELINE` 回改 —— drawer.js 5→4, drawer_templates.js 新增 1
  (`dtPersistSel` 随选择层恢复)。
