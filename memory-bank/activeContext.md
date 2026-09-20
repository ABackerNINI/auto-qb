# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-20 (**最新: 列设置多标签页整份覆盖已修并验证, issue 26-09-20-1800 置 `Fixed`; 未提交, 剩真机走查** —— 见「待用户真机走查」末条。其前一条状态: 乐观 UI「撤下」已定案并推送 `4df80dc`; 剩真机复测确认) ——
  后端三段都很快(排队 0 / 执行 8.4 / 补刷新 88ms), 慢的是**前端撤下** —— 根因是**回执写在补刷新之前**,
  前端拿到回执立刻 refresh 取到的一定是旧快照。修法: 回执改到补刷新**之后**写并带真值
  (`WebUIRuntime.flush_receipts` + 前端 `_settleFromTruth`), 服务端等真值落地再发回执(上限 1200ms)。
  仿真端到端: 暂停撤下 68~127ms / 开始撤下 60~63ms、`via=truth`; 单测 **1058 passed**;
  冒烟 ok 54 / error 54 / hang 8 项 0 失败。**待真机复测**: 看 `[perf] … via=` 是
  truth / stale / pull 中的哪一个(详见 pitfalls 末条)。

## 正在进行

- **⓪ 规则条件表达式化 (2026-09-20/21, W1 已提交 `93f1911`)**: 计划
  [docs/plans/26-09-20-2225-rule-conditions-expression-plan.html](../docs/plans/26-09-20-2225-rule-conditions-expression-plan.html)
  (v3: 五条拍板口径 + §11 动作是否纳入的三档分析, L1 动作参数表达式记为候选排在 python 插件之后)。
  **W1 已入库 `93f1911`**(语法内核: errors/lexer/parser + 15 条测试, 未接规则系统)。
  **W2 已入库 `a1841e9`**(取值面 env + 求值 eval + 类型规则 types + `ExprCondition` + `RuleContext.expr_cache` +
  **`base.py` 出错即停规则 `(False, True)`** + 校验/schema/前端接线)。
  **W3 收尾(本轮)**: `sys.upload_today/download_today/upload_month`(Traffic Monitor dat)+ **配置期数据源门控**
  (`_expr_gate` → `_validate_rules(rules_config, errors, cfg)` → expr 单独分发, 门控跑在曲线段校验之前故须容忍
  结构非法的 `traffic_source`)、前端 expr 渲染为多行文本框、知识库回写(rule-system.md 新增「表达式条件」章 +
  出错即停语义、`modules.md` 加 `expr/` 行、`conventions.md` 立「新条件字段一律先进 env.py」)。
  实测 1062 → **1094 passed**(Windows; Linux 侧未同步重测, 已在 testing.md 标注)。
  已知坑: ①解析器"一层一运算符"判定必须在消费二元运算符后给 `used` 赋值, 否则退化成笼统报错;
  ②语义校验(types.py)与运行期求值(eval.py)的报错文案不同源, 测试按文案匹配时容易写错预期。

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
    ⚠ 上一批已提交 `0c18fcd`; **P3 这批尚未提交**。
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
- **① 上轮计划复核的收尾(只剩第 7 项) (2026-09-19)**: 复核报表

- **② WEB UI 操作跟手性优化 (2026-09-19)**: 三波次全部入库(`10e06a8` 分层节拍 + 命令唤醒 + 乐观 UI + 批量合单
  / `5d1e52c` 请求超时 + 视图分片回传 + 只读缓存 / `366092d` 行窗口化)。计划
  [docs/plans/26-09-19-1241-webui-responsiveness-plan.html](../docs/plans/26-09-19-1241-webui-responsiveness-plan.html); 档案 [tasks/26-09-19-webui-responsiveness.md](tasks/26-09-19-webui-responsiveness.md)。
  **剩**: 真机走查(真实 qB 数据下的观感)。
- **③ 前端轮询按种子量分档 (2026-09-19, 待提交)**: 计划里唯一排在 P1 之后的项 —— 降轮询间隔会**放大**全量回传 + 整树重渲染, 顺序错了会加剧不跟手。档位实测而定: 1000 种子单轮 143ms / 3000 种子 353ms / 5000 种子 ~550ms ⇒ **≤1000 → 1.5s / 1000~3000 → 2s / >3000 → 3s**(主线程占用率 10%/15%/17%); 下界 1.5s = 服务端 `sync_interval`(再快只是多拿空响应)。实现: `pollSec` 字段退役(不留死字段), 新增 `basePollMs()`; 冒烟新增分档断言 ⇒ 30 项 0 失败。
- **④ WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18, 未提交)**: 真因是两条重建路径**范围不一致**(主循环 `_tick` 只重建 `_group_view` 却清掉共享脏标记 ⇒ singles/shows/flat 被饿死, 版本号照常自增 ⇒ 前端换上陈旧数组)。已改为唯一入口 `rebuild_views()` + 置脏移出门控 + 前端取消 idle 退避并把 `server_state` 并入 `/api/state`。基线 1018 → **1021 passed**。剩用户真机走查 → [tasks/26-09-18-webui-view-rebuild-scope.md](tasks/26-09-18-webui-view-rebuild-scope.md)
- **⑤ 浏览器冒烟能力 (2026-09-19, dev-only, 长期有效)**: `scripts/ui_harness.py`(真 `create_app` + `FakeClient` + 合成种子 + 命令泵 `ok|error|hang`)+ `scripts/ui_smoke.cjs`(Playwright, 双 UI **46 项断言** + 内置 A/B 基准)。**Windows 上可跑**, 攻破了"单测测不到前端交互"这个长期卡点。⚠ `--host` 现在只接受回环(免鉴权服务不得暴露到局域网)。⚠ **两种模式都要跑**: `ok` 看正向、`--expect-cmd error` 看回滚 —— 后者此前必红所以没人跑, 已按模式分流断言。

- **skills 全量安全审查 (2026-09-20, ✅ 已提交并推送 `a370354`, Gitee 主线成功; GitHub 镜像滞后 2 个提交)**: 按 skill-vetter 协议审查 26 个技能 —— 唯一红线是 `autoclaw-design-capability` 内 `design-skeletons/last30days` 的 `lib/chrome_cookies.py`(解密 Chrome cookie 取 X 会话 `auth_token`/`ct0`, 仅 macOS 可触发且该包被 sync 排除 ⇒ 不可达), 已**整体删除该骨架**; 另删 12MB 重复副本 `autoclaw-design-capability_noqa`, 同步清理 `sync_agent_skills.py` 的 `EXCLUDED` / autoclaw `INDEX.md`(骨架计数 83→82) / `NOTICE.md` / `pitfalls.md`。3 条次要发现已入池 `memory-bank/issues/`(hatch-pet 付费 API / 写 `USER.md` 口径冲突 / grill-me 空 stub)。审查报告 [docs/26-09-20-1429-skill-vetter-audit.html](../docs/26-09-20-1429-skill-vetter-audit.html)。**已补**: 实跑 `scripts/sync_agent_skills.py` 后 `my-commit-flow` 已链接进 `.codebuddy/skills`(现 24 个, = 25 个顶层 skill 减去被排除的 autoclaw), 读穿校验 OK、无悬空链接; **重启会话后才会出现在技能列表**。

- **5000 种子仿真客户端 · 独立安全/性能测试 (2026-09-19, W0–W6 全部走完)**: 已归档到 [tasks/26-09-19-sim-client-5000.md](tasks/26-09-19-sim-client-5000.md); 遗留 BUG-01(断连不自愈)按用户决定**暂不修**, 已立档在 `TODO.md`。
- **知识库瘦身 (2026-09-20, ✅ 已提交并推送 `9ccace6`, Gitee 与 GitHub 镜像均成功)**: 按"过时 / 重复 / 低价值"三分类清理根 `AGENTS.md` 与 `memory-bank/` —— **路由表与黄金法则单点收在 `AGENTS.md`**(`memory-bank/README.md` 改指针), 已完成条目从本文件迁出到 `progress.md` / 任务档案; `testing.md` 顶部基线数字**未动**(待补测 WSL 一侧再更)。提交时与上游 7 个提交 rebase, `AGENTS.md` 一处冲突按"保留上游新增的 HTML dark 主题规则 + 保留本轮压缩后的计划产出口径"解决。**知识库回写(pitfalls 新增「rebase --continue 被 VS Code 编辑器挂死 + packed-refs 陈旧致核 ref 假红」条目 + 本行状态更新)尚未提交。**

## 待用户真机走查 (代码/测试均已完, 只差真实 qB 数据下的观感确认)

- **主循环 × WebUI 解耦** (`5691c6f`, 2026-09-20) —— 纯结构性重构, 行为应**完全无感**; 重点确认
  ① 各视图照常刷新、切页无空白 ② 右键命令(暂停/删除/汇报/限速…)照常生效且乐观态正常落回
  ③ 关闭网页后主循环不再做视图重建(日志里应看不到 `[cmd] 回执(补刷新后)已写` 之外的 Web 开销)
- **跟手性优化三波次** —— 右键菜单响应 / 切视图首帧 / 3000+ 种子滚动流畅度
- **本轮新修的 4 处(建议顺路走查)** —— ① 刷新页面时若上次停在**追剧页**, 现在应正常显示(修复前是永久空白);
  ② 右键**复制磁力**在辅种页/追剧页应真能复制(修复前 100% 提示"没有 magnet 链接");
  ③ 整组/整集暂停后**行本身**应立刻变灰(半透明 `is-pending`)且颜色即时切换;
  ④ 混合状态组的颜色可能与修复前不同(状态优先级已统一到后端口径, 只影响 2 种混合态)
- **热路径提速(§11, 建议重点体感)** —— 3000+ 种子库下切视图/滚动时数据到达更快(服务端 189 → 23.5 ms)。
  重点看: 种子页在**数据变化那几轮**是否还有"迟一拍"的观感; 若大库仍觉卡, 下一步就是报表 §08 第 7 项
- **追剧页剧/集右键「打开目标文件夹」** (`c888fba`) —— 剧 → 集 → 种子三级各点一次; 顺带确认整剧开始/暂停/删除已恢复
- **视图重建范围收口** (`1021 passed`, 未提交) —— 种子速度是否已随轮询刷新
- **TASK015 错误种子原因** (`9723a76`) —— 错误态状态列是否显示 tracker 原文
- **TASK013 / TASK012 / TASK011**(第九/十/十一轮修复) —— 逐轮走查反馈
- **TASK014 UI 组件库 20 式** (`fae019a`) —— 挑选与按需迭代

- **WEBUI 状态栏上传/下载速度恒为 0 (2026-09-20, ✅ 已修并验证 → issue 置 `Fixed`; 剩用户真机走查)**: 根因**已实测确认** —— 状态栏在前端对 `groups` 求和(`decorate.js:136-141`), 而 P1-1 按视图回传把 `groups` 从种子页裁掉了(`VIEW_ARRAYS["torrent"]=("torrents",)`, `web_view.py:48`) + 前端「键不存在保留原引用」(`app.js:883`) ⇒ 种子页上 `this.groups` 恒为 `[]` ⇒ 恒 0。次因: 合计漏 `singles`, 桩实测(50组+200未归组)**少算 88.7%**。复验方式: 起 `scripts/ui_harness.py --torrents 300` 直接 curl 两视图比对(种子页响应**无 groups 键**, 真值 15,206,400)。修法选定「服务端算 `status.totals` 恒回传 + 前端改读」(候选 C 用 `server.dl_info_speed` 因桩里 `server_state=null` 不可测, 仅备选)。计划 [docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html](../docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html); 档案 [tasks/26-09-20-webui-statusbar-speed.md](tasks/26-09-20-webui-statusbar-speed.md); 报告 [issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html](issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html)。⚠ 与 2026-09-19 的 BUG-8(追剧页成员索引被裁致永久空白)**同类**: 跨视图的常驻消费者去依赖按视图裁剪的阵列, 建议顺手排查还有没有第三个。
  **已实施(未提交)**: F1 `_build_speed_totals()`(`web_view.py`) / F2 `speed_totals` 与四视图同临界区发布(`web_runtime.py`) /
  F3 `status.totals` 恒回传(`web.py`, **并把 `ensure_group_state()` 提到 status 字典之前** —— 否则字典字面量先求值,
  totals 慢一拍且首轮为 0) / F4 前端 `totalDl|totalUl` 改读 `status.totals`(`decorate.js`, 两套模板零改动)。
  实测: 桩服务种子页 `totals={dl:15206400, ul:45926400}`(= groups+singles 真值; 修复前种子页无此键、合计仅 1723392);
  单测 **1059 → 1062 passed**(Windows) / WSL **1057 → 1060 passed + 2 skipped**, +3 守阵(端点恒回传 / 静态防回潮红绿双验过 /
  合计含未归组); 冒烟双 UI **54 项 0 失败**, DOM 实测 `14.50 MiB/s`。基线数字已回写 `testing.md`。

- **列设置被重置 = 多标签页整份覆盖 (2026-09-20, ✅ 已修并验证 → issue 置 `Fixed`; 未提交; 剩用户真机走查)**: 用户报"栏的顺序/显示/宽度经常被重置"。**根因实测确认**: 内存是**加载时读一次的快照**(`app.js:273 initialColState`) + `saveColState()` **整份写回** ⇒ **last-writer-wins**, 谁最后动一下存储就变成谁的快照, 先改的标签被静默吞掉(入池时猜的"写失败/读入洗净/自适应覆盖/v3→v4 迁移"**全部排除** —— 单标签六路径全保持, 只有第二个标签能复现)。修法: **F1** `saveColState(page)` 改 read-modify-write(以存储为底, 只覆盖本 page 四段; 6 处调用点传 page) + **F2** `storage` 事件 → `adoptColState()` 整份采用 + **F3** `visibilitychange` 回到可见补漏。**F1 单独不够** —— 用户两个标签改的通常是同一个表, page 级合并同表仍然后写赢。冒烟新增「列设置多标签页互不覆盖」⇒ ok/error 双模式各 **56 项 0 失败**; 红验(摘掉标签 2 的 storage 监听)确认守阵钉得住; 单测 **1062 passed** 未退化。后端零改动, **未升 `COLS_STORE_KEY`**。计划 [docs/plans/26-09-20-1836-webui-column-prefs-sync-plan.html](../docs/plans/26-09-20-1836-webui-column-prefs-sync-plan.html); 档案 [tasks/26-09-20-webui-column-prefs-reset.md](tasks/26-09-20-webui-column-prefs-reset.md); 报告 [issues/26-09-20-1800-bug-webui-column-prefs-reset.html](issues/26-09-20-1800-bug-webui-column-prefs-reset.html)。**真机走查**: 开两个标签各改一次列(隐藏 + 拖宽), 互相刷新确认都不丢。

- **状态栏「今日流量」视觉重做 (2026-09-20, ✅ 已提交推送 `94c6857` → issue 26-09-20-1840 置 `Fixed`; 剩真机目视)**:
  图标换真图标 `#i-traffic`(上下行箭头)并改**双色** —— 两条 path 内联 `stroke: var(--today-down/--today-up)`, 靠 CSS 变量穿越 `<use>`
  影子树生效(外部选择器进不去); 数值去字面量 ↓/↑ 改用 `#i-arrow-down/up`; 历史入口图标弃粉改 lime(`--today-ico`);
  `.sb-today .v-*` 抬到 `.sb-item.sb-today .v-*`(修棱镜掉白的层叠根因); "今日" 标签与 "连接/剩余" 同格式; 速度区每方向合成
  `[方向图标] 速度 / 限速` **整组可点**按钮(状态栏不再单独给限速配图标)。⚠ **未做浏览器冒烟** —— `ui_harness.py` 桩不产 traffic
  数据(`v-if="todayTraffic"` 不渲染), 环境也没装 playwright。
  **真机走查**: ①双色是否分得清、箭头与数字 3px 间距是否合适 ②两套 UI / 五主题下 lime 历史图标是否协调 ③点速度区任一处都能弹限速浮层

- **种子页「可用性」列隐藏负数与暂停值 (2026-09-20, ✅ 已提交并推送 `7548e51`; 剩真机目视)**: 用户报该列出现负数
  (qB 拿不到 distributed_copies 时给 `-1`, 旧版 `toFixed` 出 "-1.00" 看着像真数值)且暂停中的种子也显示。修法沿用
  **单元格口径单点**: 新增 `cellAvailability(m)`(FX-26, `format.js`, 与 FX-03 的 `cellPeers` 同范式 —— 空串占位不摘节点),
  两套模板(atlas/prism 各一处)改引用它并补 `zero` 类。判据: `kind === "paused"` → 空; `availability < 0` 或缺失 → 空;
  **0 仍是有效值(确实零副本), 保留显示**。验证: `ui_harness.py --torrents 300` + Playwright 实测 —— paused 行 = 空、
  注入 `-1` = 空、注入 `2.5` = "2.50"、`0` = "0.00"; 双 UI 冒烟 **56 项 0 失败**且无 console 错误; 单测 130 passed。
  ⚠ **抽屉(drawer.js:442)仍是老口径** `(d.availability ?? 0).toFixed(2)`, 同样会显示 -1.00 —— 用户本次只点"可用性一栏",
  按范围守恒未动, 待确认是否一起改。

- **种子页「最近活动」列改相对时间 (2026-09-20, ✅ 已提交并推送 `7548e51`; 剩真机目视)**: 新增 `fmtRelTime(ts)`
  (FX-27, `format.js`) —— 刚刚 / N分钟前 / N小时前 / N天前 / **N个月前 / N年前**; 哨兵 `-1`(从未传输)仍为空白
  (TBL-01); 绝对时间点保留为 `title` 供悬停核对。
  ⚠ **口径(用户真机反馈后定的)**: 该列**一律相对, 不回落绝对日期** —— 首版写了"超 30 天回落日期", 真机上
  同一列里"有的 3天前、有的 08-11 21:06"被读成"没改干净", 故补月/年两档把长跨度也纳入相对。
  ⚠ **关键**: 相对时间必须读响应式时基 `nowSec`(新增于 `app.js` data + 30s ticker), **不能现取 `Date.now()`** ——
  后端该字段按分钟量化 + `rid` 未变不回传数组 ⇒ 行对象不变、Vue 不重渲染 ⇒ 相对值会永久冻在渲染那一刻
  (已入 pitfalls)。验证: 浏览器注入 20s/10min/2h/3d/-1/40d 六种情形实测文案正确; 把 `nowSec` 拨快 1 小时,
  文案整体加一档(证明时基生效); 双 UI 冒烟 **56 项 0 失败**、无 console 错误; 单测 130 passed。
  ⚠ **抽屉(drawer.js:488)「最近活动」仍是绝对时间**(`ts(d.last_activity)`), 同上面的可用性一样待确认是否一起改。

- **时间点列表头右键切换相对/绝对 (FX-28, 2026-09-20, ✅ 已提交并推送 `7548e51`; 剩真机目视)**: 覆盖**四个时间点列**
  —— 添加于 / 最近活动 / 完成于 / 追剧页「最近动静」(`TIME_FMT_KEYS`), 各列表头右键多两项「相对时间 / 绝对时间」,
  当前口径带勾标(`.ctx-tick`)。**按列独立**存 `data.timeFmt` {列key: "rel"|"abs"}, 持久化键 `autoqb_timefmt_v1`
  (刻意不进 `autoqb_cols_v4`: 那边是列集合/列宽/顺序 + 跨标签合并, 显示口径是另一条生命周期)。
  单元格一律走 `format.js` 的 `cellTime(ts, key)` / `cellTimeHint(ts, key)`, **所有时间点列不得再直接调
  `fmtTime`/`fmtTs`**(否则那列就没有开关); 两种口径互为 title。**默认值 = 改造前现状**(添加于/完成于/最近动静
  原为绝对, 最近活动已改相对) —— 加开关不顺手改观感。**时长列(做种时长/活跃时间/ETA)不参与**: 它们不是时间点,
  没有绝对/相对之分, 菜单里也不出现这两项。
  实测: 默认三列 = 绝对/相对/绝对; 只切「添加于」→ 另两列不动; 存储 `{"added_on":"rel","last_activity":"rel",
  "completion_on":"rel","latest":"abs"}`; 刷新保持; 分组页「添加于」与种子页共用同一设置(按列 key 不按 page);
  做种时长右键无切换项。冒烟 56 项 0 失败; 单测 130 passed。
  ✅ **跨标签同步已补(2026-09-20 21:52, 未提交)**: `adoptTimeFmt()`(`format.js`)整份采用存储值 ——
  F2 `storage` 监听(`_onTimeFmtStore`, 与列偏好**独立**监听: 两个 key 生命周期不同, 合一个监听只会让判据纠缠)
  + F3 回到可见时补对齐一次; `unmounted` 里撤监听。实测两标签双向同步(B 切相对 → A 立即跟随; A 切回绝对 → B 跟随)。

## 定案口径 (别改回去; 完整判据见 [pitfalls.md](pitfalls.md))

- **列偏好"升版本"**: 列集变更(加列/减列/重排)与存储结构扩展**一律不升版本**, 只有"旧缓存结构已无法被 `loadColState()` 正确解释"才升(如 v2 按列索引存), 且升版本必须同时挂 `LEGACY_COLS_KEYS` 迁移。当前键冻结在 `autoqb_cols_v4`, 无 v5 计划。历史计划 `docs/plans/26-09-15-1042-webui-optimization-plan-v3.html` 里"重排列集则升 v4→v5"是当时口径, 已被第十轮计划取代 —— 存档未改动, **别照抄**。
- **第十轮两处已知限制**(非待办): ① 列偏好受 localStorage **origin 隔离** 影响(`localhost` 与 `127.0.0.1`/换端口 = 不同站点各存一份) —— 用户明确要求只存浏览器, 不做服务端化; ② 目录浏览器只能浏览**已有保存路径及其子目录**(安全边界), 全新位置需在输入框手填。
- **第十一轮定案**: 行/表头一律 `fit-content; min-width: 100%`(**底色跟内容**), **行内单元格必须 `min-width: 0`**(否则 nowrap 文本把行顶宽 ⇒ 列没溢出却常驻横滚条); 曾用"行定宽 100%"治假滚动条, 会让**溢出段没有底色**(用户实测"滚动后右边无背景条"), 已回退。
- **开工先拉分支 + 提交即推送 (2026-09-19/20 用户指定, 别照抄旧文档)**: 两条规则的**单点定义都在 `AGENTS.md`**(「会话协议 · 开始」与「提交 / PR」), 本文件只留指针: ①会话第一步必为 `git pull --rebase <远端> develop` (**分支名必须写**), 确认不落后才动手, **禁止在落后分支上改代码**; 拉取前先弄干净工作区 (脏工作区 + rebase 触发 stash 会损坏对象库)。②用户说"提交" = **commit + 自动推送** (先 commit → rebase → 推 Gitee → 尝试一次 GitHub 直连, 失败不重试)。⚠ `conventions.md` 里 2026-09-10 的"🔴 绝对不要 push"**已作废**, 只作历史沿革保留 —— 按它做会漏推, 而交付只看 Gitee 有没有该提交。**同一条协作规则不在知识库复述全文, 只留指针**; 该规则共 4 处入口 (`AGENTS.md` / `.github/copilot-instructions.md` / `.agents/skills/memory-bank/SKILL.md` / `.github/instructions/ai-lib.md`), 改规则要一次改全。
- **工作区模式: 多 clone 并行 (2026-09-20 用户拍板, **git worktree 已弃用**)**: 每个 AI 实例一份**完整克隆**(各自独立 `.git`), 跨工作区同步一律走 Gitee `develop`; 单点在 `AGENTS.md`「环境硬约束」与 `conventions.md`「协作约定」。原 8 个 worktree 目录已打包存档到 `D:/Projects/_archive/auto-qb-worktrees-2026-09-20/`(含 `MANIFEST.md` 与 `sha256.txt`), 目录已移除(5 个进回收站, `auto-qb-other` 因回收站报"不支持该功能"改移到存档区 `_removed-dirs/`), 8 个本地分支已删除 —— 删除前已核验全部 `ahead=0`, 无独有提交。新布局为 `D:/Projects/auto-qb`(主) + `auto-qb-clone1` / `auto-qb-clone2` / `auto-qb-long-seeding`。
- **`想法.md`**: 工作区**干净**(最后一次入库 `3bface9`)。它属于红线文件(与 `config.yml` / `auto-qb-data/` 同级), 提交前照例用 `git status --short` 确认一遍是否又有改动, 不进暂存区。

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- **上轮复核的收尾**(见「正在进行」第 ① 条) —— 只剩报表 §08 第 7 项(节拍对齐, **需先拍板方向**)
  与同类端点的同样改法(低优先); 第 1、2 批与 §11 已实施未提交
- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-19 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改), 或已沉淀进 [progress.md](progress.md) 的「已实现」段。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
