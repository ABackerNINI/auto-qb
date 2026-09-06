# 02 架构与运行时

## 组件总览

```
                    ┌──────────────────────────────────────────────────┐
                    │ QbManager (qbmanager.py)                         │
                    │  = RuleEngineMixin + TagsMixin + CheckingMixin   │
                    │    + GroupingMixin + TrackerMixin + SpeedCurveMixin │
                    ├──────────────────────────────────────────────────┤
  每tick全量拉取 →  │ TorrentStore (torrents.py)   ← 快照同步 ──  QbApi (qbapi.py) ──→ qbittorrent-api Client
                    │  快照/惰性缓存/分组索引        (写后同步)      APIFacade
                    ├──────────────────────────────────────────────────┤
                    │ TaskQueue (taskqueue.py)  单一时间优先堆          │
                    │  Task: refresh / internal / rule / check         │
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
    due = task_queue.due(now, max=max_tasks_per_tick)   # ② 弹出到期任务(默认最多20个/tick)
    _execute_due(due, dry_run, now) # ③ 逐个执行
```

`_execute_due` 对每个任务调 `_safe(task)` → `task.handler(task, dry_run)`:
- handler 返回 **False** → 任务消亡 (`task_queue.task_died` 释放在途校验标记), 不重新入队 (典型: 种子已删除)。
- 返回 True/其它 → `task_queue.reschedule(task, now)`: 按 `task.interval` 重新入队 (`next_run = now + interval`)。
- 任务处于 **DEFERRED** 状态 → 跳过 (已让位给校验轮询, 由轮询任务恢复)。

### 每轮 `_refresh_torrents` 的数据流 (理解本项目的关键)

1. `api.torrents_info()` 全量拉取 → `store.refresh(tors)` → 返回 `(added, removed)`; 已存在记录原地 `update_from`, 惰性缓存跨 tick 保留。
2. **状态转移观测** (grouping.enabled, 先于一切自有动作): `_handle_state_transitions` (上传转暂停 → 缺文件扫描, 用上一轮 `store.state_snapshot`)。**顺序约束**: 自有停种 (大小一致性/冲突整组暂停) 经 QbApi 快照同步会**当场改写 `by_hash` 状态**, 此观测若放在自有动作之后会把自家停种误判为外部"上传转暂停"。
3. **新增种子** 逐个处理:
   - `_match_tracker_conf(torrent)` 匹配 tracker 配置 (hostname 精确匹配, 命中多个配置时打 ERROR 日志并用第一个); 未匹配 → warning + **跳过该种子**(不创建任何任务)。
   - `torrent.tracker_conf = tracker_conf` (记录引用, 后续任务直接用)。
   - `_apply_speed_limit` tracker 单种限速 (尊重奇数保护)。
   - `_create_torrent_tasks`: 创建 `maintenance` 内置任务 + 该种子应绑定的每条规则一个任务。
   - `_assign_new_torrent` (grouping.enabled): 按文件列表增量归组 + 大小一致性检查。
   - `_add_episode_tags` (add_episode_tags.enabled): 集数标签 (单/多集模板 + 连续性判定)。
4. **删除种子**: `task_queue.remove_torrent(hash)` 移除该种子全部任务 (含让位任务/在途校验标记); grouping 启用时 `_handle_removed_torrents` → 组内缺文件扫描。
5. **分组事件处理** (grouping.enabled): `_handle_save_path_changes` (重归组+两侧扫描)、`_check_download_conflicts` (每轮)。
6. `store.update_state_snapshot(tors)` 保存本轮状态快照 (存 `state_enum` 枚举对象, 跨 qB 版本)。
7. `begin_round(...)` 维护上传量快照基线 (daily/weekly/monthly, 周期切换重建基线)。

## 启动期版本兼容校验 (2026-09-06)

`_refresh_torrents` 首次拉到非空种子信息时校验 `REQUIRED_TORRENT_FIELDS` (快照字段 + 跳检重加字段, 共 23 个), 缺失抛 `QbCompatError(AutoQbError)` → tick 循环 `except AutoQbError: raise` 穿透"主循环异常"捕获 → CLI stderr 干净退出。通过后置 `_schema_validated` 不再重复 (qB 版本运行期不变); 空 qB 时跳过 (无样本)。设计动机: 快照字段缺失会**静默零值** (规则基于假数据决策), 比崩溃更危险 —— qB 5.0 preferences 键漂移前科。

## 任务队列 (taskqueue.py) — 单队列模型

> README "设计要点"已同步为单队列描述 (2026-09-05): 所有任务(含校验结果轮询)统一进一个 `heapq` 最小堆 `_fast`, 按 `next_run` 到期弹出。

- **Task 字段**: `uid`(kind:name:hash:monotonic_ns), `kind`, `name`, `hash`, `tracker_conf`, `next_run`, `interval` (<=0 归一化为 1s), `state`, `resume_cb` (一次性完成处理), `resume_index` (规则断点), `run_count`, `payload`, `handler`。
- **Task.kind**: `internal` (全局任务 + 种子级 maintenance), `rule` (种子级规则扫描), `check` (校验结果轮询)。文档中也用 `refresh` 指种子刷新 (它不是队列里的任务, 是每 tick 固定第一步)。
- **Task.state**: `PENDING`(排队) / `RUNNING`(已弹出执行中) / `DEFERRED`(让位: 不入队不消亡, 等外部恢复)。
- **队列 API**:
  - `add_task/add_tasks`: 新任务立即到期 (next_run=now, 下一 tick 执行)。
  - `due(now, max)`: 弹出所有到期任务。
  - `reschedule(task)`: 执行完按 interval 重入队; 让位任务恢复时自动移出让位集合。
  - `defer(task)`: 让位 — 从调度中挂起, 由外部决定 resume 或 reschedule。
  - `resume(task)`: 恢复让位任务 — 先触发一次性 `resume_cb` (校验成功后的完成处理), 再按 interval 重入队; **保留 resume_index** → 规则续跑。
  - `add_check_task(task)`: 校验轮询任务登记, 同种子已有在途校验则拒绝 (去重, `_active_checks`)。
  - `remove_torrent(hash)`: 移除该种子所有任务 (堆重建 heapify) + 让位任务 + 在途校验标记。
  - `task_died(task)`: handler 返回 False 时释放 check 任务的在途标记。

### 线程模型 (重要约束)

**主循环线程是唯一修改任务队列结构与 state_file 的线程, 全程无锁。** full-checking 等异步效果不是靠工作线程改队列, 而是: 主循环发 API 请求 (同步返回, 校验后台异步进行), 由队列中的 check 轮询任务每 2s 读 store 快照判断结果。任何新功能都必须维持这个假设。

## 异步校验 (full-checking) 全流程 — defer/resume 断点续跑机制

发起方 `CheckAction._execute_full_checking` (rules/actions.py):

1. 前置检查全通过后, `tq.add_check_task(poll_task)` 登记轮询任务 (interval=2s)。
2. **先** `tq.defer(origin)` (原规则任务让位), **再** `api.torrents_recheck(...)` (顺序保证: 发送失败绝不 defer, 杜绝原任务永久让位)。失败则返回 `ActionResult.fail`。
3. 动作返回 `ActionResult.pending` → `Rule.process` 记录断点 `task.resume_index = i+1` 并中断规则 (handled=True, stop=True)。

轮询方 `poll` (check 任务, 每 2s 读 store 快照):

- 仍 `is_checking` → 返回 True 继续轮询。
- `progress >= 1` (成功) → `origin.resume_cb = on_success; tq.resume(origin)`: 触发完成处理 (`store.verified_references.add(hash)` + 可选 auto_start), 因 resume_index 保留, 规则从断点动作续跑后续动作。
- `progress < 1` (失败) / 种子已删除 / 异常 → `origin.resume_index = None; tq.reschedule(origin)` → 规则任务重走完整决策链 (再次校验)。

## 数据层 TorrentStore (torrents.py)

设计目标优先级: **速度 > 可读性 > 内存**。

- `TorrentRecord` (dataclass, slots): 快照字段名与 qB `TorrentDictionary` 完全一致 (鸭子兼容), 外加惰性缓存槽 `_tags_set`/`_state_enum`/`_trackers_info`/`_files`, 以及 `tor` (原始对象引用) 与 `tracker_conf` (匹配结果引用)。派生属性: `tags_set`(frozenset), `state_enum`(TorrentState 枚举, 按类别判定与 qB 版本无关), `log_repr`, `tracker_name`。
- `refresh(tors)`: 全量刷新, 记录对象跨 tick 保留 (缓存存活), 返回 `(added, removed)`; 首轮全部视为新增。
- **惰性缓存**: `trackers_info`/`files` 首次访问才拉 API 并持久缓存 (种子删除时随记录回收); 全局 `all_tags()`/`all_categories()` 缓存 + `invalidate_*()` (由 QbApi 写操作触发失效)。
- **分组索引** (GroupingMixin 直接读写): `groups[key]`/`group_sizes[key]`/`member_to_key[hash]`(O(1) 定位)/`state_snapshot`/`download_conflict_warned`。分组键 = `(path_normalize(save_path), 排序后的文件相对路径元组)`。
- `verified_references: Set[str]`: full-checking 通过的种子, **仅内存** (重启重新积累), 作为同组跳检参考。
- `update_torrent_fields(...)`: 写后同步快照 (tags/category/state/限速/save_path), 保证同 tick 内后续读取一致。

## QbApi Facade (qbapi.py)

所有对 qB 的调用统一走 `self.api` (不直接用 raw client):

- **写方法**: 调 raw client 后同步 store 快照 + 失效相关缓存 (add_tags/remove_tags/delete_tags/create_category/set_category/start(→stalledUP)/stop(→pausedUP)/set_upload_limit/set_download_limit/set_location/delete)。
- **读方法**: 优先 store 惰性缓存 (trackers/files/tags/categories); 快照缺 hash 时 trackers/files 回退 client; `torrents_info` 透传。
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
