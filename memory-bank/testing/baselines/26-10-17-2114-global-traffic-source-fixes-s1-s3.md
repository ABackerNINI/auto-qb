# 3550 passed + 4 skipped(根) —— 全局流量来源联动缺陷修复 Phase 1 S1–S3(traffic_source.enabled 总开关 / 取数闸门 / 工具侧 shutdown)

> 摘要: Phase 1 S1–S3 实施完成：顶层 traffic_source.enabled 总开关契约 + 取数闸门与 off 快照 + gtm POST /shutdown 与 auto-qb 代理
> 基线时间: 2026-10-17 21:14
**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md, memory-bank/plans/26-10-17-1737-plan-global-traffic-source-integration-fixes.html

## 验收数字

`commands run test.full` 实测(2026-10-17 21:14, 本机):

- 汇总行: **3550 passed, 4 skipped**(33.36s)
- TOTAL 覆盖率: 18030 statements / 264 missed / 6120 branches / 191 partial / **98%**(98.10%, 闸门要求 98%, 达标)
- gtm 工具侧另跑(在 tools/global-traffic-monitor 目录内跑其测试目录全量): 213 passed

## 本改动面

- 配置(S1): `config/models.py`(TrafficSourceConfig.enabled) · `config/schema.py`(traffic_source 叶字段) · `config/validation/sections.py`(关源免检 dat_path) · `config/validation/rules.py`(`_expr_gate` 关源放行) · `config/loaders.py`(读取) · `tests/fixtures/config_key_surface.txt`(v5 168→169 键) · `memory-bank/config-reference/keys.md`(总开关行回写)。
- 后端(S2): `core/traffic_source/paths.py`(source_enabled 恒等判据 + dat_path 关源返 "" + unavailable_reason 关源分支) · `webui/tool_client.py`(`_desired()` 首行闸 + `_pass` 传 enabled) · `core/traffic_source/agent.py`(`ensure_running(enabled=)` 拉起闸, status 不设闸) · `core/modules/speed_curve_mod.py`(off 快照优先于 disabled, handle + refresh) · `rules/expr/env.py`(`_traffic` 关源透报) · `webui/server/routes/traffic_monitor.py`(notify disabled 扩到关源 + 新增 shutdown 代理)。
- 前端(S2): `static/shared/state.js`(historyState) · `static/shared/dialogs.js`(trafficOn 排除 off + loadHistory 捕获) · `static/shared/config_hub.js`(tmSourceOff/tmEnabledItems) · `static/shared/tpl/settings.html`(总开关 hub-field + D14 灰显) · `static/shared/console_hub.css`(`.hb-grey`) · `static/shared/tpl/popovers.html`(off 态专属文案)。
- 工具(S3): `tools/global-traffic-monitor/src/gtm/server.py`(stop_event + POST /shutdown 先回 200 再置位) · `src/gtm/__main__.py`(cmd_run 接线) 。
- 测试: S1 `test_config.py::test_validate_traffic_source_enabled_key` + 键面探针; S2 paths/tool_client/agent/speed_curve/expr/notify 六文件各新增关源用例; S3 gtm `test_server.py`(401/200/置位/即时醒) + auto-qb `test_web_traffic_monitor.py`(鉴权/透传/502) + 路由金清单补条目; 修正 `test_config_traffic_monitor.py` 已知键黄金集合(3→4 键, 纳入 enabled)。

## 守阵与坑

- 恒等判据 `is not False`: MagicMock 配置段不触发关闭(`test_mock_config_section_starts_no_thread` 同族, 未踩到)。
- 两处计划未明说的必需放宽: 关源免检 `traffic_monitor.dat_path` 必填(否则没配好数据源时无法从设置页关掉)、`_expr_gate` 关源不禁流量名字(否则保存必败 UI 无从自救)。
- settings.html 单分片 400 行上限: 新增总开关行后触顶, 注释块 6→3 行 + 提示 span 并入按钮行压回 400(`test_frontend_template_split_wiring`)。
- speed_curve 恢复轮用手动限速保护注意: 夹具 upload_limit 需偶数 KiB(`888*1024`), 奇数触发 `is_manual_speed_limit` 跳过。
