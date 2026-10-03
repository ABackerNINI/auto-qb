# 26-10-04-commands-commit-first-sync — ship.commit 提交先行: 同步/推送内联成一步

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04 07:40
**Summary:** 用户拍板把「先 sync 再 ship.commit」两步合成一条: agent 直接 `ship.commit`, 脚本负责同步 + 推送, 同步(冲突/断网)失败才由 agent 介入。编排翻转为**提交先行**: 闸门 → 暂存 → 提交 → ref 核对#1 → 消费消息 → 内部同步(树净, 分叉 rebase 恒可自动) → [rebase 真合入远端 → 闸门复跑 + amend] → 内联推送。同步失败从「提交失败」改判「推送未完成」(退出码仍 0, 别重新提交); 旧「先提交是死锁」论断作废, 独立 sync 的树脏失败行改带两条出路(stash 配方 / 提交先行); 回写件合流交脚本 rebase + 生成物自动化解兜底(取代 2026-09-26「先合并远端再收尾」的手工纪律)。test.pkg 100 passed(+6 真仓用例); test.full 2442 passed + 3 skipped / 99%(基线 [26-10-04-0752](../testing/baselines/26-10-04-0752-commands-commit-first-sync.md))。
**Topics:** commands-commit-first-sync

## 原始请求

用户问: 「目前的 my-commit-flow 提交流程是先同步远端然后提交, 感觉没必要分为两个步骤, 能否合为一个步骤, agent 直接推送, 脚本负责同步远端 + push, 如果同步(网络或冲突等)失败才由 agent 介入?」—— 评估轮给出结论(机制大半已存在, 但须翻转 commit 内部顺序, 否则树脏 rebase 死锁 / baseline 相撞回归), 用户答「开工」授权实施。

## 思考过程与决策

- **为什么不能只删 AGENTS.md 第①步**: ship.commit 内部本就带 run_sync, 但它跑在**提交之前、树还脏**时 —— 纯落后+重叠被拒、分叉+树脏硬失败, 只能走 stash 舞蹈(pitfalls/git/sync-pull.md 双向死锁家族复发 12 次)。翻转成提交先行后树必然干净, rebase 恒可自动, stash 舞蹈从提交路径退役。
- **闸门复跑保住「检查项一个不删」**: 旧序闸门跑在合并后的树上; 翻转后首跑在本地树上 —— rebase 真合入远端提交(HEAD 改写为判据)就按同一份清单**复跑一轮**, fmt 类闸门若又改文件则逐路径 add + `commit --amend --no-edit` 折进未推送 tip(与 sync.py 生成物收尾同款, amend 安全)。齐平(远端没动)不复跑, 代价只在分叉时多付。
- **同步失败改判「推送未完成」**: 提交已落稳(ref 核对#1 通过、消息已消费), 冲突/断网自动回滚后按 PARTIAL 语义停(退出码 0 + 补推指引), 防执行者重新提交。冲突行沿用 sync.py 的拼接缝(`同步失败需解决冲突 本地<x> 远端<y>`)。
- **ref 核对#1 必须赶在同步前**: 本环境 ref 写入会被静默丢弃(pitfalls/git/refs.md), 同步拿 HEAD 当真值 —— ref 丢了会把旧 tip 当本地提交推出去; 落稳即消费消息文件。amend 后再复核一次。
- **回写件合流交脚本**: 2026-09-26「先合并远端再收尾」手工纪律作废 —— 回写件直接写本地基线, `_index` 两边撞车由生成物自动化解兜底(rebase 冲突 ⊆ 白名单 → 取一侧 + 重跑生成器 + 自证; 重跑发生在含两边新切片的树上, 结果天然是并集); 手写件重叠才在 rebase 冲突里合流。
- **sync.py 文案随之改判**: 「先提交」解不开的死锁论断作废, 树脏失败行改带两条出路(①stash 配方 ②提交先行); commit.py 的 is_dirty_block 死锁护栏删除(提交路径树净, 该类失败不可达)。
- **--no-push 不同步**: 纯本地提交, 离线可用, 合流留给补推时的 ship.push。

## 实现计划

1. `commit.py` 编排翻转 + 新失败语义(PARTIAL 三类) + 闸门复跑/amend 分支。
2. `sync.py` 文案(死锁→两条出路) + docstring。
3. `test_commit.py` 守阵: 删 3 条死锁用例, 加 6 条(2 条替身语义 + 4 条真仓 rebase/冲突/复跑)。
4. 文档回写: AGENTS.md「提交/PR」、pipeline.md、两个 config.toml、包 README、memory-bank SKILL.md DoD 前言、conventions/collaboration.md、pitfalls/git/sync-pull.md。
5. 收尾: 立本档案 + activeContext 切片 + `kb.index` + `test.full` 新基线。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| commit.py 编排翻转(提交先行 + PARTIAL 三类 + 复跑/amend) | ✅ 完成 | 8 步编排, sha 以 rebase/竞态后的终值为准 |
| sync.py 死锁文案 → 两条出路 | ✅ 完成 | 失败行模板锚点全保留(树脏挡路 / stash 配方 / 需解决冲突) |
| test_commit.py 守阵 17 → 24 用例 | ✅ 完成 | 新增真仓用例: rebase 保线性 / 冲突回滚 / 复跑两轮 / 复跑红不推 / amend 折 tip |
| test.pkg 全绿 | ✅ 完成 | 100 passed (19.7s) |
| 文档回写(8 处) | ✅ 完成 | doc.caps AGENTS.md 7896/8000 |
| 收尾(档案 / 切片 / 索引 / test.full 基线) | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-04 07:1x** 开工同步成功 `9a3b74af`(远端有更新已快进)。评估轮已定设计(见思考过程), 本轮直接实施。
- **2026-10-04 07:2x** `commit.py` 重写(提交先行 + 复跑/amend + PARTIAL 语义); `sync.py` 文案改判(死锁作废 → 两条出路)。
- **2026-10-04 07:3x** `test_commit.py` 重写守阵: 删 test_sync_failure_blocks_commit / test_dirty_sync_failure_warns_deadlock / test_clean_sync_failure_no_deadlock_note, 新增 offline-partial / conflict-passthrough / 真仓 rebase / 真仓冲突 / 复跑两轮 / 复跑红 / amend 七组语义。`test.pkg` **100 passed**(19.7s)。
- **2026-10-04 07:4x** 文档回写八处: AGENTS.md「提交/PR」两段 / pipeline.md(编排节重写 + PARTIAL 三类 + 两条出路 + 脚本表) / 两个 config.toml / 包 README / memory-bank SKILL.md DoD 前言 / collaboration.md 单点定义 / sync-pull.md(摘要 + 死锁条改判 + 机制修复 12 次复发归因)。doc.caps 全 PASS 无债务。
