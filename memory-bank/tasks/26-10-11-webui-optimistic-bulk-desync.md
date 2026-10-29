# 26-10-11-webui-optimistic-bulk-desync — WEBUI 批量跳检后「批量开始」状态脱节修复(真值出口 + 前端回滚 + 快照回写)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-30
**Topics:** webui-optimistic-ui
**Summary:** 用户报「批量跳检成功后批量开始, UI 先显示下载、几秒后显示已停止, 而 qB 里种子已做种」。报告取证定为三条独立缺陷叠加(+ 一条加固): ①跳检收尾不回写快照; ②批量命令无真值出口(`bulk_torrents` 被整体列进延迟回执族 ⇒ drain 不给它 `defer_receipt` ⇒ `_truth_landed`/`_affected_hashes` 的 bulk 分支永不可达); ③前端兜底回滚打回「点击那一刻的旧值」+ 收敛判据与服务端不对称; ④`_sync_paused_state` 用陈旧完成位反推 state。按「止血 + 加固」修: 后端 6 处(收尾回写真值 / `is_deferred_receipt` 单点 / `CMD_ID_COMMANDS` / drain 守卫 / handler 回执分支 / 完成位联合判据) + 前端 3 处(回滚认 truthSnapshot / prev 保鲜 / 收敛同谓词) + 测试 3 处(替身保真 + 两条机械守阵)。全量结果见 kb.baseline。
**Refs:** memory-bank/plans/26-10-11-2040-plan-webui-bulk-skipcheck-start-desync.html,memory-bank/reports/26-10-11-2017-report-webui-bulk-skipcheck-start-desync.html

## 原始请求

> WEBUI批量跳检成功后批量开始UI会显示下载, 过几秒显示已停止, 实际上qb中种子状态已改为做种, 与qb脱节了, 分析原因, 写一个报告

第一轮先出报告(取证 + 逐层根因), 随后用户追问「不能直接走单种机制吗」→ 复读真值通路后发现 **bulk 的 truth 支路本就是为此写好的、只差名单归属放行**, 据此更新报告 §4.3 口径。第三轮用户令「修复问题」, 范围经选项问清后拍板 **止血 + 加固**(四条全做)。

## 思考过程与决策

### 为什么"走单种机制"不是拆成 N 次单种调用

单种 `resume_torrent` 不脱节, 靠的是 `defer_receipt → flush_truths → _affected_truth`(直查 qB `torrents/info`)→ 推 `truth` 事件这条通路; 而 bulk 与单种底层调的是**同一个** `QbApi.torrents_resume`, 差别只在传一个 hash 还是一次传全列表。所以「复用单种机制」= **共用真值通路**, 不是复用调用次数。拆成 N 次单种命令只多 N 次队列往返 + N 次主循环 tick。

### 关键发现: 那两条支路不是死代码

`_truth_landed` 的 `act = args.get("action") if cmd == "bulk_torrents" else ...`(按批量 action 分流)与 `_affected_hashes` 的 `hashes + keys` 组展开**都已写好**, 只是 `bulk_torrents` 被**整体**列进 `DEFERRED_RECEIPT_COMMANDS` ⇒ drain 走 `deferred=True` 分支 ⇒ 既不 `defer_receipt` 也不 `set_result`, `truth_pending` 里从来没有它 ⇒ 两条支路一步都走不到。修法是**按 action 分流归属**, 而非整条移出名单(那会害 `recheck` / `skip_check` / `add_torrents` 的聚合回执 —— 而本次症状的起点正是 `skip_check`)。

### 实施期才暴露的坑: cmd_id 的传递 ≠ 谁写回执

只做「按 action 放宽判定 + drain 写回执 + handler 不写」时, pause/resume 落进 `not deferred` 分支 ⇒ drain **不传 cmd_id** ⇒ handler 的 `if cmd_id:` 全假 ⇒ 「部分 hash 缺失 / 参数不合法」的 error 回执写不出来, 反被 drain 的 ok 覆盖(**4 条既有用例同时红**, 一次跑出来)。修法: 把「传不传 cmd_id」从 `deferred` 拆成独立判据 `CMD_ID_COMMANDS = DEFERRED_RECEIPT_COMMANDS | {"bulk_torrents"}` —— 这两件事本来就不同(handler 可能自写**错误**回执, 而成功回执归 drain)。

### 替身保真暴露的连锁(处置, 不回退)

`FakeClient.torrents_add` 保真为「`is_skip_checking=True` ⇒ 完成(`progress=1.0`)」后, 「跳检成功 ⇒ 种子已完成」成真 ⇒ 第二次跳检会先被 G3(`种子已完成`)或规则侧决策链 0(`种子非暂停中未完成`)拦下, **dedup(跨规则同日去重)闸门在保真语义下不可达**。真机同理(跳检后就是 `stoppedUP/100%`)。

- 处置: 两条既有用例(`test_ops_skip_check_day_shared_across_sources` / `test_checking_skip_dedup_across_rules`)在第二次跳检前把进度还原为「未完成」, 以单独验证去重闸门本身, 并注明原因 —— **保真保留**。
- 「dedup 被 G3 遮蔽」是**闸门顺序**问题, 超出本次范围, 未动闸门顺序(应另立 issue)。

### `amount_left` 不并入完成位判据

`TorrentRecord.amount_left` 的 slot **默认值就是 0**, 未同步的记录会被判成「已完成」(假阳性); `progress` 默认 `0.0` 无此问题。故完成位联合判据只并 `progress >= 1.0`。

## 实现计划

1. `ops_mod._skip_readd`: `restore_torrent` 前直查 `torrents_info` 并 `apply_delta` 回写 →
2. `webui/commands.py`: 抽 `is_deferred_receipt` 单点 + `_OPTIMISTIC_BULK_ACTIONS` + `CMD_ID_COMMANDS`; `_cmd_bulk_torrents` pause/resume 成功分支不自写回执 →
3. `webui/runtime.py`: `consume_commands` 用单点判定 + cmd_id 传递拆判 + `cmd_id not in self.results` 守卫 →
4. `qbapi._sync_paused_state`: 完成位联合 `progress >= 1.0` →
5. `static/shared/commands.js`: `_expirePending` / `_snapshotTruth` / `_optimisticSettled` 三处 →
6. `tests/helpers.py` 替身保真 + 两条机械守阵 + 两处去重用例调整 + 测试计划清单同步 →
7. 收尾: `dev.fmt` + `test.full` + 基线切片 + 报告口径修正 + 计划/档案 + `kb.index`/`kb.check`。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| P1 跳检收尾回写真值 | Done | `ops_mod._skip_readd`; 失败 fail-closed 记 warning, 不改跳检结论 |
| P2/P3/P4/P5 批量真值出口 | Done | `is_deferred_receipt` 单点 + `CMD_ID_COMMANDS` + drain 守卫 + handler 回执分支; 下游 `_truth_landed`/`_affected_hashes` 无需改动 |
| P6 完成位联合判据 | Done | `qbapi._sync_paused_state`; 只并 `progress`, 不并 `amount_left`(默认值假阳性) |
| F1/F2/F3 前端回滚与收敛 | Done | `commands.js`; 回滚认 `truthSnapshot` 现值 / `op.prev` 保鲜 / `_optimisticSettled` 与服务端同谓词 |
| T1 替身保真 | Done | `FakeClient.torrents_add`; 连带两处去重用例按保真调整 |
| T2/T3 机械守阵 | Done | 后端白名单遍历(真值出口存在) + 前端静态扫(回滚/收敛/prev 保鲜) |
| 报告口径修正 | Done | 报告 §4.3「死支路」→「可达性被名单归属切断」+ §4.3.1/§4.3.2 + §6.2 落点精化 |
| 收尾(闸门 + 协议产物) | Done | `dev.fmt` 过; `test.full` 全绿 0 failed(数字见 kb.baseline); 基线切片 `26-10-11-2040-webui-bulk-desync-fix`; 计划 `26-10-11-2040-*`; activeContext 切片; `kb.index`/`kb.check` |

## 进度日志

- **2026-10-11 (报告)** — 进程内探针实测 + 逐帧链路取证, 定为三条独立缺陷叠加 + 一条加固, 出报告 `26-10-11-2017-*`(8 章)。
- **2026-10-11 (口径修正)** — 用户追问「不能直接走单种机制吗」⇒ 复读 `runtime.py:995` / `:1013-1017`, 确认 bulk 的 truth 支路**已写好只是不可达**; 更新报告 §4.3 口径 + 新增 §4.3.1/§4.3.2 + §6.2 落点精化。`doc-updated` 抬到 `26-10-11-2028`。
- **2026-10-11 (实施 · 后端)** — P1(`_skip_readd` 直查回写) + P6(`_sync_paused_state` 联合判据) + P2/P3/P4/P5(bulk 真值出口)。首次 `test.quick` 6 红: 4 条是 cmd_id 未传递(见上「实施期才暴露的坑」), 2 条是替身保真连锁; 分别修 `CMD_ID_COMMANDS` 与调整去重用例后全绿。
- **2026-10-11 (实施 · 前端 + 守阵)** — F1/F2/F3 三处; 新增 T2(后端白名单遍历)与 T3(前端静态扫)两条机械守阵; 测试计划清单同步 `test_web_commands.py` / `test_web_seed_center.py`。
- **2026-10-11 (闸门 + 回写)** — `dev.fmt` 无额外改动(代码已合规); `commands run test.full` 全绿 / 0 failed / TOTAL 99%(数字与耗时采样见基线切片); 基线切片 `26-10-11-2040-webui-bulk-desync-fix`; 计划 `26-10-11-2040-*`; 报告口径修正; activeContext 切片; `kb.index`/`kb.check`。

- 2026-10-30 06:30 grilling 两轮+真机实测定稿: 认领 issue 26-10-01-2137(复验分岔: add ~34ms 已覆盖不改码; rename ~1.7s 与主备速度切 0~1.5s 立项); 追加实测 SSE 断退回轮询 ~1.19s 归因用户观察, 独立入池 26-10-30-0626-perf-webui-sse-down-poll-latency(暂不修)
