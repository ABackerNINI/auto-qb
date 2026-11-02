# 4916 passed + 10 skipped —— activeContext 切片上限 120 / 处置目标 80(纯 kb 工具轮)

> 摘要: activeContext 切片上限 120 / 处置目标 80(纯 kb 工具轮)
> 基线时间: 2026-11-03 04:07
**Refs:**

## 验收数字

`commands run test.full`(2026-11-03 实测, 全量 200.10s, 建档 04:07):

```
  TOTAL                                                22543    152   7736    134    99%
  4916 passed, 10 skipped, 3 warnings in 200.10s (0:03:20)
```

- 汇总行: **4916 passed + 10 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- **首跑红按口径处置**: `test_gen_all_check_is_green` 报 `memory-bank/tasks/attachments/_archive.md`
  生成物漂移 —— `kb.wrap` 更新任务档案后索引未重建, 属生成物陈旧非代码缺陷; `commands run kb.index`
  重建 23 个生成物后复跑全绿, 本轮无代码回滚。
- 配套验证: `kb.check` 全项绿(主键/认领链/回写/日期/HTML); `kb.active` 当前条数低于新上限, 无债务行。

## 本改动面

- `.agents/skills/memory-bank/scripts/_common.py`: 单点常量 `SLICE_COUNT_LIMIT` 70→120; 新增处置目标
  `SLICE_COUNT_TARGET = 80`。
- `.agents/skills/memory-bank/scripts/gen_active_recent.py`: 条数达到上限即报债务(`>=`), 文案带
  「当前 N 条 / 上限 120 条 / 蒸馏到 80 条以内」; `--check` 仍返回 0, 不阻断 kb.wrap 与提交。
- `tests/test_memory_bank_docs.py`: 新增守阵一条(常量 120/80、到 120 告警、119 静默、文案含落点、
  `--check` rc=0) + 「## 测试计划」清单同步。
- 文档口径同步: `memory-bank/conventions/collaboration.md`、`pitfalls/kb/cap-counting.md`、
  activeContext `26-09-30-2112-memory-bank-cap-debt.md`; 数值单点仍是 `_common`, 文档只引用不另立表。
- 边界: 不触 `src/` / `config.yml` / `auto-qb-data/`; 未清理既有切片(另开的活)。
