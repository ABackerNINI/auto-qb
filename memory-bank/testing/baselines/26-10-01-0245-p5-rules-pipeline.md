# 基线 · 1876 passed + 3 skipped / 91% —— 内核化重构 P5 (rules 模块化 + 刷新管线收口)

> 摘要: plan plans/26-09-30-1819 P5 全量实施 —— RuleEngineMixin 其余部分迁 **RulesModule**
> (core/modules/rules_mod.py): 事件分派改 events_removed / events_added 相位认领, 「建任务」
> 一步改 torrents_added 相位认领(与 tracker 限速 / maintenance 维护+集数 / grouping 归组合流,
> 四家按装配序), **L2 重建收进 rules.apply**(hot-reload W3: _rebuild_needed 判据段 =
> rules_config/interval/delete_tags*/global_speed_limit_curve + trackers 绑定三元组,
> 整段相等短路); **_refresh_torrents 收口为「同步 + 相位广播」**(§4.2 相位表生效, 内核只报
> 时机); _suppress_events 收口进总线 suppress(take_suppressed 窗口协议: L2 置位 → 轮首
> 读走 → events_removed 前重挂 → events_added 后关闭, 只覆盖两个事件相位, 全量轮/逐种子
> 管线照常 —— P0 骨架的「全轮抑制」设想与 §7.1「语义等价」不符, 已修正); **级别分派层与
> impact 三张手写表退役**(W4): impact.py 96→52 行(diff + RESTART_SECTIONS R 闸),
> apply_new_config 只剩 R 闸 + 换对象 + host.apply_all + qbittorrent 段变自判重连,
> 回执 levels→actions; /api/config/schema 的 levels 改模块 sections() 派生; rules 动作
> 三处改 ctx.ops; **内核零 rules import**(AST 守阵); _hr_anchors 迁 HrRuntime(plan §05)。
> 守阵: tests/test_modules_p5.py 9 例(新建: sections 认领 / 内核零 rules import AST /
> 相位订阅面+装配序 / 刷新相位顺序==§4.2 / 逐种子管线次序 / 抑制窗口只覆盖事件相位 /
> rules.apply 短路+段变重建 / 重建内存态保留 / 5000 种子短路 vs 重建耗时); test_impact
> 17→8 收缩改写(diff+R 闸口径); test_hr_config 6 分级用例合并为 2; test_config_schema
> hr_check 级别覆盖守阵退役(表已删); test_web 两热重载守阵迁移改写(levels→actions 回执,
> L2 断言走回执+总线, mock 替身钉 rules 六判据段); test_module_host 装配断言十模块;
> test_modules_p4 torrents_added 订阅计数 1→4。
> 计划外根修(验收闸门阻塞): helpers.FakeConfig 类属性共享可变段 + 测试原地改 → 跨测试
> 泄漏(xdist 分布偶发, test_build_group_view→test_refresh_removed_grouping_disabled 实报)
> → __init__ 每实例深拷贝; 坑档 pitfalls/testing/fake-config-shared-mutables.md 新立。
> 同轮另修既有 flaky(闸门阻塞): test_hr_report 断言裸 tid 撞 pytest 临时目录计数编号(pytest-1033 含
> "103")假红 → 断言改用默认种子名特征串 "EXAMPLE 103"。
> 基线时间: 2026-10-01 02:55, develop @ cc11e6d6(合并远端「打开目标文件夹」修复后复核) + 本轮 P5 改动。

TOTAL **1884 passed + 3 skipped / 91%**(13296 语句 / 1060 未覆盖 / 4404 分支 / 437 partial,
test.full 31.8s, rc=0; 合流前 @73cdc793 本段实测 1876+3/91%, 差值 +8 来自远端 cc11e6d6 新守阵) —— 较上基线 26-09-30-2250(1879 passed + 3 skipped / 91%)净减 3:
test_impact 17→8(-9)、test_hr_config impact 用例 6→2(-4)、test_config_schema -1;
新增 test_modules_p5 +9;其余为 test_web/test_core_modules/test_modules_p4 断言改写。

## 实测数字(W3 验收: 5000 种子模拟)

- rules.apply **整段短路: 0.01ms**(3 轮中位; 判据段整段相等直接返回, 与种子量无关);
- **L2 重建: 0.7ms**(3 轮中位; 队列重建 + 5000 条记录 conf 置空 + 规则重载 + 相位广播,
  纯内存不含 API 调用)。
- 结论: 热重载保存中「零规则相关变更」的模块广播成本趋近于零; 规则变更的一次性重建
  成本可忽略 —— W3「短路/重建耗时实测入档」验收达成。

## 行为变化(仅限计划内)

1. 热重载回执从 levels 换 actions(各模块 ApplyResult 汇总); /api/config/put 的 changes
   从 [{path, level}] 改路径串 —— 前端仅消费计数与 restart_required, 无适配需求。
2. 零差异保存不再产生任何模块动作(此前 L0 也过级别表); 未认领段(新配置键)不再有
   「默认 L2 全量重建」兜底 —— P6 段认领完备守阵上线(未认领段 WARN + 全量兜底)。
3. L2 重建尾段的重连复用内核 reconnect()(client 换新 + rid 失效), 与原三行序列等价;
   L1 的 qb 重连改为 qbittorrent 段变内核自判(不经级别表)。
4. 逐种子管线相位内次序 = 装配序: 限速→维护+集数→归组→建任务(plan §4.2 认领列与
   §3.3 装配序矛盾, 按装配序实现; 相位内各步数据互不依赖, 相位间次序精确保留;
   守阵 test_torrents_added_pipeline_order 锁定)。

## 本段改动面

- 新建 core/modules/rules_mod.py(~410 行): 规则加载/_rules_for_torrent/_create_rule_task/
  _handle_rule/_dispatch_events/_apply_event_rule/_handle_event_rule/_resolve_refs 原样迁入
  (self.* 改 ctx/manager 现取) + phases 订阅(events_removed/events_added/torrents_added) +
  apply(W3)/rebuild_runtime; Rule/RuleContext 宿主面仍为 QbManager。
- 新建 tests/test_modules_p5.py(9 例)与 memory-bank/pitfalls/testing/
  fake-config-shared-mutables.md(坑档)。
- 修改: core/module.py(EventBus.take_suppressed + 窗口协议 docstring)/core/qbmanager.py
  (1023→1084, 委托层净增)/core/modules/{tracker,maintenance}_mod.py(补 torrents_added 订阅)/
  core/mixins/(删 rule_engine.py, 只剩 webui 两 mixin)/hr/runtime.py(_anchors 实现迁入)/
  config/impact.py(三表退役)/config/writer.py(R 闸过滤)/webui/server/routes/config.py
  (schema 派生认领 + PUT 回执)/rules/actions/{full_checking,skip_checking,checking}.py
  (改 ctx.ops)。
