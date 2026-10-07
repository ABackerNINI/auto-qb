# qb-traffic-rate-basis — 流量图速率口径调研 + 实施

> 摘要: 用户反馈「流量图太陡」, 命题调研 qB 与业界方案裁决口径 —— 结论: 数据口径采用**区间平均速度**(计数器差分 Δbytes/Δt), 否决移动平均(平滑归展示层, 按观感再议); 瞬时速度继续落盘(r 行)供 agg 峰值与原始信号留存, 仅不再上图。调研(5 子代理串行)与实施计划 S1-S4 均已收口; 报告 [26-10-07-2031](../reports/26-10-07-2031-report-qb-traffic-rate-basis.html), 计划 [26-10-07-2127](../plans/26-10-07-2127-plan-qb-traffic-rate-basis.html)(Status: Done)。
> 最后活动: 2026-10-08 01:42

**Refs:** memory-bank/tasks/26-10-07-webui-qb-traffic-rate-basis.md,memory-bank/plans/26-10-07-2127-plan-qb-traffic-rate-basis.html

- 任务档案: [26-10-07-webui-qb-traffic-rate-basis](../tasks/26-10-07-webui-qb-traffic-rate-basis.md) —— 调研(P0-P6)与实施(S1-S4)全程、子任务状态表与实测数字都在档案, 本切片只留指针。
- 落地(已完成, 纯读侧): `traffic_grid.v4_rate_from_totals`(桶点级区间平均变换)+ `v4_grid_obs` D4 豁免 + `webui/server/traffic_qb.py` 两处 raw 段接线(窗首种子 D3)+ `MAX_RAW_BUCKETS=2880`(万桶级治理, raw 桶宽 = `max(ceil(采样间隔), ceil(span/2880))`); 采样器 / 存储 / state_file / 前端 / 配置零改动, 旧数据即刻按新口径出图(回滚 = revert 读侧提交, 无数据迁移)。
- 实测: test.full **2769 passed + 4 skipped / 99%** —— 基线切片 [26-10-08-0142](../testing/baselines/26-10-08-0142-webui-qb-traffic-rate-basis-impl.md)。
- 未决项(已迁出 [progress/roadmap.md](../progress/roadmap.md)): ①**D6 采样间隔演进**(默认 30s 改 1× main_tick + 设置仅能按 main_tick 倍数设置; 独立后续切片, 前置依赖桶数上限已具备); ②**D3 窗首种子 1s 边界带缺口**(停机落在 `(seed_t0-1, seed_t0)` 带且恢复在窗内时离线字节误归恢复首桶; Open issue [26-10-08-0141](../issues/26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html), 待认领)。
- 调研资产(仓库外, 长期留用): `D:\Projects\Else\qBittorrent`(master@8182ae071) 与 `D:\Projects\Else\libtorrent`(RC_2_1@53acefea9) 完整克隆; `D:\Projects\Else\auto-qb-speed-research\` 四份阶段笔记(01 现状 / 02 上游 / 03 业界 / 04 对比)。
