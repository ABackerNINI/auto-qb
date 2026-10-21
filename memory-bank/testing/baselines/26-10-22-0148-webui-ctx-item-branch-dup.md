# 3994 passed + 2 skipped + 1 failed —— 右键菜单 .ctx-item 骨架单点(四支合一)后全量基线

> 摘要: 右键菜单 .ctx-item 骨架单点(四支合一)后全量基线
> 基线时间: 2026-10-22 01:48

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **1 failed, 3994 passed, 2 skipped in 147.01s**
- 覆盖率: TOTAL **99.28%**(过闸)

逐条口径注记:

- 唯一 1 failed = `tests/test_web_longtail.py::test_api_traffic_qb_global_live_tail_realtime` —— **存量实时尾随 flake**(与上一基线那次 `test_traffic_snapshot.py` ts 粒度 flake 不同条, 两轮各红一条、位置漂移), 单跑 `test.one -- -k test_api_traffic_qb_global_live_tail_realtime` 通过(1 passed); 与右键菜单模板无涉(流量尾随链路), 按范围守恒未修, 建议另案入池
- 本轮改动面三件守阵在 test.full 内全绿: `test_webui_ctx_menu_registry.py` + `test_webui_trigger_registry.py`(12 passed)+ `test_webui_static_dom_panel.py`(52 passed)
- 本轮**未新增测试**(改写既有守阵的比对面), 故 passed 数变化来自开工同步带入的上游提交, 与本改动无关

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/ctx-menus.html` —— 行右键菜单四支各一份 `.ctx-item` 骨架(5 份)合并为一条 `ctxItems(ctxMenuKind())` v-for; 子面板改消费 `ctxSubItems(ctxMenuKind())`; 行菜单根块 101 → 68 行, 骨架 5 份 → 2 份
- `tests/test_webui_ctx_menu_registry.py` —— `test_ctx_menu_template_consumes_registry` 改为钉「无支名字面量 + 骨架恰 2 份 + 子面板结构 + 无逐项 @click」; 文件头测试计划同步
- `tests/test_webui_trigger_registry.py` —— `_ctx_menu_branches` 比对面从模板四支段搬到 `menu.js::ctxMenuKind()` 的四个 return 字面量(T3); 测试计划同步
- `tests/test_webui_static_dom_panel.py` —— 三处模板锚点改挂 `ctxItems(ctxMenuKind())`/行菜单根块(批量支/组级奇偶/子面板单入口); 测试计划两行同步
- `src/auto_qb/webui/static/shared/{ctx_menu,menu,triggers,decorate}.js` —— 注释回写(「模板判据链仍在 v-if」等表述已失真)
- `memory-bank/conventions/webui.md` + `memory-bank/pitfalls/web-ui/ctx-menu-branch-parity.md` —— 回写「渲染骨架也只有一条」与处置口径
- 未授权不做: commit/push

