# 396 变异 / 复跑杀死率 84.09% —— core/state+taskqueue W1 变异审计: 首轮与补测后复跑(同目标同池)

> 摘要: core/ 包 W1(R25, 计划 26-10-31-0128): 目标 `**/core/state.py` + `**/core/taskqueue.py`(target 只收单 glob, 分两次跑) · 池 3 文件定向 → 首轮合计 **396 变异 / 杀 307 / 存活 89 / no tests 0**(杀死率 **77.53%**; taskqueue 02:44 首跑有 33 条 no tests 池缺口, 见下注记) → S5 补 9 守阵进池(红验 18/18 全红) → **同目标同池复跑: 杀 333 / 存活 63 / no tests 0 / 超时 0(杀死率 84.09%, 存活 −26, 新增存活 0)**。三分类(复跑后口径): 真洞 24 处置完毕 = 22 条补断言全部实测 KILLED + 2 条 bug 入池(taskqueue dry_run 链 2 条因守阵进池连带 KILLED; state 读 encoding 2 条仍存活属确认型, 处置=bug issue 非补测); 余存活 63 = 等价 55 / 假存活 6。**零 `src/` 改动**(纯补测 + 文档 + 2 条 bug issue)。
> 基线时间: 2026-10-31 05:18

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **目标(glob)**: `**/core/state.py` 与 `**/core/taskqueue.py` —— target 只收单 glob, 两模块分两次跑, 数字分列不合池
- **选择池(逐个文件, 3 个; 跨轮一致)**:
  `tests/test_taskqueue.py` · `tests/test_module_host.py` · `tests/test_rule_engine.py`
  - 池内 3 文件均含 S5 新守阵(9 条, 全部正向+反向对照): test_taskqueue 3(dry_run 契约一条杀两条 / max_tasks=1 预算 / scan_cap 边界) · test_module_host 2(溢出淘汰 ts 最旧+当日不进候选 / 防御默认族缺字段不崩) · test_rule_engine 3+1 处([] 顶层算损坏 / 真迁移 desc 物化 / cleanup keeps 反例)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · 默认镜像 `~/auto-qb-mut`(head `bac7bc57`)
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— 本地守阵 commit 未在 origin/develop, 镜像 `--no-refresh` + 手工 cp 3 个池测试文件进镜像 `tests/`(md5 逐一核对一致); 镜像 `src/auto_qb/core/{state,taskqueue}.py` 与本地 HEAD 逐字节 diff 一致

### 首轮与复跑对照(每轮一行)

| 目标 / 轮次 | 变异 | 杀 | 存活 | no tests | 超时 | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| state.py 首轮(2026-10-31 02:44) | 222 | 157 | 65 | 0 | 0 | 未单录 | 70.72% |
| **state.py 复跑(S6, 05:11)** | **222** | **177** | **45** | **0** | **0** | **≈16s**(日志起止实测) | **79.73%** |
| taskqueue.py 首跑(02:44, 池缺口) | 174 | 116 | 25 | **33** | 0 | 未单录 | 66.67% |
| taskqueue.py 首轮(03:17, 池补 5 查询函数守阵后重跑, 池补齐口径) | 174 | 150 | 24 | 0 | 0 | ≈3 min(含基线强制失败自检) | 86.21% |
| **taskqueue.py 复跑(S6, 05:14)** | **174** | **156** | **18** | **0** | **0** | **20.8s**(wrapper 实测) | **89.66%** |
| **合计: 首轮(02:44 state + 03:17 taskqueue)** | **396** | **307** | **89** | **0** | **0** | — | **77.53%** |
| **合计: 复跑(S6)** | **396** | **333** | **63** | **0** | **0** | — | **84.09%** |

- **池缺口注记**: taskqueue 02:44 首跑 no tests **33**(`has_task`/`has_named`/`named`/`active_check_age` 全族零覆盖)——B3 已按「补 4 查询函数守阵后重跑」口径补齐, 首轮行以 **03:17 池补齐后重跑**(150/24/0)为准, 02:44 行仅作缺口留档。
- **存活 −26 的构成**(逐 id 对差, 两模块新增存活均 **0**):
  - state 65 → 45(−20): 18 条 S5 补断言真洞全杀(`_read_state_file_14` · `_migrate_state_dict_9` · `cleanup_orphan_tmp_16` · `_prune_exec_history_11/13/16/23/25/26/28/29/31/32/33/34/35/37/38`)+ 假存活 `prune_day_keys_8`(守阵 dbc13cad 本在池文件, 本轮镜像带上即杀)+ **原判等价 `load__mutmut_1`(migration_desc ""→None)被新守阵连带杀** —— 「等价」判读被复跑推翻 1 条, 说明该差异可区分, 判读保守而非假阴性洞。
  - taskqueue 24 → 18(−6): 补测真洞 `_pop_due_15`/`_pop_due_21` + 假存活 `_pop_due_16`(与 max_tasks=1 守阵同杀)+ bug 变异 `run_due_15`/`_run_one_3`(S5 守阵进池连带杀, 见下)+ **原判等价 `run_due__mutmut_1`(dry_run 缺省 False→True)被 dry_run 契约守阵反向对照连带杀**。
- **bug 入池 4 条变异的复跑口径**: 处置=**bug issue, 非补测**。①`issues/26-10-31-0449-bug-taskqueue-dry-run-chain.html`(run_due_15 + _run_one_3): issue 附带的契约守阵已进池 ⇒ 复跑实测 KILLED(优于预期, 变异销账; issue 本体=src 缺陷面仍待修); ②`issues/26-10-31-0458-bug-state-read-encoding-guard.html`(_read_state_file_3 + _6): **仍存活属预期**(确认型真洞 —— locale 打桩在 CPython 3.13 实证不可达, UTF-8 宿主杀不掉, 不硬凑假绿), 待 issue 修复后关闭。

### 三分类(复跑后口径, 合计 63)

| 模块 | 等价 | 假存活 | bug 入池待修 |
|---|---|---|---|
| state.py(45) | 38 | 5 | 2 |
| taskqueue.py(18) | 17 | 1 | 0 |
| **合计** | **55** | **6** | **2** |

- 真洞 24 条(首轮口径)处置全闭环: **22 条补断言**(9 新守阵进 3 池文件)本轮复跑全部实测 KILLED; **2 条 bug 入池**(上表末列, state encoding)。
- 假存活 8 条(S4 坐实)本轮复跑杀 2(`prune_day_keys_8` 守阵进镜像 · `_pop_due_16` 同守阵连带), 余 6 条守阵在池外文件(`test_speed_curve` / `test_rule_base` / `test_trigger_events` / `test_qbmanager` / `test_modules_p3`), 本轮池不含 ⇒ 仍存活**属预期**, 非缺口。
- S4 verify 对账: 候选 **32** 条 → SURVIVED 24 / KILLED 8 / 未判定 0(假存活 8 全坐实)。
- **手搓 18 条同构变异声明**: S5 红验用的手搓变异(bytes 层, pre 18 SURVIVED → post 18 KILLED)**仅用于形态复验与红验**, 不进本轮任何计数; 量化以本切片 S6 复跑为准。

### 全量测试(S5 补测后, 本轮实测)

- `commands run test.full`: **4206 passed + 2 skipped**(S5 阶段实测誊写; 本轮 C3 零代码/测试改动, 数字不重采)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_taskqueue.py` · `tests/test_module_host.py` · `tests/test_rule_engine.py` | S5 阶段 9 条新守阵(3+2+3/4 处), 头部「## 测试计划」同步 |
| `memory-bank/issues/26-10-31-0449-bug-taskqueue-dry-run-chain.html` · `26-10-31-0458-bug-state-read-encoding-guard.html` | 2 条 bug 入池(doc-refs 反向声明任务档案) |
| `memory-bank/testing/baselines/26-10-31-0518-mutants-core-state-taskqueue.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R25 轮次完成行追加 |

**未改**: `src/` 零改动(纯补测 + 文档 + bug 入池)。
