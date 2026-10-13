# 26-10-13-backend-global-traffic-source — 全局流量数据源信息滞后：成熟方案调研与自写独立监视小工具可行性

**Status:** Done
**Added:** 2026-10-13
**Updated:** 2026-10-13 10:51
**Topics:** global-traffic-source
**Summary:** 用户命题「traffic monitor 全局流量来源信息滞后，调研成熟解决方案、分析自写独立监视全局流量小工具可行性、出报告」。逐层取证滞后链：项目里「全局流量」的数据源是**外部程序 TrafficMonitor 的 `history_traffic.dat`**（只读），四个消费方（限速曲线任务 / `sys.*` 规则表达式 / WebUI 历史流量弹层 / WebUI 顶栏今日流量）**共享同一个由限速曲线任务发布的快照**（`_publish_traffic` 只在 `handle_speed_limit_curve` 里调用）。据此定出三层滞后：**L1 上游 TrafficMonitor ≤ ~30s**（master 源码 `//每隔30秒保存一次流量历史记录` + `SaveTodayOnly()` 增量保存，退出才全量）**、L2 本项目读侧 60s~600s（主因：`global_speed_limit_curve.interval` 缺省回退主 `interval`=60s，文档示例 10M；读文件/发布快照/写限速三者共用同一节拍）、L3 前端非瓶颈**。另记两个同源坑：TM 历史**按当前选中网卡分账不合并**、外部文件路径错则静默失效。调研三条技术路线：A 复用 qB 自身计数器（**项目已实现** = `traffic_sample_mod` v4 采样器，30s 采样 + 活尾 + 聚合分层 + 崩溃恢复，但 `QbTraffic.enabled` 默认 False）、B 操作系统网卡计数器（Windows IP Helper `GetIfTable2` / PDH / psutil / ETW，机器全局含非 qB 流量）、C 第三方工具 / 路由器 SNMP。可行性：**技术可行（高）但「独立进程」非最优**——四形态中方案 1（解耦「发布快照」与「写限速」节拍，改 `speed_curve_mod` 单模块、零新依赖）性价比最高；方案 3/4（复用 qb_traffic 采样器 + 数据源 provider 抽象）最一致；方案 2（游离小脚本写 TM 兼容文件）能跑但要重造日界/重置/崩溃恢复/单实例一整套已解难题。产出报告 `reports/26-10-13-1034`。**本轮零代码改动；全量测试全绿（数字只进基线切片，见 kb.baseline）**。**26-10-13-1047 实测复核**：用户给实测（TM 显示 40GB 下载 / auto-qb 顶栏 ↓ 显示 31GB，差 9GB）并质疑「按 config.yml interval=60s、最多 90s」解释不了 —— 回查生产 `config.yml` 确认曲线任务节拍是 `global_speed_limit_curve.interval: 10M`（`config.yml:90-91`；`config.yml:17` 的 `interval: 60S` 是主循环内置任务间隔、不适用）⇒ 滞后 ≈ 10.5 分钟，9 GiB ÷ 630s ≈ 15 MB/s，差值全额解释；另据 TM 源码确认 dat 字段序 `<上传>/<下载>`，链路无 up/down 互换（用户确认看的是 ↓）。报告 §1/§3.2 已补实测复核与「自查三步」。
**Refs:** memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html,memory-bank/activeContext/26-10-13-1037-global-traffic-source.md

## 原始请求

> traffic monitor全局流量来源信息滞后, 调研成熟解决方案, 分析自写独立监视全局流量小工具可行性, 写一个报告

## 思考过程与决策

### 1. 先界定「全局流量」是什么（否则整份调研会跑偏）

全项目检索后确认：本项目的「全局流量」**不是自有模块**，而是**一份外部只读文件** —— TrafficMonitor（zhongyang219，Windows 任务栏网速/流量悬浮窗）写出的 `history_traffic.dat`：

- 路径配置 `config/models.py:279-291`（`GlobalSpeedLimitCurve.dat_path`）；格式/解析 `core/curves.py:1-73`；用户文档 `docs/configuration.md:355-412`（原文「目前本软件不支持监控设备全局流量，所以需配置外部流量数据来源」）。
- 文件语义是「**某日已累计上传/下载量**」的按日行（当天行随流量增长、跨天重置），**日粒度累计**，不是时序采样。

### 2. 消费方盘点 → 发现「共享同一个快照」这个枢纽事实

四个消费方（限速曲线任务 `speed_curve_mod.py:129-238` / 规则表达式 `rules/expr/env.py:173-195` + `:344-351` + `:438` / WebUI 历史流量弹层 `webui/server/routes/state.py:124-133` + `dialogs.js:597-890` / WebUI 顶栏今日流量 `dialogs.js:698-707`）中，**后三个都不直接读文件**，而是读第一个发布的快照。引用检索确认 `_publish_traffic` 只在 `handle_speed_limit_curve` 内被调用（`speed_curve_mod.py:133/136/145/150/186/238`）⇒ **「读文件 + 发布快照 + 应用限速」被绑死在同一任务节拍上**。这是滞后主因的结构性来源。

### 3. 三层滞后取证

- **L1 上游（≤ ~30s，非主因）**：TrafficMonitor master 源码（`TrafficMonitor/TrafficMonitorDlg.cpp`，经 grep.app 命中并原样引用）—— `:1317` 注释「//每隔30秒保存一次流量历史记录」、`:693-697` `SaveHistoryTraffic()` → `m_history_traffic.SaveTodayOnly()`（增量，只改首行 + 今日行）、`:699-702` `SaveHistoryTrafficFull()` → `Save()`（退出全量）；写入由「今日累计 KB 变化」门控（`:1321-1322`）。NIC 采样节拍默认 1000ms（wiki 选项设置「监控时间间隔」）。历史包袱：旧版（issue #2269，v1.85.1）整文件逐行重写，master 已改增量。
- **L2 本项目读侧（60s~600s，主因）**：`speed_curve_mod.py:120-125` 任务间隔 = `gslc.interval or ctx.config.interval`；`GlobalSpeedLimitCurve.interval` 默认 None（`models.py:290`）；主 `interval` 默认 60.0s（`models.py:354`）；文档示例给 10M（`docs/configuration.md:366`）。
- **L3 前端（非瓶颈）**：历史弹层按需拉 `/api/traffic/history`（`dialogs.js:606`），拿到的是 L2 快照；前端再快也追不上。

### 4. 两个「同源但不属于滞后」的坑（一并记入报告）

- TM 历史**按当前选中网卡统计、不跨网卡合并**（trafficmonitor.org FAQ 原文）⇒ 换网卡/VPN 分账或漏计，体感像「数据不对」。
- 外部文件路径错/不存在 ⇒ 曲线整条静默失效（`speed_curve_mod.py:143-151` 已发 `stale` + 原因），易误判为滞后。

### 5. 方案选型：三条路线 + 四形态，判据是「口径」

- 三条路线：**A** qB 自身计数器（`/api/v2/sync/maindata` 的 `server_state`：`alltime_dl/ul`、`dl_info_data/up_info_data`；**项目已实现**于 `traffic_sample_mod` v4，但 `enabled` 默认 False，`models.py:314`）；**B** 操作系统网卡计数器（Windows IP Helper `GetIfTable2`/`GetIfEntry2` 64 位 `InOctets`/`OutOctets`、PDH `Network Interface\Bytes Received/sec`、`Get-NetAdapterStatistics`、`psutil.net_io_counters(pernic=True)`、ETW `Microsoft-Windows-Kernel-Network`）；**C** 第三方工具 / 路由器 SNMP。
- **比选型更重要的拍板**：「全局流量」有三个不等价口径 —— ①整机总量（含所有应用，TM 现在给的）②qB 进程流量（qB 计数器给的）③指定网卡。用①驱动「qB 限速」会出现「别的应用吃光额度 → qB 被误限速」；用②则与限速对象自洽。**这一步决定选 A 还是 B**。
- 自写工具四形态：**方案 1**（解耦发布节拍，改 `speed_curve_mod` 单模块，零新依赖，收益立竿见影）**> 方案 3/4**（复用 qb_traffic 采样器 + provider 抽象，最一致；配置注释 `docs/configuration.md:370`「后续可能支持接入其它软件来源」已预留意图）**> 方案 2**（游离小脚本写 TM 兼容文件，对项目零改动但要重造日界/重置/崩溃恢复/单实例）。硬约束清单（口径/计数器重置回绕/日界时区/崩溃窗口/单写线程/幂等/新配置键须进 `validate_config`+`schema`/Windows-only）逐条对齐项目既有对策（`traffic_sample_mod` 的 delta-reset 单点、`v4_day_epoch`、`flush_interval` 批量落盘、`_recover_aggregates` catch-up、`_win_user32` 惰性绑定模式）。

### 6. 结论

**滞后主因是本项目自己的读侧节拍，不是 TrafficMonitor**（后者 ~30s 就刷新）。**最高性价比第一步 = 方案 1（解耦发布节拍）**；若仍要脱离 TM，走方案 3/4 复用 qb_traffic 基建，而不是另起游离进程。

## 实现计划

本轮为**调研轮**，零代码改动。报告内已给建议路线（按性价比排序）：

1. 第 0 步：拍板口径（整机总量 vs qB 进程流量）。
2. 第 1 步：方案 1 —— 解耦 `speed_curve_mod` 的「发布快照」与「写限速」节拍（预期今日流量滞后 600s → ~30s）。
3. 第 2 步：方案 3/4 —— 打开 `qb_traffic` + provider 抽象，限速曲线/表达式改从 qB 采样器取数，`traffic_monitor` 降为可选 provider。
4. 第 3 步（仅当必须整机口径且不要 TM）：在 `traffic_sample_mod` 同构加「网卡计数器系列」。
5. 顺带：升级旧版 TrafficMonitor（增量保存）、核对「当前选中网卡」是否符合预期。

**后续若拍板实施，按 plans 工位单独立件（doc-topic 沿用 `global-traffic-source` 串联）。**

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 现状界定与消费方盘点（来源 = TM `history_traffic.dat`；四消费方共享快照） | Done |
| 2 | 三层滞后链取证（L1 上游源码核对 / L2 读侧节拍 / L3 前端） | Done |
| 3 | 同源坑取证（按网卡分账 / 外部文件静默失效） | Done |
| 4 | 成熟方案调研（路线 A/B/C 对比 + 口径判据） | Done |
| 5 | 自写工具四形态可行性与硬约束清单 | Done |
| 6 | 产出报告 `reports/26-10-13-1034-report-global-traffic-source-lag.html` | Done |
| 7 | 实施（口径拍板 + 方案 1 / 3 / 4） | 待用户拍板（未开工） |

## 进度日志

- 2026-10-13 10:37 — 会话开工同步 `cf08c358`（快进 f4ff399a→cf08c358）。完成现状界定 → 三层滞后取证 → 三条路线调研 → 四形态可行性 → 报告产出（`reports/26-10-13-1034-report-global-traffic-source-lag.html`，doc-topic `global-traffic-source`）。上游 TrafficMonitor 结论原样引用其 master 源码（`TrafficMonitorDlg.cpp:693-702/1313-1322`，经 grep.app 命中）。本轮零代码改动、全量测试全绿（数字见 kb.baseline）。
- 2026-10-13 10:51 — 收尾：跑 `test.full` 全绿并记基线切片 `memory-bank/testing/baselines/26-10-13-1051-global-traffic-source-lag.md`；报告 / 档案 / 切片三处「未跑测试基线」措辞订正为「数字见 kb.baseline」（测试基线数字只写基线切片一处）。随本专题入库。
- 2026-10-13 10:47 — **实测复核轮（回应用户质疑）**。用户实测：TM 显示 40GB 下载 / auto-qb 顶栏 ↓ 显示 31GB，差 9GB；指出按 config.yml `interval=60s`、最多 90s 抖动解释不了 ⇒ 前提订正：`config.yml:17` 的 `interval: 60S` 是**主循环内置任务间隔**，曲线任务节拍是 `config.yml:90-91` 的 `global_speed_limit_curve.interval: 10M`（`speed_curve_mod.py:120-125` 用 `gslc.interval or ctx.config.interval`，显式值不回退）⇒ 真实滞后 ≈ 10.5 分钟，9 GiB ÷ 630s ≈ 15 MB/s，差值全额解释。另据 TM 源码 `HistoryTrafficFile.cpp:38-39`（`sprintf_s(..., up_kBytes, down_kBytes)`）确认 dat 字段序 `<上传>/<下载>`，与项目 `curves.py:62-72` 一致 —— 链路无 up/down 互换；用户确认所见为顶栏 ↓（下载）。报告 §1 摘要表 + §3.2 补实测行 / 实测复核 box / 「自查三步」，doc-updated 抬 26-10-13-1047。按用户令「先只回写报告」——**未改代码**。
