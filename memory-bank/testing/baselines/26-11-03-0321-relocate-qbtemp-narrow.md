# 4914 passed + 2 skipped(根) —— RM04-10 真机用例与 docstring 修正后全量基线

> 摘要: Relocate .!qB 窄域计划收尾(RM04-10 真机用例 + 测试 docstring 修正)后全量基线
> 基线时间: 2026-11-03 03:21
**Refs:** memory-bank/plans/26-11-02-0134-plan-relocate-qbtemp-narrow.html, memory-bank/tasks/26-11-02-backend-relocate-qbtemp-narrow.md

## 验收数字

`commands run test.full` 实测(Windows 并行 + 覆盖率):

```text
TOTAL                                                22531    134   7732    128    99%
4914 passed, 2 skipped, 3 warnings in 184.95s (0:03:04)
```

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests-real/rm04_relocate/test_rm04_relocate.py`: 新增 RM04-10(.!qB 窄域 S5 真机用例) + 头部摘要九→十条;
  `tests-real/` 不进默认全量, 真机数字见 `testing/real-baselines/26-11-03-0316-real-RM04-qbtemp.md`。
- `tests/test_relocate_units.py`: 头部「## 测试计划」闸门枚举补 `target_type`(仅 docstring, 无逻辑改动)。
- `src/`: 零 diff; 本轮全量数字与 26-11-03-0157 切片逐位一致。
