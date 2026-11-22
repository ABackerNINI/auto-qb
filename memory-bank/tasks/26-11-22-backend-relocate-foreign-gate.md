# 26-11-22-backend-relocate-foreign-gate — foreign 判定门内容根收窄与收尾进展同步呈现: 计划 26-11-21-1600 S1-S3 实施

**Status:** Done
**Added:** 2026-11-22
**Updated:** 2026-11-22
**Summary:** foreign 判定门内容根收窄与收尾进展同步呈现: 计划 26-11-21-1600 S1-S3 五批落地 + 接缝终审钉档 + S4 真机验收完成(测试 qB 环境, 判据终态 ①PARTIAL/②③④⑤ PASS/⑥ 全绿) + 七件修复计划 26-11-22-1714 三批落地(c03f09e0/7e56f8c4/f1cd83bb)+ 接缝终审零发现 + 7 issue 翻 Done, 全绿见 kb.baseline; 真机 S4 复验五项待窗口
**Topics:** backend-relocate-foreign-gate
**Refs:** memory-bank/plans/26-11-21-1600-plan-relocate-foreign-gate.html, memory-bank/issues/26-11-21-1500-bug-relocate-foreign-sibling-mismatch-flood.html, memory-bank/issues/26-11-21-1326-refactor-relocate-foreign-notified-cleanup.html, memory-bank/testing/baselines/26-11-22-0533-backend-relocate-foreign-gate.md, memory-bank/issues/26-11-22-0604-refactor-content-root-of-duplicate-join-semantics.html, memory-bank/issues/26-11-22-0604-refactor-curves-syntaxwarning-invalid-escape.html, memory-bank/testing/baselines/26-11-22-0821-backend-relocate-foreign-gate.md, memory-bank/issues/26-11-22-0905-bug-relocate-chain-gate-eq-false-dep-self-lock.html, memory-bank/issues/26-11-22-0905-bug-relocate-foreign-added-diff-race-miss.html, memory-bank/issues/26-11-22-0905-question-relocate-confirm-probe-reask-three-step.html, memory-bank/issues/26-11-22-0905-refactor-relocate-armed-log-alias-kind-naming.html, memory-bank/issues/26-11-22-0905-feat-relocate-foreign-accounted-skip-debug-log.html, memory-bank/issues/26-11-22-0906-feat-relocate-daemon-resume-no-log.html, memory-bank/plans/26-11-22-1714-plan-relocate-foreign-gate.html, memory-bank/testing/baselines/26-11-22-2035-backend-relocate-foreign-gate.md

## 本篇只回答

计划 26-11-21-1600(B1 判定门内容根预筛 / B2 账面终态清理+文案 / B3 可观测性+WEBUI 行同步)的 S1-S3 怎么实施、做到哪了 —— 方案细节与拍板 D1-D9 单点在计划。

## 原始请求

1. <!-- wording:allow --> 「先拆解任务, 然后派子智能体分阶段实施下面的任务, 大任务需要拆分成稍小任务防止子智能体长任务过长和出错后进度全部丢失……待拍板的先询问, 你只负责委派总结, 不负责实际实施, 开新的本地分支, 每步完成后使用 ship.commit --no-push 本地 commit……全程在本地分支上工作, 完成后同步到本地 develop(rebase 保线性), 完成后等待提交指令……任务: 26-11-21-1600-plan-relocate-foreign-gate.html S1-S3」。
2. 派遣纪律: 并发数任何时刻不超过 2(含主会话), 可能写冲突的串行、只读可并行 2; 子智能体失败/超时可用 SendMessage 续跑, 非正常失败 3 次停止等待人工。
3. 后续: 「提交, 然后入池, 最后提交入池」—— 触发收尾回写 + 推送 + 两条范围外发现入池。

## 思考过程与决策

- 拆解: S1/B1 与 S2/B2 各一批, S3/B3 按前后端拆两批(后端=daemon 日志+等待提示+rewritten 日志, 前端=WEBUI 行状态+e2e), 收口=全量+接缝终审; 每批独立评审独立本地提交, 批间零牵连。
- 流程: 每批走「写入子代理 → ship.gate 预跑 → review.pack → 只读评审子代理(本地分支态三钉) → review.check 引文校验 → 修复增量 → 复评到零 actionable → ship.commit --no-push」; 615/557 行超 400 走分面派遣(2/3 面), trailer 记 `· 派发`。
- 环境坑: 本 shell 外部 TMPDIR 触 rc=4(坑档复发 12)——所有 pytest 链(ship.gate/ship.commit 内含)一律 `env -u TMPDIR` 前缀。
- 计划内裁决 1 处: S3a 实现者报「daemon 无 INFO 流程行, S4-④ 将落空」——判为计划内(§01 成事判据+验收④的直接前置)当场补进本批。
- 用户拍板 1 处(接缝终审): mismatch 条目终态清理后种子仍在场会重判重发一次 WARNING, D4「自然重判为场景 B」只对 kind=A 成立 —— 选 a) 接受现状+钉档, 零行为改动, docstring 按终态类别写全 + done/failed 双面守阵。
- 评审战果: 5 批 11 轮(含分面 2/3), 检 16/16 全过、修 16、入池 0、blocker 0; major 1 个(S2 崩溃窗恢复路径漏挂清理, 恰是 1326 滞留的恢复面)+ 接缝级语义缺口 1 个, 均已处置。
- 提交链(本地分支 relocate-foreign-gate-s1-s3, 后 rebase 进 develop): 41d40168(S1/B1)→ 1d4ae8cb(S2/B2)→ 42a9face(S3/B3 后端)→ de73d571(S3/B3 前端)→ 4e0c6662(接缝钉档; rebase 后 hash, 原 1d38c458/2be15c87/c8fbb05f/e6f60909/2d35627d)。

## 实现计划

按计划 §04: S1 内容根预筛(纯函数入 relocate_units + _foreign_drain 接线 A/B 两路) → S2 终态清理单点(非终态→终态边沿, kind 分流) + mismatch 文案改口径 → S3 后端可观测性(daemon 日志落盘/流程 INFO 行/WAIT 提示/rewritten 合并日志) → S3 前端行状态细化(finalize_state 三态投影 + decorate 单点 + e2e 四皮肤) → 收口(全量 test.full + 接缝终审)。S4 真机验收不在本任务范围(计划独立步骤, 需真机环境)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | B1 内容根预筛(纯函数+接线+DEBUG 丢弃) | Done(2026-11-22) |
| S2 | B2 终态清理(kind 分流, 三接线)+mismatch 文案改口径 | Done(2026-11-22) |
| S3 | B3 后端(daemon 日志+流程行+WAIT 提示+rewritten 日志) | Done(2026-11-22) |
| S3 | B3 前端(WEBUI 行三态+保存路径+e2e 四皮肤) | Done(2026-11-22) |
| 接缝 | 终审 3 轮零 actionable + 拍板 a 钉档批 | Done(2026-11-22) |
| 收尾 | 文档回写+基线切片+issue 翻 Done+推送 | Done(2026-11-22) |
| S4 | 真机验收(完整整组迁移全链复验, 计划验收⑤六条) | Done(2026-11-22, 测试 qB 环境环境2; 判据终态 ①PARTIAL/②③④⑤ PASS/⑥ 全绿; F1/F3 两发现已入池, 见进度日志 R2) |

## 进度日志

### R0 · 立档 (2026-11-22)

- S1-S3 五批 + 接缝钉档全部落地: 评审 5 批 11 轮检 16/16 修 16 零 blocker; test.full 全绿(见 kb.baseline); e2e @fast 三分片 515 passed/0 失败(四皮肤); 本地分支 rebase 进 develop 保线性, 随本专题入库。
- 接缝终审 1 项语义出入(mismatch 重判重发)经用户拍板 a) 接受现状+钉档, 未改行为。
- 范围外发现 2 条(grouping_mod._content_root_of 副本口径差 / core/curves.py:53 存量 SyntaxWarning)按用户指令转正入池(issues 池, 时间戳 slug 可 grep)。

- 2026-11-22 05:36 计划 26-11-21-1600 S1-S3 五批落地(预筛/终态清理+文案/daemon日志+流程行/WEBUI行三态)+接缝终审3轮钉档, 全绿见 kb.baseline; 真机 S4 待窗口

### R2 · S4 真机验收完成 (2026-11-22)

- **环境拍板改判**: 用户拍板 S4 走测试 qB 环境(环境2 副实例 56590, real.up 拉起)而非生产实例; 物理步骤(挪目录/停启 qB/探针添加)全部由子代理代执行; 外部种子走模拟(real.seed + add_multi 配方)。
- **三窗执行史**:
  - 窗1: T5① 场景A探针活到达两次未纳入(分组面收编为第3组成员) → F1 停手。
  - 窗2: 事故同款 activation 带账扫描一次全中(兄弟×2 预筛丢弃 / 探针A 场景A纳入三连 job 2→3 / mm1 mismatch 新文案落账) → 窗口链 T7-T10 全 PASS(进窗 L1 恰一条 / 逐成员改写 2 落盘+1 幂等 / 相位合并 armed→rewritten / WEBUI await_window→await_recheck) → F3 删链门自锁停手。
  - 窗3: 按产品 last_error 指引定向删 3 依赖(全是自造 real-fake) → 依赖清零 → 别名删除 → 收尾完成逐字命中 → job done(finalized) → 场景B探针 kind=B 全中 → 重启 done 账面候选 0、探针B 跨重启持久。
- **判据终态(计划 §04 S4 六条)**:
  - ① PARTIAL —— 侦测扫描腿全 PASS(计划字面①只覆盖侦测扫描); 删链门腿自锁 = F3, 删链门是执行者语义扩展(更近②「删链正常」), 本档案按扩展读法记 PARTIAL 并注明。
  - ② PASS —— 探针A 场景A纳入三连 job 2→3。
  - ③ PASS —— 窗口链 T7-T10: qB 下线→改写→回连→收尾完成全程日志 + WEBUI 行同步可见。
  - ④ PASS —— L1 即时进窗恰一条实证; L2 兜底腿真机未触发(qB 优雅下线即 L1, 单测守阵覆盖)。
  - ⑤ PASS —— mm1 mismatch 条目走「种子消失」清理先于终态(两条清理路径各有逐字 DEBUG 行), 终态 B2 只清 kind=A 1 条(计划「清 2 条」是运行手册预期, 计划 §04 字面「条目已清」达成); 场景B探针 kind=B 全中保留; mismatch 新文案呈现正确。
  - ⑥ PASS —— test.full 6789 passed / 6 skipped 覆盖率 99%, 基线切片 26-11-22-0821。
  - 口径注: timeline 末节把⑥标成「PASS(等效形态)」属标注漂移, 以本档案为准(⑥ = 全量 + 基线切片, 已跑)。
- **两发现(已拍板入池, 2026-11-22, 只建件未认领)**:
  - **F1 活到达差集漏接**: store.last_added_diff 每轮覆盖重算(含零变化轮, store.py:490)+ 窗口 1.5s vs 2S relocate tick 拍频错位, 单事件漏接约 1/4(探针A两漏/探针B一中实证); 0434 D12/D13 既有边界, 非本计划引入; 修法方向 = 累积游标或 arm 等待期低频兜底扫。已入池: `26-11-22-0905-bug-relocate-foreign-added-diff-race-miss`(bug·便签档)。
  - **F3 删链门收尾自锁**: chain_gate_hits 等值面(_norm(sp)==eq, relocate_units.py:2183)不查内容根 —— 该等值面是 2076c889(11-08)评审 blocker 有意加回的, 把 save_path 恰等旧根的同根兄弟判为依赖(数据不经 junction = 假依赖), deps 恒非零 → 别名永不删 → 收尾永不完成; 触发布局 = dir_alias + 多成员 + 同根兄弟; 保守向不丢数据但不可自愈, INFO 每 2s 刷屏无去重(138 行/4.5min)+ last_error 指引误导; 修法方向 = 等值面命中加内容根/文件交集判别(复用 content_root_of/file_alias_intersects)。11-21 事故未自锁的原因已查实: 事故 job 自有形态非 dir_alias(direct 短路或 file_links+R2 文件交集豁免), 「等值面在位 + 收尾完成 + 60 兄弟恰等旧根」三实证强制推出。已入池: `26-11-22-0905-bug-relocate-chain-gate-eq-false-dep-self-lock`(bug·标准档, 建议认领修复)。
- **观察项处置(四件已拍板入池便签, 2026-11-22)**: T2 confirm 强探测消费 confirm 位致三步交互(`26-11-22-0905-question-relocate-confirm-probe-reask-three-step`)/ 武装行「形态 dir」内部命名泄漏(`26-11-22-0905-refactor-relocate-armed-log-alias-kind-naming`)/ 在账跳过无日志行(relocate_foreign.py:218 静默 continue, `26-11-22-0905-feat-relocate-foreign-accounted-skip-debug-log`)/ daemon 续任无日志(`26-11-22-0906-feat-relocate-daemon-resume-no-log`) —— 四件便签档; journal 命名与 daemon 0 字节属行为正确, 不入池。
- **证据**: tests-real/.work/rm04_s4/evidence/(gitignored, 三窗 timeline + 日志 + 账面 + api 快照)。

- 2026-11-22 08:55 S4 真机验收完成(测试 qB 环境环境2 三窗): 判据终态 ①PARTIAL(侦测三时机 PASS/删链门腿=F3 扩展读法)/②③④⑤ PASS(④ L2 腿未触发/⑤ 双清理路径注)/⑥ 全绿基线 26-11-22-0821; 两发现 F1(活到达差集漏接, 0434 既有边界)/F3(删链门等值面假依赖自锁, 2076c889 引入)待拍板入池; 评审 3 轮 actionable 0; 详见档案 R2 与计划 R2

- 2026-11-22 09:06 S4 发现入池收尾(用户拍板, 只建件未认领): 六件入池 —— F3 删链门等值面假依赖自锁(bug·标准档, 建议认领修复)/F1 活到达差集漏接(bug·便签档)/观察项四便签(T2 confirm 流 question/武装行文案 refactor/在账跳过 DEBUG feat/daemon 续任 INFO feat), 时间戳 slug 见上方 R2 两发现与观察项条目; 六件 doc-refs ↔ 档案 Refs/计划 doc-refs 双向声明由 kb.new 自动补链

- 2026-11-22 17:42 七件修复计划立案轮(grilling 两轮 12 问全按推荐拍板 + 计划 26-11-22-1714 立案)评审收尾: 批 217 行纯文档, 3 轮零 actionable —— 首轮检 2/2 全过(2 minor 当场修: 批2/批3 测试步骤补 tests 头部「测试计划」docstring 同步说明、store.py :205-210 生命周期注释块改述入列); 复评轮 1 nit(计划内 store 注释「」转写非逐字)当场逐字化修掉, 第 3 轮 byte 级核验零发现; 该 nit 因修复后引文失效机检 REFUTE 不进修数(非幻觉, 处置留痕于计划件批2 store.py 步骤现文); Review trailer 基 17708c855224; test.full 全绿基线切片 26-11-22-1727, 本批随本专题入库

- 2026-11-22 17:27 grilling 两轮 12 问拍板(全按推荐)+ 七件修复计划立案 26-11-22-1714(等值面假依赖精判/差集累积游标/观测性文案/副本收编, 三批切分), 修复轮待实施

### R3 · 七件修复落地 (2026-11-22)

- **开工同步(硬性)**: 本轮会话开工同步行「已同步 839eb6e5(快进 f76cd450→839eb6e5)」+ 本地分支 fix/relocate-gate-closeout 全程本地态(基线 839eb6e5, 提交链 c03f09e0/213fbc9d/7e56f8c4/f1cd83bb)。
- **三批落地**:
  - 批1 c03f09e0(F1 等值面假依赖精判+刷屏去重+last_error 文案 + F7 content_root_of 副本收编; 评审 2 轮: 轮1 检 2/2 修 2[测试 scope 假构造 minor+注释表述 nit], 轮2 零 actionable; test.quick 6995P/0F/2S);
  - 批2 7e56f8c4(F2 差集改累积游标 pending_added_diff+take_added_diff 消费即排空; 评审 2 轮: 轮1 唯一送检发现因 relevance 字段枚举非法被 review.check 机械 REFUTE 弃用[其所指架构附件旧名漂移由本轮总收尾回写消化], 轮2 零发现; 7000P/0F/2S);
  - 批3 f1cd83bb(F3 daemon 三事件 INFO/F4 在账跳过 DEBUG/F5 回执预告/F6 武装行取 plan.form; 评审 2 轮零发现; 7003P/0F/2S);
- **接缝终审零发现放行**(四问: 无跨批漂移/无双套机制/测试面无重叠无漏钉/偏离合计守住设计底线);
- **7 个 issue 全部翻 Done 并回填**实际修法/验证方式/测试数字;
- **D3 对 0434 D12 的修订留痕**: 0434 拍板「last_added_diff 只读不排空」由本计划 D3 修订为「累积游标+消费即排空」(0434 历史 HTML 按计划 §01 底线 5 不改写, 以本档案为准);
- **计划外事项**: 基线 839eb6e5 自身档案缺「## 子任务状态表」章节致命名守卫红(经用户拍板补章节, 独立小提交 213fbc9d); F7 实施发现旧副本对 save_path=None 的假值容忍单点没有(3 调用点补 str(x or "") 折假值, test_web_relocate 退化用例当场抓红验证);
- **计划外事项(补覆盖小轮, 用户拍板)**: 总收尾 test.full 覆盖率闸红归因批2 池序依赖 —— relocate_foreign.py:434-436+434 True 臂为既有行, 覆盖确定性被 F2 改变(旧「每拍重算不排空」消失候选下拍必重入池覆盖恒定, F2 后只在消失候选恰留池尾执行, 池序 = frozenset 迭代序 hash 种子随机, 每轮 ~57% 覆盖/43% 缺失抖动); 修法 = test_relocate_foreign.py 新增 test_foreign_drain_vanish_pop_pool_order_independent(_foreign_enqueue 直控池序, 断言池清空+消失不记账+零 qB API 调用, 4/4 轮恒覆盖) + pytest.ini :19 注释对齐 conftest 单点(Windows 99.5/其余 99.0); 终验 rc=0 全绿 7000P/0F/6S(两次复验 148.4s/169.6s), test.quick 7004P/0F/2S。
- **待办**: 真机 S4 复验清单五项(计划 §04 批3)待用户窗口, 完成后计划翻终态。

- 2026-11-22 20:35 26-11-22-1714 七件修复三批落地(c03f09e0 判定面 F1+F7/7e56f8c4 差集累积游标 F2/f1cd83bb 观测性 F3-F6)+ 接缝终审零发现放行 + 7 issue 翻 Done 回填; 真机 S4 复验五项待窗口
