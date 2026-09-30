# QbManager 内核化重构 — 分段计划已出 (待拍板)

> 摘要: 用户令「把 mixin/logging/notify/qb client/web server/task queue+rules/hr/config/webui/tray/
> 写 state 从 qbmanager 聚拢为统一管理的模块, qbmanager 只调度不含业务, 设计通用模块机制」并问
> 「这叫什么设计模式」。答案: **微内核架构 (Microkernel / Plug-in)** + IoC/DI (ctx 服务定位) +
> 事件总线 (Mediator 的 broker 变体); 成熟参照 Home Assistant (hass+集成生命周期) / Spring
> @RefreshScope / OSGi / VS Code ext host / pluggy。计划已出: 契约 = Module 协议 (sections/
> start/stop/apply/subscribe + 可选 loop hooks), 刷新管线 8 相位表, 10 模块清单, P0-P6 七段,
> 每段独立入库全量绿; 吸收 hot-reload-simplify 方向一协议为 apply 语义。
> 最后活动: 2026-09-30 18:30

- **已完成**(勘察轮): 两个 Explore agent 摸清 qbmanager(958 行=9 mixin)/mixins 依赖矩阵(grep 实测)/taskqueue(已通用)/cli/tray/webui server/routes 访问面/notify+logging 挂载点/HrRuntime(反向依赖仅 config+_hr_anchors, 对标形态)/rules registry(装饰器)/tests 耦合面(76 构造点, make_manager 279 处/18 文件, 高频属性 mgr.client×340/mgr.store×309)。
- **已完成**(本轮): 计划 [plans/26-09-30-1819-plan-kernel-module-refactor.html](../plans/26-09-30-1819-plan-kernel-module-refactor.html) — 三层模型(内核/能力服务/功能模块, 判据: 有无生命周期语义)、模块契约与事件相位(§4, 现 _refresh_torrents 顺序的忠实编码)、职责搬迁对照(§5)、P0-P6(§6, 风险递增; P5 最大一刀=rules+管线收口, qbmanager 958→≈450 行)、10 条运行时不变量(§7)、5 个决策点(§9)。
- **关键联动**: hot-reload-simplify(1751)方向一协议被本计划 §4.3 整体吸收, 决策点 D1 建议拍板本计划即视为方向一拍板、1751 标 Superseded —— **两案分头执行会在 apply 语义上互相踩**。
- **待办(用户侧)**: 拍板计划 §09 五个决策点(D1 热重载合并 / D2 checking 归属 / D3 tracker 服务化 / D4 别名层后置 / D5 命名); 拍板后计划冻结, P0 起每段独立入库走 tasks/ 档案。
