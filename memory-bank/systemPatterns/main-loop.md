# 主循环与每轮数据流

> 摘要: 主循环 `core/qbmanager.py` 的节拍、分层与每轮 `_refresh_torrents` 的相位广播数据流。分层节拍、微步线、连接管理与相位数据流细节已外迁到 `attachments/main-loop-details.md`。
> 触发: 主循环, tick, 节拍, 数据流, refresh_torrents, 相位广播, 分层

## 主循环 (core/qbmanager.py)

```python
run(dry_run, stop_event=None, pause_event=None):        # qbmanager.py:500
    materialize_schema_migration()   # 配置 schema 启动物化(磁盘落后才写; dry-run 只探测)
    lifecycle_ready = False          # 启动期完成闸(2026-11-03): 失败启动不落空态 state
    try:
        host.start_all(dry_run)      # 模块 start 按装配序: web 服务器 / HR 端点与取数线程 /
                                     # 全局任务自注册(原 _create_global_tasks 点名退役);
                                     # 移入 try 后启动期致命错误(WebUIBindError/HrChannelBindError)
                                     # 也走 finally -> stop_all + 释放锁
        lifecycle_ready = True       # start_all 正常返回才允许退出落盘
        while not connect():         # 首连: 非托管模式失败抛 QbConnectError 干净退出;
            ...                      # 托管模式(--tray)按 main_tick 重试直至成功或收到停止
        self.state = ctx.state.load()    # run() 启动再加载一次
        ctx.state.materialize_migration(dry_run)            # state schema 迁移物化
        ctx.state.next_flush_at = now + interval            # 周期落盘起点重置
        host.get("rules")._load_rules()                     # 规则加载在 run() 进行
        while True:
            main_tick = config.main_tick                    # L0 热重载: 每轮重读
            sync_interval = min(config.sync_interval, main_tick)   # 快档>任务档时钳制(BUG-6)
            _wake_event.clear()
            state_changed = host.run_command_line()         # 命令线: 消费命令+检查在途汇报确认
            if paused: _wait_next(...); continue            # 暂停 = 完全旁观
            host.run_micro_line(dry_run)                    # 微步线: 跳检相位机每轮一步(无固定节拍)
            sync_due = now >= next_sync_at or (state_changed and not dry_run)  # P0-5 命令后补一次
            tick_due = now >= next_tick_at
            if sync_due and tick_due: _tick(dry_run, force=cmd_forced)   # 两线同拍 -> 完整一轮
            elif sync_due:            _sync_line(dry_run, force=cmd_forced)
            elif tick_due:            _task_line(dry_run, force=cmd_forced)
            web.flush_truths()               # 推迟回执无条件落(异常路径兜底)
            if not dry_run:
                ctx.state.maybe_flush(...)   # 周期落盘(间隔 state_save_interval)
            重连检测(门是 _ran_line) + 断连稳态守卫/退避重连
            _wait_next(stop_event, _wake_event, min(next_sync_at, next_tick_at, 微步线到期) - now)
    finally:
        host.stop_all()                  # 模块停用(装配逆序); 状态落盘与锁释放留在其后
        if not dry_run and lifecycle_ready:  # 失败启动不落空态 state.json(2026-11-03)
            ctx.state.save()             # 优雅退出落盘
        lock.release()                   # 任何路径都释放(含启动期 fail-fast)

_sync_line(dry_run, flush=True, force=False):  # 同步线 (sync_interval, 默认 1.5s) —— 只刷快照不跑任务
    _refresh_torrents(dry_run)           # 刷新快照 + 相位广播(见下节, :944 起)
    host.run_sync_line(force)            # (:858) 同步线收尾=视图发布; 判据在 webui/module.py:216

_task_line(dry_run, force=False):        # 任务线 (main_tick, 默认 2s)
    task_queue.run_due(dry_run, now, max_tasks,      # (:872) 到期任务执行; defer_gate=D-1 让位闸门
                       defer_gate=self._own_write_defer_gate)   # (:876; 闸实现 :881, 口径见 taskqueue.md)
    host.run_task_line(force)            # (:879) 任务线收尾三步 = webui/module.py:205-225:
                                         # 错误原因预取 -> 视图发布 -> 搜索索引推进

_tick(dry_run, force=False) = _sync_line(dry_run, flush=False) + _task_line(dry_run, force=force)   # (:899) 完整一轮; 两线同拍时视图只重建一次
```

> 已外迁: 启动期 fail-fast / 主循环与表现层边界 / 分层节拍 / 微步线 / 节流与等待 / 命令线唤醒 / 连接管理 → [attachments/main-loop-details.md](attachments/main-loop-details.md)

`run_due` 内部: 先快照到期任务再逐个执行 (异常捕获内联; 执行中途重新入队的任务留到下一轮), 收尾:
- handler 返回 **FINISHED** → 任务消亡, kind=="check" 释放在途校验标记 (典型: 种子已删除, 由 handler 的删除守卫判定)。
- handler 返回 **REQUEUE** → `_requeue` (taskqueue.py:313) 重新入队, 两分支: 默认按 `task.interval` (`next_run = now + interval`) 且**重置断点** (下一轮从头执行); handler 已挂 `task.retry_delay` 时改按 backoff 推迟到期 (`next_run = now + retry_delay`) 且**保留断点** (从失败动作续跑, 跳过条件评估与去重 —— 重走全流程会被 cooldown/execute_once 拦下, plan 26-11-01-0106 W2/R3)。断点续跑两条路: 队列内 retry backoff (上) 与子任务 `add_task(origin, keep_progress=True)`。

### 每轮 `_refresh_torrents` 的数据流 (理解本项目的关键)

> 已外迁: _refresh_torrents 相位数据流表 / 非刷新相位 / 内核保留职责 / 新增与删除种子前置处理 → [attachments/main-loop-details.md](attachments/main-loop-details.md)
