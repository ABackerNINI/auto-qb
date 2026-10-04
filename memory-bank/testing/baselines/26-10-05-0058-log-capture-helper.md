# 基线切片 26-10-05-0058 — 日志捕获统一 helper (issue 26-10-04-2311 认领收尾)

> 摘要: 认领 issue 26-10-04-2311 (QbManager 测试组合下 caplog 恒空: setup_logging 清根 handlers 连 caplog handler 一起摘)。
> 拍板方向一 (测试侧统一范式, 生产代码零改动): tests/helpers.py 新增 capture_logs (挂模块 logger, 对 root 清理/等级/传播链全免疫)
> + test_ops.py 改 3 行薄适配 (删本地类, 4 处用例零改动) + test_logging.py 新增守阵 2 条 (含对照组断言 caplog.text 恒空钉死坑存在性)。
> 基线时间: 2026-10-05 00:58

**Refs:** memory-bank/issues/26-10-04-2311-test-caplog-qbm-setup-logging.html, memory-bank/tasks/26-10-05-test-log-capture-helper.md, memory-bank/pitfalls/testing/log-capture.md, memory-bank/testing/baseline.md

- 分支: develop @ 2223c853 (+ 本轮未提交改动: tests/helpers.py / tests/test_ops.py / tests/test_logging.py / issue HTML / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2532 passed + 4 skipped, 26.98s (引擎计 27.6s), 覆盖率 TOTAL 99%**
  (14868 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向 (test_logging + test_ops): **38 passed**(3.49s); 红验: sed 禁用 helper 的 addHandler → 2 守阵红 → 还原绿 (断言非恒真)
- 相对上基线 (26-10-04-2256: 2530 passed + 4 skipped / 99% / 36.76s): passed **+2** = 本轮新守阵
  (test_capture_logs_survives_qbmanager_setup_logging / test_capture_logs_restores_logger_state); skip 集合不变 (Windows 侧 4 条 POSIX 专属)。
- 改动面: tests/helpers.py(capture_logs 统一实现 + docstring 写明别用 caplog) · tests/test_ops.py(薄适配) · tests/test_logging.py(守阵 2 条)。**src/ 零改动**。
