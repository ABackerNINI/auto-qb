# 并发与状态机约束

> 摘要: 七条线程 / 状态机硬约束, 违反即引入难以复现的 bug。
> 等级: L0
> 触发: 加线程, 改队列, 改 state_file, 改校验流程, 视图组装, QbApi 写方法, 阻塞等待, 关停, stop, join

### 带超时的阻塞等待必须配「叫停口」, 否则关停白等满超时(还在持锁就更多赔)

- **触发**: 写「等别的组件回结果」的代码 —— 等扩展回传(`hr/queue.py::HrTaskQueue.wait`)、
  等子进程、等网络响应。
- **判别**: 只设了 `timeout` 而**没有**「叫停」通路的等待, 关停时会一路等满超时:
  `HrRuntime.stop()` → `HrWorker.stop()` → `join(timeout)` 干等, 期间**站点锁不放**、
  进程退出被拖住(默认 `request_timeout` 180s)。**比"关停慢"更贵的是锁被占着** —— 那个站点从此不可刷新。
- **反例(2026-09-24 M2 实测)**: 先写成了「设 `timeout` + 关停时 join」, 看日志「一切正常」,
  只有 `--durations` 暴露 7 条用例各慢 10.5s(join 白等), 且真机场景是**分钟级**而不是 10s。
- **处置**: ① 等待表加 `cancel_all(reason)` / `resume()`, 等待方**在循环里检查叫停标记**
  (注意: 必须覆盖「叫停**之后**才发起的等待」—— 只比对进入时的 epoch 会漏掉这一支);
  ② 把叫停**内建**在 stop 里(`HrWorker.stop()` 第一件事就是 `queue.cancel_all`),
  别指望调用方记得; ③ 把「被叫停」与「等超时」**分开上报**(前者不该计入失败/熔断);
  ④ 守阵写成「测量关停耗时 < N 秒」而不是"跑通即可"。

### 主循环线程是唯一修改队列 / state_file / store 分组索引的线程

- **触发**: 想在别处改队列 / 状态 / 分组索引。
- **判别**: 候选写点包括校验回调、信号处理器、新起的线程 —— 这些都是违规写点。
- **处置**: 一律回到主循环; 需要别的线程参与时**只投递意图**(如 `_drain_web_commands` 的队列模型)。

### 校验登记与 recheck 的顺序: 先登记在途, 再发请求

- **触发**: 改 `torrents_recheck` 相关流程。
- **判别**: 顺序必须是**先** `add_task(轮询子任务)` 登记在途(已在途则 skip), **再**发 `torrents_recheck`;
  发送失败返回 `fail`(**不返回 pending**), 成功才返回 pending。
- **处置**: 顺序与返回值语义都别改 —— 反了会出现重复校验 / 假 pending。

### 断点续跑语义: `keep_progress` 两个分支不可混用

- **触发**: 改规则续跑 / `resume_index` 相关逻辑。
- **判别**: `keep_progress=True` **保留 `resume_index`**(续跑后续动作);
  默认**重置清空**并重走完整决策链。
- **处置**: 两者不可混用; 改之前先确认调用方期望哪一支。

### 种子删除没有队列级清理入口

- **触发**: 写在途任务 / 事件规则任务。
- **判别**: 种子可能已被删除 ⇒ 在途任务必须**自带 `store.get(hash) is None` 删除守卫**;
  事件规则任务作 origin 续跑后同样由**首行守卫**判死。
- **处置**: 保持首行守卫; 要打印留档走 `RuleContext.snapshot`(`print_torrent_details` 就是这么做的)。

### QbApi 写方法必须同步 store（`state` 是例外: 不回写, 等同步）

- **触发**: 加 / 改 QbApi 的写方法。
- **判别**: 不同步 store ⇒ **同 tick 读到旧值**。但 `state` 是**唯一例外** —— 它只由 qB 同步
  权威驱动, 不由写方法合成回写(A 系 26-10-13-0540 S1 起: `_sync_paused_state` 与
  `update_torrent_fields(state=)` 均已删除; 快照语义 = 严格等于最近一次同步的应用结果)。
  理由: 原合成值只写 `pausedUP/pausedDL/stalledUP/stalledDL` 四值 —— 压平值域、可能在异步
  窗口写错完成位, 且**吞掉「自家停种」这条信号**; 源无关语义要求自家停/起与外部变更一样被
  转移检测与状态事件看见(26-10-12-2229 裁定)。
- **处置**: 写方法里调 `update_torrent_fields`(tags/category/save_path/限速等**非 state** 字段)
  或 `invalidate_*`。state 的「同 tick 新鲜」是**刻意放弃**的: 同 tick 二次停/起可能重发一次
  请求(qB 幂等, 无害); 要补回见计划 26-10-13-0540 §4.4 的 `pending_writes` 意图标记。
  校验类决策若可能与自写撞窗, 走同计划 §4.3 的局部 deferral(见下条)。

### 校验类决策不得对「自有写未回流」的 hash 出决策（deferral 纪律）

- **触发**: 新增/修改任何**读快照 `state` 或组内下载态**做放行/拒绝决策的消费点(跳检闸门、校验决策链、组级判定…)。
- **判别**: 自有停/起下发后, qB 服务端状态按 `BitTorrent/Session/RefreshInterval`(默认 1.5s)节流,
  快照**尚未**反映该变化。此时按陈旧快照决策 = 双错: 按陈旧值**放行** ⇒ 脏数据洗白(跳检把正在写入的
  共享文件标全部块有效, 即 G4/G6); 按陈旧值**拒绝** ⇒ 误拒。
- **处置**: 统一判据 `store.own_write_pending(hash)`(目标 hash **或其所在组任一成员** ∈ `own_writes`)。
  已设三处闸门: **D-1** 队列级 `qbmanager._own_write_defer_gate` → `TaskQueue.run_due(defer_gate=)`
  (覆盖 task 线全体消费, 命中者重排下一 tick); **D-2** `ops.skip_check` 执行路径(WEB 路径不经 task 线);
  **D-3** `rules/actions/checking.py` `CheckAction.execute` 决策链入口(事件即时分派等非队列路径)。
  **新增校验类消费点必须接同一判据并加守阵**, 否则该点对自写裸奔(A3 的「纪律性安全」代价, 见计划 §11)。
- **有界性双依据(缺一不可)**: ① `own_writes` 在同步应用到该 hash 新 `state` 时逐出(依赖 qB 缓存前进);
  ② **TTL 兜底** `_OWN_WRITE_TTL`(10s, 不依赖任何外部条件) —— 命令在 qB 侧未生效时靠它解除让位, 防任务饿死。
  只留 ① 等于把「任务不饿死」押在「qB 一定会前进」上, 那是隐藏假设。
- **预算面(issue 26-10-30-0616, 已修)**: **让位者不占 `max_tasks` 预算** —— 让位发生在过闸时,
  而旧实现先 `_pop_due(now, max_tasks)` 出队即计数, 组级 own_write(整组停 / size 一致性停种)
  把同批同组任务整批让位时它们**各吃一个名额**, 组成员数 >= `max_tasks_per_tick`(缺省 20)时
  同 tick 的无关任务一个都轮不到、一路饿到 TTL 退出, 速率语义(20 个/2s)窗口内失真。
  现语义: `max_tasks` 只约束**可执行**名额, 让位者本轮先留在堆外(否则 `next_run=now` 会被
  本轮重复弹出过闸), 执行批次之后统一回填; 让位扫描面另以 `max_tasks * _DEFER_SCAN_FACTOR`
  封顶 —— **让位是"跳过"不是"执行", 放开预算后必须另有上界**, 否则一轮 tick 会把整条队列扫穿。
  `run_due` 返回值同步改为**实际执行数**(不再含让位者)。改这条语义时先跑
  `tests/test_taskqueue.py` 的两条守阵(预算 / 扫描上界)。
- **登记点**: QbApi 四入口 `start/stop/pause/resume` 在 raw client 调用**成功后** `note_own_write`;
  纯内存态(同 `state_snapshot`), **不落盘**, 热重载 `reset_runtime` 清空。
- **同一容器供两种语义用, 禁双轨**: `own_write_pending(hash, group=True)` 走组维度(deferral);
  `group=False` 只判自身(同 tick 幂等门, 见下条)。两者共用同一登记/清理单点, 不另起 `pending_writes`。
- **方向自洽性**(故判据无需带方向): A 系下快照不动 ⇒ 反向操作由**传统判据**先拦 ——
  `start(pausedUP)` 后同 tick `stop`: 快照仍 `pausedUP` ⇒ `is_stopped` 为真 ⇒ skip「已停止」;
  `stop(stalledUP)` 后同 tick `start`: 快照仍 `stalledUP` ⇒ `is_stopped` 为假 ⇒ skip「已开始」。
  落到幂等门的只有**同向重复**(stop 后再 stop / start 后再 start), 正是意图标记该管的事。

### 停/起动作的同 tick 幂等靠「意图标记」, 不靠回写假值

- **触发**: 增删/修改任何触发 `torrents_start/stop/pause/resume` 的动作或命令路径。
- **判别**: A 系删合成回写后, 同 tick 内 `is_stopped` 仍是旧值 ⇒ 第二次同类动作会重发一次请求。
  qB 侧幂等、无功能错误, 只是重复 HTTP 与日志噪声 —— 但**修法必须是意图标记, 不能是回写假 state 值**
  (后者正是 R1–R6 值失真的来源: 假值会压平值域、伪造完成位、吞掉真实变化)。
- **处置**: `rules/actions/basic.py` 的 `StartAction`/`StopAction` 在 dry_run 之外先查
  `store.own_write_pending(ctx.hash, group=False)` ⇒ 命中则 skip(文案同 ops 侧「状态尚未回流」)。
- **已知边界**: WEB 命令路径(`webui/commands.py`)直调 `api.torrents_start/stop` 不经动作,
  故用户手动连点仍会重复下发(无害); 需要时把幂等门上移到 QbApi 四入口 —— 但那会让「写实意图」
  与「让位」耦合, 属独立设计决策, 不在本批次范围。

### 视图组装里**绝对不能**发 qB API (硬约束, 不是优化)

- **触发**: 想在视图组装 / 渲染路径里取 qB 数据。
- **判别**: 视图可能**每 tick 重建** ⇒ 在里面发 API = 主循环被 N 次网络往返拖死。
- **处置**: 取数一律**主循环预取 + 视图只读缓存**, 且必须 **TTL + 单轮预算双限额**
  (成片错误种子会拖死主循环), 并 **先写时间戳再拉取**(失败也不在 TTL 内反复重试)。

### 校验结果判败必须有「曾见 checking」前提(首样本竞态, 2026-09-25 实证)

- **触发**: 改 full-checking 轮询判定(poll)/失败计数/校验启动逻辑, 或给任何异步结果写"失败"判定分支。
- **判别**: recheck 提交后 qB **异步应用** + 同步快照按 sync_interval 节拍滞后 —— 首个轮询样本常落在
  「尚未开检」窗口(非 checking + progress=0.0)。判败分支若无 `seen_checking` 前提, 会把快照滞后当
  校验失败(实证: WARNING「校验未通过(第1次, progress=0.0)」而实际校验成功; 假失败计数经决策链 1.6
  毒化同组, 且 skip 是 DEBUG 全盲 → 表现为"一批辅种部分不触发且无日志")。
- **处置**: 判败仅允许两条路: ①曾见 checking 后落回未完成(真失败) ②`CHECK_START_GIVEUP`(600s)宽限
  耗尽仍未见开检(活锁保险丝); 另有 `submitted` 标记 —— recheck **发送失败**时已登记的轮询子任务下轮
  直接消亡(原靠失败分支清理, 宽限语义下会滞留 600s, 不得遗留在途登记)。假失败自愈在决策链 1.6
  (记录指向已完成/已删除成员 → 清除且不参与推断)。**判定/拒绝类 skip(冷却上限/1.6 推断)必须 INFO**
  —— `Rule.process` 对 skip 一律 DEBUG, 只靠它排障等于盲区。
