# 5211 passed, 10 skipped (TOTAL 99%: 24457 语句 / 227 未覆盖 / 8386 分支 / 167 partial) —— 修复缺失站点扫描批量失败误报(26-11-04-2347)后全量

> 摘要: 修复缺失站点扫描批量失败误报(26-11-04-2347)后全量
> 基线时间: 2026-11-05 01:07
**Refs:** memory-bank/tasks/26-09-26-webui-sites-import.md,memory-bank/issues/26-11-04-2347-bug-missing-scan-partial-failure.html

## 验收数字

`commands run test.full` 实测(2026-11-05 01:05, Windows 本机, issue 26-11-04-2347 修复工作树):

```text
TOTAL                                                24457    227   8386    167    99%
5211 passed, 10 skipped in 140.43s (0:02:20)
```

- TOTAL 行口径: 语句 24457 / 未覆盖 227 / 分支 8386 / 分支 partial 167, 覆盖率 99%。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `src/auto_qb/core/exporter.py`: collector 拆 `collect_torrent_tracker_hostnames_with_failures`(返回 `(torrent_sets, failed_count)`), 原函数改薄包装(签名不变); 新增批量失败判据单点 `tracker_scan_batch_failed`(有种子且失败过半=严格多数); `export_yaml_template` 批量失败抛 `TrackerScanBatchError`。
- `src/auto_qb/infra/errors.py`: 新增 `TrackerScanBatchError(AutoQbError)`; 基类 docstring 子类清单同步。
- `src/auto_qb/webui/server/routes/sites.py`: `/api/sites/missing` 改用 with_failures 变体, 过半失败映射 502(detail 带失败比例)。
- `tests/test_exporter.py`: +4(`with_failures_counts` / `threshold` 边界 / `batch_failure_raises` / `minor_failure_still_exports`)。
- `tests/test_web_backend_misc_sites.py`: +2(批量失败 502 带 3/3 / 单种失败容忍回归)。
- `memory-bank/issues/26-11-04-2347-*.html`: 复验/修复记录回填, 状态 Open → Done。

## 真机自检

本轮未跑真机轨: 改动是错误路径的失败计数/阈值/异常映射逻辑, 纯桩可验(6 条新测试全覆盖); 触发条件本身是「qB 扫描中途断连/重启」的确定性时序, 真机无法稳定复现, 桩与真机对结论无失真差异。
