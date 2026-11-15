# 26-11-15-backend-relocate-resume-account-lifecycle — relocate 恢复确认账生命周期五件联合修

**Status:** Done
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** relocate 恢复确认账生命周期五件联合修: 四笔代码提交(923ffee8/7ccc2a1b/604b52b3/9a41204d)落地 S0-S4, test.full 6193 passed / 2 skipped(148.28s, 覆盖率 99%)入基线切片 26-11-15-1318; S5 收口——5 issue 全 Done(refactor 按 D7 零改动), 评审非 blocker 入池两条(1432/1433), flux 两例既有失败复用远端 26-11-15-1359 不重复入池; 后续单独认领 1433-test 补 kept 过滤直接钉用例(红绿双验, 零产品代码改动)并翻 Done, 详见进度日志末行
**Topics:** backend-relocate-resume-account-lifecycle
**Refs:** memory-bank/plans/26-11-15-0914-plan-relocate-resume-account-lifecycle.html, memory-bank/issues/26-11-15-0344-bug-resume-account-overwrite-jobid-reuse.html, memory-bank/issues/26-11-15-0345-bug-resume-pending-deleted-member-unclosed.html, memory-bank/issues/26-11-15-0345-bug-resume-popover-terminal-job-null.html, memory-bank/issues/26-11-15-0345-feat-relocate-failure-counters-no-consumer.html, memory-bank/issues/26-11-15-0345-refactor-webui-borrow-relocate-private-constant.html, memory-bank/issues/26-11-15-1432-bug-relocate-deleted-streak-no-reset.html, memory-bank/issues/26-11-15-1433-test-resume-deleted-kept-filter-test-gap.html

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
| S0 | 前置: 0448 收口检查 + 5 issue 认领复验(0344 锚点改判) | Done |
| S1 | 0344 job_id 复用结转 | Done |
| S2 | 0345-deleted 已删成员闭账 | Done |
| S3 | 0345-popover 终态浮窗窄放行 | Done |
| S4 | 0345-feat stop() 计数摘要 | Done |
| S5 | 回归收口 + issue 翻 Done + 基线切片 | Done |

## 进度日志

### R0 · 立档 (2026-11-15)

- grilling 两轮拍板 D1-D14(全按推荐)+ 只读取证(e2825b4b)→ 计划 26-11-15-0914 入库(Open, S0-S5 待显式开工)+ 本档案立档。
- 建件阶段零代码改动; 5 份 issue 保持 Open, 开工认领时逐份补复验行; 26-11-14 qb-side-move-echo 经 D1 排除本批(不立项)。
- 提交随本专题入库。

- 2026-11-15 09:18 grilling 两轮 14 问拍板 D1-D14 全按推荐 + 只读取证(e2825b4b: register_job 零生产调用改判 exec:1583/retries job 级 int/浮窗无旁路) + 计划 26-11-15-0914 入库(Open, S0-S5 待显式开工, 0448 先行 D8) + 档案立档; 零代码改动, 5 issue 保持 Open, qb-side-move-echo 经 D1 排除不立项
- 2026-11-15 09:41 review 两轮出口闭合: R1 检 3/3(blocker 0 / major 0 / minor 2 当场修: _member_stopped 锚改 228-238 + 计数器零读面口径收紧 / nit 1 维持现状留痕: 952d3daa 提交戳不可解析系全仓记账惯例多件沿用), R2 复评零 actionable 修复到位; 闸门键单点在提交 trailer
- 2026-11-15 09:56 S0 开工: 0448 状态确认(D8)——doc-status 仍 Open, 但 0448 的 relocate_exec 触碰面已落库(其收尾回写=2031ba16, P4 验收=9b1a248c), D8 门条件「或其触碰面已落库」成立, 本计划开工; 随即认领 5 份 issue 并逐份补复验行(0344 锚点按 D14 改判 _start_job 裸赋值 exec:1583, register_job 生产零调用已核实), 行号漂移与改判详见各 issue §07 复验行; 零代码改动
- 2026-11-15 S1 落地(923ffee8 复验后续笔 7ccc2a1b): `_carry_prev_tag_state` 扩面改名 `_carry_prev_state`, 同 id 重发把 prev.resume_pending 非空余量并进新账 resume_hashes(现场在前/结转在后/去重), retries 新账天然从 0(D2)、不看 prev 终态(D3); 5 新用例全绿, S1 时点 test.quick 6184 passed / 2 skipped; 修法与验收明细落 issue 0344 修复后补充
- 2026-11-15 S2+S4 落地(604b52b3): 判据扩三态——连续 _DELETED_CONFIRM_TICKS=3 拍不在 store 判真删除闭账(_close_deleted_members 双面同删 + INFO 一行 + 收尾链重算), streak (job_id,hash) 内存态不入 state_file(R3 保守方向); stop() 追加「relocate | 停机: tag_failures=N resume_failures=M」全 0 也打(D12/D13); S2 七用例全绿(S4 两用例归口 0345-feat) + 定向 27 passed + 相邻 15 文件 426 passed, test.quick 6193 passed / 2 skipped; 明细落 issues 0345-deleted/0345-feat
- 2026-11-15 S3 落地(9a41204d): relocate_pop.js 新增 _relPopTerminalGate 谓词(state ∈ {done,cancelled} 且 relocateResumeText 非空)窄放行 + assembleRelPop 中性 tone 替身 + row_lang.css 中性色一行, RELOCATE_TONE/行内着色/抽屉零触碰(D11); 新 e2e 3 判据 2 皮肤 passed(Windows 真浏览器复跑 3 次稳), test.quick 6193 passed / 2 skipped; 明细落 issue 0345-popover
- 2026-11-15 S5 回归收口: test.full 6193 passed / 2 skipped(148.28s, 覆盖率 99%: 27477 stmts / 73 miss)入基线切片 26-11-15-1318-relocate-resume-account-lifecycle; 定向 relocate 面 352 passed。本机无 docker, test.linux-env STOP, Linux 容器 e2e(pytest/e2e/变异)未跑——替代面改 Windows 侧 dev.e2e 全量 610 passed / 6 failed / 22 skipped, relocate 面全绿(新 spec relocate-pop-terminal 2 皮肤 passed); 6 败中 4 例瞬态(search-refresh 合成种子跨 spec 串扰, 隔离复跑 39 passed 全绿), 2 例既有失败(flux-cat-chip-hr-semantics 双 chip strict mode / flux-site-chip-shape-glow 辉光)经基座 46649c3f 临时 worktree 复现取证为存量、非本批引入——远端 origin/develop 已有 26-11-15-1359-test-flux-chip-e2e-failures 覆盖该两例(干净 HEAD 差分同结论), 不重复入池。S2 批次评审(T3)两条非 blocker 用户拍板入池: F1 = 26-11-15-1432-bug(_deleted_streak 进程内不随账重开清零, 账重开×快照空窗窄窗提前 1-2 拍闭账, 后果有界; 建议修法 _start_job 落账处或 _load_jobs 按 job 清)、F4 = 26-11-15-1433-test(resume_hashes 非 pending 已删成员不清理的 kept 过滤保证无用例直接钉, 低价值覆盖面候选)。D7 复核: _RESUME_RETRY_MAX 外部借用仍唯 views_relocate.py:14 一处, _DELETED_CONFIRM_TICKS 无配置化无第二消费方, refactor 便签「维持现状零改动 + 触发条件(穷尽口径出现第二消费方才升 relocate 公共面)」结案。五份 issue 逐份补「修复后补充」(实际修法 + 提交 hash + 验证数字)后 kb.status 翻 Done; 计划 26-11-15-0914 doc-status Done + §10 R1 行; 计划外零代码改动(本记录为文档/issue 回写面)

- 2026-11-15 15:47 修复 issue 26-11-15-1433: 补一条闭账 kept 过滤直接钉用例（resume_hashes 非 pending 成员闭账后保留）并登记主测试计划清单, 两种源码变异红绿双验, 零产品代码改动; 闸门预跑与全量全绿（见 kb.baseline）, 评审一轮零 actionable; issue 补修复后补充并翻 Done
