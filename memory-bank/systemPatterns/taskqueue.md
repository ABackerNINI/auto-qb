# 任务队列与异步校验

> 摘要: 单队列模型、两个动词、线程约束与 full-checking 全流程(含断点续跑)。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: 任务队列, taskqueue, add_task, run_due, 线程模型, 异步校验, full-checking, 断点续跑

## 任务队列 (taskqueue.py) — 单队列模型

> README "设计要点"已同步为单队列描述 (2026-09-05): 所有任务(含校验结果轮询)统一进一个 `heapq` 最小堆 `_fast`, 按 `next_run` 到期弹出。

- **Task 字段** (`__slots__` 15 项, taskqueue.py:41-57): `uid`(kind:name:hash:monotonic_ns), `kind`, `name`, `hash`, `_store`(种子数据引用, 经 `store` 属性按 hash 读快照), `next_run`, `interval` (<=0 归一化为 1s), `state`, `resume_index` (规则断点), `attempt` (动作级 retry 已重试次数, plan 26-11-01-0106 W2/R3; 成功/耗尽后归零, 重启随任务重建归零), `retry_delay` (本次 requeue 的推迟秒数: handler 设置, `_requeue` 消费后清零; >0 时 requeue 保留断点续跑), `run_count`, `created_at` (建件时刻, 经 Clock 注入), `payload`, `handler`。
- **Task.kind**: `internal` (全局任务 + 种子级 maintenance), `rule` (种子级规则扫描), `rule-event` (事件规则一次性任务, 作 origin 被轮询子任务重新入队续跑, 恒 FINISHED 不自我周期循环), `check` (校验结果轮询), `check-wait` (组内校验等待)。文档中也用 `refresh` 指种子刷新 (它不是队列里的任务, 是每 tick 固定第一步)。
- **Task.state**: `PENDING`(排队) / `RUNNING`(已弹出执行中)。
- **Task 断点**: `resume_index` 默认记住执行位置; `has_breakpoint` 属性查询; `reset()` 显式重置。
- **handler 返回值**: `REQUEUE`(True, 重入队: 默认按 interval 且重置断点; handler 挂 `task.retry_delay` 时改按 backoff 推迟且保留断点, `_requeue` taskqueue.py:313-327) / `FINISHED`(False, 本轮不重入: 消亡并释放在途登记, 或由其子任务负责重新入队)。

### 线程模型 (重要约束)

**主循环所在线程是唯一修改任务队列结构与 state_file 的线程, 全程无锁。** 控制台模式下即主线程; `--tray` 模式下主循环整体移入后台线程(主线程为 UI), 约束语义不变。 full-checking 等异步效果不是靠工作线程改队列, 而是: 主循环发 API 请求 (同步返回, 校验后台异步进行), 由队列中的 check 轮询子任务每 2s 读 store 快照判断结果。任何新功能都必须维持这个假设。

## 任务队列模型 — 生命周期只有 add_task / run_due 两个动词

- `add_task(task, now=None, keep_progress=False) -> bool`: 唯一入队口; kind=="check" 自动登记在途 (`_active_checks`), 重复登记丢弃返回 False。**默认重置断点** (下次从头执行); `keep_progress=True` 显式保存进度 (断点保留续跑), 仅供等待异步完成的子任务恢复 origin 使用。
- `run_due(dry_run, now, max_tasks, defer_gate=None) -> int` (taskqueue.py:232): 弹出到期任务执行 (异常捕获内联) 并收尾 —— handler 返回 True 按 interval 重入队 (挂 `retry_delay` 时按 backoff 推迟且保留断点, 见上节 `_requeue`); False 本轮不重入 (消亡并释放在途登记)。**先快照后执行**: 执行中途重新入队的任务留到下一轮, 避免同批重入误判。主循环 `_task_line` 传 `defer_gate=self._own_write_defer_gate` (qbmanager.py:876)。主循环 `_tick` 只做 refresh + `run_due` 一次调用, 不再持有 `_execute_due`/`_safe`。
- **D-1 队列级让位闸 (defer_gate, A 系 26-10-13-0540 S2)**: 可选回调 task -> 原因串(命中)/None(放行), 内核单点实现 `QbManager._own_write_defer_gate` (qbmanager.py:881: 任务目标 hash 或其组任一成员刚被自有停/起且快照未回流即命中, 队列级统一闸覆盖 task 线全体消费)。命中者**本轮不执行、也不占 max_tasks 预算** (issue 26-10-30-0616: 让位者不做事不耗 qB 请求预算, 计进返回数会让速率语义在 own_write 窗口失真) —— state 回 PENDING + `next_run = now` 重新入堆 (下一 run_due 立即再判, 不等自身 interval), 由 run_due 在执行批次之后统一回填 (`_pop_due` 期间留堆外, 防同轮重复过闸)。**扫描面封顶**: `_pop_due` (taskqueue.py:268-302) 单轮扫描以 `max_tasks * _DEFER_SCAN_FACTOR` (5, taskqueue.py:29) 封顶 —— 让位是「跳过」不是「执行」, 不能一轮 tick 把整条队列扫穿; `max_tasks<=0` 不限。返回值只统计**真正执行**的任务数。有界性由 store.own_writes 的逐出/TTL 兜底 (闸门失效后任务照常执行, 不饿死)。
- **无 defer/resume 挂起态**: 推迟执行两条路, 都不引入挂起态 —— ① 规则任务 handler 返回 FINISHED 让出队列 (由 `Rule.process` 的 pending 断点驱动, `_handle_rule` 检测 `task.has_breakpoint` 返回 FINISHED), 由其创建的轮询子任务在完成后**按情况重新入队** origin —— 成功: `add_task(origin, keep_progress=True)` (断点续跑); 失败/等待结束/种子删除: `add_task(origin)` (默认重置重走完整决策链; 删除时由 origin 自己的删除守卫判死); ② 队列级 defer_gate 让位 (D-1, 见上条: 不经 handler, next_run=now 重入堆下 tick 重判)。
- **无 remove_torrent**: 已删种子的任务由 run_due 到期执行时 handler 的删除守卫自然消亡 (`_handle_rule`/`_handle_maintenance`/check 轮询首行均守卫 `store.get None`)。

## 异步校验 (full-checking) 全流程 — 子任务重入队 + 断点续跑

发起方 `CheckAction._execute_full_checking` (一行委托) -> `manager.ops_recheck` (core/modules/ops_mod.py 的 OpsModule — rules → ops ← web 独立操作层, plan 26-09-30-0109, P4 起升 ctx.ops 服务; R1 提交点检查: 在途登记或快照 checking 态即 skip 拒绝, 全来源生效):

1. 前置检查全通过后, `tq.add_task(poll_task)` 入队轮询子任务 (interval=2s; check kind 自动登记在途, 重复提交返回 False → skip)。
2. `api.torrents_recheck(...)` 同步发送, 失败返回 `ActionResult.fail` (子任务已登记, 下轮消亡自愈)。
3. 动作返回 `ActionResult.pending` → `Rule.process` 记录断点 `task.resume_index = i+1` 并中断规则 → `_handle_rule` 返回 False → 规则任务本轮不重入队。

轮询方 `poll` (check 子任务, 每 2s 读 store 快照):

- 仍 `is_checking` → 返回 True 继续轮询。
- `progress >= 1` (成功) → `on_success()` 自行触发 (`store.verified_references.add(hash)` + 可选 auto_start) → `tq.add_task(origin, keep_progress=True)` 重新入队: 断点保留, 规则从断点动作续跑后续动作。
- `progress < 1` (失败) / 异常 → `tq.add_task(origin)` (默认重置断点) → 规则任务重走完整决策链 (再次校验; 当日连续失败达 RECHECK_FAIL_LIMIT 后冷却, 次日重置)。
- 种子已删除 → `tq.add_task(origin)` (默认重置) 后自身消亡 (释放在途登记); origin 重入后由自己的删除守卫判死 (check-wait 等待任务的删除分支同此模式)。
