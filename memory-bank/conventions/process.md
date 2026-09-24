# 流程约定 (dry_run / 幂等 / Git / 闸门)

> 摘要: dry_run 纪律、幂等与去重、Git 约定、提交闸门自动执行。
> 触发: dry_run, 幂等, 去重, Git 约定, 提交闸门

## dry_run 约定

- `dry_run` 逐层传递 (task.handler(task, dry_run) → execute(ctx.dry_run) → 各调用点)。
- 判定在**调用点**: `if not dry_run: api.xxx(...)`; QbApi Facade不感知 dry_run。
- dry-run 下动作仍返回 ActionResult (ok/skip), 但**不写** `record_execution` (条件: `not ctx.dry_run and ok_action`)。
- 分组/曲线等内置功能同样 dry_run 只打日志 (曲线 dry_run 还会跳过读当前值)。

## 幂等与去重约定 (设计原则 #1)

- 动作天然幂等: 先查后做 (标签已存在→skip, 状态相同→skip, 限速相同→skip)。
- 窗口语义 (每天一次) → `record_execution`/`get_exec_record` (state_file), 键 `{rule}:{hash}`。
- **不能**用 run_count/循环次数表达窗口语义。

## Git 约定 (观察自 git log)

- **开工前先同步分支 (2026-09-19 用户指定)**: 会话第一步必为 `git pull --rebase <远端> develop` (**分支名必须写**, 只给远端名会只 fetch 不合并), `git status -sb` 确认不落后才动手; **禁止在落后的分支上改代码**; 拉取前先把工作区弄干净 (脏工作区 + rebase 触发 stash 会损坏对象库)。细则见 `AGENTS.md`「会话协议 · 开始」与「提交 / PR」—— 该规则共有 4 处入口 (`AGENTS.md` / `.github/copilot-instructions.md` / `.agents/skills/memory-bank/SKILL.md` / `.github/instructions/ai-lib.md`), **改规则必须一次改全**, 本文件只留指针不复述。
- **push 口径单点定义在 `AGENTS.md`「提交 / PR」** (2026-09-19 起: "提交" = commit + 推送)。本文件不复述, 免得第三次漂移。
- 分支: `develop` 开发 (协作主线, 统一以 Gitee 的 `develop` 为准), `master` 主干。
- 提交信息: **格式单点定义在 `AGENTS.md`「提交 / PR」**(2026-09-22 起为 **gitmoji + 中文**: 首行 `<gitmoji> <中文一句话概述>` + 空行 + 详细描述); 本文件不复述。选 emoji 走 [gitmoji skill](../../.agents/skills/gitmoji/SKILL.md)。
- 格式化可单独成提交 ("格式化代码"/"格式化测试代码")。
- 用户未要求时不主动 commit; 要求"提交"时按 `AGENTS.md` 一次走完 (含推送)。

## 提交闸门自动执行 (2026-09-22 实施)

- **命令固定就标 `auto = true`** —— 由预检**真的执行**, 红了即 STOP(退出码 1); 只有需要人读输出做判断的才留 `auto = false`(只打印)。判据: 闸门存在的意义是不让步, 执行权留在记忆里等于没装。
- **占位符由预检展开**: `<root>` / `<skill-dir:NAME>` / `<changed:GLOB>` / `<each:GLOB>`; 展开不了即 **STOP, 不降级成打印**(降级 = "看起来跑过了")。自造占位符不会被猜。
- **未知键 / `timeout` 非法 → STOP**: 闸门很贵, 拼错键让它静默失效比报错坏得多。代价: 新增配置键必须先加进 `KEY_DEFAULTS` / `GATE_KEYS`。
- **测试跑两次, 不是一次**: ① 改完代码、**回写知识库之前** ② `commit.py` 内部提交前。第一次必须在回写之前 —— 测试带文档守卫(会读 `memory-bank/`), 回写后跑会分不清红的是代码还是文档。S6 推送前由 `push.py` 内嵌 `--no-auto` 只核状态(脏 / 上游 / 红线 / 镜像), 不跑闸门。
- **格式化类闸门必须在逐路径暂存之前**: 格式化会让已 staged 文件与 index 不一致, 必须重新 `add`。
- 字段与占位符的**机制**见 `.commands/my-commit-flow/references/config.md` 与其 `scripts/test_preflight.py`(34 用例); 本仓库的**取值**在 `.commands/my-commit-flow/.my-commit-flow.toml`; 设计取舍见 `memory-bank/plans/26-09-22-0812-commit-gate-auto-run-plan.html`。(包内 `README.md` 只是索引 —— 日常走 task id, 别整读。)
