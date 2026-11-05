# 4803 passed + 2 skipped —— 全量测试基线: my-commit-flow.sync 生成物自动化解修复(issue 26-11-01-2140)

> 摘要: 全量测试基线: my-commit-flow.sync 生成物自动化解修复(issue 26-11-01-2140)
> 基线时间: 2026-11-02 00:59
**Refs:** memory-bank/issues/26-11-01-2140-bug-sync-generated-whitelist-drift.html

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本修复的**未提交的工作树**(HEAD `10a32bfe` + 本轮改动: `.commands/my-commit-flow/scripts/sync.py`、`test_sync.py` 及知识库回写件)
- `commands run test.full` 实测(wrapper 墙时 178.9s, 2026-11-02 00:59, Windows 本机):
  - 汇总行: `4803 passed, 2 skipped in 175.49s (0:02:55)`
  - TOTAL 表: `TOTAL  22482  164  7708  135  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- 包内脚本测试: `commands run test.pkg.scoped -- .commands/my-commit-flow` **153 passed**(基线 151 + 本轮新增 2 条守阵; 另做红验: 还原旧暂存逻辑 → 新复现用例红, 恢复后转绿)
- **环境 / 工具**: Windows 本机(win32)· Python 3.13 · pytest-xdist 8 workers · `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)
- **口径注记**: 全量 pytest 含覆盖率报表; 注: 本轮首次全量跑(修复落盘但 `kb.index` 未重建的中间态)曾出现 2 条索引守阵红 + 覆盖率 98.97% 差门槛, `kb.index` 重建后复跑即全绿 —— 属测量时序问题, 非代码面缺陷。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `.commands/my-commit-flow/scripts/sync.py`: ①暂存面(主因修复)—— `_resolve_rebase` 化解循环在 `_regen` 后把「冲突集 ∪ (白名单 ∩ `_changed_paths()` 全量改动路径)」一并暂存, 收尾 amend 的 dirty 判定同款扩面(旧 `_modified_paths` 仅 M, 漏新增/删除/未跟踪); ②观测面 —— `_resolve_rebase` 返回值扩为五元组(末位失败原因分级), 冲突失败行带 `(原因; 冲突清单前 5 条 + 总数)`, 约定模板前缀逐字保留; 新增 `_changed_paths` / `_unmerged_paths` / `_cap_paths` 单点。
- `.commands/my-commit-flow/scripts/test_sync.py`: 新增 `test_diverged_new_generated_path_autoresolves`(本 issue 最小复现)与 `test_conflict_failure_line_lists_conflicts`(失败行带冲突清单)两条守阵 + 夹具 `_commit_file` 补父目录创建 + docstring 测试计划同步。
- 知识库回写: issue HTML(状态 Done + 复验 + 根因定案 + 修复后补充)、坑档 `pitfalls/git/rebase-continue-needs-clean-index.md`(脚本侧根因已修注记)、本切片与索引重建。
- 零 `src/` 改动; `config.yml` / `auto-qb-data/` 红线未触碰。
