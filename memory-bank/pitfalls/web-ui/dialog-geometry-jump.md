# 弹窗条件类切高度: 必须带 transition, 且过渡期量的净空要重测

> 摘要: 弹窗条件类切高度: 必须带 transition, 且过渡期量的净空要重测
> 触发: 弹窗太小, 高度跳变, 下拉展开高度跳变, pop-open, 条件类切高度, padding-bottom 过渡, 打开即展开下拉, 点选项就提交, 过渡期限高误限, 设定位置对话框
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md

### 给弹窗靠「条件类切 padding/高度」腾空间, 却没给那条属性加 transition

- **触发**: 弹窗里的下拉/浮层伸不出去(容器 `overflow-y:auto` 裁掉), 于是按开层状态给容器预留空间 —— 典型写法是模板根元素挂 `:class="{ 'pop-open': xxxMenu }"` + `.pop-open .add-dialog-body { padding-bottom: 272px }`。此时**开/收浮层 = 容器高度一步到位跳 272px**(2026-10-29 用户报「点下拉框高度跳变」), 且不开浮层时窗口只剩内容高(实测 243px = 用户报的「窗口太小」)。
- **判别**: ①打开弹窗再开/收浮层, 窗口上下缘**瞬间**位移(没有中间帧); ②DevTools 里给该属性勾 `transition` 后跳变消失, 只剩中间帧; ③收层态高度 == 纯内容高(说明预留是条件性的)。
- **处置**: ①**预留那条属性必须带过渡**: `transition: padding-bottom 200ms var(--ease)`(reduced-motion 下关掉); ②收层态基线要够「大气」: `min-height: min(360px, calc(100vh - 120px))` + 动作条 `margin-top:auto` 钉底 —— 但 **body 不能 `flex:1`**: 全局 `* { box-sizing: border-box }` 下 padding 会长在固定高度里, 内容反被挤成滚动条, 高度增长只能靠 body 的 auto 高度随 padding 走; ③**过渡期量的净空要重测**: `_fitAddPop` 在 `$nextTick` 量「输入行 → 容器可见底沿」, 过渡进行中只有一半 → 列表被误限到 120px 且**不再自恢复**(watcher 只在输入/候选变化时重跑) ⇒ 开层后挂一个 > 过渡时长的 settle 定时器(`MOVE_POP_SETTLE_MS = 240` vs CSS 200ms)复位重测, 两边时长互相点名; ④别急着补 `.pop-enter-*`: `.pop-menu` 自带 `animation: drop-in .12s`, 再加 transition 是死规则且与动画争同一组属性。
- **守阵**: 静态 `tests/test_webui_static_dom_panel.py::test_frontend_move_dialog_combobox_wiring`(三皮肤成对 min-height / 动作条钉底 / `transition: padding-bottom 200ms` / settle 常量); e2e `e2e/move-dialog-fit.spec.mjs` 用 `ResizeObserver` 采样高度序列, 断言**存在严格介于基线与终值之间的中间帧**(只有终值的断言抓不到瞬跳)。
- **复发**: 0
