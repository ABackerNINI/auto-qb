# 26-11-01-rule-engine-redesign — 规则引擎重设计与重设计方案

**Status:** Done
**Added:** 2026-11-01
**Updated:** 2026-11-03
**Summary:** 规则引擎重设计:现状取证(G1-G13)→ 调研报告 26-11-01-0057 → 方案 26-11-01-0106(R1 定稿,D1-D8 拍板)→ W1-W5 全序列实施完成(9 笔提交,test.full 4420 passed,5 份期基线切片)→ 真机收口(RM03 漂移轮 17/17 全绿 + RM09-11 choose 保存通道 + W1-B 徽标 L0 目视兑现);计划与档案均 Done
**Topics:** rule-engine-redesign
**Refs:** memory-bank/reports/26-11-01-0057-report-rule-engine-redesign.html, memory-bank/plans/26-11-01-0106-plan-rule-engine-redesign.html, memory-bank/issues/26-10-31-1304-bug-rules-stop-following-dead.html, memory-bank/issues/26-10-01-2211-refactor-rules-keys-semantics-review.html

## 原始请求

1. 规则引擎重新设计:当前规则引擎感觉不完备,特别是 `stop_following_rules_if` / `ignore_next_action_error` 这种语法有异味。
2. 调研成熟的解决方案,做一个完备的规则引擎;注意完备不代表复杂。
3. 流程:先调研写一个报告,然后 grilling 一个方案。
4. 组织方式:拆解任务后派子智能体分阶段依次实施(防长任务 token 膨胀与进度丢失);主会话只委派与总结,不实施;完成后等提交指令。<!-- wording:allow -->

## 思考过程与决策

四阶段流水(各阶段独立子智能体,主会话只委派):①现状分析——根因:执行模型已演进为「每规则×每种子独立任务+事件分派」,但 stop_following_rules_if(六档死配置,`(handled, stop)` 返回值被 `_run_rule` 丢弃)/ignore_next_action_error(伪动作)/返回值契约仍停留在旧链式模型(缺口 G1-G13,证据见报告 §02);②调研——Drools/OPA/CEL/json-rules-engine/easy-rules/Zapier/ECA/HA 七系拆解,「控制流藏进数据字段」在成熟系统全部是一等配置项;蓝本选 HA automation(场景最同构);③报告 26-11-01-0057 定稿(出厂即 Done);④方案 26-11-01-0106 R0 草稿 → 红队拷打(R1-R8:改动面漏 webui/sim_qb/夹具/schema 派生件、retry 阻塞主循环、trace 维度、registry 导入环、mode/具名状态现网价值≈0)→ grilling 轮用户拍板 D1-D8 → R1 定稿。

**拍板结论(26-11-01,详见计划 §06)**:D1 两键退场走配置升级路线(载入转未启用+warning,不做运行时兼容;webui 为配置面前提);D2 旧扁平语法永久并存(normalize 单点,webui 编辑保存即新形态);D3 choose 本期做;D4 evaluation 只留枚举位;D5 trace 按(规则×种子)维度环形 3-5 条+体积截断;D6 mode/具名状态移出本期(留设计说明+升格条件);D7 本期 W1-W5 全序列;D8 webui 可视化编辑随期同步;G13 未用条目全保留。

## 实现计划

按计划 26-11-01-0106 R1 的 W1-W5 分期实施(每期独立可交付可回退,详细内容要点与验收判据见计划 §04):W1 两键退场(升级路线+R2 四处改动面)→ W2 on_error 错误策略(retry=任务级 requeue)+ normalize_legacy_rule() 落地 → W3 条件组合树+choose+webui 编辑器 → W4 per-run trace(D5 维度)+ evaluation 枚举位 → W5 单一 registry 收口(导入方向推荐 schema 留 config.schema+延迟访问器)。每期收尾跑 `commands run test.full` 并建基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| S1 | 现状分析(规则引擎架构+两异味+缺口清单) | Done(2026-11-01) |
| S2 | 成熟方案调研(七系拆解+原语提炼+反模式) | Done(2026-11-01) |
| S3 | 调研报告落盘 26-11-01-0057(守卫全绿) | Done(2026-11-01) |
| S4 | 方案草稿 26-11-01-0106 R0(W1-W5+D1-D6) | Done(2026-11-01) |
| S5 | 红队 grilling 拷打(R1-R8 修订清单) | Done(2026-11-01) |
| S6 | 用户 grilling 拍板(D1-D8 共识) | Done(2026-11-01) |
| S7 | 方案 R1 定稿(kb.bump,守卫全绿) | Done(2026-11-01) |
| S8 | W1 两键退场(升级路线:载入转未启用+verdict 收口+webui 徽标) | Done(2026-11-01,eac5cdf6+740ecf74) |
| S9 | W2 on_error 三档+retry requeue+normalize_legacy_rule 单点 | Done(2026-11-01,b98005cd+5e4c5e30) |
| S10 | W3 组合树 all/any/not+choose+webui 编辑器(保存写规范形) | Done(2026-11-01,f0fc2040+10c71ea8) |
| S11 | W4 trace(规则×种子环形)+evaluation 枚举占坑 | Done(2026-11-01,2f5b66ca) |
| S12 | W5 单一 registry 收口(方向 a,双跑 diff 清零) | Done(2026-11-01,779ec8fc+c6f57c5c) |

## 进度日志

### R0 · 立档 (2026-11-01)

调研与方案轮完成:报告 26-11-01-0057(出厂即 Done)+ 方案 26-11-01-0106(R0→R1 定稿,doc-status Open 待实施);D1-D8 全部拍板;实施 S8-S12 待开工。本轮未动代码,未跑 test.full(无基线切片)。cap 债务 8 项存量已转告(doc.caps 现算为准)。

- 2026-11-01 02:19 调研与方案轮完成: 报告 26-11-01-0057 定稿 + 方案 26-11-01-0106 R1 定稿(D1-D8 拍板), 实施 W1-W5 待开工

### R1 · 实施完成 (2026-11-01)

W1-W5 全序列实施完成并真机收口,档案翻 Done。

- 2026-11-01 06:33 W1-W5 实施落地:9 笔提交(eac5cdf6→c6f57c5c,拆 9 个小任务派子智能体依次实施,每期独立 commit+test.full 全绿+期基线切片共 5 份,最新 26-11-01-0752-rule-engine-w5-registry);test.full 4346→4420 passed;W5 导入方向拍板 (a);兼容硬约束全程成立(生产 5 条规则快照零差异/config.yml 零改/exec_history 键口径不动);计划外入池 2 件(26-11-01-0800×2)
- 2026-11-01 23:55 真机收口:RM03 漂移复测轮 17/17 全绿(W1-W5 新面 5 条+checking 收口,基线 6aa4b4d7)+ RM09-11 choose 保存通道四腿 11/11;W1-B「webui 未启用徽标」L0 目视挂账由本会话补测兑现(锚件 26-10-31-0641 记账:徽标/伪动作标记/卡脚等价写法/对照卡四面目视全过);计划 26-11-01-0106 翻 Done(R2),activeContext 过期切片迁出

- 2026-11-03 00:32 核实 issue 1304 与 2211 对 rule-engine-redesign 的落地情况: 1304 完全解决翻 Done, 2211 部分解决置 In Progress(G-05 未落); 双向补链与索引重建

- 2026-11-03 01:06 纠正 2211 错误归类: 两键语义梳理完全解决翻 Done; G-05 自愈 pop 缺 state.save 按原归类另入池 26-11-03-0104 bug 便签
