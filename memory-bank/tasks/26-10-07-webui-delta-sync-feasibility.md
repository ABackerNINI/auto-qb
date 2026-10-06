# 26-10-07-webui-delta-sync-feasibility — webui 增量同步(qB rid 式)可行性分析

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 02:04
**Summary:** 用户命题「结合 26-10-07-0054 复验报告, 分析 auto-qb 与 auto-qb.webui 之间能否像 qB 的 /api/v2/sync/maindata?rid 那样用增量更新, 成本与收益, 与当前方案对比, 出可行性报告」。判定**可行且地基厚**: 当前 /api/state 已是 qB rid 的「跳过」半套(runtime.ensure_state rid 命中零回传), 缺「变化回增量」半套; 摄入侧 store.apply_sync 今天就在跑同款协议客户端(含 full_update 兜底/rid 归零/逐种子变化字段集), 而 delta_fields 每拍算出后在视图层门口被 consume_view_changed 塌缩成布尔丢弃 —— 方案落点是把这份信息接住。收益集中在「大库+活跃子集+命令突发」(传输/前端从 O(全库) 降 O(脏行)); 静态库收益趋零(rid 跳过已覆盖)。成本主体与风险同源: 增量聚合正确性(=issue 2 根因栏的「dirty×剧键派生」待查), 以镜子测试(逐轮吃 delta ≡ 全量快照)兜底。与 issue 1 方案 A/B/C 正交; 建议 S1(传输)→S2(组增量)→S3(追剧增量, 与 issue 2 认领并轨)→S4(口径/门控裁决), 拍板点 D1-D5 已列。
**Topics:** webui-delta-sync
**Refs:** memory-bank/reports/26-10-07-0204-report-webui-delta-sync-feasibility.html, memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html, memory-bank/issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html, memory-bank/issues/26-09-21-1408-perf-webui-shows-view-full-rebuild.html, memory-bank/activeContext/26-10-07-0204-webui-delta-sync-feasibility.md, memory-bank/testing/baselines/26-10-07-0204-webui-delta-sync-feasibility.md

## 原始请求

用户: 「结合报告memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html 分析是否可使用qb rid类似的方案，即auto-qb与auto-qb.webui之间也使用增量更新的方式，成本与收益，与当前方案的对比，写一份可行性报告。」

## 思考过程与决策

- **先核对「qb rid」在仓内的对应物, 避免凭印象答**: 当前 `/api/state?rid=` 的版本跳过(runtime.py:811-840)、`group_view_ver` 注释自述「等价 qB 的 rid」(runtime.py:136-138) —— 现方案已是半套; web-runtime.md 里「视图版本门控(等价 qB 的 rid)」是项目自己的口径。
- **决定性事实(本轮取证)**: store._apply 每轮已产出 `delta_fields` {hash: 变化字段集} + added/removed(store.py:185-264), 但 `flush_views` 只消费全局布尔 `consume_view_changed()`(store.py:266-270) —— 逐种子变化信息在生产, 在视图层门口丢弃。增量方案的落点 = 接住它, 不从零造机制。
- **只读取证不改码**: 本轮不动 runtime/views/store/polling 任何一行; 涉及的代码缺陷(issue 1 的 ensure_view 清账、复验 §06 指纹注释漂移)维持原处置, 在报告 §08 S4 里挂为「若立项的 S4 一并做」。
- **收益的诚实口径**: 静态库已被「rid 命中零回传 + _VIEW_QUANTUM 量化」覆盖, 增量对其近乎零增量; 收益主体 = 活跃传输库(脏行 ≈ 传输中种子数)与命令突发。所有「增量后」数字标注为结构性推演非实测, 在账数字(50.8ms 重建/6.3MiB/26.4ms dumps/396-501ms 前端/40 版每 60s)均引用原取证时间。
- **与既有方案的关系裁决**: 方案 A(全惰性)改「谁建」, 增量改「建多少传多少」—— 正交可组合但 A 性价比低(复验已裁定 SSE 下 -51% 蒸发); 增量是唯一同时压低四段(服务端重建/传输/前端赋值/渲染)的选项, 且 S3 与 issue 2 的增量聚合建议共享同一套脏集合推导 —— 建议并轨认领。
- **报告 vs 计划分工**: 本轮只出可行性(证据快照, report 恒 Done); 分步路线 S1-S4 与拍板点 D1-D5 列在报告 §08, 实施另出 plan(不自动转实施)。

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

## 进度日志

- **2026-10-07 02:04** 报告 + 档案 + 切片 + 认领链反向声明 + `kb.index`。test.full 实测见基线切片 26-10-07-0204(本轮纯 memory-bank 文档, `src/` 零改动, 预期与上一条基线持平)。
