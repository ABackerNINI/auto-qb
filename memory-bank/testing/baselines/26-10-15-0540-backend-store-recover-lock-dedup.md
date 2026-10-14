# 3221 passed + 4 skipped —— hr 恢复链与文件锁跨包收口(issue 26-10-11-0240 hr-store-recover-lock-family-dup)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html」→ dup-code-audit infra 轮(R18)对三轮暂缓跨包件的合并考量收口。改动 4 源文件 + 1 新测试文件: `src/auto_qb/infra/store_recovery.py` 新增「读坏→(挪走)留证→读 `.bak`」编排单点 `recover_corrupt_file`(回调式 `read_backup` + 可选 `quarantine`, 不传 = 原地保留)与 `quarantine_bad_file` 时间戳留证单点, hr/store 的 `_recover` 与 core/state 的 `load()` 损坏分支两处调用(语义差异全留调用方); `infra/locking.py` 新增 `open_file_lock` / `release_file_lock` 构造/释放单点, hr 站点锁与 SingleInstanceLock 同族收口; 消息文案字节同、行为逐位不变; 静态守阵两判据均过红验。
> 基线时间: 2026-10-15 05:40

**Refs:** memory-bank/tasks/26-10-15-backend-store-recover-lock-dedup.md,memory-bank/activeContext/26-10-15-0540-store-recover-lock-dedup.md,memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html

## 验收数字

- test.full: 3221 passed + 4 skipped / TOTAL 16862 161 5720 144 99%; 耗时 170.9s(单次采样, 口径见 baseline.md)。
- 定向 test.one(逐文件): tests/test_hr_store.py 55 passed / tests/test_locking.py 7 passed / tests/test_rule_engine.py 34 passed / tests/test_hr_status.py 28 passed / tests/test_hr_service.py 133 passed / tests/test_store_recovery.py(新增) 10 passed。
- 红验(一次性工作树变异, 还原即绿, 不进提交): ①恢复链自抄回潮 —— 临时文件放入 `.bad-{int(time.time())}` 字面量 → `test_recovery_chain_single_point_in_infra` 红, 删除即绿; ②filelock 裸 import 回潮 —— 临时文件写 `from filelock import` → `test_filelock_dependency_single_point_in_infra_locking` 红, 删除即绿。另: 改道过程的两个真实红(hr 例行 `store.quarantine` seam 被 infra 内置编排绕过)由回调式设计消解, 见档案进度日志。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 闸门 match 不命中, 未跑。
- Linux(WSL)侧未重测 —— 改动为跨模块编排收口 + 锁构造入口, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- 源(4 文件): src/auto_qb/infra/store_recovery.py(新增, 编排 + 留证单点) · src/auto_qb/infra/locking.py(`open_file_lock` / `release_file_lock` 单点 + SingleInstanceLock 委托) · src/auto_qb/hr/store.py(锁走单点 / quarantine 委托 / `_recover` 走编排) · src/auto_qb/core/state.py(`load()` 损坏分支走编排 + `_read_backup_dict` 契约); 另 src/auto_qb/infra/__init__.py 模块清单 +1 行; 全部过 dev.fmt。
- 测试(1 文件): tests/test_store_recovery.py(新增 10 条: 编排顺序 / 不传 quarantine 原地保留 / 挪不动旗标 / 原因透出 / 数据透出 / quarantine_bad_file 三态(含 OSError)/ 静态单点守阵 2 条), 头部「测试计划」清单同步。
- 文档: 本切片 · issue 报告 26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html(Done, 复验/实际修法/验证方式/测试数字留痕, doc-refs ↔ 档案 Refs 双向) · 任务档案 26-10-15-backend-store-recover-lock-dedup.md · activeContext 切片 26-10-15-0540-store-recover-lock-dedup.md · 主档案 26-10-10-backend-dup-code-audit.md 进度记 R12 · hr 档案 26-10-11-backend-hr-dup-code-fix.md 待办口径更新 · kb.index 重建。
