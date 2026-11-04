# 玻璃可见度=面板alpha×遮罩alpha叠乘; flux全浮层玻璃化预算16

> 摘要: 玻璃可见度=面板alpha×遮罩alpha叠乘; flux全浮层玻璃化预算16
> 触发: 毛玻璃不可见, blur看不见, 弹窗玻璃没效果, 遮罩太浓, 半透明底透正文, backdrop-filter预算, _FLUX_BACKDROP_BUDGET
**Refs:** memory-bank/tasks/26-11-04-webui-flux-glass-popups.md

### blur 声明还在、底也半透明, 但玻璃肉眼不可见 —— 先算「面板底 alpha × 遮罩 alpha」的叠乘, 别只盯面板自己的底

- **触发**: 用户报「毛玻璃没效果/近乎没有」时, 只检查 `backdrop-filter` 声明存在与否、只调面板自身的表面底 alpha —— 漏看面板**背后还叠着一层遮罩**(modal-mask/hr-full-mask/add-drop-mask)的情形。实测两连坑: 26-11-02 消息面统一把 `.modal` 底换成 `--bg-elev`(.92) → blur 只剩 8% 透视; 26-11-03 修回 `--bg-card`(.82) 后仍不可见, 因为 `.modal-mask` 遮罩 `rgba(4,10,22,.72)` 把透到内容的通道压成 (1-.82)×(1-.72)≈**5%** —— 数学上就不可见, 肉眼读作「毛玻璃丢了」, 与 26-11-03 用户复报吻合。
- **判别**: 对挂 blur 的浮层自上而下列出叠层(面板底 → 遮罩 → 页面内容), 逐层取 alpha 连乘: 有效透视 = ∏(1-alpha)。>10% 才有可读的玻璃感; blur 能救的是「形变」不是「对比度」—— 遮罩过浓时 blur 输出本身就是一片死暗, 无悬浮内容可透。另一个易混项: 半透明底**无 blur** 时透出的是锐利正文(26-11-02 报障), 有 blur 时才是毛玻璃 —— 先确认浮层挂没挂 blur, 再算叠乘。
- **处置**: 调可见度的**主旋钮是遮罩浓度**(`.modal-mask` .72→.5), 其次才是面板底 alpha(玻璃面 `--bg-card` .82 保住, 别动近不透明档); flux 全浮层玻璃化口径(2026-11-04): 菜单/浮层族一律半透明底+blur(预算 16), `--bg-pop` 只剩 `.col-ghost`。给浮层新挂玻璃时同步抬 `_FLUX_BACKDROP_BUDGET` 并红绿双验。
- **守阵**: `tests/webui_static_scan_css.py::`_scan_flux_modal_frost`(① 弹窗两份 blur+半透明角色底 / ④ 玻璃化浮层族正钉 + .col-ghost 反向钉 / ⑥ `.modal-mask` 遮罩 alpha ≤ .6); `_scan_backdrop_filter` 预算恰 16。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
