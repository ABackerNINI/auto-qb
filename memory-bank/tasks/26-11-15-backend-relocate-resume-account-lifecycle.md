# 26-11-15-backend-relocate-resume-account-lifecycle — relocate 恢复确认账生命周期五件联合修

**Status:** In Progress
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** relocate 恢复确认账生命周期五件联合修: grilling 两轮拍板 D1-D14, 计划 26-11-15-0914 入库(Open, S0-S5 待显式开工); 零代码改动
**Topics:** backend-relocate-resume-account-lifecycle
**Refs:** memory-bank/plans/26-11-15-0914-plan-relocate-resume-account-lifecycle.html, memory-bank/issues/26-11-15-0344-bug-resume-account-overwrite-jobid-reuse.html, memory-bank/issues/26-11-15-0345-bug-resume-pending-deleted-member-unclosed.html, memory-bank/issues/26-11-15-0345-bug-resume-popover-terminal-job-null.html, memory-bank/issues/26-11-15-0345-feat-relocate-failure-counters-no-consumer.html, memory-bank/issues/26-11-15-0345-refactor-webui-borrow-relocate-private-constant.html

## 本篇只回答

relocate 恢复确认账生命周期上五份计划外 issue(0344 / 0345-deleted / 0345-popover / 0345-feat / refactor 便签)的联合修方案与执行进度——方案与拍板单点在计划 [26-11-15-0914](../plans/26-11-15-0914-plan-relocate-resume-account-lifecycle.html)(D1-D14 冻结), 本档案管进度与收尾。

## 原始请求

1. 用户列出五份 issue 路径(0344 + 0345×3 + refactor 便签, 另附 26-11-14 qb-side-move-echo), 指令: 「grilling, 然后出一个联合修改计划」。
2. 第一轮拍板(8 问): qb-side-move-echo 排除本批, 只做其余 5 份联合计划; 其余全按推荐(D1-D8)。
3. 第二轮拍板(6 问, 只读取证回报后): 全按推荐(D9-D14)。
4. 终轮确认: 按推荐落盘计划件 + 立档。

## 思考过程与决策

- 两轮 grilling 14 决策全按推荐拍定, 全表见计划 §06; 无遗留待拍板项。
- 只读取证子代理(取证于 e2825b4b)五面事实(恢复账结构/复用路径/计数器与持久化/拍节奏/webui 浮窗链), 两个关键改判: ① 0344 真覆盖点是 `_start_job` exec:1583 裸赋值——issue 原锚 register_job 生产零调用, 属遗留 API(D14); ② `resume_retries` 是 job 级 int 非按成员 dict → D2「清零重计」天然成立, 实现收敛为「prev.resume_pending 并进新 job.resume_hashes」一件事。
- 排序约束: 与 0448(relocate-form-aware-gates)串行, 0448 先行(D8), S0 检查。

## 实现计划

S0 前置(0448 收口检查 + 5 份 issue 认领复验, 0344 锚点改判)→ S1 结转(`_carry_prev_tag_state` 扩面改名 `_carry_prev_state`, 结转成员并进 resume_hashes)→ S2 闭账(`_DELETED_CONFIRM_TICKS = 3` + `_deleted_streak` + pending/resume_hashes 双清)→ S3 浮窗窄放行(pop.js 闸 + 中性 tone 替身, RELOCATE_TONE 不动)→ S4 stop() 摘要一行 → S5 回归收口(test.full 基线 + 5 issue 修复后补充并翻 Done)。每步验收判据见计划 §04。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 前置: 0448 收口检查 + 5 issue 认领复验(0344 锚点改判) | Open |
| S1 | 0344 job_id 复用结转 | Open |
| S2 | 0345-deleted 已删成员闭账 | Open |
| S3 | 0345-popover 终态浮窗窄放行 | Open |
| S4 | 0345-feat stop() 计数摘要 | Open |
| S5 | 回归收口 + issue 翻 Done + 基线切片 | Open |

## 进度日志

### R0 · 立档 (2026-11-15)

- grilling 两轮拍板 D1-D14(全按推荐)+ 只读取证(e2825b4b)→ 计划 26-11-15-0914 入库(Open, S0-S5 待显式开工)+ 本档案立档。
- 建件阶段零代码改动; 5 份 issue 保持 Open, 开工认领时逐份补复验行; 26-11-14 qb-side-move-echo 经 D1 排除本批(不立项)。
- 提交随本专题入库。

- 2026-11-15 09:18 grilling 两轮 14 问拍板 D1-D14 全按推荐 + 只读取证(e2825b4b: register_job 零生产调用改判 exec:1583/retries job 级 int/浮窗无旁路) + 计划 26-11-15-0914 入库(Open, S0-S5 待显式开工, 0448 先行 D8) + 档案立档; 零代码改动, 5 issue 保持 Open, qb-side-move-echo 经 D1 排除不立项
- 2026-11-15 09:41 review 两轮出口闭合: R1 检 3/3(blocker 0 / major 0 / minor 2 当场修: _member_stopped 锚改 228-238 + 计数器零读面口径收紧 / nit 1 维持现状留痕: 952d3daa 提交戳不可解析系全仓记账惯例多件沿用), R2 复评零 actionable 修复到位; 闸门键单点在提交 trailer
- 2026-11-15 09:56 S0 开工: 0448 状态确认(D8)——doc-status 仍 Open, 但 0448 的 relocate_exec 触碰面已落库(其收尾回写=2031ba16, P4 验收=9b1a248c), D8 门条件「或其触碰面已落库」成立, 本计划开工; 随即认领 5 份 issue 并逐份补复验行(0344 锚点按 D14 改判 _start_job 裸赋值 exec:1583, register_job 生产零调用已核实), 行号漂移与改判详见各 issue §07 复验行; 零代码改动
