# 5343 passed, 10 skipped, 1 warning in 176.88s; coverage 99.63% —— ref 自愈静默与 COMMAND_FLOW_DEBUG 排障出口

> 摘要: ref 自愈静默与 COMMAND_FLOW_DEBUG 排障出口
> 基线时间: 2026-11-05 09:52
**Refs:** memory-bank/tasks/26-11-05-docs-git-ref-silence.md

## 验收数字

`commands run test.full` 汇总行(测于本轮工作树, 与随本专题入库的 tree 一致):

- 5343 passed, 10 skipped, 1 warning in 176.88s
- coverage: 99.63%(TOTAL 24475 stmts / 74 miss / 8396 branch / 40 partial)

口径注记: 8 worker 并行; 同一轮另跑 `.commands/my-commit-flow/scripts/test_commit.py` 包单测全绿(见档案 R0)。

## 本改动面

- `.commands/my-commit-flow/scripts/verify_ref.py`: 成功自愈静默; 自愈失败说明行仅 `COMMAND_FLOW_DEBUG=1` 可见; 输出契约 v7。
- `.commands/my-commit-flow/scripts/commit.py`: 两处 `print(line)` 调用点注释同步。
- `.commands/my-commit-flow/scripts/test_commit.py`: 成功静默/默认静默/DEBUG 可见断言更新。
- `.commands/my-commit-flow/references/pipeline.md` 与 `memory-bank/pitfalls/git/refs.md`: ref 输出口径回写。
- `memory-bank/tasks/26-11-05-docs-git-ref-silence.md`: 本任务档案。
