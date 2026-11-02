# 4933 passed, 2 skipped, 3 warnings in 173.58s (0:02:53); TOTAL 22543 134 7736 128 99% —— 端口改 0 实施轮全量测试基线

> 摘要: 端口改 0 实施轮全量测试基线
> 基线时间: 2026-11-03 05:34
**Refs:**

## 验收数字

- 汇总行: `4933 passed, 2 skipped, 3 warnings in 173.58s (0:02:53)`
- 覆盖率 TOTAL: `22543 stmts / 134 miss / 7736 branch / 128 partial / 99%`

## 本改动面

- `scripts/ui_harness.py`: `--port` 默认 0, 预绑 socket 取号并打印实绑 URL
- `e2e/harness.mjs`: 删 `PORT`/`BASE_URL`/`READY_URL`, 增 `WAIT_STDOUT` 与 `baseUrl()`; 设置 `E2E_PORT` 即抛
- `playwright.config.mjs`: webServer 只留 `wait`; `reuseExistingServer` 保持 false
- `e2e/global-teardown.mjs`: 按 `UI_HARNESS_PORT` 收尾
- `e2e/*.spec.mjs` + `e2e/lib/gestures.mjs`: `BASE_URL` → `baseUrl()`
- `scripts/e2e_selfcheck.py`: 删固定口阻断, `E2E_PORT` 直接报错
- `scripts/dev_webui.py`: `--web-port` 默认 0, 删 `+1…+20` 顺延链
- `tests-real/lib/app.py`: 取号后回绑自验, 连抢 3 次抛
- `tests/test_port_zero_guards.py`: 9 条守阵
