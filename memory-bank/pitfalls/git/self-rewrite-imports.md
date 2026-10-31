# 包脚本被自己改写后的延迟 import

> 摘要: 本包脚本住在**仓库里**, 而 `ship.commit` 的内部同步会把远端新版包脚本 rebase 进工作区 —— Python 的模块缓存让延迟 import 的**新**脚本撞上进程启动时的**旧**依赖模块, 症状是 `ImportError: cannot import name …`, 而提交其实已经落稳; 旧修法 = 延迟 import 前按磁盘现版本热刷新本包模块(内容摘要门控 + `importlib.reload` 保身份)。⚠ **该修法已于 2026-10-07 被「快照自举」取代 —— 现行判据见下方一行, 详情见文末附件「收口」节**。
> 等级: L2
> 触发: ImportError, cannot import name, ship.commit 退出码 1, 提交成功却报错, 延迟 import, 延后 import, 内部同步, rebase 之后崩, sys.modules, 模块缓存, importlib.reload, 热刷新, 包脚本自我改写, refresh_package_modules

**Refs:** memory-bank/tasks/26-10-06-ship-self-rewrite-imports.md

> 已外迁: 叙事整段迁至 [self-rewrite-imports-migrated-26-10-31-0952.md](attachments/self-rewrite-imports-migrated-26-10-31-0952.md) (kb.tier migrate 26-10-31-0952; 判据单点见上方摘要)
> 现行处置(快照自举, 2026-10-07 起): 版本快照隔离(`scripts/_snapshot.py`) ⇒ 一次调用 = 一个版本, 中途 rebase 写进工作区的新版包脚本对本进程不可见, 从下一次调用生效。遗留症状(延迟 import 的 `ImportError`)若再现 = **绕过了入口**(如 `import commit` 后直接调 `main()`) —— 守卫只在 `__main__` 分支下生效。守阵 `scripts/test_snapshot.py`。
