# 基线切片 26-10-04-0458 — WEBUI qB 流量图十档时间窗(1m-30d)

> 摘要: qb 流量图时间窗 2 档(24h/30d)扩为 10 档 —— 1m/5m/30m/3h/6h/12h/24h 与 qB 速度图对齐(raw 段,
> 桶宽 = 采样间隔) + 3d/7d 外延(hour 段, 桶宽恒 3600s, 与 30d 同口径); 全局/分组/单种三挂点共用同
> 一窗口参数, 一处扩展三处生效。后端单点 `WINDOW_SPECS`(traffic_grid.py)/`WINDOW_NAMES`(traffic_qb.py),
> 前端抽屉窗口按钮组 2→10 档 + `qbWindowLabel` 紧凑文案 + `_qbTickLabel` 三族刻度。存储层零改动。

- 时间: 2026-10-04 04:58 (GMT+8); 会话起点 sync 至 718b96f4(远端无更新)
- 分支: develop @ 718b96f4(+ 本轮未提交改动: core/traffic_grid.py · webui/server/traffic_qb.py ·
  webui/server/routes/state.py · static/shared/{qb_traffic_chart.js, state.js, tpl/drawer.html} /
  tests/test_traffic_grid.py · test_web.py + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2442 passed + 4 skipped, 29.62s, 覆盖率 TOTAL 99%**(14361 语句 / 135 未覆盖 / 4864 分支 / 106 partial)
- 相对上基线(26-10-04-0412: 2441 passed + 4 skipped)**净增 1 用例**: `test_build_grid_extended_windows`
  (六档 raw 段窗桶数/跨度 + 3d/7d hour 段窗桶数/对位); `test_api_traffic_qb_window_validation` 扩为
  十档全放行 + 非法探针 "7d"→"90d"(7d 已随本轮合法)。
- 未验证面: 真机换窗走查待用户 —— 短窗桶数(1m @30s 采样 = 2-3 桶属预期)、三族刻度文案、轮询续拉、
  组右键/种子页签入口的十档一致性。

> 补记 (2026-10-04 05:1x, 提交轮): 提交前 sync 合入远端 f019ed9c(另一 clone 的「轮询期闪烁修复」,
> 与本改动同文件不同区段, stash pop 自动合并零冲突), 合并后复跑: **test.full 2442 passed + 4 skipped /
> 99% / 34.78s** —— 用例数与覆盖率与正文采样一致, 仅耗时不同(两次均实测)。
