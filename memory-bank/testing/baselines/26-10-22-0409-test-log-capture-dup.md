# 3996 passed, 2 skipped —— 3996 passed —— 测试日志捕获器 7 份实现收敛 capture_logs 单点后全量基线

> 摘要: 3996 passed —— 测试日志捕获器 7 份实现收敛 capture_logs 单点后全量基线
> 基线时间: 2026-10-22 04:09
**Refs:** memory-bank/tasks/26-10-22-test-log-capture-dup.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3996 passed, 2 skipped in 137.88s**
- 覆盖率: TOTAL **99%**(20981 语句 / 98 未覆盖 / 7088 分支 / 101 partial, 99.28%, 过闸)

逐条口径注记:

- 首跑曾 1 failed(`test_docs_forms.py::test_claim_chain_is_bidirectional`) —— 认领链单向: 任务档案
  `**Refs:**` 引了坑档 `pitfalls/testing/log-capture.md` 但坑档未反向声明本档案; 坑档 Ref 行补档案路径后
  复跑转绿, 非测试代码问题
- 受影响 9 个测试文件子集先跑一轮 **514 passed**(test_hr_service/test_hr_worker/test_modules_p6/
  test_speed_curve/test_traffic_sample/test_web_keys/test_web_commands/test_web_longtail/test_logging)
- 本轮未新增/删除测试函数(机械收敛); passed 数与上一基线持平
- 本轮未跑 e2e(改动仅 tests/ 内的日志采集接线, 无前端/接口行为变化)

## 本改动面

- `tests/helpers.py` —— 零改动(单点已在, `.records/.messages/.text` 三视图直接承接全部调用形状)
- `tests/webui_helpers.py` —— 删 `module_log` + `_ListLogHandler`(及随之不再使用的 `import logging`)
- `tests/test_hr_service.py` —— 删 `service_log` + `_ListLogHandler`; 5 处调用改调 `capture_logs("auto_qb.hr.service")`
- `tests/test_hr_worker.py` —— 删 `worker_log` + `_ListLogHandler`; 1 处调用改调 `capture_logs("auto_qb.hr.worker")`
- `tests/test_modules_p6.py` —— 删 `_ModuleLogCapture` + `_RecHandler`; 1 处调用改调 `capture_logs("auto_qb.core.qbmanager")`(`cap.records` 形状不变)
- `tests/test_speed_curve.py` —— 删 `_CurveLogCapture`; 3 处调用改调 `capture_logs("auto_qb.core.modules.speed_curve_mod")`; 10 处 `cap.info_count()` 改 `cap.text.count("本轮不覆盖")`
- `tests/test_traffic_sample.py` —— 删 `_ModuleLogCapture`; 14 处调用改调 `capture_logs("auto_qb.core.modules.traffic_sample_mod")`(`cap.text` 形状不变); 清理随之不再使用的 `import io` / `import logging`
- `tests/test_web_keys.py` / `tests/test_web_commands.py` / `tests/test_web_longtail.py` —— import 改从 `helpers` 取 `capture_logs`; 11 处调用改调(`module_log` 的 messages 列表 → `cap.messages`)
- `memory-bank/pitfalls/testing/log-capture.md` —— 处置段补 2026-10-22 清偿注记(7 份副本已删, 全仓无第二份模块 logger 采集器)
- 未授权不做: commit/push
