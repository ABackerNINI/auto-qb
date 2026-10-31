# 3185 —— rollup_window「三义合一」→「两义合一」docstring 漂移清偿(4 处)

**Refs:** memory-bank/issues/26-10-12-2104-docs-traffic-rollup-window-docstring-drift.html

> 摘要: 清偿 issue 26-10-12-2104 —— 启动恢复读集按需口径(plan 26-10-12-2010)落地后, `rollup_window` 不再决定恢复读集, 但 4 处注释仍写旧「hour 行保留窗 + 系列淘汰龄 + 聚合补算窗口(= 天文件存活期)三义合一」。用户当场定调一并修这 4 处(scope-guard 例外 3「用户当场扩范围」): `config/models.py` `QbTraffic` docstring · `core/traffic_store.py:65` 模块头 · 同文件 `:68` catch-up 读集描述 · 同文件 `:823` `TrafficV4Store` 类 docstring · `docs/configuration.md:425` YAML 注释 —— 三义 → 两义, 并注「原『聚合补算窗口(= 天文件存活期)』一义已解耦 —— 恢复读集下界 = agg 水位所在日, 不由此窗口决定」。**纯注释/docstring 改动, 零行为面**。全绿即基线。
> 基线时间: 2026-10-13 07:31

上一基线: memory-bank/testing/baselines/26-10-13-0643-seed-state-writeback-s2.md

## 验收数字

- `test.full`: **3185 passed + 4 skipped, 0 failed** / 41.7s / 覆盖率 `TOTAL 16778 159 5714 140 99%`.
- 纯注释/docstring 改动, 语句/分支数与覆盖率相对上一基线持平(逐位差值看 `commands run kb.baseline -n 2`); 用例数 +1 来自本会话同步的 14 笔远端提交, 与本改动无关.
- Linux 侧未重测(改动为纯 docstring/注释, 平台无关).

## 本波改动面

- **源**: `src/auto_qb/config/models.py` (`QbTraffic.rollup_window` docstring) · `src/auto_qb/core/traffic_store.py` (模块头 + catch-up 行 + `TrafficV4Store` 类 docstring).
- **文档**: `docs/configuration.md` (qb_traffic YAML 示例注释) · issue 26-10-12-2104 状态日志(Open → In Progress → Done) · activeContext 切片 · 本基线切片.

## 已知偏差 / 移交

- 无行为面偏差; `grep -rn "三义合一" src/ docs/` 归零(仅余 `.pyc` 缓存, 下次 import 重生成).
- 相关只读冻结件(不改): 报告 `memory-bank/reports/26-10-12-1923-report-webui-startup-latency.html` 的 A10 行仍引旧「三义合一」表述 —— 报告出厂即冻结, 属历史现场, 不回写.
