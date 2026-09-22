# 组件总览

> 📅 **内容基线**: 2026-09-05 @ `51374bd`(全库逐文件核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。

> 摘要: 有哪些组件、谁负责什么 —— 进本目录前先读这一份。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: 组件, 总览, 架构, 有哪些模块, 谁负责什么

## 组件总览

```
                    ┌──────────────────────────────────────────────────┐
                    │ QbManager (qbmanager.py)                         │
                    │  = RuleEngineMixin + TagsMixin + CheckingMixin   │
                    │    + GroupingMixin + TrackerMixin + SpeedCurveMixin
                    │    + WebviewMixin + WebCommandsMixin (2026-09-15 拆分)
                    │    客户端构造在 qbclient.py(_new_client/LocalQbClient) │
                    ├──────────────────────────────────────────────────┤
  每tick增量同步 →│ TorrentStore (torrents.py)   ← 快照同步 ──  QbApi (qbapi.py) ──→ qbittorrent-api Client
                    │  快照/惰性缓存/分组索引        (写后同步)      APIFacade
                    │  ↑ apply_sync (sync/maindata rid 增量)
                    ├──────────────────────────────────────────────────┤
                    │ TaskQueue (taskqueue.py)  单一时间优先堆          │
                    │  Task: internal / rule / check / check-wait      │
                    ├──────────────────────────────────────────────────┤
                    │ rules/ : Rule + 15条件插件 + 11动作插件 (registry) │
                    └──────────────────────────────────────────────────┘
                    state(state_file JSON) ← 仅退出时落盘
```

**组合关系**: `QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin, SpeedCurveMixin, WebviewMixin, WebCommandsMixin)`(2026-09-15 由 6 mixin 扩至 8, 同日拆分出 qbclient.py) — mixin 依赖宿主实例属性 (`config`/`store`/`api`/`state`/`task_queue`/`client`), 各 mixin 文件头部 docstring 声明了所依赖的属性, 新 mixin 照此模式写。`__init__` 是唯一组合根, 但**实例状态分两层**: 核心域状态(`store`/`api`/`task_queue`/`state`/`_wake_event` …)留在 `__init__`; **WEB 表现层状态全部在 `self.web`(`WebUIRuntime` 门面, 2026-09-20 拆出 19 个字段)** —— mixin 仍是纯方法簇(构建器只产出 dict, 命令处理器只发一次写操作), 快照/版本号/回执/索引/活跃心跳一概不留在宿主上。
