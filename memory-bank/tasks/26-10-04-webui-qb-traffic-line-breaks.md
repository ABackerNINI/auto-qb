# 26-10-04-webui-qb-traffic-line-breaks — WEBUI qB 流量图折线断裂取证与修复

**Status:** Open
**Added:** 2026-10-04
**Updated:** 2026-10-04 16:39
**Summary:** 用户报 qB 流量图三症状(折线约 10s 一断不连接 / 更新频率固定不对齐采样设置 3s / 改 1.5s 后只剩端点)。取证报告 [26-10-04-1639](../reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html) 已定量闭合根因: 采样真实节奏被 main_tick 量化成 4s(配置 3s), 读侧桶宽 ceil(sample_interval)=3s/2s 小于行距 → 桶系统性走空 → spanGaps:false 碎段/全孤点; 伴生 task.interval 热重载不跟 + 前端轮询下界 15s 旧边界残留。修复三点(读侧桶宽按量化节奏 / handler 回写 task.interval / 轮询下界 1.5s)待拍板实施。
**Topics:** qb-traffic-line-breaks
**Refs:** memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html

## 原始请求

- 2026-10-04: 「WEBUI qb流量图折线不连贯, 10秒两条折线, 但与前后10秒的折线未连接起来, 且更新频率固定10秒未与设置的采样频率对齐, 我目前设置是3秒, 改为1.5秒后折线只剩下端点了」; 随后提供运行时数据与截图(`C:\Users\11059\Desktop\Projects\data`, 仓外)要求读取分析。
- 2026-10-04 16:3x: 「写一个调查报告，然后提交」 —— 本轮产出 = 取证报告 + 入库; **修复实施未获指令, 留待拍板**。

## 思考过程与决策

- 取证三路互证: ①落盘行距统计(6 个 dat 全部 {4s:39, 5s:1}/40 行 → 采样真实节奏 4s); ②截图像素测量(下行点簇中位间距 48px ≈ 4.08s, 全孤点无连线); ③代码链路(TaskQueue `next_run` 只在 tick 边界兑现 → `ceil(max(interval,tick)/tick)×tick`; 读侧 `build_grid` 桶宽 `ceil(sample_interval)`; 前端 `spanGaps:false` + `_qbIsolatedIdxs`)。
- 关键判别: 桶覆盖演算 —— 4s 行距 × 3s 桶 → 每 3~4 行空一桶(碎段); × 2s 桶 → 全孤点。三症状定量全吻合。
- 排除 v2 z 行程纪律(截图中种 z 行数 0; 有 z 行系列衔接桶覆盖相邻)、前端渲染链(setData/锚点重建无误)、断连洞(b88271a8 的 495s 间隔属真实空闲)。
- 新坑沉淀: 「周期任务 interval 被主循环节拍量化」入 `pitfalls/backend/task-interval-tick-quantization.md`(消费侧按配置 interval 推数据粒度必踩)。

## 实现计划

(待拍板; 细节与影响面见报告 §07)

1. 读侧桶宽改按量化节奏: `traffic_grid` 纯函数 `ceil(max(sample_interval, main_tick)/main_tick)×main_tick`, `traffic_qb._grid` 消费; meta.interval_s 随之 → 前端 xs/轮询自动对齐。
2. `handle_traffic_sample` 每轮 `task.interval = conf.sample_interval`(热重载即时生效)。
3. 前端 `_QB_POLL_MIN_MS` 15000→1500 + 注释/守卫(test_web.py:2703)同步。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 取证与根因定位 | Done | 报告 26-10-04-1639, 三路证据互证 |
| 取证报告入库 | Done | memory-bank/reports/26-10-04-1639(本轮提交) |
| 修复实施(三点) | Open | 待用户拍板后动代码 |
| 修复验收(真机走查 + 基线) | Open | 验收判据: 3s 档折线连续、1.5s 档无全孤点、刷新频率 == meta.interval_s |

## 进度日志

- **2026-10-04 16:39 (取证轮)** — 用户报障 + 提供数据快照(仓外 `C:\Users\11059\Desktop\Projects\data`: global.dat 6575 行 + 5 单种 dat + 16:23:15 截图)。行距统计/像素测量/代码链路三路取证, 根因闭合(见报告 §03/§04); z 行程纪律排除(§06)。产出报告 + 本档案 + activeContext 切片 + pitfalls 条目, 未动任何代码。test.full 基线见本轮提交的 baselines 切片(纯文档轮, 数字与 26-10-04-1039 同代码态)。
