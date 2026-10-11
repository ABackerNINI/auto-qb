# 26-10-11-2040-webui-optimistic-ui — 批量跳检后「批量开始」状态脱节修复

> 摘要: 专题 `webui-optimistic-ui`。用户报「批量跳检成功后批量开始, UI 先显示下载、几秒后显示已停止, 而 qB 里种子已做种」。先出报告取证(三条独立缺陷叠加 + 一条加固), 期间用户追问「不能直接走单种机制吗」⇒ 复读真值通路确认 **bulk 的 truth 支路本就是为此写好的、只差名单归属放行**, 修正报告口径; 用户令「修复问题」后按 **止血 + 加固** 修完: 后端 6 处(跳检收尾回写真值 / 批量 pause-resume 补真值出口 P2~P5 / 完成位联合判据) + 前端 3 处(回滚认 truthSnapshot / prev 保鲜 / 收敛同谓词) + 测试 3 处(替身保真 + 两条机械守阵)。`test.full` 全绿(数字见 `commands run kb.baseline`)。**遗留**: dedup 闸门被 G3 遮蔽(待另立 issue) + 报告 H1 待真机确认 + 真机验收未做。
> 最后活动: 2026-10-11 20:40
> 状态: Done(本专题本轮完结)

## 现在做到哪

用户报「批量跳检成功后批量开始, UI 先显示下载、几秒后显示已停止, 而 qB 里种子已做种」。

先出报告取证(三条独立缺陷叠加 + 一条加固), 期间用户追问「不能直接走单种机制吗」⇒ 复读真值通路, 确认 **bulk 的 truth 支路本就是为此写好的、只差名单归属放行**, 据此修正报告口径; 用户令「修复问题」后按 **止血 + 加固** 修复完毕:

- **后端 6 处**: 跳检收尾直查真值回写(P1) · 批量 pause/resume 补真值出口(P2~P5, 按 action 分流归属 —— `is_deferred_receipt` 单点 + `CMD_ID_COMMANDS` + drain `results` 守卫 + handler 回执分支) · `_sync_paused_state` 完成位联合判据(P6)
- **前端 3 处**: `_expirePending` 回滚认 `truthSnapshot` 现值 · `_snapshotTruth` 保鲜 `op.prev` · `_optimisticSettled` 按 action 与服务端 `_truth_landed` 同谓词(F1~F3)
- **测试 3 处**: 替身保真(`FakeClient.torrents_add` 跳过校验 ⇒ 已完成) + 两条机械守阵(T2 后端白名单遍历 / T3 前端静态扫)
- 全量测试全绿(数字与耗时见 `commands run kb.baseline`)

## 产物

- 计划: `memory-bank/plans/26-10-11-2040-plan-webui-bulk-skipcheck-start-desync.html`
- 报告: `memory-bank/reports/26-10-11-2017-report-webui-bulk-skipcheck-start-desync.html`(§4.3 口径已修正为「可达性被名单归属切断」)
- 档案: `memory-bank/tasks/26-10-11-webui-optimistic-bulk-desync.md`
- 基线: `memory-bank/testing/baselines/26-10-11-2040-webui-bulk-desync-fix.md`

## 下一步 / 遗留

- **「dedup(跨规则同日去重)闸门被 G3 遮蔽」** —— 替身保真后暴露: 跳检成功 ⇒ 种子已完成 ⇒ G3 / 规则侧决策链 0 先拦, dedup 在保真语义下不可达(真机同理)。属**闸门顺序**问题, 超出本次范围, **待另立 issue**。
- 报告 §7.2 的 **H1**(增量同步同轮同时上报「删除 + 重加」时 `store._apply` 的 `by_hash.pop` 隐患)仍是**待真机确认**的假设, 本次未处置。
- **真机验收未做**: 多选一批暂停未完成的辅种 → 批量跳检 → 立即批量开始, 行状态应直接稳定在「做种」, 不再出现「下载 → 已停止」。
