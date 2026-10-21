# 3990 passed + 2 skipped —— S3 移除提交前复核 + 基线换快照

> 摘要: S3 移除提交前复核 + 基线换快照
> 基线时间: 2026-10-22 00:04
**Refs:** memory-bank/plans/26-10-21-2323-plan-command-writeback-boundary.html

## 验收数字

```text
TOTAL                                                20975      98   7084     100    99%
3990 passed, 2 skipped in 136.46s (0:02:16)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%), 在 S3(移除提交前复核)改动后的工作树上实测。
- 首次全量跑在 23:59→00:00 跨日窗口内出现过 7 条流量类用例失败(`test_web_traffic_monitor_notify` / `test_web_traffic_qb`); 单独复跑全绿, 重跑全量也全绿 —— 属跨日抖动(用例按 `date.today()` 算窗口), 与本次改动无关。
- 用例翻面 5 条: `test_ops_recheck_submits_when_only_client_is_checking` / `test_ops_recheck_submits_without_live_query` / `test_ops_recheck_ignores_info_error_before_submit` / `test_ops_recheck_baseline_from_snapshot` / `test_ops_skip_check_export_error_mentions_gone`; `test_checking_skip_reread_gone_aborts_clean` 改写为 `test_checking_skip_gone_fails_at_export_with_clear_message`; 仲裁类直查计数 2 → 1。
- 语句数较上一切片少 16(删掉 `_live_recheck` 及其调用面)。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/core/modules/ops_mod.py`: 删 `_live_recheck`(含两处调用: recheck 提交前、跳检入口); recheck 的 `baseline_progress` 改取快照 `tor.progress`, 并补 `tor is None` 时干净 skip; 跳检导出失败文案改为「导出 .torrent 失败(种子可能已不在客户端)」; 模块/方法 docstring 与注释同步。
- `tests/test_ops.py`: 5 条用例随契约翻面 + 头部清单同步。
- `tests/test_checking.py`: R2 用例改写(种子不在时失败在导出步、撤残留记录、不删除/重加), 10 处过期注释清理。
