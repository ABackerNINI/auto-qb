# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把报告 `26-10-08-0231`(变异测试可行性)落成可复用流程: 指导 skill `mutation-testing`(四段流程 / 硬约束 / 标准步骤 / 三分类 / 派生计划模板) + 命令包 `.commands/mutants`(setup/run/report/verify/gremlins/status) + 常驻排期锚 issue `26-10-08-0642-test-mutation-audit-standing` + 方法论坑档。**config 包已全清**(七轮, 存活 893 → 443 / 杀死率 **90.02%**, 首轮入池 6 条 `test` issue 全实施)。**hr 包**: 首轮(R14)8027 变异 / 存活 2440(**69.2%**), 真洞按主题入池 6 条 `test` issue; 已实施 **R16**(service.py 第一批: 存活 604→502 / **76.07%**)与 **R17**(model·store·queue 三文件: 存活 **271→28**; model **99.88%** / store **93.66%** / queue **90.00%**), 余 4 条 issue(judgment-core / channel-server / runtime-worker / display)。**rules / core 未派生计划**。档案 `tasks/26-10-08-test-mutation-audit.md`。
> 最后活动: 2026-10-10 14:59

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

- **hr 包首轮审计(执行计划 26-10-09-1459, R11)**: 目标 `**/hr/*.py`(24 文件) · 池 15 文件 / 457 fn · mutmut 3.8.0。
  - 首轮 **8027 变异 / 杀 5554 / 存活 2440 / `no tests` 23 / 超时 10**(杀死率 **69.2%**); 墙时 ≈96 min(**4x 于计划估的 17–25 min** —— mutmut 按「估计快的先跑」, 长尾吃掉大半)。
  - **环境事故**: 共享镜像 `~/auto-qb-mut` 与**并行会话**冲突(对方 `rm -rf mutants` 冲掉本轮 `.meta`, 5125/8027 处 `FileNotFoundError`)→ 改用**专用镜像** `~/auto-qb-mut-hr`; 专用镜像首跑 60 min 撞 `mutants.run` 的 3600s 超时, 用 `mutmut run` **续跑**补齐(85.2% → 100%)。
  - **S4 抽验**: 24 条 A 档候选全套件 `apply`→跑→还原 → **24 SURVIVED / 0 KILLED**(**零假存活** —— 池宽, 与 config 池窄的 20% 假存活形成对照)。
  - **处置**: 真洞按主题入池 **6 条** `test` issue(`26-10-10-1108-test-hr-mutation-{service-engine,judgment-core,channel-server,serialization,runtime-worker,display}`); **零 `src/`/`tests/` 改动**。补测+复跑按模块拆后续轮(计划 §5 停手点)。
  - 基线切片 `testing/baselines/26-10-10-1108-mutants-hr.md`; 常驻锚 §03/§07/§08/§09 已同步。
- **R15 回灌(hr 首轮经验进 skill / 报告 / 命令包)+ 修 §03 漂移**: 三条可复用经验 —— ①**多 clone 并行共用镜像会被对方 `rm -rf mutants` 冲毁**(实测 hr 首轮 85% 作废; 处置: 专用镜像 `--mirror` + 降 `--children`; 新坑档 `pitfalls/testing/mutants-shared-mirror.md`)②**大包单轮 >60 min 且可续跑**(`mutants.run` timeout 3600→7200; mutmut 续跑只补余量; 更稳是按模块切)③**池宽 ⇒ 零假存活**, `mutants.verify` 在宽池下不缩小候选。落点: skill 硬约束 **14/15** + 三分类推论 + 派生计划 §2/§5 + 4 条反模式 + 记录口径(轮次撞号); 报告 §14 第六/七/八条 + hr 实测小节; 命令包 `config.toml` / `why.md`。另修 §03 `config/` 行(六轮 → 七轮, 补 R13)。**零 `src/`/`tests/` 改动**。
- **config 后四轮 + R13 收口**(池内 `test` issue 逐条实施): loader-defaults(R11, 存活 476 / 89.33%)· boundary-guards(R13, 存活 443 / **90.02%**)· 另含 R6 validator-strings / R7 writer 长尾 / R8 schema 键面 / R10 loop-guards。**config 首轮入池 6 条 `test` issue 已全部实施**, 余量仅剩未逐条补测的 555 条 S4 未验证候选。切片见 `testing/baselines/26-10-08-*` 与 `26-10-09-1611` / `26-10-10-0925` / `26-10-10-1045`。
- **R16 hr/service.py 第一批守阵**(issue `26-10-10-1108-service-engine`): 实施首轮建议的三函数(`_stop_condition` / `_run_downloads` / `_finish_wave`)—— 补 **30 新守阵 + 4 处既有补断言**, 红验 **85/85 KILLED**; 同池单模块复跑存活 **604 → 502**(**76.07%**)。**零 `src/` 改动**; 切片 `testing/baselines/26-10-10-1408-mutants-hr-service.md`; **issue 置 `In Progress`**(其余 12+ 函数留后续轮)。坑 `redverify-anchor-lineendings` 复发 +1(形态四)。
- **R17 hr/model·store·queue 序列化与持久化守阵**(issue `26-10-10-1108-serialization`): **三文件一次做全**(271 条存活, 首轮建议 `model.from_json` 145 条为最大单点)—— 补 **41 新守阵 + 1 处既有补断言**, 红验 **245/271 KILLED**(余 26 条逐条判等价); 同池逐文件复跑 **model 844/存活 1(99.88%) · store 205/存活 13(93.66%) · queue 140/存活 12+超时 2(90.00%)**, 对首轮逐文件存活对差 **271 → 28**(净 −243)。**零 `src/` 改动**; 切片 `testing/baselines/26-10-10-1458-mutants-hr-serialization.md`; **issue 置 `Done`**。新坑 `pitfalls/testing/mutants-mirror-dirty-worktree.md`(镜像工作树残留 apply 变异体而 git 判净) + 坑 `redverify-anchor-lineendings` 复发 +1(形态五)。

## 正在进行

- (无) —— R16 / R17 已闭环。hr 包余 **4 条** `test` issue 未实施(judgment-core / channel-server / runtime-worker / display), 属后续轮。

## 未决项

- **hr 首轮入池 6 条 `test` issue 已做 2 条**: R16 service.py 第一批(604 条中三函数) / R17 model·store·queue(全量); 余 **4 条**未实施 —— `judgment-core` / `channel-server` / `runtime-worker` / `display`。
- **config 真洞 issue 已全清**(6 条全实施); 余量仅剩 config 包内未逐条补测的 555 条 S4 未验证候选(按需另立轮)。
- **service.py 其余函数未覆盖**(R16 余量: `_run_pages` / `_do_wave` / `_refresh_locked` / `_append_history` 等, 见 R16 切片「余量」节); `rules` / `core` **仍未派生计划**(对象优先级见可行性报告 §11)。
- 常驻 issue 的认领链只有一条(本档案); 后续每轮若新增计划/档案, 记得同步 issue 的 `doc-refs`。
- **回灌已落地**(R3/R12/R15): 命令包 `mutants.report` / `mutants.verify`; skill 硬约束 9–15 与形态级复验专节; 报告 §14。下次跑任一包都应走 task id, 别再手工拼 S4。
