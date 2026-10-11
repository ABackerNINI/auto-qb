# dup-code-audit · core 批次 9 条 issue 实施(R6)

> 摘要: 用户「修复core部分问题: 26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」→ 9 条 `26-10-11-0207-refactor-core-*` 全部 Open → In Progress → **Fixed**。实施口径 A/C 类抽单点、B 类只加互指注释: qbmanager 连接状态三方法 / state `prune_day_keys` 日键淘汰单点 / `episodes.RESOLUTION_EXCLUDE` 排除集单点 / ModuleHost `_iter_hooks` + BaseModule `apply_section`·`register_global_tasks` / grouping·ops·rules·maintenance·traffic_sample 业务样板各抽单点 / curves 速度单位换算单点(取整方向显式) / traffic_store `_read_parse`·`_ensure_file_prefix` + traffic_grid `_floor_buckets`。实施细节与陷阱(qbmanager 退役名撞车 / 关块重开位置笔误 / 落批时序保持)见任务档案 R8 节与坑档 `pitfalls/backend/qbmanager-retired-names.md`。收口 `test.full` 3113 passed + 4 skipped / TOTAL 99%, 基线 `26-10-11-1630-core-dup-code-fixes`(见 kb.baseline)。工作树含全部改动, 等用户显式说「提交」再 `ship.commit`。
> 最后活动: 2026-10-11 16:30

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md,memory-bank/issues/26-10-11-0207-refactor-core-conn-state-boilerplate-dup.html

## 正在进行

- **core 9 条已全部 Fixed**(零遗留): conn-state / day-key-prune / episode-marker / module-contract / modules-ops-grouping / modules-tag-rules-sample / speed-unit-convention / traffic-parse-diff-family(仅注释) / traffic-store-read-write。
- **改动面**: `src/auto_qb/core/` 9 文件 + `modules/` 9 文件 + `tests/test_rule_engine.py`(接线守阵锚点 `_reload_state()`) + issues 9 条状态 + 坑档 1 新 + 基线切片 1 新。

## 后续候选(未开工)

- dup-code-audit 其余批次 issue 实施各另开会话: config 6 条 / hr 9 条 / webui 10 条 / rules·infra·torrents 11 条(均 Open)。
- 审查主线: Phase 2 前端轮 20(shared/*.js 非抽屉)。
