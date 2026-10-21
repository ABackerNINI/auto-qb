# 3985 passed + 2 skipped —— S1 跳检闸门证据口径 + 回执聚合

> 摘要: S1 跳检闸门证据口径 + 回执聚合
> 基线时间: 2026-10-21 19:33
**Refs:** memory-bank/plans/26-10-21-1857-plan-skip-check-async-refactor.html

## 验收数字

```text
TOTAL                                                20761      73   7024      88    99%
3985 passed, 2 skipped in 132.72s (0:02:12)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%, 实测 99.41%), 在 S1 改动后的工作树上实测。
- 本轮新增 3 例守阵: `test_skip_gates_g7_evidence_and_blocker_identity` / `test_skip_gates_inflight_ttl_expires_leaked_registration` / `test_web_bulk_skip_check_receipt_aggregates_same_reason`。
- 既有用例口径更新 4 处(契约变更, 非放宽): G5/G7 文案「校验中」→「正在全量校验」; p=1 的 checking* 由 G3 改归 G5; 批量失败回执由「N 个失败 + 前 3 条原因」改按原因聚合; `_active_checks` 断言改用公开 API。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/core/taskqueue.py`: `_active_checks` 由 `Set` 改 `Dict[hash, monotonic]`(成员语义不变), 新增 `active_check_age(hash)` —— 供闸门判「登记泄漏」。
- `src/auto_qb/rules/checking_meta.py`: 新增 `INFLIGHT_TTL = 2 × CHECK_START_GIVEUP`(在途登记泄漏的兜底时长)。
- `src/auto_qb/torrents/store.py`: 新增 `state_since`(上报 state 变化/首见时记时刻) + `state_age(hash)`, 只服务闸门文案的「已 N 分钟」。
- `src/auto_qb/core/modules/ops_mod.py`: 新增 `_checking_evidence`(快照 `is_piece_checking` ∪ 带 TTL 的在途登记, 不发起 qB 查询)与 `_dur_text`; G5 补「快照在验」半边并前移到 G3 之前(已完成但在验 → force 而非 blocked); G7 改用 `_checking_evidence`(排除 `checkingResumeData`)、加文件映射一致前置(对齐 G8)、文案点名 blocker(hash8 + 名字 + state + 时长); G7/G8 共用一份组映射。
- `src/auto_qb/webui/commands.py`: 批量跳检/批量 recheck 的失败回执改**按原因聚合**(同因多目标只出一行), 删掉 `fail_msgs[:3]` 截断。
- 测试: 新增 3 例(见上), 更新 4 处契约断言; `tests/test_checking.py` 的私有结构断言改走 `active_check_hashes()`。
