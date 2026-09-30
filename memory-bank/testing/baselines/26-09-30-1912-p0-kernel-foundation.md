# 基线 · 1843 passed + 3 skipped / 91% —— 内核化重构 P0 (契约 + 状态服务)

> 摘要: plan plans/26-09-30-1819 P0 全量实施 —— 纯加法零行为变化: 新增 core/module.py(Module 契约
> /AppContext/ModuleHost/EventBus 骨架, 287 行)+ core/state.py(StateService, 状态持久化自
> RuleEngineMixin 迁出, 227 行); qbmanager 808→1058(构造期立 ctx/host/events, config/store/api/state
> 属性对委托, 8 个状态方法单行委托); rule_engine 453→263(只留规则加载/种子级任务/事件分派)。
> 测试 +11(新守阵 tests/test_module_host.py: ctx.store is manager.store 同对象断言等)。
> 基线落在**合并远端 d4b22d8a 之后的新基线上**(远端同日两提交: 认领链修复 4989ad7a 与 WEBUI
> 标签列全量展开 d4b22d8a; 认领链修复与本轮回写件同文, stash 合流解决); 同日拍板 D1-D5 按推荐,
> 1751 号计划(hot-reload-simplify)标 Superseded 被吸收。
> 基线时间: 2026-09-30 19:12, 合流后复核 19:40 (develop @ d4b22d8a + 本轮改动) 制品: plans/26-09-30-1819 已置 In Progress。

TOTAL **1843 passed + 3 skipped / 91%**(13010 语句 / 1048 未覆盖 / 4372 分支 / 432 partial,
test.full 26.02s, rc=0, 合流后终树复核) —— 较上基线 26-09-30-1210(1829 passed + 3 skipped / 91% @ 87d154c7)增 14:
本轮 +11(tests/test_module_host.py: ctx 同对象 3 / state 委托与独立 round-trip 3 / ModuleHost
编排 4 / EventBus 注册序+suppress 1), develop 侧三提交(87d154c7..02a8e5d9: 长按连发 / explorer
前台 / commands 引擎透传)+3(test_web_shortcuts 等)。

## 本轮改动面

- 新建 2 src 文件: core/module.py(287 —— Module 协议 + BaseModule + ApplyResult + AppContext +
  EventBus + ModuleHost; 契约层不 import 业务包, 仅 TYPE_CHECKING 类型标注)、core/state.py(227
  —— StateService: load/损坏回退/schema 迁移链/原子写/materialize/maybe_flush(interval 调用方
  现读传入)/record_execution/get_exec_record/bind_field_snapshots/cleanup_orphan_tmp)。
- 新建 1 测试文件: tests/test_module_host.py(11 例, P0 指定守阵「ctx.store is manager.store
  同对象」在内; state 载荷同对象与基线重绑、委托换 config、宿主装配序/逆序停用/无条件
  apply/subscribe 回调/loop hooks 跳过、EventBus 注册序 + 抑制期零调用)。
- 摘除: core/mixins/rule_engine.py 453→263(状态持久化族 12 方法 + _CORRUPT + 相关 import 迁出)。
- 接线: qbmanager.py 808→1058(__init__ ctx/host/events 先立; config/store/api/state/state_file/
  _next_state_flush_at 属性对委托; _load_state/save_state/_maybe_flush_state/_bind_field_snapshots/
  _cleanup_orphan_tmp/_materialize_state_migration/record_execution/get_exec_record 单行委托,
  带 D4 清理指针; run()/apply_new_config 零改动)。
- 测试适配 1 文件: test_rule_engine.py(patch 目标随实现迁: rule_engine.logger/utils/os →
  auto_qb.core.state 对应符号 7 处; mock.patch.object(mgr, "save_state") → mgr.ctx.state.save 2 处;
  _state_migration_desc → ctx.state.migration_desc 1 处 —— 方法调用点 31 处未动)。
- 无新配置键、无新线程、无 state_file schema 变更、无行为变化(P0 纯加法)。

## 文档与制品

- plans/26-09-30-1819 Open → In Progress + §09 拍板记录(D1-D5 按推荐); doc-refs 修为仓库相对路径
  (裸文件名令认领链守阵红, 计划件自身缺陷随本段修复)。
- plans/26-09-30-1751 Open → Superseded + 被吸收横幅 + 反向声明 1819; 两份被引旧计划
  (26-09-20-0234 / 26-09-15-1124)补 doc-refs 反向声明。
- 立档 tasks/26-09-30-backend-kernel-module-refactor.md(P0 Done, P1-P6 Open)。
- 事实回写: systemPatterns/overview.md(实例状态分两层→三层 + ctx)、systemPatterns/client-and-state.md
  (状态持久化章节头改 StateService + 迁移注记)、modules/core-runtime.md(qbmanager 行 + module/state
  两新行)、modules/mixins.md(rule_engine 行)。
