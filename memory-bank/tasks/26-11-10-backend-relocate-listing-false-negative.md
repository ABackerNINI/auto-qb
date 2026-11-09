# 26-11-10-backend-relocate-listing-false-negative — relocate 运行时F自检假阴性修复: 链接对象判别 + 真机闭环 + 现场恢复 runbook

**Status:** Done
**Added:** 2026-11-10
**Updated:** 2026-11-10
**Summary:** 认领计划 26-11-10-0230 全链实施: 运行时F自检链接对象判别修复(qB 列目录不解析文件级 symlink 的假阴性转 skipped) + 真机闭环(测试 qB, 生产零触碰) + RM04-20 耐久用例 + 文档回写; 生产恢复 runbook 落计划 §4.1, 执行者=用户(D8)
**Topics:** backend-relocate-listing-false-negative
**Refs:** memory-bank/plans/26-11-10-0230-plan-relocate-listing-false-negative.html, memory-bank/pitfalls/backend/qb-dir-listing-no-symlink-resolve.md, memory-bank/testing/baselines/26-11-10-0351-relocate-listing-false-negative.md, memory-bank/testing/real-baselines/26-11-10-0435-real-relocate-rlfn-e2e.md

## 本篇只回答

计划 26-11-10-0230 怎么全链落地: qB 列目录不解析文件级 symlink 造成的运行时F自检假阴性怎么修、真机闭环怎么只在测试 qB 上收敛、生产恢复 runbook 在哪。

## 原始请求

1. 「先开本地分支提交计划，然后分步实施，完成后由你做一次简单验收」
2. 「派子智能体分阶段依次实施…每步完成后 ship.commit --no-push…完成后同步到本地 develop 后等待提交指令」 <!-- wording:allow --> (引述用户原话)
3. 「真机验证只在测试qb, 不能使用生产qb」
4. 「历史失败账一并纳入考虑」

## 思考过程与决策

计划 `memory-bank/plans/26-11-10-0230-plan-relocate-listing-false-negative.html`(权威, §06), 现场取证 + grilling 两轮拍板, 一行一条:

- **D1** 修法 = (a) 精确 skipped 判别(qB 条目 == 链接对象 lstat); 否决整体跳过(b)与换证据通道(c, qB 无单文件 stat 端点); 下游兜底 = 缺文件联动(整组暂停+MISSING)/errored
- **D2** 裂组接受为设计; hr-groups.md 回写口径; 不把 failed 终态纳入组键解析(失败账 dst 不可信, 强并组有误归风险)
- **D3** 历史账 jr-82f6dee7620d 账面不动(盘面已净); 终态留账清理出口与启动计数文案两件入池
- **D4** Blood 组恢复 = 修完重发同迁移(H:→I:); 全链已验证路径(幂等建链/收尾/删链门)
- **D5** 真机验证只做且只在测试 qB(硬约束, 用户明示); 生产 26586 零触碰
- **D6** 入池清单: ②③ 入池; 假阴性本体计划内直修; 裂组显示(设计内)不入池仅文档回写
- **D7** 验证深度 = (a) 完整闭环: 环境1 real.seed 跨盘拓扑(src R: → dst .work/D:), 自检 skipped → 武装 → 收尾 → done 收敛
- **D8** 生产恢复落 runbook(计划 §4.1), 用户执行; auto-qb 任务面对生产零动作
- **D9** issue 26-11-07-2336 保持 Open 不动; 计划引用 + 验证拓扑跨盘避开(拍板后 2336 已由并行会话修复翻 Done, 「不并入修」原判 moot, src=R: 拓扑口径保留)

实施期两项裁断(计划 §10 R1 前向指针已兑现; 细节单点 = RM04-20 docstring, `tests-real/rm04_relocate/test_rm04_relocate_window.py`):

- **A8** 断言二分: 收敛证据取「新 patch 行」或「在位健康 patched watcher」二选一。
- **A10** recheck 轮询窗: 尽力观测说明, 不设硬断言。

两次旁路授权的分层事实(wrapper docstring 两层表述, `tests-real/tools/daemon_window_wrapper.py`): 源会话 E2c(2026-11-10 同盘复验, `_spawn_daemon` 测试替换窄化名册, 两证保持产品原样, 坑档 `memory-bank/pitfalls/testing/relocate-window-machine-roster.md`) → 本任务 S4 沿用同配方再获授权; 产品代码零改动。

## 实现计划

波次表(S0-S6, 五笔提交 + 收尾批, hash 经 git log 实取核对):

| 波次 | 内容 | 提交 |
|---|---|---|
| 计划 | 计划入库(D1-D9) + wrapper docstring 初层授权 + 名册坑档指针行 | 652fd06b |
| S0 | 入池两件(② 终态留账无清理出口 feat / ③ 启动在途计数含终态文案 bug) | 7428b06d |
| S1-S3 | 三态用例红验 → relocate_proof.py 链接对象判别修复(relocate_exec.py 接线) → 全量绿 + 基线切片 | 46b39048 |
| S4 | RM04-20 真机闭环耐久用例(tests-real/rm04_relocate/) + real-baselines 切片 | 0b8c9f13 |
| S5 | 回写: hr-groups.md 裂组口径句 + 新坑档 qb-dir-listing-no-symlink-resolve + 索引 | 9102f75f |
| S6 | 收尾: 批次评审 + 接缝终审 + 本档案 + 计划翻 Done | 随本专题入库 |

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 计划 | 现场取证 + grilling 两轮拍板 + 计划入库 | Done(2026-11-10) |
| S0 | 入池两件 issue(Open, 不认领不排期) | Done(2026-11-10) |
| S1 | 单测红验: 三态用例(链接对象/目标/两不符), 现行代码用例①判 NEGATIVE | Done(2026-11-10) |
| S2 | 修复实施: relocate_proof.py 链接对象判别支, 红转绿零回归 | Done(2026-11-10) |
| S3 | 全量 test.full 全绿(见 kb.baseline 切片 26-11-10-0351) | Done(2026-11-10) |
| S4 | 真机闭环(环境1 测试 qB, 生产零触碰; 旁路照 E2c 配方) + real-baselines 切片 26-11-10-0435 | Done(2026-11-10) |
| S5 | 回写: hr-groups.md 口径句 + 新坑档 + kb.index | Done(2026-11-10) |
| S6 | 批次评审(P0/P1/P2/P3 分面/P4) + 接缝终审 + 立档翻状态 | Done(2026-11-10) |

## 进度日志

### R0 · 立档 (2026-11-10)

- 分工: 计划会话(现场取证/grilling/计划入库) + 本实施会话(五笔提交落地); 7 个实施子代理 + 5 个评审子代理。
- 2026-11-10 06:28 计划 26-11-10-0230 全链 S0-S6 收口: 假阴性修复落地(skipped 判别), 真机闭环 13 断言全 PASS / 0 FAIL(切片 26-11-10-0435), RM04-20 三遍 PASS(92.7s/91.8s/92.98s); 评审账 P0 3 轮(检 4/6 修 4)/P1 2 轮(检 2/2 修 2)/P2 1 轮(零发现)/P3 分面 2 派 2 轮(检 2/2 修 1 nit 1)/P4 1 轮(零发现)/终审 2 轮(检 2/2 修 2), 裁决后零 actionable; 全量绿见 kb.baseline(切片 26-11-10-0351); 范围外既有红(Linux CI webui r4 静态电池, 干净 HEAD 复现, 与本任务无关)未入池未修, 主会话已向用户报备; 本批(档案 + 计划翻 Done)随本专题入库

> rebase 换算注(2026-11-10): 合回 develop 时远端推进 20 笔(391f133a→4c57136c), 本分支 6 笔无冲突重放, 上表 hash 已按新序换算(原值 4194240b/d262e5ed/7f0e07c0/7f2fa302/061b87b3)。
