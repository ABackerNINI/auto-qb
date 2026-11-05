# 4804 passed + 2 skipped —— 修复 issue 26-11-01-0050 后全量测试基线

> 摘要: 修复 issue 26-11-01-0050(LiveTail 陈旧间隔)后全量测试基线
> 基线时间: 2026-11-02 00:56
**Refs:** memory-bank/issues/26-11-01-0050-bug-traffic-sample-livetail-stale-interval.html

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 工作树含本 issue 的源码修复与新增守阵
- `commands run test.full` 实测(2026-11-02, Windows 本机, 回写落盘后最终态复跑):
  - 汇总行: `4804 passed, 2 skipped in 167.81s (0:02:47)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- **环境 / 工具**: Windows 本机(win32 10.0.26300 x64 · 32 逻辑核)· Python 3.13.14 · pytest 9.2.0 · pytest-xdist 3.8.0 · `addopts = -n 8 --cov=src --cov-report=term-missing --cov-branch`; `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- 源码: `src/auto_qb/core/modules/traffic_sample_mod.py` —— `_publish_live_tail` 的 `interval_s` 分支加 `has_block` 守门(无块时取当前生效间隔)。
- 测试: `tests/test_traffic_sample.py` —— 新增 `test_w5_live_tail_interval_change_reset_window_uses_effective`, 并补进文件头「## 测试计划」清单(相对上基线净增 1 条用例)。
- 知识库: 本基线切片、activeContext 切片(认领链)、issue 状态与结论回写; 零其他 `src/` 改动。
