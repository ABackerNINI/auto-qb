# 5211 —— 全量基线: 规则侧跳检dedup前插修复

> 摘要: 全量基线: 规则侧跳检dedup前插修复
> 基线时间: 2026-11-05 02:12
**Refs:** memory-bank/tasks/26-11-05-backend-rule-skipcheck-dedup.md

## 验收数字

`commands run test.full` 实测(2026-11-05 02:12, Windows, 本机):

- 汇总行: `5211 passed, 10 skipped in 154.81s (0:02:34)` —— 0 failed
- 覆盖率 TOTAL 表末行: `TOTAL 24461 227 8388 167 99%`(语句 24461 / 缺 227 / 分支 8388 / 部分覆盖 167)
- 口径注记: 中途两轮全量出现的 `test_gen_all_check_is_green` 假红为文档索引陈旧(收尾建件后须重跑 kb.index), 非代码回归; 覆盖率阈值判定在本机显示 `FAIL ... 98.74%` 属既有稳态(双 OS 覆盖率底坑, 见 pitfalls/testing/coverage-floor-platform.md), 汇总退出码 0。

## 本改动面

- `src/auto_qb/core/modules/ops_verdict.py`: 新增只读谓词单点 `skip_checked_today`(dedup 闸门同源消费); 四处对 checking.py 的裸行号互指改符号锚(评审 minor #1)
- `src/auto_qb/rules/actions/checking.py`: 决策链 dedup 前插(dry-run 后、S2 deferral 前), docstring 决策链清单补 dedup 行(26-11-05-0019)
- `tests/test_checking_skip.py`: test_checking_skip_dedup_across_rules 撤空操作绕行, 改真机保真现场(progress=1.0); 修复前该用例必红(红验实测)
- `memory-bank/`: issue 26-11-05-0019 翻 Done、任务档案 26-11-05-backend-rule-skipcheck-dedup 建档、坑档 gate-order-reachability 补「空操作绕行」反向信号、认领链(plan/pitfall/doc-refs)双向闭环
