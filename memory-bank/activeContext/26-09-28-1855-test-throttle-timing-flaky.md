# 测试假红修复: throttle 守阵计时下界余量

> 摘要: 用户报 throttle 测试 Windows 偶发假红, 不确定是假红还是多线程竞争。调查定性: **真假红**(Windows 等待粒度按 15.6ms 定时器刻度取整, 46ms=3 刻度), **非竞争** —— 阻塞路径单线程、`tick_due` 时间门控保证提前唤醒只会多空迭代。修法: `tests/test_qbmanager.py` `test_run_loop_throttles_without_stop_event` 断言 `elapsed >= 0.05` 改 `>= main_tick - 0.02`。两条同根 Open issue(26-09-20-0952 / 26-09-22-2052)已改 Done, `_doc-map.md` 已再生成, `testing/baseline.md` 失效警告已删, 新坑入 `pitfalls/testing/timing-tolerance.md`。
> 最后活动: 2026-09-28 18:58

## 状态

- 修复与知识库回写已完成; 提交前合流远端 5bc43784(HR 排除 + test_config 去重), 基线切片已在合流后新基线重测(1828 passed / 3 skipped / 91%)。
- 教训沉淀: 计时下界断言留余量(见 pitfalls/testing/timing-tolerance.md), 本切片不再承担细节。
- 顺带: 新切片使 activeContext 触顶(57 > 56), 已按守卫指引把最旧的可归档切片 `26-09-22-2219-docs-readme-rewrite.md` 蒸馏进 `tasks/26-09-15-docs-restructure.md`(完成事实 + 2 条残留待拍板)后删除。
