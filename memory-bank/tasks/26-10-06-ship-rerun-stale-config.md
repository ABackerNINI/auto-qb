# 26-10-06-ship-rerun-stale-config — 自我改写后仍用启动时那份配置: commit 的闸门复跑 + sync 的生成物自动化解

**Status:** Done  
**Added:** 2026-10-06  
**Updated:** 2026-10-07  
**Topics:** ship-rerun-stale-config  
**Summary:** 另一会话报出的**计划外引擎缺陷**(撞迁移窗口必现, 平时不可见): `ship.commit` 的闸门**复跑**发生在内部同步的 rebase 之后, 而它用的 `cfg` 是**进程启动时**读的那份 —— 若那次 rebase 把远端新版 `.my-commit-flow.toml` 换进了工作区(本包目录就在仓库里), 复跑就是"用**旧规则**验合并后的新树": 旧闸门集 / 旧 `each_limit` / 旧红线 / 旧生成物白名单全都对不上, 而输出与"全过"**一字不差**(比同族的 ImportError 隐蔽得多)。修法 = 复跑前先 `refresh_package_modules()`(让 `_ship_config.KEY_DEFAULTS` 跟着现版本, 否则远端新加的键会被按「顶层未知键」误判 STOP), 再 `_pipeline.reload_config(cfg)`: 交出**磁盘现版本**并**复检 STOP 级问题**; 配置变了登记一行步骤行(没变静默), 读不到 / 新配置有错则按「推送未完成」停下 —— **绝不拿旧规则硬跑**。守阵 = `test_pipeline.py::ReloadConfigTest`(机制 3) + `test_commit.py` 接线 3(复跑用重取那份 / 没变不留痕 / 新配置坏则停), **红验两处**。第二轮(2026-10-07)收掉同族第三处: `sync.py` 的**生成物自动化解**在把树推到上游 tip 之后仍用启动那份 `cfg` 取白名单 / 重跑命令 —— 旧白名单**放宽** = 静默丢内容, 收窄 = 该保的没保, `generated_regen_cmd` 换了 = 重跑的是旧生成器(自证也自证的是旧规则)。修法 = `sync._reload_cfg(cfg)`(`_pipeline.reload_config` + "新配置仍允许自动化解" 两档), 快进后 / rebase 每轮开头与收尾各取一次; 任一档不成立即**放弃自动化解、回滚**, 退回现状失败行(自动化解是优化, 不为它新增失败模板)。守阵 = `test_sync.py` 4 条, **红验三处**。  
**Refs:** memory-bank/pitfalls/git/self-rewrite-config.md, memory-bank/testing/baselines/26-10-06-2108-ship-rerun-stale-config.md, memory-bank/testing/baselines/26-10-07-0138-ship-autoresolve-stale-config.md

## 原始请求

> 另一会话报缺陷, 分析修复: 遗留观察（未动，待拍板）：ship.commit 单进程内 rebase 改到 .my-commit-flow.toml 时，「合并远端后复跑」的闸门用的还是启动时旧配置——这是个计划外引擎缺陷（撞迁移窗口必现，平时不可见）

(另一会话在修 `ship.commit` 包脚本自我改写族缺陷时留下的**观察**, 当时按范围守恒未动、待拍板。本轮用户直接点名「分析修复」⇒ 显式授权的执行任务。)

## 思考过程与决策

### 1. 先定性: 这是哪一族

上一轮修的是同族的**模块缓存**问题(`refresh_package_modules`, 见
[26-10-06-ship-self-rewrite-imports](26-10-06-ship-self-rewrite-imports.md))。本缺陷是同一根因的**另一半**:
本包目录就在仓库里, 内部同步的 rebase 会同时换掉**包脚本**与**包配置**, 而进程手里的两份快照都停在启动时。
两者的差别决定了本缺陷更危险:

| | 症状 | 可见性 |
|---|---|---|
| 模块缓存族 | `ImportError: cannot import name …` + 退出码被误置 1 | **报出来**(提交明明成功却像硬失败) |
| 配置快照族(**本档**) | 闸门**照跑**, 只是规则不对; 输出与"全过"一字不差 | **静默** —— 只能靠"复跑前重取"这条纪律兜住 |

### 2. 代码事实核对(先读再改)

- `commit.py` 启动时 `cfg, _src = load_config()`(一次), 第 6 步复跑闸门时直接复用 `cfg["gates"]` 与 `ctx`
  —— 而 `ctx` 里的 `each_limit` 也来自同一份 `cfg`。⇒ 缺陷成立。
- `_ship_config.load_config` **不缓存**(每次真读文件) ⇒ 缺的不是"读得到", 而是"**没人再读一次**"。
- `_pipeline` 已有 `config_stops`(配置体检取 STOP 级)与步骤登记(`step`/`emit_steps`) ⇒ 机制有现成的家。

### 3. 修法选择

- **把 `load_config()` 的调用挪到复跑前一行** —— 不够: 远端新配置若同时**加了新键**, 进程里的
  `_ship_config.KEY_DEFAULTS` 还是旧的 ⇒ 新键被 `load_config` 静默丢掉, 又被 `config_problems`
  按「顶层未知键」判 STOP ⇒ 假红。必须先 `refresh_package_modules()`(上一轮已有的机制, 摘要门控,
  源码没变时零动作)再重取。**采用**。
- **只在配置里加一个开关("复跑前重读配置")** —— 多一个可能被关掉的旋钮, 而这不是可选项:
  拿旧规则验新树没有任何正当场景。**否**。
- **新配置有 STOP 级问题时照旧跑** —— 那等于"闸门静默失效", 与包内 fail-fast 判据相悖
  (闸门很贵, 拼错一个键让它不生效比报错坏得多)。**否**: 停下并按「推送未完成」处理(提交已落稳, 退出码仍 0)。

### 4. 两个刻意的"不变"

- **复跑的改动清单不变**: 仍是本次提交的那批(`present`), 不重算成"合流后的全部 diff" ——
  闸门语义是"本次改动该过的检查", 设计如此(见 `pipeline.md`「闸门跑两轮的时机」)。
- **`--no-push` 路径不碰**: 它不同步, HEAD 不改写 ⇒ 没有复跑, 也就没有重取。

### 5. 为什么放 `_pipeline` 而不是 `commit.py`

`reload_config` 是**配置体检**的一部分(`config_stops` 就在 `_pipeline`), 且与 `refresh_package_modules`
同族同家; `_pipeline` 的定位正是"内部共享件"。代价是测试要钉**两个**加载点(启动走
`commit.load_config`, 重取走 `_pipeline.load_config`)—— 这两个点本来就是两件事, 钉两处反而把"什么时候读配置"
写清楚了。

## 实现计划

| # | 文件 | 改动 |
| - | --- | --- |
| 1 | `_pipeline.py` | 新增 `reload_config(cfg) -> (配置, 停止原因)`: 磁盘现版本 + STOP 复检; 模块 docstring 补一行; 新段「自我改写后的配置重取」 |
| 2 | `commit.py` | 第 6 步复跑前: `refresh_package_modules()` → `reload_config(cfg)` → 坏了即「推送未完成」停下 / 变了登记步骤行 / 按新 `each_limit` 重建 `ctx`; import 补 `reload_config`; docstring 步骤 7 与步骤行示例补登 |
| 3 | `test_pipeline.py` | 新增 `ReloadConfigTest`(3 条) + 头部「测试计划」补登; import 补 `ConfigMissing` |
| 4 | `test_commit.py` | 新增接线 3 条(用重取那份 / 没变不留痕 / 新配置坏则停) + `_cfg_with_gate` 夹具 + 头部「测试计划」补登 |
| 5 | `.commands/my-commit-flow/references/` | `pipeline.md`(v3.1 步骤表 + 「复跑前重取配置」判据) · `config.md`(「配置在流水线里什么时候被读」) |
| 6 | `memory-bank/` | 本档案 · `pitfalls/git/self-rewrite-config.md` 新条目 · `testing/guards.md` 登记 · 基线切片 · activeContext 切片 |

### 第二轮(2026-10-07): 收掉同族的第三处 —— `sync.py` 的生成物自动化解

| # | 文件 | 改动 |
| - | --- | --- |
| 7 | `sync.py` | 新增 `_reload_cfg(cfg)`(`_pipeline.reload_config` + "新配置仍允许自动化解" 两档判据); `_resolve_behind_overlap` 在 `merge --ff-only` 之后重取 + 按**新**白名单复核已丢弃的路径; `_resolve_rebase` 在**每轮循环开头**与**收尾**各重取一次(白名单同步换新); 模块 docstring 与 `_resolve_rebase` docstring 补判据 |
| 8 | `test_sync.py` | 夹具扩 `tag`(假生成器内容可区分)与 `auto`(配置开关可写 false); 新增 `_push_remote_files`(一笔改多文件) / `_seed_repo_config_conflict`(**配置放进仓库里** —— 临时包目录在仓库外, rebase 换不掉它) + 守阵 4 条; 头部「测试计划」补登 |
| 9 | `_pipeline.py` | `reload_config` docstring 补第二个调用点(sync)与两侧"停"的差别 |
| 10 | `.commands/my-commit-flow/references/` | `pipeline.md`(生成物自动化解节补「白名单/重跑命令必须来自合并后的配置」+ 保守默认补一档) · `config.md`(读配置时机表补 sync 一行) |
| 11 | `memory-bank/` | 本档案续记 · `pitfalls/git/self-rewrite-config.md` 补第二条目 + 摘要/触发扩写 · `pitfalls/git/editing-traps.md` 行尾条目**复发 +1** 并改判据 · `testing/guards.md` 补 4 行 · 新基线切片 · activeContext 切片更新 |

## 子任务状态表

| # | 子任务 | 状态 |
| -- | --- | --- |
| S1 | 读透 `commit.py` / `_pipeline.py` / `_ship_config.py` / `sync.py`, 定性为"配置快照过期"族 | Done |
| S2 | `_pipeline.reload_config`(磁盘现版本 + STOP 复检) | Done |
| S3 | `commit.py` 复跑前接线(刷新模块 → 重取配置 → 变更留痕 / 坏则停) | Done |
| S4 | 守阵 6 条(机制 3 + 接线 3), **红验两处** | Done |
| S5 | `dev.fmt` / `test.one` / `test.pkg` / `test.full` | Done |
| S6 | 知识库回写 + 索引重建 | Done |
| S7 | `sync._reload_cfg` + 三个取用点(快进后 / rebase 每轮开头 / 收尾) | Done |
| S8 | 守阵 4 条(机制 1 + 快进 2 + 分叉 1), **红验三处** | Done |
| S9 | `dev.fmt` / `test.one` / `test.pkg` / `test.full` + 知识库续写 | Done |

## 进度日志

- 20:54 用户点名「分析修复」。先按会话协议同步(`已同步 b56520ed`), 再读 `commit.py`(第 6 步复跑)、
  `_pipeline.py`(`config_stops` / 步骤登记)、`_ship_config.py`(`load_config` 不缓存)、`sync.py`
  (`run_sync` 何时改写 HEAD)与同族坑档 `pitfalls/git/self-rewrite-imports.md` —— 确认缺陷成立、
  且与上一轮是同一根因的另一半。
- 20:5x 实现 S2/S3。**关键顺序**: `refresh_package_modules()` 必须**先于** `reload_config()` ——
  否则远端新加的配置键会撞旧 `KEY_DEFAULTS` 被判「顶层未知键」STOP(假红)。
- 20:5x 补守阵 6 条。`test.one` 两个文件 = **87 passed**(基线 81, **+6**)。
- 20:5x **红验①**(还原旧行为: 复跑直接复用启动那份 `cfg` —— 把 `reload_config(cfg)` 换成 `cfg, None`)
  ⇒ `test_post_rebase_rerun_uses_reloaded_config` FAIL(第二轮闸门名仍是"旧闸门") +
  `test_post_rebase_broken_new_config_blocks_push` FAIL(走了推送, `不该走到推送`);
  `test_post_rebase_unchanged_config_stays_silent` 照旧绿(它断言的是"没有那行", 属预期)。
- 20:5x **红验②**(去掉 `reload_config` 的 STOP 复检, 改成无条件交出 fresh) ⇒
  `ReloadConfigTest::test_broken_new_config_reports_problem` FAIL。两处均已还原(`grep RED-VERIFY` 零残留)。
- 20:5x `commands run dev.fmt -- <4 个 py>`(有改动, 已收); `commands run test.pkg` = **137 passed / 165.98s**
  (基线 131, **+6**)。
- 20:5x `commands run test.full` 见基线切片。
- 21:0x 知识库回写(坑档 / guards 登记 / 两份 references / 切片 / 基线) + `commands run kb.index`。

### 第二轮 (2026-10-07, 用户「修复sync.py」)

- 01:26 用户点名「修复sync.py」= 收掉本档案「未闭环」里记的那一处。先按会话协议同步
  (`同步: 远端领先 1 笔 → 快进 b56520ed→20bd2157 · 本地未提交改动原样保留`), 确认进来的那笔
  (kb.nav 隐藏条目)与在改文件零重叠。
- 01:3x 读透 `sync.py` 的自动化解路径, 定性: 与 commit 侧**同一根因** —— 自动化解的头一件事就是把树
  推到上游 tip, 而本包配置就在仓库里 ⇒ 那一刻磁盘上的配置已是上游那份, 而 `cfg` 变量还是启动那份。
  三档走偏: 旧白名单**放宽** = 静默丢内容(白名单注释里警告的那件事) / 收窄 = 该保的没保 /
  `generated_regen_cmd` 换了 = 重跑的是**旧生成器**(`--check` 自证也自证的是旧规则)。
- 01:3x 实现 S7: `_reload_cfg`(两档: `reload_config` 的停止原因 + 新配置仍允许自动化解) + 三个取用点
  —— 快进路径在 `merge --ff-only` 之后(**并**按新白名单复核"已丢弃的那几处"), 分叉路径在每轮
  rebase 循环开头与收尾各一次。任一档不成立即**放弃自动化解、回滚**, 退回现状失败行(不新增失败模板)。
- 01:3x 补守阵 4 条。夹具要动两处: 假生成器加 `tag`(内容可区分, 才能证明重跑用的是**新**生成器);
  新增 `_seed_repo_config_conflict` 把配置放进**仓库里** —— 原来的临时包目录在仓库外, rebase 换不掉它,
  那样的用例根本测不到本缺陷。`test.one test_sync.py` = **34 passed / 367.98s**(基线 30, **+4**)。
- 01:3x **红验①**(快进路径不重取: `fresh = cfg`) ⇒ `test_behind_overlap_new_config_disables_autoresolve`
  FAIL + `test_behind_overlap_new_regen_cmd_is_used` FAIL(内容停在 `generated:gen/a.md`), 而分叉那条
  照旧绿 —— 证明两个取用点各自独立受守。
- 01:3x **红验②**(分叉路径两处都不重取) ⇒ `test_diverged_conflict_new_config_narrowing_rolls_back` FAIL
  (`assert not ok` 拿到 `True`: 拿旧白名单把它"化解"掉了), 快进两条照旧绿。
- 01:3x **红验③**(去掉 `_reload_cfg` 的"新配置关掉自动化解"档) ⇒
  `test_reload_cfg_honours_disk_and_policy` FAIL。三处均已还原(`grep RED-VERIFY` 零残留)。
- 01:3x **顺带修一处自己上一轮踩的行尾坑**: `git status` 末尾报 `references/config.md` 的
  `CRLF will be replaced by LF` —— 上一轮那次 Edit 把整份从 `LF=69` 写成了 `CRLF=81`(git diff 干净,
  只有警告露马脚)。按字节归一回 LF; 并按 DoD 给 `pitfalls/git/editing-traps.md` 的 `sed -i` 条目
  **复发 +1**、把判据从"用哪个工具"改到"改完必查"(旧文案把 Edit 说成安全选项, 正是这次没查的原因)。
- 01:4x `commands run dev.fmt`(有改动, 已收); `commands run test.pkg` / `test.full` 见新基线切片。
- 01:4x 知识库续写(坑档第二条目 + 摘要/触发扩写 · references 两处 · guards 补 4 行 · 新基线切片 ·
  activeContext 更新) + `commands run kb.index`。
