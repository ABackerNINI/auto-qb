# 组件总览

> 📅 **内容基线**: 2026-10-01 @ `38604d07`(内核化重构 P0-P6 + 别名层处置 W0-W3 之后逐项对照代码核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。

> 摘要: 有哪些组件、谁负责什么 —— 进本目录前先读这一份。
> 触发: 组件, 总览, 架构, 有哪些模块, 谁负责什么

## 组件总览

```
                ┌──────────────────────────────────────────────────────────────┐
                │ QbManager (core/qbmanager.py)                                │
                │  = WebviewMixin + WebCommandsMixin (仅 2 个表现层 mixin,      │
                │    qbmanager.py:142-145)                                     │
                │  + 十模块经 ModuleHost 装配注册 (qbmanager.py:158-234)         │
                │  客户端构造在 core/qbclient.py(new_client/LocalQbClient)       │
                ├──────────────────────────────────────────────────────────────┤
 每tick增量同步 →│ TorrentStore (torrents/ 包: store/record/view/compat)         │
                │  快照/惰性缓存/分组索引        (写后同步)  ← QbApi (qbapi.py)   │
                │  ↑ apply_sync (sync/maindata rid 增量)      → qbittorrent-api │
                ├──────────────────────────────────────────────────────────────┤
                │ TaskQueue (taskqueue.py)  单一时间优先堆                       │
                │  Task 7 种 kind: refresh / rule / rule-event / torrent /      │
                │    internal / check / check-wait (taskqueue.py:33)            │
                ├──────────────────────────────────────────────────────────────┤
                │ rules/ : Rule + 13 条件插件 + 12 动作插件 (registry)           │
                └──────────────────────────────────────────────────────────────┘
                state(state_file JSON) ← 周期落盘 maybe_flush(state_save_interval
                默认 120s, qbmanager.py:530-535) + 优雅退出即落盘 (:577-578)
```

**组合关系**: `QbManager(WebviewMixin, WebCommandsMixin)`(`core/qbmanager.py:142-145` —— 内核化重构后只剩 2 个表现层 mixin, 原功能 mixin 已全部转正为模块)。十模块在构造期按装配序注册(`qbmanager.py:158-234`): LoggingModule → NotifyModule → WebUIModule(`webui/module.py` 门面) → HrModule(`hr/module.py` 门面) → TrackerModule → SpeedCurveModule → MaintenanceModule → GroupingModule → OpsModule → RulesModule —— 8 个在 `core/modules/`, webui/hr 两门面各自成模块; rules 最后注册(它消费前面所有人的服务)。装配顺序 = 相位内消费序 = 生命周期序; `__init__` 是唯一组合根, 也是内核唯一「知道模块名字」的地方。模块实现 Module 契约(`core/module.py`: sections/start/stop/apply/subscribe), 由 ModuleHost 编排生命周期、EventBus 做相位广播(七刷新相位 + queue_rebuilt/rebuild_runtime, 见 [main-loop.md](main-loop.md))。

**实例状态分三层**(2026-09-30 P0 起, plan kernel-module-refactor): 能力服务(`store`/`api`/`state`/`config`)挂 `self.ctx`(AppContext, 单一真相), manager 同名属性全是委托(属性面 D1 拍板**永久保留**, 2026-10-01 —— `qbmanager.py:267-273`); 核心域机制(`task_queue`/`_wake_event`/`host`/`events` …)留在 `__init__`; **WEB 表现层状态全部在 `self.web`(`WebUIRuntime` 门面, 2026-09-20 拆出)** —— 旧字段名的转发层已随别名层处置 W3 整体退役(2026-10-01, 反复活守阵 `tests/test_qbmanager_alias_freeze.py`), 新旧代码一律写 `manager.web.<字段>`。

**状态落盘**(2026-09-22 起, issue 26-09-21-1347 推翻「仅退出落盘」的旧取舍): 主循环每轮调 `ctx.state.maybe_flush` 周期落盘(间隔 `state_save_interval` 默认 120s / 配置端下限 30s / 0=关闭, `qbmanager.py:530-535`), 优雅退出再 `save` 一次(`:577-578`)。持久化语义单点见 [client-and-state.md](client-and-state.md)。
