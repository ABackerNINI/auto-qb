# 4824 passed + 10 skipped —— WEBUI 大文件列表性能优化 W1-W5 收官全量: 4824 过/10 跳/1 认领链待提交红, 覆盖率 99.00%

> 摘要: WEBUI 大文件列表性能优化 W1-W5 收官全量: 4824 过/10 跳/1 认领链待提交红, 覆盖率 99.00%
> 基线时间: 2026-11-02 07:07
**Refs:** memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html, memory-bank/tasks/26-11-02-webui-large-filelist-perf.md

## 验收数字

`commands run test.full` 实测(2026-11-02 07:0x, 工作区未提交态):

- 汇总行: `1 failed, 4824 passed, 10 skipped in 171.64s (0:02:51)`
- 覆盖率: TOTAL 22521 stmts / 152 miss, 分支 7726/135 miss, **99.00%**(门槛 99% 达标)
- **唯一 failed** = `tests/test_docs_forms.py::test_claim_chain_is_bidirectional`: 本轮计划 HTML 引用的报告文件在盘上存在但未 git 追踪, 认领链机检只认 git 可见文件 —— 工作区未提交态所致, **提交后自愈**, 与代码改动无关(W1 起每轮 test.quick 同款红, 原因一致)。

e2e 数字(同一树, 由 W4/W5 实测, 不进本切片汇总行): `e2e/drawer-content-perf.spec.mjs` 8/8(K1+K2 × V10/V11 × prism/atlas 千文件矩阵); 主表五 spec 44/44 + perf 全量 10/10(E2E_TORRENTS=3000)。真机轨 rm08 本轮 **fail-closed 未跑**(QBT_TEST_ token 未注入), 待用户给环境后随下一轮补。

## 本改动面

- `webui/static/shared/drawer_tpl/10-content-tree-detail-tall.js` — 行对象按 path 记忆化(rowMem) + sig 廉价指纹(31 进制数值滚动指纹替代 JSON.stringify) + rowsFn/destroy 缓存生命周期
- `webui/static/shared/drawer_tpl/11-content-treegrid-batch-low.js` — 同款记忆化/廉价 sig + O(D×F) 装配消除(ck 前缀归并落账, subtreeFiles 全表 filter 退役)
- `webui/static/shared/dt_table.css` — 抽屉行容器 content-visibility:auto + contain-intrinsic-size(dt10 29px / dt11 27px)
- `webui/static/shared/columns.js` — 窗口化 kind 描述符参数化(WIN_SOURCES 注册表 + winSrcContainer 容器型工厂 + _winSrc 回落文档型) + drawerContent kind 接线(容器族引擎态 _winCtnState 与文档对分家) + _measureRowH 第四探测位
- `webui/static/shared/app.js` — drawerContentV10/V11 `window: null → "drawerContent"` + ROW_WIN_EST_H.drawerContent:27 + 注释漂移修正
- `webui/static/shared/drawer_templates.js` — drawerWinView computed(rowsFn 缓存) + dtWinRows/dtWinPad/dtBridgeLines/dtWinKbd(跨窗回焦)
- `webui/static/shared/tpl/xtpl.html` — 桥 v-for 切 dtBridgeLines(窗表切片/其余全量回落) + aq-row-pad 占位 + .group-table @keydown
- `tests/test_webui_static_dom_panel.py` — 守阵 test_drawer_tpl_row_memoization_and_cheap_sig + 测试计划同步
- `tests/test_webui_static_dom_page.py` — 守阵 test_frontend_window_source_kind_descriptor_parameterized(W2 建, W3 同步 V10/V11 翻向+源族分流)
- `tests/test_webui_static_skins.py` — test_drawer_table_bridge_wiring 同步(dtBridgeLines 单点)
- `e2e/dt-live-update.spec.mjs` — #10/#11 量具 settle 竞态修复 + A/B 口径收紧(longtask 下界 0) + #11 千文件数据回路 + makeFilesK 桩
- `e2e/drawer-content-perf.spec.mjs` — 新增 W4 千级验收 spec(8 test 全矩阵)
- `e2e/perf.spec.mjs` — W5 主表×抽屉同屏交叉 2 条(E2E_TORRENTS>500 门控)
