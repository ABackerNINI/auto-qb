# 26-11-07-memory-bank-issue-fusion — create-issue 融合 memory-bank(代码融合+双 SKILL)与 issue 工位机械化

**Status:** In Progress
**Added:** 2026-11-07
**Updated:** 2026-11-07
**Summary:** create-issue 融合 memory-bank(代码融合+双 SKILL)与 issue 工位机械化
**Topics:** memory-bank-issue-fusion
**Refs:** memory-bank/plans/26-11-07-0549-plan-memory-bank-issue-fusion.html

## 本篇只回答

本专题 W1-W5 五波实施的执行状态与验证数字记在哪、做到哪。方案与拍板结论的单点在计划(见 `**Refs:**`), 本档案不重写方案 —— 方案改了改计划, 状态变了改这里。

## 原始请求

1. 「create-issue与memory-bank深度绑定, 要不要融合进memory-bank skill中」
2. 「参考memory-bank的新文档模板为create-issue添加模板」
3. 「grilling然后出一个计划」

## 思考过程与决策

grilling 三轮十问逐项拍板(D1-D10, 2026-11-07), 结论与取舍单点在计划 §03/§06。要害一条: **融合只到代码层, 双 SKILL 保触发界限** —— SKILL.md 不合并(用户点名的约束: 合并后过长、触发界限模糊), create-issue 保留独立触发面, 只有 scripts/assets/常量物理并入 memory-bank skill。翻案记录: 26-10-17-0527 D2「issues 不入列」正式翻案为 `kb.new issue` 族(当时跨 skill import 无解, 融合后自动消失)。

## 实现计划

五波 W1-W5(内容与验收判据单点在计划 §04): W1 代码融合(纯机械, 行为零变化) → W2 模板翻新(单栏+@@ 占位符) → W3 建件收编(kb.new issue 族, new_issue.py 退役) → W4 翻状态收编(kb.status issue 分支) → W5 回写收口(文档表/SKILL.md 改写/全绿+基线切片)。顺序即依赖序, 每波结束可提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| W1 | 代码融合: scripts/assets 搬移+常量单点化+引用面改指+钉住测试删除 | Done (2026-11-07) |
| W2 | 模板翻新: issue 双模板单栏化+占位符统一 @@ | Done (2026-11-07) |
| W3 | 建件收编: kb.new issue 族+new_issue.py 退役+测试改靶 | Done (2026-11-07) |
| W4 | 翻状态收编: flip_status issue 分支(两处一改+日志行+索引) | Done (2026-11-07) |
| W5 | 回写收口: doc-forms/README/SKILL.md 改写+kb.check+test.full 全绿+基线切片 | Done (2026-11-07) |
| 评审 | 三批评审+接缝终审 0 blocker, 13 发现全修, 终态基线 26-11-07-0827 | Done (2026-11-07) |

## 进度日志

### R0 · 立档 (2026-11-07)

立档轮: 开工同步 cd809913→ac07166b; 摸清现状(双 _common/3 条钉住测试/闸门 toml 直指 create-issue/flip_status 拒收 issue/模板 10-05 vs 11-06 分叉); grilling 三轮十问逐项拍板; 计划 26-11-07-0549 入库(状态 Open, 十项拍板已录 §06); 本轮零代码改动, 实施等显式开工。

- 2026-11-07 05:53 grilling 三轮十问逐项拍板成案(D1-D10), 计划 26-11-07-0549 入库(Open); 代码融合+双 SKILL/kb.new issue 收编/kb.status 收 issue/模板统一/存量豁免; 五波 W1-W5 等显式开工, 本轮零代码改动

- 2026-11-07 08:28 五波 W1-W5 实施+四批评审落地: 0 blocker, 13 发现(RB1 5/RB2 4/RB3 1 弃/终审 3)全修; 终态基线 26-11-07-0827(全绿, 见 kb.baseline); 计划翻 Done, 随本专题入库
