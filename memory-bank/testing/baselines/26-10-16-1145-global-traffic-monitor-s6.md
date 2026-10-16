# 3446 passed + 4 skipped —— 全局流量监视小工具 S6 auto-qb 配置面(工具 +7 条; 根集新增 27 条守阵)

> 摘要: 用户「实施计划S6:26-10-16-0541-plan-global-traffic-monitor.html」(对 S6 的显式授权, S7–S10 不动)。首个触碰 auto-qb 的步骤。**计划改版(用户拍板)**: S6 原文「自启开关幂等调 gtm install-autostart」未定调用路径(auto-qb 与工具是两个 venv), 用户取 B 案 —— 工具控制面新增 `POST /autostart`, auto-qb 经 HTTP 代理调用。改动面: ①配置段 4 点同步(models/loaders/validation/schema)新增 `global_traffic_monitor`(enabled/tool_url/tool_token_path/subscribe/notify_cooldown_s/autostart); ②工具 `POST /autostart`(进程内跑 installer, 200/501/500/400); ③auto-qb 代理路由 `routes/traffic_monitor.py`(status/config/autostart 三端点); ④设置页新分区(schema 分组 + settings.html 链尾 v-else-if 分支: 联动键 + 工具状态/参数读写/自启开关)。本切片为根 test.full 回归闸门数字。
> 基线时间: 2026-10-16 11:45

- test.full: 3446 passed + 4 skipped / TOTAL 17543 214 5906 164 98%(98.35%); 耗时 145.74s(单次采样, 任务墙钟 148.4s)。
- 根集 passed/skipped 较 S5 切片(3418+4)增 28 —— 本轮新增守阵 `tests/test_config_traffic_monitor.py`(12 条)+ `tests/test_web_traffic_monitor.py`(15 条, 含 1 条 parametrize 计 2)共 27 条; 余 1 条来自开工同步并入的其它会话。
- 工具侧自测(独立 venv, 不计入根 TOTAL): `uv run pytest -q` **173 passed**(S5 的 166 + 7 条 `POST /autostart`), 34.90s。
- 红验(临时脚本 `H:/Temp/gtm-s6-redverify.py`: bytes 层锚点、count==1 兜底、还原后字节恒等、突变前先跑无变异基线、解释器钉死 auto-qb/工具 venv 绝对路径、子进程 240s 超时且接住 `TimeoutExpired`、apply 后 `ast.parse` 自检、收尾先还原再复跑基线、**单文件跑加 `--no-cov -n 0` 绕覆盖率闸**): **7 条锚点突变全判 RED** —— 键集合漂移(`"tool_url"` -> `"tool_url_x"`, schema 对象段键集合 1 红) / 段校验未接线(注释掉 `_validate_global_traffic_monitor` 调用, 未知键用例 1 红) / loader 漏读(`notify_cooldown_s` 不走 parse_time, 1 红) / schema 字段键名漂移(`"tool_url"` -> `"tool_urlY"`, 1 红) / status 缺 token 不报错(`token = _read_token(token_path)` -> `token = "x"`, 1 红) / PUT 代理路径漂移(`"/config"` -> `"/configX"`, 1 红) / 工具 action 闸失效(`if action not in (...)` -> `if False:`, 1 红); 全部字节恒等还原后基线复绿。

## 出口判据逐条(计划 §04 S6)

- **新配置键过 validate_config 守卫(缺校验/缺 schema 即红)**: `test_config_schema` 的 `test_top_level_keys_match_validation`(顶层键集合 == KNOWN_CONFIG_KEYS)+ `test_object_section_keys_match_validation[global_traffic_monitor]`(对象段子键 == KNOWN_GLOBAL_TRAFFIC_MONITOR_KEYS)全绿; `test_config_key_surface` 键面基线 160 -> **167** 键(7 条新增: 段本身 + 6 叶键)+ `test_loader_probe_table_covers_named_leaf_surface`(6 条新键全配回读探针)+ `test_keys_md_covers_key_surface`(keys.md 有出处)。
- **设置页读写工具参数真机可见**: 本轮以代理路由守阵钉住契约(status 恒 200 结构化空态 / config 全量转发 + 工具 400 逐条透传 / autostart 501 透传 / 缺 token 502); 前端分区渲染由静态守阵(shell/分片体量、聚合标签配平、DOM 页)+ 既有真机冒烟框架覆盖, 与 S7 接收面联调时复核端到端可见性。
- **未知键仍被拒**: `test_config_traffic_monitor::test_validate_unknown_key_rejected`(段内未知键聚合报错)。
- **红验两类突变判红后还原复绿**: 见上(7 条)。

## 本改动面

- `src/auto_qb/config/models.py`(`GlobalTrafficMonitorConfig` + `Config.global_traffic_monitor`)
- `src/auto_qb/config/loaders.py`(`load_global_traffic_monitor_config` + 接线)
- `src/auto_qb/config/validation/{core,sections,__init__}.py`(KNOWN_CONFIG_KEYS + KNOWN_GLOBAL_TRAFFIC_MONITOR_KEYS + `_validate_global_traffic_monitor` / `_validate_tool_url` + 导出)
- `src/auto_qb/config/schema/groups.py`(新分组「全局流量监视器」, i-traffic)
- `src/auto_qb/webui/server/routes/traffic_monitor.py` **新文件**(status/config/autostart 代理)+ `routes/__init__.py`(注册)
- `src/auto_qb/webui/module.py`(WebUIModule.sections 加 `global_traffic_monitor` 认领)
- `src/auto_qb/webui/static/shared/tpl/settings.html`(链尾 v-else-if 分支)+ `config_hub.js`(tm* 方法 + 分区元信息 + hubGo 懒加载)+ `state.js`(tm 根数据)+ `triggers.js`(calls 登记 tmAutostart)
- `tools/global-traffic-monitor/src/gtm/server.py`(`POST /autostart` + 注入式 `installer_factory`)+ `README.md`(端点表)
- `tests/test_config_traffic_monitor.py` / `tests/test_web_traffic_monitor.py` 新文件; `tests/test_config_schema.py` / `test_config_key_surface.py` / `test_web_route_manifest.py` / `test_web_backend_misc.py` / `tests/fixtures/config_key_surface.txt` / `tools/global-traffic-monitor/tests/test_server.py` 同步
- 文档: `memory-bank/config-reference/keys.md`(新段)+ 计划 HTML(§04 R0 增 S6 行 + 改版记录)
- 坑档: `memory-bank/pitfalls/testing/single-file-coverage-gate.md` 复发+1(红验 harness 裸跑单文件被覆盖率闸假红)+ `pitfalls/web-ui/frontend-split.md` 新增(设置页 v-if 链跨分片 + settings.html 近 400 行上限)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html
