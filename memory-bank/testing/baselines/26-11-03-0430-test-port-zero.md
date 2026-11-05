# 4932 passed + 2 skipped(根) —— 测试/开发侧端口改 0(webServer.wait 捕获)后全量基线

> 摘要: 测试/开发侧端口改 0(webServer.wait 捕获)后全量基线
> 基线时间: 2026-11-03 04:30
**Refs:** memory-bank/plans/26-11-03-0316-plan-test-port-zero.html

## 验收数字

`commands run test.full` 实测(会话开工同步 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22543    134   7736    128    99%
4932 passed, 2 skipped, 3 warnings in 195.17s (0:03:15)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率)。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `scripts/ui_harness.py`: `--port` 默认 `0`, 先 `bind((host, 0))` 持 socket 再 `uvicorn.Server(...).run(sockets=[sock])`; `WebConfig.port` / 物化配置 / 打印全部用实绑端口; 绑定失败打印端口+原因并 rc≠0。
- `e2e/harness.mjs`: 删 `PORT`/`BASE_URL`/`READY_URL`, 新增 `WAIT_STDOUT` 与 `baseUrl()`(缺 `UI_HARNESS_PORT` 直接抛); `HARNESS_CMD` 恒 `--port 0`; 检测到 `E2E_PORT` 即抛错。
- `playwright.config.mjs`: `webServer` 去 `url`, 只留 `wait: { stdout: WAIT_STDOUT }`; `use` 不设 `baseURL`; `reuseExistingServer:false` 保留。
- `e2e/global-teardown.mjs`: 按 `UI_HARNESS_PORT` 拼正则收尾; 拿不到端口跳过并打印说明。
- 41 个 `e2e/*.spec.mjs` + `e2e/lib/gestures.mjs`: `BASE_URL` → `baseUrl()` 机械替换; `grep -rn BASE_URL e2e/` 归零。
- `scripts/e2e_selfcheck.py`: 删 `DEFAULT_E2E_PORT` 与固定口拦断; `E2E_PORT` 存在即报错退出; `--blocking` 仅人工排查; `8099` 告警保留。
- `scripts/dev_webui.py`: `--web-port` 默认 `0`, 删除 `8177` 与 `+1…+20` 顺延链; 0 就地 `bind(0)` 取具体口后落盘。
- `tests-real/lib/app.py`: `free_port()` 探空后立即回绑自验, 失败换候选, `RETRIES=3` 耗尽抛 `RuntimeError` (唯一 helper 改动)。
- `tests/test_port_zero_guards.py`: 新增纯文本守阵 9 条(固定口不回归 / 无第三份取号 / tests-real 含回绑自验 / E2E_PORT 设置即报错)。
