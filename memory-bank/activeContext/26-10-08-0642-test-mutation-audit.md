# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把报告 `26-10-08-0231`(变异测试可行性)落成可复用流程: 指导 skill `mutation-testing`(四段流程 / 硬约束 / 标准步骤 / 三分类 / 派生计划模板) + 命令包 `.commands/mutants`(setup/run/gremlins/status) + 常驻排期锚 issue `26-10-08-0642-test-mutation-audit-standing` + 方法论坑档 `pitfalls/testing/mutation-pool-artifact.md`。全流程在 WSL 用 `infra/versioning.py` 端到端跑通(155 变异 / 21.6s / 杀 147), Windows 侧 gremlins 兜底同验(25 变异 / 100% / 11.9s)。**config 包已跑五轮**: 首轮(计划 26-10-08-0720)4799 变异 / 杀 3851 / 存活 893(80.25%) → S4 全套件确认 274 条(54 假存活 + 220 真洞候选) → 补 10 守阵 → 复跑存活 **772**(−121, 82.77%); 后续按主题补守阵 → 653(85.66%) → 573(87.31%) → **533**(**88.14%**, loop-guards)。**hr 包计划已派生**(`plans/26-10-09-1459-plan-mutation-hr.html`, 状态 `Open` 待拍板, 未执行)。档案 `tasks/26-10-08-test-mutation-audit.md`。
> 最后活动: 2026-10-09 16:11

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

- **config 包第三轮(writer 长尾, 池内 `test` issue 26-10-08-0903-writer-tail)**: writer.py 的 74 条 S4 候选重判 —— 先修**被污染的 S4 判据**(镜像池含未提交改动 + 两条**读源码文本**守卫在基线就红 ⇒ 74 条被伪杀成零), 排除既有红守卫后得有效判据 **71 真洞 / 3 假存活**; 补 **22 守阵**后复跑 → **51 KILLED / 23 SURVIVED**(存活 −48); 余 22 条逐一验证为等价变异, 1 条真洞当场杀。**零 `src/` 改动**。新坑档 `pitfalls/testing/read-source-static-guard-mutation.md`; 切片 `testing/baselines/26-10-08-1144-mutants-config-writer-tail.md`。
- **config 包第四轮(schema 键面, 池内 `test` issue 26-10-08-0903-schema-surface)**: `config/schema/__init__.py` 的 **27** 条 S4 候选复验 **27/27 SURVIVED**(判据干净, 无 R7 那类污染)。
  - **关键发现**: 现状 4 条 readonly 路径**全在顶层**, 使 `walk` 的递归/前缀机制在真实数据上「看不出差别」—— 只断言当前输出**钉不住**那 8 条(`continue→break` / `if prefix else` 改假条件 / `kind == "object"` 变体 / `walk(x, None)`)。改用**合成结构探针钉机制**: ui_only 叶须放**嵌套层**(顶层已被 `real_config_fields()` 滤掉, 放顶层探针是空转 —— 首版就踩了这个坑)。
  - 新增 **6** 个守阵(全落 `tests/test_config_schema.py`): readonly 路径集**与顺序** · 遍历契约合成探针 · `plugins_by_kind` 的 condition/action **两支** + 兜底 · `constants` 键集合逐位 · 常量取值逐项 · `hr_check_site_presets` 每条键集合与逐字段取值。红验 **26/27 KILLED**; 余 1 条等价变异 `readonly_config_paths__mutmut_17`(`walk(..., "")` → `None`, 顶层 prefix 只被 `if prefix else` 消费, 同为假值)。
  - 同池 `--no-refresh` 复跑: 杀 **4190** / 存活 **573** / `no tests` **36** → 杀死率 **87.31%**; 逐 id 新杀 83 —— **26 条 = 本轮补测**, 另 **57 条集中在 writer**(镜像刷新纳入 `fcc3cd69` 的 R7 守阵, R6 基线时点之后才进 develop, **非本轮**)。**零 `src/` 改动**; 切片 `testing/baselines/26-10-08-1229-mutants-config-schema-surface.md`。
  - **踩坑(工具侧)**: 主仓该文件是 **CRLF** 行尾, 红验脚本按 LF 拼多行锚点会静默匹配不上(报 ANCHOR-MISS), 且手抄缩进极易差 1 空格(实测 52 vs 51)—— 已改用 `" " * 16` 拼接规避。
- **派生计划(hr)**: `plans/26-10-09-1459-plan-mutation-hr.html`(状态 `Open` 待拍板, 未执行) —— 目标 `**/hr/*.py`(fnmatch 实测命中 **24** 文件, 不误伤 `webui/server/routes/hr.py`); 重点面分 A(判定内核: resolve/service/bencode/parse)· B(链路·安全·持久化: channel/store/ratelimit/queue/worker/runtime/server/model)· C(表现·胶水: status/report/events/fetcher/adapters)三档; 测算 ≈7,800 变异 / ≈17–25 min(hr 池比 config 大 2.5x); 池 = **15 文件 / 457 fn**; 步骤 S1–S8(含硬约束 12 的「更新常驻锚 §07」)。零 `src/` / `tests/` 改动。
- **config 包第五轮(多条目循环 continue/break, 池内 `test` issue 26-10-08-0903-loop-guards)**: 首轮 dump 的 **30** 条 `continue→break`/`break→return` 候选复验 **21 SURVIVED / 9 KILLED**(9 条已被 R2/R7/R8 同型守阵杀死 —— 印证 issue 首轮清单已部分失效, 复验是必要动作)。
  - **关键发现(为什么首轮杀不掉)**: 池内旧用例都是**单条目**(一次迭代), `continue` 与 `break` 行为相同 —— 只有把「跳过分支条目 + 后续必处理条目」成对放入才能区分。
  - 补 **18** 个「多条目」守阵(`tests/test_config.py` 10 + `tests/test_hr_config.py` 8), 覆盖 `_validate_fs` / `_validate_trackers` / `_validate_tag_lists` / `_validate_global_speed_limit_curve` / `_validate_curve_points` / `_check_rule_refs` / `_validate_checking_action_spec` / `_validate_trigger_action_compat` / `_validate_rules` / `_validate_hr_check` / `_validate_hr_site_bindings` / `loaders._resolve_hr_site_bindings`。`_validate_hr_site_bindings` 重复绑定那条(88)现网只有两个档案, 用 `monkeypatch.setitem(SITE_PRESETS, ...)` 加合成档案使 `break` 后果可观测。
  - 红验 **34/34 RED**(30 条按 dump hunk 逐字节套同构变异保留 CRLF + 4 条手工合成; `src/` 零残留)。同池 `--no-refresh` 复跑: 杀 **4230** / 存活 **533** / `no tests` **36** → 杀死率 **88.14%**; 逐 id 新杀 **40**(21 定向 + 2 真 continue→break + 17 同循环旁支)/ 新增存活 **0**。**零 `src/` 改动**; 切片 `testing/baselines/26-10-09-1611-mutants-config-loop-guards.md`。

## 正在进行

- (无) —— config 第五轮已闭环; 等下一轮(见未决项)。

## 未决项

- **回灌已落地**(R3): 命令包新增 `mutants.report`(带 diff 的清单 + 汇总)与 `mutants.verify`(S4 全套件确认的机械化, ≈15s/条、可续跑); skill 补「流程约束 9–11」与两条记录纪律; 报告加 §14; 排期锚补进度/台账。下次跑任一包都应走这两条 task, 别再手工拼 S4。
- **config 真洞余量未逐条补测**: 首轮 S4 覆盖 274 条(220 条真洞候选); 后续各轮复跑又陆续杀掉一部分。余量按模式入池 6 条主题 issue, **已做 4 条**(validator-strings / writer-tail / schema-surface / loop-guards), 余 **2** 条等排期(`boundary-guards` / `loader-defaults`)。
- 逐包轮次: **hr 计划已派生**(`plans/26-10-09-1459-plan-mutation-hr.html`, 未执行); rules / core **仍未派生计划**(对象优先级见可行性报告 §11); config 复跑可作为下一轮对照点(存活应 ≤ 533)。
- **存量守卫违规未处理**(用户裁定): 见上「已完成」末条; 若日后要清, 需另开会话(属 `webui-qb-traffic-head-layout` 会话产物, 非本专题范围)。
- 常驻 issue 的认领链只有一条(本档案); 后续每轮若新增计划/档案, 记得同步 issue 的 `doc-refs`。
