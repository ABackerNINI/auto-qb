# 26-11-27-webui-sse — SSE 推送候选 P1/P2/P3 联合实施

**Status:** In Progress
**Added:** 2026-11-27
**Updated:** 2026-11-27
**Summary:** 立项轮: 三路取证 + grilling 两轮 12 问拍板(D1-D12 全按推荐) + 计划 26-11-27-0530 入库 Open, issue 0408 翻 In Progress; 零代码改动
**Topics:** webui-sse
**Refs:** memory-bank/issues/26-11-20-0408-feat-webui-sse-candidate-inventory.html, memory-bank/plans/26-11-27-0530-plan-webui-sse.html

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
| S1 | P1 错误日志推送化（后端事件 + 前端接线 + 对账 + 守阵） | Open |
| S2 | P2 transfer D5b 两段回执（受理段可区分 + 终态覆盖 + 前端两段 + 真机冒烟） | Open |
| S3 | P3 抽屉推送化只读评估（空转率/缓存命中率 + 结论） | Open |

## 进度日志

### R0 · 立档 (2026-11-27)

立项轮完成: 三路只读取证（P1 错误日志 / P2 长任务回执 / P3 抽屉与 SSE 基建）+ grilling 两轮共 12 问（用户全按推荐）+ 计划 26-11-27-0530 入库 Open（10 SLOT 全填、双向链 3 件）+ issue 26-11-20-0408 翻 In Progress + 本档案立档并双向链。零代码改动、零测试数字产生（故不新建基线切片）。

- 2026-11-27 05:32 立项: 三路取证 + grilling 两轮 12 问拍板(D1-D12 全按推荐) + 计划 26-11-27-0530 入库 Open(S1 P1 错误日志/S2 transfer D5b/S3 抽屉只读评估) + issue 0408 翻 In Progress + 档案立档; 零代码改动

- 2026-11-27 05:42 评审收口: 三轮评审(major 1 + minor 1 全修, 第三轮零发现), S2 受理段定案=后端不推信号+前端本地渲染(避开 onCmdEvent/onTruthEvent 双终结路径); 计划 R1/R2/R3 回写, kb.check/kb.docmap/ship.gate 全绿
