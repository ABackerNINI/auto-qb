# 6485 passed, 6 skipped —— issue 26-11-19-0052 修复轮: traffic 空路径特判(快照侧 + 曲线侧同族)

> 摘要: issue 26-11-19-0052 修复轮: traffic 空路径特判(快照侧 + 曲线侧同族)
> 基线时间: 2026-11-19 08:13

## 验收数字

`commands run test.full` 实测(2026-11-19 08:35, 曲线侧同修入批后, 196.2s):

```text
TOTAL                                                28915     44  10322     61    99%
6485 passed, 6 skipped, 7 warnings in 194.12s (0:03:14)
```

另 `commands run test.quick`(提交闸门口径)全绿: 6489 passed, 2 skipped(2026-11-19 08:31 实测)。其上某轮 quick 曾红 1 条 `test_hr_discovery.py::test_start_all_busy_returns_false_and_retries`, 单跑复绿(BIND 端口竞争 flaky, 与本批改动无关; 本批未触 hr/端口面)。

## 本改动面

- `src/auto_qb/core/traffic_source/reader.py`: 新增 `CODE_SOURCE_MISSING = "source_missing"` 契约常量(不发射, 只做 reasons.code 取值单点)。
- `src/auto_qb/core/modules/traffic_snapshot_mod.py`: `refresh()` 读盘前特判空路径(不读盘, 发布 stale + `source_missing`, 文案复用 `paths.unavailable_reason()`); 新增实例标志 `_source_missing_warned`(首条 WARNING 后降 DEBUG); docstring 三种结局更新。
- `src/auto_qb/core/modules/speed_curve_mod.py`(用户拍板曲线侧同族同修): `handle_speed_limit_curve` 同构特判 —— 不读盘, `limit=stale` + `source_missing`, 文案同走 `unavailable_reason`, 一次性 WARNING 标志同款; 模块 docstring 规则面更新。
- `tests/test_traffic_snapshot.py`: 新增 3 用例(空路径不读盘红验+恢复弧 / 一次性 WARNING / GTM 指针缺席文案), 文件头测试计划同步; 评审轮 1 minor 修复(DEBUG 断言钉到原因文案)。
- `tests/test_speed_curve_traffic.py`: 新增 2 用例(曲线侧契约+日志一次性+恢复弧 / GTM 缺席文案), 文件头测试计划同步。
- `memory-bank/issues/26-11-19-0052-bug-traffic-dat-empty-path-warning.html`: 复验行 + 修复后补充(含曲线侧同修记录) + 状态 Open→Done(kb.status)。
