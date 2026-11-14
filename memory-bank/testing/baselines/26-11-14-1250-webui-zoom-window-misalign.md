# 6136 passed + 2 skipped —— zoom!=1 行窗口化 pad 缩放换算修复

> 摘要: zoom!=1 行窗口化 pad 缩放换算修复
> 基线时间: 2026-11-14 12:50

**Refs:** memory-bank/tasks/26-11-14-webui-row-window-zoom.md

## 验收数字

`commands run test.full` 实测(2026-11-14 13:4x, HEAD fba96475 + 本批工作树收口态): **6136 passed + 2 skipped** / TOTAL **99%**(27305 语句 / 68 未覆盖 / 9588 分支 / 73 partial)。

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`: 新增 `_winZoomOf`(容器 gBR.height / computed used 高实测有效缩放); `_rowWindow` 两个 pad 出口按 1/z 换算成布局 px(issue 26-11-14-0844); `_winSigExtra` 加根缩放令牌。
- `e2e/row-window-zoom.spec.mjs`(新增): 三皮肤 zoom 0.9 贴文档底可见行 ≥5 + 末行可达 + scrollBy ±1 不塌(@fast)。
- `e2e/drawer-dock-stability.spec.mjs`: T8 根锚补用例 flux 解跳(缺陷已修)。
- `tests/webui_dom_page_support.py`: W2 窗口源电池 +3 条 zoom 换算 checks(23/23, 含 _winSigExtra 根缩放令牌钉子)+ `getComputedStyle`/`_winContainer`/`document.body` 桩。
- `tests/test_webui_static_r4_node_batteries.py`: winMembers/groupWin 两电池 ctx 补 `_winContainer` 桩。
- `tests/test_webui_static_dom_page_layout.py`: 电池阈值 18→20 + docstring 测试计划同步。
- `memory-bank/issues/26-11-14-0844-bug-webui-zoom-window-misalign.html`: Done 收口(实际修法/验证方式)。
- `memory-bank/pitfalls/web-ui/css-zoom-coordinate-space.md`(新增): CSS zoom 坐标空间错配坑档。
