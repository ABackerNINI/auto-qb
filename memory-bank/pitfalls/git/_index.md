# git — Git / 提交推送纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 本工具 shell 里 git 的硬约束与事故判据 —— ref 会被静默丢弃, 同步/推送核验已内联进 my-commit-flow 脚本(判据 ls-remote 现查真值); 旧 rebase/merge/stash 毁库禁令已随拦截层修复解除 (2026-09-25), 事故档案保留。
> **触发**: git, 提交, 推送, rebase, merge, 落后主线, ref, 改名, 行尾, 提交信息

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [editing-traps.md](editing-traps.md) | 工具 shell 里改文件的多类静默事故 —— 编辑器挂死、行尾被归一、文本模式写回双重换行(`\r\r\n`)、编码写坏、多行替换错位、同文件多次 Edit、edit 工具 CRLF 匹配、PowerShell 引号剥除 (旧"stash 毁库"条已随拦截层修复解除)。2026-10-02 起仓库 .gitattributes 统一 LF, 行尾类条目适用范围收窄(见首节)。 | git stash, GIT_EDITOR, 改文件, 行尾, CRLF, LF, 双重换行, write_text, 编码, 乱码, 多行替换, Edit, junction, oldText, python -c, 引号, 控制字符, 转义被吃, Windows 路径, 反斜杠 |
| [history-integration.md](history-integration.md) | 历史整合(merge/rebase/stash)曾因删除拦截层批量删 `.git/objects` 而被禁 —— 该问题 2026-09-25 已修复, **禁令解除**; 本文件保留作事故档案与恢复手册, 高风险历史整合前仍建议 `cp -a .git <备份>`。**同步一律 `commands run my-commit-flow.sync`(自动快进 / 分叉自动 rebase 保线性), 本文的手工同步配方已退役删除。** | 落后主线要同步, 想跑 git rebase, git merge, 合并, 变基, .git 损坏, 事故恢复 |
| [message.md](message.md) | 提交信息里的反引号会被 bash 当命令替换; `commit -F -` 的 heredoc 会让 push 静默不执行; 规模数字要当场实测。 | 写提交信息, git commit -m, git commit -F, 提交消息, 规模数字 |
| [package-move-imports.md](package-move-imports.md) | 移动/归拢包目录时 import 引用清点的漏网形态与守阵同步清单 —— 方案 C 实施实录 (W4a 五轮、W4b 三轮)。 | 目录迁移, 包移动, git mv, import 更新, 引用清点, 守阵路径, mock 字符串, logger 名 |
| [push.md](push.md) | 提交闸门依赖 `TMPDIR` 约定(默认盘会假红); 判"推没推上"只认 `ls-remote` 对比本地 HEAD —— 该核对已内联进 ship 脚本(成功一行「提交成功 <hash>」), 手动 ls-remote 仅在报「无法核实」时; 镜像允许滞后, 成败都不提(26-09-28 定调)。 | push, 推送, 提交闸门, 推没推上, Gitee, GitHub, 镜像, CI action |
| [refs.md](refs.md) | ref 三处核对已内联进 `ship.commit`(静默通过; 只看 commit 输出会被骗, 由脚本兜住); 本 shell 里 `refs/remotes/*` 的写入会被静默丢弃 —— sync/push 脚本判据因此只认 ls-remote 现查真值。 | 提交后核对, ref, packed-refs, 分支被回退, staged 暴增, 上游未设置, 领先落后算不出 |
| [ship-commit-staged-delete.md](ship-commit-staged-delete.md) | ①commit.py 按纪律逐路径 `git add -- <path>`(禁 -A), 对**已暂存的删除**(`D `)必然 pathspec 落空 —— 删除一旦进暂存区, 该路径在工作区与索引里都不复存在, `git add` 无处匹配; ②**零参数 = 全量暂存**, 未被 `.gitignore` 覆盖的会话目录(`.workbuddy/memory/`)会被一并入库, 事后补忽略还会撞 ① 的变体(`git add` 忽略路径直接失败)。 | ship.commit, git add 失败, pathspec did not match, addIgnoredFile, 删除文件, 提交失败, 蒸馏切片, 全量提交, .gitignore, 会话记忆入库, .workbuddy |
| [subagent-mixed-workspace.md](subagent-mixed-workspace.md) | 子智能体(配额耗尽等)半途夭折不会回滚它已落盘的改动 —— 计划内改动与计划外动作在同一批文件里混杂交织, 直接续派会在脏底子上叠新错。 | 子智能体夭折, 配额耗尽, 混合工作区, 计划外改动, git status 白名单, 续派 |
| [sync-pull.md](sync-pull.md) | `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒; 双 UI 镜像线何时该重放。 | git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, keep 分支, 镜像线 |
