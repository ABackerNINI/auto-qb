# 乐观 UI「撤下」改造 (P0–P3 详述)

> 摘要: 乐观 UI 从「移除」改为「保留 + 简化」的完整过程: 六处机制拆解 / 真机实测五段归因 / D2 决策 / SSE 通道选型。
> 触发: 乐观 UI, 撤下, pending, 真值, SSE, D2, 归因, 2947ms

> 迁移说明(2026-09-22 W4): 原在 `activeContext.md` 的「正在进行」里, 单条就超主题文件的 10 KB cap ⇒
> 按「超了就外迁」整条移到这里, **内容逐字未改**。

- **⓪b 乐观 UI「撤下」改造已完成并入库 (2026-09-21, 提交 `2094a36`)**:
  ✅ 真机实测撤下 **2947ms → 85ms**; 服务端侧只占 21ms, 其余 64ms 在浏览器主线程
  (大库渲染, 属前端性能议题)。下列条目按时间留档, 含中途的方案修订过程。
  - **调查报告** [docs/26-09-20-1806-optimistic-ui-half-fix-report.html](../docs/26-09-20-1806-optimistic-ui-half-fix-report.html)
    —— 根因与实测留档(bulk 缺真值 / 撤下判据过严 / 真值落地 1362ms)。
  - **可行性报告** [docs/26-09-20-2131-optimistic-ui-event-driven-feasibility.html](../docs/26-09-20-2131-optimistic-ui-event-driven-feasibility.html)
    （延迟链路拆解 / 通道选型 / 风险）。
  - **⭐ 实施计划（当前以此为准）**
    [docs/plans/26-09-20-2139-webui-truth-direct-query-and-optimistic-removal-plan.html](../docs/plans/26-09-20-2139-webui-truth-direct-query-and-optimistic-removal-plan.html)
    —— **三条硬指令**: ① 真值**不得从 `/sync/maindata` 读**, 改 **`torrents/info` 直查**
    (`QbApi.torrents_info` 已在 qbapi.py:306); ② **事件驱动(SSE), 不依赖轮询**;
    ③ **端到端反应 ≤10ms ⇒ 移除整套乐观 UI**。
    ⚠ 已提示: qB 单次 pause/resume 就 8.4ms, 理论下界 ~15~25ms, **10ms 可能差一点**(决策 D2);
    批量 448 目标用 `hashes=` 拼 URL ≈18KB 会超限(决策 D3)。
    P0 = 先实测门槛(**sim_qb 需加"maindata 快照 1.5s / info 实时"模型**才能复现), 未达标不动代码。
  - 🔄 **计划已修订(22:12): 乐观 UI 由"移除"改为「保留 + 简化」** —— 用户指示"乐观 UI 不取消,
    不过需要简化模型, 当前的模型错误太多"。§04 已重写: 撤下链路现有 **6 处互相咬合的机制**
    (`_snapshotTruth` / `_optimisticSettled` / `_settleFromTruth` / `_pullTruthAfterCmd` /
    `_expirePending` 3s 兜底 / `via` 分档), **近几轮追到的 bug 几乎全部来自 2~5**,
    而不是来自"要不要乐观" ⇒ 删 2~5, **只留"贴上 + 等推送结果"两步**。
    红线"不采纳命令前旧值"**上移到服务端**(真值已改直查, `_truth_landed` 能可靠判"是否已生效",
    未生效就不发 ok) ⇒ 前端不必再自己判。
    P3 不再依赖 P0 门槛; 门槛数字现在只决定压暗还要不要(D2)与未知超时(D4, 建议 8s)。
  - **已实施 P1(真值改直查, 2026-09-20 21:55)**, 单测 **1062 → 1063 passed**:
    `WebUIRuntime._affected_truth` 改走 `torrents/info`(**不再读 `store.by_hash` 同步快照**),
    带分批 `TRUTH_QUERY_CHUNK=50`(448 个 hash ≈18KB 会超 URL 长度限制);
    取不到**返回 None 不回落快照**(回落会把"读不到"伪装成"读到了旧值")。
    新增守阵 `test_affected_truth_reads_qb_directly_not_sync_snapshot`(故意让快照与 qB 客户端
    不一致, 真值必须等于客户端那一侧)。另修了桩 `_make_grouped_manager` —— 它只 seed store、
    **`client.torrents` 是空的**, 与真机不符(直查会查不到)。
    实测(sim_qb 零滞后): 单种子暂停撤下 **228ms**(改前 90ms) —— **仿真里直查是纯开销**,
    因为没有快照滞后可省; 真机收益待 P0 确认。
    ⚠ **直查只在走 `defer_receipt` 的命令上生效**: `bulk_torrents`(整剧/整集/多选)仍走
    "handler 自写回执", **根本不调用 `_affected_truth`** ⇒ 整剧无直查、遥测仍 0 行,
    **必须在 P2 一并接入**。
  - ⚠ **顺带发现的既有缺陷(未改, 待定夺)**: `tests/test_web.py` 里
    `test_truth_hold_budget_matches_backend` **同名定义了两次**(约 3910/3933),
    Python 后者覆盖前者 ⇒ **第一条静态守阵从未被执行**。
  - **已实施 P2(事件驱动 SSE, 2026-09-20 22:45)**, 单测 **1063 passed**:
    · 后端 `WebUIRuntime.subscribe/unsubscribe/notify`(有界队列 `EVENT_QUEUE_MAX=200` +
      `put_nowait`, 满则丢) + `GET /api/events` SSE 端点; 推 `cmd`(`set_result` 处, 带 cmd_id)
      与 `ver`(`_publish_locked` 处, **只带版本号**)。**主循环只 put 队列、不碰 socket**。
      心跳 `SSE_KEEPALIVE_S=5s` —— **必须 < WEB_VIEW_TTL(10s)**, 否则客户端被判不活跃
      ⇒ 主循环停摆 ⇒ 推送自锁。订阅/退订各记一条 INFO 便于排查句柄堆叠。
    · 前端 `startEvents/stopEvents`(startPolling 接、unmounted 断); `waitCmd` 改为
      **推送与轮询赛跑**(SSE 断了自动退回); `ver` 事件去抖 60ms 触发 refresh。
    · 鉴权: `EventSource` **发不出 Authorization 头** ⇒ 服务端放行 `?token=` 兜底。
    · 实测(独立 SSE 客户端 ×3): 推送 202/299/239ms vs 轮询 244/321/278ms ⇒ **早 23~41ms**
      (落点不同最多省 ~500ms = 原 0→150→300→500ms 退避粒度)。
    ⚠ **验证前端改动要防浏览器缓存**: agent-browser 的 Chrome 缓存 `/shared/*.js`,
      页面可能仍在跑旧包(实测页面里 `AQB_COMMANDS` 只有 2 个键, 服务端文件是新的)。
  - ✅ **D2 已实施(2026-09-20 23:45)**, 单测 **1063 passed**:
    · 服务端 `defer_receipt` 改为**回执立即写**(**不带 truth**) + 真值登记 `truth_pending`;
      `flush_receipts` → **`flush_truths`**(直查 → 落地才推 `truth` 事件, **超时不推**)。
      `RECEIPT_WAIT_CAP_MS`(1200) → **`TRUTH_PUSH_CAP_MS`(8000)**。
    · 前端**压暗与值覆盖拆开**: 回执到 ⇒ `op.grey=false`(撤下) + `op.hold=true` 继续覆盖值;
      `truth` 事件到 ⇒ `onTruthEvent` 写真值 + 删 pendingOps。删掉三处
      `_settleFromTruth`/`_pullTruthAfterCmd`(1500ms 预算是撤下 2947ms 里的 1688ms 大头)。
      `_markCmdSettle` 判据从"pendingOps 清空"改为"没有 op 还在 grey"。
    · **实测①(sim_qb 注入 1250ms 延迟)**: `贴上 0ms / 回执 2ms / 撤下 9ms`。
    · ✅ **实测②(真机 23:53 暂停种子)**: `贴上 0ms / 回执 70ms / **撤下 85ms via=receipt**`,
      真值 1624ms 后独立推送(7 轮 ×~200ms)。**撤下 2947ms → 85ms(34.7 倍), 不弹回。**
      真值仍要 1.25~1.6s(qB 自身节奏) 但**不再影响观感** —— 压暗 85ms 就结束、
      值覆盖撑到真值事件到达。另: 真值等待轮次改打 DEBUG(一次 7~8 条 INFO 会刷屏)。
    · 顺带合并了重复守阵(两条 `test_truth_hold_budget_matches_backend` → 一条
      `test_truth_hold_matches_truth_push_cap`), issue 26-09-20-2212 的问题已消除。
    · **撤下 85ms 的归因已完成(00:26 真机 resume)**: 贴上 0 / POST 24 / 执行 2.3 /
      **事件 21**(服务端推送到浏览器) / 回执 61 / 撤下 85。
      ⇒ **服务端侧只占 21ms; 浏览器侧占 64ms**(事件→兑现 40ms 主线程排队 + 兑现→渲染 24ms)。
      剩余属**前端大库渲染性能**议题, 与真值链路无关 ⇒ **到此收尾, 可提交**。
      `[perf]` 现在无条件一行打全五段(贴上/POST/排队/执行/回执/事件/撤下), 便于后续归因。
  - ✅ **P3 收尾清理已完成(2026-09-21 01:10)**, 单测 **1092 passed**(上游 rebase 带进新用例):
    · **删死代码 58 行**: `_settleFromTruth` + `_pullTruthAfterCmd` —— 真值改 `truth` 事件推送后
      已无引用。静态守阵加了**反向守阵**(这两个不许复活)。
    · ⚠ **修了一个真遗漏**: `shows.js`(追剧页集行)**此前漏改**, 还在跑 1500ms 拉取预算,
      撤下比种子页慢一大截 ⇒ 已改成与种子页一致的路径(`via=receipt`)。
    · `via` 分档 5 档(含 truth/pull/stale) → **2 档**(receipt/push)。
    · ❗**刻意保留** `_snapshotTruth` / `_optimisticSettled` / `reapplyPending` —— 它们是
      **SSE 断线时的安全网**: 推送丢了以后, 轮询带回的 `/api/state` 一旦含真值就提前收工;
      没有它, SSE 一断就是"命令其实成功、8 秒后却回滚"的假失败。守阵注释已写明勿删。
    · 实测(sim 1250ms 延迟): 撤下 7ms、`via=receipt`。
    ✅ **P3 已提交 `59754eb`**(Gitee + GitHub 均推上)。与上一批 `0c18fcd` 分两个提交, 便于单独回看/回滚。
  - ✅ **后端 `[cmd]` 诊断日志全部降为 DEBUG(提交 `dbceef4`)**: 用户指示"后端的桩调为 DEBUG,
    前端保留" ⇒ SSE 订阅/退订、真值已推、真值未落地、补刷新、命令排队/执行的**正常分支**全降
    DEBUG; **异常(真值超时 / 补刷新>300ms / 直查失败)仍 WARNING**。前端 `[perf]` 一行保留。
    ⚠ 改动带出守阵: `test_cmd_timing_is_logged_without_browser` 写死了"快命令=INFO"的级别断言
    ⇒ 已改 DEBUG 并**补反向断言**(INFO 级别下必须捞不到), 防以后改回 INFO 不报警。
    ⚠ **GitHub 镜像本次直连失败**(21085ms 超时)—— 按约定只报一次、不重试; 主线 Gitee 已推上。
    镜像滞后一个提交(`dbceef4`), 后续提交会自动带上。
  - ✅🔴 **P0 已实测(2026-09-20 23:15 真机 · 暂停种子) —— E1 判定为分支 B, 计划的关键前提变了**:
    ```
    [cmd] pause_torrent: 执行 2.7ms / 补刷新 2.9ms
    连续 7 轮「等真值落地」(每轮 ~200ms) => 回执 1259ms(踩 1200ms 上限照发)
    [perf] pause: 贴上 0ms / 回执 1259ms / 撤下 2947ms via=pull  (1 个目标)
    ```
    ① 这是**暂停**不是开始, 且 qB 执行仅 2.7ms ⇒ **"暂停本来就快"这个旧推论也被推翻**;
    ② 真值此刻已走 P1 的 `torrents/info` **直查**, **连直查都要等 ~1.25s**
       ⇒ 滞后**不在我们的同步快照, 而在 qB 自己**;
    ③ ⇒ **E1 = 分支 B**: qB 自身把状态翻过来要 >1.2s, 我们绕不开。
    **结论: 「撤下 10ms」在"依据真值"的前提下不可达**(差两个数量级, 不是差一点)。
    但**仍值得做完 P2+P3**: 2947ms 里有 **1688ms**(2947−1259) 是我们自己的拉取开销, 可整段拿掉
    ⇒ 改造后 ≈ 1.25~1.3s。
    🔴 **新增阻塞决策 D2**: 建议服务端**不再为等真值扣留回执**(正是它把回执推到 1259ms),
    改为"执行完即发回执 + 真值稍后作为独立 truth 事件推送" ⇒ 撤下可降到 10~20ms 且不弹回。
  - **新增 `scripts/dev_webui.py`(2026-09-20 23:05)**: 一键起"只开 WEB UI"的 auto-qb 连真机,
    用来看界面/试交互。生成**最小配置**到独立数据目录(默认 `%TEMP%/auto-qb-dev-webui`),
    关掉所有带开关的自动任务(规则/集数标签/标签清理/缺文件扫描/站点标签), 只留同步快照+WEB UI,
    默认端口 8177 并自动开浏览器。已用仿真端当"假真机"验证通过(300 种子连通)。
    ⚠ 两条硬知识: ① **`dry_run` 不能用** —— 项目里 `if not dry_run and web.enabled` 才起
    WEB 服务, 开 dry_run 等于没界面; ② 规则是**按键名 `_rules` 结尾自动发现**的,
    "没有规则"= 不写任何 `*_rules` 段, 写 `rules_config: {}` 会被 `validate_config`
    判"未知键"(已实测报错)。③ WebUI 上的**手动**命令会真的作用到 qB(点暂停即真暂停)。
  - **已入池 issue**: ① `26-09-20-2145-test-sim-qb-maindata-snapshot-lag`
    (sim_qb 缺"maindata 快照滞后"模型) ② `26-09-20-2212-test-duplicate-test-name-shadowed-guard`
    (`test_truth_hold_budget_matches_backend` 同名两次, 前一条守阵从未执行)。
  - ⚠ **用户纠正了目标两次**: ① 不是"让撤下变快", 而是 **让真值更快到 + 撤下依据真值 +
    **事件驱动、不依赖轮询**; ② 曾误推"暂停已好"—— 90ms 是 sim_qb 零延迟的数, 真机不成立。
  - **结论**: 我们自己加在链路上的延迟约 **1.5~2s**(回执轮询退避 0/150/300/500ms +
    `_pullTruthAfterCmd` 1500ms 预算 + `/api/state` 轮询 1.5/2/3s), 事件驱动可整体去掉;
    **qB 那侧还有 ~1362ms**, 是"等 qB 内部"还是"等 sync 快照 1.5s 刷新"**尚未判定**。
  - 🔴 **阻塞项 E1(必须先做, 约半天)**: resume 后同时轮询 `torrents/info` 与 `/sync/maindata`,
    看谁先翻。分支 A(快照滞后) ⇒ 改直查即压到几十 ms; 分支 B(qB 内部慢) ⇒ resume 下界 1.4s,
    **「撤下 10ms」与「撤下依据真值」在 resume 上互斥**。
  - 通道选型 **SSE**(FastAPI 原生、零新依赖、自带重连);`websockets` **当前未安装**, WS 需新依赖。
    挂点: `set_result`/`flush_receipts`(推 cmd) + `_publish_locked`(推 ver);
    **主循环只 put 队列, 绝不直接写 socket**。
  - ⚠ **真值变快后, `「真值 == 预测值」`的严格相等会立刻成为新瓶颈**(resume 预测 2 种 vs 落地态
    6 种), 必须与推送同期改成**分动作判据**。
