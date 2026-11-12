# 26-11-13-memory-bank-active-context-cleanup — active-context 切片债务清理与保留带口径落地

**Status:** Done
**Added:** 2026-11-13
**Updated:** 2026-11-13
**Summary:** active-context 债务清理(150>=120 触顶): 第一轮按「全删 closed」裁到 11 条被用户 revert 重定调, 口径改保留带 [60,80](单点常量+守卫测试钉桩), 第二轮 11 pending + 64 最近 closed = 75 条落地; 顺带修 2 处共享戳误报分类 + 坑档 env3-test-run-prereqs 复发+1
**Topics:** memory-bank-active-context-cleanup

**Refs:** memory-bank/pitfalls/testing/env3-test-run-prereqs.md

## 本篇只回答

active-context 切片债务(条数触顶)的一次性清理按什么判据裁留删、保留带口径 [60,80] 怎么落到机器单点, 以及为什么第一轮「全删 closed」的裁法被推翻。

## 原始请求

1. 「清理 kb.active」—— kb.active 页脚 `[债务]` 行(150 条 >= 上限 120)触发的一次性清理会话。
2. 「revert through git. keep at least 60 so that agents can know what we are doing recently, change the skill (目标 ≤80,一次降到位) to (60<=目标 ≤80,一次降到位)」—— 第一轮结果被 git restore 整体回退, 口径改保留带。
3. 「commit」—— 收尾入库。

## 思考过程与决策

- **留删判据(两轮共用)**: 专题还有没做完的事 → 必留(计划 Open/In Progress、待用户侧动作且无处另记、关联 Open issue); 全闭环 → 删, 记录归任务档案/issue/计划/坑档/基线与 git 冷库。每条切片逐一判定, 不按时间刀切 pending。
- **状态判定以 meta 机读为准**(plan `doc-status` / issue `issue-status`), 不信切片摘要 —— 抓出 6 条「摘要还写 Open、实际次日已实施翻 Done」的陈旧快照(group-hash-ref、partial-group-warning、listing-false-negative、bt-backup 等)。**共享戳误报 2 处**: 26-09-21-1408 批量建档日里 mypy 母 issue Done 而 version-dual-source 仍活; 26-10-05-0922 批里 hr-fetch-gating 清偿的是 fetchable-dead-config 而非同批 Open 的 hr-prune-notice —— 均按母 issue 裁 closed。
- **第一轮裁法(删 139 留 11)被 revert 的根因**: active-context 的职能是「最近在做什么」的滚动状态面, 全删 closed 连近期完成记录也清掉了, agent 扫目录时丢上下文; 用户的保底 60 就是给这条面上限。**教训: 一次性清理的裁法要先对齐「保留带」再动手, 「目标 ≤80」是上限语义, 不含下限。**
- **口径改带落点**: 单点常量 `SLICE_COUNT_TARGET_MIN = 60`(`_common.py`, 与 `SLICE_COUNT_LIMIT=120`/`SLICE_COUNT_TARGET=80` 同点), 债务文案改「蒸馏到 60<=目标<=80 (一次降到位…)不足下限时停止删除」, 守卫测试 `test_kb_slice_count_limit_warns_at_120_and_targets_band` 钉 (120, 60, 80) 三元组 + 文案含 60/80。
- **第二轮落点 75**(带内中位): 11 pending + 64 条最近 closed(按「最后活动」倒序取到 26-11-07 12:46 为界), 删 75 条最老 closed(26-11-04~11-07 段)。删除集逐名落盘, 不用通配。
- 反链核查: 全库仅 1 处声明引用指向切片(archive Refs), 第一轮修过、revert 后该切片落在保留带内, 引用自然闭合; 其余反链均为正文提及(历史文档一行不改)。

## 实现计划

总体思路(无计划文档): 盘点脚本(slug↔档案模糊匹配 + 戳号反查 meta 状态 + 全库反链扫描)→ 逐条裁决 pending/closed → 删除 → kb.check/kb.active 验证 → 口径改带(常量/文案/守卫测试)→ revert 后按新口径重清理 → test.one/test.quick 验证。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 第一轮清理(150→11, 删 139) | Done(2026-11-13, 经 git restore 回退) |
| S2 | 保留带口径 [60,80] 落机器单点+守卫测试 | Done(2026-11-13) |
| S3 | 第二轮清理 150→75(11 pending + 64 最近 closed) | Done(2026-11-13) |
| S4 | 验证: kb.check 全绿 + test.quick 全绿(见 kb.baseline) + kb.active 75 条在带内 | Done(2026-11-13) |

## 进度日志

### R0 · 立档 (2026-11-13)

- 债务触发: kb.active 页脚 `[债务]`(150 条 >= 120); 两轮清理 + 口径改带落地, 终态 75 条在 [60,80] 带内, 债务行消失。
- 踩已记坑 `env3-test-run-prereqs` 一次(复发+1 已记): 收尾闸门轮非交互 shell 缺 node PATH 与 TZ, r4 电池 70 条环境态假红 + TZ 敏感 1 红; **为什么没命中**: 任务面看着纯文档, 开工路由没进 testing 类 pitfalls —— 教训已写进坑档(闸门/测试轮同在触发面内)。
- 改动面: 3 个源文件(常量/文案/守卫测试)+ 75 条切片删除(记账类); 评审与基线数字见本档案进度日志后行与 kb.baseline。

- 2026-11-13 06:30 第二轮清理落地: 150→75(11 pending + 64 最近 closed, 删 75 条最老 closed); 保留带口径 [60,80] 落机器单点(SLICE_COUNT_TARGET_MIN=60)+债务文案+守卫测试钉 (120,60,80); 评审 2 轮(轮1 2 发现全修: collaboration/cap-counting 旧口径两处同步, 轮2 零 actionable), 检 2/2 修 2 入池 0; 坑档 env3-test-run-prereqs 复发+1(收尾闸门轮非交互 shell 双症踩中, 为什么没命中已记坑档); test.full 全绿(见 kb.baseline); 同步远端两轮(7a55e289→58d443a8)与本批零交集
