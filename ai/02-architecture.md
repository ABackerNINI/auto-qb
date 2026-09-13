# 02 架构与运行时

## 组件总览

```
                    ┌──────────────────────────────────────────────────┐
                    │ QbManager (qbmanager.py)                         │
                    │  = RuleEngineMixin + TagsMixin + CheckingMixin   │
                    │    + GroupingMixin + TrackerMixin + SpeedCurveMixin │
                    ├──────────────────────────────────────────────────┤
  每tick增量同步 →│ TorrentStore (torrents.py)   ← 快照同步 ──  QbApi (qbapi.py) ──→ qbittorrent-api Client
                    │  快照/惰性缓存/分组索引        (写后同步)      APIFacade
                    │  ↑ TorrentSync / SyncTorrent (sync/maindata rid 增量)
                    ├──────────────────────────────────────────────────┤
                    │ TaskQueue (taskqueue.py)  单一时间优先堆          │
                    │  Task: internal / rule / check / check-wait      │
                    ├──────────────────────────────────────────────────┤
                    │ rules/ : Rule + 15条件插件 + 11动作插件 (registry) │
                    └──────────────────────────────────────────────────┘
                    state(state_file JSON) ← 仅退出时落盘
```

**组合关系**: `QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin, SpeedCurveMixin)` — mixin 依赖宿主实例属性 (`config`/`store`/`api`/`state`/`task_queue`/`client`), 各 mixin 文件头部 docstring 声明了所依赖的属性, 新 mixin 照此模式写。

## 主循环 (qbmanager.py)

```python
run(dry_run):
    connect()                       # Client + auth_log_in
    _load_state(); _load_rules(); _create_global_tasks()
    while True:
        _tick(dry_run)              # 异常捕获后继续
        time.sleep(main_tick)       # 默认 2s
    finally: save_state()           # 仅退出时落盘

_tick(dry_run):
    _refresh_torrents(dry_run)      # ① 刷新快照 + 事件处理
    task_queue.run_due(dry_run, now=now, max_tasks=max_tasks_per_tick)  # ② 弹出+执行+收尾(默认最多20个/tick)
```

连接恢复检测: `_tick` 成功(即 API 可达)后若 `_last_conn_ok is False` 则置 True 并记一次"已重新连接"——`connect()` 仅启动时调用一次, 运行期断开/恢复只能由 tick 翻转(否则 UI 永远显示断开)。连接异常节流 (2026-09-12): 运行期 tick 内的 `APIConnectionError` 经 `_last_conn_ok` 状态机节流 — 仅"连接态→断开"转换时记一次 ERROR, 恢复时记一次 INFO("已重新连接 qBittorrent", `connect()` 内), 断开期间每 tick 重试失败静默 (防 qB 宕机刷屏); 非 `APIConnectionError` 异常照常记 "主循环异常"(exc_info=True)。启动首连失败 → `connect()` 返回 False → `run` 直接结束。

`run_due` 内部: 先快照到期任务再逐个执行 (异常捕获内联; 执行中途重新入队的任务留到下一轮), 收尾:
- handler 返回 **FINISHED** → 任务消亡, kind=="check" 释放在途校验标记 (典型: 种子已删除, 由 handler 的删除守卫判定)。
- handler 返回 **REQUEUE** → 按 `task.interval` 重新入队 (`next_run = now + interval`), **默认重置断点** (下一轮从头执行; 断点续跑只经子任务 `add_task(origin, keep_progress=True)` 路径)。

### 每轮 `_refresh_torrents` 的数据流 (理解本项目的关键)

1. `TorrentSync.fetch(api)` → qB `/api/v2/sync/maindata?rid=` **增量**拉取 (只含变化种子的变化字段) → 本地基线合并 → `store.refresh(tors)` → 返回 `(added, removed)`; 已存在记录原地 `update_from`, 惰性缓存跨 tick 保留。细节见下节「增量同步层」。
2. **状态转移观测** (grouping.enabled, 先于一切自有动作): `_handle_state_transitions` (上传转暂停 / 进入 errored(重校验发现文件缺失) → 缺文件扫描, 用上一轮 `store.state_snapshot`)。**顺序约束**: 自有停种 (大小一致性/冲突整组暂停) 经 QbApi 快照同步会**当场改写 `by_hash` 状态**, 此观测若放在自有动作之后会把自家停种误判为外部"上传转暂停"。
2.5 **事件分派** (on_* trigger 规则, 同步即时): `_dispatch_events` — 在 `store.refresh` 之后、自有动作之前、`update_state_snapshot` 之前的分派点执行各事件规则 (added 事件用本轮 added 列表, deleted 事件用 `store.refresh` 返回的 removed 及其删除前快照副本, state 变化事件用上一轮 `state_snapshot` 对比本轮)。事件规则**不建周期任务**, 由 `_apply_event_rule` 同步建 rule-event 一次性 Task 作 `ctx.task` 并 `rule.process`; 遇 checking 返回 pending 时, 该 rule-event 任务作 origin 由轮询子任务 `add_task` 重新入队, 下 tick `_handle_event_rule` 断点续跑后 FINISHED 消亡。`max_tasks_per_tick` 不约束此即时分派 (设计详见 09-roadmap 事件触发规划)。
3. **新增种子** 逐个处理:
   - `_match_tracker_conf(torrent)` 匹配 tracker 配置 (hostname 精确匹配, 命中多个配置时打 ERROR 日志并用第一个); 未匹配 → warning + **跳过该种子**(不创建任何任务)。
   - `torrent.tracker_conf = tracker_conf` (记录引用, 后续任务直接用)。
   - `_apply_speed_limit` tracker 单种限速 (尊重奇数保护)。
   - `_create_torrent_tasks`: 创建 `maintenance` 内置任务 + 该种子应绑定的每条规则一个任务。
   - `_assign_new_torrent` (grouping.enabled): 按文件列表增量归组 + 大小一致性检查。
   - `_add_episode_tags` (add_episode_tags.enabled): 集数标签 (单/多集模板 + 连续性判定)。
4. **删除种子**: `store.refresh` 返回的 removed 里, 删除前先保留各种子快照副本 (供 `on_torrent_deleted` 规则经 `ctx.torrent`/`snapshot` 读取); `task_queue.remove_torrent(hash)` 移除该种子全部任务 (含让位任务/在途校验标记); grouping 启用时 `_handle_removed_torrents` → 组内缺文件扫描; `_dispatch_events` 的 deleted 分支随后触发 `on_torrent_deleted` 规则。
5. **分组事件处理** (grouping.enabled): `_handle_save_path_changes` (重归组+两侧扫描)、`_check_download_conflicts` (每轮)。
6. `store.update_state_snapshot(tors)` 保存本轮状态快照 (存 `state_enum` 枚举对象, 跨 qB 版本)。
7. `begin_round(...)` 维护上传量快照基线 (daily/weekly/monthly, 周期切换重建基线)。

## 增量同步层 TorrentSync / SyncTorrent (torrents.py, 2026-09-13)

**动机**: 原先每 tick 全量 `torrents/info`, qB 端必须反复序列化**全部**种子 (~45 字段 × N), 种子库大时 qB CPU 明显上涨。改走 qB 自带 WebUI 同款的 `/api/v2/sync/maindata`:

- **qB 端语义** (`src/webui/api/synccontroller.cpp`): rid 与上次一致时只回**变化种子的变化字段** (`processMap` 逐字段 diff), **未变化种子完全不出现在响应中**; 删除的种子列在 `torrents_removed`; 新增种子(基线缺失)回全量字段; rid 不匹配/为 0 时 `full_update=true` 回全量。**自愈性**: 漏 tick/rid 错位/qB 重启都只会退化成一次全量, 不会丢数据。
- **字段齐平**: sync 与 `torrents/info` 共用同一 C++ 序列化器 `serialize/serialize_torrent.{h,cpp}` (sync 仅额外移除 `"id"` 键) —— 故 `REQUIRED_TORRENT_FIELDS` 全部字段(含 `share_limit_action`/`inactive_seeding_time_limit`)在 sync 响应中同样存在。
- **`TorrentSync`**: 持 `rid` + `_views`(hash -> `SyncTorrent`); `fetch(api)` 全量轮重建视图/增量轮逐字段就地合并; `need_validate` 标记本轮是否全量(供版本校验); `validate_sample` 提供校验样本; `reset()` 在重连/热重载时清基线强制下轮全量; 未知异常 rid 归零后原样上抛(由主循环兜底)。
- **`SyncTorrent(Mapping)`**: 包装一个可变 baseline dict 的字段视图。实现 Mapping 协议(供 `TorrentRecord.update_from` 走 dict 级 item 访问快路径) + `__getattr__` 属性访问(缺失抛 `AttributeError`, 对齐 `AttrDict`/`TorrentDictionary`) + `state_enum` 派生。**故意不是 dict 子类**: 使版本兼容校验的样本选择(跳过测试注入的 plain dict)保持原语义。正因如此, `store.refresh`/`update_state_snapshot`/`_dispatch_events`/`_copy_tor_attrs` 等既有代码**零改动**。
- **降级**: 端点不可用(旧版 qB / 测试替身缺 `sync_maindata`) → 捕获 `AttributeError`/`NotFound404Error` → 回退全量 `torrents_info()`(一次性 WARNING 去重), 语义与改造前一致。

## 启动期版本兼容校验 (2026-09-06, 2026-09-13 调整)

`_refresh_torrents` 在**全量轮**(`TorrentSync.need_validate`: 首轮/rid 失效/降级)对 `TorrentSync.validate_sample` 校验 `REQUIRED_TORRENT_FIELDS` (快照字段 + 跳检重加字段, 共 23 个), 缺失抛 `QbCompatError(AutoQbError)` → tick 循环 `except AutoQbError: raise` 穿透"主循环异常"捕获 → CLI stderr 干净退出。**增量轮不校验** (响应只含变化字段, 校验必误报), 由 `need_validate` 闸门控制。通过后置 `_schema_validated` 不再重复 (qB 版本运行期不变); 空 qB 时样本为 `None` → 跳过。设计动机: 快照字段缺失会**静默零值** (规则基于假数据决策), 比崩溃更危险 —— qB 5.0 preferences 键漂移前科。

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

- **Web 线程(uvicorn 独立线程)只做两件事**: 读 `manager` 暴露的只读快照(`_group_view`/`status_snapshot`)与向 `manager.web_commands` 投递命令 —— 暂停/开始/汇报/删除/热重载等写操作全由主循环 `_drain_web_commands` 消费执行(单一写线程约束不变); Web 线程不得触碰 store/队列/state_file。
- **惰性组装 + 活跃窗口**: `_group_view`(分组视图)与 `_search_index`(搜索索引)均只在主循环构建, 且仅当 `_web_last_seen` 距今 < `WEB_VIEW_TTL`(10s) 时推进 —— 关闭网页后主循环不空转。**精确置脏**: `_tick` 消费 `store.consume_view_changed()`, 仅视图字段/成员**真有变化**时才重建 (不再每 tick 无条件置脏 —— 静止种子库不再每 2s 重建)。`ensure_group_view()` 作 Web 请求侧兜底(脏则即时重建)。
- **视图版本门控 (等价 qB 的 rid)**: `_group_view_ver` 每次重建自增; `ensure_group_state(rid)` 在 rid 与服务端版本一致时**不回传 groups**(响应体趋近于零), 仅回 status(4 个标量, 与版本无关恒回传)。`/api/state?rid=` 暴露该语义, 前端据此跳过整表替换与重渲染。前端另配: 页面隐藏(`document.hidden`)停轮询、恢复即刷; `setTimeout` 链式续排(不堆叠请求); 连续无更新退避 2s→5s→10s(有更新立刻回落)。
- **搜索索引 `_search_index` (hash -> {name, files})**: 种子名匹配即时扫 `store.by_hash`(无 API 开销), 文件列表匹配依赖索引(文件 API 只在主循环线程, 种子记录 `_files` 缓存跨 tick 复用)。索引按 hash **增量**维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已删种子淘汰; 单次限流 `SEARCH_INDEX_BUILD_BUDGET`(500)条, 未拉完保持 `_search_index_dirty=True` 由下一 tick 续建, 前端据 `building` 每 1s 自动重查。
- **搜索结果是辅种组的筛选**: 前端用命中 hash 集合过滤 `sortedGroups`(组行沿用真实组 key, 组级操作可用); 未归组命中种子以虚拟行兜底 —— 组级路由 key 必须能过 `decode_group_key`, 虚拟 key 会让解码失败 500, 详见 [08-pitfalls.md](08-pitfalls.md)。

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

- `TorrentRecord` (dataclass, slots): 快照字段名与 qB `TorrentDictionary` 完全一致 (鸭子兼容), 外加惰性缓存槽 `_tags_set`/`_state_enum`/`_trackers_info`/`_files`, 以及 `tor` (原始对象引用) 与 `tracker_conf` (匹配结果引用)。派生属性: `tags_set`(frozenset), `state_enum`(TorrentState 枚举, 按类别判定与 qB 版本无关), `log_repr`, `tracker_name`。
- `refresh(tors)`: 全量刷新 (tors 为 `TorrentSync` 提供的字段视图), 记录对象跨 tick 保留 (缓存存活), 返回 `(added, removed)`; 首轮全部视为新增。同时累计 `view_changed`(仅 `_VIEW_FIELDS` 即 Web 视图展示字段/成员变化时置真), 供 `consume_view_changed()` 精确驱动分组视图惰性重建。
- **视图展示字段 `_VIEW_FIELDS`**: name/save_path/state/dlspeed/upspeed/uploaded/size/progress/seeding_time/ratio (与 `_build_group_view` 取值集合一致); 其余快照字段(如 downloaded/dl_limit)变化**不**置脏。`update_from(tor)` 返回是否有视图字段变化。
- **字段量化 `_VIEW_QUANTUM` + `view_field_value(field, value)`**: 该表内的字段按步长向下取整后再比较与展示 —— 目前仅 `seeding_time: 60`(秒级递增但前端只展示到分钟, 不量化会让做种中的种子每轮置脏, 惰性重建对绝大多数种子失效)。**重建判定与 `_build_group_view` 展示值共用同一函数**, 保证"视图内容"与"脏标记依据"不脱钩; 新增需量化的字段只需加进该表。
- **惰性缓存**: `trackers_info`/`files` 首次访问才拉 API 并持久缓存 (种子删除时随记录回收); 全局 `all_tags()`/`all_categories()` 缓存 + `invalidate_*()` (由 QbApi 写操作触发失效)。
- **分组索引** (GroupingMixin 直接读写): `groups[key]`/`group_sizes[key]`/`member_to_key[hash]`(O(1) 定位)/`state_snapshot`/`download_conflict_warned`。分组键 = `(path_normalize(save_path), 排序后的文件相对路径元组)`。
- `verified_references: Set[str]`: full-checking 通过的种子, **仅内存** (重启重新积累), 作为同组跳检参考。注意: 带跳检标签 (标签名是全局配置 `config.skip_checking_tag`, 默认 zSkipChecked, 全局统一不按规则覆盖, 动作运行时经 ctx 读取; 跳检成功后打在种子上、跨重启) 的种子即便在此集合中, 也会被 `_find_reference` 排除 —— 跳检未经哈希校验, 不可作参考。
- `update_torrent_fields(...)`: 写后同步快照 (tags/category/state/限速/save_path), 保证同 tick 内后续读取一致。

## QbApi Facade (qbapi.py)

所有对 qB 的调用统一走 `self.api` (不直接用 raw client):

- **写方法**: 调 raw client 后同步 store 快照 + 失效相关缓存 (add_tags/remove_tags/delete_tags/create_category/set_category/start(→stalledUP)/stop(→pausedUP)/set_upload_limit/set_download_limit/set_location/delete)。
- **读方法**: 优先 store 惰性缓存 (trackers/files/tags/categories); 快照缺 hash 时 trackers/files 回退 client; `torrents_info` 透传; `sync_maindata(rid)` 增量同步透传 (快照更新由 `TorrentSync` 合并 + `store.refresh` 完成)。
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
