# 3113 —— dup-code-audit core 批次 9 条 refactor issue 实施基线

> 摘要: 报告 `26-10-11-0033` 的 core 9 条 refactor issue(`26-10-11-0207-refactor-core-*`)全部认领并实施 —— A/C 类抽单点收敛、B 类按计划口径只加互指注释: ①qbmanager 抽 `_note_conn_failed/_note_conn_ok/_reload_state`(退役名 `_load_state` 被别名冻结守阵拦下后改名, 守阵生效一次); ②state 日键淘汰收敛 `prune_day_keys` 单点(exec_history/speed_curve/ops skip_check_day 三形态归一); ③集数排除集单点 `episodes.RESOLUTION_EXCLUDE`(tvshows._BARE_EXCLUDE 引用), 正则族/季标记加互指注释; ④ModuleHost 抽 `_iter_hooks`, BaseModule 增 `apply_section`(logging/notify 接入, tracker/rules 因短路原因不同保持显式并注明)与 `register_global_tasks`(speed_curve/maintenance/traffic_sample 三处接入); ⑤grouping 抽 `_scan_triggered_groups/_is_active_download`, ops 抽 `_live_recheck`, traffic_sample 抽 `_close_block_and_reopen/_reset_block/_ingest_acc/_catch_up_level`(关块重开三处实际在 traffic_sample, issue 位置笔误已按 grep 事实落点); ⑥maintenance 抽 `_apply_tag_changes/_purge_matched_tags`; ⑦rules 抽 `_make_ctx/_run_rule/_dispatch_trigger_rules`; ⑧速度单位换算单点 curves.`kib_to_bytes/bytes_to_kib/bytes_to_kib_floor`(取整方向显式: 曲线半值向上 / 读回整除向下), qbapi 6 处消费; ⑨traffic_store 抽 `_read_parse/_ensure_file_prefix` + traffic_grid `_floor_buckets`; traffic 解析差分层(B/C)只加互指注释不合并。接线守阵 `test_state_migration_materialize_is_wired_in_run` 同步改为找 `_reload_state()`(意图不变: 物化在加载后)。
> 基线时间: 2026-10-11 16:30(9 条 issue 全部实施后收口)

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md,memory-bank/issues/26-10-11-0207-refactor-core-conn-state-boilerplate-dup.html

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 c0038049; 工作树含本批次全部改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3113 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16529 语句 / 152 未覆盖 / 5664 分支 / 139 partial; 门槛 98% 达标; 本轮 26.28s)
- 前置机检: `test.quick` 逐项任务后全绿; 改动文件 `dev.fmt` 全量格式化通过。
- 改动面(摘要): `src/auto_qb/core/`(qbmanager / state / curves / qbapi / episodes / tvshows / traffic_store / traffic_grid / module) + `src/auto_qb/core/modules/`(speed_curve / ops / grouping / maintenance / traffic_sample / rules / tracker / logging / notify) + `tests/test_rule_engine.py`(接线守阵 1 处) + `memory-bank/issues/` 9 条状态流转。见 kb.baseline。
