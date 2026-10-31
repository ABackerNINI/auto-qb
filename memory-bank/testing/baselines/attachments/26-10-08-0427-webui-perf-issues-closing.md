# 2771 —— 三条 perf issue 定案 / 重归因轮基线

> 摘要: 专题 webui-perf-issues-closing 的收口 —— 全轮**只改 `memory-bank/` 文档**（两条 issue 定案 Done + 一条重归因改写 + 一条新件入池 + 本档案与切片），`src/` 与 `tests/` **零改动** ⇒ 相对上基线 26-10-08-0258(2771+4)逐位持平。
> 档案: memory-bank/tasks/26-10-08-webui-perf-issues-closing.md
> 基线时间: 2026-10-08 04:27

**Refs:** memory-bank/tasks/26-10-08-webui-perf-issues-closing.md

## test.full 实测

- 分支: `develop`（开工同步后 `0a46b58d`）
- 命令: `commands run test.full`（Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」）
- **实测 (Windows)**: **2771 passed + 4 skipped, 0 failed, 42.68s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0258](26-10-08-0258-backend-test-web-split-s0s1.md)
  (2771 passed + 4 skipped @ 56.3s, 同 16476 / 165 / 5694 / 149):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: **零 pytest 侧改动** —— 本轮新增/修改的 4 份 `memory-bank/issues/*.html` 与档案/切片均不进 `testpaths(tests/)`;
  `test_docs_forms` 一类文档守卫仍在本轮数字里跑过且全绿（`commands run kb.check` 亦全绿: 主键纪律 / 认领链 / 回写措辞 / 日期守卫）。
- 4 skipped 为 Windows 侧 POSIX 专属存量。

## 同轮非 pytest 实测（专题判据，不入 pytest）

- **前端 e2e 全量**（`commands run dev.e2e`，2026-10-08 04:15）: **94 passed / 10 skipped / 0 failed**（3.5m）。
  前置: 本机 `node_modules` 缺 `@playwright/test`（`dev.e2e` 直接 `ERR_MODULE_NOT_FOUND`），`npm install` 补 5 包后跑通 ——
  **换机器 / 新 clone 跑 e2e 前先确认依赖已装**。
  判据意义: 增量同步计划 S10 归档（`24ab7c31`）记录的 **6 条存量失败已清零**（根因 A 桩 `FakeTorrent.to_dict` 未跳过 `hr_link`
  ⇒ 详情端点恒 500 ×4，已由 `312165f8` 修；根因 B S7 WeakMap 令 `applyOptimistic` 原地变更不传导 ⇒ ×2，已由 `17dc0fc7` 修；
  两条修复都在 S10 归档之后，本轮是首次全量复跑验证；S10 基线的口径是"修复后应回 92"，实测 94）。
  ⇒ **下轮 e2e 对照点: 94 passed / 10 skipped / 0 failed**，掉下来就是回归。
- **仿真 P2 场景复测**（`uv run python scripts/sim_run.py --scenario P2 --n 5000 --duration 50 --ramp 200 --web-port 18201`，
  2026-10-08 04:19，生成 config `main_tick: 2S` / `max_tasks_per_tick: 20`）: verdict OK，
  rounds=24 / full=1 / **avg_interval=2.139 s** / **drift_max=0.801 s** / avg_bytes=487202；
  `S3.write_rate_per_min` 4299.6（≤6210.49 PASS）、`P1.first_round_s` 2.174（≤22.68 PASS）、tracebacks=0 / critical=0。
  对照 2026-09-19 取证: 稳态 2.87→2.139 s、漂移 1.22→0.801 s（已进 `SYNC.drift_max_s ≤ 1.0` 稳态门限内）。
  单次采样未取区间；产物 `R:\auto-qb-sim\runs\20261008-041959-P2`。

## 踩坑（本轮新得，下次直接复用）

- **`sim_baseline.py` 不带 `--merge` 会整体覆写 `plans/…baseline.json`** —— 只跑 P2 时 `P1.first_round_s` 等阈值会按 ramp 数字重算，
  污染硬判据。只想取数字就用 `--dry` 打印出的那条 `sim_run.py` 命令直接跑（同数字、零副作用）。
- **仿真工作根 `R:\auto-qb-sim` 在工作区外** —— 工具沙箱会拦写（`PermissionError WinError 5`），需显式放行后才能跑。

## 对照判据（后续沿用）

- pytest: 以本切片（2771+4 / 16476 / 165 / 5694 / 149）为对照点，预期 passed 只升不降、未覆盖 / partial 不升。
- e2e: 94 passed / 10 skipped / 0 failed 为新的绿线。
- 仿真: P2 漂移 0.801 s 为新观测点（不判红，只作前后对照）。
