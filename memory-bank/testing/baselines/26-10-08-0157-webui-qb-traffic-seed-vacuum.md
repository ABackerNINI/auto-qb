# 2771 —— 流量图窗首种子 1s 边界带真空断链修复基线

> 摘要: 专题 webui-qb-traffic-seed-vacuum(认领并修复 issue 26-10-08-0141)—— `v4_series_points`
> 的 null 点窗过滤下界放宽 `_V4_NULL_FLOOR_S`(1s), 使停机/断连恰落在 `(t0-1, t0)` 的真空 null
> 标记不被丢弃(种子点与恢复首点之间差分链正确断开)。相对上基线 26-10-08-0142(2769+4)
> passed **+2**(纯函数守阵 1 + 端点守阵 1, 均先红后绿); 生产代码仅 1 处语义改动(1 常量 + 2 过滤点),
> 语句 +2 全被覆盖。
> 档案: memory-bank/tasks/26-10-08-webui-qb-traffic-seed-vacuum.md
> 基线时间: 2026-10-08 01:57

**Refs:** memory-bank/issues/26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html,memory-bank/tasks/26-10-08-webui-qb-traffic-seed-vacuum.md

## test.full 实测

- 分支: develop(已同步 `7baeaf10`; 工作树含本次修复与回写的未提交改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2771 passed + 4 skipped, 0 failed, 42.3s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0142](26-10-08-0142-webui-qb-traffic-rate-basis-impl.md)
  (2769 passed + 4 skipped @ 44.95s, 16474 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **+2** / 语句 **+2** / 未覆盖 **0** / 分支 **0** / partial **0**。
- 增量明细: `tests/test_traffic_grid.py::test_v4_seed_vacuum_null_t0_edge_band_chain_break`(+1, 纯函数 1s 几何)
  + `tests/test_web.py::test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band`(+1, 端点面, 时钟钉死)。
  4 skipped 为 Windows 侧 POSIX 专属存量。

## 本专题面要点(非 pytest)

- 修复点: `core/traffic_grid.py` `v4_series_points` —— null 点窗过滤下界 `t0` → `t0 - _V4_NULL_FLOOR_S`
  (真空 null `int(prev_chain_end)` 与断连 null `floor(ts)` 两处同款取整下偏)。语义: 停机/断连恰落
  `(t0-1, t0)` 时标记取整后 = `t0-1` 落窗外, 而种子点仍因覆盖桶触及 t0 保留 ⇒ 丢标记会使差分链
  误接(离线字节误归恢复首桶)。null 点恒不外发, 多留标记只影响链断位置。
- 红验实录: 临时置 `_V4_NULL_FLOOR_S = 0` → 纯函数用例恢复首桶 `(10600-1600)/30 = 300` 假尖峰;
  端点用例恢复首桶 `dl=300/up=150`(totals 9000)。还原即复绿。
- 无 API / 响应形状 / 存储 / 配置 / 前端改动; 三端点(global/torrent/group)共享同一 `v4_series_points`,
  一处修复全覆盖; 回滚 = revert 读侧提交, 无数据迁移。

## 对照判据(后续沿用)

- 以本切片(2771+4 / 16476 / 165 / 5694 / 149)为修复后对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 回退先查本次改动: `core/traffic_grid.py` 的 `_V4_NULL_FLOOR_S` 与 `v4_series_points` 两处 `null_lo`。
- 遗留: D6 采样间隔演进(默认 1× main_tick + 仅能按倍数设置)仍为独立后续切片(见 [progress/roadmap.md](../../progress/roadmap.md))。
