# 包脚本被自己改写后的延迟 import

> 摘要: 本包脚本住在**仓库里**, 而 `ship.commit` 的内部同步会把远端新版包脚本 rebase 进工作区 —— Python 的模块缓存让延迟 import 的**新**脚本撞上进程启动时的**旧**依赖模块, 症状是 `ImportError: cannot import name …`, 而提交其实已经落稳; 修法 = 延迟 import 前按磁盘现版本热刷新本包模块(内容摘要门控 + `importlib.reload` 保身份)。
> 触发: ImportError, cannot import name, ship.commit 退出码 1, 提交成功却报错, 延迟 import, 延后 import, 内部同步, rebase 之后崩, sys.modules, 模块缓存, importlib.reload, 热刷新, 包脚本自我改写, refresh_package_modules

**Refs:** memory-bank/tasks/26-10-06-ship-self-rewrite-imports.md

### 提交已落盘, `ship.commit` 却在推送步 `ImportError` 且退出码 1

- **触发**: `commands run ship.commit` 报 `ImportError: cannot import name '<名>' from '_pipeline'`;
  或提交明明成功(HEAD 已挪、工作树已净)却以非 0 收尾; 且**只在内部同步真的 rebase 了远端提交**的那一次出现。
- **判别**: 本包脚本住在**仓库里**(`.commands/my-commit-flow/scripts/`), 而流水线是
  「提交 → 内部同步(rebase, 可能把远端新版包脚本换进工作区) → 延迟 `import push`」。
  Python 的 `from X import y` **只认 `sys.modules` 里的缓存** —— `commit.py` 启动时已缓存旧 `_pipeline`,
  于是延迟导入的**新** `push.py` 执行 `from _pipeline import … retry_note` 时, 那个新名字在缓存里没有。
  2026-10-06 实证: 远端 `aaff8b3a` 给 `_pipeline` 加了 `retry_note`, 本 clone 的 `commit.py` 是同步前起的进程
  ⇒ 推送步 ImportError、退出码被误置 1(与 v3「推送未完成不改退出码」的契约相悖)。
  **只有"同一进程里自己改写了自己的源码"才复现** —— 补跑 `ship.push`(新进程, 从磁盘重载)永远正常,
  所以初遇时极易误判成网络 / 远端问题。
- **处置**: 延迟 import 之前调 `_pipeline.refresh_package_modules()`(`commit.py` 推送步前已内联调用)。
  两条判据别省: ① 用 `importlib.reload`(**保模块身份**), 不要「删 `sys.modules` 再 import」——
  后者造出**第二个**模块对象, 已绑定旧名的调用方与新导入的名字从此分属两份;
  ② 必须按**内容摘要**门控(**不是 mtime** —— 切分支 / checkout 可能保留 mtime): 测试用 monkeypatch 把
  `run_sync` / `run_push` 换成替身而源码没变, 无条件 reload 会把替身冲掉、让守阵自己失灵。
  守阵: `test_pipeline.py::PackageRefreshTest`(机制) + `test_commit.py::test_push_path_refreshes_package_modules`
  (接线顺序 = 同步 → 刷新 → 推送)。
- **延伸**: 凡是"**脚本住在被它自己操作的仓库里**"的工具链都有这一形态 —— 判据是问一句
  「我这个进程运行期, 磁盘上我自己那份源码会不会变?」。
