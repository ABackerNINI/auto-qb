# 3147 —— 流量启动恢复计划入库(纯文档轮, 零代码改动)

**Refs:** memory-bank/tasks/26-10-12-webui-traffic-startup-recovery-on-demand.md

> 摘要: 纯文档轮 —— 产出计划 26-10-12-2010(启动恢复读集下界 → agg 水位所在日)、报告 26-10-12-1923 追加 §10(为什么恢复必须读 raw)、任务档案与活跃切片; **零代码零测试改动**, 本片记录该树上的全量测试数字。
> 基线时间: 2026-10-12 20:19

上一基线: memory-bank/testing/baselines/26-10-12-1903-webui-traffic-chart-stale-inverted.md

## 本波改动面

- `memory-bank/plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html`: 新增(计划, Open 待拍板)。
- `memory-bank/reports/26-10-12-1923-report-webui-startup-latency.html`: 追加 §10「为什么启动恢复必须读 raw(不是「打开才读」)」+ `doc-updated` 抬至 26-10-12-2017。
- `memory-bank/tasks/26-10-12-webui-traffic-startup-recovery-on-demand.md` · `memory-bank/activeContext/26-10-12-2017-webui-traffic-startup-recovery-on-demand.md`: 新增。
- 代码面: **零改动**(`src/` / `tests/` 一行未动); 本片数字因此与上一基线同源。

## 验收数字

- `test.full`: **3147 passed + 4 skipped, 0 failed** / 35.29s(单次采样) / 覆盖率 `TOTAL 16708 161 5688 140 99%`。
- 注: 本片只测 Windows 侧; Linux 侧未重测(本波零代码改动, 无平台面)。
- 注: 本波零测试增删 —— 收集数 = 3147 passed + 4 skipped。
