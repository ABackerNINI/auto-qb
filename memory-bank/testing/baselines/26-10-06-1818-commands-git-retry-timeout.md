# 2677 —— my-commit-flow git 层单次 20s 超时 + 有界重试 3 次 (@ 779cf088 + 未提交)

> 摘要: 本轮只改 `.commands/my-commit-flow/`(5 脚本 + 1 守阵测试)与文档 —— **零 `src/` 零 `tests/` 改动**,
> 故 `test.full` 数字与 develop 线上一条 [26-10-06-1119](26-10-06-1119-webui-hr-table-arrow.md) 的
> 语句/未覆盖/分支/partial **四项逐位相同**, passed +1 只来自本轮开工同步快进进来的 12 笔远端提交。
> 真正被本轮影响的面是包内脚本测试(`testpaths` 之外的 `test.pkg`): 新增 15 条守阵。
> 基线时间: 2026-10-06 18:18

**Refs:** memory-bank/tasks/26-10-06-commands-git-retry-timeout.md, memory-bank/activeContext/26-10-06-1818-commands-git-retry-timeout.md

- 分支: develop @ **779cf088**(开工 `commands run my-commit-flow.sync` 快进 `ec53fda0→779cf088`, 远端领先 12 笔;
  工作树含本轮 `.commands/my-commit-flow/` 与文档改动, **未提交**)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2677 passed + 4 skipped, 覆盖率 TOTAL 99%**; 耗时 **50.59s / 63.80s**(两次采样;
  单次数字不作基准, 见 [../baseline.md](../baseline.md)「必须带区间」)。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**(两次采样逐项相同)。
- 相对 develop 线上一条 [26-10-06-1119](26-10-06-1119-webui-hr-table-arrow.md)
  (2676 + 4 / 16021 / 163 / 5472 / 143): passed **+1** · 语句 ±0 · 未覆盖 ±0 · 分支 ±0 · partial ±0。
  ⚠ **差值归因**: 本轮改动面(`.commands/` 下的包脚本与文档)**不进 `--cov=src` 统计, 也不在 `testpaths(tests/)` 里**
  ⇒ 数字全同是**预期而非漏测**; 那 +1 passed 来自开工同步快进的 12 笔远端提交。
- ⚠ 时间上更近的 [26-10-06-1425](26-10-06-1425-playwright-e2e-s7-matrix.md) **不可直接比**: 它落在
  `playwright-e2e-migration` 分支(S7a 提交 `68f6e033`, 该分支已 rebase 并入 develop), 语句数 15823 与本 develop 线不同源。
- **包内脚本测试(本轮真正受影响的一侧)**: `commands run test.pkg` = **126 passed / 154.49s**(`-n 4`;
  收集面 `.commands` + `.agents/skills/commands`); 其中 `my-commit-flow` 单独 **106 条**
  (`test_pipeline` 51 / `test_sync` 30 / `test_commit` 25)。
  相对开工时(my-commit-flow 单独 91 条): **新增 15 条**, 全在 `test_pipeline.py`
  (`GitRetryTest` 13 + `MirrorNoRetryTest` 2), 无删除、无改写 ⇒ 91 → 106, `test.pkg` 111 → 126, 两侧增量一致(+15)。
- 分组单跑(便于下轮只改包时对照): `test_pipeline.py` **51 passed / 13.1s**;
  `test_sync.py + test_commit.py` **55 passed / 155.8s**。
- 旁证: `commands run kb.index` 重建 20 生成物; `gen_kb_index` / `gen_tasks_index` / `gen_docs_index` /
  `gen_doc_map` / `gen_active_recent` / `gen_issues_index` 六个 `--check` 全绿(主键纪律 462 文档 / 认领链 OK);
  `doc.caps` 无新增债务(AGENTS.md 6608/8000, 包 README 2461/6000); `doc.links` / `check_command_drift` 绿。
- 改动面(全部在 `.commands/my-commit-flow/` 与知识库; 无 `src/` 无 `tests/` 改动):
  `scripts/{_pipeline,_ship_config,push,sync,commit,test_pipeline}.py` · `README.md` ·
  `references/{pipeline,config}.md` · `ship/config.toml` ·
  `memory-bank/{pitfalls/git/push.md, pitfalls/git/_index.md, tasks/26-10-06-commands-git-retry-timeout.md,
  activeContext/26-10-06-1818-commands-git-retry-timeout.md, testing/baselines/26-10-06-1818-commands-git-retry-timeout.md,
  testing/baseline.md}`。
