# 26-10-08-test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

**Status:** In Progress
**Added:** 2026-10-08
**Updated:** 2026-10-08
**Summary:** 把「变异测试定期审计」从一次可行性调研落成可复用的流程: 指导 skill(mutation-testing) + 命令包(mutants: setup/run/gremlins/status) + 常驻排期锚 issue + 方法论坑档; 全流程在 WSL 用 infra/versioning.py 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。后续按包派生计划逐轮推进。
**Refs:** memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html, memory-bank/pitfalls/testing/mutation-pool-artifact.md, memory-bank/testing/baselines/26-10-08-0647-test-mutation-audit.md, memory-bank/testing/baselines/26-10-08-0727-test-mutation-audit-config-plan.md
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

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| S1 指导 skill | Done | `.agents/skills/mutation-testing/SKILL.md`; 含「派生「针对 X 的分步执行计划」」骨架 |
| S2 命令包 | Done | `mutants.setup` / `mutants.run` / `mutants.gremlins` / `mutants.status` |
| S3 实测 | Done | 见下「进度日志」R0; `set_conf` 覆盖式重写与幂等本地实测通过 |
| S4 issue + 坑档 | Done | issue `26-10-08-0642-test-mutation-audit-standing`(常驻) + `pitfalls/testing/mutation-pool-artifact.md` |
| S5 收尾 | Done | 索引 / 基线 / 软链 |
| S6+ 逐包轮次 | In Progress | config 计划已派生(`plans/26-10-08-0720-plan-mutation-config.html`); 等拍板后执行, rules/hr/core 未派生 |

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
