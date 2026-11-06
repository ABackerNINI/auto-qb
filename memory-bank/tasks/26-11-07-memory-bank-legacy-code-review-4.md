# 26-11-07-memory-bank-legacy-code-review-4 — 存量代码全库评审 R4: 五路线并行体系化

**Status:** Done
**Added:** 2026-11-07
**Updated:** 2026-11-07
**Summary:** 存量评审 R4 收口档案: review.lane 机制 S0 落地 + 五路线并行 34 批全 done, findings 475→473(机械合并 2, blocker 0), major+minor 285 行按主题入 6 份 issue(全 Open), 终报告 26-11-07-0545 入库; 零代码改动纯盘点, 发现处置在 issue 侧。
**Topics:** legacy-code-review-4
**Refs:** memory-bank/plans/26-11-05-2335-plan-legacy-code-review-4.html, memory-bank/reports/26-11-07-0545-report-legacy-code-review-4.html

## 本篇只回答

存量代码第 4 轮全库评审 R4 怎么组织、怎么执行、结果数字如何 —— 计划/执行/聚合/收口四段的决策与数字单点在本篇; 逐条发现的处置答案在 6 份 issue 侧, 本档案不复述。

## 原始请求

1. 「对当前全库生产代码做第 4 轮存量评审——参照 code-review skill 的评审包/引文校验/分级处置方法论做存量适配,切成 5 条可认领并行的路线 × 30 批,全局单冻结 hash 快照评审,纯盘点零代码改动,发现聚合入池」(2026-11-05 grilling 三轮 16 问拍板定稿, 用户改判 3 处: 多路并行 / 全局单 hash / 脚本定死基线; 转述自计划 lede)
2. 执行期追加指令(摘): 冻结基线改钉 manifest 生成时点的 develop tip(D17, 26-11-06); S0 收口补评审与两轮增量评审(26-11-06); S7 收口按 memory-bank skill 会话收尾 DoD 执行(26-11-07, 本轮)。

## 思考过程与决策

- 方法论基座 = code-review skill(批次评审 / `review.check` 引文逐字校验 / 分级处置), 存量语境改两点: 评审对象是 `git archive` 快照不是 diff; 「完成判据」(批次全覆盖/引文全验/处置完毕/终报告入库)取代「收口 blocker 清零」(计划 §01)。拍板全录计划 §06 D1-D17, 关键: D4 入池按模块主题聚合不逐条开; D5 static 只评契约/机制面; D7 多路并行、单路内串行(用户改案); D12 全局单冻结 hash(用户改判); D13 脚本定死 commit 防错评; D14 认领/状态单点全在 JSON、计划 HTML 静态零手改; D16 计划只写状态不写流水; D17 冻结改钉 manifest 生成时点 develop tip(26-11-06 改判, 认领后拒重生成)。
- 执行模型: 三 clone 协同 —— R1=clone1-main, R2/R3/R4=clone2-main, R5=clone3-main; 认领与批次状态单点 = `memory-bank/reports/attachments/legacy-review4/route-<R>.json`; 每批 verify→派遣只读 reviewer→`review.check`→复核→勾选; 全局单冻结 f0883292, develop 分支零扰动。
- 盘点数据落盘的评审口径: 路线批次提交一律带 `Review-Skip: 纯盘点数据落盘, 零代码改动(评审产物本身非被评代码)`(b8285a31 / 9359e3c2 / b54a1fd2 / 4da13dd2 实例)—— 评审产物是任务自身产出, 不再作为被评对象; S0 机制面则单独走了三轮评审(19+5+3 条全修, blocker 恒零), 与盘点面分开记账。

## 实现计划

单点 = [26-11-05-2335-plan-legacy-code-review-4.html](../plans/26-11-05-2335-plan-legacy-code-review-4.html) §04 步骤表 + §05 执行协议。链路: S0 review.lane 命令 + manifest(冻结 f0883292) → S1-S5 五路线 34 批 → S6 聚合(跨路线去重 / 主题入池 / 终报告) → S7 收口(本档案)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | review.lane 七子命令 + manifest(366 文件恰被 34 批认领 116,044 行, 冻结 f0883292) + 三轮评审全修 | Done(2026-11-06, clone1) |
| S1-S5 | R1-R5 五路线 34 批全 done, findings 合计 475 | Done(2026-11-06~07, 三 clone) |
| S6 | 聚合: 去重 475→473 + major+minor 285 行入 6 issue + 终报告入库 | Done(2026-11-07) |
| S7 | 收口: 立档 / progress 回写 / 切片 R4 / 计划翻转 Done | Done(2026-11-07, 本轮) |

## 产出物与发现处置

- 终报告: [26-11-07-0545-report-legacy-code-review-4.html](../reports/26-11-07-0545-report-legacy-code-review-4.html) —— 守恒式 473+2+0=475、批次地图实测回填、R2 底册 19 项复验(17 已消失 / A-03 复发但风险已收敛 / GH-01 部分复发)、nit 189 条全量清单、方法论注记(幻觉引文 1 条被 `review.check` 弃)。
- 6 份 issue(全 Open, doc-topic `legacy-review4`, 按约定不进本档案 doc-refs, 认领链由 issue 侧自持): memory-bank/issues/26-11-07-0527-bug-legacy-review4-core.html, memory-bank/issues/26-11-07-0527-bug-legacy-review4-config-infra.html, memory-bank/issues/26-11-07-0527-bug-legacy-review4-hr.html, memory-bank/issues/26-11-07-0536-bug-legacy-review4-webui-py.html, memory-bank/issues/26-11-07-0536-bug-legacy-review4-static.html, memory-bank/issues/26-11-07-0536-bug-legacy-review4-scripts.html —— 共 285 行(含 1 条拆回 R1#81)。
- 聚合数据面: memory-bank/reports/attachments/legacy-review4/aggregate.json(路线×severity 矩阵 / 守恒自检 / theme 映射单点)。

## 进度日志

### R0 · 立档 (2026-11-07)

S7 收口轮建本档案: 立档判定命中阈值 1/3/4(跨 2 日 3 clone / 计划与批次表述 / 已产出计划+报告制品); progress 回写 implemented-tooling; 切片 R4 行; 计划 doc-status 翻 Done。测试与基线判定: 零代码改动(纯盘点, 报告 §08 自证)—— 不跑 test.full、不建基线切片; code-review 批次判定 = 免评(纯盘点数据落盘 + 记账面, 同批次 `Review-Skip` 先例)。遗留: 6 份 issue 待认领处置, A-03 建议后续轮复核原报主张(报告 §08)。

- 2026-11-07 06:15 S7 收口完成: 立档(tasks/26-11-07-memory-bank-legacy-code-review-4.md, 阈值 1/3/4 命中) / progress 回写 implemented-tooling / 计划 doc-status 翻 Done(R1 行); 五路线 34 批全 done, findings 475→473(机械合并 2, blocker 0), major+minor 285 行入 6 份 issue(全 Open), 终报告 26-11-07-0545 入库; 评审判免评(纯盘点数据落盘+记账面, 同批次 Review-Skip 先例), 零代码改动不跑 test.full 不建基线
