# 3144 — WEBUI 流量图限速线按当时值分段(plan 26-10-12-0535 W1-W3 实施)

**Refs:** memory-bank/tasks/26-10-12-webui-traffic-limit-history.md,memory-bank/plans/26-10-12-0535-plan-webui-traffic-limit-history.html

> 摘要: W1 后端(`core/traffic_limits.py` 记录器+读侧 / `traffic_sample_mod` 接线 / `traffic_qb.py` payload 附 limits)+ W2 前端(分段绘制 + 悬停读数 + node 电池)+ W3 收尾(文档回写)。
> 基线时间: 2026-10-12 08:15

计划: memory-bank/plans/26-10-12-0535-plan-webui-traffic-limit-history.html
上一基线: memory-bank/testing/baselines/26-10-12-0619-webui-traffic-limit-history-plan.md

## 本波改动面
- `core/traffic_limits.py` 新增: SpeedLimitRecorder(变化才记 / 00:00 硬切 + 基线 carry / 重启去重 / OSError 降级不上抛 / 病态翻转常量护栏) + LimitsCache(mtime_ns+size 键控) + limits_events_for_window(合成首事件 / 同值去重 / 多看一天窥前文件 carry) + parse_limits_day_text(撕裂尾豁免)。
- `core/modules/traffic_sample_mod.py`: 构造器挂 SpeedLimitRecorder; `_sample_global` 顺带 observe(qB 在线轮, dry_run persistence_on=False 同门)。
- `webui/server/traffic_qb.py`: 三 payload 经 `_respond` 统一附 `limits`; 空态 `_empty`/组空态分支同源; last-good 快照含 limits。
- `shared/qb_traffic_chart.js`: `_qbLimitSegs`/`_qbLimitAt` 纯函数; `_qbDrawLimits` 分段化(u._qbLimits 暂存, 逐段可见性 0<v<ymax, 末段到图右沿); setData 快路同步换 limits; 悬停「当时限速」行两支; 统计栏悬浮说明 D4 文案。
- `shared/tpl/drawer.html`: tooltip 正常/缺口两支各加 `h-limit` 行。
- `tests/test_traffic_limits.py` 新增 12 条; `tests/test_web_traffic_qb.py` `_v4_opens` 排除 `limits/`; `tests/test_webui_static_dom_panel.py` 纵轴/注解守阵更新(分段锚 + 旧回潮反向断言 + node 电池 12 项)。
- 文档回写: `conventions/webui.md`(注解层限速线条目) / `modules/core-runtime.md`(traffic_sample_mod 职责)。

## 验收数字
- `test.full`: **3144 passed + 3 skipped** / 42.6s / 覆盖率 `TOTAL 16708 161 5688 140 99%`(与上基线 3132 相比 +12 = 本波新测试逐条对账闭合; skip 4→3 同源环境变化已在规划轮基线核对)。
- 全量 e2e: **166 passed + 0 failed + 10 skipped**(282.9s; 前两轮 36/14 条失败全为连接拒绝 —— 另一 clone 的会话并行跑 e2e 同抢 8137 且收尾兜底互杀桩, 非代码缺陷; 端口空闲后全绿)。
- 红验: 读侧合成首事件判据短路注入 → 2 红(还原即绿); 前端分段回潮为单值注入 → 守阵红(还原即绿)。
