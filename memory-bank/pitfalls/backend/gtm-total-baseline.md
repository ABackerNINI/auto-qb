# 合计基线在过滤集收缩时被网卡生命周期累计污染

> 摘要: 合计基线在过滤集收缩时被网卡生命周期累计污染
> 触发: GTM,采样,合计基线,网卡消失,断连恢复,当日流量虚高
**Refs:** memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html, memory-bank/issues/26-11-03-1039-bug-gtm-day-total-inflation.html, memory-bank/tasks/26-11-03-backend-gtm-day-total-inflation.md

### 用「过滤后合计」做流量基线，会把网卡生命周期累计记成一次 delta

- **触发**: 采样/记账代码用「本轮过滤后所有网卡的合计读数」作为下轮做差基线，且过滤集可能收缩（网卡 down、拔网线、`adapter_include/exclude` 变更、回环过滤）；网卡恢复时计数仍保留整个生命周期累计。
- **判别**: 当日累计突然跳变到「断网前真实流量 + 恢复瞬间合计读数」量级（实测 +62.96 GiB / +9.997 GiB 恒定偏移）；`day - last` 为正（正常单调基线应为负）；dat 已落盘因此不会自愈；state.json 的 `last_*` 恰为恢复瞬间合计。
- **处置**: 基线下沉到每张网卡（`{nic: (last_up, last_down)}`，逐卡 `max(0, cur-last)` 求和）；新卡只立基线；消失卡**保留记忆**（7 天 TTL 清理）；旧 state 载荷降级时逐卡记忆置空、首轮 delta 0（宁可少报不虚高）。速率异常只告警（C-prime），不把 delta 记 0 或改当日累计。存量虚高 dat 行需按 `day - 注入量` 人工回写（dat 是 upsert，无撤回语义）。
- **守阵**: `tools/global-traffic-monitor/tests/test_sampler.py`：`test_down_adapter_recovering_does_not_backfill_lifetime_counter`、`test_all_adapters_filtered_keeps_baselines_and_new_adapter_only_establishes`、TTL / v2 往返 / v1 降级用例；`tests/test_storage.py` 的 v1 升级保留 day 断言。
- **复发**: 0

