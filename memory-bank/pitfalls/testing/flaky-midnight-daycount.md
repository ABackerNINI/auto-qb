# 用例循环 ts+i 跨本地零点把按天计数清零 —— 距零点时段必红 flaky

> 摘要: 用例喂 `observe(ts+i)` 循环(i 到阈值+30)拿 `ts = int(time.time())` 时, 距本地零点 &lt;循环跨度秒的跑必红 —— 生产代码按天重置计数是**正确**语义, 用例未固定「同一天」致阈值永不达, 告断言红。修法锚循环起点当日 00:01 走仓库现单点 `v4_day_epoch`(本地口径, 与 `v4_epoch_date_str` 一致), **别**用 `//86400*86400`(UTC 秒对齐, 非 UTC+0 日界错位即新 flaky)。2026-10-13 流量图限速历史两条用例实证。
> 触发: flaky, 跨零点, 距零点, 必红时段, 按天计数, 阈值永不达, 循环 ts+i, 跨天清零, v4_day_epoch, 86400, 当日 00:01, 时刻相关, CI 偶发红

**Refs:** memory-bank/issues/26-10-12-2338-test-traffic-limits-guard-midnight-flaky.html

### 按天计数护栏 + 用例循环跨零点 = 时刻相关必红

- **触发**: 写 / 改用例喂时间戳循环(`for i in range(N): observe(..., ts + i)`, N 千秒级)对生产代码有**按天重置计数**护栏(单天事件超阈值即告), 或排查「全量 / 单文件跑在距本地零点约 N 分钟内必红, 其余时段绿; CI 多数时候绿」。
- **判别**: 生产代码形如 `if self._day_events_date != date_str: self._day_events = 0`(`date_str = v4_epoch_date_str(ts)`) —— 按天语义**正确**, 不受影响。缺陷在**用例**: `ts = int(time.time())` 现时刻, 循环跨度 N 秒; 距零点 &lt; N 时循环跨天, day1 计数封顶 `距零点`、day2 计数 `N - 距零点`, 两者 &lt; 阈值 ⇒ 告**永不触发**, 断红。死窗 offset∈[阈值−N+1, 阈值−1] 实测(阈值 2000、N 2030 ⇒ offset∈[31,2000]; offset≤30 edge day2 仍达阈值即绿)。失败签名与"caplog 没采到"完全一样 —— 别归到 [log-capture.md](log-capture.md) 那条采集层坑, 这条是生产代码压根没打(按天语义正确, 用例喂跨天)。
- **处置**: 锚循环起点**当日 00:01** —— `ts = v4_day_epoch(int(time.time())) + 60`, 跨度 &lt;86400 恒同日, 计数不再跨天清零。**用仓库现单点 `v4_day_epoch`**(本地时区, 与 `v4_epoch_date_str` 的 `datetime.fromtimestamp` 口径一致), **别**用 `int(time.time()) // 86400 * 86400 + 60` —— 后者按 UTC 秒对齐, 非 UTC+0 时与 `v4_epoch_date_str` 日界不一致(UTC+8 上距零点 &lt;8h 仍跨天), 即把另一时刻现红新 flaky。备选(不推荐): 把循环跨度 &lt; 距零点剩余秒 —— 脆弱, 换个时刻又红。
  **守阵(时刻无关证)**: 把 `time.time()` 钉在死窗 —— `day0 = v4_day_epoch(int(real())); time.time = lambda: day0 + 86400 - 1359` 再跑两用用例即绿; 修复前同时刻直读探针 `day_events` 远低于阈值即红验锚点。
  **泛化**: 凡是"按天/按周期重置内存计数"的护栏, 用例喂跨周期时间戳即把阈值永不达 —— 先问一句**循环跨度 vs 距周期边界**, 锚起点周期内固定。同族 [monotonic-warn-sentinel.md](monotonic-warn-sentinel.md)(哨兵 0 点 = 开机时刻) —— 两坑都是"用例假设某时钟的 0 点/边界, 生产语义正确但用例未固定"。
