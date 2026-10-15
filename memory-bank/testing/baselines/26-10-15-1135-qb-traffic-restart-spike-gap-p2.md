# 3307 passed + 3 skipped —— qB 流量图重启缝尖峰 P2 读侧接缝摊配实施轮

> 摘要: 用户「实施计划P2」→ 落地 plan `26-10-15-0829` 的 P2(读侧快照台阶按真实发生跨度摊配, P0 已定位的唯一必要环)。改动面: `src/auto_qb/core/traffic_grid.py`(v4_totals_points 接缝摊配重写 + 窗界有界回看 `_V4_SEAM_LOOKBACK_S` 取代 `_V4_NULL_FLOOR_S` 1 秒带) + `tests/test_traffic_grid.py`(6 条新用例 + 3 条既有用例期望随守阵更新)。E2E1 真实数据回放(只读探针, 运行实例 2026-10-15.dat + P0 实测活尾重建)三窗 PASS: 接缝桶 1068/1526 B/s(修复前 7,643,191/8,248,811 B/s, 消除 7157x), 30m/3h/24h 完全一致, 份额级(delta 通道)守恒精确, 无观测缝保持 null。
> 基线时间: 2026-10-15 11:35

**Refs:** memory-bank/activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md, memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html

## 验收数字

- test.full: 3307 passed + 3 skipped / TOTAL 16897 157 5726 142 99%; 耗时 129.4s(单次采样, 口径见 baseline.md)。
- 守阵红绿双验(突变脚本三类判红后还原复绿): 摊配关(阈值无穷大)→ 5 红 / z 形签名关(恒真)→ 1 红 / 洞判关(阈值无穷大)→ 1 红。
- E2E1 回放探针: 30m/3h/24h 三窗接缝桶速率逐位一致(1068, 1526), 夜均平线 (492, 532) B/s(真值 ~643 B/s, 逐记录桶宽 ceil 取整偏差, 既有口径同款), 份额级守恒 dl 15,286,382 / up 16,497,623 精确, 速率级偏差 0.11%(整数粒度容差内), 无观测缝栅格桶 0 可见。探针为会话 scratch(`.openclaw/tmp/e2e1_replay_p2.py`), 未入库。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 未跑。
- Linux(WSL)侧未重测 —— 纯函数层无平台分支, 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/core/traffic_grid.py`: v4_totals_points 接缝摊配(z 形等值游程末端的台阶按覆盖秒摊到游程桶+接收桶, 余额归接收桶; 洞判定 = 观测覆盖缝 > _V4_SEAM_NULL_S 先于一切); 窗界有界回看(_V4_SEAM_LOOKBACK_S = 86400 = 写侧 ZRUN_FLUSH_S 同值, 槽点与 null 标记同界, 取代 _V4_NULL_FLOOR_S 1 秒带 —— 标记窄于点界会在窗外重建 issue 26-10-08-0141 断链失效假尖峰)。
- `tests/test_traffic_grid.py`: 新增 test_v4_seam_*(摊配/磁盘缝回收/洞/阈内不变/flat-r 反例/常量冻结) 6 条; 既有 3 条(d1_cross_bucket / totals_diff_reset / zchain_vacuum)期望按被修复语义更新; window_filter 与 seed_vacuum_edge_band 两条按回看契约更新。
- 滚动面: activeContext 切片(追加 R5) · 计划 doc P2 实施记录(doc-updated 抬行) · implemented-webui-history 口径段 · pitfalls/backend/traffic-window-edge-floor.md(取代注记) · plans/_index.md(kb.index 重建)。
