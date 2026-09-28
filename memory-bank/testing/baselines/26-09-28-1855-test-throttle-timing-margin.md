# 1828 passed / 3 skipped —— throttle 守阵计时下界留余量(Windows 假红修复)

> 摘要: `test_run_loop_throttles_without_stop_event` 断言 `elapsed >= 0.05` 改 `>= main_tick - 0.02`(Windows 等待按 15.6ms 定时器刻度取整, 50ms 实测可提前到 46.8ms=3 刻度; 空转是微秒级, 余量不损失判别力)。调查定性为真假红非多线程竞争, 同根双 issue(26-09-20-0952 / 26-09-22-2052)关闭; `testing/baseline.md` 的「deselect 该用例取稳态数字」常驻警告随修复删除, 此后全量数字**含**该用例。教训沉淀 `pitfalls/testing/timing-tolerance.md`。
> 基线时间: 2026-09-28 18:58
> 档案: 切片 26-09-28-1855-test-throttle-timing-flaky

- test.full: **1828 passed / 3 skipped**, TOTAL **91%**(12576 语句 / 917 未覆盖 / 4246 分支 / 390 partial), 耗时 22.46s —— 合流远端 5bc43784(HR 排除 + test_config 去重)后新基线重测, 数字与前基线(26-09-28-1840)**完全一致**(本修复仅改断言余量, 对覆盖率与用例数零影响)。
- 修复后压测: 单用例 3/3 绿 + 整文件 3/3 绿(45 passed); 合流前同机 24 单跑/4 全量 --no-cov 全绿(当日 regime 未复现, 与档案 09-22 的 46ms 假红为不同定时器 regime)。
