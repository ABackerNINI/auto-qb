# 5789 —— 5789 passed, 2 skipped, 99% -- arm 侧上一世终态 journal 重置后全量基线

> 摘要: arm 侧终态账重置(issue 26-11-08-0827)后全量基线
> 基线时间: 2026-11-08 13:12

## 验收数字

- `commands run test.full`(实测 2026-11-08 13:0x, 124.2s): **5789 passed, 2 skipped**(7 warnings)
- 覆盖率 TOTAL 表: 25783 stmts / 18 miss, 8940 branch / 39 partial, **99%**
- 较上一基线(26-11-08-1142, 5782 passed): **+7 passed**(reconcile 新增 5 用例 + parametrize 展开 2 例, 另 stmts/branch 随实现小幅增)

## 本改动面

- `src/auto_qb/core/modules/relocate_exec.py` — 新增 `_reset_stale_terminal_journal` 挂 `_arm` 入口(issue 26-11-08-0827): 上一世 done/cancelled/failed 终态 journal 残留在再发起的 arm 处重置, 守卫 = 相位 ∈ STOP_PHASES 且 ts 早于本世 created_at(复用 `clear_journal` 主循环专属口); 清败/锚定不上/读不出(评审 finding 1: 读失败与账不存在混淆, 补存在性判别)三支搁置不武装下拍重试, rt 门限频告警, 证据删前留痕与 `_clear_stale_failed_journal` 同款
- `tests/test_relocate_exec_reconcile.py` — 新增 5 用例(done/cancelled parametrize 清账推进、清败搁置重试、锚定不上保守搁置、在途账不动、读不出搁置)+ `_arm_reset_env` 助手; 文件头测试计划清单同步
- `memory-bank/issues/26-11-08-0827-bug-relocate-arm-journal-reset.html` — 复验行 + 修复后补充, 状态 Open → Done
