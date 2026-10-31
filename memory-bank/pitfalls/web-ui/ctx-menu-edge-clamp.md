# 视口钳位 e2e: 锚点不贴缘的断言恒真; 左缘 clamp 真实手势结构不可达

> 摘要: 视口钳位 e2e: 锚点不贴缘的断言恒真; 左缘 clamp 真实手势结构不可达
> 等级: L0
> 触发: 视口钳位, 左缘, 右缘, ctx-menu, EDGE, e2e 断言, 恒真, 顺带断言, 红验, clientX, 滚动容器左缘

**Refs:** memory-bank/issues/26-10-20-0148-test-webui-ctx-menu-left-edge.html

### 给浮层写"贴缘"几何断言前, 先让锚点真的贴缘 —— 否则恒真

- **触发**: 给浮层(右键菜单/下拉/弹层)补视口钳位的 e2e 回归断言, 图省事挂在既有用例尾部当"顺带断言"(如垂直用例里附一条右缘 ≤ 视口宽-8)。
- **判别**: 锚点远离被测缘时断言恒真 —— 实例: 顶层 `.ctx-menu` 的右缘断言嵌在垂直 CTX-fit 用例里, 锚点在行左缘(clientX≈14), 菜单盒 14..210 距两缘数百 px, 右缘钳位全拆这条也绿。写断言前先回答"它在什么行为破坏下会红"(red-verify-must-hit-behavior 同旨), 答不出就是恒真。
- **处置**: 横轴/纵轴各安排锚点贴缘的独立用例(锚点贴滚动容器右缘 clientX≈1426 / 底部带行), 断言随即可红; 恒真的顺带断言从原用例移除, 别留"看着有守阵"的假象。

### 左缘 clamp(EDGE=8)真实手势结构不可达 —— 行可点击区被滚动容器左缘钉在 ≥12

- **触发**: 想用真实右键手势验"菜单贴视口左缘打开时左缘 ≥ 8"(clamp 咬合需要 clientX < 8)。
- **判别**: 表格滚动容器 `.group-table` 的左缘被 `.layout` 的 12px padding 钉死(实测 x=12, 双皮肤同), 且容器 `overflow-x:auto` 会把伸出部分裁掉 ⇒ 行可点击区恒 ≥12, `clientX<8` 的点落在容器外的 `.layout` 上(行 handler 不触发); 横滚容器也救不了(行左缘可以 <8, 但可点击区仍以容器可见区为界)。没有键盘开菜单路径( shortcuts.js 无 Menu 键绑定), headMenu/filePrio/drawerMenu 的锚点同样 ≥12。
- **处置**: 派发**合成 contextmenu**(`new MouseEvent('contextmenu', {bubbles, cancelable, clientX: 2, clientY})`, dispatch 在真实行元素上)—— 事件仍走真实链路 `@contextmenu → openMenu/openMemberMenu → _menuPos → _menuFit` 实测重钳位, 不借道 vm(D4 守则禁的是 vm 旁路; e2e 里 dispatchEvent 有先例)。配套注释写清"为何真实手势不可达", 否则下一个人会以为是懒惰。
- **守阵**: `e2e/menus.spec.mjs` CTX-fit 横轴两支(右缘真实手势 / 左缘合成事件), 双皮肤; 红验两类突变各自判红不误红。
- **复发**: 0
