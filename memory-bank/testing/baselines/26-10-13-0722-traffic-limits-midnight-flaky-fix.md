# 3185 —— 限速历史跨零点 flaky 两用用例锚同一天

> 摘要: 用户指派认领并修复 issue 26-10-12-2338 —— `test_recorder_patological_flip_guard` / `test_recorder_warn_first_fire_on_fresh_boot` 在距本地零点约 34 分钟内跑必红(循环 `ts+i` 跨天把按天计数 `_day_events` 清零, 2000 阈值永不达, 生产按天语义正确)。修法两条用例把循环起点 `ts` 锚当日 00:01 走仓库现单点 `v4_day_epoch`(本地口径, 与 `v4_epoch_date_str` 一致), 跨度 &lt;86400 恒同日。时刻无关证把 `time.time()` 钉距零点 1359s 跑两用用例绿(修复前同时刻直读探针 `day_events=672` 即红验锚点)。全量全绿即基线。
> 基线时间: 2026-10-13 07:22

## 验收数字

- `test.full`: **3185 passed + 4 skipped** / `TOTAL 16778 159 5714 140 99%`.
- 耗时: **57.9s** (本机并行默认).
- 较上基线 (3184/16778/5714): 用例 **+1**、语句 **±0**、分支 **±0** —— 本修复改 2 既有用例零新增用例, 改纯 test 面(`--cov=src` 只测 src, 语句/分支恒不变); +1 passed 来自随开工同步 8 笔合的另件新增用例, 不在本修复.
- Linux 侧未重测 (改动为纯 test 面时刻锚, 平台无关).

## 本改动面

- **测试**: `tests/test_traffic_limits.py` (`test_recorder_patological_flip_guard` / `test_recorder_warn_first_fire_on_fresh_boot` 场景 B —— 循环起点 `ts` 改 `int(time.time())` → `v4_day_epoch(int(time.time())) + 60`; 补 `v4_day_epoch` 进 import).
- **源**: 零改动 —— `SpeedLimitRecorder._guard_count` 按天重置计数是正确语义不受影响.
- **文档**: `pitfalls/testing/flaky-midnight-daycount.md` (新坑) · issue 26-10-12-2338 (Open→Done, 复验 + 实际修法 + 改道原因) · activeContext 切片 · 基线切片 (本份) · `kb.index` 生成物重建.

## 已知偏差 / 移交

- **改道 vs 建议修法**: 建议写 `int(time.time()) // 86400 * 86400 + 60` (UTC 秒对齐), 改道用仓库现单点 `v4_day_epoch` (本地口径) —— 非 UTC+0 时两者日界不一致, 建议形态在 UTC+8 上距零点 &lt;8h 仍跨天即新 flaky; 详见坑档与 issue 修复后补充.
- 数字差异看差值 `commands run kb.baseline -n 2` 现列.
