# hr store 恢复链与文件锁收口 · dup-code-audit R12

> 摘要: 用户「认领并修复 26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html」→ infra/store_recovery.py 新增「读坏→留证→.bak 兜底」编排单点(回调式), hr/store 与 core/state 两处调用; infra/locking.py 收口 filelock 构造/释放单点, hr 站点锁与单实例锁同族。保守口径行为逐位不变, 新增守阵十条(静态两判据均过红验); 测试全量数字见 kb.baseline。
> 最后活动: 2026-10-15 05:40

**Refs:** memory-bank/tasks/26-10-15-backend-store-recover-lock-dedup.md

## 已完成(2026-10-15 单会话收口)

- 取证归档: 任务档案 `26-10-15-backend-store-recover-lock-dedup.md`(改道记录/语义差异判据/行为等价审计); 基线切片 `26-10-15-0540-backend-store-recover-lock-dedup.md`。
- 改动面: `infra/store_recovery.py`(新) · `infra/locking.py` · `hr/store.py` · `core/state.py` · `infra/__init__.py` + `tests/test_store_recovery.py`(新); 全部过 dev.fmt。未触碰 `config.yml` / `auto-qb-data/`。
- issue 置 `Done`(doc-refs ↔ 档案 Refs 双向); 主档案 `26-10-10-backend-dup-code-audit.md` 进度记 R12; hr 档案 `26-10-11-backend-hr-dup-code-fix.md` 待办口径更新(余 `hr-fetchable-dead-config` 一条 Open)。
- 下一步(不在本轮): dup-code-audit 主线 Phase 2 前端轮; `hr-fetchable-dead-config` 待用户拍板「接上强制 vs 删死字段」。
