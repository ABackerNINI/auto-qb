# 4935 passed + 2 skipped(根) —— R5 后端单类/大 Mixin 拆分后全量基线

> 摘要: R5 后端单类/大 Mixin 拆分后全量基线
> 基线时间: 2026-11-03 08:19
**Refs:** memory-bank/tasks/26-11-03-test-big-file-split.md, memory-bank/plans/26-11-02-2342-plan-big-file-split.html

## 验收数字

`commands run test.full` 实测(同步远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22785    134   7736    128    99%
4935 passed, 2 skipped, 3 warnings in 208.32s (0:03:28)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `infra/utils.py` 1435 → 879 行根 + `utils_parse.py` 302 / `utils_paths.py` 361; Windows 域与 tracker 脱敏域、`resolve_or_create_token` 留根(patch 名同模块)。
- `core/traffic_store.py` 1616 → 615 + `traffic_store_common.py` 142 / `_paths.py` 130 / `_codec.py` 745 / `_agg.py` 130; `TrafficV4Store`/`V4DayCache` 与 `_bad_line_warn_ts` 留根。
- `core/modules/traffic_sample_mod.py` 1622 → 650 + `traffic_sample_common.py` 172 / `_agg.py` 544 / `_blocks.py` 350。
- `core/modules/relocate_mod.py` 1586 → 131 + `relocate_common.py` 85 / `_lifecycle.py` 172 / `_plan.py` 458 / `_exec.py` 800; 作业表与持久化留根。
- `core/modules/ops_mod.py` 1270 → 374 + `ops_common.py` 86 / `ops_verdict.py` 301 / `ops_skip.py` 500 / `ops_jobs.py` 90; `_backup_torrent` 留根。
- `hr/service.py` 1829 → 411 + `service_common.py` 446 / `service_wave.py` 945 / `service_status.py` 205; `build_adapter`/`build_site_view` 留根。
- `webui/views.py` 1163 → 432 + `views_common.py` 157 / `_group.py` 131 / `_row.py` 171 / `_episodes.py` 248 / `_search.py` 105; 三个 budget/TTL 常量的读取点留根。
- `webui/runtime.py` 1701 → 247 + `runtime_common.py` 128 / `_views.py` 751 / `_commands.py` 442 / `_stream.py` 222; `__init__`(时钟 patch 面)留根。
- `webui/commands.py` 1590 → 240 + `commands_common.py` 311 / `_torrents.py` 819 / `_config.py` 224 / `_limit.py` 69 / `_logs.py` 15; `TransferOrchestrator` 相关命令与 `_trackers_baseline` 留根。
- 全部 move-only: 根保留组合类/门面并全量 re-export 公开面, MRO 顺序沿用原方法解析, logger 名冻结; 唯一等价改写点是 `traffic_sample_agg.py` 内 6 处 `TrafficSampleModule._x` → `_SampleAggMixin._x`(避环, 非 patch 目标)。
- 守阵引用最小同步 6 个测试文件(`test_traffic_store_codec` / `test_utils_parse` / `test_utils_windows` / `test_web_hr_search` / `test_web_seed_center` / `test_webui_static_skins_widget`), 断言语义未改; 暂缓 2 个(`config/validation/sections.py` 1044 / `core/qbmanager.py` 1008)零改动; 新桶均 ≤1000(最大 945), 排期清单无新增。
