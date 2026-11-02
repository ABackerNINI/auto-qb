# 4478 passed + 2 skipped(根) —— core W6 R30 变异审计: 编排客户端五文件 S6 同池复跑(1,275 变异, 守阵后杀死率 78.51%)

> 摘要: core 包 W6(R30, 计划 26-10-31-0128): 目标 5 文件 `**/core/{module,qbmanager,qbapi,qbclient,exporter}.py`(439/967/410/68/150 行)· 池 10 文件 → 首轮(T5, 5 文件分跑) **1,275 变异 / 存活 444(杀死率 51.61%)+ 超时 16 + no tests 157** → S3 三分类 **真洞 332(高 1 / 中 135 / 低 168 / 极低 28)/ 等价 112 / 假存活 0** → S5 补测 **67 守阵**(core 四文件 28 + qbmanager 39, 红验 128/128 + 201/201 全红, commit 8e073df7 / dda19819)+ deselect 3→8 + 批量入池 2 件(commit c06974af)→ **S6 同目标同池复跑(5 文件分跑一次干净跑完, 全程无 WSL VM 被杀): 全轮实测 杀 997 / 存活 101 / 超时 20 / no tests 157(78.20%)**; 26 条条目级复验后**修正口径 杀 1,001 / 存活 101 / 超时 16(78.51%)**, **新增存活 0**(复跑存活 101 全部 ⊆ 首轮 444 存活)。对差: 新杀 342 = 真洞 325 + **判读等价连带 17(条目级复验全稳定, 机理=新守阵精确断言把等价转可观测, 同 W4 z_row_39 形态)** + 盲区回收 1(run_20); 盲区 16 构成变化(−run_20, +gtn_17 转盲区; TypeError 空转环 4 条复跑改判预期未兑现维持盲区); 真洞残存活 6(3 注记 + 3 签名默认极低——S5b 红验覆盖声明对后者不成立, 复跑实测守阵真洞覆盖 325 杀 + 1 盲区)。**零 `src/` 改动**(纯补测[先于本轮] + 入池[先于本轮] + 文档)。
> 基线时间: 2026-11-01 07:22
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4478 passed + 2 skipped / 覆盖率 99%**(C3 收尾实测 125.6s, mut-core-audit 本地树; 档案 `Refs:` 补 26-11-01-0614 两件反向声明后一次全绿, 无 R29 那类认领链红)。

### 首轮与复跑对照(全轮一行 + 逐文件六行)

| 轮次 | 变异 | 杀 | 存活 | 超时 | no tests | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| 首轮(T5, 2026-11-01 02:50–03:15 dump) | 1,275 | 658 | 444 | 16 | 157 | 未整录(5 文件分跑, 会话中断交接) | 51.61% |
| 复跑·全轮实测(S6, 2026-11-01 06:23–06:58) | 1,275 | 997 | 101 | 20 | 157 | 2,100s | 78.20% |
| **复跑·修正口径(26 条条目级复验后)** | 1,275 | **1,001** | **101** | **16** | **157** | 复验 26 条 ≈15 min | **78.51%** |

| 目标文件 | 变异 | 杀(首轮) | 存活(首轮) | 杀(复跑修正口径) | 存活(复跑) | 超时(首轮→复跑) | no tests | 杀死率(首轮→复跑) |
|---|---|---|---|---|---|---|---|---|
| module.py | 163 | 115 | 48 | 155 | 8 | 0→0 | 0 | 70.55% → 95.09% |
| qbmanager.py | 615 | 329 | 261 | 537 | 54 | 15→14 | 10 | 53.50% → 87.32% |
| qbapi.py | 270 | 60 | 63 | 104 | 19 | 0→0 | 147 | 22.22% → 38.52% |
| qbclient.py | 31 | 16 | 15 | 28 | 3 | 0→0 | 0 | 51.61% → 90.32% |
| exporter.py | 196 | 138 | 57 | 177 | 17 | 1→2 | 0 | 70.41% → 90.31% |
| **合计** | **1,275** | **658** | **444** | **1,001** | **101** | **16→16** | **157** | **51.61% → 78.51%** |

- **目标(glob)**: `**/core/{module,qbmanager,qbapi,qbclient,exporter}.py`(5 个单文件 glob, 5 文件分跑, 同首轮)
- **选择池(逐个文件, 10 个; 两轮一致, 未改池)**:
  `tests/test_module_host.py` · `tests/test_facade_modules.py` · `tests/test_core_modules.py` · `tests/test_qbmanager.py` · `tests/test_manager_single_point.py` · `tests/test_local_qb_service.py` · `tests/test_sync.py` · `tests/test_snapshot_sync.py` · `tests/test_exporter.py` · `tests/test_qbapi_wire.py`
  - 池内 5 文件含 S5 新守阵: test_module_host / test_snapshot_sync / test_local_qb_service / test_exporter(T7a, +28 守阵, commit 8e073df7)+ test_qbmanager(T7b, +39 守阵, commit dda19819), helpers.py make_manager 扩参同两 commit; 本轮开工已 cp 进镜像并 md5 核对一致(另 4 池文件 / test_qbapi_wire.py / 5 个差 src 文件与首轮逐位一致已核, tests/conftest.py 镜像侧 LF = 本地 CRLF checkout 伪差已排除)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**
- **镜像口径**: head **3275c1d4**(与首轮逐位一致, 两轮同 head 数字可比); ⚠ 镜像 pyproject 已本地加 `timeout_multiplier = 2`、venv pytest 钉回 **9.1.1**(pytest 9.2.0 会被 sidefx 守阵记越界 FSDEL 毒化整轮, **未刷新/未重建/未 uv sync**, `--no-refresh --no-sync` 原样复用)
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— S5 守阵 commit(8e073df7/dda19819)在本地分支线而镜像 head 3275c1d4 早于它, cp 新池文件进镜像 + `mutants.run --no-refresh --no-sync`; 5 文件顺序分跑(`commands run mutants.run -- --target '**/core/<f>.py' --pool <10 文件>`), **一次干净跑完 rc 全 0, 无 R28/R29 那类 WSL VM 被杀/分块续跑**
- **deselect 口径**: `set_conf.py` DEFAULT_DESELECT 维持 **8 条**(R30 S5 新增 5 条已入库, 首轮即用 8 条口径, 复跑一致), 本轮零新增
- **新增存活 0**(逐 id 对差做实): 复跑存活 101 全部 ⊆ 首轮 444 存活, 只有移出无移入
- **复跑存活构成闭合(修正口径 101)**: 等价 **95**(112 − 连带杀 17)+ 真洞 **6**(3 注记 export_44/46+`__init___43` + 3 签名默认极低 `__init___1`/`run_1`/`_refresh_torrents_1`)= **101** ✓
- **连带杀 17 条判读等价, 全链条目级复验稳定复现(0 条环境噪声)**: 逐 id 与机理见任务档案 R30(同 W4 z_row_39 / W3 kib_1 形态)。
- **超时 16→16 构成变化(修正口径)**: 首轮盲区 16(qbmanager 15 + exporter gtn_15)→ **run_20 复跑被杀(盲区回收, §G 销 1)** + **gtn_17 稳定超时(真洞中「双重冲突死循环」被新守阵场景触发, survived→盲区新入)** + TypeError 空转环 run_91/92/93/111 **复跑仍超时(改判预期未兑现, 维持盲区)** → 终态 qbmanager 14 + exporter 2(gtn_15/17)= 16
- **全轮 5 条 killed→timeout 翻转, 条目级复验**(全限定名单跑): run_task_line_1 / _task_line_5 / run_191 / run_200 **恢复被杀**(受扰环境时序假象, 同 R29 `__init___7` 形态, 与首轮判定一致)+ gtn_17 稳定超时(见上)
- **守阵覆盖口径(S5 声明 vs 复跑实测)**: S5b 红验 128/128 + 201/201 全红 → 声明盖 329/332; **复跑实测 = 325 杀 + gtn_17 盲区 1, 真洞残存活 6** —— 3 条签名默认极低(`__init___1`/`run_1`/`_refresh_torrents_1`)红验声明覆盖但复跑稳定存活(红验同构构造与 mutmut 实际变异形态不符, 同 R29「红验纠偏均为脚本映射错误」族); 3 条注记留账(export_44/46 + `__init___43`)口径不变

### 三分类终态(W6 池口径, 详见任务档案 R30 与 tmp-analysis/w6-r30/classify-a/b.md)

- **真洞 332**(高 1 / 中 135 / 低 168 / 极低 28): 复跑实测守阵覆盖 325 杀 + gtn_17 死循环盲区 1; **残存活 6 条留账**(3 注记: export_44/46 默认分支不可达 + `__init___43` 显式配裸文件名 state_file 才可达; 3 签名默认极低: `__init___1` no_lock / `run_1` dry_run / `_refresh_torrents_1` dry_run——生产构造点全显式传参, 补测需构造「不传显式参」的构造点用例, 留后续轮)。
- **等价 112**: 复跑实测存活面 95(连带杀 17, 逐条机理见任务档案 R30); 其余 95 条逐条理由见 classify。
- **假存活 0**(宽池轮预期兑现)。
- **超时盲区 16**(qbmanager 14 + exporter 2): 并发面阻塞/忙转/死循环形态 + TypeError 空转环 4 条(改判预期未兑现), 维持 bug 备注口径不硬判(入池 issue 记账)。
- **no tests 157**(qbapi 147 + qbmanager 10): **池外触达口径**(S1 §1/§2: qbapi 53 def 中 webui commands getattr 动态派发 19 方法 + routes 3 + transfer adapters 1 + W8/W9 模块池 4 + hr/tray/ui 池 10 触达 qbmanager reconnect/status_snapshot, 零「真正零触达」函数)——按 issue 口径不扩池, W8/W9 轮自然覆盖后再核。
- **S5 对账**: 67 守阵(28+39)红验 128/128 + 201/201 全红; 复跑实测对真洞的净覆盖 325/332(声明 329/332 的 3 条差 = 签名默认形态红验误判, 见上); 翻案 0 条(run_128/run_148 系 S5b 判等价的判读修正, 连带杀归等价账)。
- **2 件 issue**: `26-11-01-0614-test-core-w6-mutation-notests-offpool`(no-tests 157 池外触达登记)· `26-11-01-0614-test-core-w6-mutation-timeout-doubt-ledger`(超时盲区 16 + 存疑 6 清单; 复跑后盲区构成变化见上, issue 维持记账口径)。
- **dump / results 指针**: 三分类输入 = 首轮 dump/results `tmp-analysis/w6-r30/26-11-01-02{50,52}-core-module-py-*` 等 10 件(module 0250/0252 · qbmanager 0307/0312 · qbapi 0313 · qbclient 0314 · exporter 0315; 原始落盘 `R:\Temp\auto-qb\mutants\`); 复跑 results 5 件 = `tmp-analysis/w6-r30/26-11-01-06{27,54,55,56,58}-core-*-results.txt`(module 9 = 8 survived+1 timeout · qbmanager 81 = 54+17+10 no tests · qbapi 166 = 19+147 · qbclient 3 · exporter 19 = 17+2; 原始落盘 `R:\Temp\auto-qb\mutants\26-11-01-06*`); 条目级复验 26 条输出在会话记录(26 条 = 连带杀 17 + 超时翻转 5 + run_20 + 签名默认 3)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_module_host.py` · `tests/test_snapshot_sync.py` · `tests/test_local_qb_service.py` · `tests/test_exporter.py`(+ helpers.py) | S5a 阶段 28 守阵(红验 128/128 全红), commit 8e073df7(先于本轮 C3) |
| `tests/test_qbmanager.py`(+ helpers.py make_manager 扩参) | S5b 阶段 39 守阵(红验 201/201 全红), commit dda19819(先于本轮 C3) |
| `.commands/mutants/scripts/set_conf.py` | DEFAULT_DESELECT 3→8 条(读 core 源码文本的静态守阵 deselect), commit 8e073df7(先于本轮 C3) |
| `memory-bank/issues/26-11-01-0614-test-core-w6-mutation-notests-offpool.html` · `memory-bank/issues/26-11-01-0614-test-core-w6-mutation-timeout-doubt-ledger.html` | 批量入池 no-tests 登记 1(standard)+ 盲区/存疑记账 1(light), commit c06974af(先于本轮 C3; 本轮 S7 补档案 Refs 反向声明修 2 条单向认领链) |
| `memory-bank/testing/baselines/26-11-01-0722-mutation-core-w6-orchestrator.md` | 本切片 |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W6 口径)+ §03 core 行 W6 已做注记同步 |

**未改**: `src/` 零改动(纯补测[先于本轮] + 批量入池[先于本轮] + 文档); 选择池未扩(10 文件两轮一致; no-tests 157 按池外触达 issue 口径不扩)。
