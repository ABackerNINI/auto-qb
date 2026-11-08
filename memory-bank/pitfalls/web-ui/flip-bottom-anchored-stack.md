# 底部锚定的浮层栈做 FLIP: `offsetTop` 恒为 0, 动画静默不播

> 摘要: 底部锚定的浮层栈做 FLIP: `offsetTop` 恒为 0, 动画静默不播
> 触发: FLIP 队列重排, toast 栈, offsetTop, offsetHeight, 位移动画没效果, getAnimations 为空, 瞬移, 底部锚定, position:fixed bottom, 提示条排队

### 给「底部锚定」的浮层栈补 FLIP 时, 位置必须用视口坐标量 —— 容器内的 `offsetTop` 对它恒为 0

- **触发**: 给提示条栈(`.toast-wrap`, `position: fixed; bottom: …`)补 D6-3 队列重排: 想用"上一轮的
  `offsetTop` 对现布局"算 FLIP 位移, 于是记 `{ top: n.offsetTop, h: n.offsetHeight }`。
- **现象**: 代码看着完全对, 但队列重排完全不动 —— 新条插入时邻居条**瞬移**到新位置,
  `getAnimations()` 里没有任何 translate 关键帧; 控制台零报错。改成 `getBoundingClientRect()`
  立刻就好了, 但**动画中途再测**又会出问题(见下)。
- **判别**: 浏览器里 `node.getAnimations()` 只有 CSS 入场动画(`fx-toast-rise` 的 transform 关键帧),
  没有我们自己造的那条; 在 flipStack 里打点会看到 `dy` 恒等于 0 且 `prev.top === now.top`。
  反证: 把同一次插入换成 `getBoundingClientRect()` 立刻播动画 ⇒ 就是坐标系选错了, 不是动画 API 的问题。
- **根因**: 栈是 `position: fixed; bottom: 34px` 的 flex column —— 新条插到底部时**容器整体上移**,
  而各条在容器内的 `offsetTop` 一点没变(首项恒 0)。FLIP 读到 `dy = 0` ⇒ 判定"没动" ⇒ 不播动画。
  用户看到的位移发生在**视口坐标**里, 不是容器坐标里。
- **次生坑**: 改用 `getBoundingClientRect()` 之后, 若在上一轮 `transform` 还在跑时测量, rect 被
  transform 带偏, 位移会被算成 0 —— 同样静默失效。**量之前先把自己上一轮的 WAAPI 动画 cancel 掉**
  (用 WeakMap 存句柄, 只 cancel 自己造的, 别碰 CSS 入场动画: `getAnimations()` 里两者混在一起)。
- **处置**(落点 `flux/fx-mount.js::flipStack`): 两遍走 —— ① 先对每个节点 cancel 自己的动画并用
  `getBoundingClientRect()` 量视口位置(存 WeakMap); ② 再拿上一轮的值比对: 高度变了(等待态结算成
  终态)就补 `height` 关键帧, 只是位移就补 `transform: translateY(dy) → 0`。底锚定容器里高度一动,
  上沿自然跟着走, 不需要额外补位移。
- **守阵**: 静态面 `tests/test_webui_static_skins_*.py::_scan_message_surface_parity` 钉「`toastSync`
  与 `toastDrop` 都必须调 `flipStack()`」(少一处 = 插入/退场有一侧回到瞬移); 行为面只能靠浏览器取证:
  `node.getAnimations()` 里应能看到 `translate`(邻居让位) / `height`(自身结算) 关键帧。
- **复发**: 0
