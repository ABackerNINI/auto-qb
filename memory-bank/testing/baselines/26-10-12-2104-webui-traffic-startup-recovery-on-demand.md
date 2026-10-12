# 3164 —— 流量启动恢复改为按需读取口径(读集下界 = agg 水位所在日, W1+W2 实施)

**Refs:** memory-bank/plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html,memory-bank/tasks/26-10-12-webui-traffic-startup-recovery-on-demand.md,memory-bank/issues/26-10-12-2104-docs-traffic-rollup-window-docstring-drift.html,memory-bank/activeContext/26-10-12-2017-webui-traffic-startup-recovery-on-demand.md

> 摘要: 实施计划 26-10-12-2010: `_recover_series` 读集下界 `now - rollup_window` → `v4_day_epoch(wm_hour)`(agg 水位所在日), 常态 1 个天文件、跨日界至多 2 个, 与 24h 流量图读侧同阶; `agg.dat` 仍按系列照读(D4); agg 无可用水位时退回保留窗全量兜底 + INFO(D5 诚实兜底)。保留口径 `rollup_window: 1000000D` 不动。新增埋点: 恢复起止 INFO + `recovery_reads`/`recovery_stats` 计数属性(机检「读集有界」)。新增守阵 17 个(读集有界 / fallback 不烂 / 埋点行 / 读侧契约 13 档逐档机检 / 前端轮询门控), 注入红验通过(下界改回 `now - window` ⇒ 读集守阵红, 还原即绿)。
> 基线时间: 2026-10-12 21:04

上一基线: memory-bank/testing/baselines/26-10-12-2031-webui-drawer-tpl-flicker-fix.md

## 验收数字

- `test.full`: **3164 passed + 4 skipped, 0 failed** / 41.3s / 覆盖率 `TOTAL 16737 160 5694 139 99%`(上一基线 3146 passed + 4 skipped; 本波新增 17 个守阵测试 = 3164 - 3147, 3147 为 20:19 纯文档轮全量收集数)。
- 注入红验(守阵质检): 把 `_recover_series` 下界临时改回 `now - window` ⇒ `test_recovery_read_set_bounded_to_watermark_day` 红(day_files 从 48 涨到系列数 x ~29); 还原 ⇒ 绿。
- 分文件回归: `tests/test_traffic_sample.py` 83 passed(改前 66, +17) · `tests/test_traffic_store.py` 41 passed(读侧 24h 窗只开 2 日期文件守阵不回归)。
- e2e(`dev.e2e`): 全量 206 用例 **135 passed / 61 failed / 10 skipped** —— 失败签名**全部**是 `ERR_CONNECTION_REFUSED`/`ECONNREFUSED`/`ERR_CONNECTION_RESET`(桩服务 8137 中途拒连, 跨 perf/menus/views/optimistic 等无关面, 零断言内容失败), 与本波零前端零 API 改动面不符; 按 `pitfalls/testing/smoke.md` 判别 = 桩服务中途死亡(环境坑), 归因后复跑 `@fast` 子集 **108 passed / 0 failed** 证实桩服务与本波代码健康; 全量 e2e 复跑留待环境稳定时(转告项)。

## 本波改动面

- `src/auto_qb/core/modules/traffic_sample_mod.py`: ① `_recover_series` 读集下界 `now - window` → `v4_day_epoch(wm_hour)`, `wm_hour is None` 退回 `now - window`(D5); ② `_recover_aggregates` 起止 INFO + `recovery_reads`(逐系列 day_dates/bound/new_hours/slots)与 `recovery_stats`(series/day_files/hours/slots/elapsed_s)计数属性; ③ 读集 > 2 天时 INFO 留下界来源(水位日陈旧 / fallback 全量); ④ 模块 docstring §4.3 与 `_recover_series` docstring 口径句改写; ⑤ `_agg_credit_day_file` 增可选 `slot_counter` 位置参(既有三参调用零影响)。
- `src/auto_qb/core/traffic_store.py`: `series_day_dates` docstring 「补算窗口过滤」→「调用方传读集下界」(行为零改动)。
- `tests/test_traffic_sample.py`: +17 守阵(3 恢复侧 + 13 读侧契约参数化 + 1 前端轮询门控静态), 文件头「## 测试计划」同步。
- 知识库: 任务档案状态表/进度日志、activeContext 切片、计划 §10(下方状态行)、本基线切片; 计划外文档漂移入池 issue 26-10-12-2104(config/models.py `QbTraffic` docstring 仍写「聚合补算窗口」旧三义, 本轮未动它 —— 范围守恒)。

## 已知偏差 / 移交

- 真机走查留待用户: 重启 auto-qb 观察新 INFO 行(「启动恢复开始/完成」)与死区时长(报告实测死区 11.16s, 其中恢复 7.09~7.28s; 收敛后理论 ≈ agg.dat 读取 ~0.02s + ≤2 天文件逐槽入账)。
- 搜索索引首建独占主循环(C1, 1.7~2.5s)不在本计划, 另题。
- 限速注解面(1 文件/天不淘汰, `all` 随保留无界)是 §3.2 契约表唯一随窗口增长的项, 备选另题。
