# 3578 passed + 4 skipped / 0 红 —— 流量快照解耦 Phase 2 P2-A(A1–A5 后端) 收口

> 摘要: 流量快照所有权移交 traffic_snapshot 模块(A1–A5 后端批次) 收口
> 基线时间: 2026-10-18 10:19
**Refs:** memory-bank/tasks/26-10-18-backend-traffic-snapshot-merge.md, memory-bank/plans/26-10-18-0813-plan-global-traffic-source-phase2.html

## 验收数字

`commands run test.full` 实测(2026-10-18 10:19, 本机):

- 汇总行: **3578 passed, 4 skipped, 0 failed**(34.59s)
- TOTAL 覆盖率: 18146 statements / 266 missed / 6146 branches / 193 partial / **98%**(98.06%, 闸门 98%, 达标)
- 无既存红: 上一条基线记的 `test_docs_forms::test_doc_map_live_rotation` 已由 26-10-18-0901 的专题键拆分修掉。
- 相关面单跑(逐文件, `-n 0 --no-cov`): `test_traffic_snapshot.py`(14) + `test_traffic_monitor_client.py`(23) +
  `test_speed_curve.py`(45) + `test_modules_p3.py` / `test_traffic_monitor_dat.py`(66 合计) +
  `test_config_traffic_monitor.py` / `test_config_key_surface.py`(26) + `test_module_host.py` / `test_web_views_reload.py`(47)。

## 本改动面

后端(新增):
- `src/auto_qb/core/modules/traffic_snapshot_mod.py`: 新模块 —— `sections()` 只认领 `traffic_source`(解耦判据)、
  `derive_state(source, limit)` 单点派生、`publish_source` / `publish_limit` / `publish_off` 段级 API(唯一改动
  `traffic_view` 的入口, 每次「读旧快照 -> 只改自有键 -> 一次 `set_traffic_view`」)、`refresh()` 单一执行路径、
  自注册任务 `traffic_snapshot_refresh`(无曲线配置门槛)、`apply()` 就地改 interval + `queue_rebuilt` 相位兜底。
- `src/auto_qb/core/traffic_source/reader.py`: 读档共享单点 `read_source_rows(dat_path)` -> `(rows, bad, fail)`,
  `fail` 带 `dat_missing` / `dat_empty` 码 —— 两模块判据同源(计划原写「留在曲线模块内」, 实施改为共享层, 见计划 §10 R1 ①)。

后端(改造):
- `speed_curve_mod.py`: 降为只写 `limit` 段 —— 删 `_history_rows` / `_period_rows` / `_read_source_rows` / `refresh_traffic_view`;
  `start()` 首行 `_require_snapshot()`(装配序缺失即 fail-fast); 来源关闭时 handler **不发布任何东西**, 直接 REQUEUE。
- `taskqueue.py`: 新增 `named(name)`(internal + 无 hash)供 `apply()` 取任务引用就地改 `interval`。
- `webui/runtime.py`: 初始快照改新契约形状; 新增 `public_traffic_view(view)`(摘 `history`)。
- `webui/server/routes/state.py`: `_status_payload` 的 `traffic` 走 `public_traffic_view`; `/api/traffic/history` 为 history 唯一出口。
- `webui/commands.py`: `_cmd_refresh_traffic` 改调 `host.get("traffic_snapshot").refresh()`。
- 配置四层: `models.TrafficSourceConfig.refresh_interval`(默认 600.0) / `schema/groups.py` `Field("refresh_interval", "time", "10M")` /
  `validation/sections.py`(已知键 + `_try_time` 10S–1H) / `loaders.py`(`parse_time`)。
- 前端文案(非 B 批): `config_hub.js` `tmSourceRows()`(enabled + refresh_interval 两行)、`tpl/settings.html`、
  `config_editor.js` 曲线 interval help(「只管写限速」)。
- 文档: `memory-bank/config-reference/keys.md`、`docs/configuration.md` 三处 YAML 示例 + 「两个节奏别混」条目。
- 键面基线: `tests/fixtures/config_key_surface.txt` v5, 169 -> 170 键(`test.keys-update` 重生成)。

守阵:
- 新增 `tests/test_traffic_snapshot.py`(14 条): 段认领 / 装配序 / 无曲线配置照发历史 / `derive_state` 表 / state 恒派生 /
  两向段隔离 / off 清双段 / stale 原因码 / 关源不读盘 / 曲线跑完不动来源段 / `set_traffic_view` 调用点只有本模块 /
  `refresh_interval` 就地生效 / 轮询载荷无 history。
- 改造 8 个既有测试文件(依赖「曲线独家发布」的断言逐条改写, 文件头测试计划清单同步):
  `test_speed_curve` / `test_traffic_monitor_client` / `test_traffic_monitor_dat` / `test_modules_p3` /
  `test_config_traffic_monitor`(新增 `refresh_interval` 边界守阵) / `test_config_key_surface`(探针表加键) /
  `test_module_host`(装配清单) / `test_web_views_reload`(钉段补 `traffic_source`)。
