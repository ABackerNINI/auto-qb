# 26-11-11-test-fake-server-exclusive-bind — 修复 issue 0114: 测试假服裸 ThreadingHTTPServer 并发双绑假红

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** 修复 issue 0114: 测试假服裸 ThreadingHTTPServer 并发双绑假红
**Topics:** test-fake-server-exclusive-bind
**Refs:** memory-bank/issues/26-11-11-0114-test-qb-conn-flake-parallel.html

## 本篇只回答

「tests/ 内自起回环 HTTP 假服为什么在 -n 8 并发下偶发 ConnectionError 假红, 以及触发面怎么消」—— 根因(Windows SO_REUSEADDR 双绑)与修法(端口单点新增 http_server 独占 bind 入口)的单点记录; 领域结论沉淀在 pitfalls/testing/fake-server-reuse-bind.md。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-11-0114-test-qb-conn-flake-parallel.html」(用户指派认领, 2026-11-11)。

## 思考过程与决策

- **根因定位**: 症状 1(test_qb_capture_dry_true_zero_requests, ConnectionError 被中止)的假服是裸 `ThreadingHTTPServer` —— 继承 `HTTPServer.allow_reuse_address = 1`(SO_REUSEADDR); 生产侧 `src/auto_qb/hr/server.py:20` 已有同款论述: Windows 上 SO_REUSEADDR 允许抢绑已监听端口。并行下各 worker 假服都带 REUSEADDR, 双绑后连接串线/递给已关闭 socket, 与「单跑不复现、复跑全绿」吻合。
- **修法决策**: 消触发面而非 retry(台账口径「retry 不是修复」); 收敛进既有端口单点 tests/_test_ports.py(新增 `http_server()`, 独占 bind + server_bind 跳过 getfqdn + backlog 128, 两项口径逐字对齐生产 `_EndpointServer`); 三处假服(FakeQB/test_tool_client/test_legacy_review4_scripts)改道; 散落守卫禁裸实例化。
- **症状 2(test_hr_discovery bind 用例)诚实留痕**: 该路径无 HTTP 客户端流量、socket 全部独占口径, 双绑机制对它不成立, 报错原文当年未录 —— 不强行归因, 复现时先抓 traceback。
- **同族边界**: 远端 297c083b 同日从另一面修过本 issue 关联面(bind 守阵构造位收编, 翻的是新池件 0237); 两修互补不重叠。

## 实现计划

1. _test_ports.py 新增 `_ExclusiveHTTPServer` + `http_server()`(含 HTTP_SERVER_BACKLOG 常量)。
2. 三处假服改走单点(helpers.py / test_tool_client.py / test_legacy_review4_scripts.py)。
3. test_free_port.py 加行为守阵 + 散落守卫(豁免 bind 扫描器夹具字面量; 守卫可扫自身)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | _test_ports.py 单点入口 | Done(2026-11-11) |
| 2 | 三处假服改道 | Done(2026-11-11) |
| 3 | 守阵 + 散落守卫 | Done(2026-11-11) |
| 4 | 分批评审(全能档, 轮 1-3) | Done(2026-11-11) |
| 5 | test.full + 基线切片 | Done(2026-11-11) |

## 进度日志

### R0 · 立档 (2026-11-11)

认领 issue 0114 并完成修复: 单点入口 + 三处改道 + 两条守阵; 分批评审 3 轮(blocker 1 修 + nit 1 修), test.quick 全量多轮全绿(数字随本批基线切片入库, 见 kb.baseline); 详情见 issue 修复后补充与 pitfalls/testing/fake-server-reuse-bind.md。

- 2026-11-11 03:18 修复 issue 26-11-11-0114: 端口单点新增 http_server 独占 bind 入口, 三处假服改道, 守阵+散落守卫; 分批评审 3 轮零 actionable; test.full 全量绿(数字见 kb.baseline); issue 翻 Done, 台账+pitfalls+taxonomy 回写
