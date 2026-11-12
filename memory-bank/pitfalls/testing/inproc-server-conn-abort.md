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
- **复发**: 1(2026-11-09, kb 闸门 S5 收尾轮) —— `test.full` 首跑红在同一 nodeid(5,871 passed + 1 failed), 单跑该 nodeid 绿、全量复跑绿; 首跑只留 tail 未捕到完整 traceback, 按「红点 nodeid + 单跑绿 + 复跑绿」归入本族。**为什么没命中**: 本轮检索面是 kb 闸门 / timekit, 进程内假服族不在开工路由面内, 首个踩坑动作就是跑全量。
- **复发**: 2(2026-11-12, issue [26-11-12-0318](../../issues/26-11-12-0318-test-testing-parallel-flaky.html)) —— 五轮全量三轮各闪一次: 提交闸门轮与 S2 首轮闪同一 nodeid(本条族), 另一轮闪 traffic [1m](探针污染族, 另立坑档 global-open-probe-pollution); 单跑均绿按指纹归族。**处置兑现**: 本坑档预告的「同点 ≥2 次复现立针对性加固」到期 —— 对照组落地受控重试(每轮新假服+独立台账, 只对 RequestException 族, 耗尽上抛; SystemExit 等确定性失败不重试), 守阵三条腿红验; 独占 bind(26-11-11-0114)修的是双绑串线, 与本条已建连中止是两个机制, 并存不冲突。**为什么没命中**: 11-09 复发时按坑档处置「复跑取绿不改码」走(复发次数未到加固线), 11-12 第三、四次冒头才达线, 属阈值按设计生效而非漏读。
