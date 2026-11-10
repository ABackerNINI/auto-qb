# 26-11-11-webui-group-hash-ref — webui 组行 hash 引用式联合立项: 联合复验+grilling+计划入库

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** 两件 perf issue(26-10-07-1420 组行 hash 引用式 / 26-10-08-0411 /api/state 全量轮瘦身)联合复验均仍复现 → grilling 五问拍板(D1-D5 全按推荐) → 联合计划 26-11-11-0630 入库(Open): 主线 C(hash 引用式)先行, S0 成本拆分置首步, B/A 转条件裁决; S0-S6 等显式开工, 两 issue 状态保持 Open
**Topics:** webui-group-hash-ref
**Refs:** memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html, memory-bank/issues/26-10-07-1420-perf-webui-group-row-hash-ref.html, memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html

## 本篇只回答

本档案只回答: 联合立项这轮做了什么、拍板了什么、下一步从哪进(S0 开工动作与认领时机)——方案本体与取舍的单点在计划 26-11-11-0630(§03/§05/§06), 不在此复述。

## 原始请求

1. 「memory-bank/issues/26-10-07-1420-perf-webui-group-row-hash-ref.html / memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html 两个issue联合复验, 然后grilling, 出一个计划」
2. grilling 五问批复: 「全按推荐」(D1-D5, 见计划 §06)

## 思考过程与决策

- **复验先行重锚**: 大文件拆分(deb1168d, 9 个后端大文件拆域子模块)后两件锚点整体迁移(views.py → views_group/views_row/views_common/views_episodes; runtime.py → runtime_views/runtime_common), 按符号+grep 重定位后逐一核对——两件均仍复现, 结构性事实无变化; 复验行+重锚已回写两 issue §04/§07, 状态保持 Open。
- **新事实进计划**: ①前端 g.members 消费面经全树 grep 盘点 60 处/17 文件(入池树 f07cc562 全树口径即 50 处/13 文件——代码消费面大体持平, 扩的是入池锚点只记 decorate.js 两段的审计覆盖); ②协议耦合: VIEW_ARRAYS group/show 视图须连带 torrents 数组否则 memberByHash 索引拼不出(shows 视图当年「连带 groups+singles」同款先例); ③静态 UI no-cache+ETag + 同仓同进程发布 → 旧标签页刷新即愈, 协议形状演进不背长期共存面。
- **grilling D1-D5(全按推荐, 2026-11-11)**: D1 单计划联合立项 / D2 C 先行(issue 2 §05 的「先拆分再选」降级为计划内 S0 步骤, B/A 转条件裁决 G1/G2) / D3 直接改形状+version-reload 小机制(协商参数/双字段是长期复杂度税) / D4 C1 组行整体 upsert(R8 不破; C2 只作实测触发条件项 G3) / D5 复验行当轮回写、认领留 S0 开工。
- **评审**: 分批只读评审 3 轮(轮 1 十条 minor7/nit3 → 全修; 轮 2 四条 minor2/nit2 → 全修; 轮 3 零发现出口), 累计 14 发现全过检全修, 零 blocker 零入池。主要修两类: grep 口径统一为全树(53/15 仅-JS 与 50/13 全树并置未标注 → 60/17 全树, 模板 tpl/ 2 文件 7 处计入验收口径)与推算自洽(去「19 键」改粗估、40/5 对应「≈8 倍」非「≈9 倍」); `_reduce_delta` 行号指针两处按实码重锚(窗外 :684-689 / 窗内 full 代 :691-692 / 缺行防御 :713-749, return 717/723/728/749)。

## 实现计划

计划单点: `memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html`(§04 实施步骤 S0-S6)。总体: S0 sim 实测成本拆分(开工动作 = 两 issue kb.status In Progress 补认领链)→ S1 后端 hash 引用式 → S2 前端物化接缝(spike 定缝, 验收 60 处消费位零 diff)→ S3 version-reload → S4 e2e → S5 复评与条件裁决(G1/G2/G3)→ S6 收尾(两 issue 翻 Done + webui.md 回写)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 开工同步(a950f353→90764579) | Done(2026-11-11) |
| 2 | 联合复验(锚点重定位+现状核对+回写两 issue) | Done(2026-11-11) |
| 3 | grilling 五问拍板(D1-D5) | Done(2026-11-11) |
| 4 | 联合计划入库+双向补链+评审 3 轮零 actionable | Done(2026-11-11) |
| 5 | S0-S6 实施(计划 §04) | Open |

## 进度日志

### R0 · 立档 (2026-11-11)

联合复验(两件仍复现)→ grilling D1-D5 全按推荐 → 计划 26-11-11-0630 入库(Open, doc-refs 与两 issue 双向闭环)→ 评审 3 轮(14 发现全修, 轮 3 零 actionable 出口)。零生产代码改动; 全部变更随本专题入库。

- 2026-11-11 07:03 联合复验两件仍复现(重锚回写)+grilling D1-D5 全按推荐+计划 26-11-11-0630 入库(Open)+评审 3 轮 14 发现全修零 actionable; S0-S6 等显式开工, 两 issue 保持 Open
- 2026-11-11 07:03 提交轮评审收口(共 5 轮, T=16/P=12, 修 12 过检全修, 零 blocker 零入池): 轮 2 的 4 条(minor2/nit2)**未过 review.check 即修——流程偏差**, 由轮 3 逐条回验闭合(行号指针/索引源原文/比值自洽均逐字核对), 后续轮次引文过检照 ⑤ 执行; 轮 4 微复评 2 nit(口径注记不齐)过检即修; 轮 5 终确认零发现出口。远端 tip 评审窗口推进至 0d88dc3d(本地缺对象「无法核实」), 齐平走 ship.commit 提交先行 rebase。
