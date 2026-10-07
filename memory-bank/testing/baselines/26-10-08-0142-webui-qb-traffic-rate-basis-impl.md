# 2769 —— 流量图速率口径实施 S1-S4 收尾基线 (区间平均 + 桶数上限)

> 摘要: 专题 webui-qb-traffic-rate-basis 实施收尾 —— 计划 [26-10-07-2127](../../plans/26-10-07-2127-plan-qb-traffic-rate-basis.html)
> S1 读侧差分变换 `v4_rate_from_totals`+grid_obs D4 豁免 / S2 三端点接线+窗首种子(D3) / S3 raw 桶数上限
> `MAX_RAW_BUCKETS=2880` 三步入库, 相对上基线 26-10-07-2313(2757+4) passed **+12**(S1 +6 / S2 +3 / S3 +3)。
> 档案: memory-bank/tasks/26-10-07-webui-qb-traffic-rate-basis.md
> 基线时间: 2026-10-08 01:42

**Refs:** memory-bank/tasks/26-10-07-webui-qb-traffic-rate-basis.md

## test.full 实测

- 分支: develop(已同步 `b49b645e`; 工作树含 S3 与本次收尾回写的未提交改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2769 passed + 4 skipped, 0 failed, 44.95s, 覆盖率 TOTAL 99%**
  (16474 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
  —— 收尾回写前后各跑一次, 计数逐位相同(仅耗时 43.86s/44.95s 抖动); 上列为回写完成后的终树实测。
- 相对上基线 [26-10-07-2313](26-10-07-2313-webui-tooltip-declutter-r2.md)
  (2757 passed + 4 skipped @ 32.41s, 16259 语句 / 166 未覆盖 / 5686 分支 / 150 partial):
  passed **+12** / 语句 **+215** / 分支 **+8** / 未覆盖 **-1** / partial **-1**。
- 增量明细: S1 `tests/test_traffic_grid.py` +6(`v4_rate_from_totals` 4 + `v4_grid_obs` D4 豁免 1 + 组求和钉住 1);
  S2 `tests/test_web.py` 既有 6 用例按新口径改形 + 新增 3(净 +3); S3 `tests/test_traffic_grid.py` +3
  (高频上限数学 / 30s 零回归 / S3×S2 种子外扩联动)+ 既有 `test_build_grid_fractional_interval_ceils_bucket_width`
  由 24h 改 1m 窗(函数数不变)。4 skipped 为 Windows 侧 POSIX 专属存量。

## 本专题面要点(非 pytest)

- 覆盖口径变更: raw 段窗(1m-24h)速率 = 计数器差分区间平均(Δbytes/Δt), 瞬时速度不再上图
  (totals 通道逐字节不变); agg 段窗(3d+)与前端零改动。
- 桶数上限: `MAX_RAW_BUCKETS=2880` —— 1.5s 采样下 24h 窗由 43200 桶(2s 桶)加宽到 2880 桶(30s 桶),
  3h→4s 桶 2700; 30s 默认采样下数学恒等、零回归。

## 对照判据(后续沿用)

- 以本切片(2769+4 / 16474 / 165 / 5694 / 149)为实施后对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 回退先查 S1-S3 三步改动: S1 `4ab844a6` · S2 `b49b645e` · S3(本批)。
- 遗留: D3 窗首种子 1s 边界带缺口已入池 `memory-bank/issues/26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html`;
  采样间隔演进(D6, 默认 1× main_tick + 仅能按倍数设置)为独立后续切片, 前置依赖本上限已具备。
