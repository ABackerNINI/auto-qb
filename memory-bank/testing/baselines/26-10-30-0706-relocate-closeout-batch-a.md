# 4156 passed + 10 skipped(根) —— relocate 收口三修: 失败路径消费 resume_hashes / 相位机 dry_run 短路 / REBUILD-RESPAWN 退避

> 摘要: 第二次全项目 code review 批A 三条 relocate 收口: 失败路径消费 resume_hashes(不再留整组静默暂停) / 相位机与撤销补 dry_run 短路(堵恢复账本路径绕过 --dry-run) / REBUILD·RESPAWN 加退避与 attempts 上限(不再每 tick 一轮 create-fail-delete); 三件一并复位到 Done
> 基线时间: 2026-10-30 07:06

## 验收数字

`commands run test.full`(pytest `-n 8 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-30 实测, 全量约 70s, 建档 07:06):

```
  TOTAL                                                20831    113   7132    106    99%
  4156 passed, 10 skipped in 70.01s (0:01:10)
```

- 汇总行: **4156 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 113)。
- 逐条口径注记:
  - 本轮**新增 9 条 pytest 用例**(全在 `tests/test_relocate_exec.py`): 失败路径 resume ×3、dry-run 短路 ×2(相位机 / 撤销)、建链失败 attempts 记账 ×1、重建退避 ×1、重建上限 ×1、guardian 重拉退避 ×1; 另**改判据 2 条既有用例** —— `test_reconcile_respawn_guardian_on_stale_heartbeat`(重拉退避生效后需把 `rt["respawn_ts"]` 推到窗口外才看得到重拉)与 `test_relocate_paths.py::test_reconcile_revert_redelist_done_external`(重删分支同因), 两条都是「旧实现每 tick 必拉」的判据被新退避推翻, 不是功能回退。
  - `test_exec_dry_run_no_side_effects` / 既有 dry-run 用例未动(dry-run 闸门只加在相位机与撤销入口, `relocate_execute` 的既有行为逐字不变)。
  - 零 `src/` 之外的生产改动; 未跑 e2e(改动不涉前端面)。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/core/modules/relocate_mod.py` | 新增 `_resume_members()` / `_fail()` 两个收口单点, 11 处失败出口(含 `cancel_failed`)全部改走 `_fail`;`_arm` / `_finish_direct` / 撤销成功路径的恢复统一到 `_resume_members`;`_arm` 武装成功时 `attempts` 归零;`on_task_line` 与 `relocate_cancel` 补 dry_run 短路;新增 `_respawn_guardian(job, rt)`(带退避), 对账三条重拉分支改走它;ACT_REBUILD 加 attempts 上限(转 `failed`/`rebuild_exhausted`)与退避(`rt["rebuild_ts"]`);`_build_links` 失败分支记 `attempts + 1` |
| `src/auto_qb/core/modules/relocate_units.py` | 新增三个执行体内部节拍常量 `REBUILD_MAX_ATTEMPTS=3` / `REBUILD_BACKOFF=300s` / `RESPAWN_BACKOFF=60s`(与 `GUARDIAN_HEARTBEAT_MAX_AGE` 同档; 未扩配置键面) |
| `tests/test_relocate_exec.py` | 新增 9 条用例 + 修订 1 条既有重拉判据;`_job()` 辅助扩 `resume_hashes` / `src` / `dst` / `scope` 参数;头部「测试计划」清单同步 |
| `tests/test_relocate_paths.py` | 修订 1 条既有对账用例的重删分支判据(重拉退避) |
| `memory-bank/issues/26-10-30-0616-bug-*.html`(3 件) | 认领 → 复验(均仍复现)→ 已修, 状态置 Done 并补「实际修法 / 验证方式 / 测试数字」 |
