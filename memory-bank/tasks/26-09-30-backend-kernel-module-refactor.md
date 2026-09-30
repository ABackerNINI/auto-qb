# 26-09-30-backend-kernel-module-refactor — QbManager 内核化重构: 微内核 + 插件式模块

**Status:** In Progress
**Added:** 2026-09-30
**Updated:** 2026-09-30
**Summary:** 计划 26-09-30-1819 拍板按推荐(D1-D5)并实施 P0 内核地基: 新增 core/module.py(Module 契约/AppContext/ModuleHost/EventBus 骨架)+ core/state.py(StateService, 状态持久化自 RuleEngineMixin 迁出), qbmanager 构造 ctx 挂服务、属性全委托; ctx 同对象守阵上线; 1751 计划标 Superseded(被 D1 吸收)。P1-P6 待续。

**Topics:** backend-kernel-module-refactor

**Legacy-ID:** 无

## 原始请求

用户: 「实施计划P0: plans/26-09-30-1819-plan-kernel-module-refactor.html, 拍板按推荐」—— 实施 P0(内核地基: 契约 + 状态服务, 纯加法零行为变化), 五个决策点 D1-D5 全按计划推荐拍板。

## 思考过程与决策

- **D1-D5 按推荐拍板**(2026-09-30): D1 本计划吸收 hot-reload-simplify 方向一, 1751 号计划标 Superseded; D2 checking 并入 ops; D3 tracker 匹配做 ctx 服务; D4 别名层处置另立后续计划; D5 保留 QbManager 命名。
- **ctx 服务面取最小集**(P0 范围裁定): `AppContext` 只挂 config/store/api/state 四项(plan §3.1 服务清单的 P0 子集); client 的绑定逻辑(连 store/api/reset_sync)留在内核 client property, 连接管理属内核; task_queue/web/hr 不上 ctx(前者是内核机制, 后两者 P2 门面转正时处理)。
- **manager.state 委托到 `ctx.state.data`(dict)而非服务对象**: 测试 8 处 `mgr.state = {...}` 整体替换 + 多处 `mgr.state[...]` 直读 + rules 动作 `ctx.manager.state` 全是 dict 语义; 服务对象经 `mgr.ctx.state` 可达。plan §7.2 的「指向 ctx 同一对象」对 state 取「载荷同对象」解释, 收口在 P5。
- **周期落盘的 interval 由调用方现读传入**(`maybe_flush(now, interval)`): 服务自身不持配置, 热重载 L0「改 state_save_interval 即刻生效」语义由 manager 每调用读 config 保住; 避免服务反向依赖 config/manager。
- **`_next_state_flush_at` 与 run() 的字面量**: test_periodic_flush_is_wired_in_run 钉死 run() 源码含 `self._next_state_flush_at = time.time()` 字面量与 `_maybe_flush_state` 接线 —— 故管理器侧保留同名属性对(委托 service.next_flush_at), run() 零改动。
- **测试 patch 目标随实现迁**: test_rule_engine 对 `rule_engine.logger/utils/os` 的 mock.patch.object 与 `mock.patch.object(mgr, "save_state")` 拦截点改钉 `auto_qb.core.state` 模块与 `mgr.ctx.state.save` —— 语义不变, 只是实现搬家后 patch 必须跟着走; 31 处**方法调用点**未动。

## 实现计划

P0-P6 见 [计划 26-09-30-1819](../plans/26-09-30-1819-plan-kernel-module-refactor.html) §06; 本档案只记执行进度与偏差。每段验收: test.full 全绿 + 段内守阵 + 基线切片。

## 子任务状态表

| 段 | 内容 | 状态 |
|---|---|---|
| P0 | 契约 + 状态服务(纯加法) | Done (2026-09-30) |
| P1 | logging/notify 模块化 + 托盘改 ctx.notify | Open |
| P2 | webui/hr 门面转正 Module 契约 | Open |
| P3 | tracker / speed_curve / maintenance 小模块 | Open |
| P4 | grouping / ops(+checking) 中坚模块 | Open |
| P5 | rules 模块化 + 刷新管线收口 | Open |
| P6 | 回写 + 基线 + 真机走查 + 段认领守阵 | Open |

## 进度日志

- **2026-09-30 P0 实施完成**(本 clone):
  - 新增 `core/module.py`(~250 行): Module 协议(runtime_checkable, sections/start/stop/apply/subscribe)+ BaseModule(无操作默认, 刻意不定义 loop hooks)+ ApplyResult + AppContext(config 属性对托管热重载换对象)+ PhaseEvent/PhaseRegistry + EventBus(注册序同步分发 + 总线级 suppress)+ ModuleHost(注册保序/无名重名 fail-fast/装配点回调 subscribe/start·apply 装配序·stop 逆序/loop hooks getattr 探测)。
  - 新增 `core/state.py`(~230 行): StateService 收拢 load/_read_state_file/_migrate_state_dict/_state_write_payload/_write_back_recovered/cleanup_orphan_tmp/save/materialize_migration/maybe_flush/record_execution/get_exec_record/bind_field_snapshots; 回归注释随迁。
  - `core/mixins/rule_engine.py` 摘除状态持久化族(453→~260 行), 只留规则加载/种子级任务/事件分派。
  - `qbmanager.py` 接线: `__init__` 先立 ctx/events/host, config/store/api/state/state_file/_next_state_flush_at 变属性对委托, 8 个状态方法留单行委托(带过渡层标注与 D4 清理指针); run()/apply_new_config 零改动。
  - 守阵 `tests/test_module_host.py` 11 例: ctx.store/api/config is manager 同对象(P0 指定守阵)、state 载荷同对象与基线重绑、委托换 config、record 委托回环、StateService 独立 round-trip、maybe_flush 三语义、宿主注册序/fail-fast/subscribe 回调/生命周期序/loop hooks 跳过、EventBus 注册序+suppress。
  - test_rule_engine patch 目标随迁(5 处 logger/utils/os + 2 处 save_state 拦截点 + `_state_migration_desc`→`ctx.state.migration_desc`)。
  - 文档回写: 1819 计划 Open→In Progress + 拍板注记 + doc-refs 修为仓库相对路径(此前裸文件名令 test_docs_forms 认领链守阵红, 属计划件自身缺陷, 随本段修复); 1751 计划 Open→Superseded + 反向声明 1819。
  - 闸门: test.full 全绿(1843 passed + 3 skipped / 91%, 含新守阵 11 例), 基线切片 `testing/baselines/26-09-30-1912-p0-kernel-foundation.md`(合流 d4b22d8a 后复核, 数字不漂)。
