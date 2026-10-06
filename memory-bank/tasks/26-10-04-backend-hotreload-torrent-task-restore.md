# 26-10-04-backend-hotreload-torrent-task-restore — 热重载 L2 重建后种子级任务补建 (issue 26-10-01-2147)

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04 02:40
**Topics:** hot-reload
**Summary:** 认领修复 issue 26-10-01-2147(热重载 L2 重建后存量种子种子级任务丢失): TaskQueue.has_task 查重助手 + RulesModule 订阅 full_round 补建(装配序在 tracker 重匹配后) + _create_torrent_tasks 幂等化(immediate 立即到期首轮兑现维护)。红验先行 3 用例, test.full 2422 passed + 3 skipped / 99%。

## 原始请求

用户: 「认领issue: 26-10-01-2147-bug-webui-hotreload-newsite-maintenance.html, 修复」。

背景: 该 issue 2026-10-01 入池(TODO.md L77), 2026-10-04 00:55 复验改判(新机制仍复现且影响面更宽 —— 所有 L2 级热重载后存量种子的种子级任务均丢), 根因已定位, §06 给了候选修法(候选 1 推荐: rules 订阅 full_round 补建), 状态 Open 等修复安排。

## 思考过程与决策

- **缺陷链(复验已定位, 本轮核实锚点未漂移)**: `rebuild_runtime()` 换新 `TaskQueue()` 后只有全局任务(delete_tags* / speed_limit_curve)被各模块自注册重入队; 种子级任务(内置 maintenance + interval 规则任务)唯一创建点 `_create_torrent_tasks` 的唯一触发源是 `torrents_added` 相位, 而 L2 重建轮 `store.reset_runtime()` 保留记录(conf=None)⇒ 下轮全量 `_apply` 对存量记录不走 added 分支 ⇒ 无人重建。旁证: `reset_runtime` 登记的 `external_tag_changes` 唯一消费方是 `handle_maintenance`, 任务不存在则 on_change 模式「首轮全量收敛」(计划 26-09-27-1438 §07)假设不成立。
- **采纳候选 1, 关键设计决策**:
  1. **幂等单点在创建入口**: `_create_torrent_tasks` 以「队列已有该种子的内置 maintenance 任务」为任务面整面判据(与规则任务同源同批创建, 有它 = 任务面已就位), 任何调用方重复调用零副作用(黄金法则 1)。首轮全量轮「full_round 补建(相位序在前)先建、added 管线后到被挡」的双入口互斥全靠这里 —— 比在补建侧单独判断更稳(新增入口天然安全)。
  2. **队列查重助手泛化**: `TaskQueue.has_task(kind, name, hash)` 新增; `has_named`(全局任务)改为其 `hash=""` 特例转发, 判据单点归一。
  3. **「首轮立即兑现维护」不走同步直调**: 候选 1 原文未定实现形态; 同步 `handle_maintenance(force_tags=True)` 直调会阻塞 full_round 相位(逐种子 qB API 批量), 且 added 管线首轮已有同语义动作(重复跑)。改为补建任务 `immediate=True`(next_run=now, 下一 tick 执行): 经任务管线复用 dry_run 口径, on_change 模式消费 `external_tag_changes`(语义与 force_tags 等价), interval 模式提前一轮收敛。这是与建议修法的唯一实现差异, 已回写 issue。
  4. **conf 仍 None 不补建**: 装配序 TrackerModule(:220) 先于 RulesModule(:235), full_round 广播按注册序同步执行 —— 到 rules 时重匹配已完成; 仍 None = 未匹配站点(留待下一全量轮), 不进 `_rules_for_torrent`(其对 conf=None 刻意早崩溃)。emit 契约(订阅者异常中断同相位)保证 tracker 抛异常时补建不执行, 无中间态。
- **测试桩两处踩坑**: ①rebuild_runtime 尾段 `reconnect()` 把 client 置 None, mock connect 不真绑 ⇒ emit full_round 前须 `mgr.client = client` 模拟重连完成; ②默认桩 tracker 无 `@规则集` 引用 ⇒ 规则任务无创建面, 须 `make_manager(..., tracker_rules=["@example_rules"])`; ③桩配置 example_rules 组 3 条规则全默认 interval trigger ⇒ 每种子 3 个 rule 任务是正确行为, 幂等计数断言须按 (kind, name, hash) 限定。

## 实现计划

1. 红验先行: 3 条回归测试坐实红(补建不存在 / 未匹配无防御 / 双入口重复)。
2. `taskqueue.py`: `has_task` + `has_named` 委托。
3. `rules_mod.py`: subscribe 加 full_round; `_on_full_round` 补建(conf 非 None + 回执日志); `_create_torrent_tasks` 幂等 + `immediate` + 返回 bool。
4. 转绿 + 既有测试行为变化同步(订阅者数 / 返回值 / 管线序断言)。
5. 收尾: quick + full 全绿, 回写 issue Done / 主题文档 / 基线切片 / progress / pitfall 家族补段。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 红验先行 3 回归测试(test_modules_p5.py) | ✅ |
| 2 | TaskQueue.has_task + has_named 委托 | ✅ |
| 3 | RulesModule 订阅 full_round 补建 + _create_torrent_tasks 幂等/immediate | ✅ |
| 4 | 既有测试行为变化同步(p3/qbmanager/p5 管线序) | ✅ |
| 5 | 回写 issue Done + 主题文档(main-loop/core-runtime/rules-and-triggers) | ✅ |
| 6 | 基线切片 + progress 迁出 + pitfall 家族补段 | ✅ |

## 进度日志

- **2026-10-04 02:06** 用户指派认领, issue 置 In Progress, `kb.index` 重建。
- **2026-10-04 02:30** 修复落地: `taskqueue.py`(+has_task, has_named 委托) / `rules_mod.py`(subscribe + _on_full_round + _create_torrent_tasks 幂等/immediate)。红验 3 用例坐实红后同用例转绿; 既有测试随行为变化同步 3 处(test_modules_p3 full_round 订阅者 1→2 / test_qbmanager 返回值 None→False / test_modules_p5 管线序 order 首元素 = full_round 补建)。
- **2026-10-04 02:35** 闸门全绿: test.quick 2422 passed + 3 skipped(22.80s); test.full 2422 passed + 3 skipped(29.07s) 覆盖率 99%。issue 置 Done(修法/验证/数字回写 §07 修复后补充), 主题文档回写 3 份(main-loop.md 相位表 / core-runtime.md RulesModule 行 / rules-and-triggers.md 种子级任务创建), 基线切片 26-10-04-0230, progress/implemented-core.md 迁出, pitfall 家族(hot-reload-stale-bindings-derived-views.md)补第三段「换队列 ≠ 任务面自动跟进」。
- 改动随本专题入库。
