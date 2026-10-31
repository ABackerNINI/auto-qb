# 包配置被自己改写后的复跑

> 摘要: 本包目录就在**仓库里**, 而流水线自己会把远端新版 `.my-commit-flow.toml` rebase 进工作区(内部同步 / 生成物自动化解的第一步都是"把树推到上游 tip")—— 而进程手里那份 `cfg` 还是**启动时**读的。两处受害: ①`ship.commit` 的闸门**复跑**照跑, 只是规则不对(旧闸门集 / 旧 `each_limit` / 旧红线), 输出与"全过"一字不差; ②`sync.py` 的生成物自动化解用旧白名单 / 旧重跑命令**丢本地内容**(旧白名单放宽 = 静默丢内容, 重跑命令换了 = 重跑的是旧生成器)。都比同族的模块缓存问题隐蔽得多(那族会 ImportError 报出来)。旧修法 = 树被改写后按**磁盘现版本**重取配置(`_pipeline.reload_config`, 含 STOP 级复检): commit 侧复跑前先 `refresh_package_modules()` 再重取, 变了才登记步骤行; sync 侧在快进后 / rebase 每轮开头与收尾各重取一次, 取不到或新配置关掉自动化解就**放弃自动化解并回滚**。⚠ **该修法已于 2026-10-07 被「快照自举」取代 —— 现行判据见下方一行, 详情见文末附件「收口」节**。
> 等级: L2
> 触发: ship.commit, sync, 复跑, 旧配置, 配置过期, 启动时快照, 配置迁移窗口, .my-commit-flow.toml, reload_config, 闸门规则不对, 白名单, 生成物自动化解, 静默丢内容, 内部同步之后, rebase 之后, 闸门照跑但没生效

**Refs:** memory-bank/tasks/26-10-06-ship-rerun-stale-config.md

> 已外迁: 叙事整段迁至 [self-rewrite-config-migrated-26-10-31-0952.md](attachments/self-rewrite-config-migrated-26-10-31-0952.md) (kb.tier migrate 26-10-31-0952; 判据单点见上方摘要)
> 现行处置(快照自举, 2026-10-07 起): 入口启动时把整包复制到**仓库之外**的临时目录再从副本重入(`scripts/_snapshot.py`) ⇒ 一次调用 = 一个版本, 中途 rebase 换掉工作区配置也不换规则; 上游改动本包时 `ship.commit` 登记「快照: 上游改动了本包 → 本次仍按启动版本运行, 重跑以采用新版本」(不静默)。同族判据一句话: 「我这个进程运行期, 磁盘上我自己那份源码/配置会不会变?」。守阵 `scripts/test_snapshot.py` + `test_commit.py::test_post_rebase_pack_changed_leaves_hint`。
