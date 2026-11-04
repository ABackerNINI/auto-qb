# 5205 passed + 10 skipped; TOTAL 24444 / 227 miss / 99% (test.full) —— 修复 test_w6_flush_fallback_once_per_round 偶发红后全量基线

> 摘要: 修复 test_w6_flush_fallback_once_per_round 偶发红后全量基线
> 基线时间: 2026-11-05 00:59
**Refs:** memory-bank/issues/26-11-05-0035-test-qbmanager-flush-fallback-flaky.html, memory-bank/activeContext/26-11-05-0048-qbmanager-loop.md

## 验收数字

- `commands run test.full` 实测(2026-11-05 00:59, Windows 本机):
  - 覆盖率 TOTAL 表: **TOTAL 24444 / 227 miss / 99%**(statements 24444, missed 227, branch 8382, brMiss 167)
  - 汇总行: **5205 passed, 10 skipped in 190.08s (0:03:10)**
  - 口径: 全量 pytest 含覆盖率报表; 10 skipped 为平台条件跳过; 数字为该次运行实测, 非均化

## 本改动面

issue 26-11-05-0035(时序敏感用例偶发红)的最小修复:

- `tests/test_qbmanager_w6.py`: `test_w6_flush_fallback_once_per_round` 改为按「循环轮数」记账 ——
  回执 flush 每轮无条件调用, 与只在同步线调用的 refresh 不再按序数绑定; 异常轮由 refresh
  计数判定并抛 KI, 另加等待次数上限兜底出口(防兜底被改坏时无限重试到超时)。生产代码未改。
