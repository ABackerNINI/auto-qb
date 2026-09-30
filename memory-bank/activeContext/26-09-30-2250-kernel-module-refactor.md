# QbManager 内核化重构(P0-P4 完成, P5-P6 待续)

> 摘要: plan 26-09-30-1819 滚动实施 —— P3 小模块先行(细节见基线 26-09-30-2142-p3-small-modules 与任务档案)之后, P4 中坚模块完成: GroupingModule(core/modules/grouping_mod.py, GroupingMixin 387 行迁入 + group_key_of 随迁; 订阅 transitions/torrents_added/removed_scan/post 四刷新相位(§4.2 忠实编码), grouping.enabled 开关与缺文件扫描轮内去重集合归模块自管 —— transitions 每轮无条件 emit、模块入口先清零再判 enabled, 时序与原实现逐字节等价; _refresh_torrents 分组调用点改相位广播)/OpsModule(core/modules/ops_mod.py, OpsMixin 474 行 + CheckingMixin 39 行迁入(决策点 D2), 升 **ctx.ops 服务**, web 命令 recheck/右键跳检/bulk 三处改走 ctx.ops)/rules/checking_meta.py 中性叶(轮询常量+冷却 helper 自 full_checking.py 迁入, ops 对 rules 的 import 收敛为「中性叶 + rules.base」, full_checking 再导出保测试路径); AppContext 增 maintenance/ops 句柄(分组打标经 ctx.maintenance.add_tags); mixins 包再删三文件, manager 增 P4 委托层 15 个单行方法(§7.2)。test.full 1879+3 / 91%。
> 最后活动: 2026-09-30 22:50

## 已完成

- P4(2026-09-30): 新建 core/modules/{grouping_mod,ops_mod}.py(~390/~560 行) + rules/checking_meta.py(~60 行) 与 tests/test_modules_p4.py 守阵 8 例; test_module_host 装配断言改九模块; test_checking/test_actions patch 目标 8 处随迁 ops_mod; test_file_access _bare_grouping 改 GroupingModule fake-ctx 宿主; test_utils/test_grouping 类名与 import 随迁; scripts/qb_capture.py import 随迁。执行偏差两处(计划内细化): ①transitions 无条件 emit(guard 移交模块, 保去重清零时序); ②torrents_added 相位本段只有 grouping 认领, 其余四家 P5 并入。基线切片 testing/baselines/26-09-30-2250-p4-core-modules.md。
- P3(2026-09-30, 见上一切片与本 clone 基线 26-09-30-2142-p3-small-modules.md)。
- P2(2026-09-30, 基线 26-09-30-2048)。
- P1/P0(2026-09-30, 详见切片 26-09-30-2005 / 26-09-30-1912 与任务档案进度日志)。
- 档案单点: tasks/26-09-30-backend-kernel-module-refactor.md(P0-P4 Done, 偏差与取舍都在进度日志)。

## 正在进行

- 无(等下一轮指令; 未提交 —— 等用户说「提交」)。

## 下一步(按计划 P5-P6, 未开工)

- P5 最大一刀: RulesModule(rule_engine 453 行, 执行历史走 ctx.state)+ EventBus 相位表生效(相位顺序断言守阵上线)+ _refresh_torrents 收口(added 逐种子管线「维护/限速/建任务/归组/集数」分派为 torrents_added 相位订阅)+ L2 重建收进 rules.apply(hot-reload W3)+ 级别分派层与三张表退役(W4); rules 委托入口改 ctx.ops; _suppress_events 收进总线 suppress; HrRuntime 对 _hr_anchors 的 getattr 窥探届时清(plan §05)。
- P6 回写(根 README 架构段 / core-domain / conventions/modules 单点)+ 真机四场景走查 + 段认领完备守阵; 别名层处置另立计划(D4)。
