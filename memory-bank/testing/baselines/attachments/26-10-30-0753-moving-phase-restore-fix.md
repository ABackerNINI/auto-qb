# 4160 passed + 10 skipped —— MOVING 相位崩溃恢复补发 setLocation 修复后基线

> 摘要: MOVING 相位崩溃恢复补发 setLocation 修复后基线
> 基线时间: 2026-10-30 07:53
**Refs:** memory-bank/issues/26-10-30-0616-bug-moving-phase-issue-restore.html, memory-bank/reports/26-10-30-0237-report-full-code-review-2.html, memory-bank/plans/26-10-30-0221-plan-full-code-review-2.html

## 验收数字

`commands run test.full` 实测(2026-10-30 07:53, Windows, 修复落盘后):

```
TOTAL                                                20860    113   7142    106    99%
4160 passed, 10 skipped in 40.67s
```

- **汇总行**: **4160 passed / 10 skipped**, 墙时 **40.67s** 区间口径见 testing/baseline.md「耗时与覆盖率口径」。
- **TOTAL 表**: 语句 **20860** / 未覆盖 **113** / 分支 **7142** / partial **106** / 覆盖率 **99%**。
- **红验**: 三条新守阵在**临时把 `_load_jobs` 的 `"recover"` 置 False**(等于回到旧行为)后实测转红 ——
  `test_restart_reissues_setlocation_when_never_issued`(无补发)、
  `test_restart_issued_without_evidence_keeps_polling`(现场判据未跑)、
  `test_restart_recovers_to_moved_when_data_already_at_dst`(停在 moving 不进 moved); 还原后复绿。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/core/modules/relocate_units.py` | `RelocateJob` 新增持久化字段 `move_issued`(是否已向 qB 下发过 setLocation) + `job_to_dict` / `job_from_dict` 往返(老账缺位按未下发) |
| `src/auto_qb/core/modules/relocate_mod.py` | `_start_job` 下发成功后落账 `move_issued`(新单点 `_mark_issued`); `_step_move` 的补发分支同样落账; `_load_jobs` 对 MOVING 置 `recover` 标记; 新增 `_recover` 按 `ru.recover_exec_phase` 三分流处置(仍在搬⇒轮询 / 数据已到 dst⇒进 moved / 未下发过⇒补发一次), 判完即交常规轮询 |
| `tests/test_relocate_exec.py` | 新增三条重启恢复守阵 + 头部「## 测试计划」同步 |
| `tests/test_relocate_units.py` | `test_job_dict_roundtrip` 扩测 `move_issued` 往返与老账缺位默认 |
| `memory-bank/issues/26-10-30-0616-bug-moving-phase-issue-restore.html` | 认领: Open → Done, 补复验 / 实际修法 / 验证方式 / 测试数字 |
| `memory-bank/testing/baselines/26-10-30-0753-moving-phase-restore-fix.md` | 本切片 |

**未改**: `recover_exec_phase` 纯函数契约(三分流语义与 `RECOVER_STALLED` 文案保持原样); 「已下发过但 qB 无现场」仍走停滞判据而不是立刻判失败 —— 理由见 issue「修复后补充」。
