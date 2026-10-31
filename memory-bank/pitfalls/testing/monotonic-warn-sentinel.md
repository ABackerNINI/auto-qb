# 节流哨兵用 0.0 会吞掉首次告警: monotonic() 的原点是开机时刻

> 摘要: `time.monotonic()` 的 0 点是**机器开机时刻**(Linux `CLOCK_MONOTONIC` / Windows `GetTickCount64`), 不是"很久以前" —— 拿 `0.0` 当「从未告警」哨兵时, 节流判据 `now - 0.0 >= 3600` 在**开机不满 1 小时**的机器上判假, **首次告警被静默吞掉**。dev 机 uptime 常达数十小时故恒绿, 只有 CI 全新 VM 会红; 失败签名与"caplog 没采到"完全一样, 极易误判成 caplog 的坑。2026-10-12 流量图限速历史 W1 的两条 caplog 断言(GitHub CI 红 2 条)正是此因。
> 触发: CI 红, 本机绿, 平台无关的 CI 红, caplog 断言 False, 告警没打出来, 首次告警被吞, 节流, throttle, 哨兵, sentinel, time.monotonic, uptime, 全新 VM, 日志断言, 重启后翻转, 退避, backoff, 开机窗口, 重建被跳过

**Refs:** memory-bank/tasks/26-10-12-webui-traffic-limit-history.md

### 哨兵必须是「从未发生」语义(None), 不能是 0.0

- **触发**: 写 / 改带节流的告警(「同一对象 X 秒内至多一条」), 或排查「CI 上日志断言 `assert False = any(<generator ...>)`, 同用例在本机全绿」。
- **判别**: 代码形如 `self._x_ts = 0.0` 初值 + `if now - self._x_ts >= GAP:`(GAP = 3600s)。`time.monotonic()` 返回**自开机起的秒数** —— 既不是 epoch, 也没有"很久以前"的保证: 开机不满 `GAP` 的机器上 `now - 0.0 < GAP` ⇒ **首次告警被吞**; 且失败路径通常不推进 `_x_ts` 之外的判定, 该窗口内不会再补发。
  两种机器两种结论: dev 机 uptime 数十小时 ⇒ 恒绿; **CI 全新 VM 开机仅数分钟 ⇒ 必红**。这不是平台差异(`monotonic` 两平台都是开机起算), 是 **uptime 差异** —— 别归到 [patching.md](patching.md) 的"平台差异"里, 也别归到 [log-capture.md](log-capture.md) 的"caplog 采集不到"里(那条是采集层丢日志, 这条是**生产代码压根没打**)。
- **处置**: 哨兵用能区分「从未发生」的值 —— `None` + `if self._x_ts is None or now - self._x_ts >= GAP`(house style, 先例 `core/traffic_store.py::_warn_bad_lines` 的 `prev is not None`), 或 `float("-inf")`。**别用 0.0 / 任意"很小的常数"** —— 那等于假设机器 uptime > GAP。
  **守阵**: 用例里把时钟钉住 —— `monkeypatch.setattr(模块.time, "monotonic", lambda: 120.0)`(模拟开机 2 分钟), 断言**首次**告警必发; 本机即红即绿, 不再依赖 CI 才能现形(`tests/test_traffic_limits.py::test_recorder_warn_first_fire_on_fresh_boot`; 退回 0.0 本机立刻红)。
  **泛化**: 凡是"哨兵 / 初值代表某个绝对时刻"的写法(节流、去重、增量基线), 先问一句**那个时钟的 0 点是什么** —— `monotonic` = 开机, `time.time` = epoch(可用 0.0), `perf_counter` 起点未定义。

- **复发**: 1 —— 2026-10-31（issue 26-10-31-0932）镜像形态、方向相反：relocate 对账退避判据 `now - float(rt.get("rebuild_ts") or 0.0) < REBUILD_BACKOFF`（300s）把「从未重建」当「开机那一刻重建过」，**开机不满 5 分钟的机器上判据恒真**，首次重建 / guardian 首拉被静默跳过（同文件 `_respawn_guardian` 的 `respawn_ts` 同款）—— 同树 09:05 全量绿、宿主重启后单跑稳定红，排查一度归因「时序/环境敏感」。
  **守阵**: `tests/test_relocate_exec.py::test_rebuild_first_attempt_not_backoff_on_fresh_boot`（monotonic 钉 120.0）/ `::test_respawn_first_spawn_not_backoff_on_fresh_boot`（钉 30.0，弹掉 respawn_ts 还原「守护进程重启后首拉」现场）—— 旧实现即红，本机即现形，不再依赖重启窗口。
  **为什么没命中**: flaky 排查按动作只进了 testing 类索引，本条触发词没有「重启 / 退避 / 开机窗口」入口；直到沿「退避窗口与时间源」假设 grep `monotonic` 才路由到（触发词已补）。
