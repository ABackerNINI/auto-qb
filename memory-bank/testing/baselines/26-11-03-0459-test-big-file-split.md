# 4924 passed + 2 skipped(根) —— R4 前端域拆分后全量基线

> 摘要: R4 前端域拆分后全量基线
> 基线时间: 2026-11-03 04:59
**Refs:** memory-bank/tasks/26-11-03-test-big-file-split.md, memory-bank/plans/26-11-02-2342-plan-big-file-split.html, memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html

## 验收数字

`commands run test.full` 实测(同步远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22543    134   7736    128    99%
4924 passed, 2 skipped, 3 warnings in 194.03s (0:03:14)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `shared/console_hub.css` 1589 → 291 行根段(文件名不变) + `console_hub_layout.css` 300 / `console_hub_controls.css` 496 / `console_hub_panels.css` 440; 四皮肤 `<link>` 按原连续段顺序 4 连, 层叠序与选择器优先级不变。
- `shared/drawer.js` 1543 → 916 + `drawer_files.js` 152 / `drawer_general.js` 348 / `drawer_rows.js` 207。
- `shared/config_hub.js` 1484 → 617 + `config_hub_hr.js` 185 / `config_hub_tracker.js` 252 / `config_hub_tm.js` 430。
- `shared/config_editor.js` 1475 → 736 + `config_editor_tree.js` 241 / `config_editor_form.js` 180 / `config_editor_curve.js` 300。
- `shared/shortcuts.js` 1442 → 428 + `shortcuts_engine.js` 804 / `shortcuts_panel.js` 211。
- `shared/columns.js` 1429 → 124 + `columns_menu.js` 330 / `columns_grid.js` 475 / `columns_persist.js` 215 / `columns_drag.js` 114 / `columns_computed.js` 191(computed 最后加载, 保「methods 先于 computed」断言)。
- `shared/commands.js` 1076 → 431 + `commands_optimistic.js` 224 / `commands_send.js` 432; `_runningToast`/`_settleRunningToast` 工厂留根(消息面守阵)。
- `shared/dialogs.js` 1022 → 720 + `dialogs_meta.js` 273 / `dialogs_history.js` 40。
- 片段一律 `Object.assign(window.AQB_*.methods, …)` 原地扩充, 加载序紧跟根文件; 四皮肤 `index.html` 清单与 CSS link 同步; 根 `window.AQB_*` 挂载名与 `app.mixin` 注册零改动。
- 守阵引用最小同步: `tests/webui_helpers.py` 新增 `SHARED_SPLIT_PARTS` / `read_shared` / `bundle_file`, 33 个测试文件与 2 个辅助模块改「域聚合读」; node 探针改聚合临时脚本; shell 体量上限按 +23 行推导抬到 256; 断言语义未改。
- 暂缓 2 个(`drawer_templates.js` 1170 / `qb_traffic_chart.js` 1142)与不拆 2 个(`fx/showcase.html` 2926 / `shared/app.js` 981)零改动; 新桶均 ≤1000 行(最大 804), 计划 §07 排期清单无新增。
