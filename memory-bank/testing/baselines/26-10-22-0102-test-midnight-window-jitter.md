# 3990 passed + 2 skipped + 1 failed —— 跨日窗口抖动修复(通知面导入时求值 + qb 00:00:00-00:00:30 几何分档)后全量基线

> 摘要: 跨日窗口抖动修复(通知面导入时求值 + qb 00:00:00-00:00:30 几何分档)后全量基线
> 基线时间: 2026-10-22 01:02
**Refs:** memory-bank/pitfalls/testing/flaky-midnight-daycount.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **1 failed, 3990 passed, 2 skipped in 132.79s**
- 覆盖率: TOTAL **99.29%**(过闸)

逐条口径注记:

- 唯一 1 failed = `tests/test_traffic_snapshot.py::test_publish_event_patches_day_row_without_reading` —— **存量墙钟粒度 flake**(`assert tv["ts"] > before_ts` 两次 `time.time()` 背靠背返回同值, 本机亚 µs 粒度坍缩), 干净树无插件也红, 与午夜窗口无关、与本轮改动无涉; 按范围守恒未修, 建议另案入池
- 本轮修复面(通知面 12 例 / qb 21 例)在 test.full 内全绿

## 本改动面

- `tests/test_web_traffic_monitor_notify.py` —— 删模块级 `EVENT` 常量(import 时求值 `date.today()`, 与服务端请求时判据在 23:59→00:00 跨日瞬间分家), 改调用时求值工厂 `_event(**overrides)`; 全部 12 例改用工厂
- `tests/test_web_traffic_qb.py` —— `test_api_traffic_qb_global_24h_reads_only_involved_day_files` 补 00:00:00–00:00:30 子窗口守阵: 假钟档 `_FROZEN_OFFSETS = (300, 15)`, 真钟档入口钉 `monkeypatch.setattr(time, "time", ...)`, 期望值按几何分档(`now <= base + 30` 当日首记录未入窗→base 桶空桶 None; 否则跨日长洞 null 字典); 测试计划第 17 行同步三档时钟说明
- `memory-bank/pitfalls/testing/flaky-midnight-daycount.md` —— 回写四次实证(两种新形态/判别法/处置/红验形状/为什么没命中)
- 未授权不做: commit/push; 存量 `test_traffic_snapshot.py` ts 粒度 flake(范围守恒)
