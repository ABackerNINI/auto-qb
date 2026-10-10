# 3112 —— 全仓重复代码审查 轮 11–14(hr 全包)执行基线

> 摘要: 计划 `26-10-10-2333` 的执行轮 R3(用户「做 Phase 1 hr 部分」= Phase 1 后端 hr 包 = 轮 11–14)。**纯审查轮, 零 `src/`、零 `tests/` 改动**: 工具提名在 hr 收 2 组(pylint R0801 =6: 1 组为误报型 ACTION_* 重导出、1 组即展示 DTO 镜像; jscpd python 0 clone); 对 hr 全包(解析面 / 判定与序列化 / 运行面 A service / 运行面 B, ~6.8k 行 / 23 文件)做重复审查; 滚动报告 `26-10-11-0033` 追加 R11–R14(§14–§17)+ 累计计数/候选排序(§18); 入池 hr 9 条 refactor issue。数字与上基线(`26-10-11-0207`)持平 —— 本轮无 `src/`/`tests/` 改动。
> 基线时间: 2026-10-11 02:40

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进至 `81eb863d`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3112 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标, 实测 98.63%; 本轮 55.57s)
- 增量明细(本轮真正新增, **全部是文档 / 知识库件, 无 `src/` 与 `tests/` 改动**):
  - `memory-bank/reports/26-10-11-0033-report-dup-code-audit.html`(滚动报告, 追加 §14–§17 + §18 累计计数/候选排序)
  - `memory-bank/issues/26-10-11-0240-refactor-hr-*.html` **9 条** refactor issue(adapter-parse / model-serialize-helper / lane-transition / warn-dedup-throttle / report-cli / store-recover-lock-family / token-persist / site-derive / thread-lifecycle)
  - `memory-bank/tasks/26-10-10-backend-dup-code-audit.md`(档案回写: 进度日志 R3 + 子任务状态 + Summary/Refs)
  - `memory-bank/activeContext/26-10-11-0240-dup-code-audit.md`(本会话切片)
  - 各 `_index.md`(`kb.index` 重建, 20 生成物)+ 本基线切片
- 机检(本轮相关): `kb.index` 20 生成物; `kb.check` 主键纪律 / 认领链闭环 / 日期守卫全过; `test_docs_forms.py`(报告 meta / 命名 / 索引自洽 / 认领链)+ `test_memory_bank.py`(--check 绿)全过。
- 说明: 回写过程中首跑 `test.full` 因**未重建生成物索引 + 未建本基线切片**(认领链未闭环)出现 3 条自引发失败(reports/_index.md 漂移 / 认领链 2 条); `kb.index` + 本切片落地后复跑全绿。
- 未纳入本轮(刻意不越界): 轮 15–19(webui / rules / infra / torrents+tray)· 前端 · 测试横切 · 汇总; 审查发现的全部可动项(重构)均未实施(纯审查轮), 一律入池 issue。