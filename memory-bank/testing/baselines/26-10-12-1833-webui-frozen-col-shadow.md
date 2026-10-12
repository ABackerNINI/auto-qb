# 3146 —— WEBUI 名称列后"随机阴影"移除(首列吸左边界落影整条删除)

**Refs:** memory-bank/tasks/26-10-11-webui-frozen-col-boundary.md,memory-bank/pitfalls/web-ui/frozen-column.md

> 摘要: 用户报「WEBUI 名称列后随机出现阴影, 移除阴影」并附截图, 自注「可能是上次修右滑名称遮挡问题时引入的, 或者新表格引擎引起的」。取证(截图逐行测像素 + 桩服务真浏览器复现)确认**是 2026-10-11 那条边界提示里的右缘落影**(`16px 0 14px -10px rgba(0,0,0,.55)`), **不是**新表格引擎引起: 落影的可见度是**首格高度的函数** —— `spread: -10px` 先从首格四周内缩 10px 再 `blur: 14px`, 常态行首格仅 22px 高 ⇒ 落影矩形塌成 2px、只剩模糊尾巴(近不可见, 实测该列最暗处只比行底低 Δ≈2.0/255); 站点/标签多 chip 格换行把行撑高时首格 46px+ ⇒ 落影矩形 26px+ 完整显形(Δ≈13.7/255)。同一"横滚"状态逐行深浅差 7 倍, 只在"刚好被撑高的那几行"冒黑块 —— 正是用户描述的"随机"。修 = 三皮肤 `css/views.css` 删掉落影, 只留与高度无关的发丝线(`inset -1px 0 0 var(--border)`); 守阵 `test_frontend_frozen_column_boundary_wiring` 由"必须有落影成分"翻成"**不得**有 `rgba(0, 0, 0`"(红验: 注入回潮即红 / 还原即绿)。机理入坑档 `pitfalls/web-ui/frozen-column.md` 第④b条。
> 基线时间: 2026-10-12 18:33

上一基线: memory-bank/testing/baselines/26-10-12-1806-traffic-limits-warn-sentinel-ci-fix.md

## 本波改动面

- `src/auto_qb/webui/static/{prism,atlas,console}/css/views.css`: `.group-table.is-hscrolled .group-row > :first-child, .group-head.is-hscrolled > .h-cell:first-child` 的 `box-shadow` 由
  `inset -1px 0 0 var(--border), 16px 0 14px -10px rgba(0, 0, 0, .55)` → `inset -1px 0 0 var(--border)`(只删落影, 发丝线保留);
  规则上方的注释块改写成"删落影的根因"(负 spread 与首格高度的耦合), 三皮肤逐字同改。
- `tests/test_webui_static_skins.py`: `test_frontend_frozen_column_boundary_wiring` 的第 4 条判据
  由 `assert "rgba(0, 0, 0" in body` 翻成 `not in body`(声明式契约: 落影回潮即红) + 测试计划 1 行 + 函数 docstring 补第 4 点。
  **零测试增删**(collected 3150 = 3146 passed + 4 skipped)。
- `memory-bank/pitfalls/web-ui/frozen-column.md`: 第④条改口径(只留发丝线) + 新增 ④b 条(负 spread 落影 × 行高不齐的通用教训) + 摘要/触发/小节标题同步。

## 验收数字

- `test.full`: **3146 passed + 4 skipped, 0 failed** / 52.36s / 覆盖率 `TOTAL 16708 161 5688 140 99%`。
- 红验两条(闭环): ① 把落影注入回 atlas `views.css` ⇒ 守阵**即红**(`AssertionError`, 判据在第 4 条) → 还原**即绿**;
  ② 桩服务真浏览器(`atlas` + 种子页, 横滚 400px)读首格 computed `box-shadow`: 修前
  `rgb(37, 48, 69) -1px 0px 0px 0px inset, rgba(0, 0, 0, 0.55) 16px 0px 14px -10px` → 修后只剩 `rgb(37, 48, 69) -1px 0px 0px 0px inset`;
  截图逐列测像素: 名称列右缘外侧从"有暗带(Δ 最高 13.7)"变为"与行底同值(Δ 0)"。
- 注: 本片只测 Windows 侧; Linux 侧未重测(改动为纯 CSS + 一条断言方向, 无平台面)。
- 注: 本波**零测试增删**(只翻既有守阵的断言方向), 自证: `--collect-only` 收 3150 = 3146 passed + 4 skipped。
