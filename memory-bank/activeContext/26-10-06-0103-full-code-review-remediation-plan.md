# Code Review 发现分批修复计划成文 (full-code-review-remediation-plan)

> 摘要: 依据报告 [26-10-05-1036](../reports/26-10-05-1036-report-full-code-review.html) §3.2 分流结果, 新建实施计划 [26-10-06-0103](../plans/26-10-06-0103-plan-full-code-review-remediation.html) (doc-status **Open**): 28 条入池 issue 组织为六批 —— S1 P1×3(D-01/G-01/H-01, 逐条提交) · S2 P2 后端×6(A-01/B2-01/C-01/D-02/H-02/H-03) · S3 竞态回执族×4(E-01/F1-01/E-03/F2-03) · S4 chore×6+顺手 docstring×2(A-08/H-04) · S5 refactor×6(A-03/A-04/A-07/B2-02/C-04/E-04) · S6 小修×3(B2-04/G-03/G-06); 另设 S0 开工重立 test.full 基线(评审基线 2610+4 是 a4d14a8d 时点, 不可沿用)。**7 处拍板点**(P-01…P-07)各带推荐案, 其中报告遗留的 HrStoreCorrupted(P-02)建议随 S2 的 B2-01 一并定。并池备注×3 与仅记录×17 列入非目标。认领链闭环: 报告 doc-refs 补本计划反向引用 + doc-updated → 26-10-06-0103(仅 meta 机械面, 内容未动); kb.index 重建绿; test.full **2622 passed + 4 skipped / 99%**(166/139) 全绿。
> 最后活动: 2026-10-06 01:03

**Refs:** memory-bank/plans/26-10-06-0103-plan-full-code-review-remediation.html, memory-bank/reports/26-10-05-1036-report-full-code-review.html, memory-bank/issues/_index.md
