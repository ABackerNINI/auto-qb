# 5185 passed + 10 skipped(根) —— WebUI 迁移可见性 P3(qB 待收尾标签镜像)完成后全量

> 摘要: WebUI 迁移可见性 P3(qB 待收尾标签镜像)完成后全量
> 基线时间: 2026-11-04 13:30
**Refs:** memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html

## 验收数字

- `commands run test.full` 实测(2026-11-04 13:30, 157.0s, P3 标签镜像完成后): **5185 passed + 10 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 24361 stmts / 227 miss / 8342 branches / 170 partial / **99%**
- 针对性: `commands run test.one -- tests/test_relocate_tag_mirror.py tests/test_relocate_config.py tests/test_config_key_surface.py tests/test_config_schema.py` 79 passed(含标签镜像 8 例); `commands run test.keys-update` 键面 v5 -> v5, 197 -> 198 键(新增 `relocate.pending_tag`)

## 本改动面

- `src/auto_qb/core/modules/relocate_units.py`: 新增 `PENDING_TAG_PHASES`(armed + 收尾窗口), 标签镜像窗口单点。
- `src/auto_qb/core/modules/relocate_lifecycle.py`: `_tag_name`/`_tag_goal`/`_sync_pending_tag`/`_reconcile_pending_tags`; `on_task_line` 每 tick 补写非终态 job; 失败退避 30s 只告警计数, dry-run 零写。
- `src/auto_qb/core/modules/relocate_mod.py`: `_tag_applied`/`_tag_next_try`/`_tag_failures` 运行态; `_set_job` 在 state 落盘后推标签(armed 加 / 终态摘)。
- `src/auto_qb/config/models.py` + `config/schema/fields.py`(`RELOCATE_TAG_NS` 保留前缀常量)+ `schema/groups.py` + `validation/sections.py` + `loaders.py`: 新键 `relocate.pending_tag` 默认空(关闭), 非空须以 `zRelocate` 开头且不含逗号。
- `minimal.yml`: 注释示例; `memory-bank/config-reference/keys.md`: relocate 段补键说明。
- `tests/test_relocate_tag_mirror.py`(新 8 例): 默认零写/armed 加/终态摘/不读回/用户手删不重加/失败降级/重启补写/dry-run; `tests/test_relocate_config.py` 新增命名空间校验与 loader 用例; `tests/test_config_key_surface.py` + 基线补探针。
