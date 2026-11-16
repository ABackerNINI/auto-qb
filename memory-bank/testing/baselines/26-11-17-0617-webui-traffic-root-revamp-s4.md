# 6212 —— traffic root revamp S4 回归批全量基线(A4 冷态 cov 插桩红+覆盖率闸 99.40 两阻断在案)

> 摘要: traffic root revamp S4 回归批全量基线(A4 冷态 cov 插桩红+覆盖率闸 99.40 两阻断在案)
> 基线时间: 2026-11-17 06:17
**Refs:** memory-bank/tasks/26-11-15-webui-traffic-root-revamp.md

## 验收数字

`commands run test.full` 实测(2026-11-17 06:17, Windows 开发机, 流量图根修 26-11-15-1104 T1-T7 全实现面 efc90ea5 之上):

```text
TOTAL                                                27925    110   9848    109    99%
FAIL Required test coverage of 99.5% not reached. Total coverage: 99.40%
1 failed, 6212 passed, 2 skipped in 209.74s (0:03:29)
```

- 汇总: 6212 passed / 1 failed / 2 skipped, 覆盖率 99.40%(Windows 闸 99.5 **未达, FAIL**)。
- **1 failed = tests/test_traffic_qb_bucket_cache_perf.py::test_a4_bench_cold_and_warm_single_series_24h(A4 电池冷态断言)**: 仅在带覆盖率插桩的 test.full 环境系统性红(4/4 次: 冷态 1581.3-1724.3ms > 1500ms 线); 隔离 --no-cov(test.one)绿 345-380ms, test.quick(-n 8 --no-cov, 提交闸门)绿 6213 passed —— pytest-cov 追踪使冷路径膨胀 ~4.6x, 电池标定环境无插桩, T5-T7 提交闸门因此从未测到。计划内缺陷(T5 电池), 待主会话修后另落绿切片。
- **覆盖率闸 FAIL**: 缺口单位(miss+partial) 149 → 219, **净额 +70**(分母 37106 → 37773, 注明) —— 点名新进榜 `core/traffic_grid.py` 93%(35 miss + 29 partial = 64 单位, F1-F2 重写后防御/回填装配/逐出边界路径), 其余 traffic_store_codec 2+2 / traffic_sample_agg 2+4 / traffic_qb 1 零星。与 A4 失败无关(中断的是测试自身后段, src 覆盖面由其它用例照常覆盖)。待主会话补防御路径用例或拍板处置。
- A4 判据本体在标定环境(隔离 --no-cov)全过: 单种 24h 活跃 冷态 345.1ms/温态 p95 1.73ms; 单种 24h 空闲 冷态 195.1ms/p95 4.61ms; 组图 M=30 活跃 冷态 787.2ms(豁免记录)/温态 p95 10.94ms; 组图 M=30 空闲 温态 p95 220.70ms(tripwire 线 600 内, 26-11-16 拍板接受现状)。

## 本改动面

S4 本轮**零代码改动**(纯回归与基线切片); 记录本切片对应的 26-11-15-1104 T1-T7 七提交增量面(基线 commit efc90ea5):

- F1(S1a, ddc68c11): 桶宽 = 采样整倍且恒 <=500 桶(build_grid raw 分支 + MAX_RAW_BUCKETS 2880→500); 既有电池改判面 test_traffic_grid_grid/agg/group/interval_point/sample_store/web_traffic_qb/static_dom_panel_traffic。
- F2+F3(S1b, fc97c4e4 + 969d5fcf): 点位归属归桶(栅格单几何化)+ 桶速率一次算定 + holding 新几何定义 + 有界空桶持有回填; 新电池 `test_traffic_grid_f2_battery.py`(6 例: R2 双口径对照 x4 + 封口桶不可变 + A8 存量天文件零迁移)与 `test_traffic_grid_s1b_battery.py`(4 例: A1 稳态逐拍差分 + A5 活跃/停滞/断连三态), 改判面 seam/agg/store_* 五件。
- F4(S2, b501654e + 457c51f1): V4DayCache 天文件增量解析 + 桶值单调缓存(封口桶不可变 LRU)+ 组图 Σ 成员聚合; 新电池 `test_traffic_store_incremental.py` 与 `test_traffic_qb_bucket_cache_perf.py`(A4 基准三面+组图空闲 tripwire), codec/paths 增量改判。
- F5-F8(S3, abe58b8b + efc90ea5): 判定帧补尾格 + rewin 判据改窗起点口径 + 环境层解绑 + 轮询节奏 = 采样间隔全窗统一 + 冷开首拍立即; e2e 五件改判(fx-frames/fx-panel/fx-anchor/gap-zones/grid-stability)。
- S4 e2e 回归实测: 计划点名三条(traffic-gap-zones 6 / traffic-grid-stability 4 含 3d+ hour 面 / drawer-merge 14)+ T6/T7 新建四条(traffic-fx-frames 17 含 A2 三窗帧采样与 A3 零变化拍 / traffic-fx-panel 24 含 A7 文案 / traffic-fx-anchor 6 / traffic-source-switch 6)= **77 passed (5.7m)**, dev.e2e 单桩共起。

