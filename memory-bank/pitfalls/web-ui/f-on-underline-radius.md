# 强调线沿 border-radius 画成弧 (筛选底线不直)

> 摘要: 列表筛选选中强调(`.f-on`: 站点/标签/分类胶囊 + 站点/路径文本格)若用 `box-shadow: inset 0 -Npx 0 0 currentColor` 画底线, 线会**沿 border-radius 走** —— 在胶囊(radius:999px)上画成两端翘起的弧, 不是笔直横线(用户报「改为笔直的横线」)。且 `border-radius` 单独**不裁后代**, 换 `::after` 画线时必须给宿主 `overflow:hidden`, 否则直线两端会戳出圆角轮廓。处置 = 绝对定位 `::after`(left/right:0·bottom:0·height:2px·background:currentColor) + 宿主 `position:relative; overflow:hidden`; 不用 `background-image`(会与 `.f-cell:hover`/`.site-chip.<状态>` 的 `background` 互相覆盖)。
> 触发: 改筛选强调线, f-on, 下划线不直, 底线成弧, 两端翘起, 胶囊下划线, inset box-shadow 圆角, border-radius 不裁后代, 笔直横线, ::after 底线, overflow hidden 裁边, 强调线形状

**Refs:** memory-bank/tasks/26-10-10-webui-filter-underline.md,memory-bank/testing/baselines/26-10-10-1807-webui-filter-underline.md

### 强调底线在胶囊上成弧

- **触发**: 给 `.f-on`(筛选选中强调)写 `box-shadow: inset 0 -2px 0 0 currentColor` 当底线; 胶囊类(站点/标签 chip, `border-radius:999px`)上用户报"线不直、两端翘起"。
- **判别**: 强调元素是**圆角**形状且要"直线"时, 一律查这条。`box-shadow` 的 inset 阴影 = 形状减去自身位移, 它**跟着 border-radius** 走; `background` 同样被圆角裁。凡"线/边不直、随圆角弯"都查这条。
- **处置**: 用绝对定位 `::after` 画直线(恒水平, 不随圆角): `content:""; position:absolute; left:0; right:0; bottom:0; height:2px; background:currentColor;` 宿主加 `position:relative; overflow:hidden` —— **`border-radius` 单独不裁后代**, 缺 `overflow:hidden` 直线两端会戳出圆角。绝对定位不动流。**别用 `background-image`** 画这条线: `.f-cell:hover` 与 `.site-chip.<状态>` 也写 `background`, 会互相覆盖(故用 `::after`)。详见 `tasks/26-10-10-webui-filter-underline.md`。
- **守阵**: 无专项 —— 视觉类, 真机目检。
