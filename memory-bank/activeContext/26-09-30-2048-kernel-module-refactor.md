# QbManager 内核化重构(P0-P2 完成, P3-P6 待续)

> 摘要: plan 26-09-30-1819 滚动实施 —— P0 内核地基与 P1 基建模块化(见上一切片)之后, P2 门面转正完成: 新增 webui/module.py WebUIModule(106 行) + hr/module.py HrModule(41 行) 契约封装(门面对象经 manager 现取, 测试替换自动跟随), 装配清单挂入四模块, run() web 启动块/hr.start/finally 手工停止序列退役改 host.start_all/stop_all, _apply_web_config 并入 webui.apply(有差异即置脏 + 仅监听身份变化才重启), 主循环 self.web.* 五语义调用改 loop hooks(flush_truths 次序语义留内核), store.hr_link 注入移进装配, start_web_server 不再写 manager._web_token。test.full 1860+3 / 91%。
> 最后活动: 2026-09-30 20:48

## 已完成

- P2(2026-09-30): 新建 tests/test_facade_modules.py 守阵 9 例(run 接线守阵「主循环不再点名 self.web.* 五调用」在内); test_module_host 装配断言改 ["logging","notify","webui","hr"]; test_web 两守阵改经模块 apply 驱动 + MagicMock 配置补钉 web 段。行为变化仅三处且计划内(advance_error_reasons 移至任务线收尾 / token 同步扩至每次热重载 / 零差异保存不再置脏)。基线切片 testing/baselines/26-09-30-2048-p2-facade-modules.md。
- P1(2026-09-30, 详见上一切片 26-09-30-2005)。
- P0(2026-09-30, 详见切片 26-09-30-1912 与任务档案进度日志)。
- 档案单点: tasks/26-09-30-backend-kernel-module-refactor.md(P0-P2 Done, 执行偏差与 P3 注记都在进度日志)。

## 正在进行

- 无(等下一轮指令; 未提交 —— 等用户说「提交」)。

## 下一步(按计划 P3-P6, 未开工)

- P3 小模块: TrackerModule(_match_tracker_conf 升 ctx.trackers 服务, D3)/SpeedCurveModule(曲线任务自注册, _traffic_view 改 ctx.web 服务方法)/MaintenanceModule(tags mixin + _handle_maintenance + 集数标签一起搬); _create_global_tasks 从内核删除。
- P4 中坚: GroupingModule(387 行, 订阅四相位)/OpsModule(474+39 行, ctx.ops, rules 反向 import 单向化)。
- P5 最大一刀: RulesModule + EventBus 相位表生效 + _refresh_torrents 收口 + L2 重建收进 rules.apply + 级别分派层退役。
- P6 回写 + 真机四场景走查 + 段认领守阵; 别名层处置另立计划(D4)。
