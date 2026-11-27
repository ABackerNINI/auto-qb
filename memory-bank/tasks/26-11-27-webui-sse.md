# 26-11-27-webui-sse — SSE 推送候选 P1/P2/P3 联合实施

**Status:** Done
**Added:** 2026-11-27
**Updated:** 2026-11-27
**Summary:** 三路取证 + grilling 两轮 12 问拍板(D1-D12) + 计划 26-11-27-0530 入库; S1(P1 错误日志推送化 + D13 单游标回捞)、S2(P2 transfer D5b 两段回执, 真机 BLOCKED 按 D11 不阻断)、S3(P3 抽屉推送化只读评估: 空转率/RoCache 命中率实测 + 结论条件触发)三阶段全收口, 计划整体 Done, issue 0408 翻 Done
**Topics:** webui-sse
**Refs:** memory-bank/issues/26-11-20-0408-feat-webui-sse-candidate-inventory.html, memory-bank/plans/26-11-27-0530-plan-webui-sse.html, memory-bank/testing/baselines/26-11-27-0608-webui-sse-s1-frontend.md, memory-bank/testing/baselines/26-11-27-1244-webui-sse-s1-gap-recover.md, memory-bank/testing/baselines/26-11-27-1324-webui-sse-s2-transfer-two-hop.md

## 本篇只回答

候选清单 issue 0408 的 P1/P2/P3 怎么进入可开工状态——本轮只做立项（取证 + 拍板 + 计划），不含实施代码。

## 原始请求

1. 用户原话: 「memory-bank/issues/26-11-20-0408-feat-webui-sse-candidate-inventory.html P1/P2/P3联合立项，grilling，然后出一个计划」。
2. 两轮 grilling 均回「按推荐」: D1-D6（形态/通道/载荷/P2 裁剪/P3 处置/认领）+ D7-D12（断档/前端消费/两段形态/评估产物/测试真机/批次）。

## 思考过程与决策

- 计划单点: `memory-bank/plans/26-11-27-0530-plan-webui-sse.html`（Open, S1-S3 三阶段）。D1-D12 全文表在计划 §06。
- 关键取证改判（相对 issue 0408 原文）:
  - P2 的 relocate 半边已由计划 26-11-10-2350 D8 实施闭合（7d99ce32 + RM11 真机 PASS）, 只有 transfer D5b 未排期 → P2 裁剪为「仅 transfer」, 避免重复立项（D4）。
  - P3 的 1s/2s 缓存是本项目 Web `RoCache`（`context.py:31` / `torrent_detail.py:88-91`）, 非 qB 自身缓存; 抽屉已「写字段不重建 + Vue 同值不触发」→ 只做只读评估（D5）。
  - P1 发布点在日志线程（`runtime_common.py:115-126`）, 与 issue 原文「主循环线程」纪律字面冲突 → 明确为例外, 靠 `notify` 非阻塞保证安全（D3）。
- 实施期最高风险: 通用 `waitCmd` 把 `warn` 当终结态（`commands.js:234-235`）, 而 relocate 受理段正是 `warn`（`commands_torrents.py:472-479`）→ S2 受理回执必须带可区分标记, 不得复用通用 warn 终结语义。

## 实现计划

见计划 26-11-27-0530 §03/§04。摘要: S1 错误日志接 `/api/events` + 60s GET 降对账; S2 仅 transfer D5b 两段回执; S3 抽屉只读评估。三批逐批评审, 每批收尾按 DoD 回写 + 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 三路只读取证 + grilling 两轮 + 计划入库 + 认领链 | Done (2026-11-27) |
| S1 | P1 错误日志推送化（后端事件 + 前端接线 + 对账 + 守阵） | Done (2026-11-27) |
| S2 | P2 transfer D5b 两段回执（受理段可区分 + 终态覆盖 + 前端两段 + 真机冒烟） | Done (2026-11-27) |
| S3 | P3 抽屉推送化只读评估（空转率/缓存命中率 + 结论） | Done (2026-11-27) |

## 进度日志

### R0 · 立档 (2026-11-27)

立项轮完成: 三路只读取证（P1 错误日志 / P2 长任务回执 / P3 抽屉与 SSE 基建）+ grilling 两轮共 12 问（用户全按推荐）+ 计划 26-11-27-0530 入库 Open（10 SLOT 全填、双向链 3 件）+ issue 26-11-20-0408 翻 In Progress + 本档案立档并双向链。零代码改动、零测试数字产生（故不新建基线切片）。

- 2026-11-27 05:32 立项: 三路取证 + grilling 两轮 12 问拍板(D1-D12 全按推荐) + 计划 26-11-27-0530 入库 Open(S1 P1 错误日志/S2 transfer D5b/S3 抽屉只读评估) + issue 0408 翻 In Progress + 档案立档; 零代码改动

- 2026-11-27 05:42 评审收口: 三轮评审(major 1 + minor 1 全修, 第三轮零发现), S2 受理段定案=后端不推信号+前端本地渲染(避开 onCmdEvent/onTruthEvent 双终结路径); 计划 R1/R2/R3 回写, kb.check/kb.docmap/ship.gate 全绿

### R1 · S1 实施收口 (2026-11-27)

- S1-a(另批已提交): `append_err` 出锁后 `notify("errlog", {seq, level, msg})`, 只推单条小真值。
- S1-b: `startEvents` 注册 `errlog` 监听, 载荷交 `lifecycle.onErrlogEvent` 落袋, 复用 `"b"+seq` 去重与 `errPanelOpen` 未读口径, 事件路径零 GET; 载荷无 ts 故以到达时刻补。
- 乱序: 出锁广播到达序不等于 seq 序 —— 合并按 seq 降序插入(迟到的低 seq 不爬到新条上), 游标取 `max(现有, seq)` 只进不退; 后端重启 seq 归零仍由 `_errlogReseed` 清旧重拉。
- S1-c: 60s GET 保留对账/游标校准(丢事件补齐、重启重拉)并计未读以覆盖 SSE 断档窗口; 与事件不双计靠 merge 先按 `"b"+seq` 去重; boot 开页全量与 reseed 重启全量不计未读。
- 守阵: 扩 `test_webui_error_history.py`(静态接线) 与 `test_webui_static_r4_poll_auth_lifecycle.py`(SSE 监听断言 + 落袋/对账 node 电池), 新增双皮肤面板 e2e。`test.full` 实测数字见 kb.baseline 最新切片 `webui-sse-s1-frontend`。
- 计划 26-11-27-0530 整体保持 Open(S2/S3 未做), issue 状态未动。

### R2 · S1 补充单游标回捞 (2026-11-27)

- 用户新拍板 D13: 出锁广播 + 游标只进不退下, 低 seq 事件被 notify 队列丢弃而高 seq 事件先到推进游标后, 60s GET 用 after=cursor 回捞不到该低 seq 条目 —— 采用**保守游标回捞**, 不新增机制。已回填计划 §05/§06 D13/§10 R4。
- 落点 `lifecycle.js`: `created` 初始化 `_errReconcileAfter = null`; `onErrlogEvent` 在合并推进游标**之前**侦测间隙(到达 seq > 游标+1), 记回退游标 = `min(已有 ?? 当前游标, 到达seq-1)`(多缺口保最早); `_pullErrlog` 的 `after` 改用 `_errReconcileAfter ?? _errLogCursor`, 回捞走既有 `_mergeBackendErrlog`(`"b"+seq` 去重 / 按 seq 有序插入 / 游标 max)且对账计未读(去重先行不双计); 仅当本次 `after` 仍等于回退游标时清空(GET 在途新缺口不误清, 失败保留), reseed 路径同步清空。
- 口径澄清: 后端 `/api/errlog` 的 `after` 是严格 `seq > after`(`runtime_stream.py:98`), 故拍板公式 `?? seq` 的基准取「最后连续位=游标」, 并以到达 seq-1 封顶, 才满足「回退点不超过第一个可疑缺口」并真能捞回被丢条目; 字面取到达 seq-1 只会捞回到达事件及其后, 与目标相反。
- 守阵: `test_webui_static_r4_poll_auth_lifecycle.py` 的 `_NODE_ERRLOG_EVENT_PROBE` 扩九组缺口回捞断言(回捞成功/降序落位/不去重计/游标不倒退/成功后清空/多缺口保最早/GET 期间新缺口不误清/失败保留/reseed 清); `test_webui_error_history.py` 静态接线 +6 断言。定向 21 passed。
- 计划整体仍 Open(S2/S3 未做), issue 26-11-20-0408 状态未动; `test.full` 数字与基线切片见 kb.baseline 最新 `webui-sse-s1-gap-recover`。

### R3 · S2 transfer D5b 两段回执收口 (2026-11-27)

- S2-a 后端守阵: 代码本就无缺口, 零产品后端改动。确认 transfer 受理路径无新增 notify 推送点(`runtime_transfer.py` 零 `notify(`)、无新增事件类型、事件面清单恰为 `cmd/truth/skip_check/errlog/ver` 五项; 终态仍走既有 `receipt_port -> _transfer_receipt -> set_result -> notify("cmd")` 覆盖同 `cmd_id`(`runtime_commands.py:318` 全 webui 唯一 `notify("cmd")` 点); 单写线程纪律不变(回执端口只在主循环 `drain` 路径收敛, worker 线程只投结果队列); `waitCmd` 三态终结语义不改。新增 `test_tf_backend_no_accept_signal_guard` 静态钉死六项, SSE node 电池 +1 事件面清单断言。
- S2-b 前端两段消费: `transfer_flow.js::_transferExec` 受理段从 POST **之前**挪到 POST 成功返回 `cmd_id` **之后**本地渲染(pending 图标 +「后台验证中」文案, 沿用原 pending 形态), 投递失败路径不再误挂 pending(连图标调用都不发生); `waitCmd(resp.cmd_id, timeoutMs)` 保留作 SSE 丢事件兜底; 终态回执到达才结算三件套(逐项行内 ok/warn/error + toast 三态 + 目标缓存刷新)。
- 双跳时序幂等: 本批内局部 `settled` Set(`_transferRenderAccepted` / `_transferSettleIcon` 成对共用), 终态先到先记账, 后到的受理段渲染遇 settled 跳过, 已结算行不被降级回「后台验证中」; 不引入跨批全局状态。node 电池强制反序验证幂等 + 两段共用同一集合, 双皮肤 e2e 验可见性与不降级。
- 测试与真机: 定向 `test_transfer_flow_confirm.py` 5 passed、SSE 电池 1 passed; 新增 `tests/e2e/transfer-two-hop.spec.mjs` 双皮肤(prism/atlas)2 passed(4.5s); `commands run test.full` 全绿, 基线切片 `webui-sse-s2-transfer-two-hop`(见 kb.baseline)。真机 S2-c: `real.guard` FAIL(端口 56589/56590 均无监听进程), 按 D11 记 BLOCKED, 不阻断入库; 未手工杀进程、未拉共享实例。
- 计划整体仍 Open(S3 抽屉只读评估未做), issue 26-11-20-0408 状态未动。

- 2026-11-27 13:24 S2 transfer D5b 两段回执实施收口: 后端零改动守阵 + 前端 POST 后本地渲染受理段 + 本批局部 settled 双跳幂等 + 双皮肤 e2e + 真机 guard BLOCKED

### R4 · S3 抽屉推送化只读评估收口 (2026-11-27)

- S3-a 实测(一次性探针, 未落文件, 不依赖 qB 真机): ①**RoCache 命中率** —— 项目真实 `RoCache`(`context.py:15-48`) 注入假钟, 按 `currentPollMs()` 三档推进 N=10000 拍, 以 `fn` 调用次数反推: trackers(ttl=2.0s)@1.5s=50.00% / @2s=0% / @3s=0%, peers(ttl=1.0s) 三档均 0%, tp 双源@1.5s=25.00%。②**抽屉轮询空转率** —— `node` 经 `vm` 加载真实 `_dtMergeRows`(`drawer_store.js:35-48`), 喂 python 实测命中序列(N=2000): 命中拍返回同一行对象引用 → 字段零变化 / 行引用稳定 / 顶层新数组(Vue 同值不触发), 可确定空转 trackers@1.5s=50.00% / tp 双源@1.5s=25.00% / @2s·@3s=0%。③口径: 空转率是「缓存命中驱动的结构性下界」, 真实 qB 数据变化率需真机, D11 P3 免真机故不测; 1s/2s 是本项目 Web `RoCache` 非 qB 自身缓存。
- S3-b 结论: **条件触发(暂不实施)**。理由: 空转只在 1.5s 档出现且峰值 50%(单源)/25%(双源), 2s/3s 档缓存不吸收; 渲染层已「写字段不重建 + Vue 同值不触发」, 空转用户可见成本≈0; P0 per-scope 通道(26-11-18-0037)仍 Open、真机冒烟未清偿, 复用前提不成立。触发阈值(三条同时满足才另起独立排期, 不在本计划内实施): (a) 真机实测抽屉页签空转率 ≥60%; (b) 同口径 RoCache 命中率 ≤10%; (c) P0 计划 26-11-18-0037 收口且真机冒烟通过。结论与数字已回填计划 §03 S3 行 / §07 P3 风险行 / §10 R6。
- 三阶段全收口: S1/S2/S3 均 Done; 计划 doc-status Open→Done, 本档案 Status In Progress→Done, issue 26-11-20-0408 In Progress→Done(S2-c 真机 BLOCKED 按 D11 不阻断入库, 留痕于 R3)。零产品代码改动、零新增测试、零新增基线切片(纯文档批)。
- review: 降级自查(§⑧) 20 条逐条走; 首轮发现 2 minor(空转率 0% 口径限定 1 / 推送化改造成本反面证据 1)均属本批且当场修, 复评轮零发现零 actionable; review.check 检 2/2 通过弃 0; ship.gate 全绿; 本地分支态(ls-remote 无 ref)跳过 pack 前置 sync; 24 行 基 61b2d0509044

- 2026-11-27 13:37 S3 抽屉推送化只读评估收口: 实测空转率/RoCache 命中率 + 结论条件触发; 三阶段全收口

### R5 · 接缝终审 60s 对账未读口径修复 (2026-11-27)

- 接缝终审 major(用户拍板「修复后同步」): S1-c 曾把 60s 对账 GET 的 `countUnread` 改为 false, 理由是「与 SSE 事件双计」—— 但 `_mergeBackendErrlog` 先按 `"b"+seq` 去重、之后才计未读, 双计并不存在; 真实后果是 SSE 断档/丢事件窗口内由 GET 补回的错误只进历史、不亮未读徽标(`_errUnread` 为 statusbar 可见徽标)。
- 修复口径三处: 60s 周期对账 `_pullErrlog(true)`; boot 开页全量仍 `false`; reseed 重启全量显式 `{ countUnread: false }`(后端重启后整环旧条目不刷爆徽标)。注释/文档口径同步回正, 计划与 issue 状态均不动。
- 守阵: `test_webui_error_history.py` 静态接线改 true 断言 + reseed 显式 false 钉; `test_webui_static_r4_poll_auth_lifecycle.py` 的 `_NODE_ERRLOG_EVENT_PROBE` 扩真验(断档补回未读 +1 / 同 seq 先 SSE 后 GET 不二次计 / reseed 全量不计未读 / 桩 setInterval 真放拍验回调传 true)。定向全绿。
- 计划 26-11-27-0530 §03 S1-c / §06 D8·D13 / §10 R4·R7 口径回正, 整体仍 Done; issue 26-11-20-0408 状态未动。`test.full` 实测数字与基线切片见 kb.baseline 最新 `webui-sse-seam-unread-count`。
- review: 降级自查(§⑧) 20 条逐条走; 首轮发现 1 minor(node 电池断言名与场景不符)当场修, 复评轮零发现零 actionable; review.check 检 1/1 弃 0; ship.gate 全绿; 本地分支态(git ls-remote 无 ref)跳过前置 sync; 86 行 基 bdcc353d2d93
