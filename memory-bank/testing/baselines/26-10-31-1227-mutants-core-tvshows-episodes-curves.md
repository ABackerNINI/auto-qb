# 576 变异 / 复跑杀死率 88.19% —— core/tvshows·episodes·curves W3 变异审计: 首轮与补测后复跑(同目标同池)

> 摘要: core/ 包 W3(R27, 计划 26-10-31-0128): 目标 `**/core/tvshows.py`(310 变异)+ `**/core/episodes.py`(115 变异)+ `**/core/curves.py`(151 变异)(target 只收单 glob, 分三次跑) · 池 4 文件定向 → 首轮合计 **576 变异 / 杀 494 / 存活 80 / no tests 0 / 超时 2**(杀死率 **85.8%**) → S5 补测进池(tvshows +91 行 / curves 池文件 +40 行, 红验 14/14 全红) → **同目标同池复跑: 杀 508 / 存活 66 / no tests 0 / 超时 2(杀死率 88.19%, 存活 −14, 新增存活 0)**。三分类(W3 池口径): 确认真洞 46 处置闭环 = **中危 9 条(7 守阵体)+ find_episode_31 由 S5 定向补测销账**(复跑实测 KILLED 14 条: tvshows 10 + curves 4)+ **低危 23 静态判读 8 簇批量 test issue 入池(24 条目)** + **timeout 2**(死循环 DoS 形态实跑裁定, bug 备注随键归一簇 issue)+ 极低危 5 不补; 等价 28; 假存活 1(aggregate_2, 池外 test_expr_eval 杀, 处置=池调整建议, 留后续轮); 待定 3 不追。**零 `src/` 改动**(纯补测 + 批量入池 + 文档)。
> 基线时间: 2026-10-31 12:27

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4237 passed + 2 skipped**(S5 补测阶段实测誊写, commit 0af9e74d; 本轮 C3 零代码/测试改动, 数字不重采)。

### 首轮与复跑对照(每轮一行)

| 目标 / 轮次 | 变异 | 杀 | 存活 | no tests | 超时 | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| tvshows.py 首轮(2026-10-31 09:00) | 310 | 262 | 46 | 0 | 2 | 未单录 | 84.52% |
| **tvshows.py 复跑(S6, 12:23)** | **310** | **272** | **36** | **0** | **2** | 见下注 | **87.74%** |
| episodes.py 首轮(09:02) | 115 | 99 | 16 | 0 | 0 | 未单录 | 86.09% |
| **episodes.py 复跑(S6, 12:24)** | **115** | **99** | **16** | **0** | **0** | **14.6s**(wrapper 实测) | **86.09%** |
| curves.py 首轮(09:03) | 151 | 133 | 18 | 0 | 0 | 未单录 | 88.08% |
| **curves.py 复跑(S6, 12:24)** | **151** | **137** | **14** | **0** | **0** | **10.5s**(wrapper 实测) | **90.73%** |
| **合计: 首轮(09:00–09:03)** | **576** | **494** | **80** | **0** | **2** | — | **85.8%** |
| **合计: 复跑(S6)** | **576** | **508** | **66** | **0** | **2** | — | **88.19%** |

- **目标(glob)**: `**/core/tvshows.py` · `**/core/episodes.py` · `**/core/curves.py` —— target 只收单 glob, 三文件分三次跑, 数字分列不合池(合计行仅作汇总刻度)
- **选择池(逐个文件, 4 个; 两轮一致)**:
  `tests/test_tvshows.py` · `tests/test_episodes.py` · `tests/test_speed_curve.py` · `tests/test_traffic_monitor_dat.py`
  - 池内 2 文件含 S5 新守阵: test_tvshows.py(+91 行) / test_speed_curve.py(+40 行); test_episodes.py / test_traffic_monitor_dat.py 两轮无改动
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · 默认镜像 `~/auto-qb-mut`(head `c18d07a4`, 与首轮同一 head, 数字可比)
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— 本地守阵 commit(0af9e74d)未在 origin/develop, `--no-refresh` + 手工 cp 2 个改过的池测试文件(test_tvshows / test_speed_curve)进镜像 `tests/`(md5 逐一核对一致)
- **墙时注记**: tvshows 复跑跑了同命令两遍 —— 第一遍(12:23, 结果文件 1223)未录墙时, 第二遍(12:26, 结果文件 1226)wrapper 实测 **35.0s**; 两遍 SUMMARY 与逐 id 完全一致(36 survived + 2 timeout, 集合逐位相同), 表为稳定结果非抖动
- **存活 −14 的构成**(逐 id 对差, 三目标**新增存活均 0**): tvshows 46→36(新杀 10: find_episode_2/11 · normalize_key_15/16 · title_and_key_4/5 · strip_group_22 · parse_files_20 · refine_with_files_1 · find_episode_31 —— 与 S5 守阵目标逐一对应); curves 18→14(新杀 4: aggregate_20 定向销账 + kib_1 / kib_5 / bytes_to_kib_floor_6 由单位换算契约守阵连带杀 —— kib_1 原判等价(域内·防御分支), 属连带销账非假阴性); episodes 16→16(S5 未动 test_episodes, 集合逐 id 一致)
- **超时盲区 2 条复跑仍超时**(tvshows `normalize_key_34/38`): 预期行为 —— 死循环形态未修码, 口径照旧(S4 已实跑裁定死循环 DoS 形态, 处置=随键归一簇 issue 记 bug 备注, 修复取代码侧非补测)
- **aggregate_2 复跑仍存活**: 预期 —— 击杀它的 tests/test_expr_eval.py 不在本轮池(池调整建议未实施, 如实记), 处置=池调整建议, 留后续轮
- **池调整建议(未实施, 留后续轮)**: ① test_expr_eval.py 加进 W 轮选择池; ② mutmut 配置面把 5 条 flaky 测试(relocate / web_views_reload×2 / commands_engine wrapper / hr_discovery 绑定类)加进 deselect

### 三分类与处置(W3 池口径, 详见任务档案 R27 与 tmp-analysis/mut-core-w3-classify.md)

- 确认真洞 **46** 处置闭环: **中危 9 条(7 守阵体)+ find_episode_31 由 S5 定向补测销账**(守阵进 test_tvshows / test_speed_curve, 红验 14/14 全红; 复跑实测 KILLED 14 条逐 id 对应)+ **低危 23 静态判读 8 簇批量 test issue 入池(24 条目)**(链接见下)+ **极低危 5 不补**(strip_group_12/14/16 · title_and_key_40 · dir_season_14)。
- **timeout 2**(normalize_key_34/38): S4 实跑裁定死循环(DoS 形态, 危害=追剧视图每 tick 首算挂死); bug 备注随键归一簇 issue, 修复取代码侧。
- **等价 28**(逐条理由见 classify: `[-1]` 取尾段免疫 / 0·1 边界自吸收 / 防御默认等径 / 模式同起点互斥 / 无锚正则前缀免疫 / 离散域外边界)。
- **假存活 1**(aggregate_2): S4 verify 实测 KILLED(池外 test_expr_eval::test_traffic_values 击杀), 坐实假存活; 复跑仍存活属预期(池未变)。
- **待定 3 不追**(cjk_int_23 · find_episode_30 · title_and_key_2: 域外/病态语义卡点)。
- **S4 覆盖 28 条**: verify 实测 **25 SURVIVED / 1 KILLED / 2 TIMEOUT**(KILLED = aggregate_2 假存活坐实; TIMEOUT = 2 条死循环实跑裁定), 未判定 0; 判据=全套件差集(后期 deselect 5 条 flaky)。
- **红验 14/14 全红**(S5 手搓同构变异形态复验, 手搓数字不进任何计数, 量化以本切片复跑为准)。
- **8 条批量 issue**: `memory-bank/issues/26-10-31-1211-test-core-w3-mutation-year-bare-edges.html` · `26-10-31-1212-test-core-w3-mutation-cjk-numerals.html` · `26-10-31-1212-test-core-w3-mutation-curves-alias-badlines.html` · `26-10-31-1212-test-core-w3-mutation-curves-unit-edges.html` · `26-10-31-1212-test-core-w3-mutation-episodes-dir-strip.html` · `26-10-31-1212-test-core-w3-mutation-group-brackets.html` · `26-10-31-1212-test-core-w3-mutation-key-normalize.html` · `26-10-31-1212-test-core-w3-mutation-title-trim.html`
- **dump / results 指针**(R:\Temp\auto-qb\mutants\): 三分类输入 = 首轮 dump `26-10-31-0900-core-tvshows-py-mutants-dump.txt`(46 survived + 2 timeout)+ `26-10-31-0902-core-episodes-py-mutants-dump.txt`(16)+ `26-10-31-0903-core-curves-py-mutants-dump.txt`(18); 复跑 = `26-10-31-1223-core-tvshows-py-results.txt`(36 + 2 timeout; 复跑② 1226 逐 id 一致)+ `26-10-31-1224-core-episodes-py-results.txt`(16)+ `26-10-31-1224-core-curves-py-results.txt`(14)

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_tvshows.py` · `tests/test_speed_curve.py` | S5 阶段 9 守阵(+91 / +40 行, 红验 14/14 全红), commit 0af9e74d(先于本轮) |
| `memory-bank/issues/26-10-31-1211/1212-test-core-w3-mutation-*.html`(8 条) | 低危批量 test issue 入池(24 条目, doc-refs 反向声明任务档案), commit 43c05be4(先于本轮) |
| `memory-bank/testing/baselines/26-10-31-1227-mutants-core-tvshows-episodes-curves.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R27 轮次完成条目追加 |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W3 口径) |

**未改**: `src/` 零改动(纯补测 + 批量入池 + 文档); 选择池未扩(test_expr_eval 入池与 flaky deselect 留后续轮)。
