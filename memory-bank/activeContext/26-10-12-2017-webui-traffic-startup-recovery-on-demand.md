# webui-traffic-startup-recovery-on-demand — 流量启动恢复改为按需读取口径

> 摘要: 依据报告 [26-10-12-1923](../reports/26-10-12-1923-report-webui-startup-latency.html)(启动死区取证: 恢复静默全量重读 `qb-traffic-v4` 历史, 死区 11.16s / 约 +1.5~2.0s/天 无界增长)与用户三条定调(**按需读取是既定契约** / `rollup_window: 1000000D` 永久保留是有意设定 / 保持同步恢复), 产出计划 [26-10-12-2010](../plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html)(Open, 待拍板): 恢复读集下界 `now - rollup_window` → **agg 水位所在日**(常态 1 个、跨日界至多 2 个天文件), `agg.dat` 仍按系列照读, 保留口径与图表读侧零改动; B2/B3/A1/C1 出局或另题。报告同轮追加 §10 说明「恢复为什么必须读 raw」。**计划待拍板, 代码零改动。**

**创建:** 2026-10-12 20:17
**最后活动:** 2026-10-12 20:31
**主题:** webui-traffic-startup-recovery-on-demand
**摘要:** 计划 [26-10-12-2010](../plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html) 已定稿待拍板: 靶点 = `_recover_series` 读集下界由配置窗口(`now - rollup_window`)改为 **agg 水位所在日**(`v4_day_epoch(wm_hour)`), 已封口小时不读不重算(判据代码已存在), agg 缺失时退回现口径全量兜底 + 日志; 附 B4 埋点(恢复起止 INFO + 系列数/天文件数/小时数/耗时计数, 把「读集有界」变成可机检事实)。**读侧各视图读集已逐档钉死(§3.2 契约表)**: raw 段 1m–12h = 1 个天文件(跨日界 2)、24h = 2(本地 00:00 后 30s 内 3); agg 段 3d–all 恒 1 个 `agg.dat`(与窗口长度无关); 限速注解面 = 窗口天数 + 1(24h 恒 3; 6mo 约 183 / 1y 约 366 / `all` 随保留无界 —— 唯一随窗口/历史增长的项, 备选另题); 组作用域只在数据面乘 M; **不打开 = 0 个文件**。**边界**: 保留口径不动(B3 raw_window 删除 / A1 调小窗口出局)、不做后台化(B2)、搜索索引首建另题(C1)、读侧图表与前端零改动(24h 窗 ≤2 个天文件的契约已有守阵 `tests/test_traffic_store.py`)。**报告 26-10-12-1923 追加 §10** 回答「为什么不打开流量图也需要恢复读 raw」—— 恢复读的是写侧聚合链缺口(内存累计器随进程消失, 未封口小时 raw 为唯一幸存源; 不补则 hour/day/month 永久缺失且首 flush 即固化), 读集已被收敛到与 24h 图表同阶。实施波次 W0 冻结 → W1 后端+守阵 → W2 收尾见计划 §7; **代码未动, 数字见 `commands run kb.baseline`**。
**Refs:** memory-bank/tasks/26-10-12-webui-traffic-startup-recovery-on-demand.md
