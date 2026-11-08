# xdist 高载下进程内假服已建连被中止(WinError 10053)—— 偶发红先分「主断言段/对照段」

> 摘要: 测试自起 `http.server.ThreadingHTTPServer(("127.0.0.1", 0))` 当假服, test.full(并行 + 覆盖率插桩)高载下, **真客户端打真本地服**的段偶发 `ProtocolError: Connection aborted, ConnectionAbortedError(10053, '你的主机中的软件中止了一个已建立的连接')` —— 0 端口无抢号问题(fixed-port / free-port TOCTOU 两族都不沾), 是**已建立的连接被本机中止**。被测行为的主断言往往此时已全过, 红在末段"机制自证/红验"的对照组; 单跑绿 + 复跑全量绿即定性偶发, 别当回归去修测试。
> 触发: 10053, ConnectionAbortedError, Connection aborted, 你的主机中的软件中止了一个已建立的连接, ProtocolError, ThreadingHTTPServer, 进程内假服, 本地假服, 真客户端, 对照组, 红验回放, 机制自证, xdist, 并行高载, 偶发红, 单跑绿, urlopen, urllib3
**Refs:** memory-bank/tasks/26-11-07-test-legacy-review4-scripts-fix.md

### 2026-11-07 实证: qb_capture --dry 真零请求红验对照组红, 主断言已过

- **触发**: `tests/test_legacy_review4_scripts.py::test_qb_capture_dry_true_zero_requests` —— 同进程起
  ThreadingHTTPServer(("127.0.0.1", 0)), 前段跑 --dry 零请求主断言(全过), 末段对照组**真构造 Capture**
  打 4 个并发 login(机制自证, 证明计数器非空转); test.full 偶发红在对照组的
  `urllib3.exceptions.ProtocolError: ('Connection aborted.', ConnectionAbortedError(10053, ...))`。
  同批顶 test.full 曾全绿、单跑该 nodeid 绿、紧接复跑全量全绿(5649+2)。
- **判别**: 三件齐才定性(与 [parallel-run.md](parallel-run.md)「偶发红」同纪律, 先留 traceback):
  ①栈落在 urllib3/socket 读响应、错误码 **10053**(本机软件中止**已建连**) —— 不是 ConnectionRefused
  (抢号/没起服)、不是 Timeout(死循环)、也不是断言值不等; ②红的位置在"真客户端打真本地服"的
  对照/自证段, 与被测行为断言无交集; ③单跑 nodeid 绿 + 全量复跑绿。
- **处置**: 复跑一次全量取绿数字, 把首跑红(nodeid + 10053 指纹 + 红在哪一段)写进坑档与收尾切片,
  **不改测试、不放宽断言、不加无脑重试**; 若同点 ≥2 次复现再立针对性加固(对照组并发改串行 /
  受控重试), 那是代码改动走正常任务流, 不在收尾轮顺手改。
- **同族辨析**: [parallel-run.md](parallel-run.md)「偶发红: 自选端口的用例」是 bind 前 TOCTOU 抢号
  (指纹 ConnectionRefused / 打到别人的服); [fixed-port-test-collision.md](fixed-port-test-collision.md)
  是固定端口撞号 —— 本条三者机制都不同: 连接**已建立**后才被中止, 指纹是 10053, 别混。
