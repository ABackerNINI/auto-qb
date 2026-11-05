# 4915 passed + 10 skipped(根) —— CI 端跨 30s 桶边界 flaky 用例修复(入口钉钟)

> 摘要: 4915 passed + 10 skipped —— CI 端跨 30s 桶边界 flaky 用例修复(入口钉钟)
> 基线时间: 2026-11-03 03:32
**Refs:**

## 验收数字

`commands run test.full` 实测(Windows 并行 + 覆盖率, 本 clone 工作树):

```text
TOTAL                                                22543    152    7736    134    99%
4915 passed, 10 skipped, 3 warnings in 190.41s (0:03:10)
```

定向: `commands run test.one -- tests/test_web_longtail_traffic.py` = 6 passed in 1.06s
(`--no-cov`, 单文件不适用覆盖率闸)。

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率)。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests/test_web_longtail_traffic.py::test_api_traffic_qb_global_live_tail_realtime`:
  入口钉钟(`now = int(time.time()); monkeypatch.setattr(time, "time", lambda: float(now))`)。
  原用例三次 GET 之间墙钟可推进, 5m 滚动窗桶数 = `ceil((now - floor(now-300))/30)` 在
  `now % 30 == 0` 边界秒少一个开放桶、下一秒又补回, CI 慢时两次响应长度差一(多一个 `None`)。
  生产滚动窗语义正确, 属用例假设缺陷; 断言未放宽, 仍逐点全等比较快照/flush 竞态不重不漏。
- `memory-bank/pitfalls/testing/flaky-midnight-daycount.md`: 记第六轮实证(复发 3)与判别/处置口径。
- 不涉 `src/`、配置、前端与其它知识库正文。
