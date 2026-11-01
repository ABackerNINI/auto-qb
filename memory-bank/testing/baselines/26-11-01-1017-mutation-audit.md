# 4513 passed + 2 skipped(根) —— core W7 R31 变异审计: 快照与来源四文件 S6 同池复跑(1,110 变异, 守阵后杀死率 93.96%)

> 摘要: core 包 W7(R31, 计划 26-10-31-0128): 目标 4 文件 `**/core/modules/traffic_snapshot_mod.py` + `**/core/traffic_source/{agent,paths,reader}.py`(365/475/115/50 行)· 池 7 文件 → 首轮(S2, 4 文件分跑) **1,110 变异 / 存活 202(snapshot 63 / agent 120 / paths 14 / reader 5)+ no tests 18 / 超时 0(80.18%)** → S3 三分类 **真洞 138(高 0 / 中 29 / 低 100 / 极低 9)/ 等价 62 / 假存活 2** → S4 verify 候选 30(SURVIVED 28 / KILLED 2, 推翻假存活 2)+ S5 补测 **31 守阵**(红验 139/139 全红, commit 4573f9d1; reader 4 守阵基座为 W7 前置 0a6ce48f)+ 批量入池 1 件 → **S6 同目标同池复跑(4 文件分跑一次干净跑完): 杀 1,043 / 存活 49 / 超时 0 / no tests 18(93.96%)**, **新增存活 0**(复跑存活 49 全部 ⊆ 首轮 202)。对差: 移出 153 = 真洞 138 全杀(含 er_39/40 被函数级映射连带杀, S3「无可观测面」判定被复跑推翻)+ 等价连带杀 15(逐 id 实证 12, 同 W6 形态); 复跑存活构成闭合 = 等价 47 + 假存活记账 2。**零 `src/` 改动**(纯补测[先于本轮] + 入池[本轮] + 文档)。
> 基线时间: 2026-11-01 10:17
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4513 passed + 2 skipped / 覆盖率 99.08%**(C3 收尾实测 112.78s, mut-core-audit 本地树; 新入池 issue `26-11-01-0953` doc-refs 与档案 Refs 双向补链后一次全绿, 无 R29 那类认领链红)。

### 首轮与复跑对照(全轮一行 + 逐文件四行)

| 轮次 | 变异 | 杀 | 存活 | 超时 | no tests | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| 首轮(S2, 2026-11-01 07:46–07:55, 4 文件分跑) | 1,110 | 890 | 202 | 0 | 18 | ≈10 min(结果戳 0746–0754) | 80.18% |
| **复跑(S6, 2026-11-01 10:01–10:05, 4 文件分跑一次干净跑完)** | 1,110 | **1,043** | **49** | **0** | **18** | ≈4 min(rc 全 0) | **93.96%** |

| 目标文件 | 变异 | 存活(首轮) | 杀(复跑) | 存活(复跑) | no tests(首轮→复跑) | 杀死率(首轮→复跑) |
|---|---|---|---|---|---|---|
| modules/traffic_snapshot_mod.py | 385 | 63 | 368 | 17 | 0→0 | 83.64% → 95.58% |
| traffic_source/agent.py | 566 | 120 | 523 | 25 | 18→18 | 75.62% → 92.40% |
| traffic_source/paths.py | 127 | 14 | 121 | 6 | 0→0 | 88.98% → 95.28% |
| traffic_source/reader.py | 32 | 5 | 31 | 1 | 0→0 | 84.38% → 96.88% |
| **合计** | **1,110** | **202** | **1,043** | **49** | **18→18** | **80.18% → 93.96%** |

- **目标(glob)**: 4 个单文件 glob(`**/core/modules/traffic_snapshot_mod.py` + `**/core/traffic_source/{agent,paths,reader}.py`), 4 文件分跑, 同首轮
- **选择池(7 个; 两轮一致, 未改池——镜像 pyproject `pytest_add_cli_args_test_selection` 原样留有首轮清单, 复跑逐文件同单传)**:
  `tests/test_traffic_snapshot.py` · `tests/test_traffic_source_agent.py` · `tests/test_traffic_source_paths.py` · `tests/test_traffic_source_reader.py` · `tests/test_traffic_monitor_client.py` · `tests/test_web_traffic_monitor.py` · `tests/test_config_traffic_monitor.py`
  - 池内 4 文件含 S5a 新守阵: test_traffic_snapshot(+8)/test_traffic_source_agent(+19)/test_traffic_source_paths(+2)/test_traffic_source_reader(+2), commit 4573f9d1(先于本轮 C3; reader 4 守阵基座为 W7 前置 0a6ce48f)——本轮开工已 cp 进镜像并 md5 核对一致(另 3 池文件与 4 个目标 src 与本地 HEAD 逐位一致已核, conftest.py 本地 CRLF/镜像 LF 伪差已排除)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**
- **镜像口径**: head **3275c1d4**(与首轮逐位一致, 两轮同 head 数字可比); **未刷新/未重建/未 uv sync**(`--no-refresh --no-sync` 原样复用, venv pytest 钉 **9.1.1**); ⚠ 镜像 pyproject `[tool.mutmut]` 沿首轮收官态(only_mutate 四 glob——S4 曾补一次、被 run 覆盖重写过, 本轮复跑 4 次后已复原回四 glob; deselect 8 条两轮一致零新增; `timeout_multiplier` 已随首轮 set_conf 覆盖移除, 复跑同口径 0 超时)
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— S5a 守阵 commit(4573f9d1)在本地分支线而镜像 head 3275c1d4 早于它, cp 4 个新池文件进镜像 + `mutants.run --no-refresh --no-sync --mirror '~/auto-qb-mut-core'`; 4 文件顺序分跑, **一次干净跑完 rc 全 0, 无 R28/R29 那类 WSL VM 被杀/分块续跑**
- **deselect 口径**: `set_conf.py` DEFAULT_DESELECT 维持 **8 条**(R30 入库口径), 本轮零新增
- **新增存活 0**(逐 id 对差做实): 复跑存活 49 全部 ⊆ 首轮 202 存活, 只有移出无移入
- **复跑存活构成闭合(49)**: 等价 **47** + 假存活记账 **2**(`publish_limit_3` snapshot / `dtd_3` agent——mutmut 函数级映射池内无直杀, 与 S4 全套件 KILLED 判定不矛盾)= **49** ✓
- **对差 153 = 真洞 138 全杀 + 等价连带杀 15**: 真洞 138 = 守阵覆盖 ~136 + **er_39/40 复跑被 mutmut 函数级测试映射连带杀**(S3「无可观测面、守阵不硬凑」判定被复跑推翻——两 mutant 落在 `_ensure_running`, S5a 同函数新守阵经映射全部参与判验; 复跑存活构成不再有真洞残项); 等价连带杀 15 同 W6「新守阵精确断言把等价转可观测」形态, 逐 id 实证 12: snapshot `_interval_of_6/_interval_of_15/refresh_45` · agent `pdh_4/rlt_36/rct_29/run_claim_5/run_claim_7/read_pointer_10/rdn_11` · paths `source_signature_17` · reader `rsr_12`; 另 3 条为 classify 块小结(等价 62)与表行(59)的既有 ±3 记账差(S3/S4 遗留, 非 id 级新增存活)

### 三分类终态(W7 池口径, 详见任务档案 R31 与 tmp-analysis/w7-r31/classify.md)

- **真洞 138**(高 0 / 中 29 / 低 100 / 极低 9): 复跑实测**全杀 138/138**(含 er_39/40 连带); 平台相关真洞 ~35 条(Windows 分支 ~20 套件永不可杀 + GBK 编码 5 + POSIX 生产面 8)以平台内断言/契约钉参守阵覆盖(WSL 池盲区在 Windows 咬合)
- **等价 62**: 复跑实测存活面 47(连带杀 15, 逐 id 见上); 逐条理由见 classify
- **假存活 2**(S4 verify 推翻): `dtd_3`(agent, 3 池内守阵直杀)/ `publish_limit_3`(snapshot, test_speed_curve 池外 3 守阵直杀)——复跑按记账留在存活面
- **超时盲区 0**(窄池轮全程 0 超时, 无 W5/W6 那类死循环盲区)
- **no tests 18**(agent `_run_foreground`): 池内无直接触达——唯一直跑用例 `test_run_foreground_real_execution_with_allowed_binary` 依赖环境二进制 node, 无 node 静默 return, 函数体在覆盖映射期从未执行; 已入池 issue 登记, 不扩池
- **S4 对账**: 候选 30 = SURVIVED 28 / KILLED 2(推翻假存活 2)/ TIMEOUT·FLAKY·APPLY_FAIL 终态 0; 9 条首轮新增失败全是 `test_hr_discovery` 端口绑定类既有 flaky(不判死), 幂等续跑 9/9 稳定 SURVIVED
- **红验**: S5a **139/139 全红**(snapshot 43 + agent 86 + paths 7 + reader 3, 逐条 apply→跑守阵→还原, commit 4573f9d1); 复跑实测守阵真洞覆盖 **138/138**(er_39/40 经映射连带补上)
- **1 件 issue**: [`26-11-01-0953-test-core-w7-mutation-run-foreground-notests`](../issues/26-11-01-0953-test-core-w7-mutation-run-foreground-notests.html)(no-tests 18 登记: 池内无直接触达定性 + 池调整建议; 档案 Refs 已双向补链)
- **dump / results 指针**: 三分类输入 = 首轮 dump/results `tmp-analysis/w7-r31/26-11-01-07{49,52,53,54}-core-*`(snapshot 0753 · agent 0754 · paths 0754 · reader 0752/0749; 原始落盘 `R:\Temp\auto-qb\mutants\`); 复跑 results 4 件 = `R:\Temp\auto-qb\mutants\26-11-01-10{02,03,04,05}-core-*-results.txt`(snapshot 17 · agent 25+18 no tests · paths 6 · reader 1); S4 verify 产物 `R:/Temp/auto-qb/mutants/s4-verify-s4-ids.txt`(清单 `tmp-analysis/w7-r31/s4-ids.txt` 30 条); 红验 4 组日志 `tmp-analysis/w7-r31/s5-redverify-*.log`

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_traffic_snapshot.py`(+147)· `tests/test_traffic_source_agent.py`(+414)· `tests/test_traffic_source_paths.py`(+32)· `tests/test_traffic_source_reader.py`(+38) | S5a 31 守阵(红验 139/139 全红), commit 4573f9d1; reader 4 守阵基座为 W7 前置 0a6ce48f(先于本轮 C3) |
| `memory-bank/issues/26-11-01-0953-test-core-w7-mutation-run-foreground-notests.html` | 批量入池 no-tests 登记 1(standard), 本轮 |
| `memory-bank/testing/baselines/26-11-01-1017-mutation-audit.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R31 条目 + Summary/S 步表收口 W7 + 新 issue Refs 反向声明 |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W7 口径)+ §03 core 行 W7 已做注记同步 |

**未改**: `src/` 零改动; 选择池未扩(7 文件两轮一致; no-tests 18 按 issue 口径不扩)。
