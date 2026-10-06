# WebUI 增量同步(qB rid 式)可行性分析

> 摘要: 用户命题「结合 26-10-07-0054 复验报告, 分析 auto-qb ↔ auto-qb.webui 能否像 qB
> /sync/maindata?rid 那样用增量更新, 成本收益与当前方案对比, 出可行性报告」。判定
> **可行且地基厚**: 当前 /api/state 已是 qB rid 的「跳过」半套(rid 命中零回传), 缺「变化
> 回增量」半套; 摄入侧 store.apply_sync 今天就在跑同款协议客户端(full_update 兜底/rid 归零/
> 逐种子变化字段集), 而 delta_fields 每拍算出后在视图层门口被 consume_view_changed 塌缩成
> 布尔丢弃 —— 方案落点是把这份信息接住。报告
> [26-10-07-0204](../reports/26-10-07-0204-report-webui-delta-sync-feasibility.html):
> 收益集中在「大库+活跃子集+命令突发」(四段成本从 O(全库) 降 O(脏行)); 静态库收益趋零
> (rid 跳过已覆盖)。成本主体与风险同源 = 增量聚合正确性(恰是 issue 2 根因栏「dirty×剧键
> 派生」待查), 以镜子测试(逐轮吃 delta ≡ 全量快照)兜底。与 issue 1 方案 A/B/C 正交; 路线
> S1 传输→S2 组增量→S3 追剧增量(建议与 issue 2 认领并轨)→S4 口径/门控裁决, 拍板点 D1-D5。
> 最后活动: 2026-10-07 02:04

**Refs:** memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md, memory-bank/reports/26-10-07-0204-report-webui-delta-sync-feasibility.html, memory-bank/testing/baselines/26-10-07-0204-webui-delta-sync-feasibility.md

## 未闭环

- 本轮只读取证零改码; 报告 §08 为「若立项」的路线与拍板点, **未出实施计划**(等用户拍板)。
- 若立项: 从 S1 出 plan; 若不立项: issue 2 认领时把报告 §06 正确性边界清单作为其增量聚合
  论证的输入清单, 两档案互为引用。
