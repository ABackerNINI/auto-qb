# WEBUI 详情面板/流量图搜索筛选跳动修复

> 摘要: 搜索首词待响应窗空命中集把列表塌成 0 行(文档高塌掉 → 滚动钳回 0 → 停靠面板失去 sticky 锚点弹跳); 短列表下 sticky 吸底还会脱锚上浮。修法 = searchPending 门 + 三皮肤 .layout min-height 撑满首屏。修复与验证已完成, 未提交。
> 最后活动: 2026-10-07 03:46

**Refs:** memory-bank/tasks/26-10-07-webui-drawer-search-jump.md

## 已完成

- 取证: ui_harness + Playwright 逐帧采样, 修复前指纹(docH 18582→800→1141 / top 430↔416 / scrollY 8000→0)已入坑档。
- 修复: view.js/state.js/filters.js(searchPending 生命周期 + _searchGateActive 单点门) + 三皮肤 .layout min-height(calc(100vh - var(--head-h)))。
- 守阵: test_web.py::test_frontend_search_pending_no_collapse(静态) + e2e/drawer-dock-stability.spec.mjs(行为, @fast, 逐帧采样)。
- 全量: test.full 2690 passed + 4 skipped / TOTAL 99% / 41.7s(基线切片 26-10-07-0346)。

## 正在进行

- 无(等用户显式「提交」指令)。
