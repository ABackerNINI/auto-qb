# WebUI perf issue 复验 — 节拍门控双生产者 + 四视图全量重建

> 摘要: 用户指派复验两条 WebUI perf issue（26-09-19-2122 / 26-09-21-1408），代码经内核化重构后原锚点
> 全失效。逐符号重定位核对结论: 两条结构性事实全部原样保留、均仍成立、Open 维持，按用户预案出复验报告
> [26-10-07-0054](../reports/26-10-07-0054-report-webui-perf-issues-recheck.html)。
> issue 1 关键增量: SSE ver 推送（0c18fcda, 入池两天后）改写消费动态——SSE 主路径上门控等效失效、
> 请求侧 +48.7ms 伤害基本消失、方案 A 的 -51% 蒸发（消费率=生产率, 每个被消费版本必须建一次），
> 轮询兜底路径原动态原样回归；修法重排为方案 B（口径修正）+ 顺带小修（ensure_view 清账）优先。
> issue 2: 三点全在（四视图无条件全量 / `_build_shows_view` 全库聚合 / `decoratedGroups` 全量重算），
> 前置「P1 拆 create_app」已 Done → **可认领**；SSE 使活跃库下大库有效刷新节奏达 1.5s（分档设计 3s
> 的 2 倍频），痛点变重非缓解。顺带发现 runtime.py:499「发布侧按内容指纹去重」注释与 hr/worker.py
> 机制张冠李戴（四视图发布无指纹去重）——未动码未入池，处置留用户。
> 最后活动: 2026-10-07 01:15

**Refs:** memory-bank/tasks/26-10-07-webui-perf-issues-recheck.md, memory-bank/reports/26-10-07-0054-report-webui-perf-issues-recheck.html, memory-bank/testing/baselines/26-10-07-0115-webui-perf-issues-recheck.md

## 未闭环

- 两条 issue 均 Open 未修: issue 1 待做方案 B 口径修正 + ensure_view 清账小修; issue 2 可认领（根因栏
  「dirty 集合 × 剧键派生」正确性论证仍是先决）。
- runtime.py:499 注释漂移的处置待用户定: 一行注释修正, 或并入 issue 1 方案 B。
