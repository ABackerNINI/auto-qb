# 3990 passed + 2 skipped —— S2 save_path 等上报 + 写后同步边界口径

> 摘要: S2 save_path 等上报 + 写后同步边界口径
> 基线时间: 2026-10-21 23:49
**Refs:** memory-bank/plans/26-10-21-2323-plan-command-writeback-boundary.html

## 验收数字

```text
TOTAL                                                20991      97   7090      99    99%
3990 passed, 2 skipped in 127.08s (0:02:07)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%), 在 S2(写后同步边界)改动后的工作树上实测。
- 三条既有用例随契约翻面更新: `test_set_location_syncs_save_path` → `test_set_location_waits_for_sync`(同 tick 读旧值 → 一次同步后落真值)、`test_drain_web_commands_torrent_write_actions`(限速仍同 tick 生效, `save_path` 改为等上报)、`test_drain_web_commands_bulk_torrents_limits_location`(同上)。
- 语句数较上一切片少 1(`QbApi.torrents_set_location` 去掉了一行写后同步)。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/core/qbapi.py`: `torrents_set_location` 去掉 `update_torrent_fields(save_path=...)`, docstring 写明「等上报」及理由(`save_path` 是分组键输入, qB 搬家异步)。
- `memory-bank/conventions/code-style.md`: 新增「写后同步的字段边界」条 —— 判据是值的事实来源; 确定性字段(tags/category/up_limit/dl_limit)可写后同步, 运行状态(state/progress/速率/seeding_time/ratio)只等上报, `save_path` 例外, 删除摘记录保留; 指向守阵 `test_no_synthetic_state_write_site`。
- `tests/test_snapshot_sync.py`: 用例翻面 + 文件头清单同步。
- `tests/test_web_commands.py`: 两处 `save_path` 断言改为「不改写」, 限速断言保留。
