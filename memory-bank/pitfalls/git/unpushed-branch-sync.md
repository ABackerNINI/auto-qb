# 未推送分支的 ship 死锁: sync 先于 push, 而它只认同名远端分支

> 摘要: 本工具 shell 里 `refs/remotes/*` 写入被**静默丢弃** (见 refs.md), ship 脚本一律以 `ls-remote` 现查远端真值为判据 —— 一条**从未推送过**的特性分支, `run_sync` 拿不到远端同名分支就失败; 而 `run_push` 的**第一件事**就是 `run_sync` ⇒ 未推送分支永远推不上去 (鸡生蛋死锁)。**2026-11-23 起失败行已如实区分**: `ls-remote` rc=0 但无 `refs/heads/<branch>` → 「远端 <remote>/<branch> 不存在(分支未推送, 非离线)」(只报事实, 不塞 push -u 指引 —— 本地分支大多不需要推送, 平时走 develop 同步); 只有 rc≠0 (网络/远端不可达) 才报「拿不到远端 … (离线?) —— 联网后重跑」。旧版本把两者混写, 让人去查网络、反复重跑而恒败 —— 下面「旧文案」段是读历史档案时的对照, 不是现行口径。
> 触发: 未推送分支, 新特性分支, 首次推送, push 失败, 拿不到远端, ls-remote, 离线, 死锁, chicken-and-egg, sync 先于 push, run_sync, run_push, my-commit-flow.push, 开工同步失败

**Refs:** memory-bank/pitfalls/git/refs.md

### 未推送分支走 ship 脚本 = 永远失败

- **触发**: 新建 clone 或新建特性分支, 尚未在远端建过对应分支时, 跑 `commands run my-commit-flow.push`(或 `my-commit-flow.commit` 内置的推送段) —— 表现是**先失败在 sync**, 根本走不到 push。
- **判别**: 现行(2026-11-23 起)失败行 = `远端 <remote>/<当前分支> 不存在(分支未推送, 非离线)` —— 只报事实, **不含 push -u / 联网重跑等指引** (本地分支大多不需要推送, 平时走 develop 同步; 真要推这个分支时见下面「处置」)。判据是 `ls-remote` rc=0 但输出里没有 `refs/heads/<branch>` —— 远端可达、只是没这个分支。要看旁证: ①网络通 (别的分支 ls-remote 有值) ②当前分支在 `git ls-remote` 里**没有**同名 ref ③本地 `refs/remotes/` 快照**不可信** (本环境写入被静默丢弃, 见 refs.md)。
- **旧文案(读历史档案用)**: 修前失败行 = `拿不到远端 <remote>/<当前分支> (离线?) —— 联网后重跑`。旧档案里出现这一行, 且三个旁证信号齐 (网络通 / 远端无同名 ref / refs 快照不可信), 就仍按本坑定性 —— 结构性死锁, 不是离线, 别照字面去查网络或反复重跑。
- **处置**: 别在死锁里反复重跑 (每次都是同样的失败)。让**用户在自己终端** `git push -u origin <branch>` 建立远端对应, 之后 ship 脚本才能正常工作; 涉及历史整合 (rebase/合并既有提交) 的同步同理优先用户终端 (见 history-integration.md)。死锁期间本地工作不受影响, 提交可以先做 (commit 的推送段失败会如实报「已提交未推送」)。
- **修法落点**: `sync.py` 的 `remote_sha_probe()` 把 `ls-remote` 的 rc 带出来, `run_sync()` 按 rc 分为 `absent`(rc=0 无 ref) / `unreachable`(rc≠0) 两路报错; 只要 ref 真值的调用方 (commit.py 旁证 / push.py 推后核对) 仍走 `remote_sha()` 包装, 语义不变。守阵: `test_sync.py::test_remote_branch_absent_reports_unpushed` (真临时 bare 远端, 无同名分支) 与 `test_offline_reports_unreachable` (远端 URL 不存在) 两路分开钉住。
