# 4927 passed, 10 skipped, 3 warnings in 192.21s (0:03:12); TOTAL 22543 stmts / 152 miss / 7736 branch / 134 partial / 99% —— e2e 既有红修复(大表窗口化 + 右键菜单)全量测试基线

> 摘要: e2e 既有红修复(大表窗口化 + 右键菜单)全量测试基线
> 基线时间: 2026-11-03 08:20
**Refs:**

## 验收数字

- 汇总行: `4927 passed, 10 skipped, 3 warnings in 192.21s (0:03:12)`
- 覆盖率 TOTAL: `22543 stmts / 152 miss / 7736 branch / 134 partial / 99%`
- 定向 e2e（本轮）: `dt-live-update` 14 passed；`drawer-content-variant-tables` 6 passed；`ctx-custom` 2 passed；`menus` 30 passed / 6 skipped（既有 W5-off 条件组）

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`: `_rowWindow` end 改用容器 `vh`；`_winGapFor` 抽屉内容桥首拍逐帧收敛（不借主表 rowGap，上限 12 帧）；`_measureRowH` 过滤 `content-visibility` 跳过行并收窗后补两拍实测
- `e2e/drawer-content-variant-tables.spec.mjs`: dt11 树表批量后徽章期望 6→0（附乐观写依据注释）
- `e2e/ctx-custom.spec.mjs`: 定制块一级行数 19→20（注册表 `order.member` 20 行）
- `e2e/menus.spec.mjs`: CTX-04/05/06 按 `data-item` 锁定身份、`has-sub` 恒 2；CTX-sub fit hover 选择器加 `[data-item="sub-more"]`
- 该轮无 Python 产品代码改动；全量为上述改动后的 pytest 全量（含生成物守卫）
