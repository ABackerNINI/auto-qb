# 4896 passed + 10 skipped(根) —— W4 变异 2 issue(极低残存/观测面日志)结清后全量基线

> 摘要: W4 变异 2 issue(极低残存/观测面日志)结清后全量基线
> 基线时间: 2026-11-02 23:48
**Refs:** memory-bank/issues/26-10-31-1539-test-core-w4-mutation-extreme-low-residue.html, memory-bank/issues/26-10-31-1539-test-core-w4-mutation-observability-logs.html

## 验收数字

`commands run test.full`(2026-11-02 23:48)实测:

```text
TOTAL                                                22523    152   7728    134    99%
4896 passed, 10 skipped, 3 warnings in 189.12s (0:03:09)
```

口径: 根目录全量(Windows 并行 `-n 8` + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `tests/test_traffic_store.py`: 新增 `test_v4_one_byte_read_and_append_semantics`、`test_v4_live_tail_slots_zero_and_negative_span_forms`、`test_v4_read_agg_empty_default_exact_fields`、`test_v4_store_series_keys_skips_hash_named_plain_file`、`test_v4_day_cache_budget_exact_fit_and_evict_to_one`、`test_v4_store_evict_rmtree_failure_continues_remaining`(issue extreme-low-residue 6 用例); 新增 `test_v4_bad_line_warn_torn_exemption_and_gate_boundaries`、`test_v4_bad_line_warn_throttle_table_clear_boundary`、`test_v4_bad_line_warn_message_fields_and_source_identity`、`test_v4_evict_and_rewrite_failure_warning_message_content`(issue observability-logs 4 用例); 头部「## 测试计划」同步登记
- 零 src 改动; 2 件 W4 `test` issue 结清; 红验 issue1 17/17 KILLED + issue2 18/19 KILLED(`_wblp_20` 判等价: V4ParsedDay/V4ParsedAgg 恒带 torn_tail 字段, getattr 默认值不可达)
