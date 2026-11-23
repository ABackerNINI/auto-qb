# 7025 passed + 6 skipped —— issue 26-11-21-1326 修复批后基线 —— relocate_journal settled 词表注记消歧(重放闸口径与 daemon 改写步语义分层), 纯注释零行为变化, 用例数不变

> 摘要: issue 26-11-21-1326 修复批后基线 —— relocate_journal settled 词表注记消歧(重放闸口径与 daemon 改写步语义分层), 纯注释零行为变化, 用例数不变
> 基线时间: 2026-11-23 12:14

## 验收数字

`commands run test.full` 实测:

```
TOTAL                                                31412    108  11190     93    99%
7025 passed, 6 skipped, 1 warning in 123.78s (0:02:03)
```

## 本改动面

- `src/auto_qb/infra/relocate_journal.py`: 纯注释/docstring 消歧 —— unmatched/member_gone 词表注记明确「重放无意义/不再无限重试」只约束 daemon 改写步; `REWRITE_SETTLED_FROZEN` 消费方注记与 `reset_rewrites` docstring 点明清回 pending 属下窗重确认(无害收敛), 三处统一指向 FROZEN 注记「消费方按语义取用」句。零代码行为变化, `REWRITE_SETTLED`/`REWRITE_SETTLED_FROZEN` 两个 frozenset 与所有判据未动。
- `memory-bank/issues/26-11-21-1326-docs-relocate-replay-note-drift.html`: 补「实际修法(采纳 (b))/验证」到 §03, 状态 Open → Done。
- 相对 26-11-23-1121(7025P/6S): 用例数与覆盖率全不变 —— 纯注释改动, 无新增守阵。
- 只读评审零发现(事实/口径/符号逐条对源码核对); `ship.gate` 全绿; `kb.check` 全绿。
- 真机准入: 纯注释字面改动, 零运行时行为变化, 无真机可验面, 免真机轨。
