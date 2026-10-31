# 周期任务的队列节拍陷阱 — 节拍量化 + 积压饿死

> 摘要: TaskQueue 周期任务的两条同族陷阱。①**节拍量化**: 到期判据只在主循环 tick 边界评估(next_run 只能被 tick「看见」), 真实节奏 = ceil(max(interval, main_tick)/main_tick)×main_tick —— 3s 任务在 main_tick=2s 下实际 4s 一轮。任何按「配置 interval == 数据落盘节奏」设计的消费侧粒度(读侧栅格桶宽/窗口切分/滑窗长度)都会系统性走空。②**积压饿死**(2026-10-16 实证): 队列是**作业面**(受 max_tasks_per_tick 限流), 低间隔周期任务与大批立即到期任务同队时会被按 next_run 的严格升序挡在门外 —— 重启/热重载补建数百个立即到期任务, 1.5s 采样在排水窗内**一次都轮不到**(实测 7/7 复现 37~55s 静默, 丢约 36 轮), 且静默会被读侧摊配**伪装成正常速率平线**(无告警无 stale 标记)。
> 等级: L0
> 触发: 周期采样任务, 按配置间隔推算数据粒度, 读侧栅格/桶宽, 伪断线, 图上有规律缺口, 行距比配置间隔大, 采样节奏不对齐, 采样被饿死, 重启后静默, 队列积压, 补建任务, max_tasks_per_tick, 周期任务轮不到, 假平线

## 条目

- **触发**(① 节拍量化): 新增或调整周期任务(sample_interval 类配置)后, 消费侧(读侧栅格/聚合窗口/图表桶宽/超时判据)按配置 interval 推算数据粒度; 或用户报「数据有规律性缺口/断线/粒度比设置粗」。
- **判别**(①): 数落盘产物的时间戳差分布并与 ceil(interval) 对比 —— 若行距恒等于「主循环节拍的倍数」(如 3s 配置实测恒 4s = ceil(3/2)×2), 即命中。代码判据: 任务 handler 返回 REQUEUE 后 `taskqueue._requeue` 置 `next_run = now + task.interval`, 而 `run_due/_pop_due` 只在 qbmanager 主循环每 `main_tick`(config.models 缺省 2.0s)醒来时评估一次; interval < tick 的任务每 tick 兑现一次(节奏 = tick)。
- **处置**(①): 消费侧粒度一律按量化节奏算: `ceil(max(interval, main_tick)/main_tick) × main_tick`(纯函数 + 单测钉住), 不直接消费配置 interval; 运行期要改节奏的, 在 handler 每轮回写 `task.interval = conf.<interval键>`(requeue 即按新值, 热重载即时生效 —— 任务 interval 注册时定死, L0 换配置对象不会追到已注册任务上)。实例: qB 流量图折线断裂(2026-10-04, 报告 reports/26-10-04-1639): 桶宽 ceil(3)=3s/2s < 实际行距 4s → 空桶系统性出现 → spanGaps:false 碎段/全孤点。
- **守阵**(①): tests/test_traffic_grid.py(量化节奏纯函数用例, 随修复落地)。

- **触发**(② 积压饿死): 进程重启 / L2 结构重建(热重载)后, 种子库规模较大(数百)时, 小间隔周期任务(sample_interval 类, 或 2s 级轮询)出现一段「一次都不执行」的静默期; 判据只看两件事: **任务 interval < 积压清空窗口**(⌈积压任务数/max_tasks_per_tick⌉ × main_tick)。
- **判别**(②): 周期任务与补建任务同队(kind 相同或都无优先级), 队列只有 next_run 一个排序键 ⇒ 补建批次一旦打上「重启那一刻」的时间戳, 被 requeue 的周期任务 `next_run = now + interval` **恒晚于整批补建**, 只要积压未清空就一次都轮不到。代码判据: `taskqueue._pop_due` 严格按 `next_run` 升序弹、只受 `max_tasks` 计数约束; `Task.__slots__` 无 priority 字段(无 kind 公平性机制)。产物侧观察: 采样记录出现「run_len 很小的 z 行却带巨大 dt」(如 `z,1,...,54356` = 只转 1 轮却跨 54.356s); 读侧再把它摊成平线 ⇒ 静默被伪装成正常速率。
- **处置**(②): **别把小间隔周期任务放进受配额约束的作业队列** —— 判它是「传感器」还是「作业」: 传感器(只读内存快照、零 qB 请求、不与外部逐条交互)挂**时钟线钩子**(`on_task_line`, 每 main_tick 一次, 不受 max_tasks_per_tick 约束), 到期判定自持(`_next_sample_at = 上次采样时刻 + effective interval`); 只有真占 qB 请求预算的作业才留在队列里。实例与完整取舍见 issue 26-10-16-0954(`traffic_sample_mod` 采样移出队列: 迁移后同一积压下每拍照常产样)。
- **守阵**(②): tests/test_traffic_sample.py `test_sample_not_starved_by_immediate_task_backlog`(数百立即到期任务占满队列, 走真实 `_task_line` 入口断言「每拍都采到 + 采样不占队列配额」)、`test_sample_clock_line_gate_and_hot_reload_enable`(到期闸门 + 启停)与 `test_sample_task_registered_when_enabled`(队列零任务)。

