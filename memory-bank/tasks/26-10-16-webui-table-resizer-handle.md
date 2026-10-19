# 26-10-16-webui-table-resizer-handle — 列宽拖拽把手: 粗细不一致根治 + hover 高亮/线压文字修复

**Status:** Done
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户报「WEBUI 各表列宽拖拽把手宽度不一致(种子页『分类』明显更细)」。真浏览器像素级取证(桩服务 `scripts/ui_harness.py` + Playwright, 三皮肤 × 100%/125%/150%)定位: 三皮肤 `.h-cell .resizer` 规则逐字一致, 粗细差来自**非整数缩放下的亚像素相位**(2px 细线 @125% 逐列实芯 ≈1.5 vs ≈2.3 设备像素), 且实测 2px/3px/4px+透明/铺满命中区四种细线方案**全都躲不开** ⇒ 改用成熟产品(Excel/Notion/AntD)口径: **整列 hover 底色承担主视觉 + 2px 实色线退回位置指示**(现对基线仅 +1 行 CSS)。用户验收桩服务时另报两问题一并修: ①部分列 hover 未高亮(prism 首列 `:first-child` 不透明背景特异性 (0,3,1) 压过 `:hover` (0,2,1); console 上一轮回切方案时漏掉整列高亮规则) ②把手可见线压住右对齐列表头文字(11 个数字列实测重叠 −1px, 线移进 grid gap 中央)。改 5 个三皮肤 CSS 源文件, 零 Python/模板/列宽算法改动。
**Topics:** webui-table-resizer-handle
**Refs:** memory-bank/pitfalls/web-ui/table-resizer-handle.md, memory-bank/testing/baselines/26-10-16-0331-webui-table-resizer-handle.md
## 原始请求

用户: 「WEBUI 各个表格中的列宽拖拽调整把手宽度不一致, 比如种子页的『分类』把手明显更细, 需要统一, 先做个简单的调查」→ 调查结论出来后: 「将 A 与 B 分别实施然后截图让我看看效果再决定」→ 「方案 A/B 都不满意, A 不够利落, B 不常规也不好看否定, 有没有成熟的解决方案」→ 「我查看了桩服务, 有个问题: 部分列 hover 未高亮; 另外有一个相关问题一并解决: 部分列把手离文字太近, 甚至少部分重叠, 需要调整; 暂定方案 C, 修复后装服务保持打开让我验收」→ 「清理桩, 收尾提交」。

## 思考过程与决策

- **调查(只读)**: ①源码层三皮肤 `.h-cell .resizer` 规则逐字一致(命中区 10px / `::after` 2px / 落点公式相同), 表壳组件给每列渲染同一个 `<span class="resizer">`, 无按列分支 ⇒ 排除「某一列写死细线」。②真浏览器实测(隐藏表头文字后逐列取像素剖面): 100%/150% 缩放所有列恒等, **125% 出现两档**(实芯 ≈1.5 vs ≈2.3 设备像素)。③根因 = **亚像素相位**: 默认列宽模板 `minmax(Npx, X.Xfr)` 的 `fr` 分配产生小数列宽 ⇒ 每列边界落在不同子像素相位; 相位 = 累计列偏移 × DPR 的小数部分, 由已拖列宽/隐藏列运行时决定 ⇒ 「细的是哪几列」因人而异。
- **方案 A/B/C/D 的取舍**: A(4px+透明)、B(铺满命中区)、D(3px 实色) 实测**全部逐列分两档** ⇒ 证明「细线当主视觉」不可行(相位与线宽/透明度无关); 否掉「JS 逐列吸附整设备像素」(成本高易回归)。定案 **C = 整列 hover 底色**(成熟产品 Excel/Notion/AG Grid 同款语言; 色块宽几十 px, 抖动占比 <1%), 2px 实色线保持原样。
- **hover 未高亮根因**: 首列 `.group-head > .h-cell:first-child { background: var(--bg) }` 为吸左遮住滑入的相邻列**必须不透明**, 特异性 (0,3,1) 压过 `.h-cell:hover` (0,2,1) ⇒ 首列永不亮。修法取「不动 `background-color`(保遮罩)+ `background-image: linear-gradient(...)` 叠高亮」。**踩坑**: 首版写 `background: var(--surface-2), var(--bg)`(多层简写两层都带颜色)**非法**, 整条声明被浏览器丢弃 ⇒ 改合法写法。另发现 console 在上一轮回切方案 C 时因圆角差异漏掉整列 `.h-cell:hover` 规则(该皮肤全列不亮), 一并补回。
- **线压文字根因**: 2026-10-06 为让表头文字与值同缘去掉了 `.h-cell` 的 `padding-right`, 右对齐列文字紧贴格子右缘, 而把手线落列边界(R)上 ⇒ 盖住文字右 1px(11 个右对齐数字列实测 −1px)。修法 = 热区仍跨边界(**抓握手感不变**), 只把可见线移进 grid gap 中央; 用 `calc` 自适应 `--tbl-gap`(抽屉 dt11 覆盖成 8px 也自动居中, 不写死)。
- **范围守恒**: 未动热区宽度(10px)、拖拽/双击自适应/Shift 互挤行为、列宽算法、表壳模板、列偏好持久化; 抽屉表与主表同源同修。
- **cap 连带**: atlas `components.css` 加注释后涨到 705 行超 700 单文件上限(皮肤守阵判红) ⇒ 把手规则迁入同皮肤 `views.css`(与首列规则同族, 该文件有余额)复绿。

## 实现计划

A. 三皮肤 CSS: 可见线移进 gap 中央(`right` 用 `calc` 自适应) + 整列 hover 底色 + 首列 `:first-child:hover` 高亮 → B. 处理 atlas 700 行 cap(把手规则迁 `views.css`) → C. 真浏览器三皮肤验证(逐列 hover 高亮 0 缺失 + 线距文字 ≥4px + gap 中央命中) → D. test.full + 皮肤守阵 → E. 收尾回写(坑档/切片/基线/索引) + ship.commit。

## 子任务状态表

| # | 任务 | 状态 |
|---|---|---|
| A | 三皮肤 CSS 落地(拐手线居中 + 整列 hover + 首列高亮) | Done |
| B | atlas 700 行 cap: 把手规则迁 views.css | Done |
| C | 真浏览器三皮肤验证(hover/间距/命中) | Done |
| D | test.full + 皮肤守阵 | Done |
| E | 收尾回写(坑档/切片/基线/索引) + 提交 | Done |

## 进度日志

- 2026-10-16 — **R1 只读调查轮**: 定位源码层无列级差异; 真浏览器像素级实测锁定亚像素相位(125% 同表内实芯 ≈1.5 vs ≈2.3 设备像素); 给出三方向(加粗降透明 / 铺满热区 / 收敛规则单点)。**零代码改动, 未入池 issue**。
- 2026-10-16 — **R2 实施方案 A/B 并截图**: A = 4px+`opacity:.55`; B = 铺满 10px 命中区底色; 截基线/A/B 三组(prism+atlas, 125% 测量视图+hover 实拍)供用户比对。
- 2026-10-16 — **R3 用户否 A/B → 定案 C**: 补测方案 D(3px 实色, VS Code/DevTools 同款)证明**细线方案全躲不开相位差**; 定案 C(整列 hover 底色); 三皮肤统一, 更新对比页。**发现**: 回切 C 时 console 的 `.h-cell:hover` 规则漏改。
- 2026-10-16 — **R4 验收报两问题 → 修复**: ①hover 未高亮 = 首列 `:first-child` 背景特异性压过 `:hover`(prism 修 `background-image` 叠层; atlas/console 首列规则在各自 `views.css` 一并修; console 补回整列高亮) ②线压文字 = 移进 gap 中央(`calc` 自适应)。atlas `components.css` 触 705 行 cap → 把手规则迁 `views.css`。三皮肤诊断全绿(未高亮 0 列 / 线距文字 ≥4px)、皮肤守阵 16 passed。
- 2026-10-16 03:31 — **R5 收尾**: `dev.port-kill -- 8137` 关桩; test.full 全绿(数字见基线切片); 回写坑档 `pitfalls/web-ui/table-resizer-handle.md`(新建, 三类发现) + `header-cell-gutter.md`(更新陈旧 `right:-5px`); 切片 + 基线 + kb.index; 提交随本专题入库。
