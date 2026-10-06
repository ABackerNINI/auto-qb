# 26-10-07-webui-perf-issues-recheck — 两条 WebUI perf issue 重构后复验

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 01:15
**Summary:** 用户指派复验两条 WebUI perf issue（26-09-19-2122 节拍门控双生产者 / 26-09-21-1408 四视图全量重建）——代码经内核化重构后原锚点全失效。逐符号重定位核对: 两条的结构性事实全部原样保留, 均仍成立、Open 维持, 按用户预案出复验报告; issue 1 的实际影响被入池两天后引入的 SSE ver 推送（0c18fcda）改写——SSE 主路径上门控等效失效、请求侧 +48.7ms 伤害基本消失、方案 A 的 -51% 蒸发（消费率=生产率, 每个被消费版本必须建一次）, 轮询兜底路径原动态原样回归; issue 2 前置「P1 拆 create_app」已 Done 转为可认领, 且 SSE 使活跃库下大库有效刷新节奏达 1.5s（分档设计 3s 的 2 倍频）痛点变重非缓解。顺带发现 `runtime.py:499`「发布侧按内容指纹去重」注释与 hr/worker.py 机制张冠李戴（四视图发布无指纹去重）, 按范围守恒未动码未入池, 处置留用户。
**Topics:** webui-perf-issues-recheck
**Refs:** memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html, memory-bank/issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html, memory-bank/issues/26-09-21-1408-perf-webui-shows-view-full-rebuild.html, memory-bank/activeContext/26-10-07-0115-webui-perf-issues-recheck.md, memory-bank/testing/baselines/26-10-07-0115-webui-perf-issues-recheck.md

## 原始请求

用户: 「分析两个issue: 26-09-19-2122-perf-webui-poll-gate-no-net-saving.html, 26-09-21-1408-perf-webui-shows-view-full-rebuild.html，注意代码已经过重构，issue可能已过时，如果问题还在，写一个报告，如果问题不在，更新issue和其状态。」随后指令「提交」。

## 思考过程与决策

- **锚点全失效是本轮起点**: `qbmanager.py` / `mixins/web_view.py` / `web_runtime.py` 已不存在（37d33bc5 webui 包归拢 + 9a428b1a mixin 迁出 + 84473206 别名层删除, 前两者标注零行为变更）。复验方式 = grep 旧符号名（`flush_views` / `pending_ver` / `ensure_state` / `_build_shows_view` …）重定位到 `webui/runtime.py` / `webui/views.py`, 逐条与 issue 论断比对; 不做压测复测（判定「产生 issue 数字的结构是否原样」即可, 数字外推留给认领轮）。
- **issue 1 三个结构性论断全部原样成立**: ①视图版本两个生产者; ②门控只掐主循环; ③`ensure_view` 与 `ensure_state` 清账语义不一致（runtime.py:801 vs 811）。钉门控的 `test_view_rebuild_waits_for_client_consume` 仍在（test_qbmanager.py:898）。
- **SSE 是复验的最大增量发现**: `notify("ver")`（0c18fcda, 2026-09-21 = issue 入池两天后）+ 前端 60ms 去抖即拉（polling.js:50-55）+ 轮询保留兜底。推论: SSE 主路径上门控等效失效（客户端每版必拉, 欠账恒即刻清, 总重建 ≈ 服务端 tick 数 ≈ 无门控基线）; 入池时实测的伤害「一半搬请求路径 + 每次 /api/state +48.7ms」在主路径基本消失（请求到达时视图通常已净）, 只在轮询兜底路径（SSE 断线/不支持/反代缓冲）原样回归; 方案 A 的 -51% 蒸发——消费率=生产率时每个被消费版本都必须恰好建一次, 它只剩「把重建挪离主循环」的线程归属交易价值。修法建议据此重排: 方案 B（口径修正, 范围扩大到 SSE 语义）+ 顺带小修（ensure_view 清账, 且前端已不打 /api/groups, 影响面纯外部脚本）仍值得做, 方案 C 降级。
- **issue 2 三点全在且前置已满足**: 四视图无条件全量重建（runtime.py:783-788）、`_build_shows_view` 全库 by_hash 聚合（views.py:637, 约 141 行）、前端 `decoratedGroups` 全量 map（decorate.js:115）。建议修法的前置「排在 P1 拆 create_app 之后」已 Done（factory.py 薄工厂 + 13 routes 模块）→ 可认领。入池后两件相关事: P1-1 按视图回传把 decoratedGroups 重算触发面缩小到分组页（面上缓解, 单轮成本未变）; SSE 使活跃库下大库有效刷新节奏 = 服务端 sync tick 1.5s（分档设计 3s 的 2 倍频）——痛点变重非缓解, 认领时应一并复测量化（旧数字 396~501ms/轮不能直接外推, P1-1 后单轮成本未测）。
- **范围守恒两处落地**: ①「发布侧按内容指纹去重」注释漂移（runtime.py:499, 指纹去重实为 hr/worker.py 的 HR 事件推送机制）——只记进报告 §06 留决策, 未动码未入池; ②issue 正文的历史证据段（旧代码引用/旧文件清单）不改——证据快照出厂即冻结, 复验增量全部走状态变更日志行 + 定位锚点节（该节设计上就是给重定位用的）+ 报告。
- **issue 状态裁决**: 两条都「仍复现」→ 按用户预案写报告而非关单; 状态 Open 维持, 各补一行复验记录。

## 实现计划

1. 同步仓库（快进 d96169aa→20bd2157）。
2. 读两条 issue 原文, 提取锚点与论断清单。
3. grep 重定位 + 逐条核对（服务端结构 / 测试守阵 / 前端消费动态 / 相关 refactor issue 状态）。
4. 复验报告落 `memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html`（结论速览 + 逐 issue 复验 + 顺带发现 + 建议后续）。
5. 两条 issue 各补复验行（状态变更日志）, issue 2 定位锚点表刷新到新路径; 状态 Open 维持。
6. 收尾: 本档案 + activeContext 切片 + 基线切片 + 认领链双向补齐（报告 doc-refs + 两 issue doc-refs 反向声明）+ `kb.index` + `test.full`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 1 同步 + 读 issue | ✅ 完成 | 20bd2157 |
| 2 锚点重定位与逐条核对 | ✅ 完成 | 见报告 §03-05 |
| 3 复验报告 | ✅ 完成 | 26-10-07-0054 |
| 4 issue 复验行 + 锚点刷新 | ✅ 完成 | 两条均 Open 维持 |
| 5 收尾(档案/切片/基线/认领链/索引/测试) | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-07 00:54-01:15** 复验与产出: 报告 + 两条 issue 复验行/锚点刷新 + 本档案 + 切片 + 认领链反向声明 + `kb.index` 重建。test.full 实测见基线切片 26-10-07-0115（本轮纯 memory-bank 文档, `src/` 零改动, 预期与上一条基线逐位持平）。
