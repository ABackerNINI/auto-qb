# 26-11-03-memory-bank-code-review-3-s7 — 全量代码评审 3 · S7（处置建议 + 终版报告 + 收尾）

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** S7：18 条终表定去向与优先级（P1 两条先行）、终版报告落盘、计划推进 Done、test.full/文档机检与基线收尾，零源码改动
**Topics:** memory-bank-code-review-3-s7
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s6.md, memory-bank/reports/26-11-03-0636-report-memory-bank-full-code-review-3.html, memory-bank/testing/baselines/26-11-03-1245-code-review-3-s7.md

## 原始请求

1. 执行第三次 code review 计划的 **S7 步骤**（处置建议 + 终版报告 + 收尾）。
2. 必读计划 `memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html`（S7 段与总验收判据）+ S2–S6 五份 task 文档（S6 的 18 条终表为主输入）+ 报告骨架 `memory-bank/reports/26-11-03-0636-report-memory-bank-full-code-review-3.html`。
3. 工作方式：遇到问题一律**当场入池后继续**，不停下等指示；只做评审报告与收尾，**零代码改动**。
4. 开工先 `commands run my-commit-flow.sync`，贴「已同步 <hash>」；只在 clone1 操作。
5. 终版报告要求：单文件 HTML、dark 主题、delivery-artifact 风格；含 18 条终表（级/类型/三锚/可达性/对应 issue）、处置建议与优先级排序、证据边界（实证 vs 静态推断）、未覆盖面（元层/重复代码审查 Phase 3-4/生产 config.yml 与 auto-qb-data）、过程账（S0–S7 各步发现数与 issue 数）；**不写每步流水**。
6. 处置建议要点：P1 两条（`26-11-03-1035-bug-webui-group-window-source-mismatch`、`26-11-03-1144-bug-qb-capture-fs-delta-sanitize`）建议先行修复并说明理由与影响面；其余 16 条按依赖/风险排序。fs_delta 的表述按 S6 精修为「叠到错误完整路径而非静默丢增量」。
7. 收尾验证：`commands run test.full` 与最新基线切片对比（持平或说明差异），`doc.links`/`doc.caps`/`kb.check`/`kb.index` 全绿。
8. 计划文档：S7 与整体状态推进为 Done，补最终报告链接，**不写流水**。
9. 收尾 DoD 回写（含新基线切片，若 `test.full` 数字变化需新建并誊写实测），然后**单独提交并推送**。
10. 回复：同步结果、test.full 实测数字与基线对比、终版报告路径、计划状态、提交 hash 与推送核验、汇总要点（18 条分级、两条 P1、建议先做什么）。

## 思考过程与决策

- **报告就地终版化**：不新建第二份报告，直接把 S0 骨架 `26-11-03-0636-report-memory-bank-full-code-review-3.html` 填成终版并翻 `doc-status` → Done（report 恒终态）。报告是快照产物，正文只留结论/终表/处置/边界/过程账，不写 S0–S7 流水。
- **18 条去向**：全部「维持 Open + 建议修复」，无「已知接受/不修」判定；本轮不改任一 issue 状态，也不认领、不修复（零代码改动）。两条 P1 建议先行；`#5`（P2）虽非 P1，但被标注为 `#4` 的回归门禁前提，建议同批。
- **fs_delta 措辞精修**：按 S6 决策，把「回放端静默丢增量」改为「按伪 hash 取 `save_path` 落空后，增量被叠到**错误完整路径**（仍写入 `_disk_override`，非丢弃）」。报告与终表统一采用后者，避免夸大。
- **计划不写流水**：只改 S6/S7 两格的完成状态与报告链接，另加一条 R 行记录本步落盘；不新增过程叙事。S6 task 的 `Status` 从 In Progress 收口为 Done，与计划格子一致。
- **基线差异处理**：`test.full` 实测与最新切片（26-11-03-1112，另在 feat 分支实测）不是同一分支口径，且通过/跳过数与本步实测有差；按 DoD **新建基线切片**誊写本步实测数字，并在报告 §06 只引用切片不手抄数字。
- **零改码**：全程未改 `src/`、`scripts/`、`tests/`、`config.yml`、`auto-qb-data/`。

## 实现计划

1. 开工同步并记录当期 HEAD。
2. 读计划 S7/验收判据 + S2–S6 五份 task + 报告骨架。
3. 汇总 18 条终表，定每条去向，按依赖/风险排优先级（P1 先行）。
4. 写终版报告（单文件 HTML dark）并翻 Done。
5. 计划 S6/S7 状态与报告链接回填，变更记录留 R 行。
6. 跑 `test.full` 并与最新基线对比；按差异决定是否新建切片。
7. 跑 `doc.*`/`kb.check`/`kb.index`，收尾 DoD 回写。
8. 本档落盘 → 单独提交并推送 → 回复汇总。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S7-0 | 同步 + 读计划/S2–S6/报告骨架 | Done(2026-11-03) |
| S7-1 | 18 条终表定去向 + 优先级排序 | Done(2026-11-03) |
| S7-2 | 终版报告撰写（含证据边界/未覆盖面/过程账） | Done(2026-11-03) |
| S7-3 | 计划 S6/S7 状态与报告链接回填 | Done(2026-11-03) |
| S7-4 | `test.full` 实测 + 基线对比 + 新基线切片 | Done(2026-11-03) |
| S7-5 | `doc.links`/`doc.caps`/`kb.check`/`kb.index` 机检 | Done(2026-11-03) |
| S7-6 | 收尾 DoD 回写 + 本档落盘 | Done(2026-11-03) |
| S7-7 | 单独提交并推送 | Done(2026-11-03) |

## 进度日志

### R0 · S7 执行 (2026-11-03)

- **同步**：`commands run my-commit-flow.sync` → **已同步 6ea8c949**（无改写 HEAD 的步骤）；工作树仅本步文档改动，只动 clone1。
- **终表输入**：以 S6 §2 的 18 条为唯一输入，逐条复核级/类型/三锚/可达性/issue 对应；未新增、未降级、未升级、未合并。分级计数 P0 0 / P1 2 / P2 8 / P3 8。
- **处置去向**：18 条全部「维持 Open + 建议修复」；本轮不改 issue 状态。优先级见终版报告 §03：P1 两条先行（#9 fs_delta 安全红线优先于 #4 group 窗口化）；其后按「门禁/启动硬失败 → 功能正确性 → 文档真值 → 守阵补强 → 低风险清理」五批推进。
- **报告**：`memory-bank/reports/26-11-03-0636-report-memory-bank-full-code-review-3.html` 由骨架就地终版化，`doc-status` = Done；章节为结论 / 18 条终表 / 处置与优先级 / 证据边界 / 未覆盖面 / 过程账 / 材料索引，不含逐步流水。
- **计划**：S6 与 S7 格子均标 `Done 26-11-03`，S7 补终版报告链接；`doc-status` 由 In Progress 翻 Done；变更记录追加一条 R 行（kb.bump）。
- **`test.full` 实测**：见 §「实测与基线对比」。
- **机检**：`doc.links` / `doc.caps` / `kb.check` / `kb.index` 结果见本档 R0 末尾行；`doc.caps` 仅存量债务（12 项），本步无新增硬违规。
- **收尾**：DoD 回写完成 → `.git/COMMIT_MSG_AI.txt` + `ship.commit` + `ship.push`，结果行记于 R0 末。

### 实测与基线对比

- 本步 `commands run test.full` 实测数字见新建切片 `memory-bank/testing/baselines/26-11-03-1245-code-review-3-s7.md`（裸数字只写切片这一处）。
- 最新切片 `26-11-03-1112` 在 feat 分支实测，与本步 develop 口径不可直接相减；同口径最近切片为 `26-11-03-1053`（develop）。
- 与同口径切片相比：收集面（TOTAL 语句数）相同，差额全部落在 skipped 一侧：8 条符号链接用例因当前进程缺 `SeCreateSymbolicLinkPrivilege` 跳过（6 条 `tests/test_alias_fs.py` + 2 条 `tests/test_file_access.py:279`），另有 2 条平台语义跳过（`test_grouping_misc.py:219` / `test_web_hr_fs.py:267`）。非源码改动导致，本轮未新增/删除用例。
- 结论：按 DoD 新建切片记本步实测，报告与本档只引用切片、不手抄数字。

- 2026-11-03 12:40 S7 启动：同步 6ea8c949；18 条终表定去向与优先级；终版报告落盘；计划 S6/S7 → Done；零源码改动

- 2026-11-03 12:51 S7 收尾：18 条处置去向/优先级定稿、终版报告落盘、计划 Done、零源码改动、test.full 与文档机检全绿
