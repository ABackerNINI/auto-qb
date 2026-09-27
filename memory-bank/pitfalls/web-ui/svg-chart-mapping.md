# SVG 图表鼠标映射与 aspect-ratio 压扁

> 摘要: 内联 SVG 图表(viewBox + aspect-ratio)的鼠标坐标换算若假设"SVG 铺满容器", 一旦 CSS 把高度压扁(preserveAspectRatio 居中 letterbox)映射整体错位; 共享 CSS 里残留的固定 height 会以特异性压过主题的 aspect-ratio 静默复现此症。
> 触发: 改图表悬停, 改 SVG 尺寸, 改图表 CSS, 图表 tooltip 不跟手, 十字线偏移, 图看起来偏窄, letterbox

### SVG 悬停换算必须按"实际渲染缩放"算, 不能假设铺满容器

- **触发**: 改 SVG 图表的鼠标取值/十字线/tooltip; 改图表容器或共享层 CSS 尺寸。
- **判别**: 图表绘制区与容器等宽但内容居中偏小(letterbox), 或鼠标横移时十字线/取值明显滞后或跳变 ——
  说明 `px = (clientX - rect.left) / rect.width * viewBoxW` 的"铺满假设"已被打破。
  真实案例(2026-09-27): `shared/console_hub.css` 残留 `.hb-chart svg { height: 128px }`(特异性 0,1,1)压过主题
  `.ce-chart-svg { aspect-ratio: 560/210 }`(0,1,0) ⇒ 560×210 的图被压进 128px 高, 绘制区缩到约 61% 宽且水平居中,
  图"看着窄"、悬停映射整体错位 —— 该规则是旧版小图残留, 且三主题 CSS 全对、错误在共享层, 极难直觉定位。
- **处置**: ①换算一律走几何真相: `scale = min(rect.w / viewBox.w, rect.h / viewBox.h)`,
  `offX/offY = (rect尺寸 − viewBox×scale)/2`(preserveAspectRatio 居中), 再 `(clientX − rect.left − offX) / scale`;
  tooltip 定位同理, 用 SVG 的 rect 相对容器的偏移还原成真实像素百分比, 不用 viewBox 百分比直减。
  ②CSS 纪律: aspect-ratio 驱动的图表**不允许任何层再写固定 height**(含共享/历史规则); 删残留时连带查
  `.xxx-chart svg` 这类裸元素选择器对主题类的特异性压制。
  ③验收: 故意把容器压成错误高度再悬停, 取值仍应正确(冒烟页 `resources/curve-chart-smoke.html` 的 .squash 用例)。
