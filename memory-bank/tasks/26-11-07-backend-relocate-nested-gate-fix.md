# 26-11-07-backend-relocate-nested-gate-fix — relocate 嵌套闸门误拦修正实施

**Status:** In Progress
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
4. 拆解任务,派子智能体分阶段依次实施(串行防超并发;大任务拆小防 O(n²) token 与进度丢失;关联小任务合并;待拍板先询问;委派方只委派+总结;开新本地分支,每步本地 commit **不走 my-commit-flow**;子智能体免 sync;全程本地分支,完成后同步到本地 develop 等提交指令;子智能体提前停可 SendMessage 续跑;非正常失败 3 次停止等人工)。
5. 任务 = 本地提交计划 + 实施计划 + 完成后复验。

## 思考过程与决策

- 计划: `memory-bank/plans/26-11-07-1300-plan-relocate-nested-gate-fix.html`,拍板 D1-D8 全落档(对称修/scope 收窄/confirm 披露/文件级放行/UI 双披露点/互嵌形式化/真机先行/UI 缺口补齐),无待拍板遗留。
- 编排决策: 串行子代理 T1a(E1-E3)→ T1b(E4-E8)→ 回炉检查点 → T2(P2 核心+单测)→ T3(P3 UI)→ T4a(真机复验)→ T4b(test.full+基线)→ T5(code-review)→ T6(收尾回写)→ 合回 develop。
- 分支纪律: 本地分支 `relocate-nested-gate-fix`(自 develop f7ac0e46),每阶段委派方本地 commit(plain git,gitmoji+中文),不推远端;完成后 ff 合回本地 develop 等待提交指令。

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
| S7 | T5 code-review | Open |
| S8 | T6 收尾回写 | Open |
| S9 | 合回本地 develop(不推) | Open |

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

### R1 · T1a P1a 真机实验 (2026-11-07)

环境: 本机=环境2(C盘机),测试实例 56589/56590(qB 5.2.3 Legacy,免鉴权),real.up/down 起停,全程 real-fake 假种子,三约束全程未破,生产零触碰。任务提示写的 36595/36596 与 `R:/tests-real/.work` 是环境1机器事实,本机无 R: 盘;工作目录=仓库内 `tests-real/.work/`。证据(含脚本)在 `tests-real/.work/p1exp/evidence/`(gitignored;勿跑 real.seed.clean,整扫会清掉它)。

**⚠ 回炉发现(与 §03 推演不符,置顶)**: E2/E3 全链路走到核验通过后,**删链门自锁** —— `_chain_gate_deps`(relocate_exec.py:746)扫 qB 全量 save_path 对 `job.src`(= mover 声明源,非内容根)做等值/前缀匹配且**不排除本组成员**;target 在声明源内(R4/R5 放行形态)时成员搬后 save_path=dst ⊆ src 恒命中,依赖恒 ≥2,job 永卡 `rewritten/chain_deps`("删链门依赖未清(2 个)"×123 行/轮),别名永不删。E2 断言「删链全绿」**FAIL**;E3 的「D16 摩擦收尾后消失」推演随之**不成立**(收尾永不到来)。P2 若放行 R4/R5,必须同步重锚删链门(如锚改 job.scope 或豁免 job.hashes),否则放行=永久别名+永久 D16 摩擦。E1/E2/E3 其余断言全过: 账面 1.00 恒定 / 磁盘原名落位 / 零 recheck(244-918 拍状态采样,状态集合仅 stalledUP/stoppedUP)/ 零拒载(qB 日志「无法解析恢复数据」0 条)/ 别名期经硬链接可达。

逐 E 结果:
- **E1 PASS**: 多成员(2)3 文件同内容异 piece_len 组,target=源内待删兄弟目录,现行预检 `gates=['nested']` blocked,文案逐字留证(e1/precheck_receipt.json)。
- **E2(X: 跨盘符拓扑,生产同形)PASS 除删链外**: 旁路=测试侧启动器进程内 monkeypatch `nested_target_on`(盘上代码零改动);setLocation→3 硬链→武装→离线窗改写(52s,daemon 全机无 qB 才开窗)→重启双成员原生落位→核验;删链门自锁如上。
- **E2c(同盘 C: 变体,附加)**: qB 5.2.3 对与自身 CWD 同盘的保存路径把 fastresume 三路径键写成**相对形态**(probe_fr_path_forms.json 实证,相对 qB 便携 profile 目录约 4 层),daemon 改写按设计跳过(N10 口径)→ 非 mover 成员重启滞留旧根(经别名可读),job 静默等在 rewritten。同盘部署形态下整条收尾链无效 —— 生产同盘部署(数据与 qB 同盘符)有同样风险,建议委派方知悉。
- **E3 PASS 除删链外**: target ⊆ 旧内容根,qB setLocation 搬入自身子树**成功**;链接叶与新数据混居实证(disk_src_final.json: 旧内容根内 3 硬链叶 nlink=2 + 待删2/e_seed 新数据);journal 实证 h1=already/h2=rewritten(改写器 old<new 嵌套裁决正确);D16 拦截实证: 两成员 delete_files=true 均 error「1 个种子位于迁移收尾窗口的活动别名之下(X:\p1_e3\src): 带文件删除会经别名删到已迁往新位置的数据 —— …」,种子仍在、文件无损;删链后删除可行**不可达**(收尾被自锁挡死),qB 侧 teardown 删除正常(收尾清理不受限)。

实验机制附注: ①执行入口要求 `config.bt_backup` 表(rm04 模板没有,实验配置已补 56590 便携路径);②daemon 下线窗判定是**全机** qbittorrent.exe 名册口径,窗口期主实例也要 down;③派生配置被产品自动 v5→v6 迁移(带备份,无害);④产品自选 mover(组内序不定),harness 已按回执 mover 适配;⑤X: = subst 虚拟盘符指向 .work/p1exp/xdrive(用户级命令,数据物理仍在 gitignored .work 内,收尾已 subst /d 拆除)。

现场已还原: 双实例 0 种子、save_path 还原、subst 已拆、BT_backup 孤儿 .bak 已清、实例按初见状态停机;`git status` 干净(HEAD a7590059 未动,零产品代码改动)。

### R2 · T1b P1b 真机实验 (2026-11-07)

环境: 同 T1a(环境2,测试实例 56589/56590,qB 5.2.3 Legacy 免鉴权,real.up/real.guard 过,真实种子 0);跨盘符拓扑 = 用户级 subst X: -> `tests-real/.work/p1b/xdrive`(收尾已拆,拆法=`cmd //c "subst X: /D"`,Git Bash 直跑 `subst /D` 会被 MSYS 路径转换吃掉);闸门旁路仍为测试侧启动器进程内 monkeypatch,盘上产品代码零改动。三约束全程未破(不删种/不 skip_check 重加/不读盘哈希校验),生产 26586/16585 与 `I:\PT\`、config.yml、auto-qb-data 零触碰。证据(含脚本 `p1b.py`/`e8_sim.py`)在 `tests-real/.work/p1b/evidence/`(gitignored)。实验全程产品发起 6 次、旁路 3 次,双实例按初见状态停机。

**⚠ 与 §03 推演的差异(置顶;属构造口径澄清,不推翻判据,无回炉)**: E6 计划写的「平铺组 + DIR_ALIAS junction」在产品里**不可达** —— `plan()` 的 exclusive 硬前提要求内容根段非空(`relocate_units.py:203` `exclusive = ... and rel != ""`),平铺组恒 FILE_LINKS,结构性没有 junction 成环面(E6b 实测:平铺反向预检放行 cls=ok + form=file_links)。产品可达的反向成环形态是「非平铺且 save_path 恰 = target/<内容根段名>」(E6a):src_cr = save_path/rel ⊆ dst_cr = target/rel 严格成立。R1 形式化(`_within(src_cr,dst_cr) || _within(dst_cr,src_cr)`)对平铺/非平铺两种形态都拦 —— 判据文本不受影响;E6 改按 E6a 实测坐标实证成环 + E6b 平铺放行取证;E8 矩阵保留「平铺 DIR_ALIAS 反向拦」为 defensive 用例(A6x/B2/B9,标注产品不可达)。

逐 E 结果:
- **E4 PASS**: 单成员组(单枚 3 文件 e_seed 种子),target=src/待删。L1 现行预检 blocked+gate=nested,文案逐字留证(`e4/precheck_current.json`,「目标位于组成员声明源之下(X:\p1b_e4\src\待删 ⊆ X:\p1b_e4\src)…」)—— 单成员也被拦 = 拦空气实证。L2 旁路发起 started(form=direct,job jr-d0547f3ca7e3):qB 直接搬移落位 target、3 文件原名落位、job done(reason=direct)、alias_paths/alias_kind 空、无 journal 无 spec(无收尾窗口,`e4/job_final.json`)、旧内容根搬空、目标侧零链接、零 recheck(状态时间线 0 异态拍)/零拒载。→ **R1 不该拦 DIRECT 实证成立**;拟议判据下该形态 = R4 confirm(E8 B6)。
- **E5 PASS**: 8 文件两成员组(同内容异 piece_len),target=旧内容根内 待删2,旁路发起。qB 搬移成功(mover 落位 target,8/8 文件进内容根子目录)→ 建链 RuntimeError「内容根目录非空(X:\p1b_e5\src\e_seed), 目录别名建不出来」(`e5/runtime_error_loglines.json` 2 行,relocate_exec.py:281 形态)→ job armed/alias_partial/attempts=2/last_error 同文案/alias_paths 空(`e5/job_stuck.json`;重建退避 300s,观测窗 100s 不收敛,不等 rebuild_exhausted);旧内容根被待删2 占用(非空),非 mover 声明路径数据缺失(数据随 mover 进子目录)。全程零 recheck。→ **R1 正向必要性实证**:搬后卡死、别名建不出、无法收敛。mover=产品自选 h2(组内序不定,T1a 已知,E5 首跑因盯死 h1 空等 90s 踩中一次,已按回执适配)。
- **E6 PASS(E6a 非平铺反向成环 + E6b 平铺放行)**: E6b:单文件两成员平铺组,现行预检(无旁路)cls=ok/gates=[]/form=file_links(`e6/e6b_precheck_flat.json`)——闸门对祖先目标盲 + 平铺无 junction 面。E6a:save_path=X:\p1b_e6\e_seed(内容根 e_seed),target=X:\p1b_e6(祖先),**现行闸门零旁路**预检 cls=confirm/form=dir_alias/无 nested 拦截(`e6/e6a_precheck.json` —— `_within` 只判 target ⊆ 锚,对 target ⊇ 源无任何分支可命中)→ 发起 started → qB 搬移成功(rename 进非空父目录失败自动落逐文件拷贝,数据并入 X:\p1b_e6\e_seed)→ 产品自建 junction `X:\p1b_e6\e_seed\e_seed` -> `X:\p1b_e6\e_seed`(旧内容根位 -> 自身祖先;realpath/ino+dev/父位三口径一致,`e6/e6a_cycle_topology.json`)→ 祖先单层列表可见 junction + 8 个新数据文件 → 有界 DFS(深度+步数双上限,绝不递归列举)深度 1 即命中真实目录重复访问 = **成环实证**(`e6a_cycle_topology.json` bounded_walk.cycle)→ job armed(alias=[junction]),经 junction 穿透读文件 OK,成员 progress 1.0,零异态。拆现场:先停产品再 os.rmdir junction(不跟随),后清数据。→ **R1 对称拦(反向)必要性实证成立**。
- **E7 PASS**: A 组(3 文件 FILE_LINKS)独立目标发起至 armed(3 硬链别名);B 组(不同内容根,同 save_path 根)落点 = srcA\停车(A 声明源之下、A 内容根之外)。L1(无旁路):B 预检被嵌套闸门 job.src 分支拦,文案逐字留证(`e7/B_precheck_blocked.json`,「目标位于在途迁移 job jr-6aa9d7dc9c1b 的声明源之下(X:\p1b_e7\srcA\停车 ⊆ X:\p1b_e7\srcA):该目录现在是活动别名的作用域…」—— FILE_LINKS 形态下「活动别名作用域」的说法与实际不符,即误拦本体)。L2(旁路):R2 替身(进程内直接用产品纯函数 `ru._within`)按 job.scope 锚重算:`_within(job.src,target)=True` -> `_within(job.scope,target)=False`,R3=False => 放行(`e7/r2_sim.json`);B 发起 started,落位 srcA\停车\b_seed 原名;A 别名 3 硬链在位可读、A job 相位/alias_paths 不变、A 内容根 vs B 落点互不嵌套(B ⊄ A.scope)—— 物理互不干扰实证。记账面观察(纯函数):B 停进 A.src 后 `chain_gate_hits(A.src)` 把 B 的 save_path 计入 A 的删链门依赖 —— R2 放行与 T1a 回炉项(删链门 `_chain_gate_deps` 需重锚)叠加,给 P2 补了一个新实证来源(组外停车也会顶进依赖集)。→ **R2 收窄必要性+充分性实证成立**。
- **E8 PASS(29/29)**: 独立模拟脚本 `tests-real/.work/p1b/e8_sim.py` 按 §03 R1-R5 语义实现拟议判据,`_within/_norm/_join/layout_of/content_root_of/FORM_*/TERMINAL_PHASES` 直接 import 产品 relocate_units(不抄口径);矩阵 29 例 = E2.3 原 8 例按内容根锚重释(A1-A9:子目录/深层/尾斜杠源/兄弟待删2/事故同款 A4x confirm 放行/前缀同串/父目录/大小写平台条件/job src/dst 分支+终态)+ 新形态(B1-B9:DIR_ALIAS 互嵌双向拦以 E5/E6a 真机坐标闭环、dst-above-src 非平铺放行(D6 修正点)、FILE_LINKS 兄弟与深层嵌套放行(R4/R5)、DIRECT 嵌套放行(E4 坐标)、相等=幂等不进判据、平铺正反向)+ R2/R3 矩阵(C1-C6,E7 坐标:scope 收窄翻转/严格嵌套拦/含等于拦/恰等 dst 豁免/终态豁免)。全部与 §03 推演一致,**无回炉项**。过程中替身笔误 2 处(layout_of 实参传了 (名,大小) 元组、R4/R5 实参序反)当场修正,属脚本 bug 非判据问题;A1f(平铺 FILE_LINKS)R4+R5 同触发是 §03 字面语义的正确结果(平铺时链接叶就在声明源=src_cr 内)。现行闸门对照(A4x/B1/C1 现行均 blocked)逐字留证于 `evidence/e8/e8_matrix.json`。

实验机制附注: ①qB 搬移进「已存在非空目录」时走 rename 失败→逐文件拷贝合并路径(E6a 实测),这是反向成环 junction 得以建成的前提,生产同形态(目标=声明源祖先)同理;②E5/E6 的 armed 卡死现场受重建退避 300s 约束,观测窗内只见 attempts 1->2,不等 rebuild_exhausted(全耗尽需 ~15min,不必要);③本机所有实验无 qB 下线窗需求(E4-E7 均止步于 armed/direct,E5 卡死),real.down 仅收尾用。

现场已还原: 双实例 0 种子、save_path 还原(`R:\Download\PTing`)、subst 已拆、.work/rm04 用例目录已清、`.work/p1b` 只留脚本+证据(gitignored)、实例按初见状态停机;`git status` 干净(HEAD 1e5bd695 未动,零产品代码改动)。

### R4 · T4a P4 真机复验 (2026-11-08)

环境: 同 P1(环境2, 56589/56590 qB 5.2.3 Legacy 免鉴权, real.up/down 起停);subst X: -> `tests-real/.work/p4/xdrive`(收尾已拆)。**零旁路零 monkeypatch** —— 全部场景走产品真实路径(P2 fd53c8fe 判据+删链门重锚、P3 c7c839da UI 披露之后;会话开工 HEAD c7c839da,全程未动)。证据(驱动脚本 `p4.py`/`u_check.mjs` + JSON/截图)在 `tests-real/.work/p4/evidence/`(gitignored;勿跑 real.seed.clean,会整扫清掉)。三约束全程未破(不删种/不 skip_check 重加/不读盘哈希校验,teardown 清理不受限);生产 26586/16585 与 `I:\PT\`、`config.yml`、`auto-qb-data/` 零触碰。**8/8 场景 PASS,无「该拦不拦/该放不放/删链不收敛/UI 不显示」项,无置顶缺陷。**

逐场景结果(判据对照 = 计划 §03 R1-R7):
- **R-A(=E2) PASS**: 2 成员 3 文件组,target=源内兄弟目录 src\待删。预检放行 cls=confirm/gates=[nested]/member_count=2,R4 confirm 文案逐字(「新落点仍在旧声明源树下(X:\p4_ra\src\待删 ⊆ X:\p4_ra\src)…(D19)…」),R5 note 未触发(target 不在内容根内,符合判据)。两步发起实证:confirm=false → confirm 回执零副作用(jobs_on_disk=0);confirm=true → started。全链路:setLocation→3 硬链别名→武装穿透(经原路径读同 size)→下线窗改写(52s,journal rewritten)→重启双成员原生落位 target 账面 1.00→**job done(reason=finalized, alias_paths=[])——R7 修后删链门收敛、别名清零**,旧根 0 残留链接,零 recheck/零拒载(「无法解析恢复数据」0 条)/零异态。T1a 的删链自锁(旧码 240s 恒卡 rewritten/chain_deps)消除。
- **R-B(=E3) PASS**: target ⊆ 旧内容根(src\e_seed\待删2)。预检 R4 confirm + R5 note **均出现**(「新落点在旧内容根内…链接叶与新数据混居, 带文件删除会被 D16 拦(收尾完成后消失)」),放行。全链路:混居现场实证(旧内容根内 3 硬链叶 + 待删2 新数据并存,`rb/disk_src_armed.json`);别名期 D16 摩擦实证(两成员 delete_files=true 均 error「1 个种子位于迁移收尾窗口的活动别名之下(X:\p4_rb\src)…」,种子仍在、dst/链接文件无损)——R5 note 语义兑现;下线窗改写 52s→重启→**job done/finalized + alias_paths=[] + 旧叶全删,删链后旧内容根只剩待删2 新数据**。
- **R-C(=E4) PASS**: 单成员 3 文件,target=src\待删。预检 cls=confirm/form=direct + R4 confirm(旧码 blocked 拦空气 → 现按 R4 披露放行)。confirm=true → qB 直接搬移落位原名,job done(reason=direct),alias_paths/alias_kind 空、无 journal(无收尾窗),零异态。
- **R-D(=E7) PASS**: A 组(2 成员 a_seed)独立目标发起至 armed(3 硬链,scope=srcA\a_seed);B 组(b_seed)落点 srcA\停车(A 声明源之下、A 内容根之外)→ **预检 cls=ok/gates=[] 放行(R2 收窄生效;P1 旧码同坐标 nested blocked)**,cls=ok 走 confirm=false 直发,B 实迁落位 srcA\停车\b_seed 原名;A 别名在位可读、A job 相位/alias_paths 不变。R7 记账对照(纯函数,`rd/out.json`):`chain_gate_hits(旧锚 job.src)` 命中 [srcA, srcA\停车] / `新锚 job.scope` 命中 []。A 全链路(下线窗 58s 改写→重启→核验)→ **A job done/finalized + 别名清零 + 旧叶全删 —— R7 对组外停车来源的豁免在真机收尾链实证**(旧锚下 B 的停车 save_path 会把 A 永久顶在删链门);B 组数据/落位全程无损(B 的非 mover 成员由 B 自己的 job 在同一窗口完成改写,收敛 srcA\停车)。
- **B-A(=E5) PASS**: 8 文件两成员组(DIR_ALIAS 形态),target ⊆ 旧内容根 → 预检 **blocked**,R1 正向文案逐字(「目标与旧内容根互嵌(正向: 新内容根 X:/p4_ba/src/e_seed/待删2/e_seed 落于旧内容根 …之下): 目录别名落点会被搬入的新数据占住, 搬移后建链必失败…」);零副作用(无 job/save_path 不变/无 junction/状态不变)——**搬后卡死形态不再可达(拦在预检,无需现场拆除)**。
- **B-B(=E6a) PASS**: 非平铺组 save_path 恰 = target/内容根段名(src_cr=X:\p4_bb\e_seed\e_seed ⊊ dst_cr=X:\p4_bb\e_seed)→ 预检 **blocked**(P1 同坐标旧码 confirm 放行 → 现拦,即 P1 时的零防御缺口已闭合),R1 反向文案逐字(「…目录别名会指向自身祖先, 目录列举成环…」);零副作用。
- **B-C PASS**: 待删2(已存在兄弟目录)/待删2x(前缀同串)/待删除(前缀同串)/尾斜杠 四变体 → 全部 cls=confirm(R4)不 blocked,成分级(_within 以分隔符为界)不误伤。
- **U PASS(浏览器真机)**: `/api/webui/flags` relocate_enabled=true(第 4 键在位);`/shared/tpl/move-dialog.html` 服务端下发含 R6a 提示行 + `v-if="flags.relocate_enabled"` 门控;Playwright(chromium headless)真机走通 atlas UI:行右键→「设定位置…」→移动对话框渲染两行提示(第二行「整组迁移已启用: 移动将以内容组为单位, 同组其它成员一并迁移。」= R6a)→填路径提交→确认框「需确认: 迁移方式」行表逐行留证:迁移形态=逐文件链接/**来源=X:\p4_u\src(整组 2 个成员)**(R6b 后缀)/目标/未来种子/原因=R4 文案全文/提示 → 点「取消」收场零副作用(confirm=true 未发出)。截图 `u/u_move_dialog.png`/`u/u_confirm_modal.png`。

实验机制附注: ①rm04 `fake_multi` 契约:files 的 rel 首段必须 == tname(首段会被 info.files 剥掉,数据按 savepath/rel 落盘而 qB 按 savepath/<tname>/ 找内容——不一致时私有 tracker 无 peers 恒 stalledDL,wait_complete 必超时;R-D 前两跑因此失败,已加 `build_group` 断言钉住)。②B-A 首跑把 target(内容根内 待删2)**预创建** → 内容根含杂项 → exclusive=False → form=file_links(R4 confirm 放行而非 R1 拦)——E5 坐标的 待删2 是搬移时由 mover 落位才出现的,重跑不预创建即 dir_alias 形态;非判据问题。③R-D 观察一处 qB 侧现象(非产品缺陷):setLocation 的成员 save_path 若在全局下线前 ~1s 内才变更,qB 重启后该成员 save_path 回落旧值(qB fastresume 持久化竞态);给 8s 落盘裕量后未再现;产品 journal 只含本组成员(`rd/journal.json` 只有 A 的两个 hash),非成员 fastresume 产品不碰。④UI 默认视图是 groups,.torrent-row 只在种子视图渲染 —— Playwright 需先点导航 `data-view="torrents"`。

现场已还原: 双实例 0 种子、save_path 还原(`R:\Download\PTing`)、subst 已拆、X: 与 .work/rm04 用例子树定点清、`.work/p4` 只留脚本+证据(gitignored)、实例按初见状态停机(会话开工时双实例在线,收尾按 R1/R2 同款口径 real.down;如需再起 `commands run real.up`);`git status` 除本档案 md 外干净(HEAD c7c839da 未动,零产品代码改动)。

### R5 · T4b 全量基线 (2026-11-08)

- 全量基线切片: `memory-bank/testing/baselines/26-11-08-0132-backend-relocate-nested-gate-fix.md`(`commands run test.full` 后台实测, pytest 140.44s; 汇总行 `1 failed, 5651 passed, 2 skipped, 1 warning`; 覆盖率 TOTAL 25530 stmts / 6 miss / 8816 branch / 28 partial = 99%, 门槛 99.5 达标(总覆盖 99.90%); 缺口单位 34, 对上片 32 净额 +2 远低于点名线; 副作用台账 9565 条越界 0)。数字均从实测誊写入切片, 本档案只引述不另抄。
- 失败明细: 唯一 failed = `tests/test_memory_bank_docs.py::test_wording_guard_is_green_on_current_kb`(存量措辞守卫), 违规点 = 本档案 18/25 行历史表述(`等…指令`/`待提交` 两类时点相对措辞), 与任务提示给的已知基线(test.quick 口径)逐位一致 —— **失败集未超出存量 1 条, 无新增回归**; 按本轮收尾纪律不修, T6 收尾回写改写该措辞后自然消除。
- 差值说明: 对上一条切片(26-11-07-1248)passed 净增 2 = P2/P3 两批新增用例(relocate 判据/删链门重锚 + webui 披露)随全量通过; 2 skipped 与上片同 2-skip 权限面。全量口径与任务提示的 test.quick 口径同数, 无口径差。
