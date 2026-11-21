# 6660P/6S 覆盖率99% —— test.full 全绿基线

> 摘要: 6660P/6S 覆盖率99% —— test.full 全绿基线
> 基线时间: 2026-11-21 10:09

## 验收数字

```text
TOTAL                                                30044     74  10662     77    99%
6660 passed, 6 skipped, 8 warnings in 160.18s (0:02:40)
```

## 本改动面

- `.commands/review/scripts/review_content.py`: `BOOKKEEPING_PREFIXES` 正本增补 `"memory-bank/testing/real-baselines/"`(真机切片与 baselines/ 同款记账, 注释含「改一处要改两处」契约指路)
- `.commands/my-commit-flow/scripts/commit.py`: 同源抄本同步增补同款前缀; 抄本指针注释修正(初版抄自 check_review_trace.py, 判据收编进 review_content.py 单点后随迁)
- `.commands/review/scripts/check_review_trace.py`: 计数面文档字符串「不计入: 记账类」清单加 `testing/real-baselines/`
- `.commands/review/scripts/test_review_pkg.py`: `test_generated_and_bookkeeping_are_not_counted` 加真机切片排除断言; 头部「测试计划」TraceDecideTest 行同步
- `memory-bank/issues/26-11-21-0639-bug-review-bookkeeping-miss-real-baselines.html`: issue 复验/修复后补充回填 + 翻 Done(kb.status); doc-refs 反向声明任务档案(kb.new --refs 双向补链)
- `memory-bank/pitfalls/kb/review-trace-booking-sensitive-deadlock.md`: 「现口径」节后新增排除面现状补记段(`activeContext/` 经 git 实核为 11-08 取证当时原串, 历史快照不回写)
- `memory-bank/tasks/26-11-21-test-review-real-baselines-exclusion.md`: 任务档案立档(阈值 2: 改动 4 源文件)
- `memory-bank/active-context/26-11-21-1005-test-review-real-baselines-exclusion.md`: 会话切片(kb.wrap)
- `memory-bank/testing/baselines/26-11-21-1009-test-review-real-baselines-exclusion.md`: 本切片

与前一切片(26-11-21-0854, 6656P/6S)的 +4P 来自会话开工 sync 拉入的 25 笔远端提交所带测试, 与本改动面无关(本改动面不含 tests/)。
