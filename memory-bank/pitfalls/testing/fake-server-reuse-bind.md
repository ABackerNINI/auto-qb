# 测试假服裸 ThreadingHTTPServer 带 SO_REUSEADDR, Windows 并行双绑假红

> 摘要: 测试里自起回环 HTTP 假服若用裸 `ThreadingHTTPServer`, 它继承 `HTTPServer.allow_reuse_address = 1`(SO_REUSEADDR) —— Windows 上允许抢绑已监听端口, `-n 8` 并行下两把假服可能 bind(0) 到同一端口, 连接被递给别人的假服/已关闭的 socket ⇒ 客户端 ConnectionError(被中止) 假红。修法单点: `tests/_test_ports.py::http_server`(独占 bind, 对齐生产 `_EndpointServer` 口径), tests/ 下禁裸实例化。
> 触发: ThreadingHTTPServer, 假服, 双绑, SO_REUSEADDR, allow_reuse_address, ConnectionError, 回环 HTTP, 并发假红, http_server 单点, 独占 bind
**Refs:** memory-bank/issues/26-11-11-0114-test-qb-conn-flake-parallel.html, memory-bank/tasks/26-11-11-test-fake-server-exclusive-bind.md

## 本篇只回答

「测试自起回环 HTTP 假服在并行全量下偶发 ConnectionError/连接串线」这类假红的确诊与处置; 以及测试假服的 bind 口径该怎么写。

### 裸 ThreadingHTTPServer 的 SO_REUSEADDR 在 Windows 上允许双绑 —— 并行下连接串线假红

- **触发**: 在 tests/ 里写 `ThreadingHTTPServer(("127.0.0.1", 0), handler)` 这类**裸实例化**(继承 `HTTPServer.allow_reuse_address = 1`)。单跑恒绿; `-n 8` 全量并行下偶发 —— 各 worker 的假服都带 REUSEADDR, 内核可能把同一端口分给两把 bind(0), 客户端连接被递给别人的假服或已关闭的 socket。
- **判别**:
  - 报错形如 `requests.exceptions.ConnectionError`("Connection aborted" / 被中止), 指向**用例内自起的假服**端口; 单跑该用例即过, 复跑全量全绿, 只在并行全量下冒。
  - 排除法: 假服构造即 bind+listen(同步), 不存在「起线程前端口未就绪」的 TOCTOU; 被测代码与假服无共享面 —— 剩下的就是 bind 口径本身。
  - 生产侧同款论述单点: `src/auto_qb/hr/server.py` 模块 docstring(`allow_reuse_address = False` 的理由行)。
- **处置**:
  - 假服一律走端口单点 `tests/_test_ports.py::http_server(handler)`(`_ExclusiveHTTPServer`: `allow_reuse_address=False` 独占 bind + `server_bind` 跳过 getfqdn 启动期零 DNS + `request_queue_size=128`), 两项口径与生产 `_EndpointServer` 逐字一致; 用法与裸件只差构造这一行(start/shutdown/server_close 照旧)。
  - **不要**用 retry/重试遮这个症状 —— 独占 bind 把触发面消掉; 也不要在测试文件里复制一份子类(散落守卫会拦)。
  - 只要"一个空闲端口"仍用 `free_port()`; 连号段用 `hold_run()` —— 三个入口同在 `tests/_test_ports.py`。
- **守阵**: `tests/test_free_port.py::test_http_server_exclusive_bind_and_roundtrip`(独占 bind + 真回环往返 + 零 DNS, 属性断言即红验)、`::test_http_server_single_point`(tests/ 下禁裸 ThreadingHTTPServer 直建; 唯一豁免 = bind 扫描器夹具 `test_flaky_timing_guards.py` 的字面量测试数据)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
- **同族**: [consecutive-port-run.md](consecutive-port-run.md) —— 连号候选段整段自验(取号侧的另一半); [../ops/port-kill-prod-instance.md](../ops/port-kill-prod-instance.md) —— 端口"有主"的核实纪律。
