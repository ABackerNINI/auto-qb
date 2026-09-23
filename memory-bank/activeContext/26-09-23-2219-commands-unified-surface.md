# commands — 项目命令统一调用面 (纯引擎 + 包式配置层)
> 摘要: 同一条命令仓库里有 8 处副本 / 5 种写法, 唯一生效的那条恰好"看起来最不正常" (POSIX `TMPDIR=x cmd` 前缀实测 rc=1)。方案是把 skill 缩成**纯引擎** (只认识「包」与「命令」, 连"提交"都不知道), 命令单点定义在 `<仓库根>/.commands/<包>/config.toml`, 包是**黑盒** (包私有配置引擎不读), 路由**不落盘**改为逐级查询 + `pin` 常显。**W1–W5 已全部实施**: 引擎三件 (`_config.py` / `_tree.py` / `run.py`) + 六个顶级包 (test / kb / dev / env / doc / my-commit-flow, 后者含 `ship/` 子包); `my-commit-flow` 从 skill 降为同名包 (`.commit-flow.toml` 改名 `.my-commit-flow.toml` 原样搬入), 旧 skill 已删除; 反漂移闸门 `scripts/check_command_drift.py` 把文档手抄形态判红, 63 处副本已全部收口到 0。
> 触发: 命令在哪定义, commands, .commands, 包, task id, 反漂移, 手抄命令, 收录协议, add, pin, 常显, my-commit-flow 成包, 闸门位置
> 最后活动: 2026-09-23 22:19

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

**已验的事** (别重做):

- 临时加包 → 跑通 → 整包删除, 引擎 `list` / `run` 无异常; 往包里塞引擎不认识的私有配置, 引擎不报错也读不到。
- 整包移走 `.commands/my-commit-flow` 后引擎仍能 `list` / `run` 其它 task。
- 反漂移闸门: 故意手抄 → 判红, 改成 `commands run <task>` → 转绿(63 → 0)。

**下一步 / 未收口**:

- A11「自生长真的发生」还没判 —— 需要一次真实会话里 agent **自发**调 `add` 才算数。
- 文档里的 `commands run <task>` 是**记法**, 不是可直接粘贴的 shell 命令(真实入口是
  `python <skill-dir:commands>/scripts/run.py <子命令>`); 含 task id 的代码块已把 ```bash 改成 ```text。
- `check_command_drift.py` 有两条**逐文件豁免**(都写了理由): `pitfalls/testing/tmpdir.md`(命令形态就是判据)、
  `pitfalls/testing/patching.md`(WSL 另一条执行路径)。想收紧先读那两条理由。
