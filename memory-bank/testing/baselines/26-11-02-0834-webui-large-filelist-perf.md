# 4825 passed + 10 skipped —— WEBUI 大文件列表性能优化 验收修复轮终态: 4825 过/10 跳/1 认领链入库自愈红, 覆盖率 99.00%

> 摘要: WEBUI 大文件列表性能优化 验收修复轮终态: 4825 过/10 跳/1 认领链入库自愈红, 覆盖率 99.00%
> 基线时间: 2026-11-02 08:34
**Refs:** memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html, memory-bank/testing/baselines/26-11-02-0707-webui-large-filelist-perf.md

## 验收数字

`commands run test.full` 实测(2026-11-02 08:3x, 工作区未提交态, 含验收修复轮改动):

- 汇总行: `1 failed, 4825 passed, 10 skipped in 216.99s (0:03:36)`
- 覆盖率: TOTAL 22521 stmts / 152 miss, 分支 7726/135 miss, **99.00%**(门槛 99% 达标)
- **唯一 failed** = `tests/test_docs_forms.py::test_claim_chain_is_bidirectional`: 本轮计划/报告/档案/基线等制品互相引用且未 git 追踪, 认领链机检只认 git 可见文件 —— **随本专题入库自愈**, 与代码改动无关。
- 相对上一切片 26-11-02-0707(见 kb.baseline): +1 过(验收修复轮新静态守阵), 覆盖率持平。

e2e 数字(同一树, W4/W5/验收修复轮实测): `window-invalidation` 6/6(三皮肤×2) + `drawer-content-perf` 8/8 + `dt-live-update` 14/14 + `perf` 10/10。千级 longtask: 切页/关抽屉修复后 0(修复前 5.8~8.4s/5.6s)。真机轨 fail-closed 未跑(token 未注入)。

## 本改动面

- `webui/static/shared/columns.js` — 验收修复: `_measureRowH` 行高签名去 viewMode 因子(只留 resize/列集合两真变化因子) + `_winCtnSync` 加抽屉收场期守卫(过渡期 clientWidth 不可采信); 连同前轮: WIN_SOURCES kind 描述符 + winSrcContainer + drawerContent 接线 + 容器族引擎态分家 + _measureRowH 第四探测位
- `webui/static/shared/drawer_tpl/10-content-tree-detail-tall.js` / `11-content-treegrid-batch-low.js` — 行对象按 path 记忆化 + sig 廉价指纹(31 进制滚动指纹替代 JSON.stringify) + O(D×F) 装配消除
- `webui/static/shared/drawer_templates.js` — drawerWinView computed + dtWinRows/dtWinPad/dtBridgeLines/dtWinKbd
- `webui/static/shared/app.js` — drawerContentV10/V11 window: null → "drawerContent" + ROW_WIN_EST_H.drawerContent:27
- `webui/static/shared/tpl/xtpl.html` — 桥 v-for 切 dtBridgeLines + aq-row-pad 占位 + .group-table @keydown
- `webui/static/shared/dt_table.css` — 抽屉行容器 content-visibility:auto + contain-intrinsic-size
- `tests/test_webui_static_dom_panel.py` — 行记忆化/廉价 sig 守阵
- `tests/test_webui_static_dom_page.py` — kind 描述符守阵(W2 建 W3 同步) + 行高签名/ctnSync 守卫守阵(验收修复轮)
- `tests/test_webui_static_skins.py` — 桥接线守阵同步(dtBridgeLines 单点)
- `e2e/dt-live-update.spec.mjs` — 量具 settle 竞态修复 + A/B 口径收紧 + 千文件桩
- `e2e/drawer-content-perf.spec.mjs` — 新增千级验收 spec(8 test 全矩阵)
- `e2e/perf.spec.mjs` — 主表×抽屉同屏交叉 2 条
- `e2e/window-invalidation.spec.mjs` — 新增切页不重置行窗/关抽屉不假 bump 守阵(6 test, 三皮肤)
