# 4190 passed, 2 skipped —— rename 乐观回滚对称覆盖抽屉 detail 修复后全量

> 摘要: 认领修复 issue 26-10-30-0818: commands.js 新增 `_syncDrawerRollback` 把两条回滚出口(resolveOptimistic 失败分支 / _expirePending 兜底)对称覆盖到 drawer.detail, editRename 贴补丁时回填 op.prev 兜住行不在视图场景; rename 四态 node 电池加 7 条断言(25/25), test.full 全绿
> 基线时间: 2026-10-31 03:31
**Refs:** memory-bank/issues/26-10-30-0818-bug-webui-rename-rollback-drawer-detail.html

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 135.4s, 建档 03:31):

```
  TOTAL                                                21148     96   7164    100    99%
  4190 passed, 2 skipped in 133.74s (0:02:13)
```

- 汇总行: **4190 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, 实测 99.28%)。
- rename四态 node 电池单跑 25/25 过(test_webui_optimistic_rename_alt.py, 本轮加 7 条对称回滚断言)。

## 本改动面

- `src/auto_qb/webui/static/shared/commands.js`: 新增 `_syncDrawerRollback(hash, patch, rolled)`(回滚的抽屉对称面单点); resolveOptimistic 失败分支与 _expirePending 兜底各加一行调用 —— 行同款回滚值(op.prev / `t || op.prev`)对称写回 drawer.detail, 只写 patch 出现过的键。
- `src/auto_qb/webui/static/shared/drawer.js`: editRename 贴补丁时捕获抽屉旧名, detail 改新名的同时把旧名回填进 op.prev(行不在视图时 detail 是唯一旧名落点, 回滚才有原名可退); 方法头注释补回滚对称面口径。
- `tests/test_webui_optimistic_rename_alt.py`: rename 四态 node 电池加 7 条断言(失败/兜底两出口 detail 还原; 行不在视图回滚锚; 抽屉在别的 hash/已关不碰 detail; 兜底同回最后已知真值) + mkCtx api 桩空行表容错; docstring 测试计划同步。
- `memory-bank/issues/26-10-30-0818-bug-webui-rename-rollback-drawer-detail.html`: 复验/根因定案/修复后补充, 状态 Open → Done。
