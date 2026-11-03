# 抽屉桥方法参数语义错位: 调用点传 table id, 被调方按页签 key 解引用 (静默死链)

> 摘要: 抽屉变体桥方法族(`dtBridgeDef`/`dtBridgeTbl`/`dtBridgeSegs`/`dtRowAfter` 等)只认**页签 key**(`content` 等); 调用点若传 `dtBridgeTbl(tab)` 返回的 **table id**(`drawerContentV11` 等), 被调方 `_dtSel` 落到默认 `classic`、`REG.get` 无此表 ⇒ 描述符恒 null, 钩子虽在 `@vue:mounted` 照常触发却在首行 return —— 无报错、无日志, 行级键盘 roving/锚换代回焦静默失效。
> 触发: 改 shared/tpl/xtpl.html 桥表挂载钩子, 新增 dtBridge* 方法, 抽屉 content 变体 rowAfterFn 不生效, 锚换代后行级键盘焦点丢失

### 桥方法调用点传 table id, 被调方按页签 key 解引用 (2026-11-03 实证)

- **触发**: 改 `shared/tpl/xtpl.html` 的桥表挂载钩子, 或新增/改 `dtBridge*` 方法。2026-11-03 修 e2e 大表红灯时(issue 26-11-03-0802)桥表 `.group-table` 写的是 `dtRowAfter($root.dtBridgeTbl(tab), $event)` —— `dtBridgeTbl` 返回 table id, 而 `dtRowAfter`/`dtBridgeDef` 只按页签 key 解引用。
- **判别**: 同一调用点看参数来源: 页签 key 变量(`tab`, 组件 prop, `:tab="t.v"`) vs `dtBridgeTbl(tab)` 返回的 table id。node 探针打 `dtBridgeDef(tableId) === null` 且 `dtBridgeDef(tab)` 命中即实锤。**别只看"@vue:mounted 已挂"就判定钩子在跑** —— mounted 会触发, 死在被调方首行 return, 症状是纯静默。
- **处置**: 桥方法族统一收页签 key; 调用点改 `dtRowAfter(tab, $event)`。不要反过来让单个方法改吃 table id —— 会与同族 `dtBridgeDef`/`dtBridgeSegs`/`dtBridgeTbl` 的参数口径分叉。
- **守阵**: `tests/test_webui_static_dom_panel_drawer.py::test_drawer_tpl_row_after_hook_wiring`(静态钉调用点 + node 双参数对照: 传 tab 命中、传 table id 不命中)。
