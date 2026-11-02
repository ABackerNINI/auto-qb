# 4886 passed + 10 skipped(根) —— W3 测试簇 4 件结清后全量基线

> 摘要: W3 测试簇 4 件结清后全量基线
> 基线时间: 2026-11-02 22:50
**Refs:** memory-bank/issues/26-10-31-1212-test-core-w3-mutation-group-brackets.html, memory-bank/issues/26-10-31-1212-test-core-w3-mutation-episodes-dir-strip.html, memory-bank/issues/26-10-31-1212-test-core-w3-mutation-curves-unit-edges.html, memory-bank/issues/26-10-31-1212-test-core-w3-mutation-curves-alias-badlines.html

## 验收数字

`commands run test.full`(2026-11-02 22:50)实测:

```text
TOTAL                                                22523    152   7728    134    99%
4886 passed, 10 skipped, 3 warnings in 189.43s (0:03:09)
```

口径: 根目录全量(Windows 并行 `-n 8` + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `tests/test_tvshows.py`: 新增 `test_bracket_group_hint_case_and_negation`(括号段组名大小写归一 + 组名段不进标题候选)
- `tests/test_episodes.py`: 新增参数化 `test_episode_path_directory_stripped`(目录段不参与集数解析, 4 种路径形态)
- `tests/test_speed_curve.py`: `test_normalize_period_aliases` 补 `normalize_period("D")`; `test_parse_history_dat_bad_lines` 改为两条格式坏行 + 两条非法日期行(`bad == 4`); `test_merge_direction_and_bytes_to_kib` 补 `merge_direction([0, 1]) == 1`
- 零 src 改动; 4 件 W3 `test` issue 结清, 对应存活变异内存红验全杀

