# 弹窗条件类切高度: 必须带 transition, 增长只能朝下, 过渡期浮层不许伸出滚动容器, 净空要重测

> 摘要: 弹窗条件类切高度: 必须带 transition, 增长只能朝下(居中容器里增高会把内容顶到光标底下), 过渡期浮层不许伸出滚动容器(否则闪滚动条), 过渡期量的净空要重测
> 触发: 弹窗太小, 高度跳变, 下拉展开高度跳变, pop-open, 条件类切高度, padding-bottom 过渡, 打开即展开下拉, 点选项就提交, 过渡期限高误限, 设定位置对话框, 下拉出现后自动弹回, 下拉一闪就没了, 点下拉框面板自己收起, 点一次就选中了, 连点两次命中候选, 面板顶到光标底下, 输入行上移, 内容上移, align-items center, 增长方向, 弹窗向上长高, 一瞬间出现滚动条, 闪滚动条, 滚动条一闪, 内容横向跳, 挤一个滚动条宽, 预留是过渡的, overflow-y auto, scrollHeight 撑大, 面板伸出 body, 下拉消失时闪滚动条, 收层闪滚动条, 离场淡出期溢出, transition pop-leave, 开关挂状态还是挂事实, has() 选择器
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0149-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0224-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0249-webui-move-dialog-pick-geometry.md

### 给弹窗靠「条件类切 padding/高度」腾空间, 却没给那条属性加 transition

- **触发**: 弹窗里的下拉/浮层伸不出去(容器 `overflow-y:auto` 裁掉), 于是按开层状态给容器预留空间 —— 典型写法是模板根元素挂 `:class="{ 'pop-open': xxxMenu }"` + `.pop-open .add-dialog-body { padding-bottom: 272px }`。此时**开/收浮层 = 容器高度一步到位跳 272px**(2026-10-29 用户报「点下拉框高度跳变」), 且不开浮层时窗口只剩内容高(实测 243px = 用户报的「窗口太小」)。
- **判别**: ①打开弹窗再开/收浮层, 窗口上下缘**瞬间**位移(没有中间帧); ②DevTools 里给该属性勾 `transition` 后跳变消失, 只剩中间帧; ③收层态高度 == 纯内容高(说明预留是条件性的)。
- **处置**: ①**预留那条属性必须带过渡**: `transition: padding-bottom 200ms var(--ease)`(reduced-motion 下关掉); ②收层态基线要够「大气」: `min-height: min(360px, calc(100vh - 120px))` + 动作条 `margin-top:auto` 钉底 —— 但 **body 不能 `flex:1`**: 全局 `* { box-sizing: border-box }` 下 padding 会长在固定高度里, 内容反被挤成滚动条, 高度增长只能靠 body 的 auto 高度随 padding 走; ③**过渡期量的净空要重测**: `_fitAddPop` 在 `$nextTick` 量「输入行 → 容器可见底沿」, 过渡进行中只有一半 → 列表被误限到 120px 且**不再自恢复**(watcher 只在输入/候选变化时重跑) ⇒ 开层后挂一个 > 过渡时长的 settle 定时器(`MOVE_POP_SETTLE_MS = 240` vs CSS 200ms)复位重测, 两边时长互相点名; ④别急着补 `.pop-enter-*`: `.pop-menu` 自带 `animation: drop-in .12s`, 再加 transition 是死规则且与动画争同一组属性。
- **守阵**: 静态 `tests/test_webui_static_dom_panel.py::test_frontend_move_dialog_combobox_wiring`(三皮肤成对 min-height / 动作条钉底 / `transition: padding-bottom 200ms` / settle 常量); e2e `e2e/move-dialog-fit.spec.mjs` 用 `ResizeObserver` 采样高度序列, 断言**存在严格介于基线与终值之间的中间帧**(只有终值的断言抓不到瞬跳)。
- **复发**: 0

### 条件类切高度: 增长方向必须朝下 —— 居中容器里增高会把刚展开的浮层顶到光标底下

- **触发**: 给「居中的弹窗/面板」按条件类(如 `.pop-open`)腾高度(上一节的 padding-bottom 预留), 且该浮层是**由点击触发的**(点输入框展开下拉)。用户报「点下拉框, 下拉框出现后**自动弹回**」「下拉一闪就没了」「点一次就选中了」。
- **判别**: ①遮罩/外壳是 `display:flex; align-items:center` ⇒ 增高**上下对半扩**: 360→515 的弹窗, 内容整体**上移 77px**(实测 rowTop 413→335), 于是「刚在光标下展开」的面板被顶到光标**原来的位置**上 —— 光标所在处从输入框变成候选行/面板头, 用户再点一下(双击的第二次、或"以为没点中"的补点)就命中候选(`@mousedown.prevent` 直取 = 回填 + 收层)或面板头(blur 收层), 观感就是面板自己弹回。②判别探针: 记 `开层前后输入行的 getBoundingClientRect().top` + `面板 top` 与 `输入框 bottom` —— 前者变了 / 后者小于等于输入框底沿即命中本条。③**必须用人手时序复现**: 合成零延迟点击(Playwright 默认 down/up 隔 ~2ms)不触发; `delay>=120ms` 连点两次同一屏幕坐标才稳定复现(与 combobox-focusout-close 同一教训)。
- **处置**: 让增长**只朝下** = 遮罩改 `align-items:flex-start` + 弹窗 `margin-top` 复刻收层态的居中偏移(`clamp(0px, calc((100vh - 360px) / 2 - 20px), calc(100vh - 560px))`, 20 = 遮罩自身 padding, 上限扣掉开层态总高与下沿余量 ⇒ 矮视口不外溢、更矮由 `.modal` 的 max-height 壳内滚兜底)。遮罩类经 `<aq-modal mask-class="modal-mask move-dialog-mask">` 接线(别用 `:has()` 猜祖先)。收层态屏位与居中**逐像素相同**(900 视口下 top 仍 270), 只是开层态从"上下对半扩"变成"向下长"。
- **守阵**: 静态守阵三皮肤成对断言 `.modal-mask.move-dialog-mask{align-items:flex-start}` + `.modal.move-dialog` 的 margin-top 居中补偿 + 模板 `mask-class` 接线; e2e `move-dialog-fit.spec.mjs` 补**几何不变量**(开层前后输入行屏坐标不动 ≤2px / 对话框上缘不动 / 面板 top ≥ 输入框 bottom / 下缘不溢出视口)+ 专测「同一屏幕点连点两次面板仍在且输入框未被回填」。红验: 摘掉模板 `mask-class` 一行 → 静态 1 红 + e2e 4 红(其中「连点两次」直接报 element not found = 面板真没了)。
- **教训**: 「高度不跳变」(过渡)与「内容不动」(增长方向)是**两件事** —— 加了 transition 只让上移变平滑, 上移本身仍在, 而且**平滑的上移更坏**: 面板先出现在光标下, 再慢慢滑到光标底下, 用户的下一次点击正好落在上面。条件类腾空间的修法必须同时定住「谁不许动」: 被点击的锚点(输入行)屏坐标不变, 增长全部发生在它下面。
- **复发**: 0

### 预留是「过渡」的、浮层是「瞬间挂载 / 延后离场」的 ⇒ 过渡期浮层伸出滚动容器 = 闪一条滚动条

- **触发**: 上一节那类「开层时给 body 加 padding-bottom 预留 + 过渡」的弹窗里放自绘下拉。用户报「下拉框出现时弹窗**有一瞬间出现滚动条**」「内容横向抖一下」。
- **判别**: ①预留 padding 走 200ms 过渡, 而浮层(`.add-pop`, 绝对定位, 高 ~256)在开层那一刻**瞬间挂载** ⇒ 头 ~110ms 内浮层底缘伸到 `.add-dialog-body` 的 padding 盒之外(实测 `scrollHeight - clientHeight` = 256→173→108→…→0), 而 body 是 `overflow-y:auto` 的滚动容器 ⇒ 闪出一条滚动条, 并且经典滚动条占 15px 宽 ⇒ 行内内容横向被挤一下; ②判别探针: 开层后逐帧记 `body.scrollHeight - body.clientHeight` 与 `getComputedStyle(body).overflowY` —— 前者先大后 0、后者 `auto` 即命中本条; ③**无头 Chromium 是覆盖式滚动条**, `offsetWidth - clientWidth` 恒 0, 所以判据只能看计算值, 别看占位宽。
- **处置**: 把 body 的滚动**按「浮层是否存在」关掉**, 而不是按「开合状态」关 —— `.modal.move-dialog:has(.add-pop) .add-dialog-body { overflow: hidden }`(三皮肤成对)。为什么必须按存在判: 浮层离场走 `<transition name="pop">` 的淡出(`--dur-fast` ~120ms), 这期间它**仍在 DOM 里、高度不变**, 而 `.pop-open` 已摘、预留 padding 在 200ms 里往回缩 ⇒ 若开关只挂 `.pop-open`, 收层端会漏(实测溢出涨到 254px = 又闪一次, 用户第二轮报的就是这个); `:has()` 在离场期仍命中, 开层/离场两段一起覆盖, 浮层真被移除后自动回到 `auto`。安全性论证: 溢出 body 的**只有那段预留空白**(真内容都在输入行上方, 不参与溢出), 所以裁掉它不丢任何可读内容; 裁剪位置与 `auto` 完全一致(都是 padding 盒底沿), 观感不变(浮层随过渡逐帧露出/淡出), 只是不再有滚动条/横向挤压。**无浮层时仍是 `auto`** —— 矮视口下 body 收缩时还要靠它兜底滚动, 无条件 `hidden` 会把内容裁成不可达。列表自身 `overflow-y:auto` 仍能滚, 矮视口里候选依然取得到。
- **守阵**: 静态 `test_frontend_move_dialog_combobox_wiring` 三皮肤断言 `.modal.move-dialog:has(.add-pop) .add-dialog-body { overflow: hidden }`; e2e `move-dialog-fit.spec.mjs` 逐帧采样器(**只记浮层存在的帧** —— 离场后回到 `auto` 是正确状态, 混进来会假红)断言开层与收层全过程 `overflowY === 'hidden'` 且 `offsetWidth - clientWidth === 0`, 另断言收完回到 `auto`。红验: 把开关退回 `.pop-open` 口径 ⇒ 双皮肤「收层全过程」那条立刻红; 整个摘掉 ⇒ 开层那条也红。
- **教训**: 条件类预留一旦**加了过渡**, 就等于把「容器什么时候够大」变成时间函数 —— 期间任何**瞬间出现 / 尚未离场**的绝对定位后代都会暂时溢出。两头容易各漏一个: ①修开层端忘了收层端(浮层的离场动画让它在关掉之后还多活 ~120ms); ②把开关挂在**状态**(`.pop-open`)而不是**事实**(浮层在不在 DOM) —— 判据一旦写成跟状态走, 就必须问: 状态翻转之后、DOM 真正变化之前, 那段窗口谁来兜? 处置不是把浮层也做成过渡(会与既有入场动画争属性), 而是问一句「过渡期溢出的到底是什么」: 只是预留空白 ⇒ 直接关掉那段时间的滚动; 真有内容 ⇒ 才需要另想办法(缩短过渡/换预留方式)。
- **复发**: 0
