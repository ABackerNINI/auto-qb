# wrapper — 让 `commands run <task>` 真的能敲

> [SKILL.md](../SKILL.md) 只留一句摘要; 这里放"为什么这么装"与批处理的坑 —— **排障 / 换平台时才读**。

## 使用流程: 先试跑, 失败才装(2026-09-25 起)

bare `commands run <task>` **直接试跑** —— PATH 那份是用户级文件, 装过一次就一直在, 多数会话免装;
报 command not found 才跑 `install_wrapper.py`(幂等; 落点目录本就在 PATH 上, 装完即生效, 无需重开 shell)。
装了却不正常(找不到引擎 / 转发异常)→ 重装一次幂等覆盖, 或先 `--dry-run` 看落点。

## 为什么需要它(2026-09-24 实测)

`commands run <task>` 一直是**文档记法**, 真敲时要展开成 `python <skill-dir:commands>/scripts/run.py run <task>`,
而 skill 装在哪因项目而异 ⇒ 执行者每次得先 Glob 定位(实测 4 次调用才敲出第一条命令)。

**把 wrapper 放进仓库根也解决不了** —— 三个 shell 的搜索规则不同:

| shell | cwd 里有 `commands` 时, `commands run x` | 原因 |
|---|---|---|
| Git Bash | ❌ command not found | PATH 里不含 `.` |
| PowerShell | ❌ CommandNotFoundException | PowerShell 不搜 cwd |
| cmd.exe | ✅ | 唯一会搜 cwd 的 |

⇒ 只有落到 **PATH 目录**才叫"真正实现"。所以生成器**两处都写**(默认)。

## 落点与文件

| 落点 | 文件 | 给谁用 |
|---|---|---|
| 仓库根(默认) | `commands`(POSIX) / `commands.cmd`(Windows) | `./commands run <task>`; cmd.exe 里 cwd 优先, 可 bare |
| PATH 目录(默认) | 同上 | **项目无关**: 从 `$PWD` 向上找 `.commands/`, 任意项目 bare 调用 |

- PATH 目录按 `~/bin` → `~/.local/bin` 挑**第一个已在 PATH 上**的; 在 PATH 上但目录不存在就**建出来**
  (实测本机 `~/bin` 正是"在 PATH 上但不存在")。
- 生成物**不入库**(`.gitignore` 里 `/commands` `/commands.cmd`): 单点定义在生成器里, 入库就是第 N+1 处副本。
- `--cwd-only` 只装仓库根(零用户级副作用); `--uninstall` 删掉生成的那几份(**只认自己的标记行**,
  别人的同名文件一律不碰, 要覆盖得 `--force`)。
- 装完**自证**: 真跑一次 `list` 并打印 rc —— 定位不到引擎时在安装那一刻就暴露, 不留到用的时候。

## 解释器: 为什么优先 `uv run python`

包脚本是以**引擎的 `sys.executable`** 执行的(见 `_config._script_argv`), 所以 wrapper 用哪个解释器起引擎,
就决定了包里 `script =` 那些任务跑在哪个环境。有 `pyproject.toml` + `uv` 时走 `uv run -q python`(项目环境),
否则退回 `python`。**这不是可有可无的优化** —— 它决定包脚本跑在系统 python 还是项目 venv。

## 批处理(`.cmd`)的三个坑(都是实测踩出来的)

1. **`rem` 行里别出现引号 / 括号 / 反引号**: 带这些字符的 rem 版实测**静默退出 2、且无任何输出**;
   同一份逻辑换成干净 rem 立刻正常。批处理的解析细节不值得在这里赌 —— 保持最小特征集。
2. **行尾必须 CRLF**: LF 会被拆错行(报 `'exist' 不是内部或外部命令` 这类怪错)。
3. **消息一律 ASCII**: cmd 按 OEM 码页(本机 GBK)读批处理, 中文会变 mojibake。

## 收录新命令要不要动 wrapper?

**不用**。wrapper 只做三件事: 向上找仓库根 → 找引擎 → 原样转发参数。新命令进的是**包**,
`list` / `run` 立刻能看到它 —— wrapper 与包内容无关。
