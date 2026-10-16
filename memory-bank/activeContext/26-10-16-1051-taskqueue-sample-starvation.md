# 26-10-16-1051-taskqueue-sample-starvation — 采样移出任务队列改挂时钟线(issue 26-10-16-0954 认领与修复)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html」。走 issue 建议修法 #1(用户拍板): `qb_traffic` 采样**移出 `TaskQueue`**、改挂**时钟线钩子** `on_task_line`(任务线节拍, 每 `main_tick` 一次, 不受 `max_tasks_per_tick` 约束)。依据 = 采样只读内存快照、零 qB 请求, 不该占「qB 请求预算面」的队列配额; 而队列只有 `next_run` 一个排序键, 重启/L2 重建补建的数百立即到期任务会按严格升序把它挡在门外(现场 7/7 复现 37~55s 静默、1.5s 档丢约 36 轮, 且静默被读侧摊配成假平线)。落地面: 钩子做到期闸门 + 采样体自持 `_next_sample_at`; 删任务注册/`queue_rebuilt` 订阅/`TASK_NAME`; `_apply_interval` 去 `task.interval` 回写(量化口径逐字不变); 启停与热重载改由采样体入口现读 `enabled`。测试数字与红验见基线切片。
> 最后活动: 2026-10-16 10:51
> 状态: Done
> 档案: memory-bank/tasks/26-10-16-backend-taskqueue-sample-starvation.md

**Refs:** memory-bank/tasks/26-10-16-backend-taskqueue-sample-starvation.md,memory-bank/issues/26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html,memory-bank/testing/baselines/26-10-16-1051-taskqueue-sample-starvation.md

## 本轮落点(代码事实)

- `src/auto_qb/core/modules/traffic_sample_mod.py`: 新增 `on_task_line(force)` —— **只做到期闸门**(`_next_sample_at is None or now >= _next_sample_at` 才放行), 到点调采样体; 新增字段 `_next_sample_at`(None = 首拍即采, 对齐原「任务注册即到期」语义)。`handle_traffic_sample(task, dry_run) -> bool` 改 `handle_traffic_sample(dry_run) -> None`: 入口现读 `conf.enabled`(停用短路且**不动到期点**, 重新启用首拍即采)、先算 `effective = _apply_interval(conf)` 再写 `_next_sample_at = now + effective`, 其余采样体逐字未动。删除 `TASK_NAME` / `_register_task` / `subscribe` + `_on_queue_rebuilt` / `taskqueue` import。
- 为什么钩子挂**任务线**而不是同步线: 同步线节拍 = `min(sync_interval, main_tick)` **可能细于 `main_tick`**(默认 1.5s < 2s)⇒ 采样节拍会被量化到 3s 而非 2s, 与块头 `interval_s` 语义冲突; 采样节拍的单位本就是 `main_tick`(配置硬校验 `sample_interval >= main_tick`)。
- 为什么闸门在钩子、不在采样体: 让既有 ~15 处「直调采样体」的用例语义不变(直调 = 一轮采样); 时钟线的「每拍一次 + 到点才采」两件事各居其位。
- 与视图发布无先后依赖: 采样只更新内存态, 读侧 `traffic_qb` 按请求现取 `live_tail` 引用 ⇒ 模块装配序在 webui 之后也不产生新鲜度回归(已在钩子 docstring 写明, 防后人误加顺序约束)。
- `src/auto_qb/core/module.py`: `register_global_tasks` 样板单点注释「三处」→「两处」(采样退出去向已注明)。
- 用例面: `_run_sample` 助手改直调采样体; 新增 `_add_backlog`(500 个立即到期任务)与 `_spy_sample_rounds`(挂活尾发布)夹具; 3 条注册用例 → 队列零任务 / **积压饿死回归(走真实 `_task_line`)** / 闸门+热重载启停; 间隔断言改 `_effective_interval`; 线程类用例改驱动 `on_task_line`; `tests/test_traffic_store.py` 同款清理(`is True` 断言随返回值退役)。

## 未改(有意, 范围守恒)

- issue §03 点名的**同族风险未一并处置**: `check:check-checking-result` / `check-wait`(2.0s 轮询, 带 hash)与 `delete_tags`(60s)仍在队列里, 理论上可被同一机制饿死。只看 issue 点名的采样, 残留口径写进坑档条目②判据(判它是「传感器」还是「作业」), 是否跟进待用户拍板。
- 未跑 `dev.run -- config.yml --dry-run` 真机冒烟(需真实 qB 在线); 采样路径已由 `_task_line` 真实入口用例覆盖。
- 未给队列加任何公平性机制 —— 修法方向已拍板为「传感器出队列」, 与「队列内公平性」是两条不相交的路。

## 下一步 / 移交

- 真机观察点: 重启后首块第二条记录不应再出现「run_len 很小的 z 行却带数十秒 dt」(issue §02 的判别式); 若仍出现, 说明另有饿死源(先查 `check` 轮询面)。
- 遗留可跟进项(待拍板): ①`check`/`check-wait` 轮询与 `delete_tags` 是否同样移出或保底; ②issue §06 建议修法 #2 的纠正(「各 kind 各取一次」不成立, 须细化到「无 hash 全局任务保底」)是否入池成独立 issue。
- 立档阈值判定: 4 个源文件(2 src + 2 tests)、单会话多轮、涉及文档回写 ⇒ **命中阈值**(≥3 源文件), 已建 `tasks/26-10-16-backend-taskqueue-sample-starvation.md`; 认领链双向闭合(档案 Refs ↔ issue doc-refs)。
- 基线债务转告(本轮不修, 另开会话清理): `activeContext/` 切片数 123 > 70 且 `26-10-15-0728-qb-traffic-restart-spike-gap.md` 超 cap(12960 > 12000)。
