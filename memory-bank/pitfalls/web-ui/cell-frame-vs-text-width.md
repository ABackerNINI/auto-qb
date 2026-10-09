# 强调框/整格线挂 grid 单元格 div 上随列宽 (筛选强调框宽度错误)

> 摘要: 表格行是 grid, 值单元格 div 被拉满整列宽 —— 把强调框(`.f-cell.f-on` 的 inset box-shadow)或整格线挂在这个 div 上, 框随**列宽**而非文字宽。修法 = 包一层贴文字的内联块包裹层(`.m-dur` 的 `.dur-body` / 保存路径的 `.sp-body`)承载强调与点击, 省略号职责随框走(`max-width:100%` + overflow hidden)。chip 类(site/tag/cat)是 inline 元素天然贴文字, 不中招。
> 触发: 筛选强调框, f-on, f-cell, 强调框宽度错误, 框随列宽, 不贴文字, g-save-path, sp-body, dur-body, 保存路径, 路径筛选, 整格线, hr-line, grid 单元格, 拉满列宽, inset box-shadow, 点筛选框太大

**Refs:** memory-bank/tasks/26-10-09-webui-path-filter-frame-width.md,memory-bank/testing/baselines/26-10-09-2112-webui-path-filter-frame-width.md

### 路径筛选强调框(f-on)随保存路径列宽

- **触发**: 给 grid 行里可点筛选的单元格(模板挂 `f-cell` + `f-on`, 点击走 `filterFromChip`)写强调样式 `.f-cell.f-on { box-shadow: inset 0 0 0 1px currentColor }`。站点/标签/分类 chip 是 inline 元素没问题; `.g-save-path`(保存路径列)是拉满列宽的块级 div —— 点路径筛选后强调框撑满整列。用户报障口径「点击路径筛选后匹配的路径强调框宽度错误, 宽度跟随保存路径栏宽度而不是文字宽度」(2026-10-09)。
- **判别**: 强调元素是不是 grid/flex 行里被拉伸布满的**块级单元格本身**(判据: 单元格在模板上是 `div` 直接承载 `f-cell`)。同族前科: `.m-dur` 的整格 hr-line 曾挂在 `.m-dur` 上画成整列一条, 教训只写在 torrents.html 模板注释里(「整格线必须挂 .dur-body(文字包裹层)」), 未入坑档路由不到。凡「框/线宽度 = 列宽而预期 = 文字宽」都查这一条。
- **处置**: 文字包一层内联块包裹层, `f-cell`/`f-on`/`@click`/`:title` 的框职责整体挪上去(外层 div 只留列省略兜底); 包裹层自带 `display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; vertical-align:bottom` —— 短路径框贴文字, 超长路径铺满整列并省略、不破列。本次: torrents.html / groups.html 保存路径格内包 `<span class="sp-body f-cell">`, 三皮肤(atlas/console/prism)views.css 各增一条 `.g-save-path .sp-body` 规则(单页应用全局生效, 每皮肤一处即可; atlas/components.css 已顶 700 行上限, 新规则别往里塞)。
- **守阵**: 无专项 —— 视觉宽度类缺陷, `tests/test_webui_static_skins.py` 只保结构与体量不超限; 真机核验走截图目检。
