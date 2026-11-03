# 5050 passed, 10 skipped in 201.32s (0:03:21); TOTAL 23370 stmts / 185 miss / 7980 branch / 159 partial / 99% —— flux/atlas/console .ce-page 窄屏死规则并入 dialogs.css 媒体覆盖全量测试基线

> 摘要: flux/atlas/console .ce-page 窄屏死规则并入 dialogs.css 媒体覆盖全量测试基线
> 基线时间: 2026-11-04 02:45
**Refs:**

## 验收数字

- 汇总行: `5050 passed, 10 skipped in 201.32s (0:03:21)`
- 覆盖率 TOTAL: `23370 stmts / 185 miss / 7980 branch / 159 partial / 99%`
- 口径: `commands run test.full` 本机 Windows 实测(CSS 改动 + RM10/RM08 基线件两处 `[数组](中文)` 坏链误报修复后的一次全量); Linux (WSL) 侧未重测
- 备注: 修复前一轮全量 5049 passed / 1 failed,唯一红即上述坏链误报(`tests/test_memory_bank_docs.py::test_doc_links_are_not_broken`),与本轮 CSS 改动无关;修后复跑全绿

## 本改动面

- `src/auto_qb/webui/static/{flux,atlas,console}/css/views.css`: 各自从 `@media(max-width:900px)` 块移除死规则 `.ce-page { padding: 12px 12px 24px; }`(被后加载 dialogs.css 同特异性规则恒覆盖),留指路注释
- `src/auto_qb/webui/static/{flux,atlas,console}/css/dialogs.css`: 基础 `.ce-page` 规则后新增同条件媒体覆盖 `@media(max-width:900px) { .ce-page { padding: 12px 12px 24px; } }`,同文件内序保证生效,不再赌跨文件加载序(issue 26-11-03-1120)
- prism 不动: 两条规则同在 prism/css/views.css(无条件 :522 → 媒体 :680),同文件内后置胜出,本就生效
- 计划外(用户当场授权): `memory-bank/testing/real-baselines/26-11-04-0126-real-RM10-*.md` 与 `26-11-04-0156-real-RM08-*.md` 各一处 `[数组](中文)` 相邻写法改全角括号,消除文档链接检查误报
- 无产品代码/测试代码改动;定向静态扫描测试 skins_skin/dom_panel_dialogs/dom_page_layout 58 passed、skins_table/skins_widget/dom_page_hr/dom_panel_misc 30 passed
