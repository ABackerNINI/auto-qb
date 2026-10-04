# 26-10-05-test-log-capture-helper — 测试日志捕获统一 helper (认领 issue 26-10-04-2311)

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05
**Topics:** test-log-capture-helper
**Summary:** 认领 issue 26-10-04-2311 (QbManager 测试组合下 caplog 恒空: LoggingModule 装配调 setup_logging 清根 handlers, caplog 挂在根上的 handler 一并被摘)。拍板方向一 (测试侧统一范式, src/ 零改动): helpers.capture_logs 统一实现 (挂模块 logger + 显式 setLevel + 关 propagate + finally 恢复) + test_ops.py 薄适配 (删本地类, 4 处用例零改动) + test_logging.py 守阵 2 条 (make_manager 构造后捕获仍有效 + 对照断言 caplog.text 恒空钉死坑存在性, 红验通过)。test.full 2532 passed + 4 skipped / 99% (基线 26-10-05-0058)。

**Refs:** memory-bank/issues/26-10-04-2311-test-caplog-qbm-setup-logging.html, memory-bank/testing/baselines/26-10-05-0058-log-capture-helper.md, memory-bank/pitfalls/testing/log-capture.md

## 原始请求

用户: 认领 issue: 26-10-04-2311-test-caplog-qbm-setup-logging.html (test 类便签档, 现象 = QbManager 测试组合下 pytest caplog.text 恒空; issue 建议 "认领时先复验再拍板" 方向一/方向二)。

## 思考过程与决策

- 复验 (2026-10-05 00:51): 三锚点仍命中 —— `src/auto_qb/infra/logging.py:98` `logger.handlers.clear()` / `src/auto_qb/core/modules/logging_mod.py:47` 装配调用 / `tests/test_ops.py:79` 既有绕过范式; 机制成立。另发现全库 8 处测试文件各自手写同款局部捕获器 (test_ops / test_grouping×2 / test_rule_base / test_speed_curve×2 / test_tracker / test_ui / test_web×2), 坑档 `pitfalls/testing/log-capture.md` 已记且复发 2 次。
- 拍板方向一 (统一范式上移 helpers.py): 方向二 (setup_logging 不清根) 要动生产日志语义 —— 清根承担热重载重挂防重复 handler (LoggingModule.apply 变更段再走 _configure) 与独占 root 拦第三方噪音职责; 且其上方 `basicConfig` 挂的 handler 不清会双份输出, 影响面与收益不成比例。与坑档既有处置方向一致。
- 接口形状: capture_ops_logs 既有 4 处用例在 `with` 块外仍断言 `logs` (消息字符串列表) ⇒ helper 的 `.messages/.records` 必须是持续累积的**同一列表对象** (emit 时同步 append, 非 property 派生); test_ops 保 3 行薄适配 yield `cap.messages`, 既有用例零改动。
- 默认挂点: `capture_logs` 默认挂 `"auto_qb"` 收全树; 子 logger 有效等级由祖先决定 —— 构造过 QbManager 的场景 auto_qb 已被 setup_logging 设为 DEBUG 直接可用, 未构造的场景挂具体模块 logger 更直接 (helper 替目标 logger 显式 setLevel); 限界 (只收 auto_qb.* 树, 第三方 logger 收不到) 写进 docstring。约定单点 = capture_logs docstring (issue 建议的 "tests 头部约定" 落点)。

## 实现计划

- tests/helpers.py: `_LogCapture` (records/messages 持续累积 + text 派生) + `capture_logs(logger_name, level)` contextmanager
- tests/test_ops.py: 删本地 `_OpsLogCapture` + 原实现, 换薄适配
- tests/test_logging.py: 守阵 `test_capture_logs_survives_qbmanager_setup_logging` (make_manager 后捕获仍有效 + 对照断言 caplog.text 恒空, 前提失效即红提示重评范式) + `test_capture_logs_restores_logger_state` (退出恢复 level/propagate/handlers); 头部测试计划同步
- 验证: 红验 (sed 禁用 addHandler → 2 守阵红 → 还原绿) → 靶向 → 全量
- 回写: issue 状态流转 (In Progress → Done + 修法/验证/数字) · 坑档处置段更新 · 基线切片 · 本档案

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| helpers.capture_logs 统一实现 | Done |
| test_ops.py 薄适配 | Done |
| test_logging.py 守阵 2 条 | Done |
| 红验 + 靶向 + 全量基线 | Done |
| 回写 (issue Done / 坑档 / 基线 / 档案) | Done |
| 其余 7 处局部捕获范式消重 | Open (留待后续 refactor, 范围守恒) |

## 进度日志

- 2026-10-05 00:51: 认领 + 复验三锚点全命中, 拍板方向一。
- 2026-10-05 00:58: 实施完成全绿 —— 红验 (2 守阵红/还原绿); 靶向 test_logging + test_ops 38 passed (3.49s); test.full **2532 passed + 4 skipped / 99% / 26.98s** (相对上基线 2530+4: +2 = 新守阵), 基线切片 26-10-05-0058-log-capture-helper。issue 置 Done, 坑档处置段更新。
