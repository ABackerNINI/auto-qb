# 6186 —— relocate 单成员 direct 免暂停批全量基线

> 摘要: relocate 单成员 direct 免暂停批全量基线
> 基线时间: 2026-11-15 09:17
**Refs:** memory-bank/tasks/26-11-14-backend-relocate-single-direct-no-pause.md

## 验收数字

`commands run test.full` 实测(2026-11-15 09:17, Windows 开发机):

```text
TOTAL                                                27452     72   9654     77    99%
6186 passed, 2 skipped in 181.15s (0:03:01)
```

- 汇总: 6186 passed / 2 skipped, 覆盖率 99%(Windows 闸 99.5 差异面见 conftest COVERAGE_FLOOR 单点; 实测表尾 99% 由 pytest-cov 出)。
- 与上一切片的差值口径见 `memory-bank/testing/baseline.md`, 本切片不重复。

## 本改动面

- 实施批 S1-S2(commit a2c9e425, 5 文件 208 行): `relocate_units.is_complete_state` helper + 过渡态排除集 7 态(`_TRANSITION_EXCLUDED_STATES`, 口径参照 fuse `_NON_COMPLETE_STATES` 独立持有; checkingUP 唯一分歧态仍走暂停); `relocate_exec._start_job` 豁免判据(单成员且完成态 → 不下发 pause、`resume_hashes=()` 走 `_resume_members` 既有幂等 no-op) + 回执按形态分型(direct「qB 自搬中(无别名)」/ 多成员保留原文 / 豁免追加「单种子搬迁: 做种中不暂停, qB 自搬」)。
- 测试电池: `tests/test_relocate_exec_run.py` 新增 8 例(完成态免暂停/下载中/error/多成员/dry-run/文案分型逐态钉扎), `tests/test_relocate_units.py` 补 helper 守阵, `tests/test_relocate_exec_jobs.py` 既有断言计划内更新 1 处。
- S3 文档回写(commit a4057dce, 4 文件): 计划 26-11-14-1741 R2 实施回填 + 原计划 26-10-18-1604 §4.1 暂停行反指注记 + 任务档案/切片。
