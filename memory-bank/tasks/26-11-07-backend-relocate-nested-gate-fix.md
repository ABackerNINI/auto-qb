# 26-11-07-backend-relocate-nested-gate-fix — relocate 嵌套闸门误拦修正实施

**Status:** In Progress
**Added:** 2026-11-07
**Updated:** 2026-11-07
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
| S1b | T1b 真机实验(E4-E7+E8 判据模拟) | Open |
| S2 | 回炉检查点(P1 结果对照判据) | Open |
| S3 | T2 纯函数+单测重锚 | Open |
| S4 | T3 UI 披露实现 | Open |
| S5 | T4a 真机全链路复验 | Open |
| S6 | T4b test.full+基线切片 | Open |
| S7 | T5 code-review | Open |
| S8 | T6 收尾回写 | Open |
| S9 | 合回本地 develop(不推) | Open |

## 进度日志

### R0 · 立档 (2026-11-07)

- 会话: 误拦报告 → 设计文档溯源 → grilling 六问 → 计划 1300 入库(37926370)→ 用户下达实施指令。
- Stage 0 完成: 分支 `relocate-nested-gate-fix` 自 develop(f7ac0e46),计划+索引已提交(37926370),本档案立档。

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
