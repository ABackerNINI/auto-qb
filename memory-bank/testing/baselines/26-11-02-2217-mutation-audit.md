# 4880 passed + 10 skipped(根) —— W3 变异 4 issue(标题/年月/键名归一化)结清后全量

> 摘要: W3 变异 4 issue(标题/年月/键名归一化)结清后全量
> 基线时间: 2026-11-02 22:17
**Refs:** memory-bank/issues/26-10-31-1211-test-core-w3-mutation-year-bare-edges.html, memory-bank/issues/26-10-31-1212-test-core-w3-mutation-cjk-numerals.html, memory-bank/issues/26-10-31-1212-test-core-w3-mutation-key-normalize.html, memory-bank/issues/26-10-31-1212-test-core-w3-mutation-title-trim.html, memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮 4 件 W3 issue 守阵与回写的**工作树**。
- `commands run test.full` 实测(wrapper 墙时 185.4s, 2026-11-02 22:17 采样, Windows 本机):
  - 汇总行: `4880 passed, 10 skipped, 3 warnings in 182.77s (0:03:02)`
  - TOTAL 表: `TOTAL  22523  152  7728  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- **环境注记**: 本机同期有其它 clone 的 pytest 进程在跑(多 clone 并行), 本轮零失败、零偶发红, 未观察到端口/TMPDIR 争用影响。

## 本改动面

- 生产代码: 仅 `src/auto_qb/core/tvshows.py` 的 `_normalize_key` —— `while` + 手工 `i +=` 步长改为 `for` + `skip_next` 标志(行为等价), 从结构上消除 normalize_key_34/38 两条 timeout 变异面; 其余三件零 src 改动。
- 守阵: `tests/test_tvshows.py` 新增 10 个用例 —— `test_year_window_bare_edges` / `test_episode_upper_bounds` / `test_dir_season_99_boundary` / `test_invalid_date_continues_to_later_valid`(年份/bare 边界 9 条)、`test_cjk_int_bare_hundred` / `test_find_season_rejects_hundred_plus`(CJK 2 条)、`test_normalize_key_tail_bigram_noise` / `test_noise_gap_whitespace_collapsed_in_title` / `test_normalize_key_multi_bigram_terminates`(键归一 2 条 + 回归 1 条)、`test_title_tail_trim_charset`(标题 trim 1 条); 文件头部「## 测试计划」同步追加条目。
- 红验: 内存加载变异模块 14/14 **KILLED**(不改源码); timeout 2 条以代码侧结构消除处置, 不以断言死循环凑数。
- 知识库回写: 本基线切片 + 4 件 issue(`issue-status=Done` + 状态日志 + `doc-refs` 反向链) + issues 索引重建 + 任务档案 `26-10-08-test-mutation-audit.md` 进度行。
- `config.yml` / `auto-qb-data/` 红线未触碰; 未跨仓库; 未扩池。
