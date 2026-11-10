# 5947 passed + 2 skipped —— 测试假服独占 bind 单点批收尾全量绿

> 摘要: 5947 passed, 2 skipped (184.67s), 覆盖率 99% (26307 stmts / 50 miss / 9176 br / 62 partial) —— 测试假服独占 bind 单点批(issue 26-11-11-0114)收尾全量绿
> 基线时间: 2026-11-11 03:14
**Refs:** memory-bank/issues/26-11-11-0114-test-qb-conn-flake-parallel.html

## 验收数字

```text
TOTAL                                                26307     50   9176     62    99%
5947 passed, 2 skipped in 184.67s (0:03:04)
```

## 本改动面

- `tests/_test_ports.py`: 端口单点新增 `http_server()` 入口(`_ExclusiveHTTPServer`: `allow_reuse_address=False` 独占 bind + `server_bind` 跳过 getfqdn 启动期零 DNS + `request_queue_size=128`; 两项口径逐字对齐生产 `src/auto_qb/hr/server.py::_EndpointServer`); 模块 docstring 两入口改三入口并记根因。
- `tests/helpers.py` / `tests/test_tool_client.py` / `tests/test_legacy_review4_scripts.py`: 三处裸 `ThreadingHTTPServer` 假服改走单点(FakeQB / _StubTool / qb_capture 计数假服)。
- `tests/test_free_port.py`: 新增 `test_http_server_exclusive_bind_and_roundtrip`(独占 bind + 真回环往返 + 零 DNS)与 `test_http_server_single_point`(tests/ 下禁裸 ThreadingHTTPServer 直建; 唯一豁免 = bind 扫描器夹具字面量测试数据; 守卫可扫自身); 头部测试计划同步两条。
- `memory-bank/issues/26-11-11-0114-test-qb-conn-flake-parallel.html`: 翻 Done(kb.status) + §05 根因 + §07 复验/修复后补充 + doc-refs 双链。
- `memory-bank/testing/flaky-ledger.md`: 加 1 行 Done 条目(假服族 ConnectionError 假红, 端口/资源类目)。
- `memory-bank/testing/root-cause-taxonomy.md`: 端口/资源行回写(假服 reuse-bind 治理 + 三入口)。
- `memory-bank/pitfalls/testing/fake-server-reuse-bind.md`: 新坑档(触发/判别/处置/守阵)。
- 评审: 分批评审 3 轮(全能档单派): blocker 1(守卫误伤 bind 扫描器夹具字面量)当场修 + nit 1(守卫自豁免盲区)当场修, 轮 3 零 actionable。
- 与上片差值: 5945 → 5947 (+2, 即上述两条新守阵); 50 miss 不变。
