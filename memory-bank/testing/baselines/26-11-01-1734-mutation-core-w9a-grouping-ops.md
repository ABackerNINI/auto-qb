# 4609 passed + 2 skipped(根) —— core W9a R33 变异审计: grouping+ops 两文件 S6 同池复跑(1,958 变异, 杀死率 68.74% → 79.78%)

> 摘要: core 包 W9a(R33, 计划 26-10-31-0128): 目标 2 文件 `**/core/modules/grouping_mod.py` + `**/core/modules/ops_mod.py` · 池 10 文件 → 首轮(S2, 2 文件分跑 + 合并 glob 三跑) **1,958 变异 / 存活 603(grouping 234+2 no tests · 71.32% + ops 369+5 超时+2 no tests · 66.87%)** → S3 三分类(S5a 收尾翻案 pd32/pd34/pr16 改判等价后) 真洞 449(高 12/中 125/低 308/极低 4)/等价 154/超时盲区 5 → S5a 补 **46 守阵**(红验 189/189 全红, commit 8b6f4549) → **S6 同目标同池复跑(2 文件分跑 + 合并 glob): 杀 1,562 / 存活 390 / 超时 6 / no tests 0(79.78%)**; 对差: 移出 222 = 红验 189 + 连带杀 33(等价 5 + 真洞 28), not-killed 对差 6 条经逐条 apply + 全池套件实测做实为**首轮 T17a 污染 stats 假杀纠正**(5 判真洞·低 + 1 超时盲区), 非新真洞; 余量 265 批量入池 1 件(26-11-01-1711); mutmut 3.8 mtime 竞态立坑档。**零 `src/` 改动**(纯补测[先于本轮] + 入池 + 文档)。
> 基线时间: 2026-11-01 17:34
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL**: `commands run test.full` —— **4609 passed + 2 skipped / 覆盖率 99.16%**(C3 收尾实测 119.46s, mut-core-audit 本地树; 档案 Refs 与 26-11-01-1711 doc-refs 双向补链后一次全绿)。

### 首轮与复跑对照(全轮一行 + 逐文件两行)

| 轮次 | 变异 | 杀 | 存活 | 超时 | no tests | 杀死率 |
|---|---|---|---|---|---|---|
| 首轮(S2, 2026-11-01 午后, 2 文件分跑 + 合并 glob 三跑) | 1,958 | 1,346 | 603 | 5 | 4 | 68.74% |
| **复跑(S6, 2026-11-01 16:57–17:06, 2 文件分跑 + 合并 glob)** | 1,958 | **1,562** | **390** | **6** | **0** | **79.78%** |

| 目标文件 | 变异 | 存活+盲区(首轮) | 杀(复跑) | 存活(复跑) | 超时(复跑) | 杀死率(首轮→复跑) | 复跑墙时 |
|---|---|---|---|---|---|---|---|
| modules/grouping_mod.py | 823 | 234+2 no tests | 678 | 145 | 0 | 71.32% → 82.38% | 44s(25.35 mut/s) |
| modules/ops_mod.py | 1,135 | 369+5 超时+2 no tests | 884 | 245 | 6 | 66.87% → 77.89% | 4m08s(4.98 mut/s) |
| **合计** | **1,958** | **603+5+4** | **1,562** | **390** | **6** | **68.74% → 79.78%** | ≈5 min + 合并 glob 6s(stats 复验) |

- **目标(glob)**: 2 个单文件 glob(同首轮逐文件跑) + 合并 glob `**/core/modules/{grouping,ops}_mod.py` 两 glob 收官态(R33 先例, 让两份 meta 共存)
- **选择池(10 个; 两轮一致)**: `tests/test_grouping.py` · `test_grouping_relocate.py` · `test_relocate_exec.py` · `test_file_access.py` · `test_ops.py` · `test_actions.py` · `test_checking.py` · `test_logging.py` · `test_utils.py` · `test_modules_p5.py`(S5a 改过的 test_grouping/test_ops 已 cp 进镜像 md5 核对一致; test_checking/test_actions 本轮未改, 另 6 池文件逐位一致已核)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · forkserver · **专用镜像 `~/auto-qb-mut-core`**
- **镜像口径**: head **3275c1d4** 原样复用(ops_mod.py 副本 = HEAD 逐位一致, 首轮已 cp; qbapi/compat/record/webui_commands 保持镜像 head 版 = 首轮同态); **未刷新/未重建/未 uv sync**(`--no-refresh --no-sync`, venv pytest 钉 **9.1.1**); 跑前**整删 `mutants/` + mutmut-stats.json**(坑①处置的全量形态, 池基线预验 606 passed + 4 skipped 全绿)
- **deselect**: 9 条镜像口径原样(8 条 DEFAULT_DESELECT + 镜像内第 9 条 `test_relocate_exec::test_spawn_args_pinned` —— 本轮池含 test_relocate_exec, R32 已补, 基线实测 deselect 1 生效)
- **对差(逐 id, 全构成)**: 移出 222 = **红验 189**(grouping 87 + ops 102, 含 sections pin 4)+ **连带杀 33** = 等价 5(cr4/ws2/sc10/jn18/rt14 —— 同 W4-W7「新守阵精确断言把等价转可观测」形态)+ 真洞 28(中 1: fl6; 低 27: sy1/sy3/bt5/rb55-62/sb9/rt3/rt9/tl52/tl70/st6/na3/ap13/15/16/dl13/gn12/13/15/16/ss11 —— 簇级覆盖兑现); 复跑 dump 与首轮 245 条共有 id diff 逐字节一致 = 无编号漂移
- **not-killed 对差 6 条 = 首轮假杀纠正, 非新真洞**(首轮判 killed、复跑 not-killed; 逐条 `mutmut apply` + 全池 10 文件套件实测做实): **5 条 606 passed 全绿**(checking_evidence#15 hash[:9] 审计文案 / gates_detail#67·#170 闸文案 / settle#59 广播失败日志 / prepare#24 备份失败收敛文案, 均**真洞·低**并入余量, 成因归首轮 T17a 污染 stats 假杀 —— 池只增不减且当前池实测全绿, 非测试回退)+ **1 条** skip_step_add#6 apply 实测先 F 后挂起 rc=124 → 超时盲区 +1(TIMEOUT 不判死口径)
- **首轮 5 条超时全稳定**(逐 id 同, 零翻转零回收); 复跑存活构成闭合: 等价 **149**(154 − 连带 5)+ 真洞 **241**(余量 236 + 假杀纠正 5)= 390 ✓
- **三分类终态(S6 收账)**: 真洞 **454**(高 12 / 中 125 / 低 313 / 极低 4)= 红验覆盖 189 + 余量 **265**(grouping 68 / ops 197, 已入池 26-11-01-1711 一件); 等价 **149**; 超时盲区 **6**; no tests 0(sections pin 兑现转 killed)
- **1 件 issue(余量入池, 有意不补测)**: [`26-11-01-1711-test-core-w9a-mutation-low-residue`](../../issues/26-11-01-1711-test-core-w9a-mutation-low-residue.html); **1 条工具坑档**: [`pitfalls/testing/mutmut-mtime-race-stale-trampoline.md`](../../pitfalls/testing/mutmut-mtime-race-stale-trampoline.md)(T17a 跨轮增量 mtime 竞态 → forced-fail 假轮 + 全 no-tests 污染 stats / T17b 镜像副本回写无 trampoline 原件 → dump 无法重放, mutate_file_contents 原位重建; 本轮 run B 复现形态①一次); 档案 Refs 双向声明
- **dump / results 指针**: 首轮 = `tmp-analysis/w9a-r33/26-11-01-1445-*-results.txt` + `26-11-01-1455-*-dump.txt` + `26-11-01-1500-merged-results.txt`(grouping 1455 dump 重放失败经 mutate_file_contents 原位重建后重导出 `26-11-01-1505-grouping_mod-redump.txt`); 复跑 = `rerun-merged-results.txt` + `26-11-01-1710-core-modules-ops-mod-py-mutants-dump.txt`; 对账产物 = `s6-reconcile-report.txt` + `collateral-tiers.txt` + `five-suspect-diffs.txt` + `dump-diff-compare.txt` + `rerun-diff-report.txt`; 三分类输入 = `classify-grouping.md` / `classify-ops.md`(含 S5a 覆盖账目节 + S6 复跑落账节); 红验 = `s5-redverify-units.py`

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_grouping.py`(25 守阵)· `tests/test_ops.py`(22 守阵) | S5a 补测, commit 8b6f4549(先于本轮 C3) |
| `memory-bank/issues/26-11-01-1711-test-core-w9a-mutation-low-residue.html` | 余量批量入池(本轮) |
| `memory-bank/pitfalls/testing/mutmut-mtime-race-stale-trampoline.md` | 工具坑立档(本轮) |
| `memory-bank/testing/baselines/26-11-01-1734-mutation-core-w9a-grouping-ops.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R33 条目 + Summary/S 步表收口 W9a |
| `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html` | §07 覆盖进度总表 core/ 行更新(W1–W9a 口径)+ §03 core 行改「W1–W9a 已做, W9b 待做」 |
