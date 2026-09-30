# QbManager 内核化重构(P0 完成, P1-P6 待续)

> 摘要: plan 26-09-30-1819 已拍板(D1-D5 按推荐), P0 内核地基实施完成 —— core/module.py 契约+宿主+总线骨架、core/state.py StateService(状态持久化自 RuleEngineMixin 迁出)、qbmanager 属性全委托 ctx; 1751 计划标 Superseded。test.full 1843+3 / 91%。
> 最后活动: 2026-09-30 19:12

## 已完成

- P0(2026-09-30): Module 协议/AppContext/ModuleHost/EventBus 骨架(core/module.py, 287 行); StateService 迁出状态持久化(core/state.py, 227 行; rule_engine 453→263); qbmanager 构造期立 ctx/host/events, config/store/api/state/state_file 属性对委托, 8 个状态方法单行委托; 守阵 tests/test_module_host.py 11 例(ctx.store is manager.store 同对象等); test_rule_engine patch 目标随实现迁 10 处。基线切片 testing/baselines/26-09-30-1912。
- 拍板回写: 1819 计划 In Progress + §09 拍板记录 + doc-refs 修为仓库相对路径(顺带修好认领链守阵); 1751 计划 Superseded(方向一被吸收, W1-W4 → P1/P2/P5); 两份被引旧计划补反向声明。
- 档案: tasks/26-09-30-backend-kernel-module-refactor.md(P0 Done); 事实回写 systemPatterns/overview(状态分三层)/client-and-state(StateService 章节)/modules/core-runtime(qbmanager 行 + 两新行)/modules/mixins(rule_engine 行)。

## 正在进行

- 无(等下一轮指令)。

## 下一步(按计划 P1-P6, 未开工)

- P1 基建模块化: LoggingModule/NotifyModule 立契约样板 + run() 内 setup 改经模块(影子并行) + 托盘 4 处 `_notify_handler` 直写改 `ctx.notify`。
- P2 门面转正: WebUIRuntime/HrRuntime 挂 Module 协议, 主循环 `self.web.*` 五语义调用改 loop hooks。
- P3-P5 小/中坚/最大一刀(tracker+speed_curve+maintenance → grouping+ops → rules+刷新管线收口)。
- P6 回写 + 真机四场景走查 + 段认领守阵; 别名层处置另立计划(D4)。
