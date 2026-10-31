# 4180 —— relocate journal 终态前向合并修双写者竞态(含心跳拒写退休)

> 摘要: relocate journal 终态前向合并修双写者竞态(含心跳拒写退休)
> 基线时间: 2026-10-30 08:52
**Refs:** memory-bank/issues/26-10-30-0624-bug-relocate-journal-heartbeat-phase.html

## 验收数字

`commands run test.full` 实测(2026-10-30 08:30, Windows, 修复落盘后):

```
TOTAL                                                21135     96   7152    100    99%
4180 passed, 2 skipped in 144.80s (0:02:24)
```

- **汇总行**: **4180 passed / 2 skipped**, 墙时 **144.80s** 区间口径见 testing/baseline.md「耗时与覆盖率口径」。
- **TOTAL 表**: 语句 **21135** / 未覆盖 **96** / 分支 **7152** / partial **100** / 覆盖率 **99%**。
- **红验**: 竞态回归三条直接钉竞态窗口 —— `test_write_journal_refuses_nonterminal_over_terminal`
  断言非终态写终态返回 False 且 journal 不动(保序本体被移除即红);
  `test_run_heartbeat_race_aborts_when_auto_qb_closes` / `test_run_removal_aborts_when_auto_qb_closes`
  用「loop 顶读旧值 + 磁盘已终态」构造读-写间隙, 断言本轮立即 stopped、终态不被回退、removing 被拒时链接一条不删。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/infra/relocate_journal.py` | 模块头注改与事实一致(journal 实际两个写者); 新增 `STOP_PHASES`(从 finalize_watch 收编, 单一事实源); `write_journal` 写前读一次做前向合并 —— 非终态相位不得覆盖终态(done/cancelled), 拒写返回 False; 返回类型 None → bool |
| `src/auto_qb/tools/finalize_watch.py` | 四个 journal 写点接住拒写信号: 心跳/verify_mismatch/removing 被拒即返回 stopped, 其中 removing 被拒不删链接(auto-qb 收口后删除意图作废); removed 落盘不设闸(链接已删完, 终态在 journal 里本身就是记录); 本地 STOP_PHASES 定义删除改 import |
| `tests/test_finalize_watch.py` | 新增竞态回归三条(见红验) + 头部「## 测试计划」同步 |
| `memory-bank/issues/26-10-30-0624-bug-relocate-journal-heartbeat-phase.html` | 认领: Open → In Progress → Done, 状态日志记修法与 max_wait 维持 0 的评估结论 |
| `memory-bank/testing/baselines/26-10-30-0852-relocate-journal-terminal-merge.md` | 本切片 |
