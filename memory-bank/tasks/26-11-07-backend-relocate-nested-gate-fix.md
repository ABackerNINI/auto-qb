# 26-11-07-backend-relocate-nested-gate-fix — relocate 嵌套闸门误拦修正实施

**Status:** Done
**Added:** 2026-11-07
**Updated:** 2026-11-08
**Summary:** relocate 嵌套闸门误拦修正实施
**Topics:** backend-relocate-nested-gate-fix

## 本篇只回答

本档案只回答: relocate 嵌套目标闸门误拦修正的**实施过程记录** —— 分阶段委派、每阶段结果、真机实验证据锚点与收尾状态。方案本体见计划 [26-11-07-1300](../plans/26-11-07-1300-plan-relocate-nested-gate-fix.html),本档案不重复方案。

## 原始请求

1. 误拦报告: 启用整组移动时移动一个种子(3 文件,有内容根 `R:\Download\PTing\xxx`)到 `R:\Download\PTing\待删` 被 GATE_NESTED 拦;质疑一: 单个种子不该拦;质疑二: 应按内容根而非声明源比较;质疑三: 全文件型 junction(3 文件 < 阈值 8)不该拦。
2. 要求查原设计文档说明闸门动机(已完成,见计划 §02 判据出处行)。
3. grilling 后出修复计划(已完成: Q1-Q6 拍板,计划入库)。
4. 拆解任务,派子智能体分阶段依次实施(串行防超并发;大任务拆小防 O(n²) token 与进度丢失;关联小任务合并;待拍板先询问;委派方只委派+总结;开新本地分支,每步本地 commit **不走 my-commit-flow**;子智能体免 sync;全程本地分支,完成后同步到本地 develop 后`等提交指令`;子智能体提前停可 SendMessage 续跑;非正常失败 3 次停止等人工)。
5. 任务 = 本地提交计划 + 实施计划 + 完成后复验。

## 思考过程与决策

- 计划: `memory-bank/plans/26-11-07-1300-plan-relocate-nested-gate-fix.html`,拍板 D1-D8 全落档(对称修/scope 收窄/confirm 披露/文件级放行/UI 双披露点/互嵌形式化/真机先行/UI 缺口补齐),无待拍板遗留。
- 编排决策: 串行子代理 T1a(E1-E3)→ T1b(E4-E8)→ 回炉检查点 → T2(P2 核心+单测)→ T3(P3 UI)→ T4a(真机复验)→ T4b(test.full+基线)→ T5(code-review)→ T6(收尾回写)→ 合回 develop。
- 分支纪律: 本地分支 `relocate-nested-gate-fix`(自 develop f7ac0e46),每阶段委派方本地 commit(plain git,gitmoji+中文),不推远端;完成后 ff 合回本地 develop,远端推送随本专题入库时按显式指令走 ship 口径。

## 实现计划

按计划 §04 分期:P1 真机实验先行(E1-E8 + 回炉条款)→ P2 纯函数+单测 → P3 实现+UI → P4 真机全链路验收 + test.full 基线切片 → 收尾回写。三约束全程断言(不删种/不 skip_check 重加/不读盘校验,teardown 清理不受限);生产 26586/16585 与 `I:\PT\`、`config.yml`、`auto-qb-data/` 零触碰。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 建分支+提交计划+立档 | Done(2026-11-07) |
| S1a | T1a 真机实验(环境核验+E1/E2/E3) | Done(2026-11-07) |
| S1b | T1b 真机实验(E4-E7+E8 判据模拟) | Done(2026-11-07) |
| S2 | 回炉检查点(P1 结果对照判据) | Done(2026-11-07: R7 批准 + E2c 入池, 计划改版 R1) |
| S3 | T2 纯函数+单测重锚 | Done(2026-11-07, fd53c8fe) |
| S4 | T3 UI 披露实现 | Done(2026-11-07, c7c839da) |
| S5 | T4a 真机全链路复验 | Done(2026-11-08, 8/8 场景 PASS, 见 R4) |
| S6 | T4b test.full+基线切片 | Done(2026-11-08, 切片 26-11-08-0132, 失败集=存量 1 条措辞守卫, 见 R5) |
| S7 | T5 code-review | Done(2026-11-08: 批A/B面1/B面2/C + 收口终审 5 派, blocker 1 修, 检 10/10, 见 R6) |
| S8 | T6 收尾回写 | Done(2026-11-08, 计划改版 R2 置 Done + 措辞守卫清零 + 复切片) |
| S9 | 合回本地 develop(不推) | Done(2026-11-08, ff 合回) |

## 进度日志

### R0 · 立档 (2026-11-07)

- 会话: 误拦报告 → 设计文档溯源 → grilling 六问 → 计划 1300 入库(37926370)→ 用户下达实施指令。
- Stage 0 完成: 分支 `relocate-nested-gate-fix` 自 develop(f7ac0e46),计划+索引已提交(37926370),本档案立档。

### R3 · 回炉检查点 (2026-11-07)

- P1 全过(E1-E8;E8 模拟 29/29,无判据回炉项)。回炉/拍板产出:
  - **D9 = R7 删链门重锚**(用户批准): 锚 job.src → job.scope + 豁免本组成员;修 T1a 自锁(嵌套放行形态收尾永不发生)与 T1b/E7 组外停车假依赖;E2/E3 删链断言移 P4 修后必验。
  - **D10 = E2c 入池**: `issues/26-11-07-2336-bug-relocate-same-drive-finalize.html`(同盘部署收尾链无效,先于本计划存在,本计划不修)。
- 计划改版 R1(26-11-07-2339): §03 增 R7 行、§04 E6 产品可达坐标修正 + P2 增 R7 单测面 + P4 增删链断言、§07 增同盘风险行与索引超预算告警行、§06 D9/D10 回填。
- 存量告警(非本轮引入): issues `_index.md` 8,312 > 8,000 字符预算(Open 区条数病根),记计划 §07 待人工处置。

→ R1/T1a、R2/T1b、R4/T4a 三段真机实验详录(环境与逐 E 结果、实验机制附注、现场还原)已逐字外迁: [attachments/26-11-08-relocate-nested-gate-fix-experiment-logs.md](attachments/26-11-08-relocate-nested-gate-fix-experiment-logs.md)(26-11-08 cap 清零)。

### R5 · T4b 全量基线 (2026-11-08)

- 全量基线切片: `memory-bank/testing/baselines/26-11-08-0132-backend-relocate-nested-gate-fix.md`(`commands run test.full` 后台实测, pytest 140.44s; 汇总行 `1 failed, 5651 passed, 2 skipped, 1 warning`; 覆盖率 TOTAL 25530 stmts / 6 miss / 8816 branch / 28 partial = 99%, 门槛 99.5 达标(总覆盖 99.90%); 缺口单位 34, 对上片 32 净额 +2 远低于点名线; 副作用台账 9565 条越界 0)。数字均从实测誊写入切片, 本档案只引述不另抄。
- 失败明细: 唯一 failed = `tests/test_memory_bank_docs.py::test_wording_guard_is_green_on_current_kb`(存量措辞守卫), 违规点 = 本档案 18/25 行历史表述(`等…指令`/`待提交` 两类时点相对措辞), 与任务提示给的已知基线(test.quick 口径)逐位一致 —— **失败集未超出存量 1 条, 无新增回归**; 按本轮收尾纪律不修, T6 收尾回写改写该措辞后自然消除。
- 差值说明: 对上一条切片(26-11-07-1248)passed 净增 2 = P2/P3 两批新增用例(relocate 判据/删链门重锚 + webui 披露)随全量通过; 2 skipped 与上片同 2-skip 权限面。全量口径与任务提示的 test.quick 口径同数, 无口径差。

### R6 · T5 评审 + T6 收尾回写 (2026-11-08)

- 评审(5 派, 串行): 批A 文档面([]) / 批B面1 判据正确性(1 minor+2 nit) / 批B面2 安全+测试缺口(**1 blocker**+2 minor+1 nit) / 批C UI(1 minor) / 收口接缝终审(1 major+1 minor)。引文机械校验 10/10 过(review.check)。
- **blocker(B面2)**: R7 锚窄化漏「组外 save_path 恰等 job.src」真依赖(dir_alias 收尾窗经别名落进作用域的种子, D16 evaluate_add 同款建模承诺其为永久依赖)—— 误放删链=组外种子断粮且失去删种保护。修复: `chain_gate_hits` 增 `equal_root` 仅等值并列面(不并前缀, 保住 E7 假依赖修), 9f0cbe4e。
- minor/nit 全修: R2 空 scope 回落 job.src(与 R7 口径对齐)/ R4 嵌套 confirm 执行面双相测试 / R7 首例夹具真嵌套 / R6b 阈值字面量钉 / R2 文案形态无关化 / member_save_paths 注释 / supersede 断言归因; 终审 major = equal_root 回归测试已补。修复提交 9f0cbe4e(+60 行 <100 无需复评)。
- 终审结论: 接缝闭合可收口; 计划滞后项并入本节回写(计划改版 R2)。
- 计划改版 R2: §03 R7 行补 equal_root、R2 行补回落、§10 补条目, doc-status 置 Done(P4 真机 8/8 + 全量绿为验收依据)。
- 措辞守卫清零: 档案 18/25 行时点相对措辞改行内代码/随本专题入库口径; 复跑全量后复切片(新切片替代 0132 作为最新基线, 0132 留档为带存量失败的历史切片)。
- 范围外移交(本轮只报告未动, 供用户裁决): ①`commands run dev.fmt` 的 yapf shim 损坏(uv trampoline, T2 起以 `uv run python -m yapf -i` 等价形式完成格式化) ②issues `_index.md` 8,312 > 8,000 字符预算(Open 区条数存量) ③member_save_paths 死字段清理需授权 ④T3 观察的 move-note「移动后该种子将离开当前辅种组」在整组语义下措辞歧义。
- review: 范围 f7ac0e46..HEAD(relocate 嵌套闸门修正分支) · blocker 1 · 修 10 · 入池 0 · 检 10/10 · 派发 5 · 齐平按本地分支工作流声明(远端 tip 722eb3b0 落后属预期)。

- 2026-11-08 03:17 relocate 嵌套闸门误拦修正实施: P1 真机实验 E1-E8(回炉 R7 删链门重锚) → P2/P3 实现(判据形态感知+UI 披露) → P4 真机复验 8/8 → 评审 5 派(blocker 1 修) → 全绿收尾 5653 passed; 本地分支 relocate-nested-gate-fix 待合回 develop
