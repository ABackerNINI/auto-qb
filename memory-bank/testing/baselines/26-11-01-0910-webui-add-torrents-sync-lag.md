# 4385 —— 添加种子后同步追平修复的全量基线

> 摘要: 添加种子后同步追平修复的全量基线
> 基线时间: 2026-11-01 09:10
**Refs:**

## 验收数字

```text
TOTAL                                                21902    144   7430    121    99%
4385 passed, 2 skipped in 181.46s (0:03:01)
```

- 口径: `commands run test.full`（uv run pytest tests -q，带覆盖率；pytest.ini 默认 -n 4），2026-11-01 09:07 本机实测。
- 相对上基线的逐位对比不写（看 `commands run kb.baseline -n 2`）。

## 本改动面

- `src/auto_qb/torrents/store.py` —— 新增「期望落地」有界追平：`expect_hashes()` / `expect_due_at()` / `clear_expect()` / `_settle_expect()`，常量 `_EXPECT_RETRY_INTERVAL=0.08` / `_EXPECT_MAX_RETRIES=3` / `_EXPECT_TTL=3.0`；`_apply` 两个出口结算，`reset_runtime` 清空。
- `src/auto_qb/webui/commands.py` —— `_cmd_add_torrents` 调 `_expect_landing()`，把回执里的 `added_torrent_ids` 交给 store（老版 qB 纯文本回执静默跳过）。
- `src/auto_qb/core/qbmanager.py` —— 同步后 `next_sync_at = min(next_sync_at, expect_due_at())`；追平轮 `force=True`；断连分支先 `clear_expect()`。
- 测试：新增 `tests/test_store_expect.py`（7 条），`test_web_commands.py` / `test_qbmanager.py` 各加 1 条。
- 文档回写：`systemPatterns/web-responsiveness.md`、`pitfalls/web-ui/perf-cadence.md`（「补刷新只一次」的边界）、issue `26-10-30-0626` 置 Done。
