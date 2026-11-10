# 5910 passed, 2 skipped —— G9 跳检自身失败闸门批全量基线

> 摘要: G9 跳检自身失败闸门批(谓词单点 self_recheck_failed_today + ops G9/规则侧链4 双落点)全量测试基线: 5910 passed, 2 skipped (143.61s), 覆盖率 99% (26254 stmts / 48 miss)
> 基线时间: 2026-11-10 07:19

## 验收数字

5910 passed, 2 skipped in 143.61s (0:02:23)

覆盖率: TOTAL 26254 stmts / 48 miss / 9150 branch / 58 BrPart = 99%(99.69%, 闸门 99.5% 达标)

## 本改动面

- src/auto_qb/rules/checking_meta.py: 新增 self_recheck_failed_today 谓词单点(hash-keyed 只读自身)
- src/auto_qb/core/modules/ops_mod.py: checking_meta 导入扩 self_recheck_failed_today + ctx.ops 绑定通道方法(镜像 recheck_cooldown_remaining 同名同形)
- src/auto_qb/core/modules/ops_verdict.py: G9 闸门插入(G8 后 partial 前, case-2 GATE_FORCE)+ docstring 顺序/口径清单
- src/auto_qb/rules/actions/checking.py: 决策链 4 skip-checking 段 mode-scoped 硬 skip + 链表 docstring
- tests/test_checking_full.py / tests/test_ops_skip.py / tests/test_checking_skip.py: +3 守阵(谓词单测/ops G9 闸门/规则侧 mode-scoped; 钉钳红验 2 红→恢复绿)
- tests-real/rm04_relocate/test_rm04_relocate_window.py: 基座 schema_version 6→7(远端预存红, 用户授权顺手修)
- tests-real/tools/daemon_window_wrapper.py: 2 处带圈符号改 ASCII(远端预存红, 用户授权顺手修)
- memory-bank/: issue 26-10-05-0402 Done / 计划 26-11-05-0848 Done / rule-engine.md 回写 / 任务档案 26-11-10-backend-skip-check-self-fail-gate-g9 / 坑档 testing/sync-midrun-coverage-synthesis / active-context 切片 R1
