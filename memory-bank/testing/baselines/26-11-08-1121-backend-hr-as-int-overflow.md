# 5779 passed, 2 skipped, 99% —— _as_int 补 OverflowError 后全量基线

> 摘要: _as_int 补 OverflowError 后全量基线
> 基线时间: 2026-11-08 11:21

## 验收数字

- `commands run test.full`(实测 2026-11-08 11:19, 134.81s): **5779 passed, 2 skipped**(7 warnings)
- 覆盖率 TOTAL 表: 25737 stmts / 15 miss, 8914 branch / 38 partial, **99%**

## 本改动面

- `src/auto_qb/hr/model.py` — `_as_int` except 元组补 `OverflowError`(inf/超大浮点回 default; issue 26-11-08-0827)
- `src/auto_qb/hr/status.py` — `_history_lanes` 过期注释改如实(inf/超大值不再抛)
- `tests/test_hr_status_entry.py` — `test_history_lanes_dirty_numeric_values_do_not_raise` 增 inf/1e999/NaN/-inf 用例; 文件头测试计划清单同步
- `memory-bank/issues/26-11-08-0827-bug-as-int-overflow-gap.html` — 复验行 + 修复后补充, 状态 Open → Done
