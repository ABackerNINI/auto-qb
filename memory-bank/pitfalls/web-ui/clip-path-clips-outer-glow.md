# clip-path 切角裁掉 box-shadow/filter 外发光

> 摘要: 控件本体的 `clip-path` 切角会连绘制层一起裁 —— 同元素上的 box-shadow 外发光(hover 辉光)/filter/drop-shadow 被裁成只显一侧/两侧, 把 clip-path 挪进 `::before` 绘制层、本体 `clip-path: none` 即闭合。
> 触发: 切角, clip-path, 外发光, 辉光, box-shadow 被裁, glow 只显一侧, glow 缺边, hover 辉光不统一, 状态 chip 切角丢失, 切角丢失, filter, drop-shadow, site-chip, 形状分层
**Refs:** memory-bank/tasks/26-11-11-webui-flux-chip-hover-glow.md

## 本篇只回答

同一元素上「clip-path 切角」与「box-shadow/filter 外发光」互斥的坑: 什么形态会踩、怎么判别、怎么用形状/辉光分层解。clip-path 裁 fixed 后代是另一坑(见 clip-path-clips-fixed.md), 不在本篇。

### clip-path 切角元素挂 box-shadow 外发光, 辉光被切角形状裁掉 (2026-11-10 实测)

- **触发**: 给带 `clip-path` 切角的控件本体(flux `.site-chip` 八组状态 polygon)再加 box-shadow 外发光(hover 辉光 stack)或 filter/drop-shadow —— clip-path 不只裁背景, 它裁**整个元素及其阴影的绘制输出**, 向外扩散的辉光被切角形状剪掉。兄弟坑 `f-on-underline-radius.md` 的「border-radius 不裁后代、clip-path 裁」在这里再次应验。
- **判别**: 真浏览器目检: 辉光只显一侧/两侧或整体缺失, 切角方向侧明显无光; DOM 与 `getComputedStyle().boxShadow` 值完全正常 —— 纯绘制层裁剪, 静态检查与样式值全对也发现不了。第二种症状: 把本体描边/形状迁层后, 状态 chip(paused/other/search-hit)的切角丢失 —— 切角画在哪一层就要在那一层补齐, 漏迁就是丢。
- **处置**: **形状与辉光分层** —— ① 切角 `clip-path: polygon(...)` 从本体挪到 `::before` 绘制层(切角 + 语义柔底 + 状态描边都在 ::before 画, 本体只留辉光面); ② 本体 `clip-path: none`, box-shadow 外发光即四边闭合; ③ 本体 box-shadow 同属性覆盖: 常态 inset 描边会被 hover stack 整体替换(R7), 一并迁入 ::before 层绘制才能 hover 边线持续可见; ④ flux 专属规则全部带 `html[data-fx-preset]` 前缀, 避免新选择器进四皮肤键集守阵红。实证: 提交 399bdb2e(分层落地)/644f3274(守阵+e2e)/f7f4658c(状态边线迁层, 由用户真机目检触发)。
- **守阵**: `tests/test_webui_static_skins_skin.py::test_frontend_fx_site_chip_shape_layering`(本体无 clip-path + polygon 在 ::before, 「不设防」口径) + `e2e/flux-site-chip-shape-glow.spec.mjs`(主判据 computed `clipPath`, 旁证 `boxShadow`, crisp 逐层 alpha=0)。
