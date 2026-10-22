# 26-10-22-webui-overlay-fit — 浮层定位几何收敛 overlay_fit 单点

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 浮层定位几何收敛 overlay_fit 单点
**Topics:** webui-overlay-fit
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-overlay-geometry-dup.html, memory-bank/tasks/26-10-20-frontend-dup-code-audit.md

## 原始请求

1. 用户原话：「认领并修复 memory-bank/issues/26-10-20-2231-refactor-fe-overlay-geometry-dup.html」（2026-10-22，显式指派，含认领与修复两项授权；不含提交）

## 思考过程与决策

- **复验增量**：开工同步 `ad17518a` 后重跑入池锚点，9 处全在位；另实测 2 处同族手写未入账 —— `columns.js::openColMenuAt`(PAD=8) 与 `dialogs.js::speedPopStyle`(PAD=12，`openSpeedAt` 还有一处 12px 右缘回落锚)。12px 实测 2 处(hubAsk + speed-pop)而非记录的 1 处。按「以同步后代码为准」一并收敛，否则「边距常量不统一」只治了一半。
- **单点形态**：issue 建议把 `menu.js::_subFitViewport` 升为通用 `fitInViewport(el, anchor, opts)`。落为独立模块 `shared/overlay_fit.js`(挂 `window.AQB_OVERLAY_FIT`，装载序插在 `fetch_low.js` 后、首个消费方 `config_hub.js` 前，三皮肤 manifest 同点插入)。四个入口：`EDGE`(默认 8) / `clampAxis(v, size, vp, edge?)`(轴夹取) / `probeRight(startX, w, gap?, edge?)` 与 `probeLeft(anchorLeft, w, gap?, edge?)`(左右缘溢出探针) / `fitInViewport(el, x, y, opts)`(量实测或估算尺寸后两轴夹取)。
- **边界切割**：放置策略(上方优先/翻右/箭头/子面板不得搬出父项)与「菜单高过视口限高可滚」兜底都不是几何，留在各调用方；单点只收「贴边留白 + 视口夹取」。
- **12px 去留**：hubAsk 与 speed-pop 的 12px 均无注释、无佐证必须不同。按行为零变化口径**保留 12 并显式传参 + 注释原因**(回落默认 8 是视觉变更，不在本 refactor 授权内)。
- **行为零变化验证方式**：逐点做代数等价核对(夹取式与 clampAxis 在各分支同值；`openFilePrio` 纵轴原未钳下缘的角，经 `state.js` filePrio watcher 的 `_menuFitRefit` 实测重钳后终值一致，初值即终值)；e2e 几何守阵(menus.spec 的 CTX-fit 左右缘)与全量测试复核。

## 实现计划

1. 新建 `shared/overlay_fit.js` 单点 + 三份 `index.html` manifest 同点插入(fetch_low.js 后)。
2. 9 处调用点改调：ui_feedback(`_menuOverflowsRight`/`_menuPos`/`_menuFit`/aq-tip `place`)、menu(`_subOverflowsRight`/`_subFitViewport`)、config_hub(`hubAsk`)、hr(`_hrPopPlace`)、drawer(`openFilePrio`)、columns(`openColMenuAt`)、dialogs(`speedPopStyle`+`openSpeedAt` 回落锚)。
3. 守阵 `test_overlay_fit_single_point`(单点存在性 + 消费面全覆盖 + 手写形态零残留 + hubAsk/speed 显式 12)，突变红验。
4. test.full + e2e 全量；基线切片誊实测数字。
5. issue 置 Done(实际修法/验证/数字)，契约回写 `modules/webui-static-contract.md`，kb.wrap。不提交(用户未授权)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| S1 | 认领 + 复验 + 立档 + 双向链 | Done(2026-10-22) |
| S2 | overlay_fit.js 单点 + 三皮肤 manifest | Done(2026-10-22) |
| S3 | 9 处调用点改调(行为零变化) | Done(2026-10-22) |
| S4 | 守阵 + 红验 | Done(2026-10-22) |
| S5 | test.full + e2e 全量 + 基线切片 | Done(2026-10-22) |
| S6 | issue Done + 契约回写 + kb.wrap | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

认领 issue 26-10-20-2231(用户显式指派)。同步 `ad17518a`；复验 9 处锚点在位 + 实测增量 2 处(columns/dialogs，12px 实测 2 处)。单点形态与 12px 保留口径拍板如上。立档阈值 #2 命中(改动 ≥3 源文件)。

### R1 · 实现 + 验证 + 收尾 (2026-10-22)

- **实现**：新建 `shared/overlay_fit.js`(IIFE → `window.AQB_OVERLAY_FIT`，EDGE/clampAxis/probeRight/probeLeft/fitInViewport)；三皮肤 manifest 同点插入(注意：prism/index.html 撞 214 行上限，新条目与 `fetch_low.js` 同行堆放)；9 处锚点 + 2 处增量位点改调。
- **事故与修法(已入坑点)**：初版在 7 个消费文件顶层各写 `const FIT = ...`。classic script 的顶层 `let/const` 共享**全局词法环境**，config_hub.js(首个装载)声明成功、后 6 个文件全部 `Identifier 'FIT' has already been declared` SyntaxError → `window.AQB_*` mixin 未注册 → 整页瘫痪。静态守阵(源码字符串比对)全绿看不见，仅 e2e 暴露(pageerror ×6 + Vue props undefined)——这也解释了此前 e2e 全量为何屡屡 1200s 超时：不是机器慢，是每例都在对一个瘫页等 30s 超时。修法：全部别名收进方法内作用域(aq-tip IIFE 内合法)；新增第 5 类守阵：跨文件顶层 const/let 撞名扫描(双文件变异红验)。
- **验证**：node 等价网格逐位等价(旧 4 种夹取写法 ×2 处 Math.max 兜底 ×5 公式形态 ×7 视口 ×5 高 ×7 尺寸 ×10 目标位 ×2 边距)；test.full 与 e2e 全量的实测数字**见 kb.baseline**(本轮为全量轮：test.full 136.7s、e2e 11.1m；较上一轮基线的差 = +1 新增守阵 + 开工同步合入的并行会话提交)；5 类变异全先红后绿。
- **收尾**：issue 置 Done(状态日志留实际修法/验证/数字)；契约 bullet 入 `modules/webui-static-contract.md`；基线切片 `testing/baselines/26-10-22-0646-webui-overlay-fit.md`；坑点(classic script 顶层 const 撞名)入 `pitfalls/web-ui`。本轮授权范围只含认领与修复两项。

- 2026-10-22 06:52 浮层定位几何(8px/12px 边距+视口夹取)12 处手写收敛为单点 shared/overlay_fit.js(window.AQB_OVERLAY_FIT: EDGE/clampAxis/probeRight/probeLeft/fitInViewport); hubAsk 与 speed-pop 的 12px 显式命名常量传参保留; 新增守阵 test_overlay_fit_single_point(单点存在性+装载序+7 消费文件接线对账+手写残留零容忍+12px 显式命名+跨文件顶层 const/let 撞名扫描+node 等价网格); 修复过程中发现并修复 classic script 顶层 let/const 跨文件撞名致整页瘫的坑(已入 pitfalls/web-ui/classic-script-top-level-const-collision.md); test.full 3999 passed/2 skipped/99%, e2e 全量 340 passed/10 skipped 逐位持平; 未提交(用户只授权认领与修复)
