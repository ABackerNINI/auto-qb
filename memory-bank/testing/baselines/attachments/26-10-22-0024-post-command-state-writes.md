# 3992 passed + 2 skipped —— S4 补刷新不推后节拍 + 计划收口

> 摘要: S4 补刷新不推后节拍 + 计划收口
> 基线时间: 2026-10-22 00:24
**Refs:** memory-bank/plans/26-10-21-2323-plan-command-writeback-boundary.html

## 验收数字

```text
TOTAL                                                20981      98   7088     101    99%
3992 passed, 2 skipped in 131.34s (0:02:11)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%), 在 S4(补刷新计时)改动后的工作树上实测。
- 本轮新增 2 例: `test_sync_moved_proxy`(代理判据三态) / `test_cmd_resync_keeps_schedule_when_nothing_moved`(时间线: interval=1.0s, 命令在 0.9s 触发补刷新且无变化, 第 3 次刷新必须落在 ≈1.0s)。
- 红验: 把条件改回「无条件重设」后该用例报 `实得 1.91s` 失败; 还原后复绿 —— 判据确有区分力。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/core/qbmanager.py`: 主循环拆出 `sync_due_by_time`; 同步节拍改为「按时到期 或 本轮真有变化」才重设(`_sync_moved()` 读 `delta_fields`/`last_added`/`last_removed`); 新增 `_sync_moved()` 单点。
- `tests/test_qbmanager.py`: 新增 2 例(代理判据 + 计时行为) + 头部清单同步。
- 计划 `26-10-21-2323` 四期全部完成并置 Done。
