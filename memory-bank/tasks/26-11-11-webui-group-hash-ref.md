# 26-11-11-webui-group-hash-ref — webui 组行 hash 引用式联合立项: 联合复验+grilling+计划入库

**Status:** Done
**Added:** 2026-11-11
**Updated:** 2026-11-13
**Summary:** 两件 perf issue(26-10-07-1420 组行 hash 引用式 / 26-10-08-0411 /api/state 全量轮瘦身)联合复验均仍复现 → grilling 五问拍板(D1-D5 全按推荐) → 联合计划 26-11-11-0630 全批次落地收口(S0-S6 完成, 2026-11-13): 主线 C 落地(组行 members 改 hash 引用式 + 前端 ingestion 物化缝 + version-reload 自愈), 全量回包 -35%、抖动轮组行 24.6×/27.0× 塌缩(S0/S5 对照单点=本档案); G1/G2/G3 三裁决点全部不立项(2026-11-12 用户拍板); 两 issue 翻 Done; 基线切片 26-11-13-0027(测试数字见 kb.baseline)
**Topics:** webui-group-hash-ref
**Refs:** memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html, memory-bank/issues/26-10-07-1420-perf-webui-group-row-hash-ref.html, memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html, memory-bank/issues/26-11-12-2345-chore-real-seed-clean-evidence-guard.html, memory-bank/testing/baselines/26-11-13-0027-webui-group-hash-ref.md, memory-bank/issues/26-11-13-0130-test-e2e-rowwin-group-click-reachability.html

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
| 5 | S0 成本构成实测拆分(计划 §04 首步) | Done(2026-11-11, @3000+@5000 双档实测完成, 见「S0 实测数字」; 两 issue 保持 In Progress 待 S1 开工) |
| 6 | S1 后端 hash 引用式(协议+守阵同批) | Done(2026-11-11, 22a35b18 前身批 392 行, 评审轮 2 零 actionable) |
| 7 | S2 前端物化接缝(spike→ingestion 拷贝物化) | Done(2026-11-12, 本批; spike 裁决与已知边界见 R2 节) |
| 8 | S3-S6(计划 §04 余步) | Done(2026-11-13; S3-S4 随前批入库(22a35b18/de1fe327/d7e6bc23), S5a/S5b 见 R3, S6 收尾本批) |

## 进度日志

### R0 · 立档 (2026-11-11)

联合复验(两件仍复现)→ grilling D1-D5 全按推荐 → 计划 26-11-11-0630 入库(Open, doc-refs 与两 issue 双向闭环)→ 评审 3 轮(14 发现全修, 轮 3 零 actionable 出口)。零生产代码改动; 全部变更随本专题入库。

- 2026-11-11 07:03 联合复验两件仍复现(重锚回写)+grilling D1-D5 全按推荐+计划 26-11-11-0630 入库(Open)+评审 3 轮 14 发现全修零 actionable; S0-S6 等显式开工, 两 issue 保持 Open
- 2026-11-11 07:03 提交轮评审收口(共 5 轮, T=16/P=12, 修 12 过检全修, 零 blocker 零入池): 轮 2 的 4 条(minor2/nit2)**未过 review.check 即修——流程偏差**, 由轮 3 逐条回验闭合(行号指针/索引源原文/比值自洽均逐字核对), 后续轮次引文过检照 ⑤ 执行; 轮 4 微复评 2 nit(口径注记不齐)过检即修; 轮 5 终确认零发现出口。远端 tip 评审窗口推进至 0d88dc3d(本地缺对象「无法核实」), 齐平走 ship.commit 提交先行 rebase。

> 已外迁: 进度日志 R1(S0 开工+环境与口径 / 假种子配方 / 四段测量口径 / 踩坑 1-4) → [attachments/26-11-11-webui-group-hash-ref-progress-archive.md](attachments/26-11-11-webui-group-hash-ref-progress-archive.md)(2026-11-22 cap 清零)

### R2 · S2 前端物化接缝 (2026-11-12)

**S2a spike 裁决(polling.js 注释指路单点)**: 缝 = **ingestion 物化**(三入口: applyStateRows 全量/delta + auth.js bootstrap), 产**成员行浅拷贝**而非计划 §03 原推荐的 canonical 行引用 —— 偏差动因: 乐观链 `_forEachRow`(commands_optimistic.js:30-34/:64-72)prev 采集「后命中覆盖前命中」隐含「同 hash 多命中各为独立对象」, 别名化下第二命中读到已打补丁值, `op.prev` 被污染 → 失败回滚静默失效; 浅拷贝与 S1 前服务端成员字典同构, 52 处消费位零波及、补丁链代码零改动。delta 桶序 torrents/singles 先于 groups 合并 ⇒ 物化时索引恒新鲜; full 分支索引直接吃载荷数组。缺项防御: 保留原 hash 字符串不产 undefined + `_rematQueue` 登记、后续轮 `_rematDrain` 补物化(后端「成员脏⇒同代组脏」不变式下常规不可达, 纯兜底)。评审 P3 轮 1 修 1 major: `_rematDrain` 调用点从赋值前挪到赋值后(原位登记行未进 `this.groups`, `cur.includes` 恒 false, 队列当轮空转)。

**已知语义边界(评审确认接受)**: `_snapshotTruth` 组员源换成本地物化拷贝后, 误判窗口 = 组脏(他员变化)+ 该组另有成员 pending —— 提前撤 hold 且 op.prev 同窗污染; **成功路径观感不变, 失败/停滞路径补丁值停留至该成员下次变化或下一次全量轮(长期滞留, 非一轮弹回)**。绿色向守阵 = node 电池 `test_r4_truth_snapshot_materialized_members`(8 断言; 场景 1 平铺桶只放 A + 守门断言钉「快照确实经组员拷贝取到 B」, 判别面真落在物化源上)。三入口接线覆盖落点(P5 评审修复后如实, 旧表述「留 S4 e2e 覆盖」只对 delta 桶序一入口成立): delta 桶序(torrents/singles 先于 groups 合并)+ 重组后 members 仍物化对象形 = S4 e2e 乐观用例(组员拷贝补丁不触字段 `state` == 平铺真值行的新鲜度档 + 暂停真值轮 delta.groups 形状钉, e2e/group-hash-ref.spec.mjs); 待补清账 drain 赋值后时序(P3 修复点)= node 电池 `test_r4_remat_drain_after_assign_two_beat`(两拍缺项 delta, drain 挪回赋值前即红); auth.js bootstrap 同缝 = 同电池静态钉(`_materializeGroupRows` 调用先于 `this.groups` 赋值, 跨度比较钉顺序)+ 节点级声明 —— e2e 桩恒免鉴权(ui_harness skip_local_verify), 登录快照轮 e2e 不可达, 不由 e2e 覆盖; 「先物化后赋值」的响应式时序半边无直接断言面(物化挪到赋值后产物相同, 仅 Vue 代理旁路差异), 由 polling.js 注释声明 + e2e 产物面(组行 members 物化形)间接覆盖。

**数字**: 行数口径(git numstat)polling.js +113/-2 → 评审修复后 +117/-2; auth.js +5; 电池 +105/-5 → 评审三轮修复后 +115/-5; 测试面(定向 e2e 8 红全转绿 / S2b 补跑 25 spec 全绿 / test.quick)数字只记本批提交信息, 收口立基线切片后统一改「见 kb.baseline」, 不在此手抄。g.members 消费位 52 处/17 文件零 diff(全树 grep 口径)。

> 已外迁: 进度日志 R3(S5a 复评取数第一段 / 环境重建 / 三件实测 / 输出路径事故 / 现场处置) → [attachments/26-11-11-webui-group-hash-ref-progress-archive.md](attachments/26-11-11-webui-group-hash-ref-progress-archive.md)(2026-11-22 cap 清零)

> 已外迁: S0 实测数字(全量轮四段占比 / 回包字节拆分 / monster·jitter 抖动 delta, @3000/@5000) → [attachments/26-11-11-webui-group-hash-ref-s0-benchmark.md](attachments/26-11-11-webui-group-hash-ref-s0-benchmark.md)(2026-11-22 cap 清零)

> 已外迁: S5 复评数字(hash 引用式后 @3000/@5000、字节拆分、抖动塌缩、G1/G2/G3 裁决状态) → [attachments/26-11-11-webui-group-hash-ref-s5-benchmark.md](attachments/26-11-11-webui-group-hash-ref-s5-benchmark.md)(2026-11-22 cap 清零)
