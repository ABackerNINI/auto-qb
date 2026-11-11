# 6064 passed + 2 skipped, TOTAL 27073/65/9460/68 —— webui-guard-ref-drift 16 处指称改指全绿

> 摘要: webui-guard-ref-drift 16 处指称改指全绿
> 基线时间: 2026-11-12 06:12

## 验收数字

- `commands run test.full`: **6064 passed, 2 skipped** (193.98s), 覆盖率 TOTAL **27073 语句 / 65 miss / 9460 分支 / 68 br-partial (99%)** —— 与上一基线持平(纯注释面零行为变更)。

## 本改动面

- `src/auto_qb/webui/views_common.py`: 3 处注释改指(STATE_RANK 守阵 x2 → `webui_static_scan_js.py::_scan_state_rank`, `_scan_eta_sentinel` → `webui_static_scan_js.py::_scan_eta_sentinel`)
- `src/auto_qb/webui/static/shared/app.js`: 2 处(列隐藏守阵 → `webui_static_scan_css.py::_scan_column_cells_paired`, `_scan_state_rank` 指称改 `webui_static_scan_js.py`)
- `src/auto_qb/webui/static/shared/shortcuts.js` / `polling.js` / `traffic_card.js`: 各 1 处(`_scan_mixin_wiring` x2 / `_scan_pending_settle` → `webui_static_scan_js.py`)
- `scripts/ui_harness.py`: `test_frontend_static_bundle_health` 指称改 `test_webui_static_skins_skin.py`
- `tests/test_web_traffic_limit_card.py`: 三皮肤清单守阵泛称改指 `test_webui_static_skins_skin::test_frontend_template_split_wiring`
- `tests/test_web_shortcuts_registry.py`: 3 处(挂载成对泛称 → `webui_static_scan_js.py 的 _scan_mixin_wiring`; `_section_members` x2 → `webui_static_scan_common.py`)
- `tests/test_web_shortcuts_{cursor,drawer,engine}.py`: 各 1 处头部挂载成对泛称
- 记账: issue `26-11-12-0527` 翻 Done(补修复后补充), 收尾切片 `26-11-12-0603-webui-guard-ref-drift`
