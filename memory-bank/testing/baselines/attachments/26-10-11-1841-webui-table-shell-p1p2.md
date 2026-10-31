# 3126 —— WEBUI 表壳组件 + 明细单元格渲染器(P1/P2)

> 摘要: 计划 `26-10-11-1722-plan-webui-table-component` 的 **P1/P2**(模板单点, 零观感/零行为变化)—— 表头块 5 份逐字近似收敛为**单份表壳组件** `<aq-table>`(列名 / 排序箭头 / 拖宽把手 / 重排指示线 / 表头右键), 明细成员单元格 2 份收敛为**单份行模型渲染器** `<aq-member-cells>`(member 行模型, 辅种页与追剧页共用); 两者放 `shared/table.js` + `tpl/xtpl.html` 两份 x-template, 只贡献模板, 行为一律经 `$root` 回调根实例。连带: `_headEl` 统一 unwrap 组件实例, 三个 `sync*HeadScroll` 与 `_winContainer("member")` 改走它; 守阵同轮改版(`_scan_column_cells_paired` 明细列改扫渲染器 + 新增 `test_frontend_table_shell_single_point`, 均红绿双验过)。验收: 真浏览器 **A/B DOM 逐字节等价**(17 项探针 × 2 皮肤, 差异 0)+ e2e 与上片基线逐位一致。行渲染仍内联 `v-for`、行容器与占位留在页面模板(计划停手点); 种子页表头未迁移。
> 基线时间: 2026-10-11 18:41

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `ca6c8f89`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3126 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16464 语句 / 148 未覆盖 / 5608 分支 / 133 partial; 门槛 98% 达标, 实到 98.70%; 本轮 61.19s)
- 语句 / 未覆盖 / 分支 / partial 四项与上一片 `26-10-11-1804-webui-table-registry-p0` **逐位相同**(16464 / 148 / 5608 / 133)—— 纯前端模板/接线收口, Python 侧零新增代码路径。
- 增量明细(本轮真正新增): `src/auto_qb/webui/static/shared/table.js`(新片段, 两个组件) + `tpl/xtpl.html`(两份 x-template) + 三份 `index.html`(清单加一行; prism 同轮删一行空行腾额度) + `shared/app.js`(两行 `app.component` + 头注释) · `shared/columns.js`(`_headEl` unwrap / `_winContainer`) · `shared/menu.js` · `shared/selection.js` · `shared/shows.js`(横滚同步单点改走 `_headEl`) · `tpl/groups.html` · `tpl/shows.html`(四个表头块 + 成员单元格链); 测试面: `tests/test_webui_static_skins.py`(+1 守阵 `test_frontend_table_shell_single_point`, `_scan_column_cells_paired`/`test_frontend_hr_safety_wiring` 改版) · `tests/test_web_shortcuts.py`(站点格守阵改扫渲染器) · `tests/test_webui_static_dom_page.py`(`$root` 进内建白名单)。文档面: `memory-bank/plans/26-10-11-1722-*.html`(变更记录 + 状态) + `memory-bank/tasks/26-10-11-webui-table-component.md` + 本切片 + `activeContext/26-10-11-1841-webui-table-component.md` + `modules/webui-static-contract.md`(JS 数 27→28 / app.js 行数 582→587 / 新增组件单点条 + 明细列改述) + `pitfalls/web-ui/frontend-split.md`(两条新条目)。
- 机检: `commands run kb.check` 全绿(`doc.caps` 无债务)。真浏览器 e2e `commands run dev.e2e` = 与上一片基线**逐位一致**(通过 / 失败 / 跳过三项相同; 全量轮多出的 2 条是一次性 DOM 探针 spec, 已删), 失败项仍是存量(trigger-scope / multiselect-shows / optimistic / menus)。**DOM 等价判据**: 把 11 个改动件还原到 HEAD + 删掉 `table.js` 后跑同一探针, 17 项(两皮肤)逐项比对差异 0 —— 探针为临时件, 不入仓库。
