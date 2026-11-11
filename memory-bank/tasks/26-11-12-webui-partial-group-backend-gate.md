# 26-11-12-webui-partial-group-backend-gate — issue 26-11-11-0823 后端部分组闸门: delete 硬拒 + location confirm 闸(混合形态)

**Status:** In Progress
**Added:** 2026-11-12
**Updated:** 2026-11-12
**Summary:** 认领并修复 issue 26-11-11-0823: 后端部分组闸门(混合形态拍板) + 前端闸放行位 + 电池 6 条; 分面评审 3 轮 5 发现全修零 actionable
**Topics:** webui-partial-group-backend-gate
**Refs:** memory-bank/issues/26-11-11-0823-feat-webui-partial-group-backend-gate.html, memory-bank/plans/26-11-11-0820-plan-webui-partial-group-warning.html, memory-bank/testing/baselines/26-11-12-0550-webui-partial-group-backend-gate.md

## 本篇只回答

issue 26-11-11-0823(/api/torrents/bulk 直发绕过前端部分组预警)的后端闸门如何拍板、如何实现、如何验证 —— 形态选择(delete 硬拒 vs location confirm 闸)、谓词口径(与前端 D2 对账)、前端放行位一行、测试电池面。前端三落点预警的设计与实现是另一篇(计划 26-11-11-0820 / 档案 26-11-11-webui-partial-group-warning)。

## 原始请求

1. 用户: 「修复memory-bank/issues/26-11-11-0823-feat-webui-partial-group-backend-gate.html」(用户指派认领, 2026-11-12)。
2. 闸门形态拍板(AskUserQuestion, 2026-11-12): 三选项(混合/纯A/纯B)中用户选「混合:删硬拒+移确认闸 (Recommended)」。

## 思考过程与决策

- **候选 A 与已落地事实冲突(取证发现)**: issue §06 候选 A(fail-closed 硬拒, 倾向)写于 26-11-11 08:23, 早于前端 S3-S6 实施(26-11-12 入库)。两件事实使 A 不再自洽: ① D3 拍板(计划 §06)明确否决过迁移关×部分组的硬阻断(「挪一个种子单放」存在合法意图, 过硬); ② 前端 S3 确认框「确认才发」——A 会把确认后的请求必拒, S3 确认流变死胡同。
- **混合形态(用户拍板)**: delete×delete_files×部分组 = 硬拒(无合法意图, confirm 亦无保护意义); location×迁移关×部分组 = 无 confirm 拒单、confirm=true 放行(前端 S3 确认框即那道确认; 第三方显式 confirm 同径; 与整组迁移 confirm 同范式但无服务端待确认状态, 纯声明位幂等)。
- **confirm 复用安全性**: relocate_execute(confirm=True) 只跳过 CLS_CONFIRM 交互回执, blocked/部署闸/探测闸照跑 —— 旗标陈旧(前端说迁移关、后端实际武装)时前端带的 confirm 被 relocate 消费, 用户刚在 S3 框确认过同一动作, 语义已满足, 有界。
- **合流撞桩裁决(评审轮 3 期间)**: 远端 0d420c9d(键帽提示会话)与本批同文件同位置独立修了披露条电池 ensureWebFlags 桩(同一出生即红的电池) —— stash pop 零冲突但现双桩; 裁决保留远端已评审入库版(`async () => {}`, 与 e1fbd849 可 await 契约一致), 撤本批同步版。

## 实现计划

总体思路: 谓词/文案双单点 + 闸门块(minimal diff), 放行面与前端 `_partialGroupsOf` 同 D2 口径, 测试电池钉住拒收/放行/免疲三面, 分面评审闭环。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 复验锚点(三锚点全在)+ 认领链(In Progress + 复验行) | Done(2026-11-12) |
| S2 | 谓词 `_partial_groups_of` + 文案单点 `_partial_group_reject_msg` + `_cmd_bulk_torrents` 闸门块 + docstring | Done(2026-11-12) |
| S3 | 前端 drawer.js submitMoveDialog 闸放行位(`post(gated !== null)`)+ S3 node 电池断言/文档同步 | Done(2026-11-12) |
| S4 | 电池 6 条(硬拒+免疫半面/放行矩阵/双通道/聚合文案/location confirm 闸/武装态不进闸)+ dispatch 改道(平铺全组+重灌 HB)+ 无 cmd_id 矩阵第 7 类 | Done(2026-11-12) |
| S5 | 分面评审 3 轮(5 发现全修)+ 合流撞桩裁决 + test.full 全绿(数字见基线切片) | Done(2026-11-12) |
| S6 | 收尾回写(issue 翻 Done + architecture/webui.md + README 核对 + 坑档) | Done(2026-11-12) |

## 进度日志

### R0 · 立档 (2026-11-12)

认领并修复 issue 26-11-11-0823: 谓词/文案双单点 + 闸门块(commands_torrents.py)+ 前端放行位一行(drawer.js)+ 电池 6 条与守阵同步。形态经 AskUserQuestion 三选项用户拍板混合(与 D3/S3 已落地事实对齐)。机制红验双向(摘后端闸门恰 3 条闸门行为用例红; 摘前端接线 S3 电池红)。分面评审轮 1(正确性面 1 nit + 测试缺口面 1 major 2 minor 全过检全修) → 轮 2(4 修复确认在位, 新 1 nit 修) → sync 合流(远端 0d420c9d 撞同桩, 保留远端版) → 轮 3 零发现出口。test.full 全绿(数字见 kb.baseline)。提交待用户显式指令。
