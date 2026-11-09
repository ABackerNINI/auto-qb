# 架构总览

> 摘要: 项目定位、四条设计不变量、黄金法则的设计依据、六大架构包边界与组合根装配 —— 进 architecture/ 先读这份。
> 触发: 架构, 总览, 不变量, 黄金法则, 组合根, 模块装配, AppContext, 有哪些模块

## 项目定位

auto-qb 是 qBittorrent 的规则驱动管理守护进程: 周期同步 qB 种子快照, 规则引擎按条件(状态/做种时间/限速曲线/HR 状态...)对种子执行动作(停种/跳检/删种/迁移/限速/汇报...), WebUI 供人查看与干预。全程经 qB WebUI API(`core/qbclient.py`)通信; 一切种子运行状态以 qB 为准, 本地只持有快照与决策产物。

## 四条设计不变量

1. **2s tick 主循环**: 主循环固定节拍 `main_tick`(默认 2s, `config/models.py:559`)驱动任务线; 同步线以 `sync_interval`(默认 1.5s)只刷快照不跑任务, 两线同拍合成完整一轮。所有异步效果都落在"队列任务在后续 tick 到期"这一个模型里, 不为此引入并发。
2. **单一写线程**: 主循环所在线程是唯一修改任务队列结构与 state_file 的线程, 全程无锁(展开见 main-loop-queue.md)。任何新功能都必须维持这个假设。
3. **增量同步 rid 语义**: 种子快照走 qB `/api/v2/sync/maindata` rid 增量(展开见 data-state.md); 漏 tick / rid 错位 / qB 重启都自愈为一次全量, 不丢数据。
4. **fail-fast 配置校验**: 配置在 `config.validation.core.validate_config`(`config/validation/core.py:280`)全量校验并聚合报错, 之后的代码假定配置正确 —— 校验通过后不再散布防御分支。

## 黄金法则的设计依据

| 法则 | 设计依据 |
|------|----------|
| 幂等性 | 重复执行不得有副作用; "每天一次"等窗口语义靠 state_file 去重(`core/state.py` `record_execution` 写 `exec_history`), 不依赖循环频率 —— tick 频率是性能参数, 不是正确性参数 |
| 保守默认 | 高风险动作(跳检/强制汇报/删除种子/覆盖限速)默认关闭, 只对显式配置范围生效 —— 程序无人值守跑在真实 PT 账号上, 误动作不可逆 |
| 状态持久化 | 跨轮次状态统一进 state_file; 周期落盘 + 优雅退出立即落盘, 非优雅终止丢失窗口 ≤ 间隔(决策档案 issues/26-09-21-1347-bug-backend-state-save-only-on-exit.html) |
| fail-fast | 同不变量 4; 聚合报错让用户一次修完所有配置错, 而非逐轮踩雷 |
| 单一写线程 | 同不变量 2; 免锁的前提是写点唯一, 允许并发写队列/state 就要在每处加锁, 漏一处即数据竞争 |
| 范围守恒 | 计划外的缺陷一行不改, 入池 `issues/` —— 保证每次变更可归因、评审面收敛 |

## 六大架构包边界

| 文档 | 边界 |
|------|------|
| overview.md(本篇) | 全局: 定位/不变量/黄金法则/组合根装配, 不进单包细节 |
| main-loop-queue.md | 主循环节拍与每轮数据流 + 任务队列模型 + 落盘时机(`core/qbmanager.py`, `core/taskqueue.py`, `core/state.py` 落盘面) |
| data-state.md | 种子数据层与增量同步 + QbApi 门面 + 配置加载校验 + state_file 结构(`torrents/`, `config/`, `core/qbapi.py`, `core/state.py`) |
| rule-engine.md | 规则引擎: 条件/动作插件 registry、断点续跑决策链(`rules/`, `core/modules/rules_mod.py`) |
| hr-groups.md | HR 站点对接(`hr/`)与分组、种子迁移(`core/modules/grouping_mod.py`, `core/modules/relocate_*`) |
| webui.md | Web 表现层: server/runtime/static、视图发布、truth 通道、表格几何单点(dt_table.layout, `webui/`, `manager.web` 门面) |

## 组合根与装配

`QbManager(WebviewMixin, WebCommandsMixin)`(`core/qbmanager.py`)是唯一组合根, 也是内核唯一"知道模块名字"的地方: 十模块在构造期按装配序注册 —— Logging → Notify → WebUI → Hr → Tracker → SpeedCurve → Maintenance → Grouping → Ops → Rules(rules 最后注册: 它消费前面所有人的服务)。装配顺序 = 相位内消费序 = 生命周期序。模块实现 Module 契约(`core/module.py:119`: sections/start/stop/apply/subscribe), 由 ModuleHost 编排生命周期, EventBus 做相位广播。内核化改造经过见 tasks/26-09-30-backend-kernel-module-refactor.md。

**实例状态分三层**: 能力服务(`store`/`api`/`state`/`config`/`ops`)挂 `self.ctx`(AppContext, 单一真相), manager 同名属性全是委托(属性面拍板永久保留); 核心域机制(`task_queue`/`_wake_event`/`host`/`events`...)留在 manager `__init__`; WEB 表现层状态全部在 `manager.web`(WebUIRuntime 门面) —— 新旧代码一律写 `manager.web.<字段>`。

## 读图顺序

新会话按"本篇 → 对应包文档"两跳, 包内细节以代码为准: 单文件职责看模块 docstring, 机制展开看包内注释; 历史决策查 `plans/`/`tasks/`/`issues/` 冻结档案, 踩坑记录查 `pitfalls/`。
