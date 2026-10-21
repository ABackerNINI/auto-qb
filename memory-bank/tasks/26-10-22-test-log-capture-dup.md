# 26-10-22-test-log-capture-dup — 测试日志捕获器 7 份实现收敛 helpers.capture_logs 单点

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 用户指派认领 issue 26-10-21-0502-refactor-test-log-capture-dup: 7 份同语义测试日志捕获器(helpers/webui_helpers/hr_service/hr_worker/modules_p6/speed_curve/traffic_sample)全部收敛到 helpers.capture_logs 单点, 纯测试改动零源码风险; 全量测试数字见 kb.baseline(基线切片 26-10-22-0409)。
**Topics:** test-log-capture-dup
**Refs:** memory-bank/issues/26-10-21-0502-refactor-test-log-capture-dup.html, memory-bank/pitfalls/testing/log-capture.md, memory-bank/testing/baselines/26-10-22-0409-test-log-capture-dup.md

## 原始请求

1. 用户: 「认领并修复 memory-bank/issues/26-10-21-0502-refactor-test-log-capture-dup.html」(显式指派, 认领动作合法)。

## 思考过程与决策

- **收敛方向按 issue 建议**: helpers.capture_logs 已是 pitfall `testing/log-capture` 指定的唯一单点(records/messages/text 三视图 + 恢复 level/propagate), 无需升级接口, 7 处调用侧改调即可。
- **分歧适配**: module_log/service_log/worker_log 返回 messages 列表 → `cap.messages`; p6 的 `_ModuleLogCapture` 返回 records → `cap.records`; speed_curve/traffic_sample 的 StringIO `.text` → `cap.text`(join 同语义, count/in 断言不变); speed_curve 的 `info_count()` → `cap.text.count("本轮不覆盖")`。
- **propagate 差异**: 旧 p6/speed_curve/traffic_sample 捕获不动 propagate, capture_logs 会临时关 propagate —— 只减少 root 噪音输出, 无测试断言 root 输出, 行为等价。
- **不动 test_tray._capture_on_module_logger**: 它包装调用方自备 handler(probe), 与 capture_logs「自建 handler 收 messages」不同语义, 不在 issue 7 处之列。
- 纯 tests/ 改动, src/ 零触碰。

## 实现计划

1. 置 issue In Progress + 填 doc-refs 认领链 + 重建索引。
2. 删 6 处本地实现(webui_helpers/module_log+_ListLogHandler · hr_service/service_log · hr_worker/worker_log · p6/_ModuleLogCapture+_RecHandler · speed_curve/_CurveLogCapture · traffic_sample/_ModuleLogCapture), 全部调用点改调 capture_logs(含 import 增删与 io 依赖清理)。
3. 跑 7 个受影响测试文件 → test.full 全量 + 基线切片。
4. issue 置 Done(写实测数字) + kb.wrap + kb.index 收尾。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 认领: issue In Progress + doc-refs + kb.index | Done(2026-10-22) |
| S2 | 6 处本地捕获器删除 + 33 处调用点改调 capture_logs | Done(2026-10-22) |
| S3 | 受影响 9 文件子集先跑 + test.full 全量 + 基线切片(数字见 kb.baseline) | Done(2026-10-22) |
| S4 | issue Done + 收尾 DoD(kb.wrap/kb.index) | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

- 用户显式指派认领 issue 26-10-21-0502-refactor-test-log-capture-dup。复验(2026-10-22): 7 处锚点全部仍在(行号自取证基线 cecbe4a9 有漂移, helpers 1132→1030 / webui_helpers 443→450 / hr_service 1944→1937 / hr_worker 722→712 / modules_p6 60→67 / speed_curve 158→164 / traffic_sample 300→299)。
- 全仓 grep 确认 6 个待删符号无 issue 清单外引用(e2e/src 零命中); test_tray._capture_on_module_logger 语义不同(包装调用方 handler), 不在收敛面。
- 立档阈值 #2 命中(改动 ≥3 源文件, 预计 7 个 tests/ 文件)。

- 2026-10-22 04:11 7 份测试日志捕获器收敛 capture_logs 单点: 删 6 处本地实现 + 33 处调用点改调, test.full 3996 passed + 2 skipped 覆盖率 99% 过闸
