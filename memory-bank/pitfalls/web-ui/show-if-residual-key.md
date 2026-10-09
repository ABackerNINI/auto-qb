# show_if 把行藏掉 ≠ 键被删 —— 残留键让保存必败且 UI 无从修复

> 摘要: schema 字段的 show_if 只控制「这一行渲染不渲染」; 用户把触发键从命中值切走后, 该字段先前写进树的值**仍留在配置树里**(show_if 不删键), 行又已隐藏 ⇒ 用户看不见也改不了, 保存时后端校验对残留键报错(如 watch_fields 仅在 trigger: on_torrent_field_changed 下允许) ⇒ **保存必败且无法从 UI 自救**。处置 = 键残留会非法的条件下显隐一律改用 grey_if(灰显仍可见可编辑, 清得掉)。
> 触发: 给规则/段字段配 show_if; 切走关联键后保存报"该键非法"; 字段在某取值下才合法

## 触发 / 判别 / 处置

- **触发**: 字段 A 的合法性依赖字段 B 的取值(如 watch_fields 依赖 trigger), 给 A 配 `show_if=("B", v)`; 用户先在 B=v 下填了 A, 再把 B 切走 —— A 的行消失, 键还在, 保存报错且 UI 里找不到能改的地方。
- **判别**: 「展开时配过的字段在切走关联键后不见了, 保存却报该键的校验错」—— 到 GET /api/config(YAML)里看该键是否残留。grey_if 与 show_if 的语义差恰在这里: 灰显行仍可见、可编辑, 残留键清得掉(列表清空最后一项时前端自动删键, 见 config_editor.js::cfgItemRemove)。
- **处置**: 键残留会非法的, 一律 `grey_if` 而非 `show_if`; show_if 只用于「残留也合法 / 键由后端兜底剥离」的场景(空串会被 _strip_none 剥掉的键属此类)。本轮实证: 规则卡 watch_fields 由 show_if 改 grey_if(`schema/rules.py`)后, 冒烟里「切走触发时机 → 行灰显仍可见 → 清空条目 → 保存 200」全链走通。
- **守阵**: 后端语义(错 trigger 下 watch_fields 非法)由 `tests/test_trigger_events.py` 守; 前端行为走浏览器冒烟(一次性脚本, 判据记在任务档案)。

**Refs:** memory-bank/tasks/26-10-09-webui-rule-meta-fields.md
