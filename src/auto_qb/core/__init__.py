"""auto_qb 核心域包（core）

由根目录平铺文件归拢而来（plan 26-09-22-2112 · 方案 C · W4b）:
- qbmanager.py  QbManager 主协调者（微内核: 主循环三时间线 + 模块宿主 + 相位广播 +
                连接管理; 主循环唯一写线程）—— 业务已全部迁功能模块(plan
                kernel-module-refactor P0-P5), 旧名方法只剩单行委托(§7.2 测试兼容)
- module.py     内核地基: Module 契约 / AppContext / ModuleHost / EventBus
                —— 宿主只知「何时」, 不知「何事」
- modules/      功能模块包: logging / notify / tracker / speed_curve / maintenance /
                grouping / ops(+checking) / rules(装配清单见 qbmanager 构造期 §3.3)
- state.py      状态持久化服务 StateService（state.json 读写/迁移/周期落盘/执行历史单点;
                自 RuleEngineMixin 迁出, 26-09-30）
- taskqueue.py  单任务队列（add_task / run_due 两动词）
- qbapi.py      qB API Facade（写后同步快照）
- qbclient.py   qB 客户端构造（本地直连 trust_env 处理）
- curves.py     限速曲线纯逻辑（Traffic Monitor dat 解析/聚合/查档）
- episodes.py   集数解析（第x集 > S01E05 > EP05 > E05）
- tvshows.py    剧集识别（追剧视图聚合键）
- exporter.py   YAML 配置模板导出

依赖方向: core → config / infra / torrents / rules（单向）;
表现层（webui/tray）→ core 经门面与模块 ctx 口, core 不 import 表现层。
"""
