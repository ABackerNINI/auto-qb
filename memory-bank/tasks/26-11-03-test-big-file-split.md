# 26-11-03-test-big-file-split — 大文件多轮拆分 R1: 10 个测试文件 move-only 拆分

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 按计划完成 R1(10 个测试文件 → 36 个测试文件 + 12 个支撑/扫描模块)、R2(25 个测试文件 → 90 个分桶 + 20 个 support)、R3(4 个工具/脚本/扩展文件 → 9 个分片, 3 个暂缓零改动)、R4(8 个前端文件 → 20 个域名片段 + 4 段 CSS, 2 暂缓/2 不拆零改动)与 R5(9 个后端大文件 → 34 个新子模块, 2 暂缓零改动, patch 敏感名留根/MRO 与公开面不变); 测试函数名与模块级界定逐字不变; 全量见 kb.baseline; 计划 R1-R5 已全部收束(计划状态 Done), 2 个超千行新桶按口径登记后续排期, 剩余待办: 新桶 `tests/test_utils_windows.py` 1080 / `tests/test_web_commands_dispatch.py` 1058、`73>70` 容量债务、22 暂缓与 2 不拆文件的再启动触发条件。
**Topics:** test-big-file-split
**Refs:** memory-bank/plans/26-11-02-2342-plan-big-file-split.html, memory-bank/testing/baselines/26-11-03-0048-test-big-file-split.md, memory-bank/testing/baselines/26-11-03-0157-test-big-file-split.md, memory-bank/testing/baselines/26-11-03-0326-test-big-file-split.md, memory-bank/testing/baselines/26-11-03-0459-test-big-file-split.md, memory-bank/testing/baselines/26-11-03-0819-test-big-file-split.md

## 原始请求

1. 先按计划把「>1000 行大文件」扫描结果产出多轮拆分实施计划(已完成, 落盘 `memory-bank/plans/26-11-02-2342-plan-big-file-split.html`)。
2. 按计划实施第一轮(R1): 10 个测试文件, **严格 move-only** —— 只搬测试代码/用例, 不改断言、不改行为、不顺手重构; 无法 move-only 安全拆分的文件停手报告。
3. 保持测试可发现性与既有导入关系; 共享 fixture/辅助按计划指定归属; 核对 `tests/_tmp_bootstrap.py` 头部「## 测试计划」同步要求(无新增用例则不改)。
4. 每个文件拆完跑该文件定向测试(走包内 task id), 最后跑一次全量, 与最新基线对比; 本轮实现不 commit / 不 push, 改动留给用户审阅。
5. (本轮) 用户说「提交」—— 授权把 R1 改动 commit + push; 要求先同步、复核工作区只有 R1 的 `tests/` 改动(58 项)、`tests/helpers.py` / `tests/_tmp_bootstrap.py` / `src/` 零改动; 按收尾 DoD 回写文档 + 新建基线切片; 不动计划里暂缓/不拆的文件, 不新增子桶拆分。

## 思考过程与决策

- **move-only 的判据取「AST 层逐字比对」而非人工目测**: 以 HEAD 中 10 个原文件为基准, 抽出全部模块级 `FunctionDef`/`AsyncFunctionDef`/`ClassDef`/`Assign`/`AnnAssign` 源码片段逐字节比对; 测试函数名集合双向一致 —— 这两项是「搬」与「改」的分界。
- **分桶由依赖闭包决定**: 用 `ast.Name`(Load) 求每个测试函数的依赖闭包; 被恰好一个桶使用的辅助归入该桶内联, 多桶共用的提升为支撑模块(`*_support.py` / `webui_static_scan_{common,css,js}.py`)。支撑模块**不以 `test_` 开头**(pytest 只收 `test_*.py`), 避免被当成用例文件收集。
- **导入语义靠「全量复制 + 显式补 import」**: 每个生成文件都复制原文件的全部 import 语句, 再补 `from <support> import ...`; 支撑模块之间按无环分层(css → common; js → common + css; 常量集中在 common)。
- **文件头「## 测试计划」清单按桶切分, 不重写文案**: 按原顺序保留非条目行; 条目仅当归档的测试名属于当前桶时保留; 跨桶共用条目在其余桶写派生行 `原条目见 <归属文件>(跨分文件共用同一用例条目, 文案未改)`, 保留锚点原文 —— 守阵 `test_test_plan_docstring_guard.py` 绿。
- **不新增子桶**: R1 只管「把大文件拆到能拆的粒度」; 仍超千行的 12 个桶**不在本轮继续下拆**, 留给 R2 在计划里补分桶修订(保持轮次边界清晰、改动可审)。
- **文件仍留在 `tests/` 下**: 基于 `__file__` 推导仓库根/`ROOT` 常量的用例不因目录深度变化而失效, 也不需要改任何路径。

## 实现计划

1. 取 HEAD 中的 10 个原测试文件作为基准, 跑 AST 分桶分析并产出 SPECS(目标文件名 + 桶归属 + 支撑模块归属)。
2. 生成 36 个测试文件 + 12 个支撑/扫描模块, 逐文件校验: 模块级界定逐字不变、测试函数名集合一致、无跨文件残留引用。
3. 修正「## 测试计划」清单切分逻辑, 使 `test_test_plan_docstring_guard.py` 全绿。
4. 每个新文件跑定向测试; 再跑 `commands run test.quick` 与 `commands run test.full`。
5. 收尾: 立档、`kb.wrap`、回写 `memory-bank/testing/file-conventions.md`、新建基线切片、提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | `test_webui_static_dom_panel.py` → drawer / dialogs / traffic / misc + support | Done (2026-11-03) |
| S2 | `test_hr_service.py` → wave / misc / rows / store + support | Done (2026-11-03) |
| S3 | `test_traffic_sample.py` → store / core / config / misc + support | Done (2026-11-03) |
| S4 | `test_webui_static_skins.py` → table / skin / widget + scan_{common,css,js} | Done (2026-11-03) |
| S5 | `test_memory_bank.py` → cli / docs / structure / naming + support | Done (2026-11-03) |
| S6 | `test_relocate_exec.py` → run / reconcile / jobs / misc + support | Done (2026-11-03) |
| S7 | `test_config.py` → misc / load / rules + write support | Done (2026-11-03) |
| S8 | `test_grouping.py` → state / misc / scan / conflict + support | Done (2026-11-03) |
| S9 | `test_webui_static_dom_page.py` → layout / hr / store + support | Done (2026-11-03) |
| S10 | `test_extension_proxy.py` → page_fetch / options / manifest + support | Done (2026-11-03) |
| S11 | 定向测试 + 全量闸门 + 基线切片 | Done (2026-11-03) |
| S12 | 收尾回写 + 提交推送 | Done (2026-11-03) |
| R2-1 | 25 个测试文件 move-only 拆分 → 90 个分桶 + 20 个 support(逐文件用例数守恒, 合计 1524) | Done (2026-11-03) |
| R2-2 | 新桶超阈值口径落计划 + 排期清单(test_utils_windows 1075 / test_web_commands_dispatch 1058) | Done (2026-11-03) |
| R2-3 | 同步并入远端 `test_kb_nav.py` 新用例(search 缝归 `_interaction`) + 全量闸门 + 基线切片 | Done (2026-11-03) |
| R2-4 | 收尾回写 + 提交推送 | Done (2026-11-03) |
| R3-1 | `sim_qb.py` / `qb_capture.py` / `background.js` / `test_server.py` move-only 拆分(4 拆 3 暂缓) | Done (2026-11-03) |
| R3-2 | 扩展守阵加载顺序适配 + 定向闸门 + 全量闸门 + 基线切片 | Done (2026-11-03) |
| R3-3 | 收尾回写 + 提交推送 | Done (2026-11-03) |
| R4-1 | 8 个前端文件 move-only 拆分(`console_hub.css` 4 段 + `drawer`/`config_hub`/`config_editor`/`shortcuts`/`columns`/`commands`/`dialogs` 共 20 片段; 2 暂缓/2 不拆零改动) | Done (2026-11-03) |
| R4-2 | 四套皮肤清单加载序同步 + 守阵「域聚合读」引用适配 + 定向/全量闸门 | Done (2026-11-03) |
| R4-3 | 收尾回写(计划 §07/§10、本档案、基线切片) + 提交推送 | Done (2026-11-03) |
| R5-1 | 9 个后端单类/大 Mixin move-only 拆分(`utils`/`traffic_store`/`traffic_sample_mod`/`relocate_mod`/`ops_mod`/`hr.service`/`views`/`runtime`/`commands`; 2 暂缓零改动) | Done (2026-11-03) |
| R5-2 | patch 敏感 globals 留根 + 组合类 MRO 保持 + 公开面 re-export + 6 个守阵测试引用最小同步 | Done (2026-11-03) |
| R5-3 | 计划 §07/§10 回写 + 定向/全量闸门(未提交, 按本轮要求留审阅) | Done (2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

- 本轮选择 AST 层「模块级界定逐字比对 + 测试函数名双向一致」作为 move-only 证据: 搬而不改有机器判据, 不靠人工目测。
- 12 个仍超千行的桶(dom_panel_drawer / traffic_store / dom_panel_dialogs / traffic_core / config_misc / memory_cli / hr_misc / skins_table / dom_panel_traffic / hr_wave / dom_page_layout / memory_docs)留 R2 补分桶修订, 本轮不下拆。

- 2026-11-03 00:42 按计划完成 R1: 10 个大型测试文件 move-only 拆为 36 个测试文件 + 12 个支撑/扫描模块; 906 个测试函数名与 1170 个模块级界定逐字不变; 全量见 kb.baseline; 12 个仍超千行的桶留 R2

- 2026-11-03 01:58 R2 完成: 25 个测试文件 move-only 拆为 90 桶 + 20 support(用例数守恒), 同步并入远端 test_kb_nav 新用例, 新口径与排期清单入计划, 全量见 kb.baseline

- 2026-11-03 03:27 R3 完成: 4 个工具/脚本/扩展文件 move-only 拆分(sim_qb 2077->166 入口+4 模块; qb_capture 1559->959+2 模块; background.js 1427->642+2 分片; test_server.py 1274->552+1 support+2 分文件), 3 个暂缓零改动; 扩展守阵按 importScripts 顺序拼接 bundle; 全量见 kb.baseline

- 2026-11-03 R4 完成(未提交): 8 个前端文件 move-only 拆分 —— console_hub.css 1589->291 根+3 连续段(前 3 段沿用层叠序); drawer.js 1543->916+3 片段, config_hub.js 1484->617+3, config_editor.js 1475->736+3, shortcuts.js 1442->428+2, columns.js 1429->124+5(computed 片段最后加载), commands.js 1076->431+2(_runningToast 工厂留根), dialogs.js 1022->720+2; 片段一律 `Object.assign(window.AQB_*.methods, ...)` 原地扩充、加载序紧跟根文件; 四套皮肤 index.html 清单与 CSS link 同步; 守阵改「域聚合读」(tests/webui_helpers.py SHARED_SPLIT_PARTS/read_shared/bundle_file), 断言语义未改; 暂缓 drawer_templates/qb_traffic_chart 与不拆 fx/showcase.html/app.js 零改动; 新桶最大 804 行, 排期清单无新增

- 2026-11-03 04:59 R4 完成: 8 个前端文件 move-only 拆为 20 个域名片段 + 4 段连续 CSS(2 暂缓/2 不拆零改动), 四皮肤清单与守阵域聚合读同步; 新桶均 <=1000(最大 804), 排期无新增

- 2026-11-03 R5 完成(未提交): 9 个后端单类/大 Mixin move-only 拆分 —— utils 1435->879 根+2(utils_parse/utils_paths), traffic_store 1616->615 根+4, traffic_sample_mod 1622->650 根+3, relocate_mod 1586->131 根+4, ops_mod 1270->374 根+3, hr/service 1829->411 根+2(service_wave 945 最大桶), views 1163->432 根+4, runtime 1701->247 根+3, commands 1590->240 根+4; 拆分后类改为 Mixin 组合且 MRO 顺序与原方法解析一致, 根全量 re-export 公开面; patch 敏感 globals(`_bound_user32`/`_bound_kernel32`/`urlparse`/`atomic_write`+`resolve_or_create_token`/`parse_v4_*`/`TrafficSampleModule.*`/`OpsModule._backup_torrent`/`runtime.time`/`commands.TransferOrchestrator`/`build_adapter`/`build_site_view`/三个 budget 常量)全部留根; 6 个静态守阵测试只改引用指向(断言语义未变); 新桶均 <=1000, 排期无新增; 2 个暂缓(`config/validation/sections.py` 1044 / `core/qbmanager.py` 1008)零改动; test.full 全绿, 数字见 kb.baseline; 收集数增量来源为开工同步并入的上游提交新增用例, R5 本身未增删测试

- 2026-11-03 08:20 R5 完成并收束计划: 9 个后端大文件 move-only 拆分(34 个新模块, 2 暂缓零改动), patch 敏感名留根/MRO 与公开面不变, 新桶最大 945; 全量见 kb.baseline; 计划 R1-R5 全部完成, 状态 Done
