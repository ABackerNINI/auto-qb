# 26-11-04-test-coverage-uplift-3 — 覆盖率提升第三轮实施 — 新欠账清偿与出生即绿 (99% / 319 单位 → ≤100)

**Status:** In Progress
**Added:** 2026-11-04
**Updated:** 2026-11-04
**Summary:** 承接前两轮(91%→96% / 97.66%→99.41%)的第三轮实施档:门槛 99 已稳但缺口 162→319 回涨(新欠账约 +157),按计划三阶段 P0/P1/P2 收敛缺口到 ≤100(TOTAL ≈99.7%),机制 M1–M7 继承 + M8 缺口净额台账新增
**Topics:** test-coverage-uplift-3
**Refs:** memory-bank/plans/26-11-04-0157-plan-test-coverage-uplift-3.html

## 原始请求

1. 「参照前两轮覆盖率提升实施,写一个第三轮实施计划」——已产出 `plans/26-11-04-0157-plan-test-coverage-uplift-3.html`(实测 2026-11-04 develop @ 7701cd22:TOTAL 99%,缺口 319 单位 = 167m + 152p,50 文件)。
2. 「先拆解任务,然后派子智能体分阶段依次实施」——大任务拆小防 token O(n²) 与进度丢失,关联小任务合并摊薄固定成本,串行不并列;待拍板先问;委派方只委派+总结不实施;每步本地普通 commit(不用 my-commit-flow),完成后合回本地 develop 随本专题入库;子智能体异常失败 3 次即停止等待人工介入。

## 思考过程与决策

- **拍板 D1–D3**(2026-11-04,采纳全部推荐,见计划 §06):D1 终点缺口 ≤100 / TOTAL ≈99.7%,阈值阶梯 win 99→99.3→99.5 / 其他 98.5→98.8→99.0;D2 P0 顺序 rules/base(35) 先、fuse_mod(33) 后;D3 M8 净额点名门槛 = 净额为正且 >+15 单位。
- **拆解原则**:按计划 P0/P1/P2 三阶段拆 11 步,同家族合并(每步 ≈25–60 单位):快赢件按家族合并(rules 家族 / fuse 家族)、P1 按包合并(ops+路由 / hr 家族 / transfer+config)、P2 webui 二线与 core 尾分开、机制项(M8 台账)单列;每阶段末尾一个独立验收步(test.full 门槛 + 基线切片含 M8 净额 + 变异红验抽 ≥10%),验收不与清偿混在同一子智能体任务里。
- **执行形态**:工作分支 `coverage-uplift-3`(本地,无远端),子智能体开工不跑 sync(用户明确);每步完成由该步子智能体用普通 `git commit` 落一笔(用户明确不用 ship.commit);全部完成后委派方合回本地 develop,推送随本专题入库流程处理。
- **不变量照计划 §01**:I1 只补测试不改产品码(发现缺陷入池不修)、I2 行号是 26-11-04 快照开工先重刷、I3 豁免只减不增、I4 零真实副作用、I5 阈值恒低于实测、I6 硬骨头不硬啃逐条列名。

## 实现计划

1. **S0 编排准备**(委派方):拍板回填计划 + 立本档 + 开分支 `coverage-uplift-3` + 提交计划件。
2. **P0**(两清偿步 + 一验收步):T0a rules 家族守卫簇(rules/base 35 + validation/rules 22)→ T0b fuse 家族(fuse_mod 33 + cli 16)→ T0c P0 验收(TOTAL ≥99.3%、基线切片含 M8 净额首记、红验抽 ≥10%、watchlist 核销记录;不达标差额滚 P1)。
3. **P1**(三清偿步 + 一验收步):T1a ops 拆分叶(26)+ routes/traffic_monitor(10)→ T1b hr 家族(discovery 14 + service_wave 10 + runtime 7 + server 5)→ T1c transfer orchestrator(10)+ config 尾(20)→ T1d P1 验收(TOTAL ≥99.55%、阈值抬 win 99.3 / 其他 98.8、基线切片、红验)。
4. **P2**(两清偿步 + 一收口步):T2a webui 二线(≈40)→ T2b core 尾 + registry/finalize_watch(≈34,tray 维持豁免)→ T2c P2 收口(TOTAL ≥99.7% 且缺口 ≤100、阈值抬 win 99.5 / 其他 99.0、M8 台账定稿回写 baseline.md、残留逐条列名、watchlist 清零核验)。
5. **S9 收尾**(委派方):计划与档案转 Done、全轮总结、分支合回本地 develop。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 拍板回填 + 立档 + 开分支 + 提交计划 | Done (2026-11-04) |
| T0a | rules/base 35 + validation/rules 22 → test_rules_core.py · test_config_rules.py | Done (2026-11-04, 4e4acde6) |
| T0b | fuse_mod 33 + cli 16 → test_fuse_mod.py · test_cli.py | Done (2026-11-04, 806f954b) |
| T0c | P0 验收:TOTAL ≥99.3% + 基线切片(M8 首记)+ 红验 ≥10% | Done (2026-11-04, 118261bf, 切片 26-11-04-0507) |
| T1a | ops_skip 18 + ops_jobs 8 + routes/traffic_monitor 10 | Open |
| T1b | hr/discovery 14 + service_wave 10 + hr/runtime 7 + hr/server 5 | Open |
| T1c | transfer/orchestrator 10 + sections 12 + writer 6 + loaders 2 | Open |
| T1d | P1 验收:TOTAL ≥99.55% + 阈值抬 win 99.3/其他 98.8 + 基线切片 + 红验 | Open |
| T2a | webui 二线 ≈40(runtime_views/commands/runtime_commands/views_episodes/module/runtime_common/runtime_stream/commands_torrents/routes/auth/static_ui/views) | Open |
| T2b | core 尾 ≈30(traffic_grid/relocate_*/ops_mod/state/qbmanager/qbapi/rules_mod/traffic_snapshot_mod/relocate_journal)+ registry 4 + finalize_watch 5 | Open |
| T2c | P2 收口:TOTAL ≥99.7% 且缺口 ≤100 + 阈值抬 win 99.5/其他 99.0 + M8 定稿回写 baseline.md + 残留列名 + watchlist 清零 | Open |
| S9 | 计划与档案转 Done + 总结 + 合回本地 develop | Open |

## 进度日志

### R0 · 立档 (2026-11-04)

- D1–D3 拍板回填计划 §06(kb.bump R1),本档建立并双向认领计划件。
- 拆解定稿:三阶段 11 步(2+1 / 3+1 / 2+1)+ S0/S9 编排步;同家族合并、串行派发、每步本地 commit。
- 待办:开分支 `coverage-uplift-3` 提交计划件后开始派发 T0a。

### R1 · P0 三步完成 (2026-11-04)

- T0a(`4e4acde6`)rules 家族:base 全清、validation/rules 余 3 条 normalize 兜底防御支(到不了,列名留档);T0b(`806f954b`)fuse 家族:cli 全清、fuse_mod 余 1 条同快照防御 partial。
- T0c(`118261bf`)P0 验收过线(非及格带):基线切片 `26-11-04-0507-test-coverage-uplift-3-p0`(数字见切片,M8 净额首记为负),watchlist 7→4、豁免 8 零新增、红验抽 11.8% 全杀零假绿。
- T0b 揭出 1 条潜在产品缺陷(fuse_mod 摘标签路径缺 None-client 守卫,现行接线不可达)——按 I1 未修,收尾时随全轮总结提请入池裁决。
- 插曲:T0a 全量揭出本档 R0 触发措辞守卫的等待类句式违规(既有红,非本轮代码引入),已改不变措辞(`7afc56f4`)转绿。
- 待办:派发 T1a(ops 叶 + traffic_monitor 路由)。
