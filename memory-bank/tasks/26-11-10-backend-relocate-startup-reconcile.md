# 26-11-10-backend-relocate-startup-reconcile — relocate 启动对账自愈机制(防御性重启重判)

**Status:** Open
**Added:** 2026-11-10
**Updated:** 2026-11-11
**Summary:** relocate 终态失败账启动对账自愈: 按物理现状重推相位(G1-G5+A1), 复用既有收尾链零搬数收敛; 计划 26-11-10-0721 S1-S5 已完成(计划 In Progress, 终审收口另翻 Done)
**Topics:** backend-relocate-startup-reconcile
**Refs:** memory-bank/plans/26-11-10-0721-plan-relocate-startup-reconcile.html

## 本篇只回答

relocate 终态 failed 账如何通过「启动对账」自愈(判定表/重入资格/重入动线),以及生产 Blood 组既有失败账 `jr-a2ce556d0165` 如何借此零人工零搬数收敛;方案细节、拍板全记录与实施步骤的单点是计划件 26-11-10-0721,本档案只做推进与留痕。

## 原始请求

1. 「上一轮 memory-bank/plans/26-11-10-0230-plan-relocate-listing-false-negative.html 修复后未自愈, 组依然裂, 依然提示迁移失败. 现场 D:\Projects\auto-qb-long-seeding, 可只读探测, 分析原因」
2. 「错误, 上一轮算BUG修复, 应当自愈, 至少每次重启要增加重新判断当前状态的机制, grilling」
3. 「你似乎理解有误, 自愈指的是状态变为待收尾, 组自动合并, 参考之前该功能的设计文档再grilling」
4. 「该方案似乎还是着眼于修复本次BUG而不是防御性自愈, 即该方案仅针对此次事故自愈, 类似hotfix, 之后的版本基本用户到, 必要性存疑」
5. 「按推荐」(Round3 五问全采,含新计划立档)

## 思考过程与决策

- **取证先行**: 生产 state.json 三笔 job 无变化、`jr-a2ce556d0165` `updated_at` 仍为 00:37:10 原失败时刻 → 修复部署后(06:42:56 重启载新码)零重发、零对账动作;「未自愈」属实,分歧在「应不应该自愈」。
- **Round1(七问)作废**: 我按「新终态 stale + reason 白名单」出题,用户纠正: ①自愈=回到既有收尾窗「待收尾」+组自动合并(参考 26-11-05-0808 fastresume-finalize 与 26-10-18-1604 免重启两份设计文档: 收尾窗={armed,rewritten},组合并=第 1 层活跃 job 登记表);②不建新终态。
- **Round2(六问)再纠正**: reason 白名单被用户定性为 hotfix(修完即死码,必要性存疑)→ 定性改为通用启动对账。
- **Round3 定案(G1-G5)**: G1 通用对账(账面服从现实,不看 reason);G2 重入资格双证据(mover save_path==dst ∧ dst 内容 B′ 在位);G3 单一入口恢复 moved 复用既有链;G4 出路面最小(一行日志,WebUI 零新增);G5 沿用五项(首轮连接 tick 触发+热启用/账面先合并物理后收敛/立即收尾按钮零改动/cancelled+done 排除/落位本计划+吸收 issue 0327+issue 0326 收窄保留)。
- **A1(实施裁断)**: 重入上限每生命周期 1 次(attempts≥1 的 failed 不自动重入),防跨重启 churn,常数可调。
- **代码事实源**: 只读探员取证(启动路径终态仅计数+展示、qB 客户端 start() 未连、恢复机械面盘点、自检 B′ 可离线客户端、WebUI 立即收尾端点),file:line 已沉淀进计划 §02/§03。
- 计划: `memory-bank/plans/26-11-10-0721-plan-relocate-startup-reconcile.html`(Open)。

## 实现计划

按计划 §04 执行(S1 单测红验判定表四行+上限 → S2 实施(_load_jobs flag 推导+首连 tick 对账+重入) → S3 全量+基线切片 → S4 真机闭环(环境1,生产零触碰,RM04 族沉淀) → S5 回写(issue ③ 翻 Done / issue ② 批注收窄 / hr-groups.md 口径句 / code-review+档案))。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 单测红验: 判定表四行+重入上限+无态推导幂等 | Done(2026-11-10) |
| S2 | 实施: flag 推导+首连 tick 对账+判定表+重入 | Done(2026-11-10) |
| S3 | 全量 test.full + 基线切片 | Done(2026-11-11) |
| S4 | 真机闭环(环境1)+ RM04 沉淀 | Done(2026-11-11) |
| S5 | 回写(issue ③ Done/② 收窄/hr-groups.md)+ 收尾评审 | Done(2026-11-11) |

## 进度日志

### R0 · 立档 (2026-11-10)

生产取证(修复已部署但 Blood 账 failed/组裂,零重发实证)→ grilling 三轮(Round1 七问作废 → Round2 回收尾窗模型 → Round3 定案通用对账)→ 用户「按推荐」全采 → 计划 26-11-10-0721 入库(Open)+ 本档案立档,双向补链(前序计划 26-11-10-0230、issue 0326/0327)。实施等显式开工。

### R1 · 实施 S1-S5 (2026-11-11)

- S1+S2 机制实施(4897d4f6): `_load_jobs` 推导对账 flag + 首连 tick 判定表对账 + 双证据重入(重入落账即置 armed_at, 闸对所有失败形态闭环), 新用例 12(test_relocate_startup_reconcile.py); 顺带清偿两笔存量红(tests-real ASCII/schema 守卫)。
- S3 全量基线 4b69ed4f(切片 26-11-11-0001, 全量数字见 kb.baseline); S4 真机 RM04-21 两遍 PASS(4a01c94e, 时长/断言数见 real-baselines 26-11-11-0042; 生产 16585/26586 零触碰)。
- S5 回写: issue 0327 修(启动日志计数改走 active_jobs 单点, 翻 Done)+ issue 0326 收窄批注(Open 保留)+ hr-groups.md 整组迁移节补「失败账对账重推」句 + 计划 26-11-10-0721 翻 In Progress(终审收口另翻 Done)。
- 评审账: T1 立档批 轮 3(检 5/6 修 5)+ T2 实施批 轮 2(检 3/3 修 3)+ T4 真机批 轮 2(检 2/2 修 2 minor); S5 回写批评审随本批收尾闸门。

- 2026-11-11 01:25 S1-S5 实施完成: 机制实施(4897d4f6)+全量基线(4b69ed4f, 全量数字见 kb.baseline)+RM04-21 真机两遍 PASS(4a01c94e)+S5 回写(issue ③ 修/② 收窄/hr-groups 口径句)
