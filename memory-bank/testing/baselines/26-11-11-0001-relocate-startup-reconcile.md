# 5919 passed + 2 skipped —— relocate 启动对账机制 S3 全量基线

> 摘要: relocate 启动对账机制 S3 全量基线
> 基线时间: 2026-11-11 00:01

## 验收数字

```text
TOTAL                                                26277     49   9164     61    99%
5919 passed, 2 skipped in 152.40s (0:02:32)
```

(实测时点: HEAD 4897d4f6 工作树净, `commands run test.full` 2026-11-11 00:01; 较上一基线 26-11-10-0351 的 5890: +29 = 本批新用例 12(test_relocate_startup_reconcile.py) + 期间 develop 并批增量 17(test_traffic_sample_interval_point.py 等新档并入))

## 本改动面

- **relocate_mod.py**(src/auto_qb/core/modules/relocate_mod.py): `_load_jobs` 推导 `rt["reconcile"]`(仿 recover 既有模式)。
- **relocate_lifecycle.py**(src/auto_qb/core/modules/relocate_lifecycle.py): on_task_line 活跃推进后消费 reconcile, 与 recover 同窗(`_qb_up` 探活)。
- **relocate_exec.py**(src/auto_qb/core/modules/relocate_exec.py): 对账判定新段 —— 前置闸 armed_at>0 + 判定表四行 + 双证据重入(证据① 复用 `_member_at_dst` 单点 path_normalize 等值; 证据② `_dst_ready` 全量真值, 不复用 B′ any-hit; 不做「全员已到 dst」特殊直达分支 G3); 重入走 `_set_job` 单点并同步置 armed_at 使闸对所有失败形态闭环; 零新配置键零新持久状态。
- **test_relocate_startup_reconcile.py**(tests/, 新档): 12 用例 333 行(含 cancelled 负例)。
- 清偿两笔(用户拍板顺带): **daemon_window_wrapper.py**(tests-real/tools/)docstring 2 个 circled 符号 ASCII 化(697472b6 带入, ASCII 守卫红); **test_rm04_relocate_window.py**(tests-real/rm04_relocate/)基座 schema_version 6→7 三处(v7 抬升未同步 tests-real, schema 守卫红)。
- 计划件: **26-11-10-0721-plan-relocate-startup-reconcile.html**(memory-bank/plans/)§3.2 口径对齐/R3 行; 本批为计划 S3 全量基线(S1+S2 实施见 4897d4f6)。
- 基线切片: 本文件(`kb.new baseline`, --total 从 test.full 结论行誊写)。
