# 测试日志捕获统一 helper — issue 26-10-04-2311 认领完成 (Done)

> 摘要: 认领 issue 26-10-04-2311 (QbManager 测试组合下 caplog 恒空: LoggingModule 装配调 setup_logging 清根 handlers, caplog 挂在根上的 handler 一并被摘)。拍板方向一 (测试侧统一范式, src/ 零改动 —— 方向二要动 setup_logging 独占 root / 热重载防重复语义, basicConfig handler 不清会双份输出, 影响面不成比例): tests/helpers.py 新增 capture_logs (挂模块 logger + 显式 setLevel + 关 propagate + finally 恢复; .records/.messages/.text) + test_ops.py 薄适配保消息列表形状 (既有 4 处用例零改动) + test_logging.py 守阵 2 条 (make_manager 构造后捕获仍有效 + 对照断言 caplog.text 恒空钉死坑存在性; 红验通过)。test.full 2532 passed + 4 skipped / 99% (基线 [26-10-05-0058](../testing/baselines/26-10-05-0058-log-capture-helper.md))。坑档 [log-capture.md](../pitfalls/testing/log-capture.md) 处置段更新指向统一入口。
> 最后活动: 2026-10-05 01:02

**Refs:** memory-bank/issues/26-10-04-2311-test-caplog-qbm-setup-logging.html, [任务档案](../tasks/26-10-05-test-log-capture-helper.md)(Done)

## 现状

- issue Done, 认领链闭合。**新用例日志捕获一律 `helpers.capture_logs`, 别用 caplog, 别再手写局部捕获器** (约定单点 = capture_logs docstring)。
- 其余 7 处既有局部捕获范式 (test_grouping / test_rule_base / test_speed_curve / test_tracker / test_ui / test_web) 仍在原地工作, 是否消重属后续 refactor, 未纳入本轮 (范围守恒)。
- 改动未提交: tests/helpers.py / tests/test_ops.py / tests/test_logging.py + memory-bank 回写件, 等用户显式提交指令。
