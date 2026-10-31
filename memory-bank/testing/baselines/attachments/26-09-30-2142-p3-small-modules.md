# 基线 · 1871 passed + 3 skipped / 91% —— 内核化重构 P3 (小模块先行: tracker / speed_curve / maintenance)

> 摘要: plan plans/26-09-30-1819 P3 全量实施 —— 三 mixin 迁出为功能模块: TrackerModule
> (core/modules/tracker_mod.py, _match_tracker_conf 升 ctx.trackers 服务(决策点 D3) + 全量轮
> 重匹配改订阅 full_round 相位) / SpeedCurveModule(speed_curve_mod.py, 曲线任务自注册(start +
> queue_rebuilt 相位重注册) + 流量快照改经 ctx.web.set_traffic_view 服务方法推送, _curve_manual_log
> 节流状态收进模块) / MaintenanceModule(maintenance_mod.py, TagsMixin 全部 + qbmanager._handle_
> maintenance + delete_tags 两全局任务 + 集数标签一起搬, 全局任务自注册); 内核 _create_global_tasks
> 任务点名退役(只剩 queue_rebuilt 相位广播的兼容转发, §7.2 委托), run() 启动路径改 start_all 承担。
> 契约层: AppContext 增 web/task_queue/trackers(manager 属性对委托, ctx 单一真相), TaskQueue 增
> has_named 幂等守卫, WebUIRuntime 增 set_traffic_view 发布口。mixins 包删三文件(tags/tracker/
> speed_curve), 旧名方法在 manager 留单行委托(plan §7.2)。
> 守阵: tests/test_modules_p3.py 11 例(新建); test_module_host 装配断言改七模块 + task_queue/web/
> trackers 同对象; test_speed_curve import/logger 名/白盒断言改指模块; test_tracker logger 名;
> test_trigger_events spy 改装模块实例; 限速/标签/集数/曲线节流既有守阵全绿。
> 基线时间: 2026-09-30 21:42, develop @ 83e56f1f + 本轮改动。

TOTAL **1871 passed + 3 skipped / 91%**(13108 语句 / 1050 未覆盖 / 4390 分支 / 428 partial,
test.full 27.4s, rc=0) —— 较上基线 26-09-30-2048(1860 passed + 3 skipped / 91%)增 11:
本轮 +11(tests/test_modules_p3.py: ctx 装配与序 1 / full_round 重匹配 1 / 曲线 start 入队+幂等 1 /
未配置不建任务 1 / 队列重建按新 interval 重入队 1 / 兼容转发双模块入队 1 / 同队列幂等 1 /
ctx.web 服务方法发布 1 / delete_tags 按配置入队 1 / 队列重建重入队 1 / sections 认领锁定 1)。

## 本轮改动面

- 新建 core/modules/tracker_mod.py(93 行, TrackerModule): match()=原 _match_tracker_conf
  (utils.match_tracker_confs 同语义, 多匹配 WARNING 随迁)/apply_speed_limit + _apply_single_
  speed_limit(单种限速)/subscribe 订阅 full_round(_on_full_round 重匹配 conf 置空记录)/
  sections ("trackers")/client 经 ctx.api.client 现取(重连换客户端同步链)/apply 恒短路
  (匹配每轮现读 config, 存量重匹配只在全量轮)。
- 新建 core/modules/speed_curve_mod.py(321 行, SpeedCurveModule): handle_speed_limit_curve=
  原 _handle_speed_limit_curve 逐字节(聚合/查档/取最严/手动保护/回读)/start 自注册曲线任务
  (gslc None 不建, interval=gslc.interval or 主 interval)/subscribe 订阅 queue_rebuilt(L2 队列
  重建后按新配置重入队)/_curve_manual_log 节流状态自持(manager 代持删除)/_publish_traffic 改
  ctx.web.set_traffic_view/_record_curve_state 经 ctx.state.data/sections ("global_speed_limit_curve")。
- 新建 core/modules/maintenance_mod.py(339 行, MaintenanceModule): TagsMixin 全部方法公开名迁入
  (add_tags/remove_tags/add_episode_tags/remove_similar_tags/set_category/create_category_if_
  not_exists/add_hr_tag_or_category, _seed_exempt_baseline 随迁)+ handle_maintenance(原 qbmanager
  本体方法, maintenance_tag_mode 判据随迁)+ handle_delete_tags/handle_delete_tags_if_has_no_
  torrents + start 自注册两清理任务/subscribe 订阅 queue_rebuilt/sections 四段认领。
- core/module.py AppContext: 增 task_queue/web/trackers 三挂点(manager 属性对委托; task_queue
  支撑模块任务自注册现取当前队列, web 支撑流量快照服务方法, trackers 是 D3 服务句柄);
  TYPE_CHECKING 注记, 契约层运行时零新依赖。
- core/taskqueue.py: 增 has_named(name)(kind=internal 且无 hash) —— 全局任务自注册的幂等守卫
  单点(队列本身只对 check 任务去重)。
- webui/runtime.py: 增 set_traffic_view(view) 发布口(整体替换引用语义原样)。
- qbmanager.py 1023→1030: 装配清单 P3 段挂入三模块(webui→hr→tracker→speed_curve→maintenance,
  plan §3.3 顺序); run() 删 _create_global_tasks 调用(start_all 已自注册, 入队时点前移到启动,
  队列首个任务线才 drain —— 行为等价); apply_new_config L2 分支保留 _create_global_tasks 调用
  (兼容转发 → queue_rebuilt 相位); _refresh_torrents 全量轮重匹配循环改 events.emit("full_round");
  _create_global_tasks 本体(任务点名)删除, 只剩 emit 兼容转发; task_queue/web 变 ctx 委托属性对;
  _curve_manual_log 代持删除; _handle_maintenance/_handle_maintenance_task_interface 本体删除;
  新增 P3 委托层 14 个单行方法(_match_tracker_conf/_apply_speed_limit/_handle_speed_limit_curve/
  _handle_maintenance*/_add_tags/_remove_tags/_remove_similar_tags/_set_category/_create_category_
  if_not_exists/_add_hr_tag_or_category/_add_episode_tags/_handle_delete_tags*/§7.2 测试兼容)。
- core/mixins/: tags.py/tracker.py/speed_curve.py 删除(474+60+261 行迁出), __init__ 同步。
- 测试: 新建 tests/test_modules_p3.py(11 例, 头部测试计划同步); test_module_host.py 装配断言改
  七模块 + task_queue/web/trackers 同对象断言; test_speed_curve.py import 与 logger 名改
  auto_qb.core.modules.speed_curve_mod、节流白盒断言改指模块实例(host.get("speed_curve").
  _curve_manual_log); test_tracker.py logger 名改 tracker_mod; test_trigger_events.py
  _spy_tags_part 改装模块实例的 add_tags(handle_maintenance 内部直调模块方法, manager 委托已
  不在调用路径上); test_mixins_tags/test_tracker 标题行注记新家。

## 行为变化(仅限计划内, 均评估)

- 全局任务入队时点: run() 内「连接成功+加载规则后」前移到「start_all(连接前)」—— 首个任务线
  才 drain, 对执行时序无可观察影响; delete_tags/speed_limit_curve 均为 L2 级配置, 语义不变。
- 全局任务自注册幂等: 重复注册(重复 start/重复 queue_rebuilt)经 has_named 跳过 —— 原实现
  无此闸(原调用点天然不重复), 对现有路径无差异。
- L2 热重载后全局任务重入队: 原内核点名重建, 现经 queue_rebuilt 相位由模块自建 —— 入队内容
  与 interval 语义逐字节等价; test_web 两处 L2 守阵(mgr._create_global_tasks MagicMock)因 L2
  分支仍经兼容转发而零改动通过。
- 流量快照发布路径改经 ctx.web.set_traffic_view(读侧 self.web.traffic_view/_traffic_view 别名
  同一属性, Web 侧零感知)。
- HrRuntime._anchors 对 manager._hr_anchors 的 getattr 窥探**未**在本段处理(plan §05 目标形态
  「经 ctx 回调」, 归 P5 rules 模块化时收口)。

## 文档与制品

- tasks/26-09-30-backend-kernel-module-refactor.md: P3 → Done + 进度日志 + Summary 更新。
- plans/26-09-30-1819: 拍板记录更新(P0-P3 已实施)。
- activeContext/kernel-module-refactor 新切片(26-09-30-2142)。
