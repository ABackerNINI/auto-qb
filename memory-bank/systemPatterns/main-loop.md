# 主循环与每轮数据流

> 摘要: 主循环 `qbmanager.py` 的节拍、分层与每轮 `_refresh_torrents` 的数据流。
> 触发: 主循环, tick, 节拍, 数据流, refresh_torrents, 分层

## 主循环 (qbmanager.py)

```python
run(dry_run, stop_event=None, pause_event=None):
    connect()                       # _new_client(本地地址 -> LocalQbClient) + auth_log_in
    _load_state(); _load_rules(); _create_global_tasks()
    next_sync_at = next_tick_at = 0.0
    while True:
        main_tick = config.main_tick          # L0 热重载: 每轮重读
        sync_interval = config.sync_interval
        _wake_event.clear()
        state_changed = web.consume_commands()  # 命令线: 被唤醒即消费(不等节拍); 门面内含分发/回执/写序号
        web.check_pending()                     # 强制汇报的 tracker 确认跟踪
        if paused: _wait_next(...); continue   # 暂停 = 完全旁观
        sync_due = now >= next_sync_at or (state_changed and not dry_run)  # P0-5 命令后补一次
        tick_due = now >= next_tick_at
        if sync_due and tick_due: _tick(dry_run)   # 两线同拍 -> 完整一轮, 视图只重建一次
        elif sync_due:            _sync_line(dry_run)
        elif tick_due:            _task_line(dry_run)
        _wait_next(stop_event, _wake_event, min(next_sync_at, next_tick_at) - now)
    finally: save_state()           # 仅退出时落盘

_sync_line(dry_run, flush=True):     # 同步线 (sync_interval, 默认 1.5s)
    _refresh_torrents(dry_run)       # 刷新快照 + 事件/分组
    web.flush_views()                # 消费脏标记 + Web 活跃 + 已取走门控(判据全在门面内)

_task_line(dry_run):                 # 任务线 (main_tick, 默认 2s)
    web.advance_error_reasons()      # 门面内判"Web 活跃"; tracker 预取跟 main_tick, **不跟快档**
    task_queue.run_due(dry_run, now=now, max_tasks=max_tasks_per_tick)
    web.flush_views()
    web.advance_search_index()       # 门面内判"Web 活跃且脏"; 文件 API 同样只跟 main_tick

_tick(dry_run) = _sync_line(flush=False) + _task_line()   # 完整一轮; 两线同时到期时走它
```

**分层节拍 (2026-09-19)**: 主循环拆成**两条独立时间线** —— 同步线(`sync_interval`, 默认 1.5s)只刷新状态不跑任务,
任务线(`main_tick`, 默认 2s)跑任务 + tracker 预取 + 搜索索引。拆开后状态新鲜度不再被任务节拍拖累, 而
`max_tasks_per_tick` 的**速率语义**(20 个/2s = 10 任务/秒)与每 tick 的 qB 请求预算仍由 `main_tick` 唯一决定。
取值 1.5s 的依据: qB 自带 WebUI **1500ms** 更新一次, 比 qB 自身数据粒度更快没有意义。
❗**不能**退化成"单一 cadence + 任务线在内部按 next_tick_at 门控": 那样任务实际间隔会被循环粒度量化
(1.5s 循环粒 + 2s 任务间隔 ⇒ 实际 3s 一次), 速率语义失真 —— 等待必须用 `min(两条线的到期时间)` 才能各自精确。

**节流 (`_throttle`, 2026-09-14 修复)**: 非托管模式(CLI 默认, `stop_event=None`)走 `time.sleep(main_tick)`; 托管模式(`--tray` 传入 `stop_event`)走 `Event.wait(main_tick)` 以保持停止信号即时响应。**主循环的节流绝不能依赖 `stop_event` 是否存在** —— 曾写成 `if stop_event is not None and stop_event.wait(main_tick)`, 在非托管模式被 `and` 短路导致**完全不阻塞**, 主循环空转(实测约 2800 tick/s, 为 main_tick=2s 设计值的约 5500 倍), 详见 [pitfalls.md](pitfalls.md)。注意首连失败重试循环(`while not self.connect()`)的语义**不同**: 非托管模式首连失败直接返回(不重试), 不可改成 `_throttle`。

**等待 (`_wait_next`, 2026-09-19 取代循环里的 `_throttle`)**: 阻塞到"距最近一条时间线的剩余时间", 同时响应
**命令唤醒**(`manager.wake()`, Web 线程投递命令后调用)与停止信号。`stop_event` 与 `_wake_event` 是两个独立事件,
Python 无多事件等待原语, 故**以唤醒为主**: 阻塞在 `_wake_event` 上(命令到达即返回, 延迟 ≈ 0), 按
`STOP_POLL_INTERVAL=0.5s` 分段, 段间用**非阻塞**的 `stop_event.is_set()` 检查停止。顺序不能反 —— 先阻塞等
`stop_event` 会让唤醒等满一个分段才被看见, 命令延迟从 ≈0 退化到 ≤0.5s。`_throttle` 仍保留(被单测直接覆盖),
但循环里不再使用。

**命令线 / 唤醒 (`wake()`, 2026-09-19; 投递归口 2026-09-20)**: Web 侧投递命令统一走
`WebUIRuntime.post_command`(生成 cmd_id + 埋点时间戳 + 入队 + 按需 `manager.wake()`)⇒ 主循环不等下个节拍
立即消费一次命令(命令延迟 0~main_tick ⇒ ≈0)。`wake()` 本身是**核心域原语**(托盘 UI 停止时也用它打断等待),
不在表现层。❗**只走命令线, 绝不退化成"投递即跑下一轮 tick"**: ① `max_tasks_per_tick` 承载
速率语义, tick 频率一旦由命令决定即失效; ② 存在**自投递命令**(Web 侧索引脏时自己投递 `build_search_index`),
会形成自激循环(唤醒→drain 500 条文件 API→索引仍脏→再投递→立刻再唤醒), 中间没有 tick 兜底 —— 不是变慢, 是
打满 CPU 并冲垮 qB。故自投递命令登记在 `SELF_POSTED_COMMANDS` 里**不唤醒、不带 cmd_id**(有静态反向守卫: 扫
`web_view.py` 里所有 `web_commands.put(` 与 `web.post_command(` 的 cmd 名, 未登记即失败 —— 2026-09-20 起两种
写法都认)。

连接恢复检测: 任一条时间线跑通(即 API 可达)后若 `_last_conn_ok is False` 则置 True 并记一次"已重新连接"——`connect()` 仅启动时调用一次, 运行期断开/恢复只能由 tick 翻转(否则 UI 永远显示断开)。连接异常节流 (2026-09-12): 运行期 tick 内的 `APIConnectionError` 经 `_last_conn_ok` 状态机节流 — 仅"连接态→断开"转换时记一次 ERROR, 恢复时记一次 INFO("已重新连接 qBittorrent", `connect()` 内), 断开期间每 tick 重试失败静默 (防 qB 宕机刷屏); 非 `APIConnectionError` 异常照常记 "主循环异常"(exc_info=True)。启动首连失败 → `connect()` 返回 False → `run` 直接结束。

`run_due` 内部: 先快照到期任务再逐个执行 (异常捕获内联; 执行中途重新入队的任务留到下一轮), 收尾:
- handler 返回 **FINISHED** → 任务消亡, kind=="check" 释放在途校验标记 (典型: 种子已删除, 由 handler 的删除守卫判定)。
- handler 返回 **REQUEUE** → 按 `task.interval` 重新入队 (`next_run = now + interval`), **默认重置断点** (下一轮从头执行; 断点续跑只经子任务 `add_task(origin, keep_progress=True)` 路径)。

### 每轮 `_refresh_torrents` 的数据流 (理解本项目的关键)

1. `store.apply_sync(api)` → qB `/api/v2/sync/maindata?rid=` **增量**拉取(只含变化种子的变化字段) → 直接应用到快照 → 返回 `(added, removed)`; 已存在记录只更新 patch 中出现的字段(`TorrentRecord.apply_delta`), 惰性缓存跨 tick 保留。细节见下节「增量同步」。
2. **状态转移观测** (grouping.enabled, 先于一切自有动作): `_handle_state_transitions` (上传转暂停 / 进入 errored(重校验发现文件缺失) → 缺文件扫描, 用上一轮 `store.state_snapshot`)。**顺序约束**: 自有停种 (大小一致性/冲突整组暂停) 经 QbApi 快照同步会**当场改写 `by_hash` 状态**, 此观测若放在自有动作之后会把自家停种误判为外部"上传转暂停"。
2.5 **事件分派** (on_* trigger 规则, 同步即时): `_dispatch_events` — 在 `apply_sync` 之后、自有动作之前、`update_state_snapshot` 之前的分派点执行各事件规则 (added 事件用本轮 added 列表, deleted 事件用 `apply_sync` 返回的 removed 及其删除前快照副本, state 变化事件用上一轮 `state_snapshot` 对比本轮 `store.state_changed` 变化集)。事件规则**不建周期任务**, 由 `_apply_event_rule` 同步建 rule-event 一次性 Task 作 `ctx.task` 并 `rule.process`; 遇 checking 返回 pending 时, 该 rule-event 任务作 origin 由轮询子任务 `add_task` 重新入队, 下 tick `_handle_event_rule` 断点续跑后 FINISHED 消亡。`max_tasks_per_tick` 不约束此即时分派 (设计详见 progress.md 事件触发规划)。
3. **新增种子** 逐个处理:
   - `_match_tracker_conf(torrent)` 匹配 tracker 配置 (hostname 精确匹配, 命中多个配置时打 ERROR 日志并用第一个); 未匹配 → warning + **跳过该种子**(不创建任何任务)。
   - `torrent.tracker_conf = tracker_conf` (记录引用, 后续任务直接用)。
   - `_apply_speed_limit` tracker 单种限速 (尊重奇数保护)。
   - `_create_torrent_tasks`: 创建 `maintenance` 内置任务 + 该种子应绑定的每条规则一个任务。
   - `_assign_new_torrent` (grouping.enabled): 按文件列表增量归组 + 大小一致性检查。
   - `_add_episode_tags` (add_episode_tags.enabled): 集数标签 (单/多集模板 + 连续性判定)。
4. **删除种子**: `apply_sync` 返回的 removed 里, 删除前先保留各种子快照副本 (供 `on_torrent_deleted` 规则经 `ctx.torrent`/`snapshot` 读取); `task_queue.remove_torrent(hash)` 移除该种子全部任务 (含让位任务/在途校验标记); grouping 启用时 `_handle_removed_torrents` → 组内缺文件扫描; `_dispatch_events` 的 deleted 分支随后触发 `on_torrent_deleted` 规则。
5. **分组事件处理** (grouping.enabled): `_handle_save_path_changes` (重归组+两侧扫描)、`_check_download_conflicts` (每轮)。
6. `store.update_state_snapshot()` 保存本轮状态快照 (由 `by_hash` 派生 `state_enum` 枚举对象, 跨 qB 版本; 自有动作经 QbApi 同步过的状态同样计入)。
7. `begin_round(...)` 维护上传量快照基线 (daily/weekly/monthly, 周期切换重建基线)。
