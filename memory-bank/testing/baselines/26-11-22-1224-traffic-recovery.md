# 6954 —— 6954 passed, 0 failed, 6 skipped —— 流量恢复(计划 26-11-21-1546)S6 收尾全量基线: 恢复换代+acc账本+raw保留窗落地

> 摘要: 6954 passed, 0 failed, 6 skipped —— 流量恢复(计划 26-11-21-1546)S6 收尾全量基线: 恢复换代+acc账本+raw保留窗落地(首跑红旗快照见补绿记录)
> 基线时间: 2026-11-22 12:24
**Refs:** memory-bank/tasks/26-11-21-backend-traffic-recovery.md

## 验收数字

`commands run test.full` 实测(2026-11-22, Windows, HEAD d5df22b9, 收尾回写随工作树在场):

```text
TOTAL                                                31250    107  11118     88    99%
6954 passed, 6 skipped, 8 warnings in 150.85s (0:02:30)
Required test coverage of 99.5% reached. Total coverage: 99.52%
```

- 汇总: **6954 passed / 6 skipped / 0 failed**; 覆盖率闸门达标(99.52% ≥ Windows 阈, 见 testing/baseline.md), 耗时单次采样 150.85s(并行 -n 8)。
- **补绿记录**: 首跑(150.97s)含 1 failed = `test_ascii_symbol_guard::test_repo_matches_frozen` —— `tests-real/.work/s5traffic/tools/s5rm.py [circled]` 实测 4(S5 判据③④构造工具, gitignore 未跟踪, docstring 圈号); 主会话已圈号改括号数字(4 处)后重跑本片终态全绿, 两轮数字均如实誊写。
- 缺口净额: 本片 195 单位(miss 107 + partial 88) 与上片 26-11-21-1503 的 163 单位(miss 82 + partial 81) 相比 **+32**; 分母由语句 30547 / 分支 10880 变为 31250 / 11118(+703/+238)。点名(实测逐模块): `core/traffic_store_acc_ledger.py`(本计划新文件, 93%, miss 19 + partial 1 = 20 单位, 缺口集中撕裂尾/压实重写分支 539-556)与 `core/modules/traffic_sample_agg.py`(99%, 5 miss + 4 partial = 9 单位)为主, 其余流量采样面 100%; 属「新功能面进榜」非「代码变差」。

## 本改动面

本计划(26-11-21-1546)S1-S5 代码面 + S6 回写面, 基线随工作树誊写:

- 代码面(S1-S3, 提交 cb84c312..8d2ae7f0): B1 字节级块定位 + 开放段限定解析、B2 游程级闭合式入账、D12 HourFold 折叠态重构、acc 快照账本(`core/traffic_store_acc_ledger.py` 新文件 + 接线)、raw 保留窗清理(`v4_raw_keep_floor_date` + `prune_raw_window_days` + 清理 daemon)。
- 守阵面(S4, 3ad906e8): 聚合输出对拍(bitwise 等价)、快照异常矩阵、保留窗公式钉面、e2e 冷启动两跳回归 + ui_harness 桩补 `relocating_hashes()`。
- S5 真机验收(d5df22b9): 四判据全过(数字单点 = 报告 26-11-21-1650 §05), harness/工具为 gitignore 工作树件(`tests-real/.work/`), 工具 `scripts/bench_traffic_recovery.py` 已跟踪。
- 回写面(本子代理): 架构单点 data-state.md 新增「流量采样存储与启动恢复」节 + overview.md 包边界行、两条坑档(long-task-background-checkpoint / stub-interface-rename-sweep)、本基线切片; 计划/报告状态翻页与切片收尾归主会话。
