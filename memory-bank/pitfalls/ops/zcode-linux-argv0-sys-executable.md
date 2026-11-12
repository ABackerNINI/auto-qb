# ZCode Linux 宿主 argv[0] 污染致 sys.executable 虚假, commands 引擎任务全炸

> 摘要: ZCode Linux 宿主 argv[0] 污染致 sys.executable 虚假, commands 引擎任务全炸
> 触发: commands 引擎任务失败, AppImage not found, sync 失败, sys.executable, 第三环境, 新机器搭建, Non-ASCII character SyntaxError, wrapper list rc=1
**Refs:** memory-bank/reports/26-11-12-2347-report-linux-env3-probe.html

## 本篇只回答

新 Linux 环境(原生 Ubuntu, ZCode AppImage 宿主)接入时, `commands run <task>` 系列任务全炸成看似无关的报错, 该怎么判别与救活 —— uv 未装是前置断点, argv[0] 污染是深层机制, 两者叠加出的三种报错形态一并列此。

### 新 Linux 宿主上 uv 未装时, 引擎任务以「AppImage not found」或 py2 SyntaxError 全炸

- **触发**: 在新的原生 Linux 环境(第三环境类)第一次跑 `commands run <任何 task>`。前提两条叠加: ①宿主 ZCode exec 层把被启进程的 `argv[0]` 设成相对路径 `./ZCode-<版本>-linux-x64.AppImage`; ②项目未装 uv, wrapper 落到 `exec python` 兜底分支(本机 `python` = Python 2.7.18)。
- **判别**: 三种报错形态, 全都不指向真因 —— ①script 形任务(sync 等): `[/...绝对路径]/ZCode-*.AppImage: not found`(CPython getpath 按带斜杠的 argv[0] 把 `sys.executable` 解析成 `<cwd>/ZCode-*.AppImage`, 文件不存在; 引擎 `_config.py` 用 `sys.executable` 起包脚本); ②run 形任务里字面 `python` 的(kb/doc 包): `SyntaxError: Non-ASCII character '\xe...'`(py2 读 UTF-8 源码); ③每条命令输出头部一行 `parse error near '}'`(宿主自生成的 bash 语法启动脚本被 zsh 加载)与 `./ZCode-*.AppImage: command not found` 噪声, 两条都无害但污染输出。实锤一条: `python3 -c "import sys; print(sys.executable)"` 打出 AppImage 路径而非 python3 本体。
- **处置**: 装 uv 即全愈(wrapper 走 `uv run -q python` 分支: argv[0] 正确恢复 `sys.executable` = .venv/bin/python, 且 uv run 前插 venv/bin 进 PATH, 字面 `python` 也解析到 py3)。PEP 668 拦 pip 时的安装配方: `python3 -m pip install --user --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple uv`。uv 尚不可用时应急: 以 `python3 -c "import sys; sys.executable='/usr/bin/python3'; sys.path.insert(0,'<repo>/.agents/skills/commands/scripts'); import run; sys.exit(run.main())" run <task>` 临时修解释器跑单条任务。附带事实: `python-is-python2` 在装了它的新机上要用 `sudo apt install python-is-python3` 换掉(2026-11-12 第三环境已换)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
