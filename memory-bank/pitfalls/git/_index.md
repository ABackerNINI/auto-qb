# git — Git / 提交推送纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 本工具 shell 里 git 的硬约束与事故判据 —— ref 会被静默丢弃, 推送结果只看 `ls-remote`; 旧 rebase/merge/stash 毁库禁令已随拦截层修复解除 (2026-09-25), 事故档案保留。
> **触发**: git, 提交, 推送, rebase, merge, 落后主线, ref, 改名, 行尾, 提交信息

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [editing-traps.md](editing-traps.md) | 工具 shell 里改文件的多类静默事故 —— 编辑器挂死、行尾被归一、编码写坏、多行替换错位、同文件多次 Edit、edit 工具 CRLF 匹配、PowerShell 引号剥除 (旧"stash 毁库"条已随拦截层修复解除)。 | git stash, GIT_EDITOR, 改文件, 行尾, CRLF, LF, 编码, 乱码, 多行替换, Edit, junction, oldText, python -c, 引号, 控制字符, 转义被吃, Windows 路径, 反斜杠 |
| [history-integration.md](history-integration.md) | 历史整合(merge/rebase/stash)曾因删除拦截层批量删 `.git/objects` 而被禁 —— 该问题 2026-09-25 已修复, **禁令解除**; 本文件保留作事故档案与恢复手册, 高风险历史整合前仍建议 `cp -a .git <备份>`。 | 落后主线要同步, 想跑 git rebase, git merge, 合并, 变基, .git 损坏, 事故恢复 |
| [message.md](message.md) | 提交信息里的反引号会被 bash 当命令替换; `commit -F -` 的 heredoc 会让 push 静默不执行; 规模数字要当场实测。 | 写提交信息, git commit -m, git commit -F, 提交消息, 规模数字 |
| [package-move-imports.md](package-move-imports.md) | 移动/归拢包目录时 import 引用清点的漏网形态与守阵同步清单 —— 方案 C 实施实录 (W4a 五轮、W4b 三轮)。 | 目录迁移, 包移动, git mv, import 更新, 引用清点, 守阵路径, mock 字符串, logger 名 |
| [push.md](push.md) | 推送前必须先设 `TMPDIR`(否则闸门必红); 判"推没推上"的唯一依据是 `ls-remote`, 不是 push 的输出。 | push, 推送, 提交闸门, 推没推上, Gitee, GitHub, 镜像, CI action |
| [refs.md](refs.md) | 提交后必查 ref 三处(只看 commit 输出会被骗); 本 shell 里 `refs/remotes/*` 的写入会被静默丢弃。 | 提交后核对, ref, packed-refs, 分支被回退, staged 暴增, 上游未设置, 领先落后算不出 |
| [sync-pull.md](sync-pull.md) | `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒; 双 UI 镜像线何时该重放。 | git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, keep 分支, 镜像线 |
