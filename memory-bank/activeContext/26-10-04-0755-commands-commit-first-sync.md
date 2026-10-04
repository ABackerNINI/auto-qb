# ship.commit 提交先行: 同步/推送内联成一步

> 摘要: 用户拍板把「先 sync 再 ship.commit」合成一条 —— agent 直接 `ship.commit`, 脚本负责同步 + 推送, 同步(冲突/断网)失败才由 agent 介入。编排翻转: 闸门 → 暂存 → 提交 → ref 核对#1 → 消费消息 → 内部同步(树净 rebase 恒可自动) → [rebase 真合入远端 → 闸门复跑 + amend] → 内联推送; 同步失败改判「推送未完成」(退出码 0, 别重新提交)。回写件合流交脚本(取代 2026-09-26「先合并远端再收尾」); 独立 sync 树脏失败行改带两条出路(stash 配方 / 提交先行)。实施全绿: test.pkg 100 passed, test.full 2460+4 / 98.72%(基线 [26-10-04-0752](../testing/baselines/26-10-04-0752-commands-commit-first-sync.md))。
> 最后活动: 2026-10-04 08:05

## 已收口

- **已提交推送 `fa918a67`**(2026-10-04, 新流程首次真机验证): 提交落稳 `db90a7b7` 后同步撞「fetch 未落稳」暂态 → 按失败行补推 `ship.push` —— 其内部同步把提交 rebase 到远端新 tip(并行 clone 的 `6cf56550`)之上再推, 线性历史, 成功行报终值 `fa918a67`。设计的三条失败面(暂态重试 / rebase / 冲突停)两条已真机兑现。
- 档案 [tasks/26-10-04-commands-commit-first-sync](../tasks/26-10-04-commands-commit-first-sync.md)(Done)。

## 后续注意

- 本切片自身的收口编辑随下一笔提交入库(已推送不能 amend, 不为它单独跑流程)。
- 行为变化提示给并行 clone: 旧 clone 上的「先 sync 再 commit」习惯已无必要; 独立 sync 只剩会话开工用途。
