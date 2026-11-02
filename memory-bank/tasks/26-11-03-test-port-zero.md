# 26-11-03-test-port-zero — 测试/开发侧端口改 0(webServer.wait 捕获)实施

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** e2e/开发桩端口改 0 并由脚本取号回传; S1-S6 完成, 并发双 e2e 验收通过, 全量基线见 kb.baseline
**Topics:** test-port-zero
**Refs:** memory-bank/plans/26-11-03-0316-plan-test-port-zero.html

## 原始请求

1. 先提交计划与 4 条 issue(已完成: 提交 `0a67e27b`), 提交成功后按计划 S1→S5 开工。
2. S1: `ui_harness` 预绑 socket + Playwright `webServer.wait` 主线; S2: `e2e_selfcheck` 适配; S3: `dev_webui` 一律 0; S4: `tests-real` 取号补回绑自验; S5: 守阵测试与验收。
3. 本阶段结束**不要** commit/push(仅授权了前面那一次提交)。

## 思考过程与决策

- 计划: [26-11-03-0316-plan-test-port-zero](../plans/26-11-03-0316-plan-test-port-zero.html); D1 不保留 `E2E_PORT`、D2 `dev_webui` 一律 0、D3 保持两套本地 helper + `tests-real` 补回绑自验。
- 端口传递只走机制不落盘: `ui_harness` 预绑 socket(取号与监听同一 socket, 无 TOCTOU)→ 启动行打印实绑地址 → Playwright `wait.stdout` 命名组写 `UI_HARNESS_PORT` → spec 懒取值 `baseUrl()`。
- `use.baseURL` 不能设: 配置对象求值早于 webServer setup; 全部 spec 已改绝对 URL, 无需 fixture。
- spec 的机械替换: 只做 `import { BASE_URL` → `{ baseUrl` 与 `${BASE_URL}` → `${baseUrl()}` 两式, grep 归零收口。

## 实现计划

1. S1: `ui_harness.py` `--port` 默认 0、预绑 socket、统一实端口; `e2e/harness.mjs` 删静态常量、加等待正则与 `baseUrl()`; `playwright.config.mjs` 只留 `wait`; `global-teardown.mjs` 按捕获口收尾; spec codemod。
2. S2: `e2e_selfcheck.py` 去固定口阻断、`E2E_PORT` 设置即报错。
3. S3: `dev_webui.py` 删 8177 与顺延链, 默认 0 并先解析成具体口落盘。
4. S4: `tests-real/lib/app.py` 探空后回绑自验, 失败换候选, `RETRIES=3` 耗尽抛。
5. S5: `tests/test_port_zero_guards.py` 守阵 + 并发双 e2e 验收 + 全量测试与基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | harness 预绑 socket + webServer.wait 捕获 + spec codemod | Done(2026-11-03) |
| S2 | e2e_selfcheck 去固定口 / E2E_PORT 报错 | Done(2026-11-03) |
| S3 | dev_webui 默认 0, 删顺延链 | Done(2026-11-03) |
| S4 | tests-real 取号回绑自验 | Done(2026-11-03) |
| S5 | 守阵测试 + 验收 + 基线 | Done(2026-11-03) |
| S6 | 命令入口 note 与行为文档(memory-bank/testing/smoke.md 等) | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

S1-S5 已实施并验收: 单跑 e2e 与**两个并发 e2e** 各自捕获不同端口、用例全绿、teardown 杀净且无孤儿; `E2E_PORT` 设置即亮红。全量测试见 `commands run kb.baseline` 最新切片。S6(命令入口 note/行为文档)未做, 待用户另行授权。

- 2026-11-03 04:32 S1-S5 实施完成并验收(并发双 e2e 独立端口); 档案已立, S6 命令入口/行为文档待授权

- 2026-11-03 04:48 S6 文档同步: dev 包说明改脚本取号口径、smoke/browser-env 更新、4 处坑档补现状注记; doc.caps/drift/links 与 memory-bank 守阵全绿; 计划与档案转 Done
