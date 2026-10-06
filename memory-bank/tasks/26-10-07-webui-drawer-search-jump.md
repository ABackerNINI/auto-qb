# 26-10-07-webui-drawer-search-jump — 种子详情面板/流量图在搜索/筛选时跳动修复

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 03:46
**Topics:** drawer-dock, search-pending, sticky-anchor
**Summary:** 搜索首词待响应窗(防抖400ms+往返)空命中集把列表塌成 0 行 → 文档高塌掉 → 滚动位置钳回 0、停靠面板失去 sticky 锚点弹跳; 短列表下 sticky 吸底还会脱锚上浮。修法 = searchPending 门(待响应且命中集未落袋不许命中门接管列表) + 三皮肤 .layout min-height 撑满首屏(--head-h 单点)。守阵: test_web.py 新增静态守阵 + e2e/drawer-dock-stability.spec.mjs 行为守阵。

**Refs:** memory-bank/activeContext/26-10-07-0346-webui-drawer-search-jump.md,memory-bank/pitfalls/web-ui/search-pending-collapse.md,memory-bank/testing/baselines/26-10-07-0346-webui-drawer-search-jump.md

## 原始请求

用户：「修复:WEBUI种子详情面板/流量图在搜索/筛选时跳动」。

## 思考过程与决策

- **取证(ui_harness + Playwright 逐帧采样, prism 1280x800, 修复前)**: 面板开着逐字输入搜索词, docH 18582→800(塌到恰视口高)→1141, 面板 top 430↔416 反复横跳; 滚到列表中部(scrollY=8000)再搜, 滚动位置被钳回 0(整页跳顶)。筛到 0 行/真 0 命中时面板脱锚上浮, 视口越高跳幅越大(800px 视口 14px, 线性放大)。
- **根因两条**: ①`filteredTorrents`/`filteredGroups` 的命中门 `if (q && !hits.has(...))` 在**首词待响应窗**里照常生效 —— 此时 searchHits 是空集(没有"上一查询"可沿用, filters.js 注释里"沿用上一查询的命中集"契约对 空集→首词 转换失效), 防抖 400ms + 请求往返的整个窗口列表塌成 0 行; ②停靠面板 `.drawer-dock` 是流内 sticky 吸底, 只在"自然落点低于视口下界"时钉住 —— 列表变短文档变矮就脱锚, 面板跟着内容末尾走(与搜索无关, 任何筛短动作同病)。
- **修法决策**: ①新增 `searchPending` 状态(view.js 武装/落袋生命周期 + filters.js `_searchGateActive` 单点门), 待响应且命中集未落袋时命中门不生效 —— 渐进输入命中集非空仍按旧集过滤(标准 search-as-you-type 不变), 只有"空集→首词"这一段改回显示输入前列表; ②`.layout` 加 `min-height: calc(100vh - var(--head-h))` 让内容列恒撑满首屏, 面板自然落点恒在视口底, sticky 锚点与列表长短无关(--head-h 是既有单点, columns.js::_syncHeadHeight ResizeObserver 实测, 不写死顶栏高)。
- **守阵双层**: 静态守阵(test_web.py::test_frontend_search_pending_no_collapse)钉接线存在性; 行为守阵(e2e/drawer-dock-stability.spec.mjs @fast)逐帧采样钉几何 —— 坑档教训: 「调用存在但几何/时机错」静态守阵探不到(dock-panel 2026-10-04 回归), 必须真浏览器采样。
- **scope 纪律**: 搜索 building 轮间(1s 自动重查)命中集为空时列表塌 0 行是**既有行为**(文件索引构建期), 未纳入本修; 真 0 命中落袋后列表为空 + 滚动钳制属预期(结果确实为空), 不治。

## 实现计划

单轮小修(无波次): view.js(searchPending 生命周期) + state.js(声明) + filters.js(_searchGateActive + 两派生接门) + 三皮肤 CSS(.layout min-height) + 守阵两件。

## 子任务状态表

| # | 项 | 状态 | 验证门 |
|---|------|------|--------|
| 1 | 取证复现(逐帧采样) | 完成 | 探针实测值入坑档 |
| 2 | searchPending 门(view/state/filters) | 完成 | test_web 静态守阵 |
| 3 | .layout min-height(三皮肤) | 完成 | 同上 + e2e |
| 4 | e2e 行为守阵 | 完成 | e2e @fast |
| 5 | 全量测试 + 基线 + 回写 | 完成 | test.full |

## 进度日志

- 2026-10-07 03:46: 修复完成全绿。修复前指纹: docH 18582→800→1141 震荡 / 面板 top 430↔416 / scrollY 8000→0; 修复后三皮肤逐帧采样零几何变化(top 恒定, 搜索全程 docH 不塌)。守阵: test_web.py::test_frontend_search_pending_no_collapse + e2e/drawer-dock-stability.spec.mjs(2 皮肤)。test.full 2690 passed + 4 skipped / TOTAL 99% / 41.7s。未提交(等用户显式指令)。
