# 主循环与每轮数据流 — 外迁细节

> 摘要: `systemPatterns/main-loop.md` 的启动期 fail-fast、分层节拍、微步线、节流/等待、连接管理与 `_refresh_torrents` 相位数据流原文(逐字外迁)。
> 触发: 主循环, tick, 分层节拍, 微步线, _wait_next, 命令唤醒, 连接管理, 相位表, _refresh_torrents

> 本文件是外迁存档: 主档该段原文搬来, 仅相对链接整体上移一层(本文件在 `systemPatterns/attachments/`); 节流/等待段已按 2026-11-06 `_throttle` 删除回写, 其余逐字未改。

## 外迁条目

**启动期 fail-fast 与清理(2026-11-03, plan 26-11-03-0930)**: `start_all` 移入 `try` 后, 任何模块 `start` 抛错(`WebUIBindError` / 既有 `HrChannelBindError`)都不再跳过 `finally` —— `stop_all` 幂等拆已启动模块, `lock.release()` 与 `state.lock.meta.json` 在任何路径都释放(连带修掉 HR fail-fast 的既有漏锁)。`lifecycle_ready` 闸门只放行「`start_all` 正常返回」后的退出落盘, 失败启动不在 fresh 目录写空态 `state.json`; 正常运行的非优雅终止丢失窗口语义不变(黄金法则 3)。

**主循环与表现层的边界(P2 门面转正)**: 内核只按节拍调宿主 hooks(`run_command_line`/`run_sync_line`/`run_task_line`, `qbmanager.py:485/663/679`), 「要不要重建视图 / 要不要预取错误原因」等判据全部内聚在表现层 —— 三步收尾单点在 `webui/module.py:82-106`(on_command_line: consume_commands + check_pending / on_sync_line: flush_views / on_task_line: advance_error_reasons → flush_views → advance_search_index)。

**分层节拍 (2026-09-19)**: 主循环拆成**两条独立时间线** —— 同步线(`sync_interval`, 默认 1.5s)只刷新状态不跑任务,
任务线(`main_tick`, 默认 2s)跑任务 + tracker 预取 + 搜索索引。拆开后状态新鲜度不再被任务节拍拖累, 而
`max_tasks_per_tick` 的**速率语义**(20 个/2s = 10 任务/秒)与每 tick 的 qB 请求预算仍由 `main_tick` 唯一决定。
取值 1.5s 的依据: **qB 服务端的 torrent 状态本身按 `BitTorrent/Session/RefreshInterval` 节流刷新**(默认 1500ms;
qB 源码 `sessionimpl.cpp:575` 定义 + `:6009-6027` `enqueueRefresh()` 延迟投递 `post_torrent_updates()`, alert 侧
`:6557/:6736` 自维持循环), 比 qB 自身数据粒度更快没有意义。⚠这是**服务端状态缓存**的粒度, **不是**「qB 自带
WebUI 的轮询选择」—— 任何客户端(含 `/sync/maindata` 与 `/torrents/info`)都拿不到更细粒度, 调快本侧节拍或用
info 直查都不改变这一点(evidence: report 26-10-12-2148 §3 R4 的 26-10-13-0441 补证)。
**第三条时间线: 微步线 (2026-10-21, plan 26-10-21-1857 §4)**: 跳检相位机要求「毫秒级步进、但不许占住主循环」——
每轮只推进一步(至多一次 qB 调用), 步间 10~50ms 退避。它**没有固定节拍**: 到期时刻由模块
`next_micro_run_at()` 上报, 内核把它并入等待超时(`min(同步线, 任务线, 微步线)`); 推进走
`host.run_micro_line(dry_run)`(与另三条线同款 hook, 内核只知「何时」不知「何事」)。暂停时同样跳过。
批量 N 个 job 因此是**并行**推进的: 整批耗时 ≈ 相位深度 × 步间隔, 与 N 基本无关(11 个 ≈ 250ms;
改造前是 6s × N 且全程阻塞同步线)。

❗**不能**退化成"单一 cadence + 任务线在内部按 next_tick_at 门控": 那样任务实际间隔会被循环粒度量化
(1.5s 循环粒 + 2s 任务间隔 ⇒ 实际 3s 一次), 速率语义失真 —— 等待必须用 `min(两条线的到期时间)` 才能各自精确。

**节流 (2026-09-14 修复; 原实现 `_throttle` 已于 2026-11-06 删除)**: 历史上节流由 `_throttle` 承担 —— 非托管模式(CLI 默认, `stop_event=None`)走 `time.sleep(main_tick)`, 托管模式(`--tray` 传入 `stop_event`)走 `Event.wait(main_tick)`。**主循环的节流绝不能依赖 `stop_event` 是否存在** —— 曾写成 `if stop_event is not None and stop_event.wait(main_tick)`, 在非托管模式被 `and` 短路导致**完全不阻塞**, 主循环空转(实测约 2800 tick/s, 为 main_tick=2s 设计值的约 5500 倍), 详见 [pitfalls.md](../../pitfalls.md)。注意首连失败重试循环的语义**不同**: 非托管模式首连失败直接抛错退出(不重试), 不要把它并进主循环的等待原语。

**等待 (`_wait_next`, 2026-09-19 起为唯一等待原语)**: 阻塞到"距最近一条时间线的剩余时间", 同时响应
**命令唤醒**(`manager.wake()`, Web 线程投递命令后调用)与停止信号。`stop_event` 与 `_wake_event` 是两个独立事件,
Python 无多事件等待原语, 故**以唤醒为主**: 阻塞在 `_wake_event` 上(命令到达即返回, 延迟 ≈ 0), 按
`STOP_POLL_INTERVAL=0.5s` 分段, 段间用**非阻塞**的 `stop_event.is_set()` 检查停止。顺序不能反 —— 先阻塞等
`stop_event` 会让唤醒等满一个分段才被看见, 命令延迟从 ≈0 退化到 ≤0.5s。原 `_throttle` 自此退出循环,
因再无生产消费点已于 2026-11-06 删除(直测由 `_wait_next` 的等价覆盖接替)。

**命令线 / 唤醒 (`wake()`, 2026-09-19; 投递归口 2026-09-20)**: Web 侧投递命令统一走
`WebUIRuntime.post_command`(生成 cmd_id + 埋点时间戳 + 入队 + 按需 `manager.wake()`, `webui/runtime.py:556`)⇒ 主循环不等下个节拍
立即消费一次命令(命令延迟 0~main_tick ⇒ ≈0)。`wake()` 本身是**核心域原语**(托盘 UI 停止时也用它打断等待),
不在表现层。❗**只走命令线, 绝不退化成"投递即跑下一轮 tick"**: ① `max_tasks_per_tick` 承载
速率语义, tick 频率一旦由命令决定即失效; ② 存在**自投递命令**(Web 侧索引脏时自己投递 `build_search_index`),
会形成自激循环(唤醒→drain 500 条文件 API→索引仍脏→再投递→立刻再唤醒), 中间没有 tick 兜底 —— 不是变慢, 是
打满 CPU 并冲垮 qB。故自投递命令登记在 `SELF_POSTED_COMMANDS` 里**不唤醒、不带 cmd_id**(单点 `webui/commands.py:31`;
反向守阵 tests/test_web_seed_center.py 扫 webui 侧全部投递点, 未登记即失败)。

**连接管理(首连 + 运行期重连)**:
- **首连失败语义分裂是刻意的**(`qbmanager.py:441-449`): 非托管模式(stop_event=None)抛 `QbConnectError` → CLI 干净退出码 1(fail-fast, docker/compose 靠 restart 策略重拉); 托管模式按 main_tick 重试直至成功或收到停止(托盘应用保持常驻)。
- **运行期断开**: tick 内 `APIConnectionError` 节流 —— 仅"连接态→断开"转换时记一次 ERROR, 断开期间每 tick 重试失败静默(防 qB 宕机刷屏); 同时置 `client=None` 并按 `_reconnect_due` **指数退避**重连(`qbmanager.py:339-351`: main_tick → 2× → 4× …, 上限 `RECONNECT_MAX_INTERVAL=30s`, 常量 `:93` —— 每 tick 无脑重建 Client 含 netrc/代理解析, 纯属空转), 连接成功 `_reset_reconnect_backoff` 归零。
- **断连稳态守卫(issue 26-10-31-1029, 2026-11-01)**: 主循环分派线之前先判 `client is None and _last_conn_ok is False` —— 命中即**跳过全部请求线**, 直接 `_reconnect_due` → `connect()`(成功后本轮立即补一次同步), 两条时间线照常推进(防空转)。判据必须是二元组: `_last_conn_ok=False` 只由断连转换单点置位, 单看 `client is None` 会误伤启动/热重载窗口。为什么必须拦: None client 误入同步线时 AttributeError 被 store `_SYNC_UNAVAILABLE` 误分类成「qB 不支持 sync/maindata」降级再二次 AttributeError, 穿进 except Exception 逐拍刷「主循环异常」, 且该路径不调 `connect()` —— 断连态从此无出口, qB 恢复后永不回连。
- **恢复检测**: 门是 `_ran_line`(本轮真有线跑成功), 非 `sync_due/tick_due` —— 守卫轮两条 due 都可为真却没线跑, 若照旧翻转, 守卫下一轮就被 `_last_conn_ok=True` 绕开。有线跑通且 `_last_conn_ok is False` 时置 True 并记一次 INFO「已重新连接 qBittorrent」——`connect()` 仅启动时调用一次, 运行期断开/恢复只能由 tick 翻转(否则 UI 永远显示断开)。非 `APIConnectionError` 异常照常记 "主循环异常"(exc_info=True)。

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
