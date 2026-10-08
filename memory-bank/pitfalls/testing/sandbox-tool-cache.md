# 沙箱里的工具写不了自己的缓存目录 → 不报错, 而是紧循环烧 CPU + 刷磁盘 + 挂住

> 摘要: agent 工具 shell 的沙箱按**白名单**放行写操作。工具若把自己的缓存写到白名单外(本仓实测: yapf 的语法缓存 `%LOCALAPPDATA%\Google\YAPF\Cache`), 而该目录**已存在**却写不进, 失败路径可能不是报错而是**紧循环**: CPython `tempfile._mkstemp_inner` 在 Windows 上把 `PermissionError` 当成"重名"继续换名重试 ⇒ 命令**挂住 + 100% 单核 + 持续写磁盘**, 且**全程没有任何报错**。
> 触发: 沙箱, sandbox, 工具挂住, yapf 挂住, 高CPU, 一直写磁盘, 缓存目录, mkstemp, NamedTemporaryFile, 白名单, AppData, platformdirs, 提交闸门卡住, 闸门超时后仍在跑

### 判别与处置

- **触发**: 在 agent 沙箱里跑「会写自己缓存目录」的工具(格式化器 / 编译器 / linter / 包管理器)。
  本仓实例(2026-10-08 实报): `commands run dev.fmt`(yapf 0.43.0)挂住 —— 100% 单核、每分钟往
  `%LOCALAPPDATA%\Google\YAPF\Cache\0.43.0` 漏一对 `Grammar-*.pickle` / `PatternGrammar-*.pickle`
  临时文件(6 周累计 **2574 个 / 22MB**), 而**最终缓存文件一个都没落成**(`os.rename` 从未成功)。
- **判别**(四步, 前两步都是硬证据):

  1. **进程在烧但没输出**: `Get-Process yapf` 看 CPU 秒数与工作集 —— 挂住的 yapf 是"CPU 秒数涨、
     working set 很小/停滞"。
  2. **Python 级栈取证**: 起进程时加 `faulthandler.dump_traceback_later(N, exit=True)`, 到点打印的
     栈直指根因 —— 本仓实测栈为
     `tempfile._mkstemp_inner` ← `grammar.Grammar.dump` ← `pgen2.driver.load_grammar` ← `pygram`
     (yapf 在 **import 期**就要写语法缓存)。
  3. **对照实验**: **同一命令关掉沙箱跑立刻成功** ⇒ 根因是"写被拒", 不是工具本身坏。
     这一步能把"工具的 bug"与"沙箱的约束"干净切开, 别省。
  4. **机制(为什么是挂死而不是报错)**: `_mkstemp_inner` 的 `except PermissionError:` 分支在
     `_os.name == 'nt' and os.path.isdir(dir) and os.access(dir, os.W_OK)` 时 `continue` ——
     沙箱拒绝 `open`, 却**不会**让 `os.access(W_OK)` 返回 False ⇒ 走 `continue` ⇒ **最多 10000 次紧循环**。
     ❗反过来: **目录不存在时反而安全** —— mkdir 先失败, 被 `driver.load_grammar` 的
     `except OSError: pass` 吞掉, 工具退化成"不缓存"照常工作。所以"把残留目录留着"是把它按在坏状态里。
  5. **⚠ 现状要说清**: 同一天复测, 同样的沙箱内调用**多数时候 <1s 就正常跑完**(沙箱仍然拒写、仍然刷被拒的
     临时文件, 但 10000 次循环本身很快)。⇒ 挂死是**间歇**的, 与"沙箱有多忙/拒写路径有多慢"强相关;
     所以别用"现在跑得通"反推"没这回事", 也别指望它稳定复现 —— 按下面的处置做**兜底**才是正解。
- **处置**:

  - ①**首选**: 把工具的缓存目录加进沙箱白名单(Settings -> Permission & Approval -> Custom
    Configuration)。**别指望环境变量**: yapf 的目录来自 platformdirs 的 Win32 **已知文件夹 API**
    (`SHGetKnownFolderPath`), 实测 `LOCALAPPDATA` / `XDG_CACHE_HOME` 都改了也不生效
    (platformdirs 4.3.6, 2026-10-08 实查仍返回 `AppData\Local\Google\YAPF\...`)。
  - ②**别让"会不会挂"决定提交能不能过**: 该工具在沙箱内是"多半能跑但不可靠" —— 给它一个**短的
    timeout**(本仓 `dev.fmt` 60s) + 引擎的整树 kill 兜底, 而不是把闸门关掉(会白丢自动格式化)或
    留着 300s 级别的长超时(挂一次就白等 5 分钟)。
  - ③**引擎超时必须杀整棵进程树**: `subprocess.run(timeout=)` 只杀**直接子进程**(`shell=True` 下是
    cmd.exe), 真正在烧的是**孙子**(yapf)。不杀 ⇒ 孤儿继续烧 CPU 且占着管道读端, 父进程即便
    "超时返回"也可能卡在 communicate。`run.py::_shell` 与 my-commit-flow `_pipeline.run_capture`
    都走 `taskkill /F /T`(单点: `run.py::_kill_tree`)。
  - ④**清理口径**: 该缓存目录**不能留** —— 留着(哪怕空的)就会触发上面的紧循环; 要么白名单放行,
    要么把它整个删掉(在**无沙箱**终端里删: agent 侧对这些路径的删除同样被拒)。
- **守阵**: `.agents/skills/commands/scripts/test_engine.py::test_shell_kills_process_tree_on_timeout`
  (超时路径必须走 `_kill_tree(pid)`, 且不得只 `kill()` 直接子进程 —— 红验过: 抽掉该行即红)。
- **复发**: 1(2026-10-08 首记)

**Refs:** memory-bank/tasks/26-10-08-deps-sandbox-yapf-hang.md