# 5014 passed + 2 skipped —— GTM 虚高修复 review 加固全量基线

> 摘要: GTM 虚高修复 review 加固全量基线(评审 3 条修复 + 4 条守阵测试后)
> 基线时间: 2026-11-03 23:52
**Refs:** memory-bank/tasks/26-11-03-backend-gtm-day-total-inflation.md, memory-bank/reports/26-11-03-2346-report-gtm-day-total-inflation-review.html, memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html

## 验收数字

`commands run test.full` 实测(develop, Windows 并行 + 覆盖率):

```text
[ok] test.full (139.2s)
  TOTAL                                                23328    167   7956    152    99%
  5014 passed, 2 skipped in 137.41s (0:02:17)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 139.2s; 覆盖率闸 Windows 99.0(`tests/conftest.py` 单点)。

工具包 `tools/global-traffic-monitor` 为独立口径(自带 `pyproject.toml` 门槛 88, 覆盖率分母只含 gtm 包), **不与主仓合算**; 本次另跑 `commands run test.gtm` 实测:

```text
[ok] test.gtm (64.8s)
  TOTAL                   2600     25    694     16    99%
  550 passed, 2 skipped in 64.04s (0:01:04)
```

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `src/auto_qb/core/traffic_source/agent.py`: 新增 `SPIKE_TIMEOUT_S = 3.0`, `fetch_last_spike` 默认超时从探活的 10s 改专用 3s(主循环线程同步调用, 允许失败的横幅数据源不成比例占 10s)。
- `tools/global-traffic-monitor/src/gtm/sampler.py`: `_dt_since_last` 入口校验 `interval_hint`(isfinite 且 >0, 否则 DEBUG + 跳过速率判定) —— 直调误传 0/负/NaN 不再能炸 `_evaluate_rate` 除法(`min(dt, NaN)` 会静默放行真实 dt, 校验必须在 hint 入口)。
- `tools/global-traffic-monitor/src/gtm/config.py`: 新增 `_overlay_already_matches`, `save_config` 拆分路径在 overlay 已存在且解析值与内存值相等时跳过改写(mtime 不变、不陪跑 .bak), 与启动路径 `ensure_v2_overlay` 的 I3 幂等口径对齐。
- 测试 ×4: `test_sampler.py`(hint 非法跳过判定 / v1 负基线降级回归钉)、`test_config.py`(overlay 幂等)、`test_traffic_source_agent_probe.py`(SPIKE_TIMEOUT_S 契约); 三份头部「测试计划」同步。
- `memory-bank/reports/26-11-03-2346-report-gtm-day-total-inflation-review.html`(新增): 本轮 code review 报告(评审矩阵/发现与处置/1 条误判撤回记录)。
