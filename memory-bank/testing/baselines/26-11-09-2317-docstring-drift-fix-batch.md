# 5876 passed + 2 skipped, 覆盖 99% —— docstring 三处漂移修复批 (issue 26-11-08-0827)

> 摘要: docstring 三处漂移修复批 (issue 26-11-08-0827)
> 基线时间: 2026-11-09 23:17

## 验收数字

```
TOTAL                                                26153     41   9102     53    99%
5876 passed, 2 skipped in 125.71s (0:02:05)
```

实测时点 2026-11-09 23:13(`commands run test.full`, 与上一切片 6fba3de1 同数: 纯 docstring 面, 零行为改动)。

## 本改动面

- `src/auto_qb/hr/fetcher.py` — `HrLoginExpired` docstring: 「refresh.reason」改指 `data.history` 登录失效事件(issue ①)
- `src/auto_qb/webui/relocate_chain.py` — `finalize_face` docstring: 补 failed 入 STOP_PHASES 退休语义(issue ②)
- `src/auto_qb/torrents/store.py` — `update_torrent_fields` docstring: 删漂移行锚 `:237-244`, 只留符号引用(issue ③)
- `memory-bank/issues/26-11-08-0827-docs-hr-relocate-docstring-drift.html` — 翻 Done + 修复后补充
