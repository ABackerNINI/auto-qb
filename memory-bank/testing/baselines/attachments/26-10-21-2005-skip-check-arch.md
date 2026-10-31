# 3986 passed + 2 skipped —— S2 跳检相位机 + 删除不摘记录

> 摘要: S2 跳检相位机 + 删除不摘记录
> 基线时间: 2026-10-21 20:05
**Refs:** memory-bank/plans/26-10-21-1857-plan-skip-check-async-refactor.html

## 验收数字

```text
TOTAL                                                20867      82   7038      90    99%
3986 passed, 2 skipped in 128.19s (0:02:08)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%, 实测 99.38%), 在 S2 改动后的工作树上实测。
- 本轮新增 1 例守阵: `test_skip_check_no_sleep_polling_and_keeps_record`(相位机零 sleep + 删除不摘记录 + 运行状态零写入 + 调用序 export→delete→add→add_tags)。
- 既有跳检用例(test_ops / test_checking / test_actions / test_web_skip_check / test_web_keys 共 131 条)在相位机改造后全部原样通过 —— 行为等价性证据。
- 一处契约断言更新: `test_skip_checking_delete_not_confirmed` 的失败文案由「仍在客户端」改「确认删除失败」(直查异常 = 未确认, fail-closed; 旧实现把异常吞成"仍在")。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/core/modules/ops_mod.py`: 跳检执行体由「同步四阶段 + `_poll_until` sleep 轮询」改为 `SkipJob` 相位机(准备/删除/确认消失/重加/确认出现/收尾), 每步至多 1 次写 + 1 次存在性读, 等待用 `_SKIP_BACKOFF_MS`(10/20/50/50/50ms), 总时长受 `SKIP_DRIVE_TIMEOUT`(30s) 约束; 删掉 `_poll_until`/`_skip_delete`/`_skip_readd`; 失败按「种子在 / 不在 / 看不见」三分流(`_skip_fail`: 在→清备份, 不在→撤记录留备份, 看不见→都不动)。
- `src/auto_qb/core/qbapi.py`: `torrents_delete` 新增 `keep_record=False` 形参 —— 跳检传 True, 删除不摘快照记录(避免 delete+add 同上报间隔内踩「增量 diff 只给变化字段 → 新建记录缺字段」); 普通删除行为不变。
- `tests/test_ops.py`: 新增相位机守阵 1 例(零 sleep / 记录不摘 / 状态零写 / 调用序)。
- `tests/test_actions.py`: 删除确认异常路径的文案断言随新口径更新(fail-closed)。
