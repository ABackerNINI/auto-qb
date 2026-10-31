# 3205 —— hr 线程生命周期骨架抽(R3, dup-code-audit 第 9 条)执行基线

**Refs:** memory-bank/tasks/26-10-11-backend-hr-dup-code-fix.md

> 摘要: 任务档案 [26-10-11-backend-hr-dup-code-fix](../../tasks/26-10-11-backend-hr-dup-code-fix.md) R3 段。用户「认领并修复」第 9 条 `hr-thread-lifecycle-boilerplate-dup`(R1/R2 按保守口径暂缓, 用户显式指派 lift)→ 抽 `HrThreadHandle`(`hr/threadlifecycle.py`) 骨架单点(幂等 start + stop/join(timeout) + 退出/未退出日志 + started), 机制差异(Condition vs shutdown)经 request_stop 回调, worker/server 两调用点降为句柄调用, 日志文案字节同**零行为变化**. 改动面: `hr/{threadlifecycle(新),worker,server,__init__}.py` + 2 测试文件(worker 5 用例 `_thread` 钉改 `_handle._thread` · server stub 用例改真句柄假 server+stuck thread).
> 基线时间: 2026-10-15 03:16

上一基线: memory-bank/testing/baselines/26-10-14-1615-webui-peers-speed-track-removal.md

## 验收数字

- `test.full`: **3205 passed + 4 skipped, 0 failed** / 覆盖率 `TOTAL 16840 159 5728 142 99%`(98.64%, 过 98% 闸门).
- 耗时: pytest 98.47s(单次采样, 全绿跑; 口径见 baseline.md).
- 单文件前置跑: `test.one` hr 两文件 101 passed(改完先跑两文件绿再收口).
- Linux 侧未重测(改动为行为等价收口, 无平台分支; 线程骨架两侧同源 stdlib threading).

## 本波改动面

- **单点新增**: `hr/threadlifecycle.py` `HrThreadHandle`(幂等 start / stop(request_stop 回调 -> join(timeout) -> 按退出/未退出记 log -> 退出清/未退出留句柄) / started; logger 身份经参数).
- **委托收口**: `hr/worker.py`(start/stop/started 降为句柄调用, cancel_all 与 cond 置停止位 stay in stop per 告口纪律) / `hr/server.py`(`HrEndpointHandle` 持句柄 + `stop(timeout)` 全收口 shutdown 注入 + server_close 保持; `HrChannelServer.stop` 降为清句柄+委托) / `hr/__init__.py` 模块分工 docstring +1 行.
- **测试同步(2 文件)**: `test_hr_worker.py` 5 用例 `_thread` poke → `_handle._thread`; `test_hr_server.py` `test_stop_timeout_and_close_error_are_contained` stub 改真 `HrEndpointHandle`(SimpleNamespace 假 server + stuck `HrThreadHandle`) —— close-error containment 仍走真 code path.
- **回写**: 第 9 条 issue(状态 Done/实际修法/认领链 doc-refs) + 任务档案(R3 段 + 子任务表 + 待办改) + activeContext 切片更新 + `kb.index` 重建 + 本基线切片.

## 已知偏差 / 移交

- 无行为面偏差(收口表意等价; 日志文案四条字节同; two micro-diffs audited in archive R3: server stop 日志 order swap(close-error debug vs exit-status) · worker start 线程起 out of cond —— 单写线程不变, 等价).
- 移交: `hr-store-recover-lock-family-dup`(与轮 18 合并) / `hr-fetchable-dead-config`(待拍板)留 `Open`; webui 半(token R15-C01 / 站点派生 R15-C03)随轮 15.
