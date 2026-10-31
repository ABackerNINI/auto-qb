# 3989 passed + 10 skipped / TOTAL 99.17% (20728 语句 · 116 缺口 / 7088 分支 · 106 缺口) —— 轮询骨架单点(长驻 + 有界, 抽屉补悬挂兜底)后全量基线

> 摘要: 轮询骨架单点(长驻 + 有界, 抽屉补悬挂兜底)后全量基线
> 基线时间: 2026-10-22 04:33

## 验收数字

`commands run test.full` 实测(2026-10-22 04:33, 工作区 auto-qb-clone1):

```text
TOTAL    20728    116   7088    106    99%
Required test coverage of 99% reached. Total coverage: 99.17%
1 failed, 3988 passed, 10 skipped in 117.54s
```

- 那 1 条 failed = `tests/test_memory_bank.py::test_kb_index_is_regenerated`(本轮新建坑档后索引
  待重建); `commands run kb.index` 后单跑 `tests/test_memory_bank.py` 62 passed ⇒ 计入后为
  **3989 passed + 10 skipped**。
- skipped 10 条与上一笔(02:21, 2 skipped)不同是环境面(含 node 电池的守阵在无 node 时静默跳过
  的口径差异), 非本轮改动引入 —— 本轮只新增 1 条守阵。

## 本改动面

- `src/auto_qb/webui/static/shared/polling.js`: 新增长驻/有界轮询骨架三口子 `startPoll` /
  `stopPoll` / `awaitPoll` + 句柄表 `_polls` + 悬挂兜底阈值常量 `AQB_POLL_STALL_MS`(30000);
  主轮 `stopPolling` / `scheduleNext` 改走骨架(chain 形态)。
- `drawer_store.js`: `_startDrawerPoll` / `_stopDrawerPoll` 改走骨架; 新增 `_drawerPollStuck`
  (卡死判据)与 `_drawerPollUnstick`(复位门 + 留痕)—— 抽屉侧此前缺的悬挂兜底。
- `qb_traffic_chart.js`: `_qbPollStart` / `_qbPollStop` 改走骨架; 删 `_qbLoadAt` /
  `_qbLoadStalled` / `_QB_LOAD_STALL_MS` / `_qbPollResync`(间隔每拍重读 ⇒ resync 不再需要)。
- `config_hub.js` + `state.js`: `tmPollSettle` / `tmPollShutdown` 改走 `awaitPoll`, 删 `pollGen`。
- `commands.js`: `_pollCmd` 改走 `awaitPoll`(退避曲线改由 `ms(n, prev)` 表达)。
- `tests/`: 新增 `test_frontend_poll_skeleton_single_point`(形态四查 + node 电池 17 项); 更新
  `test_frontend_qb_traffic_load_stall_fallback`(含电池改写)、
  `test_frontend_api_request_timeout`(跨文件不变式换常量)、
  `test_frontend_qb_traffic_chart_wiring`、`test_frontend_drawer_groups_shows_views`、
  `test_drawer_narrow_fullscreen_w4`、`test_read_side_no_poll_when_traffic_tab_closed`。
- 红验八类突变全红后精确还原(脚手架用完即删)。
