# WEBUI qB 流量图折线断裂 — 取证闭合, 修复三点待拍板

> 摘要: 用户报 qB 流量图三症状(折线 ~10s 一断 / 更新频率固定不对齐 3s 采样设置 / 1.5s 档只剩端点), 真机数据 + 截图像素 + 代码链路三路取证闭合: 采样真实节奏被 main_tick=2s 量化成 4s(配置 3s), 读侧桶宽 ceil(sample_interval)=3s/2s < 行距 → 桶系统性走空 → spanGaps:false 碎段/全孤点; 伴生 task.interval 热重载不跟 + 前端轮询下界 15s 旧边界。报告 [26-10-04-1639](../reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html)(Done)。
> 最后活动: 2026-10-04 16:39

**Refs:** memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html, memory-bank/tasks/26-10-04-webui-qb-traffic-line-breaks.md

## 现状

- 取证完成, 报告 + 档案 + pitfalls(backend/task-interval-tick-quantization)已入库; 代码零改动。
- 修复三点(报告 §07): ①读侧桶宽按量化节奏 `ceil(max(interval,tick)/tick)×tick`; ②handler 每轮回写 task.interval; ③`_QB_POLL_MIN_MS` 15s→1.5s(+test_web 守卫同步) —— **等用户拍板**后实施 + 验收。

## 下一步

- 用户说「修复/实施」→ 按报告 §07 三点动代码(traffic_grid / traffic_qb / traffic_sample_mod / qb_traffic_chart.js / test_web 守卫), 配 test_traffic_grid + test_web 用例, 真机走查 3s 与 1.5s 两档。
