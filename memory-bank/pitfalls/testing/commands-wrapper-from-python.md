# python 子进程调不到 commands wrapper(WinError 2)

> 摘要: python 脚本里 `subprocess.run(["commands", "run", ...])` 必 FileNotFoundError(WinError 2) —— commands wrapper 是 bash 侧脚本, 不在 Windows CreateProcess 的可执行体解析范围内; 命令行能跑 ≠ 子进程能跑。
> 触发: subprocess, commands wrapper, WinError 2, FileNotFoundError, 造种脚本
**Refs:** memory-bank/tasks/26-11-05-backend-relocate-fastresume-finalize.md

### 实验脚本里用 python subprocess 调 `commands run real.seed ...` 直接炸

- **触发**: 真机实验/测试脚本(nseries 等)想在 python 内部调包内命令(造种/起停实例/守卫), 写 `subprocess.run(["commands", "run", ...])` —— 终端里 `commands` 明明可用。
- **判别**: `FileNotFoundError: [WinError 2] 系统找不到指定的文件`, 指向 `CreateProcess`; 同一命令在 Git Bash 终端直接跑没问题。根因: wrapper 落在 PATH 目录的是 bash 脚本(非 .exe), `shell=False` 的 Windows 子进程只按 PE 可执行体解析。
- **处置**: ①首选该步挪 Bash 侧先跑, python 只收结果(如 infohash 走环境变量/文件交接); ②必须进程内调时, 用 `commands show <task>` 取该任务 doc 里的 `$` 展开式行, 在 subprocess 里按该展开式直调(引擎兜底展开式见 commands skill), 且 **cwd=仓库根**(脚本按仓库相对路径找文件)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
