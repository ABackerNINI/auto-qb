# 5203 passed + 2 skipped —— 全量基线: dedup 闸门前移修复收口

> 摘要: 全量基线: dedup 闸门前移修复收口
> 基线时间: 2026-11-05 00:23
**Refs:** memory-bank/plans/26-11-04-2357-plan-skip-check-gates.html

## 验收数字

`commands run test.full` 实测(2026-11-05 00:23):

```text
TOTAL                                                24404    211   8356    166    99%
5203 passed, 2 skipped in 132.89s (0:02:12)
```

口径注记: 覆盖率 99%(211 缺失 / 166 分支未覆盖为存量面); 2 skipped 为平台跳过存量。保真链验收用例 `test_ops_skip.py::test_ops_skip_check_day_shared_across_sources` 已撤 progress 绕行(修复前该形态必红, 返 G3 fail; 修复后 skip+「今日已跳检过」)。

## 本改动面

- `src/auto_qb/core/modules/ops_verdict.py`: dedup 判定块从 filelist 前移到 G3/G4 之前(执行路径首未过闸门单点), 顺序注释与 docstring 条目同步; 谓词与文案零变化。
- `tests/test_ops_skip.py`: `test_ops_skip_check_day_shared_across_sources` 撤 progress 绕行, 恢复保真链断言。
- `tests/test_checking_skip.py`: `test_checking_skip_dedup_across_rules` 保留绕行(规则侧链 0 遮蔽未修), 注释改指新 issue 26-11-05-0019。
- 文档: 计划 26-11-04-2357(拍板 D0-D3) · 新 issue 26-11-05-0019(规则侧遮蔽) · 坑档 gate-order-reachability。
