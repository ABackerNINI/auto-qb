# 主循环与任务队列

> 摘要: 主循环节拍与每轮数据流、任务队列单一时间优先堆模型、单写线程约束、state_file 落盘时机。
> 触发: 主循环, tick, 节拍, 数据流, 任务队列, taskqueue, add_task, run_due, 断点续跑, full-checking, 落盘

## 主循环 (core/qbmanager.py)

`run()` 的节拍骨架:

- **启动**: `materialize_schema_migration`(配置 schema 启动物化, 磁盘落后才写; dry-run 只探测) → `host.start_all(dry_run)`(模块 start 按装配序: web 服务器/HR 端点/全局任务自注册; 移入 try 后启动期致命错误也走 finally → stop_all + 释放锁) → 首连(非托管失败抛 `QbConnectError` 干净退出; 托管 `--tray` 按 tick 重试) → `ctx.state.load()` + state 迁移物化 → 规则加载。
- **每轮**(while True, 各线可独立到期):
  - **命令线** `host.run_command_line()`: 消费 Web 命令 + 在途汇报确认; 有命令且非 dry-run 时本轮强制补一次同步。
  - **同步线** `_sync_line`(间隔 `sync_interval` 默认 1.5s; 快档 > 任务档时钳制到 main_tick): 只 `_refresh_torrents` 刷快照 + 视图发布, 不跑任务。
  - **任务线** `_task_line`(间隔 `main_tick` 默认 2s): `task_queue.run_due` 到期任务执行 + 任务线收尾(错误原因预取 → 视图发布 → 搜索索引推进)。
  - 两线同拍 → `_tick` = 完整一轮, 视图只重建一次。另有**微步线** `run_micro_line`: 跳检相位机每轮推进一步, 无固定节拍。
- **每轮收尾**: `web.flush_truths()` 推迟回执无条件落(异常路径兜底); 非 dry-run 调 `ctx.state.maybe_flush` 周期落盘; 重连检测 + 断连稳态守卫/退避; 睡到最近事件(`min(next_sync_at, next_tick_at, 微步线到期)`, 命令可提前唤醒)。
- **finally**: `host.stop_all()`(装配逆序) → 优雅退出 `ctx.state.save()`(**仅 `lifecycle_ready` 时** —— 启动期失败不落空态 state.json) → 释放锁(任何路径都释放, 含启动期 fail-fast)。

### 每轮数据流(理解本项目的关键)

`_refresh_torrents` → `store.apply_sync(api)`(rid 增量, 语义见 data-state.md) → store 应用时顺手收集**变化集**(`delta_fields`/`state_changed`/`dirty_groups`) → EventBus 相位广播, 各模块在订阅相位里按变化集做 O(变化数) 的下游处理(状态迁移分支/保存路径变化/下载冲突重算), 不做全量扫描。

## 任务队列 (core/taskqueue.py) — 单队列模型

所有任务(含校验结果轮询)统一进一个 `heapq` 最小堆, 按 `next_run` 到期弹出。**时间优先**: 没有独立优先级字段, 到期时间即优先级。

- **Task 字段**: `__slots__` 15 项 —— `uid`(kind:name:hash:monotonic_ns) / `kind` / `name` / `hash` / `_store`(种子数据引用, 经 `store` 属性按 hash 读快照) / `next_run` / `interval`(≤0 归一 1s) / `state`(PENDING/RUNNING) / `resume_index`(规则断点) / `attempt`(动作级 retry 已重试次数, 成功/耗尽归零) / `retry_delay`(本次 requeue 的推迟秒数, `_requeue` 消费后清零; >0 时保留断点) / `run_count` / `created_at` / `payload` / `handler`。
- **kind 五种**: `internal`(全局任务 + 种子级维护) / `rule`(种子级规则扫描) / `rule-event`(事件规则一次性任务, 作 origin 被轮询子任务重新入队续跑) / `check`(校验结果轮询) / `check-wait`(组内校验等待)。种子刷新不是队列任务 —— 它是每轮固定第一步。
- **生命周期只有两个动词**:
  - `add_task(task, keep_progress=False)`: 唯一入队口; kind=="check" 自动登记在途, 重复登记丢弃返回 False。**默认重置断点**(下轮从头执行); `keep_progress=True` 显式保留断点, 仅供等待异步完成的子任务恢复 origin 使用。
  - `run_due(dry_run, now, max_tasks, defer_gate=None)`: **先快照后执行**(执行中途重新入队的任务留到下一轮, 避免同批重入误判), 异常捕获内联。handler 返回 REQUEUE → 按 `task.interval` 重新入队; FINISHED → 本轮不重入: 消亡(kind=="check" 释放在途登记), 或由其子任务负责重新入队。
- **队列级让位闸(defer_gate, D-1)**: 可选回调 task → 原因串/None; 内核单点 `QbManager._own_write_defer_gate`(目标种子或其组刚被自有停/起且快照未回流即命中)。命中者本轮不执行、**不占 max_tasks 预算**(state 回 PENDING, `next_run=now` 重新入堆, 执行批次后统一回填), 单轮扫描以 `max_tasks × 5` 封顶 —— 让位是「跳过」不是「执行」。有界性由 store.own_writes 的逐出/TTL 兜底(闸门失效后任务照常执行, 不饿死)。
- **无挂起态、无删除动词**: 推迟执行 = 规则任务 handler 返回 FINISHED 让出队列(由规则断点 `resume_index` 驱动), 由其轮询子任务完成后按情况重新入队 origin; 已删种子的任务由 run_due 到期执行时 handler 的**删除守卫**自然消亡(`store.get(hash) is None`)。

### 异步校验 full-checking — 子任务轮询模式

不靠工作线程改队列: 主循环发 recheck API(同步返回, qB 后台异步校验), 队列中的 `check` 轮询子任务每 2s 读 store 快照判结果 —— 成功: `on_success` 后 `add_task(origin, keep_progress=True)` 断点续跑后续动作; 失败: `add_task(origin)` 默认重置重走完整决策链(当日连续失败达上限后冷却); 种子已删: 重入后由 origin 自己的删除守卫判死。发起入口 `OpsModule.ops_recheck`(`core/modules/ops_mod.py`; 在途登记或快照 checking 态即拒绝重复提交, 全来源生效)。

## 单写线程约束

**主循环所在线程是唯一修改任务队列结构与 state_file 的线程, 全程无锁。** 控制台模式下即主线程; `--tray` 模式下主循环整体移入后台线程(主线程为 UI), 约束语义不变。异步效果一律落"子任务轮询"模型, 不开工作线程写共享结构 —— 这是免锁的前提, 也是黄金法则「单一写线程」的落点。

## 落盘时机 (state_file)

- **周期**: 主循环每轮 `ctx.state.maybe_flush(now, interval)`(`core/state.py:264`), 间隔 `state_save_interval`(默认 120s / 配置端下限 30s / 0=关闭, `config/models.py:563`)—— 非优雅终止的状态丢失窗口 ≤ 间隔。
- **优雅退出**: run() 的 finally 里 `ctx.state.save()`(启动成功才落, 见上)。
- **写点即时落盘例外**: `skip_check_day`(跳检完成标记)与 `recheck_fails`(失败冷却)在动作写点直接 save —— 这两键重放代价最高; 其余键靠周期兜底, 新增写点无需插桩。
- 决策档案: issues/26-09-21-1347-bug-backend-state-save-only-on-exit.html(推翻「仅退出落盘」旧取舍)。
