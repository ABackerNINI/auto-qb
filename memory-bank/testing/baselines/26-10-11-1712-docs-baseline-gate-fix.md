# 3124 —— 三份基线切片补齐三行头 + 提交闸门补挂两条 `--check` 基线

> 摘要: issue `26-10-11-1630-docs-baselines-missing-summary-header` 两段收口 —— ①(docs) `26-10-10-2245` / `2306` / `2335` 三份 webui 基线切片补齐三行头(补 `> 摘要:` + `> 基线时间:`, 正文一字未动); ②(根因) 提交闸门 `.commands/my-commit-flow/.my-commit-flow.toml` 的 memory-bank 闸门漏挂 `gen_baseline_recent --check` 与 `check_wording --check`(两条都在 `kb.check` 的 run 里, 故"能判红却不在闸门里" = 静默红), 已补进闸门并新增守阵 `tests/test_memory_bank.py::test_commit_gate_covers_kb_check` 钉住「闸门 ⊇ kb.check」(红验过: 摘掉一条即红)。数字与会话开工时的差来自 `my-commit-flow.sync` 快进到的 develop(`960a9ab0`→`8d76b3eb`, 含上游 core / rules 两笔合流)。
> 基线时间: 2026-10-11 17:12

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 `960a9ab0`→`8d76b3eb`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3124 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16464 语句 / 148 未覆盖 / 5608 分支 / 133 partial; 门槛 98% 达标, 实到 98.70%; 本轮 59.13s)
- 增量明细(本轮真正新增): 三份基线切片补三行头 + issue `26-10-11-1630-...`(状态 `Open`→`Done` + 日志三条) + `activeContext/26-10-11-1654-docs-baseline-header-fix.md`(会话切片) + `pitfalls/kb/discipline.md`(新条目「闸门漏挂某条 `--check` → 静默红」) + `tests/test_memory_bank.py`(守阵 `test_commit_gate_covers_kb_check`) + `.commands/my-commit-flow/.my-commit-flow.toml`(memory-bank 闸门补两条 `--check`)。无 `src/` 改动。
- 机检: `commands run kb.check` 全 6 条转绿; `commands run test.pkg` 155 passed(闸门配置自证)。
