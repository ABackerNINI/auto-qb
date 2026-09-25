# commands — 项目命令统一调用面 (纯引擎 + 包式配置层)
> 摘要: 同一条命令仓库里有 8 处副本 / 5 种写法, 唯一生效的那条恰好"看起来最不正常"。方案: skill 缩成**纯引擎**(只认识「包」与「命令」), 命令单点定义在 `<仓库根>/.commands/<包>/config.toml`, 包是**黑盒**, 路由**不落盘**改为逐级查询 + `pin` 常显, 反漂移闸门把文档手抄形态判红(63 → 0)。**W1–W6 已实施**: 引擎三件 + 六个顶级包(后者含 `ship/` 子包, 旧 skill 已删); 优化轮(两种记法 / `pin` 守卫 / 闸门去双写 / SKILL.md 硬上限); **W6 会话噪音治理**(异常感知摘要 / id 包路径写法 / 闸门摘要收敛 / 开工自检同步配方 / 包测试入闸门)。全过程与实测数字见档案。
> 触发: 命令在哪定义, commands, .commands, 包, task id, 反漂移, 手抄命令, 收录协议, add, pin, 常显, my-commit-flow 成包, 闸门位置, 两种记法, 沙箱假红, skill 描述, 摘要, 噪音, token, 入口, 包测试没跑
> 最后活动: 2026-09-25 08:48

## 状态

**计划**: [../plans/26-09-23-2008-commands-plan.html](../plans/26-09-23-2008-commands-plan.html) (v1.7)
**档案**: [../tasks/26-09-23-commands-unified-surface.md](../tasks/26-09-23-commands-unified-surface.md)

**已定的口径** (改之前先读, 这些都是被纠正过的设计级约束):

- **引擎 schema 只有三块**: `[pack]` / `[packs.*]` / `[tasks.*]`; 占位符只有 `<root>` / `<skill-dir:NAME>` / `<args>`。
  判据: 引擎认识的键必须对**任何仓库、任何命令**都成立 —— 含义依赖"我们在做什么事"的键(闸门 / 红线 / 远端)
  **属于包, 不属于引擎**。引擎目录 grep 项目词(`提交` / `测试` / `知识库` / `gate` / `red_line` / `commit` /
  `ship` / `gitee` / `TMPDIR`)**必须为空**, 这是"零领域逻辑"的机检判据(实测 0)。
- **一个包 = 一个黑盒**: 引擎唯一读 `<包>/config.toml`; 包内其它文件不读、不扫描、不知道存在。
  ⇒ `my-commit-flow` 那份 `.my-commit-flow.toml` 一行未改地留在包里, 由包脚本自读 (引擎注入 `COMMAND_FLOW_PACK_DIR`)。
- **层级靠子包表达**, 不是命令上的分组字段: 顶级包自动扫 `.commands/*/config.toml`, 子包由上级 `[packs.<名>]`
  注册, `enabled` 只在上级声明一处, `pin = true` 的命令**浮一级**到父级列表。
- **不降级原则**: 未知块内键 / `timeout` 非法 / 残留占位符 / 包级 `confirmed = false` / task id 全树重复 /
  包名与目录名不一致 / 子包目录不存在 → 一律 **STOP (rc=1)**; **顶层未知键是 WARN**(它可能正是包私有配置)。
- **`SKILL.md` 是恒定大小文档**: 不出现任何可直接执行的命令, 也不含路由表本体; 硬上限挂在
  `scripts/check_context_caps.py` 的 `CONTEXT_CAPS`(`.agents/skills/commands/SKILL.md` = **2600** 字符 ——
  2026-09-24 从 4200 收下来, **上限跟着实测收**才叫恒定大小)。
  **细节一律外置到 `references/`**(按需读, 不进每次加载): 收录协议的 how-to 在
  `references/howto-add-command.md`, SKILL.md 只留摘要 + 指针; 去掉半角逗号/斜杠/括号后的空格也是为省 token。
- **两种记法, 别混**: 文档里写 `commands run <task>`(短、给人看); 真要敲 shell 时展开成
  `python <skill-dir:commands>/scripts/run.py <子命令>` —— `commands` 本身**不是**可执行程序。
- **`pin` 是稀缺资源**: 一层视图里浮出的常显命令 > `MAX_PIN_PER_LEVEL`(8) → `list` 报 WARN。
  pin 滥用等于把平表搬回一级视图, 这是 W4 说的"层级完整性检查"里唯一没落机检的一条(2026-09-24 补上)。
- **参数不许被静默丢掉**(2026-09-24 修): 传了参数而 task 的 `run` 里没有 `<args>` → **STOP(rc=1)**
  (**脚本类例外**: 额外参数接到 argv 末尾)。起因: `run doc.drift -- --list` 的 `--list` 曾被静默丢弃。
- **SKILL.md 的 description 要突出"命令"**(2026-09-24 用户反馈"描述不清"): 首句写"要跑项目命令就来这里找",
  带两件行为(先 list 找找 / 带用户原话触发), 长度跟同族 skill(220–315), **不为压到 200 而丢触发语**;
  **不写与别的 skill 的交叉引用**。

- **包内 README 只是索引, 不是入口** (2026-09-24): 决策点文档(如 `AGENTS.md`)写 task id, 不写包内文档链接 ——
  曾把提交流程的"唯一去处"指到 `.commands/my-commit-flow/README.md`, 另一会话整读 8212 字符, 分层省下的
  token 从另一头搬回来。现 README **2808 字符**(七步表 / 停手点 / 六条反模式 / 指针表), 细节外置到包内
  `references/{pipeline,config,anti-patterns}.md`; 本环境 git 事实单点在 `pitfalls/git/_index.md`, 包内不复制。
  纪律见 `pitfalls/docs/pack-readme-entry.md`。
- **`run` 的摘要 = 末几行结论 + 异常行** (2026-09-24 噪音轮, 实测驱动): 只取末 N 行会让检查表里
  "2 项 WARN"的**内容**消失(结论行在最后, WARN 行在中段)⇒ 调用方只能把整条命令**重跑一遍**才看得到
  (代价实测: 预检跑了两次 21s×2)。异常行判据只认 `[WARN]`/`[STOP]`/`[FAIL]` 与大写 `FAILED`/`ERROR`/`Traceback`
  (小写 `warnings` 是正常输出), 封顶 8 行, 有省略时打印"略过 N 行 + `show` 怎么看全文"。
- **task id 两种写法都认** (2026-09-24): 短 id `ship.commit` 与包路径限定 `包/子包.<task>` 等价 ——
  `list` 显示短 id, 文档与人习惯写全路径, 只认一种就会在另一种"看起来对"的写法上白跑一次 STOP。
  **真实入口写进 `AGENTS.md` 命令节**(`uv run python .agents/skills/commands/scripts/run.py run <task>`):
  只有 SKILL.md 写"用 Glob 定位"时, 执行者要先花 4 次调用才能敲出第一条命令。
- **包 / 引擎的脚本测试必须挂闸门** (2026-09-24): 它们在 `testpaths(tests/)` **之外**, 不挂闸门就等于
  "改了包却无机检消费"(一条与 rebase 禁令相撞的旧文案就这样躺了很久) ⇒ 已有 task `test.pkg` +
  闸门 `match = [".commands/", ".agents/skills/commands/"]`。
- **wrapper 是入口, 不是副本** (2026-09-24 W7): `commands` 不是可执行程序, 且 **cwd 不被任何 shell 搜索**
  (实测 Git Bash / PS 都不搜, 只有 cmd.exe 搜) ⇒ 生成器**两处都写**: 仓库根(`./commands`) +
  PATH 目录(`~/bin`, **项目无关**: 从 `$PWD` 向上找 `.commands/`)。生成物**不入库**, 单点定义在
  `install_wrapper.py`; 只认自己的标记行(别人同名文件不碰, `--force` 才覆盖); 解释器优先 `uv run python`
  —— 包脚本以**引擎的 `sys.executable`** 跑, 这决定它们跑在哪个环境。细节见 `references/wrapper.md`。
- **wrapper 安装时机改按需** (2026-09-25): 「先装」→「**先试跑, command not found 才装**」—— PATH 那份
  用户级、装过就命中; 落点/幂等/自证不变。三处文档已同步 (AGENTS/SKILL/wrapper.md)。
- **低噪音包是收录的验收面** (2026-09-24 W7): 八条判据(输出自带静音 / 异常行可被机器认出 / 一条 = 一个动作 /
  `when` 一句话 / `note` 只写陷阱判据 / 长文进 `doc` / `timeout` 按最坏情况 / `pin` 稀缺)落进
  `references/howto-add-command.md` —— 包会被**反复读到**, "收进来"只是第一步。
- **落后 + 树脏的顺序: 先同步、后提交** (2026-09-24 订正): `ship.commit` **之后**再 `merge --ff-only` 是
  **不可能成功**的(本地提交不在远端 tip 的祖先链上)⇒ 包内 `references/pipeline.md` 与 README 停手点 #1
  原先都写成"先提交再快进", 已按 `AGENTS.md` 与 `pitfalls/git/history-integration.md`「先同步远端, 后提交」订正;
  开工自检新增「同步路径」行, 直接给出 5 步配方, 并**先判有没有文件重叠**(重叠时不给配方, 只报"先停下报告")。

**已验的事** (别重做):

> 早先那批(可插拔 / 反漂移红绿 / `pin` 守卫 / 格式化闸门 / `list --all` 去重 / 参数传递 / 包内 README 纳管 /
> `<each:>` 语义 / `doc` 指针基准 / W6 噪音治理)已沉淀到 [../progress/implemented-tooling.md](../progress/implemented-tooling.md)
> 「commands 引擎 / my-commit-flow 包的实测记录」一条 —— 要核对细节去那里, 别在这里堆。

- wrapper 端到端(W7): `./commands run <task>`、bare `commands list`(PATH 那份)、从子目录向上找仓库根
  —— 三种形态实测通过; 不在项目里 → rc=2 + 提示; `--uninstall` 后重装幂等。测试把这条承诺钉住:
  `test_wrapper_end_to_end_passes_args`(假仓库根 + 假引擎, 断言参数原样转发)。
- `.cmd` 三坑(实测): 必须 **CRLF** 行尾; `rem` 行含**引号/括号/反引号**会**静默退出 2 且无输出**;
  消息必须 **ASCII**(cmd 按 OEM 码页读)。CreateProcess 不认 shebang ⇒ 只能经 shell 跑。
- PATH 条目在 Git Bash 下是 **MSYS 形态**(`/c/...`), 与 `Path.home()` 直接比**永远不相等**(实测误判"不在")。

**下一步 / 未收口**:

- A11「自生长真的发生」还没判 —— 需要一次真实会话里 agent **自发**调 `add` 才算数。
- **漂移闸门的 `.exe` 归一已修**(2026-09-24), 红绿验证见上一条。
- **包内 README 的入口纪律已被机检兜住**(2026-09-24): 阅读预算 3000 字符 + 漂移闸门纳管。
  想再加第二份包内说明文档, 先想清楚它会不会被当入口。
- `check_command_drift.py` 有两条**逐文件豁免**(理由写在代码里): `pitfalls/testing/tmpdir.md`、
  `pitfalls/testing/patching.md` —— 想收紧先读那两条理由。
