# ship.commit 包脚本自我改写 — 延迟 import 撞缓存旧模块

> 摘要: 用户「提交」那一跑曝出的事故 —— `ship.commit` **提交已落盘**(`9e0b35fc`), 末尾内联推送步却抛
> `ImportError: cannot import name 'retry_note' from '_pipeline'`, 退出码被置 1(明明成功却像硬失败, 与包内
> v3 契约「推送未完成不改退出码」相悖)。根因 = **包脚本住在仓库里**: 该次内部同步把远端新版包脚本
> (`aaff8b3a`)rebase 进工作区, 而 `commit.py` **进程启动时**已把旧 `_pipeline` 载入 `sys.modules`, 延迟的
> `from push import run_push` 导进来的**新** push.py 按缓存解析 `retry_note` ⇒ 找不到。修法 = 延迟 import 前
> 按**内容摘要**门控、用 `importlib.reload`(保身份)重载本包模块(`_pipeline.refresh_package_modules`);
> `commit.py` 推送步前调用。最后活动: 2026-10-06 18:36

**Refs:** memory-bank/tasks/26-10-06-ship-self-rewrite-imports.md, memory-bank/pitfalls/git/self-rewrite-imports.md, memory-bank/testing/baselines/26-10-06-1836-ship-self-rewrite-imports.md

## 现状

- **机制单点**: `_pipeline.refresh_package_modules() -> list[str]`(返回真重载的模块名, 诊断用)。
  名单 `_PACKAGE_MODULES = ("_ship_config", "_pipeline", "sync", "push")` —— **依赖在前**;
  只重载 `sys.modules` 里**已有**的模块(未导入的下次 `import` 天然是新版)。
- **两条判据不可省**: ① `importlib.reload` 保**模块身份**(删 `sys.modules` 再 import 会造出第二个模块对象,
  已绑定旧名的调用方与新导入的名字分属两份); ② **内容摘要门控**(不是 mtime) —— 测试用 monkeypatch 把
  `run_sync`/`run_push` 换替身而源码没变, 无条件 reload 会把替身冲掉、让守阵自己失灵。
- **调用点**: 仅 `commit.py` 推送步(`from push import run_push` 之前)一处 —— 第 6 步 rebase 之后**唯一**的
  延迟 import 就是它。`--no-push` 不碰推送 ⇒ 不刷新。`ship.push`/`sync` 独立入口是新进程, 从磁盘首载, 不需要。
- **顺序**: `同步 → 刷新 → 推送`(守阵钉死)。刷新静默、无行为出口。
- **守阵 5 条**: `test_pipeline.py::PackageRefreshTest` 3(源码变则重载 / 没变零动作不冲替身 / 取不到摘要跳过) +
  `test_commit.py` 2(`test_push_path_refreshes_package_modules` 顺序 + `test_no_push_never_refreshes`)。
- **验证**: `test.pkg` **131 passed** / 108.15s(基线 126, +5); `test.full` 见基线切片;
  **红验两处**(注掉调用 ⇒ 顺序守阵红; 去掉门控 ⇒ 替身守阵红);
  **端到端复现**(真实包代码 → 临时目录)先重现同一 ImportError, 刷新后 `REFRESH: ['_pipeline']` 且导入成功。
- **未动**: `push.py` / `sync.py` / `verify_ref.py` 的生产逻辑 —— 本轮只加"加载时机"的修正, 零行为变更。

## 关键决策

- **不在 `push.py` 里 try/except ImportError**: 那只是把 ImportError 换成"静默用了旧实现", 违反包内
  fail-fast 判据 —— 要修的是**加载时机**, 不是把错误吞掉。
- **不把延迟 import 挪到模块顶层**(看起来最简单的修法): `commit.py` 的 `from sync import run_sync` /
  `from push import run_push` 是**故意延迟**的, 测试靠 monkeypatch `sync_mod.run_sync` / `push_mod.run_push`
  打替身; 顶层 import 会让绑定早于打桩, 替身全失效 —— 修一个 bug 换一批守阵失灵, 不划算。
- **待重载名单"先算齐再动手"**: `_pipeline` 自己也在名单里, 重载它会重算 `_PACKAGE_DIGESTS`;
  边算边改会把排在它后面的 `sync`/`push` 被这次重算"洗白"而漏掉重载。
- **判据用内容摘要而非 mtime**: 切分支 / checkout 可能保留 mtime, 摘要才是"现版本"的可靠判据。

## 未闭环

- **`_PACKAGE_MODULES` 是手写白名单**: 将来给包加第 5 个脚本、又在同步之后延迟 import 它, 得记得加进名单。
  目前只在**名单内的**模块被刷新; 判据未上守阵(守什么? "包目录里的脚本都在名单里"会与 `test_*.py` 打架,
  需要先定义"入口 vs 库"的分界)。本轮范围守恒未做。
- **`commit.py` 自己不在名单里**: 刷新发生在 commit 进程内, 重载自己既不安全也无意义 —— 它的旧绑定(如
  `run_gates`/`git_run`)在整个进程内保持旧版。当前**是安全的**(`_pipeline` 的两版函数对 commit 的用法等价),
  但若将来 `_pipeline` 改了 commit 依赖的签名, 那次 ship 会用到旧签名。判据: 同步改签名与前缀同名不兼容的
  改动, 尽量别和"改包脚本加载逻辑"同批。
- **`activeContext/` 切片数债务 71 > 70**(上限 70): 本轮新切片把计数从 70 顶过线 —— 机检判为**债务**
  (不拦提交)。按治理纪律(单点 `pitfalls/kb/cap-counting.md`)不在本会话清理, 转告用户另开会话处置
  (删「无入链 + 非开放决策 + 内容已被档案覆盖」的**已完结波次片**; 14 天规则常零命中)。
