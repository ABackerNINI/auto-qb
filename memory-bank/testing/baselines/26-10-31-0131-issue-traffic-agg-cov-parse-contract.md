# 4179 passed, 10 skipped —— issue 26-10-30-0622 修复后全量基线

> 摘要: issue 26-10-30-0622 修复后全量基线
> 基线时间: 2026-10-31 01:31
**Refs:** memory-bank/issues/26-10-30-0622-refactor-traffic-agg-cov-parse-contract.html

## 验收数字

`commands run test.full` 实测(2026-10-31 01:31, HEAD 未含本轮改动之外内容):

- 汇总行: `4179 passed, 10 skipped in 64.29s (0:01:04)`
- 覆盖率 TOTAL: `20895 stmts, 114 miss, 7164 branch, 105 partial, 99%`,门槛判定 `Required test coverage of 99.0% reached. Total coverage: 99.18%`
- 口径注记: 修复前一轮同口径曾 1 failed(test_test_plan_docstring_guard 抓到测试计划清单条目误插测试函数 docstring —— 守卫按设计工作), 修正后全绿; 台账 `越界 0 条`

## 本改动面

- `src/auto_qb/core/traffic_store.py`:
  - `parse_v4_agg_text.on_agg_line`: cov_s 下限 1 —— `cov < 1` 抛 ValueError 按坏行整行跳过(与写侧 `v4_hour_agg` `cov_s=max(1,...)` 契约对齐, 复用 `_parse_v4_text` 吞异常路径); docstring 同步契约说明。
  - `v4_merge_agg`: 补 `cov <= 0` fail-closed 守卫(同 `v4_rollup_agg` 口径), 堵双行零 cov 合流的除零(Web 线程炸)。
- `tests/test_traffic_store.py`: 新增 `test_v4_agg_parse_cov_floor_one_bad_line`(cov_s=0/-1 坏行 / =1 边界 / 8 列旧行兜底不受影响 / rollup 上卷回归)与 `test_v4_merge_agg_zero_cov_fail_closed`(双行零 cov ValueError / 单边零 cov 合法); 文件头「## 测试计划」同步两条。
- `memory-bank/issues/26-10-30-0622-…html`: 状态 Open -> Done, 状态日志补认领/复验/修法/验证链; `_index.md` 重建。
