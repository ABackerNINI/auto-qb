# 4897 passed + 10 skipped(根) —— 标题尾 trim 不拆散成对括号(tvshows 展示名括号闭合)修复后全量基线

> 摘要: 标题尾 trim 不拆散成对括号(tvshows 展示名括号闭合)修复后全量基线
> 基线时间: 2026-11-03 00:25
**Refs:** memory-bank/issues/26-10-31-1212-test-core-w3-mutation-title-trim.html

## 验收数字

`commands run test.full`(2026-11-03 00:25)实测:

```text
TOTAL                                                22531    152   7732    134    99%
4897 passed, 10 skipped, 3 warnings in 204.02s (0:03:24)
```

口径: 根目录全量(Windows 并行 `-n 8` + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `src/auto_qb/core/tvshows.py`: `_title_and_key` 末行尾 trim 改为「有配对开括号的闭合符保留、其余尾标点照旧剥除」; 新增 `_TITLE_TRIM_CHARS` / `_CLOSER_TO_OPENER` 常量
- `tests/test_tvshows.py`: 新增 `test_title_paired_bracket_tail_preserved`(覆盖 `Show.Name.(US)` / `(UK)` / `[Group]` 闭合保留, 以及无配对闭合符与尾标点照旧剥除的对照); 头部「## 测试计划」同步登记
