# 未推送分支的 ship 死锁: sync 先于 push, 而它只认同名远端分支

> 摘要: 本工具 shell 里 `refs/remotes/*` 写入被**静默丢弃** (见 refs.md), ship 脚本一律以 `ls-remote` 现查远端真值为判据 —— 一条**从未推送过**的特性分支, `run_sync` 拿不到远端同名分支直接失败「拿不到远端 <remote>/<branch> (离线?)」; 而 `run_push` 的**第一件事**就是 `run_sync` ⇒ 未推送分支永远推不上去 (鸡生蛋死锁)。网络是通的 (curl / ls-remote 其它分支都正常), 失败行却写着「离线?」—— 别被误导去查网络。
> 触发: 未推送分支, 新特性分支, 首次推送, push 失败, 拿不到远端, ls-remote, 离线, 死锁, chicken-and-egg, sync 先于 push, run_sync, run_push, my-commit-flow.push, 开工同步失败

**Refs:** memory-bank/pitfalls/git/refs.md

### 未推送分支走 ship 脚本 = 永远失败

- **触发**: 新建 clone 或新建特性分支, 尚未在远端建过对应分支时, 跑 `commands run my-commit-flow.push`(或 `my-commit-flow.commit` 内置的推送段) —— 表现是**先失败在 sync**, 根本走不到 push。
- **判别**: 失败行 = `拿不到远端 <remote>/<当前分支> (离线?) —— 联网后重跑`。三个信号合起来才定性: ①网络通 (别的分支 ls-remote 有值) ②当前分支在 `git ls-remote` 里**没有** `refs/heads/<branch>` ③本地 `refs/remotes/` 快照**不可信** (本环境写入被静默丢弃, 见 refs.md)。三者齐 = 结构性死锁, 不是离线。
- **处置**: 别在死锁里反复重跑 (每次都是同样的失败)。让**用户在自己终端** `git push -u origin <branch>` 建立远端对应, 之后 ship 脚本才能正常工作; 涉及历史整合 (rebase/合并既有提交) 的同步同理优先用户终端 (见 history-integration.md)。死锁期间本地工作不受影响, 提交可以先做 (commit 的推送段失败会如实报「已提交未推送」)。
