# 居中弹窗内的浏览器量测假象

> 摘要: 在居中弹窗(.modal 等水平垂直居中容器)里用 getBoundingClientRect 量「内容增高把下方推下去多少」, 视口位移只有真实增量的一半 —— 弹窗增高时上下对半扩, 下方位移被「整体上移」抵消一半; 另有 body 内部滚动与 Playwright 塌缩元素两处同族假象。量测一律用「相对滚动容器顶 + scrollTop」的布局坐标。
> 触发: 真浏览器量弹窗内元素位移, 量展开/收起动画的推下量, 验证过渡动画, Playwright waitForSelector 塌缩元素超时, 量出来的位移比预期小一半

### 视口 rect 位移 = 真实增量的一半(居中弹窗)

- **触发**: 验证「弹窗内某行展开后下方内容下移多少」这类断言(如本例: 跳检警告行展开 17.8px + margin 7px, 期望下方移 24.8px)。
- **判别**: `el.getBoundingClientRect().top` 前后差远小于展开增量(实测 24.8px 只量到 8.9-12.4px, 各次不等), 但 scrollHeight 确实涨了全量 —— 无报错, 纯量测口径错。机理: `.modal` 居中定位, 内容增高 Δ 时弹窗上下各扩 Δ/2, 弹窗内元素视口位移 = Δ/2(上移抵消一半); 弹窗不居中或顶部锚定时无此现象。
- **处置**: 量测用布局坐标: `el.rect.top - scrollContainer.rect.top + scrollContainer.scrollTop`(相对滚动容器顶), 对居中扩高与内部滚动双重免疫; 或量 `scrollHeight`/`offsetTop` 差。

### 同族假象两处: body 内滚 + Playwright 塌缩元素

- **触发**: 弹窗 body 是 `overflow-y:auto` 的限高容器时量视口坐标; 或对塌缩态(height 0)元素用 Playwright `waitForSelector`。
- **判别**: 前者 —— 点击控件触发浏览器自动滚动, 视口坐标叠一层抖动, 同一断言各次量值不等; 后者 —— 选择器解析到了元素却超时, 症状像「元素没渲染」, 实为 height 0 永远不算 visible。
- **处置**: 前者同上用布局坐标; 后者用 `{ state: "attached" }`, 或直接量 computed height 断言为 0(塌缩本身就是被验行为)。
