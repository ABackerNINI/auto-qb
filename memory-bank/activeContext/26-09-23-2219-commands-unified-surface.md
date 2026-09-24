# commands — 项目命令统一调用面 (纯引擎 + 包式配置层)
> 摘要: 同一条命令仓库里有 8 处副本 / 5 种写法, 唯一生效的那条恰好"看起来最不正常" (POSIX `TMPDIR=x cmd` 前缀实测 rc=1)。方案是把 skill 缩成**纯引擎** (只认识「包」与「命令」, 连"提交"都不知道), 命令单点定义在 `<仓库根>/.commands/<包>/config.toml`, 包是**黑盒** (包私有配置引擎不读), 路由**不落盘**改为逐级查询 + `pin` 常显。**W1–W5 已全部实施**: 引擎三件 (`_config.py` / `_tree.py` / `run.py`) + 六个顶级包 (test / kb / dev / env / doc / my-commit-flow, 后者含 `ship/` 子包); `my-commit-flow` 从 skill 降为同名包 (`.commit-flow.toml` 改名 `.my-commit-flow.toml` 原样搬入), 旧 skill 已删除; 反漂移闸门 `scripts/check_command_drift.py` 把文档手抄形态判红, 63 处副本已全部收口到 0。**2026-09-24 优化轮**: SKILL.md 讲清两种记法 + description 收到 175 字符; 补 `pin` 数量守卫 (W4 声称的"层级完整性检查"里唯一缺的那条); 格式化闸门去双写 (改经引擎调 `dev.fmt`); SKILL.md 加恒定大小硬上限。
> 触发: 命令在哪定义, commands, .commands, 包, task id, 反漂移, 手抄命令, 收录协议, add, pin, 常显, my-commit-flow 成包, 闸门位置, 两种记法, 沙箱假红, skill 描述
> 最后活动: 2026-09-24 02:28

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
  并带两件行为 —— ①**先 list 找找**(别自己拼、别手抄) ②带用户原话触发("跑一下测试"/"提交"/"建索引")。
  长度跟同族 skill(220–315 字符), **不为压到 200 而丢触发语**(压到 175 反而把"命令"埋进实现细节)。
  **不写与别的 skill 的交叉引用**: 用户明确过"commands 与 scope-guard 并没有关系"。

- **包内 README 只是索引, 不是入口** (2026-09-24): 决策点文档(如 `AGENTS.md`)写 task id, 不写包内文档链接 ——
  曾把提交流程的"唯一去处"指到 `.commands/my-commit-flow/README.md`, 另一会话整读 8212 字符, 分层省下的
  token 从另一头搬回来。现 README **2808 字符**(七步表 / 停手点 / 六条反模式 / 指针表), 细节外置到包内
  `references/{pipeline,config,anti-patterns}.md`; 本环境 git 事实单点在 `pitfalls/git/_index.md`, 包内不复制。
  纪律见 `pitfalls/docs/pack-readme-entry.md`。
- **阅读预算是一类新上限** (2026-09-24): `check_context_caps.py` 里 `CONTEXT_CAPS`(IDE 注入截断)与
  `READ_BUDGET_CAPS`(被当入口就得整读)**语义不同, 分两组打印**, 判定与处置共用一套。
- **`doc` 键** (2026-09-24): `[tasks.*]` 可写 `doc = "<包内文档相对路径>"`, `show` 打印"深读"一行,
  把"想看细节读哪份"接到决策点上; 基准目录**子包继承父包**, 指向的文件不存在即 STOP(指针指空 = 静默失效)。
- **反漂移豁免不保护包内 README** (2026-09-24): `.commands/` 豁免的理由是"单点定义在这里", 但定义处是
  `config.toml` —— 故 `path.name == "README.md"` 时不走豁免, 并加进 `SCAN_GLOBS`。

**已验的事** (别重做):

- 临时加包 → 跑通 → 整包删除, 引擎 `list` / `run` 无异常; 往包里塞引擎不认识的私有配置, 引擎不报错也读不到。
- 整包移走 `.commands/my-commit-flow` 后引擎仍能 `list` / `run` 其它 task。
- 反漂移闸门: 故意手抄 → 判红, 改成 `commands run <task>` → 转绿(63 → 0)。
- `pin` 守卫: 临时树里 3 条 pin 不报、9 条 pin 报(一级与子包两层都试过)。
- 格式化闸门去双写: 预检 `<changed:*.py>` → `run.py run dev.fmt -- <文件...>` → 引擎再展开成 `yapf -i <文件...>`,
  两段都实测过, 与旧闸门等价(仍只碰本次改过的 py)。
- `list --all` 去重(2026-09-24 修): 曾把常显命令打两遍(21 条显示成 25 行, 看着像 task id 重复 —— 而重复正是
  引擎的 STOP 判据)。改为 `--all` 时不再上浮 pin。逐视图复验: `--all` 21 行零重复; `list` 3 / `kb` 3 / `test` 3 /
  `my-commit-flow` 4 / `ship` 2 / `my-commit-flow --all` 5 —— 无重复、无缺失。
- 反漂移闸门扫描面扩到 `.agents/skills/**/*.md`(2026-09-24, 原为 `**/SKILL.md`): 细节搬进 `references/`
  后只扫 SKILL.md 会给搬出去的内容留盲区。扩之前先跑过一遍**实测 0 命中**(不误伤别的 skill)。
- 参数传递(2026-09-24): `run doc.drift -- --list` 转发成功(引擎只回末 3 行摘要 —— 要全文用 `show` 看命令再自己跑);
  `run doc.caps -- --strict` **STOP rc=1 且不执行**; 脚本类 `ship.commit -- --message-file … <路径>` 仍接到 argv 末尾;
  无参数时路径不变(`show test.full` 逐字一致)。
- 包内 README 纳管 + 骨架 `.exe` 归一后的漂移闸门 (2026-09-24): 手抄 `run` 类命令 → 判红(指出应改成
  `commands run doc.links`); 手抄脚本类(`<包>/scripts/preflight.py --check-started` 带解释器前缀)原先判不出
  (引擎用 `sys.executable` 拼命令, 首 token 是 `python.exe`), 归一后同样判红; 删掉 → 转绿, 全仓无新增误伤。
- `<each:>` / `<changed:>` 只盯**本次改动清单**, 不是文件系统 glob (2026-09-24 澄清): 没匹配上的 WARN 是
  **按设计跳过**, 不是闸门失效 —— 我一度误读成"对 `.commands/**` 静默失效", 实测展开正常。WARN 文案已点明。
- `doc` 指针 (2026-09-24): 子包里写 `doc = "references/pipeline.md"` 若按子包目录解析会 STOP
  (文件在父包), 故改为**基准继承父包**; 5 个 task 的 `show` 均打印出父包那份绝对路径。

**下一步 / 未收口**:

- A11「自生长真的发生」还没判 —— 需要一次真实会话里 agent **自发**调 `add` 才算数。
- **漂移闸门的 `.exe` 归一已修**(2026-09-24), 红绿验证见上一条。
- **包内 README 的入口纪律已被机检兜住**(2026-09-24): 阅读预算 3000 字符 + 漂移闸门纳管。
  想再加第二份包内说明文档, 先想清楚它会不会被当入口。
- `check_command_drift.py` 有两条**逐文件豁免**(都写了理由): `pitfalls/testing/tmpdir.md`(命令形态就是判据)、
  `pitfalls/testing/patching.md`(WSL 另一条执行路径)。想收紧先读那两条理由。
- **W3 遗留的文档漂移已修**(2026-09-24)—— 明细已迁出到 `progress/implemented-tooling.md`。
