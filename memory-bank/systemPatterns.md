# System Patterns — 架构与运行时

> 📅 内容基线: 2026-09-05 @ `51374bd` (全库逐文件核实, 见本库 [README.md](README.md)); 文内带日期条目为增量更新, 最新易变状态见 [activeContext.md](activeContext.md)。

## 组件总览

```
                    ┌──────────────────────────────────────────────────┐
                    │ QbManager (qbmanager.py)                         │
                    │  = RuleEngineMixin + TagsMixin + CheckingMixin   │
                    │    + GroupingMixin + TrackerMixin + SpeedCurveMixin
                    │    + WebviewMixin + WebCommandsMixin (2026-09-15 拆分)
                    │    客户端构造在 qbclient.py(_new_client/LocalQbClient) │
                    ├──────────────────────────────────────────────────┤
  每tick增量同步 →│ TorrentStore (torrents.py)   ← 快照同步 ──  QbApi (qbapi.py) ──→ qbittorrent-api Client
                    │  快照/惰性缓存/分组索引        (写后同步)      APIFacade
                    │  ↑ apply_sync (sync/maindata rid 增量)
                    ├──────────────────────────────────────────────────┤
                    │ TaskQueue (taskqueue.py)  单一时间优先堆          │
                    │  Task: internal / rule / check / check-wait      │
                    ├──────────────────────────────────────────────────┤
                    │ rules/ : Rule + 15条件插件 + 11动作插件 (registry) │
                    └──────────────────────────────────────────────────┘
                    state(state_file JSON) ← 仅退出时落盘
```

**组合关系**: `QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin, SpeedCurveMixin, WebviewMixin, WebCommandsMixin)`(2026-09-15 由 6 mixin 扩至 8, 同日拆分出 qbclient.py) — mixin 依赖宿主实例属性 (`config`/`store`/`api`/`state`/`task_queue`/`client`), 各 mixin 文件头部 docstring 声明了所依赖的属性, 新 mixin 照此模式写。`__init__` 是唯一组合根, 但**实例状态分两层**: 核心域状态(`store`/`api`/`task_queue`/`state`/`_wake_event` …)留在 `__init__`; **WEB 表现层状态全部在 `self.web`(`WebUIRuntime` 门面, 2026-09-20 拆出 19 个字段)** —— mixin 仍是纯方法簇(构建器只产出 dict, 命令处理器只发一次写操作), 快照/版本号/回执/索引/活跃心跳一概不留在宿主上。

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

## 增量同步 (torrents.py, 2026-09-13)

**动机**: 原先每 tick 全量 `torrents/info`, qB 端必须反复序列化**全部**种子 (~45 字段 × N), 种子库大时 qB CPU 明显上涨。改走 qB 自带 WebUI 同款的 `/api/v2/sync/maindata`:

- **qB 端语义** (`src/webui/api/synccontroller.cpp`): rid 与上次一致时只回**变化种子的变化字段** (`processMap` 逐字段 diff), **未变化种子完全不出现在响应中**; 删除的种子列在 `torrents_removed`; 新增种子(基线缺失)回全量字段; rid 不匹配/为 0 时 `full_update=true` 回全量。**自愈性**: 漏 tick/rid 错位/qB 重启都只会退化成一次全量, 不会丢数据。
- **字段齐平**: sync 与 `torrents/info` 共用同一 C++ 序列化器 `serialize/serialize_torrent.{h,cpp}` (sync 仅额外移除 `"id"` 键) —— 故 `REQUIRED_TORRENT_FIELDS` 全部字段(含 `share_limit_action`/`inactive_seeding_time_limit`)在 sync 响应中同样存在。
- **`TorrentStore.apply_sync(api)`**: 拉取一轮并应用; `rid`/`need_validate`/`using_fallback`/`validate_sample` 等同步态内聚于 store(无独立同步对象); `reset_sync()` 在重连/热重载时清基线强制下轮全量; 未知异常 rid 归零后原样上抛(由主循环兜底)。
- **`_apply(patches, removed, full)`**: 增量时只对 `patches` 中的记录调 `TorrentRecord.apply_delta`(其余记录原样保留 —— 对象身份跨轮不变, 惰性缓存存活); 全量时以响应为全集重建(未出现者视为删除)。**无变化轮提前返回, 不重建 `by_hash`**。
- **单调基数据归属**: 快照字段存 `TorrentRecord` 的 slots(C 级属性访问); 非快照必需字段(`RE_ADD_FIELDS`, 跳检重加用)存 `_raw` dict, 属性访问经 `__getattr__` 兜底(缺失抛 `AttributeError`, 与 `AttrDict` 语义一致, 故 `hasattr` 版本校验照常工作)。
- **降级**: 端点不可用(旧版 qB / 测试替身缺 `sync_maindata`) → 捕获 `AttributeError`/`NotFound404Error` → 回退全量 `torrents_info()`(一次性 WARNING 去重), 语义与改造前一致。

### 本轮变化集 O(变化数) 驱动下游

`store` 在应用时顺手收集变化集, 使下游 O(N) 扫描可以按变化数进行(2026-09-13 性能修复):

| 字段 | 含义 | 消费方 |
|------|------|--------|
| `delta_fields` | `{hash: 变化字段名集合}` | `_handle_save_path_changes`(只看 save_path 变化) |
| `state_changed` | `[(hash, fetch 时 state_enum)]` | `_handle_state_transitions`、`_dispatch_events` 状态变化分支 |
| `dirty_groups` | 需重算下载冲突的组 key | `_check_download_conflicts`(登记于字段变化/成员增删/归组/自有停种打标) |

`dirty_groups` 跨轮累积(`_apply` 不清空), 由 `_check_download_conflicts` 取出并复位 —— 故轮次外的写操作(Web 命令/任务队列)登记不会丢。`rounds_applied` 为 0(直接驱动该方法的白盒测试/外部调用, 无变化集)时退回全量扫描。

**本地 qB 跳过 env/netrc 解析** (2026-09-14 修复为真正生效): `_new_client()` 对本地地址(`127.0.0.1`/`localhost`/`::1`, 取 `base_url` 解析后的 hostname 判定)构造 `LocalQbClient`(Client 子类, 覆盖 `_session` property 强制 `trust_env=False`), 省掉每请求的 `get_environ_proxies`/`get_netrc_auth`(环境代理与 `~/.netrc` 解析; 实测单请求 0.276ms -> 0.043ms); 远程地址用原生 `Client`(企业代理/`~/.netrc` 可能真实需要)。旧实现 `client._session.trust_env = False` **从未生效**(库在首次请求/登录重建时丢弃 Session), 详见 [pitfalls.md](pitfalls.md)。

## 启动期版本兼容校验 (2026-09-06, 2026-09-13 调整)

`_refresh_torrents` 在**全量轮**(`store.need_validate`: 首轮/rid 失效/降级)对 `store.validate_sample` 校验 `REQUIRED_TORRENT_FIELDS` (快照字段 + 跳检重加字段, 共 27 个), 缺失抛 `QbCompatError(AutoQbError)` → tick 循环 `except AutoQbError: raise` 穿透"主循环异常"捕获 → CLI stderr 干净退出。

样本为 **qB 响应原始字段映射**: sync 路径取全量响应首个 patch dict 并**补回 `hash`**(值是 `torrents[hash]`, hash 只在键上 —— 不补会误报缺字段导致启动退出); 降级路径取首个非 dict 的真实种子对象 —— 测试注入的 plain dict 不作样本。`missing_torrent_fields` 因此支持两类来源: 映射按键判定(`f not in tor`)、对象按 `hasattr` 判定。**增量轮不校验** (响应只含变化字段, 校验必误报), 由 `need_validate` 闸门控制。通过后置 `_schema_validated` 不再重复 (qB 版本运行期不变); 空 qB 时样本为 `None` → 跳过。设计动机: 快照字段缺失会**静默零值** (规则基于假数据决策), 比崩溃更危险 —— qB 5.0 preferences 键漂移前科。

## 任务队列 (taskqueue.py) — 单队列模型

> README "设计要点"已同步为单队列描述 (2026-09-05): 所有任务(含校验结果轮询)统一进一个 `heapq` 最小堆 `_fast`, 按 `next_run` 到期弹出。

- **Task 字段**: `uid`(kind:name:hash:monotonic_ns), `kind`, `name`, `hash`, `tracker_conf`, `next_run`, `interval` (<=0 归一化为 1s), `state`, `resume_index` (规则断点), `run_count`, `payload`, `handler`。
- **Task.kind**: `internal` (全局任务 + 种子级 maintenance), `rule` (种子级规则扫描), `rule-event` (事件规则一次性任务, 作 origin 被轮询子任务重新入队续跑, 恒 FINISHED 不自我周期循环), `check` (校验结果轮询), `check-wait` (组内校验等待)。文档中也用 `refresh` 指种子刷新 (它不是队列里的任务, 是每 tick 固定第一步)。
- **Task.state**: `PENDING`(排队) / `RUNNING`(已弹出执行中)。
- **Task 断点**: `resume_index` 默认记住执行位置; `has_breakpoint` 属性查询; `reset()` 显式重置。
- **handler 返回值**: `REQUEUE`(True, 按 interval 重入队) / `FINISHED`(False, 本轮不重入: 消亡并释放在途登记, 或由其子任务负责重新入队)。

### 线程模型 (重要约束)

**主循环所在线程是唯一修改任务队列结构与 state_file 的线程, 全程无锁。** 控制台模式下即主线程; `--tray` 模式下主循环整体移入后台线程(主线程为 UI), 约束语义不变。 full-checking 等异步效果不是靠工作线程改队列, 而是: 主循环发 API 请求 (同步返回, 校验后台异步进行), 由队列中的 check 轮询子任务每 2s 读 store 快照判断结果。任何新功能都必须维持这个假设。

### WEB UI 线程模型 (web.py, 2026-09-13)

- **Web 线程(uvicorn 独立线程)只做两件事**: 读只读快照(`manager.web.*` 的视图/流量快照与 `status_snapshot`)与经 `manager.web.post_command()` 投递命令 —— 暂停/开始/汇报/删除/热重载等写操作全由主循环 `web.consume_commands()` 消费执行(单一写线程约束不变); Web 线程不得触碰 store/队列/state_file。**表现层状态归 `WebUIRuntime`(2026-09-20)**: 视图快照/版本号/脏标记/活跃心跳/回执/搜索索引/命令队列都在 `manager.web`; 旧字段名(`manager._group_view` 等)经 `_WEB_STATE_ALIAS` 代理转发, 属过渡层, 新代码一律写 `manager.web.<新名>`。
- **热重载重启 WEB 服务 (2026-09-14, `_apply_web_config`)**: `web` 段虽是 L1, 但**只在"监听身份"(`enabled`/`host`/`port`)真变化时才重启** —— 密钥(`web.token`)鉴权每请求实时读 `manager._web_token`, 原实现只靠“顺带重启”生效, 导致改个日志级别也会把服务器拆了重建。重启次序**必须是 `stop_web_server(handle)`(置 `should_exit` **并 join 等线程退出**) -> 启新服务**: uvicorn 的 `should_exit` 只被其主循环每 0.1s 读一次, 之后才 `server.close()` 释放监听套接字, 不等就启新服务会撞 `Errno 10048` 且旧句柄指向已死 server(后续热重载行为不确定), 详见 [pitfalls.md](pitfalls.md)。
- **惰性组装 + 活跃窗口**: 四份视图与 `_search_index`(搜索索引)均只在主循环构建, 且仅当 `web.last_seen` 距今 < `WEB_VIEW_TTL`(10s, 常量在 `web_runtime.py`) 时推进 —— 关闭网页后主循环不空转。**精确置脏**: 门面的 `flush_views()` 消费 `store.consume_view_changed()`, 仅视图字段/成员**真有变化**时才重建 (不再每 tick 无条件置脏 —— 静止种子库不再每 2s 重建); 置脏**必须**在 `grouping.enabled` 门控之外(脏标记服务**全部**四份视图, 与分组功能是否启用无关)。`web.ensure_view()` 作 Web 请求侧兜底(脏则即时重建)。**重建唯一入口 = `WebUIRuntime._publish_locked()`**(2026-09-20 从 `WebviewMixin.rebuild_views` 迁来): groups/singles/shows/flat 四份 + 版本号 + 清标记在同一次 `view_lock` 临界区内完成, 主循环与 Web 线程都只调它 —— 两处各建一部分会让漏建的视图长期停在旧快照(2026-09-18 缺陷, 详见 pitfalls)。
- **视图版本门控 (等价 qB 的 rid)**: `_group_view_ver` 每次重建自增; `ensure_group_state(rid)` 在 rid 与服务端版本一致时**不回传 groups**(响应体趋近于零), 仅回 status(标量 + `traffic` 与 `server` 快照, 与版本无关恒回传 —— `server` 即 `store.server_state`, 状态栏常显统计与"限制速度"的数据源, 2026-09-18 起随 `/api/state` 回传, 免得状态栏与行数据的刷新频率被解耦)。`/api/state?rid=` 暴露该语义, 前端据此跳过整表替换与重渲染。前端另配: 页面隐藏(`document.hidden`)停轮询、恢复即刷; `setTimeout` 链式续排(不堆叠请求); **只做失败退避**(`pollFails` 翻倍至 15s 上限), 不做"无变化退避"。
- **搜索索引 `_search_index` (hash -> {name, files})**: 种子名匹配即时扫 `store.by_hash`(无 API 开销), 文件列表匹配依赖索引(文件 API 只在主循环线程, 种子记录 `_files` 缓存跨 tick 复用)。索引按 hash **增量**维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已删种子淘汰; 单次限流 `SEARCH_INDEX_BUILD_BUDGET`(500)条, 未拉完保持 `_search_index_dirty=True` 由下一 tick 续建, 前端据 `building` 每 1s 自动重查。
- **搜索结果是辅种组的筛选**: 前端用命中 hash 集合过滤 `sortedGroups`(组行沿用真实组 key, 组级操作可用); 未归组命中种子以虚拟行兜底 —— 组级路由 key 必须能过 `decode_group_key`, 虚拟 key 会让解码失败 500, 详见 [pitfalls.md](pitfalls.md)。
- **前端筛选/列/右键(2026-09-14 打磨, 纯前端无后端参与)**: ①**列模型** `GROUP_COLUMNS`/`DETAIL_COLUMNS` 是列头/单元格/grid 模板/列选择器的单一来源, 列宽按**列 key** 存 `autoqb_cols_v4`(`widths/hidden/manual/order`; **v4 已冻结 —— R10-09(2026-09-17)起列集变更与结构扩展一律不升版本**: 新增列在旧缓存里只是"没有记录"回退 `tpl` 默认宽, 已删列的残留 px 由 `loadColState()` 按当前列 key 求交集洗净, 都不会错配; v3→v4(新增 "H&R"/"分享率")是唯一一次因列集变更升版本, 已判定为错误决策 —— 升版本等于把用户手调的宽/隐/序清零); 拖某列**只改该列**(起始时先固化全部可见列为 px), 双击分隔线按内容自适应, Shift+拖与相邻列互挤; 未手动调过时随窗口重新实体化(填满容器)。列选择器位于**搜索框右侧**(想法.md 要求), 选项改为“无勾选框 + 整行点击切换”并与筛选弹层统一样式(左对齐 + 固定宽 300px, 不再随按钮宽度漂移)。②**筛选器**: 状态 chip(点选) + **路径/标签/分类/站点四个多选弹层**(统一由 `filterDefs` 一份定义驱动, 选项与计数由前端从 `groups[].members` 聚合, 计数口径 = 包含该值的**组数**); 同一筛选器内为"或", 不同筛选器间为"且"。**位置固定**靠三件事: 按钮定宽(`min-width` + `justify-content:center`)、计数徽标 `position:absolute`(不参与布局)、"清除筛选"按钮常驻占位(`visibility:hidden` 而非 `v-if`)。③**排序**: 默认 `added_on` 降序(组内**最近添加**时间, 组级取成员 max); 列头点击为**三态**循环 —— 降序 → 升序 → 恢复默认(`DEFAULT_SORT`); 同值时按名称排序保证稳定。④**右键菜单**: 只弹菜单**不展开明细**(展开仅靠左键点行); 顺序为正操作(开始)在前、破坏性(删除)在最后, 图标按语义着色; 删除只有**一个**菜单项, "是否连带磁盘文件"由确认框内的勾选框决定(`confirmWithOption()` 返回 `{checked}` 或 null, 与 `confirmDialog()` 的布尔契约互不影响)。
- **视图含“由配置派生的展示值”(2026-09-14)**: 成员视图除原始快照值外, 还透出 HR 展示字段(由 `qbmanager._hr_view_fields` 统一计算):
  - `hr_tag`/`hr_tag_done`: 已触发 HR 未达标 / 已达标时应有的**标签文本**(供前端把 HR 标签分别着成鲜亮/镇静两色) —— 经 `utils.replace_vars` 展开(`${required_seeding_time}`), 与真正写入 qB 的标签逐字相等(前端只需文本匹配)。
  - `hr_triggered`/`hr_satisfied`: 是否触发 HR / 是否已达成要求(前端 H&R 栏与对照列着色的依据)。
  - `hr_req_time`/`hr_req_ratio`: 要求做种时长(= required + extra)与要求分享率(0 = 不要求); 供明细表显示 `实际 / 要求` 并**按列各自的要求**决定是否着色(未配要求的列必须保持中性色)。

  判定全部委托 `check_hr_condition`/`check_hr_satisfied`(与打标签流程同一语义), **不得在 JS 里重算模板或阈值**。组级另透出 `hr_triggered`(分母: 已触发成员数) 与 `hr_pending`(分子: 已触发未达标成员数), 由后端算好, 前端只显示。**这类派生值的置脏来源比纯粹的快照字段多一个**: 除 `_VIEW_FIELDS`(seeding_time/ratio/progress 变化会经 `store.view_changed` 驱动)外, 配置热重载也会改变它(标签模板里的 `${required_seeding_time}`) —— 故 `apply_new_config` 必须显式 `_group_view_dirty = True`。
- **需额外调 API 的派生展示值: 错误原因(2026-09-18, TASK015)**: 错误状态种子的**具体原因**是"派生展示值"的第二种来源 —— 它既不是快照字段(qB `torrents/info` **没有**错误文本字段), 也不能在视图组装里现取(视图每 tick 可能重建, 发 API 会拖死主循环)。定式: **主循环按 TTL + 单轮预算预取 → 写进记录的非快照缓存槽 → 视图只读缓存**。
  - 缓存槽 `TorrentRecord.tracker_error_msg`/`tracker_error_ts` 刻意**不进** `_SNAPSHOT_FIELDS`/`_raw`(不参与 `apply_delta`/`store.view_changed`/快照槽守卫), 因此**变化必须由预取方显式 `_group_view_dirty = True`** —— 与上面 HR 派生值同一判别法: **值能在种子数据一字未变时变化 ⇒ 变化方负责置脏**。
  - 取数限额是**必需**而非优化: `ERROR_REASON_BUDGET = 5` 条/轮(错误种子会成片, 全量拉会卡主循环) + `ERROR_REASON_TTL = 300s`(tracker `msg` 随站点状态变化, 不能永久缓存); **先写时间戳再拉取**(失败也不在 TTL 内反复重试); `missingFiles` 原因自明故**不花预算**; 预取与视图重建/搜索索引同门控(网页关掉不发请求); qB 断连时**保持现值不清空**(待连接恢复再刷)。
  - 展示口径单点在后端 `_error_reason`(`missingFiles`→"文件丢失"; `error`→预取文本否则"错误"; 非错误→空串), 视图透出 `error_reason`, 前端 `stateText(m)` 仅错误态采用 —— **前端不得按 state 猜原因**。
- **限速/流量只读快照 `_traffic_view`(2026-09-14)**: 限速曲线任务每次执行后由 `SpeedCurveMixin._publish_traffic` **整体替换**该 dict(Web 线程只读引用, 无锁即自洽), 经 `/api/status` 与 `/api/state` 的 `status.traffic` 恒回传(**不参与 rid 门控** —— 它的数据源是曲线任务而非分组视图, 掺进版本门控会与 groups 的脏语义耦合)。结构: `{ts, date, state, periods[{period,label,up,down}], limit{target{up,down}, actual{up,down}, reasons[{dir,code,text}]}}`; `state` ∈ `disabled`(未启用曲线, 前端整组 pill 不渲染) / `ok` / `dry_run`(只有 target, 不读不写) / `stale`(数据源缺失或无有效行, 本轮不动限速)。**单位**: `periods[].up|down` 为**字节**, `limit.target|actual` 为 **KiB/s**(0 = 不限速, null = 该方向不管理 —— 前端跳过该方向)。`reasons` 让前端能回答“为何命中与实际不一致”(如 `manual` = 当前为奇数 KiB 疑似手动设置故不覆盖; `read_failed` = 写入后回读失败), 前端只按方向取对应原因的文本, 不自己拼原因。

### WEB UI 前端渲染与响应性 (2026-09-19, P0/P1 波次)

**总原则: 感知延迟与真实延迟分开治。** 用户说"不跟手"时第一反应常是"后端慢", 但剖面显示
**主因是"沉默"**(点击后 0.5~6.5s 无任何反馈), 所以收益最大的一项是**乐观 UI**, 后端加速
(命令唤醒 / 命令后立即刷新)只负责把真值对齐时间压到百毫秒级。

- **命令线 / tick 线解耦**: `wake()` + `_wake_event` 只触发"消费命令", **不触发 tick** ——
  否则 `max_tasks_per_tick` 的速率语义失效, 且自投递命令(`build_search_index`)会形成自激循环
  ⇒ `SELF_POSTED_COMMANDS` 白名单里的命令不唤醒。
- **命令后补刷新走完整 `_refresh_torrents()`**: 绝不单独调 `store.apply_sync()`(只更 `by_hash`
  与 `server_state`, 分组/任务/事件/索引全不管 ⇒ 留下半刷新态); 整批命令 drain 完**只补一次**。
- **乐观 UI 只做白名单(pause/resume)**: `pendingOps[hash] = {patch, prev, ts}`, 真值匹配即清,
  3s 兜底回落, **失败立即回滚**。
  - ✅ **3s 兜底会显式回滚到 `op.prev`**(2026-09-19,
    [issue 26-09-19-2141](issues/26-09-19-2141-bug-webui-pending-timeout-stale-patch.html)):
    `_expirePending()` 在每轮 `refresh()` 里先回滚超时的补丁再 `delete`, 与失败回滚同一写法。
    - ❗**光 `delete` 不叫"回落真值"**: 旧写法只删 pendingOps、注释称"下轮以服务端为准", 而 rid
      未变时服务端**不回传数组**、行对象不被替换 ⇒ 补丁值永久留在行上(命令没执行却一直显示已暂停,
      hang 模式实测 3.66s 后行仍是 `s-paused`)。**要回到真值就必须显式写回 `op.prev`。**
    - ❗`isPending()` 超时**只返回 false、不 delete**: 模板每帧都调它, 在渲染函数里改响应式数据有
      递归更新风险; 回滚统一交给 `_expirePending()`(代价: 过期条目最多多活一个轮询周期)。
  - ✅ **「真值匹配即清」已落地**(2026-09-19, [issue 26-09-19-2024](issues/26-09-19-2024-bug-webui-truth-convergence.html)):
    `refresh()` 拿到新数据时先 `_snapshotTruth()` 记下 pending hash 的**服务端原始值**,
    `reapplyPending()` 比它 ⇒ 对齐就 `delete`。回执后 `_pullTruthAfterCmd()` 立刻 refresh
    (不等轮询), 短退避 200→400ms 重试, 总窗口 1.5s, 超时仍由 3s 兜底收尾。
    - ❗**必须比服务端快照, 不能比行上的当前值**: 行在上一轮已被贴过补丁, 拿它跟补丁比 = 跟自己比
      ⇒ 首轮必"匹配"、pending 立刻消失(实测 22ms); 且 `updated === false`(rid 未变)时行对象
      根本没被换掉, 这个假匹配更容易发生。快照**拷值不拷引用**(赋值后与 payload 是同一批对象)。
    - ❗只认本轮 payload **真的带了**的 hash: 追剧视图 `view=show` 回 shows+groups+singles,
      成员真值走 groups 取到; 若某 hash 不在本轮 payload 里 ⇒ 不算对齐, 继续贴、交给 3s 兜底。
  - ❗**补丁必须先于 POST 贴上**(4 条入口: `act` / `actTorrent` / `actEpisode` / bulk 一律如此)。
    放在 `await POST` 之后 = 把"点击即变"押在网络往返上 —— 受控测量(注入 2000ms POST 延迟):
    修前补丁 2012ms 才贴, 修后 0ms(issue 26-09-19-1939, 用户真机报"点了 2-4s 才变")。
    POST 失败走 `resolveOptimistic(hashes, false)` 回滚, 不留假状态。
  - ❗**3s 兜底从「回执到达」起算**(成功时刷 `op.ts`), 不是从点击起算: 补丁提前后若按点击算,
    慢 POST 会在命令刚完成时就烧光窗口 ⇒ 弹回陈旧真值。**无回执(hang)不刷新 ts**, 3s 后照旧回落。
  - 埋点: `cmdStats` 含点击侧两段(`patchMs` / `postMs`)与回执段(`waitMs` / `execMs` / `totalMs`),
    阈值 补丁>50 / POST>400 / 排队>100 / 端到端>400 打 `[perf]` —— **「点击 → 投递」曾经是盲区**。
- **按视图回传**: `/api/state?view=group|torrent|show` 只回该视图数组; 前端赋值必须
  "键不存在则保留原引用"(否则另外两个视图每轮被抹空)。
- **只读端点短缓存 key 含 `_web_write_seq`**: 写后自动失效; **断连检查必须在查缓存之前**
  (否则 qB 断开仍返回缓存 200, 把断连藏起来)。
- **行窗口化(P1-2)是渲染侧最大的一刀**: 核心约束是**只减 DOM 行数, 不改布局模型** ——
  行仍是 flex 列里"渲染完整单元格序列"的元素, 只靠上下两个 `.row-pad` 占位撑高度,
  这样 `:nth-child` 列对齐与 `[data-table]` 列宽协议全部保持有效。高度必须**逐行实测 + 前缀和 +
  二分**(真实数据行高不齐: H&R 行多一行 ⇒ 43.7px 与 65.4px 混排, 等高假设会漂上百像素);
  展开成员行会插队打断边界 ⇒ 有 `expandedKey` 时 group 窗口**退避回全量**。
  ⚠ 附带发现: **别在 computed 里对响应式大对象做展开复制** —— `filteredTorrents` 里的
  `{ ...r, hit }` 单项 74 字段 × 3000 条 = 22 万次 Proxy `get` 陷阱, **单这一句 68ms**,
  比整个窗口渲染还贵; 改成原引用出栈 + 模板现问 `isHit(m)` 后 115ms → 5ms。

**验证手段**: 单测覆盖不到前端渲染, 靠两道 —— ①静态守阵
`test_frontend_static_bundle_health`(JS 语法、`node --check`、CSS 闭合、`<transition>` 吞弹窗、
模板引用的资源存在); ②**真浏览器冒烟** `scripts/ui_harness.py`(真 `create_app` + `FakeClient`
+ 合成种子 + 命令泵)配 `scripts/ui_smoke.cjs`(Playwright, 双 UI 断言 + 内置 A/B 基准)。
改前端渲染/交互逻辑后应当跑第 ② 道。

### WEB UI 图形化配置编辑 (web.py + config/schema.py + config/writer.py, 2026-09-14)

- **模式**: 设置页不再直接编辑 YAML 全文 —— 每个配置项经图形控件增删改; 只读 YAML 预览(展示"即将写入"的文本)供核对。
- **数据模型**: 前端持有与磁盘**同构的 YAML 树**(标量全为字符串, 与 `yaml.BaseLoader` 语义一致) → 编辑即就地增删改, 无格式往返转换、零语义漂移; 脏检测用 JSON 快照对比。
- **端点**: `GET /api/config/schema`(UI 元数据 + `impact` 的热重载级别表合并)、`GET /api/config`(树)、`PUT /api/config`(保存)、`POST /api/config/preview`(只读预览)。旧的 `GET/PUT /api/config/raw` 已移除。
- **保存管线 (config/writer.py)**: 结构自检(必须有 `config` 根段) → 落临时文件跑 `load_config`(与启动同一校验路径, 失败 400 且不碰磁盘) → `diff_config_impacts` 判定变更 → **R 级字段回退为磁盘旧值** → 备份到 **`<data_dir>/<配置名>.bak`**(备份路径由调用方传入, 不再在项目根目录产生 `config.yml.bak`; 父目录按需创建) → ruamel round-trip 写盘 → 投递 `reload_config` 命令(仍由主循环线程应用)。
- **注释与格式策略**: 已存在键的注释保留(`_sync_mapping` 递归同步 CommentedMap); **值未变化的键跳过赋值**, 从而保留磁盘原标量形态(否则 ruamel 会把无引号的 `16585`/`true` 重写为 `'16585'`/`'true'`); 新增/修改的标量走 `_plain_scalar`(数字/布尔样式写成原生标量, BaseLoader 下语义等价); **列表整体替换(项级注释不保留)**。
- **schema.py 的地位**: 纯声明的 UI 元数据(分组/字段/控件类型/单位/枚举/帮助/必填/可选段/插件 spec 表), **不承载正确性规则**(合法性唯一入口仍是 `validate_config`); 键集合与插件表由 `tests/test_config_schema.py` 守卫 —— 新增配置键或插件忘登记会直接测试失败。
- **前端结构**: `config_editor.js`(分组导航/加载保存/预览/路径读写/列表与开关/站点与曲线专段) + `config_rules.js`(规则集与 15 条件/12 动作的 spec 编辑) 作为 Vue 全局 mixin 注入 `app.js` 的根实例; 字段渲染抽为 `ce-field` 组件(`<script type="text/x-template">`, 经 `provide/inject` 复用根的 `cfg*` 方法) —— 嵌套 object 在 `cfgFlatten` 阶段扁平化为带缩进的渲染项, 因此组件**无需递归**。
- **UI 元数据扩展(2026-09-14 视觉打磨)**: `Field.icon`/`Group.icon`(侧栏与标题图标, sprite symbol id)、`Field.risk`(高风险项: 标签处盾牌徽标 + 控件下方醒目风险行)、`Field.grey_if=(同段键, 期望值)`(所属功能未启用时**灰显但仍可编辑**; 期望值按“配置值 else schema 默认值”判定, 故未显式配置的 `enabled: false` 也能正确判灰)、`Field.group_of=<父字段键>`(相关设置**子卡**: 前端在父字段之后渲染一张缩进小卡容纳该键, YAML 形状不变)。`Group.icon` 在侧栏与页头同时生效。
- **规则卡与添加交互(2026-09-14)**: 规则卡头固定(折叠仍可见名称/摘要/启用开关), 条件/动作按序号强调执行顺序且各自带说明; 新增条件/动作用**平铺选择面板**(`.ce-picker`, 每项带 help, 高风险项标 risk)替代裸下拉; "新增站点/规则集/规则"用图标(站点与规则集的 **+ 移到各自列表标题行**, 规则用 `ce-sub-head` 行)就地展开输入框(自动聚焦, Enter 确认 / Esc 取消); 限速曲线每条一张卡: 周期 + 上/下行分区(阶梯图预览 + 档位表), 图表由**前端**解析 `10GiB`/`6MiB/s` 的展示值绘制(解析失败只告警不阻断, 合法性仍归后端)。
- **设置页表单结构(2026-09-14 视觉重做)**: ①**可选段(optional object)渲染为默认折叠的 `section`** —— 折叠态一行(折叠箭头 + 写入开关 + 段名 + `已配置 n/m 项` 摘要), 展开才显示内部字段; 这与旧的"开关 + 子字段平铺"区别在于子字段**嵌套在 section 内**(因此 ce-field 会递归渲染, 与 subcard 同机制)。②**布尔型从属项(如 `add_category` 的"覆盖已有分类")改为父字段的**内联开关**(`ce-field` 标签右侧), 因为一个开关单独占一张子卡比父字段本身还显眼; 其余从属项仍走 `group_of` 子卡。③**普通 object 段的子字段不额外缩进**(旧版 `depth+1` 导致同页两组输入框左缘错 16px)。④`overwrite*` 类不再有 subcard。
- **折线图(2026-09-14 重做)**: 几何由 `config_editor._buildCurveChart(i, dir)` 计算(560×210, 留出左/下轴标签空间), 输出 line/area/**xTicks/yTicks**/`padL..padB`/`spanT`/`maxS`/`points`; 模板用 `v-for="ch in [cfgCurveChartOf(i,dir)]"` 做别名渲染(避免重复写十几次取值); **鼠标 `mousemove` → `cfgChartHover` 把像素位置反算回 (累计流量, 限速)** 并按阶梯语义(阈值=区间上限)定位到具体档位, 显十字线 + 标记点 + tooltip(靠右时 `.flip` 向左翻, 不溢出)。

## 任务队列模型 — 生命周期只有 add_task / run_due 两个动词

- `add_task(task, now=None, keep_progress=False) -> bool`: 唯一入队口; kind=="check" 自动登记在途 (`_active_checks`), 重复登记丢弃返回 False。**默认重置断点** (下次从头执行); `keep_progress=True` 显式保存进度 (断点保留续跑), 仅供等待异步完成的子任务恢复 origin 使用。
- `run_due(dry_run, now, max_tasks)`: 弹出到期任务执行 (异常捕获内联) 并收尾 —— handler 返回 True 按 interval 重入队; False 本轮不重入 (消亡并释放在途登记)。**先快照后执行**: 执行中途重新入队的任务留到下一轮, 避免同批重入误判。主循环 `_tick` 只做 refresh + `run_due` 一次调用, 不再持有 `_execute_due`/`_safe`。
- **无 defer/resume 挂起态**: 推迟执行 = 规则任务 handler 返回 FINISHED 让出队列 (由 `Rule.process` 的 pending 断点驱动, `_handle_rule` 检测 `task.has_breakpoint` 返回 FINISHED), 由其创建的轮询子任务在完成后**按情况重新入队** origin —— 成功: `add_task(origin, keep_progress=True)` (断点续跑); 失败/等待结束/种子删除: `add_task(origin)` (默认重置重走完整决策链; 删除时由 origin 自己的删除守卫判死)。
- **无 remove_torrent**: 已删种子的任务由 run_due 到期执行时 handler 的删除守卫自然消亡 (`_handle_rule`/`_handle_maintenance`/check 轮询首行均守卫 `store.get None`)。

## 异步校验 (full-checking) 全流程 — 子任务重入队 + 断点续跑

发起方 `CheckAction._execute_full_checking` (rules/actions/full_checking.py):

1. 前置检查全通过后, `tq.add_task(poll_task)` 入队轮询子任务 (interval=2s; check kind 自动登记在途, 重复提交返回 False → skip)。
2. `api.torrents_recheck(...)` 同步发送, 失败返回 `ActionResult.fail` (子任务已登记, 下轮消亡自愈)。
3. 动作返回 `ActionResult.pending` → `Rule.process` 记录断点 `task.resume_index = i+1` 并中断规则 → `_handle_rule` 返回 False → 规则任务本轮不重入队。

轮询方 `poll` (check 子任务, 每 2s 读 store 快照):

- 仍 `is_checking` → 返回 True 继续轮询。
- `progress >= 1` (成功) → `on_success()` 自行触发 (`store.verified_references.add(hash)` + 可选 auto_start) → `tq.add_task(origin, keep_progress=True)` 重新入队: 断点保留, 规则从断点动作续跑后续动作。
- `progress < 1` (失败) / 异常 → `tq.add_task(origin)` (默认重置断点) → 规则任务重走完整决策链 (再次校验; 当日连续失败达 RECHECK_FAIL_LIMIT 后冷却, 次日重置)。
- 种子已删除 → `tq.add_task(origin)` (默认重置) 后自身消亡 (释放在途登记); origin 重入后由自己的删除守卫判死 (check-wait 等待任务的删除分支同此模式)。

## 数据层 TorrentStore (torrents.py)

设计目标优先级: **速度 > 可读性 > 内存**。

- `TorrentRecord` (dataclass, slots): 种子数据的**唯一所有者**(无中间投影视图)。快照字段名与 qB `TorrentDictionary` 完全一致 (鸭子兼容), 外加惰性缓存槽 `_tags_set`/`_state_enum`/`_trackers_info`/`_files`、非快照字段容器 `_raw`、以及 `tracker_conf` (匹配结果引用)。派生属性: `tags_set`(frozenset), `state_enum`(TorrentState 枚举, **有缓存**, 按类别判定与 qB 版本无关), `log_repr`, `tracker_name`。`__getattr__` 从 `_raw` 兜底读非快照字段(如跳检所需 `seq_dl`/`ratio_limit`)。
- `apply_delta(patch) -> frozenset[str]`: **只遍历 patch 中的字段**(增量轮成本 ∝ 变化字段数: Mapping 源走 `.items()`, 真机 `TorrentDictionary` 因此走 C 级迭代); 快照字段写入 slot, 非快照字段写入 `_raw`; 返回**变化字段名集合**(视图字段按 `_VIEW_QUANTUM` 量化后比较)。`from_torrent(tor, hash=)` 为构造入口。
- `apply_sync(api)`: 主循环入口(增量); `refresh(tors)`: 全量入口(测试/降级路径); 二者共用 `_apply`。
- **视图展示字段 `_VIEW_FIELDS`**: name/save_path/state/dlspeed/upspeed/uploaded/size/progress/seeding_time/ratio/tags/category/added_on (与 `_build_group_view` 取值集合一致); 其余快照字段(如 downloaded/dl_limit)变化**不**置脏 `view_changed`(但仍计入 `delta_fields`)。`view_dirty(changed)` 判定变化集是否触及视图。**`tags`/`category` 自 2026-09-14 起计入**(组级“共同标签/共同分类”列的数据源): 随之 `update_torrent_fields` 的 tags/category 分支与 `apply_tag_removal` 均需置 `view_changed`(旧实现明确注释“不影响展示”, 改视图字段时容易漏掉这类写侧置脏)。**`added_on` 同批加入**(组级默认排序键; 同时加入 `_SNAPSHOT_FIELDS` —— 加快照字段必须同步 `tests/helpers.py` 的 `FakeTorrent._SNAPSHOT_FIELDS`, 否则 `REQUIRED_TORRENT_FIELDS` 版本校验会直接报缺字段)。
- **字段量化 `_VIEW_QUANTUM` + `view_field_value(field, value)`**: 该表内的字段按步长向下取整后再比较与展示 —— 目前仅 `seeding_time: 60`(秒级递增但前端只展示到分钟, 不量化会让做种中的种子每轮置脏, 惰性重建对绝大多数种子失效)。**重建判定与 `_build_group_view` 展示值共用同一函数**, 保证"视图内容"与"脏标记依据"不脱钩; 新增需量化的字段只需加进该表。
- **惰性缓存**: `trackers_info`/`files` 首次访问才拉 API 并持久缓存 (种子删除时随记录回收); 全局 `all_tags()`/`all_categories()` 缓存 + `invalidate_*()` (由 QbApi 写操作触发失效)。
- **分组索引** (GroupingMixin 直接读写): `groups[key]`/`group_sizes[key]`/`member_to_key[hash]`(O(1) 定位)/`state_snapshot`/`download_conflict_warned`。分组键 = `(path_normalize(save_path), 排序后的文件相对路径元组)`。
- **删除/恢复**: `remove_torrent(h)` 立即从 `by_hash` 摘除并登记 `_pending_removed`(下轮 added/removed 上报); `restore_torrent(rec)` 撤销登记并放回记录(跳检重加, 保留 tracker_conf/惰性缓存)。
- `verified_references: Set[str]`: full-checking 通过的种子, **仅内存** (重启重新积累), 作为同组跳检参考。注意: 带跳检标签 (标签名是全局配置 `config.skip_checking_tag`, 默认 zSkipChecked, 全局统一不按规则覆盖, 动作运行时经 ctx 读取; 跳检成功后打在种子上、跨重启) 的种子即便在此集合中, 也会被 `_find_reference` 排除 —— 跳检未经哈希校验, 不可作参考。
- `update_torrent_fields(...)`: 写后同步快照 (tags/category/state/限速/save_path), 保证同 tick 内后续读取一致。

## QbApi Facade (qbapi.py)

所有对 qB 的调用统一走 `self.api` (不直接用 raw client):

- **写方法**: 调 raw client 后同步 store 快照 + 失效相关缓存 (add_tags/remove_tags/delete_tags/create_category/set_category/start(→stalledUP)/stop(→pausedUP)/set_upload_limit/set_download_limit/set_location/delete)。
- **读方法**: 优先 store 惰性缓存 (trackers/files/tags/categories); 快照缺 hash 时 trackers/files 回退 client; `torrents_info` 透传; `sync_maindata(rid)` 增量同步透传 (应用由 `store.apply_sync` 完成)。
- **store 必传**: `QbApi(client, store)` / `bind(client, store)` 中 store 为必传参数 (QbManager 恒持有数据层), 无"无 store 透传"形态 — 不为测试留专用通道 (见 06 可测试性原则)。
- **透传**: torrents_add / recheck / reannounce / piece_hashes / export / auth_log_in。
- **全局限速 (qB 5.0+)**: `get_global_speed_limits`/`set_global_speed_limits` 走 `transfer_*` 端点 (bytes/s), 不用 `app/preferences` 旧键 (已失效)。内部 KiB/s ↔ bytes/s 换算。
- dry_run 判定**不在Facade内**, 由调用点负责。

## 状态持久化 (RuleEngineMixin)

- `_load_state()`: JSON 读入 `self.state` (构造时 + run 时各一次); `save_state()`: **仅程序退出时**调用 (减少磁盘写入)。
- `record_execution(rule_name, hash)`: 写 `state["exec_history"]["{rule}:{hash}"] = {ts, date, hour}` — execute_once/cooldown 去重依据。
- `begin_round(torrents)`: 维护 `state["upload_snapshots"][daily/weekly/monthly] = {key, baseline{hash: uploaded}}` — upload_size_today/week/month 条件的基线; 周期切换时清空重建。
- `upload_delta(torrent, kind)`: `max(0, uploaded - baseline)` (下限 0, 防种子重加/客户端重启归零导致负数)。
- 其它 state 键: `auto_categories` (自动设置过的分类, 判断能否覆盖), `speed_limit_curve` (当日曲线计算结果, 调试用), `skip_check_backup` (跳检重加失败时的 .torrent 备份元数据)。
