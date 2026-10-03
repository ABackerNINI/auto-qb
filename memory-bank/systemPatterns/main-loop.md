# 主循环与每轮数据流

> 📅 **内容基线**: 2026-10-01 @ `38604d07`(内核化重构 P5 收官后逐项对照代码核实)。

> 摘要: 主循环 `core/qbmanager.py` 的节拍、分层与每轮 `_refresh_torrents` 的相位广播数据流。
> 触发: 主循环, tick, 节拍, 数据流, refresh_torrents, 相位广播, 分层

## 主循环 (core/qbmanager.py)

```python
run(dry_run, stop_event=None, pause_event=None):        # qbmanager.py:403
    materialize_schema_migration()   # 配置 schema 启动物化(磁盘落后才写; dry-run 只探测, :423)
    host.start_all(dry_run)          # 模块 start 按装配序: web 服务器 / HR 端点与取数线程 /
                                     # 全局任务自注册(原 _create_global_tasks 点名退役, :435)
    while not connect():             # 首连: 非托管模式失败抛 QbConnectError 干净退出(:441-449);
        ...                          # 托管模式(--tray)按 main_tick 重试直至成功或收到停止
    self.state = ctx.state.load()    # run() 启动再加载一次(:452)
    ctx.state.materialize_migration(dry_run)            # state schema 迁移物化(:456)
    ctx.state.next_flush_at = now + interval            # 周期落盘起点重置(:458)
    host.get("rules")._load_rules()                     # 规则加载在 run() 进行(:459)
    while True:
        main_tick = config.main_tick                    # L0 热重载: 每轮重读
        sync_interval = min(config.sync_interval, main_tick)   # 快档>任务档时钳制(BUG-6)
        _wake_event.clear()
        state_changed = host.run_command_line()         # 命令线(:485): 消费命令+检查在途汇报确认
        if paused: _wait_next(...); continue            # 暂停 = 完全旁观
        sync_due = now >= next_sync_at or (state_changed and not dry_run)  # P0-5 命令后补一次
        tick_due = now >= next_tick_at
        if sync_due and tick_due: _tick(dry_run, force=cmd_forced)   # 两线同拍 -> 完整一轮
        elif sync_due:            _sync_line(dry_run, force=cmd_forced)
        elif tick_due:            _task_line(dry_run, force=cmd_forced)
        web.flush_truths()               # 推迟回执无条件落(:526; 异常路径兜底 :564-565)
        if not dry_run:
            ctx.state.maybe_flush(...)   # 周期落盘(:534-535, 间隔 state_save_interval)
        重连检测(:540-545) + 断开期间退避重连(:557-558)
        _wait_next(stop_event, _wake_event, min(next_sync_at, next_tick_at) - now)
    finally:                             # (:573-580)
        host.stop_all()                  # 模块停用(装配逆序); 状态落盘与锁释放留在其后
        ctx.state.save()                 # 优雅退出落盘(:577-578)
        lock.release()

_sync_line(dry_run, flush=True):         # 同步线 (sync_interval, 默认 1.5s) —— 只刷快照不跑任务
    _refresh_torrents(dry_run)           # 刷新快照 + 相位广播(见下节, :726-832)
    host.run_sync_line(force)            # (:663) 同步线收尾=视图发布; 判据在 webui/module.py:93

_task_line(dry_run):                     # 任务线 (main_tick, 默认 2s)
    task_queue.run_due(dry_run, now, max_tasks)      # (:677) 到期任务执行
    host.run_task_line(force)            # (:679) 任务线收尾三步 = webui/module.py:97-106:
                                         # 错误原因预取 -> 视图发布 -> 搜索索引推进

_tick = _sync_line(flush=False) + _task_line()       # 完整一轮; 两线同拍时视图只重建一次
```

**主循环与表现层的边界(P2 门面转正)**: 内核只按节拍调宿主 hooks(`run_command_line`/`run_sync_line`/`run_task_line`, `qbmanager.py:485/663/679`), 「要不要重建视图 / 要不要预取错误原因」等判据全部内聚在表现层 —— 三步收尾单点在 `webui/module.py:82-106`(on_command_line: consume_commands + check_pending / on_sync_line: flush_views / on_task_line: advance_error_reasons → flush_views → advance_search_index)。

**分层节拍 (2026-09-19)**: 主循环拆成**两条独立时间线** —— 同步线(`sync_interval`, 默认 1.5s)只刷新状态不跑任务,
任务线(`main_tick`, 默认 2s)跑任务 + tracker 预取 + 搜索索引。拆开后状态新鲜度不再被任务节拍拖累, 而
`max_tasks_per_tick` 的**速率语义**(20 个/2s = 10 任务/秒)与每 tick 的 qB 请求预算仍由 `main_tick` 唯一决定。
取值 1.5s 的依据: qB 自带 WebUI **1500ms** 更新一次, 比 qB 自身数据粒度更快没有意义。
❗**不能**退化成"单一 cadence + 任务线在内部按 next_tick_at 门控": 那样任务实际间隔会被循环粒度量化
(1.5s 循环粒 + 2s 任务间隔 ⇒ 实际 3s 一次), 速率语义失真 —— 等待必须用 `min(两条线的到期时间)` 才能各自精确。

**节流 (`_throttle`, 2026-09-14 修复)**: 非托管模式(CLI 默认, `stop_event=None`)走 `time.sleep(main_tick)`; 托管模式(`--tray` 传入 `stop_event`)走 `Event.wait(main_tick)` 以保持停止信号即时响应。**主循环的节流绝不能依赖 `stop_event` 是否存在** —— 曾写成 `if stop_event is not None and stop_event.wait(main_tick)`, 在非托管模式被 `and` 短路导致**完全不阻塞**, 主循环空转(实测约 2800 tick/s, 为 main_tick=2s 设计值的约 5500 倍), 详见 [pitfalls.md](../pitfalls.md)。注意首连失败重试循环的语义**不同**: 非托管模式首连失败直接抛错退出(不重试), 不可改成 `_throttle`。

**等待 (`_wait_next`, 2026-09-19 取代循环里的 `_throttle`)**: 阻塞到"距最近一条时间线的剩余时间", 同时响应
**命令唤醒**(`manager.wake()`, Web 线程投递命令后调用)与停止信号。`stop_event` 与 `_wake_event` 是两个独立事件,
Python 无多事件等待原语, 故**以唤醒为主**: 阻塞在 `_wake_event` 上(命令到达即返回, 延迟 ≈ 0), 按
`STOP_POLL_INTERVAL=0.5s` 分段, 段间用**非阻塞**的 `stop_event.is_set()` 检查停止。顺序不能反 —— 先阻塞等
`stop_event` 会让唤醒等满一个分段才被看见, 命令延迟从 ≈0 退化到 ≤0.5s。`_throttle` 仍保留(被单测直接覆盖),
但循环里不再使用。

**命令线 / 唤醒 (`wake()`, 2026-09-19; 投递归口 2026-09-20)**: Web 侧投递命令统一走
`WebUIRuntime.post_command`(生成 cmd_id + 埋点时间戳 + 入队 + 按需 `manager.wake()`, `webui/runtime.py:556`)⇒ 主循环不等下个节拍
立即消费一次命令(命令延迟 0~main_tick ⇒ ≈0)。`wake()` 本身是**核心域原语**(托盘 UI 停止时也用它打断等待),
不在表现层。❗**只走命令线, 绝不退化成"投递即跑下一轮 tick"**: ① `max_tasks_per_tick` 承载
速率语义, tick 频率一旦由命令决定即失效; ② 存在**自投递命令**(Web 侧索引脏时自己投递 `build_search_index`),
会形成自激循环(唤醒→drain 500 条文件 API→索引仍脏→再投递→立刻再唤醒), 中间没有 tick 兜底 —— 不是变慢, 是
打满 CPU 并冲垮 qB。故自投递命令登记在 `SELF_POSTED_COMMANDS` 里**不唤醒、不带 cmd_id**(单点 `webui/commands.py:31`;
反向守阵 tests/test_web.py 扫 webui 侧全部投递点, 未登记即失败)。

**连接管理(首连 + 运行期重连)**:
- **首连失败语义分裂是刻意的**(`qbmanager.py:441-449`): 非托管模式(stop_event=None)抛 `QbConnectError` → CLI 干净退出码 1(fail-fast, docker/compose 靠 restart 策略重拉); 托管模式按 main_tick 重试直至成功或收到停止(托盘应用保持常驻)。
- **运行期断开**: tick 内 `APIConnectionError` 节流 —— 仅"连接态→断开"转换时记一次 ERROR, 断开期间每 tick 重试失败静默(防 qB 宕机刷屏); 同时置 `client=None` 并按 `_reconnect_due` **指数退避**重连(`qbmanager.py:339-351`: main_tick → 2× → 4× …, 上限 `RECONNECT_MAX_INTERVAL=30s`, 常量 `:93` —— 每 tick 无脑重建 Client 含 netrc/代理解析, 纯属空转), 连接成功 `_reset_reconnect_backoff` 归零。
- **恢复检测**: 任一条时间线跑通后若 `_last_conn_ok is False` 则置 True 并记一次 INFO「已重新连接 qBittorrent」(`:540-545`)——`connect()` 仅启动时调用一次, 运行期断开/恢复只能由 tick 翻转(否则 UI 永远显示断开)。非 `APIConnectionError` 异常照常记 "主循环异常"(exc_info=True)。

`run_due` 内部: 先快照到期任务再逐个执行 (异常捕获内联; 执行中途重新入队的任务留到下一轮), 收尾:
- handler 返回 **FINISHED** → 任务消亡, kind=="check" 释放在途校验标记 (典型: 种子已删除, 由 handler 的删除守卫判定)。
- handler 返回 **REQUEUE** → 按 `task.interval` 重新入队 (`next_run = now + interval`), **默认重置断点** (下一轮从头执行; 断点续跑只经子任务 `add_task(origin, keep_progress=True)` 路径)。

### 每轮 `_refresh_torrents` 的数据流 (理解本项目的关键)

内核只报「何时」: 增量同步完成后按**相位表**(`qbmanager.py:726-832`, plan kernel-module-refactor §4.2)依次广播, 业务步骤全部由认领模块执行, 内核不再点名任何业务步骤:

| 相位 | 内容 | 认领 |
|------|------|------|
| `full_round`(:754, 仅全量轮) | tracker 重匹配(L2 reset_runtime 置空 conf 在此兑现)+ 存量种子级任务补建(L2 重建换队列后种子级任务随旧队列丢弃且 torrents_added 对存量不触发, 重匹配兑现后按队列查重幂等补建、立即到期首轮兑现一次维护, issue 26-10-01-2147) | TrackerModule(tracker_mod.py:40) → RulesModule(rules_mod.py:69, 装配序在后消费重匹配结果) |
| `transitions`(:767, 每轮无条件) | 状态转移观测: 上传转暂停 / errored → 缺文件扫描(用上一轮快照); **必须先于一切自有动作** —— 自有停种经快照同步会当场改写 `by_hash`, 放后面会把自家停种误判为外部转移 | GroupingModule(grouping_mod.py:89) |
| `events_removed`(:778) | on_torrent_deleted / on_torrent_state_enum_changed / on_torrent_field_changed 同步即时分派(deleted 用删除前快照副本, state 用上一轮快照对比); 事件规则**不建周期任务**, 建 rule-event 一次性 Task 作 ctx.task 同步执行, 遇 checking pending 由轮询子任务断点续跑(rules_mod.py:332-355) | RulesModule(rules_mod.py:64) |
| `events_added`(:808) | on_torrent_added —— 新增种子**已匹配 tracker conf 之后**触发 | RulesModule(rules_mod.py:65) |
| `torrents_added`(:815, 逐种子) | 逐新增种子管线: 维护打标 / tracker 限速 / 建任务 / 归组 / 集数标签, 各模块按装配序认领 | maintenance / tracker / rules / grouping(maintenance_mod.py:81 · tracker_mod.py:41 · rules_mod.py:66 · grouping_mod.py:97) |
| `removed_scan`(:822, 仅 removed 非空) | 组内缺文件扫描(剩余种子可能文件丢失, 不等下一轮) | GroupingModule(grouping_mod.py:102) |
| `post`(:826, 每轮) | 保存路径变化重归组 + 跨组文件交叉检测(独立开关 `grouping.cross_group_conflict_check` 默认关; 纯内存零触盘, plan 26-10-04-0107) + 下载冲突检查 | GroupingModule(grouping_mod.py:107) |

两个非 `_refresh_torrents` 的相位: `queue_rebuilt` —— L2 重建队列后请求各模块按当前配置重注册全局任务(已注册的幂等跳过 `TaskQueue.has_named`; 内核 `_create_global_tasks` 只剩兼容转发, `qbmanager.py:692-701`, 认领 maintenance_mod.py:80 / speed_curve_mod.py:104); `rebuild_runtime` —— L2 结构重建 + 未认领段兜底重建, 收进 RulesModule(rules_mod.py:67)。

内核保留职责(不认领): schema 校验(`_validate_torrent_schema`)/ fs 映射自检(首轮一次性)/ 事件重放保护窗口(总线 suppress, **请求位消费点贴 events_removed 臂** `:776` —— take 即 arm 相邻无窗, 失败轮不消费留待下个成功轮, 审计 M1; 仅覆盖 events_removed + events_added 两个事件相位, issue 26-10-01-0750)/ `store.update_state_snapshot()` + `update_field_snapshots()` 数据面收尾(:830-832)。

**新增种子前置处理**(:787-805): 逐个 `ctx.trackers.match(torrent)` 匹配 tracker 配置(hostname 精确匹配, 服务单点 tracker_mod.py:60); 未匹配 → warning + **跳过该种子**(不进 matched_added, 不建任何任务)。

**删除种子**(:817-822): `apply_sync` 返回的 removed 里, 删除前先保留各种子快照副本(供 `on_torrent_deleted` 规则经 ctx 回退只读取档, :760); **任务不显式清理** —— run_due 到期执行时 handler 检测种子缺失自然消亡(`qbmanager.py:818`; TaskQueue 无按种子移除的接口)。

~~`begin_round(...)` 维护上传量快照基线~~ — 已随计划 26-09-27-1232 移除 (upload_size 四条件 + 统计底座整体下线, 见 feature issue 重设计待办)。
