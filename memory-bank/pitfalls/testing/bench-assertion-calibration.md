# 基准/性能阈值断言未留标定环境声明与并行负载因子余量

> 摘要: 性能阈值断言在**非标定环境**下系统性假红 —— pytest 侧: ①覆盖率插桩(pytest-cov 追踪)使冷路径膨胀 ~4.6x, ②xdist 并行负载未留余量使 p95 恰超线 0.7%(流量图 A4 基准同族两例, 修法 = 标定环境声明 + 模块级 skipif + 余量放宽, 不是抬线掩盖); e2e JS 量具侧: ③背景轮询 tick 混进 bench 测量窗(每拍恒回传的 status 触发根重渲+逐行量高)拖穿不含墙钟项的预算, 且引擎演化使累计预算基线悄悄作废(perf.spec A/B 埋点 atlas 两长跑形态红, 修法 = 结构隔离背景轮询 + 分段计数, 判据零放松)。
> 触发: 基准电池, bench, 阈值断言, tripwire, p95, 性能断言, 插桩, pytest-cov, 覆盖率膨胀, 并行, xdist, 负载因子, 标定环境, 冷态, 温态, 膨胀, 长跑, 负载态, gBCR, 预算, 量具窗口, 背景轮询, 轮询 tick, 分段计数, PerformanceObserver, longtask, A/B bench
**Refs:** memory-bank/tasks/26-11-15-webui-traffic-root-revamp.md, memory-bank/issues/26-11-18-0308-test-e2e-perf-ab-metrics-load-red.html

## 本篇只回答

性能/基准类阈值断言(tripwire、p95 上限、冷态一次性线、e2e 渲染量具预算)在插桩环境/并行负载/长跑背景负载下为什么假红、怎么判别、怎么修 —— 同族三例(2026-11-17 流量图根修 S2/S4 两例 pytest 侧; 2026-11-18 perf.spec A/B 埋点一例 e2e JS 侧)的完整判别与处置。

### 插桩与并行让性能阈值假红: 隔离绿、全量红 ≠ 真回归

- **触发**: 写了性能阈值断言的基准电池(如「冷态 <1.5s」「组图空闲 tripwire 400ms」), 之后跑 `test.full`(带 pytest-cov 插桩)或 `test.quick`(xdist -n 8 并行, 提交闸门)时红。两例实测: ① T5 组图空闲 tripwire 400ms —— 隔离实测 217ms 看着有余量, 8 worker 并行 p95 打出 402.71ms 超线 0.7%; ② T8 A4 冷态 1500ms 线 —— 隔离 `--no-cov` 绿 345-380ms, test.full 插桩下 1581-1724ms 系统性红(4/4 次), 且 T5-T7 的提交闸门(test.quick --no-cov)从未测到, 拖到 S4 全量才爆。
- **判别**: **隔离复跑定标** —— 单进程空载、无插桩(`test.one` / `pytest --no-cov -p no:randomly` 该条)跑同一断言: 隔离绿 + 全量/并行红 = 标定环境错位(假红), 不是真回归。两个膨胀源特征不同: 插桩膨胀**大且稳定**(本例 ~4.6x, 冷路径/IO 型被放大最多 —— 与 perf-measurement.md「膨胀不是均匀的」同律), 并行膨胀**小且恰在阈值边缘**(0.7% 级, 时有时无 flaky 形态)。若隔离也红才是真性能回归。
- **处置**: 三件套, 顺序固定: ①**声明标定环境** —— 模块 docstring 写明「阈值只在无插桩/空载环境有效」与膨胀倍数实测; ②**插桩环境模块级 skipif** —— `pytest.mark.skipif(coverage.Coverage.current() is not None, reason=...)` 单点放模块顶部(带 `# owner:` 行, 见守阵), A4 阈值断言只在标定环境跑; **不要靠抬线兼容插桩环境** —— 抬线会让断言在正常环境失真(阈值变成 4.6x 后的真值上限, 判据强度全失); ③**并行余量留足** —— 阈值线按「隔离实测 × 并行因子」放宽(本例 400→600ms, 隔离实测的 ~2.75x, 对 25.6s 修复前基线仍有 42x 判别力), 因子取实测并行 p95 与隔离值的比值再留裕度, 不拍脑袋。
- **守阵**: `tests/test_platform_tolerance_guards.py::test_repo_skipif_all_have_reason_and_owner`(全仓 skipif 必带 reason + owner, 首跑即红一条兜住漏注释); bench 电池自身 docstring 的标定环境口径(`tests/test_traffic_qb_bucket_cache_perf.py`)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

### e2e JS 量具: 背景轮询混进测量窗 + 引擎演化作废累计预算基线

- **触发**: e2e 渲染量具(perf.spec A/B 埋点: 3 轮全量 + 3 轮窗口化直调 vm.refresh, 量 longtask 和与逐行 gBCR 次数)在**长跑形态**(Windows 全量串行 / 容器 testbed --full, 套件后段)红、shard 与短形态绿、prism 孪生同轮绿而 atlas 单红(issue 26-11-18-0308, 2026-11-18)。
- **判别**(trace 缺失时纯静态归因 + 本机分段实测): 两个混淆源叠一起 —— ①**背景轮询 tick 是墙钟敏感的负载源**: 页面轮询 bench 全程照常跑, 而每拍 /api/state 恒回传 status(不受 rid 门控) ⇒ vm.status 赋新对象 ⇒ 根组件重渲 ⇒ updated() 的 _measureRowH 对渲染窗每行发一次 gBCR(签名判定只管作废不管探测) —— 每拍混入 ~tRows 次预算外 gBCR, 预算公式只按渲染轮数计不含墙钟项, 慢机 bench 拉长 ⇒ 拍数变多 ⇒ 拖穿; ②**累计预算基线随引擎演化作废**: 累计口径(6 轮不清零)把「off 侧收尾 rowWin 复原重开窗的迁移探测」也计入, 该项是 26-11-02 后引擎 reprobe 面引入的固定成本(实测 prism ~24 / atlas ~54 次, 与轮数无关、皮肤相关) —— 轮询隔离成纯净窗口后 atlas 仍红(139 > 130)证明预算公式本身已被引擎演化作废, 不是负载毛刺。
- **处置**(顺序固定): ①**结构隔离优先于放宽预算** —— bench 前页面内拆轮询(stopPolling + stopEvents)并影子化 scheduleNext 为 no-op(**bench 轮内直调的 vm.refresh() 尾部会续排下一拍, 不影子化拆了也会被重新 arm**; 影子手法同 W5 的 vm.refresh 影子), bench 后赋回原函数复原; 复原**不能 delete 影子** —— Vue 3 公共实例代理 accessCache 按键缓存查找类型, delete 后不回落 mixin 方法表(实测 TypeError), 赋回保存的原函数。②**分段计数治累计基线作废** —— 计数器在每个 benchRun 开头清零, 判据只看被测语义的直接测量面(P1-3 = on 侧窗口化轮次), off 侧的设计固有迁移成本用 run 尾部 2 rAF 落定在 off 侧不进判据; 这不是放松 —— 真回归全部落在 on 侧计数里, 红验(注入每轮全 DOM 行再探 / 页面自调度忙任务)证明判别力保留; 分段收窄的那一侧不裸奔 —— off 侧另设宽松上限反面断言(perf.spec `OFF_GBR_CEILING`, 实测基线 prism 30/atlas 64 vs rowWin 门失效回归信号 900+, 余量 ~7x)守住「非窗口化轮次被逐行量高」模式, 该模式在纯 on 侧判据下无守阵覆盖且 P1-2 方向断言反因 off.lt 暴涨更易过。③**判据与预算公式零放松原样保留** —— 与 pytest 侧三件套同理: 修混淆源与计数口径, 不抬线。
- **守阵**: 无新守阵; 判据本身(P1-2 方向断言 / P1-3 预算公式)即守阵, 红验注入是其判别力证据(见 issue 修复后补充)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
