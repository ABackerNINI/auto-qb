# 6179 passed, 2 skipped (165s, 覆盖率 99%) —— hr start_all_busy flaky 两处计时脆弱位修复批全量绿

> 摘要: hr start_all_busy flaky 两处计时脆弱位修复批全量绿
> 基线时间: 2026-11-15 06:29

## 验收数字

```text
commands run test.full (2026-11-15 06:29, 修复后实测):
  TOTAL                                                27436     72   9646     77    99%
  6179 passed, 2 skipped in 165.16s (0:02:45)
```

## 本改动面

- tests/test_hr_discovery.py::test_start_all_busy_returns_false_and_retries —— 删裸调度断言
  `assert not srv.started`(后台重试线程 retry_min_s=0.05s 即可合法翻真, 主线程停摆 ≥50ms 即假红)
  + wait_until 时限 5.0 → 15.0(并行下释放位被别的 worker 抢住期可能 >5s)。产品代码零改动。
- memory-bank/issues/26-11-15-0546-bug-hr-discovery-start-all-busy-flaky.html —— 复验/根因/修复后
  补充回写, 状态 Open → Done。
- memory-bank/pitfalls/testing/busy-release-takeover-racy-assert.md —— 立坑(「全占 → 释放 → 等接管」
  形态的两处计时脆弱位; 该用例族第三次入池后的泛化教训)。
