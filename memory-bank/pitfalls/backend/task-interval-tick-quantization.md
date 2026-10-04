# 周期任务 interval 被主循环节拍量化 — 消费侧按配置 interval 推数据粒度必错

> 摘要: TaskQueue 周期任务的到期判据只在主循环 tick 边界评估(next_run 只能被 tick「看见」), 真实节奏 = ceil(max(interval, main_tick)/main_tick)×main_tick —— 3s 任务在 main_tick=2s 下实际 4s 一轮。任何按「配置 interval == 数据落盘节奏」设计的消费侧粒度(读侧栅格桶宽/窗口切分/滑窗长度)都会系统性走空。
> 触发: 周期采样任务, 按配置间隔推算数据粒度, 读侧栅格/桶宽, 伪断线, 图上有规律缺口, 行距比配置间隔大, 采样节奏不对齐

## 条目

- **触发**: 新增或调整周期任务(sample_interval 类配置)后, 消费侧(读侧栅格/聚合窗口/图表桶宽/超时判据)按配置 interval 推算数据粒度; 或用户报「数据有规律性缺口/断线/粒度比设置粗」。
- **判别**: 数落盘产物的时间戳差分布并与 ceil(interval) 对比 —— 若行距恒等于「主循环节拍的倍数」(如 3s 配置实测恒 4s = ceil(3/2)×2), 即命中。代码判据: 任务 handler 返回 REQUEUE 后 `taskqueue._requeue` 置 `next_run = now + task.interval`, 而 `run_due/_pop_due` 只在 qbmanager 主循环每 `main_tick`(config.models 缺省 2.0s)醒来时评估一次; interval < tick 的任务每 tick 兑现一次(节奏 = tick)。
- **处置**: 消费侧粒度一律按量化节奏算: `ceil(max(interval, main_tick)/main_tick) × main_tick`(纯函数 + 单测钉住), 不直接消费配置 interval; 运行期要改节奏的, 在 handler 每轮回写 `task.interval = conf.<interval键>`(requeue 即按新值, 热重载即时生效 —— 任务 interval 注册时定死, L0 换配置对象不会追到已注册任务上)。实例: qB 流量图折线断裂(2026-10-04, 报告 reports/26-10-04-1639): 桶宽 ceil(3)=3s/2s < 实际行距 4s → 空桶系统性出现 → spanGaps:false 碎段/全孤点。
- **守阵**: tests/test_traffic_grid.py(量化节奏纯函数用例, 随修复落地)。
