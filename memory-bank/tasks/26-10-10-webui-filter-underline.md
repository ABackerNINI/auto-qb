# 26-10-10-webui-filter-underline — 列表筛选选中强调改笔直下划线

**Status:** Done
**Added:** 2026-10-10
**Updated:** 2026-10-10 18:07
**Topics:** webui-filter-underline
**Summary:** 用户要求「将筛选器选中强调的效果从框改为下划线, 注意要统一」, 范围拍板 = 列表内挂件/文本格(`.f-on`: 站点/标签/分类胶囊 + 明细站点格/路径格), 不含下拉弹层/状态图例/筛选按钮。实施: 三皮肤把 `.f-on` 的 inset 描边环统一改为 2px 底线; 首版用 `inset 0 -2px 0 0 currentColor`, 用户复报「改为笔直的横线」—— box-shadow 会沿 border-radius 画成弧(胶囊两端翘起), 遂改用绝对定位 `::after` 直线 + 宿主 `overflow:hidden` 由圆角裁边(绝对定位不动流)。同步更正连带注释与 `modules/webui-static-contract.md` 契约回写。test.full 全绿(见基线切片)。
**Refs:** memory-bank/testing/baselines/26-10-10-1807-webui-filter-underline.md,memory-bank/pitfalls/web-ui/f-on-underline-radius.md,memory-bank/activeContext/26-10-10-1807-webui-filter-underline.md

## 原始请求

> 用户(2026-10-10): 「将筛选器选中强调的效果从框改为下划线, 注意要统一」
> 用户(2026-10-10): 「改为笔直的横线」

## 思考过程与决策

- **范围确认**: "注意要统一"含义有歧义, 逐项问清后用户只勾「列表挂件/文本格」—— 即 `.f-on`(站点/标签/分类胶囊 + 明细站点格 `.m-site.f-cell` + 路径格 `.sp-body.f-cell`); 下拉弹层选中项(`.pop-item.on`)、状态图例(`.dist-chip.active`)、顶栏筛选按钮(`.filter-btn.active`)**不改**。
- **统一口径**: 改动前胶囊 1.5px 环、文本格 1px 环(本身不一致) —— 合并为同一条规则、同一厚度(2px), 三皮肤逐字对齐。
- **框→线(第一版)**: `box-shadow: inset 0 -2px 0 0 currentColor`; 保留 currentColor 语义, inset 不被 console 皮肤 clip-path 裁掉, 不改布局。
- **线→笔直横线(第二版)**: 用户复报要"笔直"。**box-shadow 的 inset 底线会沿 border-radius 走** —— 胶囊(999px)上画成两端翘起的弧。改用绝对定位 `::after`(left/right:0·bottom:0·height:2px) 画直线, 宿主 `overflow:hidden` 让圆角把线两端裁齐; 绝对定位不动流。用 `::after` 而非 `background-image`, 避开 `.f-cell:hover` 与 `.site-chip.<状态>` 的 `background` 冲突。
- **副作用**: `.f-on` 态宿主加 `overflow:hidden` ⇒ 超长站点名在选中态会裁切(不再溢出); 站点名通常极短, 影响可忽略。

## 实现计划

- **S1** 三皮肤 `.f-on` 规则: 框→底线(合并胶囊/文本格, 统一 2px)。
- **S2** 用户复报: 底线 box-shadow → 绝对定位 `::after` 直线 + `overflow:hidden`。
- **S3** 连带回写: 三皮肤路径格注释 + 两份模板注释 + `modules/webui-static-contract.md`。
- **S4** 验证 + 收尾: test.full + 坑档 + 档案 + 切片 + 基线 + kb.index。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 三皮肤 `.f-on` 框→底线 | Done |
| S2 | 底线改 ::after 笔直横线 | Done |
| S3 | 注释与契约文档回写 | Done |
| S4 | 验证 + 知识库收尾 | Done |

## 进度日志

- **2026-10-10 18:07** 全部落地。开工 sync 快进 5303e64a→55ea1aa6 → 按范围问询确认后改三皮肤 `.f-on`(框→2px 底线)→ 用户复报"笔直横线"→ 改绝对定位 `::after` + `overflow:hidden` → 连带注释/契约回写 → `test.full` 全绿(基线切片 26-10-10-1807)→ 坑档 `pitfalls/web-ui/f-on-underline-radius.md` 入库 → `kb.index` 重建。
