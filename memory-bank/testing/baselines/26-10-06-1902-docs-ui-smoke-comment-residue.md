# 2678 —— 注释残留清理: 8 处改指已退役 ui_smoke.cjs (@ c31f6351 + 未提交)

> 摘要: 本轮只动**注释**与知识库 —— `src/auto_qb/webui/static/shared/{app,polling}.js` 与
> `scripts/ui_harness.py` 共 8 处的注释由已退役的 `scripts/ui_smoke.cjs` 改指 e2e 轨(spec 文件 +
> `E2E_*` 模式 env)。零行为改动 ⇒ 语句 / 未覆盖 / 分支 / partial 与上一轮
> [26-10-06-1840](26-10-06-1840-webui-frozen-first-column.md) **四项逐位相同**; passed **+1**, 全部来自
> 并行会话已入库的 `9e0b35fc`(新增守阵 `test_frontend_ctx_menu_refit_by_measured_size`), 与本轮无关。
> 唯一被触发的相关守卫是 `test_docs_forms.py::test_claim_chain_is_bidirectional` —— 首跑红,
> 原因是本切片当时还没落盘(认领链要求目标文件先存在), 落盘即绿。
> 基线时间: 2026-10-06 19:0x

**Refs:** memory-bank/tasks/26-10-06-docs-ui-smoke-comment-residue.md, memory-bank/activeContext/26-10-06-0508-playwright-e2e.md

- 分支: develop @ **c31f6351**(开工 `commands run my-commit-flow.sync` = `已同步 c31f6351`; 工作树含本轮
  3 个源文件注释 + 知识库改动, **未提交**)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2678 passed + 4 skipped, 覆盖率 TOTAL 99%**(`Required test coverage of 98% reached.
  Total coverage: 98.55%`); 耗时 **48.53s**(第二次采样)
  —— 同轮另一次采样 **42.67s**(那次 `1 failed, 2677 passed, 4 skipped`), 两值一并存档, 见 [../baseline.md](../baseline.md)「必须带区间」。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- **首跑的红是写序自伤, 不是缺陷**: 失败项 = `tests/test_docs_forms.py::test_claim_chain_is_bidirectional`
  (报 `引用的目标不存在 → memory-bank/testing/baselines/26-10-06-1902-docs-ui-smoke-comment-residue.md`) ——
  档案的 `**Refs:**` 先落盘、被引的基线切片后落盘, 中间那次全量测试正好夹在两者之间; 切片落盘后复跑即全绿。
- 相对 develop 线上一条 [26-10-06-1840](26-10-06-1840-webui-frozen-first-column.md)
  (2677 + 4 / 16021 / 163 / 5472 / 143): 语句 / 未覆盖 / 分支 / partial **四项逐位相同**(本轮改的是
  js 静态资源与 harness 脚本的注释, 都不进 `--cov=src` 的 Python 统计, 也不在 `testpaths(tests/)` 内);
  passed **2677 → 2678** 归因于 `9e0b35fc` 新增的那条守阵(它改的是 `tests/test_web.py`, 只加收集数、不加 src 语句数)。
- **注释残留复核(本轮真正的验收)**: `git grep -n ui_smoke` 全量 —— 受版本控制的代码 / 配置 / 脚本
  **0 处**; 余下命中全在 `memory-bank/` 的冻结件(档案 / 计划 / 报告 / issues / 切片 / 一次性基线快照,
  按约定不回改)与 gitignore 的 agent 草稿(`.workbuddy*/`)。语法面 `node --check
  src/auto_qb/webui/static/shared/app.js` + `ast.parse(scripts/ui_harness.py)` 过。
- 改动面: `src/auto_qb/webui/static/shared/{app,polling}.js` · `scripts/ui_harness.py` 注释 ·
  `memory-bank/{issues/26-10-06-1717-docs-docs-ui-smoke-comment-residue.html, issues/_index.md,
  tasks/26-10-06-docs-ui-smoke-comment-residue.md, tasks/_index.md,
  activeContext/26-10-06-0508-playwright-e2e.md,
  testing/baselines/26-10-06-1902-docs-ui-smoke-comment-residue.md,
  pitfalls/docs/drift.md, pitfalls/_index.md}`。
