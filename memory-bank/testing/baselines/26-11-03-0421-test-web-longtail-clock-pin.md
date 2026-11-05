# 4915 passed + 10 skipped(根) —— 尾桶边界派生用例按 B 端点固定钟收口

> 摘要: 4915 passed + 10 skipped —— 尾桶边界派生用例按 B 端点固定钟收口
> 基线时间: 2026-11-03 04:21
**Refs:**

## 验收数字

`commands run test.full` 实测(Windows 并行 + 覆盖率, 本 clone 工作树):

```text
TOTAL                                                22543    152    7736    134    99%
4915 passed, 10 skipped, 3 warnings in 208.85s (0:03:28)
```

定向: `commands run test.one -- tests/test_web_longtail_traffic.py` = 6 passed in 4.27s
(副作用台账 40 条/越界 0); 七个相关 web/traffic 文件同批 = 168 passed。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests/webui_helpers.py`: 新增 `_freeze_traffic_endpoint_clock(monkeypatch, now)` ——
  只把 `auto_qb.webui.server.traffic_qb.time` 换成固定钟, 端点 `_grid` 与用例算边界的
  now 同源; 测试进程其它 `time.time` 不冻。
- `tests/test_web_longtail_traffic.py`: 三条尾桶定位用例接入(B 方案, 各 1 行) ——
  3d 开放小时、组 30d 开放小时、6mo 开放日; 断言强度不变(仍比 `points[-1]/[-2]`、
  `totals[-1]` 与 `h_open/d_open` 全等)。上一轮 5m 跨请求全等用例的入口钉钟保留。
- `memory-bank/pitfalls/testing/flaky-midnight-daycount.md`: 记第六轮补(复发 4)与
  「尾桶派生量必须同源时钟」判别口诀。
- 不涉 `src/`、配置、前端。
