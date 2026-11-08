# 5780 —— hr 头读路径断连兜底修复轮

> 摘要: hr 头读路径断连兜底修复轮
> 基线时间: 2026-11-08 11:24

## 验收数字

`commands run test.full` 2026-11-08 11:24 实测:

```text
TOTAL                                                25744     16   8916     39    99%
5780 passed, 2 skipped, 7 warnings in 133.63s (0:02:13)
```

定向: `commands run test.one -- tests/test_hr_server.py -q` → 58 passed(含新增
test_http_mid_header_disconnect_contained 与既有 test_http_mid_body_disconnect_contained),
副作用台账越界 0 条。

## 本改动面

- `src/auto_qb/hr/server.py`: `_EndpointServer` 覆写 `handle_error`(issue 26-11-08-0827)——
  (ConnectionError, OSError) 按 debug 记「连接在请求处理中断开」静默, 其余照旧
  `super().handle_error`; server 与 discovery 共用该类, 一处覆盖全部端点; 顺带补 `import sys`。
- `tests/test_hr_server.py`: 新增 `test_http_mid_header_disconnect_contained`
  (半个请求行 + SO_LINGER(1,0) RST, 断言 debug 日志/stderr 无 traceback/线程存活/后续请求照常),
  头部「测试计划」清单同步登记。
- `memory-bank/issues/26-11-08-0827-bug-hr-server-header-read-reset.html`: 状态 Open → Done,
  复验/根因/修复后补充回写。
