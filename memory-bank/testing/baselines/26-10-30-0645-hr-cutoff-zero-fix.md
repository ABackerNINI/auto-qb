# 4148 —— 4148 passed / TOTAL 99% —— HR cutoff_done<=0 位置证明退化修复后基线

> 摘要: 4148 passed / TOTAL 99% —— HR cutoff_done<=0 位置证明退化修复后基线
> 基线时间: 2026-10-30 06:45
**Refs:** memory-bank/issues/26-10-30-0550-bug-hr-cutoff-zero-position-proof.html, memory-bank/reports/26-10-30-0237-report-full-code-review-2.html

## 验收数字

`commands run test.full` 实测(2026-10-30 06:45, Windows, 修复落盘后):

```
TOTAL                                                20811    117   7128    107    99%
4148 passed, 10 skipped in 38.07s
```

- **汇总行**: **4148 passed / 10 skipped**, 墙时 **38.07s**(test.full 另一次采样 41.54s / 43.1s —— 单次数字不具基准意义, 区间口径见 testing/baseline.md「耗时与覆盖率口径」)。
- **TOTAL 表**: 语句 **20811** / 未覆盖 **117** / 分支 **7128** / partial **107** / 覆盖率 **99%**。
- **红验**: 新守阵 `test_position_proof_cutoff_zero_is_unprovable` 在临时移除 `_lane_covers_done` 的「`cutoff_done <= 0` ⇒ 不可证」守卫后**实测转红**(断言落在 `_lane_covers_done(zero["A"], real_done) is False`), 还原后复绿 —— 守阵有效, 非恒真断言。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/hr/service.py` | 新增模块级纯函数 `_lane_covers_done(st, done, slack=0.0)` —— 单档位置覆盖证明的**唯一口径**, 显式判死「`cutoff_done <= 0` = 没有位置概念 ⇒ 不可证」; 三处调用方 `_freeze_terminal`(终态冻结) · `_position_covered`(观察期推进) · `_absence_proven_all`(批量「未列出」签发) 由各自手写的 `done < st.cutoff_done` 改为共用它(`_absence_proven_all` 传 `slack=COVERAGE_SLACK`) |
| `tests/test_hr_service.py` | 新增守阵 `test_position_proof_cutoff_zero_is_unprovable`(零位置概念三判据 + 反向对照组 + 供给侧 `_update_cutoff` 整列失明恒 0 + `_freeze_terminal` 端到端), 头部「## 测试计划」同步 |
| `memory-bank/issues/26-10-30-0550-bug-hr-cutoff-zero-position-proof.html` | 认领: 状态 Open → Done, 补复验行与实际修法 / 验证方式 / 测试数字 |
| `memory-bank/testing/baselines/26-10-30-0645-hr-cutoff-zero-fix.md` | 本切片 |

**未改**: `_update_cutoff` 行为与 `HrLaneState.cutoff_done` 的「0 = 没有位置概念」语义保持原样(判据侧收敛, 不动供给侧与持久化契约); `nexusphp.REQUIRED_KEYS` 未纳入 done —— 理由见 issue「修复后补充」。
