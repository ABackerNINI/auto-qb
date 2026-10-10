# 2886 —— 面板页签合并 R3 修订(合并页签)基线

> 摘要: 用户报「合并开启后切到另一对页签显示错乱(选择 常规+内容 并排后, tracker/用户标签显示"常规"/"内容"且为空)」且「标签页没有合并」—— 拍板"合并为两个页签"后改版: 开关模型 `off|gc|tp` → `off|on`, 双列列组与生效判据统一读 `dtPair`(修掉 R2 空列 bug 根因: 模板按标志值渲染固定一对, 与当前页签脱节), 页签栏在门内收敛为 `[常规&内容][Tracker&用户]` 两合并页签(可自由切换), 右键两项互斥勾选改单开关 `dtToggleMerge`(`dtSetMerge` 退役)。守阵 + e2e 同步。
> 档案: memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md
> 基线时间: 2026-10-10 11:37

**Refs:** memory-bank/plans/26-10-09-2219-plan-webui-drawer-merge-tabs.html,memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md

## test.full 实测

- 分支: `develop`(`cebfdcc4`, 会话开工同步所得; 工作树含本改版 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2886 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 收集面差异说明: pytest 用例数逐位持平 —— 本轮守阵为**断言面更新**(`test_drawer_tpl_registry_wiring` 增 R3 钉子: 禁 `dtSetMerge` 残留 / 合并页签标签 / `:data-merge="dtPair"`; `test_webui_error_history.py` 计数说明更新, 计数仍 2), 未新增/删除 pytest 用例函数; e2e `e2e/drawer-merge.spec.mjs` 重写为 4 用例(含"切对页签不再空列"回归), 不入 pytest 覆盖面。
- e2e 实测: `drawer-merge.spec.mjs` 4 passed; `npm run test:e2e:fast` 42 passed。
- 增量明细(本轮真正改动): `shared/` = **drawer_templates.js**(开关模型收敛 `off|on` + 新增 computed `dtMergeOn`/`dtMergeTabsOn`/`dtPair` + 方法 `dtMergeTabActive`/`dtMergeTabPick`/`dtToggleMerge`, `dtSetMerge` 退役, `dtSplitOn` 改读 `dtPair`)+ **state.js**(注释)+ **app.js**(`initialDrawerMerge` 白名单 `off/on`, 旧值 gc/tp 迁 `on`)+ **tpl/drawer.html**(页签栏两合并页签 + 双列列组 `:data-merge="dtPair"`)+ **tpl/ctx-menus.html**(两项互斥勾选 → 单开关); 守阵 `tests/test_webui_static_dom_panel.py` / `tests/test_webui_error_history.py`; 知识库回写件(主题文档 / progress / activeContext / 计划 R4 变更记录 / 本切片)。
- `src/` 后端零改动。Linux(WSL 沙箱)侧未重测 —— 本轮只改平台无关的前端静态 JS 与断言面, 未改平台相关代码(口径见 baseline.md 常驻警告; 与近几轮切片同处理)。
