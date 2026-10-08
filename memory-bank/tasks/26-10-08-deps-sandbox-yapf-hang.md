# 26-10-08-deps-sandbox-yapf-hang — 沙箱内 yapf 挂住/刷磁盘: 引擎超时杀整棵树 + 项目内 yapf

**Status:** In Progress
**Added:** 2026-10-08
**Updated:** 2026-10-08 15:39
**Topics:** deps-sandbox-tool-cache
**Summary:** 用户报「yapf 挂住, 一直占高 CPU, 且一直写磁盘; my-commit-flow 或 yapf 有严重 BUG」。取证: yapf 在 **import 期**就要把编译好的语法 pickle 写进 `%LOCALAPPDATA%\Google\YAPF\Cache\0.43.0`(路径由 platformdirs 的 Win32 已知文件夹 API 决定, **环境变量改不动**), 该目录不在 agent 工具 shell 的沙箱白名单里 ⇒ 写入被拒; 因目录**已存在**, CPython `tempfile._mkstemp_inner` 在 Windows 上把 `PermissionError` 当"重名"⇒ 最多 10000 次紧循环 ⇒ 表现为挂住 + 100% 单核 + 持续写磁盘 + 漏临时文件(6 周累计 2574 个 / 22MB, 最终缓存文件从未落成)。三处修复: ①`run.py::_shell` 超时改杀**整棵进程树**(旧 `subprocess.run(timeout=)` 只杀 cmd.exe, 把 yapf 留成孤儿继续烧); ②`dev.fmt` 改用**项目内** yapf(`uv run yapf`, dev 依赖钉 0.43.0)并把 timeout 收到 60s; ③提交闸门 fmt gate 同步 60s。残留: 缓存目录的清理**需用户在自己终端做**(agent 侧删这些路径同样被拒)。
**Refs:** memory-bank/pitfalls/testing/sandbox-tool-cache.md

## 原始请求

> 「my-commit-flow 或 yapf 似乎有严重的 BUG, 我观察到 yapf 挂住, 一直占用高 CPU, 且一直写磁盘, 分析原因」
> 随后: 「修 1/2/3/4」—— 按分析给出的四个方向实施(项目内工具 + 缓存落位 / 加超时兜底 / 坑档+守阵 / 清理残留)。

## 思考过程与决策

- **归因链(逐环实证)**: ①`dev.fmt` 原用 **PATH 上的系统 yapf**(`.venv` 里根本没装) ⇒ 工具版本/缓存位置都不可控;
  ②yapf 的语法缓存在 `%LOCALAPPDATA%\Google\YAPF\Cache\<ver>`; ③沙箱白名单不含 `AppData\Local\Google` ⇒ 拒写;
  ④**间歇挂死**: `_mkstemp_inner` 把 `PermissionError` 当重名冲突 `continue`(Windows + `isdir` + `access(W_OK)` 三者齐备),
  最多 10000 次紧循环 ⇒ 高 CPU + 刷磁盘; ⑤失败被 `driver.load_grammar` 的 `except OSError: pass` 吞掉 ⇒ 静默不留缓存。
- **取证手段(可复用)**: `faulthandler.dump_traceback_later(N, exit=True)` 抓烧 CPU 进程的 Python 栈 —— 直接指到
  `tempfile._mkstemp_inner` ← `grammar.Grammar.dump` ← `pgen2.driver.load_grammar` ← `pygram`;
  外加"同命令关沙箱跑立刻成功"的对照实验, 把"工具坏"与"沙箱约束"切开。
- **被推翻的两个方案**: ①**环境变量改缓存位置** —— 实测 platformdirs 4.3.6 在 Windows 走 `SHGetKnownFolderPath`,
  改 `LOCALAPPDATA`/`XDG_CACHE_HOME` 后 `user_cache_dir()` 仍返回 `AppData\Local\Google\...` ⇒ 此路不通;
  ②**升级 yapf** —— PyPI 实查 0.43.0 已是最新, 无版本可升。
- **口径修正(重要)**: 收尾复测时 `uv run yapf -i <file>` 与系统 `yapf -i <file>` **都在 <1s 内正常返回 rc=0**
  (沙箱仍在拒写、仍在刷临时文件) ⇒ 挂死是**间歇**的。因此**不把 fmt gate 降级为 `auto=false`**(那会白丢自动格式化),
  改为"短 timeout(60s) + 引擎整树 kill"兜底 —— 该结论已回写坑档与两处配置注释。
- **引擎缺陷独立成立**(与 yapf 无关): `subprocess.run(timeout=)` 超时只 kill 直接子进程, `shell=True` 下那是
  cmd.exe; 真正的工具是孙子 ⇒ 被留成孤儿(继续烧 + 占管道读端)。my-commit-flow 的 `_pipeline.run_capture` 早有
  `taskkill /F /T` 看门狗, 而 commands 引擎 `_shell` 一直没有 —— 这是本次的真实修复点之一(守阵钉住)。
- **做不到的一件事**: 缓存目录的**清理**(用户报的第 4 项)agent 侧做不了 —— 连 `dangerouslyDisableSandbox` 下
  `Remove-Item`/`Rename-Item` 该目录或其中的文件都被拒(实测)。只能给出命令由用户在自己终端执行。

## 实现计划

- **S1** 引擎: `run.py` 加 `_kill_tree`, `_shell` 改 Popen + 超时杀整树 + 收尸后照旧上抛 TimeoutExpired; 守阵 1 条(红验)。
- **S2** 工具: `pyproject.toml` dev 组加 `yapf==0.43.0` + `env.sync`; `dev.fmt` 改 `uv run yapf -i <args>`, timeout 300→60, note/doc 写明沙箱约束。
- **S3** 闸门: fmt gate timeout 120→60 + 注释写明判据(保留 `auto = true`)。
- **S4** 坑档: `pitfalls/testing/sandbox-tool-cache.md`(三行头 + 触发/判别/处置三必填 + 守阵 + 复发=1)。
- **S5** 收尾: 全量基线 + 档案 + 切片 + kb.index。**残留**: 缓存清理交用户(agent 无权)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 引擎超时杀整棵树 + 守阵(红验) | Done |
| S2 | 项目内 yapf 钉版本 + dev.fmt 改造 | Done |
| S3 | fmt gate timeout 收紧 + 注释判据 | Done |
| S4 | 坑档 sandbox-tool-cache | Done |
| S5 | 基线 + 档案 + 切片 + kb.index | Done (本档案) |
| S6 | 缓存目录清理(agent 无权, 交用户) | Open (用户侧) |

## 进度日志

- **2026-10-08 14:00–15:39** 取证 + 实施四方向。取证关键物证: `faulthandler` 栈(`_mkstemp_inner` ← `Grammar.dump` ←
  `load_grammar` ← `pygram`)、缓存目录 2574 个残留临时 pickle / 22.37MB / 最早 08-25 且无最终缓存文件、
  platformdirs 忽略 env 的对照实验、`uv run yapf --version` 打印版本后仍刷被拒路径。实施: `run.py` 加
  `_kill_tree` + `_shell` 改 Popen(守阵 `test_engine.py::test_shell_kills_process_tree_on_timeout`, **红验**:
  抽掉 `_kill_tree` 行即红 → 还原复绿); `pyproject.toml` dev 组加 `yapf==0.43.0`(uv.lock 随之更新);
  `dev.fmt` → `uv run yapf -i <args>` + timeout 60; fmt gate timeout 120→60(保留 auto=true);
  坑档 `pitfalls/testing/sandbox-tool-cache.md`。**口径修正**: 复测显示沙箱内 yapf 多数时候 <1s 正常返回,
  故未降级闸门, 只做"短超时 + 整树 kill"兜底(已回写坑档与两处注释)。test.pkg **155 passed**(+1 新守阵)。
- **残留**: ①缓存目录清理需用户在自己终端执行(见档案 Summary 与坑档「处置 ④」); ②"沙箱白名单放行该目录"是
  彻底消除项, 由用户在 Settings -> Permission & Approval 配置。