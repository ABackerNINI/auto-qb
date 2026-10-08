# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把报告 `26-10-08-0231`(变异测试可行性)落成可复用流程: 指导 skill `mutation-testing`(四段流程 / 硬约束 / 标准步骤 / 三分类 / 派生计划模板) + 命令包 `.commands/mutants`(setup/run/gremlins/status) + 常驻排期锚 issue `26-10-08-0642-test-mutation-audit-standing` + 方法论坑档 `pitfalls/testing/mutation-pool-artifact.md`。全流程在 WSL 用 `infra/versioning.py` 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。**config 包首轮审计已执行完毕**(计划 26-10-08-0720): 4799 变异 / 杀 3851 / 存活 893(80.25%) → S4 全套件确认 274 条(54 假存活 + 220 真洞候选) → 补 10 守阵 → 复跑存活 **772**(−121)。档案 `tasks/26-10-08-test-mutation-audit.md`。
> 最后活动: 2026-10-08 09:02

## 已完成(详情见档案, 不在此复述)

- 指导 skill `.agents/skills/mutation-testing/SKILL.md` —— 含「派生「针对 X 的分步执行计划」」骨架(用户后续按它点名包写计划)。
- 命令包 `.commands/mutants/`: `mutants.setup` / `mutants.run` / `mutants.gremlins` / `mutants.status`; 编排在 `scripts/mutants.py`, 写 `[tool.mutmut]` 在 `scripts/set_conf.py`, 排障在包内 `references/why.md`。主仓库依赖面与环境**未动**(镜像与工具只在 WSL 侧)。
- 常驻排期锚 issue(恒 `Open`) + 方法论坑档(存活数是选择池的函数)。
- **派生计划(config)**: `plans/26-10-08-0720-plan-mutation-config.html`(状态已 `Done`)。
- **config 包首轮审计(计划 26-10-08-0720 执行)**: 目标 `**/config/*.py` · 池 = 6 个定向文件 · mutmut 3.8.0 / `--max-children 4` / WSL2 8 核。
  - 首轮 **4799 变异 / 杀 3851 / 存活 893 / `no tests` 55 / 超时 0**(杀死率 **80.25%**); S4 逐条 `apply` → 跑**全套件**确认 **274** 条 → **54 假存活 + 220 真洞候选**; 补 **10** 个守阵(红验 **18/18** 全红); 同池复跑 **杀 3972 / 存活 772**(杀死率 **82.77%**, 存活 **−121**, 新增存活 0)。
  - 基线切片 `testing/baselines/26-10-08-0902-mutants-config.md`; 真洞余量按主题入池 6 条 `test` issue(`26-10-08-0903-test-config-mutation-*`)。
  - 环境坑: WSL 登录壳实为 zsh ⇒ `$()`/`$PWD` 取错 cwd, `mutants.status` 恒报 `mutmut=no`(不影响 `mutants.run`)—— 坑档 `pitfalls/testing/mutants-wsl-shell.md` + issue `26-10-08-0758-bug-mutants-status-wsl`。
  - 收尾实测 `test.full` 全绿(覆盖率 99%, 未覆盖与 partial 各较上基线 −1)—— 数字见基线切片 `testing/baselines/26-10-08-0902-mutants-config.md`。

## 正在进行

- (无) —— config 首轮已闭环; 等下一轮(见未决项)。

## 未决项

- **config 真洞余量未逐条补测**: S4 覆盖 274 条(其中 220 条真洞候选), 复跑新杀的 121 条只覆盖了其中一部分; 余量与**未 S4 验证的 555 条候选**按模式入池 6 条主题 issue, 等排期。
- 逐包轮次: rules → hr → core **仍未派生计划**(对象优先级见可行性报告 §11); config 复跑可作为下一轮对照点(存活应 ≤ 772)。
- 常驻 issue 的认领链只有一条(本档案); 后续每轮若新增计划/档案, 记得同步 issue 的 `doc-refs`。
