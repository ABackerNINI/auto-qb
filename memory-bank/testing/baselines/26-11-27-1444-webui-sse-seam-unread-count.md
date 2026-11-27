# 7058 passed, 6 skipped, 1 warning in 145.46s (0:02:25) —— 接缝修复 60s 对账补计未读全量测试基线

> 摘要: 接缝修复 60s 对账补计未读全量测试基线
> 基线时间: 2026-11-27 14:44

## 验收数字

TOTAL                                                31453  31453     0%
7058 passed, 6 skipped, 1 warning in 145.46s (0:02:25)

`commands run test.full` 实测(2026-11-27)。覆盖率行照实测输出逐字誊写; 本轮全绿。

## 本改动面

- `lifecycle.js`: 60s 对账 `_startErrPoll` 由 `_pullErrlog(false)` 改回 `true`(覆盖 SSE 断档/丢事件窗口, 补回错误亮未读徽标); boot 开页全量仍 `false`; reseed 重启全量显式 `{ countUnread: false }`(整环旧条目不刷爆徽标); 去重先行 `"b"+seq` 保证同一 seq 不双计, 注释口径同步回正。
- 测试: `test_webui_error_history.py` 静态接线改 true 断言 + reseed 显式 false 钉; `test_webui_static_r4_poll_auth_lifecycle.py` 的 `_NODE_ERRLOG_EVENT_PROBE` 扩真验(断档补回未读 +1 / 同 seq 先 SSE 后 GET 不二次计 / reseed 全量不计未读 / 桩 setInterval 真放拍验回调传 true)。定向 21 passed。
- 文档: 计划 26-11-27-0530 §03/§06/§10、任务档案 26-11-27-webui-sse、active-context 26-11-20-0421、既有两条 S1 基线切片口径回正; 计划仍 Done、issue 状态不动。
