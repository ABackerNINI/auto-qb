# 6070 passed + 2 skipped, TOTAL 27110/65/9478/68 —— 过期守阵指称族 css/html/e2e 面 7 处修复全绿

> 摘要: 过期守阵指称族 css/html/e2e 面 7 处修复全绿
> 基线时间: 2026-11-12 08:26

## 验收数字

- `commands run test.full`: **6070 passed, 2 skipped** (150.96s), 覆盖率 TOTAL **27110 语句 / 65 miss / 9478 分支 / 68 br-partial (99%)** —— 纯注释/文档面零行为变更; 较上切片的数字变动来自会话开工快进的远端提交, 非本轮改动(逐位对比见 `kb.baseline -n 2` 两条切片)。

## 本改动面

- `src/auto_qb/webui/static/atlas/css/views.css`: 1 处(拖拽把手注释的守阵指称改 `test_webui_static_skins_skin.py::test_frontend_template_split_wiring` —— 700 行体量 cap 断言的现行定义点)
- `src/auto_qb/webui/static/shared/tpl/settings-detail.html`: 1 处(例外额度注的守阵泛称改指 `test_webui_static_skins_skin.py`)
- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html`: 1 处(三变体列键并集守阵改指 `test_webui_static_skins_table.py::test_drawer_table_bridge_wiring`)
- `e2e/drawer-dock-stability.spec.mjs` / `hscroll-indicator.spec.mjs` / `main-table-pinned-hover.spec.mjs` / `main-table-pinned-selected.spec.mjs`: 各 1 处头注释改指拆分后现行守阵定义点(`_widget.py` / `_table.py`)
- 复扫: `src/` `e2e/` 的 css/html/mjs 中 `test_webui_static_skins(\.py)?[^_a-zA-Z]` 命中归零; 零逻辑/断言改动
- 记账: issue `26-11-12-0628` 翻 Done(补复验/实际修法/改道理由/验证待办口径), 任务档案 `26-11-12-webui-guard-ref-css-e2e` 立档, 会话切片 `26-11-12-0827-webui-guard-ref-css-e2e`, 评审 3 轮零 actionable
- 树态: 本片测在含本轮未提交注释/文档改动的工作树上
