# 26-09-29-webui-dialog-hover-keynav — 弹窗下拉悬停接管: 分类/标签/编辑分类 mouseenter 与键盘活动项同源打架

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29 23:16
**Topics:** webui-dialog-hover-keynav
**Summary:** issue 26-09-29-2142-bug-dialog-hover-keynav-fight(站点搜索闪烁同族, 26-09-29 21:42 入池): 添加种子分类/标签下拉与编辑弹窗分类下拉用 @mouseenter 直写键盘活动项, 光标静止停在列表上按 ↑↓ 时, 行滚动/DOM 变更触发浏览器给静止光标补发合成 hover 事件, 活动项被拽回光标行。真机复验坐实且比入池推定更重: ↓×16 轨迹两次被拽回、Enter 实选光标行 cat-06 而非键盘到达的 cat-16(不止闪烁, 实选错)。修: comboHoverIdx(kind,i,ev) 共享小工具(@mousemove + 3px 位移门限, 三处下拉共用) + 开层单点复位门限坐标 + 三皮肤 CSS data-hi 行摘 :hover(.on 单路高亮)。改后同驱动: 轨迹纯净 1→16、Enter 正确 cat-16。守阵 test_frontend_dialog_combo_hover_takeover。待「提交」指令由 ship.commit 入库。

## 原始请求

用户指派认领 issue 26-09-29-2142-bug-dialog-hover-keynav-fight(「认领issue: 26-09-29-2142-bug-dialog-hover-keynav-fight」)。

## 思考过程与决策

- **先复验再动手**(防过期原则第 5 条): issue 是代码同构推定、未实测。改前用 ui_harness 桩 + Playwright 驱动真实浏览器(真实点击/悬停/键盘, 注入 40 个分类使列表必滚): ↓×16 轨迹 [1..5, 回跳1, ..7, 回跳3..6] 两次被拽回光标行, 终值 6(键盘期望 16), **Enter 落点 cat-06 ≠ cat-16** —— 现象确凿且升级(实选错, 会把错误分类提交进添加请求)。
- **照搬站点搜索已修模式**(pitfalls/web-ui/hover-keynav-fight): mousemove + 3px 位移门限(合成事件位移恒 0 被挡) + CSS 单路高亮 + 门限坐标复位。issue §06 建议"抽共享小工具, 别三处各抄一份" —— 照做(comboHoverIdx 落 add_torrent.js, meta 下拉同调)。
- **CSS 摘 :hover 改为 data-hi 行定点中和**: `.pop-item:hover` 是共享组件样式, 列菜单/UI 切换器等无键盘导航的菜单靠它做悬停反馈, 且列菜单行绑 `.on`(可见列高亮)—— 全局摘除或 `:not()` 重写共享规则会伤及无辜(悬停暂时盖掉列的选中高亮)。改在三皮肤 dialogs 样式加 `.pop-item[data-hi]:not(.on):hover` 中和(恢复基础色), 只影响弹窗下拉行族。路径下拉(addPathHi)同为 data-hi 行一并覆盖 —— 它无 mouseenter 直写、不在本 issue 现象内, 属同族预防(双通道 CSS hover + .on 一并单路化)。
- **门限坐标只在开层单点复位**(openAddCatMenu/openAddTagMenu/openMetaCatMenu): 键盘开层路径(_comboKeydown / onMetaCatKeydown 的菜单未开分支)与 @input 内联开层**故意不复位** —— 光标静止停在列表上时旧坐标恰是保护(位移 0 被挡); 复位反而制造「坐标 null = 任何事件都接管」的夺高亮窗口。
- **不改 _hiScroll**: 它用 scrollIntoView(block:nearest), 与坑档案处置④的差值法相悖, 但滚跟随本身已工作、程序滚动可能补发的合成事件已被 3px 门限挡住; 换差值法属另一范畴, 不入本轮(scope-guard)。
- **驱动脚本对称复用**: 同一 .cjs 改前/改后各跑一遍(真实输入事件, 非合成桩), 各四段对照(轨迹/终值/Enter 落点/零位移合成 mousemove 应被挡)。脚本在 .openclaw/tmp/(临时工装不入仓库, ui-preview-harness 口径)。

## 实现计划

单轮实施, 无独立计划文档。蓝本: pitfalls/web-ui/hover-keynav-fight 处置①②③ + issue §06 建议修法。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 认领置 In Progress + 真机复验(改前基线: 轨迹回跳 ×2 / 终值 6 / Enter 选错 cat-06) | Done |
| 2 | 模板三处接线: dialogs-mgr.html(cat/tag) + popovers.html(meta) @mouseenter → @mousemove="comboHoverIdx(...)" | Done |
| 3 | add_torrent.js: comboHoverIdx 共享小工具(3px 门限) + openAddCatMenu/openAddTagMenu 复位; dialogs.js: openMetaCatMenu 复位 | Done |
| 4 | state.js: addCatMouseAt/addTagMouseAt/metaCatMouseAt 声明 | Done |
| 5 | CSS 三皮肤(atlas/console dialogs.css, prism components.css): .pop-item[data-hi]:not(.on):hover 中和 | Done |
| 6 | 守阵 test_frontend_dialog_combo_hover_takeover(接线/零残留/state 声明/门限/开层复位/CSS 成对) + 红验(临时改坏接线确认能红) | Done |
| 7 | 改后同驱动 A/B: 轨迹 1→16 纯净 / Enter cat-16 / 零位移合成 mousemove 被挡; test.full 全绿 + 基线切片 | Done |

## 进度日志

- **2026-09-29 23:16 (Done)**: 单轮完成(复验 → 实施 → 守阵红验 → 改后 A/B → test.full **1760 passed + 2 skipped / 91%**, 30.90s)。详见基线切片 [26-09-29-2316](../testing/baselines/26-09-29-2316-webui-dialog-hover-keynav.md) 与 issue「修复后补充」。待「提交」指令由 ship.commit 入库。
