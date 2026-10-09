# WEBUI qB 流量图折线断裂 — 已闭合(取证 + v3 吸收修复)

> 摘要: 用户报 qB 流量图三症状(折线 ~10s 一断 / 更新频率固定不对齐 3s 采样设置 / 1.5s 档只剩端点)。取证报告 [26-10-04-1639](../reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html) 定量闭合根因 A1-A4; 修复未按原三点单独实施, 而由 v3 存储专题 [26-10-04-backend-qb-traffic-storage-v3](../tasks/26-10-04-backend-qb-traffic-storage-v3.md) 以更彻底形式吸收: A1 节拍量化 → 写侧实测 dt 吸收; A2 读侧桶宽 → 按有效 dt 逐记录计算(伪断线根因在格式层面消除); A3 → `_apply_interval` 回写 task.interval 热重载联动; A4 → 前端轮询下界 1500ms; S6 追修 1.5s 小数秒档。档案 2026-10-09 转 Done。
> 最后活动: 2026-10-09 14:54

**Refs:** memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html, memory-bank/tasks/26-10-04-webui-qb-traffic-line-breaks.md, memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md

## 现状

- **已闭合**: 三症状(碎段 / 全孤点 / 刷新频率不对齐)由 v3 读侧结构消除, 本专题无待办。
- 原三点建议(读侧桶宽按量化节奏 / handler 回写 task.interval / 下界 1500)均已由 v3 落地或以更彻底形式替代, 见档案子任务状态表。

## 下一步

- 无。若未来回归, 相关守阵在 `tests/test_traffic_grid.py`(有效 dt 桶宽/覆盖)、`tests/test_traffic_sample.py`(热重载联动)、`tests/test_webui_static_dom_panel.py`(轮询下界常量)。
