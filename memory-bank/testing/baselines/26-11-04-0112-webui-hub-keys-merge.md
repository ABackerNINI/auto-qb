# 5014 passed + 2 skipped(根) —— 快捷键并入 WebUI 卡改版轮全量

> 摘要: 快捷键设置并入 WebUI 卡 + 双折叠改版轮全量
> 基线时间: 2026-11-04 01:12
**Refs:** memory-bank/tasks/26-11-04-webui-hub-keys-merge.md

## 验收数字

`commands run test.full` 实测输出誊写：

```text
TOTAL                                                23327    167   7956    152    99%
5014 passed, 2 skipped in 150.02s (0:02:30)
```

口径：仓库根全量；上一行为 test.full 的覆盖率 TOTAL 表原样誊写，下一行为 pytest 汇总行。同轮 e2e 冒烟(`commands run dev.e2e`)实测 424 passed / 18 skipped / 0 failed(不在基线数字族, 仅此处记结论)。

## 本改动面

- 前端(9 文件): `shared/tpl/settings-detail.html`(删独立 keys 分支; WebUI 卡加快捷键折叠块 + `aqb:kb-full-modal` 全屏覆盖层; 右键菜单布局默认折叠)、`shared/config_hub.js`(删首页 keys 卡/读数并入/`HUB_VIEW_ALIAS` 加 keys→webui/`kbDirtyView` 计算属性)、`shared/shortcuts_panel.js`(kbFullOpenPanel/kbFullClose/kbReadout/kbGuardLeave webui 口径/kbGoSettings 链 openSettings 之后)、`shared/lifecycle.js`、`shared/dialogs_meta.js`、`shared/shortcuts_engine.js`(三处名单同步 kbFullOpen)、`shared/config_editor.js`(cfgGuardActive 双脏源 + cfgReloadGuard 补存键位)、`shared/state.js`(kbFullOpen/ctxCust.open/双 watcher 传 true)、`shared/ctx_menu_custom.js`(cmPanelEnter 复位折叠)、`shared/console_hub_panels.css`(.hr-full-modal-acts)。
- 测试: `tests/test_web_shortcuts_drawer.py`(重写 test_settings_panel_section 为扫描锚口径 + 新增 test_kb_full_overlay_wiring)、`tests/test_webui_static_dom_page_layout.py`(watcher 双源断言)、`e2e/ctx-custom.spec.mjs`(适配默认折叠)。
