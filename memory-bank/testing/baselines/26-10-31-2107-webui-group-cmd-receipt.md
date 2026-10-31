# 4308 passed, 2 skipped, 3 failed —— 组命令空组显式 error 回执(issue 26-10-31-1740)全量基线

> 摘要: 组命令空组显式 error 回执(issue 26-10-31-1740)全量基线
> 基线时间: 2026-10-31 21:07

## 验收数字

- `commands run test.full`(2026-10-31, 组命令空组兜底 + 新用例落地后):
  - 汇总行: `3 failed, 4308 passed, 2 skipped in 147.33s (0:02:27)`
  - TOTAL: `21812 stmts, 145 miss, 7400 branch, 121 partial, 99%`(门槛 99%, 达标)
  - 逐条口径注记: 3 条 failed 中 2 条为**存量**(远端同步带入, 无本改动状态下 stash 复跑同样红) —— `test_docs_forms::test_artifacts_meta_complete` / `test_status_vocabulary`, 根因是 26-10-31 RM02-RM09 计划件(`memory-bank/plans/`)缺 `doc-status` meta, 属计划外缺陷待另行处置; 第 3 条 `test_memory_bank::test_gen_all_check_is_green` 为本轮改 issue 状态后索引未重建所致, `commands run kb.index` 重建后复跑已转绿(16 passed / 2 failed 存量)。代码面 4308 全绿, 含新增 `test_group_commands_unknown_key_error_receipt`。
- 红验: 移除 `commands.py` 兜底(git checkout 还原)单跑新用例判红, 恢复后转绿。

## 本改动面

- `src/auto_qb/webui/commands.py`: 新增 `_group_empty_receipt` 兜底单点(空组 WARNING 日志 + 显式 error 回执, 文案两档: 查无此组「组不存在或已被解散」/ 成员删光「组内种子不存在或已被删除」); `_group_action`/`_cmd_delete_group` 空分支挂接; `_cmd_reannounce_group` 既有 elif 分支收编进同一单点; `_cmd_pause_group`/`_cmd_resume_group`/`_cmd_delete_group` 增 `cmd_id` 形参; 三命令加入 `CMD_ID_COMMANDS`
- `tests/test_web_commands.py`: 新增 `test_group_commands_unknown_key_error_receipt`(查无此组四命令零调用+error 回执+WARNING; 成员删光档; 存活组通路不回归); 文件头测试计划同步登记
- `memory-bank/testing/real-machine.md`: 「组命令对空组静默(缺陷在池)」判据行回写为已修口径
