# 26-10-31-webui-write-side — 修复 reannounce 确认跟踪对在途 tracker 过早落 ok(issue 26-10-31-1740)

**Status:** In Progress
**Added:** 2026-10-31
**Updated:** 2026-11-01
**Summary:** 修复 reannounce 确认跟踪对在途 tracker 过早落 ok(issue 26-10-31-1740)
**Topics:** webui-write-side
**Refs:** memory-bank/issues/26-10-31-1740-bug-webui-reannounce-premature-confirm.html, memory-bank/testing/baselines/26-11-01-0025-webui-write-side.md

## 原始请求

1. 认领 `memory-bank/issues/26-10-31-1740-bug-webui-reannounce-premature-confirm.html`（已置 In Progress，复验 2026-10-31 23:42：`real.run` RM09-04 skip，真机未运行未现场复现，锚点代码分支②确认仍在）；
2. issue §6 建议修法（固定宽限拍 ~2s）代价过高（可达 tracker 成功回执慢一拍、不跟手），要求优先其它方式；
3. qB 与 libtorrent 源码在 `C:\Users\11059\Desktop\Projects\Else` 可供分析（只读）；
4. grilling 一个修复方案（round 1 D1–D5、round 2 D6–D7，各题均「按推荐」拍板）；
5. 拍板后落盘：出修复计划 + 建本档案认领，计划批准前不动代码。

## 思考过程与决策

grilling 设计树收敛为「消解等待模型」：updating 在请求发出前置位（libtorrent `torrent.cpp:3571`），对成败零信息量，故②全域废除（D2/D3）；成功正证据 = working 转换（③″，D6）与 epoch 前跳（③ 不变，域仍限基线 status≥2）；失败证据 = status∈{4,5,6}+msg（④' 扩，D7）逐行先判；回执时延 = RTT+≤1 tick，零固定宽限（D1/D4）。源码事实关键两条：失败退避也前跳 next（④先行不可动）、min_announce 发送时即赋值（「min 从无到有」不作成功信号）。计划：`memory-bank/plans/26-10-31-2354-plan-webui-write-side.html`（D1–D7 拍板表在其 §06）。

## 实现计划

总体思路：按计划 §04 五步走（判定函数改造 → 单测面 → 真机 RM09-04 → 回写坑档/主题文档 → test.full 基线收尾），每步验收判据见计划对应条目；本档案只滚动执行态。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 判定函数改造（消解等待模型，D1–D3/D6–D7） | Done(2026-11-01) |
| 2 | 单测面重写+新增（语义翻转记理由，docstring 同步） | Done(2026-11-01) |
| 3 | 真机 RM09-04 转绿（需用户起 qB；四态全验+RM09 整片 10/10） | Done(2026-11-01) |
| 4 | 回写 effect-confirmation.md（复发+1）与主题文档 | Done(2026-11-01) |
| 5 | test.full 实测 + 基线切片 + kb.wrap 收尾 | Done(2026-11-01) |

## 进度日志

### R0 · 立档 (2026-10-31)

立档于 grilling 收敛后：issue 已认领（In Progress）、计划已出（`plans/26-10-31-2354-plan-webui-write-side.html`）、认领链双向已补（issue doc-refs = 计划+本档案）。本轮未动任何代码——待用户批准计划后开工步 1。

- 2026-11-01 00:26 修复完成: _verdict_reannounce 消解等待模型(②废除/③″新增/④′扩{4,5,6}), 单测矩阵语义重写, 真机 RM09-04 四态全验+RM09 整片 10/10, test.full 4327 passed(基线切片 26-11-01-0025); 回写 effect-confirmation(复发+1)/real-machine §2.14/issue Done
