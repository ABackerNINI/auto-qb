# 26-10-06-ship-self-rewrite-imports — ship.commit: 包脚本被内部同步改写后, 延迟 import 撞缓存旧模块

**Status:** Done  
**Added:** 2026-10-06  
**Updated:** 2026-10-06  
**Topics:** ship-self-rewrite-imports  
**Summary:** 用户「提交」时实测的事故 —— `commands run ship.commit` 提交已落盘(`9e0b35fc`), 却在末尾内联推送步抛 `ImportError: cannot import name 'retry_note' from '_pipeline'`, 退出码被置 1(与包内 v3 契约「推送未完成不改退出码」相悖, 明明成功却像硬失败)。根因 = **包脚本住在仓库里**: 该次内部同步把远端新版包脚本(`aaff8b3a`, 给 `_pipeline` 加了 `retry_note`)rebase 进工作区, 而 `commit.py` **进程启动时**已把旧 `_pipeline` 载入 `sys.modules`; 延迟的 `from push import run_push` 导进来的**新** push.py 执行 `from _pipeline import … retry_note` 时按缓存解析 ⇒ 找不到新名字。修法 = `_pipeline.refresh_package_modules()`: 延迟 import 前按**内容摘要**判定源码是否被改写, 用 `importlib.reload`(保模块身份)重载本包模块, `commit.py` 在推送步前调用。守阵 = `test_pipeline.py::PackageRefreshTest`(机制: 变则重载 / 没变**零动作**不冲替身) + `test_commit.py::test_push_path_refreshes_package_modules`(接线顺序 = 同步 → 刷新 → 推送)。端到端复现脚本先重现同一 ImportError(`REPRO-OK`), 刷新后导入成功(`FIX-OK`, 重载名单恰为 `['_pipeline']`)。  
**Refs:** memory-bank/pitfalls/git/self-rewrite-imports.md, memory-bank/testing/baselines/26-10-06-1836-ship-self-rewrite-imports.md

## 原始请求

> 修复包脚本缺陷

(前一轮用户已说「提交」; `ship.commit` 完成提交后崩在推送步, 我按包内既定恢复路径补跑 `ship.push` 并报告了这条包脚本缺陷, 问「要不要入池」。用户直接选了**修** —— 于是本轮是显式授权的执行任务, 不走范围守恒的入池出口。)

## 思考过程与决策

### 1. 先定性: 是包脚本 bug 还是环境抖

`REPRO` 三处证据齐了才动手: ① 栈在 `commit.py:288 from push import run_push` → `push.py:31 from _pipeline import … retry_note`;  
② `_pipeline.py` **磁盘上**有 `retry_note`(`:205`), 而该进程内存里没有; ③ 触发条件恰是"本次内部同步 rebase 了远端提交"。  
⇒ 不是网络抖动(补跑 `ship.push` 秒成), 是**同进程自我改写源码**后延迟 import 读缓存。`aaff8b3a` 同时改了  
`_pipeline` / `_ship_config` / `sync` / `push` / `commit` / 两个测试 + 文档 —— 一个 commit 里"改名 + 改消费者",  
所以缓存错配必然发生。

### 2. 为什么不能在 `push.py` 里"容错 import"

把 `from _pipeline import … retry_note` 写成 `try/except ImportError` 再 fallback, 只是把 ImportError 换成  
"静默用了旧实现"—— 违反包内既有的 fail-fast 判据。要修的是**加载时机**, 不是把错误吞掉。

### 3. 三种修法里为什么选 `importlib.reload` + 内容摘要门控

- **删 `sys.modules` 再 import** —— 会造出**第二个** `_pipeline` 对象。`commit.py` 已绑定的 `git_run`/`run_gates`  
  与 push 新导入的名字从此分属两份(常量 / 函数可能不一致), 是更难查的雷。**否**。
- **把延迟 import 挪到模块顶层** —— `commit.py` 的 `from sync import run_sync` / `from push import run_push` 是  
  **故意延迟**的: 测试靠 monkeypatch `sync_mod.run_sync` / `push_mod.run_push` 打替身, 顶层 import 会让绑定  
  早于打桩、替身失效。**否**(动了就要重写一批守阵)。
- **`importlib.reload` + 内容摘要门控**(**采用**) —— reload 保模块身份(已在别处的绑定不受影响), 门控保证  
  "源码没变就零动作"⇒ 测试替身不被冲掉。用**内容摘要**而不是 mtime: 切分支 / checkout 可能保留 mtime,  
  摘要才是"现版本"的可靠判据。

### 4. 名单与顺序

`_PACKAGE_MODULES = ("_ship_config", "_pipeline", "sync", "push")` —— **依赖在前**(`_pipeline` import `_ship_config`;  
`sync`/`push` import 二者)。只重载 `sys.modules` 里**已有**的模块: 尚未导入的下次 `import` 天然就是新版,  
这也让生产路径只重载真正错配的那几个。**待重载名单先算齐再动手** —— `_pipeline` 自己也在名单里, 重载它会  
重算 `_PACKAGE_DIGESTS`, 边算边改会把排在它后面的 `sync` / `push` "洗白"而漏掉重载。

### 5. 调用点只放一处

rebase 发生在 `run_sync`(第 6 步)之后, 而它之后**唯一**的延迟 import 就是推送步的 `push` —— 故刷新只挂在  
`commit.py` 推送步前。`--no-push` 不碰推送, 也就不刷新(守阵钉了这一条)。`ship.push` / `sync` 作为**独立入口**  
是新进程, 从磁盘首载, 不需要。

## 实现计划

| # | 文件                 | 改动                                                                                                                                                                |
| - | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | `_pipeline.py`     | 新增 `_PACKAGE_MODULES` / `_PACKAGE_DIR` / `_source_digest` / `_PACKAGE_DIGESTS` / `refresh_package_modules()`; imports 补 `hashlib` / `importlib`; 模块 docstring 补一行 |
| 2 | `commit.py`        | 推送步前调 `refresh_package_modules()`; 顶部 import 补该名; docstring 流程第 8 步补说明                                                                                            |
| 3 | `test_pipeline.py` | 新增 `PackageRefreshTest`(3 条: 源码变则重载 / 没变零动作 / 取不到摘要跳过) + 头部「测试计划」补登                                                                                               |
| 4 | `test_commit.py`   | 新增 `test_push_path_refreshes_package_modules`(顺序守阵)与 `test_no_push_never_refreshes` + 头部「测试计划」补登                                                                  |
| 5 | `memory-bank/`     | 本档案 · `pitfalls/git/self-rewrite-imports.md` 新条目 · `testing/guards.md` 登记 · 基线切片 · activeContext 切片                                                               |

## 子任务状态表

| #  | 子任务                                          | 状态   |
| -- | -------------------------------------------- | ---- |
| S1 | 读透包脚本, 定性为"同进程自我改写 + 模块缓存"                   | Done |
| S2 | `refresh_package_modules`(摘要门控 + reload 保身份) | Done |
| S3 | `commit.py` 推送步前调用(顺序 = 同步 → 刷新 → 推送)        | Done |
| S4 | 守阵(机制 3 + 接线 2), **红验两处**                    | Done |
| S5 | 端到端复现(真实包代码, 事故重现 → 修复生效)                    | Done |
| S6 | `test.pkg` / `dev.fmt` / `test.full`         | Done |
| S7 | 知识库回写 + 索引重建                                 | Done |

## 进度日志

- 18:28 用户说「修复包脚本缺陷」⇒ 执行任务。先读 `commit.py` / `push.py` / `_pipeline.py` / `_ship_config.py` /  
  `sync.py` 与两条既有坑档(`package-move-imports.md` / `testing/patching.md`), 确认模块顶层无副作用、reload 安全。
- 18:3x 实现 S2/S3。`test.pipeline`(单文件)= **54 OK**(+3), `test_commit` = **27 passed**(+2)。
- 18:3x **红验①**: 注掉 `commit.py` 的 `refresh_package_modules()` ⇒ 顺序守阵 FAIL(`['sync','push']` 缺 `refresh`)。  
  **红验②**: 去掉摘要门控(改成"有摘要就重载") ⇒ `test_unchanged_source_never_touches_module` FAIL  
  (`VALUE 999` 被冲回 `1`)。两处都还原。
- 18:3x **端到端复现**(真实包代码 → 临时目录): 进程先 import rev A `_pipeline`(删掉 `retry_note`),  
  再把磁盘换成 rev B ⇒ `import push` 抛 `cannot import name 'retry_note' from '_pipeline'`(**与真事故一字不差**);  
  调 `refresh_package_modules()` → `REFRESH: ['_pipeline']` → 再 `import push` 成功。
- 18:3x `commands run dev.fmt -- <4 个 py>` 无改动; `test.pkg` = **131 passed** / 108.15s(基线 126, +5)。
- 18:3x `test.full` 见基线切片。
