# 3403 —— 列宽拖拽把手: 粗细不一致根治(整列 hover 底色) + hover 高亮/线压文字修复

> 摘要: 用户报「各表列宽拖拽把手宽度不一致(种子页『分类』明显更细)」。真浏览器像素级取证(桩服务 `scripts/ui_harness.py` + Playwright, 三皮肤 × 100%/125%/150% 缩放)定位根因为**非整数缩放下的亚像素相位** —— 三皮肤 `.h-cell .resizer` 规则逐字一致(命中区 10px / 可见线 2px), 但 2px 细线 @125% 逐列渲染实芯 ≈1.5 vs ≈2.3 设备像素; 实测四种细线方案(2px 基线 / 4px+opacity.55 / 3px 实色 / 铺满 10px 命中区)全躲不开 ⇒ 改用成熟产品口径「**整列 hover 底色承担主视觉 + 2px 实色线退回纯位置指示**」。验收时用户另报两问题一并修: ①部分列 hover 未高亮(prism 首列 `:first-child` 不透明吸左背景特异性 (0,3,1) 压过 `:hover` (0,2,1); console 上一轮回切方案时漏掉整列高亮规则) ②把手可见线压住右对齐列表头文字(11 个右对齐数字列实测重叠 −1px, 线移进 grid gap 中央)。改动 5 个三皮肤 CSS 源文件, **零 Python / 模板 / 列宽算法改动**。
> 档案: memory-bank/tasks/26-10-16-webui-table-resizer-handle.md
> 基线时间: 2026-10-16 03:31

**Refs:** memory-bank/tasks/26-10-16-webui-table-resizer-handle.md

## TOTAL

```
TOTAL                                               17337    182   5846    158    99%
3403 passed, 4 skipped in 117.51s (0:01:57)
```

- 语句 17337 / 未覆盖 182; 分支 5846 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 与上一基线 `26-10-16-0113`(3403 passed + 4 skipped)差 **0 passed, 已对账**: 本轮为纯 CSS 改动, **零新增 / 零修改用例**(未触任何 `tests/` 文件), TOTAL 四项与耗时量级均与上基线一致。
- 语句/分支总数与上基线**逐位相同** —— 本轮改动全在 `src/auto_qb/webui/static/*/css/*.css`(静态资源, 不进 Python 语句/分支统计)。
- 皮肤守阵 `tests/test_webui_static_skins.py` 单跑 16 passed(改 `atlas/components.css` 曾涨到 705 行超 700 上限 → 把手规则迁入同皮肤 `views.css` 后复绿; 详见档案)。
- Linux(WSL) 侧未重测 —— 纯 CSS 静态资源, 无平台分支。

## 本改动面

- `src/auto_qb/webui/static/prism/css/views.css` —— 把手 `right` 改 `calc` 自适应 gap + 首列 `:first-child:hover` 高亮
- `src/auto_qb/webui/static/atlas/css/views.css` —— 把手规则自 `components.css` 迁入 + 首列 hover 高亮
- `src/auto_qb/webui/static/atlas/css/components.css` —— 把手规则迁出(705 → 694 行)
- `src/auto_qb/webui/static/console/css/components.css` —— 把手 `right` 自适应 + 补回漏掉的整列 `.h-cell:hover`
- `src/auto_qb/webui/static/console/css/views.css` —— 新增首列 hover 高亮
