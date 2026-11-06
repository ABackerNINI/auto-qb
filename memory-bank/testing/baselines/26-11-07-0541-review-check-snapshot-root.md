# 5479 passed + 10 skipped —— issue 26-11-06-0711 收尾基线

> 摘要: issue 26-11-06-0711 收尾基线(review.check 快照 root 回归钉 + 档案回写, 扶正合流序)
> 基线时间: 2026-11-07 05:41

## 验收数字

`commands run test.full` 实测 (2026-11-07, 两采 123.9s / 114.4s):

```text
TOTAL                                                24538     74   8396     41    99%
5479 passed, 10 skipped, 1 warning
```

覆盖率 TOTAL 24538 stmts / 99.63% (门槛 99.5 过; 与 03:39 切片同 TOTAL 行且 src/tests 同面, 精确值取同值)。相对上一切片(03:45, 5471)的 +8 全部来自远端 630a9b9f 的 kb.nav 用例随 sync 合流——其 03:39 切片已录同数 5479; 本批对 `tests/` 零新增, 对全量 0 增量。

包内脚本测试 `commands run test.pkg`: 360 passed, 15 subtests (2026-11-07 实测; 含本批 +1 例: CheckTest 快照 root 放行, issue 26-11-06-0711 的回归钉)。

## 本改动面

- `.commands/review/scripts/test_review_pkg.py`: +1 例 `CheckTest.test_snapshot_root_without_git_accepted`(check --root 指向无 `.git` 快照目录放行 rc=0; pack 侧拒收由既有 `CleanPackTest.test_non_repo_root_is_rc2` 钉住), 「测试计划」docstring 同步。补的是 959dc22c 落地时缺的回归测试。
- `memory-bank/issues/26-11-06-0711-bug-review-check-snapshot-root.html`: Open→Done(复验已消失 + 修复后补充)。
- `src/` 零改动(代码修复 959dc22c 已随存量评审 R4/R5 主线在树); `_index.md` 为 `kb.index` 生成物。
