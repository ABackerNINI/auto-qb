# 26-09-30-backend-kernel-module-refactor — QbManager 内核化重构: 微内核 + 插件式模块

**Status:** In Progress
**Added:** 2026-09-30
**Updated:** 2026-09-30
**Summary:** 计划 26-09-30-1819 拍板按推荐(D1-D5)滚动实施: P0 内核地基(新增 core/module.py(Module 契约/AppContext/ModuleHost/EventBus 骨架)+ core/state.py(StateService, 状态持久化自 RuleEngineMixin 迁出), qbmanager 构造 ctx 挂服务、属性全委托; 1751 计划标 Superseded(被 D1 吸收)); P1 基建模块化(新增 core/modules 包 LoggingModule/NotifyModule 契约样板, 热重载 L1 手工重挂改 host.apply 无条件广播+整段短路, 托盘 4 处 _notify_handler 直写改 ctx.notify 公开方法)。P2-P6 待续。

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
| P1 | logging/notify 模块化 + 托盘改 ctx.notify | Done (2026-09-30) |
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

- **2026-09-30 P1 实施完成**(本 clone):
  - 新增 `core/modules/` 包(3 文件 140 行): LoggingModule(start 幂等闸合流构造期接线与 run 的 start_all 双入口; apply 段相等短路/段变重挂)+ NotifyModule(ctx 构造期注入 —— 托盘会话开关可能早于 run 的 start; start 无条件调 setup_notify(原 run() 口径, 未启用由其内部判 None); apply 先摘旧再 force=True 重挂保原 L1 语义; 托盘公开口 enabled_state/is_enabled/set_enabled)。
  - `qbmanager.py` 接线: 构造期装配清单挂入两模块(plan §3.3 顺序前缀, P2+ 全清单注释入档); `_setup_logging` 方法与 `_notify_handler` 私有字段删除(日志初始化改 `host.get("logging").start`, 单点在模块); run() 的 setup_notify 行改 `host.start_all(dry_run)`; apply_new_config 捕获整份旧配置传 `host.apply_all(old, config)` **无条件广播**, L1 分支只剩 qb 重连+web 重启(影子并行, P2 迁出)。
  - `tray/app.py` 4 处直写改公开口(405 状态同步/426 _notify_on/456+460 toggle): 读走 enabled_state/is_enabled, 写走 set_enabled(会话挂载 force 语义与 AutoQbError 上抛路径原样); setup_notify import 移除。
  - 行为变化仅限计划内: 无关保存(L1 命中但 logging/notify 段未变)不再重挂两 handler —— 过度重启族在 notify/logging 域消除, 段变路径语义与改前逐字节等价。
  - 守阵: 新建 `tests/test_core_modules.py` 7 例(段变才重挂/无关保存零动作 P1 指定守阵、托盘 API 契约、托盘+内核源码私有面清零静态守阵); test_module_host 装配断言改 ["logging","notify"]+ctx.notify 单一真相; test_web 两热重载守阵改写(L1 断言重连+web 重启, 替身区钉 logging/notify 段对象防 Mock 段被误判段变)。
  - 闸门: test.full 全绿(1850 passed + 3 skipped / 91%, 较 P0 基线 +7), 基线切片 `testing/baselines/26-09-30-2000-p1-foundation-modules.md`。
  - P2 待办注记: run() 的 web 启动块/hr.start/finally 停止序列改 host.start_all/stop_all 时, 装配序(logging→notify→webui→hr)与现启动次序(web→hr→notify)在 notify/web 之间换位 —— notify 不依赖 web, 无风险; LoggingModule.start 幂等闸届时仍兜构造期早建。
