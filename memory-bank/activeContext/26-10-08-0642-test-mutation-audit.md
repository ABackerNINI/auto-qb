# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把报告 `26-10-08-0231`(变异测试可行性)落成可复用流程: 指导 skill `mutation-testing`(四段流程 / 硬约束 / 标准步骤 / 三分类 / 派生计划模板) + 命令包 `.commands/mutants`(setup/run/gremlins/status) + 常驻排期锚 issue `26-10-08-0642-test-mutation-audit-standing` + 方法论坑档 `pitfalls/testing/mutation-pool-artifact.md`。全流程在 WSL 用 `infra/versioning.py` 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。**config 包已跑两轮**: 首轮(计划 26-10-08-0720)4799 变异 / 杀 3851 / 存活 893(80.25%) → S4 全套件确认 274 条(54 假存活 + 220 真洞候选) → 补 10 守阵 → 复跑存活 **772**(−121, 82.77%); 第二轮(池内 `test` issue 26-10-08-0903-validator-strings)补字符串键名大小写 + `and`/`or` 短路互换守阵, 红验 **26/26**, 同池复跑存活 **653**(−119, **85.66%**)。档案 `tasks/26-10-08-test-mutation-audit.md`。
> 最后活动: 2026-10-08 10:16

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
- **config 包第二轮审计(池内 `test` issue 26-10-08-0903-validator-strings)**:
  - 只补两类变异形态守阵 —— ①字符串键名字面量大小写(`dat_path`/`download_curve`/`custom_basic_check_program_path` 等)②`and`/`or` 短路互换。涉及 6 个函数: rules 的 `_expr_gate` / `_check_rule_refs` / `_validate_trigger_action_compat` / `_validate_checking_action_spec`、sections 的 `_validate_qb_traffic`、curves 的 `_validate_global_speed_limit_curve`、core 的 `_strip_none`。
  - 新增 **6** 个测试函数(均落 `tests/test_config.py`, 同步 docstring 测试计划); 红验 **26/26** 全红(`apply` 同构变异 → 目标用例变红 → 原字节还原, 主仓 `src/` 零残留)。
  - 同池 `--no-refresh` 复跑(先 `cp` 测试进镜像): 杀 **4110** / 存活 **653** / `no tests` **36** → 杀死率 **85.66%**(存活 **772 → 653**, −119); 15 条「新增存活」经辨别为 `no tests`→`survived` **覆盖归类漂移**(非本 issue 范围、非退化)。
  - 池内 6 文件全绿(见 kb.baseline); 基线切片 `testing/baselines/26-10-08-1016-mutants-config-validator-strings.md`; 常驻锚 §07 `config/` 行与 §03 描述已同步(硬约束 12)。
  - **存量守卫违规(用户裁定不管)**: `test.full` 的 2 failed(`test_memory_bank.py::test_wording_guard_is_green_on_current_kb` / `::test_number_guard_is_green_on_current_kb`)定位为**存量**违规(`activeContext/26-10-08-0713-webui-qb-traffic-head-layout.md:15` 手抄裸 passed 数字, 来源另一会话 `0e8d5432`); `git stash` 验证与本件无关, 用户答「暂时不用管」→ 不修、不入池。

## 正在进行

- (无) —— config 第二轮已闭环; 等下一轮(见未决项)。

## 未决项

- **回灌已落地**(R3): 命令包新增 `mutants.report`(带 diff 的清单 + 汇总)与 `mutants.verify`(S4 全套件确认的机械化, ≈15s/条、可续跑); skill 补「流程约束 9–11」与两条记录纪律; 报告加 §14; 排期锚补进度/台账。下次跑任一包都应走这两条 task, 别再手工拼 S4。
- **config 真洞余量未逐条补测**: 首轮 S4 覆盖 274 条(220 条真洞候选); 第二轮(validator-strings)复跑又杀掉 119 条。余量按模式入池 6 条主题 issue, **已做 1 条**(validator-strings), 余 **5** 条等排期(`loop-guards` / `boundary-guards` / `loader-defaults` / `writer-tail` / `schema-surface`)。
- 逐包轮次: rules → hr → core **仍未派生计划**(对象优先级见可行性报告 §11); config 复跑可作为下一轮对照点(存活应 ≤ 653)。
- **存量守卫违规未处理**(用户裁定): 见上「已完成」末条; 若日后要清, 需另开会话(属 `webui-qb-traffic-head-layout` 会话产物, 非本专题范围)。
- 常驻 issue 的认领链只有一条(本档案); 后续每轮若新增计划/档案, 记得同步 issue 的 `doc-refs`。
