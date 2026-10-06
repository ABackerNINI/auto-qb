# 2676 —— WEBUI 列对齐彻底方案实施(模板/CSS/JS 改动 + e2e 几何守卫)

> 摘要: 按计划 [26-10-06-1009](../../plans/26-10-06-1009-plan-webui-column-alignment.html) 实施报告
> [26-10-06-0945](../../reports/26-10-06-0945-report-webui-column-alignment.html) 的「彻底方案」(§5 P0/C1):
> 把「拖拽把手槽」与「列头文字排版」解耦 —— 省略号下移到 `<span class="h-label">`、`.h-cell` 改
> `flex + overflow:visible + padding-right:0`、把手 `right:-5px` 跨进 10px grid 列间距; 右对齐列箭头
> `order:-1`; 三主题删「0 值居中」旧口径; `e2e/smoke.spec.mjs` 加几何守卫(红绿双验)。
> **零 Python 与 `tests/` 改动** ⇒ 数字应与上一条 [26-10-06-1022](26-10-06-1022-webui-column-alignment-plan.md)
> 的 2676 + 4 逐位持平 —— 实测一致。
> 基线时间: 2026-10-06 10:37

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/pitfalls/web-ui/header-cell-gutter.md

- 分支: develop @ **2836e522**(开工 `my-commit-flow.sync` 后; 工作树含本次前端改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 本轮单次采样 **53.7s**(含覆盖率报表; wall 53.7s)。
- 相对上一条基线 [26-10-06-1022](26-10-06-1022-webui-column-alignment-plan.md)
  (2676 + 4 / 16021 / 163 / 5472 / 143): **逐位持平**(passed ±0 / 语句 ±0 / 未覆盖 ±0 / 分支 ±0 / partial ±0)
  —— 与「纯前端(模板/CSS/JS)改动, 无 Python 改动」预期一致。
- 前端验证(真浏览器, 桩服务 `scripts/ui_harness.py`):
  - `commands run dev.e2e`: **6 passed**(prism / atlas × {渲染健康, 数据契约, 几何守卫})。
  - 几何守卫**红绿双验**: 注入缺陷(prism `.h-cell` 复加 `padding-right:10px`)时该用例报 `delta:11` **红**
    (atlas 仍绿 ⇒ 逐皮肤可判); 复原后 **绿**。
  - 盒模型差(桩服务 8099 + headless Chromium, 三主题 atlas/console/prism 逐列复量):
    右对齐列 group/torrent **1px**(数据行 1px 侧边框, 允许 ±1)、detail **0px**; 点「大小」排序后仍 ≤1。
    **改前对照: 11 / 10, 排序后 21~22。** ⚠ 少数列的「值文字墨迹右缘」偏出 3~11px 属**值溢出被省略号
    截断**的既有现象(报告 §7 已划出范围), 非本次对齐缺陷; 判据以盒模型为准。
- 旁证: `commands run kb.check` / `kb.docmap -- --check` / `kb.index` 绿; `tests/test_docs_forms.py` 11 passed;
  CSS 单文件 ≤700 行守阵绿(atlas `components.css` 698 行 —— 新增 `.h-label` 规则按约定落 `atlas/css/views.css`)。
- 改动面(全部为前端静态资产 + 知识库; 无 Python / `tests/` 改动):
  - `src/auto_qb/webui/static/shared/tpl/{groups,torrents,shows}.html`(5 处列名 `<span>` 加 `h-label`)
  - `src/auto_qb/webui/static/{atlas/css/components,console/css/components,prism/css/views}.css`(`.h-cell`/`.resizer` + 删 0 值居中)
  - `src/auto_qb/webui/static/atlas/css/views.css`(新增 `.h-cell > .h-label` 规则 —— 避 components 700 行 cap)
  - `src/auto_qb/webui/static/shared/columns.js`(`colAlignCss()` 右对齐列 `.arrow{order:-1}` + 注释)
  - `e2e/smoke.spec.mjs`(新增几何守卫用例)
  - `memory-bank/{pitfalls/web-ui/header-cell-gutter.md, modules/webui-static-contract.md, tasks/26-09-29-webui-column-alignment.md, plans/26-10-06-1009-plan-webui-column-alignment.html}`
