# git — Git / 提交推送纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 本工具 shell 里 git 的硬约束与事故判据 —— ref 会被静默丢弃, 同步/推送核验已内联进 my-commit-flow 脚本(判据 ls-remote 现查真值); 旧 rebase/merge/stash 毁库禁令已随拦截层修复解除 (2026-09-25), 事故档案保留。
> **触发**: git, 提交, 推送, rebase, merge, 落后主线, ref, 改名, 行尾, 提交信息

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [editing-traps.md](editing-traps.md) | 工具 shell 里改文件的多类静默事故 —— 编辑器挂死、行尾被归一(`sed -i` 把 LF 写成 CRLF, git 侧看不见、cap 侧多算)、文本模式写回双重换行(`\r\r\n`)、编码写坏、多行替换错位、同文件多次 Edit、edit 工具 CRLF 匹配、PowerShell 引号剥除 (旧"stash 毁库"条已随拦截层修复解除)。2026-10-02 起仓库 .gitattributes 统一 LF, 行尾类条目适用范围收窄(见首节)。 | git stash, GIT_EDITOR, 改文件, 行尾, CRLF, LF, 双重换行, write_text, 编码, 乱码, 多行替换, Edit, junction, oldText, python -c, 引号, 控制字符, 转义被吃, Windows 路径, 反斜杠, 幽灵 M, stat 缓存, sed -i, 机械替换, 凭空多出的债务 |
| [history-integration.md](history-integration.md) | 历史整合(merge/rebase/stash)曾因删除拦截层批量删 `.git/objects` 而被禁 —— 该问题 2026-09-25 已修复, **禁令解除**; 本文件保留作事故档案与恢复手册, 高风险历史整合前仍建议 `cp -a .git <备份>`。**同步一律 `commands run my-commit-flow.sync`(自动快进 / 分叉自动 rebase 保线性), 本文的手工同步配方已退役删除。** | 落后主线要同步, 想跑 git rebase, git merge, 合并, 变基, .git 损坏, 事故恢复 |
| [message.md](message.md) | 提交信息里的反引号会被 bash 当命令替换; `commit -F -` 的 heredoc 会让 push 静默不执行; 规模数字要当场实测。 | 写提交信息, git commit -m, git commit -F, 提交消息, 规模数字 |
| [package-move-imports.md](package-move-imports.md) | 移动/归拢包目录时 import 引用清点的漏网形态与守阵同步清单 —— 方案 C 实施实录 (W4a 五轮、W4b 三轮)。 | 目录迁移, 包移动, git mv, import 更新, 引用清点, 守阵路径, mock 字符串, logger 名 |
| [push.md](push.md) | 提交闸门依赖 `TMPDIR` 约定(默认盘会假红); 判"推没推上"只认 `ls-remote` 对比本地 HEAD —— 该核对已内联进 ship 脚本(结果行「提交成功 <hash>」), 手动 ls-remote 仅在报「无法核实」时; Gitee 间歇性卡住 / `Recv failure` 已由 git 层「单次超时 20s + 有界重试 3 次」兜住(2026-10-06, 不再要手工补推); 镜像只给超时且允许滞后, 成败都不提(26-09-28 定调)。 | push, 推送, 提交闸门, 推没推上, Gitee, GitHub, 镜像, 卡住, 重试, 超时, 补推, CI action |
| [refs.md](refs.md) | ref 三处核对已内联进 `ship.commit`(静默通过; 只看 commit 输出会被骗, 由脚本兜住); 本 shell 里 `refs/remotes/*` 的写入会被静默丢弃 —— sync/push 脚本判据因此只认 ls-remote 现查真值。 | 提交后核对, ref, packed-refs, 分支被回退, staged 暴增, 上游未设置, 领先落后算不出 |
| [self-rewrite-config.md](self-rewrite-config.md) | 本包目录就在**仓库里**, 而流水线自己会把远端新版 `.my-commit-flow.toml` rebase 进工作区(内部同步 / 生成物自动化解的第一步都是"把树推到上游 tip")—— 而进程手里那份 `cfg` 还是**启动时**读的。两处受害: ①`ship.commit` 的闸门**复跑**照跑, 只是规则不对(旧闸门集 / 旧 `each_limit` / 旧红线), 输出与"全过"一字不差; ②`sync.py` 的生成物自动化解用旧白名单 / 旧重跑命令**丢本地内容**(旧白名单放宽 = 静默丢内容, 重跑命令换了 = 重跑的是旧生成器)。都比同族的模块缓存问题隐蔽得多(那族会 ImportError 报出来)。旧修法 = 树被改写后按**磁盘现版本**重取配置(`_pipeline.reload_config`, 含 STOP 级复检): commit 侧复跑前先 `refresh_package_modules()` 再重取, 变了才登记步骤行; sync 侧在快进后 / rebase 每轮开头与收尾各重取一次, 取不到或新配置关掉自动化解就**放弃自动化解并回滚**。⚠ **该修法已于 2026-10-07 被「快照自举」取代 —— 见文末「收口」节**。 | ship.commit, sync, 复跑, 旧配置, 配置过期, 启动时快照, 配置迁移窗口, .my-commit-flow.toml, reload_config, 闸门规则不对, 白名单, 生成物自动化解, 静默丢内容, 内部同步之后, rebase 之后, 闸门照跑但没生效 |
| [self-rewrite-imports.md](self-rewrite-imports.md) | 本包脚本住在**仓库里**, 而 `ship.commit` 的内部同步会把远端新版包脚本 rebase 进工作区 —— Python 的模块缓存让延迟 import 的**新**脚本撞上进程启动时的**旧**依赖模块, 症状是 `ImportError: cannot import name …`, 而提交其实已经落稳; 旧修法 = 延迟 import 前按磁盘现版本热刷新本包模块(内容摘要门控 + `importlib.reload` 保身份)。⚠ **该修法已于 2026-10-07 被「快照自举」取代 —— 见文末「收口」节**。 | ImportError, cannot import name, ship.commit 退出码 1, 提交成功却报错, 延迟 import, 延后 import, 内部同步, rebase 之后崩, sys.modules, 模块缓存, importlib.reload, 热刷新, 包脚本自我改写, refresh_package_modules |
| [ship-commit-staged-delete.md](ship-commit-staged-delete.md) | ①commit.py 按纪律逐路径 `git add -- <path>`(禁 -A), 对**已暂存的删除**(`D `)必然 pathspec 落空 —— 删除一旦进暂存区, 该路径在工作区与索引里都不复存在, `git add` 无处匹配; ②**零参数 = 全量暂存**, 未被 `.gitignore` 覆盖的会话目录(`.workbuddy/memory/`)会被一并入库, 事后补忽略还会撞 ① 的变体(`git add` 忽略路径直接失败)。 | ship.commit, git add 失败, pathspec did not match, addIgnoredFile, 删除文件, 提交失败, 蒸馏切片, 全量提交, .gitignore, 会话记忆入库, .workbuddy |
| [subagent-mixed-workspace.md](subagent-mixed-workspace.md) | 子智能体(配额耗尽等)半途夭折不会回滚它已落盘的改动 —— 计划内改动与计划外动作在同一批文件里混杂交织, 直接续派会在脏底子上叠新错。 | 子智能体夭折, 配额耗尽, 混合工作区, 计划外改动, git status 白名单, 续派 |
| [sync-pull.md](sync-pull.md) | `status -sb` 的 ahead/behind 是快照; 未提交改动 + 行尾会让快进合并被拒(树脏场景两条出路: stash 配方或提交先行 —— 2026-10-04 起 ship.commit 提交先行, 旧「先提交是死锁」作废); 双 UI 镜像线何时该重放。 | git fetch, git pull, 同步上游, 落后, 行尾, 快进合并被拒, 树脏, 重叠, stash, 死锁, keep 分支, 镜像线 |
