# 3550 passed + 2 failed + 4 skipped(根) —— 全局流量来源联动缺陷修复 Phase 1 S4–S5(「关闭工具」/ 去黑框)

> 摘要: Phase 1 S4–S5 实施完成：「关闭工具」按钮 + 确认框(清单取自 schema affects) + 先停订阅再停进程；去黑框(CREATE_NO_WINDOW + 启动器优先 pythonw)
> 基线时间: 2026-10-18 06:15
**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md, memory-bank/plans/26-10-17-1737-plan-global-traffic-source-integration-fixes.html, memory-bank/issues/26-10-18-0608-test-memory-bank-test-hardcoded-today.html

## 验收数字

`commands run test.full` 实测(2026-10-18 06:15, 本机 Windows 单侧):

- 汇总行: **2 failed, 3550 passed, 4 skipped**(35.09s)
- TOTAL 覆盖率: 18030 statements / 264 missed / 6120 branches / 191 partial / **98%**(98.10%, 闸门要求 98%, 达标)
- gtm 工具侧另跑(在 `tools/global-traffic-monitor` 目录内用其 `.venv` 跑全量): **213 passed**(33.47s)

## 已知红(非本轮引入)

两例失败均为 `tests/test_memory_bank.py` 把运行当天日期写死进断言(`**Updated:** 2026-10-17` / `最后更新` 类),
换日必红、与业务无关 —— 已入池 `issues/26-10-18-0608-test-memory-bank-test-hardcoded-today.html`(Open, 未修):

- `test_flip_status_flips_bumps_and_fails_fast`
- `test_bump_doc_appends_changelog_and_fails_fast`

## 本改动面

- 前端(S4): `static/shared/state.js`(`tm.shutting/shutdownMsg/shutdownErr`) · `static/shared/config_hub.js`(`TM_AFFECT_LABELS` + `tmAffectLabels()` + `tmShutdownTool()` + `tmPollShutdown()`) · `static/shared/tpl/settings.html`(按钮可见三条件 + 反馈 span 并入按钮行) · `static/shared/triggers.js`(`tmShutdownTool` 的 POST 补登 `calls`，守阵 T1 抓到)。
- 后端(S5): `core/traffic_source/agent.py`(`launch_tool` 的 `creationflags` 由 `DETACHED_PROCESS` 换 `CREATE_NO_WINDOW`，docstring/注释写明理由与「别换回去」)。
- 工具(S5): `tools/global-traffic-monitor/launch.cmd`(`pythonw.exe` → `python.exe` → `uv` 三级回退)。
- 文档: `docs/configuration.md`(YAML 样例补 `enabled`；「启用」与「关闭工具」的分野；确认框清单来源)。
- 测试: `test_web_traffic_monitor.py::test_frontend_shutdown_tool_wiring`(按钮三条件 / 方法在册 / 保存先于停工具的相对次序 / 失败回滚 / 不谎报 / 清覆盖 schema `affects` 全部 id) · `test_traffic_source_agent.py::test_launcher_prefers_pythonw`(三级回退次序 + 两类回退跑同一条命令) + `test_launch_tool_builds_platform_command` 断言换 `CREATE_NO_WINDOW` 并加「不等于 DETACHED_PROCESS」回归哨。

## 守阵与坑

- **次序即正确性**: 「关闭工具」必须先落盘 `enabled=false`(热重载停订阅) 再 `POST /shutdown`；反序会让停工具的瞬间被订阅线程抢拉。守阵用「源文本里 `cfgSave()` 先于 `/shutdown`」的相对位置钉住, 不靠人工 review。
- **两处反悔护栏**: 保存失败 → 内存开关回滚成 `true`(否则下次普通保存把「关闭」静默写进盘)；停工具失败 → 明说「来源已关闭并保存」+ 原因(不谎报成功)。
- **POST 必登记**: 新增前端 POST 调用点必须同步 `triggers.js` 的 `calls`(scope/why), 否则 `test_webui_trigger_registry` 判红 —— 本轮确实漏了一次, 被全量回归逮住。
- **pythonw 的代价**: `sys.stderr` 为 `None`, 输出全丢；与被拉起时本就 `DEVNULL` 的行为一致, 不算回归。排障时把启动器里的 `pythonw` 临时换回 `python.exe`。
- **settings.html 单分片 400 行上限**: 新增按钮行后触顶, 注释块压到 2 行回 400 以内(`test_frontend_template_split_wiring`)。
- **未入池的范围外观察**: gtm 自启注册用 `sys.executable`(`python.exe`), 开机登录理论上仍会闪一次窗；本轮 S5 范围只到「立即拉起 + 启动器」, 未动 installer。
