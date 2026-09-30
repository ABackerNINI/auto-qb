# QbManager 内核化重构(P0-P5 完成, P6 待续)

> 摘要: plan 26-09-30-1819 滚动实施 —— P4 中坚模块(细节见基线 26-09-30-2250-p4-core-modules 与任务档案)之后, **P5 最大一刀完成**: RulesModule(core/modules/rules_mod.py ~410 行, RuleEngineMixin 其余部分整体迁入)—— 事件分派改 events_removed/events_added 相位认领、建任务改 torrents_added 相位认领(与 tracker 限速/maintenance 维护+集数/grouping 归组合流, 四家按装配序)、**L2 重建收进 rules.apply**(W3: 判据段 = rules_config/interval/delete_tags*/global_speed_limit_curve + trackers 绑定三元组, 整段相等短路); _refresh_torrents 收口为「同步 + 相位广播」(§4.2 相位表生效); _suppress_events 收口进总线 suppress(take_suppressed 窗口协议: 只覆盖两个事件相位, 全量轮/逐种子管线照常 —— P0 骨架「全轮抑制」设想与 §7.1 语义等价不符已修正); **级别分派层与 impact 三张手写表退役**(W4: impact.py 96→52 行 diff+R 闸, apply_new_config 只剩 R 闸+换对象+host.apply_all+qbittorrent 段变自判重连, 回执 levels→actions); **内核零 rules import**(AST 守阵); _hr_anchors 迁 HrRuntime(plan §05); rules 动作三处改 ctx.ops; mixins/rule_engine.py 删除。计划外根修: helpers.FakeConfig 类属性共享可变段跨测试泄漏(xdist 分布偶发实报)→ 每实例深拷贝, 坑档 fake-config-shared-mutables.md 新立。W3 实测: 5000 种子短路 0.01ms vs 重建 0.7ms。test.full 1876+3 / 91%。
> 最后活动: 2026-10-01 02:45

## 已完成

- P5(2026-10-01): 新建 core/modules/rules_mod.py(~410 行) + tests/test_modules_p5.py 守阵 9 例 + 坑档 pitfalls/testing/fake-config-shared-mutables.md; test_impact 17→8 收缩改写、test_hr_config 6 分级用例合并为 2、test_config_schema hr_check 级别覆盖守阵退役、test_web 两热重载守阵迁移改写(levels→actions, mock 段钉 rules 六判据段)、test_module_host 装配断言十模块、test_modules_p4 订阅计数 1→4; config/impact.py 三表退役(96→52) + writer R 闸过滤 + schema 路由派生认领。执行偏差一处(文档化): §4.2 认领列与 §3.3 装配序矛盾, 逐种子管线按装配序实现(限速→维护+集数→归组→建任务), 相位间次序精确保留, 守阵锁定。基线切片 testing/baselines/26-10-01-0245-p5-rules-pipeline.md。

## 下一步

- P6 收尾: 段认领完备守阵(每段至少一个模块认领 + 未认领段 WARN + 全量兜底); 文档回写(根 README 架构段 / memory-bank core-domain / conventions/modules 单点); test.full 基线; dry-run 真机四场景走查(借 1751 §07: 改 main_tick 零动作 / 改 web.token 不重启 / 热接入首个 HR 站点从无到有 / 改一条规则仅队列重建且内存态保留); 别名层处置另立计划(D4)。
