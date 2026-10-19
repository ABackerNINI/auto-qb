# 26-10-16-backend-taskqueue-sample-starvation — 采样移出任务队列改挂时钟线(issue 26-10-16-0954 认领与修复)

**Status:** Done
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户指令「认领并修复 memory-bank/issues/26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html」。走 issue 建议修法 #1(原文「最干净」, 用户拍板): `qb_traffic` 采样**从 `TaskQueue` 移出**, 改挂**时钟线钩子** `on_task_line`(任务线节拍, 每 `main_tick` 一次, **不受 `max_tasks_per_tick` 约束**)。依据 = 采样只读内存快照、**零 qB 请求**(模块 docstring 原有断言), 本就不该占「qB 请求预算面」的配额; 而队列只有 `next_run` 一个排序键, 重启/L2 重建补建的数百个立即到期任务会把它按严格升序挡在门外(实测 7/7 复现 37~55s 静默, 1.5s 档丢约 36 轮), 且静默被读侧摊配**伪装成正常速率平线**。落地面: 钩子只做到期闸门, 采样体 `handle_traffic_sample(dry_run)` 自持下一到期点 `_next_sample_at = now + effective`; 删全局任务注册 `_register_task` / `queue_rebuilt` 订阅 / `TASK_NAME` 常量; `_apply_interval` 去掉 `task` 参数与 `task.interval` 回写(节拍改由 `_next_sample_at` 表达); 启停与热重载改由采样体入口现读 `conf.enabled`(不再依赖队列重建相位)。**量化口径逐字不变**(`effective = ceil(sample_interval/main_tick)×main_tick`, 块头 `interval_s` 与读侧消费口径不受影响)。测试数字唯一权威在基线切片(见 **Refs:**)。
**Topics:** taskqueue-periodic-starvation

**Refs:** memory-bank/issues/26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html, memory-bank/testing/baselines/26-10-16-1051-taskqueue-sample-starvation.md
## 原始请求

> 用户(2026-10-16): 「认领并修复 26-10-16-0954-bug-traffic-sample-starved-by-task-backlog.html」

## 思考过程与决策

- **请求边界判定**: 执行任务(改代码 + 认领 issue)。用户显式「认领并修复」= 指派 + 修复双授权; 收尾档位(立档 + 基线切片)与提交经**逐项**追问后由用户点头(「走完整收尾 DoD」+「现在提交」)。
- **修法方向三选一(用户拍板)**: 开工先把 issue §06 三条候选全部核过再做选择 —— ①**采样挂时钟线**(原文首选, **采纳**) ②队列加公平性 ③补建 `next_run` 摊配(触「立即到期 ⇒ 下一 tick 兑现一次维护」契约)。把取舍摆给用户后, 用户选 ①。
- **❗对 issue 建议修法 #2 的纠正(写进 issue §06 保留原文 + 说明)**: 按字面「各 kind 各取一次」**修不好本例** —— 采样与补建的内置 maintenance 同为 `kind=internal`, 保底的那 1 个 internal 名额会被 `next_run` 更早的补建任务拿走, 采样仍轮不到。要生效必须细化到「**无 hash 的全局任务**保底」(全队列仅 ≈6 条)。该纠正也解释了为什么不能简单「加个优先级」了事。
- **为什么是 `on_task_line` 而不是 `on_sync_line`**: issue 原文建议「与同步线同款」, 但**同步线节拍 = `min(sync_interval, main_tick)` 可能细于 `main_tick`**(默认 1.5s < 2s)⇒ 采样节拍会被量化到 3s 而非 2s, 与块头 `interval_s` 语义冲突(读侧按 `ceil(interval/main_tick)×main_tick` 消费)。采样节拍的单位本就是 `main_tick`(配置硬校验 `sample_interval >= main_tick`), 故挂**任务线钩子**——它每 `main_tick` 一次且不在 `run_due` 的配额里。
- **闸门放钩子还是放采样体**: 闸门放钩子、采样体不带闸门 —— 既让「时钟线每拍一次 + 到点才采」两件事各居其位, 也让既有 ~15 处「直调采样体」的用例语义不变(直调 = 一轮采样, 不受到期闸门约束)。到期点由采样体收尾写入(`_next_sample_at`), 首拍 `None` 即采(对齐原先「任务注册即到期」的启动语义)。
- **未启用/停用的口径**: 采样体入口现读 `conf.enabled`, 停用时**不动到期点** ⇒ 重新启用后首拍即采。零文件零目录零请求(黄金法则 2)不变。
- **与视图发布的先后**: 采样只更新内存态, 读侧 `traffic_qb` **按请求现取** `live_tail` 引用 ⇒ 钩子在装配序里排在 webui 之后(采样模块装配序最后)也不产生新鲜度回归。已在钩子 docstring 写明「无先后依赖」, 免得后人误加顺序约束。
- **`TASK_NAME` 直接删除**(不留兼容别名): 全仓引用只有模块内注册点与两个测试文件; 留一个「无主任务名」比删掉更容易误导(项目有退役名纪律, 见坑档 `qbmanager-retired-names.md`)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步(`my-commit-flow.sync`, 已同步 2f56cc4d) + 复验(探针重放) + 修法方向拍板 | Done |
| S2 | `traffic_sample_mod.py`: 删注册/订阅/`_register_task`/`TASK_NAME` + 新增 `on_task_line` 闸门 + 采样体改 `(dry_run)` 并自持 `_next_sample_at` + `_apply_interval(conf)` 去 task 回写 + docstring 三处同步 | Done |
| S3 | `core/module.py`: `register_global_tasks` 样板单点注释从「三处」改「两处」(traffic_sample 退出) | Done |
| S4 | 用例面: `_run_sample` 助手改直调采样体; 3 条注册用例改契约; 2 条间隔用例断言改 `_effective_interval`; 2 条线程用例改驱动 `on_task_line`; 清理全部 `Task(...)` 构造与 `TASK_NAME` 引用; 头部测试计划同步 | Done |
| S5 | 新守阵 3 条(队列零任务 / 积压饿死回归 / 闸门+热重载启停) + 三类突变红绿双验 | Done |
| S6 | test.full 全量 + 基线切片 | Done |
| S7 | 收尾: issue 置 `Done`(doc-refs 认领链) / 档案 / 切片 / 文档回写 / kb.index / kb.check | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 复验(锚点 + 机理重放) | Done | 三个锚点行号零漂移; 探针用真源码 `TaskQueue` 重放积压场景, 复现 31.5s 静默 |
| 模块改造(采样挂时钟线) | Done | `on_task_line` 闸门 + 采样体自持到期点; 删任务注册面与 `TASK_NAME` |
| 样板注释同步(`core/module.py`) | Done | `register_global_tasks` 从「三处同骨架」改「两处」并注明采样去向 |
| 既有用例迁移(2 文件) | Done | 15 处调用点清理; 2 条注册用例按新契约重写; 2 条间隔断言改 `_effective_interval` |
| 新守阵 3 条 + 红绿双验 | Done | 积压饿死回归走真实 `_task_line` 入口; 三类突变全判红、字节恒等还原复绿 |
| 全量测试与基线切片 | Done | test.full 与定向回归全绿(数字见基线切片, 正文不手抄) |
| 文档回写与机检 | Done | core-runtime / 坑档(升格双条目) / issue 状态与 doc-refs; kb.check + docmap --check + doc.links + doc.caps 全绿 |
| 提交 | 待用户指令 | 收尾档位与提交均经逐项确认后执行 |

## 进度日志

- **2026-10-16 10:20 开工 + 复验(防过期原则第 5 条)**: 开工同步 `my-commit-flow.sync` → 已同步 `2f56cc4d`。锚点全部原样在(行号零漂移): `core/taskqueue.py` `add_task`(:130 入队即 `next_run=now`)、`_pop_due`(:217 严格 `next_run` 升序 + `max_tasks` 计数)、`_requeue`(:235 `next_run = now + interval`)、`Task.__slots__`(:36-50, **无 priority 字段**)。机理用**真源码 `TaskQueue`** 确定性重放(只读探针 `.openclaw/tmp/probe_verify_starvation.py`, 未入库; 主循环 1.5s / `max_tasks_per_tick=20` / 先注册 1.5s 周期任务并跑成首轮 / 同 tick 补建 400 个立即到期任务): **周期任务首轮后静默 31.500s、丢 21 轮**, 与公式 `⌈400/20⌉×1.5s = 30s` 逐位吻合(+1 轮补位); 映射到 issue 记的 183 种子(任务数数百)即 37~55s。**复验结论: 仍复现**。
- **2026-10-16 10:30 修法拍板**: 三条候选的方向、代价与残留摆给用户(含对 #2 的纠正), 用户选 #1「采样挂时钟线」。
- **2026-10-16 10:35 S2–S4 实施**: 模块侧与用例侧改动一次落地(见 `实现计划` 表); `commands run test.one -- tests/test_traffic_sample.py tests/test_traffic_store.py` 首跑 2 红(积压回归的「排水未完成」自检写错 + 一处 `is True` 断言残留), 修完复绿。
- **2026-10-16 10:40 S5 红绿双验(突变 → 判红 → 字节恒等还原)**: ①`on_task_line` 直接 `return`(钩子不驱动采样) ⇒ **4 红**(积压回归 / 闸门+启停 / 采样线程 / 存储侧线程); ②到期闸门失效(`if False`) ⇒ **1 红**(未到点重复采); ③把采样**注册回队列**(修复前形态, 临时 shim) ⇒ **1 红**(积压回归的配额断言: `executed 399 != 400`, 正是「采样不该在队列里」的判据)。还原后 `grep MUTATION` = 0(字节恒等), 定向回归复绿。回归主判据 `test_sample_not_starved_by_immediate_task_backlog`: 500 个立即到期任务占满队列, 走**真实 `_task_line` 入口**连打 20 拍 ⇒ 采样 20/20 轮全采到且积压按配额原速排水。
- **2026-10-16 10:45 S6 全量 + 基线**: `commands run test.full` 全绿两跑(数字与耗时区间见基线切片 `26-10-16-1051-*`); 逐行覆盖核对: 本次新增代码**无未覆盖行**(模块未覆盖行全为既有防御分支)。
- **2026-10-16 10:51 S7 收尾**: issue `Open → Done`(meta + 封面徽标 + 状态日志 + 复验 + 修复后补充 + §06 #2 纠正)、`doc-refs` 指本档(认领链双向闭合); `core-runtime.md` 与坑档 `task-interval-tick-quantization.md`(升格为「周期任务的队列节拍陷阱」双条目)回写; 本档 + 基线切片 + activeContext 切片; `kb.index` 重建 21 个生成物; `kb.check`(含回写守卫 394/394)/`kb.docmap --check`/`doc.links`/`doc.caps` 全绿。

## 未做 / 残留(转告)

- **issue §03 点名的同族风险未一并处置**: `check:check-checking-result` / `check-wait`(2.0s 轮询, 带 hash, 同构未实测)与 `delete_tags`(60s, 余量仅 ~5s)仍在队列里, 理论上可被同一机制饿死。本轮**范围守恒**(黄金法则 6)只治 issue 点名的采样; 该残留口径已写进坑档条目②的判据里(判它是不是「传感器」), 是否跟进由用户拍板。
- 未跑 `dev.run -- config.yml --dry-run` 真机冒烟(需真实 qB 在线); 采样路径已由 `_task_line` 真实入口用例覆盖。
- Linux(WSL)侧未跑 —— 改动无平台分支(纯调度面), 本条 Windows 侧数字为事实源。
- 未给队列加任何公平性机制 —— 修法方向已拍板为「传感器出队列」, 与「队列内公平性」是两条不相交的路。
