# 26-10-08-test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

**Status:** In Progress
**Added:** 2026-10-08
**Updated:** 2026-10-08
**Summary:** 把「变异测试定期审计」从一次可行性调研落成可复用的流程: 指导 skill(mutation-testing) + 命令包(mutants: setup/run/gremlins/status) + 常驻排期锚 issue + 方法论坑档; 全流程在 WSL 用 infra/versioning.py 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。后续按包派生计划逐轮推进。**config 包首轮已执行**(计划 26-10-08-0720): 4799 变异 / 杀 3851 / 存活 893(杀死率 80.25%); S4 全套件逐条确认 274 条 → 54 假存活 + 220 真洞候选; 补 10 个守阵后同池复跑存活 **772**(−121, 新增存活 0), 杀死率 **82.77%**。 **R3 回灌**: 按首轮经验给命令包补 `mutants.report` / `mutants.verify`, 给 skill 补流程约束 9–11 与两条记录纪律, 给排期锚补进度与台账。 **R4**: 常驻锚新增 §07「覆盖进度总表」(包/上次测试日期/变异数/杀死率/轮次/状态/相关 task 文档), 并把「每轮实施完成后必更该表」写成 skill 硬约束 12 与专节, 同步进报告与命令包深读。 **R5**: 修 issue 26-10-08-0758(mutants.status 在 WSL 下恒报 mutmut=no, 回显改 `cd X && cmd` 直连)。 **R6 config 第二轮**(池内 `test` issue 26-10-08-0903-validator-strings): 补字符串键名大小写 + `and`/`or` 短路互换守阵, 红验 **26/26** 全红, 同池 `--no-refresh` 复跑存活 **772 → 653**(−119), 杀死率 **85.66%**。 **R7 config 第三轮**(池内 `test` issue 26-10-08-0903-writer-tail): 对 writer.py 的 74 条 S4 候选重判(先修被污染的 S4 判据 —— 镜像池 + 两条读源码文本守卫在基线就红, 74 条被伪杀成零), 排除既有红守卫后得有效判据 **71 真洞 / 3 假存活**; 补 **22 守阵**后复跑同 74 条 → **51 KILLED / 23 SURVIVED**(存活 −48), 余 22 条验证为等价变异、1 条真洞当场杀死; **零 src 改动**。
**Refs:** memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html, memory-bank/pitfalls/testing/mutation-pool-artifact.md, memory-bank/pitfalls/testing/mutants-wsl-shell.md, memory-bank/pitfalls/testing/read-source-static-guard-mutation.md, memory-bank/testing/baselines/26-10-08-0647-test-mutation-audit.md, memory-bank/testing/baselines/26-10-08-0727-test-mutation-audit-config-plan.md, memory-bank/testing/baselines/26-10-08-0902-mutants-config.md, memory-bank/testing/baselines/26-10-08-0958-mutants-status-wsl.md, memory-bank/testing/baselines/26-10-08-1016-mutants-config-validator-strings.md, memory-bank/testing/baselines/26-10-08-1144-mutants-config-writer-tail.md, memory-bank/testing/baselines/26-10-08-1229-mutants-config-schema-surface.md, memory-bank/issues/26-10-08-0758-bug-mutants-status-wsl.html, memory-bank/issues/26-10-08-0903-test-config-mutation-loop-guards.html, memory-bank/issues/26-10-08-0903-test-config-mutation-boundary-guards.html, memory-bank/issues/26-10-08-0903-test-config-mutation-loader-defaults.html, memory-bank/issues/26-10-08-0903-test-config-mutation-writer-tail.html, memory-bank/issues/26-10-08-0903-test-config-mutation-schema-surface.html, memory-bank/issues/26-10-08-0903-test-config-mutation-validator-strings.html, memory-bank/testing/baselines/26-10-08-0920-mutation-audit-tooling.md, memory-bank/testing/baselines/26-10-08-0939-mutation-audit-standing-table.md
**Topics:** mutation-audit

## 原始请求

用户: 根据可行性报告 `memory-bank/reports/26-10-08-0231-report-mutation-testing-feasibility.html` 写一份详细指导, 后续流程是「开一个永远 open 的 issue, 由人工定期执行, 可以是测试全部的代码, 也可以是部分代码」; 把常用命令加入 commands 包; 后续通过该指导派生计划(例: 「根据 xx 指导文档写一个针对 config 部分的分步执行计划」)。要求: **优化该初步设想**, 然后写指导与 issue。

## 思考过程与决策

- **四段职责拆分(对初步设想的优化)**: 原设想把「永远 open 的 issue」当唯一载体, 但那样它会同时承担排期、流水、真洞三件事, 与既有工位约定(每条事实只在一个工位有权威)冲突。改成四段: ①排期锚=常驻 issue(恒 Open) ②派生计划=`plans/`(一次盯一个包) ③执行=`mutants` 包 ④记录=基线切片 + 任务档案 + 真洞各自 issue。轮次流水从 issue 里挪出去 —— issue 只留一行指针。
- **指导的形态 = skill 而非 memory-bank 文档**: 它要「指导 agent 做事 / 写计划」, 这正是 `.agents/skills/` 的用途(同族: `test-gap-audit` / `commands` / `memory-bank`)。证据与实测数字仍留在报告里(skill 只引不复述, 防漂移)。配套在 `.codebuddy/skills/` 建软链(`scripts/sync_agent_skills.py`, 该目录 gitignore)。
- **命令单点成独立包 `mutants`(而非并进 `test`)**: 一轮 mutmut 是六步编排(刷新镜像 → sync → 装工具 → 清缓存 → 写 `[tool.mutmut]` → 跑 → 取结果), 每步都有「看着正常但不生效」的写法; 收进 `scripts/mutants.py` 比往 `test` 包里塞 WSL 编排干净。镜像与工具**只在 WSL 侧**, 主仓库 pyproject/.venv 一律不动(报告 §01 的沙箱纪律)。
- **结果落 `R:/Temp/auto-qb/mutants` 且只回显头部**: 存活清单可能上千行(超 AI 工具壳 30KB 内联上限), 全量落盘 + 头部回显是「搬走」不是「藏起来」; 落仓内会撞报告 §10 #7 那类坑。
- **常驻 issue 不设 In Progress**: 认领链要求认领方反向声明, 但本件语义是「只要审计在做就 Open」; 认领方(本档案)照常反向声明, 状态词仍留 `Open`(停做才 `Dropped`)。这是对 5 词表的**刻意用法**, 不是漏改。
- **不写进 pyproject**: mutmut / pytest-gremlins 不进主仓库依赖面(gremlins 走 `uv run --with`, mutmut 走镜像 venv 的 `uv pip install`)。理由: 报告 §01 明确「主仓库环境未被修改」是那轮调研的前提, 且 mutmut 在 Windows 原生被硬拒。

### 2026-10-08 R4 — 常驻锚加「覆盖进度总表」+ 约束进 skill / 相关文档

- **触发**: 用户「在变异测试长青 issue 中加一个表格(各部分测试 / 上次测试日期 / 上次测试相关 task 文档等), 每次变异测试实施完成后同步更新该表格; 将该约束加入 skill 以及相关文档; 先建表格骨架, 然后加约束」。
- **表格骨架**: 常驻锚 `issues/26-10-08-0642-…html` 原 §07 轮次台账**顺延为 §08**, 新插入 **§07 覆盖进度总表** —— 列 = 包/模块 · 上次测试日期 · 变异数 · 杀死率 · 编号/轮次 · 状态 · 基线切片/计划/任务档案; 已按现有事实填 `config/`(R2)、`infra/versioning.py`(R0)两行, `rules/` `hr/` `core/` `infra/`+`webui/server/` 留 `待做` 占位行。原 §08 状态日志顺延为 §09, 并记一条本次变更。
- **约束(硬约束 12 + 专节)写进 skill** `.agents/skills/mutation-testing/SKILL.md`:
  - 流程约束列表 3 条 → **4 条**, 新增第 12 条「每轮实施完成后同步更新常驻锚 §07 覆盖进度总表」;
  - 新增专节「覆盖进度总表(收尾必更)」—— 列口径 / 更新时机 / 三步更新内容 / 为什么不违反「issue 不记流水」(只放汇总刻度 + 指针) / 收尾口径自查;
  - 标准步骤由 8 步 → **9 步**, 第 9 步即更新该表(**不更视为该轮未收尾**);
  - 四段职责表「4 记录」落点补 `issues/` 锚 §07; 「issue 不记流水」那条加例外说明; 派生计划 §S8/§验收补该表; 反模式补 1 条。
- **相关文档同步**:
  - 证据报告 `reports/26-10-08-0231-…html` §14「三条流程修正」→ **四条**(新增「每轮实施后同步常驻锚覆盖进度总表」), §15 变更记录补 26-10-08-0935 一行, 抬 `doc-updated`;
  - 命令包深读 `.commands/mutants/references/why.md` 新增「跑完之后: 数字要落到哪几处」小节(四落点表 + 两处勿混警告)。
- **口径自查**: 表中两个「已做」行均有切片链接、日期/变异数/杀死率与切片逐位一致; 表内无 `N passed`(不触回写守卫判据族 B)。
- **收尾实测**: `commands run test.full` → **2785 passed + 4 skipped / 覆盖率 99%**(与上基线 26-10-08-0920 逐位持平, 本轮零 `src/`、零 `tests/` 改动); `kb.index`(20 生成物) / `kb.check`(主键 / 认领链 / 回写 / 日期全过) / `doc.links` / `doc.drift`(0 处) / `doc.caps`(无新增债务) 全过。基线切片 [26-10-08-0939](../testing/baselines/26-10-08-0939-mutation-audit-standing-table.md)。
- **未做**: 未 commit/push(用户未说「提交」)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 读报告 + 摸清 `commands` 引擎 schema / issue 生成器 / 认领链协议 | Done |
| S1 | 指导 skill: `.agents/skills/mutation-testing/SKILL.md`(四段流程 / 硬约束 / 命令 / 标准步骤 / 三分类 / 记录口径 / 派生计划模板 / 坑 / 反模式) | Done |
| S2 | 命令包 `.commands/mutants/`: `config.toml`(4 task) + `scripts/mutants.py`(编排) + `scripts/set_conf.py`(写 `[tool.mutmut]`) + `references/why.md` | Done |
| S3 | 实测验证: mutmut 端到端 + gremlins 端到端 + `set_conf` 幂等/覆盖 + 守卫 | Done |
| S4 | 常驻 issue + 方法论坑档 | Done |
| S5 | 收尾: 本档案 + activeContext 切片 + `kb.index` + `test.full` 基线切片 + skills 软链 | In Progress |
| S6 | 派生计划(config): `plans/26-10-08-0720-plan-mutation-config.html`(按 skill 骨架; 用户点名 config) | Done |
| S7+ | 执行审计轮次: 按计划跑 + 三分类 + 手工确认 + 真洞入池(rules → hr → core 计划仍未派生) | Open |
| S8 | config 第二轮: 池内 `test` issue 26-10-08-0903-validator-strings(字符串键名 + 短路运算符) | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| S1 指导 skill | Done | `.agents/skills/mutation-testing/SKILL.md`; 含「派生「针对 X 的分步执行计划」」骨架 |
| S2 命令包 | Done | `mutants.setup` / `mutants.run` / `mutants.gremlins` / `mutants.status` |
| S3 实测 | Done | 见下「进度日志」R0; `set_conf` 覆盖式重写与幂等本地实测通过 |
| S4 issue + 坑档 | Done | issue `26-10-08-0642-test-mutation-audit-standing`(常驻) + `pitfalls/testing/mutation-pool-artifact.md` |
| S5 收尾 | Done | 索引 / 基线 / 软链 |
| S6+ 逐包轮次 | In Progress | config **两轮已执行**(计划 `26-10-08-0720`): 首轮见 R2、第二轮见 R6(validator-strings, 85.66%); 池内 6 条 `test` issue 余 5 条待做; rules/hr/core 计划仍未派生 |

## 进度日志

### 2026-10-08 R0 — 建立(指导 / 命令 / 排期锚)

- **环境摸清**: WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限), 已有调研沙箱 `~/mut-wsl`(ext4, 含 venv + mutmut 3.8.0 + 旧 `mutants/` 残留)。`uv 0.12.14`; 仓库 origin = Gitee, 分支 `develop`。
- **端到端实测(mutmut, 用现成镜像 `--no-refresh`)**:
  - `infra/versioning.py` + `tests/test_versioning.py` → **155 变异 / 21.6s / 杀 147**(存活 7 + 超时 1), 8.25 mut/s。
  - 与报告 §07 的 155 变异一致(密度复核通过)。
- **端到端实测(gremlins, Windows)**: `uv run --with pytest-gremlins==1.11.2 pytest tests/test_versioning.py --gremlins --gremlin-targets=src/auto_qb/infra/versioning.py -n 0 --no-cov --gremlin-workers=8` → **25 变异 / 100% 杀 / 11.9s**。确认 `uv run --with` 路线可行(不动主仓库依赖)。
- **踩到并当场处置的坑**(已内建进脚本, 并写进包内 `references/why.md`):
  - **旧 `mutants/` 缓存让 mutmut「0 files mutated」提前收工**(目标从 `rules/` 换成 `infra/versioning.py` 时复现) → `mutants.run` 每次 `rm -rf mutants mutmut-cache.db`。
  - **Git Bash 把未加引号的 `~` 展开成 `C:/Users/...`**, 再进 WSL 是个错路径且不报错 → 加 `check_mirror()` 停手 + 提示加引号(走 `commands run` 时 cmd.exe 不展开 `~`, 不受影响)。
  - **deselect 表已漂移**: 报告写的 `tests/test_web.py::test_api_enqueue_wakes_main_loop` 因 test_web 拆分已不存在, 现址 `tests/test_web_seed_center.py`(2026-10-08 06:36 取证) → 写进 `set_conf.py` 的 `DEFAULT_DESELECT` 并在包内文档标注「会随拆分漂移」。
- **产物**: skill `mutation-testing`; 包 `mutants`(4 task, `commands list` 可见); issue `26-10-08-0642-test-mutation-audit-standing`(Open, 常驻); 坑档 `pitfalls/testing/mutation-pool-artifact.md`。
- **未验到**: `mutants.setup` 的 `git clone` 分支(需联网克隆 116MB)、`--out` 之外的路径 —— 已在包内 `references/why.md`「本会话验证到哪一步」如实标注。
- **收尾实测**: `commands run test.full` → **2772 passed + 4 skipped / 54.75s / TOTAL 99%**(16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial), 与上基线逐位持平(`src/` 与 `tests/` 零改动); `commands run test.pkg` → **154 passed / 115.35s**(新包脚本不进收集面, 未破坏包脚本测试面)。基线切片 `testing/baselines/26-10-08-0647-test-mutation-audit.md`。
- **索引与守卫**: `kb.index` 20 个生成物; `kb.check` 主键纪律 / 认领链 / 回写措辞 / 日期守卫**全过**; `doc.links` 无坏链。
- **skills 软链**: `scripts/sync_agent_skills.py` 建 `.codebuddy/skills/mutation-testing`(该目录 gitignore)时 `mklink /J` 返回失败(脚本打 `!`), 改用 PowerShell `New-Item -ItemType Junction` 建成 —— 疑与本工具 shell 的路径处理有关, 未确认为仓库缺陷, 记一笔待复现。
- **cap 债务(不拦提交, 转告用户另开会话清理)**: `issues/_index.md` 25,430 与 `tasks/_index.md` 25,551 均略超 25,200(两条在本轮前已越线, 本轮各加一行 ~200–250 字符); 另有存量 `tasks/26-10-08-backend-test-web-split.md` 62,661 > 48,000; 以及 activeContext 切片数 95 > 70。

### 2026-10-08 R1 — 派生 config 计划(未执行)

- **触发**: 用户「根据变异测试指导写一个针对 config 部分的分步执行计划」—— 即 skill「派生计划」节的第一个用例(档案 §原始请求 里预告的形态)。
- **产物**: `memory-bank/plans/26-10-08-0720-plan-mutation-config.html`(单文件 HTML, dark, `doc-topic=mutation-audit`, 状态 `Open` 待拍板)。
- **计划要点(按 skill 骨架逐节落到 config 上)**:
  - 目标 glob `**/config/*.py` —— 用 fnmatch 实测覆盖顶层 + `schema/` + `validation/` 两子包, 且不误伤 `webui/server/routes/config.py`; 明确不写 `**/config/**/*.py`(会漏顶层 8 文件)。
  - 重点函数清单按「判据密度 × 出错代价」分三档: A 校验内核(`validation/core.py` 的 `_try_number`/`_try_time`/`validate_config` 等 + sections/rules/curves) · B 迁移与写回(`migrations.py` 三个迁移 + `writer.py` 回退/版本闸) · C 加载与派生(loaders/fields/impact)。
  - 测算基数**在报告 §08 锚点上精化**: 报告按全行估 config/ ≈5,000 变异 / ≈11 min; 计划剔除 schema 四表(groups/hr/rules/trackers, 实测 1,151 行 0 函数)后有效面 ≈3,842 行 ⇒ ≈3,800 变异 / ≈8.5 min(依据: mutmut v3 只变异函数体, 报告 §03)。首轮一律以实测为准。
  - 池 = 6 个定向测试文件 / 186 fn: `test_config.py`(62) · `test_config_writer.py`(54) · `test_hr_config.py`(33) · `test_config_schema.py`(24) · `test_impact.py`(8) · `test_config_key_surface.py`(5)。核实池内无「读源码文本」守阵 ⇒ 默认 `--deselect` 与本轮无关(保留无副作用)。
  - 步骤 S1–S7 全走 task id(`mutants.setup` → `mutants.run` → 三分类 → 手工确认 → 补测 → 复跑 → 记录); 附 Windows 兜底 `mutants.gremlins`。
- **收尾**: `kb.index` 重建 20 个生成物(计划已进 `plans/_index.md`); `kb.check`(主键 / 认领链 / 回写措辞 / 日期守卫)与 `doc.links` 全过; `doc.caps` 无新增债务(3 项均为存量)。`test.full` → **2772 passed + 4 skipped / 54.25s / TOTAL 99%**(16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial), 与上基线 `26-10-08-0647` 逐位持平(本轮零 `src/`、零 `tests/` 改动); 基线切片 `testing/baselines/26-10-08-0727-test-mutation-audit-config-plan.md`。
- **未做**: 未执行审计(计划边界: 不在计划里实施); 未 commit/push(用户未说「提交」)。

### 2026-10-08 R2 — config 包首轮审计(执行计划 26-10-08-0720)

- **触发**: 用户「实施计划: 26-10-08-0720-plan-mutation-config.html」。
- **S1–S2 首轮(mutmut / WSL)**: 目标 `**/config/*.py`(回显 `19 files mutated, 109 ignored`), 池 = 6 个定向文件。
  - 变异 **4799** · 杀 **3851** · 存活 **893** · `no tests` **55** · 超时 **0** → 杀死率 **80.25%**; 墙时 294.4s(含 setup), 变异阶段 17.41 变异/s; mutmut 3.8.0 · `--max-children 4` · WSL2 8 核。
  - 与计划测算对照: 计划精化估 ≈3,800(剔除 schema 纯数据表)、报告全行估 ≈5,000 —— 实测 **4799** 落在两口径之间, 属 §2.2 预告的正常区, 无需复核 glob。
- **S3 三分类**: 893 存活 + 55 no-tests 全量落盘(`R:/Temp/auto-qb/mutants/26-10-08-0742-config-py-results.txt`)并按类聚合; 机器规则先筛出 **64** 条等价(错误文案 / `open` 编码变体 / 纯展示格式), 余 **829** 条进候选。`no tests` 55 条**全部**在 `validation/rules.py` 的 `_validate_watch_fields`(36) 与 `_validate_expr_condition_spec`(19) —— 池内 6 个文件不覆盖规则条件校验, 属**池边界**而非代码缺口。
- **S4 手工确认(唯一判据 = 全套件下同构变异)**: 对 **274** 条候选逐条 `mutmut apply` → 跑**全套件**(`-n 8 --no-cov -x -p no:cacheprovider`)→ 还原(`git checkout -- src/`), 结果:
  - **54 条假存活**(全套件能杀 ⇒ 池没选到): `validate_config` 15 · `_validate_qb_traffic` 10 · `_expr_gate` 6 · `_validate_global_speed_limit_curve` 5 · `_validate_trigger_action_compat` 5 · `_current_main_tick` 3 · `_prepare` 2 …
  - **220 条真洞候选**(全套件仍杀不掉): writer 74 · sections 45 · schema/__init__ 27 · core 25 · loaders 16 · rules 11 · migrations 10 · curves 9 · site_presets 2 · impact 1。
  - 覆盖口径: 优先文件(impact / migrations / site_presets / writer / validation.core / schema.__init__)全量 + 其余文件的 `continue/break`·边界·`and/or`·语句删除类; **未覆盖的 555 条**按模式分类, 留待下轮(不在本轮声称真洞)。
  - 耗时: 274 条 × ≈15s ≈ 68min(全套件 12s + 开销)。
- **S5 补测(只对确认的真洞)**: 新增 **10** 个测试函数(全部落在池内文件, 同步各文件 docstring 的「## 测试计划」), 覆盖: impact diff 并集语义 · v1→v2 多 tracker 迁移 · 显式置空收集多条目 · 掩码还原遍历 · 物化缺文件返回 · `_check_str_list`/`_try_number` 拦截侧 · `state_file` 空白 · max_tasks 下界 · qb_traffic×main_tick 交叉 · 闭区间端点逐值 · fs 多条目 · 站点绑定多条目。
  - **红验 18/18 全红**(apply 同构变异 → 目标用例变红 → 还原复绿, 主仓 `src/` 零残留)。
- **S6 复跑(同目标同池 + 补测)**: 变异 **4799** · 杀 **3972** · 存活 **772** · `no tests` **55** → 杀死率 **82.77%**; 墙时 3m46s / 22.67 变异/s。
  - **存活 −121 / 新增存活 0**(逐 id 对差; 被新守阵杀死者按文件: sections 74 · core 23 · migrations 7 · curves 7 · loaders 6 · writer 3 · impact 1)。验收 #3 达标(**772 ≤ 893**)。
- **S7 记录**: 基线切片 `testing/baselines/26-10-08-0902-mutants-config.md`; 真洞余量按**主题**入池 **6 条** `test` issue(`26-10-08-0903-test-config-mutation-{loop-guards,boundary-guards,loader-defaults,writer-tail,schema-surface,validator-strings}`); 环境坑入池 `26-10-08-0758-bug-mutants-status-wsl` + 坑档 `pitfalls/testing/mutants-wsl-shell.md`。
- **环境坑(本机)**: WSL 登录壳实为 zsh —— `cd X` 改真实 cwd, 但 `$PWD` 与 `$()` 仍报 WSL 启动目录 ⇒ `mutants.status` 恒报 `mutmut=no`(实际已装; **不影响 `mutants.run`**)。排障耗时约 30min。详见坑档。
- **收尾实测**: `commands run test.full` 全绿(覆盖率 99%, 未覆盖与 partial 各较上基线 −1)—— 数字见基线切片 [26-10-08-0902](../testing/baselines/26-10-08-0902-mutants-config.md)。
- **未做 / 遗留**: 220 条真洞候选中, 复跑新杀的 121 条覆盖了其中一部分(其余落在未 S4 验证的 555 条里), **余量未逐条补测**(按主题入池等排期); 未 commit/push(用户未说「提交」)。


### 2026-10-08 R3 — 按首轮经验回灌指导 / 命令包 / 排期锚

- **触发**: 用户「根据此次实施过程更新变异测试指导文档 + 相关 skill + 命令包和常驻排期锚(主要提交 637be05f), 使下次实施能更顺利」。
- **命令包(新增 2 个 task + 1 个脚本)**:
  - `mutants.report` —— 把镜像里上一轮的存活/未覆盖变异导出成**带 diff 的清单** + 按状态/按模块汇总。**为什么必须**: `mutmut results` 只回 `id: status`, 既没有文件:行也没有变异内容, 光看它做不了三分类。
  - `mutants.verify` —— S4「全套件确认」的机械化: 逐条 `mutmut apply` → 跑**全套件** → 还原, 记 KILLED(假存活) / SURVIVED(真洞候选); **幂等可续跑**(已写进结果文件的 id 跳过)。首轮这一步是手工脚本 + 手工解析, 耗时 ≈68min。
  - `scripts/mutants_dump.py` —— 在镜像里跑(读 `mutants/<路径>.meta` 的 `exit_code_by_key`, 用 `diff_apply` 现场重放每条变异)。配套在 `mutants.py` 加 `_wsl_write`(**内容走 stdin** —— 多行内容塞进 `bash -lc '<script>'` 会被登录壳按行拆开, 实测会静默落到别处)。
  - 实测: `report` 导出 827 条(16.4s); `verify` 2 条 smoke = **14s/条**, KILLED/SURVIVED 判定正确。
- **指导 skill(`.agents/skills/mutation-testing/SKILL.md`)**:
  - 命令表补 2 个 task; 标准步骤 S3 改走 `mutants.report`、S4 改走 `mutants.verify`、S6 注明 `--no-refresh`。
  - 硬约束新增**流程约束 9–11**(脚本没法内建的那三条): 池要覆盖目标包的**函数面**(否则成片 `no tests`) · S4 主动收窄候选(≈15s/条) · 复跑带新守阵必须 `--no-refresh`。
  - 记录口径补**两条机械守卫**: 切片之外不手抄 `N passed`(回写守卫判据族 B) · 新 issue 填 `doc-refs`(认领链)。
  - 派生计划 §2 修正测算口径(**别**剔除「纯数据声明」行 —— config 实测 4,799 比精化 3,800 高 26%)。
  - 坑补「本机 WSL 登录壳是 zsh」与「结果怎么读」两条指针; 反模式补 4 条。
- **证据报告(§14 新增)**: `reports/26-10-08-0231-…html` 加「config 包首轮实测」节(数字 + 三条流程修正 + 假存活比例 19.7%), 变更记录顺延为 §15, 抬 `doc-updated`。
- **常驻排期锚**: §03 标注 config 首轮进度与数字; §04 命令表补 2 个 task; §05 标准动作改走 task id; §07 台账补 R1/R2; §08 记一条「回灌经验」(状态仍 `Open`)。
- **收尾实测**: `test.pkg` 全绿(154 条, 与上基线同批); `test.full` 见基线切片 [26-10-08-0920](../testing/baselines/26-10-08-0920-mutation-audit-tooling.md); `doc.drift` 0 处手抄; `kb.check` 全过; `doc.caps` 无新增债务。
- **未做**: 未 commit/push(用户未说「提交」)。

### 2026-10-08 R5 — 修 issue 26-10-08-0758(mutants.status WSL 失真)

- **触发**: 用户「认领并修复: 26-10-08-0758-bug-mutants-status-wsl.html」。
- **复验(防过期原则第 5 条)**: 2026-10-08 09:50 在 WSL `Ubuntu-26.04` 重跑锚点三条对照 —— `$0=/usr/bin/zsh`; `cd "$HOME/auto-qb-mut"; echo "$(pwd)"` → `/mnt/d/Projects/auto-qb-clone5`(启动目录); `cd … && test -x .venv/bin/mutmut && echo yes` → `yes`。**现象仍复现**。
- **根因闭合**: 登录壳 zsh 的 `$PWD` / 内建 `pwd` / 相对路径解析走**逻辑目录**, `cd` 未同步逻辑 PWD ⇒ `$()` 子壳按启动目录解析。修复前 `commands run mutants.status` 实测 `mutmut=no` / `mutants=`(空)/ `head=f8f9d9b0`(= 主仓 HEAD, 非镜像的 `6214c4f3` —— 又一处同源失真)。
- **修法**(采纳 issue 建议第 1 项): `.commands/mutants/scripts/mutants.py` 的 `cmd_status` 四条回显改 `cd {mq} && <直接命令>` 形态(与 `cmd_run` 一致), 单次 wsl 调用内并列多条, 保持一屏回显。绝对路径方案未采纳(改动面更大)。**附带闭合**: 原末行 `test -f pyproject.toml && grep -m1 only_mutate …` 在镜像未跑过 `run` 时回非零 ⇒ 只读回显却报 `[FAIL]`; 改 `|| echo 'only_mutate = (未写, 先跑一轮 run)'` 兜底, 实测恢复 `[ok]`。
- **验证**: 修复后同命令实测 `mutmut=yes` / `mutants=87M` / `head=6214c4f3`(与 `git -C <mirror> rev-parse` 现查一致)/ `not_killed=827`, 退出码 0(`[ok]`)。三条失真行全部恢复; `run`/`setup`/`report`/`verify` 未受影响(全程 `cd X && cmd`, 本轮未改)。
- **回写**: issue 置 `Done`(封面徽标 + `issue-status` meta 两处 + 状态日志 + 复验行 + 修复后补充); 坑档 `pitfalls/testing/mutants-wsl-shell.md` 标注「工具侧已修」; 包内 `references/why.md` 排障表该条改「已修」、诚实交代节更新; skill `mutation-testing` 的坑条同步。
- **收尾实测**: `commands run test.full` 覆盖口径与上基线逐位持平(见基线切片 [26-10-08-0958](../testing/baselines/26-10-08-0958-mutants-status-wsl.md)); `kb.index` 20 生成物 / `kb.check` 主键与认领链全过 / `doc.drift` 0 处 / `doc.links` 过。存量红 2 项(无关文件 `activeContext/26-10-08-0713` 的裸 passed 数字, 已 stash 回退验证与本轮无关)与存量 cap 债务 3 项未动(范围守恒)。
- **未做**: 未 commit/push(用户未说「提交」)。

### 2026-10-08 R6 — config 第二轮: 校验器字符串键名 + 短路运算符(issue 26-10-08-0903-validator-strings)

- **触发**: 用户「认领并实施: `memory-bank/issues/26-10-08-0903-test-config-mutation-validator-strings.html`」—— 即首轮入池 6 条 `test` issue 中的第八条(validator-strings)。
- **范围**: 只补两类变异形态的守阵 —— ①**字符串键名字面量大小写**(`dat_path`→`DAT_PATH` · `download_curve`→`DOWNLOAD_CURVE` · `custom_basic_check_program_path`→大写)②**`and`/`or` 短路互换**。涉及 6 个函数: rules 的 `_expr_gate` / `_check_rule_refs` / `_validate_trigger_action_compat` / `_validate_checking_action_spec`, sections 的 `_validate_qb_traffic`, curves 的 `_validate_global_speed_limit_curve`, core 的 `_strip_none`。
- **补测(S5)**: 新增 **6** 个测试函数(均落在池内 `tests/test_config.py`, 同步该文件 docstring 的「## 测试计划」):
  - `test_validate_string_keys_exact_case` —— 键名大小写不符须落到「未知键」而非被静默接收(经 expr 门控间接断言 `dat_path`; period/download_curve/custom_basic_check_program_path 直接断言)。
  - `test_validate_short_circuit_pairs_differing_truth` —— 逐条构造「两操作数取不同真值」的输入击穿 `and`/`or` 互换(traffic_source 空列表 vs 非 list · curves 项单键判定 · group_spec 非 dict 但含 rule_name 子串 · 触发非 dict 单元素 list action · 空引用 `"@"`)。
  - `test_strip_none_list_branch_and_key_case` —— 列表分支去空 + 列表内嵌 dict 的 tri_state 叶豁免 + 键名大小写对照。
  - `test_validate_rule_refs_single_char_and_short_circuit` —— 钉 `r[1:]`(单字符引用须报「引用的规则集不存在」而不是「必须以 @ 开头」)。
  - `test_validate_qb_traffic_positive_boundary` —— 钉 `seconds <= 0`(0S 报正时间; 1S 落到 main_tick 下界而**不**报正时间)。
  - `test_validate_gslc_interval_key_exact` —— 钉 `interval` 精确键名与正值判定。
- **红验 26/26 KILLED**: 用 ast 定位函数体行范围做精确替换的临时脚本(`apply` 同构变异 → 跑 5 个目标测试 → **原字节回写还原**), 26 条全红; 主仓 `src/` 零残留(首版用 `write_text` 引入 LF 行尾出现过假 modified, 已改 `read_bytes`/`write_bytes`)。
- **S6 复跑(同目标同池 + 补测, 硬约束 11)**: 先 `cp` 新 `tests/test_config.py` 进镜像(否则被 `git checkout -f` 冲掉), 带 `--no-refresh` 复跑 —— 变异 **4799** · 杀 **4110** · 存活 **653** · `no tests` **36** → 杀死率 **85.66%**。
  - **存活 772 → 653(−119)**; 辨别出 15 条「新增存活」实为 **`no tests` → `survived` 的覆盖归类漂移**(在 `_validate_expr_condition_spec` 与 `writer._backup`, 非本 issue 范围、非退化)。
- **池内验证**: 池内 6 文件全绿(数字见 kb.baseline)。
- **环境 / 存量问题(用户裁定)**: 首跑 `test.full` 曾现 2 failed(wording / number 守卫)—— 定位为**存量违规**(`activeContext/26-10-08-0713-webui-qb-traffic-head-layout.md:15` 手抄裸 passed 数字, 来源另一会话提交 `0e8d5432`), 当时用户答「暂时不用管」; **提交前同步远端后该违规已由远端修复**(计数 393 ≤ 冻结 394), 闸门恢复绿。
- **S7 记录**: 基线切片 `testing/baselines/26-10-08-1016-mutants-config-validator-strings.md`; 常驻锚 §07 `config/` 行与 §03 描述同步更新(硬约束 12)。
- **未做**: 「新增存活」15 条归类漂移不单独立项(非退化、非本 issue 范围)。

### 2026-10-08 R7 — 实施 writer-tail 真洞 issue(74 条 S4 候选重判 + 补 22 守阵)

- **触发**: 用户「认领并实施: `issues/26-10-08-0903-test-config-mutation-writer-tail.html`」, 并在追问下选择「全部 74 条逐条补(推荐)」。
- **范围**: `src/auto_qb/config/writer.py` 的 **74 条 S4 真洞候选**(来自首轮 config 审计的 S4 清单, `R:/Temp/auto-qb/mutants/real_holes.json` 的 `.config.writer.` 前缀)。这是「writer 回退/掩码/格式长尾缺守阵」那条 issue 的实施轮。**零 `src/` 改动**(纯补测 + 文档)。
- **关键发现(判据污染)**: 首轮 S4 的「74 条全套件杀不掉」结论**先被假象推翻、再被纠正回来**, 详见坑档 [read-source-static-guard-mutation](../pitfalls/testing/read-source-static-guard-mutation.md):
  - **首次判定(伪影)**: 直接用**镜像**工作树跑 → 74 条**全 KILLED**。根因两层: ①镜像池含另一工作流未提交的 `tests/test_config.py` +309 行(池漂移); ②主因: 镜像 `memory-bank/` 落后一条, 使两条**读源码文本**的守卫(`test_wording_guard_is_green_on_current_kb` / `test_number_guard_is_green_on_current_kb`)在**基线就红**, 而它们对 src 文本敏感 ⇒ 任意 src 变异都被「杀」。
  - **二次验证**: 复位镜像 `tests/` 后仍全 KILLED; 实测这两条守卫在**原样 HEAD** 上本就 **2 failed**(「手抄测试数字 395 > 冻结常数 394」), 属既有债务。
  - **三次判定(有效)**: **显式 `--deselect` 两条既有红守卫** → 基线绿 → 74 条得 **71 SURVIVED(真洞) / 3 KILLED(假存活)**。**issue 前提成立**(且首轮 S4 的 74 条真洞结论正确)。
- **S5 补测**: 新增 **22** 个测试函数(全部落 `tests/test_config_writer.py`, 同步该文件 docstring「测试计划」), 按函数簇: 盖章/物化实参 · backup_versioned/_backup 建目录与编码 · 版本闸门消息 · `_validate_tree` 临时文件往返 + finally 短路与 · `_build_yaml` 引号/缩进档案 · `_build_doc` 回退 · R 级/readonly 回退点路径切分与删键 · `_delete_path` 精确末段 · `_sync_mapping` 未变不动原节点 + 类型互转 · `_same_value`/`_as_builtin` BaseLoader 语义 · `_plain_scalar` 布尔/无损 · `unmask_tree` 守卫与只碰哨兵 · `mask_tree` 递归 + 空值不掩码 · `_set_path` 复用/重建中途节点。
- **S6 复跑(同 74 条 + 补测, 排除既有红守卫)**: **51 KILLED / 23 SURVIVED**(首轮有效判据 71 SURVIVED ⇒ 存活 **−48, −68%**)。
- **余 22 条经逐一验证 = 等价变异**(无法杀死): `_validate_tree` 的 tempfile 参数(`encoding=None/UTF-8`、`suffix` 变体、`"w"`) · `yaml.dump` 参数(`allow_unicode`、`default_flow_style` —— 临时文件解析等价) · `_validate_tree__mutmut_1`(`tmp_path=""` 与 None 同为假值) · `_backup__mutmut_3` / `backup_versioned__mutmut_7`(`parent=None` —— `utils.atomic_write` 内部自带 `makedirs(dirname, exist_ok=True)`, 纵深冗余不可观测) · `_backup__mutmut_14` / `_build_doc__mutmut_8`(删 `open` 的 `"r"`, 默认即 `"r"`) · `_build_doc__mutmut_2`(`doc=""` 与 None 同路) · `_fallback_readonly_fields__mutmut_4/5`(`split(None)` / `split("XX.XX")` —— readonly 路径全不含点, 返回同一单元素列表)。
- **真洞 1 条当场杀死**: `_validate_tree__mutmut_29`(finally 守卫的 `and` → `or`)—— 新增 `test_validate_tree_finally_guard_skips_none_tmp_path`(mock 造临时文件创建失败, 断言原始 OSError 原样冒出; `or` 会变 `stat(None)` TypeError)。**⇒ 71 真洞 = 48 复跑杀 + 1 当场杀 = 49 已清, 22 条等价(不追)**。
- **S7 记录**: 基线切片 [26-10-08-1144-mutants-config-writer-tail](../testing/baselines/26-10-08-1144-mutants-config-writer-tail.md); 新坑档 [read-source-static-guard-mutation](../pitfalls/testing/read-source-static-guard-mutation.md); 本档案 R7; 常驻锚 §07/§08/§09 同步(config 行补第 3 个切片指针, 台账补 R7); writer-tail issue 状态与变更日志更新。
- **收尾实测**: `commands run test.full` 数字见基线切片 [26-10-08-1144](../testing/baselines/26-10-08-1144-mutants-config-writer-tail.md)(2 failed 为既有债务 `tests/test_memory_bank.py` 两条读源码守卫, 远端已在 R6 后修复, 本轮基线 `f9101a33` 上复跑已转绿); `kb.index`(20 生成物) / `kb.check`(主键 / 认领链 / 回写 / 日期全过) / `doc.links` / `doc.drift`(0 处) / `doc.caps`(无新增债务) 全过。
- **未做 / 遗留**: 其余 4 条 config 真洞 issue(loop-guards / boundary-guards / loader-defaults / schema-surface)未实施; 未重跑 `mutants.run` 全包(writer 单文件非 mutmut 目标粒度, 本轮是**对既有 74 条候选的 S4 重判 + 补测复跑**); 未 commit/push(用户未说「提交」)。

### 2026-10-08 R8 — 实施 schema-surface 真洞 issue(27 条 S4 候选复验 + 补 6 守阵)

- **触发**: 用户「认领并修复: `issues/26-10-08-0903-test-config-mutation-schema-surface.html`」—— 首轮入池 6 条 `test` issue 中的第五条。
- **范围**: `src/auto_qb/config/schema/__init__.py` 的 **27 条 S4 真洞候选**(schema_payload 16 / readonly_config_paths 8 / plugins_by_kind 3)。**零 `src/` 改动**(纯补测 + 文档)。
- **S4 复验(判据干净)**: `mutants.verify` 对 27 条逐条 `apply` → 全套件 → 还原, **27/27 SURVIVED**(473s, ≈17s/条)。与 R7 不同, 本轮**未**出现「读源码文本守卫在基线就红」的判据污染(该两类守卫已在远端修复), 无需 `--deselect`。
- **S5 补测**: 新增 **6** 个测试函数(全落 `tests/test_config_schema.py`, 同步该文件 docstring「测试计划」): `readonly_config_paths` 的路径集**与顺序** · 遍历契约**合成结构探针** · `plugins_by_kind` 的 condition/action **两支** + 兜底 · `constants` 键集合逐位 · 常量取值逐项 · `hr_check_site_presets` 每条键集合与逐字段取值。
  - **关键发现(为什么旧守卫杀不掉)**: 现状 4 条 readonly 路径**全在顶层**, 使 `walk` 的递归/前缀机制在真实数据上「看不出差别」—— 只断言当前输出**钉不住** `continue→break`、`if prefix else` 改假条件、`kind == "object"` 变体、`walk(x, None)` 这几类。故改用**合成结构钉机制**: 把 `[ui_only 叶][readonly 叶]` 放进**嵌套层**(顶层已由 `real_config_fields()` 滤掉 ui_only, 放顶层探针是空转 —— 首版就踩了这个坑, 探针空转导致 mutmut_2 仍存活)。
- **红验 26/27 KILLED**(apply 同构变异 → 跑目标测试文件 → 原字节还原, `src/` 零残留)。余 **1 条等价变异**: `readonly_config_paths__mutmut_17`(`walk(real_config_fields(), "")` → `None` —— 顶层 prefix 只被 `if prefix else` 消费, `""` 与 `None` 同为假值, 全部输入产出逐一相同)。
  - **踩坑(工具侧)**: 主仓 `src/auto_qb/config/schema/__init__.py` 是 **CRLF** 行尾, 红验脚本按 LF 拼多行锚点会「静默匹配不上」(报 ANCHOR-MISS 而非假绿); 另外手抄缩进空格数极易差 1(**实测差 1 空格 → 锚点长度 52 vs 51**), 已改用 `" " * 16` 拼接规避。
- **S6 复跑(同目标同池 + 补测, 硬约束 11)**: 先 `cp` 新 `tests/test_config_schema.py` 进镜像再 `--no-refresh` —— 变异 **4799** · 杀 **4190** · 存活 **573** · `no tests` **36** → 杀死率 **87.31%**(R6 基线 653 存活 / 85.66%)。
  - **逐 id 对差: 新杀 83 / 新增存活 3**。归因拆分: **26 条 = 本轮补测**(与红验 26/26 逐 id 对应); **57 条集中在 writer 模块** —— 镜像 12:07 刷新到 `origin/develop` 时纳入了 `fcc3cd69`(R7 的 22 守阵), 而 R6 基线(10:16)时点尚未包含它, **非本轮补测**, 已在切片里如实标注。新增存活 3 条(`writer.x__backup__mutmut_12/15/19`)为归类漂移、非退化。
- **S7 记录**: 基线切片 [26-10-08-1229](../testing/baselines/26-10-08-1229-mutants-config-schema-surface.md); 本档案 R8; 常驻锚 §07/§08/§09 同步(config 行补第 4 个切片指针); schema-surface issue 状态与变更日志更新。
- **收尾实测**: `commands run test.full` 数字见基线切片 [26-10-08-1229](../testing/baselines/26-10-08-1229-mutants-config-schema-surface.md)(`src/` 零改动, 新增用例 +6)。
- **未做 / 遗留**: 其余 3 条 config 真洞 issue(loop-guards / boundary-guards / loader-defaults)未实施; 未 commit/push(用户未说「提交」)。
