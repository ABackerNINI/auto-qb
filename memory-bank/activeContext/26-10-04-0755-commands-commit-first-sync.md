# ship.commit 提交先行: 同步/推送内联成一步

> 摘要: 用户拍板把「先 sync 再 ship.commit」合成一条 —— agent 直接 `ship.commit`, 脚本负责同步 + 推送, 同步(冲突/断网)失败才由 agent 介入。编排翻转: 闸门 → 暂存 → 提交 → ref 核对#1 → 消费消息 → 内部同步(树净 rebase 恒可自动) → [rebase 真合入远端 → 闸门复跑 + amend] → 内联推送; 同步失败改判「推送未完成」(退出码 0, 别重新提交)。回写件合流交脚本(取代 2026-09-26「先合并远端再收尾」); 独立 sync 树脏失败行改带两条出路(stash 配方 / 提交先行)。实施全绿: test.pkg 100 passed, test.full 2460+4 / 98.72%(基线 [26-10-04-0752](../testing/baselines/26-10-04-0752-commands-commit-first-sync.md))。
> 最后活动: 2026-10-04 07:55

## 正在进行

- 实施与回写全部完成(档案 [tasks/26-10-04-commands-commit-first-sync](../tasks/26-10-04-commands-commit-first-sync.md), Done), **改动留在工作树等用户显式「提交」指令**。
- 涉及: `.commands/my-commit-flow/`(commit.py / sync.py / test_commit.py / pipeline.md / 包 README / 两个 config.toml) + AGENTS.md「提交/PR」+ memory-bank SKILL.md DoD 前言 + collaboration.md + pitfalls/git/sync-pull.md(死锁改判 + 机制修复归因)。

## 后续注意

- 下次真机「提交」就是新流程首验: 若远端前移, 预期 `ship.commit` 一次走完(提交 → rebase → 闸门复跑 → 推送);
  `_index` 撞车应出现「自动重跑生成物 N 处」标记, 手写件冲突才会停下要人。
- 行为变化提示给并行 clone: 旧 clone 上的「先 sync 再 commit」习惯已无必要; 独立 sync 只剩会话开工用途。
