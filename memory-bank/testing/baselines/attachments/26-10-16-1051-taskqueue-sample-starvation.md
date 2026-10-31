# 3418 passed + 4 skipped —— 采样从任务队列移出改挂时钟线(issue 26-10-16-0954 修复; 新增守阵 2 条、删 2 条旧注册用例)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html」(修法方向经追问拍板: 走 issue 建议修法 #1「采样移出队列挂时钟线」)。`core/modules/traffic_sample_mod.py` 采样移出 `TaskQueue` —— 它只读内存快照、零 qB 请求, 不该受任务线配额 `max_tasks_per_tick` 限流; 新增 `on_task_line` 钩子(每 `main_tick` 一次, 不在配额里)做到期闸门, 采样体 `handle_traffic_sample(dry_run)` 自持 `_next_sample_at = now + effective`; 删全局任务注册/`queue_rebuilt` 订阅/`TASK_NAME`; `_apply_interval` 去 `task` 回写(量化口径逐字不变); `core/module.py` 的 `register_global_tasks` 样板注释从「三处」改「两处」。用例面: 2 条注册用例改为新契约(队列零任务 / 闸门+热重载启停)+ 1 条积压饿死回归, `test_sampling_runs_on_caller_thread` 与 `test_traffic_store.test_all_persist_writes_on_caller_thread` 改驱动 `on_task_line`, 间隔类断言改 `_effective_interval`。本切片为根 test.full 回归闸门数字, 测在含上述 4 文件改动与文档回写的工作树上。
> 基线时间: 2026-10-16 10:51
> 档案: memory-bank/tasks/26-10-16-backend-taskqueue-sample-starvation.md

**Refs:** memory-bank/tasks/26-10-16-backend-taskqueue-sample-starvation.md,memory-bank/issues/26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html

## 验收数字

- test.full: 3418 passed + 4 skipped / TOTAL 17377 185 5854 158 98%; 耗时 154.2~175.4s(三次采样 175.35s / 154.23s / 168.97s, 最后一次为**提交树**实测; 口径见 baseline.md)。
- 对账(相对上基线 `26-10-16-0940-replace-retry`): passed 逐位相同(删 2 条旧任务注册用例、增 2 条新契约用例); 语句 17383 → 17377(**-6**)、未覆盖 185 → 185(**0** —— 新增代码行全被守阵覆盖, 删掉的是已覆盖样板)、分支 5856 → 5854(-2)、partial 159 → 158(-1)。覆盖率闸门 `--cov-fail-under=98` 通过; 逐行核对: 本模块未覆盖行全为**既有**防御分支(本次新增的钩子/闸门/自持到期点无未覆盖行)。
- 定向回归: `commands run test.one -- tests/test_traffic_sample.py tests/test_traffic_store.py` 130 passed(含新增 3 条中的 2 条 —— 第 3 条走真实 `_task_line` 入口), 副作用台账越界 0。
- 复验探针(只读, `.openclaw/tmp/probe_verify_starvation.py`, 未入库): 真源码 `TaskQueue` 重放启动场景(1.5s 拍 / 配额 20 / 先注册周期任务跑成首轮 / 同 tick 补建 400 个立即到期任务)⇒ 周期任务首轮后**静默 31.500s、丢 21 轮**(公式 `⌈400/20⌉×1.5s`), 与 issue 现场 37~55s 同族 —— 修复前形态复现成功。
- 红验(3 类突变, 全部字节恒等还原后复绿): ①`on_task_line` 直接 `return` ⇒ 4 条红(积压回归 / 闸门+启停 / 采样线程 / 存储侧线程); ②闸门 `if False` ⇒ 1 条红(未到点重复采); ③把采样注册回队列(修复前形态 shim)⇒ 1 条红(采样占掉一个作业配额: `executed 399 != 400`)。
- Linux(WSL)侧未跑 —— 改动为纯调度面无平台分支, 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/core/modules/traffic_sample_mod.py`: 删 `TASK_NAME` / `_register_task` / `subscribe`+`_on_queue_rebuilt` / `taskqueue` import; 新增 `on_task_line(force)`(到期闸门, 与同线其它钩子无先后依赖)与 `_next_sample_at` 字段; `handle_traffic_sample(task, dry_run) -> bool` 改 `handle_traffic_sample(dry_run) -> None` 并收尾写下一到期点; `_apply_interval(conf, task)` 改 `_apply_interval(conf) -> float`(去 `task.interval` 回写); docstring 四处同步(调度位置新增段落 / C1 / 线程模型 / 配置)。
- `src/auto_qb/core/module.py`: `register_global_tasks` 样板单点注释「speed_curve / maintenance / traffic_sample 三处」→ 两处(并注明采样退出去向)。
- `tests/test_traffic_sample.py`: `_run_sample` 助手改直调采样体(不驱动闸门); 新增 `_add_backlog` / `_spy_sample_rounds` 两个夹具; 3 条注册用例 → `test_sample_task_registered_when_enabled`(队列零任务)/ `test_sample_not_starved_by_immediate_task_backlog` / `test_sample_clock_line_gate_and_hot_reload_enable`; `test_sampling_runs_on_caller_thread`、`test_interval_change_hot_reload_new_block_and_effective_interval`、`test_interval_mismatch_ceils_and_warns_once`、`test_interval_decimal_match_kept_not_ceiled`、`test_disabled_at_runtime_handler_noop` 及全部 `Task(...)` 构造点改用例; 头部测试计划同步。
- `tests/test_traffic_store.py`: `_run_sample` 改直调采样体; `test_all_persist_writes_on_caller_thread` 改驱动 `on_task_line`; 7 处 `is True` 断言随返回值退役清理。
- 滚动面(文档): `memory-bank/modules/core-runtime.md`(模块描述补「采样挂时钟线」)、`memory-bank/pitfalls/backend/task-interval-tick-quantization.md`(升格为「周期任务的队列节拍陷阱」双条目, 新增条目②积压饿死: 触发/判别/处置/守阵)、`memory-bank/tasks/26-10-16-backend-taskqueue-sample-starvation.md`、`memory-bank/activeContext/26-10-16-1051-taskqueue-sample-starvation.md`、issue `26-10-16-0954`(Open → In Progress → Done + doc-refs)。
