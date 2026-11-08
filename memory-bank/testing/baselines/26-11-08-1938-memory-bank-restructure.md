# 5,760 passed + 2 skipped —— memory-bank 大重构落地: 移除层手术 + 架构六包蒸馏 + 索引生态退役

> 摘要: memory-bank 大重构落地: 移除层手术 + 架构六包蒸馏 + 索引生态退役
> 基线时间: 2026-11-08 19:38

## 验收数字

## 验收数字

`commands run test.full` 2026-11-08 19:38 实测: **5,760 passed, 2 skipped, 7 warnings in 154.83s**; 覆盖率 99% (TOTAL 25,783 语句 / 18 未覆盖 / 8,940 分支 / 39 未覆盖)。上一基线 26-11-08-1142 compare-digest-ascii: 5,782 passed — 差 −22 为索引/进度族生成器退役与存根机制删除所删用例(见计划 26-11-08-1625 D3/D5/D12), 非回归。

## 本改动面

## 本改动面

按计划 [26-11-08-1625-plan-memory-bank-restructure.html](../../plans/26-11-08-1625-plan-memory-bank-restructure.html) W1-W5 落地, 12+1 提交:

- **W1 蒸馏**: 新增 `memory-bank/architecture/` 六包(overview/main-loop-queue/data-state/rule-engine/hr-groups/webui, 各 ≤8K); `projectbrief.md` 吸收 productContext+techContext 蒸馏物(7,263B)。
- **W2 移除**: 7 目录(checklists/config-reference/modules/rule-system/systemPatterns/progress/archive)+ 9 墓碑/指针桩 + 12 _index + 5 _archive 全删(96 D); `activeContext/` → `active-context/`(91 R); 守卫脚本 13 + .commands 5 + 活文件 7 + tests 10 同批收敛; README 重写为极简路由。
- **W3 退役**: gen_tasks_index/gen_docs_index/gen_issues_index/kb_tier 删除; kb.docmap 命令入口退役(gen_doc_map 保留为认领链守卫); rebuild_index 收口到 pitfalls 单路。
- **W4 换轨**: AGENTS.md(检索纪律 kb.active→README 路由→grep)/双 SKILL/doc-forms/.github instructions 六面重写; templates/progress.md 孤儿删除。
- **W5 清零**: cap 债务 5 项逐字外迁归零; 257 件 pitfalls 等级行删除; check_status_drift progress 死分支退役; CAP_POLICY reference 行删除。
- **W2 前置**: known-bugs(10)+roadmap(11) 三分类处置, 无主项入池 12 件 issue(26-11-08-1716/1717/1721)。
- **终审**: blocker 0 / major 1 / minor 6 全修(4f0be6d0)。
