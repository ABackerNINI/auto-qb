# 26-09-30-backend-kernel-module-refactor — QbManager 内核化重构: 微内核 + 插件式模块

**Status:** In Progress
**Added:** 2026-09-30
**Updated:** 2026-10-01
**Summary:** 计划 26-09-30-1819 拍板按推荐(D1-D5)滚动实施: P0 内核地基(新增 core/module.py(Module 契约/AppContext/ModuleHost/EventBus 骨架)+ core/state.py(StateService, 状态持久化自 RuleEngineMixin 迁出), qbmanager 构造 ctx 挂服务、属性全委托; 1751 计划标 Superseded(被 D1 吸收)); P1 基建模块化(新增 core/modules 包 LoggingModule/NotifyModule 契约样板, 热重载 L1 手工重挂改 host.apply 无条件广播+整段短路, 托盘 4 处 _notify_handler 直写改 ctx.notify 公开方法); P2 门面转正(新增 webui/module.py WebUIModule + hr/module.py HrModule, run() 启停改 host.start_all/stop_all, _apply_web_config 并入 webui.apply, 主循环五语义调用改 loop hooks, store.hr_link 注入移进装配, start_web_server 不再写 manager._web_token); P3 小模块先行(新增 tracker_mod/speed_curve_mod/maintenance_mod 三模块: tracker 匹配升 ctx.trackers 服务(D3)+full_round 相位重匹配, 曲线任务自注册+流量快照改 ctx.web.set_traffic_view 服务方法, TagsMixin+_handle_maintenance+delete_tags+集数标签一起搬+全局任务自注册, _create_global_tasks 任务点名退役只剩 queue_rebuilt 相位兼容转发, mixins 包删三文件, AppContext 增 task_queue/web/trackers, TaskQueue 增 has_named 幂等守卫, WebUIRuntime 增 set_traffic_view, manager 旧名方法留单行委托); P4 中坚模块(新增 grouping_mod(GroupingModule: GroupingMixin 387 行迁入, 认领 transitions/torrents_added/removed_scan/post 四刷新相位, enabled 开关与缺文件扫描轮内去重集合归模块自管, _refresh_torrents 分组调用点改相位广播) + ops_mod(OpsModule: OpsMixin 474 行 + CheckingMixin 39 行迁入(D2), 升 ctx.ops 服务, web 命令改走 ctx.ops) + rules/checking_meta.py 中性叶(轮询常量+冷却 helper 迁入, ops 与 rules 单向化), AppContext 增 maintenance/ops 句柄); P5 最大一刀(新增 core/modules/rules_mod.py(RulesModule: RuleEngineMixin 全部迁入, 事件分派改 events_removed/events_added 相位 + 建任务改 torrents_added 相位, L2 重建收进 rules.apply(hot-reload W3), 级别分派层与 impact 三张手写表退役(W4, impact.py 只留 diff+R 闸)); _refresh_torrents 收口为「同步 + 相位广播」(§4.2 相位表生效, 逐种子管线(限速/维护+集数/归组/建任务)按装配序分派四模块订阅), _suppress_events 收口进总线 suppress(take_suppressed 窗口协议, 只覆盖两个事件相位); 内核零 rules import(AST 守阵); _hr_anchors 迁 HrRuntime(plan §05); rules 动作改 ctx.ops)。P6 待续。

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
| P2 | webui/hr 门面转正 Module 契约 | Done (2026-09-30) |
| P3 | tracker / speed_curve / maintenance 小模块 | Done (2026-09-30) |
| P4 | grouping / ops(+checking) 中坚模块 | Done (2026-09-30) |
| P5 | rules 模块化 + 刷新管线收口 | Done (2026-10-01) |
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

- **2026-09-30 P2 实施完成**(本 clone):
  - 新增 `webui/module.py`(106 行, WebUIModule)与 `hr/module.py`(41 行, HrModule): 门面转正走**契约封装**而非「只换基类」—— WebUIRuntime 的 SSE `subscribe()` 与 Module.subscribe 撞名、HrRuntime.start/apply 签名有内外调用点, 且 plan §3.3 装配清单本就点名 WebUIModule/HrModule 类。两模块经 manager 现取门面对象(不缓存引用): 测试整体替换 mgr.web/mgr.hr(test_apply_new_config_levels 的 `mgr.hr = MagicMock()` 等)时模块自动跟随。
  - WebUIModule: start(dry-run/未启用无操作 + handle 幂等闸)/stop(只 handle.stop() 不等线程, 原 finally 口径)/apply(_apply_web_config 语义迁入: mark_dirty 有差异即置脏(plan §4.3「不能完全短路」) + 监听身份对比, 相等 ensure_token / 不等先 stop_web_server 等退出再启新或停净)/loop hooks(on_command_line/on_sync_line/on_task_line)。WebUIRuntime 增 ensure_token/start_server/stop_server —— 令牌生命周期内聚门面, start_web_server 删 `manager._web_token` 直写。
  - HrModule: apply 透传 old.hr_check(短路/重建判据单点仍在 HrRuntime.apply); sections 认领 ("hr_check","trackers") —— 站点绑定派生自 trackers.X.hr_check, 只认 hr_check 会在 P6 段认领守阵漏判。
  - qbmanager.py 1060→1023: 装配清单挂入两模块 + `store.hr_link = self.hr` 注入移进装配块; run() web 启动块/hr.start/finally 手工停止序列删除(改 host.start_all/stop_all, 逆序 hr→webui→notify→logging); 主循环命令线改 host.run_command_line, _sync_line/_task_line 收尾改 run_sync_line/run_task_line; apply_new_config 删 mark_dirty 手工行/old_web/old_hr_check 捕获/L1 web 重启/hr.apply 手工调, L1 分支只剩 qb 重连; `_apply_web_config` 方法删除。
  - 行为变化仅限计划内(三处, 均评估过): ①advance_error_reasons 自任务执行**前**移至任务线收尾 hook(预取变更经置脏同轮可见, 无顺序钉点); ②token 同步时机自「L1 且身份未变」扩展为「每次热重载且身份未变且在跑」(ensure_web_token 幂等); ③零差异保存不再置脏视图(原无条件 mark_dirty)。关停顺序 web 先于 hr 换为 hr 先于 web(装配逆序, 资源独立)。
  - 守阵: 新建 `tests/test_facade_modules.py` 9 例(webui start 语义/stop 口径/置脏判据/仅身份变化才重启/loop hooks 次序/hr 契约/run 接线守阵「主循环不再点名 self.web.* 五调用、flush_truths 留内核」/装配+判定桥/start_server 先密钥后服务); test_module_host 装配断言改四模块; test_web 两守阵改经 `mgr.host.get("webui").apply(old, new)` 驱动并更名, 两处 MagicMock 配置补钉 `new_cfg.web = mgr.config.web`(Mock 段不钉会被误判身份变化而真启服务器)。web stop+wait 竞态/hr 从无到有三件套/别名代理层既有守阵零改动全绿。
  - 闸门: test.full 全绿(1860 passed + 3 skipped / 91%, 较上基线 +9), 基线切片 `testing/baselines/26-09-30-2048-p2-facade-modules.md`。
  - P3 待办注记: `_create_global_tasks` 的 delete_tags/speed_limit_curve 任务随 MaintenanceModule/SpeedCurveModule 自注册; `_match_tracker_conf` 升 ctx.trackers 服务(D3); `_hr_anchors` 经 ctx 回调取锚点(plan §05, HrRuntime getattr 窥探届时清)。

- **2026-09-30 P3 实施完成**(本 clone):
  - 新增 `core/modules/tracker_mod.py`(93 行, TrackerModule): `match()`=原 `_match_tracker_conf`(utils.match_tracker_confs 同语义, 多匹配 WARNING 随迁)+ `apply_speed_limit` 单种限速; subscribe 订阅 **full_round 相位**(plan §4.2)—— `_refresh_torrents` 全量轮的重匹配循环改 `events.emit("full_round")`, 内核只报时机; client 经 `ctx.api.client` 现取(重连换客户端随 QbApi.bind 同步链); apply 恒短路(匹配每轮现读 config, 存量重匹配只在全量轮)。
  - 新增 `core/modules/speed_curve_mod.py`(321 行, SpeedCurveModule): `handle_speed_limit_curve` 逐字节随迁(聚合/查档/取最严/手动保护/回读); 曲线任务 **start 自注册**(gslc None 不建, interval=gslc.interval or 主 interval)+ subscribe 订阅 **queue_rebuilt 相位**(L2 队列重建后按新配置重入队); `_curve_manual_log` 节流状态收进模块实例(manager 代持删除); `_publish_traffic` 改经 `ctx.web.set_traffic_view` 服务方法(plan §5 跨层直写清零); `_record_curve_state` 经 ctx.state.data。
  - 新增 `core/modules/maintenance_mod.py`(339 行, MaintenanceModule): TagsMixin 全部方法公开名迁入(add_tags/remove_tags/add_episode_tags/remove_similar_tags/set_category/create_category_if_not_exists/add_hr_tag_or_category, `_seed_exempt_baseline` 随迁)+ qbmanager 本体的 `_handle_maintenance`(maintenance_tag_mode 判据随迁)+ delete_tags 两全局任务(start 自注册 + queue_rebuilt 重入队)+ sections 四段认领(delete_tags/delete_tags_if_has_no_torrents/add_episode_tags/maintenance_tag_mode)。
  - 内核退役: `_create_global_tasks` **任务点名本体删除**(plan §3.2/§5), 只剩 §7.2 兼容转发 —— 单行 emit("queue_rebuilt")(L2 分支与 test_web 守阵仍走它); run() 删该调用(start_all 已自注册, 入队时点自「连接成功后」前移到启动, 队列首个任务线才 drain, 行为等价); mixins 包删 tags.py/tracker.py/speed_curve.py 三文件, manager 新增 P3 委托层 14 个单行方法(§7.2: mgr._xxx 直调与相邻 mixin 引用零改动)。
  - 契约层: AppContext 增 task_queue/web/trackers 三挂点(manager 属性对委托, ctx 单一真相; task_queue 支撑模块自注册现取当前队列, web 支撑流量快照发布, trackers 是 D3 服务句柄); TaskQueue 增 `has_named(name)`(kind=internal 且无 hash)—— 全局任务自注册的幂等守卫单点(黄金法则 1; 队列本身只对 check 任务去重); WebUIRuntime 增 `set_traffic_view(view)` 发布口。
  - 守阵: 新建 `tests/test_modules_p3.py` 11 例(ctx.trackers 装配本体+装配序 / full_round 重匹配 conf 置空记录 / 曲线 start 入队+重复幂等 / 未配置不建任务 / 队列重建按新 interval 重入队 / 兼容转发双模块入队+同队列幂等 / ctx.web 服务方法发布+别名同源 / delete_tags 按配置入队 / 队列重建重入队 / sections 认领锁定); test_module_host 装配断言改七模块 + task_queue/web/trackers 同对象; test_speed_curve import/logger 名/节流白盒断言改指模块(host.get("speed_curve")._curve_manual_log); test_tracker logger 名随迁; test_trigger_events `_spy_tags_part` 改装模块实例的 add_tags(handle_maintenance 内部直调模块方法, manager 委托已不在调用路径上 —— 测试 seam 跟实现走)。
  - 设计取舍(本段唯一的机制发明): **queue_rebuilt 相位** —— L2 重建队列后全局任务重入队需要内核→模块触发, 复调 host.start_all 不可行(HrRuntime.start 先 stop 再重建会真重启取数线程), 级别分派表又是 P5 退役对象; 用既有 EventBus 广播「队列重建」领域事件(plan §2 调停者语义), 模块订阅自注册, 内核知道「何时」不知道「何事」; P5 L2 重建收进 rules.apply 后由其继续 emit, 机制可存活。
  - 未动项注记: HrRuntime._anchors 对 manager._hr_anchors 的 getattr 窥探归 P5(plan §05 目标「经 ctx 回调」随 rules 模块化收口); 分组 mixin 对 `_add_tags` 的一处调用经 manager 委托保持(P4 grouping 模块化时改 ctx 口)。
  - 闸门: test.full 全绿(1871 passed + 3 skipped / 91%, 较上基线 +11), 基线切片 `testing/baselines/26-09-30-2142-p3-small-modules.md`(合流 83e56f1f 后实测)。

- **2026-09-30 P4 实施完成**(本 clone, 用户指令「实施计划P4…拍板按推荐」):
  - 新增 `core/modules/grouping_mod.py`(~390 行, GroupingModule): GroupingMixin 全部方法原样迁入(self.store/api/config 改 ctx 现取, client 经 ctx.api.client 现取)+ `group_key_of` 纯函数随迁(scripts/qb_capture.py 单一事实源, import 路径随迁); sections ("grouping"); **订阅四刷新相位**(plan §4.2 忠实编码): transitions(入口先清 _missing_scanned_keys 再判 enabled —— 去重清零时序与原内核每轮开头无条件 clear 逐字节等价, enabled 翻转不吞首轮扫描)/torrents_added(payload 带 hash+dry_run, 当前唯一认领者, 其余四家 P5 随逐种子管线并入)/removed_scan/post; `grouping.enabled` 开关模块自判(内核广播不再带 guard); MISSING 打标改 `ctx.maintenance.add_tags`(AppContext 增 maintenance 句柄, 模块间不 import)。
  - 新增 `core/modules/ops_mod.py`(~560 行, OpsModule): OpsMixin 全部迁入(公开动词 `recheck`/`skip_check`, R1/R2/冷却/备份/布局推断语义逐行随迁)+ CheckingMixin.check_filelist 并入(决策点 D2); sections ("skip_checking_tag"); `state` 属性 + `save_state()` 经 ctx.state 门面 —— 供 checking_meta 冷却 helper 的鸭子类型宿主面(manager 与本模块同满足, 测试直传 mgr 不变)。
  - 新增 `rules/checking_meta.py`(~60 行, 中性叶): 轮询常量(CHECK_RESULT_INTERVAL/RECHECK_FAIL_LIMIT/GROUP_CHECK_WAIT_LIMIT/CHECK_START_GIVEUP)与冷却 helper(_recheck_fail_count/_bump_recheck_fail)自 actions/full_checking.py 迁入(plan §5「迁到 rules 包中性位置; ops 与 rules 单向化」)—— ops 对 rules 的 import 收敛为「中性叶 + rules.base(ActionResult)」两个已鉴定的叶子, 不再拖 actions 插件注册; full_checking.py 从 checking_meta 再导出(测试导入路径不变), actions/__init__ 改从 checking_meta 取常量; 本叶子不 import actions/core, 防环方向写进头注。
  - 内核接线: 装配清单挂 GroupingModule + OpsModule(ctx.ops 句柄, plan §3.3 序 maintenance→grouping→ops); `_refresh_torrents` 四个分组调用点改 `events.emit(...)`(payload: transitions/post 带 dry_run, torrents_added 带 hash+dry_run, removed_scan 带 hashes+dry_run); `_missing_scanned_keys` 字段与每轮清零从内核删除; P4 委托层 15 个单行方法(§7.2: mgr._check_download_conflicts/_assign_new_torrent/_group_*/ops_recheck/ops_skip_check/check_filelist 等, 测试与 rules 动作零改动); mixins 包删 grouping/ops/checking 三文件。
  - web 命令改 ctx.ops(plan P4 指定): commands.py 三处(recheck 单发 / 右键跳检 / bulk 逐个提交)改 `self.ctx.ops.recheck/skip_check`; 规则侧(full_checking/skip_checking 委托入口)仍走 manager 旧名, P5 收口。
  - 守阵: 新建 `tests/test_modules_p4.py` 8 例(ctx.ops/ctx.maintenance 装配本体+序 / 四相位各恰一订阅者+emit 计数 / enabled 自判+去重清零先于 enabled 判定 / torrents_added 相位归组+disabled 零动作 / removed_scan+post 相位驱动 / ctx.ops 直调与旧名委托共享在途互斥 / check_filelist 双路可达 / sections 认领锁定); test_module_host 装配断言九模块; test_checking patch 目标 5 处随迁 ops_mod; test_file_access _bare_grouping 改 GroupingModule fake-ctx 宿主; test_utils/test_actions 类名与 patch 目标随迁; test_grouping 去重清零改经 host.get("grouping"); scripts/qb_capture.py import 随迁; test_web 守阵文案改 ops_mod。「缺文件扫描与跳检代表种两口径不混」断言保留(两判据各自单点, docstring 互指)。
  - 文档回写: code-style.md 日志目录 owner 改模块名(2 行); systemPatterns/taskqueue.md 与 rule-system/checking.md ops 执行体指针改 ops_mod; modules/mixins.md 加「P0-P4 已迁出」警示头; 1819 计划拍板注记/colophon/meta 加 P4; 基线切片 testing/baselines/26-09-30-2250-p4-core-modules.md。
  - 闸门: test.full 全绿(**1879 passed + 3 skipped / 91%**, 较上基线 +8, 26.6s), 基线 `26-09-30-2250-p4-core-modules.md`。
  - P5 待办注记: 逐种子管线(维护/限速/建任务/集数)并入 torrents_added 相位时, 内核现存的 `_dispatch_events`/`_suppress_events` 收进总线 suppress(plan §4.3); rules 委托入口改 ctx.ops; `_hr_anchors` 经 ctx 回调; L2 重建收进 rules.apply(hot-reload W3)。

- **2026-10-01 P5 实施完成**(本 clone, 用户指令「实施计划P5…拍板按推荐」):
  - 新增 `core/modules/rules_mod.py`(~410 行, RulesModule): RuleEngineMixin 其余部分整体迁入(状态持久化 P0 已先迁); 三条接线改相位/服务 —— ①事件分派订阅 `events_removed`/`events_added` 相位(plan §4.2), `_dispatch_events` 内核调用点退役; ②逐种子管线的「建任务」一步订阅 `torrents_added` 相位, `_create_torrent_tasks` 迁入(内置 maintenance 任务 handler 经 ctx.maintenance 句柄绑定, 不 import 兄弟模块); ③**L2 重建收进 rules.apply**(hot-reload W3 合并点): `_rebuild_needed` 判据段 = rules_config/interval/delete_tags*/global_speed_limit_curve + trackers 绑定三元组(domains/rules/groups —— tags/remove_tags/limits/hr_check 运行时现读不触发, 过度重建族防线), 整段相等短路; `rebuild_runtime` = 队列换新 + store.reset_runtime + _load_rules + queue_rebuilt 相位 + 总线 suppress 置位 + manager.reconnect。Rule/RuleContext 宿主面仍是 QbManager(构造期传入不换对象), 规则动作层零改动。
  - 刷新管线收口: `_refresh_torrents` 收为「同步 + 相位广播」—— 内核保留 schema 校验/fs 自检(fail-fast)、事件重放保护窗口、store 双快照收尾, 其余全为相位广播: full_round → transitions → events_removed → events_added → torrents_added(逐种子) → removed_scan → post(§4.2 相位表生效); tracker/maintenance 模块补 `torrents_added` 订阅(限速 / 维护+集数, 与 grouping 的 P4 订阅合流, 加 rules 共四家)。
  - 抑制窗口协议(plan §4.3): P0 骨架的「总线抑制=全轮 emit 跳过」与 §7.1「语义等价」不符(原 _suppress_events 只闸两个 _dispatch_events 调用点, 全量轮重匹配/分组相位在 L2 首轮必须照常跑) —— 落地为 `EventBus.take_suppressed()`: rules L2 置位 → 刷新轮首原子读走 → events_removed 前按需重挂 → events_added 后关闭, 窗口精确覆盖两个事件相位; 全量轮/逐种子管线不受抑制(守阵锁定)。
  - 逐种子管线次序偏差(文档化): plan §4.2 认领列(maintenance→tracker→rules→grouping)与 §3.3 装配序(tracker<maintenance<grouping<rules)矛盾, 「单订阅 + 装配序 = 相位内消费序」语义下两者不可双全; 按装配序实现 = 限速→维护+集数→归组→建任务, 依据: 相位内各步数据互不依赖(各只读 tracker_conf/store/config), 相位间次序精确保留; test_modules_p5 相位顺序守阵锁定, 变更必须是有意行为。
  - 内核退役: `mixins/rule_engine.py` 删除(mixins 包只剩 webui views/commands 组合入口); qbmanager 删 `from ..rules import Rule`(**内核零 rules import**, AST 守阵 test_kernel_does_not_import_business_packages); `_suppress_events` 字段删; `_create_torrent_tasks`/`_hr_anchors` 方法删(后者迁 `HrRuntime._anchors`, plan §05: 门面经 store 只读取数, 不再 getattr 窥私有面); manager 增 P5 委托层(rules/enabled_rules 属性委托带 setter + 9 个单行方法, §7.2)与 `reconnect()` 公开口(L1 qbittorrent 段变与 L2 重建共用, 模块不直写 client/_last_conn_ok 私有面)。
  - W4 三表退役: `config/impact.py` 96→52 行 —— SECTION_LEVELS/TRACKER_FIELD_LEVELS/HR_CHECK_FIELD_LEVELS 删除, 只留 `diff_config_impacts`(顶层段粒度, ConfigChange 改三参 path/old/new)+ `RESTART_SECTIONS`(state_file/data_dir/fs)+ `restart_required_paths`; apply_new_config 的 L1/L2 分支删除, 只剩 R 闸 + 换对象 + host.apply_all + qbittorrent 段变自判重连, 回执 levels→actions(W4); config/writer 的 R 级回退改只回退 R 闸命中段(顺带修正: 原逻辑经 level 过滤, 收缩后若整表回退会回退一切变更 —— 已在 _prepare 过滤); /api/config/schema 的 levels 改由模块 sections() 派生(claimed_sections, 前端无消费方); PUT 回执 changes 改路径串(前端只消费计数与 restart_required); rules 动作三处(full_checking/skip_checking/checking)改 `ctx.ops`(P4 待办收口)。
  - 守阵: 新建 `tests/test_modules_p5.py` 9 例(sections 认领 / 内核零 rules import AST / 相位订阅面+装配序 / 刷新相位顺序==§4.2 相位表 / 逐种子管线次序 / 抑制窗口只覆盖事件相位 / rules.apply 整段短路+段变重建 / 重建内存态保留 / 5000 种子短路 vs 重建耗时); test_impact 17 例收缩改写为 8 例(diff+R 闸口径); test_hr_config 6 个 impact 分级用例合并为 2(整段一条 + 不命中 R 闸); test_config_schema 的 hr_check 级别覆盖守阵退役(表已删); test_web 两热重载守阵迁移改写(levels→actions 回执断言, L2 重建断言走回执+总线 suppress, mock 段钉住 rules 六判据段 —— pitfalls/testing/hot-reload-mock-sections 的 P5 复查条款照做); test_core_modules 回执断言适配; test_module_host 装配断言十模块; test_modules_p4 torrents_added 订阅计数 1→4。
  - 测试基建根修(计划外, 属验收闸门阻塞项): helpers.FakeConfig 的段对象是**类属性共享可变对象**, 任一测试原地改(grouping.enabled/web.port/hr_check.enabled 等 11 处)泄漏到之后所有 make_manager —— 是否爆雷只取决于 xdist 分布, 本轮新增测试文件改变了分布使 `test_build_group_view`→`test_refresh_removed_grouping_disabled` 污染链实报(单跑恒绿)。根修: FakeConfig.__init__ 对非标量类属性深拷贝成实例属性(与真实 Config 每实例独立同形); 坑档新立 [pitfalls/testing/fake-config-shared-mutables.md](../pitfalls/testing/fake-config-shared-mutables.md)。同轮另修一处既有 flaky(闸门阻塞): test_hr_report::test_run_hr_status_rows_limit 断言裸 tid 子串撞 pytest 临时目录计数编号(pytest-1033 含 "103")假红 —— 断言改用该行默认种子名特征串 "EXAMPLE 103"(意图不变, 路径不可能撞)。
  - 实测数字(W3 验收): 5000 种子下 rules.apply 整段短路 **0.01ms**(3 轮中位) vs L2 重建 **0.7ms**(纯内存: 队列重建+conf 置空+规则重载, 不含 API 调用) —— 热重载保存的零规则相关变更成本趋近于零, 规则变更重建一次性成本可忽略。
  - 文档回写: modules/mixins.md(P0-P5 全迁出警示头)/overview.md(迁移映射注记)/core-config.md(impact.py 行改 diff+R 闸)/rules-and-deps.md(执行体指针改 ops_mod + 依赖图注记)/systemPatterns/web-config-editor.md(schema 端点描述)/config-reference/keys.md(删 SECTION_LEVELS 引用); 1819 计划拍板注记/colophon/meta 加 P5; 基线切片 testing/baselines/26-10-01-0245-p5-rules-pipeline.md。
  - 行数账: qbmanager.py 1023→1084(§7.2 委托层净增 ~60 行盖过迁移删除; 计划 ≤500 的口径未扣兼容层与别名层, 该目标随 D4 清理才可达; 「内核零业务 import」目标已达成且可 AST 验证); impact.py 96→52。
  - 闸门: test.full 全绿(**1876 passed + 3 skipped / 91%**, 31.6s), 基线切片 26-10-01-0245。
  - P6 待办注记: 段认领完备守阵(配置每段至少被一个模块认领 + 未认领段 WARN + 全量兜底); 文档回写(根 README 架构段/core-domain/conventions/modules 单点); dry-run 真机四场景走查; 别名层处置另立计划(D4)。
