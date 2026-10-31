# 4328 passed, 10 skipped (coverage 99%: 21812 stmts, 163 miss, 7400 br, 126 pb) —— 状态漂移机检落地(守卫测试 9 条+接线+wrap 集成+存量清零)

> 摘要: 状态漂移机检落地(守卫测试 9 条+接线+wrap 集成+存量清零)
> 基线时间: 2026-11-01 00:16

## 验收数字

`commands run test.full` (178.6s, 2026-11-01 实测):

```text
TOTAL                                                21812    163   7400    126    99%
4328 passed, 10 skipped in 175.99s (0:02:55)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。

## 本改动面

- 新增 `.agents/skills/memory-bank/scripts/check_status_drift.py`(状态漂移机检, 四档判据+异常档, 481 行)。
- `.agents/skills/memory-bank/scripts/wrap_session.py`: 收尾尾部追加状态漂移双档清单与硬拦提示行(不改退出码)。
- `.commands/kb/config.toml` + `.commands/my-commit-flow/.my-commit-flow.toml`: kb.check 第 9 条与 memory-bank 组闸门同步接线。
- `tests/test_memory_bank.py`: 新增守卫测试 9 条(四档判据/异常档/豁免路径/接线钉名/wrap 行为), 头部测试计划同步。
- 存量清零: issue 26-10-10-1108 badge 对齐 Done; tasks 26-10-11-webui-drawer-refactor、26-10-13-backend-seed-state-writeback 翻 Done(各自取证链见档案进度日志)。
