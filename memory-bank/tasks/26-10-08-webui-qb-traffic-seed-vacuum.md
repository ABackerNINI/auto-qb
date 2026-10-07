# 26-10-08-webui-qb-traffic-seed-vacuum — 流量图窗首种子 1 秒边界带真空断链修复

**Status:** Done
**Added:** 2026-10-08
**Updated:** 2026-10-08
**Summary:** 用户指派认领并修复 issue 26-10-08-0141 —— D3 窗首种子在停机时刻落在 (seed_t0-1, seed_t0) 这 1 秒带时, 真空 null 点 t = int(prev_chain_end) 取整后 = seed_t0-1 被窗过滤丢弃, 种子点(覆盖桶触及 t0 照收)与恢复首点之间差分链误接, 离线期 qB 自行传输的字节被误归恢复首桶出假尖峰(rate 300 / totals 9000)。修法 = `v4_series_points` 的 null 点窗过滤下界放宽 `_V4_NULL_FLOOR_S`(1s)(真空/断连两处同款取整下偏); 读侧纯函数改动, 无数据迁移, 回滚 = revert。test.full **2771 passed + 4 skipped / 99%**(+2 守阵, 先红后绿)。
**Topics:** qb-traffic-rate-basis

**Refs:** memory-bank/issues/26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html,memory-bank/testing/baselines/26-10-08-0157-webui-qb-traffic-seed-vacuum.md,memory-bank/pitfalls/backend/traffic-window-edge-floor.md

> 背景关联(不进机器认领链): 本缺口是专题 `qb-traffic-rate-basis`(速率口径调研 + 实施)的 D3 缺陷, 档案 [26-10-07-webui-qb-traffic-rate-basis](26-10-07-webui-qb-traffic-rate-basis.md), 计划 [26-10-07-2127](../plans/26-10-07-2127-plan-qb-traffic-rate-basis.html) S2 实施期发现并入池。

## 原始请求

用户指令: 「认领并修复 issue: 26-10-08-0141-bug-qb-traffic-seed-vacuum-1s-edge.html」 —— 即 create-issue 流程的「修一条 issue 时」路径: 用户显式指派认领(非 agent 自认领) → 复验 → 修复 → 置 Done + 补实测数字 → 认领链双向闭合。

## 思考过程与决策

- **复验(先红后绿)**: 按 create-issue 防过期原则第 5 条, 先按锚点重跑并构造 1s 几何 —— 纯函数脚本实测: 种子块末槽 @999.5(∈ (t0-1, t0), t0 = seed_t0 = 1000)、恢复块首点 @1030 时, `v4_series_points` 返回流**无 null 点**, `v4_rate_from_totals` 恢复首桶 rate = (10600-1600)/30 = **300**(假尖峰), 现象**仍复现**。
- **根因(证实, 非推断)**: 真空 null 点 t = `int(prev_chain_end)` 向下取整; 停机落在 `(seed_t0-1, seed_t0)` 时取整后 = `seed_t0-1 < t0`, 被 `if t0 <= t < t1` 丢弃。而同一几何下种子点(key = t0-w, 覆盖桶 `[t0-w, t0)` 触及 t0)按覆盖规则**仍保留** ⇒ 种子点与恢复首点之间无断链标记, 差分链误接。
- **边界带恰为 (t0-1, t0) 的论证**: 种子点保留 ⟺ `ceil(prev_chain_end) >= t0` ⟺ `prev_chain_end > t0-1`; 标记被丢 ⟺ `int(prev_chain_end) < t0` ⟺ `prev_chain_end < t0`。两条件交集 = `prev_chain_end ∈ (t0-1, t0)`, 取整后标记恒 = `t0-1`。故下界放宽 **1 秒**即完整覆盖(带外 prev_chain_end ≤ t0-1 时种子点亦被滤, 恢复首点本就无基线, 无假尖峰路径)。
- **修法选择(与 issue「建议修法」的出入, 说明改道原因)**: issue 建议方向 ① 措辞含混(「按原始窗 t0 判保留」方向相反 —— 原始窗 t0 > seed_t0, 会更严而非放宽), ②「种子只喂差分基线、不参与 null 过滤」语义不清。实际采**取整下偏容差**: null 点窗过滤下界由 `t0` 放宽为 `t0 - _V4_NULL_FLOOR_S`(= 1s, 命名常量 + 注释), 真空与断连两处同款取整下偏一并覆盖。理由: ① 该下界与种子点保留带**精确对齐**(见上论证), 不多留也不少留; ② null 点恒不外发(`v4_grid_obs` 跳过), 多留的标记只影响链断位置, 无输出面副作用; ③ 纯读侧一行语义改动, 无 API/形状/存储面变化。
- **范围守恒**: 只动 `v4_series_points` 的窗过滤下界与两处过滤点; 未触碰种子外扩量、`v4_grid_obs`、端点接线、agg 段窗、前端。issue 的「影响面」所述三端点(global/torrent/group)共享同一 `v4_series_points`, 一处修复全覆盖。

## 实现计划

单步(单会话可闭): ① 复验(构造 1s 几何, 脚本 + 单测先行红验)→ ② `traffic_grid.py` 加 `_V4_NULL_FLOOR_S` 常量 + 两处 null 过滤下界改用 `null_lo` + 区头注释 → ③ 守阵两处(`test_traffic_grid.py` 纯函数 + `test_web.py` 端点, 各红验)→ ④ `dev.fmt` + `test.full` + 基线切片 → ⑤ 收尾回写(档案/切片/roadmap/issue 状态与认领链)+ `kb.index`。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| F0 | 复验(构造 1s 几何, 先红) | ✅ | 脚本实测恢复首桶 rate=300 假尖峰(现象仍复现) |
| F1 | 修复: null 点窗过滤下界放宽 | ✅ | `core/traffic_grid.py` `_V4_NULL_FLOOR_S` + `null_lo`(真空/断连两处) |
| F2 | 守阵(纯函数 + 端点, 各红验) | ✅ | `test_traffic_grid.py` +1 / `test_web.py` +1(均先红后绿) |
| F3 | 收口: 全量测试 + 基线 + 回写 | ✅ | test.full **2771+4 / 99%**; 基线 26-10-08-0157; 档案/切片/roadmap/issue 回写; kb.index 重建 |

## 进度日志

- **2026-10-08 01:51** 会话开工: 同步 `已同步 7baeaf10`; 读 issue 26-10-08-0141(Open/standard/bug)+ 计划 26-10-07-2127(D3)+ 现行 `traffic_grid.py`/`traffic_qb.py` + S2 守阵。
- **2026-10-08 01:5x** 复验并定位根因(见「思考过程与决策」); 用户已显式指派认领(非自认领)。
- **2026-10-08 01:5x** 落码: `_V4_NULL_FLOOR_S = 1` 常量 + `v4_series_points` 内 `null_lo = t0 - _V4_NULL_FLOOR_S`, n 槽 null 过滤与真空 null 最终过滤两处改用 `null_lo`; 区头「窗口」注释同步。复验脚本复跑: null 点 @999 保留、恢复首桶 rate 由 300 变 None。
- **2026-10-08 01:5x** 守阵两处落码并**逐条红验**(临时置 `_V4_NULL_FLOOR_S = 0` 复现红, 还原复绿): `test_traffic_grid.py::test_v4_seed_vacuum_null_t0_edge_band_chain_break`(含带外对照)、`test_web.py::test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band`(时钟钉死使 1s 几何确定; 红验实测恢复首桶 dl=300/up=150)。
- **2026-10-08 01:57** 收口: `dev.fmt` 三文件; `commands run test.full` **2771 passed + 4 skipped, 0 failed, 42.3s, TOTAL 99%**(相对上基线 26-10-08-0142 的 2769+4: passed **+2** = 本轮新增守阵; 回写前后各跑一次逐位相同); 新建基线切片 [26-10-08-0157](../testing/baselines/26-10-08-0157-webui-qb-traffic-seed-vacuum.md); 新坑按动作写进坑档 [pitfalls/backend/traffic-window-edge-floor.md](../pitfalls/backend/traffic-window-edge-floor.md)(窗口边界取整下偏 1 秒带); issue 置 Done + 认领链回填; activeContext 切片与 roadmap 回写; `kb.index` 重建。
