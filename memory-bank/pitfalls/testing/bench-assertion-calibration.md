# 基准/性能阈值断言未留标定环境声明与并行负载因子余量

> 摘要: 性能阈值断言在**两种非标定环境**下系统性假红 —— ①覆盖率插桩(pytest-cov 追踪)使冷路径膨胀 ~4.6x, ②xdist 并行负载未留余量使 p95 恰超线 0.7% —— 流量图 A4 基准同族两例(T5 tripwire 400ms / T8 冷态 1500ms 线), 修法是「标定环境声明 + 模块级 skipif + 余量放宽」, 不是抬线掩盖。
> 触发: 基准电池, bench, 阈值断言, tripwire, p95, 性能断言, 插桩, pytest-cov, 覆盖率膨胀, 并行, xdist, 负载因子, 标定环境, 冷态, 温态, 膨胀
**Refs:** memory-bank/tasks/26-11-15-webui-traffic-root-revamp.md

## 本篇只回答

性能/基准类阈值断言(tripwire、p95 上限、冷态一次性线)在插桩环境与并行负载下为什么假红、怎么判别、怎么修 —— 同族两例(2026-11-17 流量图根修 S2/S4)的完整判别与处置。

### 插桩与并行让性能阈值假红: 隔离绿、全量红 ≠ 真回归

- **触发**: 写了性能阈值断言的基准电池(如「冷态 <1.5s」「组图空闲 tripwire 400ms」), 之后跑 `test.full`(带 pytest-cov 插桩)或 `test.quick`(xdist -n 8 并行, 提交闸门)时红。两例实测: ① T5 组图空闲 tripwire 400ms —— 隔离实测 217ms 看着有余量, 8 worker 并行 p95 打出 402.71ms 超线 0.7%; ② T8 A4 冷态 1500ms 线 —— 隔离 `--no-cov` 绿 345-380ms, test.full 插桩下 1581-1724ms 系统性红(4/4 次), 且 T5-T7 的提交闸门(test.quick --no-cov)从未测到, 拖到 S4 全量才爆。
- **判别**: **隔离复跑定标** —— 单进程空载、无插桩(`test.one` / `pytest --no-cov -p no:randomly` 该条)跑同一断言: 隔离绿 + 全量/并行红 = 标定环境错位(假红), 不是真回归。两个膨胀源特征不同: 插桩膨胀**大且稳定**(本例 ~4.6x, 冷路径/IO 型被放大最多 —— 与 perf-measurement.md「膨胀不是均匀的」同律), 并行膨胀**小且恰在阈值边缘**(0.7% 级, 时有时无 flaky 形态)。若隔离也红才是真性能回归。
- **处置**: 三件套, 顺序固定: ①**声明标定环境** —— 模块 docstring 写明「阈值只在无插桩/空载环境有效」与膨胀倍数实测; ②**插桩环境模块级 skipif** —— `pytest.mark.skipif(coverage.Coverage.current() is not None, reason=...)` 单点放模块顶部(带 `# owner:` 行, 见守阵), A4 阈值断言只在标定环境跑; **不要靠抬线兼容插桩环境** —— 抬线会让断言在正常环境失真(阈值变成 4.6x 后的真值上限, 判据强度全失); ③**并行余量留足** —— 阈值线按「隔离实测 × 并行因子」放宽(本例 400→600ms, 隔离实测的 ~2.75x, 对 25.6s 修复前基线仍有 42x 判别力), 因子取实测并行 p95 与隔离值的比值再留裕度, 不拍脑袋。
- **守阵**: `tests/test_platform_tolerance_guards.py::test_repo_skipif_all_have_reason_and_owner`(全仓 skipif 必带 reason + owner, 首跑即红一条兜住漏注释); bench 电池自身 docstring 的标定环境口径(`tests/test_traffic_qb_bucket_cache_perf.py`)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
