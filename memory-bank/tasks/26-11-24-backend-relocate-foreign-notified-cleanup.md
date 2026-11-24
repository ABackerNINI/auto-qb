# 26-11-24-backend-relocate-foreign-notified-cleanup — 外部旧路径种子通知账启动自愈与探测确认 UX 记账

**Status:** In Progress
**Added:** 2026-11-24
**Updated:** 2026-11-24
**Summary:** 外部旧路径种子通知账启动自愈与探测确认 UX 记账
**Topics:** backend-relocate-foreign-notified-cleanup
**Refs:** memory-bank/plans/26-11-24-2204-plan-relocate-foreign-notified-cleanup.html, memory-bank/issues/26-11-24-2150-bug-relocate-probe-reask-ui-loop.html, memory-bank/testing/baselines/26-11-24-2221-relocate-foreign-notified-cleanup-and-confirm-ux-accounting.md

## 本篇只回答

本轮如何在不改生产状态、不推翻既有 D4 拍板的前提下，把「旧路径外部种子通知账清不掉」与「探测确认 UX 回环」分别沉淀为可执行 issue 和计划，并完成提交前验证。

## 原始请求

1. 只读分析 `D:\Projects\auto-qb-long-seeding`：整组移动时大量种子显示「旧路径外部种子」、旧路径/现位置与 `首见 —`，分析原因并判断是否与既有 Open issue 相关。
2. 上次响应受 429 中断后，用户要求恢复未完成任务。
3. 用户确认「无法再次移动」实为确认框反复出现导致误判，要求建 issue；本轮聚焦「账目清不掉」，通过 grilling 产出计划。
4. 用户追问「为什么下次还会滞留？目前代码是否一直会产滞留」，要求校正根因表述。
5. 用户逐项拍板：A 窄版自愈、启动扫 + 落账拦截、job 不在 + 已终态、撤掉拦截保留重告警、靠启动自愈、只受 dry-run 限制、使用测试 qB `real.up` 测试。
6. 用户要求「提交」。

## 思考过程与决策

- 根因：目标机历史 61 条候选来自 2026-11-21 的旧扫描；其中 60 条是同 `save_path` 不同内容根的兄弟目录误报，1 条是 BTSchool 的真 scenario A。B1 内容根预过滤已封堵该误报家族，但两 job 终态与历史清空发生在清理逻辑落地之前，导致 `relocate.jobs = 0` 而 `foreign.notified` 仍留 61 条。
- `首见 —` 是组级聚合只带 `state/dst/src/updated_at`、漏带 `first_seen`，种子级注解本身有值；前端显示逻辑无误。
- 「不能动」是 UX 回环：首次确认被同机探测闸消费，回执为 `warn`（已受理、探测中）；前端只把 `confirm` 当确认，把非 `ok` 当失败并重开「设定位置」框；探测后续跑再次要求确认，用户误判为后端拒绝。已入池 issue `26-11-24-2150-bug-relocate-probe-reask-ui-loop`。
- 清理方案取窄版自愈：启动时清 `kind ∈ {A, mismatch}` 且 `job_id` 不存在或 job 已终态的账；保留全部 `kind=B` 与 active job 的 A 账。
- 不 overturn D4：终态 mismatch 允许重落账且只重告警一次，见 `26-11-21-1326-refactor-relocate-foreign-notified-cleanup`；不做落账拦截。
- 边界：清理只在 `relocate.enabled=true` 的 `_load_jobs` 路径发生，且受 dry-run 保护；真机验收走测试 qB 的 `real.up`。
- 完整决策记录见计划 `26-11-24-2204-plan-relocate-foreign-notified-cleanup.html` §05–§07。

## 实现计划

本轮只做诊断与文档入池，不改产品代码、不改生产 `state.json`。后续实现按计划执行：

1. 补启动自愈清理函数并在 `_load_jobs` 尾部接线。
2. 补单测覆盖：(job 缺失 / 终态 / active A / B 保留 / dry-run / enabled 边界)。
3. 用测试 qB `real.up` 做真机验收。
4. 计划完成后单独提交实现批；本档案再追加 R 行。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| T1 | 只读诊断旧账来源、滞留原因、`首见 —` 与确认回环 | Done(2026-11-24) |
| T2 | 新建探测确认 UX issue 并补双向反链 | Done(2026-11-24) |
| T3 | grilling 出启动自愈计划并落 D1–D8 决策 | Done(2026-11-24) |
| T4 | 评审、闸门、全量测试、基线/切片/档案回写并随本专题入库 | Done(2026-11-24) |
| T5 | 按计划实现启动自愈清理函数与接线 | Open |
| T6 | 补测试并用测试 qB `real.up` 验收 | Open |

## 进度日志

### R0 · 立档 (2026-11-24)

诊断确认历史误报家族已被 B1 封堵，滞留来自终态/清史窗口缺失；新建 UX issue 与窄版自愈计划，按拍板保留 D4 重告警语义；两轮只读评审零 actionable，闸门与全量测试全绿（见 kb.baseline），基线切片、会话切片与本档案随本专题入库。

- 2026-11-24 22:22 只读诊断旧路径外部种子滞留与确认回环根因: 新建探测确认 UX issue 与启动自愈窄版清理计划, 保留 D4 终态重告警语义; 两轮评审零 actionable, kb.check/kb.docmap/ship.gate 全绿, 全量测试全绿见 kb.baseline 26-11-24-2221; 实现与测试 qB real.up 验收留作后续
