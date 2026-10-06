# 26-10-07-ship-self-snapshot — my-commit-flow 自我改写版本撕裂: 快照自举可行性验证与治本方案

**Status:** Done  
**Added:** 2026-10-07  
**Updated:** 2026-10-07  
**Topics:** my-commit-flow-self-snapshot  
**Summary:** 用户报出本包自我改写的**治本**需求: `ship.commit` 内部同步的 rebase 会把远端新版**包脚本 / 配置**换进工作区(本包目录就在仓库里), 于是同一次调用里"提交前"与"提交后"跑的可能不是同一版代码 / 同一份规则 —— 既有修复(`reload_config` + `refresh_package_modules`)是逐点打补丁, **治标**: 入口脚本自身无法热刷新、`importlib.reload` 不重绑调用方已导入的名字、配置重取只覆盖两个点、逐点接线无全局不变量、门控与依赖序本身脆弱(共 5 处漏洞)。用户提出「把整包复制到临时目录运行」。本轮**只做分析与可行性验证, 未改生产脚本**: ①通读全部脚本与 references, 逐点核对既有修复的覆盖边界; ②对**真实包**注入快照机制原型, 端到端实测 **10/10 通过**(真仓真包提交成功 / 副本在仓库外 / **改写原包后旧副本免疫** / 新调用采纳新版 / `import` 不重入 / 信息入口作用于原包 / 根解析 / 退出码透传), 复制开销 avg 26.2ms。结论: **临时目录快照自举可行且为最优解**, 采纳「快照语义」= 一次调用只认一个版本; 方案空间(移出仓库 / git worktree / 两段进程 / 继续打补丁)均有结构性缺陷。完整分析见报告; 实施与批次待用户拍板。 **实施已完成(2026-10-07)**: 新增 `scripts/_snapshot.py`(快照自举核心), 四个入口 `commit/sync/push/verify_ref` 的 `__main__` 各加 3 行守卫, `_ship_config.find_root()` 认 `COMMAND_FLOW_REPO_ROOT`; 退役 `refresh_package_modules` / `reload_config` / `sync._reload_cfg` 三条治标机制及全部接线(生产脚本里已零残留), 新增 `_pipeline.pack_touched()` 步骤行(上游改本包 → 提示重跑); 守阵迁到 `test_snapshot.py`(15 条: 重入 / 免疫 / 采纳 / 根注入 / `import` 不重入 / 退出码透传 / 治标机制已退役静态守卫), `test_commit.py` 增 `test_post_rebase_pack_changed_leaves_hint`; 真机 `my-commit-flow.sync` 与 `verify-ref` 均经快照重入成功、无残留临时目录; test.pkg **142 passed**。  
**Refs:** memory-bank/reports/26-10-07-0208-report-my-commit-flow-self-snapshot.html, memory-bank/activeContext/26-10-07-0208-ship-self-snapshot.md

## 原始请求

> my-commit-flow脚本在pull时会更新, 如果my-commit-flow本身也更新了, 可能会导致一部分按更新前的运行, 一部分按更新后的运行, 之前的修复只是治标, 需要一个彻底的解决方案, 目前想到的方案是: my-commit-flow将自己复制到临时目录运行, 需要验证可行性, 或考虑其它更好的方案, 写一个报告

## 思考过程与决策

### 1. 先定性: 这是自指(self-reference)缺陷

工具的**源码与配置住在被它自己操作的仓库里**, 而工具在运行中途(内部同步的 rebase)会改写这棵树。
危害分两族(既有坑档已记): **模块缓存族**(`ImportError`, 报出来)与**配置快照族**(闸门照跑但规则不对, 静默)。
用户说的"一部分按更新前、一部分按更新后"正是撕裂本身 —— 混合边界取决于补丁打在哪几个点, 不可预测。

### 2. 既有修复为什么只是治标(逐点核对, 5 处漏洞)

| # | 漏洞 | 代码事实 |
|---|---|---|
| 1 | 入口脚本自身**永远无法热刷新** | `_PACKAGE_MODULES` 只有 `_ship_config/_pipeline/sync/push`, **不含** `commit.py`/`verify_ref.py`(它们作为 `__main__` 运行) |
| 2 | `importlib.reload` 只换模块对象, **不重绑调用方已导入的名字** | `commit.py:52` `from _pipeline import (…, run_gates, …)` 是 import 期绑定; reload 后第 6 步复跑(`commit.py:267`)调的还是**旧**闸门引擎 |
| 3 | 配置重取只覆盖两个点 | 仅 `commit.py:255` 与 `sync._reload_cfg`(`sync.py:178`); `verify_ref.py:27` 的 `REPO`/`BRANCH` import 期定死; `commit.py` 的 `cfg` dict 之后仍用于红线/warn/each_limit |
| 4 | 逐点接线, **没有全局不变量** | 同类缺陷已修两轮(模块缓存 → 配置快照), "旧代码 × 新树"组合空间无法穷举 ⇒ 无法闭环 |
| 5 | 门控与依赖序本身脆弱 | `refresh_package_modules` 的"源码变了"摘要门控 + 注释自承的 `_PACKAGE_DIGESTS` 排序陷阱; 看不见 `commit.py`/`verify_ref.py` |

### 3. 方案选型

- **A. 临时目录快照 + 重入(用户提议)** —— 一次调用 = 一个版本, 免疫一切自我改写, 副本含工作区未提交改动。**采纳**。
- B. 把包移出仓库 —— 破坏"整包复制即可带走", 引擎要求包在 `.commands/` 下。**否**。
- C. `git worktree` 快照 —— 只含已提交版(丢工作区改动, 正在改流水线自己时反而跑旧版), 根歧义更复杂。**否**。
- D. 拒绝自我改写(检测到本包被改 → 停下要求重跑) —— 不自动续推, 但**作为提示并入 A**。
- E. 两段进程(提交 / 同步+推送) —— 段间仍撕裂。**否**。
- F. 继续打补丁 —— 治标, 已知 5 处漏洞。**否**。

### 4. 关键取舍: 快照语义(一次调用 = 一个版本)

启动时复制、从副本重入 ⇒ 中途 rebase 写进工作区的新版本对**本进程不可见**, 从**下一次调用**生效。
**放弃**"复跑用新规则"(那正是撕裂来源, 且补不全); 改为 rebase 后若发现本包被上游改动 → 登记一行步骤行提示重跑(不静默)。

## 实现计划

> 已实施（2026-10-07）。8 项一次完成 —— 测试迁移与机制退役**同批**做（机制没了, 测机制的守阵留着就是
> "测不到现实"的死守阵, 必须成对删除）。

| # | 文件 | 改动 |
| - | --- | --- |
| 1 | `scripts/_snapshot.py`(新) | 快照自举核心(原型已验证, 全文见报告 §06.5) |
| 2 | `commit.py` / `sync.py` / `push.py` / `verify_ref.py` | `__main__` 分支加 3 行守卫 |
| 3 | `_ship_config.py` | `find_root()` 认 `COMMAND_FLOW_REPO_ROOT` |
| 4 | `_pipeline.py` | 退役 `refresh_package_modules` / `reload_config`; 新增「本包被上游改动」步骤行 |
| 5 | `sync.py` | 退役 `_reload_cfg` 及三个取用点 |
| 6 | `test_*.py` | 迁移 9 条 reload/刷新守阵 → 改为快照守阵(重入 / 免疫 / 根注入 / import 不重入), 附红验 |
| 7 | `references/pipeline.md` · `config.md` | 更新「配置何时被读」表; 退役 reload 段, 换成快照语义 |
| 8 | `memory-bank/` | 两条 pitfall 补收口注记 · 本档案 · 报告 · 切片 |

## 子任务状态表

| # | 子任务 | 状态 |
| -- | --- | --- |
| S1 | 通读 `.commands/my-commit-flow/` 全部脚本 + references + 两条 self-rewrite 坑档, 定性为自指缺陷 | Done |
| S2 | 逐点核对既有修复的覆盖边界(5 处漏洞) | Done |
| S3 | 方案空间枚举与选型(A–F) | Done |
| S4 | 快照自举原型(真仓真包, 10/10 断言, 含免疫证明) | Done |
| S5 | 出可行性分析报告(HTML, 入 `reports/`) | Done |
| S6 | 实施(§实现计划 1–8) | Done |

## 进度日志

- 02:0x 用户点名「验证可行性 / 或更好的方案 / 写报告」。通读 `commit.py` / `_pipeline.py` / `sync.py` / `push.py` /
  `_ship_config.py` / `verify_ref.py` 与 `references/`, 并核对 `pitfalls/git/self-rewrite-{imports,config}.md`。
  定性: 自指缺陷, 既有修复(commit `58f7bb0a`)治标, 列出 5 处漏洞。
- 02:0x 写原型 `tmp-analysis/mcf-snapshot-proto/`(`_snapshot.py` + `run_proto.py`), 对真实包注入快照机制,
  在真 git 仓端到端验证: **10/10 通过**(T3a 免疫 / T3b 采纳为核心证据); 复制开销 avg 26.2ms / 16 文件。
  期间修正两处**测试夹具**问题(哨兵误置于 `from __future__` 之前致 SyntaxError; 未跟踪的包被首次提交卷入)——
  均为夹具问题, 与机制无关, 修正后全绿且可重复。
- 02:0x 出报告 `memory-bank/reports/26-10-07-0208-report-my-commit-flow-self-snapshot.html` + 本档案 + 切片;
  `commands run kb.index` 重建索引。**本轮不改生产脚本** —— 实施待用户拍板。
- 02:2x 用户拍板实施。新增 `scripts/_snapshot.py`(整包复制到**仓库之外** + `subprocess.call` 重入; 契约 5 个
  环境变量; `INFO_FLAGS` 纯信息入口不复制; 崩溃泄漏靠启动时清扫 >1 天); 四个入口 `commit/sync/push/verify_ref`
  的 `__main__` 各加 3 行守卫; `_ship_config.find_root()` 顶部认 `COMMAND_FLOW_REPO_ROOT`(副本在仓库外,
  向上找不到 `.git`)。
- 02:2x 退役治标机制: `_pipeline.refresh_package_modules` / `reload_config`(及 `_source_digest` /
  `_PACKAGE_*` / `hashlib` / `importlib` 导入)、`sync._reload_cfg` 及三个取用点、`commit.py` 的两处刷新调用
  —— 生产脚本里已**零残留**。新增 `_pipeline.pack_touched(old, new)`: rebase 后判上游是否改动了本包,
  `commit.py` 第 6 步据此登记一行 `快照: 上游改动了本包 → 本次仍按启动版本运行, 重跑以采用新版本`。
- 02:2x 守阵迁移: 删 `PackageRefreshTest`(3) / `ReloadConfigTest`(3) / `test_commit.py` 5 条 reload 接线 /
  `test_sync.py` 4 条配置重取(含 `_seed_repo_config_conflict` / `_push_remote_files` 夹具);
  新增 `test_snapshot.py` 15 条(单元 / 守卫 / 端到端重入·免疫·采纳 / 根注入 / 治标已退役静态守卫) +
  `test_commit.py::test_post_rebase_pack_changed_leaves_hint`; `StaticNameTest` 清单加 `_snapshot.py`;
  三份 docstring 的「测试计划」同步。test.pkg **142 passed**(首跑 4 条 push 用例在 `-n 4` 并行下假红 ——
  `git-receive-pack: Permission denied`, 串行复跑全绿, 与本轮改动无关)。
- 02:2x 文档: `references/pipeline.md` 新增「快照自举」节(契约表 / 取舍 / 开销 / 泄漏处置), 步骤行表、
  生成物自动化解的配置来源、复跑与推送两处 reload 段全部改写成快照语义, 脚本表加 `_snapshot.py`;
  `references/config.md`「配置何时被读」表压成一行(启动一次 = 一个版本)并补根解析的 env 覆盖;
  README 补一段快照自举。两条 pitfall 的摘要加"已被取代"标注 + 文末「收口」节。
- 02:2x 真机验证: `commands run my-commit-flow.sync` 经快照重入成功(且顺手快进 0b614153→f4430f32),
  `my-commit-flow.verify-ref` 经快照重入成功, `H:/Temp` 无残留快照目录; `commands run doc.caps` 无债务。
