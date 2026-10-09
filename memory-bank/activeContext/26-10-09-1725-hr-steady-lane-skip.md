# HR 稳态期跳过 B/C 档取数可行性

> 摘要: 用户命题「HR 在线核实稳态时 B/C 页是否不用访问, 只访问 A 页」→「写成报告」。产出可行性报告 `reports/26-10-09-1725-report-hr-steady-lane-skip.html`。**结论: 不建议** —— A 档确是新增义务的唯一入口, 但 B/C 在 v3 里是覆盖证明的一部分(观察期出口 / 批量签发 / 终态退役)与超额种子转档的唯一见证; 砍掉只省每天 2 个请求, 却换来一处真实判定回归(超额种子 A→B/C 迁移失明 ⇒ 陈旧「受管束」)+ 两处结构副作用, 并与 v3「每波自证覆盖」冲突。**零 `src/` / `tests/` 改动**; 若要推进须另立计划(报告 §08)。
> 最后活动: 2026-10-09 17:25

## 状态

- 已完成: 报告产出并入库(`reports/_index.md` 重建); 本档案 + 本切片 + 基线切片; `kb.index` / `kb.check` 全绿。
- 未做: 无代码改动; 未拍板「是否入池 issue」与「是否立项」。
- 下一步(待用户拍板): ①要不要把该方向入池 issue; ②若推进, 先定报告 §08 的两条口径 —— 稳态定义是否收紧为「无本地种子在 A」(把超额种子纳入, 注意这会**增加**请求, 与动议目标相反); `_position_covered` / `_absence_proven_all` 的「全档」是否改「参与档」。

## 关键结论(便于下次直取)

- 稳态语义单点: `service.py:503` `steady = anchors_known and not objects` —— 只等价「对账对象集为空」, 不等于「本地无义务」。
- 唯一硬伤: 超额线(`service.py:1428`, ≥3× 要求)种子被排除出对象集 ⇒ 本地种子在 A 时仍判稳态 ⇒ A→B/C 迁移只能靠 B/C 页发现。
- 五处 B/C 消费点: `_freeze_terminal` / `_position_covered` / `_absence_proven_all` / `_retention_check` / 判定表行 2; 前三者硬遍历 `FETCH_LANES`。

**Refs:** memory-bank/reports/26-10-09-1725-report-hr-steady-lane-skip.html,memory-bank/tasks/26-10-09-backend-hr-steady-lane-skip.md,memory-bank/testing/baselines/26-10-09-1725-hr-steady-lane-skip.md
