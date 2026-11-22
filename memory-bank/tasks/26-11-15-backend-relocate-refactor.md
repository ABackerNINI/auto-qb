# 26-11-15-backend-relocate-refactor — relocate 结构重构: 单活任务模型与判定收敛

**Status:** In Progress
**Added:** 2026-11-15
**Updated:** 2026-11-21
**Summary:** relocate 结构重构: 第一批 S1-S4(单活任务模型/撤销不搬回/生命周期账统一/路径判定单点)六笔提交落地 + 真机复验轮(26-11-17~19, 计划 0636 七片执行完毕: 21 条回归适配 + 13 条新增耐久用例全 PASS, 产品回归 0)+ issue 七条翻 Done; S5 跨模块接口显式化两笔提交落地(a652290f 登记集退役改 RelocateModule 派生查询 / 80d8ea09 常量收口+接口 AST 守卫, 全仓 src 侧 relocate 家族私有名跨界 import 清零, test.quick 6499P/2S/0F); S6 探测异步化五笔提交落地(0c1b7d5b 等五笔, 并轨 2350 D1-D10, 单测/仿真面全绿)+ RM11 真机复验轮三项 PASS(26-11-21, 计划 26-11-21-0223, 切片 26-11-21-0446: 3P/0F/0B, 产品回归 0), issue 0638 翻 Done, 两批计划均翻 Done, 全专题闭合
**Topics:** backend-relocate-refactor
**Refs:** memory-bank/plans/26-11-15-2340-plan-relocate-refactor.html, memory-bank/issues/26-11-17-0214-question-qbmanager-startup-reload-state-discard.html, memory-bank/pitfalls/backend/startup-state-write-reload-discard.md, memory-bank/plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html, memory-bank/plans/26-11-21-0223-plan-real-rm11-s6-probe-verify.html, memory-bank/pitfalls/testing/state-file-lag-and-journal-absence.md, memory-bank/pitfalls/testing/restart-transient-and-offline-cmd-window.md, memory-bank/testing/baselines/26-11-21-0658-relocate-refactor-rm11-close.md

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
| S6 | 探测异步化(并轨 2350) | Done(第二批; 单测+真机复验全达成, RM11 轮 3P/0F/0B, issue 0638 已翻 Done) |

## 进度日志

> 已外迁: R0/R1/R1-A/R2 轮次全文 → [attachments/26-11-15-backend-relocate-refactor-progress-archive.md](attachments/26-11-15-backend-relocate-refactor-progress-archive.md)（2026-11-22 cap 清零）

### R3 · 第二批 S6 探测异步化落地 (2026-11-20)

- **五笔提交链**(T1-T5, 并轨 26-11-10-2350 D1-D10, 设计钉死点单点在该计划 R3): d899e91a T1 探测 runner 基建(单飞槽+结果队列+probe_pending 容器+线程侧独立 qB 连接) → 9caf2675 T2 _ensure_probe 异步化(意图入队+单飞 kick+探测中回执; 合并键=意图三元组, 并轨适配点: probe_fingerprint 实为 qB 连接身份不编码 src/dst) → 8f129b47 T3 verdict 消费接线(消费四步+probing 键防自环+队首重 kick 恢复+超龄清扫挂 start+apply) → 7d99ce32 T4 web 两段回执(受理段 warn+cmd_id 绑 receipt_ids 出站面+webui drain 补发) → 824f6b94 T5 sweep 四断点残留核验+两洞补扫(H1 目录残留根集扫描+H3 _map_local 映射; 目录认领收紧自产 token)。
- **分批评审**(派发/发现/修/轮): T1 2/8/8/3 · T2 2/3/3/3 · T3 2/4/4/2 · T4 2/7/6+忽1/2 · T5 1/1/1/2; 引文校验全过、复评均零 actionable(口径单点=各笔提交 Review trailer); T5 major = 裸前缀认领的用户目录误删面(全修: 认领收紧自产 token+lookalike 对照用例)。
- **测试与基线**: 新增 59 条(test_relocate_probe_async 20 / probe_gate_async 8 / probe_consume 19 / test_web_relocate 6 / test_relocate_probe 36→42); test.full 全绿(数字见 kb.baseline), 覆盖率闸门达标, 基线切片 26-11-20-2348-relocate-refactor-s6 落位; T3 实施中 test_ascii_symbol_guard 批内拦截计划圈号进 .py 注释(坑档 testing/ascii-circled-digits-py-comments.md 复发+1: 实施子代理扫了 pitfalls/_index 但没打开该条目再动笔, 批内拦截未产生复评成本)。
- **真机延期与边界**: 真机复验三项拍板延期待真机复验轮 —— dry-run 冒烟(web 命令全链回执管线正常且无 probing 桶, notes 含「dry-run: 跳过强探测」)/受理段 warn 验证挂非 dry-run 真实探测窗/FS 不可达时主循环 tick 停摆<单步预算(评审终审校准: dry-run 短路在闸决策表第 2 位(先于缓存与未命中), --dry-run 下「探测中」受理段结构性不出现, 原判据「dry-run 冒烟受理段」按代码现实不可达); issue 26-11-10-0638 保持 Open(正文补落地注记), 复验 PASS 后关(2350 §04-S6 的 issue 置 Done 判据随之顺延); 本收口轮零代码改动, 提交统一走主会话 ship.commit。
- **S5 hash rebase 注记**: S5 两笔经 rebase 改写 a652290f→bde75be0 / 80d8ea09→28e3b4dd(树差=远端推进面 27 文件, tests 仅 +3 用例: a14e1e20 ALT 解锁 +2 / e0411a38 行高恒等 +1), R1-A 同型; 上文 S5 行与计划 R4 的旧 hash 为当时实测原值不回改, 追溯按本映射换算, 计划 R5 与基线切片差值口径均按新 hash 记。
- **S6 hash rebase 注记**: S6 五笔+T6 收尾共六笔经 rebase(2026-11-21, origin/develop=d5e5e0c2, 远端并行=WEBUI 列风格切换整批 + hold_run 基址改私用段随机抽取 flake 根治)线性重放, hash 全部改写, 映射: d899e91a→0c1b7d5b / 9caf2675→c964278d / 8f129b47→120b14df / 7d99ce32→20540c53 / 824f6b94→1cd04a20 / 36f1f171→3f34af3b, S5 注记/R1-A 同型; 上文本段与计划 R5/R6、基线切片引用的旧 hash 为当时实测原值不回改, 追溯一律按本映射换算(映射表单点=计划 2340 R7)。

- 2026-11-20 23:54 S6 探测异步化收口: T1-T5 五笔提交落地(评审五批全闭环, 见 R3 段), test.full 6557P/6S/0F 覆盖率闸门 99.70% 达标, 基线切片 26-11-20-2348-relocate-refactor-s6 落位, 两计划回写(2350 R3 并轨执行完成 / 2340 R5+§04-S6+§03.6), issue 0638 补落地注记保持 Open, 坑档圈号复发+1; 真机复验三项(dry-run 冒烟/受理段 warn 挂非 dry-run 真实探测窗/FS 不可达 tick 停摆断言)拍板延期待复验轮(评审终审校准, 判据详见 R3 段)

### R4 · RM11 真机复验轮: S6 三项闭合 (2026-11-21)

- **执行面**: 计划 26-11-21-0223(§10 R3), 分支 relocate-rm-s6(纯本地无远端), 切片 26-11-21-0446-real-rm11-sliceA(基线 commit 310f125d, 实测全程 HEAD 未动; 测试侧 mover 动态识别修随 73e8f422 入库)。环境2(C盘机, 56589/56590 qB v5.2.3), 逐条 `real.run --case --yes`, 未跑整片 suite; 串行序 RM04-35→36→37。
- **三态汇总**: **3 PASS / 0 FAIL / 0 BLOCKED** —— RM04-35 dry-run 冒烟 L3(A 腿零副作用+双 dry-run note+无 probing 键; B 对照腿真实受理 blocked+probing 键+verdict passed/ok, 分支承重实证; 判据①按 R6 校准拆两腿, web 全链由 RM04-36 承载)/ RM04-36 受理段 warn 全链(A1 warn→A3 verdict 消费→A4 终态补发→A5 mover 真搬 done(finalized)→A6 缓存落盘)/ RM04-37 FS 不可达行为面代理(句柄锁造法预检成立 write_proof_timeout/env=False 无 BLOCKED; W1-W7 七项阈值全落内: W1 受理 0.04s≤5s+缓存 at 差 12.5s≥8s / W2 窗内 pause 0.03s≤8s / W3 verdict 消费 13.79s≤25s / W4 补发 error 含「已缓存」0.87s≤10s)。**产品回归 0 / 产品代码零改动**。
- **断轮二分**: 2 起均测试侧/环境面, 非产品回归 —— RM04-35 attempt1 = 上轮遗留 210 枚 real-fake 假种子撞前置 fail-closed 断言(guard「真实种子 210」系计数误标: runner.py:74/conftest.py:33 调 guard.snapshot 未传 skip_tags, 入池 26-11-21-0639); RM04-36 attempt1 = 用例把 mover 硬编码在 h1, 产品 mover 选拔 records[0] 随 qB 列表序轮换(两轮实测 h2/h1 相反), 测试侧改动态识别 mover(先到 dst 的唯一成员)后 attempt2 过。
- **执行事故与减损**: 收尾 `real.seed.clean --yes` 裸跑整扫误删 tests-real/.work/rm04/async/ 全部取证(24 evidence json + 3 产品日志副本)与 rm04 顶层 11 份 tee 日志共 38 份(gitignored 直删不可恢复); 踩中坑 pitfalls/ops/seed-clean-vs-evidence.md **复发+1**(为什么没命中: 只读计划 §07-R9 转述没读坑原文, 把「闸会拦」当保障, --dir 前盘点纪律没进执行序列; 直接放大器 = clean 保护闸只查 .work 顶层、rmNN 内层不设防, 入池 26-11-21-0638); 减损 = 三用例关键数字执行时逐字段打印誊录 + 计时双口径(pytest 汇总行 / real.run 外层包装)来源标注, 切片数字即实测值, 幸存收尾 guard 终态 tee。
- **收尾核净**: real.seed.rm --all 命中 0; guard 终态复跑双实例 firewalled、真实种子 0; 进程比对一致(pid 无轮换, real.down 未使用, 按守卫语义保留双实例在线净态)。
- **批次评审轨迹**(主会话派只读子代理): 批A 9 发现(1 弃 8 修复)复评零 actionable / 批B 4 轮 11 发现全修、派发 2 / 批C 2 轮 2 修; RM11 计划 §10 R2 记批A 修复面, 批B 同步用例文件 W1/W5 断言面。
- **计划外四项入池**(Open 待认领): 26-11-21-0638(real.seed.clean 保护闸只查 .work 顶层, rmNN 内层证据不设防) / 26-11-21-0639(real.guard「真实种子 N」计数把 real-fake 计入) / 26-11-21-0639(review 记账排除面缺 memory-bank/testing/real-baselines/) / 26-11-21-0639(kb.wrap --topic kebab 校验拒绝 sliceA 式大写 + real.guard 输出 vv5.2.3 双 v 拼印, cosmetic 合并)。
- **文档面**: RM11 计划回写(§10 R3 + §3.2「210 个真实种子」误标勘误 + doc-status 翻 Done)/ 母计划 2340 回写(§03.6 0638 行翻灯 + §04-S6 达成注记 + §10 R8 + §01 三目标核验后 doc-status Open→Done)/ issue 26-11-10-0638 翻 Done(正文补实际修法/验证方式/测试数字)/ 坑档复发+1 + kb.index 重建 / 基线切片落位(数字见 kb.baseline)。
- **提交指针**: 9bbde6e4(执行计划立项)/ 310f125d(真机用例 RM04-35~37 落地)/ 73e8f422(切片A + mover 动态识别修); 本批收尾回写(两计划/四 issue/坑档/本档案/基线切片)另行提交。
