# 2676 —— my-commit-flow v3.1 步骤行 (@ 295bb226 + 未提交)

> 摘要: 本轮只改 `.commands/my-commit-flow/`(三脚本 + 两份守阵测试)与文档 —— **零 `src/` 零 `tests/` 改动**,
> 故 `test.full` 与上一条基线 `26-10-06-0713`(2676 + 4 / 16021 / 163 / 5472 / 143 / 46.61s)**逐项全同**,
> 耗时 46.28s 亦在同区间。真正被本轮影响的面是包内脚本测试(`testpaths` 之外的 `test.pkg`)。
> 基线时间: 2026-10-06 10:12

**Refs:** memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md, memory-bank/activeContext/26-10-06-1012-commands-shipflow-steps.md

- 分支: develop @ **295bb226**(工作树含本轮 `.commands/my-commit-flow/` 与文档改动, 未提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**; 单次 **46.28s**。
  语句 16021 / 未覆盖 163 / 分支 5472 / partial 143。
- 相对上一条基线 `26-10-06-0713`(2676 + 4 / 16021 / 163 / 5472 / 143 / 46.61s):
  passed ±0 · 语句 ±0 · 未覆盖 ±0 · 分支 ±0 · partial ±0; 耗时 46.61s → 46.28s(单次数字不作基准)。
- **差值归因**: 本轮改动面全在 `.commands/my-commit-flow/`(`sync.py` / `commit.py` / `push.py` /
  `_pipeline.py` + `test_sync.py` / `test_commit.py`)与 `.commands/`·`memory-bank/`·`AGENTS.md` 文档,
  **不进 `--cov=src` 统计, 也不在 `testpaths(tests/)` 里** ⇒ `test.full` 数字全同是**预期**而非漏测。
- **包内脚本测试(本轮真正受影响的一侧)**: `commands run test.pkg` = **111 passed /
  171.25s ~ 176.42s**(四次相邻采样, `-n 4`; 收集面 `.commands` + `.agents/skills/commands`);
  其中 `my-commit-flow` 单独 **91 条**(`test_sync` / `test_commit` / `test_pipeline`)。
  相对本轮开工时: **新增 8 条**守阵(快进留痕 / 分叉 rebase 留痕 / rebase 与 amend 两行的**顺序** /
  生成物自动化解留痕 / 主入口步骤与结果行顺序 / 提交侧 amend 留痕 / 步骤链不变量 / 齐平零步骤)、
  **删 1 条**(「本地领先留痕」: 该路径不改写 HEAD, 按登记纪律②不该报步骤, 已并入
  `test_ahead_only_is_noop` 的零步骤断言) ⇒ 净增 7。
- **为什么单记一条**: 一是把「只动 `.commands/` 的改动不惊动 `test.full`」这个事实留档(免得后续看到数字
  全同又去查为什么没变), 二是给下一轮改动 `.commands/` 的会话一个可比对的 `test.pkg` 数字。
