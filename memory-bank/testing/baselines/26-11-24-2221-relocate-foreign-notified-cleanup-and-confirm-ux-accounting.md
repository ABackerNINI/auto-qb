# 7026 passed, 6 skipped, 2 warnings(根) —— 外部旧路径种子通知账清理与探测确认 UX 记账批后基线

> 摘要: 外部旧路径种子通知账清理与探测确认 UX 记账批后基线
> 基线时间: 2026-11-24 22:21
**Refs:** memory-bank/tasks/26-11-24-backend-relocate-foreign-notified-cleanup.md

## 验收数字

TOTAL                                                31412    108  11190     93    99%
7026 passed, 6 skipped, 2 warnings in 190.80s (0:03:10)

`commands run test.full` 实测(2026-11-24 22:18, HEAD `b638122e`, 覆盖率 99% 达标)。本批只改知识库文档/记账件，零产品代码与测试改动；passed/skipped/覆盖率与上一条基线持平，2 条 warnings 按当前树实测记录，不归因于本批文档改动。

## 本改动面

- `memory-bank/issues/26-11-24-2150-bug-relocate-probe-reask-ui-loop.html`: 新建 Open bug，记录首次确认被同机探测闸消费、`warn` 回执被前端当失败、续跑再确认造成「回到设定位置框」的三步 UX 回环，附日志与四处代码锚点。
- `memory-bank/issues/26-11-22-0905-question-relocate-confirm-probe-reask-three-step.html`: 只补新 issue 的反向声明，状态仍 Done。
- `memory-bank/plans/26-11-24-2204-plan-relocate-foreign-notified-cleanup.html`: 新建 Open 计划，拍板启动自愈窄版清理（仅清缺失/终态 A 与 mismatch，保留 B 与 active A），不覆盖 D4 终态重告警语义，真机验收走测试 qB `real.up`。
- `memory-bank/tasks/26-11-24-backend-relocate-foreign-notified-cleanup.md`: 立档，汇总原始请求、根因、D1–D8 取舍与后续实现/验收分步。
- 本基线切片与 active-context 切片 `backend-relocate-foreign-notified-cleanup`: 随本专题入库；评审两轮零 actionable，`kb.check` / `kb.docmap` / `ship.gate` 全绿。
