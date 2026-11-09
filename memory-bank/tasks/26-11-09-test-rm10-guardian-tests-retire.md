# 26-11-09-test-rm10-guardian-tests-retire — tests-real RM10 guardian 三用例随 finalize_watch 退役 (issue 26-11-09-2128)

**Status:** Done
**Added:** 2026-11-09
**Updated:** 2026-11-10
**Summary:** 测已退役 finalize_watch 的 tests-real RM10 三用例随 S4a 决定退役清偿, 过期 acquire_pid 导入修复, 全量 5876 passed 复绿 (issue 26-11-09-2128)
**Topics:** test-rm10-guardian-tests-retire
**Refs:** memory-bank/issues/26-11-09-2128-test-tests-real-acquire-pid-stale-import.html

## 本篇只回答

tests-real 侧 RM10-05/06/07(测已随 S4a 整文件退役的 finalize_watch/guardian)如何清偿: 为何退役而非改写、退役边界(用例+独占 helper+过期导入)、验证方式。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-09-2128-test-tests-real-acquire-pid-stale-import.html」

## 思考过程与决策

- issue 表象: `tests-real/rm10_notify/test_rm10_notify.py` 模块级 `from auto_qb.infra.relocate_journal import acquire_pid` —— 该符号已随 S4 退役, import 即失败, 整文件无法收集; `tests-real/` 不在 pytest testpaths, 全量全绿也发现不了。
- 根因比 issue 表象深一层: 该文件 RM10-05/06/07 三条 guardian 用例测的是 `finalize_watch`(S4a 66418c7e 已整文件退役, 285 行删除, 同步退役了 `tests/test_finalize_watch.py` 但漏了 tests-real 侧); 三证的接替面 recycle_daemon 已有 `tests/test_recycle_daemon.py` 单测覆盖。
- **拍板: 退役而非改写** —— 对齐 S4a 既有决定(「测试面同步退役」), 不是缩小修法; 组件已删, 「改用现行 API」无从谈起。
- 退役边界: 三条用例 + 仅其独占的面( `_StepClock`/`_journal_watch`/`_accept_loop`/`build_guardian_scene`/`GUARDIAN_JOB`/`dead_port`/`import json`/`import socket`/`alias_fs`/`guard` 导入/ relocate_journal 全部导入)。活用例 RM10-01/02/03/04/08 与其 helper(`case_dir`/`purge_tree`/`_ps_pids`/`send_attempts`/`metric` 等)不动; `_ps_pids` docstring 的 `finalize_watch._names_from_tasklist` 指针改指随迁后的 `recycle_daemon._names_from_tasklist`。
- 发现路径盲区(不在本轮修): `tests-real/` 不在 testpaths 的结构性盲区仍在那, 下次再漂移还是要靠人工全仓复扫。

## 实现计划

1. 模块 docstring 八条→五条, 记退役依据(66418c7e / issue 26-11-09-2128)与接替面指针。
2. 删三条用例与独占 helper/导入(sed 自底向上三段删 + Edit 小修)。
3. 验证: pytest collect-only 收集 5 条不再 import 失败; AST 查无未用导入; dev.fmt 过。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | docstring 改五条口径 + 退役注记 | Done(2026-11-09) |
| 2 | 删 RM10-05/06/07 + 独占 helper + 过期导入 | Done(2026-11-09) |
| 3 | collect-only 5 条 + AST 导入检查 + fmt | Done(2026-11-09) |
| 4 | 评审 5 发现修完(conftest/export_merge/档案数字) | Done(2026-11-09) |

## 进度日志

### R0 · 立档 (2026-11-09)

- issue 26-11-09-2128 认领修复; 代码面完成(test_rm10_notify.py 10 增/325 删), collect-only 验证过。
- 评审: 只读子代理 1 派, 检 5/5, blocker 0, minor 4 + nit 1 全部当场修(conftest 两处 docstring 仍按八条口径 / export_merge「既有 8 条」失真 / 档案 numstat 旧快照 / 66418c7e 实删 285 行非 286)。
- 环境清障(计划外, 非代码): ASCII 闸门红于本 clone 11-05~07 会话遗留的 `tests-real/.work/` 实验探针 6 文件(gitignore 工件, 结论已录 tasks/26-11-05-backend-relocate-fastresume-finalize.md), 按 tests-real `.work` 收尾即删纪律删除; 认领链 D4 反向声明补进本档案 Refs 行。
- 收尾: 全量在合并后 HEAD 77b649fc 复测 5876 passed/2 skipped(基线切片 26-11-09-2341-test-rm10-guardian-retire); 新坑 `pitfalls/testing/tests-real-retirement-blindspot.md`(退役 grep 面必须含 tests-real)已入档并 kb.index。

- 2026-11-09 23:44 退役 RM10-05/06/07 + 独占 helper + 过期导入; 评审两轮(5 发现全修, 复评零 actionable); test.full 5876 passed/2 skipped; 基线切片 26-11-09-2341; issue 翻 Done; ASCII 闸门红清障(删本 clone 遗留 .work 探针 6 文件)
