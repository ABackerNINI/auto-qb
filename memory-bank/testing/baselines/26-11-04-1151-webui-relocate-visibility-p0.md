# 5159 passed + 10 skipped(根) —— WebUI 迁移可见性 P0 完成后全量

> 摘要: WebUI 迁移可见性 P0 完成后全量
> 基线时间: 2026-11-04 11:51
**Refs:** memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html

## 验收数字

- `commands run test.full` 实测(2026-11-04 11:51, 155.3s, P0 完成且共享装饰层指纹改动后): **5159 passed + 10 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 24029 stmts / 226 miss / 8214 branches / 168 partial / **99%**
- 口径注记: 首跑出现 1 例既有偶发失败(`test_qb_capture` 伪 hash 随机落回真值 "H1"), 复跑通过; 与本改动无关, 未修改该测试。

## 本改动面

- `src/auto_qb/core/modules/relocate_units.py`: `RelocateJob.origin`(旧 state 回落 unknown) + `RelocateSnapshot`/`job_rank` 只读快照数据契约。
- `src/auto_qb/core/modules/relocate_mod.py`、`relocate_lifecycle.py`: 主循环 job 变更路径发布不可变快照(`by_hash` 最佳 job), 内容变化置 full 脏; Web 只读 `jobs_snapshot()`。
- `src/auto_qb/core/modules/relocate_exec.py`、`src/auto_qb/webui/commands_torrents.py`、`src/auto_qb/rules/actions/transfer.py`: `relocate_execute(origin=...)` 落账, web/rule 入口分别传值。
- `src/auto_qb/webui/views_relocate.py`(新): 相位归并、成员标注、组级后端聚合纯函数; 零文件系统探测。
- `src/auto_qb/webui/views.py`/`views_row.py`/`views_group.py`: 成员/组 `relocate` 字段(值恒在, 无 job 为 null), 组级状态后端聚合。
- `src/auto_qb/webui/static/shared/decorate.js`: 成员/组 relocate 值签名进指纹, 槽位长度同步(8n+3)。
- `tests/test_webui_relocate_visibility.py`(新) + `tests/test_actions_state.py`/`test_relocate_exec_run.py` stubs: 状态归并、origin、组级 mixed/顺序无关、快照活跃优先、三种 null、零触盘/零 job 遍历、指纹槽位。
