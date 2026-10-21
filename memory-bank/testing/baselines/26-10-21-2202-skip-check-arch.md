# 3989 passed + 2 skipped —— S5 收尾: 计划 Done + issue 重估 + 文档回写

> 摘要: S5 收尾: 计划 Done + issue 重估 + 文档回写
> 基线时间: 2026-10-21 22:02
**Refs:** memory-bank/plans/26-10-21-1857-plan-skip-check-async-refactor.html

## 验收数字

```text
TOTAL                                                20992      97   7090      99    99%
3989 passed, 2 skipped in 168.20s (0:02:48)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%, 实测 99.30%), 在 S5 收尾后的工作树上实测(本轮无代码改动, 只动档案与文档)。
- 收尾轮改动: 三条背景 issue 解除认领并回到 `Open`(状态日志写明已落地部分与剩余面)、计划置 `Done`、`systemPatterns/main-loop.md` 补第三条时间线(微步线)、`modules/core-runtime.md` 的 ops 行补相位机说明。
- 三条 issue 的 s7(状态变更日志)在早前填充正文时被整段覆盖丢失, 本轮补回(入池/认领/重估三条历史)。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- 代码零改动(本轮纯收尾)。
- `memory-bank/issues/26-10-21-1812-bug-cmd-driven-resync.html` / `…decision-moment-live-query.html` / `26-10-21-1813-bug-qbapi-write-facade-store-writes.html`: 状态 `In Progress` → `Open`, 解除与计划的认领链, 补回 s7 状态变更日志(含 S5 重估结论)。
- `memory-bank/plans/26-10-21-1857-plan-skip-check-async-refactor.html`: `doc-status` → `Done`, 封面状态改「Done（S1–S5 全部完成）」, 变更记录补 S5 条目与未纳入本计划的后续项。
- `memory-bank/systemPatterns/main-loop.md`: 主循环伪码补 `host.run_micro_line(dry_run)` 与等待超时并入微步线; 新增「第三条时间线: 微步线」段。
- `memory-bank/modules/core-runtime.md`: `ops_mod.py` 行补相位机/微步线/异步入口/崩溃对账说明。
