# 7057 passed, 6 skipped, 1 warning in 141.14s (0:02:21) —— S1 前端 errlog 事件接线与对账全量测试基线

> 摘要: S1 前端 errlog 事件接线与对账全量测试基线
> 基线时间: 2026-11-27 06:08
**Refs:** memory-bank/tasks/26-11-27-webui-sse.md

## 验收数字

TOTAL                                                31453  31453     0%
7057 passed, 6 skipped, 1 warning in 141.14s (0:02:21)

`commands run test.full` 实测(2026-11-27)。覆盖率行照实测输出逐字誊写; 本轮全绿。

## 本改动面

- `polling.js` `startEvents` 注册 `errlog` 监听, 载荷交 `lifecycle.onErrlogEvent`, 事件路径零 GET。
- `lifecycle.js` 新增事件落袋单点(无 ts 补到达时刻), 合并按 seq 降序插入防乱序, 游标只进不退; 60s GET 保留对账并计未读(覆盖 SSE 断档窗口; 去重先行不双计)〔接缝修复口径回正〕。
- 测试: `test_webui_error_history.py` +1 接线守阵; `test_webui_static_r4_poll_auth_lifecycle.py` 扩 SSE 监听断言 +1 落袋/对账 node 电池; 新增 `tests/e2e/errlog-sse-panel.spec.mjs` 双皮肤面板可见(2 passed)。
- 档案 `memory-bank/tasks/26-11-27-webui-sse.md` S1 翻 Done; 计划 26-11-27-0530 仍 Open(S2/S3 未做)。
