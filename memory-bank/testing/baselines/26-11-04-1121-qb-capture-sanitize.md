# 5140 passed + 10 skipped; 覆盖率 99% —— 全量测试基线 · qb-capture sanitize 假红修复后

> 摘要: 全量测试基线 · qb-capture sanitize 假红修复后
> 基线时间: 2026-11-04 11:21
**Refs:** memory-bank/issues/26-11-04-0943-test-qb-capture-sanitize-flaky-hash.html, memory-bank/pitfalls/testing/flaky-random-salt-hash-identity.md, memory-bank/activeContext/26-11-04-0628-qb-capture-fs-delta-sanitize.md

## 验收数字

- 汇总行: `5140 passed, 10 skipped in 177.78s (0:02:57)`(2026-11-04 本机 Windows 实测, `commands run test.full` 总耗时 180.2s)
- 覆盖率 TOTAL: `23946 stmts / 226 miss / 8188 branch / 168 partial / 99%`
- 口径注记: 本机 Windows 走 `commands run test.full`(内部已带 TMPDIR 自举); 定向口径 `commands run test.one -- tests/test_qb_capture.py` 16 passed
- 反复验证: 同进程直跑受影响的 fs_delta 用例 100 轮 —— 修前 `test_sanitize_all_rewrites_fs_delta_with_same_derivation` 8 红 / `test_self_test_flags_unscrubbed_fs_delta` 5 红, 修后均 0 红

## 本改动面

- `tests/test_qb_capture.py`: 新增合法 40 位 hex 假 hash 常量 `_FAKE_HASH`; `test_write_corpus_end_to_end_minimal` / `_fs_delta_capture` 及其三个调用用例里的非 hex 假 hash `"H1"` 全部替换(断言口径不变); 产品侧零改动
- `memory-bank/issues/26-11-04-0943-*.html`: 认领(In Progress) → 修复完成(Done), 补「复验 / 修复后补充」实测明细
- `memory-bank/pitfalls/testing/flaky-random-salt-hash-identity.md`: 新增坑档(随机盐 + 非 hex 短假 hash 恒等映射假红)
