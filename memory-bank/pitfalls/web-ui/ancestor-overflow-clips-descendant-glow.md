# 祖先 overflow:hidden 裁后代 box-shadow 外发光

> 摘要: 直接父容器的 `overflow:hidden` 裁剪边界连后代画在盒外的 box-shadow 外发光一起裁 —— hover 辉光只显一侧/两侧、静态值全对; `overflow: clip + overflow-clip-margin` 外扩放行即闭合, 不放弃内容裁剪语义。
> 触发: 祖先裁剪, overflow hidden 裁辉光, 父容器裁剪, 外发光缺失, 辉光缺边, 辉光只显一侧, overflow-clip-margin, overflow clip, 辉光放行, chip 辉光不统一, box-shadow 被裁, glow 缺边, g-tags, g-cat
**Refs:** memory-bank/tasks/26-11-14-webui-flux-chip-glow-ancestor-clip.md

## 本篇只回答

后代控件 box-shadow 外发光被**祖先容器** `overflow:hidden` 裁掉的坑: 症状与本体 clip-path 裁剪同形(辉光缺边、静态值全对), 但裁剪主体在父级、修法是外扩放行而非本体分层。控件本体 clip-path 裁自身绘制输出是另一坑(见 clip-path-clips-outer-glow.md), 两篇并列、不改写彼此。

### 直接父容器 overflow:hidden, 后代盒外辉光在容器边界被裁 (2026-11-13 实测)

- **触发**: 后代元素挂 box-shadow 外发光(hover 辉光 stack), 而其**直接父容器**带 `overflow:hidden` 做内容裁剪/文本省略 —— 实例: flux 表格筛选 chip 的父格 `.g-tags/.m-tags/.g-cat/.m-cat`(`components.css:340-341`; 四格无 padding、chip 紧贴上下边缘), `--fx-glow-stack` 最大层 `0 0 12px 3px` 必然越界, 用户读感「部分辉光仅显示一侧或两侧」。⚠ 本体自带的 `overflow:hidden`(文本省略)只裁自身内容、不裁自身盒外阴影 —— 裁辉光的是**祖先层**, 别在本体上找根因。
- **判别**: DOM 与 `getComputedStyle` 值完全正常(本体 boxShadow 逐字正确)—— 纯绘制层裁剪, 静态检查与 computed 断言全抓不到; 真浏览器目检见「辉光只显一侧/两侧」。像素采样定界(计划 26-11-12-1012 §02 最小 Chromium 实验): 同一子元素白色外发光采 RGB, 父 `hidden` 时容器外上/左 `[0,0,0]`/`[0,0,0]`, 父 `visible` 时 `[136,136,136]`/`[135,135,135]`, 容器内两者同为 `[203,203,203]` ⇒ 裁剪只发生在容器边界外。
- **处置**: 祖先改 `overflow: clip` + `overflow-clip-margin` 外扩放行 —— `clip` 不建立滚动容器、保留内容裁剪语义; margin 覆盖辉光最大半径(本项目 12px blur + 3px spread + 1px 硬芯 = **16px**, 实测 12px/24px 与 `visible` 放光效果一致)。**不用 `visible`**: 放弃内容裁剪语义, 牵动标签全量展开换行行高与吸左首格几何(attachments/frozen-column-constraints.md:53); **不用 `:has()` 动态切 visible**: 每帧样式重算, 且 focus-visible 分支不命中时辉光仍被裁; flux 专属规则带 `html[data-fx-preset]` 前缀落 fx-mount.css(components.css 恰 700 行禁净增)。实证: 提交 fa0eea6d(S1 放行 + S2 竖线迁层)/bf95eefb(S3 e2e)。支持面(MDN BCD 实查 2026-11-14): Chromium(`overflow-clip-margin` 自 Chrome 90, 双轴都 clip 才生效)与 Firefox(102)完整; **Safari / iOS Safari 无 `overflow-clip-margin`**(BCD `version_added: false`), `overflow: clip` 值亦需 Safari 16+ —— 不支持处 margin 被忽略, 退化为贴边裁剪, 辉光缺失与改前同观感、不另生破相; 本坑实证均为 Chromium, 非 Chromium 支持面未实测。
- **守阵**: `tests/test_webui_static_skins_skin.py::test_frontend_fx_tag_cat_chip_glow_layering`(删 overflow:clip / 迁层规则即红) + `e2e/flux-tag-cat-chip-glow.spec.mjs`(同一页面内放行态 vs 注入 hidden 基线的相对亮度差红绿双验)。
