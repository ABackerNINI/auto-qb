# 流量图读侧窗过滤: null 标记取整下偏的 1 秒边界带

> 摘要: `traffic_grid.v4_series_points` 的真空/断连 null 标记时间**向下取整**(`int(prev_chain_end)` / `floor(ts)`), 而观测点的保留判据是「覆盖桶触及窗口左界」(`ceil(ts) >= t0`)—— 两判据不同源。停机/断连恰落 `(t0-1, t0)` 时标记取整后 = `t0-1` 落窗外被丢, 种子点却仍保留 ⇒ 差分链误接、离线期字节误归恢复首桶(假尖峰)。修法(issue 26-10-08-0141, 2026-10-08 落地): null 点窗过滤下界放宽 1 秒(`_V4_NULL_FLOOR_S`)与种子点保留带精确对齐。
> 触发: 改读侧窗过滤, 改窗首种子外扩, 改归桶/真空判定, 改 null 点, 改 v4_series_points, 假尖峰, 恢复首桶, 取整, 边界带

**Refs:** memory-bank/tasks/26-10-08-webui-qb-traffic-seed-vacuum.md

### 窗口边界上「标记时间取整」与「覆盖保留」不同源 —— 1 秒带内标记被丢、链误接

- **触发**: 改 `traffic_grid.v4_series_points` 的窗口过滤下界 / 窗首种子外扩(D3, `seed_t0 = grid.t0 - grid.interval`) / 真空与断连 null 点生成; 或用户报「程序停机或断连后恢复的首桶出现假尖峰(离线期字节)」。
- **判别**: 两条判据**不同源** —— ①null 标记 t = **向下取整**(真空 `int(prev_chain_end)` / 断连 `floor(ts)`); ②观测点保留 = **覆盖桶触及窗口左界**(`key + w >= t0`, 即 `ceil(ts) >= t0`)。交集带恰为 `prev_chain_end ∈ (t0-1, t0)`: 标记取整后 = `t0-1 < t0` 被丢, 种子点却因 `ceil(prev_chain_end) = t0 >= t0` 保留 ⇒ 差分链误接。带外(`prev_chain_end <= t0-1`)种子点亦被滤, 恢复首点本就无基线, 无此路径 —— 故边界带恰 1 秒宽。
- **处置**: null 点窗过滤下界放宽 1 秒(`_V4_NULL_FLOOR_S = 1`, 取整下偏容差), 与种子点保留带精确对齐; 真空与断连两处同款下偏一并覆盖。null 点恒不外发(`v4_grid_obs` 跳过), 多留的标记只影响链断位置, 无输出面副作用。实例: issue 26-10-08-0141(假尖峰 rate 300 / totals 9000 = 离线字节 `10600-1600` 跨停机差分)。
- **守阵**: `tests/test_traffic_grid.py::test_v4_seed_vacuum_null_t0_edge_band_chain_break`(纯函数 1s 几何 + 带外对照)、`tests/test_web.py::test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band`(端点面, 时钟钉死)。
