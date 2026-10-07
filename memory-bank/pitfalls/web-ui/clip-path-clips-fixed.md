# clip-path / transform 祖先会裁剪或位移 fixed 后代

> 摘要: 祖先带 `clip-path`(console/atlas 皮肤的 `.hb-cut` 切角)或 `transform` 时, 其内 `position: fixed` 后代的「相对视口」语义被改写成「相对该祖先」—— `clip-path` 表现为**绘制裁剪**(全屏层只剩与祖先重叠的部分可点/可见), 而**入场动画里的瞬时 `transform`** 表现为**位移后回弹**(fixed 元素先落在祖先盒对应的位置, 动画结束 transform 归 none 再跳回视口位置, 用户看到"先出现在中间再移到下方"的闪烁)。两种症状同一根因, 修法都是让 fixed 后代脱离会生成 containing block 的祖先。覆盖式全屏层一律写成块盒的**兄弟节点**(或确保祖先链无 clip-path/transform/filter), 不靠 z-index 救。
> 触发: fixed 全屏不显示, 覆盖层只显示一部分, 弹窗被裁剪, 全屏遮罩点不到, clip-path, 切角, hb-cut, z-index 调不动, fixed 后代, 设置页覆盖层, 全屏层错位, 底部动作条先出现在中间再下移, 状态栏闪烁, 保存条闪烁, 切设置页闪烁, page-in, transform 动画, containing block, 包含块, ce-page, hb-actbar
**Refs:** memory-bank/tasks/26-10-02-webui-hr-status-display.md

### clip-path 裁剪 fixed 后代: 机制与修法 (2026-10-02 实测)

- **触发**: 在带切角皮肤的卡片/块盒(`.hb-blk` 等, console/atlas 用 `.hb-cut` + `clip-path: polygon(...)` 实现)**内部**放 `position: fixed` 的覆盖式全屏层(遮罩 + 弹窗), 想让它铺满视口。
- **判别**: 真浏览器目检(桩数据起盘)发现全屏层**只剩与块盒重叠的部分**可点/可见, 超出块盒的部分像不存在 —— `z-index` 调多高都没用, DOM 检查器里元素坐标是对的。根因: CSS 规范里 `clip-path`(同族还有 `transform` / `filter` / `will-change` 等生成 containing block 的属性)会使该元素成为 fixed 后代的**裁剪/包含上下文**, fixed 的「相对视口」语义在绘制层被截断为「相对该祖先」。静态守阵与代码审查都发现不了(坐标与类名全对), 必须真浏览器目检。
- **处置**: 覆盖层写成块盒的**兄弟节点**而非子节点(HR 站点状态全屏层: 覆盖层是 `.hb-blk` 的兄弟, 单节点 `v-show` 显隐, 状态在组件 state 天然随行, 零 DOM 搬迁); 同理给这类皮肤写新弹层前先确认祖先链无 clip-path/transform。若确需在裁剪祖先内做浮层, 只能放弃 fixed 改用祖先内绝对定位(即放弃"全屏"语义)。
- **守阵**: 阶段 2 提交在 settings-detail.html 模板注释里钉了「覆盖层是 .hb-blk 的兄弟而非子节点」的原因(含本坑一句话); `tests/test_webui_static_dom_page.py::test_frontend_hr_full_modal_wiring` 钉三套 UI CSS 成对与接线。

### 入场动画的瞬时 transform 也会位移 fixed 后代 (2026-10-04 实测)

- **触发**: 切换进设置页时, 底部动作条(`.hb-actbar`, 内容「已与磁盘同步 / 放弃改动 / 保存并应用」)**先出现在页面中段, 短时间内再下移到视口底部**, 造成一次闪烁。同页的说明浮窗 `.hb-pop` / 箭头 `.hb-pop-arrow` 也是 `position: fixed`, 偶发同症。
- **判别**: 真浏览器(桩数据起盘)按帧量 `.hb-actbar` 的 `getBoundingClientRect` —— 动画期间 `gap-from-bottom` 是 **162px**(落在 `<main>` 盒底附近), 动画一结束跳成 **34px**(`--statusbar-h`)。同期 `<main class="ce-page hub-page">` 的 `getComputedStyle().transform` 从 `matrix(1,0,0,1,0,4)` 渐归 `none`。根因: `.ce-page`(components.css)挂着入场动画 `.ce-page { animation: page-in .2s }`, `@keyframes page-in { from { transform: translateY(4px) } }`; 三个 fixed 元素都是 `<main class="ce-page hub-page">` 的**直接子节点** ⇒ 动画期间 `<main>` 带 `transform` ⇒ 按规范成为它们的**包含块**, `bottom: var(--statusbar-h)` 从「相对视口」变成「相对 `<main>` 盒」; `<main>` 不够高(高视口 / 内容少)时动作条就落在页面中段, 动画结束 transform 归 none 才跳回。**与静态 clip-path 版同根因, 只是 transform 是瞬时的**。
  ⚠ 排查易误判: 直觉会怀疑内层 `.hb-view.on { animation: hb-in }`(也带 transform), 但 `.hb-view` **不是**这三个 fixed 元素的祖先(hub 页里 `.hb-view` 包在 `.hb-wrap` 内, 动作条/浮窗是 `.hb-wrap` 的兄弟), 其 transform 无害 —— 必须看清 fixed 元素的**最近带 transform 的祖先**是谁。
- **处置**: 在 `shared/console_hub.css` 给设置页关掉 `page-in`(`.hub-page { animation: none; }`; console_hub.css 三套皮肤都最后加载, 同特异性下覆盖 components.css 的本页规则), 入场交给内层 `.hb-view.on` 的 `hb-in`(只作用内容, 不动 fixed 元素)⇒ 观感不变、位移消失。**不动 `page-in` 全局定义** —— `.layout`(种子等视图)没有这类 fixed 子节点, 位移入场可保留。通用解仍是让 fixed 后代脱离会动画的祖先(或该动画一律只动 opacity, 不带 transform)。
- **守阵**: `shared/console_hub.css` 的 `.hub-page` 段内已钉死原因注释(含本坑与 `.hb-view.on` 不背锅一句)。
