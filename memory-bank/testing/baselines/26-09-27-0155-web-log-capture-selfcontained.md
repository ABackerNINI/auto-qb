# 1685 passed + 1 skipped / 0 failed —— web 生命周期测试日志采集自足化(caplog → 模块 logger)

> 摘要: 修 CI 偶发红(`test_web_loop_exception_handler_downgrades_connection_reset` 抓到 0 条日志):
> 根因不是实现缺陷, 是测试对全局日志状态的隐式依赖(root 出厂 WARNING 拦 INFO + xdist 动态调度
> 下同 worker 邻居不定)。`tests/test_web.py` 新增 `_grab_web_logger` 自足采集器(挂模块 logger +
> 显式 setLevel + finally 恢复), 5 个测试切换(noise 三兄弟 / started_message / port_taken)。
> 生产代码不动。坑与触发面见 pitfalls/testing/stubs-sim.md(复发 +1)。
> 基线时间: 2026-09-27 01:55
> 档案: 26-09-27-0155-test-web-log-capture-selfcontained(activeContext 切片, 未达立档阈值)

- **测试增量**: 总数不变(1685+1)。5 个测试去 caplog 化改自足采集: 断言对象从 `caplog.records`
  改为自建 handler 的 records, 级别靠显式 `setLevel`; `started_message` 原先依赖 test_logging
  泄漏的 root level 才能过(单跑必挂), 现已自足。
- **验证**: 组合跑 `test_logging.py + web 日志组`(-n0, 修复前 started_message 必挂)12 passed;
  本地全量 2 轮 + CI 同款 test.full 均绿。

TOTAL 91%(11209 语句 / 815 未覆盖 / 3720 分支 / 330 partial;
test.full 22.3s(单采样, -n4 并行); 另 2 轮 23.4~23.6s; 覆盖率口径见 [../baseline.md](../baseline.md))。

合并 origin/develop c4bb0fa(4 笔)后重验(-n4 全量): 1683 passed + 1 skipped + 2 failed ——
2 failed 全部为远端 0f98e7a 落盘的 `26-09-26-2345-plan-commands-shipflow-v2.html` 缺
doc-topic/doc-status/doc-added/doc-updated 四项 meta(test_docs_forms 两守卫), stash 本改动
在远端 HEAD 上复测同样红, 与本改动无关(待用户决定: 入池或补 meta)。
