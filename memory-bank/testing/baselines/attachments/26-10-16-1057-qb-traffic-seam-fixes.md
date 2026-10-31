# 3420 passed + 4 skipped —— 接缝边界形态修复轮(短缝尖峰 + 断链首桶 null 语义)

> 摘要: 用户「认领并修复: 26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker, 26-10-16-0954-bug-traffic-seam-short-gap-spike」—— 两件均属 plan 26-10-15-0829 P2 同一决策面的边界形态收口。改动 `src/auto_qb/core/traffic_grid.py`(摊配判据三形态[本点前有 null 标记 / 未覆盖段 span>cov / 陈旧长跨度]; 基准 `step_w = step × cov // span`[未覆盖秒不归因] + 份额按累计比例取整不堆接收桶; `v4_grid_obs` 断链首桶该向出 None 而快照照记; `BucketObs` 速率放宽 Optional; `group_rate_points` 有观测而全成员该向皆未知出 null) + `tests/test_traffic_grid.py`(新增 2 条守阵 + 6 条按新口径重钉) + `tests/test_web_traffic_qb.py`(端点面 4 条期望同步); 前端 / 配置 / 运行数据零触碰。红绿双验 4 类突变判红后全部还原复绿; 合成几何复现两件 issue(短缝 8.5×→1.00× 且磁盘/活尾两路径同值; 洞后桶 null + 快照链不断)。文档面: 两 issue → Done、计划 §03 修复记录、专题档案 R11、activeContext 切片 R11、progress 口径单点、坑档 2 条。
> 基线时间: 2026-10-16 10:57
> 档案: memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md

- test.full: 3420 passed + 4 skipped / TOTAL 17202 语句 185 未覆盖 5862 分支 161 partial / 98%; `Required test coverage of 98% reached. Total coverage: 98.47%`(闸门过)。耗时 145.84s / 147.53s / 147.76s(同轮三次采样, 取区间 145.8–147.8s; 口径见 baseline.md; 本机无 uv 走 venv 直跑, 见 pitfalls/testing/no-uv-fallback.md)。
- 本轮新增 2 条守阵用例(`test_v4_seam_short_gap_two_paths_agree_no_spike` / `test_v4_grid_obs_break_bucket_rate_null_snapshot_kept`), 其余为既有用例的期望重钉(无新测试函数之外的结构变化)。
- 红绿双验(逐条突变 → 跑目标用例 → 精确反向还原, 不用 git checkout): ①断链桶速率改回 `0` → 新守阵 1 红; ②摘掉新摊配判据(`marked or span > cov or`) → 3 红(新短缝守阵 + below_threshold + edge_band); ③摊配基准改回不缩放(`step_w = step`) → 6 红(zchain_vacuum / edge_band / 两条 P2 摊配 / below_threshold / 新短缝守阵); ④组面未知判据改回 `0` → 1 红。四类均字节级还原后复绿(`MUTANT` 标记零残留)。
- 合成几何复现(只读探针 scratch `.openclaw/tmp/probe_seam_fix_round.py` 等, 未入库; 真实运行实例天文件在另一 clone, 跨 clone 不读): ①短缝(证据行 08:16 重启几何)缝后首桶 up `1,248,412 → 146,872 B/s`(= step / 真实跨度 17s, 8.5× → 1.00×), 磁盘(真空标记)与活尾(无标记)两路径取值逐位一致, 次记录桶 up=122,818 与 issue 证据行「刷盘后变平线」吻合; 近洞 60s 缝 `3100 → 100 B/s`(31× 消除); ②洞后首桶 `BucketObs(dl_rate=None, up_rate=None, 快照)` + `rate_points` 该桶 null + 次桶 delta 照旧(快照链不断)。
- 对既有验收判据的影响: E2E1 的「Σ(rate × w) = 字节守恒」细化为**覆盖份额守恒**(`step × cov // span`; 全覆盖时与原式逐字一致 —— 本事故 cov/span ≈ 0.9996, 量级无影响); E2E3(洞/断连仍 null 断链)不变; R2 风险缓解面收窄为「块内短游程行为逐字不变」。计划 §07 #2(常量非配置)不动, 阈值仍 60/60。
- Linux/macOS 侧未跑 —— 改动为纯函数层整数/覆盖口径, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/core/traffic_grid.py`: `v4_totals_points` 接缝摊配(判据三形态 + 覆盖份额基准 + 累计比例取整)与文档; `v4_grid_obs` 断链首桶该向 None(观测缝跟踪 `prev_cov_end` + 桶级 `broke` 标记)与文档; `BucketObs.dl_rate/up_rate` 放宽 `Optional[int]`; `group_rate_points` 全成员该向未知出 null; `rate_points` 文档补 null 语义。
- `tests/test_traffic_grid.py`: 新增 2 条守阵; 重钉 6 条(zchain_vacuum / edge_band 双形态 / below_threshold / live_tail / disk_vacuum); 头部「测试计划」清单同步。
- `tests/test_web_traffic_qb.py`: 4 条端点面期望同步(24h D4 0 线两条改为洞后 null / 短缝回收值 107·53 与 150·75)。
- `memory-bank/`: 两 issue → Done(复验 + 修复后补充) + `issues/_index.md` 重生成; 计划 §03「实施记录 · 计划外缺陷修复轮」+ 变更记录 + `doc-updated=26-10-16-1057`; 档案 R11 + Refs; activeContext 切片 R11; `progress/implemented-webui-history.md` 口径单点补注; 坑档 `pitfalls/backend/traffic-window-edge-floor.md` 再更新 + 新增 `pitfalls/testing/no-uv-fallback.md`。

**Refs:** memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md
