# 6064 passed + 2 skipped —— webui 键帽提示计划入库 + 键位守阵注释漂移修复 + 电池补桩

> 摘要: webui 键帽提示计划入库 + 键位守阵注释漂移修复 + 电池补桩
> 基线时间: 2026-11-12 05:21

## 验收数字

`commands run test.full` 实测(2026-11-12 05:21, 本 clone HEAD 6e7b4478 + 本批未提交改动):

```
TOTAL                                                27073     65   9460     68    99%
6064 passed, 2 skipped in 192.95s (0:03:12)
```

差值口径: 上一切片 26-11-12-0258(webui-partial-group-warning)为 6063 passed + 1 failed(入库树 `test_r4_move_dialog_partial_disclosure_bar` 出生即红) —— 本切片红转绿: `tests/test_webui_static_r4_node_batteries.py` 的 `_NODE_MOVE_PARTIAL_DISCLOSURE_PROBE` mkCtx 补 `ensureWebFlags` 桩后 6064 passed + 2 skipped, 用例总数不变。

## 本改动面

- `src/auto_qb/webui/server/routes/keys.py` / `src/auto_qb/webui/static/shared/shortcuts.js` / `tests/web_shortcuts_support.py`: `_scan_keys_serial_re` 守阵指称漂移 3 处(不存在文件 `tests/test_webui_static_skins.py` → 定义点 `tests/webui_static_scan_js.py`), keys.py 与 shortcuts.js 互为「同一正则」对照面;
- `src/auto_qb/webui/static/shared/ctx_menu.js`: `:93` 注释次级计数过期 11 → 10(copy-magnet 退役后未同步);
- `tests/test_webui_static_r4_node_batteries.py`: S4 电池 mkCtx 补 `ensureWebFlags` 桩(照 loadMoveOptions/$nextTick 范式);
- 文档记录层: 计划 26-11-12-0344(Open) + 任务档案 + 坑档 subagent-survey-fact-verify + active-context 切片。
