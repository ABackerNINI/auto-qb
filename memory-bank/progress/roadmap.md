# 路线图 (规划中 + 已定案口径)

> 摘要: 尚未实现的功能线、仍敞着的设计取舍, 以及「已定案、别改回去」的方向性口径。
> 触发: 规划中, 下一步做什么, 路线图, 已定案口径, 别改回去, 未实现

## 规划中 (🚧, 尚未实现)

- 多用户(账号体系/并发会话) — WEB UI 核心、图形化配置编辑与 SSE 事件推送均已实现, 见 productContext.md / modules.md

### 真机 qB 语料抓取 / 脱敏 / 离线回放 (2026-09-21, W0–W6 已全部落地)

> 计划 [memory-bank/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html](../plans/26-09-21-0024-qb-corpus-capture-replay-plan.html) (v3 已拍板) · 任务档案 [tasks/26-09-21-qb-corpus-capture-replay.md](../tasks/26-09-21-qb-corpus-capture-replay.md)

- ⬜ **残留**: 真机走查清单里约 13 条观感项待用户目视(不得计入闭环); TASK015 待含 error 态种子的语料。

### 规则系统

#### 事件触发(规则)规划 (2026-09-12 设计定论, 已实现)

**核心原则** — 区分"触发(瞬时)"与"结果(异步/状态式)"两种调度, 事件两者都要支持:

| 环节 | 触发方式 | 依据 |
|------|---------|------|
| 事件检测 + 事件规则动作入口 | 同步即时 (当拍快照, 不排队) | 事件是对瞬时状态转移的反应, 延后失真 |
| checking 动作的提交判断 (execute 决策链) | 同步即时 (随事件入口执行) | 判断"该不该校验"读瞬时状态 |
| checking 动作的结果轮询/组内等待 | 走队列 (现状 check / check-wait) | 轮询异步终态, 延后无害 |
| 校验成功后事件规则断点续跑 | 走队列 (`add_task(origin, keep_progress=True)`) | 复用现有 origin 恢复机制 |

**为事件造"可恢复 origin" (关键机制)**: 事件触发时 `_apply_event_rule` 传入真正的 `Task` 对象 (kind="rule-event", 一次性任务) 作 `ctx.task`, 而非 None。这样 `_execute_full_checking` 的 `origin = ctx.task` 就是该 rule-event 任务: 校验成功 → `on_success()` + `tq.add_task(origin, keep_progress=True)` → 断点保留 → 下 tick `_handle_event_rule` 从断点续跑事件后续动作; 失败/删除 → `add_task(origin)` 默认重置重走完整决策链 (删除由事件 handler 的删除守卫判死)。

**rule-event 任务的可恢复但一次性双重性质**: 它从不被 `run_due` 主动弹出 (事件分派时**不 add_task**, 避免被当周期任务弹掉/占 max_tasks 计数); 只在两条路径出现 — (A) 事件分派即时执行: `_apply_event_rule` 拿到 process 返回后持有 Task 对象作 origin, 不接 `_fast`; (B) 断点续跑: 轮询子任务 `add_task(origin, keep_progress=True)` 把它入 `_fast`, 下 tick `_handle_event_rule` 执行并从断点续跑后**返回 FINISHED 消亡** (恒不自我周期循环, 除非再遇 pending)。

**触发时机 × 动作白名单** (`_validate_trigger_action_compat`, config 阶段 fail-fast):

| trigger | 允许动作 | 特别说明 |
|---------|----------|---------|
| `interval` | 全部 12 | 现状 |
| `on_torrent_added` | 全部 12 含 checking | 事件入口 + origin 续跑 |
| `on_torrent_state_enum_changed` | 全部 12 含 checking | 事件入口 + origin 续跑 |
| `on_torrent_deleted` | **仅 `print_torrent_details`** | 删除后 store 无该种子, `ctx.torrent` 回退删除前快照副本; 需活种子的动作 (启停/校验/限速/移动/汇报) 都无意义 → 拒绝; 只读留档动作适用。**此即"唯一待确认"的答案**: 因新增 `print_torrent_details`, 原空集白名单放宽为只读动作集 |

**性能与副作用**: 事件分派同步执行拉长单 tick (数千种子大库 + 大量事件时, 与 grouping 缺文件扫描同模式, 已被接受); `max_tasks_per_tick` 只约束队列里的轮询/恢复任务, 不约束事件即时分派。

### 其它功能
- 通知多渠道: webhook/邮件/Telegram 等(channels 配置结构已按列表预留, 与 traffic_source 同款演进路径); Windows 自定义图标(当前快捷方式图标为 Python 解释器图标, AUMID 来源名已实现); toast 交互按钮(需 winsdk)
- 插件系统: 直接支持自定义 Python plugin
- 根据流量接入更多数据源 (traffic_source 当前仅 traffic_monitor 单源, 代码已按列表预留)
- 与 PTD-cli 合作: 自动分析 HR 标签 / 暂停低分享率非免费种子 (想法.md 标注"需可行性验证")
- WEBUI 报表 §08 第 7 项(节拍对齐, 需先拍板方向)及同类端点的同样改法(低优先; 相关 Open issue [issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html](../issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html) — 原 activeContext 切片 26-09-19-0000-docs-plan-review-wrapup 于 2026-09-26 蒸馏并入此行)
- 分组/辅种安全: 跨组文件交叉紧急处置 —— 分组键不拦跨组文件交叉(部分重叠文件列表 / 大小写不同文件名 / junction·symlink 别名路径), 现有三条防线(组内大小一致性 / 同组下载冲突 / 缺文件扫描)全以同组为边界; 建议方向 = 全局物理路径映射检测 + 警告暂停, 细节开工拍板(Open issue [issues/26-09-22-2221-feat-cross-group-file-conflict.html](../issues/26-09-22-2221-feat-cross-group-file-conflict.html) — 原 activeContext 切片 26-09-22-2221-backend-cross-group-file-conflict 于 2026-09-27 蒸馏并入此行)
- 规则系统可选增强(待拍板): 新增「阻断下载」动作(整种子文件优先级置 0) —— qB 层已有该手段且 WEB UI 有手动入口, 规则动作集没有; 可行性实验见 [reports/26-09-27-0047-report-rule-iyuu-stop-guard.html](../reports/26-09-27-0047-report-rule-iyuu-stop-guard.html)
- 流量图采样间隔演进(D6, 独立后续切片): 默认 30s 改 1× `main_tick`(推荐哨兵 0 语义「跟随 main_tick」)+ 设置仅能按 `main_tick` 倍数设置(配置语义从秒值改倍数); 前置依赖「raw 桶数上限 `MAX_RAW_BUCKETS=2880`」已实施(计划 [26-10-07-2127](../plans/26-10-07-2127-plan-qb-traffic-rate-basis.html) S3), 两项实施时合并为一个切片, 按黄金法则 4 四处登记(models 字段 / validation 白名单 / schema Field / 守卫测试)。(原 activeContext 切片 26-10-07-2046-qb-traffic-rate-basis 于 2026-10-08 蒸馏并入此行)
