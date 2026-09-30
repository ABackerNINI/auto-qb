# QbManager 内核化重构(P0-P3 完成, P4-P6 待续)

> 摘要: plan 26-09-30-1819 滚动实施 —— P2 门面转正(细节见基线 26-09-30-2048-p2-facade-modules 与任务档案)之后, P3 小模块先行完成: 三 mixin 迁出为功能模块 —— TrackerModule(core/modules/tracker_mod.py, _match_tracker_conf 升 ctx.trackers 服务(决策点 D3); 全量轮重匹配改订阅 full_round 相位, _refresh_torrents 内核只 emit)/SpeedCurveModule(speed_curve_mod.py, 曲线任务 start 自注册 + queue_rebuilt 相位重注册; _traffic_view 跨层直写改 ctx.web.set_traffic_view 服务方法; _curve_manual_log 节流状态收进模块)/MaintenanceModule(maintenance_mod.py, TagsMixin 全部 + _handle_maintenance + delete_tags 两全局任务 + 集数标签一起搬, 全局任务自注册); 内核 _create_global_tasks 任务点名退役(只剩 queue_rebuilt 相位广播兼容转发, run() 启动路径改 start_all 承担); mixins 包删三文件, manager 旧名方法留单行委托(§7.2)。契约层: AppContext 增 task_queue/web/trackers, TaskQueue 增 has_named 幂等守卫, WebUIRuntime 增 set_traffic_view。test.full 1871+3 / 91%。
> 最后活动: 2026-09-30 21:42

## 已完成

- P3(2026-09-30): 新建 core/modules/{tracker_mod,speed_curve_mod,maintenance_mod}.py(93/321/339 行)与 tests/test_modules_p3.py 守阵 11 例; test_module_host 装配断言改七模块 + 三新挂点同对象; test_speed_curve/test_tracker import 与 logger 名随迁, test_trigger_events spy 改装模块实例。全局任务入队时点自「连接成功后」前移到 start_all(队列首个任务线才 drain, 行为等价); L2 重入队经 queue_rebuilt 相位(test_web L2 守阵零改动通过)。基线切片 testing/baselines/26-09-30-2142-p3-small-modules.md。
- P2(2026-09-30, 见上一切片内容与本 clone 基线 26-09-30-2048-p2-facade-modules.md)。
- P1(2026-09-30, 详见切片 26-09-30-2005)。
- P0(2026-09-30, 详见切片 26-09-30-1912 与任务档案进度日志)。
- 档案单点: tasks/26-09-30-backend-kernel-module-refactor.md(P0-P3 Done, 执行偏差与 queue_rebuilt 取舍都在进度日志)。

## 正在进行

- 无(等下一轮指令; 未提交 —— 等用户说「提交」)。

## 下一步(按计划 P4-P6, 未开工)

- P4 中坚: GroupingModule(387 行搬家, 订阅 transitions/torrents_added/removed_scan/post 四相位; 其对 _add_tags 的一处调用经 manager 委托保持, 届时改 ctx 口)/OpsModule(474+39 行, ctx.ops, rules 反向 import 单向化; web commands 的 ops 调用改走 ctx.ops)。
- P5 最大一刀: RulesModule + EventBus 相位表生效(相位顺序断言守阵上线)+ _refresh_torrents 收口(added 逐种子管线分派为模块订阅)+ L2 重建收进 rules.apply + 级别分派层退役; HrRuntime 对 _hr_anchors 的 getattr 窥探届时清(plan §05)。
- P6 回写 + 真机四场景走查 + 段认领守阵; 别名层处置另立计划(D4)。
