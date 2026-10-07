# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把报告 `26-10-08-0231`(变异测试可行性)落成可复用流程: 指导 skill `mutation-testing`(四段流程 / 硬约束 / 标准步骤 / 三分类 / 派生计划模板) + 命令包 `.commands/mutants`(setup/run/gremlins/status) + 常驻排期锚 issue `26-10-08-0642-test-mutation-audit-standing` + 方法论坑档 `pitfalls/testing/mutation-pool-artifact.md`。全流程在 WSL 用 `infra/versioning.py` 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。档案 `tasks/26-10-08-test-mutation-audit.md`。
> 最后活动: 2026-10-08 07:20

## 已完成(详情见档案, 不在此复述)

- 指导 skill `.agents/skills/mutation-testing/SKILL.md` —— 含「派生「针对 X 的分步执行计划」」骨架(用户后续按它点名包写计划)。
- 命令包 `.commands/mutants/`: `mutants.setup` / `mutants.run` / `mutants.gremlins` / `mutants.status`; 编排在 `scripts/mutants.py`, 写 `[tool.mutmut]` 在 `scripts/set_conf.py`, 排障在包内 `references/why.md`。主仓库依赖面与环境**未动**(镜像与工具只在 WSL 侧)。
- 常驻排期锚 issue(恒 `Open`) + 方法论坑档(存活数是选择池的函数)。
- 实测: mutmut 端到端(现成镜像 `--no-refresh`)与 gremlins 端到端(Windows)都拿到汇总; `set_conf` 覆盖式重写与幂等本地实测通过。
- **派生计划(config)**: `plans/26-10-08-0720-plan-mutation-config.html` —— 按 skill 的「派生计划」节写: 目标 glob `**/config/*.py`(实测覆盖顶层 + schema/ + validation/ 两子包) · 重点函数清单按「判据密度 × 出错代价」分 A/B/C 三档 · 测算基数在报告 §08 的 ≈5,000 变异锚点上**精化**(剔除 schema 四表 1,151 行纯数据声明 —— mutmut v3 只变异函数体 ⇒ 有效面 ≈3,842 行 / ≈3,800 变异 / ≈8.5 min) · 池 = 6 个定向测试文件(186 fn) · 执行步骤 S1–S7 全走 task id。已 `kb.index` 重建索引, `kb.check` / `doc.links` 全过; `test.full` 2772+4 / 99% 与上基线逐位持平(本轮零 `src/`、零 `tests/` 改动), 基线切片 `baselines/26-10-08-0727-test-mutation-audit-config-plan.md`。

## 正在进行

- (无) —— 本轮为计划派生, 未执行审计。

## 未决项

- `mutants.setup` 的 `git clone` 分支(需联网克隆 116MB)未在本次真跑 —— 首次真用若失败, 先核 Gitee 可达 / 镜像路径 / WSL 发行版名(包内 `references/why.md` 已列)。
- 逐包轮次: **config 计划已派生, 等用户拍板后按计划执行**(执行时立任务档案 + 基线切片 + 真洞各自入池); rules → hr → core 仍未派生。
- 常驻 issue 的认领链只有一条(本档案); 后续每轮若新增计划/档案, 记得同步 issue 的 `doc-refs`。
