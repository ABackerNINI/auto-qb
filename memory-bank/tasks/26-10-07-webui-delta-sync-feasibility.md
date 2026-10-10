# 26-10-07-webui-delta-sync-feasibility — webui 增量同步(qB rid 式)可行性分析

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07
**Summary:** 用户命题「结合 26-10-07-0054 复验报告, 分析 auto-qb 与 auto-qb.webui 之间能否像 qB 的 /api/v2/sync/maindata?rid 那样用增量更新, 成本与收益, 与当前方案对比, 出可行性报告」。判定**可行且地基厚**: 当前 /api/state 已是 qB rid 的「跳过」半套(runtime.ensure_state rid 命中零回传), 缺「变化回增量」半套; 摄入侧 store.apply_sync 今天就在跑同款协议客户端(含 full_update 兜底/rid 归零/逐种子变化字段集), 而 delta_fields 每拍算出后在视图层门口被 consume_view_changed 塌缩成布尔丢弃 —— 方案落点是把这份信息接住。收益集中在「大库+活跃子集+命令突发」(传输/前端从 O(全库) 降 O(脏行)); 静态库收益趋零(rid 跳过已覆盖)。成本主体与风险同源: 增量聚合正确性(=issue 2 根因栏的「dirty×剧键派生」待查), 以镜子测试(逐轮吃 delta ≡ 全量快照)兜底。与 issue 1 方案 A/B/C 正交; 建议 S1(传输)→S2(组增量)→S3(追剧增量, 与 issue 2 认领并轨)→S4(口径/门控裁决), 拍板点 D1-D5 已列。**计划轮(04:38)**: qB rid 源码级调研(双指针 ack 协议/字段级部分字典/避坑 5 条)证实报告 4 处与 qB 实现出入(deque 窗口只存键系自创改进而非「qB 同款」), 实施计划 [26-10-07-0414](../plans/26-10-07-0414-plan-webui-delta-sync.html) 已出: S0-S10 四里程碑, 拍板点 P-01..P-05 全带推荐案, 设计规则 R1-R12, 每步独立提交/回滚; 仓库对表新发现两缺口(store 不持久化 added/removed、剧侧无 member_to_key 等价映射)落为显式步骤 S1/S8。**实施轮(S0-S10 全部落地)**: 分步派工 15 个提交(3a6e81f7..1ad13659), 终态 test.full **2745+4 / 99%** 见 [S10 基线切片](../testing/baselines/26-10-07-1336-webui-delta-sync-s10-baseline.md)(含 e2e 分档复测 before/after 与 6 条存量 e2e 失败根因); 机制单点回写 web-runtime.md「rid 式增量同步」段; P-03 裁决 = pending_ver 门控保留。
**Topics:** webui-delta-sync
**Refs:** memory-bank/reports/26-10-07-0204-report-webui-delta-sync-feasibility.html, memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html, memory-bank/issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html, memory-bank/issues/26-09-21-1408-perf-webui-shows-view-full-rebuild.html, memory-bank/testing/baselines/26-10-07-0204-webui-delta-sync-feasibility.md, memory-bank/testing/baselines/26-10-07-0438-webui-delta-sync-plan.md, memory-bank/testing/baselines/26-10-07-1336-webui-delta-sync-s10-baseline.md, memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html, memory-bank/pitfalls/testing/stub-bypass-apply.md, memory-bank/pitfalls/backend/last-round-snapshot-stale.md, memory-bank/tasks/26-10-08-webui-perf-issues-closing.md

## 原始请求

用户: 「结合报告memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html 分析是否可使用qb rid类似的方案，即auto-qb与auto-qb.webui之间也使用增量更新的方式，成本与收益，与当前方案的对比，写一份可行性报告。」

## 思考过程与决策

- **先核对「qb rid」在仓内的对应物, 避免凭印象答**: 当前 `/api/state?rid=` 的版本跳过(runtime.py:811-840)、`group_view_ver` 注释自述「等价 qB 的 rid」(runtime.py:136-138) —— 现方案已是半套; web-runtime.md 里「视图版本门控(等价 qB 的 rid)」是项目自己的口径。
- **决定性事实(本轮取证)**: store._apply 每轮已产出 `delta_fields` {hash: 变化字段集} + added/removed(store.py:185-264), 但 `flush_views` 只消费全局布尔 `consume_view_changed()`(store.py:266-270) —— 逐种子变化信息在生产, 在视图层门口丢弃。增量方案的落点 = 接住它, 不从零造机制。
- **只读取证不改码**: 本轮不动 runtime/views/store/polling 任何一行; 涉及的代码缺陷(issue 1 的 ensure_view 清账、复验 §06 指纹注释漂移)维持原处置, 在报告 §08 S4 里挂为「若立项的 S4 一并做」。
- **收益的诚实口径**: 静态库已被「rid 命中零回传 + _VIEW_QUANTUM 量化」覆盖, 增量对其近乎零增量; 收益主体 = 活跃传输库(脏行 ≈ 传输中种子数)与命令突发。所有「增量后」数字标注为结构性推演非实测, 在账数字(50.8ms 重建/6.3MiB/26.4ms dumps/396-501ms 前端/40 版每 60s)均引用原取证时间。
- **与既有方案的关系裁决**: 方案 A(全惰性)改「谁建」, 增量改「建多少传多少」—— 正交可组合但 A 性价比低(复验已裁定 SSE 下 -51% 蒸发); 增量是唯一同时压低四段(服务端重建/传输/前端赋值/渲染)的选项, 且 S3 与 issue 2 的增量聚合建议共享同一套脏集合推导 —— 建议并轨认领。
- **报告 vs 计划分工**: 本轮只出可行性(证据快照, report 恒 Done); 分步路线 S1-S4 与拍板点 D1-D5 列在报告 §08, 实施另出 plan(不自动转实施)。
- **计划轮(04:38)口径修正**: qB 源码级调研证实 qB 是「快照+存值缓冲的双指针 ack 协议」, 报告的「deque 窗口只存键」是自创改进而非 qB 同款 —— 计划通篇按此改口径并立设计规则(禁写「qB 同款」); 报告「单调递增」与 qB 回绕机制不符, 计划沿用本项目单调 ver 不模仿回绕。
- **计划轮新发现两缺口落为显式步骤**: store 不持久化 added/removed(flush_views 拿不到)⇒ S1; 剧侧无 member_to_key 等价映射 ⇒ S8。
- **计划轮工作方式**: 四个串行子智能体(调研→对表→内容稿→渲染), 中间笔记落仓库外 `_planwork-webui-delta/` 防长会话丢进度; 每步独立提交/回滚, 为后续分步派工实施的样板。

## 实现计划

1. 开工同步(快进 9bf42e03→b736f1a3)。
2. 读复验报告 + doc-forms 协议 + web-runtime.md 路由文档。
3. 逐文件取证: runtime.py(视图发布/门控/SSE)、views.py(四视图构建/VIEW_ARRAYS)、torrents/view.py(_VIEW_FIELDS/量化)、store.py(apply_sync/_apply/delta_fields)、routes/state.py、polling.js/decorate.js/tpl(groups :key)。
4. 读两条 issue 原文取在账数字与方案 A/B/C。
5. 写可行性报告 → `memory-bank/reports/26-10-07-0204-report-webui-delta-sync-feasibility.html`(判定/现状解剖/qB 语义与摄入侧事实/方案映射/收益/成本风险/对比/路线与拍板点/结论)。
6. 收尾: 本档案 + activeContext 切片 + 认领链反向声明(复验报告 doc-refs、两 issue doc-refs)+ `kb.index` + `test.full` 基线切片。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 1 同步 + 路由阅读 | ✅ 完成 | b736f1a3 |
| 2 代码取证(七文件) | ✅ 完成 | 锚点见报告 §02-04 |
| 3 issue 原文数字提取 | ✅ 完成 | issue 1 §02②③④ / issue 2 §02 |
| 4 可行性报告 | ✅ 完成 | 26-10-07-0204 |
| 5 收尾(档案/切片/认领链/索引/基线) | ✅ 完成 | 数字见进度日志 |
| 6 计划轮 P1: qB rid 源码级调研 | ✅ 完成 | 避坑 5 条 + 报告出入 4 处; 笔记在仓库外 |
| 7 计划轮 P2: 报告+仓库对表 | ✅ 完成 | 触点带行号(f4430f32); 新缺口 2 处; 漂移 1 处已修 |
| 8 计划轮 P3: 计划内容稿 | ✅ 完成 | S0-S10 / P-01..P-05 / R1-R12, 自查五项全过 |
| 9 计划轮 P4: 渲染+认领链+索引 | ✅ 完成 | 26-10-07-0414; kb.check 全绿 |
| 10 实施轮 S0-S5(协议/前端/镜子) | ✅ 完成 | 3a6e81f7(S0 基线)→f3c0b5d6(S1)→f8cf9049(S2)→124e0c4f(S2补)→17bcf911(S3)→11a81c0f(S4)→a64a2c72(S5a)→effdc31a(S5b); 基线切片 0514/0805 |
| 11 实施轮 S6-S9(重聚合/show 解锁) | ✅ 完成 | aa4d855e(S6)→582d1acd(S7)→2ca5491f(S6/S7间桩保真修复)→c8846b4f(S8)→6f5f345f(S9a)→0b071760(S9)→1ad13659(S6补); 基线切片 1213 |
| 12 S10 收尾(裁决/回写/复测/归档) | ✅ 完成 | P-03 门控保留; web-runtime.md 机制段; e2e 分档复测 + 6 条存量失败根因; S10 基线切片 1336 |

## 进度日志

- **2026-10-07 02:04** 报告 + 档案 + 切片 + 认领链反向声明 + `kb.index`。test.full 实测见基线切片 26-10-07-0204(本轮纯 memory-bank 文档, `src/` 零改动, 预期与上一条基线持平)。
- **2026-10-07 04:38** 实施计划轮(四个串行子智能体): P1 qB 源码调研 → P2 报告+仓库对表 → P3 内容稿 → P4 渲染 [26-10-07-0414](../plans/26-10-07-0414-plan-webui-delta-sync.html) + 认领链双向闭环(web-runtime.md 按协议移出 doc-refs)+ `kb.index`。`kb.check` 全绿; test.full **2689 passed + 4 skipped / 99%**(41.75s) 见基线切片 26-10-07-0438(passed +3 来自区间已入库提交的 3 个新增测试函数, 本轮 `src/` 零改动)。**未实施, 计划 Open 待拍板**。
- **2026-10-07 13:36** S10 收尾步(实施 S0-S9 已由分步派工各自提交入库, 见子任务表 10-11): ①P-03 裁决落地 —— pending_ver 门控**保留**(增量下成本=一次键集追加, 保留无害且保守; 纯冗余实测确认后另立小步移除), 裁决口径写进 runtime.py 三处注释; ②flush_views/_publish_locked docstring 口径回写(时间线只存键/值回放现取/四视图同轮发布/单一写线程不破)+ HR 段「按内容指纹去重」错误注释修正(报告 26-10-07-0054 §06); ③web-runtime.md 增补「rid 式增量同步」机制单点段 + 涉改段落重锚; ④e2e 分档复测归档(桩口径): delta 载荷 1,809 B ≈ 同数据全量回包 1/4800(不随档位增长)、HTTP delta 轮 ~4ms / 零回传 ~2ms(全量 93.8ms @3000)、前端 delta 轮 29-43ms 与档位无关(全量整表替换 562-816ms @3000); dev.e2e **86 passed / 10 skipped / 6 failed** —— 6 条为 S5b-S9 存量(S4 后 e2e 未重跑, S10 首次暴露; 根因 A: 2ca5491f 桩走真 _apply 后 FakeTorrent.to_dict 未跳过 hr_link → 详情端点恒 500 ×4 条; 根因 B: S7 WeakMap 记忆化令 applyOptimistic 原地变更不再传导 decoratedGroups ×2 条), 按范围守恒未改、数字与根因记入基线切片; ⑤test.full **2745 passed + 4 skipped / 99%**(35.4s) 终态基线; ⑥新坑两条入档(testing/stub-bypass-apply + backend/last-round-snapshot-stale)+ kb.index。详见基线切片 [26-10-07-1336](../testing/baselines/26-10-07-1336-webui-delta-sync-s10-baseline.md)。
