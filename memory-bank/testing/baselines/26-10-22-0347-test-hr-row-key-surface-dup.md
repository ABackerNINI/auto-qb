# 3996 passed + 2 skipped —— HR 键面单点补全(lane 子键面 + SiteStatus)后全量基线

> 摘要: HR 键面单点补全(lane 子键面 + SiteStatus)后全量基线
> 基线时间: 2026-10-22 03:47

**Refs:** memory-bank/tasks/26-10-22-test-hr-row-key-surface-dup.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3996 passed, 2 skipped in 152.77s**
- 覆盖率: TOTAL **99%**(20981 stmts / 7088 branch, 99.28%)

逐条口径注记:

- 本轮仍只改测试侧(两常量 + 三处断言), `src/` 零改动 ⇒ 收集面与上一条基线一致
- 守阵红验(探针): `HistoryLane` 加 `probe_lane` → 两处 lane 键面断言**同时红**; `SiteStatus` 加 `probe_site` → 键面断言红。还原后归绿
- 基线测在「已含本次代码改动、尚未提交」的工作树上
- 耗时 152.77s 是单次采样(同时段机器负载口径见 `testing/baseline.md`)

## 本改动面

- `tests/webui_helpers.py` —— HR 段追加 `HISTORY_LANE_KEYS`(7 键) 与 `SITE_STATUS_KEYS`(39 键), 与 R0 的三常量同处
- `tests/test_hr_status.py` —— `test_history_rows_field_surface` / `test_history_lanes_defaults_and_fallbacks` 的 lane 子键面改引 `HISTORY_LANE_KEYS`(两处去重); `test_site_status_to_dict_field_surface` 改引 `SITE_STATUS_KEYS`(单处搬家, 无去重收益)
- 生产代码零改动; `LaneStatus`(14 键)与 `QuotaStatus` 保持原样, 不在本轮范围
