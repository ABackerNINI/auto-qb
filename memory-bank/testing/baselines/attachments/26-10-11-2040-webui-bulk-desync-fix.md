# 3129 —— WEBUI 批量跳检后「批量开始」状态脱节修复(6.1~6.4)

> 摘要: 报告 `memory-bank/reports/26-10-11-2017-report-webui-bulk-skipcheck-start-desync.html` 四条根因的「止血 + 加固」修复(方案见 `memory-bank/plans/26-10-11-2040-plan-webui-bulk-skipcheck-start-desync.html`)。诊断: 批量跳检后批量开始, UI 先「下载」再「已停止」而 qB 已做种 —— 三条独立缺陷叠加(**①** 跳检收尾不回写快照 / **②** 批量命令无真值出口 / **③** 前端兜底回滚打回点击那一刻的旧值)**+** 一条加固(**④** `_sync_paused_state` 用陈旧完成位反推 state)。改动: **P1** 跳检收尾直查真值 `apply_delta` 回写记录(`ops_mod._skip_readd`); **P2** 抽 `is_deferred_receipt(cmd, args)` 判定单点 + **P3** 新增 `CMD_ID_COMMANDS`(cmd_id 传递与「谁写回执」解耦)+ **P4** drain 加 `cmd_id not in self.results` 守卫 + **P5** bulk pause/resume 成功分支不再自写回执 —— 批量 pause/resume 由此走回与单种同一条 `defer_receipt → flush_truths → truth` 通路(下游 `_truth_landed` / `_affected_hashes` 的 bulk 分支本就是为此写好的, 只是被 `DEFERRED_RECEIPT_COMMANDS` 的**整体归属**切断了可达性); **P6** `_sync_paused_state` 完成位联合 `progress >= 1.0`; **F1~F3** 前端兜底回滚改认 `truthSnapshot` 现值 + `_snapshotTruth` 保鲜 `op.prev` + `_optimisticSettled` 按 action 与服务端 `_truth_landed` 同谓词。加固/守阵: `FakeClient.torrents_add` 在 `is_skip_checking=True` 时保真为已完成(`progress=1.0`); 该保真暴露两处既有用例依赖旧假象(跳检后种子已完成 ⇒ G3 / 规则侧决策链 0 先拦, 走不到 dedup 闸门), 已按保真调整用例(还原进度以单独验证去重闸门, 并注明「dedup 被 G3 遮蔽」属闸门顺序问题、另置); 新增两条机械守阵(见下)。机检: `kb.check` 全绿。
> 基线时间: 2026-10-11 20:40

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `1733803f`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3129 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial; 本轮 33.56s, `test.full` 总 35.7s)
- 增量明细(本轮真正新增): **源** —— `core/modules/ops_mod.py`(`_skip_readd` 收尾直查真值回写) · `core/qbapi.py`(`_sync_paused_state` 完成位联合判据) · `webui/commands.py`(`is_deferred_receipt` 单点 + `_OPTIMISTIC_BULK_ACTIONS` + `CMD_ID_COMMANDS` + `_cmd_bulk_torrents` 回执分支) · `webui/runtime.py`(`consume_commands` 改用单点判定 + cmd_id 传递拆判 + results 守卫) · `webui/static/shared/commands.js`(`_expirePending` / `_snapshotTruth` / `_optimisticSettled` 三处); **测试** —— `tests/helpers.py`(FakeClient.torrents_add 保真) · `tests/test_ops.py` / `tests/test_checking.py`(dedup 用例按保真调整) · `tests/test_web_commands.py`(新增 `test_bulk_optimistic_actions_have_truth_channel`) · `tests/test_web_seed_center.py`(新增 `test_optimistic_rollback_and_settle_use_truth_not_stale_prev`)。**文档面**: 计划 `26-10-11-2040-*` + 报告 `26-10-11-2017-*`(§4.3 口径修正) + 任务档案 `26-10-11-webui-optimistic-bulk-desync.md` + 本切片 + `activeContext/26-10-11-2040-webui-bulk-desync-fix.md`。
- 机检: `commands run kb.check` 全绿。**新增守阵**: ① 后端 `test_bulk_optimistic_actions_have_truth_channel` —— 按乐观白名单遍历断言「不在延迟回执族 + 走完 drain 后 `truth_pending` 有条目 + 回执由 drain 写」, 反向断言非乐观批量动作保持延迟回执族; ② 前端静态 `test_optimistic_rollback_and_settle_use_truth_not_stale_prev` —— 读 `commands.js` 断言回滚认 `truthSnapshot` / `op.prev` 保鲜 / `_optimisticSettled` 的 action 分支。两条均为「删掉实现即红」形态。

## 风险 / 观察

- **P3 是实施期才暴露的坑**: 只做 P2/P4/P5 时, pause/resume 会落进 `not deferred` 分支 ⇒ drain **不传 cmd_id** ⇒ handler 写不出 error 回执(部分 hash 缺失 / 参数不合法), 反被 drain 的 ok 覆盖 —— 4 条既有用例同时红。修法: 把「传不传 cmd_id」从 `deferred` 拆成独立的 `CMD_ID_COMMANDS` 判据(`cmd_id` 传递与「谁写回执」是两件事)。
- **替身保真的连锁(已处置, 非回退)**: T1 让「跳检成功 ⇒ 已完成」成真 ⇒ 第二次跳检被 G3 / 决策链 0 先拦, dedup(跨规则同日去重)闸门在保真语义下**不可达**(真机同理)。本方案只调整用例(还原进度单独验闸门), **未动闸门顺序**; 「dedup 被 G3 遮蔽」属闸门顺序问题, 超出本次范围, 需另立 issue。
- 报告 §7.2 的 **H1**(增量同步同轮同时上报「删除 + 重加」时 `store._apply` 的 `by_hash.pop` 隐患)仍为**待真机确认**的假设, 本轮未处置。
