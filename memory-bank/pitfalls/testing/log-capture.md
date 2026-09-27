# 日志断言的自足采集

> 摘要: caplog 与全局日志状态是跨测试共享的 —— 断言日志要挂模块 logger 自建 handler + 显式 setLevel, 不碰 caplog。
> 触发: caplog, 日志断言, 日志级别, root handlers, root level, xdist, 偶发, CI 红, setup_logging, make_manager

### caplog 挂在 root 上、依赖全局日志状态 ⇒ 断言偶发落空或恒空

- **触发**: 用 `caplog`(或任何依赖 root 传播的采集)断言 `auto_qb.*` 的日志级别 / 内容。
- **判别**: 三层伤害面: ① `make_manager` / `setup_logging` 的 `root.handlers.clear()` 把 pytest
  挂在 root 上的采集 handler 一并清掉 ⇒ "日志断言恒空"(不是没打日志); fixture 里建 manager 没事
  (call 阶段重挂), 用例体内建中招。② root 出厂 level=WARNING, logger 未显式设级时 INFO 调用被拦成
  no-op —— 挂在模块 logger 上的 handler 也收不到("WEB UI 已启动"测试单跑必挂、全量靠别的测试
  泄漏的 root level 才过)。③ xdist(-n4)动态调度下同 worker 邻居每次不同, 以上状态被邻居改变就
  **偶发落空**(CI 实测 2026-09-27: 噪音日志测试抓 0 条, py3.12/3.13 都见, 本地难复现)。
- **处置**: 挂**模块 logger** 自建 handler + **显式 setLevel** + `finally` 恢复原 level 与 handlers
  —— 对 root 级别 / handlers / 传播链全部免疫。守阵: `test_web.py::_grab_web_logger`
  (web 生命周期 5 个测试已切换)。不要因此放弃日志断言 —— 日志级别即通知语义。
- **复发**: 1(原记于 stubs-sim「make_manager 清 root handlers」条, 2026-09-27 外迁至此。
  为什么没命中: 旧判别只写"用例体内建 manager"这层, 没料到 root level 与 xdist 两个更底层的伤害面。)
