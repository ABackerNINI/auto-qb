# 修复三份 webui 基线切片缺三行头致 kb.check 恒红

> 摘要: 认领 issue `26-10-11-1630-docs-baselines-missing-summary-header`(docs / light)并修复: `26-10-10-2245` / `26-10-10-2306` / `26-10-10-2335` 三份 webui 基线切片(专题 `webui-selection-trigger-parity`, 提交 `0a71a758` 带入)缺三行头里的 `> 摘要:` 行, 使 `gen_baseline_recent --check`(`commands run kb.check` 第 4 条)对这三份恒报「缺 `> 摘要:`」而 rc=1 —— 提交闸门未挂这条故不拦提交, 属静默红。修法 = 三份切片标题后补齐三行头(`> 摘要:` 取各切片主题/首段要点 + `> 基线时间:` 取文件名时间戳, 与排序回退一致), **正文一字未动**; `commands run kb.check` 全 6 条转绿。**续作(用户「修复静默红的根因」)**: 根因 = 闸门与 `kb.check` 的 `--check` 清单各自演化, 漏挂 `gen_baseline_recent --check` 与 `check_wording --check`(两条都在 `kb.check` 里), 已一并补进 memory-bank 闸门并加守阵钉住「闸门 ⊇ kb.check」。
> 最后活动: 2026-10-11 17:09

## 正在进行

- 本专题已闭环(issue 置 `Done`), 无在办项。逐笔留痕见 issue 的状态变更日志。
- 本轮实测数字见 `commands run kb.baseline`(本会话切片 `26-10-11-1712-docs-baseline-gate-fix`)。

## 关键结论

- **缺陷形态 = 三份切片只有 `# 标题` 就直接接 `- 主题:`, 整块 `>` 三行头全缺** —— 机检只报 `> 摘要:`(`gen_baseline_recent` 的校验面只有 `TITLE_RE` + `SUMMARY_RE`); `> 基线时间:` 缺失会被排序回退(文件名时间戳)静默兜住, 故不判红, 但按 `testing/baseline.md` 口径段三行头应齐全, 本次一并补齐。
- **静默红的根因 = 提交闸门与 `kb.check` 的 `--check` 清单各自演化(手抄副本)**: `.my-commit-flow.toml` 的 memory-bank 闸门原只有 `gen_tasks_index` / `gen_kb_index` / `gen_docs_index` / `gen_doc_map` / `timekit`, **漏了** `gen_baseline_recent --check` 与 `check_wording --check`(两条都在 `kb.check` 的 run 里) ⇒ "能判红却不在闸门里", 缺陷静默通过所有提交, 只能靠人手动跑 `kb.check` 撞见。**已修**: 两条补进 memory-bank 闸门; 新守阵 `tests/test_memory_bank.py::test_commit_gate_covers_kb_check` 钉住「闸门 ⊇ `kb.check`」(取 `kb.check` 每条 `--check`, `gen_all` 展开成 `GENERATORS`), 红验过(摘掉一条即红, 还原即绿)。机理入坑档 `pitfalls/kb/discipline.md`「闸门漏挂某条 `--check` → 静默红」。
- 修复前全量 444 份基线切片里仅此三份缺 `> 摘要:`; 缺 `> 基线时间:` 的有 44 份(排序回退兜住, 属可容忍) —— 只有 `> 摘要:` 是机检判红项。
