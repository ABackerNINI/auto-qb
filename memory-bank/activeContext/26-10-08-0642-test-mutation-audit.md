# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把报告 `26-10-08-0231`(变异测试可行性)落成可复用流程: 指导 skill `mutation-testing`(四段流程 / 硬约束 / 标准步骤 / 三分类 / 派生计划模板) + 命令包 `.commands/mutants`(setup/run/gremlins/status) + 常驻排期锚 issue `26-10-08-0642-test-mutation-audit-standing` + 方法论坑档 `pitfalls/testing/mutation-pool-artifact.md`。全流程在 WSL 用 `infra/versioning.py` 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。档案 `tasks/26-10-08-test-mutation-audit.md`。
> 最后活动: 2026-10-08 06:42

## 已完成(详情见档案, 不在此复述)

- 指导 skill `.agents/skills/mutation-testing/SKILL.md` —— 含「派生「针对 X 的分步执行计划」」骨架(用户后续按它点名包写计划)。
- 命令包 `.commands/mutants/`: `mutants.setup` / `mutants.run` / `mutants.gremlins` / `mutants.status`; 编排在 `scripts/mutants.py`, 写 `[tool.mutmut]` 在 `scripts/set_conf.py`, 排障在包内 `references/why.md`。主仓库依赖面与环境**未动**(镜像与工具只在 WSL 侧)。
- 常驻排期锚 issue(恒 `Open`) + 方法论坑档(存活数是选择池的函数)。
- 实测: mutmut 端到端(现成镜像 `--no-refresh`)与 gremlins 端到端(Windows)都拿到汇总; `set_conf` 覆盖式重写与幂等本地实测通过。

## 正在进行

- 收尾回写: 索引重建 / 全量测试基线切片 / `.codebuddy/skills` 软链同步。

## 未决项

- `mutants.setup` 的 `git clone` 分支(需联网克隆 116MB)未在本次真跑 —— 首次真用若失败, 先核 Gitee 可达 / 镜像路径 / WSL 发行版名(包内 `references/why.md` 已列)。
- 逐包轮次(rules → hr → config → core)未开工: 等用户点名包后按 skill 的「派生计划」节出计划。
- 常驻 issue 的认领链只有一条(本档案); 后续每轮若新增计划/档案, 记得同步 issue 的 `doc-refs`。
