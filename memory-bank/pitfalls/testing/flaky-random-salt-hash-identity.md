# 随机盐逐位映射下非 hex 短假 hash 可恒等 —— 脱敏断言假红

> 摘要: 随机盐逐位映射下非 hex 短假 hash 可恒等 —— 脱敏断言假红
> 触发: flaky, 偶发红, 假红, 随机盐, os.urandom, infohash, 假 hash, 恒等映射, 非 hex, 短 hash, 40 位 hex, 脱敏, 夹具, 1/16, 16^-40
**Refs:** memory-bank/issues/26-11-04-0943-test-qb-capture-sanitize-flaky-hash.html, memory-bank/testing/baselines/26-11-04-1121-qb-capture-sanitize.md

### 随机盐逐位映射下非 hex 短假 hash 可恒等 —— 脱敏断言假红

- **触发**: 用例夹具用**短的非 hex 假 hash**(如 `"H1"`)喂 `qb_capture.Sanitizer`, 且走 `Capture.sanitize_all()`(每次 `os.urandom(32)` 新盐逐位映射); 断言是「真 hash 不得留在流里」或「未脱敏态 → 自检必红」。全量偶发红、单文件重跑又绿。
- **判别**: 失败率约 1/16 —— 非 hex 字符被原样保留, 只有那 **1 个 hex 位**会以 1/16 概率映射回自身; 一旦 `infohash("H1") == "H1"`, 「已脱敏」与「未脱敏」不可区分, 泄漏断言与自检红断言同时假红。取证: 同进程循环直跑目标用例计数, 或统计 `Sanitizer(os.urandom(32)).infohash("H1") == "H1"`(实测 59/1000)。与 `_san()` **固定盐**的用例无关(固定盐档是确定性的)。产品 `infohash` 逐位映射语义正确, **不要**放宽阈值或删断言。
- **处置**: 夹具改用 qB 真实可能的 hash 形态 —— 合法 40 位 hex 假 hash(如 `_FAKE_HASH = "0123456789abcdef0123456789abcdef01234567"`), 恒等概率降到 16^-40; 断言口径不变。**别只修红了的那一条** —— 同文件内同款夹具要一起扫换(本次 `"H1"` 同时埋在 `test_write_corpus_end_to_end_minimal` / `_fs_delta_capture` 的调用用例 / `test_self_test_flags_unscrubbed_fs_delta` 里, 只是恰由其中一条先红)。
- **守阵**: `tests/test_qb_capture.py` 的四条用例(落盘全链最小用例 + fs_delta 三连); 红验 = 把夹具换回 `"H1"` 后同进程 100 轮直跑, 约 5-8 次红。

