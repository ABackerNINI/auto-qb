# 3193 —— 全局流量数据源滞后调研 + 实测复核出厂（纯文档轮）

> 摘要: 专题 `global-traffic-source`。产出报告 `reports/26-10-13-1034-report-global-traffic-source-lag.html`（三层滞后链取证 + 三条技术路线调研 + 自写独立小工具四形态可行性），并按用户实测（TrafficMonitor 显示 40GB 下载 / auto-qb 顶栏 ↓ 显示 31GB，差 9GB）回写「实测复核」：曲线任务节拍 = 生产 `config.yml:90-91` 的 `global_speed_limit_curve.interval: 10M`（**非**顶层 `interval: 60S`，那是 `config.yml:17` 的主循环内置任务间隔）⇒ 快照滞后 ≈ 10.5 分钟，9 GiB ÷ 630s ≈ 15 MB/s 全额解释；TM dat 字段序据其源码 `HistoryTrafficFile.cpp:38-39` 确认为 `<上传>/<下载>`，与 `curves.py:62-72` 一致，链路无 up/down 互换。**纯文档轮：零代码改动，零行为面**。
> 基线时间: 2026-10-13 10:51

上一基线: memory-bank/testing/baselines/26-10-13-0933-infra-win-dll-sig-order.md

## 验收数字

- `test.full`: **3193 passed + 4 skipped, 0 failed** / 50.60s / 覆盖率 `TOTAL 16785 157 5720 140 99%`.
- 纯文档轮, 语句/分支数与覆盖率相对上一基线持平(逐位差值看 `commands run kb.baseline -n 2`).
- Linux 侧未重测(改动为纯文档, 平台无关).

## 本波改动面

- **新增**: 报告 `memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html` · 任务档案 `memory-bank/tasks/26-10-13-backend-global-traffic-source.md` · activeContext 切片 `memory-bank/activeContext/26-10-13-1037-global-traffic-source.md` · 本基线切片.
- **生成物**: `memory-bank/reports/_index.md` · `memory-bank/tasks/_index.md`（`commands run kb.index` 重建）.
- **源**: 无（零代码改动）.

## 已知偏差 / 移交

- 无行为面偏差; 滞后根因（L2 读侧/发布节拍 60s~600s）**未修** —— 待用户拍板实施（报告 §6 建议路线：首选方案 1「把发布快照从写限速节拍拆出」）.
- 报告内引用的 TrafficMonitor master 源码行号（`TrafficMonitorDlg.cpp:693-702/1313-1322` · `HistoryTrafficFile.cpp:38-39`）属**外部证据**，非本仓行号.
