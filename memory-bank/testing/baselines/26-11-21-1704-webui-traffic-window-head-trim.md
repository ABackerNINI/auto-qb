# 6757 passed + 6 skipped(根), 覆盖率 99.60%(线 99.5% 达标) —— 流量图名义窗头部修剪收尾基线

> 摘要: 流量图名义窗头部修剪收尾基线
> 基线时间: 2026-11-21 17:04
**Refs:** memory-bank/tasks/26-11-21-webui-traffic-window-head-trim.md

## 验收数字

- 汇总行: `6757 passed, 6 skipped, 8 warnings in 165.82s (0:02:45)`
- 覆盖率: `Required test coverage of 99.5% reached. Total coverage: 99.60%`
- TOTAL 表: `TOTAL 30550 84 10882 83 99%`(语句 30550 / 缺 84 / 分支 10882 / 部分分支 83)
- 上一切片对照: 26-11-21-1341(backend-relocate-foreign-torrent)`6748 passed + 6 skipped` → 本轮 +9 passed(新增: 后端 span_s 断言面 + 前端纯函数电池 8 断言 + SSE 电池 A7 真跑含门关对照 + 坑档守卫新档), 6 skipped 持平。

## 本改动面

- `src/auto_qb/webui/server/traffic_qb.py` — `_meta` 增响应键 `span_s`(窗长 = grid.t1−t0 整值归一; WINDOW_SPECS 经栅格单点下发)。
- `src/auto_qb/webui/static/shared/qb_traffic_chart.js` — 模块级纯函数 `_qbTrimStaleHead`(修剪线 = 尾t − span_s, 含界保留/无 t 即停/列尾恒存活/非法 span 不剪)+ `_qbStreamFrame` 数据入口面接线(门 = schema=2 且 span_s>0 且页面可见, 与渲染门合流 `live` 单点)+ 三处注释面回写。
- `tests/test_web_traffic_qb.py` — meta 全量形状断言补 `span_s: 86400` + 未启用空态/30d 用例 span_s 断言 + 测试计划 docstring 同步。
- `tests/test_webui_static_dom_panel_traffic.py` — 纯函数电池 8 断言(_NODE_QB_TRAFFIC_PROBE)+ SSE 电池 A7 帧面修剪真跑含门关对照 + 测试计划 docstring 同步 + 测试基建: 13 处 node 探针调用 stdin 化(`_NODE_STDIN_WRAPPER` 常量, Windows CreateProcess 32k 命令行上限 WinError 206 实爆修复)。
