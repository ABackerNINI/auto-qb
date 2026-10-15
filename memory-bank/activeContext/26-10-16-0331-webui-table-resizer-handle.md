# 26-10-16-0331-webui-table-resizer-handle — 列宽拖拽把手: 粗细差根治(整列 hover 底色) + hover 高亮/线压文字修复

> 摘要: 用户报「各表列宽拖拽把手宽度不一致(种子页『分类』明显更细)」→ 只读调查(桩服务 + Playwright 像素级取证)定根因为**非整数缩放下的亚像素相位**(非列级问题) → 用户令「A/B 两方案分别实施后截图」→ 两版均被否(不惯利落 / 不常规也不好看) → 补判据证明**任何细线当主视觉都躲不开相位差**后定案**方案 C = 整列 hover 底色承担主视觉 + 2px 实色线退回位置指示**(Excel/Notion/AntD 口径, 相对基线仅 +1 行 CSS) → 用户验收桩服务时另报两问题: ①部分列 hover 未高亮 ②把手线压住右对齐列表头文字 —— 均定位根因并修复(三皮肤同步)。改动 5 个三皮肤 CSS 源文件, **零 Python / 模板 / 列宽算法改动**。
> 最后活动: 2026-10-16 03:31
> 状态: Done(修复已落地; 收尾回写随本专题入库)

**Refs:** memory-bank/tasks/26-10-16-webui-table-resizer-handle.md

## 本轮落点(细节单点在档案与坑档, 此处只留入口)

- **根因 ①(粗细差)**: 三皮肤 `.h-cell .resizer` 规则逐字一致(命中区 10px / 可见线 2px) ⇒ 不是列级问题; 根因 = 2px 细线在非整数缩放(125%)下逐列落**不同亚像素相位**, 渲染实芯宽度不一(同表内 ≈1.5 vs ≈2.3 设备像素); 相位 = 累计列偏移(拖过的列宽 / 隐藏过的列) × DPR 的小数部分 ⇒ 「细的是哪几列」运行时决定, 因人而异。
- **四方案实测对照(均 125%)**: 2px 基线 / 4px+`opacity:.55` / 3px 实色 / 铺满 10px 命中区 —— **全部逐列分两档** ⇒ 「细线当主视觉」不可行。
- **定案(方案 C)**: `.h-cell:hover { background: var(--surface-2) }`(与行 hover 同变量) + 2px accent 线保持原样充当位置指示; 色块宽几十 px, 抖动占比 <1%, 粗细观感天然一致。
- **根因 ②(hover 未高亮)**: prism 首列 `.group-head > .h-cell:first-child` 的 `background: var(--bg)`(特异性 0,3,1, 为吸左遮罩**必须不透明**)压过 `.h-cell:hover`(0,2,1) ⇒ 首列永不亮; 修法 = `background-image: linear-gradient(var(--surface-2), var(--surface-2))` 叠高亮(**不动** `background-color`, 保住遮罩)。console 另有「上一轮回切方案 C 时批量替换漏掉整列 `.h-cell:hover` 规则」(圆角差异) ⇒ 补回。
- **根因 ③(线压文字)**: 2026-10-06 去 `padding-right` 后右对齐列表头文字贴格子右缘, 线落列边界(R)上 ⇒ 盖住文字右 1px(11 个数字列实测 −1px); 修法 = 线移进 grid gap 中央 `right: calc(-1 * var(--tbl-gap, 10px) / 2 - 3px)` + `::after{left:6px}`, 热区仍跨边界(**抓握手感不变**), 用 `calc` 自适应 gap(抽屉 dt11 的 8px 也居中)。
- **落地文件**: 三皮肤 `views.css`(prism/atlas/console, 各含把手 `right` 与首列 hover) + 两处 `components.css`(atlas 把手规则迁出腾 700 行 cap → 705→694 / console 补回整列高亮与自适应)。
- **回写**: 新坑档 `pitfalls/web-ui/table-resizer-handle.md`(三类发现); 前序坑档 `pitfalls/web-ui/header-cell-gutter.md` 的 `right:-5px` 陈迹更新为 `calc` 口径并互链。

## 下一步 / 移交

- 桩服务已关(`dev.port-kill -- 8137`); 修复已落地并随本专题入库; 需再验收可 `commands run dev.harness` 重开。
- 闸门: test.full 全绿(数字见 `commands run kb.baseline` 最新切片, 与上基线持平); 皮肤守阵 `tests/test_webui_static_skins.py` 16 passed; kb.check / kb.docmap --check / doc.links 全绿; kb.index 已重建。
