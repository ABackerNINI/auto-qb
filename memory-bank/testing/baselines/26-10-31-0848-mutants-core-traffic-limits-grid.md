# 1112 变异 / 复跑杀死率 88.58% —— core/traffic W2 变异审计: 首轮与补测后复跑(同目标同池)

> 摘要: core/ 包 W2(R26, 计划 26-10-31-0128): 目标 `**/core/traffic_limits.py`(312 变异)+ `**/core/traffic_grid.py`(800 变异)(target 只收单 glob, 分两次跑) · 池 4 文件定向 → 首轮合计 **1112 变异 / 杀 933 / 存活 176 / no tests 0 / 超时 3**(杀死率 **83.89%**) → S5 补 22 守阵进池(红验 36/36 全红) → **同目标同池复跑: 杀 985 / 存活 121 / no tests 0 / 超时 6(杀死率 88.58%, 存活 −55, 新增存活 0)**。三分类(W2 池口径): 真洞 98 处置闭环 = **定向补测 36 条销账**(22 守阵)+ **低危 9 簇缩并 8 条批量 test issue 入池(43 条目)** + FLAKY 1(gtp_28 维持真洞已补测); 等价 76; 假存活实证 2(app_36/gtp_29, 复跑均被杀); 超时盲区 3→6(机械死循环形态人工判死)。**零 `src/` 改动**(纯补测 + 批量入池 + 文档)。
> 基线时间: 2026-10-31 08:48

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4228 passed + 2 skipped**(S5 补测阶段实测誊写; 本轮 C3 零代码/测试改动, 数字不重采)。

### 首轮与复跑对照(每轮一行)

| 目标 / 轮次 | 变异 | 杀 | 存活 | no tests | 超时 | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| traffic_limits.py 首轮(2026-10-31 05:48) | 312 | 238 | 74 | 0 | 0 | 未单录 | 76.28% |
| **traffic_limits.py 复跑(S6, 08:32)** | **312** | **265** | **47** | **0** | **0** | **75.6s**(wrapper 实测) | **84.94%** |
| traffic_grid.py 首轮(05:45) | 800 | 695 | 102 | 0 | 3 | 未单录(过程含 WSL 崩溃 + 镜像内续跑, 记录在案) | 86.88% |
| **traffic_grid.py 复跑(S6, 08:39)** | **800** | **720** | **74** | **0** | **6** | **408.3s**(wrapper 实测) | **90.00%** |
| **合计: 首轮(05:45 grid + 05:48 limits)** | **1112** | **933** | **176** | **0** | **3** | — | **83.89%** |
| **合计: 复跑(S6)** | **1112** | **985** | **121** | **0** | **6** | — | **88.58%** |

- **目标(glob)**: `**/core/traffic_limits.py` 与 `**/core/traffic_grid.py` —— target 只收单 glob, 两文件分两次跑, 数字分列不合池(合计行仅作汇总刻度)
- **选择池(逐个文件, 4 个; 两轮一致)**:
  `tests/test_traffic_limits.py` · `tests/test_traffic_grid.py` · `tests/test_traffic_sample.py` · `tests/test_traffic_monitor_dat.py`
  - 池内 2 文件含 S5 新守阵(22 条): test_traffic_limits(+184 行) / test_traffic_grid(+189 行)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · 默认镜像 `~/auto-qb-mut`(head `c18d07a4`)
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— 本地守阵 commit 未在 origin/develop, `--no-refresh` + 手工 cp 2 个池测试文件(test_traffic_limits / test_traffic_grid)进镜像 `tests/`(md5 逐一核对一致)
- **存活 −55 的构成**(逐 id 对差, 两文件**新增存活均 0**): 53 条由存活转被杀(36 条为 S5 守阵定向销账 —— 红验 36/36 对应条目; 其余 17 条为同族/同主题守阵连带杀)+ 2 条转超时(bg_52 / bg_53 首轮存活 → 复跑超时); 另 bg_56 首轮被杀 → 复跑转超时(杀死 −1 / 超时 +1)
- **超时盲区 3 → 6**: 首轮 3 条(fb_8 / vgo_88 / vgo_89)+ 复跑新增 3 条(bg_52 / bg_53 原存活, bg_56 原被杀)—— 六条均为「变异使循环发散」的机械超时(死循环或万桶级构造), 人工判死形态, 不进三分类; 超时计数随时长环境波动, bg_56 类跨轮漂移属盲区现象非回归
- **FLAKY 时序注记**: 首轮 limits 存活两源计数 74(dump)与 73 差 1 条(时序敏感变异); 复跑以当轮实测为准(47)
- **S4 判假存活 2 条(app_36 / gtp_29)复跑均实测被杀**(app_36 为 uptime 敏感型: 首轮存活 / S4 verify 环境被杀 / 复跑被杀; gtp_29 被池内 S5 组 totals 守阵连带杀)

### 三分类与处置(W2 池口径, 详见任务档案 R26)

- 真洞 98 处置闭环: **定向补测 36 条销账**(22 守阵进 2 个池文件; 红验 36/36 全红为手搓同构变异形态复验, 手搓数字不进任何计数, 量化以本切片复跑为准)+ **低危 9 簇缩并 8 条批量 test issue 入池(43 条目)**(链接见下)+ **FLAKY 1**(gtp_28: S4 唯一失败为已知 hr 端口 flake, 靶向复跑 3 绿, 维持真洞已补测)。
- **等价 76**(verify 修正后口径: limits 29 + grid 47)。
- **假存活实证 2**(app_36 / gtp_29): S4 verify KILLED, 复跑亦被杀。
- **S4 verify 对账**: 候选 38 条 → SURVIVED 35 / KILLED 2 / FLAKY 1(APPLY_FAIL / TIMEOUT 0)。
- **8 条批量 issue**: `memory-bank/issues/26-10-31-0823-test-core-w2-mutation-parse-edges.html`(4 条) · `26-10-31-0823-test-core-w2-mutation-badbytes-read.html`(6 条) · `26-10-31-0823-test-core-w2-mutation-recorder-defense.html`(3 条) · `26-10-31-0823-test-core-w2-mutation-guard-counter.html`(3 条) · `26-10-31-0823-test-core-w2-mutation-boundary-grid.html`(10 条) · `26-10-31-0823-test-core-w2-mutation-snapshot-mixbucket.html`(8 条) · `26-10-31-0823-test-core-w2-mutation-empty-meta-grid.html`(2 条) · `26-10-31-0823-test-core-w2-mutation-broke-contract.html`(7 条)
- **dump / results 指针**(R:\Temp\auto-qb\mutants\): 三分类输入 = 首轮 `26-10-31-0548-core-traffic-limits-py-mutants-dump.txt`(74 survived)+ `26-10-31-0545-core-traffic-grid-py-mutants-dump.txt`(102 survived + 3 timeout); 复跑 = `26-10-31-0832-core-traffic-limits-py-results.txt`(47)+ `26-10-31-0839-core-traffic-grid-py-results.txt`(74 + 6 timeout)

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_traffic_limits.py` · `tests/test_traffic_grid.py` | S5 阶段 22 条新守阵(红验 36/36 全红), commit b8834462 |
| `memory-bank/issues/26-10-31-0823-test-core-w2-mutation-*.html`(8 条) | 低危批量 test issue 入池(43 条目, doc-refs 反向声明任务档案), commit 72724215 |
| `memory-bank/testing/baselines/26-10-31-0848-mutants-core-traffic-limits-grid.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R26 轮次完成条目追加 |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1+W2 口径) |

**未改**: `src/` 零改动(纯补测 + 批量入池 + 文档)。
