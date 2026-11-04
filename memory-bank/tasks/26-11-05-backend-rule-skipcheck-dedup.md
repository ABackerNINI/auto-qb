# 26-11-05-backend-rule-skipcheck-dedup — 规则侧链0遮蔽跳检dedup修复(26-11-05-0019)

**Status:** Done
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** 规则侧决策链 0 遮蔽 ops dedup 闸门(26-11-05-0019, 与 ops 侧 26-10-11-2045 同构): 修复 = dedup 查表前插链 0 之前, 谓词单点化 ops 只读 helper skip_checked_today; 撤测试绕行并纠正「绕行是空操作」的取证误读; 全量 5211 绿(见 kb.baseline), 收口评审 blocker 清零修 2
**Topics:** backend-rule-skipcheck-dedup
**Refs:** memory-bank/issues/26-11-05-0019-bug-rule-chain0-shadows-skipcheck-dedup.html,memory-bank/plans/26-11-04-2357-plan-skip-check-gates.html,memory-bank/pitfalls/backend/gate-order-reachability.md

## 原始请求

1. 「认领并修复memory-bank/issues/26-11-05-0019-bug-rule-chain0-shadows-skipcheck-dedup.html」(用户指令, 构成指派认领)

## 思考过程与决策

- issue §06 二选一未拍板(「等 ops 侧修复后的实际观察再定」); 用户指令「认领并修复」即拍板走方案 1(链 0 前插 dedup 查表)—— 方案 2「接受遮蔽」非修复, 与指令不符
- 前置闸门顺序沿用 ops 侧先例(26-10-11-2045): dedup 排最前 —— 谓词一次 dict 查询全链最便宜, 且只读 ops state 不碰 qB 快照, 不属 S2 让位闸门防的「陈旧状态出决策」面, 排在 dry-run 后、S2 deferral 闸门前
- 跨层边界(规则层读 ops state 表)收敛: 谓词单点化为 ops 侧只读 helper `skip_checked_today(hash)`, `_skip_gates_detail` 的 dedup 闸门与规则侧同源消费(防两套谓词漂移, T18 思路); 规则层不触 dict 内部
- **取证纠正**: issue 证据 C 称测试「依赖 progress 绕行」才能到去重闸门 —— 实测红验发现 `t.progress = 0.0` 是**空操作**(替身默认就是 0.0, 跳检流程不改写 t), 旧用例从未复现真机遮蔽链路(pausedDL 直达 ops dedup)。修复后用例显式置 `progress=1.0` 还真机「跳检成功 ⇒ 已完成」现场, 红验确认旧码下恒被链 0 以「非暂停中未完成」拦下
- 修复影响面: dedup 前插只改写文案归因(行为恒 skip), 对 full-checking 同日重请求的文案从「无需校验」变「今日已跳检过」—— 语义等价且更自解释(跳检成功 ⇒ 数据已验证)。**边缘行为变化**(评审 minor #2 如实补记): 当日跳检成功后种子被删并同日重加(progress 归 0 且暂停)时, full-checking 旧码会走到 recheck、新码被 dedup 拦下 —— 是行为收窄而非纯文案改写; 方向保守(当日数据已被跳检判定有效, recheck 无收益)且次日自愈, 并与 ops 侧跳检闸门 dedup-first 口径一致; WEB recheck 路径无 dedup, 两侧在此边缘上不对称, 接受

## 实现计划

1. ops_verdict.py 加只读 helper `skip_checked_today`, `_skip_gates_detail` dedup 闸门改同源消费 — 验收: ops 侧测试全绿(谓词零变化)
2. checking.py 决策链 dedup 前插(dry-run 后、S2 deferral 前) + docstring/注释回写 — 验收: 保真用例绿(修复前必红)
3. test_checking_skip.py test_checking_skip_dedup_across_rules 撤绕行改保真现场(progress=1.0) — 验收: 红验(旧码红: 恒返「非暂停中未完成」)+ 新码绿
4. test.full 全量 + 基线切片 — 验收: 无用例转红, 切片落盘
5. issue 翻 Done + 修复后补充 + 认领链闭环 + kb.wrap — 验收: 索引/认领链机检过

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | ops_verdict.py skip_checked_today 谓词单点 | Done(2026-11-05) |
| 2 | checking.py dedup 前插 + 注释/docstring 回写 | Done(2026-11-05) |
| 3 | 保真用例改写 + 红验 | Done(2026-11-05) |
| 4 | test.full 全量 + 基线切片 | Done(2026-11-05) |
| 5 | issue 翻 Done + 认领链 + kb.wrap | Done(2026-11-05) |

## 进度日志

### R0 · 立档 (2026-11-05)

- 认领 → 复验(证据 A/B/C 锚点逐一重跑仍复现) → 实施步骤 1-3: 红验实测旧码下规则 B 恒返「种子非暂停中未完成状态, 无需校验」, 新码下保真现场(progress=1)返「今日已跳检过该种子(跨规则去重)」; 相关三文件 84 用例全绿
- 取证纠正: issue 证据 C 的「progress 绕行」实为空操作, 旧用例从未复现真机遮蔽链路; 已在用例注释与 issue 修复后补充中留痕
- 全量 5211 passed / 10 skipped / 0 failed(见 kb.baseline 26-11-05-0212); 收口评审(全能档, 1 只读子代理): blocker 清零, 修 2(ops_verdict 四处行号互指改符号锚; 档案补记 full-checking 边缘行为收窄+代码注释写明覆盖面), 入池 0; findings 引文 review.check 2/2 通过
- 插入实施时一次中间态误删 S2 deferral 闸门本体(仅剩注释), test_checking_single 当轮全量抓住, 已还原 —— 相关面单文件 test.one 不够, 全量兜底必要性的现成例证

- 2026-11-05 02:15 规则侧链0遮蔽跳检dedup修复收口(26-11-05-0019): 前插+谓词单点+保真用例红验; 全量5211绿切片26-11-05-0212; 评审blocker清零修2
