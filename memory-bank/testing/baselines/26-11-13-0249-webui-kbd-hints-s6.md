# 6070 passed + 2 skipped —— webui 键帽提示 S1-S5 实施完成基线(取数单点/菜单键帽/顶栏 N-K/页签徽标/状态栏入口)

> 摘要: webui 键帽提示 S1-S5 实施完成基线(取数单点/菜单键帽/顶栏 N-K/页签徽标/状态栏入口)
> 基线时间: 2026-11-13 02:49

## 验收数字

`commands run test.full` 实测(2026-11-13 02:47, 本 clone HEAD b661be35, 分支 feature/webui-kbd-hints):

```
TOTAL                                                27073     65   9460     68    99%
6070 passed, 2 skipped in 198.95s (0:03:18)
```

差值口径: 上一切片 26-11-12-0521(webui-kbd-hints)为 6064 passed + 2 skipped —— 本切片 +6: 计划 26-11-12-0344 S1-S5 四笔实施新增守阵/电池用例(test_webui_kbd_keycap.py 电池扩容 + test_webui_ctx_menu_registry.py key 字段对账 + test_webui_static_dom_panel_dialogs.py / test_webui_trigger_registry.py 断言同步), e2e 侧新增 menus 键帽断言与 statusbar-kbd-entry.spec.mjs 不计 pytest 总数。

## 本改动面

- S1 `src/auto_qb/webui/static/shared/shortcuts.js` + `console_hub_panels.css`: 键帽取数单点 kbShortcutDisplay/kbShortcutDisplayOf + 共享 `.aq-kbd` 键帽类(令牌复用, 零新增令牌);
- S2 `ctx_menu.js` + `tpl/ctx-menus.html` + `ui_feedback.js`: 两条菜单注册表加 key 字段(引用注册表 shortcut id) + ctxRenderItem 增产键帽字段 + 键帽列(无键位留白对齐);
- S3+S4 `tpl/topbar.html` + `tpl/drawer.html` + `drawer.js` + `ctl_bits.js` + `state.js` + `shortcuts.js`/`shortcuts_panel.js`/`shortcuts_engine.js`: 顶栏添加种子 N / 列 K 内联键帽 + 抽屉页签 Alt+1..5 徽标(合并态与 KB_MERGE_TAB_REMAP 同一单点);
- S5 `tpl/statusbar.html` + `shortcuts_engine.js` + `triggers.js`: 状态栏「键位」入口钮 + Shift+/ 键帽(click 分派 = help-panel 同链);
- 守阵: `tests/test_webui_kbd_keycap.py`(新电池族) + `tests/test_webui_ctx_menu_registry.py`(key 字段对账扩面) + `tests/test_webui_static_dom_panel_dialogs.py` + `tests/test_webui_trigger_registry.py`; e2e: `e2e/menus.spec.mjs` 键帽断言 + `e2e/statusbar-kbd-entry.spec.mjs`(新) + drawer-merge 等五 spec 同步。
