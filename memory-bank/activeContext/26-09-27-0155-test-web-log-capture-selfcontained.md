# web 生命周期测试的日志采集自足化(CI 偶发红修复)

> 摘要: CI(GitHub Actions, ubuntu, py3.12/3.13)偶发报 `test_web_loop_exception_handler_downgrades_connection_reset` 断言「断连应记为一行 INFO」抓到 0 条。定案: 非实现缺陷, 是测试对**全局日志状态**的隐式依赖 —— ① root 出厂 level=WARNING, auto_qb.web 未显式设级时 INFO 被拦成 no-op(「WEB UI 已启动」测试单跑必挂, 全量靠 test_logging 泄漏的 root level 才过, 是确定性脆弱); ② xdist(-n4)动态调度下同 worker 邻居每次不同, 依赖全局状态的断言偶发落空, 3.12/3.13 都见、本地难复现。
> 最后活动: 2026-09-27 01:55

- **修复**(26-09-27, 1 文件): `tests/test_web.py` 新增 `_grab_web_logger(min_level)` —— 挂 `auto_qb.web` 模块 logger + 显式 setLevel + finally 恢复的自足采集器(对 root level/handlers/传播链免疫); 5 个测试从 caplog 切换到它: noise 三兄弟(downgrades/throttled/delegates)、`started_message`、`port_taken`。生产代码不动(lifecycle.py 的日志行为在生产正确)。
- **知识库**: 坑记入 `pitfalls/testing/stubs-sim.md`「make_manager 清 root handlers ⇒ caplog 抓不到」条目, 复发 +1(新触发面: root level 伤害面 + xdist 偶发); 基线切片 26-09-27-0155。
- **完成, 待用户验证/提交**: test.full 全绿(1685 passed / 91% / 22.3s, 与上条基线一致); 组合跑(test_logging + web 日志组)修复前必挂、修复后 12 passed。
- **遗留(未修, 属套件级)**: 其余几十处 caplog 测试理论上同受 xdist 邻居影响, 但无实锤个案 —— 不在本轮范围, 再遇 CI 偶发红(尤其"日志断言恒空"型)先按本坑判别排查。
