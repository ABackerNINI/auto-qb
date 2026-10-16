# 3421 passed + 4 skipped —— 接缝残余边界补修(活尾组同判块间真空)

> 摘要: 用户「修复残余边界」—— 收口 `26-10-16-1057` 轮自报的残余形态: 覆盖连续(`span == cov`)且带块界真空标记的缝, 活尾路径此前不判真空 ⇒ 同一几何两条路径取值不同(修复前: 磁盘走摊配回收、`span <= 60s` 时甚至走 `elif marked` 丢弃成 None; 活尾把整块台阶按自身桶宽打入接收桶)。改动 `src/auto_qb/core/traffic_grid.py`(`v4_series_points` 的活尾组改为**与磁盘块同判块间真空** —— 首槽覆盖桶抵达不了磁盘链末槽即出 null 标记; 旧注释假设「磁盘链末槽与活尾首槽之间是一次标称采样间隔」只对同块续链成立, `head_pending` 的活尾首槽是块首记录 `B.start`, 重启后可隔一整段停机; 模块头与函数 docstring 同步) + `tests/test_traffic_grid.py`(新增 1 条守阵 + 活尾相关 3 条既有用例改钉「同标记」口径 + 头部清单同步)。前端 / 配置 / 运行数据零触碰。
> 基线时间: 2026-10-16 11:26
> 档案: memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md

- test.full: 3421 passed + 4 skipped / TOTAL 17202 语句 185 未覆盖 5862 分支 161 partial / 98%; `Required test coverage of 98% reached. Total coverage: 98.47%`(闸门过)。耗时 145.05s / 145.07s(同轮两次采样, 取区间 145.0–145.1s; 口径见 baseline.md; 本机无 uv 走 venv 直跑, 见 pitfalls/testing/no-uv-fallback.md)。
- 本轮新增 1 条守阵用例(`test_v4_seam_covered_span_mark_two_paths_agree`); 活尾相关 3 条既有用例的**数值零变化**(仅多一个同位的缝真空标记, 断言改按标记过滤/显式索引 —— 活尾场景实测: 过滤后 out[1:62] 仍全 (2,1)、Σ 仍 244/122)。
- 红绿双验(1 类): 摘除活尾组的真空判定(条件加 `not is_tail`)→ 4 红(新残余守阵 + short_gap 两路径一致 + live_tail + hole 三条); 字节级还原后复绿, `MUTANT` 标记零残留。
- 只读探针 scratch `.openclaw/tmp/probe_tail_vacuum.py`(未入库): 残余几何两路径逐位一致(含同一位标记 1003; 接收桶 (34, 17) vs 修复前活尾 (100, …) 单桶归因/磁盘 None 丢弃); 覆盖份额守恒(span == cov ⇒ 基准 = step 全额, 游程桶+接收桶逐点 delta 之和 = step 200/100)。
- 对本轮前一轮数字的影响: 仅 +1 条新用例; S6 旧钉「活尾合流不产 null 标记」改为「活尾同判真空 —— 与磁盘路径同标记」(旧钉护住的是缺陷面, 见坑档 `pitfalls/backend/traffic-window-edge-floor.md` 第三条)。
- Linux/macOS 侧未跑 —— 改动为纯函数层槽位/覆盖口径, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/core/traffic_grid.py`: `v4_series_points` 真空判定合并为「本组(磁盘块或活尾)首槽覆盖桶起点晚于上组游标终值 → 出 null 标记」(活尾仍保留按槽 ts 与磁盘链去重的后缀过滤); 模块头「活尾合流」条与函数 docstring 改写。
- `tests/test_traffic_grid.py`: 新增 `test_v4_seam_covered_span_mark_two_paths_agree`; `test_v4_seam_short_gap_two_paths_agree_no_spike` / `test_v4_seam_spread_live_tail_restart_no_spike` / `test_v4_seam_hole_over_threshold_drops_delta` 三条改钉「活尾同标记」口径(标记过滤 + 显式索引); 头部「测试计划」清单同步。
- `memory-bank/`: issue `26-10-16-0954-bug-traffic-seam-short-gap-spike` 状态变更日志 + 修复后补充补记残余边界修(状态维持 Done); 计划 §03 修复记录追加补修段 + 变更记录 + `doc-updated=26-10-16-1126`; 档案 R12 + 子任务表; activeContext 切片 R12 + Refs; 坑档 `pitfalls/backend/traffic-window-edge-floor.md` 再补一条(「稳态才成立」的假设不得当不变式入守阵)。

**Refs:** memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md
