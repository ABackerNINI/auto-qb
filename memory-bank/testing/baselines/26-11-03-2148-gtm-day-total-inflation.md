# 5012 passed + 2 skipped(根) —— GTM 当日总量虚高修复全量基线

> 摘要: GTM 当日总量虚高修复全量基线
> 基线时间: 2026-11-03 21:48
**Refs:** memory-bank/tasks/26-11-03-backend-gtm-day-total-inflation.md, memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html, memory-bank/issues/26-11-03-1039-bug-gtm-day-total-inflation.html

## 验收数字

`commands run test.full` 实测(分支 `feat/gtm-day-total-inflation`, Windows 并行 + 覆盖率):

```text
[ok] test.full (222.6s)
  TOTAL                                                23327    167   7956    152    99%
  5012 passed, 2 skipped, 3 warnings in 216.82s (0:03:36)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 222.6s; 覆盖率闸 Windows 99.0(`tests/conftest.py` 单点)。与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

工具包 `tools/global-traffic-monitor` 为独立口径(自带 `pyproject.toml` 门槛 88, 覆盖率分母只含 gtm 包), **不与主仓合算**; 本次另跑 `commands run test.gtm` 实测:

```text
[ok] test.gtm (99.4s)
  TOTAL                   2585     23    684     14    99%
  547 passed, 2 skipped in 95.31s (0:01:35)
```

## 本改动面

- `tools/global-traffic-monitor/src/gtm/sampler.py`: 文档串补 C-prime 速率告警(只 WARNING + `last_spike`, 不改 delta/day)与「三条记账状态 + 一条只读观测」口径; 无行为改动。
- `docs/configuration.md`: 口径补逐网卡基线/消失卡 7 天记忆; 参数表新增 `sample_rate_warn_bps`(默认 1GiB/s, 只告警); 补 `config.v2.yml` overlay 与告警可见面(状态栏横幅主告知, 设置页为次级)。
- `tests/test_traffic_source_agent_probe.py`: 修 `fetch_last_spike` 失败矩阵的不可达用例——原前置仍停在空密钥分支, 未真正走到 `ToolUnreachable` catch; 补合法密钥后覆盖该分支(连带上浮覆盖率至门槛)。
- `memory-bank/issues/26-11-03-1039-bug-gtm-day-total-inflation.html`: 状态 Open→Done, 补修复证据与存量虚高未回写事实。
- `memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html`: 实施阶段标完成并附各步 commit; 告警可见面注明确认状态栏常驻横幅为主告知、设置页非唯一入口。
- `memory-bank/tasks/26-11-03-backend-gtm-day-total-inflation.md`(新增): 本专题档案(原始请求/决策/子任务状态/进度日志)。
- `memory-bank/pitfalls/backend/gtm-total-baseline.md`(新增): 「过滤后合计基线被过滤集收缩污染」坑档。

