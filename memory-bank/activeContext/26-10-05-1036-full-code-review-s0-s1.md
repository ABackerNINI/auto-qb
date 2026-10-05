# 全面 Code Review S0(准备+底册) + S1(批次地图) (full-code-review-s0-s1)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 的 S0 与 S1 完成, 计划状态 Open → In Progress; D1–D5 用户已逐项拍板「按推荐」。S0: sync 成功, 实测起点 HEAD **a4d14a8d**(成文时 ef93db56; 其间他人提交 = v3 S6 活尾合流 / HR 稳态降频 / test.one 覆盖率闸 / 危险动作防护, 故基线漂移); test.full 实测 **2610 passed + 4 skipped / 99%**(计划原载 2581+4/98%, +29 passed 全来自他人提交, 与评审无关), 基线切片 [26-10-05-1034](../testing/baselines/26-10-05-1034-full-code-review-s0-baseline.md)。已知问题底册四表落报告附录: ①issues 池 Open 实测 **37 条**(计划载 38: 0922 chore/docs 两条已修毕转 Done, 新增 feat 1015 —— 正常演进无需拍板), 撞车比对类 bug/perf/refactor/docs/chore 共 16 条逐条标比对批, feat/question 21 条「不重开」; ②坑档 7 类 112 主题逐条一句话; ③在途件清单(v3 计划 Open 但 S6 已落地剩 S7 agg=issue 1015; reannounce 0923 Open 将改 commands.py/runtime.py/shared/commands.js; v3 报告 1730 由「待评审」更正「已落地」); ④guards.md 守阵按 5 组蒸馏。报告草稿 [26-10-05-1036](../reports/26-10-05-1036-report-full-code-review.html)(dark 单文件, doc-status Open, 发现登记格式 + A/B1/B2/C/D/E/F1/F2/G/H 十章占位)。S1: git ls-files 重盘 8 批 **221 文件, 并集==全集 0 漏 0 重**(Unassigned/Dups/Missing 全空); 规模实测: A 5,977 / B1 2,930 / B2 4,651 / C 2,889 / D 4,966 / E 5,296 / F 24,286(JS 13,479+CSS 6,977+HTML 3,830) / G 3,960 / H 15,044(含 scripts≈8.9k+extensions≈1.6k); F1/F2 拆分 = 主干 6 件 6,466 行(config_editor/drawer/shortcuts/config_hub/dialogs/commands, commands.js 标 reannounce 交叉「落地后复验」) / 其余 25 件 7,013 行 + CSS/HTML 机制面随 F2。计划 §06 规模列与备注已回填实测。
> 最后活动: 2026-10-05 10:36

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html, memory-bank/reports/26-10-05-1036-report-full-code-review.html

## 已完成
- S0: sync(a4d14a8d) → test.full 基线(2610+4/99%) + 基线切片 → 底册四表(issues 37 Open / 坑档 7 类 / 在途件 / 守阵) → 报告草稿骨架(十章占位 + 登记格式) → 计划回写 In Progress + 变更记录。
- S1: 批次重盘脚本(git ls-files + 行数) → 批 A–H 文件×LOC×关联测试×关联文档×重点维度 → F1/F2 拆分 → 0 漏 0 重核对 → 计划 §06 回填。

## 正在进行
- S2 起每批一轮: 批 A → B1 → B2 → C → D → E → F1 → F2 → G → H, 每批开工先 sync 记 HEAD, 发现按登记格式回填报告草稿对应章节。
