# 4375 passed + 2 skipped —— 锁测试日志采集修正后的全量基线

> 摘要: 锁测试日志采集修正后的全量基线
> 基线时间: 2026-11-01 06:55
**Refs:**

## 验收数字

```text
TOTAL                                                21840    144   7410    122    99%
4375 passed, 2 skipped in 163.40s (0:02:43)
```

- 口径: `commands run test.full`（uv run pytest tests -q，带覆盖率；pytest.ini 默认 -n 4），2026-11-01 06:55 本机实测。
- 相对上基线的逐位对比不写（看 `commands run kb.baseline -n 2`）。

## 本改动面

- `tests/test_locking.py::test_release_file_lock_none_and_failure_logger` 手写局部捕获器改走统一 `tests/helpers.py::capture_logs`（logger 显式 setLevel + finally 恢复），断言语义不变（DEBUG 级别 + 「释放测试锁失败」消息）。
- 无 src/ 改动 —— 纯测试采集侧修复；生产侧 `release_file_lock` 释放失败本就正确打 DEBUG（单跑复现 seen==[] 定位到采集侧）。
- 坑档 `pitfalls/testing/log-capture.md` 复发 2→3（同症状第三种踩法：新用例手写捕获器漏 setLevel）。
