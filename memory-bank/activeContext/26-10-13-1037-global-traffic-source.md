# 26-10-13-1037-global-traffic-source — 全局流量数据源滞后：调研 + 自写独立小工具可行性（报告已出）

> 摘要: 专题 `global-traffic-source`。用户命题「traffic monitor 全局流量来源信息滞后 → 调研成熟方案 → 分析自写独立监视全局流量小工具可行性 → 出报告」。取证定论：项目里「全局流量」的数据源是**外部程序 TrafficMonitor 的 `history_traffic.dat`**（只读），四个消费方（限速曲线任务 / `sys.*` 表达式 / WebUI 历史流量弹层 / 顶栏今日流量）**共享同一份由限速曲线任务发布的快照**（`_publish_traffic` 只在 `handle_speed_limit_curve` 调用）。滞后分三层：**L1 上游 ≤ ~30s**（master 源码「每隔30秒保存一次」+ `SaveTodayOnly()` 增量保存，退出才全量）**、L2 本项目读侧 60s~600s = 主因**（`global_speed_limit_curve.interval` 缺省回退主 `interval`=60s，文档示例 10M；读文件/发布快照/写限速三者同节拍）、**L3 前端非瓶颈**。另记两个同源坑：TM 历史按当前选中网卡分账不合并、外部文件路径错则静默失效。调研三路线：A 复用 qB 计数器（**项目已实现** `traffic_sample_mod` v4，30s 采样 + 活尾 + 聚合分层 + 崩溃恢复，但 `enabled` 默认 False）/ B 操作系统网卡计数器（IP Helper `GetIfTable2`、PDH、psutil、ETW；整机口径）/ C 第三方工具与路由器 SNMP。可行性：技术可行（高）但**「独立进程」非最优**——四形态中方案 1（解耦发布节拍，改 `speed_curve_mod` 单模块、零新依赖）性价比最高，方案 3/4（复用 qb_traffic + provider 抽象）最一致，方案 2（游离小脚本写 TM 兼容文件）会重造日界/重置/恢复/单实例。产出报告 `reports/26-10-13-1034`。**本轮零代码改动；全量测试全绿（数字只进基线切片，见 kb.baseline）。**
> 最后活动: 2026-10-13 10:51
> 状态: Done（本轮请求的调研报告已交付；实施待用户拍板，未开工）

**Refs:** memory-bank/tasks/26-10-13-backend-global-traffic-source.md

## 现在做到哪

**报告已产出**：`memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html`（doc-topic `global-traffic-source`，doc-status Done），含 6 节：①摘要 ②现状界定与消费方盘点 ③三层滞后链取证 ④三条路线调研（含口径判据）⑤自写工具四形态可行性与硬约束清单 ⑥结论与建议路线。

**核心结论**：滞后主因是**本项目自己的读侧节拍**（60s~600s，读/发布/写限速耦合在同一任务节拍），不是 TrafficMonitor（~30s 刷新一次）。

**26-10-13-1047 实测复核（回应用户质疑）**：用户实测 TM 显示 40GB 下载 / auto-qb 顶栏 ↓ 显示 31GB（差 9GB），质疑「按 config.yml interval=60s、最多 90s」解释不了。回查生产 `config.yml` **订正前提**：曲线任务节拍 = `global_speed_limit_curve.interval: 10M`（`config.yml:90-91`），**不是**顶层 `interval: 60S`（`config.yml:17`，那是主循环内置任务间隔；`speed_curve_mod.py:120-125` 用 `gslc.interval or ctx.config.interval`，显式值不回退）⇒ 真实滞后 ≈ **10.5 分钟**，9 GiB ÷ 630s ≈ **15 MB/s**，差值由滞后全额解释。另据 TM 源码 `HistoryTrafficFile.cpp:38-39` 确认 dat 字段序 `<上传>/<下载>`，与 `curves.py:62-72` 一致 —— 链路无 up/down 互换（用户确认看的是 ↓）。报告 §1/§3.2 已补实测复核 + 「自查三步」，doc-updated 抬 26-10-13-1047。

## 未做 / 待拍板

- **未改任何代码**、未入池 issue；全量测试全绿（数字只进基线切片，见 `kb.baseline`）。
- **待用户拍板两件事**：①口径（整机总量 vs qB 进程流量）；②是否实施 —— 首选方案 1（解耦发布节拍），其次方案 3/4（复用 qb_traffic 采样器 + provider 抽象）。
- 拍板后按 `plans/` 工位单独立件（doc-topic 沿用 `global-traffic-source`）。
