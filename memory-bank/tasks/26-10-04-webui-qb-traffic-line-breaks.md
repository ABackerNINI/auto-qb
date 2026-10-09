# 26-10-04-webui-qb-traffic-line-breaks — WEBUI qB 流量图折线断裂取证与修复

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-09
**Summary:** 用户报 qB 流量图三症状(折线约 10s 一断不连接 / 更新频率固定不对齐采样设置 3s / 改 1.5s 后只剩端点)。取证报告 [26-10-04-1639](../reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html) 已定量闭合根因 A1-A4(采样节奏被 main_tick 量化成 4s / 读侧桶宽 ceil(sample_interval) 小于行距 → 桶系统性走空 → spanGaps:false 碎段/全孤点 / task.interval 热重载不跟 / 前端轮询下界 15s 旧边界残留)。**修复未按原三点单独实施, 而由后续 v3 存储专题 [26-10-04-backend-qb-traffic-storage-v3](26-10-04-backend-qb-traffic-storage-v3.md) 以更彻底的形式吸收闭合**: A1 节拍量化 → 由写入侧实测 dt 吸收; A2 读侧桶宽 → 改按有效 dt 逐记录计算(伪断线根因在格式层面消除); A3 → handler 每轮回写 task.interval 的热重载联动; A4 → 前端轮询下界 1500ms; 另 S6 追修 1.5s 小数秒档被整数秒口径静默抬到 2s。三症状(碎段/全孤点/频率不对齐)已结构消除, 本档案转 Done。
**Topics:** qb-traffic-line-breaks
**Refs:** memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html, memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md

## 原始请求

- 2026-10-04: 「WEBUI qb流量图折线不连贯, 10秒两条折线, 但与前后10秒的折线未连接起来, 且更新频率固定10秒未与设置的采样频率对齐, 我目前设置是3秒, 改为1.5秒后折线只剩下端点了」; 随后提供运行时数据与截图(`C:\Users\11059\Desktop\Projects\data`, 仓外)要求读取分析。
- 2026-10-04 16:3x: 「写一个调查报告，然后提交」 —— 本轮产出 = 取证报告 + 入库; **修复实施未获指令, 留待拍板**。

## 思考过程与决策

- 取证三路互证: ①落盘行距统计(6 个 dat 全部 {4s:39, 5s:1}/40 行 → 采样真实节奏 4s); ②截图像素测量(下行点簇中位间距 48px ≈ 4.08s, 全孤点无连线); ③代码链路(TaskQueue `next_run` 只在 tick 边界兑现 → `ceil(max(interval,tick)/tick)×tick`; 读侧 `build_grid` 桶宽 `ceil(sample_interval)`; 前端 `spanGaps:false` + `_qbIsolatedIdxs`)。
- 关键判别: 桶覆盖演算 —— 4s 行距 × 3s 桶 → 每 3~4 行空一桶(碎段); × 2s 桶 → 全孤点。三症状定量全吻合。
- 排除 v2 z 行程纪律(截图中种 z 行数 0; 有 z 行系列衔接桶覆盖相邻)、前端渲染链(setData/锚点重建无误)、断连洞(b88271a8 的 495s 间隔属真实空闲)。
- 新坑沉淀: 「周期任务 interval 被主循环节拍量化」入 `pitfalls/backend/task-interval-tick-quantization.md`(消费侧按配置 interval 推数据粒度必踩)。

## 实现计划

(原三点建议已由 v3 存储专题吸收闭合, 列此仅供溯源; 见子任务状态表与进度日志)

1. 读侧桶宽改按量化节奏: `traffic_grid` 纯函数 `ceil(max(sample_interval, main_tick)/main_tick)×main_tick`, `traffic_qb._grid` 消费; meta.interval_s 随之 → 前端 xs/轮询自动对齐。
   - **实际落法(v3)**: 不按量化节奏算桶宽, 而改按记录**有效 dt 逐记录**计算覆盖桶(桶宽 = ceil(有效 dt)), 根因在格式层面消除(见 v3 报告 §2.3/§4.2)。
2. `handle_traffic_sample` 每轮 `task.interval = conf.sample_interval`(热重载即时生效)。
   - **实际落法(v3)**: `traffic_sample_mod._apply_interval` 每轮现读 sample_interval + main_tick, 失配向上取整到 main_tick 下一倍数(告警一次)并回写 `task.interval`, 采样率变化即关块换新 interval。
3. 前端 `_QB_POLL_MIN_MS` 15000→1500 + 注释/守卫(test_web.py:2703)同步。
   - **实际落法(v3 S3b)**: 已改 1500(`qb_traffic_chart.js`), 守卫随 test_web 拆分迁至 `tests/test_webui_static_dom_panel.py` 并同步。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 取证与根因定位 | Done | 报告 26-10-04-1639, 三路证据互证 |
| 取证报告入库 | Done | memory-bank/reports/26-10-04-1639(本轮提交) |
| 修复实施(三点) | Done | 未按原三点单独实施, 由 v3 存储专题以更彻底形式吸收: 有效 dt 桶宽 / `_apply_interval` 热重载 / 下界 1500(见 [26-10-04-backend-qb-traffic-storage-v3](26-10-04-backend-qb-traffic-storage-v3.md)) |
| 修复验收(真机走查 + 基线) | Done | v3 S3b 读侧验收「折线连续(spanGaps 断口只剩真实真空/断连)」; S6 真机验收追加活尾实时 + 1.5s 小数秒追修; 3s 与 1.5s 两档症状消除 |

## 进度日志

- **2026-10-04 16:39 (取证轮)** — 用户报障 + 提供数据快照(仓外 `C:\Users\11059\Desktop\Projects\data`: global.dat 6575 行 + 5 单种 dat + 16:23:15 截图)。行距统计/像素测量/代码链路三路取证, 根因闭合(见报告 §03/§04); z 行程纪律排除(§06)。产出报告 + 本档案 + activeContext 切片 + pitfalls 条目, 未动任何代码。test.full 基线见本轮提交的 baselines 切片(纯文档轮, 数字与 26-10-04-1039 同代码态)。
- **2026-10-09 14:54 (状态闭合轮)** — 用户确认本专题「应已完成」, 复核代码与档案后转 **Done**。确认依据: 原三点建议(A1-A4)均已被后续 v3 存储专题 [26-10-04-backend-qb-traffic-storage-v3](26-10-04-backend-qb-traffic-storage-v3.md) 以更彻底形式吸收——A1 节拍量化由写侧实测 dt 吸收(A1 不再需要消费侧按量化节奏推算); A2 读侧桶宽改按有效 dt 逐记录计算(D1 覆盖, 伪断线根因在格式层面消除); A3 `traffic_sample_mod._apply_interval` 每轮回写 `task.interval`(热重载即时生效); A4 `qb_traffic_chart.js` `_QB_POLL_MIN_MS` 已为 1500(守卫在 `tests/test_webui_static_dom_panel.py`); 另 S6 追修 1.5s 小数秒档被整数秒口径静默抬到 2s。三症状(碎段/全孤点/频率不对齐)已结构消除。本轮纯文档状态更新, 零代码改动。
