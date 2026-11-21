# 6656P/6S 覆盖率99% —— test.full 全绿基线

> 摘要: test.full 全绿基线
> 基线时间: 2026-11-21 08:54

## 验收数字

```text
TOTAL                                                30030     74  10658     77    99%
6656 passed, 6 skipped, 8 warnings in 185.12s (0:03:05)
```

## 本改动面

- `src/auto_qb/webui/static/shared/polling.js`: refresh() 改在途合流薄壳(_refreshInFlight/_refreshQueued 记账位; 补拍经 refresh() 再入重查守卫 + document.hidden 短路), 原函数体改名 _refreshOnce 原样持有; lastRid 采纳守卫(viewMode===reqView 才回写, goView 置空保活 → 补拍带空 rid 取新视图全量)
- `tests/test_webui_static_r4_poll_auth_lifecycle.py`: _NODE_POLLCURVE_PROBE 追加第 9 节(在途合流 + 第三拍钉再入守卫)/9b 节(hidden 翻转钉补拍短路)/10 节(切视图竞态置空保活)/11 节(401xqueued 早退仍补拍恰拆两次), docstring「## 测试计划」第 5 行同步
- `memory-bank/testing/baselines/26-11-21-0854-webui-refresh-inflight-coalesce.md`: 本切片
- `memory-bank/active-context/26-11-21-<kb.wrap 派生>-webui-refresh-inflight-coalesce.md`: 会话切片
