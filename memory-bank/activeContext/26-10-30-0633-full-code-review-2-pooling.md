# full-code-review-2-pooling

> 摘要: 二评 26 条发现入池落位: 17 新池位(6xP2 标准档 + 2 合并条 + 9 P3 逐条, 专题 full-code-review-2, 状态全 Open) + 3 处既有池备注回填(26-09-21-1408/26-10-20-2345/26-10-20-2231), 复验留待认领时做; kb.index/kb.check 全绿, 26/26 对账无落空
> 最后活动: 2026-10-30 07:10

**R0(2026-10-30 06:33):** 二评 26 条发现入池落位: 17 新池位(6xP2 标准档 + 2 合并条 + 9 P3 逐条, 专题 full-code-review-2, 状态全 Open) + 3 处既有池备注回填(26-09-21-1408/26-10-20-2345/26-10-20-2231), 复验留待认领时做; kb.index/kb.check 全绿, 26/26 对账无落空

**R1(2026-10-30 07:10):** 认领并修复二评批A 三条 relocate bug(resume_hashes 失败路径 / 相位机与撤销 dry_run 短路 / REBUILD-RESPAWN 退避与 attempts 上限): 11 处失败出口统一走 _fail 收口单点, on_task_line 与 relocate_cancel 补 dry_run 闸, 增 REBUILD_MAX_ATTEMPTS/REBUILD_BACKOFF/RESPAWN_BACKOFF 三常量; 三件 issue 复验仍复现后修复并置 Done
