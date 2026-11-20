# 26-11-15-backend-relocate-refactor — relocate 结构重构: 单活任务模型与判定收敛

**Status:** In Progress
**Added:** 2026-11-15
**Updated:** 2026-11-21
**Summary:** relocate 结构重构: 第一批 S1-S4(单活任务模型/撤销不搬回/生命周期账统一/路径判定单点)六笔提交落地 + 真机复验轮(26-11-17~19, 计划 0636 七片执行完毕: 21 条回归适配 + 13 条新增耐久用例全 PASS, 产品回归 0)+ issue 七条翻 Done; S5 跨模块接口显式化两笔提交落地(a652290f 登记集退役改 RelocateModule 派生查询 / 80d8ea09 常量收口+接口 AST 守卫, 全仓 src 侧 relocate 家族私有名跨界 import 清零, test.quick 6499P/2S/0F); S6 探测异步化五笔提交落地(d899e91a→824f6b94, 并轨 2350 D1-D10, 单测/仿真面全绿, 真机复验两项拍板延期)
**Topics:** backend-relocate-refactor
**Refs:** memory-bank/plans/26-11-15-2340-plan-relocate-refactor.html, memory-bank/issues/26-11-17-0214-question-qbmanager-startup-reload-state-discard.html, memory-bank/pitfalls/backend/startup-state-write-reload-discard.md, memory-bank/plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html, memory-bank/pitfalls/testing/state-file-lag-and-journal-absence.md, memory-bank/pitfalls/testing/restart-transient-and-offline-cmd-window.md

## 本篇只回答

relocate 结构重构这条线推进到哪、拍板了什么、下一步从哪个 S 开始 —— 方案细节与验收判据单点在计划(D 编号引用), 本档案不复制。

## 原始请求

1. 「目前存在很多整组移动 relocate 的 issues, 整组移动已经打过超过 20 个补丁, 可能是底层架构设计有问题, 先分析原因, 是否需要重构, 如何重构能从结构上简化」
2. grilling 指令: 技术细节按推荐, 行为变更要问; Q2 并入探测异步化并更改之前文档状态; Q4 链式搬迁应简化(全部指向最终位置, 不建链式链接); Q5 按最初设计不允许自动搬回; 修复清单写入文档供人工复验; 每条相关 issue 配 real 测试
3. 两轮修正: 旧任务不能删除记录, 只能随新任务一起消亡; 撤销文案需含手动处置推荐; 终态保留 20 条会冲掉批量搬迁的失败账

## 思考过程与决策

- 双只读子代理并行: 结构面(12 文件 7418 行, 三病灶: 相位/账 ≥5 处真相、mixin 假边界、判定分叉+裸总线) + 病因面(45 issue 归类, 结构类 51%, 补丁打补丁三实锤)。关键论断经主会话抽查证实(双 _norm / qbapi 反向 import / plan 双算 / R5 头注)。
- 链式简化评估: 「全部指向最终位置」已是现改道机制设计意图, 复杂度在前任活账参与收尾 → 落地为单活任务模型(D4)。
- grilling 四轮(问答三轮+修正一轮)D1-D10 全拍板, 全文见计划 §06; 技术面按推荐(生命周期账不上重型事件溯源、mixin 随刀1/2 自然消解)。

## 实现计划

单点在计划 §04 分期表: 第一批 S1 单活任务模型 → S2 撤销语义重做 → S3 生命周期账统一 → S4 路径判定单点 → 批次收尾(评审+终审+基线); 第二批 S5 接口显式化 → S6 探测异步化(并轨 26-11-10-2350 D1-D10)。每步 real 测试先红后绿(口径 D10, 清单在计划 §03.6)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 单活任务模型: 续迁收官+移交+统一改指+改道机器退役+旧账迁移器 | Done(第一批) |
| S2 | 撤销语义重做: 删搬回+三段式确认文案 | Done(第一批; 「上界面」降级为 API/命令通道下发, UI 消费面另立 issue) |
| S3 | 生命周期账统一: phase 派生+终态分级保留+双真相收敛 | Done(第一批) |
| S4 | 路径判定单点: 归一/到位/根内合一+删链门修复 | Done(第一批) |
| S5 | 跨模块接口显式化: 登记集→查询协议+私有引用清除 | Done(第二批; 守卫 test_relocate_interface_guard.py 承考, 见计划 R4) |
| S6 | 探测异步化(并轨 2350) | Done(第二批; 单测面达成, 真机复验两项延期, issue 0638 待复验后关) |

## 进度日志

### R0 · 立档 (2026-11-15)

- 双子代理分析 + grilling 四轮 D1-D10 全拍板; 计划 26-11-15-2340 入库(Open), 认领 8 个 Open issue 双向补链。
- 并轨处置: 计划 26-11-10-2350 翻 Superseded(设计条目全保留, 执行并入 S6), issue 0638 认领链改挂本计划, 其活动切片补注记。
- 各 issue 状态等对应批次开工再翻 In Progress(照 probe-async 先例: 拍板计划已批准、开工才翻)。

- 2026-11-15 23:44 立项: 双子代理分析(结构7418行/45issue归类) + grilling D1-D10 全拍板 + 计划 26-11-15-2340 入库认领 8 Open issue; 并轨处置 2350 计划翻 Superseded + issue 0638 认领链改挂 + 活动切片注记

- 2026-11-16 00:12 批次评审(提交前): R1 发现 2 minor+1 nit 过检 3/3 全修(指针§03.6/D11 误写/mixin 口径), R2 复评零 actionable 回退校验通过 —— 计划与 8 issue 认领链可入库

### R1 · 第一批落地 (2026-11-16 ~ 11-17)

- **六笔提交链**(S1-S4 + 收尾追修, 全部随本专题入库): f0004ef9 S1a 单活任务模型核心(续迁收官+移交+统一改指) → 785ad5ae S1b 改道机器退役+整链清理单元+旧账迁移器 → dae75d34 S2 撤销语义重做(删搬回+三段式 guide API/命令通道下发) → df15af5f S3 生命周期账统一(phase 派生单点+终态分级保留+清空历史) → 3692616c S4 路径判定单点(双 _norm 合一+删链门候选面修复) → cd786499 收尾缺陷追修(启动期接管面写穿+撤销 docstring 对齐+补测 5 条)。
- **分批评审**(逐笔只读子代理, 发现经引文校验全修零回退): S1a 5 轮 11 条; S1b 4 轮 12 条(3 major: armed 继任改写义务失主断粮洞/热启用 fail-fast 失效内存覆盖回滚/回滚测试还原断言恒真); S2 2 轮 5 minor; S3 3 轮 7 条(1 blocker 清空历史前端回执形状错配 + 1 major 自动滚出可静默删恢复挂账); S4 2 轮 3 minor(含 _rel_under 空串契约漂移); 追修 1 轮零 actionable。接缝终审发现的前三条补测缺口随追修提交落入。
- **真机验收 4 项 PASS**(证据 27 件, tmp-analysis/acc-reloc-single/): acc1 链式 A→B→C 撤销(旧路径解析/数据路径未动); acc2 迁移器(good/bad/restart 三形态); acc3 终态分级保留+清空历史; acc4 闸门面(0535 祖先方向 + 0711 direct)。
- **S2 偏离**(用户拍板 2026-11-17): 「上界面」降级为 API/命令通道结构化下发(_CANCEL_GUIDE 经 confirm 回执 guide 字段); 前端撤销入口+弹窗消费面入池 issue 单独跟进。
- **收尾(本轮)**: test.full 主体全绿(数字见 kb.baseline), 覆盖率闸门未达 Windows 阈(缺口净额与点名模块见基线切片; relocate 家族新增路径为缺口主体, 补测属后续轮); 计划 HTML 回写 R1 注记/§03.3 偏离注记/§04-S4 判据回写/§03.6 本批状态列; 基线切片落位。第二批 S5/S6 待显式开工。
- **内核级通用隐患裁决(2026-11-17)**: qbmanager.run() 的 _reload_state 在 start_all 之后整体重读磁盘替换 ctx.state.data(qbmanager.py:547→:435→:371), 任何模块启动期写 state 被静默丢弃 —— relocate 发病点(迁移盖章/对账回写/prune 滚出)已由 cd786499 写穿规避(_load_jobs 尾部 ctx.state.save()), 内核面曾「未修待裁决」, 现已裁决入池 issue 26-11-17-0214(question: reload 挪到 start_all 之前 vs 显式接管协议), 坑档随该 issue 处置一并落。

### R1-A · rebase hash 映射注记 (2026-11-17)

- 2026-11-17 为合流远端推进(origin/develop=3840ba10, 含 2e2ffe1f columns_grid 行窗口化), 本专题 8 笔提交被 rebase 线性重放, hash 全部改写。映射表(旧→新): f0004ef9→33d7f850 / 785ad5ae→ca820f5f / dae75d34→1f3f88a7 / df15af5f→1fad4fce / 3692616c→0df84475 / cd786499→24e8d063 / 11fc721d→4040c93d / 0c0caab3→2b78e9d7。 二次 rebase(origin/develop=12ff9a1e)后再改写, 上表为终值; 白名单机制终由上游 ARCHIVE_MD_EXCEPTIONS 承担, 我方重复实现于合流中弃用。
- df15af5f' 解 columns_grid 冲突(双方语义共存), 两追加修(ASCII 圈号/stub filteredGroups)折进 1fad4fce。上文 R1 段引用的旧 hash 为当时实测原值, 不回改, 追溯按本映射表换算。
- 树同一性核实(git diff --stat 逐对): 每对旧→新 hash 的树差 = 远端推进面(36 files, +2437/-71: columns_grid.js 行窗口化、webui static scan 测试面、skill-portability 文档面等), 我方各笔提交内容不变; 两基线切片(26-11-17-0159/26-11-17-0319)的实测数字继续有效。

### R2 · 真机复验轮 (2026-11-17 ~ 11-19)

- **执行面**: 计划 26-11-17-0636(§01 五项验收)七片(片A~G)全部执行完毕; 分支 relocate-rm-r2(本地), 末片 HEAD 3bef94ae。片级记账单点 = testing/real-baselines/ 八份切片: 26-11-17-0756(片A) → 26-11-18-0240(片A-fix) → -0425(片B) → -0648(片C) → -2308(片D) → 26-11-19-0102(片E) → -0330(片F) → -0505(片G)。
- **三态汇总**: 现有 21 条回归(RM04-01~21)片A 初判 3P/18F(测试基建形态过时, 四族工单) → 片A-fix 18 条适配后 **19P/1F/1S**(唯一 FAIL = RM04-05 L490 负向腿 QBT_REAL_SMALL_TARGET 环境前置, 用户拍板记账 FAIL; 唯一 SKIP = RM04-13 前提钉死); RM04-20 升 L3 负向腿落地。**13 条新增耐久用例**(RM04-22~34, acc 面 6 + E 面 7)逐片编写+耐久遍全 PASS(片B 4/4 · 片C 4/4 · 片D 9 正式遍 · 片E 4 正式+R26 修后 2 · 片F 6 正式遍 · 片G 6 正式遍); 升档 5 条(RM04-20 升 L3 + RM04-24/25/30/33 新建即 L3)。**全程产品回归 0 / 产品代码零改动**; 每片断轮二分全为测试侧造法/锚缺陷(当轮修再跑全绿); 执行期评审轮 R10/R11(片A-fix)→R16(片B)→R19(片C, 0711 声明收窄)→R23(片D)→R26(片E, probe_phase 实证坐实)→R30/R31(片F)→R34(片G)修复后重跑全绿闭环。
- **issue 翻灯结果**: 26-11-07-0528(撤销断粮语义)/26-11-10-0326(终态留账)/26-11-13-0535(删链门祖先)/26-11-13-0711(direct 绕过)/26-11-11-0553(换键占位, e2e 轨)/26-11-05-0420(零搬移)/26-11-14-0401(停机期删除)七条翻 **Done**(正文逐条补实际修法/验证方式/测试数字); 0420/0401 终态已定(RM04-26 真机闸门拦截成立·深层孪生, D2 预案未触发 / RM04-27 闭账三态符合 728d6ac8 定稿语义); 26-11-10-0638 不在本轮保持 Open; 新入池 26-11-18-0315(链浮窗健壮性, 片A-fix §3.3 暴露, Open 待认领)。
- **坑档蒸馏**: 新立 `pitfalls/testing/state-file-lag-and-journal-absence.md`(磁盘账 30S 迟滞只配终态等待 + journal armed 相位恒无文件, 过程断言取数面单点; 片C/E/F 三处实证, 片G 零复发)+ `pitfalls/testing/restart-transient-and-offline-cmd-window.md`(账面 rewritten 毫秒瞬态轮询不可观测[合并与 VERIFY 同拍] + 下线窗命令回执被 urllib3 重试预算阻塞 ~29s/次须放宽 90s; 片E 实锤); `pitfalls/ops/seed-clean-vs-evidence.md` **复发+1**(片E `--dir rm04` 整树清掉历史证据层 22 份, 增量面 = --dir 前先 ls 盘点非本轮所建目录 + case 根旧惯例是历史证据沉积层; 未命中 = 路由没到/读档未连线; 片F/G 盘点纪律零复发); `pitfalls/testing/bg-process-cleanup.md` 补实测结论(「terminate 只杀启动器留孤儿」片B R16 现场探针证伪: uv trampoline stub 死连带真解释器, plain stop 真问题是非优雅退出非孤儿)。
- **证据归档说明**: 逐遍证据在 tests-real/.work/(gitignored, 逐案 evidence 带时刻戳防覆写); **片E 起证据落点变更** = repo 外 `rm04-sliceE-evidence-archive\`(189 份, 片F/G 同款归档), 片A 既有 prev-run-archive 归档层; .work 顶层多片证据目录受证据闸保护在盘。
- **批次外待办**(本轮零代码改动, 转主会话/用户): ①AppProc.kill docstring「只杀启动器留孤儿」旧机制句 —— 片B 已证伪, 结论入 bg-process-cleanup 坑档, 代码句待 scope-guard 处置; ②深形态添加卷剩余取数面(片F RM04-31: precheck_add 卷剩余 scope_hit 恒 None, 是否改取数面属产品裁量)报用户决定是否入池; ③real-machine.md:26 约束 3 的 tests-real/config/*.yml 同款漂移(规程单点既有问题, 0636 §10 R2 遗留)报用户裁决。
- 2026-11-19 05:54 真机复验轮文档收口: test.full 全量绿(分支 tip 3bef94ae, 数字见 kb.baseline)、issue 七条翻灯、两计划回写(0636 §10 R3 + §03.4 RM04-25 卡「dst 祖先」口误勘误[权威口径 = 旧根严格父目录, 片C 已按此落刀]; 2340 §03.6 状态列翻灯 + §10 R3)、坑档四件、基线切片落位、本档案 R2 段。接缝终审随主会话收口轮执行; 提交由主会话统一走 ship.commit(本收口轮不提交)。

- 2026-11-19 06:20 真机复验轮收口: 计划 0636 七片执行完毕(21 回归适配 19P/1F/1S + 13 新增耐久用例全 PASS, 产品回归 0), issue 七条翻 Done(0528/0326/0535/0711/0553/0420/0401), 两计划回写(0636 R3+勘误 / 2340 状态列+R3), 坑档新立 2 + 复发+1 + 孤儿证伪, 基线切片落位, 档案 R2 段; 第二批 S5/S6 待开工

- 2026-11-20 02:45 S5 跨模块接口显式化两笔提交落地: a652290f(登记集退役+RelocateModule 派生查询三方法, fuse/grouping/ops_skip/qbapi 消费点迁 ctx.relocate 句柄)+80d8ea09(常量收口+接口 AST 守卫, 全仓 src 侧 relocate 家族私有名跨界 import 清零, units 增显式 __all__); 评审两批各 2 轮(10 修/3 修, 引文校验 10/10 与 3/3, 复评零新增); 验收达成: 消费面测试全绿(test.quick 6499P/2S/0F; test.full 6495P/6S/0F, 覆盖率闸门 99.73% 达标), grep 无跨层私有引用由 tests/test_relocate_interface_guard.py 机械承考(真仓 198 文件); 开工拍板三条记计划 §06 D11-D13(全按推荐); 基线切片 26-11-20-0244-relocate-refactor-s5 落位; 第二批 S6 待开工

### R3 · 第二批 S6 探测异步化落地 (2026-11-20)

- **五笔提交链**(T1-T5, 并轨 26-11-10-2350 D1-D10, 设计钉死点单点在该计划 R3): d899e91a T1 探测 runner 基建(单飞槽+结果队列+probe_pending 容器+线程侧独立 qB 连接) → 9caf2675 T2 _ensure_probe 异步化(意图入队+单飞 kick+探测中回执; 合并键=意图三元组, 并轨适配点: probe_fingerprint 实为 qB 连接身份不编码 src/dst) → 8f129b47 T3 verdict 消费接线(消费四步+probing 键防自环+队首重 kick 恢复+超龄清扫挂 start+apply) → 7d99ce32 T4 web 两段回执(受理段 warn+cmd_id 绑 receipt_ids 出站面+webui drain 补发) → 824f6b94 T5 sweep 四断点残留核验+两洞补扫(H1 目录残留根集扫描+H3 _map_local 映射; 目录认领收紧自产 token)。
- **分批评审**(派发/发现/修/轮): T1 2/8/8/3 · T2 2/3/3/3 · T3 2/4/4/2 · T4 2/7/6+忽1/2 · T5 1/1/1/2; 引文校验全过、复评均零 actionable(口径单点=各笔提交 Review trailer); T5 major = 裸前缀认领的用户目录误删面(全修: 认领收紧自产 token+lookalike 对照用例)。
- **测试与基线**: 新增 59 条(test_relocate_probe_async 20 / probe_gate_async 8 / probe_consume 19 / test_web_relocate 6 / test_relocate_probe 36→42); test.full 全绿(数字见 kb.baseline), 覆盖率闸门达标, 基线切片 26-11-20-2348-relocate-refactor-s6 落位; T3 实施中 test_ascii_symbol_guard 批内拦截计划圈号进 .py 注释(坑档 testing/ascii-circled-digits-py-comments.md 复发+1: 实施子代理扫了 pitfalls/_index 但没打开该条目再动笔, 批内拦截未产生复评成本)。
- **真机延期与边界**: 真机复验三项拍板延期待真机复验轮 —— dry-run 冒烟(web 命令全链回执管线正常且无 probing 桶, notes 含「dry-run: 跳过强探测」)/受理段 warn 验证挂非 dry-run 真实探测窗/FS 不可达时主循环 tick 停摆<单步预算(评审终审校准: dry-run 短路在闸决策表第 2 位(先于缓存与未命中), --dry-run 下「探测中」受理段结构性不出现, 原判据「dry-run 冒烟受理段」按代码现实不可达); issue 26-11-10-0638 保持 Open(正文补落地注记), 复验 PASS 后关(2350 §04-S6 的 issue 置 Done 判据随之顺延); 本收口轮零代码改动, 提交统一走主会话 ship.commit。
- **S5 hash rebase 注记**: S5 两笔经 rebase 改写 a652290f→bde75be0 / 80d8ea09→28e3b4dd(树差=远端推进面 27 文件, tests 仅 +3 用例: a14e1e20 ALT 解锁 +2 / e0411a38 行高恒等 +1), R1-A 同型; 上文 S5 行与计划 R4 的旧 hash 为当时实测原值不回改, 追溯按本映射换算, 计划 R5 与基线切片差值口径均按新 hash 记。

- 2026-11-20 23:54 S6 探测异步化收口: T1-T5 五笔提交落地(评审五批全闭环, 见 R3 段), test.full 6557P/6S/0F 覆盖率闸门 99.70% 达标, 基线切片 26-11-20-2348-relocate-refactor-s6 落位, 两计划回写(2350 R3 并轨执行完成 / 2340 R5+§04-S6+§03.6), issue 0638 补落地注记保持 Open, 坑档圈号复发+1; 真机复验三项(dry-run 冒烟/受理段 warn 挂非 dry-run 真实探测窗/FS 不可达 tick 停摆断言)拍板延期待复验轮(评审终审校准, 判据详见 R3 段)
