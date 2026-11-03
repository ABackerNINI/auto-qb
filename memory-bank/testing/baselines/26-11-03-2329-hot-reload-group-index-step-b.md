# 4997 passed + 10 skipped(根) —— 热重载分组索引修复 Step B 守阵与回归全量基线

> 摘要: 热重载分组索引修复 Step B 守阵与回归全量基线
> 基线时间: 2026-11-03 23:29
**Refs:** memory-bank/plans/26-11-03-2223-plan-hot-reload-group-index.html, memory-bank/issues/26-11-03-2206-bug-webui-hotreload-group-index-vanish.html

## 验收数字

`commands run test.full` 实测:

```text
TOTAL                                                23289    185   7948    158    99%
4997 passed, 10 skipped, 3 warnings in 177.79s (0:02:57)
```

口径注记:
- 3 条 warning 与 10 条 skipped 均为既有存量;
- TOTAL 语句数随 Step A(95a497d5) 删除 `store.reset_runtime` 的 3 个 `clear()` 同步减少;
- 本步新增 3 条守阵用例并改写 1 条既有用例, 通过面无退化。

## 本改动面

- `tests/test_webui_delta_mirror.py`: 改写 `test_unkeyed_command_source_yields_full` 的 reset 段
  (reset 保留分组索引的 D1=B 新语义, full 判定不变); 另以真实 `_leave_group` 解散组覆盖
  `row_key_unresolvable`(不再靠清空索引伪造场景)。
- `tests/test_torrents_store.py`: 新增 `test_store_reset_runtime_keeps_group_index` /
  `test_store_reset_runtime_no_regroup_cost`; 更新 `test_store_reset_runtime_marks_view_changed` 过时 docstring。
- `tests/test_modules_p5.py`: 新增 `test_l2_rebuild_group_view_not_empty`(首红验证: 回退
  `store.py` 至父提交 3adfc5d8 后该用例在 `len(store.groups) == 1` 处 0 == 1 失败)。
- 未改 `src/`; 修复本体在 Step A 提交 95a497d5(分支基线)。

