# 26-09-28-webui-settings-categorize-logs — 设置页分类回归修复: 「常规/日志」成块 + 运行日志默认折叠

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 26-09-26 分组合并(1905d6d)的回归修复 —— log/web/notify 三段去 open=True 恢复成块(「常规/日志/WebUI/通知」各自显标题, 不折叠保持平铺诉求), label 恢复 日志/WebUI/通知 + 补回旧分组 help; 运行日志块默认折叠、首次展开才拉 /api/log; hubHits/hubFieldCount 递归适配; test_config_schema_endpoint 钉"尾三段不声明 open"; 三套 UI 经 shared 层一处生效。全量 1815 passed + 3 skipped, TOTAL 91.39%。

## 原始请求

> WEBUI将多项移入"常规"的更改丢失了分类, 比如之前的"日志"也并入了"常规/常规"中,应该是"常规/日志"中.运行日志需要默认折叠, 之前的提交"1905d6df…"

用户随后纠正「目前共有3套UI, 2套UI是旧口径, 同时修改第3套UI」与「提交」。

## 思考过程与决策

- **根因**: 合并把三段标成 `open=True`, 而 `cfgFlatten` 对 open 段的处理是**不渲染标题头、子字段平铺成同级普通字段**(config_editor.js) —— 三段字段全部落进 hubBlocks 的合成根块「常规」, 成了「常规/常规」。
- **成块 ≠ 折叠**: 直接去 `open=True` 后三段经 hubBlocks walk 变成带标题的块且**永远展开** —— 分类名显性化(用户要求)与 2026-09-15「短段平铺不折叠」诉求(不点开就能看全字段)同时满足, 无需前端 hack。
- **label 恢复合并前分组名**(日志/WebUI/通知)并补回旧分组一行 help(落盘轮转与格式 / 图形界面的监听与鉴权 / WARNING 及以上日志推送平台原生通知), 分类语义与合并前一致。
- **运行日志懒加载**: 默认折叠后"打开分区就拉一次"的预取失去意义 —— 首次展开才拉(hubLogsToggle), 折叠态动等级/行数/刷新 = 明确想看, 自动展开再拉(hubLogsLoad)。
- **派生逻辑适配**: 三段成块后其字段不再是 cfgFlatten 顶层项, hubHits(搜索直跳)与 hubFieldCount(首页「共 M 项」)改递归进块; hubCollectRisk 本就递归不动。
- **三套 UI 无需成对改**: atlas/prism/console 的设置页同吃 `shared/tpl/settings-detail.html` + `shared/config_hub.js`, console 是纯 CSS 换肤; shell tpl-manifest 一致性守阵(`_UI_ALL`)钉住三套不漂移 —— 本线只改共享层。
- **`open` 字段保留**: 现 schema 仅 hr_check(optional)段在用, cfgFlatten 的平铺分支作为通用能力保留, 注释改写防误用。

## 实现计划

1. `config/schema/groups.py`: log/web/notify 三段去 `open=True`, label 改 日志/WebUI/通知, 补回旧分组一行 help, 注释写明成块口径。
2. `config_hub.js`: 新增 `hubLogsToggle`/`hubLogsLoad`; hubGo 去掉 basic 预取; hubHits/hubFieldCount 改递归进块; hubRestore 注释同步。
3. `shared/tpl/settings-detail.html`: 运行日志块头加「展开/收起」按钮, 正文 `v-show="logs.open"`, 等级/行数/刷新换 `hubLogsLoad`。
4. `state.js`/`auth.js`: logs 状态加 `open: false`(重置路径同步)。
5. `config_editor.js`: cfgFlatten 平铺分支与 cfgGroupOpen 的过时举例注释改写。
6. 守阵: `test_config_schema_endpoint` 加断言尾三段 kind=object 且无 open; `fields.py` open 字段注释更新。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | groups.py: 三段去 open=True + label/help 恢复 | ✅ |
| 2 | config_hub.js: hubLogsToggle/hubLogsLoad + hubGo 去预取 + hubHits/hubFieldCount 递归 | ✅ |
| 3 | settings-detail.html: 运行日志块折叠 + 控件换 hubLogsLoad | ✅ |
| 4 | state.js/auth.js: logs.open 标志 | ✅ |
| 5 | 守阵: test_config_schema_endpoint 钉尾三段无 open + 过时注释清理 | ✅ |
| 6 | 收尾回写 + 提交推送 | ✅ |

## 进度日志

- **2026-09-28 01:3x–02:1x**: 同步齐平(635693f); 定位根因在 cfgFlatten open 平铺; 7 文件修复, test_web.py 177 passed; test.quick 1815 passed / 3 skipped。用户纠正三套 UI 口径 → 核实 console 经 manifest 守阵与共享层自动覆盖, 另补防回归守阵(fields.py 注释 + schema 端点断言)。
- **2026-09-28 02:1x**: 收尾回写(档案/切片/基线 26-09-28-0212/progress 条目), test.full 实测 1815 passed + 3 skipped, TOTAL 91.39%(12504/914/4204/388, 18.66s)。
