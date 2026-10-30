# 4188 passed + 2 skipped(根) —— 常驻锚蒸馏改版与防流水守阵后全量

> 摘要: 常驻锚 26-10-08-0642 蒸馏改版(移除逐轮台账/逐轮状态日志, 只留 §07 覆盖进度总表一张记录表)+ 新守阵 `check_mutation_anchor.py`(挂 kb.check + 提交闸门)+ `tests/test_memory_bank.py` 新增 3 条守阵测试, test.full 全绿
> 基线时间: 2026-10-31 02:00

**Refs:** memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html, memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-10-31-0029-memory-bank-kb-nav-searchbox.md

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 119.89s, 建档 02:00):

```
  TOTAL                                                21144     99   7160    101    99%
  4188 passed, 2 skipped in 119.89s (0:01:59)
```

- 汇总行: **4188 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 对上基线(26-10-31-0029: 4185 passed): **passed +3** —— 即本轮新增的 3 条守阵测试
  (test_mutation_anchor_guard_is_green_on_current_kb / test_mutation_anchor_guard_flags_ledger_log_and_round_numbers /
  test_mutation_anchor_guard_is_wired_into_kb_check_and_gate)。

## 本改动面

- `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html`: 常驻锚蒸馏改版 —— §08 轮次台账与逐轮状态日志整体移除(事实源 = 任务档案 + 基线切片), 只留 §07 覆盖进度总表; 修 §07 hr 行漏记 R22 与 core 行计划指针; CSS 按 create-issue 最新模板重制。
- `.agents/skills/memory-bank/scripts/check_mutation_anchor.py`(新): 常驻锚防流水守卫, 挂进 `.commands/kb/config.toml` 的 kb.check 与 `.commands/my-commit-flow/.my-commit-flow.toml` 提交闸门。
- `tests/test_memory_bank.py`: 新增 3 条守阵测试 + docstring 测试计划同步。
- `.agents/skills/mutation-testing/SKILL.md`: 「issue 只做锚, 不记流水」条补守阵指针。
