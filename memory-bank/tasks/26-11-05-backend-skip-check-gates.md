# 26-11-05-backend-skip-check-gates — 跳检 dedup 闸门遮蔽修复(26-10-11-2045)

**Status:** In Progress
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** 跳检 dedup 闸门被 G3 结构性遮蔽(同日重跳恒返 fail「已完成」而非 skip「今日已跳检过」); 修复 = dedup 判定块前移到 G3/G4 之前, 谓词文案零变化; 已收口
**Topics:** backend-skip-check-gates
**Refs:** memory-bank/plans/26-11-04-2357-plan-skip-check-gates.html

## 原始请求

1. 「认领memory-bank/issues/26-10-11-2045-bug-ops-skipcheck-dedup-shadowed-by-g3.html, 出一个修复计划并对改计划grilling」
2. grilling 第一轮四问后用户答「按推荐」(D0 方案1 / D1 规则侧入池不修 / D2 dedup 放最前 / D3 记坑档) = 批准实施

## 思考过程与决策

- 计划文档: `memory-bank/plans/26-11-04-2357-plan-skip-check-gates.html`(拍板 D0-D3 结论见其 §06)
- 复验发现锚点漂移(ops_mod.py → ops_verdict.py move-only), 现象仍复现; 另发现规则侧链 0 同构遮蔽(checking.py:100 先于 ops 闸门), 拍板独立入池(26-11-05-0019)不顺手修
- grilling 期间补核事实: 规则源保真下到不了 ops 闸门; 规则引擎 skip/fail 分派异径(fail 走 on_error 三档) —— 佐证 skip 类别恢复不只是文案问题
- 收口评审(分面档, 2 子代理): blocker 清零, 修 1(补预检 dedup 回归钉 test_ops_recheck.py HDUP 样本), 入池 0

## 实现计划

1. ops_verdict.py dedup 判定块前移(G3/G4 之前) + 顺序注释/docstring 同步 — 验收: 注释与实际追加顺序一致
2. test_ops_skip.py 撤 progress 绕行恢复保真链 — 验收: 用例绿(修复前必红)
3. test_checking_skip.py 保留绕行、注释改指新 issue — 验收: 注释与 D1 拍板一致
4. test.full 全量 + 基线切片 — 验收: 无用例转红, 切片落盘
5. D1 入池 + D3 坑档 + issue 翻 Done — 验收: 索引/认领链机检过

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | ops_verdict.py dedup 前移 + 注释同步 | Done(2026-11-05) |
| 2 | test_ops_skip.py 撤绕行保真链 | Done(2026-11-05) |
| 3 | test_checking_skip.py 注释改指 26-11-05-0019 | Done(2026-11-05) |
| 4 | test.full 全量绿 + 基线切片 26-11-05-0023(见 kb.baseline) | Done(2026-11-05) |
| 5 | issue 26-11-05-0019 入池 + 坑档 gate-order-reachability + 2045 翻 Done | Done(2026-11-05) |
| 6 | 收口评审(分面) blocker 清零 + 预检回归钉补测 | Done(2026-11-05) |

## 进度日志

### R0 · 立档 (2026-11-05)

- 认领 → 复验(仍复现, 锚点漂移已更新) → 计划 26-11-04-2357 + grilling 拍板 → 实施全部 6 步完成; 实测全量绿(数字见 kb.baseline 26-11-05-0023); review: blocker 清零, 修 1, 入池 0(分面档)

- 2026-11-05 00:43 dedup 前移修复收口: 拍板 D0-D3 + 实施 6 步 + test.full 全量绿(见 kb.baseline); review blocker 清零修 1; 2045 翻 Done, 规则侧 26-11-05-0019 入池, 坑档 gate-order-reachability
