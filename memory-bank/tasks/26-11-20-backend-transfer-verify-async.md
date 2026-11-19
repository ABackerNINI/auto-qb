# 26-11-20-backend-transfer-verify-async — transfer_run 验证等待异步化立项(目标侧整段进 daemon 线程)

**Status:** Open
**Added:** 2026-11-20
**Updated:** 2026-11-20
**Summary:** transfer_run 验证等待异步化立项: grilling 单轮 D1-D8 拍板 + 计划 26-11-20-0127 入库(Open, S1-S6 待显式开工); 零代码改动
**Topics:** backend-transfer-verify-async
**Refs:** memory-bank/plans/26-11-20-0127-plan-transfer-verify-async.html, memory-bank/issues/26-11-11-0039-perf-main-loop-blocking-candidates.html

## 本篇只回答

transfer_run(issue 0039 §06.1 行 1)的「验证等待移出主循环」如何立项: 取证、grilling 拍板(D1-D8)、计划入库与指针回写。实施另行认领开工, 本档案只记立项轮。

## 原始请求

1. 指认 issue 26-11-11-0039 §06.1 行 1「transfer_run 验证等待」为对象;
2. 「grilling 然后出一个计划」—— 单轮拍板后出正式实施计划。

## 思考过程与决策

- **取证**(基线 a14e1e20, 2026-11-20): 阻塞面 = `_cmd_transfer_run` 同步跑 `run_batch`(commands.py:194 → orchestrator.py:274), `_verify`(orchestrator.py:417-447)对目标侧 0.5s 轮询 ≤10s/种子、批内串行 N×10s 量级; 源侧读/导出走主 qB 共享 Session(qbapi.py:481/494), 删源写 store.remove_torrent(qbapi.py:202-240)——三步必须留主循环; 目标 adapter 独立 Client(adapters/qb.py:156)可进线程; 回执在 DEFERRED_RECEIPT_COMMANDS(commands_common.py:168), 前端 waitCmd 超时已随批量放大(transfer_flow.js:326)——单段终态回执契约下前端零改动。
- **grilling 单轮八问**(2026-11-20): D1 案甲(目标侧整段 add→验证→pause 进 daemon 线程, adapter 批次级独占; 拒绝 issue 原案 add 留主循环——同 adapter 两线程 Session 并发风险) / D2 生产段留主循环(残余记录在案) / D3 不设单飞单 worker FIFO / D4 退出不 join 不持久化(丢弃只丢「删」不丢「保」) / D5 **单段回执本期不变, 两段回执(即时受理+终态补发)拍板为后续阶段**——本条是唯一改判(Q5 用户改判) / D6 消费挂点=命令线尾部(consume_commands 内 drain, 删源白享 P0-5) / D7 串行 FIFO 不并行轮询 / D8 入库即 --refs 双向补链 + issue 行 1 指针 + 0306 反指。
- **计划**: memory-bank/plans/26-11-20-0127-plan-transfer-verify-async.html(Open, S1-S6 分期 + 后续阶段两段回执未排期); issue 0039 行 1 状态格与变更日志已挂指针, 旧计划 26-10-31-0306 变更记录补 R4 反指(D6「不引入线程」读法改道)。

## 实现计划

见计划 26-11-20-0127 §04: S1 orchestrator 拆分(生产/worker 侧函数, run_batch 语义不变) → S2 TransferVerifyCenter(队列/worker/drain/批次聚合 + 命令线尾部接线) → S3 命令面改造(生产段+递交+快路径) → S4 关停与告警面(stop Event/丢弃清单/日志) → S5 回归+守阵收口 → S6 回写翻 Done。两段回执为后续阶段(D5b), 不在 S1-S6 内。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 立项 | 取证 + grilling D1-D8 拍板 + 计划入库 + 指针回写 + 评审三轮零 actionable | Done(2026-11-20) |
| S1 | orchestrator 拆分(生产/worker 侧函数, 验证作业数据结构) | Open |
| S2 | TransferVerifyCenter(队列/worker/drain/批次聚合/stop Event + consume_commands 尾部接线) | Open |
| S3 | 命令面改造(_cmd_transfer_run 生产段+递交+快路径) | Open |
| S4 | 关停与告警面(stop Event 接线/丢弃清单 WARNING/生命周期日志) | Open |
| S5 | 回归+守阵收口(慢目标桩守阵/全量回归/基线切片) | Open |
| S6 | 回写与收口(issue 行 1 实施留痕/架构文档/计划翻 Done) | Open |
| 后续 | 两段回执(即时受理+终态补发, 前端 transfer_flow 配套; D5b 拍板, 未排期) | Open |

## 进度日志

### R0 · 立档 (2026-11-20)

立项轮完成: 开工同步 cd4e08af→a14e1e20→71724c83(两轮快进); 取证基线 a14e1e20; grilling 单轮八问拍板(七按推荐, Q5 改判两段回执降后续阶段); 计划 26-11-20-0127 入库(kb.new --refs 双向补链 issue 0039 与计划 0306); issue 0039 行 1 状态格/变更日志/§06.6 提示行三处指针改, 计划 0306 追加 R4 反指(kb.bump); 分批评审三轮: 轮 1 全量 2 发现(minor+nit)全修, 轮 2 复评抓出修复文本反事实(major: 删已删 hash 实为静默无操作非「源删除失败注记」+nit 条件括注)再修, 轮 3 终审零 actionable(四处待校验面全过); 轮 2 两条因先修后检引文对修复后树 REFUTE 未进 trailer 计数, 以 R2 行与本日志留痕。零代码改动, 无 test.full 轨(立项轮先例同口径)。范围外观察一件待裁决: 计划 0306 既有 doc-refs 指向 memory-bank/testing/baselines/26-10-31-0608-torrent-transfer.md 实际位于 baselines/attachments/ 下(本批之前已存在, 评审员标范围外交 scope-guard)。
