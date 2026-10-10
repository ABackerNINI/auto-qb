# 列表筛选选中强调: 框 → 笔直下划线

> 摘要: 用户要求「将筛选器选中强调的效果从框改为下划线, 注意要统一」, 范围拍板 = 列表内 `.f-on`(站点/标签/分类胶囊 + 明细站点格/路径格), 不含下拉弹层/状态图例/筛选按钮。三皮肤统一为 2px 底线; 首版 `inset 0 -2px 0 0 currentColor` 会沿圆角成弧, 用户复报后改绝对定位 `::after` 直线 + 宿主 `overflow:hidden` 由圆角裁边。基线 `26-10-10-1807`(见 kb.baseline); 机理入坑档 `pitfalls/web-ui/f-on-underline-radius.md`。
> 最后活动: 2026-10-10 18:07

**Refs:** memory-bank/tasks/26-10-10-webui-filter-underline.md

## 正在进行

- 无 —— 本轮已完成并收口(见 kb.baseline)。

## 关键结论(供后续改 `.f-on` 参考)

- **强调线一律走直线**: `inset box-shadow` 会沿 `border-radius` 画成弧(胶囊两端翘起), 想要笔直横线必须用绝对定位 `::after`(或等价的独立绘制层) + 宿主 `overflow:hidden`。详见坑档。
- **宿主须 `overflow:hidden`**: `border-radius` 单独**不裁后代**; 直线两端要贴圆角就必须让宿主建裁剪上下文(box-shadow/background 则天然被圆角裁)。
- **勿用 `background-image` 画这条线**: `.f-cell:hover` 与 `.site-chip.<状态>` 都写 `background`, 会与底线互相覆盖(故选 `::after`)。
- **范围只到列表**: 下拉弹层 `.pop-item.on`(淡底+左色条)、状态图例 `.dist-chip.active`(整圈描边)、顶栏按钮 `.filter-btn.active` 均**未改** —— 若日后要"全站统一", 从这里接手。
