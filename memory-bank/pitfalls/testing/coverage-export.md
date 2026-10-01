# 手工跑 coverage 报表 / 导出 JSON 的命名陷阱

> 摘要: 手工做覆盖率分析时, 导出文件叫 `.coverage.json` 会被 coverage 当成并行数据文件去读, 报 `Couldn't use data file ... not a database` + `Combined 0 files, 1 file errored`, 看着像数据坏了其实报表仍正确; 换个名字即免。
> 触发: coverage report, coverage json, 导出覆盖率, not a database, CoverageWarning, Combined 0 files, 缺口分析

### 导出文件叫 `.coverage.json` → `coverage report` 报 not-a-database 告警

- **触发**: 全量跑完想拿机器可读明细, 顺手 `uv run coverage json -o .coverage.json` 再 `coverage report` (2026-10-01, 覆盖率提升计划 26-10-01-2157 实测)。
- **判别**: 后续任何 `coverage report` / `coverage json` 都刷 `CoverageWarning: Couldn't use data file '<仓库根>\.coverage.json': file is not a database` + `Combined 0 files, 1 file errored` —— **报表数字本身仍正确** (来自真正的数据文件 `.coverage`), 是告警唬人; 根因是 coverage 把 `.coverage.*` 前缀当并行数据文件族, json 导出撞了这个名字。
- **处置**: 导出名避开 `.coverage.*` 前缀 (如 `cov-gap.json`), **且不放仓库根** (仓库根覆盖率文件的删除会被拦截层记越界, 见 [tmpdir.md](tmpdir.md)); 分析完即删, 不进提交。
