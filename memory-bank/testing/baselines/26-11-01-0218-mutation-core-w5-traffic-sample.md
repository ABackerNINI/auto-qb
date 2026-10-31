# 4411 passed + 2 skipped(根) —— 1,805 变异 / 复跑杀死率 93.91%(修正口径 94.07%) —— core W5 traffic_sample_mod R29 变异审计: 首轮与补测后复跑(同目标同池)

> 摘要: core 包 W5(R29, 计划 26-10-31-0128): 目标 `**/core/modules/traffic_sample_mod.py`(1,622 行)单文件 **1,805 变异** · 池 3 文件定向 → 首轮 **杀 1,598 / 存活 197 / no tests 0 / 超时 7 / not checked 3**(杀死率 **89.07%**; 主轮 811.3s 至 1624/1805 被截断 + WSL VM 反复被杀, 条目级续跑清尾) → S4 verify 候选 38(SURVIVED 37 / KILLED 1 / 推翻假存活 1)+ S5a 补测 **38 守阵**进池(test_traffic_sample, 红验 **88/88 全红**, commit 1ae96e94)+ 批量入池 2 件(commit eddb7396)→ **同目标同池复跑(全轮实测): 杀 1,695 / 存活 96 / no tests 0 / 超时 14 / not checked 0**(杀死率 **93.91%**, **新增存活 0**); 全轮转超时 5 条经条目级复验: 3 恢复被杀 + 1 复验存活(环境时序假象)+ 1 死循环族稳定超时 → **修正口径 杀 1,698 / 存活 97 / 超时 10(杀死率 94.07%)**。三分类终态(S5a 落账): **真洞 101(高 0 / 中 31 / 低 70; 其中 100 条已被 S5a 38 守阵覆盖)** · 等价 95(修正口径存活面 94: `_append_record_120/122` 被新守阵连带杀)· 假存活 1(`__init___13`, 守阵已在全套件)· 超时盲区 10。bug 面 1(`_publish_live_tail_59`, 反向暴露原码契约 bug, 入池 issue 非补测)+ 未盖 1(`_agg_credit_day_file_9`, 存疑注记 issue)。**零 `src/` 改动**(纯补测 + 入池 + 文档)。
> 基线时间: 2026-11-01 02:18
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4411 passed + 2 skipped / 覆盖率 99.06%**(C3 收尾实测 129.59s, mut-core-audit 本地树; 首跑 1 failed = `test_docs_forms.py::test_claim_chain_is_bidirectional` —— R29 交接档(S5a 入池 commit eddb7396)遗留的 **2 条单向认领链**(26-11-01-0050 两件入池 issue 声明了本档案、档案未反向声明), 本轮 S7 回写把反向声明补进档案 `Refs:` 后复跑全绿)。

### 首轮与复跑对照(每轮一行)

| 目标 / 轮次 | 变异 | 杀 | 存活 | no tests | 超时 | not checked | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|---|
| traffic_sample_mod.py 首轮(2026-10-31 19:24 dump) | 1,805 | 1,598 | 197 | 0 | 7 | 3 | 主轮 811.3s 至 1624/1805 被截断, 条目级续跑清尾(未整录) | 89.07% |
| **traffic_sample_mod.py 复跑(S6 全轮实测, 2026-11-01 01:33–02:00)** | **1,805** | **1,695** | **96** | **0** | **14** | **0** | **未整录**(WSL VM 反复被杀, 分块幂等续跑, 墙钟 ≈27 min) | **93.91%** |
| 复跑·条目级复验修正口径(同轮) | 1,805 | **1,698** | **97** | 0 | **10** | 0 | 复验 5 条 ≈5 min | **94.07%** |

- **目标(glob)**: `**/core/modules/traffic_sample_mod.py`(单文件, target 只收单 glob)
- **选择池(逐个文件, 3 个; 两轮一致, 未改池)**:
  `tests/test_traffic_sample.py` · `tests/test_traffic_limits.py` · `tests/test_traffic_store.py`
  - 池内 1 文件含 S5a 新守阵: test_traffic_sample.py(+38 守阵, commit 1ae96e94, 先于本轮 C3); 另 2 池文件与目标 src 的 md5 与本地逐位一致已核(镜像内四文件 md5: `d9adcbe2` / `836b69ed` / `f28c0f0e` / `24756800`)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**
- **镜像口径**: head **3275c1d4**(与首轮逐位一致, 两轮同 head 数字可比); ⚠ 镜像 pyproject 已本地加 `timeout_multiplier = 2`、venv pytest 钉回 **9.1.1**(pytest 9.2.0 会被 sidefx 守阵记越界 FSDEL 毒化整轮, **未刷新/未重建/未 uv sync**, `--no-refresh --no-sync` 原样复用)
- **机器**: WSL2 · **8 核**
- **复跑方式**: 硬约束 11 —— S5a 守阵 commit(1ae96e94)在本地分支线而镜像 head 3275c1d4 早于它, `--no-refresh --no-sync` + 镜像内 test_traffic_sample.py 已是 S5a 版(R29 S5a 红验时 cp 进镜像, 本轮开工 md5 核对一致, 无需再 cp); `mutants.run` 首启 79.3s 跑到 645/1805 被 WSL 截断(exit 1)后, **绕过 `mutants.run` 在镜像内 `.venv/bin/mutmut run` 分块幂等续跑**(续跑脚本 `tmp-analysis/w5-resume.sh`, 按 `.meta` 的 `exit_code_by_key` 计数判完成, 重试循环直至 1805/1805)
- **deselect 口径**: `set_conf.py` DEFAULT_DESELECT 维持 R28 的 **3 条, 本轮零新增** —— S5a 新守阵逐一核过: `read_text` 全部指向 tmp_path 下的数据文件(v4 day 文件), **无读源码文本的静态守阵**, 未触发 R28 的 stats 恒红缺口(deselect-guards issue 无新实证)
- **新增存活 0**(逐 id 对差做实): 复跑全轮实测 96 存活 + 复验回归 1(`__init___7`)**共 97 条, 全部 ⊆ 首轮 204 存活∪超时集合**, 只有移出无移入
- **存活 197 → 96(修正口径 97)的构成**(新杀 101 全轮实测 / 100 修正口径, 逐 id 对差):
  - **S5a 38 守阵直杀**(含 S4 候选 37 条 SURVIVED 对应的真洞 + 告警节流族 `__init___8` 复验兑现): 红验 88/88 全红的同构变异在复跑实测转杀
  - **等价连带杀 2**: `_append_record_120/122`(`replace(rec, dt_ms=None)` / `replace(rec, )` 纯 no-op 形态)—— S5a 块首游程守阵断言后转可观测, 判读保守非假阴性, 同 W3 kib_1 / W4 z_row_39 形态
  - **盲区回收 1**: `x__record_slots__mutmut_7`(首轮超时盲区)→ 复跑被杀(record_slots 守阵族连带, 盲区 10 → 9)
- **超时 7 → 14(全轮实测)→ 10(修正口径)明细**:
  - 首轮盲区 10(7 dump 超时 + 3 条 not checked `_agg_credit_hours_14/30/31` 补判超时)复跑: **9 条仍超时**(预期, while 循环界死循环未修码)+ `record_slots_7` 转被杀(回收, 见上)
  - 全轮实测另 **5 条转超时**: `__init___7`/`__init___8`(首轮存活)+ `_agg_feed_39`/`_agg_flush_all_2`/`_append_record_167`(首轮被杀)—— 条目级复验(全限定名单跑, `mutmut run <fqid>`): `_agg_flush_all_2` · `_append_record_167` **恢复被杀**(与首轮判定一致, 全轮超窗属受扰环境)· `__init___8` **被杀**(S5a 告警节流守阵直杀, 预期兑现)· `__init___7` **复验 SURVIVED**(classify 判等价, 与复验一致; 全轮超窗为 WSL 受扰环境时序假象, 同 R26 limits flaky 前科的镜像形态)· `_agg_feed_39` **TIMEOUT 稳定复现**(实参错位 `credit[0]→credit[1]` 进 `_agg_credit_hours` while 游标不推进, 与盲区 14/30/31 同族机械死循环形态, 不进三分类)
  - 复验后注册表终态 = 修正口径行(杀 1,698 / 存活 97 / 超时 10); 全轮实测行与复验注记并存, 下轮对差以修正口径为准
- **复跑存活构成闭合(修正口径 97)**: 等价 **94**(95 − 连带杀 2)+ 假存活 **1**(`__init___13`, 守阵已在全套件不在池)+ bug 面 **1**(`_publish_live_tail_59`, 反向暴露原码契约 bug, 不补测)+ 未盖 **1**(`_agg_credit_day_file_9`, 存疑注记) = **97** ✓

### 三分类与处置(W5 池口径, 详见任务档案 R29 与 tmp-analysis/mut-core-w5-classify.md)

- **真洞 101**(高 0 / 中 31 / 低 70)处置闭环: **100 条已被 S5a 38 守阵覆盖**(复跑实测转杀)+ **bug 面 1**(`_publish_live_tail_59`): 变异反向暴露原码契约 bug(`LiveTail.interval_s` 契约在改间隔瞬态窗发布陈旧旧块间隔, 两头违约), 按处置=bug 缺口非 test 缺口入池 `26-11-01-0050-bug-traffic-sample-livetail-stale-interval`; **未盖 1**(`_agg_credit_day_file_9`)入存疑注记 `26-11-01-0050-test-core-w5-mutation-dayfile-zeroblock-doubt`。
- **等价 95**(S5a 终态, 含 `__init___14` 翻案): 复跑修正口径存活面 **94**(`_append_record_120/122` 连带转杀); 其余 93 条逐条理由见 classify(初始化死存储 / 钳制回默认 / 契约性等价 / DEBUG 文案族)。
- **假存活 1**(`__init___13`): S4 全套件实证(test_qbmanager 等 7 条新增失败且复跑复现), 守阵已在全套件(test_qbmanager 经 module host 装配间接触达), 无需补测; 复跑池内存活符合预期。
- **超时盲区 10**(S3 的 7 + S4 补判 3): while 循环界机械死循环形态(record_slots ×2 / hour_spans ×3 / agg_credit_hours ×5), 复跑 9 条仍超时 + 1 条回收; 处置=bug 备注口径非补测。
- **S4 对账**: 候选 **38**(硬约束 10 收窄: 三块真洞危害序头部 + 全部存疑点 + 日志面代表)→ verify 实测 **SURVIVED 37 / KILLED 1 / 推翻假存活 1**(`__init___13`)/ FLAKY 0; 基线 4356 passed + 12 skipped 0 失败; 逐条结论见 classify §S4。
- **红验 88/88 全红**(S5a 手搓同构变异复验 + 盲区坐实, commit 1ae96e94; 手搓数字不进任何计数, 量化以本切片复跑为准)。
- **3 件 issue**: `26-11-01-0050-bug-traffic-sample-livetail-stale-interval`(bug 面)· `26-11-01-0050-test-core-w5-mutation-dayfile-zeroblock-doubt`(未盖存疑注记)· `26-10-31-1539-bug-mutation-tooling-verify-channel`(工具坑, R29 S4 补充形态④已注记: WSL 不可达 ≠ 镜像缺失)。
- **dump / results 指针**(R:\Temp\auto-qb\mutants\): 三分类输入 = 首轮 dump `26-10-31-1924-core-modules-traffic-sample-mod-py-mutants-dump.txt`(204 条 = 197 survived + 7 timeout); S4 verify = `s4-verify-w5-s4-ids.txt`(38 条终态); 复跑全轮实测 = `26-11-01-0200-core-modules-traffic-sample-mod-py-results.txt`(110 条 = 96 survived + 14 timeout)+ dump `26-11-01-0204-…-mutants-dump.txt`(110 条带 diff); 复验终态 = `26-11-01-0235-core-modules-traffic-sample-mod-py-results.txt`(107 条 = 97 survived + 10 timeout)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_traffic_sample.py` | S5a 阶段 38 守阵(+红验 88/88 全红), commit 1ae96e94(先于本轮 C3) |
| `memory-bank/issues/26-11-01-0050-bug-traffic-sample-livetail-stale-interval.html` · `memory-bank/issues/26-11-01-0050-test-core-w5-mutation-dayfile-zeroblock-doubt.html` | 批量入池 bug 面 1 + 存疑注记 1, commit eddb7396(先于本轮 C3; 本轮 S7 补档案 Refs 反向声明修 2 条单向认领链) |
| `memory-bank/testing/baselines/26-11-01-0218-mutation-core-w5-traffic-sample.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R29 轮次完成条目追加 + Refs 反向声明(2 条 issue + 本切片) |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W5 口径) |

**未改**: `src/` 零改动(纯补测[先于本轮] + 批量入池[先于本轮] + 文档); `.commands/mutants/scripts/set_conf.py` 零改动(DEFAULT_DESELECT 维持 3 条); 选择池未扩(bug 面/未盖各 1 条按 issue 口径处置, 留后续轮)。
