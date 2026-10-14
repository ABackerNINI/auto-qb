# 26-10-14-webui-drawer-cadence-main-beat — 抽屉页签轮询节拍: 5s 固定改主节拍 currentPollMs()

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-14
**Summary:** 用户报「种子详情面板用户页实时速度刷新率太低, 改成与 webui 主节拍一致, 即种子页的刷新间隔」。落点 = `_startDrawerPoll` 的 setInterval 尾部固定 5000 改 `this.currentPollMs()`(种子页刷新间隔单点: 按种子量分档 1.5/2/3s + 失败退背)—— 抽屉实时速度与行数据同频观, 节拍口径吃单点不手抄数字。服务端不动: peers 短缓存(1s)窗口仍窗口外(主节拍下界 1.5s), trackers 默认 2s 缓存把 1.5s 档里的白拉吸收(缓存是为这设计)。守阵同步同轮: 两处测试里钉 `}, 5000);` 正则改钉新形态(判据不放宽); 五处代码注释「5s 轮询」引用改写「主节拍/抽屉轮询」。验证 = pytest 全量 + e2e 全量全绿(e2e 首轮一条 flaky 红属 delta-sync 时序竞态与本轮无关, 单 spec 重跑与全量重跑绿), 数字见 Refs 基线。

**Refs:** memory-bank/testing/baselines/26-10-14-1513-webui-drawer-cadence-main-beat.md
**Topics:** webui-detail-panel-redesign, webui-polling-cadence

## 原始请求

> 种子详情面板用户页实时速度刷新率太低, 改成与webui主节拍一致, 即种子页的刷新间隔

## 思考过程与决策

- 「用户页」= 抽屉 peers 页签(已连接用户); 实时速度 = drawer.js 汇总行「实时 down/up」与 peers 表 dlspeed/upspeed 列, 数据源 `/api/torrents/{hash}/peers`, 续拉走 `_startDrawerPoll` 单定时器(trackers/peers 两页签共用, 流量页签走 `_qbPollStart` 采样间隔另一口径不动)。
- 主节拍单点 = polling.js `currentPollMs()`(basePollMs 按种子量分档 1.5/2/3s, 失败退背翻倍至 15s)—— 种子页的刷新间隔恒走它, 用户「与主节拍一致」字取 = 同方法调用, 不手抄档位数字。
- 旧 P1-4 拍 5s 的省 qB 直连成本与用户新口径(速度滞后直接卖掉)冲突 —— 用户口径取, 注释里保留旧拍动机与改判据两侧历史。
- 服务端两窗口核对改完: peers ttl=1.0s < 主节拍下界 1.5s ⇒ 每轮仍拿新数据(窗口外不变, 注释改写); trackers 默认 2s 缓存 ⇒ 1.5s 档里部分轮拿缓存(白拉但缓存是为这, 省 qB 直连)。
- 守阵两处(test_webui_static_dom_panel / test_web_shortcuts)正则里钉 setInterval 尾部 `}, 5000);` —— 改节拍时守阵必同轮改钉新形态, 放宽即回潮判据失; 新正则对旧形态即时红 = 钉随改有牙。

## 实现计划

1. 节拍单点改: `_startDrawerPoll` setInterval 尾部 5000 改 `this.currentPollMs()` + 注释改写两侧历史。
2. 服务端窗口核对: peers ttl 1s 与 trackers 默认 2s 缓存对照主节拍, 注释口径同步。
3. 守阵两处正则钉改新形态 + 断文案与「5s 轮询」注释引用改写。
4. `test.full` + e2e 全量验证, 基线切片 + 立档档案 + 切片 + 契约回写 + kb.index 重建。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| `_startDrawerPoll` 尾部改 currentPollMs() + 注释改两侧历史 | ✅ |
| 守阵两处正则同步钉新形态 | ✅ |
| 五处「5s 轮询」代码注释引用改写 | ✅ |
| test.full + e2e 全量绿 + 基线切片 + kb 回写 | ✅ |

## 进度日志

- **2026-10-14**: 开工先 `my-commit-flow.sync` → 已同步 `06f150a8`。路由 pitfalls/web-ui/perf-cadence(改节拍前必读)后 drawer_store/drawer/polling 摸底; 节拍口径与服务端缓存窗口核对定改面。
- **改动**: 3 源文件(drawer_store.js 尾部 + 注释两处 · drawer.js 注释两处 · torrent_detail.py 注释一处)+ 2 测试文件(正则钉同步)—— 命中立档阈值(>=3 源文件)。
- **验证**: test.full 全绿(数字见 Refs 切片); e2e 全量首轮一条 flaky 红(delta-sync「lastRid 置空恒全量恢复」8s 谓超时, 时序竞态与本轮改动面 disjoint), 单 spec 重跑绿 + 全量重跑全绿; 端口 8137 残留走 `dev.port-kill` 再重跑。
- **kb 回写**: 契约附件 webui-static-contract-details.md 两处「5s 轮询 tick」改「抽屉轮询 tick」; kb.index 重建。
