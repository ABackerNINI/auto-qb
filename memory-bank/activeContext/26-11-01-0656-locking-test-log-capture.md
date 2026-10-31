# locking-test-log-capture

> 摘要: 修复 test_locking flaky: test_release_file_lock_none_and_failure_logger 手写局部捕获器漏显式 setLevel(root 默认 WARNING 时 DEBUG 被 logger 层拦, 单跑/净树恒挂, 全量靠邻居泄漏 root level 偶发绿, xdist 邻居不定即红); 改走统一 capture_logs, 断言语义不变; 生产侧 release_file_lock 本就正确; 单跑+双文件 20 条全绿, 全量 4375 passed + 2 skipped 见基线切片 26-11-01-0655; 坑档 log-capture 复发 2->3
> 最后活动: 2026-11-01 06:56
**Refs:**

**R0(2026-11-01 06:56):** 修复 test_locking flaky: test_release_file_lock_none_and_failure_logger 手写局部捕获器漏显式 setLevel(root 默认 WARNING 时 DEBUG 被 logger 层拦, 单跑/净树恒挂, 全量靠邻居泄漏 root level 偶发绿, xdist 邻居不定即红); 改走统一 capture_logs, 断言语义不变; 生产侧 release_file_lock 本就正确; 单跑+双文件 20 条全绿, 全量 4375 passed + 2 skipped 见基线切片 26-11-01-0655; 坑档 log-capture 复发 2->3
